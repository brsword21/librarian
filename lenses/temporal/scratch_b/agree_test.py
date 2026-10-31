"""Test (no gold): A's computed gap vs B's independent event-route computation (b_sem sem_turns9)."""
import json, sys
sys.path.insert(0, '.')
from core.data import questions
from core.index import HistoryIndex
from lenses.temporal import b_sem as B
split = sys.argv[1] if len(sys.argv) > 1 else 'test'
packs = {json.loads(l)['question_id']: json.loads(l) for l in open(sys.argv[2])}
qm = {q.question_id: q for q in questions(split)}
agree = dis = bnone = 0
for qid, r in packs.items():
    if (r.get('debug') or {}).get('parse', {}).get('kind') != 'gap':
        continue
    q = qm[qid]; hx = HistoryIndex.load(split, q.history_id)
    bp = B.build(q, hx, _variant='sem_turns9', **B.VARIANTS['sem_turns9'])
    a = r.get('computed') or (r.get('debug') or {}).get('computed_raw')
    b = bp.computed
    tag = 'NONE' if b is None else ('AGREE' if a is not None and abs(int(a) - int(b)) <= 1 else 'DIS')
    agree += tag == 'AGREE'; dis += tag == 'DIS'; bnone += tag == 'NONE'
    if tag != 'AGREE':
        print(tag, qid, q.question[:80], '| A', r.get('computed'), 'raw', (r.get('debug') or {}).get('computed_raw'), '| B', b)
        for pk in (bp.debug or {}).get('picks') or []:
            print('     B pick', pk.get('date'), pk.get('subj'), repr(pk.get('sent', '')[:120]))
        for pk in (r.get('debug') or {}).get('picks') or []:
            print('     A pick', pk)
print('agree', agree, 'disagree', dis, 'B none', bnone)
