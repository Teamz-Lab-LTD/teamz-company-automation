#!/usr/bin/env bash
# =============================================================================
# aso-refresh-runner.sh
# -----------------------------------------------------------------------------
# Mechanical wrapper that chains the existing ASO/SEO data scripts for ONE app
# in ONE mode and prints a structured markdown report at the end.
#
# This script does NOT make ASO recommendations. It does NOT touch fastlane
# metadata. It only runs the read-only data-pull scripts in SIGNAL_ONLY mode,
# and only invokes the orchestrator (aso-store-blitz.py --dry-run) for
# FULL_REWRITE_* modes — never duplicates the chained sub-scripts inside it.
#
# Usage:
#   bash teamz-company-automation/sh/aso-refresh-runner.sh <app-slug> <mode> [--force]
#
# Where:
#   <app-slug>  devicegpt | debugger | toss | toolz | toss_app
#               | top3picks | top_3_picks | no-trace-chat | ntc | zoyiai
#   <mode>      SIGNAL_ONLY | FULL_REWRITE_IOS | FULL_REWRITE_ANDROID
#               | FULL_REWRITE_BOTH
#   --force     (optional) re-run every step even if a fresh (<1h) output exists.
#
# Exit codes:
#   0 = every required step passed
#   1 = at least one step failed (see "Failed steps" section + audit log)
#   2 = invalid usage / unknown app slug / unknown mode
#
# Audit log:
#   ~/.config/teamzlab/audit/aso-refresh-runs.log  (one line per invocation)
#
# Per-run log:
#   <app_dir>/automation_data/aso-refresh/<ts>-<mode>.log
# =============================================================================

set -u
set -o pipefail
IFS=$'\n\t'

# ----- Args ------------------------------------------------------------------

APP_SLUG_RAW="${1:-}"
MODE="${2:-}"
FORCE_FLAG="${3:-}"

if [ -z "$APP_SLUG_RAW" ] || [ -z "$MODE" ]; then
  echo "Usage: $0 <app-slug> <mode> [--force]" >&2
  echo "  mode: SIGNAL_ONLY | FULL_REWRITE_IOS | FULL_REWRITE_ANDROID | FULL_REWRITE_BOTH" >&2
  exit 2
fi

case "$MODE" in
  SIGNAL_ONLY|FULL_REWRITE_IOS|FULL_REWRITE_ANDROID|FULL_REWRITE_BOTH) ;;
  *)
    echo "ERROR: unknown mode '$MODE'" >&2
    echo "  expected: SIGNAL_ONLY | FULL_REWRITE_IOS | FULL_REWRITE_ANDROID | FULL_REWRITE_BOTH" >&2
    exit 2
    ;;
esac

FORCE=0
if [ "$FORCE_FLAG" = "--force" ]; then
  FORCE=1
fi

# ----- App slug mapping ------------------------------------------------------
# Resolved from data/app-fleet.json (2026-09-05). The old hardcoded `case` knew 5
# apps; the fleet has 19, and the 7 game-kit slugs share one repo but each own a
# different Play package and data dir — which a repo-only mapping cannot express.
# Old aliases (debugger, toss_app, top_3_picks, ntc) still resolve via the repo
# basename so existing muscle memory keeps working.

PROJECTS_ROOT="/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects"
FLEET_MANIFEST="$(cd "$(dirname "$0")/.." && pwd)/data/app-fleet.json"
APP_DIR=""
APP_CANONICAL=""
APP_DATA_DIR_RESOLVED=""
APP_PLAY_PACKAGE=""
APP_ASC_ID=""

_resolved="$(python3 - "$APP_SLUG_RAW" "$FLEET_MANIFEST" <<'PY'
import json, os, sys
raw, manifest = sys.argv[1], sys.argv[2]
aliases = {"debugger": "devicegpt", "toolz": "toss", "toss_app": "toss", "top_3_picks": "top3picks",
           "ntc": "no-trace-chat", "arrow-escape-3d": "arrow-jam-3d", "notetube_ai": "notetube-ai",
           "ai_resume_checker": "resume-coach", "interviewboss": "interview-boss-plus"}
want = aliases.get(raw, raw)
try:
    apps = json.load(open(manifest))["apps"]
except Exception as e:  # noqa: BLE001
    print(f"ERROR: cannot read {manifest}: {e}", file=sys.stderr); sys.exit(2)
for a in apps:
    if a["slug"] == want or os.path.basename(a["repo"]) == raw:
        print("\t".join([a["slug"], a["repo"], a["data_dir"], a.get("play_package") or "", a.get("asc_app_id") or ""]))
        sys.exit(0)
print("known: " + " ".join(a["slug"] for a in apps), file=sys.stderr)
sys.exit(1)
PY
)" || { echo "ERROR: unknown app slug '$APP_SLUG_RAW' (see known list above)" >&2; exit 2; }
IFS=$'\t' read -r APP_CANONICAL APP_DIR APP_DATA_DIR_RESOLVED APP_PLAY_PACKAGE APP_ASC_ID <<< "$_resolved"

if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: app dir does not exist: $APP_DIR" >&2
  exit 2
fi

# ----- Submodule root + data dir --------------------------------------------

SUBMODULE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DATA_DIR="${APP_DATA_DIR_RESOLVED:-$APP_DIR/automation_data}"
mkdir -p "$APP_DATA_DIR"

# TEAMZ_DATA_DIR for the children — per-app, never shared.
export TEAMZ_DATA_DIR="$APP_DATA_DIR"

# Load app env if present (TEAMZ_PLAY_PACKAGE_NAME, TEAMZ_APPLE_APP_ID, etc.), then
# the manifest's per-app ids on top. Both the shell AND _teamz_config.py (which
# re-reads the env file with override=True) must see the same values, so the merged
# copy is what TEAMZ_AUTOMATION_ENV points at. Without this every game-kit slug
# inherited Arrow's package from the kit's shared env.
_MERGED_ENV="$APP_DATA_DIR/aso-refresh/run.env"
mkdir -p "$(dirname "$_MERGED_ENV")"
_BASE_ENV="${TEAMZ_BASE_ENV:-$HOME/.config/teamzlab/automation.base.env}"
if [ -f "$_BASE_ENV" ]; then set -a; . "$_BASE_ENV"; set +a; fi
{
  if [ -f "$APP_DIR/.teamz-automation.env" ]; then cat "$APP_DIR/.teamz-automation.env"; fi
  echo
  echo "# --- manifest overrides (aso-refresh-runner.sh, last assignment wins) ---"
  echo "TEAMZ_DATA_DIR=\"$APP_DATA_DIR\""
  echo "TEAMZ_HOST_SITE_ROOT=\"$APP_DIR\""
  echo "TEAMZ_APP_SLUG=\"$APP_CANONICAL\""
  # An app env that says TEAMZ_PLAY_SERVICE_ACCOUNT_JSON= (empty) must not erase the base path.
  [ -n "${TEAMZ_PLAY_SERVICE_ACCOUNT_JSON:-}" ] && echo "TEAMZ_PLAY_SERVICE_ACCOUNT_JSON=\"$TEAMZ_PLAY_SERVICE_ACCOUNT_JSON\""
  [ -n "$APP_PLAY_PACKAGE" ] && echo "TEAMZ_PLAY_PACKAGE_NAME=\"$APP_PLAY_PACKAGE\""
  [ -n "$APP_ASC_ID" ] && { echo "TEAMZ_APPLE_APP_ID=\"$APP_ASC_ID\""; echo "TEAMZ_APP_IDS=\"$APP_ASC_ID\""; }
} > "$_MERGED_ENV"
set -a
# shellcheck disable=SC1090,SC1091
. "$_MERGED_ENV"
set +a
export TEAMZ_AUTOMATION_ENV="$_MERGED_ENV"
export TEAMZ_DATA_DIR="$APP_DATA_DIR"

# ----- Logging ---------------------------------------------------------------

AUDIT_DIR="$HOME/.config/teamzlab/audit"
AUDIT_LOG="$AUDIT_DIR/aso-refresh-runs.log"
mkdir -p "$AUDIT_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_LOG_DIR="$APP_DATA_DIR/aso-refresh"
mkdir -p "$RUN_LOG_DIR"
RUNNER_LOG="$RUN_LOG_DIR/${TS}-${MODE}.log"
: > "$RUNNER_LOG"

log() {
  # Echo to stdout AND append to the per-run log.
  echo "$@" | tee -a "$RUNNER_LOG"
}

# ----- Step tracking ---------------------------------------------------------
# Bash 3.2 compatible — parallel arrays instead of associative.

STEP_NAMES=()
STEP_CMDS=()
STEP_DURATIONS=()
STEP_EXITS=()
STEP_OUTPUTS=()
STEP_OUTPUT_OK=()
STEP_VERDICTS=()

FAILED_STEPS=()

# Freshness window: skip a step if its expected output is newer than this (sec).
FRESH_WINDOW_SEC=3600

is_fresh() {
  # is_fresh <path>  -> 0 if file exists and mtime < $FRESH_WINDOW_SEC ago.
  local f="$1"
  [ -n "$f" ] || return 1
  [ -f "$f" ] || return 1
  # macOS stat -f vs Linux stat -c — try BSD first, fallback to GNU.
  local mtime
  mtime="$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo 0)"
  [ "$mtime" -gt 0 ] || return 1
  local now
  now="$(date +%s)"
  local age=$(( now - mtime ))
  [ "$age" -lt "$FRESH_WINDOW_SEC" ]
}

run_step() {
  # run_step "<name>" "<expected-output-file-or-empty>" <argv...>
  # Reads STEP_DISPLAY_CMD env for the human-readable command to log
  # (the executor sets it; argv handles execution correctly with spaces).
  local name="$1"; shift
  local expected_out="$1"; shift
  local cmd_str="${STEP_DISPLAY_CMD:-$*}"

  local idx=${#STEP_NAMES[@]}
  local num=$(( idx + 1 ))

  log ""
  log "STEP ${num}/__TOTAL__: ${name} ..."
  log "  cmd: ${cmd_str}"
  if [ -n "$expected_out" ]; then
    log "  expected output: ${expected_out}"
  fi

  # Idempotency: skip if fresh and not forced.
  if [ "$FORCE" -eq 0 ] && [ -n "$expected_out" ] && is_fresh "$expected_out"; then
    log "  SKIP (fresh output < 1h old; pass --force to re-run)"
    STEP_NAMES+=("$name")
    STEP_CMDS+=("$cmd_str")
    STEP_DURATIONS+=("0")
    STEP_EXITS+=("0")
    STEP_OUTPUTS+=("$expected_out")
    STEP_OUTPUT_OK+=("YES")
    STEP_VERDICTS+=("SKIP_FRESH")
    return 0
  fi

  local start_ts end_ts dur ec=0
  start_ts="$(date +%s)"

  # Run the command, tee output to the runner log.
  # We capture exit via $? after the pipeline thanks to pipefail.
  ( "$@" ) >>"$RUNNER_LOG" 2>&1 || ec=$?

  end_ts="$(date +%s)"
  dur=$(( end_ts - start_ts ))

  local out_ok="N/A"
  if [ -n "$expected_out" ]; then
    if [ -s "$expected_out" ]; then
      out_ok="YES"
    else
      out_ok="NO"
    fi
  fi

  local verdict
  if [ "$ec" -eq 0 ]; then
    if [ "$out_ok" = "NO" ]; then
      verdict="FAIL_NO_OUTPUT"
      log "  STEP ${num} FAILED: exit 0 but expected output missing/empty (${expected_out})"
      FAILED_STEPS+=("${num}|${name}|exit0 but missing output: ${expected_out}")
    else
      verdict="PASS"
      log "  STEP ${num} OK (${dur}s)"
    fi
  else
    verdict="FAIL_EXIT_${ec}"
    log "  STEP ${num} FAILED: exit ${ec} after ${dur}s — see $RUNNER_LOG"
    FAILED_STEPS+=("${num}|${name}|exit ${ec} — see $RUNNER_LOG")
  fi

  STEP_NAMES+=("$name")
  STEP_CMDS+=("$cmd_str")
  STEP_DURATIONS+=("$dur")
  STEP_EXITS+=("$ec")
  STEP_OUTPUTS+=("$expected_out")
  STEP_OUTPUT_OK+=("$out_ok")
  STEP_VERDICTS+=("$verdict")

  return 0
}

# ----- Resolve inputs --------------------------------------------------------

# Package + Apple ID may come from env, otherwise per-app fallbacks.
PACKAGE="${TEAMZ_PLAY_PACKAGE_NAME:-}"
APPLE_APP_ID="${TEAMZ_APPLE_APP_ID:-}"

case "$APP_CANONICAL" in
  toss_app)
    PACKAGE="${PACKAGE:-com.teamz.toss.toss}"
    APPLE_APP_ID="${APPLE_APP_ID:-6739454718}"
    ;;
  devicegpt)
    PACKAGE="${PACKAGE:-com.teamz.lab.debugger}"
    ;;
  no-trace-chat)
    PACKAGE="${PACKAGE:-com.teamzlab.no_trace_code_chat}"
    ;;
esac

# Keywords file: prefer per-app override, else search common locations.
KEYWORDS_FILE=""
for cand in \
  "$APP_DATA_DIR/aso-keywords.txt" \
  "$APP_DATA_DIR/keywords.txt" \
  "$APP_DIR/keywords.txt"; do
  if [ -f "$cand" ]; then
    KEYWORDS_FILE="$cand"
    break
  fi
done

# Competitors (Play package list) — only if file present.
COMPETITORS_PLAY=""
if [ -f "$APP_DATA_DIR/competitors-play.txt" ]; then
  COMPETITORS_PLAY="$(tr '\n' ',' < "$APP_DATA_DIR/competitors-play.txt" | sed 's/,$//')"
fi

# Firebase project — only set if .teamz-automation.env declared it.
FIREBASE_PROJECT="${TEAMZ_FIREBASE_PROJECT:-}"

# Seed keywords for build-keyword-volume.py — pull first 5 lines of kw file.
SEED_KWS=""
if [ -n "$KEYWORDS_FILE" ] && [ -f "$KEYWORDS_FILE" ]; then
  SEED_KWS="$(head -n 5 "$KEYWORDS_FILE" | tr '\n' '|' | sed 's/|$//')"
fi

# ----- Header ----------------------------------------------------------------

START_TS="$(date +%s)"
log "================================================================"
log "ASO REFRESH RUNNER"
log "  app           : $APP_CANONICAL  (raw: $APP_SLUG_RAW)"
log "  app dir       : $APP_DIR"
log "  mode          : $MODE"
log "  force         : $FORCE"
log "  package       : ${PACKAGE:-<unset>}"
log "  apple app id  : ${APPLE_APP_ID:-<unset>}"
log "  keywords file : ${KEYWORDS_FILE:-<none found>}"
log "  competitors   : ${COMPETITORS_PLAY:-<none>}"
log "  firebase proj : ${FIREBASE_PROJECT:-<none — skipping firebase step>}"
log "  data dir      : $TEAMZ_DATA_DIR"
log "  runner log    : $RUNNER_LOG"
log "  ts (utc)      : $TS"
log "================================================================"

# ----- Cross-cutting paths ---------------------------------------------------

PY_BIN="python3"

PRECHECK="$SUBMODULE_ROOT/py/aso/aso-master-precheck.sh"
PLAY_CONSOLE="$SUBMODULE_ROOT/py/build-play-console.py"
KW_VOLUME="$SUBMODULE_ROOT/py/build-keyword-volume.py"
KW_INTEL="$SUBMODULE_ROOT/py/build-keyword-intel.py"
ASO_PIPELINE="$SUBMODULE_ROOT/py/aso/aso-keyword-pipeline.py"
ASO_SEO_MERGE="$SUBMODULE_ROOT/py/aso/aso-seo-merge.py"
ASO_COMPETITORS="$SUBMODULE_ROOT/py/aso/aso-competitors.py"
ASO_REVIEWS="$SUBMODULE_ROOT/py/aso/aso-reviews.py"
ASO_FIREBASE="$SUBMODULE_ROOT/py/aso/aso-firebase-events.py"
ASO_ADMOB="$SUBMODULE_ROOT/py/aso/aso-admob-rpm-benchmarks.py"
ASO_TRACK="$SUBMODULE_ROOT/py/aso/aso-track.py"
ASO_VELOCITY="$SUBMODULE_ROOT/py/aso/aso-velocity.py"
ASO_BLITZ="$SUBMODULE_ROOT/py/aso/aso-store-blitz.py"
APP_STATS_PULL="$SUBMODULE_ROOT/app-stats/pull_all.sh"

# Expected per-app output files (used for freshness + verification).
# These match the scripts' default --out paths under TEAMZ_DATA_DIR.
OUT_KW_VOLUME="$TEAMZ_DATA_DIR/keyword-volume-latest.json"
OUT_KW_INTEL="$TEAMZ_DATA_DIR/keyword-intel-latest.json"
OUT_PIPELINE="$TEAMZ_DATA_DIR/aso-pipeline-latest.json"
OUT_SEO_MERGE="$TEAMZ_DATA_DIR/combined-keywords-score.csv"
OUT_COMPETITORS="$TEAMZ_DATA_DIR/aso-competitors-latest.json"
OUT_REVIEWS="$TEAMZ_DATA_DIR/aso-reviews-sentiment-latest.json"
OUT_FIREBASE="$TEAMZ_DATA_DIR/firebase-events-latest.json"
OUT_ADMOB="$TEAMZ_DATA_DIR/admob-rpm-benchmarks.json"
OUT_TRACK="$TEAMZ_DATA_DIR/aso-rank-history-latest.json"
OUT_VELOCITY="$TEAMZ_DATA_DIR/aso-velocity-history.csv"
OUT_PLAY_BULK="$TEAMZ_DATA_DIR/play-bulk-reports-latest.json"

# Master precheck dated output. We compute today's expected file.
if [ -n "$PACKAGE" ]; then
  PKG_SAFE="$(echo "$PACKAGE" | tr '.' '-')"
  OUT_PRECHECK="$TEAMZ_DATA_DIR/aso-master-table-${PKG_SAFE}-$(date +%Y%m%d).json"
else
  OUT_PRECHECK=""
fi

# ----- Plan steps ------------------------------------------------------------
# We build the plan first so we know the TOTAL up front and can substitute it
# into the per-step log lines.

PLAN_NAMES=()
PLAN_OUTS=()
PLAN_CMDS=()          # argv joined by ASCII 30 (record separator) — handles paths-with-spaces
PLAN_DISPLAY=()       # human-readable command for logging (quoted)

# Record-separator delimiter: ASCII 30, never appears in filesystem paths or
# CLI flags. Lets us serialize argv arrays through a flat string array (Bash
# 3.2 has no array-of-arrays support).
PLAN_RS=$'\x1e'

# Helper: shell-quote a single arg for display (best-effort, not for eval)
_quote_arg() {
  case "$1" in
    *' '*|*$'\t'*|*$'\n'*|*'$'*|*'"'*|*"'"*|*'\\'*|*'`'*) printf "'%s'" "${1//\'/\'\\\'\'}" ;;
    *) printf '%s' "$1" ;;
  esac
}

plan_add() {
  # plan_add "<name>" "<expected-out>" <argv...>
  # Each argv element is preserved verbatim — spaces in paths OK.
  local name="$1" outf="$2"
  shift 2
  PLAN_NAMES+=("$name")
  PLAN_OUTS+=("$outf")
  local joined="" sep="" display="" dsep=""
  for arg in "$@"; do
    joined="${joined}${sep}${arg}"
    sep="$PLAN_RS"
    display="${display}${dsep}$(_quote_arg "$arg")"
    dsep=" "
  done
  PLAN_CMDS+=("$joined")
  PLAN_DISPLAY+=("$display")
}

# Helper: only plan a step if its tool exists on disk.
have() { [ -x "$1" ] || [ -f "$1" ]; }

# --- SIGNAL_ONLY plan (always runs first) ---

# 1. app-stats pull (optional)
if have "$APP_STATS_PULL"; then
  plan_add "app-stats pull_all" "" bash "$APP_STATS_PULL" last-30d
fi

# 2. Play Console drift check (listing-pull)
if have "$PLAY_CONSOLE" && [ -n "$PACKAGE" ]; then
  plan_add "play-console listing-pull" "" \
    "$PY_BIN" "$PLAY_CONSOLE" listing-pull --package "$PACKAGE"
fi

# 3. Master precheck
if have "$PRECHECK" && [ -n "$PACKAGE" ] && [ -n "$KEYWORDS_FILE" ]; then
  PRECHECK_ARGS=(bash "$PRECHECK" --package "$PACKAGE" --keywords-file "$KEYWORDS_FILE")
  [ -n "$COMPETITORS_PLAY" ] && PRECHECK_ARGS+=(--competitors-play "$COMPETITORS_PLAY")
  [ -n "$FIREBASE_PROJECT" ] && PRECHECK_ARGS+=(--firebase-project "$FIREBASE_PROJECT")
  PRECHECK_ARGS+=(--app-slug "$APP_CANONICAL")
  plan_add "aso-master-precheck" "$OUT_PRECHECK" "${PRECHECK_ARGS[@]}"
fi

# 4. Keyword volume (free)
if have "$KW_VOLUME" && [ -n "$SEED_KWS" ]; then
  # Split SEED_KWS on '|' into separate args
  KW_VOL_ARGS=("$PY_BIN" "$KW_VOLUME")
  OLDIFS="$IFS"
  IFS='|'
  for kw in $SEED_KWS; do
    [ -n "$kw" ] && KW_VOL_ARGS+=("$kw")
  done
  IFS="$OLDIFS"
  KW_VOL_ARGS+=(--top 20)
  plan_add "build-keyword-volume" "$OUT_KW_VOLUME" "${KW_VOL_ARGS[@]}"
fi

# 5. Keyword intel
if have "$KW_INTEL"; then
  plan_add "build-keyword-intel" "$OUT_KW_INTEL" \
    "$PY_BIN" "$KW_INTEL" --top 30 --export csv
fi

# 6. ASO keyword pipeline
if have "$ASO_PIPELINE"; then
  PIPELINE_ARGS=("$PY_BIN" "$ASO_PIPELINE")
  if [ -n "$SEED_KWS" ]; then
    # convert | to , for --seeds arg
    PIPELINE_ARGS+=(--seeds "${SEED_KWS//|/,}")
  fi
  plan_add "aso-keyword-pipeline" "$OUT_PIPELINE" "${PIPELINE_ARGS[@]}"
fi

# 7. ASO + SEO merge
if have "$ASO_SEO_MERGE"; then
  plan_add "aso-seo-merge" "$OUT_SEO_MERGE" "$PY_BIN" "$ASO_SEO_MERGE"
fi

# 8. Competitors (top 10)
if have "$ASO_COMPETITORS" && [ -n "$SEED_KWS" ]; then
  FIRST_SEED="$(echo "$SEED_KWS" | awk -F'|' '{print $1}')"
  plan_add "aso-competitors" "$OUT_COMPETITORS" \
    "$PY_BIN" "$ASO_COMPETITORS" --find "$FIRST_SEED" --top 10
fi

# 9. Reviews (competitors)
if have "$ASO_REVIEWS"; then
  plan_add "aso-reviews" "$OUT_REVIEWS" \
    "$PY_BIN" "$ASO_REVIEWS" --competitors
fi

# 10. Firebase events — only if project configured
if have "$ASO_FIREBASE" && [ -n "$FIREBASE_PROJECT" ]; then
  plan_add "aso-firebase-events" "$OUT_FIREBASE" \
    "$PY_BIN" "$ASO_FIREBASE" --project "$FIREBASE_PROJECT" --days 30
fi

# 11. AdMob RPM benchmarks
if have "$ASO_ADMOB"; then
  plan_add "aso-admob-rpm-benchmarks" "$OUT_ADMOB" \
    "$PY_BIN" "$ASO_ADMOB" --category utilities
fi

# 12. Rank tracker
if have "$ASO_TRACK"; then
  plan_add "aso-track" "$OUT_TRACK" \
    "$PY_BIN" "$ASO_TRACK" --record
fi

# 13. Velocity
if have "$ASO_VELOCITY"; then
  plan_add "aso-velocity" "$OUT_VELOCITY" \
    "$PY_BIN" "$ASO_VELOCITY" --history
fi

# --- FULL_REWRITE_* extras ---
# CRITICAL: aso-store-blitz.py is the orchestrator that internally chains
# aso-generate-batch, aso-pad-resize, aso-localize, aso-play-batch-push,
# asc-screenshots-push.rb. Do NOT call those scripts here — only call blitz.

if [ "$MODE" != "SIGNAL_ONLY" ]; then
  case "$MODE" in
    FULL_REWRITE_IOS)     BLITZ_ARGS="--only apple_metadata" ;;
    FULL_REWRITE_ANDROID) BLITZ_ARGS="--only play_metadata" ;;
    FULL_REWRITE_BOTH)    BLITZ_ARGS="" ;;
  esac
  if have "$ASO_BLITZ"; then
    BLITZ_ARGV=("$PY_BIN" "$ASO_BLITZ" --dry-run)
    [ -n "$BLITZ_ARGS" ] && BLITZ_ARGV+=($BLITZ_ARGS)
    plan_add "aso-store-blitz DRY-RUN ($MODE)" "" "${BLITZ_ARGV[@]}"
  fi
fi

TOTAL_STEPS=${#PLAN_NAMES[@]}

if [ "$TOTAL_STEPS" -eq 0 ]; then
  log "ERROR: no runnable steps planned. Check inputs (KEYWORDS_FILE, PACKAGE, scripts on disk)." >&2
  echo "$(date -u +%FT%TZ) | $APP_CANONICAL | $MODE | 0 | 0 | 0 | 0s | NO_STEPS_PLANNED" >> "$AUDIT_LOG"
  exit 1
fi

log ""
log "Planned $TOTAL_STEPS step(s) for mode=$MODE."

# ----- Execute plan ----------------------------------------------------------

# Executor — reconstruct argv from RS-joined cmdstr. Each PLAN_CMDS entry
# was built by plan_add joining argv with ASCII 30 (PLAN_RS). Splitting back
# on $PLAN_RS preserves arguments that contain spaces (file paths like
# "Teamz Lab Projects/..." were truncated when we split on whitespace).
i=0
while [ $i -lt $TOTAL_STEPS ]; do
  name="${PLAN_NAMES[$i]}"
  outf="${PLAN_OUTS[$i]}"
  cmdstr="${PLAN_CMDS[$i]}"
  display="${PLAN_DISPLAY[$i]}"
  # Split RS-joined cmdstr back to argv array
  oldIFS="$IFS"
  IFS="$PLAN_RS"
  # shellcheck disable=SC2206
  argv=($cmdstr)
  IFS="$oldIFS"
  # Pass the human-readable display string via env so run_step can log it
  STEP_DISPLAY_CMD="$display" run_step "$name" "$outf" "${argv[@]}"
  i=$(( i + 1 ))
done

END_TS="$(date +%s)"
TOTAL_DURATION=$(( END_TS - START_TS ))

# Replace __TOTAL__ placeholder in the per-run log so the file is self-consistent.
# (macOS sed needs '' after -i.)
sed -i.bak "s/__TOTAL__/$TOTAL_STEPS/g" "$RUNNER_LOG" 2>/dev/null || true
rm -f "${RUNNER_LOG}.bak" 2>/dev/null || true

# ----- Final report (markdown) -----------------------------------------------

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
i=0
while [ $i -lt $TOTAL_STEPS ]; do
  v="${STEP_VERDICTS[$i]}"
  case "$v" in
    PASS) PASS_COUNT=$(( PASS_COUNT + 1 )) ;;
    SKIP_FRESH) SKIP_COUNT=$(( SKIP_COUNT + 1 )); PASS_COUNT=$(( PASS_COUNT + 1 )) ;;
    *) FAIL_COUNT=$(( FAIL_COUNT + 1 )) ;;
  esac
  i=$(( i + 1 ))
done

log ""
log "================================================================"
log "FINAL REPORT"
log "================================================================"
log ""
log "| # | Step | Mode | Duration | Exit | Output File Exists | Verdict |"
log "|---|------|------|----------|------|--------------------|---------|"

i=0
while [ $i -lt $TOTAL_STEPS ]; do
  n=$(( i + 1 ))
  log "| ${n} | ${STEP_NAMES[$i]} | ${MODE} | ${STEP_DURATIONS[$i]}s | ${STEP_EXITS[$i]} | ${STEP_OUTPUT_OK[$i]} | ${STEP_VERDICTS[$i]} |"
  i=$(( i + 1 ))
done

log ""
log "Summary: ${PASS_COUNT}/${TOTAL_STEPS} passed (${SKIP_COUNT} skipped-fresh), ${FAIL_COUNT} failed, total ${TOTAL_DURATION}s."

# ----- Failed steps + how-to-fix --------------------------------------------

if [ "${#FAILED_STEPS[@]}" -gt 0 ]; then
  log ""
  log "Failed steps:"
  for fs in "${FAILED_STEPS[@]}"; do
    log "  - $fs"
  done
  log ""
  log "How to fix:"
  log "  1. Open the per-run log: $RUNNER_LOG"
  log "  2. Re-run a single failing step manually with the cmd shown above."
  log "  3. If it's an env var: check $APP_DIR/.teamz-automation.env vs"
  log "     $SUBMODULE_ROOT/.teamz-automation.env.example."
  log "  4. If it's a missing keywords file: add $APP_DATA_DIR/aso-keywords.txt"
  log "     (one keyword per line) and re-run with --force."
  log "  5. If it's an API quota error: wait, then re-run with --force."
fi

# ----- Audit log entry -------------------------------------------------------
# Format: timestamp | app | mode | step_count | passed | failed | duration | log
AUDIT_LINE="$(date -u +%FT%TZ) | $APP_CANONICAL | $MODE | ${TOTAL_STEPS} | ${PASS_COUNT} | ${FAIL_COUNT} | ${TOTAL_DURATION}s | ${RUNNER_LOG}"
echo "$AUDIT_LINE" >> "$AUDIT_LOG"

log ""
log "Audit log entry:"
log "  $AUDIT_LINE"
log "Audit log path: $AUDIT_LOG"

# ----- Confirm prompt for real run (rewrite modes) --------------------------
# Per requirement: if blitz dry-run passed, prompt user to confirm before real
# run. We do NOT auto-execute the real run — we only print the next command.

if [ "$MODE" != "SIGNAL_ONLY" ] && [ "$FAIL_COUNT" -eq 0 ]; then
  log ""
  log "Dry-run succeeded for $MODE."
  log "To execute the real push, run manually (confirms intent):"
  case "$MODE" in
    FULL_REWRITE_IOS)
      log "  cd \"$APP_DIR\" && $PY_BIN $ASO_BLITZ --only apple_metadata"
      ;;
    FULL_REWRITE_ANDROID)
      log "  cd \"$APP_DIR\" && $PY_BIN $ASO_BLITZ --only play_metadata"
      ;;
    FULL_REWRITE_BOTH)
      log "  cd \"$APP_DIR\" && $PY_BIN $ASO_BLITZ"
      ;;
  esac
fi

# ----- Exit ------------------------------------------------------------------

if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi
exit 0
