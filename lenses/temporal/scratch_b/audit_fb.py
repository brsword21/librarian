"""Test audit of the gap fallback: questions where lens A has no computed value -> B's picks (qualitative only)."""
import re, sys
sys.path.insert(0, '.')
from core.data import questions
from core.index import HistoryIndex
from core.router import route
from lenses.temporal import b_merge as M
for q in questions('test'):
    if route(q.question)[0] != 'temporal' or not M._GAP.search(q.question): continue
    hx = HistoryIndex.load('test', q.history_id)
    a = M._A.build(q, hx, _variant='ftb_bm25', **M._A.VARIANTS['ftb_bm25'])
    if a.computed is not None: continue
    b = M._B.build(q, hx, _variant="sem_turns9", **M._B.VARIANTS["sem_turns9"]); print("   guard ok:", M._fallback_sane(b, b.debug.get("picks") or []))
    print('==', q.question, '| qdate', q.date_str)
    print('   A raw', (a.debug or {}).get('computed_raw'), 'A picks', [(x[0][:30], x[1]) for x in (a.debug or {}).get('picks') or []])
    print('   B computed', b.computed, 'conf', b.debug.get('conf'))
    for x in b.debug.get('picks') or []:
        print('     pick', x['event'][:40], x['date'], x.get('how'), x.get('subj'), '|', x.get('sent', '')[:200])
