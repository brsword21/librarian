#!/bin/sh
# Make https://librarian67.pages.dev live from this laptop: models + demo server + Cloudflare tunnel, and register the
# tunnel URL in the site's KV so the Pages Functions proxy /api/* and /m/* here. Ctrl-C unregisters (site -> replay).
#   sh tools/serve_live.sh                    # live retrieval only (Reactor answers stay recorded)
#   sh tools/serve_live.sh --allow-reactor    # + live Reactor answers and ask-back (one job at a time)
# Needs: wrangler logged in to the Cloudflare account that owns the site; for --allow-reactor also ../reactor.sh,
# ../reactor.env and the key in the macOS keychain (ONBOARDING.md, level 2). Never enable Reactor while a benchmark
# run uses the same agent: every live job opens a new Reactor history.
set -eu
LIB="$(cd "$(dirname "$0")/.." && pwd)"
cd "$LIB"
PORT="${PORT:-8800}"
SITE="https://librarian67.pages.dev"
KV_ID="3860d719c39540b682b283bce3f88f71"
LOG="$(mktemp -t librarian-tunnel)"
PIDS=""
cleanup() {
  echo "unregistering backend (site falls back to replay)"
  npx -y wrangler@4 kv key delete --namespace-id "$KV_ID" backend --remote >/dev/null 2>&1 || true
  [ -n "$PIDS" ] && kill $PIDS 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if ! nc -z 127.0.0.1 8765 2>/dev/null; then
  .venv/bin/python -m core.model_server & PIDS="$PIDS $!"
  echo "starting model server..."
  until nc -z 127.0.0.1 8765 2>/dev/null; do sleep 1; done
fi
if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then echo "port $PORT is busy: stop the other demo server first" >&2; exit 2; fi
PUBLIC_URL="$SITE" .venv/bin/python -m demo.server --web demo/site --port "$PORT" "$@" & PIDS="$PIDS $!"
cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$PORT" >"$LOG" 2>&1 & PIDS="$PIDS $!"
URL=""
for _ in $(seq 1 60); do
  URL="$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1 || true)"
  [ -n "$URL" ] && break
  sleep 1
done
[ -n "$URL" ] || { echo "tunnel did not start: $LOG" >&2; exit 2; }
npx -y wrangler@4 kv key put --namespace-id "$KV_ID" backend "$URL" --remote >/dev/null
echo "live: $SITE  (backend $URL)"
until curl -sf -m 10 "$SITE/api/status" >/dev/null 2>&1; do sleep 3; done
echo "status: $(curl -s -m 10 "$SITE/api/status")"
wait
