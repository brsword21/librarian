"""Scratch: offline ranking experiments on the dumped features (no models).

    .venv/bin/python -m lenses.ssu.scratch_b.exp
For each scoring recipe: session P@1 (= CF1 of a top-1 cite_plan), session R@2/R@3, gold-unit rank, and how far below
the top the gold unit sits (logit margin).
"""
import math
import pickle
import statistics
from pathlib import Path

from core.index import HistoryIndex

HERE = Path(__file__).parent


def load(split):
    return pickle.load(open(HERE / f"feats_{split}.pkl", "rb"))


def zs(d, keys):
    v = [d[k] for k in keys]
    m, s = statistics.mean(v), (statistics.pstdev(v) or 1.0)
    return {k: (d[k] - m) / s for k in keys}


def rank_units(r, hx, depth=150, a_dense=0.0, a_bm=0.0, a_rrf=0.0):
    pool = r["hybrid"][:depth]
    rr = {u: r["rr"][u] for u in pool if u in r["rr"]}
    zd = zs(r["dense"], r["users"])
    zb = zs(r["bm25"], r["users"])
    hpos = {u: i for i, u in enumerate(r["hybrid"])}
    sc = {u: rr[u] + a_dense * zd[u] + a_bm * zb[u] + a_rrf * 60.0 / (60 + hpos[u]) for u in rr}
    return sorted(sc, key=lambda u: -sc[u]), sc


def sess_rank(units, sc, hx, lam=0.0):
    by = {}
    for u in units:
        by.setdefault(hx.units[u].session_id, []).append(sc[u])
    agg = {s: v[0] + (lam * max(0, v[1]) if len(v) > 1 else 0) for s, v in by.items()}
    return sorted(agg, key=lambda s: -agg[s]), agg


def evaluate(split, **kw):
    rows = load(split)
    p1 = r2 = r3 = 0
    n = 0
    granks = []
    for r in rows:
        if r["abstain"]:
            continue
        hx = HistoryIndex.load(split, r["hid"])
        units, sc = rank_units(r, hx, **{k: v for k, v in kw.items() if k != "lam"})
        ss, agg = sess_rank(units, sc, hx, kw.get("lam", 0.0))
        G = set(r["evidence"])
        n += 1
        p1 += ss[0] in G if ss else 0
        r2 += bool(set(ss[:2]) & G)
        r3 += bool(set(ss[:3]) & G)
        gr = [i for i, u in enumerate(units) if u in set(r["gold_uids"])]
        granks.append(gr[0] if gr else 999)
    return dict(n=n, P1=round(p1 / n, 3), R2=round(r2 / n, 3), R3=round(r3 / n, 3),
                gr_med=statistics.median(granks), gr_max=max(granks), gr_gt10=sum(g > 10 for g in granks))


if __name__ == "__main__":
    import sys
    splits = sys.argv[1:] or ["dev", "dev200"]
    grid = [dict(), dict(depth=50), dict(depth=100), dict(a_dense=0.5), dict(a_dense=1.0), dict(a_bm=0.5),
            dict(a_rrf=2.0), dict(a_dense=0.5, a_bm=0.5), dict(lam=0.15), dict(lam=0.3)]
    for sp in splits:
        if not (HERE / f"feats_{sp}.pkl").exists():
            continue
        for kw in grid:
            print(sp, kw, evaluate(sp, **kw))
