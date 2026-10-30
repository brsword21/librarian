"""Smoke-run b_sweep.build on a few dev multi questions (not an eval; uses the shared model server).
    .venv/bin/python -m lenses.multi.scratch_b.smoke q_id [q_id ...]"""
import sys, time
from core.data import questions, gold
from core.gold_turns import gold_turns
from core.index import HistoryIndex
from lenses.multi import b_sweep as L

qs = {q.question_id: q for q in questions("dev")}
G, GT = gold("dev"), gold_turns()
for qid in sys.argv[1:]:
    q = qs[qid]; g = G[qid]
    hx = HistoryIndex.load("dev", q.history_id)
    for v in ("sweep", "sessagg"):
        t = time.time()
        p = L.build(q, hx, _variant=v, **L.VARIANTS[v])
        ev, P = set(g["evidence"]), set(p.session_ids())
        A = set(GT.get(qid, []))
        cite = set(p.planned_citations())
        tp = len(cite & ev)
        f1 = 2 * tp / (len(cite) + len(ev)) if cite and ev else 0
        print(f"{qid} {v:8} ALL={int(ev <= P)} SR={len(ev & P)}/{len(ev)} ATR={len(A & p.included_turns)}/{len(A)} "
              f"sess={len(P)} cite={len(cite)} CF1={f1:.2f} chars={p.debug['chars']} abst={p.abstain_p:.2f} "
              f"top_rr={p.debug['top_rr']:.1f} ms={1000*(time.time()-t):.0f}")
    print("  HINT:", p.hint[:300])
    print("  first passage:", p.passages[0].date, p.passages[0].text[:300].replace("\n", " | "))
