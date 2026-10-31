"""Scratch r3: where do the gold sessions rank in a_struct2 r3rn's session ranking (routed ssu, non-ssu gold or PA<1).
    .venv/bin/python -m lenses.ssu.scratch_b.r3_diag runs/r3-ssu-b/ssu-routed/merged_r2/role8_r3rn/dev200 dev200
"""
import json
import re
import sys

from core.data import gold, questions
from core.index import HistoryIndex
from lenses.ssu import a_struct2
from lenses.ssu.a_owner import parse_question, unit_class
from lenses.ssu.a_struct import Q_PAST_RX, adjust, candidate_pool, tense_adjust

run, split = sys.argv[1], sys.argv[2]
types = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else {"ku", "multi", "temporal"}
G = gold(split)
Q = {q.question_id: q for q in questions(split)}
P = {**a_struct2.DEFAULTS, **a_struct2.VARIANTS["r3rn"]}
for line in open(f"{run}/per_question.jsonl"):
    r = json.loads(line)
    if r["route"] != "ssu" or (r["type"] not in types and r.get("PA", 1) == 1 and (r.get("CF1") or 0) >= 1):
        continue
    if r["abstain_gold"]:
        continue
    q = Q[r["question_id"]]
    hx = HistoryIndex.load(split, q.history_id)
    qp = parse_question(q.question)
    pool = candidate_pool(q, hx, qp, P)
    rr = dict(hx.rerank(q.question, pool))
    qpast = bool(Q_PAST_RX.search(q.question))
    sc, cl = {}, {}
    for u in pool:
        c = unit_class(hx.units[u], qp)
        cl[u] = c
        sc[u] = rr[u] + adjust(c, qp, P) + tense_adjust(hx.units[u], c, qpast, P)
    best = {}
    for u in sorted(sc, key=lambda x: -sc[x]):
        best.setdefault(hx.units[u].session_id, u)
    srank = sorted(best, key=lambda s: -sc[best[s]])
    ev = G[q.question_id]["evidence"]
    print("=" * 110)
    print(f"[{r['type']}] PA={r.get("PA")} CF1={r.get("CF1") or 0:.2f} {q.question} | gold={G[q.question_id]['answer'][:60]}")
    print("   pack:", [p["id"][-6:] for p in r["passages"]], "cite:", [c[-6:] for c in (r["cite_plan"] or [])])
    for s in srank[:5]:
        u = best[s]
        c = cl[u]
        tag = "GOLD" if s in ev else "    "
        print(f"   {tag} #{hx.sess_by_id[s]['sess_idx']:3d} {s[-6:]} sc={sc[u]:6.2f} rr={rr[u]:6.2f} {c.owner[:5]}/{c.polarity}/h{int(c.head_hit)}"
              f" {re.sub(chr(10), ' ', hx.units[u].text)[:110]}")
    for s in ev:
        if s not in srank[:5]:
            if s in best:
                u = best[s]
                c = cl[u]
                print(f"   MISS rank {srank.index(s)} #{hx.sess_by_id[s]['sess_idx']} sc={sc[u]:.2f} rr={rr[u]:.2f} {c.owner[:5]}/{c.polarity}/h{int(c.head_hit)}"
                      f" {re.sub(chr(10), ' ', hx.units[u].text)[:110]}")
            else:
                us = [x.uid for x in hx.units if x.session_id == s and x.role == "user"]
                rs = hx.rerank(q.question, us)
                b = max(rs, key=lambda t: t[1]) if rs else (None, -99)
                print(f"   MISS not-in-pool #{hx.sess_by_id[s]['sess_idx']} best user rr={b[1]:.2f} "
                      f"{re.sub(chr(10), ' ', hx.units[b[0]].text)[:110] if b[0] is not None else ''}")
