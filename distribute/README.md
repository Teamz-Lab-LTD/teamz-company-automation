# distribute/ — multi-platform content publishing

Content distribution hub: posts articles, pins, and videos to 11+ platforms with rate limits and history. Main entry: [`distribute.py`](./distribute.py) (post/queue/flush/status across devto, hashnode, medium, blogger, wordpress, tumblr, bluesky, mastodon, github, google-sites, pinterest). One-time per-platform auth scripts below; tokens live in `config.json` (gitignored, template: [`config.example.json`](./config.example.json)). Video pipeline lives in [`remotion/`](./remotion/).

| File | What it does | Typical command |
|---|---|---|
| [`TIKTOK-SETUP.md`](./TIKTOK-SETUP.md) | TikTok app review status and the credential-swap steps to run after approval. | — |
| [`articles`](./articles) | 181 ready-to-publish markdown articles (finance calculators, free-tool roundups, country-specific tax tools). | — |
| [`awesome-list-tracker.md`](./awesome-list-tracker.md) | Historical log of awesome-list PRs; program discontinued 2026-04-29 after GitHub spam flag. | — |
| [`blogger-auth.py`](./blogger-auth.py) | One-time Google OAuth for Blogger API; saves tokens and blog ID to config.json. | `python3 scripts/distribute/blogger-auth.py` |
| [`config.example.json`](./config.example.json) | Template for platform API keys/tokens; copy to config.json (gitignored). | — |
| [`distribute.py`](./distribute.py) | Main publisher CLI: post/edit/delete/queue articles to devto, hashnode, medium, blogger, wordpress, tumblr, bluesky, mastodon, github, google-sites, pinterest. | `python3 scripts/distribute/distribute.py next` |
| [`drafts`](./drafts) | 43 unpublished article drafts; 'distribute.py next' picks the highest-priority one. | — |
| [`google-sites-auth.py`](./google-sites-auth.py) | Interactive setup for the Google Sites bridge; configures the Apps Script web-app URL. | `python3 scripts/distribute/google-sites-auth.py` |
| [`google-sites-bridge.gs`](./google-sites-bridge.gs) | Apps Script web app: REST bridge that lets distribute.py create pages on Google Sites. | — |
| [`history.json`](./history.json) | Record of every post per platform; powers duplicate detection and status command. | — |
| [`pin-images`](./pin-images) | 2,058 pre-rendered Pinterest pin images, organized by board (finance, devtech, general, all-tools, top-tools). | — |
| [`pinterest-auth.py`](./pinterest-auth.py) | One-time Pinterest OAuth2; creates refreshable token for pin posting. | `python3 scripts/distribute/pinterest-auth.py` |
| [`pinterest-upgrade-script.md`](./pinterest-upgrade-script.md) | Video script and guide for applying to Pinterest Standard Access. | — |
| [`queue.json`](./queue.json) | Posts waiting for rate limits to clear; flushed by 'distribute.py flush'. | — |
| [`remotion`](./remotion) | Remotion video factory: plans, renders, and uploads short tool-promo videos to YouTube, TikTok, Instagram. | — |
| [`remotion/capture-tool.js`](./remotion/capture-tool.js) | Playwright screenshot capture of tool pages for tutorial videos. | `node distribute/remotion/capture-tool.js --url /ai/grammar-checker/` |
| [`remotion/content-engine.py`](./remotion/content-engine.py) | Generates SEO-optimized video plans from free data (Trends, autocomplete, Search Console, ASO keywords). | `python3 distribute/remotion/content-engine.py --count 30` |
| [`remotion/render-batch.js`](./remotion/render-batch.js) | Renders batches of reels with Remotion from video plans or the tool index. | `node distribute/remotion/render-batch.js --from-plans` |
| [`remotion/upload/instagram-upload.js`](./remotion/upload/instagram-upload.js) | Uploads Reels via Meta Graph API; limited to 1/day, 4/week. | `node distribute/remotion/upload/instagram-upload.js` |
| [`remotion/upload/tiktok-auth.js`](./remotion/upload/tiktok-auth.js) | One-time TikTok OAuth for the Content Posting API. | `node distribute/remotion/upload/tiktok-auth.js` |
| [`remotion/upload/tiktok-upload.js`](./remotion/upload/tiktok-upload.js) | Uploads videos to TikTok inbox drafts; enforces 2/day, 5/week limits. | `node distribute/remotion/upload/tiktok-upload.js` |
| [`remotion/upload/youtube-upload.js`](./remotion/upload/youtube-upload.js) | Uploads a video to YouTube as private, then auto-publishes at the best time. | `node distribute/remotion/upload/youtube-upload.js --from-history` |
| [`remotion/youtube-autopilot.js`](./remotion/youtube-autopilot.js) | One-command pipeline: decides Short vs Tutorial, renders, uploads, tracks status. | `node distribute/remotion/youtube-autopilot.js` |
| [`tumblr-auth.py`](./tumblr-auth.py) | One-time Tumblr OAuth1; prints tokens for distribute.py. | `python3 scripts/distribute/tumblr-auth.py CONSUMER_KEY CONSUMER_SECRET` |
| [`wordpress-auth.py`](./wordpress-auth.py) | One-time WordPress.com OAuth; saves access token to config.json. | `python3 scripts/distribute/wordpress-auth.py CLIENT_ID CLIENT_SECRET` |
| [`youtube-auth.py`](./youtube-auth.py) | One-time YouTube Data API OAuth; reuses existing Google client, has --test mode. | `python3 scripts/distribute/youtube-auth.py` |

---
**Lost?** The repo-wide index lives in [`../README.md`](../README.md) (root README, section 5) and the agent rulebook in [`../CLAUDE.md`](../CLAUDE.md). This folder's table above is the complete list — every file here is in it.
