"""Round 3: dump KU-pair features for every routed-ssu question (dev, dev200, test) -> jsonl.
Usage: .venv/bin/python -m lenses.ssu.scratch_a.r3_kufeat dev|dev200|test
"""
import json
import sys

from core.data import gold, questions
from core.index import HistoryIndex
from core.router import route
from core.types import SHORT
from harness.sweep import load_lens

split = sys.argv[1]
g = gold(split) if split != "test" else {}
kb = load_lens("lenses/ku/b_r2.py")
role = load_lens("lenses/ssa/b_role.py")
B = kb.B
out = open(f"lenses/ssu/scratch_a/r3_kufeat_{split}.jsonl", "w")
for q in questions(split):
    if route(q.question)[0] != "ssu":
        continue
    hx = HistoryIndex.load(split, q.history_id)
    try:
        if role.role_guess(q, hx) >= 0.8:
            continue
    except Exception:
        pass
    p = dict(kb.VARIANTS["r2b"])
    r = B.analyze(q, hx, **p)
    ok, f = kb.confidence(r, hx, q.question, dict(p, gate_v=2))
    row = {"qid": q.question_id, "q": q.question, "gt": SHORT[g[q.question_id]["question_type"]] if q.question_id in g else "?",
           "abst": bool(g.get(q.question_id, {}).get("abstain")),
           "gold_s": g.get(q.question_id, {}).get("evidence"),
           "f": {k: v for k, v in f.items() if k != "threat"}, "pair": r.get("pair")}
    if len(r.get("pair") or []) == 2:
        bbs = r["best_by_sess"]
        row["raw"] = [bbs[s]["raw"][:300] for s in r["pair"]]
        row["own"] = [bbs[s]["own"] for s in r["pair"]]
        row["vals"] = [sorted(B.values(bbs[s]["raw"], q.question)) for s in r["pair"]]
        row["dates"] = [hx.sess_by_id[s]["date_str"][:10] for s in r["pair"]]
    out.write(json.dumps(row) + "\n")
out.close()
