"""Scratch r3: AUC of abstention features recorded by b_r3_ssu (debug) on routed runs, pooled over the given runs.
    .venv/bin/python -m lenses.ssu.scratch_b.r3_abst RUN_DIR [RUN_DIR ...]
"""
import json
import math
import sys


def auc(pos, neg):
    if not pos or not neg:
        return float("nan")
    w = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return w / (len(pos) * len(neg))


rows = []
for d in sys.argv[1:]:
    for l in open(d + "/per_question.jsonl"):
        r = json.loads(l)
        dbg = r.get("debug") or {}
        if dbg.get("route_final", "ssu") != "ssu" or dbg.get("z_sent") is None:
            continue
        rows.append((r["abstain_gold"], dbg, r["abstain_p"], d.split("/")[-1]))
print(len(rows), "rows,", sum(a for a, *_ in rows), "unanswerable")
feats = {
    "ab_r3rn": lambda d: d["ab_r3rn"],
    "-u_best": lambda d: -d["u_best"],
    "-sent_best": lambda d: -d["sent_best"],
    "-z_user": lambda d: -d["z_user"],
    "-z_sent": lambda d: -d["z_sent"],
    "-gap2": lambda d: -d["gap2"],
    "-(sent-mu)": lambda d: -(d["sent_best"] - d["pool_mu"]),
}
for split in sorted({s for *_, s in rows}) + ["pooled"]:
    R = [r for r in rows if split == "pooled" or r[3] == split]
    out = []
    for k, f in feats.items():
        pos = [f(d) for a, d, *_ in R if a]
        neg = [f(d) for a, d, *_ in R if not a]
        out.append(f"{k}={auc(pos, neg):.3f}")
    # mixes
    for w in (0.25, 0.5, 0.75):
        def mix(d, w=w):
            pz = 1 / (1 + math.exp(-(-1.2 * d["z_sent"] + 2.5)))
            return (1 - w) * d["ab_r3rn"] + w * pz
        pos = [mix(d) for a, d, *_ in R if a]
        neg = [mix(d) for a, d, *_ in R if not a]
        out.append(f"mix{w}={auc(pos, neg):.3f}")
    print(split, len(R), " ".join(out))
