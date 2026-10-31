"""Evaluate ku hand-off rules on ssu-routed features (dev, dev200 gold; test firings listed)."""
import json, itertools
from collections import Counter
def load():
    out = []
    for split in ["dev", "dev200"]:
        for l in open(f"runs/r3-ku-b/ssu-routed/b_r3_gate/v1/{split}/per_question.jsonl"):
            r = json.loads(l); f = (r.get("debug") or {}).get("ku_feats")
            if r.get("route") != "ssu" or not f or "pair_sc" not in f: continue
            out.append((split, r["type"], r.get("abstain_gold"), r["question"], f, r["question_id"]))
    for l in open("runs/audit/ssu/b_r3_gate/v1/test_packs.jsonl"):
        r = json.loads(l); f = (r.get("debug") or {}).get("ku_feats")
        if r.get("route") != "ssu" or not f or "pair_sc" not in f: continue
        out.append(("test", "?", None, r["question"], f, r["question_id"]))
    return out
T = {"time", "money", "qty", "freq", "day"}
def rule(f, s_thr, c_thr, types=T, own=True):
    if own and (min(f["own"]) <= 0 or any(f["asst"])): return False
    if not (set(f["diff_types"]) & types): return False
    return min(f["pair_sc"]) >= s_thr and f["cov_min"] >= c_thr
rows = load()
import sys
grid = [(s, c) for s in (-2, 0, 2, 3, 4, 6) for c in (0.0, 0.25, 0.3, 0.4, 0.5)]
for s, c in grid:
    cnt = Counter((sp if sp != "dev200" else "d200", t) for sp, t, ab, q, f, _ in rows if rule(f, s, c))
    print(f"s>={s:3} cov>={c:.2f}  ", dict(sorted(cnt.items())))
if len(sys.argv) > 2:
    s, c = float(sys.argv[1]), float(sys.argv[2])
    for sp, t, ab, q, f, qid in rows:
        if rule(f, s, c) and t != "ku":
            print(sp, t, qid, q[:80], f["diff_types"], f["pair_sc"], f["cov_min"]); print("    O:", f["raw_o"][:150]); print("    N:", f["raw_n"][:150])
