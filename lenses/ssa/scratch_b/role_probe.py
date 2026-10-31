"""Probe evidence-based role features on questions the router sends to ssu (no 'you' cue).
Label = gold type is single-session-assistant. Writes one JSON row per question to scratch_b/role_probe_<split>.jsonl.
Usage: .venv/bin/python -m lenses.ssa.scratch_b.role_probe dev
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from core.data import gold, questions
from core.index import HistoryIndex
from core.router import route

OUT = Path(__file__).parent


def feats(q, hx, n=40):
    cand = hx.hybrid(q.question, k=100, pool=300)
    top = [u for u, _ in cand[:n]]
    rr = hx.rerank(q.question, top)
    units = hx.units
    best = {"assistant": -20.0, "user": -20.0}
    for u, s in rr:
        r = units[u].role
        best[r] = max(best[r], s)
    u0, s0 = rr[0]
    sid = units[u0].session_id
    sb = {"assistant": -20.0, "user": -20.0}
    for u, s in rr:
        if units[u].session_id == sid:
            sb[units[u].role] = max(sb[units[u].role], s)
    # rank-weighted role mass in top-10
    mass = sum((1 if units[u].role == "assistant" else -1) / (1 + i) for i, (u, _) in enumerate(rr[:10]))
    # BM25-only: role of best bm25 unit
    b = hx.bm25(q.question, k=10)
    b_role = units[b[0][0]].role if b else "user"
    # assistant-only vs user-only dense top
    da = hx.dense(q.question, k=1, roles=["assistant"])
    du = hx.dense(q.question, k=1, roles=["user"])
    return {
        "ce_a": best["assistant"], "ce_u": best["user"], "d_all": best["assistant"] - best["user"],
        "d_sess": sb["assistant"] - sb["user"], "top_role": units[u0].role, "mass10": mass,
        "bm25_role": b_role, "dense_d": (da[0][1] if da else 0) - (du[0][1] if du else 0),
    }


def text_feats(qs: str):
    first = len(re.findall(r"\b(I|my|me|mine|I'm|I've|I'd|myself)\b", qs))
    return {"n_first": first}


def main(split="dev"):
    g = gold(split)
    rows = []
    for q in questions(split):
        r = route(q.question)[0]
        if r != "ssu":
            continue
        t = g[q.question_id]["question_type"]
        hx = HistoryIndex.load(split, q.history_id)
        f = feats(q, hx)
        f.update(text_feats(q.question))
        f.update({"qid": q.question_id, "type": t, "q": q.question, "abstain": g[q.question_id].get("abstain", False)})
        rows.append(f)
        print(t[:12], f"{f['d_all']:+.2f} {f['d_sess']:+.2f} {f['top_role'][:4]} {f['mass10']:+.2f} nf={f['n_first']}",
              q.question[:80], flush=True)
    with open(OUT / f"role_probe_{split}.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
