# Teamz Company Automation — AI Agent Instructions

This directory contains **58 Python scripts + 1 Ruby script** for SEO, ASO, keyword research, competitor analysis, monitoring, and QA. Before writing custom code or inventing data, **check if a script already exists here**.

## Critical Rules

**Rule 1 — Never fabricate keyword scores, search volumes, or metrics.** Run the existing scripts to get real data. If a script fails, fix it — don't work around it with made-up numbers.

**Rule 2 — Never claim features the app doesn't have.** Apple Guideline 2.3.1 (Accurate Metadata) and Google Play deceptive-behavior policy reject metadata that misrepresents the app. Before writing ANY name / subtitle / description / promo text / keywords, verify each claim against the actual app code & config. **Mandatory 60-second audit:**

1. **Ad claims** ("no ads", "ad-free") — check `.appstore-fastlane.env` `SERVES_ADS=`, AdMob/AppLovin SDK in pubspec.yaml, AndroidManifest meta-data tags, `lib/common/ads/`. If ads ship, NEVER claim "no ads".
2. **Subscription/IAP claims** ("no subscription", "no IAP") — grep for `in_app_purchase`, `purchases_flutter`, `RevenueCat`, Info.plist `SKAdNetworkItems`. If IAP ships, NEVER claim "no subscription".
3. **Offline claims** ("works offline", "no internet needed") — verify critical features don't require network (grep for `http`, `dio`, API base URLs, WebView dependency).
4. **Privacy claims** ("no tracking", "private", "no data collection") — check ATT prompt, Firebase Analytics, Crashlytics, AdMob personalized-ads flag, PrivacyInfo.xcprivacy.
5. **No-signup claims** ("no account needed") — verify auth flows are truly optional (grep for required-login screens).
6. **Quantified claims** ("2000+ tools", "50+ calculators") — verify against actual tool registry / count. Don't round up.

**Rule 3 — Translate metadata IN-CHAT, never just copy English to non-English locales.** When `aso-localize.py` runs without `--translate`, it falls back to copying en-US to all 40 other locales (better than empty 0-byte files but not real localization). For final-quality output, write a per-project `automation_data/localize_metadata.py` script that contains hand-translated entries for every locale (German `nettolohn`, Japanese `手取り`, Spanish `sueldo neto`, etc. — Claude IS the translator, no external Translation API needed). The user can fine-tune later but must NEVER ship 40 locales of English fallback as the final state — that wastes the localization slots and looks unprofessional in non-English markets. The translation script writes name/subtitle/keywords/promotional_text/description directly to `fastlane/metadata/{locale}/*.txt` respecting char limits (name ≤30, subtitle ≤30, keywords ≤100, promo ≤170, desc ≤4000). Latin-script European → translate keywords to local terms; non-Latin (ja/ko/zh/ar/he/hi/th) → mix English (universally understood for fintech) + local. See `toss_app/automation_data/localize_metadata.py` for the canonical pattern.

**Rule 4 — Always populate `automation_data/deep-research-keywords.json` with `_app_constraints`** before writing metadata. Schema:
```json
{
  "_app_constraints": {
    "monetization": "ad-supported / freemium / paid / subscription",
    "forbidden_claims": ["no ads", ...],
    "allowed_claims": ["free", "no paywall", "offline", ...],
    "rejection_risk": "Apple 2.3.1 / Google deceptive-behavior if forbidden_claims appear in metadata"
  }
}
```
The orchestrator's `aso-store-release.py` listing step MUST refuse to write metadata containing any string from `forbidden_claims`.

**Rule 5 — Mirror Apple metadata to Android Play listing files in the same step.** Apple Fastlane metadata lives at `fastlane/metadata/{locale}/*.txt`. Android Play Console expects `android/app/src/main/play/listings/{locale}/{title,short-description,full-description}.txt`. The mappings:
- `name.txt` (≤30 Apple) → `title.txt` (≤30 Play, identical)
- `subtitle.txt` (≤30 Apple) + `promotional_text.txt` (≤170 Apple) → combined into `short-description.txt` (≤80 Play)
- `description.txt` (≤4000 Apple) → `full-description.txt` (≤4000 Play, identical)
- `keywords.txt` — Apple-only field (Play has no keyword slot; Play indexes the description text instead)

ASO research from `aso-keywords.py` already pulls Google Play autocomplete data, so no separate Android keyword research is needed — the same merged scored CSV (`aso-seo-master.csv`) covers both stores.

Why this matters: a misleading-metadata rejection blocks the release for 24-72h plus a manual appeal cycle, AND post-launch enforcement removes the app entirely. Worse: 1-star reviews citing "lied about ads" tank conversion permanently. This is non-recoverable damage.

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
| **ASO + SEO master merge** (combined_score CSV) | `py/aso/aso-seo-merge.py` |
| **Localize iOS Fastlane metadata (all 40 locales)** | `py/aso/aso-localize.py` |
| **Auto release notes from git** | `py/aso/aso-release-notes-gen.py` |
| **App icon audit** (contrast / size / alpha / fill) | `py/aso/aso-icon-audit.py` |
| **A/B experiment tracker** (icon, screenshots, subtitle) | `py/aso/aso-experiments.py add\|snapshot\|list\|report` |
| **Download velocity** (Play + ASC, no new auth) | `py/aso/aso-velocity.py [--history]` |
| **AI image edit** (Nano Banana, no MCP) | `py/aso/aso-gemini-edit.py --prompt "..." --image src.jpg --output out.jpg` |
| **Play Console batch push** (listings + graphics, 39 locales) | `python3 py/aso/aso-play-batch-push.py [--commit]` |
| **ASC screenshot direct push** (bypasses fastlane silent-fail) | `bundle exec ruby py/aso/asc-screenshots-push.rb` |
| **Localize metadata template** (per-project translation scaffold) | `cp py/aso/aso-localize-metadata-template.py <project>/automation_data/localize_metadata.py` |
| **Pre/post-flight validation** | `py/aso/aso-preflight.py --pre` / `--post` |
| **Upload AAB** | `py/build-play-console.py upload --aab file.aab --track internal --commit` |
| **Push listing** | `py/build-play-console.py listing-push --file listing.json --commit` |
| **Copy-paste helper + release notes paste** | `py/aso/aso-copy-helper.py` (HTML + `.txt` with `<locale>` tags for Play Console) |
| **Keyword autocomplete** | `py/aso/aso-keywords.py --suggest "term"` |
| **Competitor analysis** | `py/aso/aso-competitors.py --find "term"` |
| **Metadata audit** | `py/aso/aso-metadata.py --audit APP_ID` |

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
