# py/aso/ — App Store Optimization toolkit

py/aso/ is the App Store Optimization toolkit — a free, mostly stdlib alternative to paid tools like AppTweak. It covers the whole store lifecycle: keyword research, competitor spying, screenshot generation, metadata localization, pushing listings to Google Play and App Store Connect, and tracking ranks/installs afterward. The MAIN orchestrator is aso-store-blitz.py (one command runs the entire ship pipeline end to end); aso-master-precheck.sh is the data-gathering orchestrator run before writing any ASO copy, and aso-store-release.py orchestrates first-time Play Store setup — everything else is a leaf tool those three (or you) call directly.

**Do NOT hand-pick these scripts for ASO work.** Go through `/aso-refresh <app-slug>` (Claude) or [`aso-store-blitz.py`](./aso-store-blitz.py) — the orchestrators run these in the correct order including the SEO leading-indicator scripts. Which script belongs to which refresh mode: [`../../claude-config/aso-script-registry.md`](../../claude-config/aso-script-registry.md).

| File | What it does | Typical command |
|---|---|---|
| [`__init__.py`](./__init__.py) | Package marker; states the suite is a free AppTweak alternative built on _aso_common helpers. | — |
| [`_aso_common.py`](./_aso_common.py) | Shared library: iTunes/Play API wrappers, autocomplete, review parser, tokenizer, rate limiter. Imported, never run. | — |
| [`asc-screenshots-push.rb`](./asc-screenshots-push.rb) | Uploads screenshots straight to App Store Connect via Spaceship, avoiding fastlane deliver silent failures. | `TARGET_VERSION=2.1.0 LOCALES=ALL ruby scripts/asc-screenshots-push.rb` |
| [`aso-admob-rpm-benchmarks.py`](./aso-admob-rpm-benchmarks.py) | Local database of mobile ad eCPM benchmarks by category, format, country; rough revenue projections. | `python3 scripts/aso-admob-rpm-benchmarks.py --top 10` |
| [`aso-competitors.py`](./aso-competitors.py) | Competitor intelligence from iTunes Search: find rivals, analyze listings, extract keywords, spot gaps. | `python3 scripts/aso-competitors.py --find "fitness tracker"` |
| [`aso-compose-screenshot.py`](./aso-compose-screenshot.py) | Composes one store screenshot: device frame plus hero/subtitle text on a colored background (Pillow only). | `python3 scripts/aso-compose-screenshot.py --raw shot.png --hero "TITLE" --output out.jpg` |
| [`aso-copy-helper.py`](./aso-copy-helper.py) | Builds an HTML page with one-click copy buttons for pasting listing text into Play Console. | `python3 scripts/aso-copy-helper.py` |
| [`aso-deep-research-prompt.py`](./aso-deep-research-prompt.py) | Generates a ready-made ChatGPT Deep Research prompt for an app's keywords and competitors. | `python3 scripts/aso-deep-research-prompt.py --app <slug> --keywords-file kws.txt` |
| [`aso-experiments.py`](./aso-experiments.py) | Logs store-listing A/B tests, snapshots impressions/installs per variant, reports winners. | `python3 scripts/aso-experiments.py list` |
| [`aso-firebase-events.py`](./aso-firebase-events.py) | Pulls Firebase Analytics events from BigQuery for funnel and user-behavior analysis. | `python3 scripts/aso-firebase-events.py --project <slug> --days 30` |
| [`aso-gemini-edit.py`](./aso-gemini-edit.py) | Minimal Gemini (Nano Banana) REST wrapper that AI-edits a screenshot image from a prompt. | `python3 scripts/aso-gemini-edit.py --prompt "..." --image in.png --output out.jpg` |
| [`aso-generate-batch.py`](./aso-generate-batch.py) | Batch-generates all store screenshots from a project presets JSON via the composer script. | `python3 scripts/aso-generate-batch.py --presets automation_data/aso_screenshot_presets.json` |
| [`aso-guide.py`](./aso-guide.py) | Teaches ASO basics and produces app-specific checklists, content plans, and LLM prompts from iTunes data. | `python3 scripts/aso-guide.py --learn` |
| [`aso-icon-audit.py`](./aso-icon-audit.py) | QA-checks app icon PNGs: size, brightness, contrast, transparency, frame fill — flags store-killing issues. | `python3 scripts/aso-icon-audit.py --strict` |
| [`aso-keyword-pipeline.py`](./aso-keyword-pipeline.py) | Full keyword research pipeline: autocomplete discovery, competitor mining, scoring — outputs master/ios keyword CSVs. | `python3 scripts/aso-keyword-pipeline.py` |
| [`aso-keywords.py`](./aso-keywords.py) | Keyword CLI: suggest, expand, trending, long-tail via Apple/Play autocomplete and iTunes signals. | `python3 scripts/aso-keywords.py --suggest "photo editor"` |
| [`aso-localize-metadata-template.py`](./aso-localize-metadata-template.py) | Template to copy into a project as localize_metadata.py; fill hand-made translations, writes fastlane locale files. | — |
| [`aso-localize.py`](./aso-localize.py) | Auto-fills fastlane iOS metadata (keywords, subtitle, name, promo) for all 40 locales. | `python3 scripts/aso-localize.py --translate` |
| [`aso-master-precheck.sh`](./aso-master-precheck.sh) | Orchestrator: runs every data source (Play reports, keywords, competitors, Firebase) into one master JSON before writing copy. | `./scripts/aso-master-precheck.sh --package <pkg> --keywords-file kws.txt` |
| [`aso-metadata.py`](./aso-metadata.py) | Audits, scores, compares, and optimizes iOS/Android listing metadata against character limits and keyword data. | `python3 scripts/aso-metadata.py --audit <app-id>` |
| [`aso-openrouter-image-edit.py`](./aso-openrouter-image-edit.py) | OpenRouter image-to-image wrapper (cheap Gemini model, ~$0.04/edit) for screenshot polish. | `python3 scripts/aso-openrouter-image-edit.py --prompt "..." --image in.png --output out.png` |
| [`aso-pad-resize.py`](./aso-pad-resize.py) | Pads a screenshot with background color then resizes to exact target device dimensions. | `python3 scripts/aso-pad-resize.py --src in.jpg --dst out.jpg --width 1080 --height 1920 --bg "#CDFF1A"` |
| [`aso-play-batch-push.py`](./aso-play-batch-push.py) | Pushes all 39 Play Console listings plus graphics in one androidpublisher edit transaction. | `python3 scripts/aso-play-batch-push.py` |
| [`aso-preflight.py`](./aso-preflight.py) | Validates ASO work is backed by real data — run before and after writing any listing content. | `python3 scripts/aso-preflight.py --full` |
| [`aso-priority-export.py`](./aso-priority-export.py) | Exports tools_priority.json so the in-app tool ordering matches current ASO keyword positioning. | `python3 scripts/aso-priority-export.py` |
| [`aso-release-notes-gen.py`](./aso-release-notes-gen.py) | Generates multi-locale release-notes JSON (36 locales, ≤500 chars each) from git log. | `python3 scripts/aso-release-notes-gen.py --version 1.4.0` |
| [`aso-reviews.py`](./aso-reviews.py) | Fetches and analyzes App Store reviews: keywords, sentiment, complaints, praise, reply prompts, trends. | `python3 scripts/aso-reviews.py <app-id> --complaints` |
| [`aso-seo-merge.py`](./aso-seo-merge.py) | Merges ASO scores, SEO volume, web rank, and Deep Research into one combined-score master keyword CSV. | `python3 scripts/aso-seo-merge.py --top 50` |
| [`aso-store-blitz.py`](./aso-store-blitz.py) | MAIN orchestrator: one command runs screenshots, localization, Play push, and Apple submit with no prompts. | `python3 scripts/aso-store-blitz.py  (from app project root; --dry-run to validate only)` |
| [`aso-store-release.py`](./aso-store-release.py) | Orchestrator for first-time Play Store setup: keywords, listing, build, upload steps with progress tracking. | `python3 scripts/aso-store-release.py --status` |
| [`aso-tablet-from-phone.py`](./aso-tablet-from-phone.py) | Derives iPad/tablet screenshot presets from a phone preset JSON so tablet shots are never forgotten. | `python3 scripts/aso-tablet-from-phone.py --phone automation_data/aso_screenshot_presets_ios.json` |
| [`aso-track.py`](./aso-track.py) | Records daily App Store search rank for watched keywords; reports movers over time. | `python3 scripts/aso-track.py --record <app-id>` |
| [`aso-velocity.py`](./aso-velocity.py) | Tracks install/download velocity and country breakdown from Play Console and App Store Connect reports. | `python3 scripts/aso-velocity.py --days 7` |

---
**Lost?** The repo-wide index lives in [`../../README.md`](../../README.md) (root README, section 5) and the agent rulebook in [`../../CLAUDE.md`](../../CLAUDE.md). This folder's table above is the complete list — every file here is in it.
