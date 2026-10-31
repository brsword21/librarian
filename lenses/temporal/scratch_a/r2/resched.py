"""Scheduled-event check: picks whose date is after their session date; list later mentions of the same event."""
import re, sys
from core.index import HistoryIndex
from core.data import questions
from lenses.temporal import a_gap as G
split = sys.argv[1]
P = G.VARIANTS["ct_evgba"]
for q in questions(split):
    if not G._GAP.search(q.question): continue
    hx = HistoryIndex.load(split, q.history_id)
    qp, picks, alts, allm, computed, conf, gate = G.analyse2(q, hx, P)
    for ev, m, g in picks:
        if m is None or m.value <= m.sess_date.date(): continue
        later = [x for x in allm[ev] if x.sess_date > m.sess_date and x.cov >= 0.5 and x.sentence != m.sentence]
        print("=" * 90); print(q.question[:110], "| pick", m.value, "said", m.sess_date.date(), "conf", conf)
        for x in later[:4]:
            print(f"    later {x.score:.2f} cov={x.cov:.2f} {x.value} {x.kind} {x.role[0]} {x.sess_date:%Y-%m-%d} {x.why} | {x.sentence[:130]}")
