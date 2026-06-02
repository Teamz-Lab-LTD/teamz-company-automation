# Gemini Deep Research — ASO Cadence + Free Tools (2026-06-03)

**Source:** Gemini Advanced Deep Research, prompted by `aso-orchestration-audit` workflow output.
**Purpose:** Real cadence data + free tool inventory + 2025-2026 algorithm updates + indie portfolio case study.

---

## 1. ASO Refresh Cadence for Sub-10K-Install Apps

Biggest indie mistake: treating ASO as high-frequency trading. Low install volume → statistical significance takes much longer.

- **AppTweak (Algorithm Timeline):**
  - iOS: *"keyword rankings stabilize around 4 weeks after a new build is uploaded."*
  - Android: *"6 to 8 weeks before updating metadata on Android. This timeframe ensures you have a stable dataset."*
  - Source: https://www.apptweak.com/en/aso-blog/how-often-should-you-update-your-app-store-metadata
- **Sensor Tower (Industry Benchmark):** Top iOS apps average ~30 days between updates (mostly bug responses, not pure keyword refreshes). Source: https://sensortower.com/blog/25-top-ios-apps-and-their-version-update-frequencies
- **Phiture (Signal-Led Growth 2026):** Advocates "high-volume, high-cadence creative tests" — but explicitly for high-paid-UA teams, NOT indie. Source: https://phiture.com/mobilegrowthstack/product-led-growth-mobile-signal-led-growth/
- **Confidence intervals:** Google Play A/B requires 95% confidence. Apps <10K installs don't have daily traffic for 1-2% conversion shifts → set MDE to 5-6% → wait 4+ weeks. Refreshing before threshold = destroyed A/B signal + algorithm reset penalty.

### Conflict Flag
- Phiture says "high-cadence creative testing" — assumes massive paid UA.
- AppTweak says wait 4-8 weeks for rankings to stabilize.
- **For indie sub-10K installs: AppTweak wins.** Phiture's advice does not apply.

### Final cadence rule (Gemini's verdict)
**Wait 4 weeks iOS / 8 weeks Android before touching metadata.**

---

## 2. Multi-App Portfolio Prioritization

### Real Case Study — r/AppBusiness "65 Apps" Solo Dev (early 2026)
- 65 apps, ~$4,200/mo solo
- Strategy: *"The 'Boring Keyword' Hunt: I look for highly specific, long-tail keywords that have decent search volume but terrible existing apps. Think 'PDF compressor for X'... Pure ASO: I spend 80% of my time optimizing the title, subtitle, and screenshots. That's my only marketing. I publish it, maybe tweak the keywords once a month, and otherwise forget about it."*
- Source: https://www.reddit.com/r/AppBusiness/comments/1ro3n7c/i_built_65_boring_apps_none_of_them_went_viral/

### When to Freeze an App
- Capture #1–#3 rank for highly specific long-tail keyword (e.g., paycheck calc for specific geo) → freeze. Metadata changes carry more risk than reward.

### Scoring Formula (build as Python cron)
```
Priority Score = (30-Day Revenue) × (7-Day Install Velocity) × (Days Since Last Metadata Update)
```
- If app has 45+ days no update AND install velocity climbing (like Toss/Toolz +650% WoW) → score spikes → investigate WHY + double down on converting keywords.

---

## 3. Free Signal Sources Currently Missing From My Stack

### Appfigures API (HOLY GRAIL for Python devs)
- **1,000 API requests/day free**
- Pull Product metadata (2 credits), Ratings (3), Ranks (5), ASO data (5)
- Source: https://help.appfigures.com/en/article/appfigures-api-access-limits-and-add-ons-1seiibo/
- **Action:** Add `aso-appfigures-pull.py` script to automation stack.

### SplitMetrics Apple Search Ads Popularity Chrome Extension
- Apple ASA native UI only shows 1-5 blue dots.
- SplitMetrics free Chrome extension extracts the exact **0-100 Search Popularity Index** into ASA dashboard.
- Examples: popularity 60 = ~10k daily impressions; 82 = ~40k.
- Source: https://splitmetrics.com/blog/apple-search-popularity-index/
- **Action:** Install extension + add screenshot-export step to `/aso-refresh` workflow.

### AppFollow Free Tier
- Tracks 2 apps, 1,000 keywords, 10 competitors. Catch: 7-day history only.
- **Play:** Python script scrapes free tier every 5 days → builds unlimited historical DB locally.
- Source: https://www.g2.com/products/appfollow/pricing
- **Action:** Add `aso-appfollow-archiver.py` cron.

### Google Play Console "Search Appearance"
- Restrictive for sub-10K apps: groups low-volume keywords into "Other" (privacy threshold).
- Signal only on terms driving 50+ organic installs/month.
- Realistic for established apps, not new launches.

---

## 4. 2025-2026 Algorithm Updates (CRITICAL — outdated advice will get you penalized)

### Screenshot Caption Indexing (Apple, June 2025)
- Apple OCRs iOS screenshots + indexes text as keywords.
- Indie devs still use decorative text ("Welcome to the app!").
- **Must put secondary keywords directly into screenshot graphics.**
- Source: https://digitalseoland.com/blog/aso-app-ranking-strategies/

### Keyword Stuffing = Active Penalty (WWDC 2025)
- Apple introduced AI-generated App Store Tags.
- Both stores use semantic NLP models.
- *"Keyword stuffing doesn't just fail – it signals low quality to the algorithm."*

### Duplicating Keywords (Ariel Michaeli, Appfigures CEO)
- *"Ultimate sin of ASO."*
- Never put a word in iOS Keyword field if it already exists in Title or Subtitle. Wastes space + confuses algorithm.
- Source: https://subclub.com/episode/maximizing-organic-growth-with-app-store-optimization-ariel-michaeli-appfigures

### Retention = ASO Metric (Google Play 2026)
- Android Vitals actively suppresses search rankings if crash rate high OR uninstall within 48h.
- Download is NO LONGER the end of the ASO funnel. It's the beginning.

---

## 5. The TL;DR Rule

> Wait 4 weeks on iOS and 8 weeks on Android before touching your metadata. Use Python to bleed Appfigures API of its 1,000 daily free calls. Put your secondary long-tail keywords directly into your iOS screenshot graphics.

---

## Convergent Insights vs ChatGPT Companion Doc

| Topic | Gemini | ChatGPT |
|-------|--------|---------|
| Cadence | 4w iOS / 8w Android (decisive) | "verify at execution time" (validation lens) |
| Locale counts | Says "40 Apple / 39 Play" | Warns against hardcoding — both change |
| Indexing | Not split clearly | **Splits into store-search / web-search / deep-link** ← Gemini missed this |
| Tooling | Mentions google-play-scraper generically | **Names exact repo: facundoolano/google-play-scraper** + warns maintainer marked it unmaintained |
| Competitor universe | Implicit | **Explicit 5-tier framework**: direct/aspirational/low-end/adjacent/regional |
| ROI scoring | None | **Proposed weights**: 35 visibility / 25 conversion / 15 effort / 15 confidence / 10 regional |
| Indie case study | r/AppBusiness "65 apps" | None |
| Free tools | Appfigures + SplitMetrics + AppFollow concrete | None |
| 2025/2026 algo updates | Apple OCR screenshots June 2025 + WWDC25 Tags + Retention as ASO | None |

**Verdict:** Gemini = data. ChatGPT = structure. Use both.
