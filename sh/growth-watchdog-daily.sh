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

# Revenue watchdog runs alongside, never inside, the health one. They answer
# different questions and must fail independently: "did the machine run" is
# not "is the business still earning", and a break in either must not hide
# the other's verdict. Added 2026-08-13 — until then nothing in this repo
# watched money at all, while 31% of revenue sat on a single URL.
echo
echo "--- revenue watchdog ---"
python3 "$ROOT/py/build-revenue-watchdog.py"
rev_rc=$?

# Event windows. The calendar has always carried the DATE and the INSTRUCTION
# ("refresh existing UCL pages Aug 20-28, build NOTHING new"), and the digest has
# always been able to print them — but the digest only ever ran when the owner
# typed /growth. Nothing pushed. So on 2026-08-14 he had to ask six questions in a
# row to discover a decision that was already written down, dated, and five days
# from its window opening. A calendar nobody is shown is a diary, not a reminder.
#
# Now the digest is regenerated nightly and any OPEN or LATE window notifies. The
# window drives the alert, not the status field: "live" means the page exists, it
# does not mean this season's work is done.
echo
echo "--- growth digest + event windows ---"
python3 "$ROOT/py/build-growth-digest.py" >/dev/null 2>&1
dig_rc=$?
if [ "$dig_rc" -ne 0 ]; then
  echo "result: DIGEST FAILED (exit $dig_rc) — event windows are NOT being checked"
  osascript -e 'display notification "Growth digest failed — event build windows unchecked." with title "Teamz Growth Digest"' 2>/dev/null || true
else
  OPEN_N=$(grep -c "ACT THIS WEEK\|BUILD NOW" "$ROOT/docs/growth-digest.md" 2>/dev/null || echo 0)
  if [ "${OPEN_N:-0}" -gt 0 ]; then
    # Name them, don't just count them. "3 windows open" sends him to a file; the
    # event names tell him whether it matters before he opens anything.
    NAMES=$(grep -E "ACT THIS WEEK|BUILD NOW" "$ROOT/docs/growth-digest.md" \
            | sed -E 's/^\| *[0-9]+d \| [0-9-]+ \| ([^|]+) \|.*/\1/' | paste -sd '; ' - | cut -c1-160)
    echo "result: $OPEN_N event window(s) OPEN — $NAMES"
    osascript -e "display notification \"$OPEN_N open: $NAMES\" with title \"Teamz — event window open\"" 2>/dev/null || true
  else
    echo "result: no event build windows open"
  fi
fi

if [ "$rc" -ne 0 ]; then
  echo "result: WATCHDOG FAILED (exit $rc) — you are unmonitored until this is fixed"
  osascript -e 'display notification "Growth watchdog failed to run — you are unmonitored." with title "Teamz Growth Watchdog"' 2>/dev/null || true
fi

if [ "$rev_rc" -ne 0 ]; then
  echo "result: REVENUE WATCHDOG FAILED (exit $rev_rc) — revenue drops are NOT being watched"
  osascript -e 'display notification "Revenue watchdog failed to run — revenue drops are unwatched." with title "Teamz Revenue Watchdog"' 2>/dev/null || true
fi

# Non-zero if EITHER failed, so launchd's own status reflects both.
[ "$rc" -ne 0 ] && exit "$rc"
exit "$rev_rc"
