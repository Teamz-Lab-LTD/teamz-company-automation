# Growth Digest — 2026-07-13

Window: **2026-06-12 → 2026-07-10** (28d) vs the 28d before it.

| property | clicks | vs prev | impressions | CTR | avg pos | nightly |
|---|---|---|---|---|---|---|
| https://tool.teamzlab.com/ | **12,373** | +390% | 1,089,394 | 1.14% | 12.0 | ? ran 15h ago — no status file, cannot confirm it worked |
| https://apps.teamzlab.com/ | **38** | +245% | 5,799 | 0.66% | 20.0 | ⚠️ ran, but DEPLOY FAILED (14h ago) — serving the old build |
| sc-domain:goalkit.teamzlab.com | **594** | +76% | 3,587 | 16.56% | 8.8 | ok (12h ago) |
| https://learn.teamzlab.com/ | **28** | +47% | 10,027 | 0.28% | 12.8 | ⚠️ ran, but DEPLOY FAILED (13h ago) — serving the old build |
| https://teamzlab.com/ | **265** | -32% | 3,676 | 7.21% | 5.0 | ? ran 13h ago — no status file, cannot confirm it worked |

## What the engine actually did

**https://tool.teamzlab.com/** — 1 change(s)
- 9ccdcd769 chore(nightly): commit accumulated build artifacts to unblock enhance loop

**https://apps.teamzlab.com/** — 9 change(s)
- a9da25b chore(nightly): refresh generated ecommerce page data (GSC export timestamp)
- 5fd1d2c content(prompt): RETARGET rules — a title rewrite does not move a page from #59
- 271ef26 chore(nightly): night-one artifacts + content queue/log
- 6179c64 chore(nightly): content report 2026-07-12
- 3ba20a3 content(no-trace-chat): shortDescription leads with 'invisible chat application' + add targeted FAQ — position 17.3 → page 1 for 'invisible chat application', 26 impr, 0 clicks
- 28f0c90 content(threema-vs-session): fix metaTitle + add direct H2 — position 8.8 → page 1 for 'threema vs session', 37 impr, 0 clicks
- 91520c1 content(animations): sharpen meta desc + 2 buyer-intent FAQs — position 23.2 → page 1 for 'hire lottie developers', 128 impr, 0 clicks
- 60f3d47 chore(nightly): migrate apps to the shared content-capable runner

**sc-domain:goalkit.teamzlab.com** — 19 change(s)
- 217acfe chore(nightly): regenerated collection HTML + first nightly-status.json
- f3c2d1d chore(nightly): content report 2026-07-13 — 4 targets (2 enhance + 2 cold-start + new Barcelona collection hub)
- 0f7a7b0 content(barcelona-cold-start): seo_title + new collection hub /barcelona-jersey-bangladesh/ — 0-impression pages get identity + internal links
- e18703c content(japan-authentic-home): seo_title + price-first desc target 'japan jersey 2026 price in bangladesh' #11.6 → page 1
- f0a1b13 content(chile-2026-home-mens): seo_title reorders 'Chile Jersey 2026' tight phrase — targets #9.3 → page 1
- 161517e content(prompt): name is for the customer, seo_title is for Google — and never the reverse
- d1ea495 chore(nightly): content report 2026-07-12 run-2 — 6 targets (4 enhance + 2 cold-start)
- a84e231 content(real-madrid-hub): cold-start fix — price-first intro, 5-question FAQ for AI citability, player names (Vinicius Jr/Mbappé/Bellingham) — 0 impressions → give ChatGPT quotable facts

_A quiet property is not necessarily a broken one: the queue skips a night when no page is close enough and no demand is unserved. Inventing work would be worse._