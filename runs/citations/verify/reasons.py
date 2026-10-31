import json, sys
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, ".")
import core.paths
from reactorq import attribution as A
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
D="runs/citations/"
load=lambda n:[json.loads(l) for l in open(D+f"feats_{n}.jsonl")]
dev,d200=load("dev"),load("dev200")
for qs in (dev,d200):
    for q in qs:
        for r in q["rows"]:
            r["x"]=[float(r[f])/(10.0 if f.startswith("ce_") else 1.0) for f in A.FEATURES]
X=np.array([r["x"] for q in dev for r in q["rows"]]); y=np.array([r["label"] for q in dev for r in q["rows"]])
g=np.array([q["qid"] for q in dev for _ in q["rows"]]); cvp=np.zeros(len(y))
for tr,te in GroupKFold(5).split(X,y,g):
    cvp[te]=LogisticRegression(C=0.1,max_iter=2000,fit_intercept=False).fit(X[tr],y[tr]).predict_proba(X[te])[:,1]
i=0
for q in dev:
    for r in q["rows"]: r["p"]=cvp[i]; i+=1
for q in d200:
    for r in q["rows"]: r["p"]=A.prob(r["x"])
def spec(ans):
    import re
    from score import normalize
    toks=normalize(ans).split()
    content=[t for t in toks if not t.isdigit() and t not in A._STOP and len(t)>=3]
    return len(content)>=2 or any(t.replace(".","").isdigit() and len(t.replace(".",""))>=4 for t in toks)
for name,qs in (("dev(cv)",dev),("dev200",d200)):
    stats=defaultdict(lambda:[0,0])
    for scen in ("top1","none"):
        for q in qs:
            rows=q["rows"]; cont=[r for r in rows if r["contains"]]
            cited=[] if scen=="none" else ([max(cont,key=lambda r:r["ce_qa"])["id"]] if cont else [])
            probs=[r["p"] for r in rows]
            out=A.decide(rows,cited,probs)
            for r in rows:
                if r["id"] in out and r["id"] not in cited:
                    if r["plan_comp"]: why="plan_comp"
                    elif r["contains"] and spec(q["answer"]): why="contains,specific(>=2 words/4-digit)"
                    elif r["contains"]: why="contains,1-word/short"
                    elif r["num_match"]: why="num_match ONLY (number token, phrase absent)"
                    else: why="?"
                    k=(scen,q["route"],why); stats[k][0]+=1; stats[k][1]+=r["label"]
    print("==",name)
    for k,(n,gd) in sorted(stats.items()): print(f"  {k}: added {n}, gold {gd}")

# examples of num_match-only adds (top1 scenario, dev CV)
import re
from score import normalize
packs={json.loads(l)["question_id"]:json.loads(l) for l in open(D+"dev_packs.jsonl")}
shown=0
for q in dev:
    rows=q["rows"]; cont=[r for r in rows if r["contains"]]
    cited=[max(cont,key=lambda r:r["ce_qa"])["id"]] if cont else []
    out=A.decide(rows,cited,[r["p"] for r in rows])
    for r in rows:
        if r["id"] in out and r["id"] not in cited and r["num_match"] and not r["contains"] and not r["plan_comp"] and q["route"] in ("multi","temporal"):
            pk=packs[q["qid"]]; txt=next(p["text"] for p in pk["passages"] if p["id"]==r["id"])
            n=A._num(q["answer"])
            m=re.search(r"(?<![\d.])"+re.escape(n)+r"(?![\d.])", txt.replace(",",""))
            ctx=txt.replace(",","")[max(0,m.start()-110):m.start()+80].replace("\n"," ") if m else "?"
            print(f"[{q['route']}] gold={r['label']} p={r['p']:.2f} Q={pk['question'][:70]!r} A={q['answer']!r}\n     ...{ctx}...")
            shown+=1
    if shown>=16: break
