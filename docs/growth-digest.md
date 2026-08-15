# Growth Digest — 2026-08-14

Window: **2026-07-14 → 2026-08-11** (28d) vs the 28d before it.

| property | clicks | vs prev | impressions | CTR | avg pos | nightly |
|---|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | **38,923** | +192% | 1,500,615 | 2.59% | 11.4 | ok (5h ago) |
| https://apps.teamzlab.com/ | **48** | +20% | 5,235 | 0.92% | 21.3 | ⚠️ ran, agent SKIPPED: dirty-tree (1h ago) |
| sc-domain:goalkit.teamzlab.com | **271** | -48% | 2,220 | 12.21% | 10.4 | ✅ ran (0h ago) — deploy exited 0 but was NOT verified against the live site |
| https://learn.teamzlab.com/ | **57** | +97% | 13,649 | 0.42% | 11.6 | ✅ ran (1h ago) — deploy exited 0 but was NOT verified against the live site |
| https://teamzlab.com/ | **257** | +8% | 3,079 | 8.35% | 8.2 | ok (0h ago) |

## AI channel (ChatGPT / Perplexity / Claude / Gemini)
| property | AI sessions | vs prev | AI revenue | $/1k sessions | organic $/1k |
|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | 2,054 | -17% | $31.39 | $15.28 | $4.78 |
| https://apps.teamzlab.com/ | 34 | +70% | $0.00 | $0.00 | $0.00 |
| sc-domain:goalkit.teamzlab.com | 280 | -54% | $0.00 | $0.00 | $0.00 |
| https://learn.teamzlab.com/ | 94 | +9300% | $0.00 | $0.00 | $0.00 |
| https://teamzlab.com/ | 0 | — | $0.00 | $0.00 | $0.00 |

### tool.teamzlab.com — AI Assistant sessions, last 6 weeks
| week | sessions | revenue |
|---|---|---|
| 28 | 488 | $13.72 |
| 29 | 620 | $26.07 |
| 30 | 544 | $7.24 |
| 31 | 385 | $3.05 |
| 32 | 426 | $3.37 |
| 33 | 272 | $1.19 |

## Apps property, split by business

| business | clicks 28d | vs prior 28d | impressions | CTR |
|---|---|---|---|---|
| app | 29 | flat | 1164 | 2.49% |
| SaaS | 0 | too small to judge (<25) | 28 | 0.00% |
| service | 1 | too small to judge (<25) | 1293 | 0.08% |
| blog | 15 | too small to judge (<25) | 2402 | 0.62% |
| home | 0 | too small to judge (<25) | 69 | 0.00% |
| other | 0 | too small to judge (<25) | 311 | 0.00% |

🔔 **service: 1293 impressions, 1 click(s) in 28 days.** Google is showing these pages and nobody is reaching them — that is a ranking-depth problem, not a copy problem. Check position before rewriting anything.

## Apps — are the mobile apps earning?

**£9/month**, owner-stated. Compare: tools ≈ £140/month.

_Per-app split unavailable (AdMob not connected), so which of the apps carry this is unknown. Run `python3 py/admob.py auth` when the split matters._

## Money — is revenue holding?

_Checked 2026-08-14T23:55:17 (0h ago). Recent = 7d ending D-2 vs the 3 weeks before it; GA4 per-page revenue needs ~48h to settle._

### teamzlab-tools — $10.92/day now vs $8.11/day baseline (+34.8%)
_Watching 15 pages = **93.4% of revenue**._

| top earner | $/day | share |
|---|---|---|
| `/football/premier-league-table-predictor/` | $6.01 | 55.0% |
| `/games/arrow-escape-3d/` | $0.66 | 6.0% |
| `/ar/ar-measure-tape/` | $0.41 | 3.8% |
| `/football/penalty-shootout-simulator/` | $0.25 | 2.3% |
| `/tools/ai-emotion-detector/` | $0.2 | 1.9% |

🔔 **CONCENTRATION: one page is 55.0% of this property's revenue.** Losing it costs about $180/month. Diversification here means growing high-RPM pages, not more traffic to this one.

**Fading (expected wind-down, not an alarm):**
- `/football/how-to-watch-fifa-world-cup-2026-in-germany/` — 1.64 → 0.0 → 0.0 → 0.0 $/day, ~$16.37/mo below its old rate
- `/football/penalty-shootout-simulator/` — 0.5 → 0.48 → 0.31 → 0.25 $/day, ~$5.57/mo below its old rate
- `/grooming/attractiveness-quiz/` — 0.2 → 0.17 → 0.13 → 0.09 $/day, ~$2.19/mo below its old rate
- `/football/how-to-watch-fifa-world-cup-2026-in-france/` — 0.44 → 0.0 → 0.0 → 0.0 $/day, ~$4.38/mo below its old rate

_3 smaller page(s) also fell but are under the notify floor — see `revenue-watchdog-status.json` for the list._

### teamz-lab-generic-landing-pages
_No ad revenue on this property — nothing to watch._

⚠️ **These alerts reach the Mac only.** No WhatsApp or email channel is configured, so a revenue drop fires into an empty room while you are out. Two-minute one-time fix: `~/.config/teamzlab/whatsapp-callmebot.env.example`.

## What the engine actually did

**https://tool.teamzlab.com/** — 12 change(s)
- 254abbf10 content(fantasy): close SEO gaps on trade analyzer + retarget dead FPL page
- f2224aa3f content(fpl): move the calculator to 2026/27 — after checking the maths still holds
- 3dfce053a content(football): PL predictor — trim meta description 159 -> 142 chars
- c3c17e634 content(football): PL predictor — cover "predictions" + "simulator" intent before Aug 21
- c89927e12 content(football): route 203k impressions of dead World Cup traffic into the league predictors, 3 weeks before PL kickoff
- b04d3c6ec content(forward-year): audit-driven cleanup of 393 pages titling 2028+ — 153 labeled, 210 noindexed
- 8c5cd1e62 chore(nightly): commit leftover enhanced page from the interrupted run
- 07219b3a4 content(batch-results): drop Keyword Planner results for football predictor batches

**https://apps.teamzlab.com/** — 111 change(s)
- 37a2f5d content(sms-cost): document the ABSENTEE SMS route, not just the diary one
- fe1d5b9 content(machine-import): the page had one road, and his machine closed it
- e617ccb content(gift-finder): the query wants a finder, the page was an essay
- 5750b77 content(devicegpt): the page sold half the app — four shipped features were missing entirely
- 3323ca2 content(apps): rewrite the bodies to match the retargeted keywords, and stop shipping cut-off Google snippets
- 0d4f57a content(apps): retarget 4 game/app pages off near-zero-volume keywords, refuse 3 with reasons
- 773d893 content(notetube-ai): the page was optimised for a 10/mo keyword while 8,100/mo sat next to it
- ac00cca chore(nightly): refresh generated site output

**sc-domain:goalkit.teamzlab.com** — 92 change(s)
- 215f47d chore(nightly): refresh generated site output
- 41e50ef chore(nightly): report — 2026-08-14
- 3fe6fca content(chittagong): additive enhance — club breadth + fabric-quality FAQ depth
- 91e4beb content(switzerland, algeria-youth, uruguay): additive enhance — price-transparency FAQ + fabric FAQ depth
- cdc461d content(goalkit): the collection hubs were invisible to every AI assistant
- 886e58f content(goalkit): the World Cup ended; club demand is what is left, and it peaks now
- ad4dd19 chore(nightly): refresh generated site output
- 9d66a7e chore(nightly): refresh generated site output

**https://learn.teamzlab.com/** — 47 change(s)
- d8e1c73 chore(nightly): refresh generated site output
- e5aaf23 content(class-9-math-bangla): rewrite lesson 51 meta description — targets 'sin cos tan সূত্র' at pos 6.8, 1623 impr, 16 clicks
- effa5ba content(android-interview-mastery): rewrite lesson 27 meta description — targets 'okhttp retry' at pos 11.3, 1970 impr, 5 clicks
- ec75d5f chore(nightly): refresh generated site output
- 601cf30 chore(nightly): refresh generated site output
- a481ef9 chore(nightly): refresh generated site output
- c2cdf1f chore(nightly): refresh generated site output
- d417900 content(android-interview-mastery): additive depth on lesson 56 — targets 'android fileprovider' at pos 12.2, 1865 impr, 1 click

**https://teamzlab.com/** — 28 change(s)
- 6a0c45a chore(nightly): refresh generated site output
- b184b5e chore(nightly): refresh generated site output
- 12b9496 chore(nightly): refresh generated site output
- adb12fd chore(nightly): refresh generated site output
- bccdba8 chore(nightly): refresh generated site output
- 673f0df chore(nightly): refresh generated site output
- c05a419 chore(nightly): refresh generated site output
- 7372c8d chore(nightly): refresh generated site output

_A quiet property is not necessarily a broken one: the queue skips a night when no page is close enough and no demand is unserved. Inventing work would be worse._

## Distribution (articles + video)
- ✅ articles: 2.5d ago on substack
- ✅ video: 4.8d ago on tiktok — "Resume Builder App For Android in Seconds — Free Tool"
- enabled platforms: blogger, bluesky, substack, telegraph, tiktok, youtube
- outcome (28d GA4): 16 sessions, $0.12 ($7.75/1k) from distribution-platform referrers
- per-business leads tracking: 16 snapshot(s) on file, 6d span, 2 business(es) matched last pull — `python3 py/build-distribution-leads.py --report-only` for the full table

## Keyword volume — pull freshness (Planner data ~1yr valid)
| property | volume data | age | action |
|---|---|---|---|
| https://tool.teamzlab.com/ | ✅ fresh (36 file(s)) | 0d | ok |
| https://apps.teamzlab.com/ | ✅ fresh (3 file(s)) | 6d | ok |
| sc-domain:goalkit.teamzlab.com | ✅ fresh (2 file(s)) | 6d | ok |
| https://learn.teamzlab.com/ | ✅ fresh (21 file(s)) | 6d | ok |
| https://teamzlab.com/ | — no-store (0 file(s)) | — | keyword engine not wired here |

## External data feeds (third-party APIs behind tool pages)
| feed | state | detail |
|---|---|---|
| NFL player values (Sleeper API) | ✅ fresh | 549 players, pulled 0d ago |

## ⏰ Deadlines + data health (tools)
- ✅ all data-freshness checks green (checked 2026-08-14T13:09:49+00:00)

| in | date | event | status | window | what to do |
|---|---|---|---|---|---|
| 7d | 2026-08-21 | Premier League 2026-27 matchday 1 | live 🔔 **ACT THIS WEEK** | **OPEN NOW** | refresh only — football/premier-league-table-predictor is live; verify standings started:true after kickoff |
| 18d | 2026-09-01 | NFL fantasy draft season | built 🔔 **ACT THIS WEEK** | **OPEN NOW** | UPGRADE existing /us/fantasy-football-calculator/ (already pos 3.7, 40 clicks/90d) — add trade-calculator mode; do NOT build a new page |
| 18d | 2026-09-01 | NFL fantasy trade season (Sep-Nov peak) | built 🔔 **ACT THIS WEEK** | **OPEN NOW** | us/fantasy-football-trade-analyzer — NEW dedicated page for the trade-ANALYZER term |
| 27d | 2026-09-10 | NFL 2026 season kickoff | built 🔔 **ACT THIS WEEK** | **OPEN NOW** | nfl/nfl-playoff-predictor + nfl/nfl-passer-rating-calculator |
| 33d | 2026-09-16 | UCL 2026-27 league phase | live | opens in 5d | refresh existing UCL pages Aug 20-28, build NOTHING new (locked decision) |