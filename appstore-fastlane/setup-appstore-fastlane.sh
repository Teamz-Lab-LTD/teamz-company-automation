#!/usr/bin/env bash
# ─── Teamz Lab — App Store Fastlane Setup ────────────────────────
# Run this from your Flutter project root to set up Fastlane.
# It symlinks the shared Fastfile and creates project-specific config.
#
# Usage:
#   bash packages/team_mvp_kit/teamz-company-automation/appstore-fastlane/setup-appstore-fastlane.sh
#
# What it does:
#   1. Creates fastlane/ directory in project root
#   2. Symlinks the shared Fastfile from kit submodule
#   3. Copies env template if not already present
#   4. Creates metadata directory structure for all 40 Apple locales
#   5. Adds entries to .gitignore

set -euo pipefail

# ── Resolve paths ──

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

echo "📦 Setting up App Store Fastlane for: ${PROJECT_ROOT}"
echo ""

# ── 1. Create fastlane directory ──

FASTLANE_DIR="${PROJECT_ROOT}/fastlane"
mkdir -p "${FASTLANE_DIR}"
echo "✅ Created fastlane/ directory"

# ── 2. Symlink shared Fastfile ──

FASTFILE_LINK="${FASTLANE_DIR}/Fastfile"
FASTFILE_TARGET="${SCRIPT_DIR}/Fastfile"

if [ -L "${FASTFILE_LINK}" ]; then
  echo "⏭️  Fastfile symlink already exists, skipping"
elif [ -f "${FASTFILE_LINK}" ]; then
  echo "⚠️  Fastfile already exists (not a symlink). Backing up to Fastfile.bak"
  mv "${FASTFILE_LINK}" "${FASTFILE_LINK}.bak"
  ln -s "${FASTFILE_TARGET}" "${FASTFILE_LINK}"
  echo "✅ Symlinked Fastfile (old file backed up)"
else
  ln -s "${FASTFILE_TARGET}" "${FASTFILE_LINK}"
  echo "✅ Symlinked Fastfile → kit submodule"
fi

# ── 3. Symlink Gemfile ──

GEMFILE_LINK="${FASTLANE_DIR}/Gemfile"
GEMFILE_TARGET="${SCRIPT_DIR}/Gemfile"

if [ -L "${GEMFILE_LINK}" ] || [ -f "${GEMFILE_LINK}" ]; then
  echo "⏭️  Gemfile already exists, skipping"
else
  ln -s "${GEMFILE_TARGET}" "${GEMFILE_LINK}"
  echo "✅ Symlinked Gemfile"
fi

# ── 4. Copy env template ──

ENV_FILE="${PROJECT_ROOT}/.appstore-fastlane.env"

if [ -f "${ENV_FILE}" ]; then
  echo "⏭️  .appstore-fastlane.env already exists, skipping"
else
  cp "${SCRIPT_DIR}/appstore-fastlane.env.example" "${ENV_FILE}"
  echo "✅ Created .appstore-fastlane.env (edit this with your app details)"
fi

# ── 5. Create metadata directories for all 40 Apple locales ──

METADATA_DIR="${FASTLANE_DIR}/metadata"

# All 40 Apple App Store locales
LOCALES=(
  "en-US"
  "ar-SA"
  "ca"
  "cs"
  "da"
  "de-DE"
  "el"
  "es-ES"
  "es-MX"
  "fi"
  "fr-CA"
  "fr-FR"
  "he"
  "hi"
  "hr"
  "hu"
  "id"
  "it"
  "ja"
  "ko"
  "ms"
  "nl-NL"
  "no"
  "pl"
  "pt-BR"
  "pt-PT"
  "ro"
  "ru"
  "sk"
  "sv"
  "th"
  "tr"
  "uk"
  "vi"
  "zh-Hans"
  "zh-Hant"
  "en-AU"
  "en-CA"
  "en-GB"
)

METADATA_FILES=(
  "name.txt"
  "subtitle.txt"
  "description.txt"
  "keywords.txt"
  "release_notes.txt"
  "promotional_text.txt"
  "privacy_url.txt"
  "support_url.txt"
  "marketing_url.txt"
)

for locale in "${LOCALES[@]}"; do
  locale_dir="${METADATA_DIR}/${locale}"
  mkdir -p "${locale_dir}"
  for file in "${METADATA_FILES[@]}"; do
    touch "${locale_dir}/${file}"
  done
done

# Create screenshots directories too
SCREENSHOT_DEVICES=(
  "APP_IPHONE_67"
  "APP_IPHONE_65"
  "APP_IPHONE_55"
  "APP_IPAD_PRO_129"
  "APP_IPAD_PRO_3GEN_129"
)

for locale in "${LOCALES[@]}"; do
  for device in "${SCREENSHOT_DEVICES[@]}"; do
    mkdir -p "${FASTLANE_DIR}/screenshots/${locale}/${device}"
  done
done

echo "✅ Created metadata directories for ${#LOCALES[@]} locales"
echo "✅ Created screenshot directories for ${#SCREENSHOT_DEVICES[@]} device sizes"

# ── 6. Create Deliverfile ──

DELIVERFILE="${FASTLANE_DIR}/Deliverfile"
if [ ! -f "${DELIVERFILE}" ]; then
  cat > "${DELIVERFILE}" << 'DELIVER_EOF'
# Deliverfile — project-specific deliver config
# Most config comes from the shared Fastfile + .appstore-fastlane.env

# App review information (update per project)
app_review_information(
  first_name: "Teamz",
  last_name: "Lab",
  phone_number: "",
  email_address: "teamz.lab.contact@gmail.com"
)
DELIVER_EOF
  echo "✅ Created Deliverfile"
else
  echo "⏭️  Deliverfile already exists, skipping"
fi

# ── 7. Update .gitignore ──

GITIGNORE="${PROJECT_ROOT}/.gitignore"

add_to_gitignore() {
  local entry="$1"
  if [ -f "${GITIGNORE}" ] && grep -qF "${entry}" "${GITIGNORE}"; then
    return
  fi
  echo "${entry}" >> "${GITIGNORE}"
}

add_to_gitignore ""
add_to_gitignore "# App Store Fastlane"
add_to_gitignore ".appstore-fastlane.env"
add_to_gitignore "fastlane/report.xml"
add_to_gitignore "fastlane/Preview.html"
add_to_gitignore "fastlane/test_output"

echo "✅ Updated .gitignore"

# ── Done ──

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Fastlane setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .appstore-fastlane.env with your app details"
echo "  2. Generate an App Store Connect API key:"
echo "     https://appstoreconnect.apple.com/access/integrations/api"
echo "  3. Save the .p8 file to ~/.config/teamzlab/"
echo ""
echo "Available commands (run from project root):"
echo "  cd fastlane && fastlane ios create_app      # Create app on App Store Connect"
echo "  cd fastlane && fastlane ios upload_metadata  # Upload metadata"
echo "  cd fastlane && fastlane ios upload_screenshots # Upload screenshots"
echo "  cd fastlane && fastlane ios upload_testflight  # Upload to TestFlight"
echo "  cd fastlane && fastlane ios submit_review    # Submit for review"
echo "  cd fastlane && fastlane ios full_release     # Metadata + screenshots + submit"
echo "  cd fastlane && fastlane ios app_info         # Print app info"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
