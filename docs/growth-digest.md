# Growth Digest — 2026-08-08

Window: **2026-07-08 → 2026-08-05** (28d) vs the 28d before it.

| property | clicks | vs prev | impressions | CTR | avg pos | nightly |
|---|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | **30,023** | +169% | 1,410,706 | 2.13% | 11.7 | ⚠️ ran, but DEPLOY state is UNKNOWN (8h ago) — cannot confirm the new build is live |
| https://apps.teamzlab.com/ | **49** | +48% | 5,371 | 0.91% | 19.1 | ⚠️ ran, but GIT PUSH FAILED (9h ago) — commits are local-only and the remote backup is not receiving them; check `git ls-remote origin` |
| sc-domain:goalkit.teamzlab.com | **321** | -47% | 2,281 | 14.07% | 11.1 | ⚠️ ran, agent SKIPPED: dirty-tree (9h ago) |
| https://learn.teamzlab.com/ | **53** | +104% | 13,548 | 0.39% | 11.3 | ⚠️ ran, but GIT PUSH FAILED (9h ago) — commits are local-only and the remote backup is not receiving them; check `git ls-remote origin` |
| https://teamzlab.com/ | **246** | -7% | 3,164 | 7.77% | 8.1 | ⚠️ ran, but GIT PUSH FAILED (8h ago) — commits are local-only and the remote backup is not receiving them; check `git ls-remote origin` |

## AI channel (ChatGPT / Perplexity / Claude / Gemini)
| property | AI sessions | vs prev | AI revenue | $/1k sessions | organic $/1k |
|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | 2,127 | -23% | $50.42 | $23.70 | $5.08 |
| https://apps.teamzlab.com/ | 21 | +31% | $0.00 | $0.00 | $0.00 |
| sc-domain:goalkit.teamzlab.com | 311 | -63% | $0.00 | $0.00 | $0.00 |
| https://learn.teamzlab.com/ | 67 | new | $0.00 | $0.00 | $0.00 |
| https://teamzlab.com/ | 0 | — | $0.00 | $0.00 | $0.00 |

### tool.teamzlab.com — AI Assistant sessions, last 6 weeks
| week | sessions | revenue |
|---|---|---|
| 27 | 388 | $11.97 |
| 28 | 488 | $13.72 |
| 29 | 620 | $26.07 |
| 30 | 544 | $7.24 |
| 31 | 385 | $3.05 |
| 32 | 233 | $1.82 |

## What the engine actually did

**https://tool.teamzlab.com/** — 12 change(s)
- f2224aa3f content(fpl): move the calculator to 2026/27 — after checking the maths still holds
- 3dfce053a content(football): PL predictor — trim meta description 159 -> 142 chars
- c3c17e634 content(football): PL predictor — cover "predictions" + "simulator" intent before Aug 21
- c89927e12 content(football): route 203k impressions of dead World Cup traffic into the league predictors, 3 weeks before PL kickoff
- b04d3c6ec content(forward-year): audit-driven cleanup of 393 pages titling 2028+ — 153 labeled, 210 noindexed
- 8c5cd1e62 chore(nightly): commit leftover enhanced page from the interrupted run
- 07219b3a4 content(batch-results): drop Keyword Planner results for football predictor batches
- 31dfe6633 content(batch-prep): 2 Keyword Planner batches for La Liga/Serie A/Bundesliga table predictors

**https://apps.teamzlab.com/** — 104 change(s)
- 2aa9752 content(devicegpt): link the dead-pixel guide to the new interactive test tool
- a8715e3 content(devicegpt): add first-hand build section + original v37 screenshots to dead-pixel guide
- 304e233 chore(nightly): recover stranded output — dead-pixel test guide + regenerated data
- d524801 chore(nightly): refresh generated site output
- 4844891 content(report): 2026-08-07 night — 3 enhanced, 2 rejected, 2 queue bugs flagged
- 46fa558 content(teamz-lab-tools): subdomain disambiguation + company-proof FAQ
- 15b78e5 content(fedex-soap-retired): August-reader section + kill a stale sandbox claim
- 945967a content(claude-code-development-service): answer 'best claude ai development agency' on-page

**sc-domain:goalkit.teamzlab.com** — 122 change(s)
- 8770a01 chore(nightly): refresh generated site output
- 3e50670 chore(nightly): report 2026-08-05 — 3 real fixes (FAQPage schema depth), 2 cold-start already-done
- 894459f content(players): additive enhance — 2 more FAQ Q&A (delivery time, fabric) + matching FAQPage schema on all 6 shared player pages; targets haaland-9 #6.8 (154 impr/31 clicks) + ronaldo-7 #11.3 (127 impr/18 clicks)
- f3d5fe8 content(chittagong): additive enhance — add FAQPage schema matching existing 5-Q on-page FAQ (was missing entirely); targets #8.1 'chittagong jersey shop' (149 impr, 7 clicks)
- 5810a63 content(puma-czech-republic-2026-home-replica-jersey-mens): additive enhance — kit-design FAQ + price-transparency FAQ, FAQPage schema depth; targets #8.9 'czech jersey 2026' (63 impr, 0 clicks)
- 3ff378f chore(nightly): refresh generated site output
- 5794ddd chore(nightly): report 2026-08-04 — 4 real fixes (FAQ schema/depth), 2 cold-start already-done
- 0b4140a content(argentina-jersey-bangladesh, brazil-jersey-bangladesh): additive enhance — FAQ depth + FAQPage schema match

**https://learn.teamzlab.com/** — 39 change(s)
- 3423f29 chore(nightly): refresh generated site output
- 4cae381 chore(nightly): refresh generated site output
- 06a6ec1 content(class-9-math-bangla): additive standard-angle-table depth on lesson 51 (sin/cos/tan) — targets page-level striking distance at pos 6.8, 1382 impr, 12 clicks
- e0f5054 content(android-interview-mastery): additive minimal-example depth on lesson 73 (pagingsource) — targets pos 14.8, 1218 impr, 3 clicks
- 129f486 content(android-interview-mastery): additive minimal-setup depth on lesson 56 (fileprovider) — targets pos 12.6, 1870 impr, 1 click
- e667414 content(android-interview-mastery): additive logging-interceptor depth on lesson 27 (okhttp interceptor) — targets pos 10.7, 1329 impr, 4 clicks
- eb9dddd chore(nightly): refresh generated site output
- db18ec3 content(android-interview-mastery): additive minimal-example depth on lesson 27 (okhttp interceptor) — targets pos 10.8, 1276 impr, 4 clicks

**https://teamzlab.com/** — 26 change(s)
- 7372c8d chore(nightly): refresh generated site output
- 96edf45 chore(nightly): refresh generated site output
- 3a36be9 chore(nightly): refresh generated site output
- 0e05170 chore(nightly): refresh generated site output
- 501e9d7 chore(nightly): refresh generated site output
- 5e0ee55 chore(nightly): refresh generated site output
- 4bce630 chore(nightly): refresh generated site output
- 43b62b6 chore(nightly): refresh generated site output

_A quiet property is not necessarily a broken one: the queue skips a night when no page is close enough and no demand is unserved. Inventing work would be worse._

## Distribution (articles + video)
- 🔴 articles: **STALE** — 71.9d since last publish (tiktok), 975 total posts on record
- ✅ video: 0.3d ago on youtube — "NUA Net Unrealized Appreciation Calculator — Free, No Signup"
- enabled platforms: blogger, bluesky, hashnode, substack, telegraph, tiktok, youtube
- outcome (28d GA4): 19 sessions, $0.17 ($8.81/1k) from distribution-platform referrers
- per-business leads tracking: 2 snapshot(s) on file, 2 business(es) matched last pull — `python3 py/build-distribution-leads.py --report-only` for the full table

### 🔔 TRIGGER — distribution engine needs attention
- articles stale 72d (last: tiktok)
- check: `python3 scripts/distribute/distribute.py outcome --days 7` (tools property) or the nightly's own health_alerts.

## Keyword volume — pull freshness (Planner data ~1yr valid)
| property | volume data | age | action |
|---|---|---|---|
| https://tool.teamzlab.com/ | ✅ fresh (22 file(s)) | 9d | ok |
| https://apps.teamzlab.com/ | ✅ fresh (2 file(s)) | 0d | ok |
| sc-domain:goalkit.teamzlab.com | ✅ fresh (1 file(s)) | 21d | ok |
| https://learn.teamzlab.com/ | ✅ fresh (11 file(s)) | 17d | ok |
| https://teamzlab.com/ | — no-store (0 file(s)) | — | keyword engine not wired here |