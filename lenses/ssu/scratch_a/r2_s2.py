"""s2 (second session score) and s2-s3 by type, with gold flag of s2: does an outlier runner-up predict a 2nd gold session?"""
import json, sys
from collections import defaultdict
from core.data import gold
rows = defaultdict(list)
for d in sys.argv[1:]:
    split = d.rstrip("/").split("/")[-1]; g = gold(split)
    for l in open(d + "/per_question.jsonl"):
        r = json.loads(l)
        if r.get("abstain_gold"): continue
        ev = set(g[r["question_id"]]["evidence"]); ss = r["debug"]["sess"] + [("x", -12)] * 3
        rows[r["type"]].append((ss[1][1], ss[1][1] - ss[2][1], ss[0][1] - ss[1][1], ss[1][0] in ev, r["PA"]))
for th_abs in (-7, -6, -5, -4):
    for th_out in (2, 3, 4):
        out = []
        for t, rs in sorted(rows.items()):
            fire = [x for x in rs if x[0] > th_abs and x[1] > th_out]
            out.append(f"{t}:{len(fire)}/{len(rs)} g{sum(x[3] for x in fire)}")
        print(f"s2>{th_abs} s2-s3>{th_out}: " + "  ".join(out))
