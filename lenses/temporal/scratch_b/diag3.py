"""Question-route failures of a run: gold session rank, in pack, gold turn included, unit rank."""
import json,sys
sys.path.insert(0,'.')
from core.data import gold, questions
from core.gold_turns import gold_turns
from core.index import HistoryIndex
run=sys.argv[1]; split=run.rstrip('/').split('/')[-1]; route=sys.argv[2] if len(sys.argv)>2 else 'question'
g=gold(split); gt=gold_turns(); qm={q.question_id:q for q in questions(split)}
rows=[json.loads(l) for l in open(run+'/per_question.jsonl')]
for r in rows:
    if r['abstain_gold'] or r.get('PA',1)==1 or not str(r['debug'].get('route') or r['debug'].get('r3_from')).startswith(route): continue
    q=qm[r['question_id']]; hx=HistoryIndex.load(split, q.history_id)
    rank=r.get('ranking_top') or []; sess_order=list(dict.fromkeys(hx.units[u].session_id for u in rank))
    print('==',r['question_id'], q.question[:90], q.date_str, 'ALL',r['ALL'],'ATR',r['ATR'],'np',len(r['passages']),'cite',r['cite_plan'])
    inc=set(r['included_turns'])
    for sid in g[r['question_id']]['evidence']:
        s=hx.sess_by_id[sid]
        gts=[t for t in gt[r['question_id']] if t in {x['turn_id'] for x in s['turns']}]
        urank=[i for i,u in enumerate(rank) if hx.units[u].turn_id in gts]
        print('   gold',sid,s['date_str'],'sessrank',sess_order.index(sid) if sid in sess_order else None,'pack',sid in {p['id'] for p in r['passages']},'cite',sid in (r['cite_plan'] or []),'turns',[(t in inc) for t in gts],'urank',urank[:3])
