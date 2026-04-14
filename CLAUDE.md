# Teamz Company Automation — AI Agent Instructions

This directory contains **48 Python scripts** for SEO, ASO, keyword research, competitor analysis, monitoring, and QA. Before writing custom code or inventing data, **check if a script already exists here**.

## Critical Rule

**Never fabricate keyword scores, search volumes, or metrics.** Run the existing scripts to get real data. If a script fails, fix it — don't work around it with made-up numbers.

## Before ANY ASO/Store Listing Task

**Use the orchestrator — one command does everything:**

```bash
# Full flow: keywords → volume → competitors → listing → release notes → build → upload → guide manual steps
python3 py/aso/aso-store-release.py

# Check what's done / what's pending
python3 py/aso/aso-store-release.py --status

# Run a specific step only
python3 py/aso/aso-store-release.py --step volume
```

The orchestrator tracks progress in `store-release-progress.json`. It calls all scripts in order, catches fabricated data via preflight, and prints exact instructions for manual steps (screenshots, content rating, data safety). Any team member can run it.

## Key Scripts (called by orchestrator, or run individually)

| Task | Script |
|------|--------|
| **Full store release** | `py/aso/aso-store-release.py` |
| **Keyword volume** (Bing + Trends + autocomplete) | `py/build-keyword-volume.py "kw1" "kw2"` |
| **Full ASO pipeline** (discover + score + CSV) | `py/aso/aso-keyword-pipeline.py` |
| **Pre/post-flight validation** | `py/aso/aso-preflight.py --pre` / `--post` |
| **Upload AAB** | `py/build-play-console.py upload --aab file.aab --track internal --commit` |
| **Push listing** | `py/build-play-console.py listing-push --file listing.json --commit` |
| **Copy-paste helper + release notes paste** | `py/aso/aso-copy-helper.py` (HTML + `.txt` with `<locale>` tags for Play Console) |
| **Keyword autocomplete** | `py/aso/aso-keywords.py --suggest "term"` |
| **Competitor analysis** | `py/aso/aso-competitors.py --find "term"` |
| **Metadata audit** | `py/aso/aso-metadata.py --audit APP_ID` |
| **AdMob accounts/apps/units/reports** | `py/admob.py {auth\|accounts\|apps\|ad-units\|report}` |

## iOS App Store (Fastlane)

```bash
# First-time setup (creates fastlane/ dir, symlinks Fastfile, copies env template)
bash appstore-fastlane/setup-appstore-fastlane.sh

# Then from project root:
cd fastlane && fastlane ios create_app        # Create app on App Store Connect
cd fastlane && fastlane ios upload_metadata   # Upload 39-locale metadata
cd fastlane && fastlane ios upload_screenshots # Upload screenshots
cd fastlane && fastlane ios submit_review     # Submit for review
cd fastlane && fastlane ios app_info          # Check app info
```

Config: `appstore-fastlane/appstore-fastlane.env.example` → copy to project root as `.appstore-fastlane.env`.
Full guide: `packages/team_mvp_kit/prompts/ios-release-guide.md`.

## AdMob (REST API, cross-project)

```bash
# One-time OAuth (saves refresh token to ~/.config/teamzlab/admob-token.json)
python3 py/admob.py auth

# Then from any project:
python3 py/admob.py accounts                         # List publisher accounts
python3 py/admob.py apps                             # List apps
python3 py/admob.py ad-units --app APP_ID            # List ad units for an app
python3 py/admob.py find-unit --app APP_ID --format NATIVE
python3 py/admob.py report --days 7                  # Network report (last 7 days)
python3 py/admob.py report --app APP_ID --days 30
```

Stdlib-only (no pip deps). Reuses `~/.config/teamzlab/oauth-client-config.json`.
Token refresh is automatic.

## Pre-Release Verification

```bash
# Run from project root — checks Flutter, Firebase, iOS, Android, Fastlane, metadata
bash packages/team_mvp_kit/teamz-company-automation/sh/pre-release-verify.sh

# Options:
#   --fix            Auto-fix formatting issues
#   --skip-flutter   Skip Flutter analyze/format
#   --skip-firebase  Skip Firebase checks
```

Auto-detects monetization model (ads-only, IAP, both, free) and adjusts checks accordingly.

## Full Registry

See `automation-tool-registry.md` (this directory) for the complete mapping of every task to every script (48 scripts, 7 categories).

## Output Locations

- **Pipeline CSVs** (`master_keywords.csv`, `ios_keywords.csv`) go in the **project's** `automation_data/` directory (set via `TEAMZ_DATA_DIR` in `.teamz-automation.env`), NOT in this submodule's `data/` directory.
- **Transient script output** (`aso-keywords-latest.json`, etc.) goes in this submodule's `data/` directory.

## Teamz Lab Company Info (shared across ALL projects)

- **Company name:** Teamz Lab LTD
- **Copyright:** © 2026 Teamz Lab LTD
- **Contact email:** teamz.lab.contact@gmail.com
- **Review phone:** +447490356046
- **Privacy policy:** https://teamzlab.com/privacy-policy
- **Apple Developer Team ID:** NDV83KC5LC
- **App Store Connect API Key ID:** 559DD92MBH
- **App Store Connect Issuer ID:** 100d6ef8-7452-4aff-85a4-990158b60b3d
- **P8 key location:** `~/.config/teamzlab/AuthKey_559DD92MBH.p8`

## Config

Scripts read `.teamz-automation.env` from the host project. Key vars for ASO:
- `TEAMZ_ASO_KEYWORDS` — comma-separated seed keywords
- `TEAMZ_APP_IDS` — Apple numeric app ID
- `TEAMZ_PLAY_PACKAGE_NAME` — Android package name
- `TEAMZ_DATA_DIR` — where to write project-level output
