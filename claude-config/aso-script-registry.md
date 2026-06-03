# ASO + SEO Script Registry — Every Tool, When to Call It

**Used by `/aso-refresh` skill.** Source of truth for what runs in which mode. If a script exists but isn't listed here, the skill won't know to call it — add it.

Last full audit: 2026-06-03. Re-run `ls py/aso/ py/` quarterly to catch new scripts.

---

## 32 ASO Scripts (py/aso/)

Grouped by purpose. Mode = which `/aso-refresh` run fires it.

### A. Canonical orchestrators (entry points — call ONE, never bypass)
| Script | Mode | What it does | Always-call? |
|--------|------|--------------|--------------|
| `aso-store-blitz.py` | REWRITE | 13-step full pipeline: preflight → keywords → competitors → AI-edit → compose → pad-resize → feature-graphic → localize → play-push → apple-version → apple-metadata → apple-screenshots → apple-submit | YES in REWRITE |
| `aso-store-release.py` | REWRITE (legacy) | Older orchestrator. Kept for backwards-compat; new work uses aso-store-blitz.py | Only if blitz fails |
| `aso-master-precheck.sh` | SIGNAL | Multi-source data merge: Play bulk reports + Trends + competitor reviews + Firebase funnels + autocomplete seeds + ChatGPT Deep Research prompt | YES in SIGNAL |

### B. Keyword research + scoring
| Script | Mode | What it does | When |
|--------|------|--------------|------|
| `aso-keywords.py` | both | Apple + Play autocomplete fetch + scoring | Auto-called by aso-store-blitz.py step 2 |
| `aso-keyword-pipeline.py` | both | Chains Apple autocomplete + Play autocomplete + iTunes Search API + scoring → one CSV | Step 5 of pipeline; or standalone for ad-hoc |
| `aso-seo-merge.py` | both | Merges ASO scores with web-search volume (build-keyword-volume.py output) | Step 6 of pipeline; never skip — copy must merge both signals |

### C. Competitor + voice-of-user intel
| Script | Mode | What it does | When |
|--------|------|--------------|------|
| `aso-competitors.py` | both | Pull top N competitors via iTunes Search + Play scraper, with metadata + ratings | Step 7 of pipeline; foundation for RULE-001 winnability table |
| `aso-reviews.py` | both | Mine competitor reviews (last N) for pain-theme classification: missing_feature / slow / broken / privacy / price / UI | Step 8 of pipeline; feeds voice-of-user.md |
| `aso-deep-research-prompt.py` | both | Generates ChatGPT Deep Research prompt for competitor SERP intel | Auto-called by aso-master-precheck.sh |

### D. Monetization context (Rule 4a — mandatory before money claims)
| Script | Mode | What it does | When |
|--------|------|--------------|------|
| `aso-admob-rpm-benchmarks.py` | both | 15 categories × 5 ad formats × 56 country multipliers eCPM benchmarks | Step 9 of pipeline; required if copy mentions revenue/IAP/$ |
| `admob.py` (root, not aso/) | both | Live AdMob REST API: accounts, apps, ad-units, report | Health check before any RPM-dependent decision |

### E. Behavioral signals
| Script | Mode | What it does | When |
|--------|------|--------------|------|
| `aso-firebase-events.py` | both | Top-N Firebase Analytics events + sequential funnel (requires Blaze + BigQuery export) | Step 10 of pipeline; feeds positioning narrative |
| `aso-track.py` | both | Record today's keyword rank positions for 14-day delta | Step 11; always-call regardless of mode |
| `aso-velocity.py` | both | Pull Play Reporting API + ASC Sales & Trends, append to history CSV | Run WEEKLY independently; also each SIGNAL run |

### F. Metadata generation + push
| Script | Mode | What it does | When |
|--------|------|--------------|------|
| `aso-metadata.py` | REWRITE | Generate optimized listing draft (title/subtitle/keywords/desc) from merged signals | Step 12; auto-called by aso-store-blitz.py |
| `aso-preflight.py` | REWRITE | Compliance gate: forbidden claims (Rule 2), keyword stuffing, duplicate kws (iOS Ariel Michaeli rule), unvalidated money claims | Step 13; hard-fails on violation |
| `aso-localize.py` | REWRITE | Localize metadata to 39 Apple + 39 Play locales. Use per-project `automation_data/localize_metadata.py` for hand-translated tuples (NEVER English fallback per Rule P2.1) | Step 14 |
| `aso-localize-metadata-template.py` | one-time | Per-project translation scaffold template | When onboarding new app |
| `aso-play-batch-push.py` | REWRITE | Play Console batch push (listings + graphics, 39 locales) | Step 9 of aso-store-blitz.py |
| `aso-copy-helper.py` | REWRITE | Generate Apple ASC + Play paste files (`<locale>...</locale>` blocks for bulk-locale input) | Always before manual Play UI steps |
| `aso-release-notes-gen.py` | REWRITE | Auto release notes from git commits | Step 12 (REWRITE-iOS) |

### G. Visual / screenshot pipeline (5 scripts — orchestrate via aso-store-blitz.py steps 4-7)
| Script | Mode | What it does | When |
|--------|------|--------------|------|
| `aso-icon-audit.py` | REWRITE | Icon contrast / size / alpha / fill check | Before icon push |
| `aso-compose-screenshot.py` | REWRITE | Toss-style composer: Apple frame + Poppins headline. Zero API cost. See CLAUDE.md Rule P4.6 + P4.7 for bug-prevention | Step 5 |
| `aso-generate-batch.py` | REWRITE | Batch driver reading `automation_data/aso_screenshot_presets.json` | Step 5 |
| `aso-pad-resize.py` | REWRITE | Fan out composed -> 5 device sizes (1242x2208, 1242x2688, 2048x2732, 1080x1920, 1200x1920) | Step 6 |
| `aso-tablet-from-phone.py` | REWRITE | Derive iPad tablet shots from iPhone outputs (Universal-app submit blocker prevention) | Step 6 |
| `aso-gemini-edit.py` | REWRITE | Nano Banana AI edit (USD/local terms etc) | Step 4 (only if en-US-edited dir missing) |
| `aso-openrouter-image-edit.py` | REWRITE | Cheaper Gemini 2.5 Flash Image via OpenRouter (~$0.04/image). Use for 1024×500 Play feature graphic per Rule P4.8 | Step 7 |

### H. Post-release monitoring (cron-call, NOT in /aso-refresh run)
| Script | Mode | What it does | When |
|--------|------|--------------|------|
| `aso-experiments.py` | post | A/B experiment tracker (icon, screenshots, subtitle) | After REWRITE push: `aso-experiments.py add ...`. Weekly `snapshot`. |
| `aso-priority-export.py` | both | Mirror store positioning into in-app tool list ordering (Rule P5.7) | Auto-called as `priority_export` step. CRITICAL for retention. |
| `aso-guide.py` | REWRITE | Print manual-steps guide (screenshots, content rating, data safety) | After aso-store-blitz.py finishes |

---

## 25 Leading-Indicator SEO Scripts (py/, root)

These produce signals that arrive on Google web search BEFORE the equivalent term lights up in App Store search. Always-skip is fine for indie SEO; never-skip for ASO leading-indicator purposes is wrong.

### I. Keyword volume + intent (call in SIGNAL mode)
| Script | Purpose | Output |
|--------|---------|--------|
| `build-keyword-volume.py` | Google Trends + autocomplete + Bing Webmaster volume + Google result counts | `data/keyword-volume-latest.json` |
| `build-keyword-intel.py` | Different angle: intent classification + question keywords | `data/keyword-intel-latest.json` |
| `build-keyword-planner-auth.py` | Google Keyword Planner OAuth (one-time setup) | token JSON |
| `build-bing-data.py` | Bing Webmaster keyword volume (more honest than GSC for low-traffic sites) | `data/bing-data-latest.json` |
| `seo-keyword-engine.py` | Aggregator: keyword research engine pulling multiple sources | Combined CSV |
| `build-youtube-keywords.py` | **MANDATORY per Rule 6 before ANY video/Shorts/Reels content.** YouTube intent ≠ Google Search intent. | `data/youtube-keywords-latest.json` |

### J. Rank tracking + SERP monitoring (call WEEKLY, ASO leading indicator)
| Script | Purpose |
|--------|---------|
| `build-rank-tracker.py` | Daily rank tracking for tracked keywords (web). If a term drops on web, it usually drops on App Store within 7-14 days. |
| `build-serp-tracker.py` | SERP feature presence (featured snippet, video carousel, knowledge panel) |
| `build-serp-features-log.py` | Append-only SERP features history |
| `build-gsc-anomalies.py` | GSC anomaly detector — sudden CTR/position drops |
| `build-gsc-broken-pages.py` | GSC "Discovered — currently not indexed" finder |

### K. Authority + trust signals (call MONTHLY)
| Script | Purpose |
|--------|---------|
| `build-backlinks.py` | Common Crawl + Moz + Bing Webmaster backlink pull |
| `build-backlinks-overview.py` | Aggregate referring domain analysis |
| `build-brand-mentions-log.py` | Track brand-name mentions across web. Drop in mentions → drop in app store branded search. |

### L. Competitive intel (call in REWRITE mode)
| Script | Purpose |
|--------|---------|
| `build-competitor-gaps.py` | Find keywords competitor ranks for but we don't |
| `build-reddit-scanner.py` | Pain phrases from Reddit threads about competitor apps |
| `build-reddit-rpm-tracker.py` | Reddit AdMob/IAP/eCPM crowd intel (Rule 4a complement) |
| `build-public-rpm-benchmarks.py` | Public RPM data scraped from PriceonomyX, Sensor Tower free posts, etc. |
| `build-content-ideas.py` | Content gap analysis vs competitors |
| `build-topic-cluster-report.py` | Topic cluster mapping for landing-page integration |

### M. Quality + compliance (call in REWRITE mode + before any push)
| Script | Purpose |
|--------|---------|
| `inspect-urls.py` | **Rule 0 — mandatory after schema/canonical/sitemap change.** Validates Rich Results eligibility. |
| `inspect-cwv.py` | Core Web Vitals snapshot for landing pages (affects organic discovery → ASO leading indicator) |
| `build-schema-validate.py` | JSON-LD schema validation |
| `build-static-schema.py` | Generate static Schema.org for landing pages |
| `build-fix-orphans.py` | Find orphan landing pages (no internal link) |

### N. Auth + plumbing (one-time setup)
| Script | Purpose |
|--------|---------|
| `build-search-console-auth.py` | GSC OAuth one-time |
| `build-analytics-auth.py` | GA4 OAuth one-time |
| `build-adsense-auth.py` | AdSense OAuth one-time |

---

## Installed Claude Skills — Invoke for Specific Subtasks

These are pre-built skills (not scripts). Invoke via Skill tool when the matching subtask appears in a `/aso-refresh` run.

| Skill | When to invoke during /aso-refresh |
|-------|------------------------------------|
| `aso-appstore-screenshots` | REWRITE mode, ONLY when the project does NOT have `automation_data/aso_screenshot_presets.json` (i.e., new app onboarding). For existing apps, prefer the toss-style composer per Rule P4.6 — it's deterministic, zero API cost, and the composer fixes are bug-tested. |
| `seo-dataforseo` | SIGNAL mode (Step 3 of skill) — pull live competitor SERP + keyword data when DataForSEO MCP extension is installed. Complements `build-keyword-volume.py`. |
| `seo-google` | SIGNAL mode — pull GSC field data (real impressions/clicks/CTR/position) + GA4 organic traffic. Most reliable leading indicator we have. |
| `seo-firecrawl` | REWRITE Step 7 (competitor universe) — full crawl of top competitor's landing pages to extract messaging + features list. |
| `seo-backlinks` | REWRITE — competitor authority signal. Use Moz/Common Crawl free data. |
| `seo-content` | REWRITE — E-E-A-T audit for full app description (Apple ≥4000 char + Google indexed). |
| `seo-image-gen` | REWRITE — fallback for feature graphic if `aso-openrouter-image-edit.py` not configured. |
| `seo-schema` | One-time per app — validate Schema.org for landing pages (different from app store). |
| `seo-page` | One-time per app — deep audit of the app's landing page on apps.teamzlab.com. |
| `competitive-ads-extractor` | REWRITE Step 7 — pull competitor ads from Facebook/LinkedIn ad libraries. Reveals messaging that converts. |
| `changelog-generator` | REWRITE Step 12 — auto-generate release notes from git commits (alternative to `aso-release-notes-gen.py`). |

---

## When to Add a Script to This Registry

A script qualifies if it:
1. Produces a signal that informs ASO decisions (keywords, competitor, monetization, behavior, visual)
2. Lives in `teamz-company-automation/py/` or `py/aso/`
3. Is documented (has `--help` or top docstring)

When a new script is added to the automation submodule:
1. Add it to the right table (A-N) in this file
2. Specify mode (SIGNAL / REWRITE / both / one-time / post)
3. Reference it from `claude-config/commands/aso-refresh.md` if it should auto-fire

---

## Audit Yourself

Quarterly: `ls teamz-company-automation/py/aso/*.py teamz-company-automation/py/aso/*.sh teamz-company-automation/py/build-*.py | wc -l` — compare against count in this registry. Diff = scripts the LLM doesn't know to call.
