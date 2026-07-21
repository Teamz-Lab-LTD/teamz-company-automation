#!/usr/bin/env bash
# =============================================================================
# nightly-app.sh — nightly SIGNAL COLLECTION for an APP repo.
#
# The app-shaped sibling of nightly-site.sh. That one serves websites: Search
# Console, sitemaps, a content agent, a build and a deploy. An app repo has no
# site to build and no GSC property; what it has is a store listing, store
# vitals, reviews and competitors. Pointing nightly-site.sh at an app repo does
# not degrade gracefully — build-search-index.sh hard-exits for
# TEAMZ_PROJECT_TYPE=app — so apps needed their own entry point.
#
# ONE SCRIPT, MANY APPS, NO SHARED STATE
#
# Every app symlinks THIS file as <repo>/scripts/nightly-app.sh and configures
# it from its own .teamz-automation.env. Nothing about any single app is
# encoded here: the package, platform, locales and launchd label all come from
# the repo that invokes it.
#
# Isolation is the point, and it is enforced in one place — TEAMZ_DATA_DIR is
# pinned to the calling repo's own data directory below. Without that, every
# app's pulls land in teamz-company-automation/data/ and one app's nightly
# quietly overwrites another's numbers. Verified: build-play-console.py
# listing-pull writes to the central data/ by default.
#
# HOW AN APP OPTS IN  (all keys live in <repo>/.teamz-automation.env)
#   TEAMZ_APP_SLUG            hazira-khata                     (required)
#   TEAMZ_PACKAGE             com.Teachers.HaziraKhataByGk     (required, Android)
#   TEAMZ_PLATFORM            android | ios | both             (required)
#   TEAMZ_NIGHTLY_LABEL       com.teamzlab.hazira-nightly      (required, UNIQUE)
#   TEAMZ_APP_DATA_DIR        automation_data                  (optional, default shown)
#   TEAMZ_APP_LOCALES         en-US,bn-BD                      (optional, default en-US)
#   TEAMZ_NIGHTLY_HOUR/MINUTE 3 / 10                           (optional)
#   TEAMZ_APP_SEED_KEYWORD         "hazira khata"                   (optional, skips if unset)
#
# Install:   bash scripts/nightly-app.sh --install
# Uninstall: bash scripts/nightly-app.sh --uninstall
# Run now:   bash scripts/nightly-app.sh
#
# Writes <repo>/<data-dir>/nightly-app-status.json so build-growth-digest.py and
# nightly-catchup.sh can see what happened, in the same shape nightly-site.sh uses.
# =============================================================================
set -uo pipefail

# Symlinked into <repo>/scripts/, and bash does NOT resolve $0, so dirname($0)/..
# is the CALLING repo — which is what we want. Same trick as nightly-site.sh.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUTOMATION="$(cd "$(dirname "$(readlink "$0" || echo "$0")")/.." && pwd)"

if [ ! -f "$ROOT/.teamz-automation.env" ]; then
  echo "FATAL: no .teamz-automation.env in $ROOT — this repo is not wired to the engine."
  exit 1
fi
set -a; . "$ROOT/.teamz-automation.env"; set +a

SLUG="${TEAMZ_APP_SLUG:-}"
PACKAGE="${TEAMZ_PACKAGE:-}"
PLATFORM="${TEAMZ_PLATFORM:-android}"
LABEL="${TEAMZ_NIGHTLY_LABEL:-}"
LOCALES="${TEAMZ_APP_LOCALES:-en-US}"
DATA_SUBDIR="${TEAMZ_APP_DATA_DIR:-automation_data}"

# THE ISOLATION LINE. Exported before any puller runs so every script that
# resolves TEAMZ_DATA_DIR (see py/_teamz_config.py) writes into THIS app's
# directory and can never reach another app's data.
export TEAMZ_DATA_DIR="$ROOT/$DATA_SUBDIR"
mkdir -p "$TEAMZ_DATA_DIR"

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STATUS_FILE="$TEAMZ_DATA_DIR/nightly-app-status.json"
STEPS=()

record() { STEPS+=("$1=$2"); }

# Run a step, never let one failure kill the night. A store API that is briefly
# unreachable must not cost the other five signals; the status file records
# which ones failed so the digest and a human can see it.
step() {
  local name="$1"; shift
  echo "--> $name"
  if "$@" >/dev/null 2>&1; then
    echo "    ok"; record "$name" "ok"
  else
    echo "    FAILED (rc=$?) — continuing"; record "$name" "failed"
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

LOG_DIR="$ROOT/logs"; mkdir -p "$LOG_DIR"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$LOG_DIR/$LABEL.log"

# ------------------------------------------------------------------ install
if [ "${1:-}" = "--install" ] || [ "${1:-}" = "--uninstall" ]; then
  if [ -z "$LABEL" ]; then
    echo "FATAL: TEAMZ_NIGHTLY_LABEL is not set in $ROOT/.teamz-automation.env"
    exit 1
  fi
fi

if [ "${1:-}" = "--uninstall" ]; then
  launchctl unload "$PLIST_PATH" 2>/dev/null || true
  rm -f "$PLIST_PATH"
  echo "Uninstalled $LABEL"
  exit 0
fi

if [ "${1:-}" = "--install" ]; then
  # ANTI-CLOBBER GUARD, same reasoning as nightly-site.sh: a launchd Label is
  # global, so installing over another project's label silently replaces its job.
  if [ -f "$PLIST_PATH" ] && ! grep -q "$ROOT" "$PLIST_PATH"; then
    echo "REFUSING TO INSTALL — label '$LABEL' already belongs to another project:"
    grep -m1 "nightly" "$PLIST_PATH" || true
    echo "    Pick a unique TEAMZ_NIGHTLY_LABEL in $ROOT/.teamz-automation.env"
    exit 1
  fi
  HOUR="${TEAMZ_NIGHTLY_HOUR:-3}"; MINUTE="${TEAMZ_NIGHTLY_MINUTE:-10}"
  cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$ROOT/scripts/nightly-app.sh</string></array>
  <key>RunAtLoad</key><false/>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>$HOUR</integer><key>Minute</key><integer>$MINUTE</integer></dict>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
PLIST
  launchctl unload "$PLIST_PATH" 2>/dev/null || true
  launchctl load "$PLIST_PATH"
  echo "Installed $LABEL — runs daily at $HOUR:$(printf '%02d' "$MINUTE")"
  echo "  repo: $ROOT"
  echo "  data: $TEAMZ_DATA_DIR"
  echo "  log:  $LOG"
  exit 0
fi

# ---------------------------------------------------------------------- run
echo "=== nightly-app: $SLUG ($PLATFORM) — $STARTED_AT ==="
echo "    data dir: $TEAMZ_DATA_DIR"

if [ -z "$SLUG" ] || [ -z "$PACKAGE" ]; then
  echo "FATAL: TEAMZ_APP_SLUG and TEAMZ_PACKAGE must be set in $ROOT/.teamz-automation.env"
  write_status 1
  exit 1
fi

PY_DIR="$AUTOMATION/py"

# 1) Store listing per locale — the authority on title/short/full description.
#    Feeds the site's llms.txt generator, so a listing edit reaches the website
#    without anyone copying text by hand.
if [ "$PLATFORM" = "android" ] || [ "$PLATFORM" = "both" ]; then
  IFS=',' read -ra LOCS <<< "$LOCALES"
  for loc in "${LOCS[@]}"; do
    loc="$(echo "$loc" | tr -d ' ')"
    [ -z "$loc" ] && continue
    step "listing:$loc" python3 "$PY_DIR/build-play-console.py" \
      listing-pull --package "$PACKAGE" --language "$loc"
  done

  # 2) Vitals — crash + ANR rates. The one signal that tells you a release is
  #    hurting users before the reviews do.
  step "vitals" python3 "$PY_DIR/build-play-console.py" report --package "$PACKAGE"

  # 3) Installs / store performance / reviews CSVs from the bulk-reports bucket.
  step "bulk-reports" python3 "$PY_DIR/build-play-console.py" \
    bulk-reports --package "$PACKAGE"
else
  skip "listing" "platform=$PLATFORM (Android pullers only)"
fi

# 4) Own-app review text straight from Play. bulk-reports carries review CSVs
#    too, but on the bucket's schedule; this is the same-day read and it is the
#    Android-native half of aso-competitors.py, whose other modes are iTunes.
if [ "$PLATFORM" = "android" ] || [ "$PLATFORM" = "both" ]; then
  step "play-reviews" python3 "$PY_DIR/aso/aso-competitors.py" --play-reviews "$PACKAGE"
fi

# 5) Competitor set for the app's own keyword — no credential needed.
#    NOTE: --find queries the iTunes Search API, so for an Android-only app this
#    is market intelligence (who else builds this, how they position it), not a
#    Play ranking peer set. Kept because the category read is still worth having;
#    do not mistake it for Play competitor data.
if [ -n "${TEAMZ_APP_SEED_KEYWORD:-}" ]; then
  step "competitors" python3 "$PY_DIR/aso/aso-competitors.py" --find "$TEAMZ_APP_SEED_KEYWORD"
else
  skip "competitors" "TEAMZ_APP_SEED_KEYWORD unset"
fi

# 6) YouTube autocomplete — a demand signal that leads store search. Costs
#    nothing and needs no key. Seeds are POSITIONAL, not a flag: --seed is read
#    as --seed-file and the script then tries to open the keyword as a path.
if [ -n "${TEAMZ_APP_SEED_KEYWORD:-}" ]; then
  step "youtube-keywords" python3 "$PY_DIR/build-youtube-keywords.py" "$TEAMZ_APP_SEED_KEYWORD"
else
  skip "youtube-keywords" "TEAMZ_APP_SEED_KEYWORD unset"
fi

FAILED=0
for s in "${STEPS[@]:-}"; do case "$s" in *=failed) FAILED=1;; esac; done
write_status "$FAILED"
echo "=== done (failures: $FAILED) ==="
exit 0
