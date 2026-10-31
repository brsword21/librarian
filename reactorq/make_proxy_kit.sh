#!/bin/sh
# Build proxy_kit.tar.gz for the simulator Mac (see PROXY.md). Run from anywhere; writes ../proxy_kit.tar.gz.
set -eu
LIB="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$(dirname "$LIB")"
cd "$BASE"
tar -czf proxy_kit.tar.gz \
  --exclude '__pycache__' \
  librarian/core/*.py librarian/reactorq/*.py librarian/PROXY.md \
  librarian/runs/proxy/packs/cal_packs.jsonl librarian/runs/proxy/packs/exp_*.jsonl \
  librarian/runs/reactor/e1_results.jsonl librarian/runs/reactor/e1b_results.jsonl \
  data/dev/questions.jsonl data/dev/gold.jsonl data/dev200/questions.jsonl data/dev200/gold.jsonl \
  memory-challenge/score.py memory-challenge/reactor/client.py memory-challenge/reactor/predictions.py
ls -la "$BASE/proxy_kit.tar.gz"
