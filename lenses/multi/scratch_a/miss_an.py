"""For PA<1 rows: which gold turns were missed, where they sit, and whether their session was in the pack."""
import json, sys
from core.data import gold, questions
from core.gold_turns import gold_turns
from core.index import HistoryIndex
run = sys.argv[1]
split = run.rstrip('/').split('/')[-1]
g, gt = gold(split), gold_turns()
qm = {q.question_id: q for q in questions(split)}
rows = [json.loads(l) for l in open(run + '/per_question.jsonl')]
for r in rows:
    if r.get('abstain_gold') or r.get('PA', 1) == 1: continue
    q = qm[r['question_id']]
    hx = HistoryIndex.load(split, q.history_id)
    inc = set(r['debug'].get('inc', []))
    packed = {p['id'] for p in r['passages']}
    print('=' * 100); print(q.question, '| gold:', g[q.question_id]['answer'][:80], '| kind', r['debug'].get('kind'))
    for tid in gt.get(q.question_id, []):
        if tid in inc: continue
        uids = hx.turn_units(tid)
        u = hx.units[uids[0]]
        rank = [i for i, x in enumerate(r.get('ranking_top', [])) if x in uids]
        print(f'  MISS turn t{u.turn_idx} sess {u.session_id} {"IN-PACK" if u.session_id in packed else "NOT-PACKED"} rank30={rank}:', ' '.join(hx.units[i].text for i in uids)[:300].replace('\n', ' '))
