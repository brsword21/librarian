import json, sys
from core.index import HistoryIndex
from harness.sweep import load_lens
L = load_lens('lenses/multi/a_r4_verb.py')
from lenses.multi import a_r3_pin as P3
packs={json.loads(l)['question_id']:json.loads(l) for l in open('runs/final/v2_test_packs.jsonl')}
qid=sys.argv[1]; needles=sys.argv[2:]
p=packs[qid]; qtext=p['question_text'].split('\n')[0]
hx=HistoryIndex.load('test', p['history_id'])
own=P3._own_sents(hx)
sc=hx.dense_texts(qtext,[s for s,_ in own])
order=sorted(range(len(own)), key=lambda i:-sc[i])
vre,w=L._verb_class(qtext)
print(qtext, 'verb', w, 'n_own', len(own))
for r,i in enumerate(order):
    s,uid=own[i]
    if r<15 or any(n.lower() in s.lower() for n in needles):
        print(r, round(sc[i],3), hx.units[uid].session_id, 'V' if vre and vre.search(s) else '-', 'B' if P3._bad_sent(s) else '-', s[:140])
