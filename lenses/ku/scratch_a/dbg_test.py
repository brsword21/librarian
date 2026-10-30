"""Debug a TEST question (no gold): mentions, pair, hint. Usage: dbg_test.py variant 'substring of question'"""
import sys
sys.path.insert(0, '.')
from core.data import questions
from core.index import HistoryIndex
from harness.sweep import load_lens
var, sub = sys.argv[1], sys.argv[2]
lens = load_lens('lenses/ku/a_timeline.py')
for q in questions('test'):
    if sub.lower() not in q.question.lower():
        continue
    hx = HistoryIndex.load('test', q.history_id)
    p = {**lens.VARIANTS[var]}
    spec, ranking, mentions, tl, dbg = lens.analyse(q, hx, p)
    print('=' * 100); print(q.question, '| key', spec.key, spec.atype, spec.direction, 'head', spec.head, 'x', spec.query_x)
    for m in sorted(mentions, key=lambda m: m.sort_key):
        if m.score < 0.5: continue
        print(f"  {m.date_str[:10]} {m.session_id} u{m.uid} {m.role[:4]} {m.owner:5s} sc={m.score:.2f} cov={m.cov:.2f} v={m.vals[:3]} | {m.sent[:120]}")
    print('newest', tl.newest and tl.newest.sent[:100]); print('older', tl.older and tl.older.sent[:100])
