#!/bin/sh
# Container entrypoint: the API opens its port at once (status reports models:false while they load); the model
# server (embeddings + reranker) runs next to it and is restarted if it ever exits. Logs: GET /api/log
cd /app/librarian
(while true; do echo "== model server start $(date)"; python -m core.model_server; echo "== exited $? $(date)"; sleep 2; done) >> /tmp/model.log 2>&1 &
if [ -n "${REACTOR_ACCESS_KEY:-}" ]; then ALLOW="--allow-reactor"; else ALLOW=""; fi
exec python -m demo.server --web demo --port 8800 --host 0.0.0.0 $ALLOW 2>> /tmp/server.log
