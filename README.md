# Teamz Company Automation

Shared **Python + shell** tooling for Teamz Lab: content distribution, Google Search Console / GA4 / AdSense / PageSpeed, rank tracking, backlinks, indexing, and encrypted secrets backup.

## Use in a project (git submodule)

From your site or app repo (e.g. Teamz Lab Tools):

```bash
git submodule add ../teamz-company-automation teamz-company-automation
git submodule update --init --recursive
```

Teamz Lab Tools mounts the same files under `scripts/` via symlinks so existing commands keep working:

`python3 scripts/build-keyword-intel.py`, `python3 scripts/distribute/distribute.py`, etc.

## Setup

- Copy `distribute/config.example.json` to `distribute/config.json` and fill API keys (file is gitignored).
- Google tokens live in `~/.config/teamzlab/` — see your site’s Search Console / Analytics setup docs.
- **Secrets backup:** run `secrets-export.sh` / `secrets-import.sh` from this directory (or via symlinks). Default GPG archive is written to the **parent** of this repo (e.g. `teamzlab-tools/teamzlab-secrets.gpg`).

## Site audit / HTML crawl

`build-seo-dashboard.sh --audit` crawls the **host** repository by default: parent directory of this submodule (`TEAMZ_HOST_SITE_ROOT`, default `..`). Override if needed:

```bash
TEAMZ_HOST_SITE_ROOT=/path/to/static-site ./build-seo-dashboard.sh --audit
```

## QA static server

`qa-server.py` serves the **parent** folder when it looks like a Teamz site (`index.html` present), else this repo. Override with `TEAMZ_QA_SITE_ROOT`.
