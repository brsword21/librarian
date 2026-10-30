"""Offline cite_plan rule analysis from a sweep's per_question.jsonl (debug['sess'] = [sid, sscore, lex, flags] in pack order)."""
import json, sys
from core.data import gold
run = sys.argv[1]
split = run.rstrip('/').split('/')[-1]
g = gold(split)
rows = [json.loads(l) for l in open(run + '/per_question.jsonl')]
rows = [r for r in rows if not r.get('abstain_gold') and 'debug' in r and 'sess' in r['debug']]

def f1(c, G):
    c = list(dict.fromkeys(c)); G = set(G)
    if not c: return 0.0
    tp = len(set(c) & G); 
    if not tp: return 0.0
    p, r = tp / len(c), tp / len(G)
    return 2 * p * r / (p + r)

rules = {}
def rule(name):
    def d(fn): rules[name] = fn; return fn
    return d
rule('current')(lambda r, S: r['cite_plan'])
for k in (1, 2, 3, 4, 5, 6):
    rule(f'packorder_top{k}')(lambda r, S, k=k: [x[0] for x in S[:k]])
    rule(f'sscore_top{k}')(lambda r, S, k=k: [x[0] for x in sorted(S, key=lambda x: -x[1])[:k]])
    rule(f'lex_top{k}')(lambda r, S, k=k: [x[0] for x in sorted(S, key=lambda x: (-x[2], -x[1]))[:k]])
for fr in (0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 1.0):
    for cap in (3, 4, 5, 6):
        def fn(r, S, fr=fr, cap=cap):
            best = max((x[2] for x in S), default=0)
            c = [x for x in sorted(S, key=lambda x: (-x[2], -x[1])) if x[2] >= fr * best and not ({'other', 'neg'} & set(x[3]))]
            return [x[0] for x in c[:cap]] or [x[0] for x in S[:2]]
        rules[f'lexfrac{fr}_cap{cap}'] = fn
    for cap in (3, 4, 5, 6):
        def fn2(r, S, fr=fr, cap=cap):
            best = max((x[1] for x in S), default=0)
            c = [x for x in sorted(S, key=lambda x: -x[1]) if x[1] >= fr * best]
            return [x[0] for x in c[:cap]]
        rules[f'ssfrac{fr}_cap{cap}'] = fn2
res = []
for name, fn in rules.items():
    v = [f1(fn(r, r['debug']['sess']), g[r['question_id']]['evidence']) for r in rows]
    res.append((sum(v) / len(v), name))
res.sort(reverse=True)
for m, n in res[:15]: print(f'{m:.3f} {n}')
print('current', [f'{m:.3f}' for m, n in res if n == 'current'])
import statistics
print('mean |G|', statistics.mean(len(g[r['question_id']]['evidence']) for r in rows), 'mean |cite|', statistics.mean(len(r['cite_plan']) for r in rows))
# oracle: best possible CF1 if we cite exactly gold∩pack
print('oracle', sum(f1([x[0] for x in r['debug']['sess'] if x[0] in g[r['question_id']]['evidence']], g[r['question_id']]['evidence']) for r in rows) / len(rows))
