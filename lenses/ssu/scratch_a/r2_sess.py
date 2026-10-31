"""Per question of a routed run: top-5 session scores with gold marks (G) and pack marks (P)."""
import json, sys
from core.data import gold
d = sys.argv[1]; types = sys.argv[2].split(",") if len(sys.argv) > 2 else ["ku"]; only_fail = len(sys.argv) > 3
split = d.rstrip("/").split("/")[-1]; g = gold(split)
for l in open(d + "/per_question.jsonl"):
    r = json.loads(l)
    if r.get("type") not in types or r.get("abstain_gold"): continue
    if only_fail and r["PA"] >= 1: continue
    ev = set(g[r["question_id"]]["evidence"]); pk = {p["id"] for p in r["passages"]}
    ss = " ".join(f"{s[1]:.1f}{'G' if s[0] in ev else ''}{'P' if s[0] in pk else ''}" for s in r["debug"]["sess"])
    miss = [e for e in ev if e not in {s[0] for s in r['debug']['sess']}]
    print(f"{r['type']:5s} PA={r['PA']:.0f} top={r['debug']['top_logit']:5.1f} [{ss}] miss5={len(miss)} | {r['question'][:70]}")
