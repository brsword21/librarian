"""Round 3: firings of the typed KU gate on routed-ssu questions (role hand-off removed first)."""
import json, sys
from core.data import gold, questions
from core.index import HistoryIndex
from core.router import route
from core.types import SHORT
from harness.sweep import load_lens
split = sys.argv[1]
R = load_lens("lenses/ssu/a_r3_route.py")
role = load_lens("lenses/ssa/b_role.py")
g = gold(split) if split != "test" else {}
cfgs = {"kg6": dict(min_score=6.0, min_cov=0.5), "kg4": dict(min_score=4.0, min_cov=0.4), "kg3": dict(min_score=3.0, min_cov=0.4), "kg3g": dict(min_score=3.0, min_cov=0.4, gv=True)}
for q in questions(split):
    if route(q.question)[0] != "ssu":
        continue
    hx = HistoryIndex.load(split, q.history_id)
    if role.role_guess(q, hx) >= 0.8:
        continue
    gt = SHORT[g[q.question_id]["question_type"]] if q.question_id in g else "?"
    res = {k: R.ku_gate(q, hx, **c) for k, c in cfgs.items()}
    fired = [k for k, (h, _) in res.items() if h]
    why = res["kg3g"][1]
    if fired or gt == "ku":
        print(split, gt, q.question_id, fired, why.get("why"), why.get("types"), why.get("pair_sc"), why.get("cov_min"), "|", q.question[:80])
