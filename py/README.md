# py/ — Python toolbox (SEO, Search Console, QA, stores, revenue)

The py/ folder is the script toolbox of teamz-company-automation: ~67 standalone Python scripts that do SEO research, App Store/Play Store (ASO) checks, store automation (IAP, achievements, Play Console), site QA, and revenue tracking for every Teamz Lab website and app. Most scripts are free-API or stdlib-only, read shared config from _teamz_config.py and ~/.config/teamzlab tokens, and write JSON/CSV results into the host project's data/ folder. After running setup-symlinks.sh in a host project, every script is callable as scripts/<name>.py.

**Standalone use:** every script runs from a host project as `python3 scripts/<name>.py` (after `setup-symlinks.sh`), or directly as `python3 py/<name>.py` from this repo if `.teamz-automation.env` exists next to it. Config questions → [`_teamz_config.py`](./_teamz_config.py) loads the env cascade described in the root README.

| File | What it does | Typical command |
|---|---|---|
| [`_teamz_config.py`](./_teamz_config.py) | Shared library: loads .teamz-automation.env files and resolves site, data, and token paths for all scripts. | — |
| [`admob.py`](./admob.py) | Reads AdMob accounts, apps, ad units, and earnings reports via REST API; OAuth stored once. | `python3 scripts/admob.py report --days 7` |
| [`aso-claims-lint.py`](./aso-claims-lint.py) | Blocks store submission if listing text or screenshots contain forbidden claims like "offline" or "no ads". | `python3 scripts/aso-claims-lint.py` |
| [`aso-name-collision.py`](./aso-name-collision.py) | Checks whether a proposed app name already exists or clashes on App Store and Google Play. | `python3 scripts/aso-name-collision.py "Arrow Jam 3D"` |
| [`batch-fix-display-bug.py`](./batch-fix-display-bug.py) | Bulk-fixes the JS bug where style.display='' leaves elements hidden by a CSS class. | `python3 scripts/batch-fix-display-bug.py --dry-run` |
| [`build-adsense-auth.py`](./build-adsense-auth.py) | One-time browser OAuth for the AdSense API; saves token under ~/.config/teamzlab. | `python3 scripts/build-adsense-auth.py` |
| [`build-analytics-auth.py`](./build-analytics-auth.py) | One-time browser OAuth for the Google Analytics (GA4) Data API token. | `python3 scripts/build-analytics-auth.py` |
| [`build-backlinks-overview.py`](./build-backlinks-overview.py) | Finds who links to your site using free sources, mainly Search Console links data. | `python3 scripts/build-backlinks-overview.py scan` |
| [`build-backlinks.py`](./build-backlinks.py) | Tracks and helps submit the site to 40+ free directories; pings indexing services. | `python3 scripts/build-backlinks.py submit` |
| [`build-bing-data.py`](./build-bing-data.py) | Pulls Bing Webmaster top queries, top pages, and crawl stats into dated JSON snapshots. | `python3 scripts/build-bing-data.py` |
| [`build-brand-mentions-log.py`](./build-brand-mentions-log.py) | Manually log brand mentions (Reddit, Medium, forums) to a CSV for outreach follow-up. | `python3 scripts/build-brand-mentions-log.py --report` |
| [`build-competitor-gaps.py`](./build-competitor-gaps.py) | Crosses your top GSC queries with Google Autocomplete to find keywords you don't rank for. | `python3 scripts/build-competitor-gaps.py` |
| [`build-content-ideas.py`](./build-content-ideas.py) | Generates content and tool ideas from Autocomplete, Trends, Search Console, Reddit, and seasonal calendars. | `python3 scripts/build-content-ideas.py --trending` |
| [`build-crawl-diff.py`](./build-crawl-diff.py) | Snapshots each page's canonical, robots meta, schema count, and H1; diffs against the previous run. | `python3 scripts/build-crawl-diff.py` |
| [`build-dead-revival.py`](./build-dead-revival.py) | Re-targets indexed pages with zero search demand toward related keywords that do have demand. | `python3 scripts/build-dead-revival.py` |
| [`build-enhance-queue.py`](./build-enhance-queue.py) | Merges outputs of the other SEO scripts into one prioritized queue of tools to improve. | `python3 scripts/build-enhance-queue.py` |
| [`build-fix-orphans.py`](./build-fix-orphans.py) | Adds orphan tool pages into siblings' related-tools lists so every page gets internal links. | `python3 scripts/build-fix-orphans.py` |
| [`build-gsc-anomalies.py`](./build-gsc-anomalies.py) | Compares two Search Console time windows and flags CTR drops plus impression spikes or drops. | `python3 scripts/build-gsc-anomalies.py` |
| [`build-gsc-broken-pages.py`](./build-gsc-broken-pages.py) | Finds 404 pages Google still sends traffic to and appends 301 redirect rules to .htaccess. | `python3 scripts/build-gsc-broken-pages.py --dry-run` |
| [`build-hub-subtitles.py`](./build-hub-subtitles.py) | Fills missing subtitles on hub-page tool cards using each tool's meta description. | `python3 scripts/build-hub-subtitles.py --fix` |
| [`build-keyword-batches.py`](./build-keyword-batches.py) | Turns a project's page inventory into upload-ready CSVs for manual Keyword Planner volume pulls. | `python3 scripts/build-keyword-batches.py` |
| [`build-keyword-intel.py`](./build-keyword-intel.py) | Free Ubersuggest replacement: GSC keyword report with intent, difficulty, opportunities, and gaps. | `python3 scripts/build-keyword-intel.py --opportunities` |
| [`build-keyword-planner-auth.py`](./build-keyword-planner-auth.py) | One-time browser OAuth for the Google Ads Keyword Planner API token. | `python3 scripts/build-keyword-planner-auth.py` |
| [`build-keyword-volume.py`](./build-keyword-volume.py) | Estimates relative keyword search volume (0-100) from Trends, Autocomplete, and GSC — no paid API. | `python3 scripts/build-keyword-volume.py "bmi calculator"` |
| [`build-money-tracker.py`](./build-money-tracker.py) | Tracks whether high-RPM money pages are growing, flat, stuck, or dead using 28-day GSC data. | `python3 scripts/build-money-tracker.py` |
| [`build-multilang.py`](./build-multilang.py) | Shows which high-RPM tools have, or still need, Spanish/Portuguese and other language versions. | `python3 scripts/build-multilang.py status` |
| [`build-og-images.py`](./build-og-images.py) | Generates branded 1200x630 social-share (OG) images per hub category using Pillow. | `python3 scripts/build-og-images.py` |
| [`build-play-console.py`](./build-play-console.py) | Pulls Play Console reports and pulls/pushes store listing text via a service account. | `python3 scripts/build-play-console.py report` |
| [`build-programmatic-seo.py`](./build-programmatic-seo.py) | Generates location-specific tool page variants, e.g. one income-tax page per US state. | `python3 scripts/build-programmatic-seo.py --list` |
| [`build-public-rpm-benchmarks.py`](./build-public-rpm-benchmarks.py) | Writes a local database of public ad RPM benchmarks per niche and country; hand-curated quarterly. | `python3 scripts/build-public-rpm-benchmarks.py --top 10` |
| [`build-rank-tracker.py`](./build-rank-tracker.py) | Records daily keyword positions from Search Console; shows ranking trends, movers, and a watchlist. | `python3 scripts/build-rank-tracker.py record` |
| [`build-reddit-rpm-tracker.py`](./build-reddit-rpm-tracker.py) | Scrapes Reddit for real publisher RPM/eCPM mentions to sanity-check the static benchmarks. | `python3 scripts/build-reddit-rpm-tracker.py --quick` |
| [`build-reddit-scanner.py`](./build-reddit-scanner.py) | Auto-scans Reddit and Dev.to for brand mentions and appends new ones to a CSV. | `python3 scripts/build-reddit-scanner.py` |
| [`build-request-indexing.py`](./build-request-indexing.py) | Asks Google (URL Inspection), Bing/DuckDuckGo (IndexNow), and sitemap pings to index your pages. | `python3 scripts/build-request-indexing.py` |
| [`build-revenue-velocity-score.py`](./build-revenue-velocity-score.py) | Scores candidate tool ideas by estimated dollars per month at month 3; ranks them. | `python3 scripts/build-revenue-velocity-score.py --demo` |
| [`build-schema-validate.py`](./build-schema-validate.py) | Validates every page's JSON-LD schema blocks locally for required fields per type. | `python3 scripts/build-schema-validate.py` |
| [`build-search-console-auth.py`](./build-search-console-auth.py) | One-time browser OAuth for the Google Search Console API token. | `python3 scripts/build-search-console-auth.py` |
| [`build-seo-audit-fixes.py`](./build-seo-audit-fixes.py) | Fixes crawl-audit issues: too-short titles, URL/title keyword mismatch, and thin pages. | `python3 scripts/build-seo-audit-fixes.py --dry-run` |
| [`build-seo-experiments.py`](./build-seo-experiments.py) | Compares Search Console numbers before vs after a dated page change, per experiment. | `python3 scripts/build-seo-experiments.py` |
| [`build-seo-fix-all.py`](./build-seo-fix-all.py) | Bulk-fixes mechanical SEO issues across all pages: meta descriptions, display bug, freshness line. | `python3 scripts/build-seo-fix-all.py --dry-run` |
| [`build-serp-features-log.py`](./build-serp-features-log.py) | Manually log SERP features you observe (snippet, PAA, AI overview) per keyword into CSV. | `python3 scripts/build-serp-features-log.py --report` |
| [`build-serp-tracker.py`](./build-serp-tracker.py) | Auto-detects SERP features for watchlist keywords by fetching and parsing Google results. | `python3 scripts/build-serp-tracker.py` |
| [`build-static-schema.py`](./build-static-schema.py) | Extracts schema data from each page's inline JS and injects static JSON-LD into the head. | `python3 scripts/build-static-schema.py` |
| [`build-topic-cluster-report.py`](./build-topic-cluster-report.py) | Counts pages per top-level hub folder for content-cluster planning; saves JSON. | `python3 scripts/build-topic-cluster-report.py` |
| [`build-uptime-check.py`](./build-uptime-check.py) | Checks site health on sample sitemap URLs plus SSL certificate expiry; can gate with exit 1. | `python3 scripts/build-uptime-check.py --alert` |
| [`build-youtube-keywords.py`](./build-youtube-keywords.py) | YouTube-specific keyword research via YouTube autocomplete and search results; scores each seed keyword. | `python3 scripts/build-youtube-keywords.py "uber clone"` |
| [`cloudflare-purge.py`](./cloudflare-purge.py) | Purges Cloudflare cache for a Teamz site or for specific URLs; shared token setup. | `python3 scripts/cloudflare-purge.py` |
| [`gamecenter.py`](./gamecenter.py) | Syncs Apple Game Center achievements from one YAML file via the App Store Connect API. | `python3 scripts/gamecenter.py sync --dry-run` |
| [`generate-salary-cities.py`](./generate-salary-cities.py) | Generates 30 city-specific salary comparison pages from the base salary tool. | `python3 scripts/generate-salary-cities.py` |
| [`gpgs.py`](./gpgs.py) | Syncs Google Play Games achievements from the same YAML file via the Games Configuration API. | `python3 scripts/gpgs.py sync --dry-run` |
| [`gpgs_icon_push.py`](./gpgs_icon_push.py) | Back-compat shim: uploads Play Games achievement icons via the web_automation Playwright recipe. | `python3 scripts/gpgs_icon_push.py --application-id <id>` |
| [`iap.py`](./iap.py) | Creates one in-app purchase on Apple, Google, and RevenueCat in a single automated flow. | `python3 scripts/iap.py setup --sku com.teamz.<app>.<slug> --price-usd 2.99 --name "<Bundle Name>"` |
| [`iap_discovery.py`](./iap_discovery.py) | Library that verifies an API endpoint exists in Google's discovery doc before iap.py calls it. | `python3 scripts/iap_discovery.py refresh` |
| [`iap_doctor.py`](./iap_doctor.py) | Diagnoses a live app whose purchases fail or whose remove-ads entitlement never activates. | `python3 scripts/iap_doctor.py` |
| [`iap_preflight.py`](./iap_preflight.py) | Pre-checks 14 conditions (keys, permissions, builds, SKU naming, text limits) before iap.py setup. | `python3 scripts/iap_preflight.py --sku com.teamz.<app>.<slug> --price-usd 2.99` |
| [`inspect-cwv.py`](./inspect-cwv.py) | Batch Core Web Vitals and Lighthouse scores via PageSpeed Insights; fails CI on bad thresholds. | `python3 scripts/inspect-cwv.py --url <URL>` |
| [`inspect-urls.py`](./inspect-urls.py) | Batch Google URL Inspection: indexing verdict, canonical, and rich-results status after schema/sitemap changes. | `python3 scripts/inspect-urls.py --url <URL>` |
| [`keyword_volume_manual.py`](./keyword_volume_manual.py) | Library that reads manually exported Keyword Planner CSVs — the authoritative exact search-volume source. | — |
| [`qa-mobile-ux.py`](./qa-mobile-ux.py) | Loads changed tools in an iPhone-sized headless browser; blocks on horizontal scroll and tiny touch targets. | `python3 scripts/qa-mobile-ux.py --changed` |
| [`qa-runtime-test.py`](./qa-runtime-test.py) | Opens every tool page in headless Chromium and fails on JS errors or broken rendering. | `python3 scripts/qa-runtime-test.py --changed` |
| [`qa-schema-layout.py`](./qa-schema-layout.py) | Checks pages for duplicate schema blocks and render calls missing their HTML containers. | `python3 scripts/qa-schema-layout.py` |
| [`qa-server.py`](./qa-server.py) | Tiny multi-threaded local HTTP server used by the QA scripts (default port 9091). | `python3 scripts/qa-server.py 9091` |
| [`qa-test.py`](./qa-test.py) | Fast static QA over all pages: doctype, lang, viewport, title, and similar structural checks. | `python3 scripts/qa-test.py` |
| [`revenue_priority.py`](./revenue_priority.py) | Library that maps a page's hub/slug to an expected dollars-per-month number for prioritization. | — |
| [`seo-healthcheck.py`](./seo-healthcheck.py) | Probes the whole SEO toolchain's data quality, catching scripts that run but silently return blanks. | `python3 scripts/seo-healthcheck.py` |
| [`seo-keyword-engine.py`](./seo-keyword-engine.py) | All-in-one free SEO and ASO keyword tool: audit, suggest, trends, validate ideas, auto-fix placement. | `python3 scripts/seo-keyword-engine.py audit` |
| [`serp_difficulty.py`](./serp_difficulty.py) | Library that scores keyword winnability 1-10 by checking which authority sites rank on page 1. | — |

---
**Lost?** The repo-wide index lives in [`../README.md`](../README.md) (root README, section 5) and the agent rulebook in [`../CLAUDE.md`](../CLAUDE.md). This folder's table above is the complete list — every file here is in it.
