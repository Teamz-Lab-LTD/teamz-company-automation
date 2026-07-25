#!/bin/bash
# FRESHNESS VALIDATOR — Checks for stale/outdated data across the project
# Run: ./build-validate-freshness.sh
# Run annually or when tax years change

_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
SCRIPTS="$(cd "$(dirname "$_SCRIPT")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPTS/lib/config.sh"
teamz_load_config "$_SCRIPT"
BASE="$TEAMZ_HOST_SITE_ROOT"
CURRENT_YEAR=$(date +%Y)
NEXT_YEAR=$((CURRENT_YEAR + 1))
PREV_YEAR=$((CURRENT_YEAR - 1))
WARNINGS=0

echo "============================================="
echo "  Freshness Validator — Checking for stale data"
echo "  Current year: $CURRENT_YEAR"
echo "============================================="
echo ""

# 1. Check for outdated year references in titles
echo "[1/6] Checking for outdated years in <title> tags..."
STALE_TITLES=$(grep -rn "<title>.*$PREV_YEAR" --include="*.html" "$BASE" | grep -v node_modules | grep -v FALLBACK | wc -l | tr -d ' ')
if [ "$STALE_TITLES" -gt 0 ]; then
  echo "  WARNING: $STALE_TITLES pages have $PREV_YEAR in <title> — may need updating:"
  grep -rn "<title>.*$PREV_YEAR" --include="*.html" "$BASE" | grep -v node_modules | grep -v FALLBACK | sed 's/.*teamzlab-tools\//  /' | head -10
  WARNINGS=$((WARNINGS + STALE_TITLES))
else
  echo "  OK — no outdated years in titles"
fi

echo ""

# 2. Check for hardcoded tool counts that don't match reality
echo "[2/6] Checking tool counts in meta descriptions..."
TOTAL=$(find "$BASE" -path "*/*/index.html" -not -path "*/about/*" -not -path "*/contact/*" -not -path "*/privacy/*" -not -path "*/terms/*" -not -path "*/docs/*" -not -path "*/node_modules/*" -not -path "*/.git/*" | wc -l | tr -d ' ')
STALE_COUNTS=$(grep -rn "29[0-9]\|30[0-9]\|31[0-9]\|32[0-9].*free.*tool\|294\|299\|300+" --include="*.html" "$BASE/index.html" "$BASE/about/"*.html 2>/dev/null | grep -v search-index | grep -v sitemap | wc -l | tr -d ' ')
echo "  Actual tool count: $TOTAL"
if [ "$STALE_COUNTS" -gt 0 ]; then
  echo "  WARNING: Found old tool count references"
  WARNINGS=$((WARNINGS + 1))
else
  echo "  OK — no stale count references found"
fi

echo ""

# 3. Check tax year references
echo "[3/6] Checking tax year references..."
TAX_YEARS=$(grep -rl "FY $PREV_YEAR\|FY $((PREV_YEAR-1))\|tax year $PREV_YEAR\|$((PREV_YEAR-1))-$PREV_YEAR" --include="*.html" "$BASE" | grep -v node_modules | wc -l | tr -d ' ')
if [ "$TAX_YEARS" -gt 0 ]; then
  echo "  INFO: $TAX_YEARS files reference previous tax years — review if new rates published:"
  grep -rl "FY $PREV_YEAR\|FY $((PREV_YEAR-1))" --include="*.html" "$BASE" | grep -v node_modules | sed 's/.*teamzlab-tools\//  /' | head -10
else
  echo "  OK"
fi

echo ""

# 4. Check for past event dates
echo "[4/6] Checking for past hardcoded event dates..."
# Find dates that have already passed
PAST_EVENTS=0
for f in $(grep -rl "new Date($PREV_YEAR\|'$PREV_YEAR-" --include="*.html" "$BASE" | grep -v node_modules | grep -v FALLBACK); do
  fname=$(echo "$f" | sed "s|$BASE/||")
  if echo "$fname" | grep -qi "countdown\|event\|deadline"; then
    echo "  REVIEW: $fname has $PREV_YEAR dates"
    PAST_EVENTS=$((PAST_EVENTS + 1))
  fi
done
if [ "$PAST_EVENTS" -eq 0 ]; then
  echo "  OK — no past event dates found in countdown tools"
fi

echo ""

# 5. Check regulation tools for passed deadlines
echo "[5/6] Checking compliance tools for passed deadlines..."
for f in "$BASE/compliance/"*/index.html "$BASE/uk/"*/index.html "$BASE/eu/"*/index.html; do
  if [ -f "$f" ]; then
    fname=$(echo "$f" | sed "s|$BASE/||")
    if grep -q "$PREV_YEAR" "$f" 2>/dev/null; then
      echo "  REVIEW: $fname references $PREV_YEAR — check if regulation updated"
    fi
  fi
done
echo "  (Regulation tools should be reviewed annually)"

echo ""

# 6. Check external API endpoints still work
echo "[6/6] Testing external API endpoints..."
# TheSportsDB
SPORTS_OK=$(curl -s -o /dev/null -w "%{http_code}" "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4480&s=$CURRENT_YEAR-$NEXT_YEAR" 2>/dev/null)
echo "  TheSportsDB UCL API: HTTP $SPORTS_OK"

# ipinfo.io (used by IP/VPN/DNS diagnostic tools)
IP_OK=$(curl -s -o /dev/null -w "%{http_code}" "https://ipinfo.io/json" 2>/dev/null)
echo "  ipinfo.io (IP lookup): HTTP $IP_OK"

# Cloudflare DoH
CF_OK=$(curl -s -o /dev/null -w "%{http_code}" "https://cloudflare-dns.com/dns-query?name=example.com&type=A" -H "Accept: application/dns-json" 2>/dev/null)
echo "  Cloudflare DoH: HTTP $CF_OK"

echo ""
echo "============================================="
echo "  Warnings: $WARNINGS"
echo "  Status: $([ $WARNINGS -eq 0 ] && echo 'ALL FRESH' || echo 'NEEDS REVIEW')"
echo ""
echo "  ANNUAL UPDATE CHECKLIST:"
echo "  [ ] UK tax brackets (uk/ tools) — April each year"
echo "  [ ] US tax brackets (evergreen/ tax tools) — January each year"
echo "  [ ] India tax slabs (in/ tools) — April each year"
echo "  [ ] EU AI Act milestones (compliance/) — check August deadlines"
echo "  [ ] UK Companies House deadlines (uk/) — check November"
echo "  [ ] UCL prize money (football/) — August each year"
echo "  [ ] Apple event dates (apple/) — auto-pattern but verify"
echo "  [ ] Minimum wage rates (country hubs) — varies by country"
echo "  [ ] SSP/NI/NMW rates (uk/) — April each year"
echo "============================================="

# ── Show latest SEO auto-report if available ──
# The sentinel line below tells nightly-build.sh's run_phase_cmd where THIS run's real
# output ends and a paste of a PREVIOUS night's report begins. Without it, a stale
# ERROR:/FAILED line sitting inside that pasted report gets re-matched as tonight's health
# issue by extract_health_issue() — and since seo-latest-report.txt is itself partly built
# from what THIS script printed on earlier nights, an old error snowballs: re-recorded as a
# new alert, re-pasted into tomorrow's report, re-matched the night after, forever. Confirmed
# live: 52 repeated "- Freshness validation:" lines and growing before this fix, none of them
# a real failure on the night they were logged.
SEO_REPORT="$TEAMZ_DATA_DIR/seo-latest-report.txt"
if [ -f "$SEO_REPORT" ]; then
    echo ""
    echo ">>>TEAMZ-TRAILER<<<"
    echo "============================================="
    echo "  LATEST SEO AUTO-REPORT"
    echo "============================================="
    cat "$SEO_REPORT"
    echo "============================================="
fi
