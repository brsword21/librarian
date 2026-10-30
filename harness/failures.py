"""Worst questions of a sweep run, with what was missed and what was taken instead.

    python -m harness.failures runs/<tag>/<type>/<lens>/<variant>/<split> --n 20 [--full]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.data import gold, history, questions
from core.gold_turns import gold_turns


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--full", action="store_true", help="print whole gold turns and passages")
    a = ap.parse_args(argv)
    run = Path(a.run)
    split = run.name
    rows = [json.loads(l) for l in open(run / "per_question.jsonl", encoding="utf-8")]
    g, gt = gold(split), gold_turns()
    qmap = {q.question_id: q for q in questions(split)}
    errs = [r for r in rows if r.get("error")]
    bad = [r for r in rows if not r.get("error") and not r.get("abstain_gold") and r.get("PA", 1) < 1]
    bad.sort(key=lambda r: (r.get("PA", 0), r.get("SR", 0), r.get("ATR", 0)))
    print(f"{len(rows)} rows, {len(bad)} answerable with PA<1, {len(errs)} errors")
    cut = 4000 if a.full else 400
    for r in bad[: a.n]:
        q, gg = qmap[r["question_id"]], g[r["question_id"]]
        h = history(split, q.history_id)
        sess = {s["session_id"]: s for s in h["sessions"]}
        idx = {s["session_id"]: i for i, s in enumerate(h["sessions"])}
        print("=" * 110)
        print(f"{r['question_id']} [{r.get('type')}] {q.question}   (asked {q.date_str})")
        print(f"GOLD: {gg['answer'][:200]}")
        print(f"SR={r.get('SR'):.2f} ATR={r.get('ATR'):.2f} ALL={r.get('ALL')} AC={r.get('AC')} HA={r.get('HA')} "
              f"CF1={r.get('CF1'):.2f} chars={r.get('chars')} gold_rank={r.get('gold_rank')} computed={r.get('computed')!r}")
        if r.get("hint"):
            print(f"HINT: {r['hint'][:300]}")
        taken = {p['id'] for p in r.get("passages", [])}
        for sid in gg["evidence"]:
            mark = "IN " if sid in taken else "MISSING"
            s = sess.get(sid)
            print(f"  gold session {sid} #{idx.get(sid)} {s['date'] if s else '?'} {mark}")
            for t in (s["turns"] if s else []):
                if t["turn_id"] in set(gt.get(r["question_id"], [])):
                    print(f"     {t['role']}: {t['content'][:cut]!r}")
        print(f"  our passages ({len(r.get('passages', []))}): " +
              ", ".join(f"{p['id']}#{idx.get(p['id'])}" for p in r.get("passages", [])))
        for p in r.get("passages", [])[: (99 if a.full else 3)]:
            if p["id"] not in gg["evidence"]:
                print(f"     [{p['id']} {p['date']}] {p['text'][:cut]!r}")
    if errs:
        print("\nFIRST ERROR:\n", errs[0]["error"])


if __name__ == "__main__":
    main()
