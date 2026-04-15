#!/usr/bin/env bash
# Orchestrator: load env, fan out to pullers, merge into one markdown report.
# Partial failure is OK — we return whatever data we managed to pull.
set -u

RANGE="${1:-lifetime}"
case "$RANGE" in
  lifetime|last-30d|last-90d|ytd) ;;
  *) echo "Usage: $0 [lifetime|last-30d|last-90d|ytd]" >&2; exit 2 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# Resolve symlink so pullers/lib paths resolve inside the kit, not the symlink.
REAL_SCRIPT_DIR="$(cd "$(dirname "$(readlink "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")" 2>/dev/null && pwd -P)"
[ -z "$REAL_SCRIPT_DIR" ] && REAL_SCRIPT_DIR="$SCRIPT_DIR"

# PROJECT_ROOT = caller's cwd (the app using the symlink).
PROJECT_ROOT="$(pwd -P)"

load_env() {
  local f="$1"
  [ -f "$f" ] || return 1
  set -a
  # shellcheck disable=SC1090
  . "$f"
  set +a
  return 0
}

# Same lookup order as appstore-fastlane: ../.stats.env then ./.stats.env.
STATS_ENV=""
for cand in "$PROJECT_ROOT/../.stats.env" "$PROJECT_ROOT/.stats.env"; do
  if [ -f "$cand" ]; then STATS_ENV="$cand"; break; fi
done

if [ -z "$STATS_ENV" ]; then
  echo "ERROR: no .stats.env found in project root. Copy .stats.env.example and fill it in." >&2
  exit 1
fi

# Inherit shared ASC creds from appstore-fastlane env if present.
for cand in "$PROJECT_ROOT/../.appstore-fastlane.env" "$PROJECT_ROOT/.appstore-fastlane.env"; do
  [ -f "$cand" ] && load_env "$cand"
done
load_env "$STATS_ENV"

APP_NAME="${APP_NAME:-App}"
REPORT_OUT_DIR="${REPORT_OUT_DIR:-$PROJECT_ROOT/app-stats-reports}"
mkdir -p "$REPORT_OUT_DIR"

TMP="$(mktemp -d -t app-stats.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/ios" "$TMP/android" "$TMP/admob" "$TMP/ga4"

SUCCESSES=0
declare -a ERRORS

run_puller() {
  local name="$1"; shift
  echo "→ $name"
  if "$@" >"$TMP/$name.log" 2>&1; then
    SUCCESSES=$((SUCCESSES + 1))
    echo "  ok"
  else
    local reason
    reason="$(tail -n 1 "$TMP/$name.log" 2>/dev/null || echo "unknown error")"
    echo "  warn: $name failed — $reason" >&2
    ERRORS+=("$name: $reason")
  fi
}

run_puller ios      ruby   "$REAL_SCRIPT_DIR/pullers/ios_sales.rb"     "$RANGE" "$TMP/ios"
run_puller android  bash   "$REAL_SCRIPT_DIR/pullers/play_stats.sh"    "$RANGE" "$TMP/android"
run_puller admob    python3 "$REAL_SCRIPT_DIR/pullers/admob_revenue.py" "$RANGE" "$TMP/admob"
run_puller ga4      python3 "$REAL_SCRIPT_DIR/pullers/ga4_analytics.py" "$RANGE" "$TMP/ga4"

STAMP="$(date +%Y-%m-%d)"
OUT="$REPORT_OUT_DIR/${STAMP}-${RANGE}.md"

ERR_JOINED="$(printf '%s\n' "${ERRORS[@]:-}")"
APP_NAME="$APP_NAME" RANGE="$RANGE" ERRORS="$ERR_JOINED" \
  python3 "$REAL_SCRIPT_DIR/lib/report_builder.py" "$TMP" "$OUT" || {
    echo "ERROR: report builder failed" >&2
    exit 1
  }

echo "Report: $OUT"

if [ "$SUCCESSES" -eq 0 ]; then
  echo "ERROR: all pullers failed" >&2
  exit 1
fi
exit 0
