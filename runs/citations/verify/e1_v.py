import json, sys, importlib.util
sys.path.insert(0, ".")
import core.paths
from score import evidence_f1, normalize
from predictions import convert
from core.data import gold
from reactorq import attribution as A
from reactorq import finalize as CUR
import numpy as np
from sklearn.linear_model import LogisticRegression
spec=importlib.util.spec_from_file_location("fprop",__import__('os').path.join(__import__('os').path.dirname(__file__), 'finalize_verified.py')); R=importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
G=gold("dev")
dev=[json.loads(l) for l in open("runs/citations/feats_dev.jsonl")]
for name in ("e1","e1b"):
    res={}
    for l in open(f"runs/reactor/{name}_results.jsonl"):
        r=json.loads(l)
        if r.get("status")=="answered" or res.get(r["question_id"],{}).get("status")!="answered": res[r["question_id"]]=r
    packs={}
    for l in open(f"runs/reactor/{name}_packs.jsonl"):
        p=json.loads(l); packs.setdefault(p["pack_hash"],p); packs.setdefault(p["question_id"],p)
    qids=set(res)
    tr=[q for q in dev if q["qid"] not in qids]
    X=np.array([[float(r[f])/(10.0 if f.startswith("ce_") else 1.0) for f in A.FEATURES] for q in tr for r in q["rows"]])
    y=np.array([r["label"] for q in tr for r in q["rows"]])
    coef_ex=[float(c) for c in LogisticRegression(C=0.1,max_iter=2000,fit_intercept=False).fit(X,y).coef_[0]]
    preds,_,_=convert(list(res.values()),{"agent","no-answer"},None)
    tot={k:[] for k in ("own","cur","rules","model_leaky","model_ex")}
    print("=====",name)
    for p in preds:
        g=G[p["question_id"]]
        if g["abstain"]: continue
        r=res[p["question_id"]]; pk=packs.get(r.get("pack_hash")) or packs.get(p["question_id"])
        if p["abstain"]:
            for k in tot: tot[k].append((0.0,False))
            continue
        ids=[x["id"] for x in pk["passages"]]
        c={}
        c["own"]=p["citations"]
        c["cur"]=CUR.attribute(p,pk,True,True)[0]["citations"]
        c["rules"]=R.attribute(p,pk,True,True,reply=r.get("reply") or "")[0]["citations"]
        c["model_leaky"]=A.attribute(p,pk,r)[0]
        old=A.COEF; A.COEF=coef_ex
        try: c["model_ex"]=A.attribute(p,pk,r)[0]
        finally: A.COEF=old
        for k in tot: tot[k].append((evidence_f1(c[k],g["evidence"]),True))
        lab=lambda L:[f"E{ids.index(s)+1}" for s in L]
        gl=lab([s for s in g["evidence"] if s in ids])
        print(f"{p['question_id']} [{pk['route']}] A={p['answer'][:45]!r} gold={gl} (+{len(g['evidence'])-len(gl)} not in pack) "+
              " ".join(f"{k}={lab(c[k])}:{evidence_f1(c[k],g['evidence']):.2f}" for k in c))
    for k,v in tot.items():
        a=[f for f,ok in v]; b=[f for f,ok in v if ok]
        print(f"  {k:12s} answerable={np.mean(a):.4f} (n={len(a)}) answered={np.mean(b):.4f} (n={len(b)})")
