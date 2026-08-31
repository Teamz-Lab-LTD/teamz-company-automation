# Growth Digest — 2026-08-31

Window: **2026-08-21 → 2026-08-28** (7d) vs the 7d before it.

| property | clicks | vs prev | impressions | CTR | avg pos | nightly |
|---|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | **18,584** | flat | 666,067 | 2.79% | 13.4 | ⚠️ ran, but GIT PUSH FAILED (5h ago) — commits are local-only and the remote backup is not receiving them; check `git ls-remote origin` |
| https://apps.teamzlab.com/ | **20** | +82% | 1,775 | 1.13% | 24.5 | ⚠️ ran, agent SKIPPED: dirty-tree (5h ago) |
| sc-domain:goalkit.teamzlab.com | **48** | -23% | 488 | 9.84% | 12.9 | ⚠️ PREFLIGHT FAILED: dns-failed-during-run (4h ago) |
| https://learn.teamzlab.com/ | **13** | -38% | 2,317 | 0.56% | 8.2 | ⚠️ ran, but DEPLOY FAILED (5h ago) — serving the old build |
| https://teamzlab.com/ | **76** | -7% | 856 | 8.88% | 5.8 | ok (4h ago) |
| https://tekko.teamzlab.com/ | **2** | new | 38 | 5.26% | 62.0 | ✅ ran (2h ago) — deploy exited 0 but was NOT verified against the live site |

## AI channel (ChatGPT / Perplexity / Claude / Gemini)
| property | AI sessions | vs prev | AI revenue | $/1k sessions | organic $/1k |
|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | 822 | -6% | $7.41 | $9.02 | $4.29 |
| https://apps.teamzlab.com/ | 17 | +6% | $0.00 | $0.00 | $0.00 |
| sc-domain:goalkit.teamzlab.com | 76 | +90% | $0.00 | $0.00 | $0.00 |
| https://learn.teamzlab.com/ | 22 | flat | $0.00 | $0.00 | $0.00 |
| https://teamzlab.com/ | 0 | — | $0.00 | $0.00 | $0.00 |
| https://tekko.teamzlab.com/ | 0 | — | $0.00 | $0.00 | $0.00 |

### tool.teamzlab.com — AI Assistant sessions, last 6 weeks
| week | sessions | revenue |
|---|---|---|
| 30 | 544 | $7.24 |
| 31 | 385 | $3.05 |
| 32 | 426 | $3.37 |
| 33 | 699 | $3.22 |
| 34 | 887 | $6.80 |
| 35 | 586 | $5.82 |

## Apps property, split by business

| business | clicks 28d | vs prior 28d | impressions | CTR |
|---|---|---|---|---|
| app | 36 | +20% | 1316 | 2.74% |
| SaaS | 0 | too small to judge (<25) | 21 | 0.00% |
| service | 0 | too small to judge (<25) | 1840 | 0.00% |
| blog | 15 | too small to judge (<25) | 2616 | 0.57% |
| home | 2 | too small to judge (<25) | 68 | 2.94% |
| other | 1 | too small to judge (<25) | 383 | 0.26% |

🔔 **service: 1840 impressions, 0 click(s) in 28 days.** Google is showing these pages and nobody is reaching them — that is a ranking-depth problem, not a copy problem. Check position before rewriting anything.

## Apps — are the mobile apps earning?

**£9/month**, owner-stated. Compare: tools ≈ £140/month.

_Per-app split unavailable (AdMob not connected), so which of the apps carry this is unknown. Run `python3 py/admob.py auth` when the split matters._

## Money — is revenue holding?

### AdSense daily — complete days only

Account reports in **Europe/London**. Newest COMPLETE day on file: **2026-08-29**.

| date | earnings (GBP) | pageviews |
|---|---|---|
| 2026-08-23 | 10.69 | 3084 |
| 2026-08-24 | 8.09 | 2965 |
| 2026-08-25 | 7.94 | 2894 |
| 2026-08-26 | 8.13 | 2864 |
| 2026-08-27 | 8.56 | 3009 |
| 2026-08-28 | 6.80 | 3021 |
| 2026-08-29 | 5.80 | 2335 |

Newest complete day is **-37%** vs the 7-day mean before it.

**Still running (NOT counted above):** 2026-08-30 = GBP 6.73 (2126 pageviews). This is a part-day total and always reads low.

The account clock is Europe/London, so a Bangladesh late evening or early morning is still the PREVIOUS AdSense day — a fresh-looking 'today' is usually an hour or two of data, not a drop.

_Checked 2026-08-30T23:55:16 (4h ago). Recent = 7d ending D-2 vs the 3 weeks before it; GA4 per-page revenue needs ~48h to settle._

### teamzlab-tools — $13.1/day now vs $12.35/day baseline (+6.0%)
_Watching 16 pages = **101.1% of revenue**._

| top earner | $/day | share |
|---|---|---|
| `/football/premier-league-table-predictor/` | $4.44 | 33.9% |
| `/games/arrow-escape-3d/` | $1.03 | 7.9% |
| `/ar/ar-measure-tape/` | $0.57 | 4.3% |
| `/football/ucl-group-stage-simulator/` | $0.33 | 2.5% |
| `/pest/bug-bite-identifier/` | $0.3 | 2.3% |

🔔 **CONCENTRATION: one page is 33.9% of this property's revenue.** Losing it costs about $133/month. Diversification here means growing high-RPM pages, not more traffic to this one.

🔔 **DROP: `/football/premier-league-table-predictor/` down 46.2%** — $8.25/day → $4.44/day, ~$114.52/month at risk. Weekly $/day: 4.65 → 6.7 → 8.25 → 4.44.

### teamz-lab-generic-landing-pages
_No ad revenue on this property — nothing to watch._

## What the engine actually did

**https://tool.teamzlab.com/** — 6 change(s)
- 93d32af17 content(grooming): nicer body-shape silhouettes (authored in Codex, verified here)
- 5cf6cae64 content(grooming): make the body shape calculator serve men too
- 45350afc0 content(grooming): body shape calculator — measured demand, LOW competition, no cannibalisation
- 43773298b chore(nightly): enhance run summary 2026-08-30 — 13 pages, 5 defect classes fixed
- 00a036248 content(pest): trim the bug-bite title to 53 chars
- fcff913c1 content(pest): illustrated bite comparison chart on the bug-bite identifier

**https://apps.teamzlab.com/** — 23 change(s)
- bbe943f chore(nightly): refresh generated site output
- 392c4fd content(report): 2026-08-28 — 3 edits, 5 refused, 3 queue bugs (one is a 301'd URL)
- 91ab2e0 content(ride-share): answer 'vibe app development consulting' and route it out — #33.5, 25 impr, 0 clicks
- ab8acef content(hidden-chat-apps): scannable pick table + the leaks no hidden app closes — position 13.3 → page 1, 206 impr, 5 clicks
- 9adbf63 content(claude-code-development-service): buying-route depth for 'what is the best claude ai development agency?' — position 21.9 → page 1, 75 impr, 0 clicks
- 1f25f78 chore(nightly): refresh generated site output
- 85d00a3 content(report): 2026-08-27 — 2 edits, 3 skipped, 2 NEW rejected, 1 new bug
- dbca9dc content(devicegpt): list the other half of the cluster that already links in

**sc-domain:goalkit.teamzlab.com** — 22 change(s)
- 8ae146d chore(nightly): refresh generated site output
- 57ecba4 content(argentina-jersey-bangladesh): additive enhance — brand-trust + ordering FAQ
- 505fce5 content(chittagong): additive enhance — jersey quality-verification FAQ
- 65818d5 content(ronaldo-7): additive enhance — Portugal-vs-Al-Nassr buyer-intent FAQ
- 12202fe content(haaland-9): fix false ৳899 player-edition price claim — no such SKU exists
- 499b20e chore(nightly): refresh generated site output
- 940a95a chore(nightly): write last-night-content report — 2026-08-30
- 222d5e5 content(portugal-jersey-bangladesh): additive enhance — sizes FAQ, #8.1 striking-distance

**https://learn.teamzlab.com/** — 17 change(s)
- 90c8de7 chore(nightly): refresh generated site output
- efd62ae chore(nightly): refresh generated site output
- 3a8c23b chore(nightly): refresh generated site output
- 3e41e0d chore(nightly): refresh generated site output
- 48aedcd chore(nightly): refresh generated site output
- da44dec content(android-interview-mastery): rewrite meta description on compose state lesson — targets pos 11.2, 374 impr, 0 clicks (0.0% CTR), query includes 'mutablestateof'
- bdf3ae5 content(android-interview-mastery): rewrite meta description on logcat/profiler lesson — targets pos 11.3, 375 impr, 0 clicks (0.0% CTR), query 'android studio logcat'
- 3848a98 content(android-interview-mastery): rewrite meta description on activity/fragment lifecycle lesson — targets pos 12.6, 541 impr, 0 clicks (0.0% CTR)

**https://teamzlab.com/** — 7 change(s)
- bb68eff chore(nightly): refresh generated site output
- 51e9dd1 chore(nightly): refresh generated site output
- a3761d3 chore(nightly): refresh generated site output
- d3e7676 chore(nightly): refresh generated site output
- 7c87e54 chore(nightly): refresh generated site output
- 36a2a83 chore(nightly): refresh generated site output
- 5599a87 chore(nightly): refresh generated site output

**https://tekko.teamzlab.com/** — 6 change(s)
- 6be4b39 chore(nightly): refresh generated site output
- 7472ffb chore(nightly): refresh generated site output
- 1745ea1 chore(nightly): refresh generated site output
- b0f6fb7 chore(nightly): commit generated cache-bust churn to unblock the dirty-tree guard
- 0653ea8 chore(nightly): refresh generated site output
- f26f247 chore(nightly): ignore manual zip exports dropped into assets/

_A quiet property is not necessarily a broken one: the queue skips a night when no page is close enough and no demand is unserved. Inventing work would be worse._

## Distribution (articles + video)
- ✅ articles: 0.5d ago on tiktok
- ✅ video: 0.5d ago on tiktok — "EQ Test  Measure Your Emotional Intelligence — Free, No Signup"
- enabled platforms: blogger, bluesky, substack, telegraph, tiktok, youtube
- outcome (28d GA4): 7 sessions, $0.03 ($3.59/1k) from distribution-platform referrers
- per-business leads tracking: 40 snapshot(s) on file, 22d span, 3 business(es) matched last pull — `python3 py/build-distribution-leads.py --report-only` for the full table

## Keyword volume — pull freshness (Planner data ~1yr valid)
| property | volume data | age | action |
|---|---|---|---|
| https://tool.teamzlab.com/ | ✅ fresh (44 file(s)) | 11d | ok |
| https://apps.teamzlab.com/ | ✅ fresh (3 file(s)) | 22d | ok |
| sc-domain:goalkit.teamzlab.com | ✅ fresh (2 file(s)) | 22d | ok |
| https://learn.teamzlab.com/ | ✅ fresh (21 file(s)) | 22d | ok |
| https://teamzlab.com/ | — no-store (0 file(s)) | — | keyword engine not wired here |
| https://tekko.teamzlab.com/ | — no-store (0 file(s)) | — | keyword engine not wired here |

## Kindle books — apps.teamzlab.com/books/

| signal | value |
|---|---|
| /books/ search impressions (28d) | 0 |
| /books/ clicks | 0 |
| paid units (KDP export) | 8 |
| KENP pages read | 43 |
| royalty, USD rows only | $1.75 |
| months the export covers | June 2026, May 2026, April 2026, March 2026 |
| Amazon rank / reviews | not collectable — Amazon blocks automated reads |
| monthly report age | 8d (writes itself day 1, 06:10) |

## Football fortress — is anyone taking the top-earning terms?

_17 money terms judged, as of 2026-08-27._

| term | position | best ever |
|---|---|---|
| premier league table predictor | 2.5 | 2.0 |
| prem table predictor | 3.2 | 1.9 |
| prem predictor | 3.8 | 2.0 |
| predict the premier league table | 4 | 2.0 |
| epl predictor | 4.4 | 2 |
| premier league predictor | 5.2 | 2.0 |

### 🔔 TRIGGER — a term that pays is slipping
- **premier league table predictor** — BLEEDING: losing ~28 clicks/day: CTR 44% -> 28% on 172 impressions/day (pos 2.5, best 2.0) (page /football/premier-league-table-predictor/). This is revenue, not a vanity rank.
- **premier league predictor** — BLEEDING: losing ~97 clicks/day: CTR 30% -> 13% on 582 impressions/day (pos 5.2, best 2.0) (page /football/premier-league-table-predictor/). This is revenue, not a vanity rank.
- **championship predictor** — OFF_PAGE_ONE: pos 18.4 for 3 checks running; best 6.8 (page /football/championship-table-predictor/). This is revenue, not a vanity rank.

## Pages losing clicks while Google still shows them

_Impressions held, clicks did not — so the searches are still there and something else is taking them. Seasonal impression drops are excluded on purpose. Alerting at 10 clicks/day per page._

| page | clicks/day lost | worst query |
|---|---|---|
| / | **0** | teamz lab tools — CTR 1% → 0% |

Site total: **~0 clicks/day** against these pages' own recent CTR.

## External data feeds (third-party APIs behind tool pages)
| feed | state | detail |
|---|---|---|
| NFL player values (Sleeper API) | ✅ fresh | 549 players, pulled 0d ago |

## ⏰ Deadlines + data health (tools)
- ✅ all data-freshness checks green (checked 2026-08-30T16:24:08+00:00)

| in | date | event | status | window | what to do |
|---|---|---|---|---|---|
| 1d | 2026-09-01 | NFL fantasy draft season | built 🔔 **ACT THIS WEEK** | **OPEN NOW** | UPGRADE existing /us/fantasy-football-calculator/ (already pos 3.7, 40 clicks/90d) — add trade-calculator mode; do NOT build a new page |
| 1d | 2026-09-01 | NFL fantasy trade season (Sep-Nov peak) | built 🔔 **ACT THIS WEEK** | **OPEN NOW** | us/fantasy-football-trade-analyzer — NEW dedicated page for the trade-ANALYZER term |
| 10d | 2026-09-10 | NFL 2026 season kickoff | built 🔔 **ACT THIS WEEK** | **OPEN NOW** | nfl/nfl-playoff-predictor + nfl/nfl-passer-rating-calculator |
| 16d | 2026-09-16 | UCL 2026-27 league phase | live 🔔 **ACT THIS WEEK** | **OPEN NOW** | refresh existing UCL pages Aug 20-28, build NOTHING new (locked decision) |