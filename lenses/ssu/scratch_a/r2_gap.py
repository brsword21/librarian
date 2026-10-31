"""Session-score gap between top-1 and top-2 by gold type (routed ssu runs)."""
import json, sys
from core.data import gold
for d in sys.argv[1:]:
    split = d.rstrip("/").split("/")[-1]; g = gold(split)
    for l in open(d + "/per_question.jsonl"):
        r = json.loads(l)
        if r.get("abstain_gold"): continue
        ev = set(g[r["question_id"]]["evidence"])
        ss = r["debug"]["sess"]
        if len(ss) < 2: gap = 99; s2g = False
        else:
            gap = ss[0][1] - ss[1][1]; s2g = ss[1][0] in ev
        s1g = ss[0][0] in ev if ss else False
        print(f"{r['type']:8s} gap={gap:5.2f} top1gold={int(s1g)} top2gold={int(s2g)} s1={ss[0][1] if ss else 0:5.2f} | {r['question'][:70]}")
