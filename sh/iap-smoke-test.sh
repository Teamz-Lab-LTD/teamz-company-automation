#!/usr/bin/env bash
# iap-smoke-test.sh — exercise the IAP automation gates without writing.
#
# Runs (in order):
#   1. iap_discovery.py refresh     (verifies Google discovery doc reachable + cached)
#   2. iap_discovery.py check ...   (positive + negative path checks)
#   3. iap_preflight.py             (14 precondition checks, fails loudly)
#   4. iap.py setup --dry-run       (prints resolved API bodies, no writes)
#   5. iap.py setup --verify-only   (reads both stores + RC, no writes)
#
# Reads the host project's .teamz-automation.env + .env.local (must be
# at the cwd or one level deep). Pass --sku/--name/--description on the
# command line, or accept the chopstick defaults for the canonical
# Captain's Bundle test target.
#
# Exits non-zero on any gate failure. Suitable for CI.
#
# Usage:
#   bash team_mvp_kit/teamz-company-automation/sh/iap-smoke-test.sh
#   bash .../iap-smoke-test.sh --sku <new-sku> --name "<name>" --description "<desc>"

set -u
set -o pipefail

SKU="${SKU:-com.teamz.chopstick.captains_bundle}"
PRICE="${PRICE:-2.99}"
NAME="${NAME:-Captains Bundle}"
DESC="${DESC:-Remove ads forever and unlock all current rocket skins.}"
ENTITLEMENT="${ENTITLEMENT:-remove_ads}"
PACKAGE="${PACKAGE:-captains_bundle}"

while [ $# -gt 0 ]; do
    case "$1" in
        --sku) SKU="$2"; shift 2 ;;
        --price) PRICE="$2"; shift 2 ;;
        --name) NAME="$2"; shift 2 ;;
        --description) DESC="$2"; shift 2 ;;
        --rc-entitlement) ENTITLEMENT="$2"; shift 2 ;;
        --rc-package) PACKAGE="$2"; shift 2 ;;
        --help|-h)
            grep '^# ' "$0" | sed 's/^# //'
            exit 0
            ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PY_DIR="${SCRIPT_DIR}/../py"

step() {
    printf '\n\033[1;36m==> %s\033[0m\n' "$*"
}

fail() {
    printf '\n\033[1;31m[FAIL] %s\033[0m\n' "$*" >&2
    exit 1
}

step "1/5 refresh Google discovery doc"
python3 "${PY_DIR}/iap_discovery.py" refresh || fail "discovery refresh failed (network?)"

step "2a/5 discovery sanity (PATCH onetimeproducts)"
python3 "${PY_DIR}/iap_discovery.py" check PATCH \
    "androidpublisher/v3/applications/{packageName}/onetimeproducts/{productId}" \
    || fail "PATCH onetimeproducts not in discovery — Google may have renamed; investigate"

step "2b/5 discovery sanity (GET oneTimeProducts camelCase)"
python3 "${PY_DIR}/iap_discovery.py" check GET \
    "androidpublisher/v3/applications/{packageName}/oneTimeProducts/{productId}" \
    || fail "GET oneTimeProducts not in discovery — Google may have renamed; investigate"

step "2c/5 discovery negative test (lowercase GET — should FAIL)"
if python3 "${PY_DIR}/iap_discovery.py" check GET \
    "androidpublisher/v3/applications/{packageName}/onetimeproducts/{productId}" \
    >/dev/null 2>&1; then
    fail "lowercase GET unexpectedly accepted — discovery enforcement broken"
fi
echo "  (expected ValueError; discovery enforcement working)"

step "3/5 iap_preflight (14 checks)"
python3 "${PY_DIR}/iap_preflight.py" \
    --sku "$SKU" \
    --price-usd "$PRICE" \
    --name "$NAME" \
    --description "$DESC" \
    || fail "preflight failed — fix the failed check above before touching iap.py setup"

step "4/5 iap.py setup --dry-run"
python3 "${PY_DIR}/iap.py" setup \
    --sku "$SKU" \
    --price-usd "$PRICE" \
    --name "$NAME" \
    --description "$DESC" \
    --rc-entitlement "$ENTITLEMENT" \
    --rc-package "$PACKAGE" \
    --dry-run \
    || fail "dry-run unexpectedly errored"

step "5/5 iap.py setup --verify-only"
python3 "${PY_DIR}/iap.py" setup \
    --sku "$SKU" \
    --price-usd "$PRICE" \
    --name "$NAME" \
    --description "$DESC" \
    --rc-entitlement "$ENTITLEMENT" \
    --rc-package "$PACKAGE" \
    --verify-only \
    || echo "  (verify-only non-zero — expected on a fresh app where no IAP yet exists)"

printf '\n\033[1;32m==> SMOKE TEST PASSED\033[0m\n'
