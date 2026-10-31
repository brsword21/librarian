"""Offline: per-kind keep thresholds on p(gold) from b_tight p08 runs (debug sess2[sid]['p'])."""
import json
from core.data import gold, questions
from lenses.multi.b_sweep import analyze


def f1(c, G):
    c = set(c)
    return 2 * len(c & G) / (len(c) + len(G)) if c else 0.0


for split in ("dev", "dev200"):
    g = gold(split); Q = {q.question_id: q for q in questions(split)}
    ref = {json.loads(l)["question_id"]: json.loads(l) for l in open(f"runs/r2-multi-b/multi/b_sweep/deep8_10k/{split}/per_question.jsonl")}
    rows = [json.loads(l) for l in open(f"runs/r2-multi-b/multi/b_tight/p08/{split}/per_question.jsonl")]
    rows = [r for r in rows if not r.get("abstain_gold")]
    from collections import Counter
    kinds = Counter()
    for r in rows:
        a = analyze(Q[r["question_id"]].question, Q[r["question_id"]].date)
        r["kind"] = a["kind"] + ("F" if a["facets"] else "")
        kinds[r["kind"]] += 1
        r["ng"] = len(g[r["question_id"]]["evidence"])
    print(split, dict(kinds))
    for k in sorted(kinds):
        sub = [r for r in rows if r["kind"] == k]
        print(f"   {k:8} n={len(sub)} mean gold sessions={sum(r['ng'] for r in sub)/len(sub):.2f}")
    for tc_count in (0.08, 0.05, 0.03, 0.02):
        pa = cf = ns = 0
        for r in rows:
            S = r["debug"]["sess2"]; G = set(g[r["question_id"]]["evidence"])
            o = sorted(S, key=lambda s: S[s]["r"])
            t = tc_count if r["kind"] == "count" else 0.08
            k = [s for s in o if S[s]["p"] >= t][:8]
            k = k if len(k) >= 2 else o[:2]
            pa += ref[r["question_id"]]["PA"] * (G <= set(k)); cf += f1(k, G); ns += len(k)
        n = len(rows)
        print(f"   tk(count)={tc_count}: PA~{pa/n:.3f} CF1all~{cf/n:.3f} sess={ns/n:.2f} S~{100*(0.65*pa/n+0.3*cf/n-0.05*(1600+1100*ns/n)/16000):.1f}")
