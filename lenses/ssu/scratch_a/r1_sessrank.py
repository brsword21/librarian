"""Session-level rank of the gold session in a sweep's ranking; prints misses with top-session text.
usage: python lenses/ssu/scratch_a/r1_sessrank.py runs/<...>/<split>"""
import json, sys, collections
sys.path.insert(0, '.')
from core.index import HistoryIndex
from core.data import questions, gold

d = sys.argv[1]
split = d.rstrip('/').split('/')[-1]
qs = {q.question_id: q for q in questions(split)}
G = gold(split)
rows = [json.loads(l) for l in open(d + '/per_question.jsonl')]
cnt = collections.Counter()
cite_ok = 0
n = 0
for r in rows:
    g = G[r['question_id']]
    if g['abstain']:
        continue
    n += 1
    q = qs[r['question_id']]
    hx = HistoryIndex.load(split, q.history_id)
    rank = r.get('ranking_top')
    if rank is None:
        continue
    sess, seen = [], set()
    for u in rank:
        s = hx.units[u].session_id
        if s not in seen:
            seen.add(s); sess.append(s)
    ev = set(g['evidence'])
    sr = next((i for i, s in enumerate(sess) if s in ev), None)
    cnt[sr] += 1
    if r.get('cite_plan') and set(r['cite_plan']) & ev:
        cite_ok += 1
    if sr != 0 and len(sys.argv) > 2:
        print('---', r['question_id'], sr, q.question, '| gold:', g['answer'])
        top = rank[0]
        print('   TOP', hx.units[top].role, hx.units[top].text[:200].replace('\n', ' '))
print('n', n, 'gold session rank', sorted(cnt.items(), key=lambda x: (x[0] is None, x[0] or 0)), 'cite hit', cite_ok)
