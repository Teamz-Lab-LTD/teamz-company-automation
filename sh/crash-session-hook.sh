#!/bin/bash
# SessionStart hook: surface this project's open crashes to the coding agent.
#
# Why: the fleet crash report lives in teamz-company-automation/data/, which nobody opens
# while working inside an app repo. DeviceGPT carried a defect for three months and Hazira
# Khata — a paying-customer app — was never monitored at all. Writing the status into each
# repo is only half a fix; something has to *say it out loud* when work starts here.
#
# build-crashlytics-monitor.py writes .claude/crash-status.md into every app repo it scans.
# This hook prints it at session start, so it lands in the agent's context automatically.
#
# Design rules:
#   * Never block a session. Any failure exits 0 and stays silent.
#   * Never nag with stale data — a status older than MAX_AGE_DAYS is reported as stale
#     rather than as fact, because an old all-clear is exactly the lie we are fixing.
#   * Say nothing when there is nothing to say, so the signal keeps its meaning.

set -uo pipefail

STATUS_FILE="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/crash-status.md"
MAX_AGE_DAYS=3

[ -f "$STATUS_FILE" ] || exit 0

# A clean report is not worth spending context on.
if grep -q "No crashes in window" "$STATUS_FILE"; then
  exit 0
fi

# Freshness. `stat -f %m` is macOS; the GNU form is the fallback.
mtime=$(stat -f %m "$STATUS_FILE" 2>/dev/null || stat -c %Y "$STATUS_FILE" 2>/dev/null || echo 0)
now=$(date +%s)
age_days=$(( (now - mtime) / 86400 ))

echo "⚠️  OPEN CRASHES IN THIS PROJECT"
echo

if [ "$age_days" -gt "$MAX_AGE_DAYS" ]; then
  echo "NOTE: this status is ${age_days} days old — the monitor has not run recently."
  echo "Re-run before trusting it:"
  echo "  python3 teamz-company-automation/py/build-crashlytics-monitor.py --dry-run"
  echo
fi

cat "$STATUS_FILE"
echo
echo "Raised automatically by crash-session-hook.sh. Mention this to the user early;"
echo "do not silently start unrelated work while a CRITICAL crash is open."

exit 0
