#!/bin/sh
# Waits for the v3 test pass to finish, then re-asks the questions whose pack changed after they were answered,
# then refreshes the submission and the demo replay. Logs to runs/final/after_v3.log
cd "$(dirname "$0")/../.."
while pgrep -f "reactorq.queue --packs runs/final/v3_test_packs" >/dev/null; do sleep 20; done
.venv/bin/python - <<'PY'
import json
q = set(open("runs/final/v3_reask_qids.txt").read().split())
with open("runs/final/v3_reask_packs.jsonl", "w") as f:
    for l in open("runs/final/v3_test_packs.jsonl"):
        if json.loads(l)["question_id"] in q:
            f.write(l)
PY
.venv/bin/python -m reactorq.queue --packs runs/final/v3_reask_packs.jsonl --out runs/final/v3_reask_results.jsonl --timeout 600
.venv/bin/python -m reactorq.finalize --results runs/final/v1_results.jsonl runs/final/v3_reask_results.jsonl \
    --packs runs/final/v3_test_packs.jsonl runs/final/v2_test_packs.jsonl runs/final/v1_test_packs.jsonl \
    --split test --out submission/predictions.jsonl
.venv/bin/python -m demo.export_replay --out demo/replay.json
echo AFTER_V3_DONE
