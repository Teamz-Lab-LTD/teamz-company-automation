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

## ASO Playbook — Mistakes Claude Has Made (Don't Repeat)

This section captures every pitfall learned during real shipping. Any new Teamz project using this kit inherits these rules automatically — don't re-learn them by repeating the mistakes.

### Phase 1 — Understanding the app (before touching metadata)

**Rule P1.1 — Audit native-vs-WebView BEFORE making architecture claims.** Don't call an app a "WebView wrapper" without counting Scaffold widgets, bottom-nav tabs, and `InAppWebView` usages. Apple 4.2 risk assessment depends on the actual ratio of native screens to WebView screens.

```bash
# Minimum audit before any claim:
grep -rn "class.*extends.*StatefulWidget\|class.*extends.*StatelessWidget" lib/ | grep -iE "screen|widget" | wc -l
grep -rn "InAppWebView\|WebView\|WebViewController" lib/
cat lib/screens/main_navigation_screen.dart  # or similar — enumerate tabs
```

A 12-tab app with 11 native calculators + 1 WebView tab is NOT at 4.2 risk. Don't cause panic without evidence.

**Rule P1.2 — Verify monetization claims from code, not assumption.**

```bash
# Ad SDK check:
grep -rn "google_mobile_ads\|AdMob\|AppLovin" pubspec.yaml lib/ ios/ android/
grep "SERVES_ADS\|USES_IDFA" .appstore-fastlane.env
# IAP check:
grep -rn "in_app_purchase\|purchases_flutter\|RevenueCat" pubspec.yaml lib/
# Analytics/tracking:
grep -rn "firebase_analytics\|firebase_crashlytics\|onesignal_flutter" pubspec.yaml
```

Before writing ANY metadata, populate `automation_data/deep-research-keywords.json` `_app_constraints` block:

```json
{
  "_app_constraints": {
    "monetization": "ad-supported / freemium / paid / subscription",
    "forbidden_claims": ["no ads", "ad-free", ...],  // if AdMob ships
    "allowed_claims": ["free", "no paywall", "offline", ...]
  }
}
```

### Phase 2 — Writing metadata text

**Rule P2.1 — Translate IN-CHAT for all 39 Fastlane locales, don't use English fallback.** `aso-localize.py` without `--translate` copies en-US to all locales. That's a fallback, NOT ship-quality. Write a per-project `automation_data/localize_metadata.py` using the kit template (`py/aso/aso-localize-metadata-template.py`) with hand-translated tuples. Reference impl: `toss_app/automation_data/localize_metadata.py` (30 locales × 5 fields = 195 files, runs in 1 sec).

**Rule P2.2 — Mirror Apple metadata to Play Console in the same step.** Apple uses `fastlane/metadata/{locale}/{name,subtitle,keywords,description,promotional_text,release_notes}.txt`. Play Console expects `android/app/src/main/play/listings/{locale}/{title,short-description,full-description}.txt`.

Mapping:
- Apple `name.txt` (≤30) → Play `title.txt` (≤30, identical)
- Apple `subtitle.txt` (≤30) + `promotional_text.txt` (≤170) → combined → Play `short-description.txt` (≤80)
- Apple `description.txt` (≤4000) → Play `full-description.txt` (≤4000, can be identical)
- Apple `keywords.txt` (≤100) → Play has no keyword slot; Play indexes description for ranking
- Apple `release_notes.txt` → Play `release-notes.txt` (when each new release ships)

**Rule P2.3 — Strip Play-forbidden promotional words from Play title + short-description (NOT Apple).** Play rejects "Free/Gratis/Kostenlos/Best/#1/Top Rated/etc." with a "may not be promoted" warning. Apple is lenient. Apply locale-aware regex ONLY to Play files, leave Apple alone. See `feedback_play_no_promo_words_in_metadata` pattern.

**Rule P2.4 — Never claim features the app doesn't have.** Apple 2.3.1 rejects. Before writing: audit monetization (Rule P1.2). If AdMob ships, NEVER write "No Ads" or equivalents in any of the 41 locales.

### Phase 3 — App icon

**Rule P3.1 — Use kit template, single concept, ask the user for BG color.** Template at `packages/team_mvp_kit/prompts/icon-prompt-template.md`. When user says "make icon prompt":
1. Read the template FIRST (don't invent structure)
2. ASK user for BG color (neon-on-dark `#12151A` / neon BG `#D9FE06` / light `#F4F5F5`) — don't default
3. Inspect the existing `ios/Runner/Assets.xcassets/AppIcon.appiconset/Icon-App-1024x1024@1x.png` to match existing pattern unless user requests a pivot
4. Write to `prompts/{app_snake}_icon_prompt.md`
5. Single ICON CONCEPT (not A/B/C variants)

**Rule P3.2 — Use TeamzLab design system colors from `design_system.dart`.** `#D9FE06` (neon green), `#12151A` (dark), `#1D1F25` (dark II), `#FFFFFF`, `#F4F5F5`, `#DDDDDD`. NEVER `#CDFF1A` chartreuse — that's wrong.

**Rule P3.3 — After generating, audit + regenerate all platform sizes.** Run `py/aso/aso-icon-audit.py` then `dart run flutter_launcher_icons`. Delete stale files (e.g. `Icon-App-60x60@1x.png` at wrong dimensions — deprecated iOS 7+ slot). Sync Android `ic_launcher.png` across all mipmap densities so third-party SDKs referencing default names get the new icon.

### Phase 4 — Screenshots

**Rule P4.1 — Screenshot text contrast follows WCAG: pair BG with FG.** compose.py defaults `--text-color=white`. On bright BGs (`#D9FE06` neon, `#CDFF1A` chartreuse, pastels, any BG with luminance >0.35) pass `--text-color=black`. Also explicitly tell Nano Banana in the enhancement prompt: "Keep the BLACK headline text — BLACK, not white."

**Rule P4.2 — Force iPhone 15 Pro device frame in Nano Banana prompts.** Default renders Android-looking phones. Apple may reject screenshots showing non-Apple devices. Add:

> "CRITICAL: Device MUST be a photorealistic Apple iPhone 15 Pro in Natural Titanium — Dynamic Island pill-shaped cutout at top center, Apple titanium side rails with rounded-square volume buttons left and single power button right, Apple's exact corner radius. No Samsung, no Pixel, no generic Android. No logos on chassis."

**Rule P4.3 — Forbid emoji/chart icons/sparkles + gradients/glows explicitly.** Nano Banana loves adding 📈🎯✨ and radial gradients. Always:

> "ABSOLUTELY NO emoji, NO colored icons, NO chart icons, NO sparkles. Keep background solid [color] — no gradients, glows, radial patterns, or light effects."

**Rule P4.4 — Populate ALL 5 Apple device-size folders.** Apple ASC silently shows OLD version screenshots in any empty slot. Must fill:
- `fastlane/screenshots/{locale}/APP_IPHONE_55/` (1242×2208)
- `fastlane/screenshots/{locale}/APP_IPHONE_65/` (1242×2688)
- `fastlane/screenshots/{locale}/APP_IPHONE_67/` (1290×2796)
- `fastlane/screenshots/{locale}/APP_IPAD_PRO_129/` (2048×2732)
- `fastlane/screenshots/{locale}/APP_IPAD_PRO_3GEN_129/` (2048×2732)

Use `py/aso/pad_resize.py` or the skill's padding script to derive the 3 missing sizes from the 6.7" + 12.9" canonical sets (zero API cost).

**Rule P4.5 — Derive Android screenshots from iOS, not regenerate.** Play accepts iPhone-framed screenshots (suboptimal but fine). Pad iOS outputs to 1080×1920 (phone) + 1200×1920 (tablet) via `pad_resize.py` — zero API cost vs $2-3 for native Pixel regen. Deploy to `android/app/src/main/play/listings/en-US/graphics/{phone,tablet-10-inch}-screenshots/`.

### Phase 5 — Pushing to stores

**Rule P5.1 — fastlane deliver silently fails to attach screenshots. Verify via ASC API, fall back to direct Spaceship.** After `fastlane upload_screenshots` or `upload_all` says "Successfully uploaded", QUERY the API:

```ruby
# Ruby: check screenshots actually attached
loc = version.get_app_store_version_localizations.find { |l| l.locale == "en-US" }
sets = loc.get_app_screenshot_sets
# If sets.size == 0 despite fastlane success — use py/aso/asc-screenshots-push.rb
```

If 0 sets attached, STOP retrying fastlane (it fails the same way). Use `py/aso/asc-screenshots-push.rb` (direct Spaceship, `wait_for_processing: true` per image).

**Rule P5.2 — Push screenshots to ALL 39 Apple locales, not just en-US.** Apple does NOT auto-inherit across locales within the same version. Empty locale slot → falls back to PREVIOUS version's screenshots (stale). The kit script `asc-screenshots-push.rb` accepts `LOCALES=ALL` (default) or comma-list. Expect ~30-45 min for 39 locales × 30 screenshots with `wait_for_processing: true`. For Play, push to en-US only — Play auto-inherits to other locales.

**Rule P5.3 — Apple Deliverfile `phone_number` must be E.164.** Never empty. Teamz default: `+447490356046`. Kit's `setup-appstore-fastlane.sh` pre-fills this. Empty string causes fastlane deliver to fail AFTER uploading metadata — wasted time.

**Rule P5.4 — Apple needs a new binary to update the App Store icon; Play accepts direct icon push.** iOS 1024×1024 marketing icon is embedded in the IPA via AppIcon.appiconset. Must `flutter build ipa --release` + `fastlane upload_testflight` for the new icon to appear. Play has a separate 512×512 icon slot pushable via `androidpublisher` API.

**Rule P5.5 — Release notes per locale use ASC `whatsNew` field (camelCase), not `whats_new`.** The `whats_new` key doesn't exist in the v1 API. Use `Spaceship::ConnectAPI.patch_app_store_version_localization(attributes: { whatsNew: text })`. The `aso-release-notes-gen.py` script generates the JSON — push it via the direct patch pattern in `toss_app/fastlane` as reference.

**Rule P5.6 — For Play Console release notes, use the kit's paste-file pattern.** Don't hand-write bulk paste files. `aso-copy-helper.py` writes BOTH paste files automatically when the orchestrator's `copy_helper` step runs:
- `{data_dir}/release-notes-v{ver}-paste.txt` — Apple ASC format
- `{data_dir}/play-release-notes-v{ver}-paste.txt` — Play Console format

Both have `<locale>...</locale>` blocks per Google/Apple's paste conventions. User opens the file, Cmd+A, Cmd+C, pastes into the respective console's bulk-locale release-notes input.

Files also exist per-locale for fastlane/supply auto-discovery:
- Apple: `fastlane/metadata/{locale}/release_notes.txt`
- Play: `android/app/src/main/play/release-notes/{play-locale}/default.txt`

Play's Managed Publishing enforces photo/video permissions declaration review before accepting new AAB commits via API. If your app declares `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO`, expect a blocker on first release after policy activation (late 2024): submit declaration → wait for Google review (hours-days) → retry AAB commit. Manual upload via Play Console UI may succeed even when API rejects.

**Rule P5.7 — Keep in-app list ordering in lock-step with store positioning via `aso-priority-export.py`.** When the store listing says "Paycheck & Freelance Calculator", the first tools a user sees after install MUST be paycheck/freelance/mortgage/tax/BMI — not alphabetical A-for-Age. Otherwise install→open→confused→uninstall tanks retention and makes the listing feel misleading (soft 2.3.1 risk).

The kit ships `py/aso/aso-priority-export.py` which reads the project's `deep-research-keywords.json` `_recommended_clusters` (primary/secondary/tertiary) and the top-N rows of `aso-seo-master.csv`, then writes `tools_priority.json`:

```json
{
  "version": 1,
  "keywords": [{"term": "paycheck calculator", "weight": 100}, ...],
  "hub_boosts": {"freelance": 60, "money": 50, ...}
}
```

Wired into the orchestrator as step `priority_export` (runs automatically after `seo_merge`). The script also mirrors the file into the host app's `assets/data/tools_priority.json` if the folder exists, so the bundled fallback ships fresh on each release build.

**Host app integration (one-time per project):**
1. Add `assets/data/` to `pubspec.yaml` `assets:` list
2. Create a priority loader mirroring `toss_app/lib/common/tool_priority.dart` — fetches remote JSON (GitHub raw from project repo), falls back to bundled asset, exposes `score(tool)` + `sortByPriority(list)`
3. Call `ToolPriority.load()` alongside registry load; sort list/hub-grid by `score desc, title asc`

Zero manual work per ASO pivot: user edits clusters → `aso-store-release.py` runs → script regenerates JSON (remote + bundled) → next app launch reflects new order.

**Rule P6.1 — Realign category + tags on every positioning pivot.** Category is a top-3 ranking signal. A "Paycheck Calculator" app in "Utilities / Developer Tools" category gets ~zero discovery benefit from keyword work.

Data-driven selection process:
1. Read `deep-research-keywords.json` competitor table → which category houses the scale leaders for your positioning cluster?
2. For money-calc apps: **Apple Primary=Finance, Secondary=Productivity**; **Play Category=Finance**
3. Avoid saturated categories: Utilities (browsers/VPNs dominate), generic Productivity (off-chart) — proven graveyards per real App Store research.

**Rule P6.2 — Play tags cannot be set via API. Guide the user through Play Console UI.** `androidpublisher` v3 exposes listings + graphics + AAB but NOT category or tags. Apple primary/secondary category also UI-only.

For each project, maintain `android/app/src/main/play/STORE_CONFIG.md` as a versioned reference of:
- Play category + 5 tags (per release)
- Apple primary + secondary category (per release)
- Age rating answers + justification
- Data source links to `deep-research-keywords.json` / `aso-seo-master.csv`

Reference implementation: `toss_app/android/app/src/main/play/STORE_CONFIG.md`.

**Rule P6.3 — Pick Play tags by data-driven cluster rank, not intuition.** For each tag in the Finance category, match against:
- Bing exact-match volume from `keyword-volume-latest.json`
- ChatGPT difficulty + gap from `deep-research-keywords.json`
- Peer group reality (Mobile Payment tag pulls Venmo/PayPal peers — wrong for calculator apps)

Prefer tags that match your app's actual tools. For money-calc + freelance apps: `Loan, Personal finance, Calculator, Investment, Business` proved optimal (1 Tools tag + 3 Finance + 1 Business).

### Phase 7 — App Privacy (Apple) — often-forgotten blocker

**Rule P7.1 — Declare ALL data types matching SDKs in the binary, don't under-declare.** Apple scans the IPA for SDKs and rejects if App Privacy declaration doesn't match. Default data types for Teamz apps with AdMob + Firebase + OneSignal:

| Data type (ASC) | Why | Used for tracking? | Linked to user? |
|---|---|---|---|
| Identifiers → Device ID | AdMob uses IDFA | **YES** | No |
| Usage Data → Product Interaction | Firebase Analytics events | No | No |
| Usage Data → Advertising Data | AdMob logs impressions/clicks | **YES** | No |
| Diagnostics → Crash Data | Crashlytics | No | No |
| Diagnostics → Performance Data | Crashlytics performance | No | No |

Guide the user through ASC → App Privacy → Edit Data Types. This is UI-only, no API.

**Rule P7.2 — Age rating: Advertising=YES if AdMob ships. All other questions NO for calculator apps.** Final rating: 4+. Guide user through the 7-step questionnaire with explicit answer per question.

### Phase 8 — Post-publication monitoring

**Rule P8.1 — Run `aso-velocity.py --history` weekly.** Pulls Play Reporting API + ASC Sales & Trends. Appends to `aso-velocity-history.csv` for trend charts. No new auth needed — uses existing Play service account + ASC P8 key.

**Rule P8.2 — Register A/B experiments before launch via `aso-experiments.py add ...`.** Icon variants, subtitle variants, feature-graphic variants. Snapshot weekly via `snapshot` subcommand.

---

## Full Registry

See `automation-tool-registry.md` (this directory) for the complete mapping of every task to every script (19 ASO + 18 SEO + other categories).

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
- **App Store Connect Vendor #:** 93213066 (for sales/financial reports)
- **P8 key location:** `~/.config/teamzlab/AuthKey_559DD92MBH.p8`
- **Google Play reports Cloud Storage bucket:** `pubsite_prod_7194763656319643086`
  - Installs: `gs://pubsite_prod_7194763656319643086/stats/installs/`
  - Crashes: `gs://pubsite_prod_7194763656319643086/stats/crashes/`
  - Ratings: `gs://pubsite_prod_7194763656319643086/stats/ratings/`
  - Earnings: `gs://pubsite_prod_7194763656319643086/earnings/`
- **Play Console service account JSON:** `~/.config/teamzlab/play-console-service-account.json`
- **AdMob Publisher ID:** pub-7088022825081956
- **AdMob OAuth token:** `~/.config/teamzlab/admob-token.json`

## Config

Scripts read `.teamz-automation.env` from the host project. Key vars for ASO:
- `TEAMZ_ASO_KEYWORDS` — comma-separated seed keywords
- `TEAMZ_APP_IDS` — Apple numeric app ID
- `TEAMZ_PLAY_PACKAGE_NAME` — Android package name
- `TEAMZ_DATA_DIR` — where to write project-level output
