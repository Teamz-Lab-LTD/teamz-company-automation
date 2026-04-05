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
| **Full store release (22 steps)** | `py/aso/aso-store-release.py` | **START HERE — orchestrates everything** |
| **Copy-paste helper HTML** | `py/aso/aso-copy-helper.py` | For manual paste when API can't commit (draft apps) |

### ASO Workflow (must follow this order)

```
0. py/aso/aso-preflight.py --pre                          → VALIDATE before starting (blocks if data missing)
1. py/aso/aso-keywords.py --suggest/--expand/--trending   → discover keywords
2. py/build-keyword-volume.py "kw1" "kw2" ...            → get REAL volume data (Bing + Trends + autocomplete)
3. py/aso/aso-competitors.py --find/--matrix               → competitive landscape
4. py/aso/aso-keyword-pipeline.py                          → produce scored CSVs (integrates step 2 data)
5. py/aso/aso-metadata.py --audit/--optimize               → audit current listing
6. Google Trends (browser) — compare top 5 keywords        → confirm relative demand (script can't do this — 429 rate limited)
7. THEN write the listing using data from steps 1-6
8. py/aso/aso-preflight.py --post                          → VALIDATE after writing (blocks if listing has issues)
```

**⚠️ NEVER skip step 0 or step 8. The preflight script catches fabricated data, missing volume estimation, and listing issues.**
**⚠️ NEVER skip step 2 (volume estimation). Without it, you cannot determine which keywords have actual search demand.**
**⚠️ Step 6 (Google Trends) requires browser — the API is 429 rate-limited. Ask the user to do this manually.**

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
| **Schema validation** | `py/build-schema-validate.py` |
| **Search Console anomalies** | `py/build-gsc-anomalies.py` |
| **Topic cluster report** | `py/build-topic-cluster-report.py` |
| **Request indexing** | `py/build-request-indexing.py` |

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

## Anti-Patterns (NEVER do these)

| ❌ DON'T | ✅ DO |
|---|---|
| Invent keyword scores or search volumes | Run `build-keyword-volume.py` for real data |
| Manually create `master_keywords.csv` | Run `aso-keyword-pipeline.py` to generate it |
| Guess which keywords have demand | Run `build-keyword-volume.py` — it checks Google Trends, Bing API, autocomplete rank, and GSC |
| Skip competitor analysis | Run `aso-competitors.py --find` + `--matrix` + `--keywords` |
| Write store listings without data | Follow the ASO Workflow (6 steps above) |
| Assume a tool doesn't exist | `ls packages/team_mvp_kit/teamz-company-automation/py/` first |
| Suggest Google Trends manually | `build-keyword-volume.py` already integrates Google Trends |
| Suggest paid tools when free ones exist | Check this registry — 48 scripts cover most needs |

---

## Script Count by Category

- **ASO**: 9 scripts (keyword research → competitor analysis → metadata → reviews → tracking)
- **SEO**: 18 scripts (audit → keywords → volume → competitors → SERP → content → indexing)
- **Auth**: 4 scripts (GSC, GA4, Google Ads, AdSense)
- **Content**: 5 scripts (ideas, multilang, OG images, subtitles, programmatic SEO)
- **Monitoring**: 5 scripts (brand mentions, SERP features, GSC anomalies, uptime)
- **QA**: 5 scripts (runtime test, schema layout, server, test suite, batch fix)
- **Config**: 1 script

**Total: 48 Python scripts. All standard library (no pip install needed).**
