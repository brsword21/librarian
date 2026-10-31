#!/bin/sh
# Reactor client inside the container: URL and agent id are Worker vars, the key is a Worker secret (env only).
exec python /app/memory-challenge/reactor/client.py --base-url "$REACTOR_BASE_URL" --agent-id "$REACTOR_AGENT_ID" "$@"
