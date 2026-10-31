"""Which gold sessions does a pruning rule drop? .venv/bin/python -m lenses.multi.scratch_a.prune_miss <dir> D extra min"""
import json, sys
from pathlib import Path
from core.data import gold
from lenses.multi.scratch_a.prune_sim import rule

d, D, extra, mn = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
rows = [json.loads(l) for l in open(Path(d) / "per_question.jsonl")]
split = "dev200" if d.rstrip("/").endswith("dev200") else "dev"
g = gold(split)
for r in rows:
    if r.get("abstain_gold") or not r["PA"]:
        continue
    G = set(g[r["question_id"]]["evidence"])
    S = r["debug"]["sess"]
    keep = rule(S, D, extra, mn)
    if G <= set(keep):
        continue
    order = sorted(S, key=lambda s: -S[s][4])
    top = S[order[0]][4]
    print(r["question_id"], r["question"][:90])
    for i, s in enumerate(order):
        f = S[s]
        print(f"   {i:2d} {'G' if s in G else ' '} {'K' if s in keep else ' '} rr_max={f[4]:6.2f} (top-{top-f[4]:5.2f}) first_rank={f[0]} lab={f[2]} n40={f[3]}")
