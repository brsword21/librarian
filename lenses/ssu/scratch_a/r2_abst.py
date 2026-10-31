"""Abstention on pooled dev+dev200 routed-ssu rows: AUC of abstain_p vs top_logit; reliability of abstain_p bins;
grid of (bias, temp) for a calibrated logistic prior (log-loss)."""
import json, math, sys
rows = []
for d in sys.argv[1:]:
    rows += [json.loads(l) for l in open(d + "/per_question.jsonl")]
y = [1 if r.get("abstain_gold") else 0 for r in rows]
def auc(s):
    pos = [a for a, b in zip(s, y) if b]; neg = [a for a, b in zip(s, y) if not b]
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))
ap = [r["abstain_p"] for r in rows]; tl = [-r["debug"]["top_logit"] for r in rows]
print(f"n={len(rows)} pos={sum(y)}  AUC abstain_p={auc(ap):.3f}  AUC -top_logit={auc(tl):.3f}")
for lo, hi in ((0, .2), (.2, .5), (.5, .7), (.7, .8), (.8, .9), (.9, 1.01)):
    b = [yy for a, yy in zip(ap, y) if lo <= a < hi]
    print(f"  abstain_p in [{lo},{hi}): n={len(b)} pos={sum(b)}")
best = None
for bias in [x / 2 for x in range(-4, 13)]:
    for temp in (0.5, 1, 1.5, 2, 3):
        ll = 0
        for t, yy in zip(tl, y):
            pr = 1 / (1 + math.exp(-(t - bias) / temp)); pr = min(max(pr, 1e-6), 1 - 1e-6)
            ll -= yy * math.log(pr) + (1 - yy) * math.log(1 - pr)
        if best is None or ll < best[0]: best = (ll / len(y), bias, temp)
print("best logistic on -top_logit: logloss=%.3f bias=%.1f temp=%.1f" % best)
for r, yy in zip(rows, y):
    if yy: print(f"  POS ap={r['abstain_p']:.2f} top={r['debug']['top_logit']:5.1f} {r['type']:8s} {r['question'][:70]}")
hi = sorted([(r['abstain_p'], r['debug']['top_logit'], r['type'], r['question'][:70]) for r, yy in zip(rows, y) if not yy], reverse=True)[:12]
for h in hi: print(f"  NEG ap={h[0]:.2f} top={h[1]:5.1f} {h[2]:8s} {h[3]}")
