"""R3: precision of rescued sessions (a_r3_pin r2) and their features."""
import json, sys
from core.data import gold
split = sys.argv[1]; var = sys.argv[2] if len(sys.argv) > 2 else "r2"
G = gold(split)
rows = [json.loads(l) for l in open(f"runs/r3-multi-a/multi/a_r3_pin/{var}/{split}/per_question.jsonl")]
ref = {json.loads(l)["question_id"]: json.loads(l) for l in open(f"runs/r3-multi-a/multi/a_r3_pin/ref/{split}/per_question.jsonl")}
n = tp = 0
for r in rows:
    d = r["debug"]; res = d.get("rescued", [])
    if not res: continue
    ev = set(G[r["question_id"]]["evidence"]) if not r["abstain_gold"] else set()
    sr = dict((s, v) for s, v in d["resc"]["s_rank"])
    top = d["resc"]["s_top"]
    kept_v = [sr[s] for s in d["keep"] if s in sr]
    for s in res:
        n += 1; tp += s in ev
        rk = [x for x, _ in d["resc"]["s_rank"]].index(s)
        print(f"{'GOLD' if s in ev else '----'} {r['question_id']} PA {ref[r['question_id']].get('PA')}->{r.get('PA')} rank={rk} keep={len(d['keep'])} v={sr[s]:.3f} gap={top-sr[s]:.3f} minkept={min(kept_v) if kept_v else None} abst={r['abstain_gold']} | {r['question'][:70]}")
print(f"rescued {n}, gold {tp}, q with rescue {sum(1 for r in rows if r['debug'].get('rescued'))}/{len(rows)}")
