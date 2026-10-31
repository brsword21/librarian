"""R4 debug of TEST ku packs: pair, gate, best sentence per session. Usage: r4_dbg.py lensfile variant 'substr'..."""
import sys, json
sys.path.insert(0, '.')
from core.data import questions
from core.index import HistoryIndex
from harness.sweep import load_lens
from lenses.ku import b_semantic as B
from lenses.ku import b_r2 as R2
lensf, var, subs = sys.argv[1], sys.argv[2], sys.argv[3:]
lens = load_lens(lensf)
split = 'test'
for q in questions(split):
    if not any(s.lower() in q.question.lower() for s in subs):
        continue
    hx = HistoryIndex.load(split, q.history_id)
    p = {**lens.VARIANTS[var], '_variant': var}
    r = B.analyze(q, hx, **p)
    ok, feats = R2.confidence(r, hx, q.question, p)
    print('=' * 100); print(q.question_id, q.question, '| mode', r['mode'], 'pair', r['pair'], 'conf', ok, feats)
    for sid in r['sess_rank'][:6]:
        s = r['best_by_sess'][sid]
        print(f"  {hx.sess_by_id[sid]['date_str'][:10]} {sid} own={s['own']:.1f} val={s['val']} cov={s['cov']:.2f} sc={s['score']:.2f} asst={bool(s.get('asst'))} | {s['raw'][:150]}")
    pk = lens.build(q, hx, **p)
    print('  PACK', [ps.id for ps in pk.passages], 'cite', pk.cite_plan, 'comp', pk.computed)
    print('  HINT', pk.hint.split('\nIf the value')[0].replace('\n', ' || ')[:700])
