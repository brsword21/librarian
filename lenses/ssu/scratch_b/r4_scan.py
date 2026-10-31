"""r4: for every ssu-route v2 test pack: best user sentence (CE) in the pack vs best user sentence in the history
(hybrid top-150 user units). Flags packs whose best history sentence is not in the pack."""
import json, re, sys
from core.index import HistoryIndex
from core.data import questions
from lenses.ssu.a_owner import sentences
r = [json.loads(l) for l in open('runs/final/v2_test_packs.jsonl')]
Q = {q.question_id: q for q in questions('test')}
for x in r:
    if x.get('route_text') != 'ssu':
        continue
    q = Q[x['question_id']]
    hx = HistoryIndex.load('test', q.history_id)
    ptxt = '\n'.join(p['text'] for p in x['passages'])
    pool = [u for u, _ in hx.hybrid(q.question, k=150, roles=['user'], pool=400)]
    texts, own = [], []
    for u in pool:
        for s in sentences(hx.units[u].text) or [hx.units[u].text]:
            if len(s) >= 12:
                texts.append(s); own.append(u)
    sc = hx.rerank_texts(q.question, texts)
    o = sorted(range(len(texts)), key=lambda i: -sc[i])
    inp = [i for i in o if texts[i][:60] in ptxt]
    outp = [i for i in o if texts[i][:60] not in ptxt]
    bi = sc[inp[0]] if inp else -99
    bo = sc[outp[0]] if outp else -99
    flag = 'FLAG' if bo > bi - 1.0 else '    '
    print(f"{flag} {x['question_id']} in={bi:6.2f} out={bo:6.2f} | {q.question[:70]}")
    if flag == 'FLAG':
        for i in inp[:1]:
            print(f"      IN  {sc[i]:6.2f} {hx.units[own[i]].session_id} | {texts[i][:130]}")
        for i in outp[:3]:
            print(f"      OUT {sc[i]:6.2f} {hx.units[own[i]].session_id} {hx.units[own[i]].date_str[:10]} | {texts[i][:130]}")
    sys.stdout.flush()
