"""Join role_probe features with per-question S of the ssu lens and the ssa lenses on routed-to-ssu questions and
score candidate role_guess rules by the routed-system gain (sum of S deltas / all questions of the split).
Usage: PYTHONPATH=. .venv/bin/python lenses/ssa/scratch_b/role_eval.py dev
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from core.paths import ROOT

HERE = Path(__file__).parent
N_ALL = {"dev": 526, "dev200": 125}


def load(path):
    out = {}
    p = ROOT / path / "per_question.jsonl"
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        r = json.loads(line)
        out[r["question_id"]] = r
    return out


def sig(x):
    return 1 / (1 + math.exp(-x))


def p_assistant(f, a=0.35, b=2.2, c=-1.0):
    """Logistic blend: CE margin (best assistant unit vs best user unit in the reranked pool) + 'no first person'."""
    return sig(a * max(-8.0, min(8.0, f["d_all"])) + b * (f["n_first"] == 0) + c)


def main(split="dev"):
    rows = [json.loads(x) for x in (HERE / f"role_probe_{split}.jsonl").read_text().splitlines()]
    ssu = load(f"runs/r2-ssa-b-role/ssu/a_struct/nb3t0/{split}")
    ssa_a = load(f"runs/r2-ssa-b-role/ssu/a_recsent/recqs_cf7/{split}")
    ssa_b = load(f"runs/r2-ssa-b-role/ssu/b_semantic/session10k1_rr/{split}")
    rules = {
        "nf0": lambda f: f["n_first"] == 0,
        "nf0_d>-2": lambda f: f["n_first"] == 0 and f["d_all"] > -2,
        "nf0_d>-4": lambda f: f["n_first"] == 0 and f["d_all"] > -4,
        "nf0|d>6": lambda f: f["n_first"] == 0 or f["d_all"] > 6,
        "(nf0&d>-4)|d>6": lambda f: (f["n_first"] == 0 and f["d_all"] > -4) or f["d_all"] > 6,
        "d>2": lambda f: f["d_all"] > 2,
        "d>4": lambda f: f["d_all"] > 4,
        "p>=0.5": lambda f: p_assistant(f) >= 0.5,
        "p>=0.7": lambda f: p_assistant(f) >= 0.7,
        "all": lambda f: True,
    }
    print(f"{split}: {len(rows)} routed-to-ssu questions, gold ssa {sum(r['type'].endswith('assistant') for r in rows)}")
    for name, ssa in (("A recqs_cf7", ssa_a), ("B session10k1_rr", ssa_b)):
        if not ssa:
            continue
        print(f"  ssa lens = {name}")
        for rn, rule in rules.items():
            tp = fp = fn = 0
            dS = dSall = 0.0
            for f in rows:
                qid = f["qid"]
                if qid not in ssu or qid not in ssa:
                    continue
                pos = f["type"].endswith("assistant")
                flag = rule(f)
                tp += flag and pos
                fp += flag and not pos
                fn += (not flag) and pos
                if flag:
                    s0, s1 = ssu[qid].get("S"), ssa[qid].get("S")
                    if s0 is not None and s1 is not None:
                        dS += s1 - s0
                        dSall += ssa[qid].get("Sall", s1) - ssu[qid].get("Sall", s0)
            print(f"    {rn:16s} TP={tp:3d} FP={fp:3d} FN={fn:3d}  routed dS={dS / N_ALL[split]:+.2f}"
                  f"  dSall={dSall / N_ALL[split]:+.2f}")
    # per-question deltas for flagged non-ssa (the cost side)
    print("  non-ssa questions flagged by nf0|d>6 (A lens S - ssu lens S):")
    for f in rows:
        if not f["type"].endswith("assistant") and (f["n_first"] == 0 or f["d_all"] > 6):
            qid = f["qid"]
            if qid in ssu and qid in ssa_a:
                print(f"    {f['type'][:10]} d={f['d_all']:+.1f} dS={ssa_a[qid].get('S', 0) - ssu[qid].get('S', 0):+.1f}"
                      f" {f['q'][:70]}")
    # AUC of p_assistant for ssa vs rest
    pos = [p_assistant(f) for f in rows if f["type"].endswith("assistant")]
    neg = [p_assistant(f) for f in rows if not f["type"].endswith("assistant")]
    if pos and neg:
        auc = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))
        print(f"  AUC p_assistant (ssa vs rest, routed-to-ssu) = {auc:.3f}")
    pos = [p_assistant(f) for f in rows if f["type"].endswith("assistant")]
    neg = [p_assistant(f) for f in rows if f["type"].endswith("user")]
    if pos and neg:
        auc = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))
        acc = (sum(p >= 0.5 for p in pos) + sum(n < 0.5 for n in neg)) / (len(pos) + len(neg))
        print(f"  ssa vs ssu only: AUC={auc:.3f} acc@0.5={acc:.3f} (n={len(pos)}+{len(neg)})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
