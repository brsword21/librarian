import json
from collections import defaultdict
rules = {
 "x1": lambda r: r[2] < 1,
 "x2": lambda r: r[2] < 2,
 "x1|n40>=4&so<=6": lambda r: r[2] < 1 or (r[5] >= 4 and r[4] <= 6),
 "x1|n40>=5": lambda r: r[2] < 1 or r[5] >= 5,
 "x1|n40>=4": lambda r: r[2] < 1 or r[5] >= 4,
 "x1|so<=3": lambda r: r[2] < 1 or r[4] <= 3,
 "x1|lex>=3": lambda r: r[2] < 1 or r[6] >= 3,
 "x1|n40>=4&lex>=1": lambda r: r[2] < 1 or (r[5] >= 4 and r[6] >= 1),
 "x0|n40>=4": lambda r: r[5] >= 4,
 "x0|so<=4": lambda r: r[4] <= 4,
 "x1min2": None,
}
for split in ("dev", "dev200"):
    rows = json.load(open(f"lenses/multi/scratch_a/outside_{split}.json"))
    byq = defaultdict(list)
    for r in rows:
        byq[r[1]].append(r)
    print(split, "questions", len(byq))
    for name, fn in rules.items():
        if fn is None:
            continue
        lost = 0; added = 0
        for qid, rs in byq.items():
            core = rs[0][7]
            keep = [r for r in rs if fn(r)]
            # min 2: if core==1 and nothing kept, keep pos 0
            gold_out = [r for r in rs if r[0]]
            if any(not fn(r) for r in gold_out):
                lost += 1
            added += len(keep)
        print(f"  {name:22} questions losing gold={lost:3d} extras/q={added/len(byq):.2f}")
