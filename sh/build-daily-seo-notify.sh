#!/bin/bash
# ============================================================
#  SEO Auto-Runner WITH Notifications
#  Runs SEO tasks + sends macOS notification + writes summary
#  for Claude health check to read.
# ============================================================

_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$_SCRIPT")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/config.sh"
teamz_load_config "$_SCRIPT"
cd "$TEAMZ_HOST_SITE_ROOT"

MODE="${1:---daily}"
DATE=$(date '+%Y-%m-%d %H:%M')
LOG_DIR="$TEAMZ_DATA_DIR/seo-logs"
REPORT_FILE="$TEAMZ_DATA_DIR/seo-latest-report.txt"
mkdir -p "$LOG_DIR"

HEALTH_ALERTS=()

extract_health_issue() {
    printf '%s\n' "$1" | grep -m1 -E 'ERROR:|FAILED|Traceback|token refresh failed|No Search Console token|Could not get Search Console token|✗ ' || true
}

record_health_alert() {
    HEALTH_ALERTS+=("$1")
}

run_capture() {
    local label="$1"
    shift
    local output exit_code issue_line
    output=$("$@" 2>&1)
    exit_code=$?
    issue_line=$(extract_health_issue "$output")
    if [ "$exit_code" -ne 0 ]; then
        record_health_alert "$label failed (exit $exit_code)"
    elif [ -n "$issue_line" ]; then
        record_health_alert "$label: $issue_line"
    fi
    printf '%s' "$output"
}

write_health_section() {
    if [ "${#HEALTH_ALERTS[@]}" -eq 0 ]; then
        echo "SCRIPT HEALTH: OK"
    else
        echo "SCRIPT HEALTH: REVIEW NEEDED (${#HEALTH_ALERTS[@]} issues)"
        for item in "${HEALTH_ALERTS[@]}"; do
            echo "  - $item"
        done
    fi
}

# ── DAILY ──
if [[ "$MODE" == "--daily" ]]; then
    # Record rankings
    OUTPUT=$(run_capture "Rank tracker record" python3 scripts/build-rank-tracker.py record)
    KEYWORDS=$(echo "$OUTPUT" | grep -o '[0-9]* keywords' | head -1)

    # Check movers
    MOVERS=$(run_capture "Rank tracker movers" python3 scripts/build-rank-tracker.py movers)
    WINNERS=$(echo "$MOVERS" | grep "improved" | grep -o '[0-9]*' | head -1)
    LOSERS=$(echo "$MOVERS" | grep "declined" | grep -o '[0-9]*' | head -1)
    WINNERS=${WINNERS:-0}
    LOSERS=${LOSERS:-0}

    # Uptime + anomalies (quick daily checks)
    run_capture "Uptime check" python3 scripts/build-uptime-check.py > /dev/null
    run_capture "GSC anomalies" python3 scripts/build-gsc-anomalies.py --json-only > /dev/null

    # Write summary for Claude health check
    {
        echo "DAILY SEO REPORT — $DATE"
        echo "Mode: daily"
        echo "Keywords tracked: $KEYWORDS"
        echo "Rank changes: $WINNERS improved, $LOSERS declined"
        echo "---"
        write_health_section
        echo "---"
        echo "Run 'python3 scripts/build-rank-tracker.py report' for details"
        echo "Run 'python3 scripts/build-rank-tracker.py movers' for biggest changes"
    } > "$REPORT_FILE"

    # macOS notification
    osascript -e "display notification \"$KEYWORDS tracked. $WINNERS up, $LOSERS down.\" with title \"SEO Daily\" subtitle \"Rank Tracker Updated\"" 2>/dev/null

    # Log
    echo "[$DATE] Daily: $KEYWORDS, $WINNERS up, $LOSERS down" >> "$LOG_DIR/daily.log"
fi

# ── WEEKLY ──
if [[ "$MODE" == "--weekly" ]]; then
    # Opportunities
    OPPS=$(run_capture "Keyword opportunities" python3 scripts/build-keyword-intel.py --opportunities)
    OPP_COUNT=$(echo "$OPPS" | grep -o 'Total opportunities: [0-9]*' | grep -o '[0-9]*')

    # Backlinks scan
    BL=$(run_capture "Backlinks overview scan" python3 scripts/build-backlinks-overview.py scan)
    BL_COUNT=$(echo "$BL" | grep -o 'Total links found: [0-9]*' | grep -o '[0-9]*')

    # Pending directories
    DIR=$(run_capture "Backlinks status" python3 scripts/build-backlinks.py status)
    DIR_PENDING=$(echo "$DIR" | grep -o 'Pending:.*[0-9]*' | grep -o '[0-9]*')

    # Content ideas
    run_capture "Seasonal content ideas" python3 scripts/build-content-ideas.py --seasonal > /dev/null

    # Weekly monitoring
    run_capture "Crawl diff" python3 scripts/build-crawl-diff.py > /dev/null
    run_capture "SERP tracker" python3 scripts/build-serp-tracker.py > /dev/null
    run_capture "Reddit scanner" python3 scripts/build-reddit-scanner.py > /dev/null

    # Write summary
    {
        echo "WEEKLY SEO REPORT — $DATE"
        echo "Mode: weekly"
        echo "Keyword opportunities: $OPP_COUNT"
        echo "Backlinks found: $BL_COUNT"
        echo "Directories pending: $DIR_PENDING"
        echo "---"
        write_health_section
        echo "---"
        echo "ACTION NEEDED:"
        echo "  1. Run: python3 scripts/build-backlinks.py submit  (submit to 5 directories)"
        echo "  2. Run: python3 scripts/build-keyword-intel.py --opportunities  (see quick wins)"
        echo "  3. Run: python3 scripts/build-content-ideas.py --trending  (see what to build)"
    } > "$REPORT_FILE"

    # macOS notification
    osascript -e "display notification \"$OPP_COUNT opportunities. $DIR_PENDING directories pending. $BL_COUNT backlinks.\" with title \"SEO Weekly\" subtitle \"Action needed: submit to directories\"" 2>/dev/null

    echo "[$DATE] Weekly: $OPP_COUNT opps, $BL_COUNT backlinks, $DIR_PENDING dirs pending" >> "$LOG_DIR/weekly.log"
fi

# ── MONTHLY ──
if [[ "$MODE" == "--monthly" ]]; then
    # Full dashboard
    DASH=$(run_capture "SEO dashboard" ./scripts/build-seo-dashboard.sh --quick)

    # Content gaps
    GAPS=$(run_capture "Content gaps" python3 scripts/build-content-ideas.py --gaps)
    GAP_COUNT=$(echo "$GAPS" | grep -o '[0-9]* content gaps' | grep -o '[0-9]*')

    # Full keyword report
    KW=$(run_capture "Keyword report" python3 scripts/build-keyword-intel.py --top 30)

    # Indexing check
    run_capture "Indexing check" python3 scripts/build-request-indexing.py --check > /dev/null

    # Monthly deep monitoring
    run_capture "Schema validation" python3 scripts/build-schema-validate.py > /dev/null
    run_capture "Competitor gaps" python3 scripts/build-competitor-gaps.py > /dev/null
    run_capture "Topic clusters" python3 scripts/build-topic-cluster-report.py > /dev/null

    {
        echo "MONTHLY SEO REPORT — $DATE"
        echo "Mode: monthly"
        echo "Content gaps found: $GAP_COUNT"
        echo "---"
        write_health_section
        echo "---"
        echo "ACTION NEEDED:"
        echo "  1. Review: python3 scripts/build-keyword-intel.py --top 30  (keyword rankings)"
        echo "  2. Review: python3 scripts/build-content-ideas.py --gaps  (what to build next)"
        echo "  3. Review: ./scripts/build-seo-dashboard.sh  (full dashboard)"
        echo "  4. Review: python3 scripts/build-backlinks-overview.py report  (backlink health)"
    } > "$REPORT_FILE"

    osascript -e "display notification \"Monthly audit complete. $GAP_COUNT content gaps found.\" with title \"SEO Monthly\" subtitle \"Review your dashboard\"" 2>/dev/null

    echo "[$DATE] Monthly: $GAP_COUNT gaps" >> "$LOG_DIR/monthly.log"
fi
