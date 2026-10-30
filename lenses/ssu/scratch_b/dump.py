"""Scratch: dump per-question retrieval features for ssu (dev / dev200) so ranking ideas can be tested offline.

    .venv/bin/python -m lenses.ssu.scratch_b.dump dev 150
Writes lenses/ssu/scratch_b/feats_<split>.pkl: one dict per question with, for every USER unit, bm25 + dense scores,
and cross-encoder logits for the user-only hybrid top-K (plus the gold units, for diagnostics only).
"""
import pickle
import sys
from pathlib import Path

import numpy as np

from core import models
from core.data import gold, questions
from core.gold_turns import gold_turns
from core.index import HistoryIndex

split = sys.argv[1]
K = int(sys.argv[2]) if len(sys.argv) > 2 else 150
out = Path(__file__).parent / f"feats_{split}.pkl"
g, gt = gold(split), gold_turns()
qs = [q for q in questions(split) if g[q.question_id]["question_type"] == "single-session-user"]
rows = []
for n, q in enumerate(qs):
    hx = HistoryIndex.load(split, q.history_id)
    users = [u.uid for u in hx.units if u.role == "user"]
    bm = np.zeros(len(hx.units), np.float32)
    bm[:] = hx.bm25_scores(q.question)
    qv = models.embed([q.question], query=True)[0]
    de = np.zeros(len(hx.units), np.float32)
    de[users] = hx.vectors(users) @ qv
    hyb = hx.hybrid(q.question, k=300, roles=["user"], pool=300)
    gold_uids = [i for tid in gt.get(q.question_id, []) for i in hx.turn_units(tid)]
    pool = [u for u, _ in hyb[:K]]
    rr = dict(hx.rerank(q.question, list(dict.fromkeys(pool + gold_uids))))
    rows.append(dict(qid=q.question_id, hid=q.history_id, question=q.question, answer=g[q.question_id]["answer"],
                     abstain=g[q.question_id]["abstain"], evidence=g[q.question_id]["evidence"],
                     gold_uids=gold_uids, users=users, bm25={u: float(bm[u]) for u in users},
                     dense={u: float(de[u]) for u in users}, hybrid=[u for u, _ in hyb], rr=rr, K=K))
    print(n, q.question_id, len(rr), flush=True)
pickle.dump(rows, open(out, "wb"))
print("wrote", out)
