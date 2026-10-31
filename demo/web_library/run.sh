#!/bin/sh
set -eu
app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$app_dir/../.."
exec .venv/bin/python -m demo.server --web demo/web_library --port "${PORT:-8804}"
