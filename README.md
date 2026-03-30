# teamz-company-automation

Shared **Python + shell** tooling for Teamz Lab: content distribution, Google Search Console / GA4 / AdSense / PageSpeed, rank tracking, backlinks, indexing, and encrypted secrets backup.

## Layout

| Path | Contents |
|------|-----------|
| `sh/` | Shell entrypoints (`.sh`) — Search Console, analytics, PageSpeed, SEO dashboard, secrets |
| `py/` | Python tools (`.py`) — keyword intel, rank tracker, indexing, backlinks, auth helpers |
| `data/` | JSON data (rank history, backlinks) — committed for company-wide history |
| `distribute/` | Multi-platform publishing (`distribute.py`, articles, `history.json`) |

Teamz Lab Tools links `scripts/*` → `teamz-company-automation/sh/*` and `py/*` via symlinks, so commands like `python3 scripts/build-keyword-intel.py` stay unchanged.

## Clone as submodule

```bash
git submodule add https://github.com/Teamz-Lab-LTD/teamz-company-automation.git teamz-company-automation
git submodule update --init --recursive
```

## Setup

- Copy `distribute/config.example.json` to `distribute/config.json` and add API keys (gitignored).
- Google tokens: `~/.config/teamzlab/` (see your site’s Search Console / Analytics docs).
- **Secrets backup:** `sh/secrets-export.sh` / `sh/secrets-import.sh` (or via `scripts/` symlinks). Default GPG output: parent of this repo (e.g. `teamzlab-tools/teamzlab-secrets.gpg`).

## Site audit (`build-seo-dashboard.sh --audit`)

Crawls the **host** static site (parent of this submodule). Override:

```bash
TEAMZ_HOST_SITE_ROOT=/path/to/site ./sh/build-seo-dashboard.sh --audit
```

## QA server (`py/qa-server.py`)

Serves the Teamz site root when `index.html` exists next to the submodule. Override: `TEAMZ_QA_SITE_ROOT`.
