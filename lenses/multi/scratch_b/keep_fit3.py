"""Round 3: refit p(gold session) with fact-sentence CE features (fit on dev, hold out dev200).
    .venv/bin/python -m lenses.multi.scratch_b.keep_fit3"""
import json, math
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from core.data import gold
from lenses.multi.b_r3_full import feats2

RUN = "runs/r3-multi-b/multi/b_r3_full/ufull_fs/{}"


def load(split):
    g = gold(split)
    rows = []
    for l in open(Path(RUN.format(split)) / "per_question.jsonl"):
        r = json.loads(l)
        if r.get("abstain_gold") or r["question_id"] not in g or g[r["question_id"]]["abstain"]:
            continue
        r["G"] = set(g[r["question_id"]]["evidence"])
        rows.append(r)
    return rows


def f1(c, G):
    c = set(c)
    return 2 * len(c & G) / (len(c) + len(G)) if c else 0.0


def ordered(S):
    return sorted(S, key=lambda s: S[s]["r"])


def feats5(f):
    return [f["gap"], min(f["r"], 10), f["cov"], min(f["n40"], 10), math.log1p(f["first"])]


P5 = ((-0.3061, -0.3145, 0.961, 0.3231, -1.3884), 3.1546)


def prob(fe, coef, b):
    return lambda f: 1 / (1 + math.exp(-(b + sum(c * v for c, v in zip(coef, fe(f))))))


def both(rows, pf, tk, tc=0.35, mn=2, mx=8):
    pa = cfc = cfk = ns = 0
    lost = []
    for r in rows:
        S = r["debug"]["sess2"]
        o = ordered(S)
        p = [pf(S[s]) for s in o]
        k = [s for s, pi in zip(o, p) if pi >= tk][:mx]
        k = k if len(k) >= mn else o[:mn]
        c = [s for s, pi in zip(o, p) if pi >= tc and s in k]
        c = c if len(c) >= 2 else k[:2]
        ok = r["G"] <= set(k)
        pa += ok * (r["ATR"] >= 0.999 or not (r["G"] <= {x for x in S}))  # approx: PA if all gold sessions kept
        cfk += f1(k, r["G"]); cfc += f1(c, r["G"]); ns += len(k)
        if not ok:
            lost.append((r["question"][:60], [(S[g]["r"], round(pf(S[g]), 3), S[g].get("fs"), S[g].get("nfs")) if g in S else "OUT" for g in r["G"] - set(k)]))
    n = len(rows); ch = 1600 + 1300 * ns / n
    pen = 0.05 * ch / 16000
    return 100 * (0.65 * pa / n + 0.3 * cfc / n - pen), 100 * (0.65 * pa / n + 0.3 * cfk / n - pen), pa / n, ns / n, lost


dev, d200 = load("dev"), load("dev200")
X, y = [], []
for r in dev:
    S = r["debug"]["sess2"]
    for s in ordered(S)[:12]:
        X.append(feats2(S[s])); y.append(int(s in r["G"]))
X, y = np.array(X), np.array(y)
models = {"p5(v1)": prob(feats5, *P5)}
for C in (0.3, 1.0):
    clf = LogisticRegression(C=C, max_iter=5000).fit(X, y)
    print("C", C, "coef", np.round(clf.coef_[0], 4).tolist(), "b", round(float(clf.intercept_[0]), 4))
    models[f"p8 C={C}"] = prob(feats2, clf.coef_[0].tolist(), float(clf.intercept_[0]))
for name, pf in models.items():
    for tk in (0.05, 0.08, 0.1, 0.12, 0.15):
        a = both(dev, pf, tk); b = both(d200, pf, tk)
        print(f"{name:12} tk={tk:<5}| dev S {a[0]:.1f} Sall {a[1]:.1f} PA {a[2]:.3f} n {a[3]:.2f} | dev200 S {b[0]:.1f} Sall {b[1]:.1f} PA {b[2]:.3f} n {b[3]:.2f}")
for name in ("p5(v1)", "p8 C=1.0"):
    print("==", name, "lost at tk=0.08")
    for split, rows in (("dev", dev), ("dev200", d200)):
        for l in both(rows, models[name], 0.08)[4]:
            print("  ", split, l)
