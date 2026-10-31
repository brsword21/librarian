"""Offline: simulate pruning B's pack to sessions near the cite set. Reads per_question.jsonl with debug['sess'].
    .venv/bin/python -m lenses.multi.scratch_a.prune_sim runs/r1-multi-b/multi/b_sweep/deep8_10k/dev"""
import json, sys
from pathlib import Path
from core.data import gold


def f1(c, G):
    c, G = set(c), set(G)
    if not c or not G:
        return 0.0
    tp = len(c & G)
    return 2 * tp / (len(c) + len(G))


def rule(S, d, extra, mn):
    order = sorted(S, key=lambda s: -S[s][4])
    if not order:
        return []
    top = S[order[0]][4]
    core = [s for s in order if S[s][4] >= top - d]
    if len(core) < mn:
        core = order[:mn]
    rest = [s for s in order if s not in core]
    return core + rest[:extra]


def main(d):
    rows = [json.loads(l) for l in open(Path(d) / "per_question.jsonl")]
    split = "dev200" if d.rstrip("/").endswith("dev200") else "dev"
    g = gold(split)
    ans = [r for r in rows if not r.get("abstain_gold")]
    def S_of(pa, cf, ch):
        return 100 * (0.65 * pa + 0.30 * cf - 0.05 * ch / 16000)
    base_S = sum(S_of(r["PA"], r["CF1"], r["chars"]) for r in ans) / len(ans)
    base_Sall = sum(S_of(r["PA"], f1([p["id"] for p in r["passages"]], g[r["question_id"]]["evidence"]), r["chars"]) for r in ans) / len(ans)
    npass = sum(len(r["passages"]) for r in ans) / len(ans)
    print(f"{d} n={len(ans)} base S={base_S:.1f} Sall={base_Sall:.1f} passages={npass:.1f}")
    res = []
    for D in (2, 3, 4, 5, 6, 8, 10, 99):
        for extra in (0, 1, 2, 3, 4):
            for mn in (2, 3, 4):
                tS = tSa = tpa = tp = 0
                for r in ans:
                    G = set(g[r["question_id"]]["evidence"])
                    S = r["debug"]["sess"]
                    keep = set(rule(S, D, extra, mn))
                    pas = [p for p in r["passages"] if p["id"] in keep]
                    ch = r["chars"] - sum(len(p["text"]) + 60 for p in r["passages"] if p["id"] not in keep)
                    pa = r["PA"] if G <= keep or not (G <= {p["id"] for p in r["passages"]}) else 0.0
                    if not G <= keep:
                        pa = 0.0
                    cite = [c for c in (r["cite_plan"] or []) if c in keep]
                    tS += S_of(pa, f1(cite, G), ch)
                    tSa += S_of(pa, f1(keep, G), ch)
                    tpa += pa
                    tp += len(pas)
                n = len(ans)
                res.append((tSa / n, tS / n, tpa / n, tp / n, D, extra, mn))
    for x in sorted(res, reverse=True)[:15]:
        print(f"  Sall={x[0]:.1f} S={x[1]:.1f} PA={x[2]:.3f} pass={x[3]:.1f}  D={x[4]} extra={x[5]} min={x[6]}")


if __name__ == "__main__":
    for d in sys.argv[1:]:
        main(d)
