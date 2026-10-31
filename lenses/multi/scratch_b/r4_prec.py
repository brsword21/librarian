"""Selector precision probe (gold): run the r4 rescue with NO sessions excluded on dev/dev200 multi questions and
check whether each picked session is a gold session (holds a gold turn)."""
import sys
from core.data import questions
from core.index import HistoryIndex
from core.gold_turns import gold_turns
from lenses.multi import b_sweep as R1
from lenses.multi import b_r4_inst as B

GT = gold_turns()
from core.data import gold
GOLD = {s: gold(s) for s in ("dev", "dev200")}
V = dict(r_max=2, r_thr=-7.0, d_thr=0.62, d_ce=-3.0, r_gap=4.0)
for split in ("dev", "dev200"):
    tp = fp = nq = 0
    for q in questions(split):
        gg = GOLD[split].get(q.question_id, {})
        if "multi" not in str(gg.get("question_type", gg.get("type", ""))):
            continue
        g = GT.get(q.question_id) or []
        if not g:
            continue
        hx = HistoryIndex.load(split, q.history_id)
        gs = {hx.units[hx.turn_units(t)[0]].session_id for t in g if hx.turn_units(t)}
        a = R1.analyze(q.question, q.date)
        best = B.rescue(q, hx, a, V, set(), False)
        if not best:
            continue
        nq += 1
        for sid, v in best.items():
            ok = sid in gs
            tp += ok
            fp += not ok
            print(split, "GOLD" if ok else "miss", q.question[:60], "|", v[1][:90], v[2])
    print(f"## {split}: fired {nq} q, picks gold {tp}, non-gold {fp}")
