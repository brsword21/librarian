"""Offline: core rules on the session-strength lists saved by a_prune (debug['strength'], top 25)."""
import json, sys
from core.data import gold

def f1(c, G):
    c, G = set(c), set(G)
    tp = len(c & G)
    return 2 * tp / (len(c) + len(G)) if c and G else 0.0

def rule(st, D, gap, extra, mn=2):
    order = sorted(st, key=lambda s: -st[s])
    top = st[order[0]]
    core = []
    for i, s in enumerate(order):
        if st[s] < top - D:
            break
        if i >= mn and gap and st[order[i - 1]] - st[s] >= gap:
            break
        core.append(s)
    core = core[:14]
    if len(core) < mn:
        core = order[:mn]
    return core + [s for s in order if s not in core][:extra]

for sp in ("dev", "dev200"):
    g = gold(sp)
    rows = [json.loads(l) for l in open(f"runs/r2-multi-a/multi/a_prune/b_ref/{sp}/per_question.jsonl")]
    rows2 = {json.loads(l)["question_id"]: json.loads(l) for l in open(f"runs/r2-multi-a/multi/a_prune/p8x1_dof/{sp}/per_question.jsonl")}
    res = []
    for D in (8, 10, 12):
        for gap in (0, 3, 4, 5, 6):
            for extra in (0, 1):
                pa = fa = n = 0
                for r in rows:
                    if r["abstain_gold"]:
                        continue
                    st = rows2[r["question_id"]]["debug"]["strength"]
                    G = set(g[r["question_id"]]["evidence"])
                    keep = set(rule(st, D, gap, extra))
                    ok = r["PA"] and G <= keep
                    pa += ok; fa += f1(keep, G); n += 1
                res.append((round(100 * (0.65 * pa / n + 0.3 * fa / n), 1), round(pa / n, 3), round(fa / n, 3), D, gap, extra))
    print(sp)
    for x in sorted(res, reverse=True)[:10]:
        print("  proxy=%s PA=%s F1all=%s D=%s gap=%s extra=%s" % x)
