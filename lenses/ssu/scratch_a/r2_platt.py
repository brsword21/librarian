"""Platt scaling of abstain_p on pooled rows: p' = sig(a*logit(p)+c); grid search log-loss. Prints AUC + bins."""
import json, math, sys
rows = []
for d in sys.argv[1:]:
    rows += [json.loads(l) for l in open(d + "/per_question.jsonl")]
y = [1 if r.get("abstain_gold") else 0 for r in rows]
lg = lambda p: math.log(min(max(p, 1e-4), 1 - 1e-4) / (1 - min(max(p, 1e-4), 1 - 1e-4)))
sig = lambda x: 1 / (1 + math.exp(-x))
z = [lg(r["abstain_p"]) for r in rows]
def ll(a, c):
    s = 0
    for zz, yy in zip(z, y):
        p = min(max(sig(a * zz + c), 1e-6), 1 - 1e-6); s -= yy * math.log(p) + (1 - yy) * math.log(1 - p)
    return s / len(y)
base = ll(1, 0)
best = min(((ll(a / 10, c / 4), a / 10, c / 4) for a in range(1, 21) for c in range(-24, 9)))
print(f"n={len(y)} pos={sum(y)} logloss raw={base:.3f}  platt best={best[0]:.3f} a={best[1]} c={best[2]}")
a, c = best[1], best[2]
for th in (0.3, 0.5, 0.7):
    sel = [yy for zz, yy in zip(z, y) if sig(a * zz + c) >= th]
    print(f"  p'>={th}: n={len(sel)} pos={sum(sel)}")
