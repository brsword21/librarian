import sys
sys.path.insert(0, '.')
from core.data import questions
from core.index import HistoryIndex
from lenses.temporal import b_r4_last as L
split = sys.argv[1]
for q in questions(split):
    pq = L.parse_last(q.question)
    if not pq: continue
    hx = HistoryIndex.load(split, q.history_id)
    cs = [c for c in L.candidates(q, hx, pq, {}) if c['own'] and c['ce'] > -6]
    print('=====', q.question[:80], '|', L._statement(pq))
    for c in sorted(cs, key=lambda c: c['key']):
        print(f"   {c['date']} ce={c['ce']:.2f} {c['sent'][:120]!r}")
