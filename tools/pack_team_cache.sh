#!/bin/sh
# On the machine that has the caches (Mikołaj's Mac): pack everything a teammate needs to run sweeps without
# re-embedding ~200M characters. ~1.6 GB, AirDrop it. Unpack in the WORKSPACE root:  tar -xf librarian_team_cache.tar
# Contents: embedding + reranker cache (consistent sqlite backup), sharded histories, has_answer turns, session id
# files, the dev200 split (built from dev-large) and the LongMemEval oracle file used by core.gold_turns.
set -eu
LIB="$(cd "$(dirname "$0")/.." && pwd)"
WS="$(dirname "$LIB")"
OUT="${1:-$WS/librarian_team_cache.tar}"
TMP="$(mktemp -d)"
mkdir -p "$TMP/librarian/cache"
sqlite3 "$LIB/cache/models.sqlite" ".backup '$TMP/librarian/cache/models.sqlite'"
tar -cf "$OUT" -C "$TMP" librarian/cache/models.sqlite \
  -C "$WS" librarian/cache/hist librarian/cache/gold_turns.json librarian/cache/session_ids_dev.jsonl \
  librarian/cache/session_ids_test.jsonl data/dev200 data/lme
rm -rf "$TMP"
ls -lh "$OUT"
