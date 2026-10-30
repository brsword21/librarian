"""Qualitative test audit (no gold): BM25(minibm25) + rec features -> top-3 assistant units and the abstain signal."""
import json, sys
sys.path.insert(0, '.'); sys.path.insert(0, 'lenses/ssa/scratch_b'); sys.path.insert(0, 'lenses/ssa')
from minibm25 import Units, BM25, toks
from core.data import history
import b_semantic as L

class FakeHX:
    def __init__(self, U):
        class _u:
            def __init__(s, d): s.text = d['text']
        self.units = [_u(d) for d in U.units]

rows = [json.loads(l) for l in open('runs/samples/ssa.jsonl') if '"split": "test"' in l]
for r in rows:
    h = history('test', r['history_id']); U = Units(h); us = U.units
    bm = BM25([toks(u['ctx'] + ' ' + u['text']) for u in us])
    cq = L.clean_question(r['question']); rp = L.parse_rec(r['question'])
    sc = bm.score(toks(cq))
    idf = L.history_idf(FakeHX(U))
    top = sorted(range(len(us)), key=lambda i: -sc[i])[:40]
    fused = {}
    feats = {}
    mu = sum(sc[i] for i in top) / len(top); sd = (sum((sc[i] - mu) ** 2 for i in top) / len(top)) ** .5 or 1
    for i in top:
        z = (sc[i] - mu) / sd
        if us[i]['role'] == 'assistant':
            f = L.rec_features(us[i]['text'], rp['purpose'], rp['cat'], idf=idf); feats[i] = f
            z += 0.6 * f['rec'] + 0.6 * f['purpose'] * (f['rec'] > 0) + 0.2 * f['cat']
        else:
            z -= 0.3
        fused[i] = z
    rk = sorted(fused, key=lambda i: -fused[i])
    ap = L.abstain_probability(rk, fused, feats, rp)
    print(f"\nQ: {r['question']}  [cat={rp['cat']!r} purpose={rp['purpose']!r}] abstain_p={ap}")
    for i in rk[:3]:
        f = feats.get(i, {})
        print(f"   {fused[i]:+.2f} bm25#{top.index(i)+1:<3d} {us[i]['role'][:4]} rec={f.get('rec',0):+.1f} pur={f.get('purpose',0):.2f} | {us[i]['text'][:150]!r}")
