"""Where is the gold turn relative to the lens's best turn? (dev/dev200, from a sweep's per_question.jsonl)
Usage: .venv/bin/python -m lenses.ssa.scratch_a.turn_dist <run_dir>"""
import json
import sys
from collections import Counter
from pathlib import Path

from core.data import gold, questions
from core.gold_turns import gold_turns
from core.index import HistoryIndex

run = Path(sys.argv[1])
split = run.name
g = gold(split)
gt = gold_turns()
qmap = {q.question_id: q for q in questions(split)}
dist = Counter()
rows = []
for line in open(run / "per_question.jsonl"):
    r = json.loads(line)
    q = qmap[r["question_id"]]
    hx = HistoryIndex.load(split, q.history_id)
    top = r["ranking_top"]
    A = gt.get(r["question_id"], [])
    if not top or not A:
        continue
    bu = hx.units[top[0]]
    gold_tids = set(A)
    # rank of the first gold unit
    rk = next((i for i, u in enumerate(top) if hx.units[u].turn_id in gold_tids), None)
    gu = [hx.units[i] for t in A for i in hx.turn_units(t)][0]
    same_sess = gu.session_id == bu.session_id
    d = (gu.turn_idx - bu.turn_idx) if same_sess else None
    dist[d] += 1
    sess_chars = sum(len(t["content"]) for t in hx.sess_by_id[bu.session_id]["turns"])
    rows.append((r["question_id"], rk, d, sess_chars, r["chars"], r["question"][:90]))
print(split, "best-turn -> gold-turn offset:", sorted(dist.items(), key=lambda x: (x[0] is None, x[0] or 0)))
for row in rows:
    if row[2] != 0:
        print(row)
