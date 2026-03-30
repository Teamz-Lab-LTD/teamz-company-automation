#!/bin/bash
# =============================================================================
# Continuous Build — Builds tools while you're away
#
# Usage:
#   bash scripts/continuous-build.sh 3h             # Sonnet, 3 hours (default)
#   bash scripts/continuous-build.sh 5h opus         # Opus, 5 hours (higher quality)
#   bash scripts/continuous-build.sh 90m             # Sonnet, 90 minutes
#   bash scripts/continuous-build.sh --scripts 2h   # Only maintenance, no Claude
#   bash scripts/continuous-build.sh stop            # Stop from another terminal
#
# Smart quota: max 3 builds per session. Maintenance in between.
# =============================================================================

_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
_SCRIPT_DIR="$(cd "$(dirname "$_SCRIPT")" && pwd)"
# shellcheck disable=SC1091
source "$_SCRIPT_DIR/lib/config.sh"
teamz_load_config "$_SCRIPT"
PROJECT_DIR="$TEAMZ_HOST_SITE_ROOT"
LOCK_FILE="$PROJECT_DIR/.continuous-build.lock"
LOG_FILE="$PROJECT_DIR/logs/continuous-build.log"

# Parse arguments
MODE="safe"
DURATION_MIN=0
MODEL="sonnet"
for arg in "$@"; do
    case "$arg" in
        --scripts) MODE="scripts" ;;
        --max) MODE="max" ;;
        stop) MODE="stop" ;;
        opus) MODEL="opus" ;;
        sonnet) MODEL="sonnet" ;;
        *h) DURATION_MIN=$(( ${arg%h} * 60 )) ;;
        *m) DURATION_MIN=${arg%m} ;;
    esac
done

# Default: 2 hours if no time given
if [ "$DURATION_MIN" -eq 0 ] && [ "$MODE" != "stop" ]; then
    DURATION_MIN=120
fi

START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION_MIN * 60))
RETURN_TIME=$(date -r "$END_TIME" '+%I:%M %p' 2>/dev/null || date -d "@$END_TIME" '+%I:%M %p' 2>/dev/null)

# Max 3 Claude builds per session to preserve quota for daytime manual work
MAX_BUILDS=3

if [ "$MODE" = "stop" ]; then
    if [ -f "$LOCK_FILE" ]; then
        kill "$(cat "$LOCK_FILE")" 2>/dev/null
        rm -f "$LOCK_FILE"
        echo "Continuous build stopped."
    else
        echo "Not running."
    fi
    exit 0
fi

# Prevent double-run
if [ -f "$LOCK_FILE" ] && kill -0 "$(cat "$LOCK_FILE")" 2>/dev/null; then
    echo "Already running (PID $(cat "$LOCK_FILE")). Stop with: bash scripts/continuous-build.sh stop"
    exit 1
fi

mkdir -p "$PROJECT_DIR/logs"
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"; echo "Stopped."; exit 0' INT TERM

cd "$PROJECT_DIR" || exit 1

echo "============================================================" | tee -a "$LOG_FILE"
echo "  CONTINUOUS BUILD — $(date '+%Y-%m-%d %H:%M %Z')" | tee -a "$LOG_FILE"
echo "  Duration: ${DURATION_MIN} minutes | Stops at: $RETURN_TIME" | tee -a "$LOG_FILE"
echo "  Mode: $MODE | Model: $MODEL | Max builds: $MAX_BUILDS" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"

BUILDS_DONE=0

time_remaining() {
    local now=$(date +%s)
    local left=$(( (END_TIME - now) / 60 ))
    echo "$left"
}

# Main loop
while true; do
    # Check if time is up
    REMAINING=$(time_remaining)
    if [ "$REMAINING" -le 5 ]; then
        echo "" | tee -a "$LOG_FILE"
        echo "  Time's up! Stopping. You should be back soon." | tee -a "$LOG_FILE"
        echo "  Built $BUILDS_DONE tool sets in this session." | tee -a "$LOG_FILE"
        break
    fi

    # Claude build (if allowed and time remaining > 30 min)
    if [ "$MODE" != "scripts" ] && [ "$BUILDS_DONE" -lt "$MAX_BUILDS" ] && [ "$REMAINING" -gt 30 ]; then
        BUILDS_DONE=$((BUILDS_DONE + 1))
        echo "" | tee -a "$LOG_FILE"
        echo "=== Claude Build #$BUILDS_DONE/$MAX_BUILDS — $(time_remaining)min left ===" | tee -a "$LOG_FILE"

        git pull origin main 2>/dev/null
        MODEL=$MODEL bash scripts/nightly-build.sh 2>&1 | tee -a "$LOG_FILE"
    fi

    # Check time again after build
    REMAINING=$(time_remaining)
    if [ "$REMAINING" -le 5 ]; then
        echo "  Time's up after build. Stopping." | tee -a "$LOG_FILE"
        break
    fi

    # Maintenance (ZERO quota)
    echo "" | tee -a "$LOG_FILE"
    echo "=== Maintenance — $(time_remaining)min left (no quota) ===" | tee -a "$LOG_FILE"

    python3 scripts/build-static-schema.py 2>&1 | tail -2
    ./scripts/build-search-index.sh 2>&1 | tail -3
    python3 scripts/build-fix-orphans.py fix 2>&1 | tail -3
    ./scripts/build-seo-audit.sh --fix 2>&1 | tail -3
    python3 scripts/build-request-indexing.py 2>&1 | tail -5

    # Commit and push
    if ! git diff --quiet 2>/dev/null; then
        git add -A
        git commit -m "Auto maintenance: schemas, search index, SEO fixes"
        git push origin main 2>/dev/null
        echo "  Pushed fixes." | tee -a "$LOG_FILE"
    fi

    # Wait 10 min before next cycle (or exit if time is up)
    REMAINING=$(time_remaining)
    if [ "$REMAINING" -le 10 ]; then
        echo "  Almost time. Stopping." | tee -a "$LOG_FILE"
        break
    fi

    echo "  Starting next build immediately..." | tee -a "$LOG_FILE"
done

# Final summary
echo "" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"
echo "  SESSION COMPLETE — $(date '+%H:%M %Z')" | tee -a "$LOG_FILE"
echo "  Claude builds: $BUILDS_DONE" | tee -a "$LOG_FILE"
echo "  Check results: git log --oneline --since='${DURATION_MIN} minutes ago'" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"

rm -f "$LOCK_FILE"
