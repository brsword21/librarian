"""Simulate: among questions the text router sends to ssu, use the ssa lens when role_guess >= thr, else the ssu lens.
Usage: .venv/bin/python -m lenses.ssa.scratch_a.route_sim <split> [--ce]"""
import json
import sys
from collections import defaultdict
from core.data import questions
from core.index import HistoryIndex
from lenses.ssa import a_recsent as L

split = sys.argv[1]
ce = "--ce" in sys.argv
base = "runs/r2-ssa-a-route/ssu"
A = {json.loads(l)["question_id"]: json.loads(l) for l in open(f"{base}/a_recsent/recqs_cf7/{split}/per_question.jsonl")}
U = {json.loads(l)["question_id"]: json.loads(l) for l in open(f"{base}/a_struct/nb3t0/{split}/per_question.jsonl")}
U = {k: v for k, v in U.items() if not v.get("abstain_gold")}
qm = {q.question_id: q for q in questions(split)}
p = {}
for qid in U:
    q = qm[qid]
    f = L.role_features(q, HistoryIndex.load(split, q.history_id), use_ce=ce)
    p[qid] = f["p_assistant"] if ("--nofirst" not in sys.argv or (f["q_nofirst"] == 0 and f["q_ours"] == 0)) else 0.0
by = defaultdict(lambda: [0, 0.0, 0.0])
for qid in U:
    t = U[qid]["type"]
    by[t][0] += 1; by[t][1] += A[qid]["S"]; by[t][2] += U[qid]["S"]
print(split, "per gold type: n, S(ssa lens), S(ssu lens)")
for t, (n, a, u) in sorted(by.items()):
    print(f"  {t:9s} n={n:3d}  ssa-lens {a/n:5.1f}  ssu-lens {u/n:5.1f}")
n = len(U)
for key in ("S", "Sall"):
    print(f"{key}: all-ssu {sum(U[q][key] for q in U)/n:.2f}  all-ssa {sum(A[q][key] for q in U)/n:.2f}  "
          f"oracle-best {sum(max(U[q][key], A[q][key]) for q in U)/n:.2f}")
    for thr in (0.0, 0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8):
        s = sum((A[q][key] if p[q] >= thr else U[q][key]) for q in U) / n
        k = sum(p[q] >= thr for q in U)
        print(f"   thr {thr:.2f}: {s:.2f}  (to ssa lens: {k})")
