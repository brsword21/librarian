"""results.jsonl (possibly with retries) -> submission predictions.jsonl, validated.

    python -m reactorq.finalize --results runs/final/results.jsonl --split test --out submission/predictions.jsonl
Keeps one line per question (the last answered one, else the last one), converts with the kit's predictions.py
(--abstain-on agent,no-answer), checks format with score.validate and fills nothing by hand.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import core.paths  # noqa: F401  (puts the upstream kit on sys.path)
from score import validate  # upstream kit

from core.data import questions, read_jsonl, session_ids_file
from core.paths import KIT, SPLIT_DIRS


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    best: dict[str, dict] = {}
    for r in read_jsonl(Path(a.results)):
        qid = r.get("question_id")
        if not qid:
            continue
        if r.get("status") == "answered" or best.get(qid, {}).get("status") != "answered":
            best[qid] = r
    qids = [q.question_id for q in questions(a.split)]
    missing = [q for q in qids if q not in best]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        for qid in qids:
            if qid in best:
                tmp.write(json.dumps(best[qid]) + "\n")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([sys.executable, str(KIT / "reactor" / "predictions.py"), tmp.name, "--histories",
                           str(session_ids_file(a.split)), "--out", str(out),
                           "--abstain-on", "agent,no-answer"], capture_output=True, text=True)
    print(proc.stderr.strip()[-2000:])
    preds = list(read_jsonl(out))
    errors = validate(preds, set(qids))
    status = {}
    for r in best.values():
        status[r.get("status")] = status.get(r.get("status"), 0) + 1
    print(f"statuses: {status}; predictions: {len(preds)}/{len(qids)}; missing questions: {len(missing)}; "
          f"abstained: {sum(p['abstain'] for p in preds)}; format errors: {len(errors)}")
    for e in errors[:10]:
        print("  ", e)
    return 0 if not errors and not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
