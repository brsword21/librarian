"""Role features for questions the router sends to ssu: is the answer in an ASSISTANT turn (gold ssa) or not?
Usage: .venv/bin/python -m lenses.ssa.scratch_a.role_eval <split> [--ce]
Prints per-feature AUC (gold ssa vs every other gold type) among questions routed to ssu."""
import math
import sys

from core.data import gold, questions
from core.index import HistoryIndex
from core.router import route
from lenses.ssa import a_recsent as L


def auc(pos, neg):
    if not pos or not neg:
        return float("nan")
    s = 0.0
    for p in pos:
        for n in neg:
            s += 1.0 if p > n else (0.5 if p == n else 0.0)
    return s / (len(pos) * len(neg))


split = sys.argv[1]
use_ce = "--ce" in sys.argv
g = gold(split)
rows = []
for q in questions(split):
    if route(q.question)[0] != "ssu":
        continue
    t = g[q.question_id]["question_type"]
    hx = HistoryIndex.load(split, q.history_id)
    f = L.role_features(q, hx, use_ce=use_ce)
    rows.append((t == "single-session-assistant", t, f, q.question))
keys = list(rows[0][2])
print(f"{split}: routed-to-ssu n={len(rows)}  ssa={sum(r[0] for r in rows)}")
for k in keys:
    pos = [r[2][k] for r in rows if r[0]]
    neg = [r[2][k] for r in rows if not r[0]]
    neg_ssu = [r[2][k] for r in rows if r[1] == "single-session-user"]
    print(f"  {k:14s} AUC(all others)={auc(pos, neg):.3f}  AUC(vs ssu)={auc(pos, neg_ssu):.3f}")
if "-v" in sys.argv:
    for r in sorted(rows, key=lambda r: -r[2]["p_assistant"]):
        print(f"{r[2]['p_assistant']:.2f} {r[1][:12]:12s} {r[3][:100]}")
