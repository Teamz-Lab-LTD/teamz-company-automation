#!/bin/bash
# Rebuild sitemap.xml from all tool pages
# Run after adding/removing any tool: ./build-sitemap.sh

SCRIPTS="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")" && pwd)"
source "$SCRIPTS/lib/config.sh"
teamz_load_config "$0"
BASE="$TEAMZ_HOST_SITE_ROOT"

if [[ "${TEAMZ_PROJECT_TYPE:-website}" == "app" ]]; then
  echo "INFO: build-sitemap.sh is website-focused and disabled for TEAMZ_PROJECT_TYPE=app."
  exit 2
fi

# Helper: get lastmod date from git history for a file
get_lastmod() {
  local file="$1"
  local date
  date=$(git -C "$BASE" log -1 --format="%as" -- "$file" 2>/dev/null)
  if [ -z "$date" ]; then
    date=$(date +%Y-%m-%d)
  fi
  echo "$date"
}

{
echo '<?xml version="1.0" encoding="UTF-8"?>'
echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'

# Static pages with lastmod
home_mod=$(get_lastmod "index.html")
echo "  <url>"
echo "    <loc>https://tool.teamzlab.com/</loc>"
echo "    <lastmod>$home_mod</lastmod>"
echo "    <changefreq>weekly</changefreq>"
echo "    <priority>1.0</priority>"
echo "  </url>"

for static_page in about contact privacy terms; do
  case "$static_page" in
    about|contact) prio="0.5" ;;
    *) prio="0.3" ;;
  esac
  mod=$(get_lastmod "$static_page/index.html")
  echo "  <url>"
  echo "    <loc>https://tool.teamzlab.com/$static_page/</loc>"
  echo "    <lastmod>$mod</lastmod>"
  echo "    <changefreq>monthly</changefreq>"
  echo "    <priority>$prio</priority>"
  echo "  </url>"
done

# Tool pages — exclude static pages, root index.html, docs, node_modules
find "$BASE" -path "*/*/index.html" \
  -not -path "*/.claude/*" -not -path "*/.claude-memory/*" \
  -not -path "*/about/*" -not -path "*/contact/*" \
  -not -path "*/privacy/*" -not -path "*/terms/*" \
  -not -path "*/docs/*" -not -path "*/node_modules/*" \
  | sed "s|$BASE/||" | sed 's|/index.html||' | sort | while read slug; do
  # Skip the root index.html (already added as homepage above)
  if [ "$slug" = "index.html" ] || [ -z "$slug" ]; then
    continue
  fi
  # Skip noindex pages and redirect stubs
  if grep -qE '<meta[[:space:]]+name="robots"[[:space:]]+content="[^"]*noindex' "$BASE/$slug/index.html" 2>/dev/null; then
    continue
  fi
  if grep -q 'http-equiv="refresh"' "$BASE/$slug/index.html" 2>/dev/null; then
    continue
  fi
  # Skip pages that canonicalise to a DIFFERENT URL. Listing a page in the sitemap
  # while its canonical points elsewhere is the contradiction that produces GSC's
  # "Duplicate, Google chose a different canonical than the user" — it asks Google
  # to index a URL the page itself disowns. Added 2026-08-23 when the two passer-rating
  # calculators were consolidated; applies to every future dedupe automatically.
  canon=$(grep -o '<link rel="canonical" href="[^"]*"' "$BASE/$slug/index.html" 2>/dev/null \
            | head -1 | sed 's|.*href="||; s|"$||')
  if [ -n "$canon" ] && [ "$canon" != "https://tool.teamzlab.com/$slug/" ]; then
    continue
  fi
  mod=$(get_lastmod "$slug/index.html")
  echo "  <url>"
  echo "    <loc>https://tool.teamzlab.com/$slug/</loc>"
  echo "    <lastmod>$mod</lastmod>"
  echo "    <changefreq>monthly</changefreq>"
  echo "    <priority>0.7</priority>"
  echo "  </url>"
done

echo '</urlset>'
} > "$BASE/sitemap.xml.tmp"

# NEVER overwrite a good sitemap with a gutted one.
# On 2026-08-22 two concurrent runs of this script truncated sitemap.xml from 6,854
# URLs to 1,238 and wrote it straight into place; it was caught by eye, not by code.
# The same shape would appear if a future property enabled TEAMZ_NIGHTLY_SITEMAP=1
# and inherited the hardcoded tool.teamzlab.com prefix, since every canonical would
# then mismatch and every page would be skipped. Build to a temp file, and refuse to
# publish a sudden collapse — an unreadable input must never become a smaller sitemap.
count=$(grep -c '<url>' "$BASE/sitemap.xml.tmp")
prev=0
[ -f "$BASE/sitemap.xml" ] && prev=$(grep -c '<url>' "$BASE/sitemap.xml" 2>/dev/null || echo 0)
if [ "$count" -eq 0 ]; then
  rm -f "$BASE/sitemap.xml.tmp"
  echo "FATAL: generated sitemap has 0 URLs — keeping the existing $prev-URL sitemap." >&2
  exit 1
fi
if [ "$prev" -gt 100 ] && [ "$count" -lt $(( prev * 90 / 100 )) ]; then
  mv "$BASE/sitemap.xml.tmp" "$BASE/sitemap.xml.rejected"
  echo "FATAL: sitemap would drop $prev -> $count URLs (>10% loss). NOT published." >&2
  echo "       Rejected build left at sitemap.xml.rejected for inspection." >&2
  echo "       Most likely: two builds running at once, or a canonical/domain mismatch." >&2
  exit 1
fi
mv "$BASE/sitemap.xml.tmp" "$BASE/sitemap.xml"
echo "Sitemap rebuilt: $count URLs in sitemap.xml (previous: $prev)"

# Ping search engines (free, no API key needed)
echo "Pinging search engines..."
curl -s "https://www.google.com/ping?sitemap=https://tool.teamzlab.com/sitemap.xml" > /dev/null 2>&1 && echo "  Google: pinged" || echo "  Google: failed (ok, they'll crawl anyway)"
curl -s "https://www.bing.com/indexnow?url=https://tool.teamzlab.com/sitemap.xml&key=teamzlab" > /dev/null 2>&1 && echo "  Bing: pinged" || echo "  Bing: failed (ok, they'll crawl anyway)"
