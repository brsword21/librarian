"""Audit: own sentences with a category hit + fact/number that sit in sessions NOT in the pack (test, no gold)."""
import json, re, sys
from core.index import HistoryIndex
from harness.sweep import load_lens
L = load_lens('lenses/multi/a_r4_verb.py')
from lenses.multi import a_r3_pin as P3, b_sweep as R1
packs=[json.loads(l) for l in open(sys.argv[1])]
NUM=re.compile(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|a couple|a dozen)\b", re.I)
for p in packs:
    if p['route']!='multi': continue
    qt=p['question_text'].split('\n')[0]
    from datetime import datetime
    hx=HistoryIndex.load('test', p['history_id'])
    a=R1.analyze(qt, datetime(2023,12,31))
    terms=a["terms"]+[w for f in a["facets"] for w in R1.content_terms(f)]
    vre,w=L._verb_class(qt)
    inp={x['id'] for x in p['passages']}
    own=P3._own_sents(hx)
    sc=hx.dense_texts(qt,[s for s,_ in own])
    order=sorted(range(len(own)), key=lambda i:-sc[i])
    out=[]
    for r,i in enumerate(order[:80]):
        s,uid=own[i]; sid=hx.units[uid].session_id
        if sid in inp or P3._bad_sent(s): continue
        if L._lex2(s, terms, w or '') and NUM.search(s):
            out.append((r, sid, hx.units[uid].date_str[:10], s[:150]))
    print('==', p['question_id'], qt[:90], '| verb', w)
    for o in out[:4]: print('    ', o)
