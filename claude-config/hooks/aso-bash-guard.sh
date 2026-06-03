#!/bin/bash
# PreToolUse hook on Bash — blocks ASO-related commands unless /aso-refresh
# was invoked recently. Forces the LLM through the canonical skill flow.
#
# Triggers on Bash commands that touch:
#   - py/aso/*.py | py/aso/*.sh
#   - fastlane/metadata/**
#   - **/store-listing/**
#   - aso-store-blitz.py | aso-store-release.py | aso-master-precheck.sh
#
# Blocks unless audit log shows /aso-refresh invocation in last 60 minutes.
# User can override: type "override aso bash" in a message; hook reads
# transcript and allows for the next 5 minutes.

set -e

AUDIT_LOG="$(cd "$(dirname "$0")/.." && pwd)/audit/skill-invocations.log"

# Read hook input
input="$(cat)"
command="$(python3 -c "
import json, sys
try:
    d = json.loads(sys.argv[1])
    tn = d.get('tool_name', d.get('toolName', ''))
    if tn != 'Bash':
        sys.exit(0)
    ti = d.get('tool_input', d.get('toolInput', {}))
    print(ti.get('command', ''))
except Exception:
    pass
" "$input" 2>/dev/null)"

[ -z "$command" ] && exit 0

# Check if command matches ASO patterns
case "$command" in
  *py/aso/*|*fastlane/metadata*|*store-listing*|*aso-store-blitz*|*aso-store-release*|*aso-master-precheck*|*aso-metadata.py*|*aso-play-batch-push*)
    pattern_matched=1 ;;
  *)
    exit 0 ;;
esac

# Check audit log for aso-refresh invocation in last 60 min
if [ -f "$AUDIT_LOG" ]; then
  cutoff=$(date -u -v-60M +'%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -d '60 minutes ago' +'%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)
  recent=$(awk -v c="$cutoff" -F' \\| ' '$1 >= c && $2 == "aso-refresh"' "$AUDIT_LOG" | tail -1)
  if [ -n "$recent" ]; then
    exit 0
  fi
fi

# Check for user override in recent transcript (rolling window)
# Claude Code passes session info in env CLAUDE_SESSION_ID; transcript at
# ~/.claude/projects/<encoded>/<session>.jsonl. Cheap check: grep last 100 lines.
session_dir="$HOME/.claude/projects"
if [ -d "$session_dir" ]; then
  recent_override=$(find "$session_dir" -name '*.jsonl' -mmin -10 -print0 2>/dev/null | xargs -0 tail -n 100 2>/dev/null | grep -c "override aso bash" || echo 0)
  if [ "$recent_override" -gt 0 ]; then
    exit 0
  fi
fi

# Block: emit JSON-format permission decision
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "ASO bash command blocked. Reason: command touches ASO scripts/metadata but the /aso-refresh skill was not invoked in the last 60 minutes (audit log: $AUDIT_LOG). Either invoke /aso-refresh first, or have the user type 'override aso bash' to allow the next 10 minutes."
  }
}
EOF

exit 0
