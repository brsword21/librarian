import json, sys
from core.data import questions
from core.index import HistoryIndex
from lenses.multi import b_sweep as B, a_prune as AP
variant = sys.argv[1]
Q = {q.question_id: q for q in questions("test")}
for l in open(f"runs/audit/multi/a_prune/{variant}/test_packs.jsonl"):
    r = json.loads(l)
    dr = r["debug"].get("dropped_other") or []
    if not dr:
        continue
    q = Q[r["question_id"]]
    hx = HistoryIndex.load("test", q.history_id)
    P = dict(B.VARIANTS["sweep"]); P.update(AP.VARIANTS[variant])
    a = B.analyze(q.question, q.date)
    ranked, final, rr, lab, facet_top, rest, win_active = B._score_units(q, hx, a, P)
    print("Q:", q.question)
    for sid in dr:
        us = sorted([u for u in rr if hx.units[u].session_id == sid], key=lambda u: -rr[u])[:3]
        for u in us:
            print(f"   {sid} {rr[u]:6.2f} {lab.get(u)} {hx.units[u].role}: {hx.units[u].text[:260]!r}")
