"""Run lens variants over a split and score them offline.

    python -m harness.sweep --lens lenses/temporal/a_calendar.py --variants all --split dev --type temporal --tag r1 --workers 2
Options: --route (select questions by the router instead of gold type; results go to runs/<tag>/<type>-routed/...),
--qfilter REGEX (keep questions whose text matches, case-insensitive), --limit N, --no-abstain (skip unanswerable).
Runs over several gold types (no --type, or --route) also print a per-gold-type breakdown (S, Sall, PA, CF1, route mix).
summary.json carries passages_mean (number of passages = sessions sent to Reactor).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

from core.paths import ROOT, RUNS
from core.types import LONG, SHORT

FIELDS = ["when", "tag", "type", "lens", "variant", "split", "n", "n_answerable", "errors", "S", "PA", "ATR", "SR",
          "ALL", "AC", "HA", "CF1", "chars_mean", "chars_p90", "ms_mean", "abstain_auc", "git"]


def load_lens(path: str):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    spec = importlib.util.spec_from_file_location(f"lens_{p.parent.name}_{p.stem}", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _pack_row(pack) -> dict:
    return {"passages": [{"id": p.id, "date": p.date, "text": p.text[:2500]} for p in pack.passages],
            "hint": pack.hint, "computed": pack.computed, "cite_plan": pack.planned_citations(),
            "route": pack.route, "abstain_p": pack.abstain_p, "included_turns": sorted(pack.included_turns or [])}


def work(job: tuple) -> list[dict]:
    lens_path, variants, split, qids_by_hist = job
    from core.data import gold, questions
    from core.index import HistoryIndex
    from core.pack import message_chars
    from harness.metrics import question_metrics
    lens = load_lens(lens_path)
    g = gold(split)
    qmap = {q.question_id: q for q in questions(split)}
    rows = []
    for hid, qids in qids_by_hist:
        hx = HistoryIndex.load(split, hid)
        for qid in qids:
            q = qmap[qid]
            for name, params in variants:
                row = {"question_id": qid, "variant": name, "question": q.question}
                try:
                    t0 = time.perf_counter()
                    pack = lens.build(q, hx, _variant=name, **params)
                    ms = (time.perf_counter() - t0) * 1000
                    chars = message_chars(q, pack.passages, pack.hint)
                    if qid in g:
                        row.update(question_metrics(pack, g[qid], hx, ms, chars))
                    else:
                        row.update({"chars": chars, "ms": round(ms, 1), "abstain_p": pack.abstain_p})
                    row.update(_pack_row(pack))
                    if isinstance(pack.debug, dict):
                        row["debug"] = {k: v for k, v in pack.debug.items() if k != "ranking"}
                        if "ranking" in pack.debug:
                            row["ranking_top"] = list(pack.debug["ranking"])[:30]
                except Exception as exc:
                    row["error"] = f"{exc!r}\n{traceback.format_exc()[-1500:]}"
                rows.append(row)
    return rows


def git_hash() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip() or "-"
    except OSError:
        return "-"


def print_by_type(vr: list[dict]) -> None:
    """Per-gold-type breakdown of one variant's rows (answerable questions; route mix over all of them)."""
    by = defaultdict(list)
    for r in vr:
        if r.get("type"):
            by[r["type"]].append(r)
    for t in ["ssu", "ssa", "multi", "ku", "temporal"]:
        rs = by.get(t, [])
        ans = [r for r in rs if not r.get("abstain_gold") and r.get("S") is not None]
        if not rs:
            continue
        m = lambda k: sum(r.get(k) or 0.0 for r in ans) / len(ans) if ans else float("nan")
        mix = defaultdict(int)
        for r in rs:
            mix[r.get("route")] += 1
        print(f"     {t:9s} n={len(rs):3d} S={m('S'):5.1f} Sall={m('Sall'):5.1f} PA={m('PA'):.3f} CF1={m('CF1'):.3f} "
              f"routes={dict(mix)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lens", required=True)
    ap.add_argument("--variants", default="all")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--type", help="ssu|ssa|multi|ku|temporal (gold type on dev splits; router on test)")
    ap.add_argument("--route", action="store_true", help="select questions by router prediction instead of gold type")
    ap.add_argument("--no-abstain", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--qfilter", help="regex on the question text (case-insensitive); only matching questions run")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--tag", default="adhoc")
    a = ap.parse_args(argv)

    from core.data import gold, questions
    from core.router import route
    from harness.metrics import summarize
    lens = load_lens(a.lens)
    allv = dict(getattr(lens, "VARIANTS", {"default": {}}))
    names = list(allv) if a.variants == "all" else [v.strip() for v in a.variants.split(",")]
    variants = [(n, allv[n]) for n in names]
    g = gold(a.split)
    qs = []
    for q in questions(a.split):
        if a.type:
            t = route(q.question)[0] if (a.route or q.question_id not in g) else SHORT[g[q.question_id]["question_type"]]
            if t != a.type:
                continue
        if a.no_abstain and g.get(q.question_id, {}).get("abstain"):
            continue
        if a.qfilter and not re.search(a.qfilter, q.question, re.I):
            continue
        qs.append(q)
    if a.limit:
        qs = qs[: a.limit]
    by_hist = defaultdict(list)
    for q in qs:
        by_hist[q.history_id].append(q.question_id)
    items = list(by_hist.items())
    n_jobs = max(1, min(len(items), a.workers * 4))
    jobs = [(a.lens, variants, a.split, items[i::n_jobs]) for i in range(n_jobs)]
    t0 = time.time()
    rows: list[dict] = []
    if a.workers <= 1:
        for j in jobs:
            rows += work(j)
    else:
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for r in ex.map(work, jobs):
                rows += r
    lens_name = Path(a.lens).stem
    typ = (a.type or "all") + ("-routed" if a.route and a.type else "")
    when = datetime.now().strftime("%m-%d %H:%M")
    lb = RUNS / "leaderboard.csv"
    new = not lb.exists()
    gh = git_hash()
    print(f"{len(qs)} questions x {len(variants)} variants on {a.split} in {time.time() - t0:.0f}s")
    print(f"{'variant':24s} {'S':>6s} {'PA':>5s} {'ATR':>5s} {'SR':>5s} {'ALL':>5s} {'AC':>5s} {'HA':>5s} {'CF1':>5s} {'chars':>6s} {'ms':>6s} {'AUC':>5s} err")
    with open(lb, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for name, _ in variants:
            vr = [r for r in rows if r["variant"] == name]
            out = RUNS / a.tag / typ / lens_name / name / a.split
            out.mkdir(parents=True, exist_ok=True)
            with open(out / "per_question.jsonl", "w", encoding="utf-8") as fq:
                for r in vr:
                    fq.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            s = summarize(vr)
            okr = [r for r in vr if "passages" in r]
            s["passages_mean"] = round(sum(len(r["passages"]) for r in okr) / len(okr), 2) if okr else None
            (out / "summary.json").write_text(json.dumps(s, indent=1))
            w.writerow({"when": when, "tag": a.tag, "type": typ, "lens": lens_name, "variant": name, "split": a.split,
                        "git": gh, **{k: s.get(k) for k in FIELDS if k in s}})
            f_ = lambda v: "-" if v is None else (f"{v:.3f}" if isinstance(v, float) and v <= 1.0 else f"{v:.1f}" if isinstance(v, float) else str(v))
            print(f"{name:24s} {f_(s['S']):>6s} {f_(s['PA']):>5s} {f_(s['ATR']):>5s} {f_(s['SR']):>5s} {f_(s['ALL']):>5s} "
                  f"{f_(s['AC']):>5s} {f_(s['HA']):>5s} {f_(s['CF1']):>5s} {f_(s['chars_mean']):>6s} {f_(s['ms_mean']):>6s} "
                  f"{f_(s['abstain_auc']):>5s} {s['errors']}")
            if s.get("Sall") is not None:
                print(f"   if Reactor cites every passage: CF1all={s['CF1all']:.3f} Sall={s['Sall']:.1f}")
            print(f"   -> {out.relative_to(ROOT)}")
            if not a.type or a.route:
                print_by_type(vr)
    errs = [r for r in rows if r.get("error")]
    if errs:
        print(f"\n{len(errs)} errors; first:\n{errs[0]['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
