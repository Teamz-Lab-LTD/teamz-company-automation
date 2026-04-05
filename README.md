# teamz-company-automation

Reusable, config-driven **SEO / analytics / QA / content** automation for any Teamz Lab project (website or app). Add as a git submodule; configure via `.teamz-automation.env`.

## Quick start (new project)

```bash
# 1. Add submodule
git submodule add https://github.com/Teamz-Lab-LTD/teamz-company-automation.git teamz-company-automation
git submodule update --init --recursive

# 2. Create project config
cp teamz-company-automation/.teamz-automation.env.example .teamz-automation.env
# Edit: set TEAMZ_SITE_URL, TEAMZ_PROJECT_TYPE, etc.

# 3. (First time on this machine) Set up shared token paths
mkdir -p ~/.config/teamzlab
cp teamz-company-automation/automation.base.env.example ~/.config/teamzlab/automation.base.env

# 4. Create symlinks so you can run scripts as `python3 scripts/...`
bash teamz-company-automation/setup-symlinks.sh

# 5. Authenticate Google APIs (one-time per machine)
python3 scripts/build-search-console-auth.py   # Search Console
python3 scripts/build-analytics-auth.py         # GA4
python3 scripts/build-adsense-auth.py           # AdSense (optional)
```

## Layout

| Path | What it contains |
|------|------------------|
| `py/` | Python scripts + `_teamz_config.py` (shared config loader) |
| `sh/` | Shell scripts + `lib/config.sh` (shared config loader) |
| `data/` | JSON/CSV output (rank history, backlinks, snapshots). **`ecommerce-demos.json`** — demo storefront URLs + pricing. **`ecommerce-landing-seo.json`** — long-tail ecommerce copy merged into `/ecommerce-development/` via `npm run sync:ecommerce-page`. **`ecommerce-gsc-keywords-latest.json`** — optional; produced by `npm run refresh:ecommerce-keywords` (`build-keyword-intel.py --export json` for queries hitting `ecommerce-development`). |
| `distribute/` | Multi-platform publishing (Blogger, Dev.to, Medium, etc.) |

## Config system

Scripts load config in this order (later overrides earlier):

1. `~/.config/teamzlab/automation.base.env` — machine-level shared defaults
2. `<host-project>/.teamz-automation.env` — **project-level** (URL, type, paths)
3. `teamz-company-automation/.teamz-automation.env` — submodule-level fallback

### Key variables

| Variable | Example | Required |
|----------|---------|----------|
| `TEAMZ_SITE_URL` | `https://tool.teamzlab.com/` | Yes |
| `TEAMZ_SITE_PROPERTY` | same as SITE_URL (or GSC property) | Yes |
| `TEAMZ_PROJECT_TYPE` | `website` or `app` | Yes |
| `TEAMZ_HOST_SITE_ROOT` | `/path/to/project` | Auto-detected |
| `TEAMZ_GOOGLE_CLOUD_PROJECT` | `my-gcp-project` | For GSC/GA4 |
| `TEAMZ_SC_TOKEN_FILE` | `~/.config/teamzlab/search-console-token.json` | For GSC scripts |
| `TEAMZ_PLAY_SERVICE_ACCOUNT_JSON` | path to Play SA key JSON | For `build-play-console.py` |
| `TEAMZ_PLAY_PACKAGE_NAME` | `com.example.app` | Android applicationId |
| `TEAMZ_GA4_PROPERTY_ID` | `528521795` | For GA4 scripts |

`TEAMZ_PROJECT_TYPE=app` makes website-only scripts exit with code `2` (not an error).

## Complete script catalog

### Google API integrations

| Script | What it does |
|--------|-------------|
| `sh/build-search-console.sh` | Pull GSC data: queries, pages, indexing status, devices |
| `sh/build-analytics.sh` | Pull GA4 traffic data: sessions, sources, top pages |
| `sh/build-adsense.sh` | Pull AdSense revenue: earnings, RPM, top pages |
| `sh/build-pagespeed.sh` | PageSpeed / Core Web Vitals for top pages |
| `sh/build-clarity.sh` | Microsoft Clarity session data |
| `sh/build-seo-dashboard.sh` | Combined dashboard (GSC + GA4 + PageSpeed) |
| `py/build-search-console-auth.py` | OAuth setup for Search Console |
| `py/build-analytics-auth.py` | OAuth setup for GA4 |
| `py/build-adsense-auth.py` | OAuth setup for AdSense |
| `py/build-keyword-planner-auth.py` | OAuth setup for Google Ads |
| `py/build-play-console.py` | Play crash metrics + pull/push store listing (service account) |

### SEO & keyword tools

| Script | What it does |
|--------|-------------|
| `py/build-keyword-intel.py` | Keyword research: volume, intent, CPC, difficulty, opportunities |
| `py/build-keyword-volume.py` | Keyword search volume estimator |
| `py/build-rank-tracker.py` | Daily rank tracking with trends + movers + watchlist |
| `py/build-request-indexing.py` | Request Google/Bing indexing for pages |
| `py/seo-keyword-engine.py` | Full keyword analysis engine |
| `sh/build-seo-audit.sh` | SEO keyword audit with hub scores |

### Backlinks & content

| Script | What it does |
|--------|-------------|
| `py/build-backlinks.py` | Directory submission tracker (39 directories) |
| `py/build-backlinks-overview.py` | Backlinks overview (DoFollow/NoFollow) |
| `py/build-content-ideas.py` | Content ideas from trends, gaps, competitors |

### Site builders (website mode)

| Script | What it does |
|--------|-------------|
| `sh/build-sitemap.sh` | Rebuild sitemap.xml |
| `sh/build-search-index.sh` | Rebuild search index + llms.txt + homepage counts |
| `py/build-static-schema.py` | Rebuild JSON-LD schemas (Breadcrumb, FAQ, WebApp) |
| `py/build-fix-orphans.py` | Auto-link orphan pages to siblings |
| `sh/build-internal-links.sh` | Internal link health score |

### QA & validation

| Script | What it does |
|--------|-------------|
| `sh/build-qa-check.sh` | Automated QA: missing FAQs, schemas, content, JS logic |
| `py/qa-test.py` / `sh/qa-test.sh` | QA test runner |
| `py/qa-runtime-test.py` | Runtime behavior tests |
| `py/qa-schema-layout.py` | Schema + layout consistency checker |
| `py/qa-server.py` | Local dev server for QA |

### SEO monitoring & experiments

| Script | What it does |
|--------|-------------|
| `py/build-gsc-anomalies.py` | CTR drops + impression spikes/drops (page + query) |
| `py/build-crawl-diff.py` | Snapshot canonical/robots/schema/title/H1; diff vs prior |
| `py/build-topic-cluster-report.py` | Page counts by top-level hub folder |
| `py/build-seo-experiments.py` | Before/after GSC totals for title/meta tests |
| `py/build-serp-features-log.py` | Manual SERP feature observations (snippet/PAA/video/AI) |
| `py/build-brand-mentions-log.py` | Manual brand mention tracking for outreach |
| `py/build-uptime-check.py` | HTTP health check + SSL expiry + response latency |
| `py/build-schema-validate.py` | Local JSON-LD validation per @type required fields |
| `py/build-serp-tracker.py` | Automated SERP feature detection (snippet/PAA/video/AI overview) |
| `py/build-reddit-scanner.py` | Auto-scan Reddit + Dev.to for brand mentions |
| `py/build-competitor-gaps.py` | Keyword gap analysis via GSC + Google Autocomplete |

### Build orchestration

| Script | What it does |
|--------|-------------|
| `sh/build.sh` | Full build pipeline + multi-step validation |
| `sh/build-catchup.sh` | Smart catch-up: detects stale data, runs what's needed |
| `sh/build-validate-freshness.sh` | Check for outdated/stale content |
| `sh/build-daily-seo.sh` | Daily SEO routine (rank + backlinks + keywords) |
| `sh/build-daily-seo-notify.sh` | Daily SEO + macOS notification + report |
| `sh/nightly-build.sh` | Nightly build agent (launchd, full pipeline) |
| `sh/continuous-build.sh` | Continuous build runner (timed sessions) |
| `sh/run-build-now.sh` | Trigger nightly build immediately |

### Content & assets

| Script | What it does |
|--------|-------------|
| `py/build-og-images.py` | Generate hub OG images |
| `py/build-hub-subtitles.py` | Generate hub page subtitles |
| `py/build-multilang.py` | Multi-language translation tracker |
| `py/build-programmatic-seo.py` | Programmatic SEO page generator (state/city variants) |
| `py/build-seo-audit-fixes.py` | Auto-fix common SEO issues |
| `py/build-seo-fix-all.py` | Bulk SEO fixer |
| `sh/build-static-header.sh` | Inject static header HTML (CLS prevention) |
| `sh/newsletter-export.sh` | Export newsletter subscribers from Firestore |

### Utilities

| Script | What it does |
|--------|-------------|
| `sh/secrets-export.sh` | GPG-encrypt project secrets for backup |
| `sh/secrets-import.sh` | Restore secrets from GPG backup |
| `sh/claude-sessions.sh` | List/kill stale Claude processes |
| `py/batch-fix-display-bug.py` | Batch fix display:none bugs |
| `py/generate-salary-cities.py` | Generate city-specific salary pages |

### ASO suite (free AppTweak alternative, `py/aso/`)

| Script | What it does |
|--------|-------------|
| `py/aso/aso-keywords.py` | Keyword research: Apple + Play autocomplete, expand, long-tail, trending |
| `py/aso/aso-metadata.py` | Metadata audit + ASO score + LLM optimization prompts |
| `py/aso/aso-competitors.py` | Competitor find/analyze/keyword-gaps/matrix |
| `py/aso/aso-reviews.py` | Review fetch, keywords, sentiment, complaints, reply prompts |
| `py/aso/aso-track.py` | Daily keyword rank tracking via iTunes Search |
| `py/aso/aso-guide.py` | ASO crash course + personalized checklists + LLM prompts for content |

Uses free public APIs only (iTunes Search, Apple/Play autocomplete, iTunes RSS reviews). No paid keys. Config: `TEAMZ_APP_IDS`, `TEAMZ_ASO_COUNTRIES`, `TEAMZ_ASO_KEYWORDS`.

### Google Play Console (service account, `py/build-play-console.py`)

Private Play data and **publishing** store listings require a **service account** linked in Play Console (not OAuth like Search Console). The GCP project can differ from Firebase / `TEAMZ_GOOGLE_CLOUD_PROJECT`.

| Step | Action |
|------|--------|
| 1 | In your **Play-API** GCP project: create a service account → **Keys** → JSON; enable **Google Play Android Developer API** and **Play Developer Reporting API**. |
| 2 | **Play Console** → **Users and permissions** → invite the service account email. Grant **View app information** (reporting) and **Manage store presence** (title/descriptions/video). |
| 3 | Set `TEAMZ_PLAY_SERVICE_ACCOUNT_JSON` and `TEAMZ_PLAY_PACKAGE_NAME` in `.teamz-automation.env`. |
| 4 | `pip3 install google-api-python-client google-auth` |

| Command | Purpose |
|---------|---------|
| `python3 scripts/build-play-console.py report --days 7 --out data/play-crash.json` | Crash-rate metrics (Reporting API; end date lags ~2d — override with `TEAMZ_PLAY_REPORTING_LAG_DAYS`) |
| `python3 scripts/build-play-console.py listing-pull --language en-US` | Export listing JSON (edit draft → read → discard) |
| `python3 scripts/build-play-console.py listing-push --file listing.json` | Validate merged listing, **discard** draft |
| `python3 scripts/build-play-console.py listing-push --file listing.json --commit` | **Publish** listing changes (live) |

Pair **listing-pull** / **listing-push** with `py/aso/` research; keep the JSON in version control only if it contains no secrets.

### ASO reliability notes (production)

- `market.android.com` suggest endpoints are legacy and can return frequent `404`; ASO now treats them as **last-resort** only.
- Primary Play suggestions come from `suggestqueries.google.com/complete/search` (chrome/firefox client variants + multiple query patterns).
- Google suggest can return JSON prefixed with `)]}'`; parser strips this safely before JSON decode.
- Play listing HTML fetch uses browser-like headers and retries with `&gl=us` when initial response is empty.
- Apple hints requests use browser-like accept/referer headers and fall back to iTunes Search title extraction.
- This is production-ready with resilient fallbacks, but external API behavior can still vary by region/rate limits over time.

### LLM handoff contract (for other projects)

When another project or AI agent integrates ASO scripts, keep this fallback order:

1. `play_autocomplete()` -> Google suggest endpoint first.
2. Legacy `market.android.com` suggest only if primary is empty.
3. `apple_autocomplete()` -> hints endpoint first, iTunes Search fallback.
4. `play_store_metadata()` -> browser-like headers, retry with `hl/gl`.

Operational expectations:

- Treat upstream `403/404/429` as recoverable, not fatal.
- Keep request pacing (`_MIN_DELAY`) enabled.
- Log actionable fix hints (`[FIX]`) for operators and LLM agents.
- Validate JSON decode and HTML parse failures with graceful fallback, never hard crash.

## For AI assistants

When working on a project that uses this submodule, run scripts via the `scripts/` symlink path:

```bash
python3 scripts/build-keyword-intel.py --opportunities
python3 scripts/build-play-console.py listing-pull --language en-US
python3 scripts/build-rank-tracker.py report
./scripts/build-seo-dashboard.sh --quick
./scripts/build.sh
```

All scripts auto-detect the host project root via config. No hardcoded paths.
