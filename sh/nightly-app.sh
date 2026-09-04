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

# AUTOMATION must resolve to THIS file's real directory (teamz-company-automation/sh),
# not the caller's. `readlink "$0"` on macOS/BSD returns the symlink target VERBATIM —
# if the symlink was made with a relative target (e.g. `../teamz-company-automation/
# sh/nightly-app.sh`, which `ln -s` produces by default), that relative path is only
# valid relative to the symlink's OWN directory, not the caller's cwd. Resolving it
# against cwd (the old one-liner) silently produced a bogus AUTOMATION path whenever
# invoked with an absolute $0 (any launchd job does this) — every python call in this
# script failed for every app since 2026-08-04. Fix: resolve the symlink target
# relative to the symlink's directory explicitly.
if [ -L "$0" ]; then
  _SYMLINK_DIR="$(cd "$(dirname "$0")" && pwd)"
  _TARGET="$(readlink "$0")"
  case "$_TARGET" in
    /*) _REAL="$_TARGET" ;;
    *) _REAL="$_SYMLINK_DIR/$_TARGET" ;;
  esac
  AUTOMATION="$(cd "$(dirname "$_REAL")/.." && pwd)"
else
  AUTOMATION="$(cd "$(dirname "$0")/.." && pwd)"
fi

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

# step / skip / write_status live in sh/lib/app-steps.sh so the fleet runner
# (sh/app-fleet-nightly.sh) writes the identical status shape. Same globals.
. "$AUTOMATION/sh/lib/app-steps.sh"

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

  # 2b) LIVE MONEY DATA integrity. Read-only, and the only thing in this project that checks
  #     production DATA rather than production CODE.
  #
  #     Added 2026-08-23, the day a money bug was found by accident. Deleting a paid salary wrote
  #     its reversal with txnDate=0, so it fell outside every month `observeTxns` queries and
  #     cancelled nothing: দারুণ নাজাত হাবিবীয়া ছিদ্দিকীয়া মাদরাসা showed ৳21,000 of expense that
  #     should have been ৳0, every month from January to August, and 10 schools were affected. Every
  #     document involved looked perfectly correct on its own — the damage lived only in the
  #     RELATIONSHIP between two documents, which is exactly what no unit test and no source-scanning
  #     guard can see. 3400+ tests were green throughout.
  #
  #     The code guard now stops that bug shipping again. It can do nothing about data already
  #     written, and nothing about the next invariant somebody breaks. This is that safety net, and a
  #     day is the longest anything like it should now go unnoticed.
  #
  #     Only runs for hazira-khata: it is the only app with this ledger.
  if [ "$SLUG" = "hazira-khata" ] && [ -f "$ROOT/scripts/audit_finance_ledger_integrity.py" ]; then
    step "ledger-integrity" python3 "$ROOT/scripts/audit_finance_ledger_integrity.py" \
      --json "$TEAMZ_DATA_DIR/finance-ledger-integrity.json"
  fi

  # 2b) Remote Config drift — a version floor is not an audience, and it expires by itself.
  #
  #     "Internal testers only" is expressed here as `app.version >= 3.2.NNN`, which means exactly
  #     that until NNN promotes, and then means EVERYONE — with no notification and no diff. Found
  #     2026-08-30 on machine_lan_pull_internal_199_plus, live fleet-wide for days while its own
  #     description still called it internal-only. Re-checked 2026-09-01 at production 3.2.238: the
  #     class had THREE live instances, two of them plain `default: true` params whose safety
  #     argument was a SENTENCE about production that had quietly become false, one of which
  #     ("set false before promoting 161+") was an order to a human that nothing ever enforced.
  #
  #     Runs nightly because the trigger is a PROMOTION, not a commit — no code review can catch it,
  #     and the gap between "we promoted" and "someone re-reads the config" is otherwise unbounded.
  #     It never writes: a non-zero exit is a claim to re-check, never a value to change.
  if [ "$SLUG" = "hazira-khata" ] && [ -f "$ROOT/scripts/check-remote-config-drift.py" ]; then
    step "remote-config-drift" python3 "$ROOT/scripts/check-remote-config-drift.py"
  fi

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

# A COUNT, not a flag. This was `FAILED=1` — a boolean — printed under a label
# that reads as a number, so a night with FIVE broken steps reported
# "done (failures: 1)" and looked like a single blip. Every consumer only tests
# `exit_code != 0`, so a real count keeps working for them and stops the summary
# understating the damage to the human reading it.
FAILED="$(count_failed_steps)"
write_status "$FAILED"
echo "=== done (failures: $FAILED) ==="
exit 0
