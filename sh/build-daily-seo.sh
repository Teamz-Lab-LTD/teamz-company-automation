#!/bin/bash
# ============================================================
#  Teamz Lab Tools — Daily SEO Auto-Runner
#  Runs all SEO tasks automatically based on schedule.
#
#  Usage:
#    ./build-daily-seo.sh              # Morning routine (daily)
#    ./build-daily-seo.sh --weekly     # Weekly deep scan
#    ./build-daily-seo.sh --monthly    # Monthly full audit
#    ./build-daily-seo.sh --all        # Run everything
# ============================================================

set -e
_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$_SCRIPT")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/config.sh"
teamz_load_config "$_SCRIPT"
cd "$TEAMZ_HOST_SITE_ROOT"

MODE="${1:---daily}"
DATE=$(date '+%Y-%m-%d %H:%M')
LOG_DIR="$TEAMZ_DATA_DIR/seo-logs"
mkdir -p "$LOG_DIR"

echo ""
echo "============================================================"
echo "  SEO AUTO-RUNNER — $DATE"
echo "  Mode: $MODE"
echo "============================================================"
echo ""

# ── DAILY (every morning) ──
if [[ "$MODE" == "--daily" || "$MODE" == "--all" ]]; then
    echo "  [DAILY] Recording keyword rankings..."
    python3 scripts/build-rank-tracker.py record 2>&1 | tail -3

    echo "  [DAILY] Checking rank movers..."
    python3 scripts/build-rank-tracker.py movers 2>&1 | tail -10

    echo ""
    echo "  Daily tasks complete."
    echo ""
fi

# ── WEEKLY (every Monday) ──
if [[ "$MODE" == "--weekly" || "$MODE" == "--all" ]]; then
    echo "  [WEEKLY] Finding keyword opportunities..."
    python3 scripts/build-keyword-intel.py --opportunities 2>&1 | tail -25

    echo "  [WEEKLY] Checking trending content ideas..."
    python3 scripts/build-content-ideas.py --seasonal 2>&1

    echo "  [WEEKLY] Scanning backlinks..."
    python3 scripts/build-backlinks-overview.py scan 2>&1 | tail -10

    echo "  [WEEKLY] Pending directory submissions..."
    python3 scripts/build-backlinks.py status 2>&1 | grep -A5 "PRIORITY 1"

    echo ""
    echo "  Weekly tasks complete."
    echo "  ACTION NEEDED: Run 'python3 scripts/build-backlinks.py submit' to submit to directories."
    echo ""
fi

# ── MONTHLY (1st of month) ──
if [[ "$MODE" == "--monthly" || "$MODE" == "--all" ]]; then
    echo "  [MONTHLY] Full SEO dashboard..."
    ./scripts/build-seo-dashboard.sh --quick 2>&1 | tail -40

    echo "  [MONTHLY] Content gaps analysis..."
    python3 scripts/build-content-ideas.py --gaps 2>&1 | tail -30

    echo "  [MONTHLY] Full keyword report..."
    python3 scripts/build-keyword-intel.py --top 30 2>&1 | tail -40

    echo "  [MONTHLY] Requesting Google indexing for new pages..."
    python3 scripts/build-request-indexing.py --check 2>&1 | tail -10

    echo ""
    echo "  Monthly tasks complete."
    echo ""
fi

# Save log
LOG_FILE="$LOG_DIR/seo-$(date '+%Y%m%d').log"
echo "  Log saved to: $LOG_FILE"
echo "  Run at: $DATE | Mode: $MODE" >> "$LOG_FILE"
echo ""
