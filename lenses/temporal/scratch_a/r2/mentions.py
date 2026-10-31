"""Top mentions per event for questions matching a substring. usage: mentions.py split substr [n]"""
import sys
from core.index import HistoryIndex
from core.data import questions
from lenses.temporal import a_calendar as A
split, sub = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
for q in questions(split):
    if sub.lower() not in q.question.lower():
        continue
    hx = HistoryIndex.load(split, q.history_id)
    qp, picks, alts, computed, conf = A.analyse(q, hx, 40, 0.55, 0.08, False)
    print("=" * 100); print(q.date_str[:10], q.question, "->", computed, conf)
    for ev, ms in A.analyse.last_mentions.items():
        print("  EV", ev)
        for m in ms[:n]:
            print(f"    {m.score:.2f} cov={m.cov:.2f} {m.value} {m.kind:7s} {m.role[0]} {m.session_id[-6:]} {m.sess_date:%m-%d} {m.why} | {A._snip(m.sentence, 140)}")
