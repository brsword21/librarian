#!/bin/sh
# Public HTTPS URL for the local demo server, so Reactor can open /m/<token>/search links.
# No account needed (Cloudflare quick tunnel). Only token-scoped /m/ links are meant for Reactor; tokens are random
# and per question. Usage: sh tools/tunnel.sh [port]   (default 8800). Prints the https://...trycloudflare.com URL.
set -eu
PORT="${1:-8800}"
command -v cloudflared >/dev/null || { echo "install: brew install cloudflared" >&2; exit 2; }
exec cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$PORT" 2>&1 | grep --line-buffered -Eo 'https://[a-z0-9-]+\.trycloudflare\.com|ERR.*'
