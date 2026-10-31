"""Offline session-pruning analysis (round 2): from a sweep's per_question.jsonl (debug['sess'] = sid ->
[first_rank, rr_first, label, n_top40, rr_max]) simulate 'keep only sessions with rr_max >= top - D (min mn, max mx)'.
Reports ALL (gold subset of kept), CF1all (F1 of kept vs gold), estimated PA and Sall-ish.
    .venv/bin/python -m lenses.multi.scratch_b.prune_fit <run_dir> [...]"""
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


def keep(S, d, mn, mx):
    order = sorted(S, key=lambda s: -S[s][4])
    if not order:
        return []
    top = S[order[0]][4]
    out = [s for s in order if S[s][4] >= top - d][:mx]
    return out if len(out) >= mn else order[:mn]


def main(dirs):
    for d in dirs:
        rows = [json.loads(l) for l in open(Path(d) / "per_question.jsonl")]
        split = "dev200" if d.rstrip("/").endswith("dev200") else "dev"
        g = gold(split)
        rows = [r for r in rows if not r.get("abstain_gold") and "debug" in r and r["question_id"] in g]
        n = len(rows)
        pa0 = sum(r["PA"] for r in rows) / n
        cfa0 = sum(r.get("CF1all", 0) for r in rows) / n
        np0 = sum(len(r["debug"]["sess"]) for r in rows) / n
        print(f"{d}: n={n} PA={pa0:.3f} CF1all={cfa0:.3f} sessions/pack={np0:.1f}")
        res = []
        for D in (2, 3, 4, 5, 6, 7, 8, 10, 99):
            for mn in (2, 3, 4):
                for mx in (4, 5, 6, 8, 10, 22):
                    al = pa = cf = ns = 0
                    for r in rows:
                        S = r["debug"]["sess"]
                        G = set(g[r["question_id"]]["evidence"])
                        k = keep(S, D, mn, mx)
                        lost = bool((G & set(S)) - set(k))
                        al += not lost and G <= set(S)
                        pa += r["PA"] * (not lost)
                        cf += f1(k, G)
                        ns += len(k)
                    res.append((0.65 * pa / n + 0.30 * cf / n, D, mn, mx, al / n, pa / n, cf / n, ns / n))
        for x in sorted(res, reverse=True)[:15]:
            print(f"   D={x[1]:<3} mn={x[2]} mx={x[3]:<3} ALL={x[4]:.3f} PA~{x[5]:.3f} CF1all={x[6]:.3f} "
                  f"sess={x[7]:.1f}  0.65PA+0.3CF={x[0]:.3f}")


if __name__ == "__main__":
    main(sys.argv[1:])
