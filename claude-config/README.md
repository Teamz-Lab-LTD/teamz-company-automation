# claude-config/

**Canonical Claude Code user-global config for the Teamz Lab toolbox.** Lives in this git-tracked submodule so a new machine recovers the full LLM setup from a clone + one script. Without this folder, Claude Code on a fresh PC has none of the workflow rules, skill files, or locked memory the user spent weeks building.

## What's in here

| Path | Type | Symlinked to | Purpose |
|------|------|--------------|---------|
| `commands/aso-refresh.md` | Slash command | `~/.claude/commands/aso-refresh.md` | End-to-end ASO orchestrator entry point. Any LLM session reads this when user types `/aso-refresh`. |
| `memory/aso_cadence.md` | Project memory | `~/.claude/projects/<encoded-cwd>/memory/aso_cadence.md` | Locked platform-split cadence rule (28d iOS / 56d Android). |
| `CLAUDE-md-additions.md` | Reference text | NOT symlinked | Snippets to paste manually into `~/.claude/CLAUDE.md` global rules on a new machine. CLAUDE.md is user-specific so we don't symlink the whole file. |

Add files here as new rules get formalized. Each must be referenced from `setup-symlinks.sh` so it wires automatically.

## New-PC bootstrap (4 commands)

```bash
# 1) Clone the host repo + submodule
git clone <host-repo-url> ~/Projects/teamz-lab-generic-landing-pages
cd ~/Projects/teamz-lab-generic-landing-pages
git submodule update --init --recursive

# 2) Wire symlinks into ~/.claude/
bash teamz-company-automation/setup-symlinks.sh

# 3) Paste CLAUDE.md additions
# Open teamz-company-automation/claude-config/CLAUDE-md-additions.md in your editor.
# Append any section not already in ~/.claude/CLAUDE.md.

# 4) Restart Claude Code to pick up the new commands + memory
```

After this:
- `/aso-refresh` slash command works.
- Memory file `aso_cadence.md` loads on Claude Code session start.
- Any future LLM session knows to invoke `/aso-refresh` before touching ASO (per the global rule pasted in step 3).

## Why this exists (the original bug)

Before 2026-06-03, all the user's Claude Code config lived in `~/.claude/` — outside any git repo. PC swap, accidental delete, or fresh install = total loss. The user spent weeks building 28 ASO scripts + cadence rules + skill orchestration; none of it survived a backup gap.

Fix: source of truth here in the submodule (git-tracked, push/pull across machines). `~/.claude/` files become symlinks. Setup script re-wires on demand.

## What's NOT in here (intentional)

- **User-personal CLAUDE.md global** — kept in `~/.claude/CLAUDE.md` because it has personal sections (English coach, current job-search state, etc.). The `CLAUDE-md-additions.md` covers the project-rule subset that DOES belong in git.
- **Per-app `.claude/` project folders** — those belong in each app repo, not this central automation folder.
- **Other Claude skills shipped by the automation submodule** — already handled at `teamz-company-automation/skills/<name>/SKILL.md` by the older symlink-to-host-`.claude/skills` block.

## Conflict resolution

If a symlink already exists at `~/.claude/commands/<name>.md` pointing somewhere ELSE (not this folder), `setup-symlinks.sh` overwrites it with the canonical version from here. If you want to keep a personal override, copy it elsewhere first.
