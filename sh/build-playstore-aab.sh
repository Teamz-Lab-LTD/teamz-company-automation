#!/usr/bin/env bash
# Teamz Lab — release Android App Bundle (AAB) for Google Play
#
# Generic script for any Flutter project. Reads all values from pubspec.yaml
# and android/app/build.gradle.kts — no hardcoded project names.
#
# Naming convention:
#   {DisplayName}_PlayStore_{applicationId}_v{versionName}_versionCode{versionCode}_{YYYY-MM-DD}_release.aab
#
# Sources: versionName + versionCode from pubspec.yaml "version: name+code";
#          applicationId from android/app/build.gradle.kts
#          displayName from TEAMZ_PLAY_DISPLAY_NAME env or pubspec.yaml "name:" field
#
# Usage (from project root):
#   bash packages/team_mvp_kit/teamz-company-automation/sh/build-playstore-aab.sh
#   # Or via symlink:
#   ./scripts/build-playstore-aab.sh
#   # Override display name:
#   TEAMZ_PLAY_DISPLAY_NAME="My App" ./scripts/build-playstore-aab.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# If run from automation submodule sh/, navigate to project root
if [[ -f "$ROOT/../py/_teamz_config.py" ]]; then
  # Running from automation submodule — go up to project root
  # Try TEAMZ_HOST_SITE_ROOT first, then walk up to find pubspec.yaml
  if [[ -n "${TEAMZ_HOST_SITE_ROOT:-}" && -f "$TEAMZ_HOST_SITE_ROOT/pubspec.yaml" ]]; then
    ROOT="$TEAMZ_HOST_SITE_ROOT"
  else
    # Walk up until we find pubspec.yaml
    SEARCH="$ROOT"
    while [[ "$SEARCH" != "/" ]]; do
      if [[ -f "$SEARCH/pubspec.yaml" ]]; then
        ROOT="$SEARCH"
        break
      fi
      SEARCH="$(dirname "$SEARCH")"
    done
  fi
elif [[ -f "$ROOT/../pubspec.yaml" ]]; then
  # Running from project scripts/ dir
  ROOT="$(cd "$ROOT/.." && pwd)"
fi

cd "$ROOT"

if [[ ! -f pubspec.yaml ]]; then
  echo "ERROR: pubspec.yaml not found in $ROOT" >&2
  exit 1
fi

# Display name: env override → pubspec "name:" field
if [[ -n "${TEAMZ_PLAY_DISPLAY_NAME:-}" ]]; then
  DISPLAY_NAME="$TEAMZ_PLAY_DISPLAY_NAME"
else
  DISPLAY_NAME="$(grep -E '^name:' pubspec.yaml | head -n1 | sed 's/^name:[[:space:]]*//' | tr -d '\r')"
fi
# No spaces in artifact names
DISPLAY_NAME="${DISPLAY_NAME// /_}"

VER_LINE="$(grep -E '^version:' pubspec.yaml | head -n1 | tr -d '\r')"
if [[ ! "$VER_LINE" =~ ^version:[[:space:]]*([^+]+)\+([0-9]+)[[:space:]]*$ ]]; then
  echo "ERROR: pubspec.yaml must have version like 1.0.0+1 (got: ${VER_LINE:-empty})" >&2
  exit 1
fi
VERSION_NAME="${BASH_REMATCH[1]}"
VERSION_CODE="${BASH_REMATCH[2]}"

APP_ID_LINE="$(grep -E 'applicationId[[:space:]]*=' android/app/build.gradle.kts | head -n1)"
if [[ ! "$APP_ID_LINE" =~ \"([^\"]+)\" ]]; then
  echo "ERROR: could not parse applicationId from android/app/build.gradle.kts" >&2
  exit 1
fi
APPLICATION_ID="${BASH_REMATCH[1]}"

BUILD_DATE="$(date +%Y-%m-%d)"
OUT_BASENAME="${DISPLAY_NAME}_PlayStore_${APPLICATION_ID}_v${VERSION_NAME}_versionCode${VERSION_CODE}_${BUILD_DATE}_release.aab"
OUT_PATH="dist/${OUT_BASENAME}"

echo "==> Building release appbundle (fvm)…"
echo "    versionName=$VERSION_NAME versionCode=$VERSION_CODE applicationId=$APPLICATION_ID"
fvm flutter build appbundle --release

mkdir -p dist
cp -f build/app/outputs/bundle/release/app-release.aab "$OUT_PATH"

echo ""
echo "==> Play Store AAB (copy for upload / tracking):"
echo "    $ROOT/$OUT_PATH"
ls -lh "$OUT_PATH"
echo ""
echo "SHA-256:"
shasum -a 256 "$OUT_PATH" | awk '{print $1}'
