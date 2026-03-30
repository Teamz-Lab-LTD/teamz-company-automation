#!/bin/bash
# ============================================================
#  Teamz Lab Tools — Smart Catch-Up Runner
#  Detects what's stale and runs only what's needed.
#  Called by health check at START of every Claude conversation.
#
#  Logic:
#    - If rank tracker hasn't run today → run it
#    - If weekly scan hasn't run this week → run it
#    - If monthly audit hasn't run this month → run it
#    - If away for 30+ days → run full catch-up + suggest new tools
#    - Always shows actionable summary
#
#  Usage:
#    ./build-catchup.sh           # Auto-detect and catch up
#    ./build-catchup.sh --status  # Just show what's stale (no run)
# ============================================================

_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
SCRIPTS="$(cd "$(dirname "$_SCRIPT")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPTS/lib/config.sh"
teamz_load_config "$_SCRIPT"
cd "$TEAMZ_HOST_SITE_ROOT"

MODE="${1:---run}"
NOW=$(date +%s)
TODAY=$(date +%Y-%m-%d)
THIS_WEEK=$(date +%Y-%W)
THIS_MONTH=$(date +%Y-%m)
ACTIONS=()
STALE_COUNT=0
HEALTH_ALERTS=()

echo ""
echo "============================================="
echo "  SMART CATCH-UP CHECK — $TODAY"
echo "============================================="

# ── Helper: get file age in days ──
file_age_days() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo "9999"
        return
    fi
    local mod=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file" 2>/dev/null || echo "0")
    local age=$(( (NOW - mod) / 86400 ))
    echo "$age"
}

extract_health_issue() {
    printf '%s\n' "$1" | grep -m1 -E 'ERROR:|FAILED|Traceback|token refresh failed|No Search Console token|Could not get Search Console token|✗ ' || true
}

record_health_alert() {
    HEALTH_ALERTS+=("$1")
}

# ── 1. Rank Tracker ──
RANK_FILE="$TEAMZ_DATA_DIR/rank-history.json"
RANK_AGE=$(file_age_days "$RANK_FILE")
if [ "$RANK_AGE" -ge 1 ]; then
    echo "  [!] Rank tracker: last run ${RANK_AGE} days ago"
    STALE_COUNT=$((STALE_COUNT + 1))
    ACTIONS+=("rank")
else
    echo "  [ok] Rank tracker: up to date (today)"
fi

# ── 2. Backlinks Overview ──
BL_FILE="$TEAMZ_DATA_DIR/backlinks-data.json"
BL_AGE=$(file_age_days "$BL_FILE")
if [ "$BL_AGE" -ge 7 ]; then
    echo "  [!] Backlinks scan: last run ${BL_AGE} days ago (weekly)"
    STALE_COUNT=$((STALE_COUNT + 1))
    ACTIONS+=("backlinks")
else
    echo "  [ok] Backlinks scan: up to date (${BL_AGE}d ago)"
fi

# ── 3. Keyword Intel ──
# Check if opportunities were reviewed this week
KW_LOG="$TEAMZ_DATA_DIR/seo-logs/weekly.log"
KW_AGE=$(file_age_days "$KW_LOG")
if [ "$KW_AGE" -ge 7 ]; then
    echo "  [!] Keyword opportunities: not checked this week"
    STALE_COUNT=$((STALE_COUNT + 1))
    ACTIONS+=("keywords")
else
    echo "  [ok] Keyword opportunities: checked ${KW_AGE}d ago"
fi

# ── 4. Directory Submissions ──
DIR_FILE="$TEAMZ_DATA_DIR/backlinks-history.json"
DIR_AGE=$(file_age_days "$DIR_FILE")
PENDING=$(python3 -c "
import json
from pathlib import Path
f = Path('$DIR_FILE')
if f.exists():
    h = json.loads(f.read_text())
    print(39 - len(h))
else:
    print(39)
" 2>/dev/null || echo "39")
if [ "$PENDING" -gt 0 ]; then
    echo "  [!] Directory submissions: $PENDING pending (of 39)"
    ACTIONS+=("directories")
else
    echo "  [ok] All directories submitted"
fi

# ── 5. Content Freshness ──
CONTENT_AGE=$(file_age_days "$TEAMZ_DATA_DIR/seo-logs/monthly.log")
if [ "$CONTENT_AGE" -ge 30 ]; then
    echo "  [!] Monthly audit: last run ${CONTENT_AGE} days ago"
    STALE_COUNT=$((STALE_COUNT + 1))
    ACTIONS+=("monthly")
else
    echo "  [ok] Monthly audit: ${CONTENT_AGE}d ago"
fi

# ── 6. Seasonal Check ──
MONTH=$(date +%-m)
case $MONTH in
    1)  SEASONAL="Tax season prep, New Year resolution tools, budget calculators" ;;
    2)  SEASONAL="Valentine tools, heart health, tax refund estimator" ;;
    3)  SEASONAL="Tax filing deadline, Ramadan tools, spring cleaning, Eid prep" ;;
    4)  SEASONAL="Tax deadline (Apr 15!), Eid tools, Earth Day, spring allergy" ;;
    5)  SEASONAL="Mother's Day, graduation tools, summer budget planner" ;;
    6)  SEASONAL="Father's Day, summer vacation budget, back-to-school prep" ;;
    7)  SEASONAL="Summer fitness, vacation cost calculator, heat index" ;;
    8)  SEASONAL="Back to school, college cost calculator, football season" ;;
    9)  SEASONAL="Fall budget reset, school year planner, Apple event tools" ;;
    10) SEASONAL="Halloween tools, holiday budget planner, Black Friday prep" ;;
    11) SEASONAL="Black Friday calculator, Thanksgiving, Cyber Monday, gift budget" ;;
    12) SEASONAL="Christmas tools, New Year countdown, year-in-review, annual tax recap" ;;
esac

# ── 7. Away Detection ──
AWAY_DAYS=$RANK_AGE
if [ "$AWAY_DAYS" -ge 30 ]; then
    echo ""
    echo "  *** WELCOME BACK! You've been away ${AWAY_DAYS} days. ***"
    echo "  Running full catch-up..."
    ACTIONS=("rank" "backlinks" "keywords" "monthly" "directories")
fi

echo ""
echo "  Seasonal opportunities this month:"
echo "    $SEASONAL"
echo ""

# ── Execute or just report ──
if [[ "$MODE" == "--status" ]]; then
    echo "  Status only (no scripts executed)."
    echo "  Run ./build-catchup.sh to execute catch-up."
    echo ""
    echo "============================================="
    return 0 2>/dev/null || exit 0
fi

if [ ${#ACTIONS[@]} -eq 0 ]; then
    echo "  Everything is up to date! No catch-up needed."
    echo ""
    echo "============================================="
    return 0 2>/dev/null || exit 0
fi

echo "  Running ${#ACTIONS[@]} catch-up tasks..."
echo ""

for action in "${ACTIONS[@]}"; do
    case $action in
        rank)
            echo "  --> Recording keyword rankings..."
            OUTPUT=$(python3 scripts/build-rank-tracker.py record 2>&1)
            ISSUE=$(extract_health_issue "$OUTPUT")
            if [ -n "$ISSUE" ]; then
                record_health_alert "Rank tracker record: $ISSUE"
            fi
            printf '%s\n' "$OUTPUT" | grep -E "Recorded|Total"
            echo ""
            ;;
        backlinks)
            echo "  --> Scanning backlinks..."
            OUTPUT=$(python3 scripts/build-backlinks-overview.py scan 2>&1)
            ISSUE=$(extract_health_issue "$OUTPUT")
            if [ -n "$ISSUE" ]; then
                record_health_alert "Backlinks scan: $ISSUE"
            fi
            printf '%s\n' "$OUTPUT" | grep -E "Found|Total|DoFollow"
            echo ""
            ;;
        keywords)
            echo "  --> Finding keyword opportunities..."
            OUTPUT=$(python3 scripts/build-keyword-intel.py --opportunities 2>&1)
            ISSUE=$(extract_health_issue "$OUTPUT")
            if [ -n "$ISSUE" ]; then
                record_health_alert "Keyword opportunities: $ISSUE"
            fi
            printf '%s\n' "$OUTPUT" | tail -8
            echo ""
            ;;
        monthly)
            echo "  --> Running SEO dashboard..."
            OUTPUT=$(./scripts/build-seo-dashboard.sh --quick 2>&1)
            ISSUE=$(extract_health_issue "$OUTPUT")
            if [ -n "$ISSUE" ]; then
                record_health_alert "SEO dashboard: $ISSUE"
            fi
            printf '%s\n' "$OUTPUT" | tail -15
            echo ""
            echo "  --> Finding content gaps..."
            OUTPUT=$(python3 scripts/build-content-ideas.py --gaps 2>&1)
            ISSUE=$(extract_health_issue "$OUTPUT")
            if [ -n "$ISSUE" ]; then
                record_health_alert "Content gaps: $ISSUE"
            fi
            printf '%s\n' "$OUTPUT" | tail -8
            echo ""
            ;;
        directories)
            echo "  --> Directory submission status:"
            OUTPUT=$(python3 scripts/build-backlinks.py status 2>&1)
            ISSUE=$(extract_health_issue "$OUTPUT")
            if [ -n "$ISSUE" ]; then
                record_health_alert "Directory status: $ISSUE"
            fi
            printf '%s\n' "$OUTPUT" | grep -E "Submitted|Pending|PRIORITY"
            echo ""
            ;;
    esac
done

# ── Write latest report for future reference ──
mkdir -p "$TEAMZ_DATA_DIR/seo-logs"
cat > "$TEAMZ_DATA_DIR/seo-latest-report.txt" << EOF
CATCH-UP REPORT — $TODAY
Stale items fixed: $STALE_COUNT
Tasks run: ${ACTIONS[*]}
Seasonal: $SEASONAL
---
SCRIPT HEALTH: $([ ${#HEALTH_ALERTS[@]} -eq 0 ] && echo "OK" || echo "REVIEW NEEDED (${#HEALTH_ALERTS[@]} issues)")
$(for item in "${HEALTH_ALERTS[@]}"; do echo "  - $item"; done)
---
SUGGESTED NEXT ACTIONS:
  1. python3 scripts/build-backlinks.py submit     # Submit to 5 directories ($PENDING pending)
  2. python3 scripts/build-content-ideas.py --trending  # See what to build
  3. python3 scripts/build-rank-tracker.py movers  # Check biggest rank changes
  4. python3 scripts/build-content-ideas.py --seasonal  # Seasonal tool ideas
EOF

echo "============================================="
echo "  Catch-up complete! $STALE_COUNT items updated."
echo ""
echo "  SUGGESTED NEXT ACTIONS:"
echo "    1. python3 scripts/build-backlinks.py submit     # Submit to directories"
echo "    2. python3 scripts/build-content-ideas.py --trending  # What to build"
echo "    3. python3 scripts/build-rank-tracker.py movers  # Rank changes"
echo ""
echo "============================================="
