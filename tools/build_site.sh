#!/bin/sh
# Build the public site into cloudflare/public: / landing (demo/landing), /demo/ demo (demo/web), /live, /inbox, /pitch/.
#   sh tools/build_site.sh            # build only; preview: python3 -m http.server -d cloudflare/public 8840
#   sh tools/build_site.sh --deploy   # build + deploy to https://librarian67.pages.dev (Cloudflare Pages + Functions)
# /api/*, /m/* and /mcp are Cloudflare Functions (cloudflare/functions) that reach the backend container.
set -eu
LIB="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$LIB/cloudflare/public"
rm -rf "$OUT" && mkdir -p "$OUT"
cp -R "$LIB/demo/landing/." "$OUT/"             # / : the landing page (the pitch, use cases, plugin, stack)
mkdir -p "$OUT/demo" && cp -R "$LIB/demo/web/." "$OUT/demo/"   # /demo/ : the demo itself
rm -rf "$OUT/demo/qa" "$OUT/demo/README.md" "$OUT/demo/IMPLEMENTATION.md"
cp "$LIB/demo/live.html" "$OUT/live.html"
sed 's#href="/">#href="/demo/">#' "$LIB/demo/inbox.html" > "$OUT/inbox.html"   # "The library" link -> the demo
cp "$LIB/demo/replay.json" "$LIB/demo/askback.json" "$LIB/demo/users.json" "$OUT/"
[ -d "$LIB/demo/samples" ] && cp -R "$LIB/demo/samples" "$OUT/samples"
cp -R "$LIB/demo/pitch" "$OUT/pitch"          # the pitch deck at /pitch/
cat > "$OUT/_redirects" <<'R'
/demo.html   /demo/  301
/pitch.html  /pitch/ 301
R
cat > "$OUT/_headers" <<'H'
/*.json
  Cache-Control: public, max-age=300
/fonts/*
  Cache-Control: public, max-age=31536000, immutable
H
echo "built $OUT ($(du -sh "$OUT" | cut -f1))"
if [ "${1:-}" = "--deploy" ]; then
  cd "$LIB/cloudflare"
  npx -y wrangler@4 pages deploy --project-name librarian67 --branch main --commit-dirty=true
fi
