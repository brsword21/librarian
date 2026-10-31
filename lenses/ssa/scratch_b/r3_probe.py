"""Round 3: probe role features (B CE margin + A structural/lexical) on every question the text router does NOT send
to ssa (ssu, multi, ku, temporal). Writes scratch_b/r3_probe_<split>.jsonl.
Usage: .venv/bin/python -m lenses.ssa.scratch_b.r3_probe dev|dev200|test
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from core.data import gold, questions
from core.index import HistoryIndex
from core.router import route
from lenses.ssa import a_recsent as A
from lenses.ssa import b_role as B

OUT = Path(__file__).parent


def main(split="dev"):
    g = gold(split) if split != "test" else {}
    rows = []
    for q in questions(split):
        r = route(q.question)[0]
        if r == "ssa":
            continue
        hx = HistoryIndex.load(split, q.history_id)
        fb = B.role_features(q, hx)
        fa = A.role_features(q, hx)
        gg = g.get(q.question_id, {})
        row = {"qid": q.question_id, "route": r, "type": gg.get("question_type", "?"), "abstain": gg.get("abstain"),
               "q": q.question, "d": fb["d"], "nfB": fb["n_first"], "ce_a": fb["ce_a"], "ce_u": fb["ce_u"],
               "pB": B.p_from_features(fb["d"], fb["n_first"], c=-1.2),
               **{"A_" + k: v for k, v in fa.items()}}
        rows.append(row)
        print(r, row["type"][:14], f"pB={row['pB']:.2f} pA={fa['p_assistant']:.2f} d={fb['d']:+.1f}", q.question[:70],
              flush=True)
    with open(OUT / f"r3_probe_{split}.jsonl", "w") as fh:
        for x in rows:
            fh.write(json.dumps(x) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
