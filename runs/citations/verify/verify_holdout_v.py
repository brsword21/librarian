"""Honest hold-out check of the learned attribution vs simple rules. Read-only on project files.
Run from librarian/: .venv/bin/python <this>"""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd()))
import core.paths  # noqa: F401
from score import evidence_f1  # kit
from sklearn.linear_model import LogisticRegression

from reactorq import attribution as A
from reactorq import finalize as CUR

spec = importlib.util.spec_from_file_location("fprop", __import__('os').path.join(__import__('os').path.dirname(__file__), 'finalize_verified.py'))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

D = Path("runs/citations")
load = lambda n: [json.loads(l) for l in open(D / f"feats_{n}.jsonl")]
dev, d200, e1b = load("dev"), load("dev200"), load("e1b")
for qs in (dev, d200, e1b):
    for q in qs:
        for r in q["rows"]:
            r["x"] = [float(r[f]) / (10.0 if f.startswith("ce_") else 1.0) for f in A.FEATURES]
packs = {}
for f in ("runs/citations/dev_packs.jsonl", "runs/citations/dev200_packs.jsonl"):
    packs[f] = {json.loads(l)["question_id"]: json.loads(l) for l in open(f)}
e1b_packs = {}
for l in open("runs/reactor/e1b_packs.jsonl"):
    p = json.loads(l)
    e1b_packs.setdefault(p["pack_hash"], p)
    e1b_packs.setdefault(p["question_id"], p)
e1b_res = {}
for l in open("runs/reactor/e1b_results.jsonl"):
    r = json.loads(l)
    if r.get("status") == "answered" or e1b_res.get(r["question_id"], {}).get("status") != "answered":
        e1b_res[r["question_id"]] = r

POL = (A.THRESHOLD, A.MAX_ADD, A.FILL_THRESHOLD, A.FILL_MAX)
print("module policy", POL, "C=0.1")


def sim_cited(q, scen):
    rows = q["rows"]
    if scen == "real":
        return list(q["reactor"]["citations"]) if q["reactor"] and q["reactor"]["answered"] else None
    if scen == "none":
        return []
    cont = [r for r in rows if r["contains"]]
    if scen == "contains":
        return [r["id"] for r in cont]
    if scen == "top1":
        return [max(cont, key=lambda r: r["ce_qa"])["id"]] if cont else []


def fit(qs, C=0.1):
    X = np.array([r["x"] for q in qs for r in q["rows"]])
    y = np.array([r["label"] for q in qs for r in q["rows"]])
    m = LogisticRegression(C=C, max_iter=2000, fit_intercept=False).fit(X, y)
    return [float(c) for c in m.coef_[0]]


def cites_for(q, scen, method, coef=None, pack=None, reply=""):
    cited = sim_cited(q, scen)
    if cited is None or not q["answer"]:
        return None
    if method == "own":
        return cited
    if method.startswith("model"):
        probs = [A.prob(r["x"], coef) for r in q["rows"]]
        c = A.decide(q["rows"], cited, probs, *POL)
        if method == "model":
            c = A.ku_chain({"route": q["route"], "cite_plan": q["plan"]}, c)
        return c
    if method.startswith("allsup"):                 # no model: add every support-rule session
        key = "support" if cited else "support_fill"
        c = list(cited) + [r["id"] for r in q["rows"] if r[key] and r["id"] not in cited]
        if method == "allsup":
            c = A.ku_chain({"route": q["route"], "cite_plan": q["plan"]}, c)
        return c
    pred = {"question_id": q["qid"], "abstain": False, "answer": q["answer"], "citations": list(cited)}
    if method == "cur":
        return CUR.attribute(pred, pack, True, True)[0]["citations"]
    if method == "rules":
        return R.attribute(pred, pack, True, True, reply=reply)[0]["citations"]
    if method == "rules_noreply":
        return R.attribute(pred, pack, True, True, reply="")[0]["citations"]
    if method == "rules_noku":
        return R.attribute(pred, pack, True, False, reply=reply)[0]["citations"]
    raise ValueError(method)


def evaluate(qs, scen, method, coef=None, packmap=None, by_type=False):
    f1s, bt, added, added_gold = [], defaultdict(list), 0, 0
    for q in qs:
        pack = reply = None
        if packmap is not None:
            pack = packmap.get(q["qid"])
        if scen == "real":
            rr = e1b_res.get(q["qid"], {})
            pack = e1b_packs.get(rr.get("pack_hash")) or e1b_packs.get(q["qid"])
            reply = rr.get("reply") or ""
        c = cites_for(q, scen, method, coef, pack, reply or "")
        f = 0.0 if c is None else evidence_f1(c, q["gold"])
        if c is not None:
            base = sim_cited(q, scen)
            new = [s for s in c if s not in base]
            added += len(new)
            added_gold += sum(s in q["gold"] for s in new)
        f1s.append(f)
        bt[q["type"]].append(f)
    out = round(float(np.mean(f1s)), 4)
    if by_type:
        return out, {t: round(float(np.mean(v)), 3) for t, v in sorted(bt.items())}, f"{added_gold}/{added}"
    return out, f"{added_gold}/{added}"


d200_q = {q["qid"] for q in d200}
e1b_q = {q["qid"] for q in e1b}
print("dev200 qids in dev feats:", sum(q["qid"] in d200_q for q in dev), "/", len(d200))
print("e1b qids in dev feats:", sum(q["qid"] in e1b_q for q in dev), "/", len(e1b))

coef_full = list(A.COEF)
coef_ex200 = fit([q for q in dev if q["qid"] not in d200_q])
coef_exe1b = fit([q for q in dev if q["qid"] not in e1b_q])
coef_check = fit(dev)
print("refit on full dev reproduces module COEF:", np.allclose(coef_check, coef_full, atol=1e-3))

# dev200 not-in-dev-training: also evaluate the dev questions that are NOT in dev200 with ex200 coefficients? no: use CV.
print("\n=== dev200 (125 q, same questions as dev) ===")
for scen in ("none", "contains", "top1"):
    row = {}
    for name, meth, coef in (("own", "own", None), ("cur", "cur", None), ("rules", "rules_noreply", None),
                             ("allsup(no model)", "allsup", None), ("model[full-dev fit, LEAKY]", "model", coef_full),
                             ("model[fit excl. dev200 q]", "model", coef_ex200),
                             ("model_noku[excl]", "model_noku", coef_ex200), ("allsup_noku", "allsup_noku", None)):
        row[name] = evaluate(d200, scen, meth, coef, packs["runs/citations/dev200_packs.jsonl"])
    print(scen, json.dumps(row))

print("\n=== dev, 5-fold grouped CV for model; rules have no fitted params ===")
from sklearn.model_selection import GroupKFold
X = np.array([r["x"] for q in dev for r in q["rows"]])
y = np.array([r["label"] for q in dev for r in q["rows"]])
groups = np.array([q["qid"] for q in dev for _ in q["rows"]])
cvp = np.zeros(len(y))
for tr, te in GroupKFold(5).split(X, y, groups):
    m = LogisticRegression(C=0.1, max_iter=2000, fit_intercept=False).fit(X[tr], y[tr])
    cvp[te] = m.predict_proba(X[te])[:, 1]
i = 0
cvprob = {}
for q in dev:
    cvprob[q["qid"]] = list(cvp[i:i + len(q["rows"])])
    i += len(q["rows"])


def eval_cv(qs, scen, ku=True):
    f1s, ad, ag = [], 0, 0
    for q in qs:
        cited = sim_cited(q, scen)
        if cited is None or not q["answer"]:
            f1s.append(0.0)
            continue
        c = A.decide(q["rows"], cited, cvprob[q["qid"]], *POL)
        if ku:
            c = A.ku_chain({"route": q["route"], "cite_plan": q["plan"]}, c)
        new = [s for s in c if s not in cited]
        ad += len(new); ag += sum(s in q["gold"] for s in new)
        f1s.append(evidence_f1(c, q["gold"]))
    return round(float(np.mean(f1s)), 4), f"{ag}/{ad}"


for scen in ("none", "contains", "top1"):
    row = {"own": evaluate(dev, scen, "own"), "cur": evaluate(dev, scen, "cur", None, packs["runs/citations/dev_packs.jsonl"]),
           "rules": evaluate(dev, scen, "rules_noreply", None, packs["runs/citations/dev_packs.jsonl"]),
           "allsup": evaluate(dev, scen, "allsup"), "allsup_noku": evaluate(dev, scen, "allsup_noku"),
           "model_cv": eval_cv(dev, scen), "model_cv_noku": eval_cv(dev, scen, ku=False)}
    print(scen, json.dumps(row))

print("\n=== dev (excluding dev200 questions), CV model ===")
dev_x = [q for q in dev if q["qid"] not in d200_q]
for scen in ("top1",):
    print(scen, "allsup", evaluate(dev_x, scen, "allsup"), "rules", evaluate(dev_x, scen, "rules_noreply", None, packs["runs/citations/dev_packs.jsonl"]),
          "model_cv", eval_cv(dev_x, scen))

print("\n=== e1b real (16 answerable) ===")
ans = [q for q in e1b if q["reactor"] and q["reactor"]["answered"]]
for name, meth, coef in (("own", "own", None), ("cur", "cur", None), ("rules (rec2, with replies)", "rules", None),
                         ("rules no reply-rows", "rules_noreply", None), ("rules no ku", "rules_noku", None),
                         ("allsup", "allsup", None), ("model[full-dev fit, LEAKY]", "model", coef_full),
                         ("model[fit excl. e1b q]", "model", coef_exe1b)):
    a16 = evaluate(e1b, "real", meth, coef, by_type=True)
    a13 = evaluate(ans, "real", meth, coef)
    print(f"{name:32s} all16={a16[0]} answered13={a13[0]} added gold/added={a13[1]}  {a16[1]}")

# which e1b questions differ between methods
print("\nper-question e1b (answered):")
for q in ans:
    rr = e1b_res.get(q["qid"], {})
    pack = e1b_packs.get(rr.get("pack_hash")) or e1b_packs.get(q["qid"])
    line = []
    for meth, coef in (("own", None), ("cur", None), ("rules", None), ("allsup", None), ("model", coef_exe1b)):
        c = cites_for(q, "real", meth, coef, pack, rr.get("reply") or "")
        line.append(f"{meth}={evidence_f1(c, q['gold']):.2f}")
    print(f"  {q['qid']} {q['type'][:12]:12s} {q['route']:8s} {q['answer'][:40]!r:44s} " + " ".join(line))
