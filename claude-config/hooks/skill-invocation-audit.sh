#!/bin/bash
# PostToolUse hook on Skill tool — appends every invocation to audit log.
# Wired by setup-symlinks.sh into ~/.claude/hooks/. Source-of-truth here in
# the automation submodule so log file pattern survives PC swap.
#
# Audit log location: teamz-company-automation/claude-config/audit/skill-invocations.log
# (git-tracked — user can grep history of every skill call across all machines)
#
# Input via stdin: JSON from Claude Code harness — { "tool_name": "Skill",
# "tool_input": { "skill": "...", "args": "..." }, ... }

set -e

# User-global audit log. Lives at ~/.config/teamzlab/audit/ (same parent as
# the cred files in CLAUDE.md). Works from ANY app project — you open a
# conversation in debugger/, toss_app/, top_3_picks/, etc., and every Skill
# call lands in the same log. Grep from anywhere:
#   grep aso-refresh ~/.config/teamzlab/audit/skill-invocations.log
# Not git-tracked (audit is transient forensic, not source state).
AUDIT_LOG="$HOME/.config/teamzlab/audit/skill-invocations.log"
mkdir -p "$(dirname "$AUDIT_LOG")"

# Read JSON from stdin (Claude Code passes hook input as JSON)
input="$(cat)"

# Extract skill name + args via python (always available on macOS)
skill_name="$(python3 -c "
import json, sys
try:
    d = json.loads(sys.argv[1])
    tn = d.get('tool_name', d.get('toolName', ''))
    if tn != 'Skill':
        sys.exit(0)
    ti = d.get('tool_input', d.get('toolInput', {}))
    print(ti.get('skill', '?'))
except Exception as e:
    pass
" "$input" 2>/dev/null)"

# Only log Skill invocations
if [ -n "$skill_name" ]; then
  ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  cwd="$(pwd)"
  echo "$ts | $skill_name | cwd=$cwd" >> "$AUDIT_LOG"
fi

exit 0
