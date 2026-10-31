"""Offline fit of the session keep rule from b_tight debug['sess2'] features (dev/dev200 only).
    .venv/bin/python -m lenses.multi.scratch_b.keep_fit"""
import json, math
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from core.data import gold

RUN = "runs/r2-multi-b/multi/b_tight/s10m2/{}"
REF = "runs/r2-multi-b/multi/b_sweep/deep8_10k/{}"


def load(split):
    g = gold(split)
    ref = {json.loads(l)["question_id"]: json.loads(l) for l in open(Path(REF.format(split)) / "per_question.jsonl")}
    rows = []
    for l in open(Path(RUN.format(split)) / "per_question.jsonl"):
        r = json.loads(l)
        if r.get("abstain_gold") or r["question_id"] not in g:
            continue
        r["G"] = set(g[r["question_id"]]["evidence"])
        r["refPA"] = ref[r["question_id"]]["PA"]
        rows.append(r)
    return rows


def feats(f, nq):
    smax_gap = f["top"] - f["smax"] if f["smax"] > -50 else 15
    return [f["gap"], min(f["r"], 10), min(f["gn"], 8), f["cov"], min(f["n40"], 10), f["ft"],
            math.log1p(f["first"]), min(smax_gap, 15), f["top"], f["w4"]]


def f1(c, G):
    c = set(c)
    if not c:
        return 0.0
    return 2 * len(c & G) / (len(c) + len(G))


def evaluate(rows, keepfn, name):
    pa = cf = ns = 0
    for r in rows:
        S = r["debug"]["sess2"]
        k = keepfn(S)
        ok = r["G"] <= set(k)
        pa += r["refPA"] * ok
        cf += f1(k, r["G"])
        ns += len(k)
    n = len(rows)
    chars = 1600 + 1100 * ns / n
    s = 100 * (0.65 * pa / n + 0.30 * cf / n - 0.05 * chars / 16000)
    return s, pa / n, cf / n, ns / n


def ordered(S):
    return sorted(S, key=lambda s: S[s]["r"])


def rule_gap(D, mn, mx):
    def fn(S):
        o = ordered(S)
        n = sum(1 for s in o if S[s]["gap"] <= D)
        return o[:max(mn, min(mx, n))]
    return fn


def rule_model(clf, tau, mn, mx):
    def fn(S):
        o = ordered(S)
        X = np.array([feats(S[s], 0) for s in o])
        p = clf.predict_proba(X)[:, 1]
        k = [s for s, pi in zip(o, p) if pi >= tau][:mx]
        if len(k) < mn:
            k = k + [s for s in o if s not in k][:mn - len(k)]
        return k
    return fn


def train(rows):
    X, y = [], []
    for r in rows:
        S = r["debug"]["sess2"]
        for s in ordered(S)[:12]:
            X.append(feats(S[s], 0))
            y.append(int(s in r["G"]))
    clf = LogisticRegression(C=1.0, max_iter=2000)
    clf.fit(np.array(X), np.array(y))
    return clf


dev, d200 = load("dev"), load("dev200")
for name, rows in (("dev", dev), ("dev200", d200)):
    print(f"== {name} n={len(rows)}")
    for D, mn, mx in ((99, 8, 8), (8, 2, 8), (10, 2, 8), (7, 3, 8), (12, 2, 8), (10, 3, 8), (99, 3, 3), (99, 4, 4), (99, 5, 5)):
        print(f"   gap D={D} mn={mn} mx={mx}: S~%.1f PA~%.3f CF1all~%.3f sess=%.1f" % evaluate(rows, rule_gap(D, mn, mx), ""))
clf = train(dev)
print("coef", np.round(clf.coef_, 3), np.round(clf.intercept_, 3))
for tau in (0.08, 0.1, 0.12, 0.15, 0.2, 0.25, 0.3):
    for mn in (2, 3):
        a = evaluate(dev, rule_model(clf, tau, mn, 8), "")
        b = evaluate(d200, rule_model(clf, tau, mn, 8), "")
        print(f"   model(dev) tau={tau} mn={mn}: dev S~{a[0]:.1f} PA~{a[1]:.3f} CF~{a[2]:.3f} n={a[3]:.1f} | dev200 S~{b[0]:.1f} PA~{b[1]:.3f} CF~{b[2]:.3f} n={b[3]:.1f}")


# ---- pack keep (tau_k) vs cite (tau_c): S uses cite F1, Sall uses keep F1
def both(rows, clf, tk, tc, mn=2, mx=8, fe=feats):
    pa = cfc = cfk = ns = 0
    for r in rows:
        S = r["debug"]["sess2"]
        o = ordered(S)
        p = clf.predict_proba(np.array([fe(S[s], 0) for s in o]))[:, 1]
        k = [s for s, pi in zip(o, p) if pi >= tk][:mx]
        k = k if len(k) >= mn else o[:mn]
        c = [s for s, pi in zip(o, p) if pi >= tc and s in k]
        c = c if len(c) >= 2 else k[:2]
        pa += r["refPA"] * (r["G"] <= set(k))
        cfk += f1(k, r["G"]); cfc += f1(c, r["G"]); ns += len(k)
    n = len(rows); ch = 1600 + 1100 * ns / n
    pen = 0.05 * ch / 16000
    return 100 * (0.65 * pa / n + 0.3 * cfc / n - pen), 100 * (0.65 * pa / n + 0.3 * cfk / n - pen), pa / n, ns / n


print("\n tk    tc   | dev S  Sall  PA   n  | dev200 S Sall PA  n")
for tk in (0.03, 0.05, 0.08, 0.1, 0.15):
    for tc in (0.15, 0.25, 0.35):
        a = both(dev, clf, tk, tc); b = both(d200, clf, tk, tc)
        print(f" {tk:<5} {tc:<5}| {a[0]:.1f} {a[1]:.1f} {a[2]:.3f} {a[3]:.1f} | {b[0]:.1f} {b[1]:.1f} {b[2]:.3f} {b[3]:.1f}")

print("\nlost gold sessions at tk=0.08 (dev, dev200):")
for rows in (dev, d200):
    for r in rows:
        S = r["debug"]["sess2"]; o = ordered(S)
        p = clf.predict_proba(np.array([feats(S[s], 0) for s in o]))[:, 1]
        k = [s for s, pi in zip(o, p) if pi >= 0.08][:8]
        k = k if len(k) >= 2 else o[:2]
        lost = [g for g in r["G"] if g not in k]
        if lost and r["refPA"]:
            info = [(S[g]["r"], S[g]["gap"], S[g]["first"], S[g]["n40"], S[g]["cov"], round(float(p[o.index(g)]), 3)) if g in S else "OUT" for g in lost]
            print(f"  {r['question'][:70]:70} keep={len(k)} lost(r,gap,first,n40,cov,p)={info}")


def feats5(f, nq):
    return [f["gap"], min(f["r"], 10), f["cov"], min(f["n40"], 10), math.log1p(f["first"])]


X, y = [], []
for r in dev:
    S = r["debug"]["sess2"]
    for s in ordered(S)[:12]:
        X.append(feats5(S[s], 0)); y.append(int(s in r["G"]))
clf5 = LogisticRegression(C=1.0, max_iter=2000).fit(np.array(X), np.array(y))
print("\nfeats5 coef", np.round(clf5.coef_, 4).tolist(), np.round(clf5.intercept_, 4).tolist())
for tk in (0.05, 0.08, 0.1, 0.12, 0.15, 0.2):
    for mn in (2, 3):
        a = both(dev, clf5, tk, 0.35, mn=mn, fe=feats5); b = both(d200, clf5, tk, 0.35, mn=mn, fe=feats5)
        print(f" f5 tk={tk:<5} mn={mn}| dev S {a[0]:.1f} Sall {a[1]:.1f} PA {a[2]:.3f} n {a[3]:.1f} | dev200 S {b[0]:.1f} Sall {b[1]:.1f} PA {b[2]:.3f} n {b[3]:.1f}")
