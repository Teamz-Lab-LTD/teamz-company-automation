# Teamz Company Automation — AI Agent Instructions

This directory contains **48 Python scripts** for SEO, ASO, keyword research, competitor analysis, monitoring, and QA. Before writing custom code or inventing data, **check if a script already exists here**.

## Critical Rule

**Never fabricate keyword scores, search volumes, or metrics.** Run the existing scripts to get real data. If a script fails, fix it — don't work around it with made-up numbers.

## Before ANY ASO/Store Listing Task

**Use the orchestrator — one command does everything:**

```bash
# Full flow: 22 steps (keywords → volume → competitors → build → upload → guide manual steps)
python3 py/aso/aso-store-release.py

# Check what's done / what's pending
python3 py/aso/aso-store-release.py --status

# Run a specific step only
python3 py/aso/aso-store-release.py --step volume
```

The orchestrator tracks progress in `store-release-progress.json`. It calls all scripts in order, catches fabricated data via preflight, and prints exact instructions for manual steps (screenshots, content rating, data safety). Any team member can run it.

## Key Scripts (called by orchestrator, or run individually)

| Task | Script |
|------|--------|
| **Full store release** (22 steps) | `py/aso/aso-store-release.py` |
| **Keyword volume** (Bing + Trends + autocomplete) | `py/build-keyword-volume.py "kw1" "kw2"` |
| **Full ASO pipeline** (discover + score + CSV) | `py/aso/aso-keyword-pipeline.py` |
| **Pre/post-flight validation** | `py/aso/aso-preflight.py --pre` / `--post` |
| **Upload AAB** | `py/build-play-console.py upload --aab file.aab --track internal --commit` |
| **Push listing** | `py/build-play-console.py listing-push --file listing.json --commit` |
| **Copy-paste helper** | `py/aso/aso-copy-helper.py` (HTML with copy buttons for Play Console) |
| **Keyword autocomplete** | `py/aso/aso-keywords.py --suggest "term"` |
| **Competitor analysis** | `py/aso/aso-competitors.py --find "term"` |
| **Metadata audit** | `py/aso/aso-metadata.py --audit APP_ID` |

## Full Registry

See `automation-tool-registry.md` (this directory) for the complete mapping of every task to every script (48 scripts, 7 categories).

## Output Locations

- **Pipeline CSVs** (`master_keywords.csv`, `ios_keywords.csv`) go in the **project's** `automation_data/` directory (set via `TEAMZ_DATA_DIR` in `.teamz-automation.env`), NOT in this submodule's `data/` directory.
- **Transient script output** (`aso-keywords-latest.json`, etc.) goes in this submodule's `data/` directory.

## Config

Scripts read `.teamz-automation.env` from the host project. Key vars for ASO:
- `TEAMZ_ASO_KEYWORDS` — comma-separated seed keywords
- `TEAMZ_APP_IDS` — Apple numeric app ID
- `TEAMZ_PLAY_PACKAGE_NAME` — Android package name
- `TEAMZ_DATA_DIR` — where to write project-level output
