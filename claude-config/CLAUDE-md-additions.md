# CLAUDE.md additions — paste into ~/.claude/CLAUDE.md on new PC

This file holds Claude global-instruction snippets that should be merged into the user's `~/.claude/CLAUDE.md` whenever setting up a new machine. The user's CLAUDE.md has personal sections (English coach, etc.) so we don't symlink the whole file — instead we keep additions here for re-application.

After cloning this repo + running `setup-symlinks.sh`, open `~/.claude/CLAUDE.md` and merge any sections below that are missing.

---

## ASO Work — ALWAYS Use the /aso-refresh Skill, Never Run Scripts Manually
For ANY ASO task on a teamzlab app (title/subtitle/keyword/description/screenshot/competitor analysis):

**MANDATORY:** Invoke the `/aso-refresh <app-slug>` skill via Skill tool. Never propose ASO changes from memory or partial-script runs.

The skill is at `~/.claude/commands/aso-refresh.md` (symlinked from this automation repo's `claude-config/commands/aso-refresh.md`). It chains all 28 ASO scripts + supporting SEO/Play scripts in the correct order, applies the platform-split cadence rule (see memory `aso_cadence.md`), and produces a winnability table per stop-rules RULE-001.

Two modes auto-selected from `.last_refresh` timestamp:
- SIGNAL_ONLY (every 14 days) — data pull only, no metadata edit
- FULL_REWRITE (28d floor iOS / 56d floor Android) — produces draft, NEVER auto-pushes

Why this rule exists: the user has 28 ASO scripts in `teamz-company-automation/py/aso/` but no orchestrator wired them together for years. Each session re-derived which to run, skipped some, produced inconsistent recommendations. The skill fixes this. If you bypass it you repeat the past mistake.

If user asks for ASO without naming the app, ask which app first. If user asks for keyword/title pick directly, refuse + invoke `/aso-refresh` first to generate the winnability table that RULE-001 requires.

---

---

## Settings.json hooks — register the audit + ASO bash guard

After running `setup-symlinks.sh` on a new PC, open `~/.claude/settings.json` (create if missing — `{}` is valid). Merge in these hook entries — they wire the two mechanical guards that prevent ASO-related cheating:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          { "type": "command", "command": "~/.claude/hooks/skill-invocation-audit.sh" }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "~/.claude/hooks/aso-bash-guard.sh" }
        ]
      }
    ]
  }
}
```

What they do:
- **`skill-invocation-audit.sh`** appends every Skill tool call to `teamz-company-automation/claude-config/audit/skill-invocations.log` (git-tracked — full history across machines). User greps anytime for "did /aso-refresh actually run?"
- **`aso-bash-guard.sh`** blocks any Bash command touching `py/aso/*`, `fastlane/metadata/**`, `**/store-listing/**`, or the core ASO orchestrator scripts UNLESS `/aso-refresh` was invoked in the last 60 minutes. User overrides by typing "override aso bash" in a message (active 10 min).

To verify the wiring after merging into settings.json:

```bash
bash teamz-company-automation/sh/aso-refresh-selftest.sh devicegpt
```

Exit 0 = all guards intact. Exit 1 = something missing — fix before any real ASO work.

(Add more snippets here as new rules get formalized. Each new section gets a header + a clear "what this is" + "where it goes" line.)
