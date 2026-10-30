import json, re, sys
from collections import Counter
sys.path.insert(0, '.'); sys.path.insert(0, 'lenses/ssa/scratch_b')
from minibm25 import chunk, ssa_questions
from core.data import history
GT = json.load(open('cache/gold_turns.json'))
def norm(s): return re.sub(r'\W+', ' ', s.lower()).strip()
for sp in ['dev', 'dev200']:
    ngt = Counter(); chunk_of_ans = Counter(); nchunks = Counter(); sess_len = []; gt_roles = Counter(); turnspan = Counter()
    for q, g in ssa_questions(sp):
        h = history(sp, q.history_id)
        tmap = {t['turn_id']: (s, i, t) for s in h['sessions'] for i, t in enumerate(s['turns'])}
        gts = [t for t in GT.get(q.question_id, []) if t in tmap]
        ngt[len(gts)] += 1
        gt_roles[tuple(sorted(tmap[t][2]['role'] for t in gts))] += 1
        if len(gts) > 1:
            idxs = sorted(tmap[t][1] for t in gts); turnspan[idxs[-1] - idxs[0]] += 1
        s0 = tmap[gts[0]][0] if gts else None
        if s0: sess_len.append(sum(len(t['content']) for t in s0['turns']))
        a = norm(g['answer'])
        for t in gts:
            ch = chunk(tmap[t][2]['content']); nchunks[len(ch)] += 1
            for ci, c in enumerate(ch):
                if a and a in norm(c): chunk_of_ans[ci] += 1; break
    sess_len.sort()
    print(sp, 'gold turns/q', dict(ngt), 'roles', dict(gt_roles))
    print('   span between gold turns', dict(turnspan), ' chunks per gold turn', sorted(nchunks.items()))
    print('   chunk idx holding answer', sorted(chunk_of_ans.items()), ' gold session chars p50/p90', sess_len[len(sess_len)//2], sess_len[int(.9*len(sess_len))])
