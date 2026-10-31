"""Inspect a_gap analyse2 picks + top mentions. usage: insp.py split substr [n]"""
import sys
from core.index import HistoryIndex
from core.data import questions
from lenses.temporal import a_calendar as A
from lenses.temporal import a_gap as G
split, sub = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
P = G.VARIANTS["ct_evgba"]
for q in questions(split):
    if sub.lower() not in q.question.lower():
        continue
    hx = HistoryIndex.load(split, q.history_id)
    qp, picks, alts, allm, computed, conf, gate = G.analyse2(q, hx, P)
    print("=" * 100); print(q.question_id, q.date_str[:10], q.question, "->", computed, conf, gate, qp.kind, qp.unit, qp.events)
    for ev, ms in allm.items():
        print("  EV", ev)
        for m in ms[:n]:
            print(f"    {m.score:.2f} {m.value} {m.kind:7s} {m.role[0]} {m.session_id[-6:]} {m.sess_date:%y-%m-%d} {m.why} | {A._snip(m.sentence, 160)}")
