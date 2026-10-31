"""span firing + own coverage over gap/ago questions. usage: chk.py split"""
import sys, re
from core.index import HistoryIndex
from core.data import questions, gold
from lenses.temporal import a_calendar as A, a_gap as G
from lenses.temporal import a_r3_gap as R
sp = sys.argv[1]
gd = gold(sp) if sp != "test" else {}
for q in questions(sp):
    if R._SPAN.search(q.question):
        hx = HistoryIndex.load(sp, q.history_id)
        p = R.build_span(q, hx, {})
        print("SPAN", q.question_id, q.question, "->", p.computed if p else None, p.debug.get("span") if p else "")
    g = gd.get(q.question_id, {})
    if sp != "test" and "temporal" not in str(g.get("type", g.get("question_type", ""))):
        continue
    qp = A.parse_question(q.question)
    if qp.kind not in ("gap", "ago") or not qp.events:
        continue
    hx = HistoryIndex.load(sp, q.history_id)
    rows, missing = R._own_check(q, hx, qp.events, 0.75)
    ab = g.get("abstain", "?")
    flag = "MISS" if missing else "    "
    print(flag, sp, q.question_id, "abst=%s" % ab, q.question[:80], "|", [(ev[:30], round(o, 2), round(a, 2)) for ev, o, a, _, _ in rows])
