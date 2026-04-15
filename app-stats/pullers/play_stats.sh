#!/usr/bin/env bash
# Pulls install + earnings CSVs from the Play Console's private GCS bucket.
# gsutil authenticates via GOOGLE_APPLICATION_CREDENTIALS (service account
# with "View financial data" on the app).
set -u

RANGE="${1:-lifetime}"
OUT_DIR="${2:?usage: play_stats.sh <range> <out_dir>}"
mkdir -p "$OUT_DIR"

: "${ANDROID_PACKAGE:?ANDROID_PACKAGE missing}"
: "${PLAY_REPORTS_BUCKET:?PLAY_REPORTS_BUCKET missing}"

if ! command -v gsutil >/dev/null 2>&1; then
  echo "gsutil not found. Install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install" >&2
  exit 1
fi

# Expand ~ in the creds path so gsutil picks it up via BOTO.
if [ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
  export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS/#\~/$HOME}"
fi

BUCKET="${PLAY_REPORTS_BUCKET#gs://}"
BUCKET="${BUCKET%%/*}"

filter_months() {
  # Play Console CSVs are named *_YYYYMM.csv. Range → which months to keep.
  case "$RANGE" in
    lifetime) cat ;;
    ytd)
      local y; y="$(date +%Y)"
      grep -E "_${y}[0-9]{2}\\.csv$" || true ;;
    last-30d)
      local m; m="$(date -v-1m +%Y%m 2>/dev/null || date -d '1 month ago' +%Y%m)"
      grep -E "_${m}\\.csv$" || true ;;
    last-90d)
      local m1 m2 m3
      m1="$(date -v-1m +%Y%m 2>/dev/null || date -d '1 month ago' +%Y%m)"
      m2="$(date -v-2m +%Y%m 2>/dev/null || date -d '2 months ago' +%Y%m)"
      m3="$(date -v-3m +%Y%m 2>/dev/null || date -d '3 months ago' +%Y%m)"
      grep -E "_(${m1}|${m2}|${m3})\\.csv$" || true ;;
  esac
}

sync_prefix() {
  local gcs_prefix="$1" dest="$2"
  mkdir -p "$dest"
  local all; all="$(gsutil ls "gs://${BUCKET}/${gcs_prefix}" 2>/dev/null || true)"
  [ -z "$all" ] && return 0
  local keep; keep="$(printf '%s\n' "$all" | filter_months)"
  [ -z "$keep" ] && return 0
  # -m parallel, -I reads URIs from stdin.
  printf '%s\n' "$keep" | gsutil -m cp -I "$dest/" 2>/dev/null || true
}

sync_prefix "stats/installs/installs_${ANDROID_PACKAGE}_*_overview.csv" "$OUT_DIR/installs"
sync_prefix "earnings/earnings_*.csv" "$OUT_DIR/earnings"

# Play exports are UTF-16LE with BOM. Normalize to UTF-8 so report_builder can parse.
for f in "$OUT_DIR"/installs/*.csv "$OUT_DIR"/earnings/*.csv; do
  [ -f "$f" ] || continue
  iconv -f UTF-16LE -t UTF-8 "$f" 2>/dev/null | sed '1s/^\xEF\xBB\xBF//' > "$f.utf8" && mv "$f.utf8" "$f"
done

echo "wrote $OUT_DIR"
