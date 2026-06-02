---
name: aso-cadence
description: "Locked ASO refresh cadence for indie apps under 10K installs — 14-day signal pull / 30-day rewrite floor. Stops flip-flop between \"2-4 weeks\" and \"quarterly\"."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 183a9d8e-fc01-4962-bbd4-50a794d564ca
---

**Rule (locked 2026-06-03, REVISED same day with Gemini+ChatGPT Deep Research):**

| Action | iOS | Android |
|--------|-----|---------|
| Signal-only pull (no metadata edit) | every 14 days | every 14 days |
| Title/subtitle/keywords rewrite floor | **28 days** | **56 days** |
| Promo text refresh | weekly OK (direct ASC API — fastlane edit_live broken) | n/a |
| Short description (Play) | n/a | 56 days |
| Long description refresh | as needed (no floor — Apple doesn't index, Google does) | weekly OK (Google indexes it; treat like SEO content) |
| Screenshot refresh | HIGH FRICTION — requires NEW BUILD | weekly OK on Play Store Listing Experiments |
| Apple PPO A/B variant | 90-day window, up to 3 treatments per variant | n/a |
| Play Store Listing Experiment | n/a | run continuously, free |

**Why iOS 28d / Android 56d (NOT a flat 30d):** Apple keyword ranks stabilize ~4 weeks (AppTweak). Google Play NLP indexation smooths over 6-8 weeks. Faster = destroyed A/B signal + algorithm reset penalty. Source: `teamz-company-automation/aso-research/2026-06-03/SYNTHESIS.md`.

**Why:**
- Apple search index re-crawls metadata in 24-72h after new build, but ranking confidence intervals stabilize over ~10-14 days (AppTweak keyword-rank smoothing window).
- Google Play uses ~7-day rolling install/retention signal (Google Play ASO PDF 2023).
- Rewriting faster than 14 days destroys your own A/B signal — you cannot attribute movement.
- Phiture ASO Stack + Sylvain Gauchet (Mobile Dev Memo) both recommend 2-week observation per change for apps under 10K installs because daily install variance is wider than metadata-driven delta.
- Quarterly = too slow (competitors ship every 2-3 weeks, Apple Search Ads popularity index shifts monthly).
- Weekly = too fast at indie scale (no statistical signal).

**How to apply:**
- Day 0, 14, 28, 42, 56... → run `/aso-refresh <app-slug>` in SIGNAL_ONLY mode for every app. ~15min per app. Pull stats + rank deltas + competitor changes. Generate winnability table. NO metadata edit.
- iOS rewrite: day 28, 56, 84... → pick ONE app whose iOS variant moved most. FULL_REWRITE iOS only. Push. Don't touch iOS for 28 more days.
- Android rewrite: day 56, 112, 168... → same logic but Android-only. Slower cadence because NLP indexation takes 6-8 weeks.
- Break the floor ONLY when: (1) competitor ships major title/subtitle change → counter within 7 days, (2) install velocity drops >40% WoW for unknown reason, (3) genuinely new feature worth subtitle slot, (4) Apple/Google rejects listing.

**Multi-app priority when only 2 hours available:** score = `revenue * 0.5 + install_velocity * 0.3 + days_since_last_refresh * 0.2`. Highest score wins the slot today.

**Benchmarks cited (for skeptics):**
- AppTweak: 10-14 day keyword rank smoothing window
- Phiture ASO Stack: 2-week minimum observation per metadata change
- Google Play ASO PDF (2023): 7-day rolling install/retention signal
- Apple Search Ads popularity index: refreshed roughly monthly
- Mobile Dev Memo (Sylvain Gauchet): solo-dev cadence 2-4 weeks
- Sensor Tower: keyword volatility 14-21 days for mid-tail

When in doubt, this rule wins over any prior session's recommendation.
