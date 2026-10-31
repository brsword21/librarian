"""Prototype the question-typed value gate offline on dumped features."""
import json, re, sys
from collections import Counter
sys.path.insert(0, ".")
from lenses.ku.scratch_b.r3_rules import load
from lenses.ku.b_r3_gate import typed_values, q_types, REVERT
rows = load()
def rule(q, f, s_thr, c_thr):
    qt = q_types(q)
    if not qt or min(f["own"]) <= 0 or any(f["asst"]): return False, ""
    to, tn = typed_values(f["raw_o"], q), typed_values(f["raw_n"], q)
    d = [k for k in qt if k in to and k in tn and not (to[k] & tn[k])]
    if not d: return False, "nodiff"
    if REVERT.search(f["raw_o"]) or REVERT.search(f["raw_n"]): return False, "revert"
    return min(f["pair_sc"]) >= s_thr and f["cov_min"] >= c_thr, "thr"
for s in (-2, 0, 2, 3, 4):
    for c in (0.0, 0.25, 0.4):
        cnt = Counter(("d200" if sp == "dev200" else sp, t) for sp, t, ab, q, f, _ in rows if rule(q, f, s, c)[0])
        print(f"s>={s:3} cov>={c:.2f}", dict(sorted(cnt.items())))
if len(sys.argv) > 2:
    s, c = float(sys.argv[1]), float(sys.argv[2])
    for sp, t, ab, q, f, qid in rows:
        ok, why = rule(q, f, s, c)
        if ok or (t == "ku" and why in ("revert", "thr")):
            print(sp, t, "FIRE" if ok else why, qid, q[:80], f["pair_sc"], f["cov_min"])
