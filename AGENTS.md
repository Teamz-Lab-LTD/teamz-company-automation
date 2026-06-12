# Agent entry point (Cursor / Claude / any LLM)

You are inside **teamz-company-automation** — the company-wide automation toolbox
(SEO, ASO, store publishing, QA, stats, content distribution) used as a git
submodule by every Teamz Lab project.

Read in this order, before doing anything:

1. **[README.md](README.md)** — the complete index. Every script in this repo is
   listed there with a one-line purpose and a copy-paste command. Find your task
   in "Common tasks" (section 4) or the full index (section 5) — do not grep blindly.
2. **[CLAUDE.md](CLAUDE.md)** — the rulebook. Critical rules, API recipes,
   past-mistakes playbook. The rules apply to ALL agents, not just Claude.

Non-negotiable rules (full versions in CLAUDE.md):

- **Orchestrators first.** ASO work goes through `/aso-refresh <app-slug>` (or
  `py/aso/aso-store-blitz.py`) — never hand-pick leaf ASO scripts. Skipping the
  SEO leading-indicator scripts during ASO is the #1 historical mistake here.
- **Never fabricate metrics.** Numbers come from script output or they don't exist.
- **Cadence gate.** Store metadata edits respect the 28-day iOS / 56-day Android
  floor (`claude-config/memory/aso_cadence.md`). Signal pulls every 14 days.
- **Config, not code.** A missing-variable error is fixed in the host project's
  `.teamz-automation.env` or `~/.config/teamzlab/automation.base.env`, not by
  editing the script.
- Exit code `2` from a website-only script on an app project means "not
  applicable", not failure.

Setup for a new project or machine: README.md section 2 (five commands).
