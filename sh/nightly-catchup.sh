#!/bin/bash
#
# MORNING CATCH-UP SWEEP — re-run any property whose night did not actually work.
#
# WHY THIS EXISTS
#
# On 2026-07-12, the first unattended night, an upstream outage took out api.anthropic.com AND
# github.com at the same time. Two unrelated services do not fail together, so the fault was DNS
# or the ISP link. It ran from at least 22:31 to 23:01 and had cleared by 23:21 — thirty to fifty
# minutes.
#
# The damage: apps skipped its content agent and failed to deploy. learn did the same. tools
# enhanced nineteen pages, could not push, and left twenty commits stranded and invisible. Four
# properties, one night, effectively zero output — and the digest reported all of them green.
#
# Retrying inside the nightly is the right first move, but it can only ever buy minutes. No
# sensible amount of in-run waiting survives a 45-minute outage. The answer to a long outage is
# not more patience; it is TO COME BACK LATER.
#
# So: the runner writes data/nightly-status.json from an EXIT trap (it lands even when the build
# fails and the script exits 1). This sweep reads it in the morning, and re-runs any site whose
# night genuinely did not work. A night lost to a network blip now costs hours, not a day — and
# never silently.
#
# Deliberately NOT included: teamzlab-tools. It runs its own engine twice a day (15:00 and 21:00)
# and `git push` sends everything ahead of origin, so a stranded night self-heals on its next run.
#
# Install:  bash sh/nightly-catchup.sh --install
# Run now:  bash sh/nightly-catchup.sh

set -uo pipefail

PROJECTS="$(cd "$(dirname "$0")/../.." && pwd)"
LABEL="com.teamzlab.nightly-catchup"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$PROJECTS/teamz-company-automation/logs/$LABEL.log"

# Only re-run a site whose status is from LAST NIGHT. An older status file means the nightly is
# not running at all — a different problem, and re-running it here would just mask it.
MAX_AGE_HOURS="${TEAMZ_CATCHUP_MAX_AGE_HOURS:-16}"

if [ "${1:-}" = "--install" ]; then
  mkdir -p "$(dirname "$LOG")"
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$PROJECTS/teamz-company-automation/sh/nightly-catchup.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
PLISTEOF
  launchctl unload "$PLIST" 2>/dev/null
  launchctl load "$PLIST" && echo "Installed $LABEL — sweeps every morning at 08:30."
  exit 0
fi

echo "============================================================"
echo "  NIGHTLY CATCH-UP SWEEP — $(date '+%Y-%m-%d %H:%M')"
echo "============================================================"

RERAN=0
SKIPPED=0

# Derived from disk, never a hardcoded list. Two hardcoded lists that must agree by hand is the
# bug that made goalkit's Real Madrid hub invisible to Google and nearly deadlocked its nightly.
for env_file in "$PROJECTS"/*/.teamz-automation.env; do
  [ -f "$env_file" ] || continue
  repo="$(dirname "$env_file")"
  name="$(basename "$repo")"
  [ -x "$repo/scripts/nightly-site.sh" ] || [ -f "$repo/scripts/nightly-site.sh" ] || continue

  status_file="$repo/data/nightly-status.json"
  if [ ! -f "$status_file" ]; then
    echo "  $name — no status file yet (has not run under the new runner). Skipping."
    continue
  fi

  verdict="$(python3 - "$status_file" "$MAX_AGE_HOURS" <<'PY'
import json, sys, datetime
path, max_age = sys.argv[1], float(sys.argv[2])
try:
    s = json.load(open(path))
except Exception:
    print("unreadable"); raise SystemExit
try:
    ts = datetime.datetime.fromisoformat(s.get("finished_at", ""))
except Exception:
    print("no-timestamp"); raise SystemExit
age_h = (datetime.datetime.now() - ts).total_seconds() / 3600
if age_h > max_age:
    print(f"stale:{age_h:.0f}h"); raise SystemExit

content = s.get("content", "")
deploy = s.get("deploy", "")
build = s.get("build", "")
# A night "worked" only if the agent was not prevented from running AND the work reached the site.
broken = (
    content.startswith("skipped:api-unreachable")
    or content.startswith("failed")
    or build.startswith("failed")
    or deploy.startswith("failed")
)
print("RERUN" if broken else f"ok:{content}/{deploy}")
PY
)"

  case "$verdict" in
    RERUN)
      echo ""
      echo "  ▶ $name — last night did NOT work. Re-running."
      RERAN=$((RERAN + 1))
      ( cd "$repo" && bash scripts/nightly-site.sh 2>&1 | sed 's/^/      /' )
      ;;
    ok:*)
      echo "  $name — worked (${verdict#ok:}). Nothing to do."
      SKIPPED=$((SKIPPED + 1))
      ;;
    stale:*)
      echo "  ⚠️  $name — status is ${verdict#stale:} old. The NIGHTLY ITSELF is not running;"
      echo "      re-running it here would only hide that. Check its launchd job."
      ;;
    *)
      echo "  ⚠️  $name — status file unreadable ($verdict)."
      ;;
  esac
done

echo ""
echo "============================================================"
echo "  re-ran: $RERAN    already fine: $SKIPPED"
echo "  DONE — $(date '+%H:%M:%S')"
echo "============================================================"
