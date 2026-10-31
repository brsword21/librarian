"""Does turn_margin predict best turn == gold turn? Usage: .venv/bin/python -m lenses.ssa.scratch_a.margin_eval <split>"""
import sys
from core.data import gold, questions
from core.gold_turns import gold_turns
from core.index import HistoryIndex
from lenses.ssa import a_recsent as L
split = sys.argv[1]
g = gold(split); gt = gold_turns()
P = L.VARIANTS["r2_b6"]
rows = []
for q in questions(split):
    if g[q.question_id]["question_type"] != "single-session-assistant":
        continue
    hx = HistoryIndex.load(split, q.history_id)
    pk = L.build(q, hx, _variant="x", **P)
    b = pk.debug["ranking"][0]
    ok = hx.units[b].turn_id in set(gt.get(q.question_id, []))
    gl = sum(len(hx.units[i].text) for t in gt.get(q.question_id, []) for i in hx.turn_units(t))
    rows.append((pk.debug["best"]["turn_margin"], ok, len(hx.units[b].text), gl))
rows.sort(key=lambda r: -r[0])
for thr in (3.0, 2.5, 2.0, 1.8, 1.6, 1.5, 1.4, 1.3, 1.2, 1.1):
    sub = [r for r in rows if r[0] >= thr]
    print(f"thr {thr}: n={len(sub)} best==gold {sum(r[1] for r in sub)}/{len(sub)}  max gold chars {max((r[3] for r in sub), default=0)}")
