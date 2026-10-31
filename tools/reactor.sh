#!/bin/sh
# (copy of the workspace-root wrapper; expects reactor.env, .venv with websockets and memory-challenge/ next to it)
# reactor/client.py z kluczem z pęku kluczy macOS (nie w pliku, nie w historii shella, nie w czacie)
# oraz base URL i agent id z reactor.env. Argumenty jak dla client.py, bez --base-url/--agent-id:
#   ./reactor.sh --new-history
#   ./reactor.sh --history <id> --question "..." --question-date "2023/05/30 (Tue) 08:08" --evidence ev.json
# Dowolna komenda z kluczem i configiem w env (REACTOR_ACCESS_KEY, REACTOR_BASE_URL, REACTOR_AGENT_ID):
#   ./reactor.sh --run .venv/bin/python moj_pipeline.py
# Jednorazowo, we własnym Terminalu (pyta o klucz i go nie pokazuje):
#   security add-generic-password -a "$USER" -s reactor-hackathon-key -w
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/reactor.env"
case "$REACTOR_BASE_URL$REACTOR_AGENT_ID" in
  *tNN*|*agt_...*) echo "uzupełnij REACTOR_BASE_URL i REACTOR_AGENT_ID w $DIR/reactor.env" >&2; exit 2 ;;
esac
REACTOR_ACCESS_KEY="$(security find-generic-password -a "$USER" -s reactor-hackathon-key -w 2>/dev/null)" || {
  echo 'brak klucza w pęku kluczy; w Terminalu: security add-generic-password -a "$USER" -s reactor-hackathon-key -w' >&2
  exit 2
}
export REACTOR_ACCESS_KEY REACTOR_BASE_URL REACTOR_AGENT_ID REACTOR_TIMEOUT
if [ "${1:-}" = "--run" ]; then
  shift
  exec "$@"
fi
exec "$DIR/.venv/bin/python" "$DIR/memory-challenge/reactor/client.py" \
  --base-url "$REACTOR_BASE_URL" --agent-id "$REACTOR_AGENT_ID" "$@"
