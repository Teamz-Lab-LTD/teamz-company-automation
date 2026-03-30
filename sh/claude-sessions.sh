#!/bin/bash
# =============================================================================
# Claude Session Manager — See and kill stale Claude processes
#
# Usage:
#   bash scripts/claude-sessions.sh           # List all sessions
#   bash scripts/claude-sessions.sh --kill-old # Kill sessions older than 24h
# =============================================================================

echo "============================================================"
echo "  CLAUDE SESSIONS — $(date '+%Y-%m-%d %H:%M %Z')"
echo "============================================================"
echo ""

# Get current time in seconds
NOW=$(date +%s)

count=0
old_count=0
old_pids=""

while IFS= read -r line; do
    pid=$(echo "$line" | awk '{print $1}')
    # Get start time
    started=$(ps -p "$pid" -o lstart= 2>/dev/null)
    if [ -z "$started" ]; then continue; fi

    start_sec=$(date -j -f "%c" "$started" +%s 2>/dev/null)
    if [ -z "$start_sec" ]; then continue; fi

    age_sec=$((NOW - start_sec))
    age_hours=$((age_sec / 3600))
    age_days=$((age_hours / 24))

    # Get model
    model="default"
    echo "$line" | grep -q "opus" && model="opus"
    echo "$line" | grep -q "sonnet" && model="sonnet"

    # Get memory usage
    mem=$(ps -p "$pid" -o rss= 2>/dev/null | awk '{printf "%.0f", $1/1024}')

    # Determine status
    if [ "$age_hours" -gt 24 ]; then
        status="OLD (${age_days}d ${age_hours}h)"
        old_count=$((old_count + 1))
        old_pids="$old_pids $pid"
    elif [ "$age_hours" -gt 4 ]; then
        status="STALE (${age_hours}h)"
        old_count=$((old_count + 1))
        old_pids="$old_pids $pid"
    else
        status="ACTIVE (${age_hours}h)"
    fi

    count=$((count + 1))
    printf "  PID %-7s | %-8s | %4sMB RAM | %s | %s\n" "$pid" "$model" "$mem" "$status" "$started"

done < <(ps aux | grep "[c]laude.*--output-format" | awk '{print $0}')

echo ""
echo "  Total: $count sessions | Old/Stale: $old_count"

if [ "$old_count" -gt 0 ]; then
    echo ""
    echo "  Old PIDs:$old_pids"
    echo "  Kill them: bash scripts/claude-sessions.sh --kill-old"
fi

# Kill old sessions
if [ "$1" = "--kill-old" ] && [ "$old_count" -gt 0 ]; then
    echo ""
    echo "  Killing $old_count old sessions..."
    for pid in $old_pids; do
        kill "$pid" 2>/dev/null && echo "    Killed PID $pid" || echo "    Failed PID $pid"
    done
    echo "  Done. Run again to verify."
fi

echo ""
