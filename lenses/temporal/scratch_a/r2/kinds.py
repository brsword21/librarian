import json,re,collections,sys
from statistics import mean
sys.path.insert(0,".")
from lenses.temporal import a_calendar as A
GAP = re.compile(r"how many (days|weeks|months)\b.*\b(apart|after|before|between|passed)|days? (apart|after|before)", re.I)
split=sys.argv[1]; vs=sys.argv[2:]
runs={v:{json.loads(l)["question_id"]:json.loads(l) for l in open(f"runs/r2-temporal-a/temporal/{v}/{split}/per_question.jsonl")} for v in vs}
first=runs[vs[0]]
grp=collections.defaultdict(list)
for k,x in first.items():
    if x.get("abstain_gold"): continue
    qp=A.parse_question(x["question"])
    kind=("GAP:" if GAP.search(x["question"]) else "")+qp.kind+("" if qp.events else "-noev")
    grp[kind].append(k)
for kind,ks in sorted(grp.items()):
    print(f"{split} {kind:16s} n={len(ks):3d} "+" | ".join(f"{v.split('/')[-1]} S={mean(runs[v][k]['S'] for k in ks):.1f} Sall={mean(runs[v][k]['Sall'] for k in ks):.1f} PA={mean(runs[v][k]['PA'] for k in ks):.2f} np={mean(len(runs[v][k]['passages']) for k in ks):.1f}" for v in vs))
