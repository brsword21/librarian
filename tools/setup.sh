#!/bin/sh
# One-shot setup of a workspace around this repo (ONBOARDING.md, level 1). Run from anywhere:
#   sh librarian/tools/setup.sh                    # dev + test data, venv, sharded histories, has_answer turns
#   WITH_DEV_LARGE=1 sh librarian/tools/setup.sh   # also dev-large (0.74 GB, 2.3 GB unpacked), then: python -m core.data dev200
# Layout (core/paths.py resolves everything relative to it):
#   <workspace>/librarian/          this repo (+ .venv)
#   <workspace>/memory-challenge/   organisers' kit at a pinned commit (imported, never copied: upstream has no LICENSE)
#   <workspace>/data/{dev,test,dev-large,lme}
set -eu
LIB="$(cd "$(dirname "$0")/.." && pwd)"
WS="$(dirname "$LIB")"
REL=https://github.com/RxAI-dev/memory-challenge/releases/download/data-v1
cd "$WS"
[ -d memory-challenge ] || git clone -q https://github.com/RxAI-dev/memory-challenge.git
git -C memory-challenge checkout -q f0a317d
mkdir -p data-download data/lme
for s in dev test ${WITH_DEV_LARGE:+dev-large}; do
  [ -f "data/$s/questions.jsonl" ] && continue
  [ -f "data-download/$s.tar.gz" ] || curl -fL --progress-bar -o "data-download/$s.tar.gz" "$REL/$s.tar.gz"
  tar -xzf "data-download/$s.tar.gz" -C data
done
# LongMemEval oracle (15 MB): maps the gold answer turns (has_answer) used by the harness metrics
[ -f data/lme/longmemeval_oracle.json ] || curl -fL --progress-bar -o data/lme/longmemeval_oracle.json \
  https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json
cd "$LIB"
[ -d .venv ] || uv venv -q --python 3.14 .venv
uv pip install -q --python .venv/bin/python -r requirements.txt
[ -f cache/session_ids_test.jsonl ] || .venv/bin/python -m core.data shard dev test
[ -f cache/gold_turns.json ] || .venv/bin/python -m core.gold_turns
echo "setup done. Next (from librarian/): start .venv/bin/python -m core.model_server in its own terminal tab;"
echo "for full-speed sweeps unpack the team cache in $WS:  tar -xf ~/Downloads/librarian_team_cache.tar"
