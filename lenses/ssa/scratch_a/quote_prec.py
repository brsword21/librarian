"""Precision of the quoted key line: is the quoted sentence inside a gold turn? (dev/dev200 sweep output)
Usage: .venv/bin/python -m lenses.ssa.scratch_a.quote_prec <run_dir>"""
import json
import re
import sys
from pathlib import Path

from core.data import questions
from core.gold_turns import gold_turns
from core.index import HistoryIndex

run = Path(sys.argv[1])
split = run.name
gt = gold_turns()
qmap = {q.question_id: q for q in questions(split)}
n = ok = 0
for line in open(run / "per_question.jsonl"):
    r = json.loads(line)
    m = re.search(r'Likely the line you need \(assistant, session of .*?\d\d:\d\d\): "(.*)"$', r.get("hint") or "")
    if not m:
        continue
    q = qmap[r["question_id"]]
    hx = HistoryIndex.load(split, q.history_id)
    gold_text = " ".join(re.sub(r"[*_`#]+", "", t["content"]) for s in hx.sessions for t in s["turns"]
                         if t["turn_id"] in set(gt.get(r["question_id"], [])))
    hit = m.group(1)[:80] in gold_text
    n += 1
    ok += hit
    if not hit:
        print("MISS", r["question_id"], r["question"][:100], "\n     quoted:", m.group(1)[:160])
print(f"{split}: quote fired {n}/{sum(1 for _ in open(run / 'per_question.jsonl'))}, inside gold turn {ok}/{n}")
