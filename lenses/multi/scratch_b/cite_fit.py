"""Offline cite-rule analysis from a sweep's per_question.jsonl (debug['sess'] = sid -> [first_rank, rr_first, label,
n_top40, rr_max]). Evaluates simple cite rules against gold evidence (dev/dev200 only).
    .venv/bin/python -m lenses.multi.scratch_b.cite_fit runs/r1-multi-b/multi/b_sweep/sweep/dev [more dirs]"""
import json
import sys
from pathlib import Path

from core.data import gold


def f1(c, G):
    c, G = set(c), set(G)
    if not c or not G:
        return 0.0
    tp = len(c & G)
    return 2 * tp / (len(c) + len(G))


def rules():
    for d in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
        for mx in (3, 4, 5, 6):
            for mn in (1, 2):
                yield f"rel{d}_mx{mx}_mn{mn}", (lambda S, d=d, mx=mx, mn=mn: _rel(S, d, mx, mn))
    for k in (2, 3, 4):
        yield f"top{k}", (lambda S, k=k: [s for s, _ in sorted(S.items(), key=lambda x: x[1][0])][:k])
    for t in (-4, -3, -2, -1, 0, 1):
        for mn in (1, 2):
            yield f"abs{t}_mn{mn}", (lambda S, t=t, mn=mn: _abs(S, t, mn))


def _rel(S, d, mx, mn):
    order = sorted(S, key=lambda s: -S[s][4])
    if not order:
        return []
    top = S[order[0]][4]
    out = [s for s in order if S[s][4] >= top - d][:mx]
    return out if len(out) >= mn else order[:mn]


def _abs(S, t, mn):
    order = sorted(S, key=lambda s: -S[s][4])
    out = [s for s in order if S[s][4] >= t][:6]
    return out if len(out) >= mn else order[:mn]


def main(dirs):
    for d in dirs:
        rows = [json.loads(l) for l in open(Path(d) / "per_question.jsonl")]
        split = "dev200" if d.rstrip("/").endswith("dev200") else "dev"
        g = gold(split)
        rows = [r for r in rows if not r.get("abstain_gold") and "debug" in r and r["question_id"] in g]
        cur = sum(r["CF1"] for r in rows) / len(rows)
        print(f"{d}: n={len(rows)} current CF1={cur:.3f}")
        res = []
        for name, fn in rules():
            v = sum(f1(fn(r["debug"]["sess"]), g[r["question_id"]]["evidence"]) for r in rows) / len(rows)
            res.append((v, name))
        for v, name in sorted(res, reverse=True)[:12]:
            print(f"   {name:22} {v:.3f}")
        # oracle: cite exactly gold-in-pack
        orc = sum(f1([s for s in r["debug"]["sess"] if s in g[r["question_id"]]["evidence"]],
                     g[r["question_id"]]["evidence"]) for r in rows) / len(rows)
        print(f"   oracle(gold in pack)   {orc:.3f}")
        # gold session rank by rr_max
        ranks = []
        for r in rows:
            S = r["debug"]["sess"]
            order = sorted(S, key=lambda s: -S[s][4])
            G = g[r["question_id"]]["evidence"]
            ranks += [order.index(s) for s in G if s in order]
        import collections
        c = collections.Counter(min(x, 10) for x in ranks)
        print("   gold-session rank by rr_max:", sorted(c.items()))


if __name__ == "__main__":
    main(sys.argv[1:])


def combo(S, k, d, mx):
    by_rank = sorted(S, key=lambda s: S[s][0])
    by_rr = sorted(S, key=lambda s: -S[s][4])
    if not by_rr:
        return []
    top = S[by_rr[0]][4]
    out = by_rank[:k]
    for s in by_rr:
        if s not in out and S[s][4] >= top - d and len(out) < mx:
            out.append(s)
    return out


def combo_main(dirs):
    for dd in dirs:
        rows = [json.loads(l) for l in open(Path(dd) / "per_question.jsonl")]
        split = "dev200" if dd.rstrip("/").endswith("dev200") else "dev"
        g = gold(split)
        rows = [r for r in rows if not r.get("abstain_gold") and "debug" in r and r["question_id"] in g]
        res = []
        for k in (2, 3):
            for d in (0.5, 1.0, 1.5, 2.0, 3.0):
                for mx in (3, 4, 5):
                    v = sum(f1(combo(r["debug"]["sess"], k, d, mx), g[r["question_id"]]["evidence"]) for r in rows)
                    res.append((v / len(rows), f"combo_k{k}_d{d}_mx{mx}"))
        print(dd)
        for v, n in sorted(res, reverse=True)[:8]:
            print(f"   {n:24} {v:.3f}")
