#!/usr/bin/env bash
# Daily Crashlytics sweep across every Teamz Lab app.
#
# Wrapper around py/build-crashlytics-monitor.py for launchd
# (com.teamzlab.crashlytics-daily). Keeps the plist trivial and lets you run the
# exact same thing by hand:
#
#   bash sh/crashlytics-monitor-daily.sh
#
# Exit codes from the monitor:
#   0  scanned cleanly, nothing new or critical
#   1  hard failure (auth dead, or self-test refused to trust the results)
#   2  critical issues found -- alerts were dispatched
#
# A hard failure is itself worth knowing about: if the monitor cannot run, you
# are blind again, which is the exact situation it exists to prevent. So on
# exit 1 we raise a desktop notification rather than dying quietly in a log.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

WINDOW_HOURS="${CRASHLYTICS_WINDOW_HOURS:-24}"

echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') crashlytics-monitor (window ${WINDOW_HOURS}h) ==="

python3 "$ROOT/py/build-crashlytics-monitor.py" --window-hours "$WINDOW_HOURS" "$@"
rc=$?

case "$rc" in
  0) echo "result: clean" ;;
  2) echo "result: CRITICAL issues found — alerts dispatched" ;;
  *)
    echo "result: MONITOR FAILED (exit $rc) — you are unmonitored until this is fixed"
    osascript -e 'display notification "Monitor failed to run — you are unmonitored." with title "Crashlytics Monitor"' 2>/dev/null || true
    ;;
esac

exit "$rc"
