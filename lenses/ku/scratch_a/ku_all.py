"""Dump every dev KU question with full gold-turn text and positions."""
import json, sys, re
sys.path.insert(0, '.')
from core.data import questions, gold, history
from core.gold_turns import gold_turns

gt = json.load(open('cache/gold_turns.json'))
qs = {q.question_id: q for q in questions('dev')}
g = gold('dev')
ku = [qid for qid, x in g.items() if x['question_type'] == 'knowledge-update']
print(len(ku), 'ku dev; abstain', sum(g[q]['abstain'] for q in ku))
for qid in ku:
    q = qs[qid]; x = g[qid]
    h = history('dev', q.history_id)
    sidx = {s['session_id']: i for i, s in enumerate(h['sessions'])}
    tmap = {t['turn_id']: (s['session_id'], s['date'], ti, t) for s in h['sessions'] for ti, t in enumerate(s['turns'])}
    print('=====', qid, q.date_str, 'n=', len(h['sessions']), 'abst' if x['abstain'] else '')
    print('Q:', q.question)
    print('A:', x['answer'], '| aliases', x.get('aliases'))
    print('EV:', [(e, sidx.get(e)) for e in x['evidence']])
    for tid in gt.get(qid, []):
        sid, d, ti, t = tmap[tid]
        print(f'  GT [{sidx[sid]}] {d} turn{ti} {t["role"]}: {t["content"][:700]!r}')
