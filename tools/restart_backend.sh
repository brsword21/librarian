#!/bin/sh
# Restart the hosted backend container (picks up a new Reactor key or a new version), then wait until it is ready
# and re-warm the demo's caches. Needs cloudflare/api/.admin_key (local, not in git).
set -eu
LIB="$(cd "$(dirname "$0")/.." && pwd)"
API="https://librarian67-api.st-tomaszew.workers.dev"
curl -s -m 60 "$API/admin/restart?k=$(cat "$LIB/cloudflare/api/.admin_key")"
until curl -s -m 30 "$API/api/status" | grep -q '"models": true'; do sleep 5; done
echo "ready: $(curl -s -m 30 "$API/api/status")"
python3 "$LIB/tools/warm_backend.py" "$API"
