# ASO Research Synthesis — 2026-06-03

**Sources:**
- Gemini Deep Research: cadence + free tools + 2025-2026 algo updates + indie case study → `gemini-deep-research-cadence-and-tools.md`
- ChatGPT Deep Research: methodology critique + competitor framework + ROI scoring + execution sequence → `chatgpt-deep-research-methodology-critique.pdf`

ChatGPT did NOT produce substantive ASO research — it produced a **research-methodology validation**. That is actually complementary: Gemini gives the WHAT, ChatGPT gives the HOW + RIGOR.

---

## CONVERGENT (both agree — high confidence to act on)

1. **Wait longer between metadata changes than indie devs typically do.** Gemini explicit: 4w iOS / 8w Android. ChatGPT implicit via "creative test is 90 days with up to 3 treatments" + "Apple description used for web engine search results — different rhythm than store search."
2. **Treat iOS and Android as different ASO problems.** Different fields, different limits, different indexing, different cadence. Both reject "one strategy, both stores."
3. **Competitor analysis must be tiered.** Don't lump direct + aspirational + low-end together. Gemini's "65-app dev" picks empty long-tail; ChatGPT formalizes the tiers in a table.
4. **Don't trust 2023 ASO advice.** Both flag the landscape shifted (Gemini: WWDC 2025 algorithm changes; ChatGPT: Apple/Play docs change locale counts + field constraints).
5. **Free tools exist beyond what I have.** Gemini names them concretely (Appfigures 1k/day, SplitMetrics popularity extension, AppFollow archiving trick); ChatGPT confirms `facundoolano/google-play-scraper` + `facundoolano/app-store-scraper` as the canonical baseline wrappers.

## DIVERGENT (each unique insight worth keeping)

**Gemini exclusive (data — act on it):**
- Appfigures **1,000 API requests/day free** — biggest free signal source I am not using
- SplitMetrics Chrome extension extracts exact 0-100 Apple Search Popularity Index
- Apple OCRs iOS screenshots since June 2025 — secondary keywords must go in screenshot graphics
- Keyword duplication across Title+Subtitle+Keywords field = active penalty (Ariel Michaeli, Appfigures CEO)
- Android Vitals (crash rate + 48h uninstall) actively demotes Play search ranking — retention IS ASO
- r/AppBusiness "65 apps / $4,200/mo" dev case study — long-tail empty-keyword strategy

**ChatGPT exclusive (structure — bake into the skill):**
- **Indexing splits 3 ways** — store-search relevance / page-conversion assets / web+deep-link indexing. Each verified separately.
- **Competitor universe by category × country × query context** — never just by category alone
- **ROI scoring weights:** 35% search visibility, 25% page conversion, 15% effort inverse, 15% data confidence, 10% regional leverage
- **"Assumed competitor universe" fallback** — when target list not locked, document the inference logic transparently on page 1 of the report
- **Tooling-risk requires:** maintenance recency + stars/forks + issue backlog + parser-breakage risk for each script
- **Execution sequence:** Scope lock → Mechanics review → Competitor build → Evidence capture → Review mining → Repo audit → Synthesis
- **Apple PPO treatments** can run 90 days with up to 3 variants — treat creative testing as PART of ASO, not a separate appendix
- **Data asymmetry:** Play exposes install bands publicly; iOS does not. Proxy iOS competitor scale via review volume + rating density + chart presence + asset sophistication

## CONTRADICTIONS (resolve explicitly)

- **Locale counts.** Gemini says "Apple 40 / Play 39." ChatGPT says do NOT hardcode — both stores currently list more. **Winner: ChatGPT.** Action: any script that targets "tier 1 locales" must query the live SDK list at runtime, not a hardcoded array.

---

## CADENCE MEMO UPDATE REQUIRED

Current `aso_cadence.md` says: 14-day signal pull / 30-day rewrite floor.

**Recommended revision based on convergent research:**

| Action | iOS | Android | Source |
|--------|-----|---------|--------|
| Signal-only pull (no metadata edit) | every 14 days | every 14 days | unchanged |
| Title/subtitle rewrite floor | **28 days** (was 30) | **56 days** (was 30) | AppTweak |
| Promo text refresh | weekly OK | weekly OK | unchanged |
| Screenshot refresh | flag as higher friction — requires NEW BUILD on iOS | weekly OK on Play | ChatGPT page 4 |
| Apple PPO A/B variant | 90-day window, up to 3 treatments | n/a | ChatGPT page 4 |
| Play Store Listing Experiment | n/a | run continuously, free | unchanged |

**Why Android is 8 weeks not 4:** Google Play uses NLP indexation that smooths over a much longer window than Apple. AppTweak data: Android keyword positions don't stabilize for 6-8 weeks.

---

## CHANGES TO PROPOSED `/aso-refresh` SKILL

Original 15-step plan was good. Research adds these:

### Step additions / refinements
- **Step 0 (new):** Scope lock per ChatGPT. Pick category + country + query context BEFORE running anything. Output: `scope.lock.json`. Without this, every downstream signal is noisy.
- **Step 4a (new):** Run `aso-screenshot-ocr-check.py` — extract OCR text from current iOS screenshots, flag if no secondary keywords present. (Apple June 2025 update.)
- **Step 6 (modified):** Add Appfigures API pull → `aso-appfigures-pull.py` (new script needed). Replaces ~70% of guesswork. Budget 200-300 of the 1k daily credits per app refresh.
- **Step 6 (modified):** Add SplitMetrics popularity extension export → manual screenshot during signal pull, store in `automation_data/<app>/asa_popularity_<date>.png`. Optional but high-value.
- **Step 7 (modified):** Competitor pull uses ChatGPT's 5-tier framework, not flat top-10. Categories: direct / aspirational / low-end / adjacent-substitute / regional-variant. Each tier gets distinct extract logic.
- **Step 8 (new sub-step):** Run `aso-keyword-cannibalize-check.py` — diff keywords across all 5 publisher apps, flag overlaps that hurt cross-app ranking. (Ariel Michaeli "ultimate sin.")
- **Step 11 (modified):** If mode == SIGNAL_ONLY, output includes ChatGPT's ROI weight scoring (35/25/15/15/10) for each candidate keyword. Not just winnability binary.
- **Step 12 (modified, FULL_REWRITE only):** Cadence gate uses 28/56 split — iOS-only rewrite path can fire at day 28 if iOS variant has stabilized; Android waits to 56. Block the wrong-platform path.
- **Step 13 (modified):** Preflight adds duplicate-keyword check (Title vs Subtitle vs Keywords field — iOS only).
- **Step 14 (modified):** Localize step queries live SDK locale list, NOT a hardcoded "tier1" array. Per ChatGPT: locale counts shift.
- **Step 15 (modified):** Final report begins with executive summary answering 4 questions per ChatGPT: what was verified, what changed vs prior run, which competitor matters most, top ROI actions.

### New scripts needed
1. `aso-appfigures-pull.py` — Appfigures API client + daily-credit budget tracker
2. `aso-screenshot-ocr-check.py` — Tesseract or Vision API OCR on iOS screenshots + keyword presence check
3. `aso-keyword-cannibalize-check.py` — diff merged_keywords.csv across all Teamz Lab apps
4. `aso-asa-popularity-import.py` — ingest SplitMetrics popularity exports (manual screenshot OR CSV from extension)
5. `aso-roi-score.py` — apply ChatGPT's 35/25/15/15/10 weights to keyword candidates
6. `aso-locale-discover.py` — query Apple + Play live locale lists at runtime, write to `data/active_locales.json`

### Dead/risky scripts to flag (per ChatGPT page 3)
- `google-play-scraper` (facundoolano) — maintainer says no longer actively maintained. **Decision needed:** keep using until it breaks vs switch to alternative. Today: keep using, set monitoring alert if scrape returns empty.
- Apple iTunes Search API — official docs last updated 2017. Wrapper still works but verify quarterly that output matches live App Store HTML.

---

## DECISIONS USER NEEDS TO MAKE

1. **Accept platform-split cadence (28d iOS / 56d Android)?** Yes = update `aso_cadence.md`. No = stick with 30/30.
2. **Build the 6 new scripts now or after first real `/aso-refresh` dry-run?** Recommendation: dry-run first with existing 28 scripts + manual SplitMetrics export, identify which new script unlocks most value, build that one first.
3. **Which app gets the first FULL_REWRITE run?** Per scoring formula, likely DeviceGPT (highest revenue) OR Toss/Toolz (+650% iOS WoW, needs forensic post-mortem to lock cause). Recommend Toss/Toolz — unrepeatable spike will fade if cause unknown.
4. **Build `/aso-refresh` skill scaffold today?** Or wait for more iteration.

---

## TRACKING

This file is the canonical synthesis. Future ASO sessions MUST read this before proposing changes. Linked from:
- `/Users/mdgolamkibriaemon/.claude/projects/-Users-mdgolamkibriaemon-Projects-Teamz-Lab-Projects-teamz-projects-teamz-lab-generic-landing-pages/memory/aso_cadence.md`
- (TBD) `/Users/mdgolamkibriaemon/.claude/commands/aso-refresh.md` when scaffolded
