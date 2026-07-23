#!/usr/bin/env bash
# Nightly cross-property watchdog. Wrapper around py/build-growth-watchdog.py
# for launchd (com.teamzlab.growth-watchdog). Runs the exact same thing by hand:
#
#   bash sh/growth-watchdog-daily.sh
#
# Scheduled for 23:55 — after all 4 properties' own nightly jobs have finished
# (apps 22:30, learn 23:00, goalkit 23:20, tools runs earlier at 15:00).
#
# If the watchdog script itself dies, that is worse than any single alert it
# might have found — silently unmonitored is the exact failure this exists to
# prevent, so a crash here notifies too, the same way build-crashlytics-monitor
# already does.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') growth-watchdog ==="

python3 "$ROOT/py/build-growth-watchdog.py"
rc=$?

if [ "$rc" -ne 0 ]; then
  echo "result: WATCHDOG FAILED (exit $rc) — you are unmonitored until this is fixed"
  osascript -e 'display notification "Growth watchdog failed to run — you are unmonitored." with title "Teamz Growth Watchdog"' 2>/dev/null || true
fi

exit "$rc"
