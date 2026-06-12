# py/web_automation/ — Playwright recipe framework

py/web_automation/ is a small Playwright-style browser-automation framework for admin chores that have no API: you write a "Recipe" class (yields work items, processes each in a logged-in browser), log into the site once with --debug, and the cookies persist in a per-site Chromium profile so later runs need no re-login. Recipes are discovered and run via `python3 -m web_automation run <name>` from the py/ directory; each recipe reads its data (yaml lists of posts, comments, form steps) from the host project's automation_data/ folder. py/product-hunt/ holds one script that assembles a complete Product Hunt launch package (tagline, description, thumbnail, gallery images) from the app's existing landing-page and ASO data, refreshing stale keyword data first.

Use this for sites that have NO API and no MCP support: write one recipe file per site, run it headed with `--debug` to watch it work. Full recipe-authoring guide: [`../../CLAUDE.md`](../../CLAUDE.md) § Web automation framework.

| File | What it does | Typical command |
|---|---|---|
| [`__init__.py`](./__init__.py) | Framework core: BrowserSession, Recipe base class, runner; persistent per-site Chromium profiles keep logins alive. | — |
| [`__main__.py`](./__main__.py) | CLI that lists recipes and runs one by name, passing extra flags to the recipe's parser. | `cd teamz-company-automation/py && python3 -m web_automation list` |
| [`recipes/__init__.py`](./recipes/__init__.py) | Recipes package doc: one module per site/task; data files live in host project's automation_data/. | — |
| [`recipes/blogger_post.py`](./recipes/blogger_post.py) | Bulk-creates Blogger draft or published posts from a yaml file by driving the Blogger UI. | `python3 -m web_automation run blogger_post -- --yaml automation_data/blogger_posts.yaml` |
| [`recipes/generic_form_fill.py`](./recipes/generic_form_fill.py) | Fills any web form from a yaml list of steps (goto, fill, click, upload, wait). | `python3 -m web_automation run generic_form_fill -- --yaml my_form.yaml --profile <profile>` |
| [`recipes/play_console_icons.py`](./recipes/play_console_icons.py) | Uploads Play Games achievement icons to Play Console drafts via the web UI (no API exists). | `python3 -m web_automation run play_console_icons -- --dev-id <id> --app-id <id>` |
| [`recipes/reddit_comment.py`](./recipes/reddit_comment.py) | Posts one comment per Reddit thread from a yaml list; user must vet targets against sub rules. | `python3 -m web_automation run reddit_comment -- --yaml automation_data/reddit_comments.yaml` |

---
**Lost?** The repo-wide index lives in [`../../README.md`](../../README.md) (root README, section 5) and the agent rulebook in [`../../CLAUDE.md`](../../CLAUDE.md). This folder's table above is the complete list — every file here is in it.
