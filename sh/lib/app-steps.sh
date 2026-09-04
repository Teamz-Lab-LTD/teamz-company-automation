#!/usr/bin/env bash
# =============================================================================
# app-steps.sh — the step/skip/status contract shared by every APP signal runner.
#
# Sourced by sh/nightly-app.sh (one app, its own launchd job) and
# sh/app-fleet-nightly.sh (every app in data/app-fleet.json, one job). Both must
# write the SAME nightly-app-status.json shape, because build-app-fleet-digest.py
# and the growth watchdog read it without caring which runner produced it.
#
# Callers set these globals BEFORE calling step/skip/write_status:
#   STEPS        bash array, start empty:  STEPS=()
#   LOG_DIR      where logs/steps/<name>.log go
#   STATUS_FILE  the nightly-app-status.json to write
#   SLUG LABEL STARTED_AT   recorded into the status file
#
# A step NEVER aborts the run and ALWAYS leaves evidence: output goes to
# logs/steps/<name>.log and, on failure, the last lines are echoed inline so the
# nightly log itself carries the reason. This used to be `>/dev/null 2>&1` and
# five hazira steps failed for weeks with no log anywhere saying why.
# =============================================================================

record() { STEPS+=("$1=$2"); }

step() {
  local name="$1"; shift
  local safe="${name//[^A-Za-z0-9._-]/_}"
  local step_log="$LOG_DIR/steps/$safe.log"
  mkdir -p "$LOG_DIR/steps"
  echo "--> $name"
  local rc=0
  "$@" >"$step_log" 2>&1 || rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "    ok"; record "$name" "ok"
  else
    echo "    FAILED (rc=$rc) — continuing; last lines of $step_log:"
    tail -n 12 "$step_log" 2>/dev/null | sed 's/^/      | /'
    record "$name" "failed"
  fi
}

skip() { echo "--> $1"; echo "    skipped: $2"; record "$1" "skipped:$2"; }

write_status() {
  local rc="$1"
  python3 - "$STATUS_FILE" "$rc" "$SLUG" "$LABEL" "$STARTED_AT" "${STEPS[@]:-}" <<'PY'
import json, sys, datetime
path, rc, slug, label, started = sys.argv[1:6]
steps = {}
for pair in sys.argv[6:]:
    if "=" in pair:
        k, v = pair.split("=", 1)
        steps[k] = v
json.dump({
    "app": slug,
    "label": label,
    "started_at": started,
    "finished_at": datetime.datetime.now(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
    "exit_code": int(rc),
    "steps": steps,
}, open(path, "w"), indent=2)
print(f"status -> {path}")
PY
}

# A COUNT of failed steps, not a flag — "done (failures: 1)" once hid five broken steps.
count_failed_steps() {
  local n=0 s
  for s in "${STEPS[@]:-}"; do case "$s" in *=failed) n=$((n + 1));; esac; done
  echo "$n"
}
