# Growth Digest — 2026-08-03

Window: **2026-07-03 → 2026-07-31** (28d) vs the 28d before it.

| property | clicks | vs prev | impressions | CTR | avg pos | nightly |
|---|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | **23,530** | +157% | 1,337,158 | 1.76% | 11.6 | ⚠️ ran, but DEPLOY FAILED (0h ago) — serving the old build |
| https://apps.teamzlab.com/ | **48** | +78% | 5,733 | 0.84% | 18.4 | ⚠️ ran, agent SKIPPED: dirty-tree (20h ago) |
| sc-domain:goalkit.teamzlab.com | **333** | -49% | 2,404 | 13.85% | 10.9 | ok (12h ago) |
| https://learn.teamzlab.com/ | **52** | +160% | 10,352 | 0.50% | 9.4 | ok (11h ago) |
| https://teamzlab.com/ | **223** | -24% | 3,156 | 7.07% | 7.4 | ok (19h ago) |

## AI channel (ChatGPT / Perplexity / Claude / Gemini)
| property | AI sessions | vs prev | AI revenue | $/1k sessions | organic $/1k |
|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | 2,081 | -18% | $52.77 | $25.36 | $5.54 |
| https://apps.teamzlab.com/ | 22 | +100% | $0.00 | $0.00 | $0.00 |
| sc-domain:goalkit.teamzlab.com | 359 | -52% | $0.00 | $0.00 | $0.00 |
| https://learn.teamzlab.com/ | 50 | new | $0.00 | $0.00 | $0.00 |
| https://teamzlab.com/ | 0 | — | $0.00 | $0.00 | $0.00 |

### tool.teamzlab.com — AI Assistant sessions, last 6 weeks
| week | sessions | revenue |
|---|---|---|
| 26 | 791 | $13.07 |
| 27 | 388 | $11.97 |
| 28 | 488 | $13.72 |
| 29 | 620 | $26.07 |
| 30 | 544 | $7.24 |
| 31 | 338 | $2.70 |

## What the engine actually did

**https://tool.teamzlab.com/** — 11 change(s)
- 3dfce053a content(football): PL predictor — trim meta description 159 -> 142 chars
- c3c17e634 content(football): PL predictor — cover "predictions" + "simulator" intent before Aug 21
- c89927e12 content(football): route 203k impressions of dead World Cup traffic into the league predictors, 3 weeks before PL kickoff
- b04d3c6ec content(forward-year): audit-driven cleanup of 393 pages titling 2028+ — 153 labeled, 210 noindexed
- 8c5cd1e62 chore(nightly): commit leftover enhanced page from the interrupted run
- 07219b3a4 content(batch-results): drop Keyword Planner results for football predictor batches
- 31dfe6633 content(batch-prep): 2 Keyword Planner batches for La Liga/Serie A/Bundesliga table predictors
- b27d9f2b7 content(football): link premier-league-table-predictor from UCL club-football tools

**https://apps.teamzlab.com/** — 75 change(s)
- 9f07da5 chore(nightly): add a 10:30 GSC catch-up fire time, refresh generated status
- 19782f3 chore(nightly): refresh generated site output
- 6e41c1d chore(nightly): refresh ecommerce GSC keyword export timestamp
- f7f9e52 chore(nightly): refresh generated data — queue, keywords, status, indexing report
- 6d2fce8 content(report): 4 shipped, 1 rejected — night 2026-07-31
- 31b2a00 content(home): identity FAQ + motion-service FAQ — additive, title untouched
- 629d0c2 content(chopstick-landing-games): how-to-catch depth + 2 FAQs — additive
- 53d8eb1 content(devicegpt): body section for 'device assessment' — additive, title untouched

**sc-domain:goalkit.teamzlab.com** — 108 change(s)
- 7949ba3 chore(nightly): refresh generated site output
- 96fa32c chore(nightly): refresh generated site output
- 583e19c chore(nightly): refresh generated site output
- 91817ba chore(nightly): refresh generated site output
- 1c5cd02 chore(nightly): refresh generated site output
- 5fc19ed chore(nightly): report 2026-07-30 — 1 real fix, 5 rejected as already-done/dead-topic
- 5c4e06d content(brazil-jersey-bangladesh): fix wrong prices, add FAQ depth (additive #20.4, 137 impr, 6 clicks)
- 68c6981 chore(nightly): refresh generated site output

**https://learn.teamzlab.com/** — 28 change(s)
- 555ff54 chore(nightly): refresh generated site output
- e9a7d28 content(class-9-math-bangla): additive depth on top-CTR lesson 51 (sin/cos/tan)
- 3f66af6 content(android-interview-mastery): additive depth on 3 striking-distance lessons
- 0559946 chore(nightly): refresh generated site output
- a37a929 chore(nightly): refresh generated site output
- 44e43a2 chore(nightly): refresh generated site output
- 5bf4e19 chore(nightly): refresh generated site output
- c048742 chore(nightly): refresh generated site output

**https://teamzlab.com/** — 21 change(s)
- 5e0ee55 chore(nightly): refresh generated site output
- 4bce630 chore(nightly): refresh generated site output
- 43b62b6 chore(nightly): refresh generated site output
- 5338516 chore(nightly): refresh generated site output
- 6223fa6 chore(nightly): refresh generated site output
- 3868b68 chore(nightly): refresh generated site output
- 75688a7 chore(nightly): refresh generated site output
- f2915eb chore(nightly): refresh generated site output

_A quiet property is not necessarily a broken one: the queue skips a night when no page is close enough and no demand is unserved. Inventing work would be worse._

## Keyword volume — pull freshness (Planner data ~1yr valid)
| property | volume data | age | action |
|---|---|---|---|
| https://tool.teamzlab.com/ | ✅ fresh (22 file(s)) | 4d | ok |
| https://apps.teamzlab.com/ | ✅ fresh (1 file(s)) | 16d | ok |
| sc-domain:goalkit.teamzlab.com | ✅ fresh (1 file(s)) | 16d | ok |
| https://learn.teamzlab.com/ | ✅ fresh (11 file(s)) | 12d | ok |
| https://teamzlab.com/ | — no-store (0 file(s)) | — | keyword engine not wired here |