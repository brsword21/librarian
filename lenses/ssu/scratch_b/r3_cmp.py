"""Scratch r3: per-question diff of two runs (PA / CF1 / passages / chars) with the KU cue match.
    .venv/bin/python -m lenses.ssu.scratch_b.r3_cmp RUN_A RUN_B
"""
import json
import sys

from lenses.ssu.b_merge import KU_CUE

A = {json.loads(l)["question_id"]: json.loads(l) for l in open(sys.argv[1] + "/per_question.jsonl")}
B = {json.loads(l)["question_id"]: json.loads(l) for l in open(sys.argv[2] + "/per_question.jsonl")}
dS = 0
for k, b in B.items():
    a = A.get(k)
    if not a:
        continue
    pa = [p["id"] for p in a["passages"] if p["id"]]
    pb = [p["id"] for p in b["passages"] if p["id"]]
    if pa == pb and a.get("cite_plan") == b.get("cite_plan"):
        continue
    m = KU_CUE.search(b["question"])
    dS += (b.get("S") or 0) - (a.get("S") or 0)
    print(f"{b['type']:8s} PA {a.get('PA')}->{b.get('PA')} CF1 {a.get('CF1') or 0:.2f}->{b.get('CF1') or 0:.2f} "
          f"S {a.get('S') or 0:5.1f}->{b.get('S') or 0:5.1f} np {len(pa)}->{len(pb)} ch {a['chars']}->{b['chars']} "
          f"cue={m.group(0) if m else '-'!r} | {b['question'][:80]}")
print("sum dS", round(dS, 1), "over", len(B))
