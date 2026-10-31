"""r4 diag: v2 ssu route pack for a test/dev question, rank of a uid, sentence-level CE of user sentences."""
import json, sys
from core.index import HistoryIndex
from harness.sweep import load_lens
from core.data import questions
from lenses.ssu.a_owner import sentences
split, qid = sys.argv[1], sys.argv[2]
uid_t = int(sys.argv[3]) if len(sys.argv) > 3 else None
cfg = json.load(open('configs/best.json'))['routes']['ssu']
q = [q for q in questions(split) if q.question_id == qid][0]
hx = HistoryIndex.load(split, q.history_id)
lens = load_lens(cfg['lens'])
pk = lens.build(q, hx, _variant=cfg['variant'], **cfg['params'])
d = pk.debug
print(q.question, '| route_final', d.get('route_final'), '| cite', pk.cite_plan, '| ab', round(pk.abstain_p, 3))
print('sess', d.get('sess'))
print('top', d.get('top'))
rk = d.get('ranking', [])
if uid_t is not None:
    print('target rank', rk.index(uid_t) if uid_t in rk else 'NOT IN POOL', 'of', len(rk))
# sentence CE over user units of top hybrid pool
pool = [u for u, _ in hx.hybrid(q.question, k=300, roles=['user'], pool=600)]
print('target in hybrid300', uid_t in pool if uid_t is not None else '-', pool.index(uid_t) if uid_t in pool else '')
texts, owners = [], []
for u in pool[:150]:
    for s in sentences(hx.units[u].text) or [hx.units[u].text]:
        if len(s) >= 12:
            texts.append(s); owners.append(u)
sc = hx.rerank_texts(q.question, texts)
order = sorted(range(len(texts)), key=lambda i: -sc[i])
for i in order[:12]:
    u = owners[i]
    print(f'{sc[i]:6.2f} {u:5d} {hx.units[u].session_id} {hx.units[u].date_str[:10]} | {texts[i][:140]}')
if uid_t is not None:
    for i in range(len(texts)):
        if owners[i] == uid_t:
            print('TARGET', f'{sc[i]:6.2f} rank', order.index(i), '|', texts[i][:140])
