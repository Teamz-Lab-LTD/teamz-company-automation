#!/bin/bash
# ─── SEO & ASO Keyword Engine — Teamz Lab Tools ───────────────────
# Wrapper script for the SEO + ASO keyword engine.
# Works for websites AND mobile apps (App Store + Play Store).
#
# SEO (Web):
#   ./build-seo-audit.sh                          # Quick audit
#   ./build-seo-audit.sh --verbose                # Verbose audit
#   ./build-seo-audit.sh --report                 # Full report
#   ./build-seo-audit.sh --suggest "keyword"      # Web keyword suggestions
#   ./build-seo-audit.sh --trends "keyword"       # Google Trends
#   ./build-seo-audit.sh --trends "kw1" "kw2"    # Compare keywords
#   ./build-seo-audit.sh --validate-new "keyword" # Validate new tool
#   ./build-seo-audit.sh --internal-links         # Internal linking check
#   ./build-seo-audit.sh --batch-trends           # Trends all hubs
#   ./build-seo-audit.sh --freshness              # Content freshness
#   ./build-seo-audit.sh --viral                  # Virality check
#   ./build-seo-audit.sh --cannibalize            # Keyword conflicts
#   ./build-seo-audit.sh --fix-dry-run            # Preview fixes
#
# ASO (Mobile Apps):
#   ./build-seo-audit.sh --aso-suggest "keyword"                     # App Store + Play suggestions
#   ./build-seo-audit.sh --aso-suggest "keyword" --store apple       # Apple only
#   ./build-seo-audit.sh --aso-suggest "keyword" --country bd        # Bangladesh market
#   ./build-seo-audit.sh --aso-audit --title "App" --subtitle "Tag"  # Audit app metadata
#   ./build-seo-audit.sh --aso-validate "habit tracker"              # Validate app idea
#   ./build-seo-audit.sh --aso-compare "Name A" "Name B"            # Compare app names
# ────────────────────────────────────────────────────────────────────

SCRIPTS="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")" && pwd)"
source "$SCRIPTS/lib/config.sh"
teamz_load_config "$0"
PY_DIR="$TEAMZ_AUTOMATION_ROOT/py"
SCRIPT="$PY_DIR/seo-keyword-engine.py"

if [ ! -f "$SCRIPT" ]; then
    echo "ERROR: seo-keyword-engine.py not found at $SCRIPT"
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is required"
    exit 1
fi

WEB_ONLY_COMMANDS="--report --internal-links --batch-trends --freshness --viral --cannibalize --fix-dry-run --fix --verbose -v audit"
CMD="${1:-audit}"

if [[ "$TEAMZ_PROJECT_TYPE" == "app" ]]; then
  for web_cmd in $WEB_ONLY_COMMANDS; do
    if [[ "$CMD" == "$web_cmd" ]]; then
      echo "INFO: '$CMD' is website-focused and disabled for TEAMZ_PROJECT_TYPE=app."
      echo "      Use ASO commands instead: --aso-suggest, --aso-audit, --aso-validate, --aso-compare."
      exit 2
    fi
  done
fi

case "$CMD" in
    --report)
        python3 "$SCRIPT" report
        ;;
    --suggest)
        shift
        python3 "$SCRIPT" suggest "$@"
        ;;
    --trends)
        shift
        python3 "$SCRIPT" trends "$@"
        ;;
    --validate-new)
        shift
        python3 "$SCRIPT" validate-new "$@"
        ;;
    --bing-stats)
        python3 "$SCRIPT" bing-stats
        ;;
    --internal-links)
        python3 "$SCRIPT" internal-links
        ;;
    --batch-trends)
        python3 "$SCRIPT" batch-trends
        ;;
    --freshness)
        python3 "$SCRIPT" freshness
        ;;
    --viral)
        python3 "$SCRIPT" viral
        ;;
    --cannibalize)
        python3 "$SCRIPT" cannibalize
        ;;
    --fix-dry-run)
        python3 "$SCRIPT" fix --dry-run
        ;;
    --fix)
        python3 "$SCRIPT" fix
        ;;
    --ph-search)
        shift
        python3 "$SCRIPT" ph-search "$@"
        ;;
    --ph-trending)
        python3 "$SCRIPT" ph-trending
        ;;
    --aso-suggest)
        shift
        python3 "$SCRIPT" aso-suggest "$@"
        ;;
    --aso-audit)
        shift
        python3 "$SCRIPT" aso-audit "$@"
        ;;
    --aso-validate)
        shift
        python3 "$SCRIPT" aso-validate "$@"
        ;;
    --aso-compare)
        shift
        python3 "$SCRIPT" aso-compare "$@"
        ;;
    --volume)
        shift
        python3 "$PY_DIR/build-keyword-volume.py" "$@"
        ;;
    --volume-bulk)
        python3 "$PY_DIR/build-keyword-volume.py" --bulk
        ;;
    --bing-volume)
        shift
        # Quick Bing-only volume lookup (no Google signals, just Bing API)
        BING_KEY_FILE="${TEAMZ_BING_API_KEY_FILE:-$HOME/.config/teamzlab/bing-webmaster-api-key.txt}"
        BING_KEY=$(cat "$BING_KEY_FILE" 2>/dev/null)
        if [ -z "$BING_KEY" ]; then echo "ERROR: No Bing API key at $BING_KEY_FILE"; exit 1; fi
        for kw in "$@"; do
            encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$kw'))")
            data=$(curl -s "https://ssl.bing.com/webmaster/api.svc/json/GetKeywordStats?q=${encoded}&country=us&language=en-US&apikey=${BING_KEY}")
            python3 -c "
import json, sys
data = json.loads('$data'.replace(\"'\", \"\"))
entries = data.get('d', [])
if not entries:
    print(f'  $kw: No data')
else:
    exact = sum(e.get('Impressions',0) for e in entries) // len(entries)
    broad = sum(e.get('BroadImpressions',0) for e in entries) // len(entries)
    print(f'  $kw: {exact*4:,}/mo exact | {broad*4:,}/mo broad ({len(entries)} weeks)')
" 2>/dev/null || echo "  $kw: API error"
        done
        ;;
    --verbose|-v)
        python3 "$SCRIPT" audit --verbose
        ;;
    audit|*)
        python3 "$SCRIPT" audit
        ;;
esac
