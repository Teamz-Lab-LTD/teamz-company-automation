#!/usr/bin/env bash
# ============================================
# Teamz Lab — Pre-Release Verification Script
# Reusable across all Teamz Lab Flutter + Firebase projects.
#
# Checks: Firebase config, Cloud Functions, secrets, SHA fingerprints,
#          enabled APIs, Flutter analyze, release build readiness.
#
# Run:  ./pre-release-verify.sh [--fix] [--skip-flutter] [--skip-firebase]
# ============================================

set -euo pipefail

SCRIPTS="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")" && pwd)"
source "$SCRIPTS/lib/config.sh"
teamz_load_config "$0"

# ── Resolve project root (works from kit submodule or project root) ──
# Walk up from CWD to find the Flutter project root (has pubspec.yaml + lib/main.dart)
_resolve_project_root() {
  # 1. If run from the project root directly
  if [[ -f "$(pwd)/lib/main.dart" ]]; then
    echo "$(pwd)"; return
  fi
  # 2. Walk up from TEAMZ_HOST_SITE_ROOT
  local dir="$TEAMZ_HOST_SITE_ROOT"
  for _ in 1 2 3 4; do
    if [[ -f "$dir/lib/main.dart" ]]; then
      echo "$dir"; return
    fi
    dir="$(dirname "$dir")"
  done
  # 3. Walk up from CWD
  dir="$(pwd)"
  for _ in 1 2 3 4; do
    if [[ -f "$dir/lib/main.dart" ]]; then
      echo "$dir"; return
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}

PROJECT_ROOT=$(_resolve_project_root) || {
  echo "ERROR: Cannot find Flutter project root. Run from project directory."
  exit 1
}
cd "$PROJECT_ROOT"

# ── Colors ──
RED='\033[0;31m'
YEL='\033[1;33m'
GRN='\033[0;32m'
CYN='\033[0;36m'
BLD='\033[1m'
NC='\033[0m'

# ── Flags ──
SKIP_FLUTTER=false
SKIP_FIREBASE=false
FIX_MODE=false
for arg in "$@"; do
  case "$arg" in
    --fix)            FIX_MODE=true ;;
    --skip-flutter)   SKIP_FLUTTER=true ;;
    --skip-firebase)  SKIP_FIREBASE=true ;;
  esac
done

PASS=0
FAIL=0
WARN=0
MANUAL=0

pass()   { ((PASS++)); echo -e "  ${GRN}✓${NC} $1"; }
fail()   { ((FAIL++)); echo -e "  ${RED}✗${NC} $1"; }
warn()   { ((WARN++)); echo -e "  ${YEL}⚠${NC} $1"; }
manual() { ((MANUAL++)); echo -e "  ${CYN}👤${NC} $1"; }
header() { echo -e "\n${BLD}── $1 ──${NC}"; }

# ── Auto-detect Firebase project ID ──
detect_firebase_project() {
  if [[ -f ".firebaserc" ]]; then
    grep -o '"default":\s*"[^"]*"' .firebaserc | head -1 | sed 's/.*"default":\s*"\([^"]*\)"/\1/'
  elif [[ -f "lib/firebase_options.dart" ]]; then
    grep "projectId:" lib/firebase_options.dart | head -1 | sed "s/.*'\([^']*\)'.*/\1/"
  fi
}

# ── Auto-detect Android package name ──
detect_package_name() {
  if [[ -f "android/app/build.gradle.kts" ]]; then
    grep 'applicationId' android/app/build.gradle.kts | head -1 | sed 's/.*"\(.*\)".*/\1/'
  elif [[ -f "android/app/build.gradle" ]]; then
    grep 'applicationId' android/app/build.gradle | head -1 | sed 's/.*"\(.*\)".*/\1/'
  fi
}

# ── Auto-detect iOS bundle ID ──
detect_bundle_id() {
  if [[ -f "ios/Runner.xcodeproj/project.pbxproj" ]]; then
    grep 'PRODUCT_BUNDLE_IDENTIFIER' ios/Runner.xcodeproj/project.pbxproj | head -1 | sed 's/.*= \(.*\);/\1/' | tr -d ' "'
  fi
}

FIREBASE_PROJECT=$(detect_firebase_project)
ANDROID_PACKAGE=$(detect_package_name)
IOS_BUNDLE=$(detect_bundle_id)
GCLOUD="/opt/homebrew/share/google-cloud-sdk/bin/gcloud"

echo -e "${BLD}Teamz Lab Pre-Release Verification${NC}"
echo "Project root: $PROJECT_ROOT"
echo "Firebase project: ${FIREBASE_PROJECT:-unknown}"
echo "Android package: ${ANDROID_PACKAGE:-unknown}"
echo "iOS bundle: ${IOS_BUNDLE:-unknown}"

# ══════════════════════════════════════════════
# 1. FLUTTER CHECKS
# ══════════════════════════════════════════════
if [[ "$SKIP_FLUTTER" == false ]]; then
  header "Flutter Code Quality"

  # Format check
  if fvm dart format --set-exit-if-changed -o none lib/ > /dev/null 2>&1; then
    pass "Code formatting OK"
  else
    if [[ "$FIX_MODE" == true ]]; then
      fvm dart format lib/ > /dev/null 2>&1
      pass "Code formatting fixed"
    else
      fail "Code formatting issues (run with --fix or: fvm dart format .)"
    fi
  fi

  # Analyze
  ANALYZE_OUTPUT=$(fvm flutter analyze lib/ 2>&1 || true)
  ERROR_COUNT=$(echo "$ANALYZE_OUTPUT" | grep -c "error •" || true)
  WARN_COUNT=$(echo "$ANALYZE_OUTPUT" | grep -c "warning •\|info •" || true)
  if [[ "$ERROR_COUNT" -gt 0 ]]; then
    fail "Flutter analyze: $ERROR_COUNT errors"
  elif [[ "$WARN_COUNT" -gt 0 ]]; then
    warn "Flutter analyze: $WARN_COUNT warnings/infos (no errors)"
  else
    pass "Flutter analyze clean"
  fi

  # Check for hardcoded secrets
  SECRET_HITS=$(grep -rn "sk-\|api[_-]key\s*=\s*['\"]" lib/ --include="*.dart" 2>/dev/null | grep -v "// " | grep -v "test" || true)
  if [[ -n "$SECRET_HITS" ]]; then
    fail "Possible hardcoded secrets in lib/"
    echo "$SECRET_HITS" | head -5 | sed 's/^/        /'
  else
    pass "No hardcoded secrets in lib/"
  fi

  # Check for print() usage
  PRINT_HITS=$(grep -rn "^\s*print(" lib/ --include="*.dart" 2>/dev/null || true)
  if [[ -n "$PRINT_HITS" ]]; then
    PRINT_COUNT=$(echo "$PRINT_HITS" | wc -l | tr -d ' ')
    fail "Found $PRINT_COUNT print() calls — use LoggerService instead"
  else
    pass "No print() calls in lib/"
  fi

  # Check mounted after await in StatefulWidgets
  MOUNTED_GAPS=$(grep -rn "await " lib/ --include="*.dart" -A1 2>/dev/null | grep -B1 "setState\|context\." | grep -v "mounted" | grep "await" || true)
  if [[ -n "$MOUNTED_GAPS" ]]; then
    MOUNTED_COUNT=$(echo "$MOUNTED_GAPS" | wc -l | tr -d ' ')
    warn "$MOUNTED_COUNT potential missing mounted checks after await"
  else
    pass "No obvious missing mounted checks"
  fi
fi

# ══════════════════════════════════════════════
# 2. FIREBASE CHECKS
# ══════════════════════════════════════════════
if [[ "$SKIP_FIREBASE" == false && -n "$FIREBASE_PROJECT" ]]; then
  header "Firebase Configuration"

  # Check firebase CLI logged in
  if firebase projects:list > /dev/null 2>&1; then
    pass "Firebase CLI authenticated"
  else
    fail "Firebase CLI not authenticated (run: firebase login)"
  fi

  # List deployed functions
  FUNCTIONS_OUTPUT=$(firebase functions:list --project "$FIREBASE_PROJECT" 2>&1 || true)
  if echo "$FUNCTIONS_OUTPUT" | grep -q "Function"; then
    FUNC_COUNT=$(echo "$FUNCTIONS_OUTPUT" | grep -c "│" || true)
    pass "Cloud Functions deployed ($((FUNC_COUNT / 2)) functions)"
  else
    fail "No Cloud Functions deployed"
  fi

  # Check enforceAppCheck in code vs console setup
  if [[ -d "functions/" ]]; then
    ENFORCE_HITS=$(grep -rn "enforceAppCheck:\s*true" functions/ --include="*.js" 2>/dev/null | grep -v "node_modules\|CLAUDE.md" || true)
    if [[ -n "$ENFORCE_HITS" ]]; then
      warn "enforceAppCheck: true found in Cloud Functions code"
      echo -e "        ${YEL}Verify App Check providers are registered in Firebase Console${NC}"
      manual "Firebase Console → App Check → Verify providers registered for all platforms"

      # Check SHA fingerprints (Android) — need the App ID
      ANDROID_APP_ID=$(grep "appId:" lib/firebase_options.dart 2>/dev/null | head -1 | sed "s/.*'\([^']*\)'.*/\1/" || true)
      if [[ -n "$ANDROID_APP_ID" ]]; then
        SHA_OUTPUT=$(firebase apps:android:sha:list "$ANDROID_APP_ID" --project "$FIREBASE_PROJECT" 2>&1 || true)
        SHA256_COUNT=$(echo "$SHA_OUTPUT" | grep -c "SHA_256" || true)
        if [[ "$SHA256_COUNT" -ge 2 ]]; then
          pass "Android SHA-256 fingerprints registered ($SHA256_COUNT — upload + Play signing)"
        elif [[ "$SHA256_COUNT" -ge 1 ]]; then
          warn "Only $SHA256_COUNT Android SHA-256 fingerprint — add both upload key AND Play signing key"
        else
          fail "No Android SHA-256 fingerprint in Firebase — App Check will fail"
        fi
      else
        warn "Could not detect Android App ID from firebase_options.dart"
      fi
    else
      pass "enforceAppCheck is disabled (safe for launch)"
    fi
  fi

  # Check secrets in Secret Manager
  if [[ -d "functions/" ]]; then
    SECRETS=$(grep -roh "defineSecret(\"[^\"]*\")" functions/ --include="*.js" 2>/dev/null | sed 's/defineSecret("\(.*\)")/\1/' | sort -u)
    if [[ -n "$SECRETS" ]]; then
      header "Cloud Function Secrets"
      while IFS= read -r secret; do
        if firebase functions:secrets:access "$secret" --project "$FIREBASE_PROJECT" > /dev/null 2>&1; then
          pass "Secret $secret exists in Secret Manager"
        else
          fail "Secret $secret NOT in Secret Manager"
        fi
      done <<< "$SECRETS"

      # Check .env overlap
      if [[ -f "functions/.env" ]]; then
        ENV_OVERLAP=false
        while IFS= read -r secret; do
          if grep -q "^$secret=" functions/.env 2>/dev/null; then
            fail "Secret $secret is in BOTH .env AND Secret Manager — deploy will fail"
            ENV_OVERLAP=true
          fi
        done <<< "$SECRETS"
        if [[ "$ENV_OVERLAP" == false ]]; then
          pass "No .env / Secret Manager overlap"
        fi
      fi
    fi
  fi

  # Check google-services.json has certificate hashes
  if [[ -f "android/app/google-services.json" ]]; then
    header "Android Firebase Config"
    OAUTH_COUNT=$(python3 -c "
import json
with open('android/app/google-services.json') as f:
    data = json.load(f)
clients = data.get('client', [])
total = sum(len(c.get('oauth_client', [])) for c in clients)
print(total)
" 2>/dev/null || echo "0")
    if [[ "$OAUTH_COUNT" -gt 0 ]]; then
      pass "google-services.json has $OAUTH_COUNT oauth_client entries"
    else
      warn "google-services.json has empty oauth_client — re-download from Firebase Console after adding SHA fingerprints"
    fi
  fi

  # Check enabled APIs via gcloud (if available)
  if [[ -x "$GCLOUD" ]]; then
    GCLOUD_AUTHED=$("$GCLOUD" auth list --format="value(account)" 2>/dev/null || true)
    if [[ -n "$GCLOUD_AUTHED" ]]; then
      header "Google Cloud APIs"
      for api in "playintegrity.googleapis.com" "firebaseappcheck.googleapis.com" "secretmanager.googleapis.com"; do
        SHORT_NAME=$(echo "$api" | cut -d. -f1)
        if "$GCLOUD" services list --enabled --project "$FIREBASE_PROJECT" --format="value(name)" 2>/dev/null | grep -q "$api"; then
          pass "API enabled: $SHORT_NAME"
        else
          warn "API not enabled: $SHORT_NAME"
        fi
      done
    else
      manual "gcloud not authenticated — run: $GCLOUD auth login"
    fi
  fi
fi

# ══════════════════════════════════════════════
# 3. ANDROID RELEASE CHECKS
# ══════════════════════════════════════════════
header "Android Release"

# Check key.properties exists
if [[ -f "android/key.properties" ]]; then
  pass "key.properties exists"

  # Check keystore file exists
  KEYSTORE_PATH=$(grep "storeFile" android/key.properties | cut -d= -f2 | tr -d ' ')
  if [[ -f "android/app/$KEYSTORE_PATH" ]]; then
    pass "Keystore file found: $KEYSTORE_PATH"
  else
    fail "Keystore file not found: android/app/$KEYSTORE_PATH"
  fi
else
  fail "android/key.properties missing — cannot sign release builds"
fi

# Check .gitignore has sensitive files
if grep -q "key.properties" .gitignore 2>/dev/null; then
  pass "key.properties in .gitignore"
else
  fail "key.properties NOT in .gitignore — secrets at risk"
fi

if grep -q "*.jks" .gitignore 2>/dev/null || grep -q "upload-keystore" .gitignore 2>/dev/null; then
  pass "Keystore in .gitignore"
else
  warn "Keystore files may not be in .gitignore"
fi

# ══════════════════════════════════════════════
# 4. iOS RELEASE CHECKS
# ══════════════════════════════════════════════
header "iOS Release"

# ── Auto-detect monetization model from codebase ──
USES_ADS=false
USES_IAP=false
USES_REVENUECAT=false
ADS_PERSONALIZED=false

# Detect ads (check app pubspec, kit pubspec, pubspec.lock, and main.dart for ad config)
if grep -q "google_mobile_ads" pubspec.yaml pubspec.lock packages/*/pubspec.yaml 2>/dev/null; then
  # Also verify ads are actually enabled in code (not just a dependency)
  if grep -q "AdsConfig\|adsConfig\|google_mobile_ads\|AdMob\|admob" lib/main.dart 2>/dev/null; then
    USES_ADS=true
  elif grep -q "GADApplicationIdentifier" ios/Runner/Info.plist 2>/dev/null; then
    USES_ADS=true
  fi
fi
# Detect RevenueCat / IAP (check app, kit, and lock file)
if grep -q "purchases_flutter\|revenue_cat\|in_app_purchase" pubspec.yaml pubspec.lock packages/*/pubspec.yaml 2>/dev/null; then
  USES_IAP=true
fi
if grep -q "initializeRevenueCat.*true" lib/main.dart 2>/dev/null; then
  USES_REVENUECAT=true
elif [[ "$USES_IAP" == true ]] && grep -q "initializeRevenueCat.*false" lib/main.dart 2>/dev/null; then
  # RevenueCat dependency exists but explicitly disabled
  USES_REVENUECAT=false
  USES_IAP=false
fi
# Detect personalized vs non-personalized ads
if grep -q "nonPersonalizedAds.*true" lib/main.dart 2>/dev/null; then
  ADS_PERSONALIZED=false
elif [[ "$USES_ADS" == true ]]; then
  ADS_PERSONALIZED=true
fi

# Show detected model
if [[ "$USES_ADS" == true && "$USES_REVENUECAT" == true ]]; then
  echo -e "  ${CYN}Monetization: Ads + IAP (RevenueCat)${NC}"
elif [[ "$USES_ADS" == true ]]; then
  echo -e "  ${CYN}Monetization: Ads only${NC}"
elif [[ "$USES_REVENUECAT" == true || "$USES_IAP" == true ]]; then
  echo -e "  ${CYN}Monetization: IAP only (no ads)${NC}"
else
  echo -e "  ${CYN}Monetization: Free (no ads, no IAP)${NC}"
fi

if [[ -f "ios/Runner/Info.plist" ]]; then

  # ── AdMob checks (only if project uses ads) ──
  if [[ "$USES_ADS" == true ]]; then
    # Check GADApplicationIdentifier
    if grep -q "GADApplicationIdentifier" ios/Runner/Info.plist; then
      GAD_ID=$(python3 -c "
import plistlib
with open('ios/Runner/Info.plist', 'rb') as f:
    d = plistlib.load(f)
print(d.get('GADApplicationIdentifier',''))
" 2>/dev/null || true)
      if [[ "$GAD_ID" == *"3940256099942544"* ]]; then
        fail "AdMob App ID is TEST ID — replace with production ID"
      else
        pass "AdMob App ID configured: $GAD_ID"
      fi
    else
      fail "google_mobile_ads in pubspec but no GADApplicationIdentifier in Info.plist"
    fi

    # Check SKAdNetwork
    if grep -q "SKAdNetworkItems" ios/Runner/Info.plist; then
      pass "SKAdNetworkItems configured"
    else
      warn "Missing SKAdNetworkItems — ad attribution may not work"
    fi

    # Check test ad IDs are gated by kDebugMode
    TEST_AD_COUNT=$(grep -c "ca-app-pub-3940256099942544" lib/main.dart 2>/dev/null || true)
    TEST_AD_COUNT=${TEST_AD_COUNT:-0}
    if [[ "$TEST_AD_COUNT" -gt 0 ]]; then
      if grep -B5 "ca-app-pub-3940256099942544" lib/main.dart 2>/dev/null | grep -q "kDebugMode"; then
        pass "Test ad IDs properly gated by kDebugMode"
      else
        fail "Test ad IDs NOT gated by kDebugMode — will show test ads in production!"
      fi
    else
      pass "No test ad IDs found (all production)"
    fi

    # Check ATT vs nonPersonalizedAds consistency
    HAS_ATT=$(grep -c "NSUserTrackingUsageDescription" ios/Runner/Info.plist 2>/dev/null || true)
    HAS_ATT=${HAS_ATT:-0}
    if [[ "$ADS_PERSONALIZED" == false ]]; then
      # Non-personalized: ATT should NOT be present
      if [[ "$HAS_ATT" -gt 0 ]]; then
        warn "NSUserTrackingUsageDescription present BUT nonPersonalizedAds=true — conflict! Remove ATT key or set nonPersonalizedAds=false"
      else
        pass "No ATT prompt (correct for nonPersonalizedAds)"
      fi
    else
      # Personalized: ATT SHOULD be present
      if [[ "$HAS_ATT" -gt 0 ]]; then
        pass "NSUserTrackingUsageDescription present (needed for personalized ads)"
      else
        fail "Personalized ads enabled but NSUserTrackingUsageDescription missing — Apple will reject"
      fi
    fi
  else
    # No ads — ATT should NOT be present
    if grep -q "NSUserTrackingUsageDescription" ios/Runner/Info.plist 2>/dev/null; then
      warn "NSUserTrackingUsageDescription present but app doesn't use ads — remove it"
    fi
    if grep -q "GADApplicationIdentifier" ios/Runner/Info.plist 2>/dev/null; then
      warn "GADApplicationIdentifier in Info.plist but google_mobile_ads not in pubspec"
    fi
    pass "No ads — ad-related checks skipped"
  fi

  # ── IAP / RevenueCat checks (only if project uses IAP) ──
  if [[ "$USES_REVENUECAT" == true || "$USES_IAP" == true ]]; then
    # Check StoreKit configuration
    if ls ios/*.storekit ios/Runner/*.storekit 2>/dev/null | head -1 > /dev/null 2>&1; then
      pass "StoreKit configuration file found"
    else
      warn "No .storekit file found — needed for local IAP testing"
    fi

    # Check if products are configured in code
    if grep -rq "entitlementIdentifier\|productId\|offering" lib/ --include="*.dart" 2>/dev/null; then
      pass "IAP product/entitlement IDs found in code"
    else
      warn "No product/entitlement IDs found in lib/ — verify IAP setup"
    fi

    # Manual check for App Store Connect
    manual "Verify IAP products are created in App Store Connect → In-App Purchases"
    manual "Verify IAP products are in 'Ready to Submit' or 'Approved' state"
  fi

  # ── Common iOS checks (always run) ──

  # Check ITSAppUsesNonExemptEncryption
  if grep -q "ITSAppUsesNonExemptEncryption" ios/Runner/Info.plist; then
    pass "Encryption declaration present"
  else
    warn "Missing ITSAppUsesNonExemptEncryption — App Store will ask during upload"
  fi

  # Check NSPhotoLibraryUsageDescription (if share_plus is used)
  if grep -q "share_plus" pubspec.yaml 2>/dev/null; then
    if grep -q "NSPhotoLibraryUsageDescription" ios/Runner/Info.plist; then
      pass "NSPhotoLibraryUsageDescription present (share_plus)"
    else
      warn "share_plus used but NSPhotoLibraryUsageDescription missing"
    fi
  fi

  # Check PrivacyInfo.xcprivacy exists
  if [[ -f "ios/Runner/PrivacyInfo.xcprivacy" ]]; then
    pass "PrivacyInfo.xcprivacy exists"
  else
    fail "PrivacyInfo.xcprivacy missing — required by Apple"
  fi

  # Check development team
  DEV_TEAM=$(grep "DEVELOPMENT_TEAM" ios/Runner.xcodeproj/project.pbxproj 2>/dev/null | head -1 | sed 's/.*= \(.*\);/\1/' | tr -d ' "' || true)
  if [[ -n "$DEV_TEAM" ]]; then
    pass "Development team: $DEV_TEAM"
  else
    fail "No DEVELOPMENT_TEAM set in Xcode project"
  fi
fi

# ══════════════════════════════════════════════
# 5. FASTLANE & APP STORE CONNECT CHECKS
# ══════════════════════════════════════════════
header "Fastlane & App Store Connect"

# Check Fastlane installed
if command -v fastlane > /dev/null 2>&1; then
  pass "Fastlane installed ($(fastlane --version 2>/dev/null | head -1 | sed 's/fastlane //' || echo 'unknown'))"
else
  fail "Fastlane not installed — run: brew install fastlane"
fi

# Check Fastlane setup for this project
if [[ -f "fastlane/Fastfile" ]]; then
  pass "Fastlane configured (fastlane/Fastfile exists)"
else
  fail "Fastlane not set up — run: bash packages/team_mvp_kit/teamz-company-automation/appstore-fastlane/setup-appstore-fastlane.sh"
fi

# Check .appstore-fastlane.env
if [[ -f ".appstore-fastlane.env" ]]; then
  pass ".appstore-fastlane.env exists"

  # Check API key file
  KEY_PATH=$(grep "ASC_KEY_FILEPATH" .appstore-fastlane.env 2>/dev/null | cut -d= -f2 | tr -d ' ')
  EXPANDED_KEY_PATH=$(eval echo "$KEY_PATH" 2>/dev/null || echo "")
  if [[ -f "$EXPANDED_KEY_PATH" ]]; then
    pass "App Store Connect API key found: $(basename "$EXPANDED_KEY_PATH")"
  else
    fail "API key file not found: $KEY_PATH"
    manual "Generate at: https://appstoreconnect.apple.com/access/integrations/api"
  fi

  # Check required env vars are set (not placeholder)
  for var in ASC_KEY_ID ASC_ISSUER_ID APP_BUNDLE_ID; do
    VAL=$(grep "^$var=" .appstore-fastlane.env 2>/dev/null | cut -d= -f2)
    if [[ -z "$VAL" || "$VAL" == "YOUR_"* ]]; then
      fail "$var not configured in .appstore-fastlane.env"
    else
      pass "$var configured"
    fi
  done
else
  fail ".appstore-fastlane.env missing — run setup script"
fi

# Check metadata completeness
if [[ -d "fastlane/metadata" ]]; then
  LOCALE_COUNT=$(ls -d fastlane/metadata/*/ 2>/dev/null | wc -l | tr -d ' ')
  EMPTY_COUNT=0
  for locale_dir in fastlane/metadata/*/; do
    for file in name.txt subtitle.txt keywords.txt description.txt; do
      if [[ ! -s "${locale_dir}${file}" ]]; then
        EMPTY_COUNT=$((EMPTY_COUNT + 1))
      fi
    done
  done
  if [[ "$EMPTY_COUNT" -gt 0 ]]; then
    warn "Metadata: $LOCALE_COUNT locales, $EMPTY_COUNT empty files"
  else
    pass "Metadata complete: $LOCALE_COUNT locales, all files populated"
  fi

  # Check char limits on en-US
  if [[ -d "fastlane/metadata/en-US" ]]; then
    NAME_LEN=$(printf '%s' "$(cat fastlane/metadata/en-US/name.txt 2>/dev/null)" | wc -m | tr -d ' ')
    SUB_LEN=$(printf '%s' "$(cat fastlane/metadata/en-US/subtitle.txt 2>/dev/null)" | wc -m | tr -d ' ')
    KW_LEN=$(printf '%s' "$(cat fastlane/metadata/en-US/keywords.txt 2>/dev/null)" | wc -m | tr -d ' ')
    [[ "$NAME_LEN" -gt 30 ]] && fail "en-US name too long: $NAME_LEN/30 chars" || pass "en-US name OK: $NAME_LEN/30 chars"
    [[ "$SUB_LEN" -gt 30 ]] && fail "en-US subtitle too long: $SUB_LEN/30 chars" || pass "en-US subtitle OK: $SUB_LEN/30 chars"
    [[ "$KW_LEN" -gt 100 ]] && fail "en-US keywords too long: $KW_LEN/100 chars" || pass "en-US keywords OK: $KW_LEN/100 chars"
  fi
else
  warn "No fastlane/metadata/ directory — metadata not set up"
fi

# Check screenshots
if [[ -d "fastlane/screenshots/en-US" ]]; then
  SS_COUNT=$(ls fastlane/screenshots/en-US/*.png 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$SS_COUNT" -ge 6 ]]; then
    pass "Screenshots: $SS_COUNT files (iPhone + iPad)"
  elif [[ "$SS_COUNT" -ge 3 ]]; then
    warn "Screenshots: only $SS_COUNT files — need 3+ per device size (6.7\", 6.5\", iPad)"
  else
    fail "Screenshots: only $SS_COUNT files — Apple requires at least 3"
  fi
else
  warn "No screenshots directory — fastlane/screenshots/en-US/"
fi

# Check Deliverfile has review contact
if [[ -f "fastlane/Deliverfile" ]]; then
  if grep -q "phone_number" fastlane/Deliverfile; then
    if grep -q 'phone_number: ""' fastlane/Deliverfile 2>/dev/null; then
      fail "Review phone number is empty in Deliverfile"
    else
      pass "Review contact info configured in Deliverfile"
    fi
  else
    warn "No review contact info in Deliverfile"
  fi

  # Check copyright
  if grep -q "copyright" fastlane/Deliverfile; then
    pass "Copyright configured in Deliverfile"
  else
    warn "No copyright in Deliverfile — Apple requires this"
  fi
fi

# ══════════════════════════════════════════════
# 6. APP STORE CONNECT MANUAL CHECKLIST
# ══════════════════════════════════════════════
header "App Store Connect Manual Checklist"
echo -e "  ${CYN}These cannot be automated — verify before submitting:${NC}"
manual "Pricing set (Free or correct tier) — App Store Connect → Pricing"
manual "App Privacy form completed — App Store Connect → App Privacy"
manual "Age Rating questionnaire filled — App Store Connect → Age Rating"
manual "MRDP declaration done — 'personal service' question → No"
manual "License Agreement accepted — developer.apple.com/account"
manual "Content Rights declared — 'does not use third-party content'"

# Monetization-specific manual checks
if [[ "$USES_ADS" == true ]]; then
  echo ""
  echo -e "  ${CYN}Ads-specific:${NC}"
  manual "App Privacy: Device ID → Yes → Analytics, Advertising → Not linked → No tracking"
  if [[ "$ADS_PERSONALIZED" == true ]]; then
    manual "App Privacy: mark 'Yes' for tracking (personalized ads)"
  fi
fi
if [[ "$USES_REVENUECAT" == true || "$USES_IAP" == true ]]; then
  echo ""
  echo -e "  ${CYN}IAP-specific:${NC}"
  manual "IAP products created & approved in App Store Connect → In-App Purchases"
  manual "IAP products linked to app version for review"
  manual "App Privacy: Purchases → Yes → App Functionality → Not linked"
fi

# ══════════════════════════════════════════════
# 7. SUMMARY
# ══════════════════════════════════════════════
echo ""
echo -e "${BLD}══════════════════════════════════════${NC}"
echo -e "${BLD}  Pre-Release Verification Summary${NC}"
echo -e "${BLD}══════════════════════════════════════${NC}"
echo -e "  ${GRN}✓ Passed:${NC}  $PASS"
echo -e "  ${RED}✗ Failed:${NC}  $FAIL"
echo -e "  ${YEL}⚠ Warnings:${NC} $WARN"
echo -e "  ${CYN}👤 Manual:${NC}  $MANUAL"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
  echo -e "${RED}${BLD}RELEASE BLOCKED — fix $FAIL failure(s) before releasing.${NC}"
  exit 1
elif [[ "$MANUAL" -gt 0 ]]; then
  echo -e "${YEL}${BLD}RELEASE NEEDS MANUAL CHECKS — verify $MANUAL item(s) in Firebase/Play Console.${NC}"
  exit 0
elif [[ "$WARN" -gt 0 ]]; then
  echo -e "${YEL}${BLD}RELEASE OK with $WARN warning(s).${NC}"
  exit 0
else
  echo -e "${GRN}${BLD}ALL CLEAR — ready to release!${NC}"
  exit 0
fi
