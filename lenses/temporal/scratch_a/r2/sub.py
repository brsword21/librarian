"""Subset metrics (gap vs rest) from per_question.jsonl files. usage: sub.py run_dir [run_dir...]"""
import json, re, sys
from statistics import mean
GAP = re.compile(r"how many (days|weeks|months)\b.*\b(apart|after|before|between|passed)|days? (apart|after|before)", re.I)
def load(p):
    return [json.loads(l) for l in open(p + "/per_question.jsonl")]
def agg(rows):
    ans = [r for r in rows if not r.get("abstain_gold")]
    f = lambda k: round(mean([r[k] for r in ans if r.get(k) is not None]), 3) if any(r.get(k) is not None for r in ans) else None
    return dict(n=len(rows), na=len(ans), S=round(mean([r["S"] for r in ans]), 1) if ans else None, PA=f("PA"), HA=f("HA"),
                ATR=f("ATR"), ALL=f("ALL"), CF1=f("CF1"), CF1all=f("CF1all"), Sall=round(mean([r["Sall"] for r in ans]), 1) if ans else None,
                chars=int(mean([r["chars"] for r in rows])), npass=round(mean([len(r["passages"]) for r in rows]), 1),
                ncomp=sum(r.get("computed") is not None for r in ans))
for p in sys.argv[1:]:
    rows = load(p)
    g = [r for r in rows if GAP.search(r["question"])]
    o = [r for r in rows if not GAP.search(r["question"])]
    print(p)
    print("  all ", agg(rows))
    print("  gap ", agg(g))
    print("  rest", agg(o))
