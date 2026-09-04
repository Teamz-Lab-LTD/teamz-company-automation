#!/usr/bin/env bash
# =============================================================================
# aso-signal-sweep.sh — put the 14-day ASO SIGNAL pull on a clock.
#
# aso_cadence.md (locked 2026-06-03) says: every 14 days, SIGNAL_ONLY for every
# app — pull stats, rank deltas, competitor changes, winnability table, NO
# metadata edit. Until 2026-09-05 nothing scheduled it: 7 apps' sentinels were
# 1–12 weeks stale and 12 apps had never been pulled at all.
#
# This runs sh/aso-refresh-runner.sh <slug> SIGNAL_ONLY for the apps whose
# .last_refresh.signal is older than TEAMZ_ASO_SIGNAL_DAYS (14) or missing,
# oldest first, at most TEAMZ_ASO_SWEEP_MAX (8) per sweep — ~15 min each, so a
# Sunday-morning job stays inside two hours. It NEVER runs a FULL_REWRITE: the
# rewrite floors (28d iOS / 56d Android) stay human-triggered via /aso-refresh,
# which build-app-fleet-digest.py prints as a ready-to-paste line when due.
#
# Usage:
#   bash sh/aso-signal-sweep.sh            # do it
#   bash sh/aso-signal-sweep.sh --dry-run  # list who is due, run nothing
#   bash sh/aso-signal-sweep.sh --only=goldmend
# launchd: com.teamzlab.aso-signal-weekly, Sunday 07:00.
# =============================================================================
set -uo pipefail

AUTOMATION="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$AUTOMATION/data/app-fleet.json"
RUNNER="$AUTOMATION/sh/aso-refresh-runner.sh"
LOG_DIR="$AUTOMATION/logs/aso-sweep"
mkdir -p "$LOG_DIR"
SIGNAL_DAYS="${TEAMZ_ASO_SIGNAL_DAYS:-14}"
MAX="${TEAMZ_ASO_SWEEP_MAX:-8}"

DRY=0; ONLY=""
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --only=*) ONLY="${a#--only=}"; MAX=999 ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

echo "=== aso-signal-sweep — $(date -u +%Y-%m-%dT%H:%M:%SZ) — due if signal > ${SIGNAL_DAYS}d, max ${MAX}/sweep ==="

# slug|age_days|sentinel_path — oldest first; "never" sorts first.
DUE="$(python3 - "$MANIFEST" "$SIGNAL_DAYS" "$ONLY" <<'PY'
import json, os, sys, time
manifest, days, only = sys.argv[1], int(sys.argv[2]), sys.argv[3]
now = time.time()
rows = []
for a in json.load(open(manifest))["apps"]:
    if only and a["slug"] != only:
        continue
    sentinel, age = None, None
    for base in (a["data_dir"], os.path.join(a["repo"], "automation_data")):
        fp = os.path.join(base, ".last_refresh.signal")
        if os.path.exists(fp):
            try:
                ts = int(open(fp).read().strip() or 0)
                if ts > 0:
                    age = (now - ts) / 86400
            except ValueError:
                pass
            sentinel = fp
            break
    sentinel = sentinel or os.path.join(a["data_dir"], ".last_refresh.signal")
    if only or age is None or age > days:
        rows.append((age if age is not None else 1e9, a["slug"], sentinel))
rows.sort(key=lambda r: -r[0])
for age, slug, sentinel in rows:
    print(f"{slug}|{'never' if age >= 1e9 else int(age)}|{sentinel}")
PY
)"

if [ -z "$DUE" ]; then echo "nothing due"; exit 0; fi
echo "$DUE" | awk -F'|' '{printf "  due: %-26s signal %s\n", $1, ($2=="never"?"never pulled":$2"d old")}'

RAN=0; FAILED=0
while IFS='|' read -r slug age sentinel; do
  [ -z "$slug" ] && continue
  [ "$RAN" -ge "$MAX" ] && { echo "  cap reached (${MAX}); $slug waits for next sweep"; continue; }
  if [ "$DRY" -eq 1 ]; then echo "  would run: $RUNNER $slug SIGNAL_ONLY"; RAN=$((RAN + 1)); continue; fi
  echo; echo "--> $slug SIGNAL_ONLY (signal ${age})"
  log="$LOG_DIR/$(date -u +%Y%m%dT%H%M%SZ)-$slug.log"
  if bash "$RUNNER" "$slug" SIGNAL_ONLY >"$log" 2>&1; then
    mkdir -p "$(dirname "$sentinel")"
    date +%s > "$sentinel"
    echo "    ok — sentinel $sentinel"
  else
    rc=$?
    echo "    FAILED (rc=$rc) — sentinel NOT advanced; last lines of $log:"
    tail -n 8 "$log" | sed 's/^/      | /'
    FAILED=$((FAILED + 1))
  fi
  RAN=$((RAN + 1))
done <<< "$DUE"

[ "$DRY" -eq 1 ] && exit 0
echo; echo "=== sweep done: $RAN ran, $FAILED failed ==="
if [ "$FAILED" -gt 0 ]; then
  osascript -e "display notification \"ASO signal sweep: $FAILED of $RAN apps failed — see logs/aso-sweep\" with title \"Teamz ASO Sweep\"" 2>/dev/null || true
  exit 1
fi
