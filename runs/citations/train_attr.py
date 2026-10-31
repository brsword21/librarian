"""Fit the evidence-attribution model of reactorq/attribution.py.

    .venv/bin/python runs/citations/train_attr.py feats      # features for dev / dev200 / e1b -> runs/citations/feats_*.jsonl
    .venv/bin/python runs/citations/train_attr.py fit        # CV on dev, policy search, dev200 + e1b check, report numbers
    .venv/bin/python runs/citations/train_attr.py fit --write  # also writes COEF / THRESHOLD / MAX_ADD / FLOOR into the module
Packs: runs/citations/{dev,dev200}_packs.jsonl (reactorq.build_packs, configs/best.json = v3), e1b: runs/reactor/e1b_*.
Training proxy: the gold answer (first alias) plays Reactor's answer; label = session in gold evidence.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import core.paths  # noqa: F401,E402
from score import aliases, evidence_f1  # noqa: E402

from core.data import gold, read_jsonl  # noqa: E402
from reactorq import attribution as A  # noqa: E402

D = Path(__file__).resolve().parent
ROOT = D.parents[1]


def proxy_answer(g: dict) -> str:
    al = aliases(g["answer"])
    return al[1] if len(al) > 1 else g["answer"]


def reactor_rows():
    """e1b: real Reactor answers + citations (answered, non-abstained) and the rest as F1 0."""
    best = {}
    for r in read_jsonl(ROOT / "runs/reactor/e1b_results.jsonl"):
        if r.get("status") == "answered" or best.get(r["question_id"], {}).get("status") != "answered":
            best[r["question_id"]] = r
    out = {}
    for qid, r in best.items():
        ok = r.get("status") == "answered" and str(r.get("abstained")) not in ("True", "true") and r.get("answer")
        c = r.get("citations") or []
        c = ast.literal_eval(c) if isinstance(c, str) else c
        out[qid] = {"answered": bool(ok), "answer": A.strip_labels(r.get("answer") or "") if ok else "",
                    "citations": [x["id"] for x in c] if ok else []}
    return out


def feats(argv):
    jobs = [("dev", ROOT / "runs/citations/dev_packs.jsonl"), ("dev200", ROOT / "runs/citations/dev200_packs.jsonl"),
            ("e1b", ROOT / "runs/reactor/e1b_packs.jsonl")]
    rr = reactor_rows()
    for name, path in jobs:
        g = gold("dev" if name == "e1b" else name)
        out = []
        for pk in read_jsonl(path):
            gg = g[pk["question_id"]]
            if gg["abstain"]:
                continue
            if name == "e1b":
                r = rr.get(pk["question_id"]) or {"answered": False, "answer": "", "citations": []}
                ans, cited = r["answer"], r["citations"]
            else:
                r, ans, cited = None, proxy_answer(gg), None
            rows = A.session_features(pk["question"], ans, pk, set(cited or []), use_ce=True) if ans else []
            for x in rows:
                x["label"] = int(x["id"] in gg["evidence"])
            out.append({"qid": pk["question_id"], "type": gg["question_type"], "route": pk["route"],
                        "gold": gg["evidence"], "plan": pk.get("cite_plan") or [], "computed": pk.get("computed"),
                        "answer": ans, "reactor": r, "rows": rows,
                        "pack_ids": [p["id"] for p in pk["passages"]]})
        (D / f"feats_{name}.jsonl").write_text("".join(json.dumps(o) + "\n" for o in out))
        print(name, len(out), "questions", sum(len(o["rows"]) for o in out), "sessions")


# ---- policies / baselines --------------------------------------------------------------------------------------------
def sim_cited(q, scen):
    rows = q["rows"]
    if scen == "real":
        return list(q["reactor"]["citations"]) if q["reactor"] and q["reactor"]["answered"] else None
    if scen == "none":
        return []
    cont = [r for r in rows if r["contains"]]
    if scen == "contains":                     # task spec: cited = sessions containing the answer
        return [r["id"] for r in cont]
    if scen == "top1":                         # Reactor under-cites: the single best containing session
        return [max(cont, key=lambda r: r["ce_qa"])["id"]] if cont else []
    raise ValueError(scen)


def finalize_rules(q, cited, ku=True):
    """reactorq/finalize.py attribute(): fill-missing + ku-chain."""
    cites = list(cited)
    if not cites:
        sup = [r["id"] for r in q["rows"] if r["contains"]]
        if not sup and A.computed_matches(q["answer"], q["computed"]):
            sup = list(q["plan"])
        cites = sup
    if ku:
        cites = A.ku_chain({"route": q["route"], "cite_plan": q["plan"]}, cites)
    return cites


def evaluate(qs, scen, method, probs=None, pol=None, ku=True):
    f1s = []
    for q in qs:
        cited = sim_cited(q, scen)
        if cited is None or not q["answer"]:      # no answer from Reactor -> F1 0 whatever we cite
            f1s.append(0.0)
            continue
        if method == "reactor":
            c = cited
        elif method == "finalize":
            c = finalize_rules(q, cited, ku)
        elif method == "plan":
            c = list(q["plan"])
        elif method == "model":
            c = A.decide(q["rows"], cited, probs[q["qid"]], *pol)
            if ku:
                c = A.ku_chain({"route": q["route"], "cite_plan": q["plan"]}, c)
        f1s.append(evidence_f1(c, q["gold"]))
    return float(np.mean(f1s)) if f1s else 0.0


def by_type(qs, scen, method, probs=None, pol=None, ku=True):
    g = defaultdict(list)
    for q in qs:
        g[q["type"]].append(q)
    return {t: (len(v), evaluate(v, scen, method, probs, pol, ku)) for t, v in sorted(g.items())}


def XY(qs):
    X = np.array([r["x"] for q in qs for r in q["rows"]])
    y = np.array([r["label"] for q in qs for r in q["rows"]])
    return X, y


def fit(argv):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    load = lambda n: [json.loads(l) for l in open(D / f"feats_{n}.jsonl")]
    dev, d200, e1b = load("dev"), load("dev200"), load("e1b")
    # recompute x from raw features (lets FEATURES change without rebuilding CE scores)
    for qs in (dev, d200, e1b):
        for q in qs:
            for r in q["rows"]:
                r["x"] = [float(r[f]) / (10.0 if f.startswith("ce_") else 1.0) for f in A.FEATURES]
    drop = [a for a in argv if a.startswith("--drop=")]
    if drop:
        dropped = drop[0].split("=", 1)[1].split(",")
        keep = [i for i, f in enumerate(A.FEATURES) if f not in dropped]
        for qs in (dev, d200, e1b):
            for q in qs:
                for r in q["rows"]:
                    r["x"] = [r["x"][i] for i in keep]
    feats_used = [f for f in A.FEATURES if not drop or f not in dropped]
    scens = ["none", "contains", "top1"]
    pols = [(t, k, tf, kf) for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01) for k in (1, 2, 3)
            for tf in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8) for kf in (1, 2, 3, 5)]
    groups = np.array([q["qid"] for q in dev for _ in q["rows"]])
    X, y = XY(dev)
    best = None
    for C in (0.1, 0.3, 1.0, 3.0):
        cvp = np.zeros(len(y))
        for tr, te in GroupKFold(5).split(X, y, groups):
            m = LogisticRegression(C=C, max_iter=2000, fit_intercept=False).fit(X[tr], y[tr])
            cvp[te] = m.predict_proba(X[te])[:, 1]
        probs, i = {}, 0
        for q in dev:
            probs[q["qid"]] = list(cvp[i:i + len(q["rows"])])
            i += len(q["rows"])
        for pol in pols:
            s = np.mean([evaluate(dev, sc, "model", probs, pol) for sc in scens])
            if best is None or s > best[0]:
                best = (s, C, pol, probs)
    s, C, pol, cvprobs = best
    m = LogisticRegression(C=C, max_iter=2000, fit_intercept=False).fit(X, y)
    coef = [float(c) for c in m.coef_[0]]
    pr = lambda qs: {q["qid"]: [A.prob(r["x"], coef) for r in q["rows"]] for q in qs}
    res = {"C": C, "policy": {"threshold": pol[0], "max_add": pol[1], "fill_threshold": pol[2], "fill_max": pol[3]},
           "features": feats_used, "coef": dict(zip(feats_used, [round(c, 4) for c in coef]))}
    table = {}
    for name, qs, probs, sc_list in (("dev_cv", dev, cvprobs, scens), ("dev200", d200, pr(d200), scens),
                                     ("e1b_real", e1b, pr(e1b), ["real"])):
        for sc in sc_list:
            row = {}
            for meth in ("reactor", "finalize", "plan", "model"):
                row[meth] = round(evaluate(qs, sc, meth, probs, pol), 4)
            row["model_noku"] = round(evaluate(qs, sc, "model", probs, pol, ku=False), 4)
            row["n"] = len(qs)
            row["by_type_model"] = {t: (n, round(v, 3)) for t, (n, v) in by_type(qs, sc, "model", probs, pol).items()}
            row["by_type_finalize"] = {t: (n, round(v, 3)) for t, (n, v) in by_type(qs, sc, "finalize").items()}
            table[f"{name}/{sc}"] = row
    # e1b restricted to answered questions
    ans = [q for q in e1b if q["reactor"] and q["reactor"]["answered"]]
    pe = pr(ans)
    table["e1b_real/answered_only"] = {m_: round(evaluate(ans, "real", m_, pe, pol), 4)
                                       for m_ in ("reactor", "finalize", "plan", "model")} | {"n": len(ans)}
    # e1b changes
    changes = []
    for q in ans:
        c0 = q["reactor"]["citations"]
        c1 = A.decide(q["rows"], c0, pe[q["qid"]], *pol)
        c1 = A.ku_chain({"route": q["route"], "cite_plan": q["plan"]}, c1)
        if c1 != c0:
            changes.append({"qid": q["qid"], "type": q["type"], "route": q["route"], "answer": q["answer"][:60],
                            "before": c0, "after": c1, "gold": q["gold"],
                            "f1": [round(evidence_f1(c0, q["gold"]), 3), round(evidence_f1(c1, q["gold"]), 3)]})
    res["table"], res["e1b_changes"] = table, changes
    # sensitivity: F1 by threshold for dev cv (k, floor fixed)
    res["sweep_threshold"] = {t: [round(evaluate(dev, sc, "model", cvprobs, (t, pol[1], pol[2], pol[3])), 4)
                                  for sc in scens] for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01)}
    res["sweep_fill"] = {t: round(evaluate(dev, "none", "model", cvprobs, (pol[0], pol[1], t, pol[3])), 4)
                         for t in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)}
    out = D / ("fit_result.json" if not drop else "fit_result_drop.json")
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "e1b_changes"}, indent=1)[:6000])
    print("e1b changes:", json.dumps(changes, indent=1))
    if "--write" in argv and not drop:
        src = (ROOT / "reactorq/attribution.py").read_text()
        src = re.sub(r"^COEF = .*$", "COEF = [" + ", ".join(f"{c:.4f}" for c in coef) + "]", src, flags=re.M)
        src = re.sub(r"^THRESHOLD = [^ ]*", f"THRESHOLD = {pol[0]}", src, flags=re.M)
        src = re.sub(r"^MAX_ADD = [^ ]*", f"MAX_ADD = {pol[1]}", src, flags=re.M)
        src = re.sub(r"^FILL_THRESHOLD = [^ ]*", f"FILL_THRESHOLD = {pol[2]}", src, flags=re.M)
        src = re.sub(r"^FILL_MAX = [^ ]*", f"FILL_MAX = {pol[3]}", src, flags=re.M)
        (ROOT / "reactorq/attribution.py").write_text(src)
        print("wrote coefficients into reactorq/attribution.py")


if __name__ == "__main__":
    {"feats": feats, "fit": fit}[sys.argv[1]](sys.argv[2:])
