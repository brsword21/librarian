"""Probe a test history with dense + bm25 queries; print top user/assistant units."""
import sys, json
from core.index import HistoryIndex
from core.data import questions
Q = {q.question_id: q for q in questions('test')}
qid = sys.argv[1]
q = Q[qid]
hx = HistoryIndex.load('test', q.history_id)
print(q.question, q.date_str)
for query in sys.argv[2:]:
    print('######', query)
    seen = set()
    d = hx.dense(query, k=12)
    b = hx.bm25(query, k=12)
    for tag, lst in (('D', d), ('B', b)):
        for uid, s in lst:
            if uid in seen: continue
            seen.add(uid)
            u = hx.units[uid]
            print(f'  {tag} {s:.2f} {u.date_str[:10]} {u.session_id} {u.role[0]} | {u.text[:220]!r}')
