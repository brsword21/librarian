#!/bin/sh
# After after_v3.sh: re-ask the 3 test questions whose call failed on a DNS error (network drop ~06:30), in the SAME
# Reactor history their dataset history already used, then rebuild the submission and the demo replay.
cd "$(dirname "$0")/../.."
while pgrep -f "runs/final/after_v3.sh" >/dev/null; do sleep 15; done
grep -E '"(q_78e1ac09e342|q_07a3d3d857f4|q_1a034c66813d)"' runs/final/v3_test_packs.jsonl > runs/final/v3_err_packs.jsonl
.venv/bin/python -m reactorq.queue --packs runs/final/v3_err_packs.jsonl --out runs/final/v3_err_reask_results.jsonl \
    --timeout 600 --reuse-history runs/final/v1_results.jsonl
.venv/bin/python -m reactorq.finalize --results runs/final/v1_results.jsonl runs/final/v3_reask_results.jsonl \
    runs/final/v3_err_reask_results.jsonl \
    --packs runs/final/v3_test_packs.jsonl runs/final/v2_test_packs.jsonl runs/final/v1_test_packs.jsonl \
    --split test --out submission/predictions.jsonl
.venv/bin/python -m demo.export_replay --out demo/replay.json
echo AFTER_ERR_DONE
