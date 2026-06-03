# Per-App Conversation Workflow

**Your real situation:** you open a Claude Code conversation in ONE app project at a time (debugger/, toss_app/, top_3_picks/, no-trace-code-chat/, zoyiai/, etc.), not in the landing-pages project. You expect `/aso-refresh`, the cadence rule, the registry, the hooks, and the audit log to ALL work from there.

This file documents how that works + the one-time setup you do per app project.

## What is shared globally (works from ANY conversation, in ANY project, with no per-conversation setup)

| Thing | Where | Why it works everywhere |
|-------|-------|-------------------------|
| `/aso-refresh` slash command | `~/.claude/commands/aso-refresh.md` → symlink to landing-pages submodule | Claude Code reads `~/.claude/commands/` regardless of cwd |
| `~/.claude/hooks/skill-invocation-audit.sh` | symlink to landing-pages submodule | hooks are user-global, fire on every conversation |
| `~/.claude/hooks/aso-bash-guard.sh` | same | same |
| Audit log | `~/.config/teamzlab/audit/skill-invocations.log` | user-global file — one log captures every Skill call from every conversation in every app |
| CLAUDE.md global rule (mandates /aso-refresh) | `~/.claude/CLAUDE.md` | loaded on every conversation |

## What is per-project (must be set up once per app)

| Thing | Where | Why per-project |
|-------|-------|-----------------|
| Memory file `aso_cadence.md` | `~/.claude/projects/<encoded-app-cwd>/memory/aso_cadence.md` | Claude Code memory is per-project; the file path encodes the project's absolute cwd |
| Submodule clone | `<app-project>/teamz-company-automation/` (or `<app>/packages/team_mvp_kit/teamz-company-automation/` per the kit pattern) | Each app's git pulls its own working copy of the shared submodule |
| `scripts/` symlinks | `<app-project>/scripts/` | One-time `setup-symlinks.sh` per app exposes scripts there |

## One-time setup per app project

After cloning the app repo on a new PC (or after pulling new commits in the submodule):

```bash
cd ~/Projects/Teamz\ Lab\ Projects/teamz-projects/<app>
git submodule update --init --recursive          # pull latest submodule
bash teamz-company-automation/setup-symlinks.sh  # wires symlinks + creates memory dir if needed
```

That ONE script creates:
- `scripts/aso/`, `scripts/build-*.py`, etc. (symlinks to the submodule's scripts)
- `~/.claude/projects/<encoded-app-cwd>/memory/aso_cadence.md` → symlink to the submodule's canonical memory file (only if Claude Code has been opened in this project at least once, so the memory dir exists)
- `~/.claude/commands/aso-refresh.md` (idempotent — re-uses if already wired)
- `~/.claude/hooks/skill-invocation-audit.sh` + `~/.claude/hooks/aso-bash-guard.sh` (idempotent)

If the memory dir does not exist yet (Claude Code never opened in this project), the script prints a note. Open Claude Code once in that project, exit, then re-run `setup-symlinks.sh`. Now the memory symlink wires correctly.

## Why this works for your "one conversation per app" pattern

Scenario: you finished setup on all 5 app projects. Today you open Claude Code in `~/Projects/.../top_3_picks/` and type "write ASO for top3picks".

1. Claude sees the global CLAUDE.md rule → MUST invoke `/aso-refresh top3picks`.
2. `/aso-refresh` skill is at `~/.claude/commands/aso-refresh.md` — found regardless of cwd.
3. Skill reads `~/.claude/projects/<encoded-top3picks-cwd>/memory/aso_cadence.md` — symlinked to landing-pages submodule's canonical copy. Same content as if you opened conversation in landing-pages.
4. Skill reads `teamz-company-automation/claude-config/aso-script-registry.md` — uses the COPY of submodule that lives at `top_3_picks/teamz-company-automation/`. Content identical because both git repos pulled from same upstream.
5. Skill body invokes `aso-store-blitz.py` etc. — uses the COPY at `top_3_picks/teamz-company-automation/py/aso/aso-store-blitz.py`. Same script.
6. Skill's hook audit logs to `~/.config/teamzlab/audit/skill-invocations.log` — single user-global file. Logs every invocation from any app's conversation.

You can later grep that log from ANY terminal:
```bash
grep aso-refresh ~/.config/teamzlab/audit/skill-invocations.log
# Shows every /aso-refresh call across every app + every conversation, with timestamp + cwd
```

## When the submodule needs updating per app

The submodule is shared by reference but each app has its own working copy. When you push changes to the submodule from one app (e.g., landing-pages), other app projects don't auto-pull. You must:

```bash
# In each app project that has the submodule:
cd ~/Projects/Teamz\ Lab\ Projects/teamz-projects/<other-app>
cd teamz-company-automation && git pull origin main && cd ..
git add teamz-company-automation && git commit -m "chore: bump submodule"
```

OR pull at the host level:
```bash
git submodule update --remote --merge
```

Both methods bump that app's submodule pointer to the latest commit.

## Trust checks you can run from any app project

From any app's project root:

```bash
# 1. Static self-test (5 sec)
bash teamz-company-automation/sh/aso-refresh-selftest.sh <app-slug>

# 2. Audit recent skill invocations
tail -20 ~/.config/teamzlab/audit/skill-invocations.log

# 3. Specific app
grep '<app-slug>' ~/.config/teamzlab/audit/skill-invocations.log
```

All three work from any project, no special setup.

## What happens if /aso-refresh tries to run in a project where setup was not done

- Slash command runs (command symlink is user-global)
- Skill body tries to read `~/.claude/projects/<encoded-cwd>/memory/aso_cadence.md` → fails if symlink not created → skill stops with clear error
- User runs `bash teamz-company-automation/setup-symlinks.sh` once → memory wires → retry succeeds

Friction is one command per new app project, one time. After that, every conversation Just Works.
