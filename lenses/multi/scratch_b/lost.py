"""Which gold sessions would a rr_max pruning drop? Prints question, gold session gap to top, its rank."""
import json, sys
from pathlib import Path
from core.data import gold
d = sys.argv[1]; D = float(sys.argv[2]) if len(sys.argv) > 2 else 8
rows = [json.loads(l) for l in open(Path(d) / "per_question.jsonl")]
g = gold("dev200" if d.rstrip("/").endswith("dev200") else "dev")
for r in rows:
    if r.get("abstain_gold") or r["question_id"] not in g:
        continue
    S = r["debug"]["sess"]; G = g[r["question_id"]]["evidence"]
    order = sorted(S, key=lambda s: -S[s][4]); top = S[order[0]][4]
    gaps = [(round(top - S[s][4], 1), order.index(s)) if s in S else ("OUT", -1) for s in G]
    if any(x[0] == "OUT" or x[0] > D for x in gaps):
        print(f"{r['question'][:85]:85} top={top:.1f} gold(gap,rank)={gaps} n={len(order)}")
