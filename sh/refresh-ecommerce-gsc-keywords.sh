#!/usr/bin/env bash
# Export Search Console queries that touch the ecommerce service URL to JSON.
# Requires: TEAMZ_HOST_SITE_ROOT = landing repo root, TEAMZ_SITE_URL = https://apps.teamzlab.com/
#           Google Search Console token + verified property for that URL.
#
# Usage (from landing repo root):
#   npm run refresh:ecommerce-keywords
#   # or:
#   bash teamz-company-automation/sh/refresh-ecommerce-gsc-keywords.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# teamz-company-automation/sh -> landing repo is two levels up
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export TEAMZ_HOST_SITE_ROOT="${TEAMZ_HOST_SITE_ROOT:-$REPO_ROOT}"
export TEAMZ_SITE_URL="${TEAMZ_SITE_URL:-https://apps.teamzlab.com/}"
export TEAMZ_SITE_PROPERTY="${TEAMZ_SITE_PROPERTY:-${TEAMZ_SITE_URL}}"

cd "$REPO_ROOT"
OUT_REL="teamz-company-automation/data/ecommerce-gsc-keywords-latest.json"
PY="teamz-company-automation/py/build-keyword-intel.py"

if [[ ! -f "$PY" ]]; then
  echo "refresh-ecommerce-gsc-keywords: missing $PY"
  exit 1
fi

echo "refresh-ecommerce-gsc-keywords: TEAMZ_HOST_SITE_ROOT=$TEAMZ_HOST_SITE_ROOT"
echo "refresh-ecommerce-gsc-keywords: TEAMZ_SITE_URL=$TEAMZ_SITE_URL"

set +e
python3 "$PY" --page "ecommerce-development" --top 80 --export json --output "$OUT_REL"
STATUS=$?
set -e

if [[ "$STATUS" -ne 0 ]]; then
  echo "refresh-ecommerce-gsc-keywords: GSC export failed or no token/data (exit $STATUS). The site still builds using ecommerce-landing-seo.json only."
  exit 0
fi

echo "refresh-ecommerce-gsc-keywords: wrote $OUT_REL — run: node scripts/sync-ecommerce-page-from-automation.mjs && npm run build"
