#!/bin/sh
# Submission time only (~10:45): a clean public snapshot of HEAD as ONE commit, without the team's private notes,
# agent scratch dumps, QA screenshots or the live Reactor slot. The team repo stays private (its history has them).
#   sh tools/make_submission_snapshot.sh            # build + check in $TMPDIR/librarian-submission, publish nothing
#   sh tools/make_submission_snapshot.sh --publish  # ...and create the PUBLIC repo brsword21/librarian-submission
set -eu
LIB="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${TMPDIR:-/tmp}/librarian-submission"
rm -rf "$OUT" && mkdir -p "$OUT"
git -C "$LIB" archive HEAD | tar -x -C "$OUT"
cd "$OUT"
rm -f docs/NIGHT_LOG.md ONBOARDING.md tools/make_submission_snapshot.sh
find lenses -path '*/scratch_*' -type f \( -name '*.log' -o -name '*.txt' -o -name '*.out' -o -name '*.jsonl' \
  -o -name '*.tsv' -o -name '*.pkl' -o -name '*.done' \) -delete
rm -f demo/*/qa/*.png demo/*/source-art/*.png
sed -i.bak -e 's#^REACTOR_BASE_URL=.*#REACTOR_BASE_URL=https://tNN.api.reactor-hackathon.rxai.dev#' \
  -e 's#^REACTOR_AGENT_ID=.*#REACTOR_AGENT_ID=agt_...#' tools/reactor.env.example
sed -i.bak -e "s# Team onboarding: \\[ONBOARDING.md\\](ONBOARDING.md) (Polish).##" README.md
sed -i.bak -e 's#Read ONBOARDING.md first; docs/NIGHT_LOG.md has the full#See README.md for the#' \
  -e 's#^event context. Team language: Polish.#pipeline and how to run it.#' CLAUDE.md
find . -name '*.bak' -delete
echo "== checks"
grep -rIl -e 'rxk_[A-Za-z0-9]\{8,\}' -e '/Users/mikolaj' -e 'receptionos' --exclude-dir=lenses . && { echo "FOUND private strings above"; exit 1; } || true
wc -l < submission/predictions.jsonl | sed 's/^/predictions lines: /'
du -sh . | sed 's/^/size: /'
git init -q -b main && git add -A
git -c user.name="Team Ptysie" -c user.email="brsword21@users.noreply.github.com" commit -qm "Librarian: hackathon submission"
echo "snapshot ready: $OUT"
if [ "${1:-}" = "--publish" ]; then
  gh repo create brsword21/librarian-submission --public --source . --push \
    --description "Librarian: evidence retrieval for the Reactive AI Memory Retrieval Challenge"
fi
