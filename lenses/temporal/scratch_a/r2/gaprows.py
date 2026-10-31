import json,re,sys
GAP = re.compile(r"how many (days|weeks|months)\b.*\b(apart|after|before|between|passed)|days? (apart|after|before)", re.I)
from core.data import gold
path, split = sys.argv[1], sys.argv[2]
skip = int(sys.argv[3]) if len(sys.argv) > 3 else 0
g=gold(split)
i=0
for l in open(f"{path}/{split}/per_question.jsonl"):
    r=json.loads(l)
    if not GAP.search(r["question"]): continue
    i+=1
    if i<=skip: continue
    gg=g[r["question_id"]]
    d=r.get("debug",{})
    print(f'{split} PA={r.get("PA")} HA={r.get("HA")} ALL={r.get("ALL")} ATR={r.get("ATR")} S={r.get("S",0):.0f} Sall={r.get("Sall",0):.0f} np={len(r["passages"])} cite={len(r.get("cite_plan") or [])} comp={r["computed"]} raw={d.get("computed_raw")} conf={d.get("conf")} gold={str(gg["answer"])[:40]!r} abst={gg["abstain"]} ap={r.get("abstain_p")}')
    print("    ", r["question"][:150])
    for p in d.get("picks",[]): print("      ", p)
