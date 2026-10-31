"""Out-of-distribution check on LoCoMo (Maharana et al., 2024): does the retrieval side work on a dataset we never tuned on?

LoCoMo: 10 long conversations between two people (19-32 sessions each), ~2k questions with gold answers and evidence
dialogue ids ("D1:3"). Categories: 1 multi-hop, 2 temporal, 3 open-domain, 4 single-hop, 5 adversarial (unanswerable).
Offline only (no Reactor): we build the evidence pack with the full routed system (lenses/pipeline.py + config) and with
the naive keyword baseline (lenses/generic.py naive, 42.9 S on dev), then check whether the gold evidence made it in.

    curl -sSL -o ../data/locomo/locomo10.json https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json
    .venv/bin/python -m harness.ood_locomo --src ../data/locomo/locomo10.json --per-cat 0 --roles user,ab --systems routed,naive,hybrid,hybrid_3k

Conversion: session = session_N (date from session_N_date_time), turn = dia_id, content "Name: text" (+ the photo
caption when a turn shares an image). Roles: "ab" = speaker_a -> user, speaker_b -> assistant; "user" = every turn is a
user turn. Question date = the day after the last session. Shards go to cache/hist/locomo_<roles>/<history_id>.json, so
HistoryIndex.load("locomo_<roles>", hid) works like any split. Output: runs/ood/locomo_results.jsonl (+ a summary).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from multiprocessing import Pool
from pathlib import Path

import core.paths  # noqa: F401  (puts the upstream kit on sys.path)
from core.data import DATE_FMT, shard_dir
from core.paths import ROOT
from core.types import Question

LOCOMO_FMT = "%I:%M %p on %d %B, %Y"
CATS = {1: "multi-hop", 2: "temporal", 3: "open-domain", 4: "single-hop", 5: "adversarial"}
OUT = ROOT / "runs" / "ood"


def _sessions(conv: dict) -> list[int]:
    return sorted(int(k.split("_")[1]) for k in conv if re.fullmatch(r"session_\d+", k) and conv[k])


def convert(src: Path, roles: str) -> tuple[str, list[dict]]:
    """LoCoMo -> our history shards + a flat list of question records (with gold)."""
    split = f"locomo_{roles}"
    out = shard_dir(split)
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for conv_rec in json.loads(src.read_text(encoding="utf-8")):
        sid = conv_rec["sample_id"].replace("-", "")
        conv = conv_rec["conversation"]
        hid = f"h_{sid}"
        sessions, dia2turn, dia2sess, last = [], {}, {}, None
        for n in _sessions(conv):
            d = datetime.strptime(conv[f"session_{n}_date_time"], LOCOMO_FMT)
            last = d if last is None or d > last else last
            turns = []
            for t in conv[f"session_{n}"]:
                role = "assistant" if roles == "ab" and t["speaker"] == conv["speaker_b"] else "user"
                text = f"{t['speaker']}: {t['text']}"
                if t.get("blip_caption"):
                    text += f" [shares a photo: {t['blip_caption']}]"
                tid = f"t_{sid}_{t['dia_id'].replace(':', '_')}"
                dia2turn[t["dia_id"]], dia2sess[t["dia_id"]] = tid, f"s_{sid}_{n}"
                turns.append({"turn_id": tid, "role": role, "content": text})
            sessions.append({"session_id": f"s_{sid}_{n}", "date": d.strftime(DATE_FMT), "turns": turns})
        (out / f"{hid}.json").write_text(json.dumps({"history_id": hid, "sessions": sessions}, ensure_ascii=False),
                                         encoding="utf-8")
        qdate = (last + timedelta(days=1)).replace(hour=12, minute=0)
        for i, q in enumerate(conv_rec["qa"]):
            ev = [e for e in re.findall(r"D\d+:\d+", " ".join(map(str, q.get("evidence") or []))) if e in dia2turn]
            records.append({
                "question_id": f"q_{sid}_{i}", "history_id": hid, "question": q["question"],
                "question_date": qdate.strftime(DATE_FMT), "category": q["category"],
                "answer": None if q.get("answer") is None else str(q["answer"]),
                "gold_turns": sorted({dia2turn[e] for e in ev}), "gold_sessions": sorted({dia2sess[e] for e in ev}),
            })
    return split, records


def sample(records: list[dict], per_cat: int, seed: int) -> list[dict]:
    by = defaultdict(list)
    for r in records:
        if r["category"] == 5 or r["gold_turns"]:   # answerable questions need resolvable evidence
            by[r["category"]].append(r)
    rng = random.Random(seed)
    out = []
    for c in sorted(by):
        rows = sorted(by[c], key=lambda r: r["question_id"])
        out += rows if per_cat <= 0 or len(rows) <= per_cat else rng.sample(rows, per_cat)
    return out


def _metrics(pack, r: dict, hx, ms: float, chars: int) -> dict:
    from score import answer_matched, evidence_f1, normalize
    m = {"abstain_p": float(pack.abstain_p), "chars": chars, "ms": round(ms, 1), "route": pack.route,
         "n_passages": len(pack.passages)}
    if r["category"] == 5:
        return m
    G, A = set(r["gold_sessions"]), set(r["gold_turns"])
    P = set(pack.session_ids())
    m["SR"] = len(P & G) / len(G)
    m["ALL"] = float(G <= P)
    m["ATR"] = len(A & set(pack.included_turns or ())) / len(A)
    pack_text = "\n".join(p.text for p in pack.passages)
    gold_text = " ".join(t["content"] for s in hx.sessions for t in s["turns"] if t["turn_id"] in A)
    g = {"answer": r["answer"] or ""}
    m["extractive"] = bool(r["answer"]) and answer_matched(gold_text, g)
    m["AC"] = float(answer_matched(pack_text, g)) if r["answer"] else None
    m["answer_norm"] = normalize(r["answer"] or "")
    # the dev score S with a per-category stand-in for PA (no code-computed answers here, so no HA):
    # single-hop / open-domain like ssu (gold turns in, answer in if extractive), multi-hop / temporal like multi
    m["CF1"] = evidence_f1(pack.planned_citations(), list(G))
    ac_ok = m["AC"] == 1.0 if m["extractive"] else True
    pa = (m["ATR"] == 1.0 and ac_ok) if r["category"] in (3, 4) else (m["ALL"] == 1.0 and m["ATR"] == 1.0)
    m["PA"] = float(pa)
    m["S"] = 100 * (0.65 * m["PA"] + 0.30 * m["CF1"] - 0.05 * chars / 16000)
    return m


def work(job: tuple) -> list[dict]:
    split, systems, recs = job
    from core.index import HistoryIndex
    from core.pack import message_chars
    from harness.sweep import load_lens
    lenses = {name: (load_lens(path), params) for name, (path, params) in systems.items()}
    rows = []
    for r in recs:
        hx = HistoryIndex.load(split, r["history_id"])
        q = Question(r["question_id"], r["history_id"], r["question"], datetime.strptime(r["question_date"], DATE_FMT),
                     r["question_date"])
        for name, (lens, params) in lenses.items():
            row = {"split": split, "system": name, **{k: r[k] for k in ("question_id", "category", "question", "answer")}}
            try:
                t0 = time.perf_counter()
                pack = lens.build(q, hx, _variant=name, **params)
                ms = (time.perf_counter() - t0) * 1000
                row.update(_metrics(pack, r, hx, ms, message_chars(q, pack.passages, pack.hint)))
                row["included_sessions"] = pack.session_ids()
                row["gold_sessions"] = r["gold_sessions"]
            except Exception as exc:
                row["error"] = repr(exc)[:300]
            rows.append(row)
    return rows


def auc(pos: list[float], neg: list[float]) -> float | None:
    if not pos or not neg:
        return None
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def summarize(rows: list[dict]) -> list[dict]:
    out = []
    keys = sorted({(r["split"], r["system"]) for r in rows})
    for split, system in keys:
        rs = [r for r in rows if r["split"] == split and r["system"] == system and "error" not in r]
        for cat in [1, 2, 3, 4, "1-4"]:
            sub = [r for r in rs if (r["category"] in (1, 2, 3, 4) if cat == "1-4" else r["category"] == cat)]
            if not sub:
                continue
            mean = lambda k, xs=sub: round(sum(x[k] for x in xs) / len(xs), 3) if xs else None  # noqa: E731
            ext = [r for r in sub if r.get("extractive")]
            out.append({"split": split, "system": system, "cat": cat, "n": len(sub), "S": mean("S"), "PA": mean("PA"),
                        "CF1": mean("CF1"), "SR": mean("SR"),
                        "ALL": mean("ALL"), "ATR": mean("ATR"), "AC_ext": mean("AC", ext), "n_ext": len(ext),
                        "chars": round(sum(r["chars"] for r in sub) / len(sub)),
                        "ms": round(sum(r["ms"] for r in sub) / len(sub))})
        neg = [r["abstain_p"] for r in rs if r["category"] in (1, 2, 3, 4)]
        pos = [r["abstain_p"] for r in rs if r["category"] == 5]
        out.append({"split": split, "system": system, "cat": 5, "n": len(pos),
                    "abstain_auc": None if auc(pos, neg) is None else round(auc(pos, neg), 3),
                    "abstain_p_cat5": round(sum(pos) / len(pos), 3) if pos else None,
                    "abstain_p_cat1_4": round(sum(neg) / len(neg), 3) if neg else None,
                    "errors": sum(1 for r in rows if r["split"] == split and r["system"] == system and "error" in r)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT.parent / "data" / "locomo" / "locomo10.json"))
    ap.add_argument("--roles", default="ab", help="comma list of: ab (speaker_b = assistant), user (all user turns)")
    ap.add_argument("--per-cat", type=int, default=60, help="stratified sample per category; 0 = all questions")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--config", default="configs/best.json")
    ap.add_argument("--systems", default="routed,naive",
                    help="comma list of: routed (full system), naive (keyword baseline), hybrid (generic hybrid + rerank, "
                         "no router, 12k-char budget), hybrid_3k (the same at 3.3k chars)")
    ap.add_argument("--out", default=str(OUT / "locomo_results.jsonl"))
    a = ap.parse_args(argv)
    known = {"routed": ("lenses/pipeline.py", {"config": a.config}),
             "naive": ("lenses/generic.py", {"mode": "naive"}),
             "hybrid": ("lenses/generic.py", {"mode": "hybrid", "pool": 300, "rerank_top": 100, "budget": 12000,
                                              "window": 1}),
             # same lens at about the routed system's mean pack size on LoCoMo (~3.3k chars): equal-budget comparison
             "hybrid_3k": ("lenses/generic.py", {"mode": "hybrid", "pool": 300, "rerank_top": 100, "budget": 3300,
                                                 "window": 1})}
    systems = {name: known[name] for name in a.systems.split(",")}
    all_rows, t0 = [], time.time()
    for roles in a.roles.split(","):
        split, records = convert(Path(a.src), roles.strip())
        recs = sample(records, a.per_cat, a.seed)
        counts = defaultdict(int)
        for r in recs:
            counts[r["category"]] += 1
        print(f"{split}: {len(records)} questions, sample {len(recs)} {dict(sorted(counts.items()))} (seed {a.seed})",
              flush=True)
        by_hist = defaultdict(list)
        for r in recs:
            by_hist[r["history_id"]].append(r)
        hists = sorted(by_hist.items(), key=lambda kv: -len(kv[1]))
        jobs = [(split, systems, [r for _, rs in hists[i::a.workers] for r in rs]) for i in range(a.workers)]
        with Pool(a.workers) as pool:
            for rows in pool.imap_unordered(work, jobs):
                all_rows += rows
        print(f"  done in {time.time() - t0:.0f}s", flush=True)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in sorted(all_rows, key=lambda r: (r["split"], r["question_id"], r["system"])):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = summarize(all_rows)
    out.with_name(out.stem + "_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    for s in summary:
        print(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
