"""Precision of 'cross-encoder top turn == lens best turn' (and of turn_margin) as a best-turn-is-gold signal.
Usage: .venv/bin/python -m lenses.ssa.scratch_a.agree_eval <split>"""
import sys
from core.data import gold, questions
from core.gold_turns import gold_turns
from core.index import HistoryIndex
from lenses.ssa import a_recsent as L
split = sys.argv[1]
g = gold(split); gt = gold_turns()
P = L.VARIANTS["r2_solo_b6"]
rows = []
for q in questions(split):
    if g[q.question_id]["question_type"] != "single-session-assistant":
        continue
    hx = HistoryIndex.load(split, q.history_id)
    pk = L.build(q, hx, _variant="x", **P)
    b = pk.debug["ranking"][0]; bu = hx.units[b]
    suids = [i for t in hx.sess_by_id[bu.session_id]["turns"] for i in hx.turn_units(t["turn_id"])]
    ce = hx.rerank(q.question, suids)
    agree = hx.units[ce[0][0]].turn_id == bu.turn_id
    ok = bu.turn_id in set(gt.get(q.question_id, []))
    rows.append((agree, pk.debug["best"]["turn_margin"], ok))
n = len(rows)
for name, f in (("agree", lambda r: r[0]), ("margin>=1.3", lambda r: r[1] >= 1.3), ("agree|m1.3", lambda r: r[0] or r[1] >= 1.3),
                ("agree&m1.1", lambda r: r[0] and r[1] >= 1.1), ("agree&m1.05", lambda r: r[0] and r[1] >= 1.05)):
    sub = [r for r in rows if f(r)]
    print(f"{split} {name:12s} cover {len(sub)}/{n}  best==gold {sum(r[2] for r in sub)}/{len(sub)}")
