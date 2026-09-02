# Growth Digest — 2026-09-01

Window: **2026-08-01 → 2026-08-29** (28d) vs the 28d before it.

| property | clicks | vs prev | impressions | CTR | avg pos | nightly |
|---|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | **63,457** | +176% | 1,998,373 | 3.18% | 12.3 | ⚠️ ran, but DEPLOY state is UNKNOWN (2h ago) — cannot confirm the new build is live |
| https://apps.teamzlab.com/ | **58** | +29% | 6,192 | 0.94% | 23.0 | ⚠️ ran, agent SKIPPED: dirty-tree (1h ago) |
| sc-domain:goalkit.teamzlab.com | **205** | -37% | 1,956 | 10.48% | 10.3 | ⚠️ ran, agent SKIPPED: dirty-tree (1h ago) |
| https://learn.teamzlab.com/ | **65** | +30% | 13,987 | 0.46% | 11.5 | ⚠️ ran, agent SKIPPED: dirty-tree (1h ago) |
| https://teamzlab.com/ | **291** | +34% | 3,203 | 9.09% | 6.5 | ⚠️ ran, agent SKIPPED: dirty-tree (0h ago) |
| https://tekko.teamzlab.com/ | **2** | new | 43 | 4.65% | 62.2 | ✅ ran (2h ago) — deploy exited 0 but was NOT verified against the live site |

## AI channel (ChatGPT / Perplexity / Claude / Gemini)
| property | AI sessions | vs prev | AI revenue | $/1k sessions | organic $/1k |
|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | 2,728 | +34% | $20.13 | $7.38 | $4.28 |
| https://apps.teamzlab.com/ | 65 | +195% | $0.00 | $0.00 | $0.00 |
| sc-domain:goalkit.teamzlab.com | 226 | -34% | $0.00 | $0.00 | $0.00 |
| https://learn.teamzlab.com/ | 99 | +98% | $0.00 | $0.00 | $0.00 |
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
| 35 | 670 | $6.40 |

## Apps property, split by business

| business | clicks 28d | vs prior 28d | impressions | CTR |
|---|---|---|---|---|
| app | 35 | +13% | 1328 | 2.64% |
| SaaS | 0 | too small to judge (<25) | 21 | 0.00% |
| service | 1 | too small to judge (<25) | 1841 | 0.05% |
| blog | 18 | too small to judge (<25) | 2633 | 0.68% |
| home | 2 | too small to judge (<25) | 67 | 2.99% |
| other | 1 | too small to judge (<25) | 390 | 0.26% |

🔔 **service: 1841 impressions, 1 click(s) in 28 days.** Google is showing these pages and nobody is reaching them — that is a ranking-depth problem, not a copy problem. Check position before rewriting anything.

## Apps — are the mobile apps earning?

**£9/month**, owner-stated. Compare: tools ≈ £140/month.

_Per-app split unavailable (AdMob not connected), so which of the apps carry this is unknown. Run `python3 py/admob.py auth` when the split matters._

## Money — is revenue holding?

### AdSense daily — complete days only

Account reports in **Europe/London**. Newest COMPLETE day on file: **2026-08-31**.

| date | earnings (GBP) | pageviews |
|---|---|---|
| 2026-08-25 | 7.94 | 2894 |
| 2026-08-26 | 8.13 | 2864 |
| 2026-08-27 | 8.56 | 3009 |
| 2026-08-28 | 6.80 | 3021 |
| 2026-08-29 | 5.80 | 2335 |
| 2026-08-30 | 6.92 | 2227 |
| 2026-08-31 | 5.55 | 2897 |

Newest complete day is **-29%** vs the 8-day mean before it.

**Still running (NOT counted above):** 2026-09-01 = GBP 4.72 (3129 pageviews). This is a part-day total and always reads low.

The account clock is Europe/London, so a Bangladesh late evening or early morning is still the PREVIOUS AdSense day — a fresh-looking 'today' is usually an hour or two of data, not a drop.

_Checked 2026-09-01T23:55:16 (0h ago). Recent = 7d ending D-2 vs the 3 weeks before it; GA4 per-page revenue needs ~48h to settle._

### teamzlab-tools — $10.29/day now vs $13.36/day baseline (-23.0%)
_Watching 19 pages = **102.7% of revenue**._

| top earner | $/day | share |
|---|---|---|
| `/football/premier-league-table-predictor/` | $1.92 | 18.7% |
| `/games/arrow-escape-3d/` | $0.94 | 9.1% |
| `/ar/ar-measure-tape/` | $0.58 | 5.7% |
| `/football/ucl-group-stage-simulator/` | $0.36 | 3.5% |
| `/tools/signature-analyzer/` | $0.29 | 2.8% |

🔔 **DROP: `/football/premier-league-table-predictor/` down 78.7%** — $9.02/day → $1.92/day, ~$213.0/month at risk. Weekly $/day: 5.47 → 7.01 → 9.02 → 1.92.

_3 smaller page(s) also fell but are under the notify floor — see `revenue-watchdog-status.json` for the list._

### teamz-lab-generic-landing-pages
_No ad revenue on this property — nothing to watch._

## What the engine actually did

**https://tool.teamzlab.com/** — 19 change(s)
- 93d32af17 content(grooming): nicer body-shape silhouettes (authored in Codex, verified here)
- 5cf6cae64 content(grooming): make the body shape calculator serve men too
- 45350afc0 content(grooming): body shape calculator — measured demand, LOW competition, no cannibalisation
- 43773298b chore(nightly): enhance run summary 2026-08-30 — 13 pages, 5 defect classes fixed
- 00a036248 content(pest): trim the bug-bite title to 53 chars
- fcff913c1 content(pest): illustrated bite comparison chart on the bug-bite identifier
- 331b2df0c content(football): Premier League table calculator — serving the intent we were ceding
- a1cdc55b9 content(football): Championship table predictor — 14,800 August searches, no owner

**https://apps.teamzlab.com/** — 89 change(s)
- bbe943f chore(nightly): refresh generated site output
- 392c4fd content(report): 2026-08-28 — 3 edits, 5 refused, 3 queue bugs (one is a 301'd URL)
- 91ab2e0 content(ride-share): answer 'vibe app development consulting' and route it out — #33.5, 25 impr, 0 clicks
- ab8acef content(hidden-chat-apps): scannable pick table + the leaks no hidden app closes — position 13.3 → page 1, 206 impr, 5 clicks
- 9adbf63 content(claude-code-development-service): buying-route depth for 'what is the best claude ai development agency?' — position 21.9 → page 1, 75 impr, 0 clicks
- 1f25f78 chore(nightly): refresh generated site output
- 85d00a3 content(report): 2026-08-27 — 2 edits, 3 skipped, 2 NEW rejected, 1 new bug
- dbca9dc content(devicegpt): list the other half of the cluster that already links in

**sc-domain:goalkit.teamzlab.com** — 89 change(s)
- 7ae9cef chore(nightly): refresh generated site output
- aead829 chore(nightly): write last-night-content report — 2026-08-31
- dc8f52f chore(nightly): refresh sitemap lastmod after content enhancements
- 009186c content(netherlands-2026-home-authentic-jersey-mens): additive enhance — replica-vs-player + custom-print FAQ
- 1768d0a content(haaland-9): additive enhance — away-jersey + care-instructions FAQ
- d031231 content(chittagong): additive enhance — national-team + bulk-order FAQ
- e91699d content(/): additive enhance — brand-trust + WhatsApp-contact FAQ
- 8ae146d chore(nightly): refresh generated site output

**https://learn.teamzlab.com/** — 56 change(s)
- b93c946 chore(nightly): refresh generated site output
- cb4bc66 chore(nightly): refresh generated site output
- 90c8de7 chore(nightly): refresh generated site output
- efd62ae chore(nightly): refresh generated site output
- 3a8c23b chore(nightly): refresh generated site output
- 3e41e0d chore(nightly): refresh generated site output
- 48aedcd chore(nightly): refresh generated site output
- da44dec content(android-interview-mastery): rewrite meta description on compose state lesson — targets pos 11.2, 374 impr, 0 clicks (0.0% CTR), query includes 'mutablestateof'

**https://teamzlab.com/** — 27 change(s)
- 5f1afd3 chore(nightly): refresh generated site output
- bb68eff chore(nightly): refresh generated site output
- 51e9dd1 chore(nightly): refresh generated site output
- a3761d3 chore(nightly): refresh generated site output
- d3e7676 chore(nightly): refresh generated site output
- 7c87e54 chore(nightly): refresh generated site output
- 36a2a83 chore(nightly): refresh generated site output
- 5599a87 chore(nightly): refresh generated site output

**https://tekko.teamzlab.com/** — 11 change(s)
- e076bfb chore(nightly): refresh generated site output
- 82dc246 chore(nightly): refresh generated site output
- 6be4b39 chore(nightly): refresh generated site output
- 7472ffb chore(nightly): refresh generated site output
- 1745ea1 chore(nightly): refresh generated site output
- b0f6fb7 chore(nightly): commit generated cache-bust churn to unblock the dirty-tree guard
- 0653ea8 chore(nightly): refresh generated site output
- f26f247 chore(nightly): ignore manual zip exports dropped into assets/

_A quiet property is not necessarily a broken one: the queue skips a night when no page is close enough and no demand is unserved. Inventing work would be worse._

## Distribution (articles + video)
- ✅ articles: 0.7d ago on substack
- ✅ video: 1.5d ago on tiktok — "Your 2027 Taxes Are Going UP — Free TCJA Sunset Calculator"
- enabled platforms: blogger, bluesky, substack, telegraph, tiktok, youtube
- outcome (28d GA4): 7 sessions, $0.03 ($3.59/1k) from distribution-platform referrers
- per-business leads tracking: 44 snapshot(s) on file, 24d span, 1 business(es) matched last pull — `python3 py/build-distribution-leads.py --report-only` for the full table

## Keyword volume — pull freshness (Planner data ~1yr valid)
| property | volume data | age | action |
|---|---|---|---|
| https://tool.teamzlab.com/ | ✅ fresh (44 file(s)) | 13d | ok |
| https://apps.teamzlab.com/ | ✅ fresh (3 file(s)) | 24d | ok |
| sc-domain:goalkit.teamzlab.com | ✅ fresh (2 file(s)) | 24d | ok |
| https://learn.teamzlab.com/ | ✅ fresh (21 file(s)) | 24d | ok |
| https://teamzlab.com/ | — no-store (0 file(s)) | — | keyword engine not wired here |
| https://tekko.teamzlab.com/ | ⬜ never (0 file(s)) | — | no volume yet — first pull pending |

## Kindle books — apps.teamzlab.com/books/

| signal | value |
|---|---|
| /books/ search impressions (28d) | 13 |
| /books/ clicks | 0 |
| paid units (KDP export) | 8 |
| KENP pages read | 43 |
| royalty, USD rows only | $1.75 |
| months the export covers | June 2026, May 2026, April 2026, March 2026 |
| Amazon rank / reviews | not collectable — Amazon blocks automated reads |
| monthly report age | 0d (writes itself day 1, 06:10) |

## Football fortress — is anyone taking the top-earning terms?

_15 money terms judged, as of 2026-08-28._

| term | position | best ever |
|---|---|---|
| prem table predictor | 5.9 | 1.9 |
| predict the premier league table | 6.1 | 2.0 |
| epl predictor | 6.4 | 2 |
| premier league table predictor | 6.9 | 2.0 |
| prem predictor | 7.0 | 2.0 |
| premier league predictor | 7.4 | 2.0 |

### 🔔 TRIGGER — a term that pays is slipping
- **premier league table predictor** — BLEEDING: losing ~38 clicks/day: CTR 44% -> 20% on 159 impressions/day (pos 6.9, best 2.0) (page /football/premier-league-table-predictor/). This is revenue, not a vanity rank.
- **premier league predictor** — BLEEDING: losing ~103 clicks/day: CTR 30% -> 8% on 485 impressions/day (pos 7.4, best 2.0) (page /football/premier-league-table-predictor/). This is revenue, not a vanity rank.
- **prem predictor** — BLEEDING: losing ~26 clicks/day: CTR 34% -> 4% on 90 impressions/day (pos 7.0, best 2.0) (page /football/premier-league-table-predictor/). This is revenue, not a vanity rank.
- **pl predictor** — SLIPPING: pos 7.8 vs best 2.6 (tolerance 1.3) for 3 checks running (page /football/premier-league-table-predictor/). This is revenue, not a vanity rank.
- **prem table predictor** — SLIPPING: pos 5.9 vs best 1.9 (tolerance 1.0) for 3 checks running (page /football/premier-league-table-predictor/). This is revenue, not a vanity rank.

## Pages losing clicks while Google still shows them

_Impressions held, clicks did not — so the searches are still there and something else is taking them. Seasonal impression drops are excluded on purpose. Alerting at 10 clicks/day per page._

| page | clicks/day lost | worst query |
|---|---|---|

Site total: **~0 clicks/day** against these pages' own recent CTR.

## External data feeds (third-party APIs behind tool pages)
| feed | state | detail |
|---|---|---|
| NFL player values (Sleeper API) | ✅ fresh | 549 players, pulled 0d ago |

## ⏰ Deadlines + data health (tools)
- ✅ all data-freshness checks green (checked 2026-08-31T20:32:39+00:00)

| in | date | event | status | window | what to do |
|---|---|---|---|---|---|
| 0d | 2026-09-01 | NFL fantasy draft season | built 🔔 **ACT THIS WEEK** | **OPEN NOW** | UPGRADE existing /us/fantasy-football-calculator/ (already pos 3.7, 40 clicks/90d) — add trade-calculator mode; do NOT build a new page |
| 0d | 2026-09-01 | NFL fantasy trade season (Sep-Nov peak) | built 🔔 **ACT THIS WEEK** | **OPEN NOW** | us/fantasy-football-trade-analyzer — NEW dedicated page for the trade-ANALYZER term |
| 9d | 2026-09-10 | NFL 2026 season kickoff | built 🔔 **ACT THIS WEEK** | **OPEN NOW** | nfl/nfl-playoff-predictor + nfl/nfl-passer-rating-calculator |
| 14d | 2026-09-15 | color-cards — decide on a Crazy Eights mode | planned 🔔 **ACT THIS WEEK** | **OPEN NOW** | DECISION + SERP CHECK first, then build only if winnable. Read the live SERP for 'crazy eights' and 'crazy eights online' — it could NOT be read on 2026-09-01 because DuckDuckGo rate-limited the session, so winnability is still unmeasured. |
| 15d | 2026-09-16 | UCL 2026-27 league phase | live 🔔 **ACT THIS WEEK** | **OPEN NOW** | refresh existing UCL pages Aug 20-28, build NOTHING new (locked decision) |
| 28d | 2026-09-29 | Brick Breaker — the 28-day verdict | planned | opens in 21d | MEASURE ONLY, build nothing. Pull GSC for tool.teamzlab.com/games/brick-breaker/ and for queries containing 'block breaker', 'brick breaker', '2 player'. Then apply the rule below — it was agreed in advance so the result is not argued backwards from whatever the number happens to be. |
| 30d | 2026-10-01 | Fantasy football trade season — Oct/Nov peak | planned | opens in 23d | us/fantasy-football-trade-analyzer — swap the H1/title noun from 'Analyzer' to 'Calculator'. Do NOT add more internal links; do NOT change the URL. |
| 61d | 2026-11-01 | NFL playoff race — Dec/Jan peak | planned | opens in 26d | nfl/nfl-playoff-predictor — refresh only (season labels, dateModified). It is BUILT and already ranks; do not rebuild. |