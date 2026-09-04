#!/usr/bin/env bash
# =============================================================================
# app-fleet-nightly.sh — store-signal collection for EVERY app in one job.
#
# Why this exists (2026-09-05 audit): 36 repos carried a scripts/nightly-app.sh
# symlink and exactly ONE (hazira-khata) had a launchd job. The other apps had
# no installs, no uninstalls, no vitals, no ratings pulled — ever. Nothing read
# the one file that was pulled. The web nightly could therefore "grow" an app
# whose users were uninstalling it the same week.
#
# One job, one manifest (data/app-fleet.json), one status file per app in that
# app's own automation_data (the same TEAMZ_DATA_DIR isolation nightly-app.sh
# uses, so /aso-refresh sees the same numbers). Then py/build-app-fleet-digest.py
# turns the pulls into one VERDICT per app.
#
# Usage:
#   bash sh/app-fleet-nightly.sh                 # all apps
#   bash sh/app-fleet-nightly.sh --only=goldmend # one app
#   bash sh/app-fleet-nightly.sh --dry-run       # print the plan, pull nothing
#
# launchd: com.teamzlab.app-fleet-nightly @ 10:30 (after hazira's own 10:00 job,
# which the manifest marks own_nightly=true so the fleet never double-pulls it).
# =============================================================================
set -uo pipefail

AUTOMATION="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$AUTOMATION/data/app-fleet.json"
FLEET_LOG_ROOT="$AUTOMATION/logs/app-fleet"
FLEET_LABEL="com.teamzlab.app-fleet-nightly"
PY_DIR="$AUTOMATION/py"
mkdir -p "$FLEET_LOG_ROOT"

# shellcheck disable=SC1091
. "$AUTOMATION/sh/lib/app-steps.sh"

BASE_ENV="${TEAMZ_BASE_ENV:-$HOME/.config/teamzlab/automation.base.env}"
if [ -f "$BASE_ENV" ]; then set -a; . "$BASE_ENV"; set +a; fi

DRY=0; ONLY=""
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --only=*) ONLY="${a#--only=}" ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

[ -f "$MANIFEST" ] || { echo "FATAL: manifest missing: $MANIFEST"; exit 2; }

run_app() {
  local slug="$1" pkg="$2" asc="$3" platforms="$4" repo="$5" data_dir="$6"
  local run_dir="$FLEET_LOG_ROOT/$slug"
  mkdir -p "$run_dir" "$data_dir"

  # PER-APP ENV, LAST WINS. The app repo's own .teamz-automation.env is loaded first
  # (keywords, countries, ASC ids), then the fleet's overrides. _teamz_config.py
  # re-reads the env file with override=True, so the overrides must live IN the file
  # it reads — which is why TEAMZ_AUTOMATION_ENV points at this merged copy. Without
  # it, the game kit's shared env (TEAMZ_PLAY_PACKAGE_NAME=arrowescape3d) would
  # relabel every other game's velocity pull as Arrow.
  local run_env="$run_dir/run.env"
  {
    if [ -f "$repo/.teamz-automation.env" ]; then cat "$repo/.teamz-automation.env"; fi
    echo
    echo "# --- fleet overrides, written by app-fleet-nightly.sh (last assignment wins) ---"
    echo "TEAMZ_DATA_DIR=\"$data_dir\""
    echo "TEAMZ_HOST_SITE_ROOT=\"$repo\""
    echo "TEAMZ_APP_SLUG=\"$slug\""
    echo "TEAMZ_PROJECT_TYPE=app"
    [ -n "$pkg" ] && echo "TEAMZ_PLAY_PACKAGE_NAME=\"$pkg\""
    [ -n "$asc" ] && { echo "TEAMZ_APP_IDS=\"$asc\""; echo "TEAMZ_APPLE_APP_ID=\"$asc\""; }
  } > "$run_env"
  set -a; . "$run_env"; set +a
  export TEAMZ_AUTOMATION_ENV="$run_env"
  export TEAMZ_DATA_DIR="$data_dir" TEAMZ_HOST_SITE_ROOT="$repo"

  STEPS=(); SLUG="$slug"; LABEL="$FLEET_LABEL"
  STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  STATUS_FILE="$data_dir/nightly-app-status.json"
  LOG_DIR="$run_dir"

  echo
  echo "=== $slug ($platforms) — $STARTED_AT"
  echo "    data: $data_dir"
  cd "$repo" || { echo "    FATAL: repo missing: $repo"; record "cd" "failed"; write_status 1; return; }

  if [ -n "$pkg" ] && { [ "$platforms" = "android" ] || [ "$platforms" = "both" ]; }; then
    step "vitals" python3 "$PY_DIR/build-play-console.py" report --package "$pkg"
    step "bulk-reports" python3 "$PY_DIR/build-play-console.py" bulk-reports --package "$pkg" --months 2
  else
    skip "vitals" "no Play package"
    skip "bulk-reports" "no Play package"
  fi

  local vplat="both"
  case "$platforms" in android) vplat="play" ;; ios) vplat="ios" ;; esac
  step "velocity" python3 "$PY_DIR/aso/aso-velocity.py" --platform "$vplat" --history

  if [ -n "$asc" ]; then
    step "ios-reviews" python3 "$PY_DIR/aso/aso-reviews.py" "$asc" --fetch
  else
    skip "ios-reviews" "no App Store id"
  fi

  local failed
  failed="$(count_failed_steps)"
  write_status "$failed"
  echo "    done (failures: $failed)"
  [ "$failed" -gt 0 ] && FAILED_APPS=$((FAILED_APPS + 1))
  RAN=$((RAN + 1))
}

echo "=== app-fleet-nightly — $(date -u +%Y-%m-%dT%H:%M:%SZ) — manifest $MANIFEST ==="
RAN=0; FAILED_APPS=0; SKIPPED=0

# '|' not TAB: bash treats a run of whitespace IFS chars as ONE delimiter, so an
# empty asc column collapsed and shifted every field after it (found on the first
# dry-run — devicegpt read its repo path as its platform and pulled nothing).
while IFS='|' read -r slug pkg asc platforms repo data_dir own_nightly; do
  [ -z "$slug" ] && continue
  if [ -n "$ONLY" ] && [ "$slug" != "$ONLY" ]; then continue; fi
  if [ "$own_nightly" = "1" ]; then
    echo; echo "=== $slug — skipped: its own launchd job pulls this data (fleet only reads)"
    SKIPPED=$((SKIPPED + 1)); continue
  fi
  if [ "$DRY" -eq 1 ]; then
    echo "PLAN  $slug  platforms=$platforms  play=${pkg:-—}  asc=${asc:-—}  data=$data_dir"
    continue
  fi
  # Subshell: one app's env, cwd and step list never leak into the next.
  ( run_app "$slug" "$pkg" "$asc" "$platforms" "$repo" "$data_dir" )
  RAN=$((RAN + 1))
done < <(python3 - "$MANIFEST" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
for a in m["apps"]:
    row = [str(a.get(k) or "") for k in ("slug", "play_package", "asc_app_id", "platforms", "repo", "data_dir")]
    row.append("1" if a.get("own_nightly") else "0")
    print("|".join(row))
PY
)

if [ "$DRY" -eq 1 ]; then echo; echo "dry-run: nothing pulled"; exit 0; fi

echo
echo "=== fleet pulls done: $RAN ran, $SKIPPED own-nightly ==="
echo "--- building verdicts ---"
python3 "$PY_DIR/build-app-fleet-digest.py"
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "result: VERDICT BUILD FAILED (exit $rc) — the fleet is unjudged tonight"
  osascript -e 'display notification "App fleet verdicts failed to build — apps are unjudged." with title "Teamz App Fleet"' 2>/dev/null || true
  exit "$rc"
fi
echo "result: ok"
