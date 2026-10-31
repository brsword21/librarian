"""Router -> chosen lens per route -> evidence packs for every question of a split.

    python -m reactorq.build_packs --config configs/best.json --split test --out runs/final/test_packs.jsonl [--qids q1,q2]
configs/best.json: {"routes": {"ssu": {"lens": "...py", "variant": "..."}, ...}, "fallback": {"lens": ..., "variant": ...}}
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from core.data import questions
from core.index import HistoryIndex
from core.pack import message_chars, question_text
from core.paths import ROOT
from core.router import route
from harness.sweep import load_lens


def pack_hash(rec: dict) -> str:
    key = json.dumps([rec["question_text"], rec["question_date"], rec["passages"]], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/best.json")
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", required=True)
    ap.add_argument("--qids")
    ap.add_argument("--suffix", default=None, help="text appended to every question (default: config 'answer_suffix')")
    a = ap.parse_args(argv)
    cfg = json.loads((ROOT / a.config).read_text())
    suffix = a.suffix if a.suffix is not None else cfg.get("answer_suffix", "")
    lenses = {}
    pipeline = load_lens("lenses/pipeline.py")

    def get(spec):
        if spec["lens"] not in lenses:
            lenses[spec["lens"]] = load_lens(spec["lens"])
        lens = lenses[spec["lens"]]
        return lens, {**lens.VARIANTS[spec["variant"]], **spec.get("params", {})}, spec["variant"]

    want = set(a.qids.split(",")) if a.qids else None
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for q in questions(a.split):
            if want and q.question_id not in want:
                continue
            hx = HistoryIndex.load(a.split, q.history_id)
            conf = route(q.question)[1]
            try:  # the routed system exactly as swept: text router + evidence hand-offs + per-route lens
                pack = pipeline.build(q, hx, config=a.config)
            except Exception as exc:  # never lose a question: fall back
                print(f"{q.question_id}: pipeline failed ({exc!r}); fallback")
                lens, params, vname = get(cfg["fallback"])
                pack = lens.build(q, hx, _variant=vname, **params)
                pack.debug = {**(pack.debug or {}), "lens": cfg["fallback"]["lens"], "lens_variant": vname}
            r = pack.route
            spec = {"lens": (pack.debug or {}).get("lens", "?")}
            vname = (pack.debug or {}).get("lens_variant", "?")
            rec = {"question_id": q.question_id, "history_id": q.history_id, "route": r, "route_conf": conf,
                   "lens": spec["lens"], "variant": vname, "question": q.question,
                   "question_text": question_text(q, "\n".join(x for x in (pack.hint, suffix) if x)),
                   "question_date": q.date_str,
                   "passages": [{"id": p.id, "date": p.date, "text": p.text} for p in pack.passages],
                   "cite_plan": pack.planned_citations(), "abstain_p": pack.abstain_p, "computed": pack.computed,
                   "route_text": (pack.debug or {}).get("route_text"),
                   "chars": message_chars(q, pack.passages, "\n".join(x for x in (pack.hint, suffix) if x))}
            rec["pack_hash"] = pack_hash(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} packs -> {out}")


if __name__ == "__main__":
    main()
