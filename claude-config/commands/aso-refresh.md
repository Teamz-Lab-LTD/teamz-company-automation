---
description: Entry point for ALL ASO work on a Teamz Lab app. Decides SIGNAL_ONLY vs FULL_REWRITE from the cadence rule, then DELEGATES to the existing aso-store-blitz.py (or aso-master-precheck.sh for signal-only). Never duplicates orchestration. Overlays 2026-06-03 research insights (Appfigures, ASA popularity, screenshot OCR, cannibalization).
allowed-tools: Bash, Read, Write, Edit, WebFetch
---

# /aso-refresh <app-slug> [--force-rewrite-ios|--force-rewrite-android|--dry-run]

**MANDATORY ENTRY POINT for any ASO task.** Never run ASO scripts individually. Never propose title/keyword/pillar from memory. This skill routes to the canonical orchestrator + applies cadence gate + adds research overlays.

## This skill does NOT re-orchestrate anything

The heavy lifting lives in pre-existing scripts:
- `py/aso/aso-store-blitz.py` — **canonical full-pipeline orchestrator** (preflight → keyword-volume → competitors → AI edit → compose → pad-resize → feature-graphic → localize → play-push → apple-version → apple-metadata → apple-screenshots → apple-submit). 13 steps, each `--skip-<name>` or `--only <step>`.
- `py/aso/aso-store-release.py` — older orchestrator, kept for backwards-compat. New work uses `aso-store-blitz.py`.
- `py/aso/aso-master-precheck.sh` — multi-source signal pull (Play bulk reports, Trends, competitor reviews, Firebase funnels, autocomplete seeds). Used in SIGNAL_ONLY mode.

This skill ONLY adds:
1. **Cadence gate** (`claude-config/memory/aso_cadence.md` — 14d signal / 28d iOS rewrite / 56d Android rewrite)
2. **Research overlays** (`aso-research/<date>/SYNTHESIS.md` — Appfigures, ASA popularity, screenshot OCR, cross-app cannibalization)
3. **Stop-rules RULE-001 winnability table** before any recommendation

## Pre-flight reads (LLM must do this BEFORE running anything)

1. `~/.claude/projects/<encoded-cwd>/memory/aso_cadence.md` — platform-split cadence (symlink → `claude-config/memory/aso_cadence.md`)
2. `teamz-company-automation/aso-research/<latest-date>/SYNTHESIS.md` — current research insights
3. `teamz-company-automation/CLAUDE.md` — Rule 0–6 + Phase 1–8 playbook
4. `teamz-company-automation/py/aso/aso-store-blitz.py` header docstring — confirm step list current
5. **`teamz-company-automation/claude-config/aso-script-registry.md`** — **MANDATORY READ.** Exhaustive list of every ASO + leading-indicator SEO script + installed skill, with WHEN to call each. If you proceed without reading this file you WILL skip scripts and produce incomplete recommendations. The cost: months of script-building that goes unused per `/aso-refresh` run.

## Flow

### Step 1 — Resolve app + decide cadence mode

```bash
APP_SLUG="$1"
case "$APP_SLUG" in
  devicegpt|debugger) PROJECT_DIR="$HOME/Projects/Teamz Lab Projects/teamz-projects/debugger";;
  toss|toolz|toss_app) PROJECT_DIR="$HOME/Projects/Teamz Lab Projects/teamz-projects/toss_app";;
  top3picks|top_3_picks) PROJECT_DIR="$HOME/Projects/Teamz Lab Projects/teamz-projects/top_3_picks";;
  no-trace-chat|ntc) PROJECT_DIR="$HOME/Projects/Teamz Lab Projects/teamz-projects/no-trace-code-chat";;
  zoyiai) PROJECT_DIR="$HOME/Projects/Teamz Lab Projects/teamz-projects/zoyiai";;
  *) echo "Unknown slug — update skill switch"; exit 1;;
esac

LAST_IOS=$(cat "$PROJECT_DIR/automation_data/.last_refresh.ios_rewrite" 2>/dev/null || echo 0)
LAST_ANDROID=$(cat "$PROJECT_DIR/automation_data/.last_refresh.android_rewrite" 2>/dev/null || echo 0)
NOW=$(date +%s)
IOS_DAYS=$(( (NOW - LAST_IOS) / 86400 ))
ANDROID_DAYS=$(( (NOW - LAST_ANDROID) / 86400 ))
[ $IOS_DAYS -ge 28 ] && MODE_IOS="REWRITE" || MODE_IOS="SIGNAL"
[ $ANDROID_DAYS -ge 56 ] && MODE_ANDROID="REWRITE" || MODE_ANDROID="SIGNAL"
echo "Mode: iOS=$MODE_IOS (day $IOS_DAYS/28), Android=$MODE_ANDROID (day $ANDROID_DAYS/56)"
```

If user passed `--force-rewrite-ios` or `--force-rewrite-android`: override, but require a one-line reason matching one of the 4 break conditions in `aso_cadence.md`.

### Step 2 — Drift check (`feedback_play_console_drift_check.md`)

```bash
cd "$PROJECT_DIR"
python3 teamz-company-automation/py/build-play-console.py listing-pull
```

If drift detected: STOP. User reconciles in Play Console UI first. Do not auto-fix.

### Step 3 — Route to orchestrator (delegate, do not duplicate)

**Both modes SIGNAL** — pull data only, no metadata writes:
```bash
TEAMZ_PLAY_DEV_ACCOUNT_ID=<dev-id> \
TEAMZ_PLAY_SERVICE_ACCOUNT_JSON=$HOME/.config/teamzlab/play-console-service-account.json \
teamz-company-automation/py/aso/aso-master-precheck.sh \
  --package "$PKG" \
  --keywords-file automation_data/seed_keywords.txt \
  --competitors-play "$(jq -r '.competitors[]' automation_data/aso-competitors.json | head -3 | tr '\n' ',')" \
  --app-slug "$APP_SLUG" \
  --months 3 \
  --out automation_data/master_$(date +%Y%m%d).json
```

**Either mode REWRITE** — invoke the canonical full pipeline:
```bash
cd "$PROJECT_DIR"
# Dry-run first to inspect resolved plan
python3 teamz-company-automation/py/aso/aso-store-blitz.py --dry-run

# Then full run (auto-submit is OFF by default — keep it OFF)
python3 teamz-company-automation/py/aso/aso-store-blitz.py

# Or single-step inspection when needed:
# python3 teamz-company-automation/py/aso/aso-store-blitz.py --only keyword-volume
# Available step names: preflight, keyword-volume, competitors, ai-edit, compose,
#   pad-resize, feature-graphic, localize, play-push, apple-version,
#   apple-metadata, apple-screenshots, apple-submit
```

If iOS-only rewrite: `--skip play-push`. If Android-only rewrite: `--skip apple-version --skip apple-metadata --skip apple-screenshots --skip apple-submit`.

### Step 3a — Cross-reference registry to catch scripts aso-store-blitz.py skips

Read `claude-config/aso-script-registry.md` Section A-N. For each script marked "always-call" in the relevant mode, verify aso-store-blitz.py either (a) called it, or (b) you call it as a sidecar. Missed scripts to typically backfill:

**SIGNAL mode sidecars (always run alongside aso-master-precheck.sh):**
- `build-keyword-volume.py` (Bing + Trends + autocomplete + Google result counts)
- `build-keyword-intel.py` (intent classification + question keywords)
- `build-rank-tracker.py` (weekly rank tracking — leading indicator)
- `build-gsc-anomalies.py` (sudden CTR/position drops)
- `build-brand-mentions-log.py` (branded-search leading indicator)
- `aso-velocity.py` (Play Reporting + ASC Sales & Trends history)
- `aso-track.py --record` (lock today's positions for 14-day delta)
- **Skills:** `seo-dataforseo` (if DataForSEO MCP installed), `seo-google` (GSC field data)

**REWRITE mode sidecars (always run alongside aso-store-blitz.py):**
- `build-competitor-gaps.py` (keywords competitor ranks for, we don't)
- `build-reddit-scanner.py` (pain phrases from Reddit competitor threads)
- `build-reddit-rpm-tracker.py` (Rule 4a complement)
- `build-content-ideas.py` (content gap)
- `build-topic-cluster-report.py` (landing page integration)
- `inspect-urls.py` (Rule 0 — schema/canonical validation)
- `aso-copy-helper.py` (generate Play paste files)
- `aso-priority-export.py` (Rule P5.7 — in-app list must mirror store positioning)
- `aso-tablet-from-phone.py` (Universal-app submit blocker prevention)
- `aso-experiments.py add` (register A/B variants)
- **Skills:** `seo-firecrawl` (competitor landing page crawl), `seo-backlinks` (competitor authority), `competitive-ads-extractor` (FB/LinkedIn ad teardown), `seo-content` (E-E-A-T on full description)

**Both modes (idempotent — call always):**
- `admob.py report --days 7` (live revenue context check)
- `build-youtube-keywords.py` IF any video/Shorts/Reels asset planned (Rule 6 — YT intent ≠ Google intent)

If you skip ANY of the above, you produce incomplete data. The registry exists so the LLM does not have to remember which scripts to call.

### Step 4 — Research overlays (NEW signals NOT yet in aso-store-blitz.py)

These were added by 2026-06-03 Gemini + ChatGPT Deep Research. Today they run as manual sidecars; future PR folds them into `aso-store-blitz.py` once dry-runs confirm ROI.

**4a Appfigures** (1k free API/day): sign up at appfigures.com → pull competitor ranks → save CSV to `automation_data/appfigures_$(date +%Y%m%d).csv`. ~250 credits per app. Future script: `aso-appfigures-pull.py`.

**4b SplitMetrics ASA popularity index** (exact 0-100, free Chrome extension): install extension → open Apple Search Ads → screenshot/CSV export → `automation_data/asa_popularity_$(date +%Y%m%d).{png,csv}`. Future script: `aso-asa-popularity-import.py`.

**4c Screenshot OCR check** (Apple OCRs since June 2025):
```bash
which tesseract >/dev/null || brew install tesseract
for s in "$PROJECT_DIR"/fastlane/screenshots/en-US/*.png; do
  echo "$(basename "$s"): $(tesseract "$s" - 2>/dev/null | tr '\n' ' ')"
done > "$PROJECT_DIR/automation_data/screenshot_ocr_$(date +%Y%m%d).txt"
```
Manually verify each line contains ≥1 secondary keyword. Apps without keyword-laden screenshots leave money on the table.

**4d Cross-app keyword cannibalization** (Ariel Michaeli "ultimate sin"):
```bash
for csv in "$HOME/Projects/Teamz Lab Projects/teamz-projects"/*/automation_data/keywords_merged.csv; do
  [ -f "$csv" ] && awk -F',' 'NR>1 {print $1}' "$csv" | sort -u
done | sort | uniq -d > "$PROJECT_DIR/automation_data/cannibalize_$(date +%Y%m%d).txt"
```
Any keyword duplicated across 2+ teamzlab apps = cannibalization risk. Decide canonical owner (highest revenue keeps; others must pivot).

### Step 5 — Winnability table (MANDATORY per stop-rules RULE-001)

Before ANY title/keyword/pillar recommendation, output:

```
| Keyword | Top competitor | Reviews | Installs | Winnable? |
|---------|----------------|---------|----------|-----------|
```

Winnable for <10K-install apps (per `feedback_aso_winnability_first.md`): competitor reviews <50K AND bottom-half category installs. Skip everything else.

### Step 6 — Final report (ChatGPT 2026-06-03 methodology)

1. Executive summary: what verified, what changed vs last run, which competitor matters most, top 3 ROI actions
2. Mode (per platform) + cadence days elapsed
3. Winnability table
4. Rank deltas vs last refresh
5. Voice-of-user top 5 pain phrases (from `aso-reviews.py`)
6. Monetization context (Rule 4a — from `aso-admob-rpm-benchmarks.py`)
7. Research overlay findings (Step 4 results)
8. IF REWRITE: proposed metadata DIFF + push command (NEVER auto-push)
9. Citations: every file/script read, with paths

### Step 7 — Update cadence timestamps + commit

```bash
date +%s > "$PROJECT_DIR/automation_data/.last_refresh.signal"
[ "$IOS_PUSHED" = "1" ] && date +%s > "$PROJECT_DIR/automation_data/.last_refresh.ios_rewrite"
[ "$ANDROID_PUSHED" = "1" ] && date +%s > "$PROJECT_DIR/automation_data/.last_refresh.android_rewrite"
cd "$PROJECT_DIR" && git add automation_data/ && git commit -m "aso($APP_SLUG): refresh $(date +%Y-%m-%d) mode=$MODE_IOS+$MODE_ANDROID"
```

## Refusal conditions

- Unknown app slug
- Drift detected and not reconciled (Step 2)
- Preflight gate fails in aso-store-blitz.py
- User requests keyword/title pick WITHOUT winnability table being printed first
- Cadence floor not reached AND no `--force-rewrite-*` AND no documented break condition

## Multi-app priority (2-hour slots)

Score = `revenue × 0.5 + install_velocity × 0.3 + days_since_refresh × 0.2`. Highest wins. See `claude-config/memory/aso_cadence.md`.

## Citation requirement

LLM MUST mention in the final report:
- This skill (`claude-config/commands/aso-refresh.md`)
- Which orchestrator was actually called (`aso-store-blitz.py` or `aso-master-precheck.sh`)
- Cadence rule consulted (`claude-config/memory/aso_cadence.md`)
- Research synthesis read (`aso-research/<date>/SYNTHESIS.md`)

So user can audit which signals actually fired vs were skipped.
