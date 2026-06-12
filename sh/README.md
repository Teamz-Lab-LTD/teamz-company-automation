# sh/ — shell scripts (builds, monitors, release gates)

The sh/ folder holds the shell-script half of Teamz Lab's company automation toolkit. These scripts pull marketing data (Search Console, GA4, AdSense, PageSpeed, Clarity), rebuild and QA the tools website (sitemap, search index, link checks), and handle app-release chores (AAB builds, pre-release checks, ASO refresh runs, secrets backup). Host projects expose them via setup-symlinks.sh, so you usually run them as scripts/<name>.sh from the project root.

All scripts source [`lib/config.sh`](./lib/config.sh) for paths/env. From a host project they are callable as `bash scripts/<name>.sh`.

| File | What it does | Typical command |
|---|---|---|
| [`aso-refresh-runner.sh`](./aso-refresh-runner.sh) | Chains all read-only ASO/SEO data scripts for one app and prints a markdown report. | `bash scripts/aso-refresh-runner.sh <app-slug> SIGNAL_ONLY` |
| [`aso-refresh-selftest.sh`](./aso-refresh-selftest.sh) | Static check that the /aso-refresh skill wiring (registry, symlinks, hooks, logs) is intact. | `bash scripts/aso-refresh-selftest.sh <app-slug>` |
| [`build-adsense.sh`](./build-adsense.sh) | Pulls live AdSense revenue, RPM, clicks, and impressions from the AdSense API. | `bash scripts/build-adsense.sh --all` |
| [`build-analytics.sh`](./build-analytics.sh) | Pulls live GA4 traffic data: pages, sources, daily and 30-day overviews. | `bash scripts/build-analytics.sh --all` |
| [`build-catchup.sh`](./build-catchup.sh) | Detects which daily/weekly/monthly SEO jobs are stale and runs only those. | `bash scripts/build-catchup.sh --status` |
| [`build-clarity.sh`](./build-clarity.sh) | Pulls Microsoft Clarity bot, traffic, and UX engagement metrics (10 requests/day limit). | `bash scripts/build-clarity.sh 3` |
| [`build-daily-seo-notify.sh`](./build-daily-seo-notify.sh) | Runs SEO tasks, sends a macOS notification, and writes a summary report for health checks. | `bash scripts/build-daily-seo-notify.sh --daily` |
| [`build-daily-seo.sh`](./build-daily-seo.sh) | Runs the scheduled SEO routine: daily rank tracking, weekly deep scan, monthly full audit. | `bash scripts/build-daily-seo.sh --daily` |
| [`build-internal-links.sh`](./build-internal-links.sh) | Checks every internal link across the tools website and finds orphan pages (website projects only). | `bash scripts/build-internal-links.sh --quick` |
| [`build-pagespeed.sh`](./build-pagespeed.sh) | Checks Core Web Vitals and performance scores via Google PageSpeed Insights API. | `bash scripts/build-pagespeed.sh --top20` |
| [`build-playstore-aab.sh`](./build-playstore-aab.sh) | Builds a release Android App Bundle for any Flutter project with a standard file name. | `bash scripts/build-playstore-aab.sh` |
| [`build-qa-check.sh`](./build-qa-check.sh) | One QA pass over website pages: SEO structure, runtime safety, usability, design system. | `bash scripts/build-qa-check.sh --verbose` |
| [`build-search-console.sh`](./build-search-console.sh) | Pulls Google Search Console queries, pages, status, and ranking opportunities. | `bash scripts/build-search-console.sh --all` |
| [`build-search-index.sh`](./build-search-index.sh) | Rebuilds the website's search-index.js plus homepage counts and sitemap after any page change. | `bash scripts/build-search-index.sh` |
| [`build-seo-audit.sh`](./build-seo-audit.sh) | Wrapper around the SEO+ASO keyword engine: audits, keyword suggestions, trends, app-name compares. | `bash scripts/build-seo-audit.sh --report` |
| [`build-seo-dashboard.sh`](./build-seo-dashboard.sh) | Free Ubersuggest-style dashboard combining Search Console, GA4, and PageSpeed into one report. | `bash scripts/build-seo-dashboard.sh --quick` |
| [`build-sitemap.sh`](./build-sitemap.sh) | Rebuilds sitemap.xml from all tool pages using git dates for lastmod. | `bash scripts/build-sitemap.sh` |
| [`build-static-header.sh`](./build-static-header.sh) | Injects the shared pre-rendered header HTML into every page to stop layout shift (CLS). | `bash scripts/build-static-header.sh --check` |
| [`build-validate-freshness.sh`](./build-validate-freshness.sh) | Finds stale content: old years in titles, wrong tool counts, outdated data. | `bash scripts/build-validate-freshness.sh` |
| [`build.sh`](./build.sh) | Master website build: rebuilds index, sitemap, counts, then validates everything; run after any change. | `bash scripts/build.sh` |
| [`claude-sessions.sh`](./claude-sessions.sh) | Lists running Claude processes and can kill sessions older than 24 hours. | `bash scripts/claude-sessions.sh --kill-old` |
| [`continuous-build.sh`](./continuous-build.sh) | Runs timed unattended build sessions (Claude builds tools plus maintenance) while you are away. | `bash scripts/continuous-build.sh 3h` |
| [`iap-smoke-test.sh`](./iap-smoke-test.sh) | Dry-runs the whole in-app-purchase setup pipeline (discovery, preflight, store verify) without writing anything. | `bash scripts/iap-smoke-test.sh --sku <sku>` |
| [`install-claude-context.sh`](./install-claude-context.sh) | Wires kit knowledge into a host project: writes CLAUDE.md imports, skill symlinks, optional git hooks. | `bash scripts/install-claude-context.sh --install-hooks` |
| [`lib/config.sh`](./lib/config.sh) | Shared config loader sourced by every script: resolves paths, env files, tokens, and defaults. | — |
| [`newsletter-export.sh`](./newsletter-export.sh) | Exports newsletter subscribers from Firestore via the Firebase CLI, as list, CSV, or count. | `bash scripts/newsletter-export.sh --csv` |
| [`nightly-build.sh`](./nightly-build.sh) | The 3 AM launchd agent: full nightly pipeline with all local scripts and tokens. | `bash scripts/nightly-build.sh --status` |
| [`overflow-audit.sh`](./overflow-audit.sh) | Runs Flutter overflow tests to catch modal/sheet layout breaks on small phones before release. | `bash scripts/overflow-audit.sh` |
| [`pre-release-verify.sh`](./pre-release-verify.sh) | Pre-release gate for Flutter+Firebase apps: config, functions, secrets, SHA keys, analyze, build readiness. | `bash scripts/pre-release-verify.sh --fix` |
| [`qa-test.sh`](./qa-test.sh) | Automated QA suite that tests every website tool page for common issues, with optional auto-fix. | `bash scripts/qa-test.sh --fix` |
| [`refresh-ecommerce-gsc-keywords.sh`](./refresh-ecommerce-gsc-keywords.sh) | Exports Search Console queries for the ecommerce landing page to a JSON data file. | `bash scripts/refresh-ecommerce-gsc-keywords.sh` |
| [`run-build-now.sh`](./run-build-now.sh) | Triggers the full nightly build pipeline immediately using the Sonnet model. | `bash scripts/run-build-now.sh` |
| [`secrets-export.sh`](./secrets-export.sh) | Packs every API key, token, and config into one encrypted GPG backup file. | `bash scripts/secrets-export.sh` |
| [`secrets-import.sh`](./secrets-import.sh) | Restores all API keys and configs on a new machine from the encrypted backup. | `bash scripts/secrets-import.sh teamzlab-secrets.gpg` |

---
**Lost?** The repo-wide index lives in [`../README.md`](../README.md) (root README, section 5) and the agent rulebook in [`../CLAUDE.md`](../CLAUDE.md). This folder's table above is the complete list — every file here is in it.
