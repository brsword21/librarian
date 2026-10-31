"""R4 scratch: sentence features for first-person ssu-routed questions (role-play detector check)."""
import json, sys
from core.data import questions, gold
from core.index import HistoryIndex
from core.router import route
from harness.sweep import load_lens
r4 = load_lens('lenses/ssa/a_r4_role.py'); br = load_lens('lenses/ssa/b_role.py')
split = sys.argv[1]
G = gold(split) if split != 'test' else {}
out = open(f'lenses/ssa/scratch_a/r4/fp_feats_{split}.jsonl', 'w')
for q in questions(split):
    if route(q.question)[0] != 'ssu':
        continue
    hx = HistoryIndex.load(split, q.history_id)
    f = br.role_features(q, hx)
    if f['n_first'] == 0:
        continue
    s = r4.sent_features(q, hx)
    g = G.get(q.question_id, {}).get('question_type')
    row = dict(qid=q.question_id, q=q.question, gold=g, d=f['d'], nf=f['n_first'], **s)
    out.write(json.dumps(row) + '\n')
    if s['u_first'] == 0 or s['d_sent'] >= 3:
        print(split, (g or '-')[:16], 'd=%.2f ds=%.2f uf=%d' % (f['d'], s['d_sent'], s['u_first']), q.question[:80], '|U:', s['u_sent'][:80])
