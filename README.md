# Teamz Company Automation

**The company toolbox.** One git submodule that gives every Teamz Lab project (website or app) the same battle-tested automation: SEO research and monitoring, ASO (App Store Optimization), store publishing (Play / App Store / IAP / achievements), QA gates, revenue stats, and multi-platform content distribution.

> **You are an intern or an AI agent (Cursor / Claude) seeing this repo for the first time?**
> This README is the **complete index — every script in this repo is listed below** with a one-line purpose and a copy-paste command. Read sections 1-4, then jump into the index.

---

## 1. Which document answers what

| You want to know… | Read this |
|---|---|
| "What scripts exist and what does each one do?" | **This README** (full index, section 5) |
| "Which script do I use for task X?" | [`automation-tool-registry.md`](automation-tool-registry.md) — task → tool mapping + anti-patterns |
| "I am an AI agent. What are the rules?" | [`CLAUDE.md`](CLAUDE.md) — agent rulebook: never fabricate metrics, orchestrator-first ASO, API recipes, past mistakes |
| "How do I set up ASO for a NEW app?" | [`HOW-TO-ASO-NEW-APP.md`](HOW-TO-ASO-NEW-APP.md) — 2-minute checklist |
| "Which ASO/SEO script runs in which /aso-refresh mode?" | [`claude-config/aso-script-registry.md`](claude-config/aso-script-registry.md) |
| "What is shared per-machine vs per-app?" | [`claude-config/PER-APP-WORKFLOW.md`](claude-config/PER-APP-WORKFLOW.md) |
| "How do I deploy a static site to our VPS?" | [`HOSTINGER-VPS-DEPLOY.md`](HOSTINGER-VPS-DEPLOY.md) |
| "What is the revenue strategy?" | [`MONEY_MACHINE_2026_2027.md`](MONEY_MACHINE_2026_2027.md) |
| "How do I pull lifetime app revenue/stats?" | [`app-stats/README.md`](app-stats/README.md) + [`app-stats/QUICKSTART.md`](app-stats/QUICKSTART.md) |

---

## 2. Five-minute setup (once per project)

**Working with ONLY this repo (no host project)?** That works too: clone it directly, `cp .teamz-automation.env.example .teamz-automation.env`, fill it in, and run scripts as `python3 py/<name>.py` / `bash sh/<name>.sh` from the repo root. The `scripts/` form below applies when the repo is a submodule inside a host project.

```bash
# 1. Add the submodule to your project (skip if already there)
git submodule add https://github.com/Teamz-Lab-LTD/teamz-company-automation.git teamz-company-automation
git submodule update --init --recursive

# 2. Create the project config (tells scripts which site/app this is)
cp teamz-company-automation/.teamz-automation.env.example .teamz-automation.env
#    → edit: TEAMZ_SITE_URL, TEAMZ_PROJECT_TYPE (website|app), package name…

# 3. First time on this MACHINE only: shared machine-level defaults
mkdir -p ~/.config/teamzlab
cp teamz-company-automation/automation.base.env.example ~/.config/teamzlab/automation.base.env

# 4. Wire everything up (creates scripts/ symlinks + Claude config + skills)
bash teamz-company-automation/setup-symlinks.sh

# 5. First time on this MACHINE only: Google OAuth tokens
python3 scripts/build-search-console-auth.py   # Search Console
python3 scripts/build-analytics-auth.py        # GA4
python3 scripts/build-adsense-auth.py          # AdSense (optional)
```

After step 4, **every script in this repo is callable from your project root as `scripts/<name>`** — that is the form used in all tables below.

### How config resolves (later overrides earlier)

```
~/.config/teamzlab/automation.base.env          ← machine-level (Apple team ID, ASC key, AdMob publisher)
<your-project>/.teamz-automation.env            ← PROJECT-level (site URL, package name, data dir)
teamz-company-automation/.teamz-automation.env  ← submodule fallback (rarely used)
```

`TEAMZ_PROJECT_TYPE=app` makes website-only scripts exit code `2` ("not applicable", not an error).

---

## 3. The mental model (read before touching anything)

```
                  ┌──────────────────────────────────────────────────┐
                  │  ORCHESTRATORS — start here, they call the rest  │
                  │                                                  │
ASO work ───────▶ │  /aso-refresh <app-slug>    (Claude command)     │
                  │    └─▶ py/aso/aso-store-blitz.py   (full flow)   │
                  │    └─▶ py/aso/aso-master-precheck.sh (signal)    │
Website build ──▶ │  sh/build.sh                (index+sitemap+QA)   │
Nightly ────────▶ │  sh/nightly-build.sh        (3 AM launchd)       │
App stats ──────▶ │  app-stats/pull_all.sh      (all sources)        │
Content ────────▶ │  distribute/distribute.py   (11+ platforms)      │
                  └──────────────────────────────────────────────────┘
                                     │ call
                                     ▼
                  ~150 leaf scripts (py/, py/aso/, sh/) — each does ONE thing
                                     │ write
                                     ▼
                  data/  (JSON/CSV outputs, mostly gitignored, regenerable)
```

**Rule #1 (the most-broken rule in this repo's history):** do NOT hand-pick leaf scripts for ASO work. Always go through `/aso-refresh` — it runs the right scripts in the right order, including the SEO leading-indicator scripts everyone forgets. The hook `claude-config/hooks/aso-bash-guard.sh` enforces this.

---

## 4. Common tasks → exact command

| Task | Command |
|---|---|
| Any ASO work (title/keywords/screenshots/competitors) | `/aso-refresh <app-slug>` (Claude) — never run leaf ASO scripts directly |
| "Which keywords should this page/app target?" | `python3 scripts/build-keyword-intel.py --opportunities` |
| Estimate keyword volume (free) | `python3 scripts/build-keyword-volume.py "bmi calculator"` |
| Track keyword rankings daily | `python3 scripts/build-rank-tracker.py record` |
| Pull Search Console report | `bash scripts/build-search-console.sh --all` |
| Find pages Google ignores | `python3 scripts/build-dead-revival.py` |
| Full website build after editing pages | `bash scripts/build.sh` |
| QA all tool pages | `bash scripts/qa-test.sh --fix` |
| Check Core Web Vitals | `bash scripts/build-pagespeed.sh --top20` |
| Ask Google/Bing to index new pages | `python3 scripts/build-request-indexing.py` |
| AdMob revenue report | `python3 scripts/admob.py report --days 7` |
| Lifetime app stats (all sources) | `./app-stats/pull_all.sh lifetime` |
| Publish next queued article | `python3 scripts/distribute/distribute.py next` |
| Build release AAB for any Flutter app | `bash scripts/build-playstore-aab.sh` |
| Pre-release gate (Flutter+Firebase) | `bash scripts/pre-release-verify.sh --fix` |
| iOS metadata/screenshots to App Store | `appstore-fastlane/` lanes — see [`CLAUDE.md`](CLAUDE.md) § Fastlane |
| Set up IAP on both stores | `bash scripts/iap-smoke-test.sh --sku <sku>` first, then `py/iap.py` |
| Back up every secret/token on this machine | `bash scripts/secrets-export.sh` |
| New machine: restore secrets | `bash scripts/secrets-import.sh teamzlab-secrets.gpg` |

---

## 5. FULL INDEX — every file in this repo

> **Working inside ONE folder only?** Every code directory has its own local `README.md` with the same index scoped to that folder: [`py/`](py/README.md) · [`py/aso/`](py/aso/README.md) · [`py/web_automation/`](py/web_automation/README.md) · [`py/product-hunt/`](py/product-hunt/README.md) · [`sh/`](sh/README.md) · [`claude-config/`](claude-config/README.md) · [`skills/`](skills/README.md) · [`distribute/`](distribute/README.md) · [`app-stats/`](app-stats/README.md) · [`appstore-fastlane/`](appstore-fastlane/README.md) · [`aso-research/`](aso-research/README.md) · [`data/`](data/README.md)


### 5.1 `py/` — Python toolbox (SEO, GSC, QA, stores, revenue)

The py/ folder is the script toolbox of teamz-company-automation: ~67 standalone Python scripts that do SEO research, App Store/Play Store (ASO) checks, store automation (IAP, achievements, Play Console), site QA, and revenue tracking for every Teamz Lab website and app. Most scripts are free-API or stdlib-only, read shared config from _teamz_config.py and ~/.config/teamzlab tokens, and write JSON/CSV results into the host project's data/ folder. After running setup-symlinks.sh in a host project, every script is callable as scripts/<name>.py.

| File | What it does | Typical command |
|---|---|---|
| [`py/_teamz_config.py`](py/_teamz_config.py) | Shared library: loads .teamz-automation.env files and resolves site, data, and token paths for all scripts. | — |
| [`py/admob.py`](py/admob.py) | Reads AdMob accounts, apps, ad units, and earnings reports via REST API; OAuth stored once. | `python3 scripts/admob.py report --days 7` |
| [`py/aso-claims-lint.py`](py/aso-claims-lint.py) | Blocks store submission if listing text or screenshots contain forbidden claims like "offline" or "no ads". | `python3 scripts/aso-claims-lint.py` |
| [`py/aso-name-collision.py`](py/aso-name-collision.py) | Checks whether a proposed app name already exists or clashes on App Store and Google Play. | `python3 scripts/aso-name-collision.py "Arrow Jam 3D"` |
| [`py/batch-fix-display-bug.py`](py/batch-fix-display-bug.py) | Bulk-fixes the JS bug where style.display='' leaves elements hidden by a CSS class. | `python3 scripts/batch-fix-display-bug.py --dry-run` |
| [`py/build-adsense-auth.py`](py/build-adsense-auth.py) | One-time browser OAuth for the AdSense API; saves token under ~/.config/teamzlab. | `python3 scripts/build-adsense-auth.py` |
| [`py/build-analytics-auth.py`](py/build-analytics-auth.py) | One-time browser OAuth for the Google Analytics (GA4) Data API token. | `python3 scripts/build-analytics-auth.py` |
| [`py/build-backlinks-overview.py`](py/build-backlinks-overview.py) | Finds who links to your site using free sources, mainly Search Console links data. | `python3 scripts/build-backlinks-overview.py scan` |
| [`py/build-backlinks.py`](py/build-backlinks.py) | Tracks and helps submit the site to 40+ free directories; pings indexing services. | `python3 scripts/build-backlinks.py submit` |
| [`py/build-bing-data.py`](py/build-bing-data.py) | Pulls Bing Webmaster top queries, top pages, and crawl stats into dated JSON snapshots. | `python3 scripts/build-bing-data.py` |
| [`py/build-brand-mentions-log.py`](py/build-brand-mentions-log.py) | Manually log brand mentions (Reddit, Medium, forums) to a CSV for outreach follow-up. | `python3 scripts/build-brand-mentions-log.py --report` |
| [`py/build-competitor-gaps.py`](py/build-competitor-gaps.py) | Crosses your top GSC queries with Google Autocomplete to find keywords you don't rank for. | `python3 scripts/build-competitor-gaps.py` |
| [`py/build-content-ideas.py`](py/build-content-ideas.py) | Generates content and tool ideas from Autocomplete, Trends, Search Console, Reddit, and seasonal calendars. | `python3 scripts/build-content-ideas.py --trending` |
| [`py/build-crawl-diff.py`](py/build-crawl-diff.py) | Snapshots each page's canonical, robots meta, schema count, and H1; diffs against the previous run. | `python3 scripts/build-crawl-diff.py` |
| [`py/build-dead-revival.py`](py/build-dead-revival.py) | Re-targets indexed pages with zero search demand toward related keywords that do have demand. | `python3 scripts/build-dead-revival.py` |
| [`py/build-enhance-queue.py`](py/build-enhance-queue.py) | Merges outputs of the other SEO scripts into one prioritized queue of tools to improve. | `python3 scripts/build-enhance-queue.py` |
| [`py/build-fix-orphans.py`](py/build-fix-orphans.py) | Adds orphan tool pages into siblings' related-tools lists so every page gets internal links. | `python3 scripts/build-fix-orphans.py` |
| [`py/build-gsc-anomalies.py`](py/build-gsc-anomalies.py) | Compares two Search Console time windows and flags CTR drops plus impression spikes or drops. | `python3 scripts/build-gsc-anomalies.py` |
| [`py/build-gsc-broken-pages.py`](py/build-gsc-broken-pages.py) | Finds 404 pages Google still sends traffic to and appends 301 redirect rules to .htaccess. | `python3 scripts/build-gsc-broken-pages.py --dry-run` |
| [`py/build-hub-subtitles.py`](py/build-hub-subtitles.py) | Fills missing subtitles on hub-page tool cards using each tool's meta description. | `python3 scripts/build-hub-subtitles.py --fix` |
| [`py/build-keyword-batches.py`](py/build-keyword-batches.py) | Turns a project's page inventory into upload-ready CSVs for manual Keyword Planner volume pulls. | `python3 scripts/build-keyword-batches.py` |
| [`py/build-keyword-intel.py`](py/build-keyword-intel.py) | Free Ubersuggest replacement: GSC keyword report with intent, difficulty, opportunities, and gaps. | `python3 scripts/build-keyword-intel.py --opportunities` |
| [`py/build-keyword-planner-auth.py`](py/build-keyword-planner-auth.py) | One-time browser OAuth for the Google Ads Keyword Planner API token. | `python3 scripts/build-keyword-planner-auth.py` |
| [`py/build-keyword-volume.py`](py/build-keyword-volume.py) | Estimates relative keyword search volume (0-100) from Trends, Autocomplete, and GSC — no paid API. | `python3 scripts/build-keyword-volume.py "bmi calculator"` |
| [`py/build-money-tracker.py`](py/build-money-tracker.py) | Tracks whether high-RPM money pages are growing, flat, stuck, or dead using 28-day GSC data. | `python3 scripts/build-money-tracker.py` |
| [`py/build-multilang.py`](py/build-multilang.py) | Shows which high-RPM tools have, or still need, Spanish/Portuguese and other language versions. | `python3 scripts/build-multilang.py status` |
| [`py/build-og-images.py`](py/build-og-images.py) | Generates branded 1200x630 social-share (OG) images per hub category using Pillow. | `python3 scripts/build-og-images.py` |
| [`py/build-play-console.py`](py/build-play-console.py) | Pulls Play Console reports and pulls/pushes store listing text via a service account. | `python3 scripts/build-play-console.py report` |
| [`py/build-programmatic-seo.py`](py/build-programmatic-seo.py) | Generates location-specific tool page variants, e.g. one income-tax page per US state. | `python3 scripts/build-programmatic-seo.py --list` |
| [`py/build-public-rpm-benchmarks.py`](py/build-public-rpm-benchmarks.py) | Writes a local database of public ad RPM benchmarks per niche and country; hand-curated quarterly. | `python3 scripts/build-public-rpm-benchmarks.py --top 10` |
| [`py/build-rank-tracker.py`](py/build-rank-tracker.py) | Records daily keyword positions from Search Console; shows ranking trends, movers, and a watchlist. | `python3 scripts/build-rank-tracker.py record` |
| [`py/build-reddit-rpm-tracker.py`](py/build-reddit-rpm-tracker.py) | Scrapes Reddit for real publisher RPM/eCPM mentions to sanity-check the static benchmarks. | `python3 scripts/build-reddit-rpm-tracker.py --quick` |
| [`py/build-reddit-scanner.py`](py/build-reddit-scanner.py) | Auto-scans Reddit and Dev.to for brand mentions and appends new ones to a CSV. | `python3 scripts/build-reddit-scanner.py` |
| [`py/build-request-indexing.py`](py/build-request-indexing.py) | Asks Google (URL Inspection), Bing/DuckDuckGo (IndexNow), and sitemap pings to index your pages. | `python3 scripts/build-request-indexing.py` |
| [`py/build-revenue-velocity-score.py`](py/build-revenue-velocity-score.py) | Scores candidate tool ideas by estimated dollars per month at month 3; ranks them. | `python3 scripts/build-revenue-velocity-score.py --demo` |
| [`py/build-schema-validate.py`](py/build-schema-validate.py) | Validates every page's JSON-LD schema blocks locally for required fields per type. | `python3 scripts/build-schema-validate.py` |
| [`py/build-search-console-auth.py`](py/build-search-console-auth.py) | One-time browser OAuth for the Google Search Console API token. | `python3 scripts/build-search-console-auth.py` |
| [`py/build-seo-audit-fixes.py`](py/build-seo-audit-fixes.py) | Fixes crawl-audit issues: too-short titles, URL/title keyword mismatch, and thin pages. | `python3 scripts/build-seo-audit-fixes.py --dry-run` |
| [`py/build-seo-experiments.py`](py/build-seo-experiments.py) | Compares Search Console numbers before vs after a dated page change, per experiment. | `python3 scripts/build-seo-experiments.py` |
| [`py/build-seo-fix-all.py`](py/build-seo-fix-all.py) | Bulk-fixes mechanical SEO issues across all pages: meta descriptions, display bug, freshness line. | `python3 scripts/build-seo-fix-all.py --dry-run` |
| [`py/build-serp-features-log.py`](py/build-serp-features-log.py) | Manually log SERP features you observe (snippet, PAA, AI overview) per keyword into CSV. | `python3 scripts/build-serp-features-log.py --report` |
| [`py/build-serp-tracker.py`](py/build-serp-tracker.py) | Auto-detects SERP features for watchlist keywords by fetching and parsing Google results. | `python3 scripts/build-serp-tracker.py` |
| [`py/build-static-schema.py`](py/build-static-schema.py) | Extracts schema data from each page's inline JS and injects static JSON-LD into the head. | `python3 scripts/build-static-schema.py` |
| [`py/build-topic-cluster-report.py`](py/build-topic-cluster-report.py) | Counts pages per top-level hub folder for content-cluster planning; saves JSON. | `python3 scripts/build-topic-cluster-report.py` |
| [`py/build-uptime-check.py`](py/build-uptime-check.py) | Checks site health on sample sitemap URLs plus SSL certificate expiry; can gate with exit 1. | `python3 scripts/build-uptime-check.py --alert` |
| [`py/build-youtube-keywords.py`](py/build-youtube-keywords.py) | YouTube-specific keyword research via YouTube autocomplete and search results; scores each seed keyword. | `python3 scripts/build-youtube-keywords.py "uber clone"` |
| [`py/cloudflare-purge.py`](py/cloudflare-purge.py) | Purges Cloudflare cache for a Teamz site or for specific URLs; shared token setup. | `python3 scripts/cloudflare-purge.py` |
| [`py/gamecenter.py`](py/gamecenter.py) | Syncs Apple Game Center achievements from one YAML file via the App Store Connect API. | `python3 scripts/gamecenter.py sync --dry-run` |
| [`py/generate-salary-cities.py`](py/generate-salary-cities.py) | Generates 30 city-specific salary comparison pages from the base salary tool. | `python3 scripts/generate-salary-cities.py` |
| [`py/gpgs.py`](py/gpgs.py) | Syncs Google Play Games achievements from the same YAML file via the Games Configuration API. | `python3 scripts/gpgs.py sync --dry-run` |
| [`py/gpgs_icon_push.py`](py/gpgs_icon_push.py) | Back-compat shim: uploads Play Games achievement icons via the web_automation Playwright recipe. | `python3 scripts/gpgs_icon_push.py --application-id <id>` |
| [`py/iap.py`](py/iap.py) | Creates one in-app purchase on Apple, Google, and RevenueCat in a single automated flow. | `python3 scripts/iap.py setup --sku com.teamz.<app>.<slug> --price-usd 2.99 --name "<Bundle Name>"` |
| [`py/iap_discovery.py`](py/iap_discovery.py) | Library that verifies an API endpoint exists in Google's discovery doc before iap.py calls it. | `python3 scripts/iap_discovery.py refresh` |
| [`py/iap_doctor.py`](py/iap_doctor.py) | Diagnoses a live app whose purchases fail or whose remove-ads entitlement never activates. | `python3 scripts/iap_doctor.py` |
| [`py/iap_preflight.py`](py/iap_preflight.py) | Pre-checks 14 conditions (keys, permissions, builds, SKU naming, text limits) before iap.py setup. | `python3 scripts/iap_preflight.py --sku com.teamz.<app>.<slug> --price-usd 2.99` |
| [`py/inspect-cwv.py`](py/inspect-cwv.py) | Batch Core Web Vitals and Lighthouse scores via PageSpeed Insights; fails CI on bad thresholds. | `python3 scripts/inspect-cwv.py --url <URL>` |
| [`py/inspect-urls.py`](py/inspect-urls.py) | Batch Google URL Inspection: indexing verdict, canonical, and rich-results status after schema/sitemap changes. | `python3 scripts/inspect-urls.py --url <URL>` |
| [`py/keyword_volume_manual.py`](py/keyword_volume_manual.py) | Library that reads manually exported Keyword Planner CSVs — the authoritative exact search-volume source. | — |
| [`py/qa-mobile-ux.py`](py/qa-mobile-ux.py) | Loads changed tools in an iPhone-sized headless browser; blocks on horizontal scroll and tiny touch targets. | `python3 scripts/qa-mobile-ux.py --changed` |
| [`py/qa-runtime-test.py`](py/qa-runtime-test.py) | Opens every tool page in headless Chromium and fails on JS errors or broken rendering. | `python3 scripts/qa-runtime-test.py --changed` |
| [`py/qa-schema-layout.py`](py/qa-schema-layout.py) | Checks pages for duplicate schema blocks and render calls missing their HTML containers. | `python3 scripts/qa-schema-layout.py` |
| [`py/qa-server.py`](py/qa-server.py) | Tiny multi-threaded local HTTP server used by the QA scripts (default port 9091). | `python3 scripts/qa-server.py 9091` |
| [`py/qa-test.py`](py/qa-test.py) | Fast static QA over all pages: doctype, lang, viewport, title, and similar structural checks. | `python3 scripts/qa-test.py` |
| [`py/revenue_priority.py`](py/revenue_priority.py) | Library that maps a page's hub/slug to an expected dollars-per-month number for prioritization. | — |
| [`py/seo-healthcheck.py`](py/seo-healthcheck.py) | Probes the whole SEO toolchain's data quality, catching scripts that run but silently return blanks. | `python3 scripts/seo-healthcheck.py` |
| [`py/seo-keyword-engine.py`](py/seo-keyword-engine.py) | All-in-one free SEO and ASO keyword tool: audit, suggest, trends, validate ideas, auto-fix placement. | `python3 scripts/seo-keyword-engine.py audit` |
| [`py/serp_difficulty.py`](py/serp_difficulty.py) | Library that scores keyword winnability 1-10 by checking which authority sites rank on page 1. | — |

### 5.2 `py/aso/` — App Store Optimization

py/aso/ is the App Store Optimization toolkit — a free, mostly stdlib alternative to paid tools like AppTweak. It covers the whole store lifecycle: keyword research, competitor spying, screenshot generation, metadata localization, pushing listings to Google Play and App Store Connect, and tracking ranks/installs afterward. The MAIN orchestrator is aso-store-blitz.py (one command runs the entire ship pipeline end to end); aso-master-precheck.sh is the data-gathering orchestrator run before writing any ASO copy, and aso-store-release.py orchestrates first-time Play Store setup — everything else is a leaf tool those three (or you) call directly.

| File | What it does | Typical command |
|---|---|---|
| [`py/aso/__init__.py`](py/aso/__init__.py) | Package marker; states the suite is a free AppTweak alternative built on _aso_common helpers. | — |
| [`py/aso/_aso_common.py`](py/aso/_aso_common.py) | Shared library: iTunes/Play API wrappers, autocomplete, review parser, tokenizer, rate limiter. Imported, never run. | — |
| [`py/aso/asc-screenshots-push.rb`](py/aso/asc-screenshots-push.rb) | Uploads screenshots straight to App Store Connect via Spaceship, avoiding fastlane deliver silent failures. | `TARGET_VERSION=2.1.0 LOCALES=ALL ruby scripts/asc-screenshots-push.rb` |
| [`py/aso/aso-admob-rpm-benchmarks.py`](py/aso/aso-admob-rpm-benchmarks.py) | Local database of mobile ad eCPM benchmarks by category, format, country; rough revenue projections. | `python3 scripts/aso-admob-rpm-benchmarks.py --top 10` |
| [`py/aso/aso-competitors.py`](py/aso/aso-competitors.py) | Competitor intelligence from iTunes Search: find rivals, analyze listings, extract keywords, spot gaps. | `python3 scripts/aso-competitors.py --find "fitness tracker"` |
| [`py/aso/aso-compose-screenshot.py`](py/aso/aso-compose-screenshot.py) | Composes one store screenshot: device frame plus hero/subtitle text on a colored background (Pillow only). | `python3 scripts/aso-compose-screenshot.py --raw shot.png --hero "TITLE" --output out.jpg` |
| [`py/aso/aso-copy-helper.py`](py/aso/aso-copy-helper.py) | Builds an HTML page with one-click copy buttons for pasting listing text into Play Console. | `python3 scripts/aso-copy-helper.py` |
| [`py/aso/aso-deep-research-prompt.py`](py/aso/aso-deep-research-prompt.py) | Generates a ready-made ChatGPT Deep Research prompt for an app's keywords and competitors. | `python3 scripts/aso-deep-research-prompt.py --app <slug> --keywords-file kws.txt` |
| [`py/aso/aso-experiments.py`](py/aso/aso-experiments.py) | Logs store-listing A/B tests, snapshots impressions/installs per variant, reports winners. | `python3 scripts/aso-experiments.py list` |
| [`py/aso/aso-firebase-events.py`](py/aso/aso-firebase-events.py) | Pulls Firebase Analytics events from BigQuery for funnel and user-behavior analysis. | `python3 scripts/aso-firebase-events.py --project <slug> --days 30` |
| [`py/aso/aso-gemini-edit.py`](py/aso/aso-gemini-edit.py) | Minimal Gemini (Nano Banana) REST wrapper that AI-edits a screenshot image from a prompt. | `python3 scripts/aso-gemini-edit.py --prompt "..." --image in.png --output out.jpg` |
| [`py/aso/aso-generate-batch.py`](py/aso/aso-generate-batch.py) | Batch-generates all store screenshots from a project presets JSON via the composer script. | `python3 scripts/aso-generate-batch.py --presets automation_data/aso_screenshot_presets.json` |
| [`py/aso/aso-guide.py`](py/aso/aso-guide.py) | Teaches ASO basics and produces app-specific checklists, content plans, and LLM prompts from iTunes data. | `python3 scripts/aso-guide.py --learn` |
| [`py/aso/aso-icon-audit.py`](py/aso/aso-icon-audit.py) | QA-checks app icon PNGs: size, brightness, contrast, transparency, frame fill — flags store-killing issues. | `python3 scripts/aso-icon-audit.py --strict` |
| [`py/aso/aso-keyword-pipeline.py`](py/aso/aso-keyword-pipeline.py) | Full keyword research pipeline: autocomplete discovery, competitor mining, scoring — outputs master/ios keyword CSVs. | `python3 scripts/aso-keyword-pipeline.py` |
| [`py/aso/aso-keywords.py`](py/aso/aso-keywords.py) | Keyword CLI: suggest, expand, trending, long-tail via Apple/Play autocomplete and iTunes signals. | `python3 scripts/aso-keywords.py --suggest "photo editor"` |
| [`py/aso/aso-localize-metadata-template.py`](py/aso/aso-localize-metadata-template.py) | Template to copy into a project as localize_metadata.py; fill hand-made translations, writes fastlane locale files. | — |
| [`py/aso/aso-localize.py`](py/aso/aso-localize.py) | Auto-fills fastlane iOS metadata (keywords, subtitle, name, promo) for all 40 locales. | `python3 scripts/aso-localize.py --translate` |
| [`py/aso/aso-master-precheck.sh`](py/aso/aso-master-precheck.sh) | Orchestrator: runs every data source (Play reports, keywords, competitors, Firebase) into one master JSON before writing copy. | `./scripts/aso-master-precheck.sh --package <pkg> --keywords-file kws.txt` |
| [`py/aso/aso-metadata.py`](py/aso/aso-metadata.py) | Audits, scores, compares, and optimizes iOS/Android listing metadata against character limits and keyword data. | `python3 scripts/aso-metadata.py --audit <app-id>` |
| [`py/aso/aso-openrouter-image-edit.py`](py/aso/aso-openrouter-image-edit.py) | OpenRouter image-to-image wrapper (cheap Gemini model, ~$0.04/edit) for screenshot polish. | `python3 scripts/aso-openrouter-image-edit.py --prompt "..." --image in.png --output out.png` |
| [`py/aso/aso-pad-resize.py`](py/aso/aso-pad-resize.py) | Pads a screenshot with background color then resizes to exact target device dimensions. | `python3 scripts/aso-pad-resize.py --src in.jpg --dst out.jpg --width 1080 --height 1920 --bg "#CDFF1A"` |
| [`py/aso/aso-play-batch-push.py`](py/aso/aso-play-batch-push.py) | Pushes all 39 Play Console listings plus graphics in one androidpublisher edit transaction. | `python3 scripts/aso-play-batch-push.py` |
| [`py/aso/aso-preflight.py`](py/aso/aso-preflight.py) | Validates ASO work is backed by real data — run before and after writing any listing content. | `python3 scripts/aso-preflight.py --full` |
| [`py/aso/aso-priority-export.py`](py/aso/aso-priority-export.py) | Exports tools_priority.json so the in-app tool ordering matches current ASO keyword positioning. | `python3 scripts/aso-priority-export.py` |
| [`py/aso/aso-release-notes-gen.py`](py/aso/aso-release-notes-gen.py) | Generates multi-locale release-notes JSON (36 locales, ≤500 chars each) from git log. | `python3 scripts/aso-release-notes-gen.py --version 1.4.0` |
| [`py/aso/aso-reviews.py`](py/aso/aso-reviews.py) | Fetches and analyzes App Store reviews: keywords, sentiment, complaints, praise, reply prompts, trends. | `python3 scripts/aso-reviews.py <app-id> --complaints` |
| [`py/aso/aso-seo-merge.py`](py/aso/aso-seo-merge.py) | Merges ASO scores, SEO volume, web rank, and Deep Research into one combined-score master keyword CSV. | `python3 scripts/aso-seo-merge.py --top 50` |
| [`py/aso/aso-store-blitz.py`](py/aso/aso-store-blitz.py) | MAIN orchestrator: one command runs screenshots, localization, Play push, and Apple submit with no prompts. | `python3 scripts/aso-store-blitz.py  (from app project root; --dry-run to validate only)` |
| [`py/aso/aso-store-release.py`](py/aso/aso-store-release.py) | Orchestrator for first-time Play Store setup: keywords, listing, build, upload steps with progress tracking. | `python3 scripts/aso-store-release.py --status` |
| [`py/aso/aso-tablet-from-phone.py`](py/aso/aso-tablet-from-phone.py) | Derives iPad/tablet screenshot presets from a phone preset JSON so tablet shots are never forgotten. | `python3 scripts/aso-tablet-from-phone.py --phone automation_data/aso_screenshot_presets_ios.json` |
| [`py/aso/aso-track.py`](py/aso/aso-track.py) | Records daily App Store search rank for watched keywords; reports movers over time. | `python3 scripts/aso-track.py --record <app-id>` |
| [`py/aso/aso-velocity.py`](py/aso/aso-velocity.py) | Tracks install/download velocity and country breakdown from Play Console and App Store Connect reports. | `python3 scripts/aso-velocity.py --days 7` |

### 5.3 `py/web_automation/` + `py/product-hunt/` — browser automation

py/web_automation/ is a small Playwright-style browser-automation framework for admin chores that have no API: you write a "Recipe" class (yields work items, processes each in a logged-in browser), log into the site once with --debug, and the cookies persist in a per-site Chromium profile so later runs need no re-login. Recipes are discovered and run via `python3 -m web_automation run <name>` from the py/ directory; each recipe reads its data (yaml lists of posts, comments, form steps) from the host project's automation_data/ folder. py/product-hunt/ holds one script that assembles a complete Product Hunt launch package (tagline, description, thumbnail, gallery images) from the app's existing landing-page and ASO data, refreshing stale keyword data first.

| File | What it does | Typical command |
|---|---|---|
| [`py/product-hunt/build-launch-content.py`](py/product-hunt/build-launch-content.py) | Builds a paste-ready Product Hunt launch kit (copy, thumbnail, gallery) from app's existing landing/ASO data. | `python3 teamz-company-automation/py/product-hunt/build-launch-content.py --app-slug <slug>` |
| [`py/web_automation/__init__.py`](py/web_automation/__init__.py) | Framework core: BrowserSession, Recipe base class, runner; persistent per-site Chromium profiles keep logins alive. | — |
| [`py/web_automation/__main__.py`](py/web_automation/__main__.py) | CLI that lists recipes and runs one by name, passing extra flags to the recipe's parser. | `cd teamz-company-automation/py && python3 -m web_automation list` |
| [`py/web_automation/recipes/__init__.py`](py/web_automation/recipes/__init__.py) | Recipes package doc: one module per site/task; data files live in host project's automation_data/. | — |
| [`py/web_automation/recipes/blogger_post.py`](py/web_automation/recipes/blogger_post.py) | Bulk-creates Blogger draft or published posts from a yaml file by driving the Blogger UI. | `python3 -m web_automation run blogger_post -- --yaml automation_data/blogger_posts.yaml` |
| [`py/web_automation/recipes/generic_form_fill.py`](py/web_automation/recipes/generic_form_fill.py) | Fills any web form from a yaml list of steps (goto, fill, click, upload, wait). | `python3 -m web_automation run generic_form_fill -- --yaml my_form.yaml --profile <profile>` |
| [`py/web_automation/recipes/play_console_icons.py`](py/web_automation/recipes/play_console_icons.py) | Uploads Play Games achievement icons to Play Console drafts via the web UI (no API exists). | `python3 -m web_automation run play_console_icons -- --dev-id <id> --app-id <id>` |
| [`py/web_automation/recipes/reddit_comment.py`](py/web_automation/recipes/reddit_comment.py) | Posts one comment per Reddit thread from a yaml list; user must vet targets against sub rules. | `python3 -m web_automation run reddit_comment -- --yaml automation_data/reddit_comments.yaml` |

### 5.4 `sh/` — shell scripts (builds, monitors, gates)

The sh/ folder holds the shell-script half of Teamz Lab's company automation toolkit. These scripts pull marketing data (Search Console, GA4, AdSense, PageSpeed, Clarity), rebuild and QA the tools website (sitemap, search index, link checks), and handle app-release chores (AAB builds, pre-release checks, ASO refresh runs, secrets backup). Host projects expose them via setup-symlinks.sh, so you usually run them as scripts/<name>.sh from the project root.

| File | What it does | Typical command |
|---|---|---|
| [`sh/aso-refresh-runner.sh`](sh/aso-refresh-runner.sh) | Chains all read-only ASO/SEO data scripts for one app and prints a markdown report. | `bash scripts/aso-refresh-runner.sh <app-slug> SIGNAL_ONLY` |
| [`sh/aso-refresh-selftest.sh`](sh/aso-refresh-selftest.sh) | Static check that the /aso-refresh skill wiring (registry, symlinks, hooks, logs) is intact. | `bash scripts/aso-refresh-selftest.sh <app-slug>` |
| [`sh/build-adsense.sh`](sh/build-adsense.sh) | Pulls live AdSense revenue, RPM, clicks, and impressions from the AdSense API. | `bash scripts/build-adsense.sh --all` |
| [`sh/build-analytics.sh`](sh/build-analytics.sh) | Pulls live GA4 traffic data: pages, sources, daily and 30-day overviews. | `bash scripts/build-analytics.sh --all` |
| [`sh/build-catchup.sh`](sh/build-catchup.sh) | Detects which daily/weekly/monthly SEO jobs are stale and runs only those. | `bash scripts/build-catchup.sh --status` |
| [`sh/build-clarity.sh`](sh/build-clarity.sh) | Pulls Microsoft Clarity bot, traffic, and UX engagement metrics (10 requests/day limit). | `bash scripts/build-clarity.sh 3` |
| [`sh/build-daily-seo-notify.sh`](sh/build-daily-seo-notify.sh) | Runs SEO tasks, sends a macOS notification, and writes a summary report for health checks. | `bash scripts/build-daily-seo-notify.sh --daily` |
| [`sh/build-daily-seo.sh`](sh/build-daily-seo.sh) | Runs the scheduled SEO routine: daily rank tracking, weekly deep scan, monthly full audit. | `bash scripts/build-daily-seo.sh --daily` |
| [`sh/build-internal-links.sh`](sh/build-internal-links.sh) | Checks every internal link across the tools website and finds orphan pages (website projects only). | `bash scripts/build-internal-links.sh --quick` |
| [`sh/build-pagespeed.sh`](sh/build-pagespeed.sh) | Checks Core Web Vitals and performance scores via Google PageSpeed Insights API. | `bash scripts/build-pagespeed.sh --top20` |
| [`sh/build-playstore-aab.sh`](sh/build-playstore-aab.sh) | Builds a release Android App Bundle for any Flutter project with a standard file name. | `bash scripts/build-playstore-aab.sh` |
| [`sh/build-qa-check.sh`](sh/build-qa-check.sh) | One QA pass over website pages: SEO structure, runtime safety, usability, design system. | `bash scripts/build-qa-check.sh --verbose` |
| [`sh/build-search-console.sh`](sh/build-search-console.sh) | Pulls Google Search Console queries, pages, status, and ranking opportunities. | `bash scripts/build-search-console.sh --all` |
| [`sh/build-search-index.sh`](sh/build-search-index.sh) | Rebuilds the website's search-index.js plus homepage counts and sitemap after any page change. | `bash scripts/build-search-index.sh` |
| [`sh/build-seo-audit.sh`](sh/build-seo-audit.sh) | Wrapper around the SEO+ASO keyword engine: audits, keyword suggestions, trends, app-name compares. | `bash scripts/build-seo-audit.sh --report` |
| [`sh/build-seo-dashboard.sh`](sh/build-seo-dashboard.sh) | Free Ubersuggest-style dashboard combining Search Console, GA4, and PageSpeed into one report. | `bash scripts/build-seo-dashboard.sh --quick` |
| [`sh/build-sitemap.sh`](sh/build-sitemap.sh) | Rebuilds sitemap.xml from all tool pages using git dates for lastmod. | `bash scripts/build-sitemap.sh` |
| [`sh/build-static-header.sh`](sh/build-static-header.sh) | Injects the shared pre-rendered header HTML into every page to stop layout shift (CLS). | `bash scripts/build-static-header.sh --check` |
| [`sh/build-validate-freshness.sh`](sh/build-validate-freshness.sh) | Finds stale content: old years in titles, wrong tool counts, outdated data. | `bash scripts/build-validate-freshness.sh` |
| [`sh/build.sh`](sh/build.sh) | Master website build: rebuilds index, sitemap, counts, then validates everything; run after any change. | `bash scripts/build.sh` |
| [`sh/claude-sessions.sh`](sh/claude-sessions.sh) | Lists running Claude processes and can kill sessions older than 24 hours. | `bash scripts/claude-sessions.sh --kill-old` |
| [`sh/continuous-build.sh`](sh/continuous-build.sh) | Runs timed unattended build sessions (Claude builds tools plus maintenance) while you are away. | `bash scripts/continuous-build.sh 3h` |
| [`sh/iap-smoke-test.sh`](sh/iap-smoke-test.sh) | Dry-runs the whole in-app-purchase setup pipeline (discovery, preflight, store verify) without writing anything. | `bash scripts/iap-smoke-test.sh --sku <sku>` |
| [`sh/install-claude-context.sh`](sh/install-claude-context.sh) | Wires kit knowledge into a host project: writes CLAUDE.md imports, skill symlinks, optional git hooks. | `bash scripts/install-claude-context.sh --install-hooks` |
| [`sh/lib/config.sh`](sh/lib/config.sh) | Shared config loader sourced by every script: resolves paths, env files, tokens, and defaults. | — |
| [`sh/newsletter-export.sh`](sh/newsletter-export.sh) | Exports newsletter subscribers from Firestore via the Firebase CLI, as list, CSV, or count. | `bash scripts/newsletter-export.sh --csv` |
| [`sh/nightly-build.sh`](sh/nightly-build.sh) | The 3 AM launchd agent: full nightly pipeline with all local scripts and tokens. | `bash scripts/nightly-build.sh --status` |
| [`sh/overflow-audit.sh`](sh/overflow-audit.sh) | Runs Flutter overflow tests to catch modal/sheet layout breaks on small phones before release. | `bash scripts/overflow-audit.sh` |
| [`sh/pre-release-verify.sh`](sh/pre-release-verify.sh) | Pre-release gate for Flutter+Firebase apps: config, functions, secrets, SHA keys, analyze, build readiness. | `bash scripts/pre-release-verify.sh --fix` |
| [`sh/qa-test.sh`](sh/qa-test.sh) | Automated QA suite that tests every website tool page for common issues, with optional auto-fix. | `bash scripts/qa-test.sh --fix` |
| [`sh/refresh-ecommerce-gsc-keywords.sh`](sh/refresh-ecommerce-gsc-keywords.sh) | Exports Search Console queries for the ecommerce landing page to a JSON data file. | `bash scripts/refresh-ecommerce-gsc-keywords.sh` |
| [`sh/run-build-now.sh`](sh/run-build-now.sh) | Triggers the full nightly build pipeline immediately using the Sonnet model. | `bash scripts/run-build-now.sh` |
| [`sh/secrets-export.sh`](sh/secrets-export.sh) | Packs every API key, token, and config into one encrypted GPG backup file. | `bash scripts/secrets-export.sh` |
| [`sh/secrets-import.sh`](sh/secrets-import.sh) | Restores all API keys and configs on a new machine from the encrypted backup. | `bash scripts/secrets-import.sh teamzlab-secrets.gpg` |

### 5.5 `claude-config/`, `skills/`, registry — AI-agent wiring

This scope covers the Claude Code config and Claude skills that travel with the teamz-company-automation submodule: the /aso-refresh slash command and its supporting registry/memory/hooks, the new-PC bootstrap, and two self-contained skills (teamz-design-bridge for brand-consistent UI, teamz-ux-research for evidence-based UX work). It also includes the symlink installer, the top-level tool registry doc, and Google Keyword Planner CSV templates. An intern should run setup-symlinks.sh once per app project, then invoke /aso-refresh for ASO work; the skills auto-activate on UI and research requests.

| File | What it does | Typical command |
|---|---|---|
| [`automation-tool-registry.md`](automation-tool-registry.md) | Doc mapping every automation task to the exact script that must be used. | — |
| [`claude-config/CLAUDE-md-additions.md`](claude-config/CLAUDE-md-additions.md) | Global-rule snippets to merge by hand into ~/.claude/CLAUDE.md on a new machine. | — |
| [`claude-config/PER-APP-WORKFLOW.md`](claude-config/PER-APP-WORKFLOW.md) | Explains what config is shared globally vs per-app, and the one-time per-app setup. | — |
| [`claude-config/README.md`](claude-config/README.md) | Index of claude-config folder plus the four-command new-PC bootstrap for Claude Code setup. | — |
| [`claude-config/aso-script-registry.md`](claude-config/aso-script-registry.md) | Source-of-truth mapping every ASO/SEO script to its /aso-refresh mode and when to call it. | — |
| [`claude-config/commands/aso-refresh.md`](claude-config/commands/aso-refresh.md) | Slash-command entry point routing all ASO work to canonical orchestrators with cadence gate. | `/aso-refresh <app-slug>` |
| [`claude-config/hooks/aso-bash-guard.sh`](claude-config/hooks/aso-bash-guard.sh) | PreToolUse Bash hook blocking ASO commands unless /aso-refresh ran in last 60 minutes. | — |
| [`claude-config/hooks/skill-invocation-audit.sh`](claude-config/hooks/skill-invocation-audit.sh) | PostToolUse Skill hook logging every skill invocation to a user-global audit log. | — |
| [`claude-config/memory/aso_cadence.md`](claude-config/memory/aso_cadence.md) | Locked ASO refresh cadence: 14-day signal pull, 28-day iOS / 56-day Android rewrite floor. | — |
| [`claude-config/memory/aso_screenshot_compliance.md`](claude-config/memory/aso_screenshot_compliance.md) | Rule banning any pricing text in App Store screenshots (Apple 2.3.7) before render. | — |
| [`reference/keyword-planner-templates/keywords-template.csv`](reference/keyword-planner-templates/keywords-template.csv) | Single-column starter CSV (header Keyword) for listing keywords to research. | — |
| [`reference/keyword-planner-templates/kp-plan-template.csv`](reference/keyword-planner-templates/kp-plan-template.csv) | Google Ads Keyword Planner upload template (UTF-16) with campaign/bid/keyword columns. | — |
| [`setup-symlinks.sh`](setup-symlinks.sh) | Wires submodule scripts, skills, and Claude config into host project and ~/.claude/. | `bash teamz-company-automation/setup-symlinks.sh` |
| [`skills/teamz-design-bridge/SKILL.md`](skills/teamz-design-bridge/SKILL.md) | Skill that rewrites generic UI suggestions into Teamz Lab brand-token-compliant code. | — |
| [`skills/teamz-design-bridge/platforms/flutter.md`](skills/teamz-design-bridge/platforms/flutter.md) | Maps abstract design tokens to team_mvp_kit Flutter widgets and context accessors. | — |
| [`skills/teamz-design-bridge/platforms/nextjs-tw.md`](skills/teamz-design-bridge/platforms/nextjs-tw.md) | Maps design tokens to Next.js plus Tailwind CSS custom properties and config. | — |
| [`skills/teamz-design-bridge/platforms/plain-css.md`](skills/teamz-design-bridge/platforms/plain-css.md) | Maps design tokens to vanilla HTML/CSS custom properties without Tailwind. | — |
| [`skills/teamz-design-bridge/platforms/wordpress.md`](skills/teamz-design-bridge/platforms/wordpress.md) | Maps design tokens to WordPress theme.json palette and typography slugs. | — |
| [`skills/teamz-design-bridge/rules/a11y.md`](skills/teamz-design-bridge/rules/a11y.md) | WCAG 2.1 AA rules for contrast, touch targets, and states every generated UI must meet. | — |
| [`skills/teamz-design-bridge/rules/banned.md`](skills/teamz-design-bridge/rules/banned.md) | Lists color/UI patterns that produce illegible or off-brand output and must never be emitted. | — |
| [`skills/teamz-design-bridge/rules/contrast.md`](skills/teamz-design-bridge/rules/contrast.md) | Core rule: always pair every background with its matching foreground on-token. | — |
| [`skills/teamz-design-bridge/tokens.json`](skills/teamz-design-bridge/tokens.json) | Stack-agnostic design tokens (colors, typography) with their roles and contrast pairings. | — |
| [`skills/teamz-ux-research/SKILL.md`](skills/teamz-ux-research/SKILL.md) | Skill conducting rigorous UX research: planning, discovery, testing, synthesis, recommendations. | — |
| [`skills/teamz-ux-research/methods/01-planning.md`](skills/teamz-ux-research/methods/01-planning.md) | How to write a research plan before any observation; cites the research-plan template. | — |
| [`skills/teamz-ux-research/methods/02-interviews.md`](skills/teamz-ux-research/methods/02-interviews.md) | Generative and JTBD interview method with a 30-minute session structure. | — |
| [`skills/teamz-ux-research/methods/03-usability-testing.md`](skills/teamz-ux-research/methods/03-usability-testing.md) | When and how to run usability tests watching real users attempt real tasks. | — |
| [`skills/teamz-ux-research/methods/04-thematic-analysis.md`](skills/teamz-ux-research/methods/04-thematic-analysis.md) | Braun and Clarke thematic analysis plus affinity mapping to turn observations into findings. | — |
| [`skills/teamz-ux-research/methods/05-severity-rubric.md`](skills/teamz-ux-research/methods/05-severity-rubric.md) | Nielsen 0-4 severity scale for scoring and prioritizing usability issues. | — |
| [`skills/teamz-ux-research/methods/06-personas.md`](skills/teamz-ux-research/methods/06-personas.md) | JTBD-flavored persona format anchoring design decisions to a real user job. | — |
| [`skills/teamz-ux-research/methods/07-journey-maps.md`](skills/teamz-ux-research/methods/07-journey-maps.md) | Journey map format walking a persona through a goal to surface experience breaks. | — |
| [`skills/teamz-ux-research/methods/08-competitive-audit.md`](skills/teamz-ux-research/methods/08-competitive-audit.md) | Structured competitor and Nielsen-heuristic audit to find patterns without user sessions. | — |
| [`skills/teamz-ux-research/methods/09-accessibility.md`](skills/teamz-ux-research/methods/09-accessibility.md) | Accessibility as a research method; minimum pre-launch audit per surface. | — |
| [`skills/teamz-ux-research/rules/no-fabrication.md`](skills/teamz-ux-research/rules/no-fabrication.md) | Never invent quotes, metrics, or findings; every claim cites evidence or is labeled hypothesis. | — |
| [`skills/teamz-ux-research/rules/reflexivity.md`](skills/teamz-ux-research/rules/reflexivity.md) | Every research plan must declare the researcher's biases before collecting data. | — |
| [`skills/teamz-ux-research/rules/triangulation.md`](skills/teamz-ux-research/rules/triangulation.md) | No recommendation ships unless the finding appears across two-plus independent sources. | — |
| [`skills/teamz-ux-research/templates/ab-test-plan.md`](skills/teamz-ux-research/templates/ab-test-plan.md) | Template for A/B test plans on any recommendation with severity two or higher. | — |
| [`skills/teamz-ux-research/templates/discussion-guide.md`](skills/teamz-ux-research/templates/discussion-guide.md) | Fill-in moderated session discussion guide with pre-session moderator checklist. | — |
| [`skills/teamz-ux-research/templates/persona-card.md`](skills/teamz-ux-research/templates/persona-card.md) | One-card-per-persona template storing JTBD and validation status. | — |
| [`skills/teamz-ux-research/templates/recommendation-matrix.md`](skills/teamz-ux-research/templates/recommendation-matrix.md) | Matrix template scoring each recommendation by severity, effort, and priority. | — |
| [`skills/teamz-ux-research/templates/research-plan.md`](skills/teamz-ux-research/templates/research-plan.md) | Fill-in research plan template covering objectives and research questions. | — |
| [`skills/teamz-ux-research/templates/tree-test.md`](skills/teamz-ux-research/templates/tree-test.md) | Tree-test plan template to validate navigation labels and hierarchy before build. | — |

### 5.6 `distribute/`, `app-stats/`, `aso-research/`, `appstore-fastlane/`, `data/`, top-level docs

This part of teamz-company-automation covers four jobs: publishing marketing content (distribute/ posts 181 articles, 2,058 pin images, and Remotion-rendered videos to blogs, Pinterest, YouTube, TikTok, Instagram), pulling app revenue and usage stats (app-stats/ merges App Store, Play, AdMob, GA4 into one report), shipping iOS releases (appstore-fastlane/ shared Fastlane config), and storing research and generated data (aso-research/ deep-research archives, data/ script outputs). The top-level docs are the rulebooks: CLAUDE.md is the master agent instruction file, and the env examples are the config templates every app project copies.

| File | What it does | Typical command |
|---|---|---|
| [`.gitignore`](.gitignore) | Keeps secrets (config.json) and regenerable data/ snapshots out of git so per-app runs stay clean. | — |
| [`.teamz-automation.env.example`](.teamz-automation.env.example) | Per-project config template: site URL, data dir, token paths, ASO/Play settings. Copy into each app. | — |
| [`CLAUDE.md`](CLAUDE.md) | 61KB agent rulebook: critical rules (never fabricate metrics, verify claims), ASO orchestrator-first workflow, key script index, Fastlane/AdMob/achievements/IAP REST recipes, web-automation framework, pre-release checks, past-mistakes playbook, company IDs, output locations. | — |
| [`HOSTINGER-VPS-DEPLOY.md`](HOSTINGER-VPS-DEPLOY.md) | Playbook for deploying any Teamz static site to the shared Hostinger VPS (Apache, Cloudflare DNS, certbot). | — |
| [`HOW-TO-ASO-NEW-APP.md`](HOW-TO-ASO-NEW-APP.md) | Canonical 2-minute steps to register a new app for ASO: .teamz-automation.env, symlink, seed keywords, /aso-refresh. | — |
| [`MONEY_MACHINE_2026_2027.md`](MONEY_MACHINE_2026_2027.md) | Revenue strategy doc: AdSense fix first, 90-day tool-building plan, RPM hub gaps, honest projections. | — |
| [`app-stats/.stats.env.example`](app-stats/.stats.env.example) | Per-app config template: vendor number, package name, Play bucket, AdMob and GA4 IDs. | — |
| [`app-stats/QUICKSTART.md`](app-stats/QUICKSTART.md) | Five-minute per-project setup: symlink, copy .stats.env, run the puller. | — |
| [`app-stats/README.md`](app-stats/README.md) | Full setup guide for the lifetime app-stats puller (credentials, permissions, env vars). | — |
| [`app-stats/lib/asc_jwt.rb`](app-stats/lib/asc_jwt.rb) | Shared ES256 JWT signer for App Store Connect API (20-minute tokens). | — |
| [`app-stats/lib/report_builder.py`](app-stats/lib/report_builder.py) | Merges all puller CSVs into the final markdown stats report. | — |
| [`app-stats/pull_all.sh`](app-stats/pull_all.sh) | Orchestrator: pulls App Store, Play, AdMob, GA4 stats and merges into one markdown report. | `./app-stats/pull_all.sh lifetime` |
| [`app-stats/pullers/admob_revenue.py`](app-stats/pullers/admob_revenue.py) | Pulls AdMob ad revenue, impressions, clicks; chunks lifetime requests into yearly windows. | — |
| [`app-stats/pullers/ga4_analytics.py`](app-stats/pullers/ga4_analytics.py) | Pulls GA4 daily engagement metrics; accepts service-account or OAuth token files. | — |
| [`app-stats/pullers/ios_sales.rb`](app-stats/pullers/ios_sales.rb) | Pulls monthly App Store Connect sales reports and aggregates to CSV. | — |
| [`app-stats/pullers/play_stats.sh`](app-stats/pullers/play_stats.sh) | Pulls Android install and earnings CSVs from the Play Console GCS bucket via gsutil. | — |
| [`app-stats/requirements.txt`](app-stats/requirements.txt) | Python deps for the pullers (google-auth, google-analytics-data, requests). | `pip3 install -r app-stats/requirements.txt` |
| [`appstore-fastlane/Fastfile`](appstore-fastlane/Fastfile) | Shared Fastlane lanes (auth, metadata, screenshots, submit) reused by every Teamz iOS app via symlink. | `fastlane <lane_name>` |
| [`appstore-fastlane/Gemfile`](appstore-fastlane/Gemfile) | Ruby deps: fastlane >= 2.220 and dotenv. | `bundle install` |
| [`appstore-fastlane/appstore-fastlane.env.example`](appstore-fastlane/appstore-fastlane.env.example) | Per-app env template: ASC API key (pre-filled for Teamz), bundle ID, app name, URLs. | — |
| [`appstore-fastlane/setup-appstore-fastlane.sh`](appstore-fastlane/setup-appstore-fastlane.sh) | One-time project setup: symlinks shared Fastfile, copies env template, creates 40-locale metadata dirs. | `bash appstore-fastlane/setup-appstore-fastlane.sh` |
| [`appstore-fastlane/sync_game_achievements.rb`](appstore-fastlane/sync_game_achievements.rb) | Creates/updates Game Center and Play Games achievements from a JSON spec; dry-run by default. | `ruby appstore-fastlane/sync_game_achievements.rb --spec=achievements.json --platform=both` |
| [`aso-research/2026-06-03/SYNTHESIS.md`](aso-research/2026-06-03/SYNTHESIS.md) | Merged Gemini + ChatGPT research: platform-split cadence (28d iOS / 56d Android), tiered competitors, free tools. | — |
| [`aso-research/2026-06-03/chatgpt-deep-research-methodology-critique.pdf`](aso-research/2026-06-03/chatgpt-deep-research-methodology-critique.pdf) | ChatGPT output: research-methodology critique, competitor tier framework, ROI scoring. | — |
| [`aso-research/2026-06-03/gemini-deep-research-cadence-and-tools.md`](aso-research/2026-06-03/gemini-deep-research-cadence-and-tools.md) | Gemini transcript: metadata refresh cadence data, free ASO tools, 2025-26 algorithm changes. | — |
| [`aso-research/README.md`](aso-research/README.md) | Rules for the ASO deep-research archive: read latest SYNTHESIS.md before any ASO strategy decision. | — |
| [`automation.base.env.example`](automation.base.env.example) | Machine-level shared defaults (Apple team, ASC key, AdMob publisher); copy to ~/.config/teamzlab/automation.base.env. | — |
| [`data/`](data/) | Generated outputs from the SEO/ASO scripts: rank history, GSC pulls, crawl snapshots, store listings, benchmarks. Mostly gitignored/regenerable. | — |
| [`data/aso-competitors-latest.json`](data/aso-competitors-latest.json) | Latest app-store competitor analysis output. | — |
| [`data/aso-metadata-history.json`](data/aso-metadata-history.json) | History of every store metadata change, for cadence enforcement. | — |
| [`data/backlinks-history.json`](data/backlinks-history.json) | Backlink counts over time from the backlinks monitor. | — |
| [`data/crawl-snapshot-latest.json`](data/crawl-snapshot-latest.json) | Latest full site crawl snapshot; paired crawl-diff files show what changed. | — |
| [`data/cwv-history.json`](data/cwv-history.json) | Core Web Vitals measurements over time. | — |
| [`data/gsc-anomalies-latest.json`](data/gsc-anomalies-latest.json) | Latest Search Console anomaly detection output (traffic drops/spikes). | — |
| [`data/gsc-top-pages-2026-05-29.json`](data/gsc-top-pages-2026-05-29.json) | Dated Google Search Console top-pages snapshot (one file per pull). | — |
| [`data/play-listing-devicegpt-en-US.json`](data/play-listing-devicegpt-en-US.json) | Cached Play Store listing for one app (one file per package/locale). | — |
| [`data/rank-history.json`](data/rank-history.json) | Time series of keyword rank positions from the rank tracker. | — |
| [`data/rank-watchlist.json`](data/rank-watchlist.json) | Keywords currently being watched by the rank tracker. | — |
| [`data/rpm-benchmarks.json`](data/rpm-benchmarks.json) | Ad RPM benchmark data (with AdMob and Reddit crowd-sourced variants). | — |
| [`data/seo-latest-report.txt`](data/seo-latest-report.txt) | Most recent combined SEO monitoring text report. | — |
| [`data/seo-logs/`](data/seo-logs/) | Daily and weekly run logs from the SEO monitoring scripts. | — |
| [`distribute/`](distribute/) | Content distribution hub: posts articles, pins, and videos to 11+ platforms with rate limits and history. | — |
| [`distribute/TIKTOK-SETUP.md`](distribute/TIKTOK-SETUP.md) | TikTok app review status and the credential-swap steps to run after approval. | — |
| [`distribute/articles/`](distribute/articles/) | 181 ready-to-publish markdown articles (finance calculators, free-tool roundups, country-specific tax tools). | — |
| [`distribute/awesome-list-tracker.md`](distribute/awesome-list-tracker.md) | Historical log of awesome-list PRs; program discontinued 2026-04-29 after GitHub spam flag. | — |
| [`distribute/blogger-auth.py`](distribute/blogger-auth.py) | One-time Google OAuth for Blogger API; saves tokens and blog ID to config.json. | `python3 scripts/distribute/blogger-auth.py` |
| [`distribute/config.example.json`](distribute/config.example.json) | Template for platform API keys/tokens; copy to config.json (gitignored). | — |
| [`distribute/distribute.py`](distribute/distribute.py) | Main publisher CLI: post/edit/delete/queue articles to devto, hashnode, medium, blogger, wordpress, tumblr, bluesky, mastodon, github, google-sites, pinterest. | `python3 scripts/distribute/distribute.py next` |
| [`distribute/drafts/`](distribute/drafts/) | 43 unpublished article drafts; 'distribute.py next' picks the highest-priority one. | — |
| [`distribute/google-sites-auth.py`](distribute/google-sites-auth.py) | Interactive setup for the Google Sites bridge; configures the Apps Script web-app URL. | `python3 scripts/distribute/google-sites-auth.py` |
| [`distribute/google-sites-bridge.gs`](distribute/google-sites-bridge.gs) | Apps Script web app: REST bridge that lets distribute.py create pages on Google Sites. | — |
| [`distribute/history.json`](distribute/history.json) | Record of every post per platform; powers duplicate detection and status command. | — |
| [`distribute/pin-images/`](distribute/pin-images/) | 2,058 pre-rendered Pinterest pin images, organized by board (finance, devtech, general, all-tools, top-tools). | — |
| [`distribute/pinterest-auth.py`](distribute/pinterest-auth.py) | One-time Pinterest OAuth2; creates refreshable token for pin posting. | `python3 scripts/distribute/pinterest-auth.py` |
| [`distribute/pinterest-upgrade-script.md`](distribute/pinterest-upgrade-script.md) | Video script and guide for applying to Pinterest Standard Access. | — |
| [`distribute/queue.json`](distribute/queue.json) | Posts waiting for rate limits to clear; flushed by 'distribute.py flush'. | — |
| [`distribute/remotion/`](distribute/remotion/) | Remotion video factory: plans, renders, and uploads short tool-promo videos to YouTube, TikTok, Instagram. | — |
| [`distribute/remotion/capture-tool.js`](distribute/remotion/capture-tool.js) | Playwright screenshot capture of tool pages for tutorial videos. | `node distribute/remotion/capture-tool.js --url /ai/grammar-checker/` |
| [`distribute/remotion/content-engine.py`](distribute/remotion/content-engine.py) | Generates SEO-optimized video plans from free data (Trends, autocomplete, Search Console, ASO keywords). | `python3 distribute/remotion/content-engine.py --count 30` |
| [`distribute/remotion/render-batch.js`](distribute/remotion/render-batch.js) | Renders batches of reels with Remotion from video plans or the tool index. | `node distribute/remotion/render-batch.js --from-plans` |
| [`distribute/remotion/upload/instagram-upload.js`](distribute/remotion/upload/instagram-upload.js) | Uploads Reels via Meta Graph API; limited to 1/day, 4/week. | `node distribute/remotion/upload/instagram-upload.js` |
| [`distribute/remotion/upload/tiktok-auth.js`](distribute/remotion/upload/tiktok-auth.js) | One-time TikTok OAuth for the Content Posting API. | `node distribute/remotion/upload/tiktok-auth.js` |
| [`distribute/remotion/upload/tiktok-upload.js`](distribute/remotion/upload/tiktok-upload.js) | Uploads videos to TikTok inbox drafts; enforces 2/day, 5/week limits. | `node distribute/remotion/upload/tiktok-upload.js` |
| [`distribute/remotion/upload/youtube-upload.js`](distribute/remotion/upload/youtube-upload.js) | Uploads a video to YouTube as private, then auto-publishes at the best time. | `node distribute/remotion/upload/youtube-upload.js --from-history` |
| [`distribute/remotion/youtube-autopilot.js`](distribute/remotion/youtube-autopilot.js) | One-command pipeline: decides Short vs Tutorial, renders, uploads, tracks status. | `node distribute/remotion/youtube-autopilot.js` |
| [`distribute/tumblr-auth.py`](distribute/tumblr-auth.py) | One-time Tumblr OAuth1; prints tokens for distribute.py. | `python3 scripts/distribute/tumblr-auth.py CONSUMER_KEY CONSUMER_SECRET` |
| [`distribute/wordpress-auth.py`](distribute/wordpress-auth.py) | One-time WordPress.com OAuth; saves access token to config.json. | `python3 scripts/distribute/wordpress-auth.py CLIENT_ID CLIENT_SECRET` |
| [`distribute/youtube-auth.py`](distribute/youtube-auth.py) | One-time YouTube Data API OAuth; reuses existing Google client, has --test mode. | `python3 scripts/distribute/youtube-auth.py` |

---

## 6. For AI agents (Cursor, Claude Code, any LLM)

1. **This README is the index** — find the script by task here; do not grep blindly.
2. **[`CLAUDE.md`](CLAUDE.md) is the rulebook** — read its "Critical Rules" + "Anti-Patterns" before running anything. Highlights: never fabricate metrics; never push store metadata without the cadence gate; never skip SEO scripts during ASO work.
3. **Orchestrators first** (section 3). Hand-picking leaf scripts for ASO = the #1 historical mistake in this repo.
4. **Outputs land in `data/`** of the HOST project (not this submodule) once `.teamz-automation.env` sets the paths.
5. Scripts are config-driven: if a script complains about a missing variable, the fix is in `.teamz-automation.env` (project) or `~/.config/teamzlab/automation.base.env` (machine) — not in the script.
6. Website-only script on an app project exits code `2` = "not applicable", not a failure.

## 7. Glossary (plain words)

| Term | Meaning |
|---|---|
| **ASO** | App Store Optimization — getting the app found in Play/App Store search |
| **SEO** | Search Engine Optimization — getting web pages found in Google/Bing |
| **GSC** | Google Search Console — Google's free "how my site ranks" data |
| **GA4** | Google Analytics 4 — visitor/usage analytics |
| **RPM** | Revenue per 1000 ad impressions — how much ads pay |
| **CWV** | Core Web Vitals — Google's page-speed health metrics |
| **SERP** | Search Engine Results Page — what Google shows for a query |
| **IAP** | In-App Purchase |
| **ASC** | App Store Connect — Apple's developer console |
| **Orchestrator** | A script/command that runs many leaf scripts in the right order |
| **Leaf script** | A script that does exactly one job |
| **Signal pull** | Data-collection-only ASO run (every 14 days), no metadata edits |
| **Full rewrite** | ASO metadata rewrite run (28-day iOS / 56-day Android minimum gap) |

---

*Index generated against the repo state of 2026-06-12; every tracked file/area is listed. When you add a script: add one row to the matching table in section 5 — one line of purpose + one runnable command. That is the whole contract.*
