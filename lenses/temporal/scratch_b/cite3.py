"""Question route cite-rule grid: CF1 of cite rules mixing the time-prior ranking and plain CE (dev + dev200)."""
import json, sys
sys.path.insert(0, '.')
from core.data import gold, questions
from core.index import HistoryIndex
from lenses.temporal import b_sem as B
sp = dict(B.VARIANTS['sem_turns9'])
data = []
for split in ['dev', 'dev200']:
    g = gold(split); qm = {q.question_id: q for q in questions(split)}
    for l in open(f'runs/r3-temporal-b/temporal/b_r3_merge/r3/{split}/per_question.jsonl'):
        r = json.loads(l)
        if r['abstain_gold'] or not str(r['debug'].get('r3_from')).startswith('b_r3:other3'):
            continue
        q = qm[r['question_id']]; hx = HistoryIndex.load(split, q.history_id)
        rows = B.rank_question(hx, q, sp)
        pack = {p['id'] for p in r['passages']}
        bs, bc = {}, {}
        for x in rows:
            if x['session_id'] not in pack: continue
            bs[x['session_id']] = max(bs.get(x['session_id'], -99), x['score'])
            bc[x['session_id']] = max(bc.get(x['session_id'], -99), x['ce'])
        S = sorted(bs, key=lambda s: -bs[s]); C = sorted(bc, key=lambda s: -bc[s])
        data.append((split, set(g[r['question_id']]['evidence']), S, C, bs, bc, B.expected_items(q.question)))
def f1(c, G):
    c = set(c)
    if not c: return 0
    tp = len(c & G); 
    if tp == 0: return 0
    p, rr = tp / len(c), tp / len(G); return 2 * p * rr / (p + rr)
def rule(S, C, bs, bc, n, a, b, gap):
    if n: return S[:n]
    top = bs[S[0]] if S else 0
    out = [s for s in S[:a] if bs[s] >= top - gap]
    topc = bc[C[0]] if C else 0
    for s in C[:b]:
        if s not in out and bc[s] >= topc - gap: out.append(s)
    return out
res = []
for a in [1, 2, 3, 4, 5]:
    for b in [0, 1, 2, 3]:
        for gap in [2, 3, 4, 6, 8]:
            m = {}
            for sp_ in ['dev', 'dev200']:
                v = [f1(rule(S, C, bs, bc, n, a, b, gap), G) for (s, G, S, C, bs, bc, n) in data if s == sp_]
                m[sp_] = sum(v) / len(v)
            res.append((m['dev'], m['dev200'], a, b, gap))
res.sort(reverse=True)
print('n', {s: sum(1 for d in data if d[0] == s) for s in ['dev', 'dev200']})
cur = [x for x in res if x[2] == 4 and x[3] == 0 and x[4] == 8][0]
print('current (4,0,8):', cur)
for x in res[:15]: print(x)
