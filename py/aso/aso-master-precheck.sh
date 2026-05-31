#!/usr/bin/env bash
# aso-master-precheck.sh — run ALL data sources for an app before writing
# ASO copy, landing pages, or blog content.
#
# Outputs a single combined JSON at:
#   <data_dir>/aso-master-table-<package>-<YYYYMMDD>.json
#
# Sources (per global "data first, always" rule):
#   1. Play bulk reports          (build-play-console.py bulk-reports)
#   2. ASO keyword score          (aso-keywords.py)
#   3. Free keyword volume + Trends (build-keyword-volume.py)
#   4. Paid keyword volume        (build-keyword-volume.py --source dataforseo)
#   5. Competitor App Store cards (aso-competitors.py --analyze)
#   6. Competitor Play reviews    (aso-competitors.py --play-reviews)
#   7. Firebase event counts      (aso-firebase-events.py) [skipped if no Blaze]
#   8. Deep Research prompt       (aso-deep-research-prompt.py) [paste to ChatGPT manually]
#
# Required env vars:
#   TEAMZ_PLAY_SERVICE_ACCOUNT_JSON, TEAMZ_PLAY_PACKAGE_NAME (or --package),
#   TEAMZ_PLAY_DEV_ACCOUNT_ID (the long number in your Play Console URL),
#   TEAMZ_APP_IDS (ios:<id>,android:<pkg>) for the ASC side.
#
# Usage:
#   ./aso-master-precheck.sh \
#       --package com.teamzlab.no_trace_code_chat \
#       --keywords-file kws.txt \
#       --competitors-asc 994233666,1499053793 \
#       --competitors-play org.thoughtcrime.securesms,ch.threema.app,network.loki.messenger \
#       [--firebase-project no-trace-chat] \
#       [--app-slug no-trace-chat] \
#       [--country us] \
#       [--months 3] \
#       [--out master.json]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="${TEAMZ_DATA_DIR:-$PY_ROOT/../data}"
mkdir -p "$DATA_DIR"

PACKAGE=""
KEYWORDS_FILE=""
COMP_ASC=""
COMP_PLAY=""
FIREBASE_PROJECT=""
APP_SLUG=""
COUNTRY="us"
MONTHS=3
OUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --package) PACKAGE="$2"; shift 2 ;;
    --keywords-file) KEYWORDS_FILE="$2"; shift 2 ;;
    --competitors-asc) COMP_ASC="$2"; shift 2 ;;
    --competitors-play) COMP_PLAY="$2"; shift 2 ;;
    --firebase-project) FIREBASE_PROJECT="$2"; shift 2 ;;
    --app-slug) APP_SLUG="$2"; shift 2 ;;
    --country) COUNTRY="$2"; shift 2 ;;
    --months) MONTHS="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help)
      sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# //'
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$PACKAGE" ]]; then
  echo "ERROR: --package is required (e.g. com.teamzlab.no_trace_code_chat)" >&2
  exit 2
fi
if [[ -z "$KEYWORDS_FILE" || ! -f "$KEYWORDS_FILE" ]]; then
  echo "ERROR: --keywords-file path missing or invalid" >&2
  exit 2
fi

PKG_SAFE="${PACKAGE//./-}"
TODAY="$(date +%Y%m%d)"
WORK_DIR="$DATA_DIR/master-precheck/${PKG_SAFE}-${TODAY}"
mkdir -p "$WORK_DIR"
echo "[precheck] workdir: $WORK_DIR"

run_step() {
  # run_step "label" cmd args...
  local label="$1"; shift
  echo "[precheck] >> $label"
  if "$@"; then
    echo "[precheck] OK  $label"
    return 0
  fi
  echo "[precheck] WARN $label failed (continuing)" >&2
  return 1
}

# 1. Play bulk reports — non-fatal if it fails (e.g. wrong dev account id)
run_step "play-bulk-reports" \
  python3 "$PY_ROOT/build-play-console.py" bulk-reports \
    --package "$PACKAGE" --months "$MONTHS" \
    --out "$WORK_DIR/play-bulk-reports.json" || true

# 2. Free keyword volume + Trends (existing FREE script)
if [[ -s "$KEYWORDS_FILE" ]]; then
  KWS=$(grep -v '^#' "$KEYWORDS_FILE" | sed '/^$/d' | head -50 | tr '\n' '\0' | xargs -0 -I{} printf '"%s" ' "{}")
  if [[ -n "$KWS" ]]; then
    eval "python3 \"$PY_ROOT/build-keyword-volume.py\" $KWS" \
      > "$WORK_DIR/keyword-volume-free.txt" 2>&1 || true
    echo "[precheck] OK  keyword-volume-free.txt"
  fi
fi

# 3. (DataForSEO step intentionally omitted — account is paid and we want
# this orchestrator to be 100% free. To re-enable, uncomment below.)
# run_step "keyword-volume-dataforseo" \
#   python3 "$PY_ROOT/build-keyword-volume.py" --source dataforseo \
#     --keywords-file "$KEYWORDS_FILE" --out "$WORK_DIR/keyword-volume-dataforseo.json" || true

# 4. Competitor App Store analyze
if [[ -n "$COMP_ASC" ]]; then
  IFS=',' read -ra ASC_IDS <<< "$COMP_ASC"
  run_step "competitors-asc" \
    python3 "$PY_ROOT/aso/aso-competitors.py" --analyze "${ASC_IDS[@]}" \
    > "$WORK_DIR/competitors-asc.txt" 2>&1 || true
fi

# 5. Competitor Play reviews
if [[ -n "$COMP_PLAY" ]]; then
  IFS=',' read -ra PLAY_PKGS <<< "$COMP_PLAY"
  run_step "competitors-play-reviews" \
    python3 "$PY_ROOT/aso/aso-competitors.py" \
      --play-reviews "${PLAY_PKGS[@]}" \
      --out "$WORK_DIR/competitors-play-reviews.json" --country "$COUNTRY" || true
fi

# 6. Firebase events (optional — requires Blaze + BQ link)
if [[ -n "$FIREBASE_PROJECT" ]]; then
  run_step "firebase-events" \
    python3 "$PY_ROOT/aso/aso-firebase-events.py" \
      --project "$FIREBASE_PROJECT" --days 30 \
      --funnel "gate_unlocked,home_create_room_clicked,room_created,message_sent,credits_exhausted,premium_modal_shown" \
      --out "$WORK_DIR/firebase-events.json" || true
fi

# 7. Deep Research prompt — emit a copy-paste prompt for ChatGPT
if [[ -n "$APP_SLUG" ]]; then
  run_step "deep-research-prompt" \
    python3 "$PY_ROOT/aso/aso-deep-research-prompt.py" \
      --app "$APP_SLUG" --keywords-file "$KEYWORDS_FILE" --country "$COUNTRY" \
      --out "$WORK_DIR/deep-research-prompt.txt" || true
fi

# 8. Combine into one master JSON
MASTER="${OUT:-$DATA_DIR/aso-master-table-${PKG_SAFE}-${TODAY}.json}"
python3 - "$WORK_DIR" "$MASTER" "$PACKAGE" "$TODAY" "$APP_SLUG" "$COUNTRY" <<'PY'
import json, sys
from pathlib import Path
work_dir = Path(sys.argv[1])
out = Path(sys.argv[2])
master = {
    "package": sys.argv[3],
    "generated_at": sys.argv[4],
    "app_slug": sys.argv[5] or None,
    "country": sys.argv[6],
    "sources": {},
    "missing": [],
}
mapping = {
    "play_bulk_reports": "play-bulk-reports.json",
    "keyword_volume_dataforseo": "keyword-volume-dataforseo.json",
    "competitors_play_reviews": "competitors-play-reviews.json",
    "firebase_events": "firebase-events.json",
}
for key, fname in mapping.items():
    p = work_dir / fname
    if p.exists():
        try:
            master["sources"][key] = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            master["sources"][key] = {"_parse_error": str(e)}
    else:
        master["missing"].append(key)

for key, fname in [("keyword_volume_free", "keyword-volume-free.txt"),
                   ("competitors_asc", "competitors-asc.txt"),
                   ("deep_research_prompt", "deep-research-prompt.txt")]:
    p = work_dir / fname
    if p.exists():
        master["sources"][key] = {"text": p.read_text(encoding="utf-8")}
    else:
        master["missing"].append(key)

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(master, indent=2), encoding="utf-8")
print(f"[precheck] master table -> {out}")
have = [k for k, v in master["sources"].items() if v]
print(f"[precheck] sources captured: {len(have)} / {len(mapping) + 3}")
print(f"[precheck] missing: {master['missing']}")
PY

echo
echo "Next steps:"
echo "  1. Open the Deep Research prompt:"
echo "       cat \"$WORK_DIR/deep-research-prompt.txt\""
echo "     Paste into ChatGPT, save response as JSON to"
echo "       $WORK_DIR/deep-research-result.json"
echo "  2. Re-run merge:"
echo "       python3 -c 'import json,pathlib; m=pathlib.Path(\"$MASTER\"); d=json.loads(m.read_text()); d[\"sources\"][\"deep_research_result\"]=json.loads(pathlib.Path(\"$WORK_DIR/deep-research-result.json\").read_text()); m.write_text(json.dumps(d,indent=2))'"
echo "  3. Write content from the master JSON, not from memory."
