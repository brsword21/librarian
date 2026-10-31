import sys, re
sys.path.insert(0, '.')
from core.data import questions
from core.index import HistoryIndex
from lenses.temporal import b_r4_last as L
split = sys.argv[1]
for q in questions(split):
    pq = L.parse_last(q.question)
    if not pq: continue
    hx = HistoryIndex.load(split, q.history_id)
    cs = [c for c in L.candidates(q, hx, pq, {}) if c['own']]
    if not cs: continue
    qq = re.sub(r"\b(?:last|most recently)\b ?", "", q.question)
    ce = hx.rerank_texts(qq, [c['sent'] for c in cs])
    de = hx.dense_texts(qq, [c['sent'] for c in cs])
    print('=====', qq, pq['cat'])
    for c, a, b in sorted(zip(cs, ce, de), key=lambda x: -x[1])[:7]:
        print(f"   {c['date']} qce={a:.2f} dense={b:.3f} sce={c['ce']:.2f} {c['sent'][:110]!r}")
