"""Break a per_question.jsonl down by gold type: python -m ... <run_dir> [<run_dir2>]"""
import json, sys
from collections import defaultdict
from core.data import gold
from core.types import SHORT

def load(d):
    split = d.rstrip("/").split("/")[-1]
    g = gold(split)
    rows = [json.loads(l) for l in open(d + "/per_question.jsonl")]
    return g, rows

for d in sys.argv[1:]:
    g, rows = load(d)
    by = defaultdict(list)
    for r in rows:
        t = r.get("type") or "?"
        by[t].append(r)
    print(d)
    for t, rs in sorted(by.items()):
        ans = [r for r in rs if "S" in r and r.get("S") is not None]
        def m(k):
            v = [r[k] for r in ans if r.get(k) is not None]
            return sum(v) / len(v) if v else float("nan")
        print(f"  {t:9s} n={len(rs):3d} ans={len(ans):3d} S={m('S'):6.1f} Sall={m('Sall'):6.1f} PA={m('PA'):.3f} CF1={m('CF1'):.3f} CF1all={m('CF1all'):.3f} chars={m('chars'):.0f}")
