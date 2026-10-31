"""Question route: per session, deficit from the top (time-prior score and plain CE) for gold vs non-gold sessions."""
import json, sys
sys.path.insert(0, '.')
from core.data import gold, questions
from core.index import HistoryIndex
from lenses.temporal import b_sem as B
split = sys.argv[1]
run = sys.argv[2]
g = gold(split); qm = {q.question_id: q for q in questions(split)}
rows_run = [json.loads(l) for l in open(run + '/per_question.jsonl')]
sp = dict(B.VARIANTS['sem_turns9'])
G, N = [], []
per_q = []
for r in rows_run:
    if r['abstain_gold'] or not str(r['debug'].get('r3_from')).startswith('b_r3:other3'):
        continue
    q = qm[r['question_id']]; hx = HistoryIndex.load(split, q.history_id)
    rows = B.rank_question(hx, q, sp)
    bs, bc = {}, {}
    for x in rows:
        bs[x['session_id']] = max(bs.get(x['session_id'], -99), x['score'])
        bc[x['session_id']] = max(bc.get(x['session_id'], -99), x['ce'])
    ts, tc = max(bs.values()), max(bc.values())
    pack = [p['id'] for p in r['passages']]
    gs = set(g[r['question_id']]['evidence'])
    for sid in pack:
        d = (round(ts - bs.get(sid, -99), 1), round(tc - bc.get(sid, -99), 1))
        (G if sid in gs else N).append(d)
    per_q.append((r['question_id'], [(round(ts - bs.get(s, -99), 1), round(tc - bc.get(s, -99), 1)) for s in gs if s in pack]))
import itertools
for fs, fc in itertools.product([3, 4, 5, 6, 8], [3, 4, 5, 6, 8]):
    keepG = sum(1 for a, b in G if a <= fs or b <= fc); keepN = sum(1 for a, b in N if a <= fs or b <= fc)
    print(f"floor score {fs} ce {fc}: gold kept {keepG}/{len(G)}  non-gold kept {keepN}/{len(N)}")
for x in per_q: print(x)
