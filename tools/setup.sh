#!/bin/sh
# One-shot setup of a workspace around this repo (see ONBOARDING.md, level 1). Run from anywhere:
#   sh librarian/tools/setup.sh
# Layout it builds (paths in core/paths.py are relative to it):
#   <workspace>/librarian/          this repo (+ .venv)
#   <workspace>/memory-challenge/   organisers' kit, pinned commit (imported, never copied: upstream has no LICENSE)
#   <workspace>/data/{dev,dev-large,test}   release data-v1 of the kit
set -eu
LIB="$(cd "$(dirname "$0")/.." && pwd)"
WS="$(dirname "$LIB")"
cd "$WS"
[ -d memory-challenge ] || git clone https://github.com/RxAI-dev/memory-challenge.git
git -C memory-challenge checkout -q f0a317d
if [ ! -f data/test/questions.jsonl ]; then
  mkdir -p data-download data
  gh release download data-v1 -R RxAI-dev/memory-challenge -D data-download --skip-existing \
    -p dev.tar.gz -p test.tar.gz ${WITH_DEV_LARGE:+-p dev-large.tar.gz}
  for f in data-download/*.tar.gz; do tar -xzf "$f" -C data; done
fi
cd "$LIB"
[ -d .venv ] || uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt
echo "setup done. Next: AirDrop the team cache (ONBOARDING.md) or build it: python -m core.data shard dev test"
