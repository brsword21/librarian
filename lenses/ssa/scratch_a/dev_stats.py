"""Dev/dev200 SSA stats: gold turn role/length/chunks, where the answer sits, cue words."""
import json, re, sys
from collections import Counter
sys.path.insert(0, '.')
from core.data import gold, questions, history
from core.gold_turns import gold_turns
from core.units import chunk

split = sys.argv[1] if len(sys.argv) > 1 else 'dev'
G = gold(split); Q = {q.question_id: q for q in questions(split)}
GT = gold_turns()
def norm(s): return re.sub(r'[^a-z0-9 ]', ' ', s.lower()).split()
roles = Counter(); nturn = Counter(); nchunks = []; pos = Counter(); ac = Counter(); ansc = Counter(); tlen = []
n = 0
for qid, g in G.items():
    if g['question_type'] != 'single-session-assistant': continue
    n += 1
    q = Q[qid]; h = history(split, q.history_id)
    tids = GT.get(qid, [])
    nturn[len(tids)] += 1
    turns = {t['turn_id']: (s, i, t) for s in h['sessions'] for i, t in enumerate(s['turns'])}
    ans = g['answer']
    for tid in tids:
        if tid not in turns: roles['MISSING'] += 1; continue
        s, i, t = turns[tid]
        roles[t['role']] += 1
        cs = chunk(t['content'])
        nchunks.append(len(cs)); tlen.append(len(t['content']))
        pos[f"turn{i}/{len(s['turns'])}"[:6]] += 1
        # answer verbatim?
        a = ans.strip().rstrip('.').lower()
        found = a in t['content'].lower()
        ac['verbatim' if found else 'not'] += 1
        # which chunk holds most answer tokens
        at = set(w for w in norm(ans) if len(w) > 3)
        best = max(range(len(cs)), key=lambda k: len(at & set(norm(cs[k])))) if cs else -1
        ansc[f"{best}/{len(cs)}"] += 1
print(split, 'n', n, 'roles', dict(roles), 'n gold turns', dict(nturn))
import statistics as st
print('turn len median', st.median(tlen), 'max', max(tlen), 'chunks median', st.median(nchunks), 'max', max(nchunks))
print('chunks dist', sorted(Counter(nchunks).items()))
print('answer verbatim in gold turn', dict(ac))
print('best answer chunk / nchunks', sorted(ansc.items(), key=lambda x: -x[1])[:20])
print('gold turn position', sorted(pos.items(), key=lambda x: -x[1])[:12])
