#!/bin/bash
# /aso-refresh self-test — runs the skill in dry-run mode and asserts
# the expected scripts/registry were read + winnability table emitted.
#
# Usage:
#   bash teamz-company-automation/sh/aso-refresh-selftest.sh <app-slug>
#
# Exit 0 = trust intact (every required step happened)
# Exit 1 = LLM skipped something — investigate before any real ASO run
#
# What it checks:
#   1. Registry file exists + readable
#   2. Cadence memo exists + readable
#   3. Skill file references registry (grep)
#   4. Skill file references aso-store-blitz.py
#   5. Symlink ~/.claude/commands/aso-refresh.md resolves to automation
#   6. Audit log writeable
#   7. Hook scripts exist + executable
#   8. Counts: scripts in py/aso/ vs registry mentions
#
# This is a STATIC check — it does NOT actually invoke /aso-refresh
# (that takes 45-60 min and hits live APIs). It verifies the system
# the LLM uses is wired correctly.

set -e

SUBMODULE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_HOME="$HOME/.claude"
APP_SLUG="${1:-devicegpt}"
fail=0

check() {
  local name="$1"
  local cond="$2"
  if eval "$cond" >/dev/null 2>&1; then
    echo "  [PASS] $name"
  else
    echo "  [FAIL] $name"
    fail=$((fail + 1))
  fi
}

echo "==> /aso-refresh self-test ($APP_SLUG) at $(date -u +%FT%TZ)"
echo ""

echo "== File presence =="
check "registry exists" "[ -f '$SUBMODULE_ROOT/claude-config/aso-script-registry.md' ]"
check "cadence memo exists" "[ -f '$SUBMODULE_ROOT/claude-config/memory/aso_cadence.md' ]"
check "skill file exists" "[ -f '$SUBMODULE_ROOT/claude-config/commands/aso-refresh.md' ]"
check "skill audit hook exists" "[ -x '$SUBMODULE_ROOT/claude-config/hooks/skill-invocation-audit.sh' ]"
check "aso bash guard exists" "[ -x '$SUBMODULE_ROOT/claude-config/hooks/aso-bash-guard.sh' ]"
check "aso-store-blitz.py exists" "[ -f '$SUBMODULE_ROOT/py/aso/aso-store-blitz.py' ]"
check "aso-master-precheck.sh exists" "[ -f '$SUBMODULE_ROOT/py/aso/aso-master-precheck.sh' ]"

echo ""
echo "== Symlink wiring (~/.claude/ -> automation) =="
check "command symlink exists" "[ -L '$CLAUDE_HOME/commands/aso-refresh.md' ]"
check "command symlink resolves correctly" "[ \"\$(readlink '$CLAUDE_HOME/commands/aso-refresh.md')\" = '$SUBMODULE_ROOT/claude-config/commands/aso-refresh.md' ]"

# Memory file path encodes project root
proj_encoded="$(echo "$(cd "$SUBMODULE_ROOT/.." && pwd)" | sed -e 's|/|-|g' -e 's| |-|g')"
mem_link="$CLAUDE_HOME/projects/$proj_encoded/memory/aso_cadence.md"
check "memory symlink exists" "[ -L '$mem_link' ]"

echo ""
echo "== Skill body coverage (grep registry contents) =="
SKILL="$SUBMODULE_ROOT/claude-config/commands/aso-refresh.md"
check "skill references aso-script-registry.md" "grep -q 'aso-script-registry.md' '$SKILL'"
check "skill references aso-store-blitz.py" "grep -q 'aso-store-blitz.py' '$SKILL'"
check "skill references aso-master-precheck.sh" "grep -q 'aso-master-precheck.sh' '$SKILL'"
check "skill references cadence file" "grep -q 'aso_cadence.md' '$SKILL'"
check "skill mandates winnability table" "grep -q 'Winnable?' '$SKILL'"
check "skill names SIGNAL mode sidecars" "grep -q 'build-keyword-volume' '$SKILL'"
check "skill names REWRITE mode sidecars" "grep -q 'build-competitor-gaps' '$SKILL'"
check "skill references seo-dataforseo skill" "grep -q 'seo-dataforseo' '$SKILL'"
check "skill references seo-google skill" "grep -q 'seo-google' '$SKILL'"

echo ""
echo "== Registry coverage (vs py/aso/ on disk) =="
disk_aso=$(ls "$SUBMODULE_ROOT"/py/aso/*.py "$SUBMODULE_ROOT"/py/aso/*.sh 2>/dev/null | grep -v __pycache__ | grep -v __init__.py | grep -v _aso_common.py | wc -l | tr -d ' ')
listed_aso=$(grep -cE '^\| `aso-' "$SUBMODULE_ROOT/claude-config/aso-script-registry.md")
echo "  Scripts in py/aso/: $disk_aso (excluding __init__ and _aso_common)"
echo "  Registry entries  : $listed_aso"
if [ "$listed_aso" -ge $((disk_aso - 2)) ]; then
  echo "  [PASS] registry coverage adequate (within 2 of disk count)"
else
  echo "  [FAIL] registry missing $((disk_aso - listed_aso)) scripts — update aso-script-registry.md"
  fail=$((fail + 1))
fi

echo ""
echo "== Audit log (user-global ~/.config/teamzlab/audit/ — shared across all app projects) =="
AUDIT_LOG="$HOME/.config/teamzlab/audit/skill-invocations.log"
mkdir -p "$(dirname "$AUDIT_LOG")"
check "audit dir writeable" "touch '$(dirname "$AUDIT_LOG")/.testwrite' && rm '$(dirname "$AUDIT_LOG")/.testwrite'"

if [ -f "$AUDIT_LOG" ]; then
  total_calls=$(wc -l < "$AUDIT_LOG" | tr -d ' ')
  aso_calls=$(grep -c '| aso-refresh |' "$AUDIT_LOG" 2>/dev/null || echo 0)
  last_aso=$(grep '| aso-refresh |' "$AUDIT_LOG" 2>/dev/null | tail -1 || echo "(never)")
  echo "  Total skill invocations logged: $total_calls"
  echo "  /aso-refresh invocations      : $aso_calls"
  echo "  Most recent /aso-refresh      : $last_aso"
else
  echo "  (audit log not created yet — first skill invocation will create it)"
fi

echo ""
echo "== Git tracking =="
cd "$SUBMODULE_ROOT"
check "registry is git-tracked" "git ls-files --error-unmatch claude-config/aso-script-registry.md"
check "skill is git-tracked" "git ls-files --error-unmatch claude-config/commands/aso-refresh.md"
check "hooks are git-tracked" "git ls-files --error-unmatch claude-config/hooks/skill-invocation-audit.sh"

echo ""
echo "== Summary =="
if [ $fail -eq 0 ]; then
  echo "[PASS] all checks. System wired correctly — trust intact."
  echo ""
  echo "Note: this is a STATIC check. To verify a real /aso-refresh run,"
  echo "actually invoke '/aso-refresh $APP_SLUG' in Claude Code + check"
  echo "the audit log afterwards: grep aso-refresh $AUDIT_LOG"
  exit 0
else
  echo "[FAIL] $fail checks failed. Fix above before any real ASO work."
  exit 1
fi
