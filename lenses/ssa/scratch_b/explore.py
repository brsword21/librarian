"""Exploration of SSA dev/dev200: where gold turns sit, how long, where the answer sits in the turn."""
import json, re, sys
from collections import Counter
from core.data import questions, gold, history
GT = json.load(open('cache/gold_turns.json'))

def norm(s): return re.sub(r'\W+', ' ', s.lower()).strip()

for sp in ['dev', 'dev200']:
    g = gold(sp)
    qs = [q for q in questions(sp) if g[q.question_id]['question_type'] == 'single-session-assistant']
    roles = Counter(); lens = []; pos = []; found = Counter(); ntur = []; idx = []; uncued = 0; asst_long = []
    for q in qs:
        h = history(sp, q.history_id)
        turns = {t['turn_id']: (s, i, t) for s in h['sessions'] for i, t in enumerate(s['turns'])}
        gts = GT.get(q.question_id, [])
        ans = g[q.question_id]['answer']
        for tid in gts:
            if tid not in turns: found['missing_tid'] += 1; continue
            s, i, t = turns[tid]
            roles[t['role']] += 1; lens.append(len(t['content'])); idx.append(i); ntur.append(len(s['turns']))
            a = norm(ans); c = norm(t['content'])
            if a and a in c:
                found['answer_in_turn'] += 1
                p = c.index(a) / max(1, len(c)); pos.append(c.index(a))
            else:
                found['answer_not_extractive'] += 1
        if not gts: found['no_gold_turns'] += 1
        # assistant turn lengths in history
        asst_long += [len(t['content']) for s in h['sessions'] for t in s['turns'] if t['role'] == 'assistant']
    lens.sort(); pos.sort(); asst_long.sort()
    print(sp, 'n', len(qs), 'roles', dict(roles), dict(found))
    pct = lambda L, p: L[int(p * (len(L) - 1))] if L else None
    print('  gold turn len p25/50/75/90', [pct(lens, p) for p in (.25, .5, .75, .9)])
    print('  answer char offset in turn p25/50/75/90', [pct(pos, p) for p in (.25, .5, .75, .9)], ' >700:', sum(p > 700 for p in pos), '/', len(pos))
    print('  gold turn idx in session', Counter(idx).most_common(8))
    print('  asst turn len in histories p50/75/90', [pct(asst_long, p) for p in (.5, .75, .9)])
