import json, sys, re
packs={json.loads(l)['question_id']:json.loads(l) for l in open(sys.argv[1])}
qid=sys.argv[2]; kw=[k.lower() for k in sys.argv[3:]]
p=packs[qid]
print(p['question'][:1200]); print('CITE', p['cite_plan'], 'comp', p['computed'])
for i,ps in enumerate(p['passages']):
    print(f"--- E{i+1} {ps['id']} {ps.get('date')} len={len(ps['text'])}")
    txt=ps['text']
    if kw:
        for s in re.split(r'(?<=[.!?])\s+|\n', txt):
            if any(k in s.lower() for k in kw): print('   *', s[:300])
    else:
        print(txt[:1500])
