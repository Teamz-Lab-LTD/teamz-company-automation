# Automation Tool Registry

**MANDATORY: Read this file before running ANY automation task.** This registry maps every task to the exact scripts that must be used. Do NOT skip scripts, do NOT fabricate data, do NOT assume a tool doesn't exist.

> **Rule: If a script exists for a task, USE IT. If you need data, CHECK if a script already produces it before writing code or inventing numbers.**

---

## How to Use This Registry

1. **Before starting any ASO/SEO/automation task**, scan this file for matching scripts
2. **Run the scripts** and use their output — never fabricate scores, volumes, or metrics
3. **If a script fails**, fix it or report the error — don't work around it with made-up data
4. **If you're unsure**, list the contents of `packages/team_mvp_kit/teamz-company-automation/py/` first

---

## ASO Tasks (App Store Optimization)

| When you need... | Run this script | NOT this |
|---|---|---|
| **Keyword suggestions** (autocomplete) | `py/aso/aso-keywords.py --suggest "term"` | Don't guess keywords |
| **Keyword expansion** (2-level deep) | `py/aso/aso-keywords.py --expand "term"` | |
| **Trending keywords** in a category | `py/aso/aso-keywords.py --trending shopping` | |
| **Long-tail keywords** | `py/aso/aso-keywords.py --long-tail "term"` | |
| **Seasonal keywords** | `py/aso/aso-keywords.py --seasonal "term"` | |
| **Search volume estimates** | `py/build-keyword-volume.py "kw1" "kw2"` | Don't invent volume numbers |
| **Keyword scoring + ranked CSVs** | `py/aso/aso-keyword-pipeline.py` | Don't manually create CSVs |
| **Competitor apps** | `py/aso/aso-competitors.py --find "term"` | |
| **Competitor keywords** | `py/aso/aso-competitors.py --keywords APP_ID` | |
| **Competitor gaps** | `py/aso/aso-competitors.py --gaps MY_ID COMP_ID` | |
| **Competitive matrix** | `py/aso/aso-competitors.py --matrix "term"` | |
| **Metadata audit** (score 0-100) | `py/aso/aso-metadata.py --audit APP_ID` | |
| **Metadata optimization prompt** | `py/aso/aso-metadata.py --optimize APP_ID --keywords "..."` | |
| **Review analysis** | `py/aso/aso-reviews.py --fetch APP_ID` | |
| **Review keywords** | `py/aso/aso-reviews.py --keywords APP_ID` | |
| **Rank tracking** | `py/aso/aso-track.py --record APP_ID` | |
| **ASO guide/checklist** | `py/aso/aso-guide.py --checklist APP_ID` | |
| **Title/description prompts** | `py/aso/aso-guide.py --prompt "write title" --app APP_ID` | |
| **Play Console listing pull** | `py/build-play-console.py listing-pull --package com.x` | |
| **Play Console listing push** | `py/build-play-console.py listing-push --file listing.json` | |
| **Upload AAB to Play Console** | `py/build-play-console.py upload --aab file.aab --track internal --commit` | Auto-bumps versionCode if conflict |
| **Store settings (contact)** | `py/build-play-console.py store-settings --commit` | |
| **Full store release (27 steps)** | `py/aso/aso-store-release.py` | **START HERE — orchestrates everything, chained 100%** |
| **Copy-paste helper HTML** | `py/aso/aso-copy-helper.py` | For manual paste when API can't commit (draft apps) |
| **Release notes paste file** | `py/aso/aso-copy-helper.py` | Also generates `release-notes-*-paste.txt` with `<locale>` tags (≤500 chars/locale) |
| **Auto-generate release notes from git** | `py/aso/aso-release-notes-gen.py` | Reads git log since last tag → `release-notes-v{ver}.json`; `--translate` uses `claude` CLI for 35 locales |
| **Localize Fastlane iOS metadata (all 40 locales)** | `py/aso/aso-localize.py` | Populates empty `fastlane/metadata/*/keywords.txt\|subtitle.txt\|name.txt\|promotional_text.txt` via locale-aware iTunes autocomplete; `--translate` for LLM copy |
| **ASO+SEO master keyword merge** | `py/aso/aso-seo-merge.py` | Unifies ASO score + SEO volume + web rank + Deep Research → `aso-seo-master.csv` with `combined_score` (fulfills the "combine all sources" global rule) |
| **In-app tool ordering priority** | `py/aso/aso-priority-export.py` | Derives `tools_priority.json` from clusters + master CSV. Mirrors into `assets/data/tools_priority.json` when the host app has a Flutter assets folder, so the bundled fallback stays fresh on release builds. App fetches the remote copy at launch (GitHub raw) and boosts tools matching current ASO positioning to the top of list/favorites/hub views — keeps store listing language and in-app ordering in lock-step across ASO pivots. |
| **A/B experiment tracker** | `py/aso/aso-experiments.py add\|snapshot\|end\|list\|report` | Icon/screenshot/subtitle/title variants with CVR tracking; writes `aso-experiments.json` + `aso-experiments-report.md` |
| **App icon audit (contrast, size, alpha, fill)** | `py/aso/aso-icon-audit.py` | Stdlib PNG parser; catches iOS alpha rejection, low corner↔center contrast, undersized icons |
| **Download velocity + install trend (Play + ASC)** | `py/aso/aso-velocity.py` | Uses existing Play service account + ASC P8 key (no new setup); writes `aso-velocity-latest.json` + history CSV + markdown report |
| **AdMob eCPM benchmarks (app-idea generation gate)** | `py/aso/aso-admob-rpm-benchmarks.py [--query CATEGORY] [--country CC] [--top N] [--format rewarded\|interstitial\|banner\|native\|app-open] [--revenue-projection --category X --country US --daus 1000] [--validate]` | Mobile counterpart to `build-public-rpm-benchmarks.py`. 15 categories × 5 ad formats × 56 country multipliers. Auto-called by `aso-store-release.py` Phase 1 `monetization` step — populates `_monetization_context` block in `deep-research-keywords.json` with country-adjusted eCPM range + revenue projection. Use `--revenue-projection` standalone for "should I build this?" gate. |
| **Reddit AdMob/IAP/eCPM crowd intel** | `py/build-reddit-rpm-tracker.py --niche aso [--quick] [--report]` | Scans r/AdMob, r/iOSProgramming, r/androiddev, r/PlayConsole, r/ASO + 5 more for eCPM/ARPDAU/ARPPU dollar mentions. Writes `data/reddit-aso-rpm-crowd.json`. Auto-called by orchestrator's `monetization` step (--quick). Cross-validation against AdMob benchmarks via `aso-admob-rpm-benchmarks.py --validate`. |
| **Gemini Nano Banana image edit (no MCP)** | `py/aso/aso-gemini-edit.py --prompt "..." --image <src> --output <dst>` | REST wrapper for `nano-banana-pro-preview`. Reads API key from `~/.config/teamzlab/gemini-api-key.txt`. Used for screenshots, icons, feature graphics. Stdlib only. |
| **Play Console batch push (39 locales + graphics)** | `TEAMZ_PLAY_PACKAGE_NAME=com.x python3 py/aso/aso-play-batch-push.py [--commit]` | Single edit transaction pushes listings for all locales + screenshots + feature graphic + icon in one shot. Dry-run by default. |
| **ASC screenshots direct push (Ruby/Spaceship)** | `TARGET_VERSION=2.1.0 bundle exec ruby py/aso/asc-screenshots-push.rb` | Bypasses fastlane deliver's silent-failure race. Uploads to ALL 39 locales with `wait_for_processing: true`. Env: `LOCALES=ALL` or comma-list. |
| **Localize metadata template (per-project translation file)** | Copy `py/aso/aso-localize-metadata-template.py` to project's `automation_data/localize_metadata.py` and fill TRANSLATIONS dict | Use Claude as translator; template enforces Apple char limits; auto-writes 195 metadata files + supports parent-copy for en-AU/fr-CA/es-MX |

### ASO Workflow (must follow this order)

```
0.  py/aso/aso-preflight.py --pre                          → VALIDATE before starting (blocks if data missing)
0b. py/aso/aso-admob-rpm-benchmarks.py                     → Refresh eCPM benchmark JSON (15 categories × 56 countries)
0c. py/build-reddit-rpm-tracker.py --niche aso --quick     → Refresh Reddit crowd intel (AdMob/eCPM/ARPDAU mentions)
0d. (auto) write _monetization_context to deep-research-keywords.json so listing/translations reference real eCPM × country tier data
1.  py/aso/aso-keywords.py --suggest/--expand/--trending   → discover keywords
2.  py/build-keyword-volume.py "kw1" "kw2" ...             → get REAL volume data (Bing + Trends + autocomplete)
3.  py/aso/aso-competitors.py --find/--matrix              → competitive landscape
4.  py/aso/aso-keyword-pipeline.py                         → produce scored CSVs (integrates step 2 data)
5.  py/aso/aso-seo-merge.py                                → UNIFY ASO + SEO volume + web rank → aso-seo-master.csv (the ONE source of truth)
5b. py/aso/aso-priority-export.py                          → Export tools_priority.json so the host app's list order mirrors the current positioning (keywords + hub boosts)
6.  py/aso/aso-metadata.py --audit/--optimize              → audit current listing
7.  Google Trends (browser) — compare top 5 keywords       → confirm relative demand (script can't — 429 rate limited)
8.  py/aso/aso-localize.py                                 → fill all 40 Fastlane locales' keywords/subtitle/name from master
9.  py/aso/aso-release-notes-gen.py                        → auto-build release-notes-v{ver}.json from git log
10. py/aso/aso-icon-audit.py                               → QA icon PNGs (contrast, size, alpha, fill)
11. THEN write the listing using data from steps 1-10
12. py/aso/aso-preflight.py --post                         → VALIDATE after writing (blocks if listing has issues)
13. py/aso/aso-experiments.py add                          → register A/B variants before upload; `snapshot` weekly after release
```

**⚠️ NEVER skip step 0 or step 12 (preflight). The preflight script catches fabricated data, missing volume estimation, and listing issues.**
**⚠️ NEVER skip step 2 (volume estimation). Without it, you cannot determine which keywords have actual search demand.**
**⚠️ NEVER skip step 5 (seo-merge). The global CLAUDE.md rule mandates combining ASO + SEO + Deep Research before writing content.**
**⚠️ Step 7 (Google Trends) requires browser — the API is 429 rate-limited. Ask the user to do this manually.**
**⚠️ The orchestrator `py/aso/aso-store-release.py` runs steps 0–13 automatically in order — prefer it over running scripts individually.**
**⚠️ Step 0b/0c/0d (monetization research) auto-fires as orchestrator step `monetization` immediately after preflight. Listing-generation step depends on `_monetization_context` being populated — never skip.**

---

## SEO Tasks

| When you need... | Run this script |
|---|---|
| **Full keyword audit** | `py/seo-keyword-engine.py audit` |
| **Keyword suggestions** | `py/seo-keyword-engine.py suggest` |
| **Keyword trends** | `py/seo-keyword-engine.py trends` |
| **ASO keyword scoring** | `py/seo-keyword-engine.py aso-suggest "term"` |
| **Keyword intelligence** | `py/build-keyword-intel.py` |
| **Keyword volume** (Google Trends + Bing + GSC) | `py/build-keyword-volume.py "term"` |
| **Competitor gap analysis** | `py/build-competitor-gaps.py` |
| **Rank tracking** | `py/build-rank-tracker.py record` |
| **Content ideas** | `py/build-content-ideas.py` |
| **Backlink discovery** | `py/build-backlinks-overview.py` |
| **SERP feature tracking** | `py/build-serp-tracker.py` |
| **SEO audit fixes** | `py/build-seo-audit-fixes.py --dry-run` |
| **Crawl snapshot** | `py/build-crawl-diff.py` |
| **Schema validation (static)** | `py/build-schema-validate.py` |
| **URL indexation + rich-results status via GSC API** (REQUIRED after any schema/canonical/sitemap change — replaces manual Rich Results Test clicks) | `py/inspect-urls.py` |
| **Cloudflare cache purge after deploy** | `py/cloudflare-purge.py` |
| **Search Console anomalies** | `py/build-gsc-anomalies.py` |
| **Topic cluster report** | `py/build-topic-cluster-report.py` |
| **Request indexing** | `py/build-request-indexing.py` |

### Review snippet eligibility (MUST know before adding `review` to JSON-LD)
Google only renders star rich-results when the `Review` / `AggregateRating` parent node is one of these types:
`Book, Course, Event, HowTo, LocalBusiness, MediaObject, Movie, Organization, Product, Recipe, SoftwareApplication`.
Attaching reviews to `Service`, `CreativeWork`, `Article`, etc. validates as JSON but fails at the Rich Results layer with "Invalid object type for field `<parent_node>`". Default choice for Teamz agency pages: put the reviews on the `Organization` node and cross-link the `Service` via `provider.@id`.

---

## Monitoring Tasks

| When you need... | Run this script |
|---|---|
| **Brand mentions** (Reddit/Dev.to) | `py/build-reddit-scanner.py` |
| **SERP feature detection** | `py/build-serp-tracker.py` |
| **GSC anomaly alerts** | `py/build-gsc-anomalies.py` |
| **Uptime check** | `py/build-uptime-check.py` |

---

## Auth Setup (run once per machine)

| Service | Script |
|---|---|
| Google Search Console | `py/build-search-console-auth.py` |
| Google Analytics GA4 | `py/build-analytics-auth.py` |
| Google Ads Keyword Planner | `py/build-keyword-planner-auth.py` |
| Google AdSense | `py/build-adsense-auth.py` |

---

## App Store (iOS) — Fastlane

| When you need... | Run this |
|---|---|
| **Initial setup** (run once per project) | `bash appstore-fastlane/setup-appstore-fastlane.sh` |
| **Create app on App Store Connect** | `cd fastlane && fastlane ios create_app` |
| **Upload metadata** (all locales) | `cd fastlane && fastlane ios upload_metadata` |
| **Upload screenshots** | `cd fastlane && fastlane ios upload_screenshots` |
| **Upload metadata + screenshots** | `cd fastlane && fastlane ios upload_all` |
| **Upload build to TestFlight** | `IPA_PATH=... cd fastlane && fastlane ios upload_testflight` |
| **Distribute TestFlight to testers** | `cd fastlane && fastlane ios distribute_testflight` |
| **Submit for App Store review** | `cd fastlane && fastlane ios submit_review` |
| **Full release** (metadata + screenshots + submit) | `cd fastlane && fastlane ios full_release` |
| **Download existing metadata** | `cd fastlane && fastlane ios download_metadata` |
| **Get app info** | `cd fastlane && fastlane ios app_info` |

### Config
- API key setup: `appstore-fastlane/appstore-fastlane.env.example`
- Project config: `.appstore-fastlane.env` (gitignored)
- Metadata files: `fastlane/metadata/<locale>/*.txt`
- Shared Fastfile: `appstore-fastlane/Fastfile` (symlinked into each project)

---

## Pre-Release Verification (Shell)

| When you need... | Run this |
|---|---|
| **Full pre-release check** (Flutter + Firebase + iOS + Android + Fastlane) | `bash sh/pre-release-verify.sh` |
| **Skip Flutter analyze** (faster) | `bash sh/pre-release-verify.sh --skip-flutter` |
| **Skip Firebase checks** | `bash sh/pre-release-verify.sh --skip-firebase` |
| **Auto-fix formatting** | `bash sh/pre-release-verify.sh --fix` |

Auto-detects monetization model (ads-only / IAP / both / free) and adjusts checks. Validates:
- Flutter code quality (format, analyze, secrets, print() calls)
- Firebase (functions deployed, secrets, App Check, SHA fingerprints, APIs)
- Android (key.properties, keystore, gitignore)
- iOS (AdMob ID, ATT vs nonPersonalizedAds, PrivacyInfo.xcprivacy, dev team, test ad gating)
- Fastlane (installed, configured, API key, metadata completeness, screenshot count)
- Manual checklist (pricing, App Privacy, age rating, MRDP, license, content rights)

---

## Anti-Patterns (NEVER do these)

| ❌ DON'T | ✅ DO |
|---|---|
| Invent keyword scores or search volumes | Run `build-keyword-volume.py` for real data |
| Manually create `master_keywords.csv` | Run `aso-keyword-pipeline.py` to generate it |
| Guess which keywords have demand | Run `build-keyword-volume.py` — it checks Google Trends, Bing API, autocomplete rank, and GSC |
| Skip competitor analysis | Run `aso-competitors.py --find` + `--matrix` + `--keywords` |
| Write store listings without data | Follow the ASO Workflow (6 steps above) |
| Write release notes >500 chars/locale | Play Console limit is 500, not 4000. Always validate with `aso-preflight.py --post` |
| Output release notes as markdown/code blocks | Output as JSON (`release-notes-v*.json`), then run `aso-copy-helper.py` to generate paste `.txt` with `<locale>` tags |
| Assume a tool doesn't exist | `ls packages/team_mvp_kit/teamz-company-automation/py/` first |
| Suggest Google Trends manually | `build-keyword-volume.py` already integrates Google Trends |
| Suggest paid tools when free ones exist | Check this registry — 48 scripts cover most needs |
| Claim "No Ads" / "Ad-Free" when AdMob ships | Check `.appstore-fastlane.env` `SERVES_ADS=` and `pubspec.yaml` for ad SDKs FIRST. Apple 2.3.1 rejects misleading claims. |
| Claim "No Subscription" / "No IAP" without grep | Grep for `in_app_purchase`, `purchases_flutter`, `RevenueCat` before claiming. |
| Claim "Offline" without verifying network deps | Critical-path features must work without network. WebView-wrapper apps almost never qualify. |
| Round up tool/feature counts in metadata | "2000+ tools" must mean ≥2000. Auditor counts must back the claim. |
| Write metadata before populating `_app_constraints` in deep-research-keywords.json | The constraints block lists `forbidden_claims` per-app. Listing step must refuse strings from that list. |

---

## Script Count by Category

- **ASO**: 19 scripts (keyword research → competitor analysis → metadata → reviews → rank tracking → SEO merge → localization → release notes → icon audit → A/B experiments → download velocity → Gemini image edit → Play batch push → ASC Spaceship screenshot push → localize template)
- **SEO**: 18 scripts (audit → keywords → volume → competitors → SERP → content → indexing)
- **Auth**: 4 scripts (GSC, GA4, Google Ads, AdSense)
- **Content**: 5 scripts (ideas, multilang, OG images, subtitles, programmatic SEO)
- **Monitoring**: 5 scripts (brand mentions, SERP features, GSC anomalies, uptime)
- **QA**: 5 scripts (runtime test, schema layout, server, test suite, batch fix)
- **Config**: 1 script
- **App Store (iOS)**: Fastlane setup (Fastfile + setup script + env template)
- **Pre-Release**: 1 shell script (`sh/pre-release-verify.sh`) — adaptive checks for all monetization models

**Total: 58 Python scripts + 1 Ruby script + Fastlane iOS automation + pre-release verification. Python scripts are all standard library except `build-play-console.py`, `aso-velocity.py`, and `aso-play-batch-push.py` which need `pip3 install google-api-python-client google-auth`. Ruby script `asc-screenshots-push.rb` uses Spaceship from the Fastlane gem (already installed via Fastlane). Gemini-based scripts (`aso-gemini-edit.py`, `aso-appstore-screenshots` skill) need a Gemini API key at `~/.config/teamzlab/gemini-api-key.txt`.**
