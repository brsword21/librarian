"""Probe: r4 rescue on multi-routed v2 test packs (no gold). python -m lenses.multi.scratch_b.r4_probe PACKS"""
import json, sys
from core.data import questions
from core.index import HistoryIndex
from lenses.multi import b_sweep as R1
from lenses.multi import b_r4_inst as B

packs = [json.loads(l) for l in open(sys.argv[1])]
V = B.VARIANTS[sys.argv[2] if len(sys.argv) > 2 else "vc2"]
qs = {q.question_id: q for q in questions("test")}
for p in packs:
    q = qs[p["question_id"]]
    hx = HistoryIndex.load("test", q.history_id)
    a = R1.analyze(q.question, q.date)
    in_pack = {x["id"] for x in p["passages"] if x["id"]}
    span = (hx.sessions[-1]["date"] - hx.sessions[0]["date"]).days
    win_active = span >= 45 and bool(a["window"])
    cands, classes, heads = B.candidates(q, hx, a, in_pack, win_active)
    best = B.rescue(q, hx, a, V, in_pack, win_active) if cands else {}
    print(f"== {q.question_id} {q.question[:80]} | cls {[c[0] for c in classes]} | cands {len(cands)} | RESCUE {len(best)}")
    texts = [c[1] for c in cands][:300]
    if texts:
        ce = hx.rerank_texts(q.question, texts)
        dn = hx.dense_texts(q.question, texts)
        for i in sorted(range(len(texts)), key=lambda i: -ce[i])[:4]:
            uid, se, hh, cls = cands[i]
            mark = "**" if hx.units[uid].session_id in best else "  "
            print(f" {mark} ce {ce[i]:6.2f} dn {dn[i]:.3f} head {int(hh)} {hx.units[uid].date_str[:10]} {se[:120]}")
