#!/usr/bin/env bash
# install-claude-context.sh — wire Teamz kit context into a host project
#
# What this does (idempotent — safe to re-run any time):
#   1. Writes / refreshes the project's root CLAUDE.md with @-imports
#      to the kit's canonical knowledge files (house rules, UI guide,
#      Flutter standards, AI-agent instructions).
#   2. Creates .claude/skills symlinks so kit-tied skills auto-activate
#      in Claude Code sessions.
#   3. (Optional, --install-hooks) Points `git config core.hooksPath`
#      at the kit's .githooks dir so `git pull` / `git merge` auto-runs
#      this script when the kit submodule changes — keeping every
#      project in sync without manual remembering.
#
# Usage (from a host project root):
#   bash team_mvp_kit/teamz-company-automation/sh/install-claude-context.sh
#   bash team_mvp_kit/teamz-company-automation/sh/install-claude-context.sh --install-hooks
#   bash team_mvp_kit/teamz-company-automation/sh/install-claude-context.sh --check
#
# Exit codes:
#   0 = success (or already wired)
#   1 = kit not found / not a submodule at expected path
#   2 = --check was passed and context is stale / missing
set -euo pipefail

# ---------------------------------------------------------------------------
# Locate project root + kit root
# ---------------------------------------------------------------------------
# Canonical home: teamz-company-automation/sh/install-claude-context.sh
# Callers should invoke via the canonical path:
#   bash team_mvp_kit/teamz-company-automation/sh/install-claude-context.sh
# Legacy `team_mvp_kit/scripts/<name>` symlinks have been retired — do not
# rely on them in new tooling.
#
# So the script can't assume a fixed depth. Walk up from $PWD looking for
# the kit marker (`team_mvp_kit/pubspec.yaml`).
find_project_root() {
  local dir="$PWD"
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/team_mvp_kit/pubspec.yaml" ]] && \
       [[ -d "$dir/team_mvp_kit/prompts" ]]; then
      echo "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}

if ! PROJECT_ROOT="$(find_project_root)"; then
  echo "✗ Couldn't find a Teamz project root at or above $PWD." >&2
  echo "  Run this from a project that has team_mvp_kit at ./team_mvp_kit/." >&2
  exit 1
fi
KIT_ROOT="$PROJECT_ROOT/team_mvp_kit"

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------
INSTALL_HOOKS=0
CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --install-hooks) INSTALL_HOOKS=1 ;;
    --check)         CHECK_ONLY=1 ;;
    -h|--help)
      grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown arg: $arg" >&2; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# The list of kit files every project should have auto-loaded.
# Add to this list (and commit in the kit) when a new kit-wide prompt ships.
# ---------------------------------------------------------------------------
KIT_IMPORTS=(
  "team_mvp_kit/CLAUDE.md"
  "team_mvp_kit/prompts/teamz-ui-generation-guide.md"
  "team_mvp_kit/prompts/flutter-development-standards.md"
  "team_mvp_kit/prompts/ai-agent-instructions.md"
)

# ---------------------------------------------------------------------------
# Check kit files exist
# ---------------------------------------------------------------------------
missing=()
for rel in "${KIT_IMPORTS[@]}"; do
  if [[ ! -f "$PROJECT_ROOT/$rel" ]]; then
    missing+=("$rel")
  fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "✗ Kit is missing expected files:" >&2
  for m in "${missing[@]}"; do echo "   - $m" >&2; done
  echo "  Run 'git submodule update --remote team_mvp_kit' and try again." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Build the managed import block
# ---------------------------------------------------------------------------
MANAGED_BEGIN="<!-- claude-context:begin -->"
MANAGED_END="<!-- claude-context:end -->"

MANAGED_BLOCK="$MANAGED_BEGIN
> Managed by \`team_mvp_kit/teamz-company-automation/sh/install-claude-context.sh\`.
> Do not edit between the begin/end markers — re-run the script instead.

## Inherited from the kit (auto-loaded — do not duplicate below)
"
for rel in "${KIT_IMPORTS[@]}"; do
  MANAGED_BLOCK="$MANAGED_BLOCK
@$rel"
done
MANAGED_BLOCK="$MANAGED_BLOCK
$MANAGED_END"

CLAUDE_MD="$PROJECT_ROOT/CLAUDE.md"

# ---------------------------------------------------------------------------
# Check mode — exit 0 if fresh, 2 if stale / missing
# ---------------------------------------------------------------------------
if [[ $CHECK_ONLY -eq 1 ]]; then
  if [[ ! -f "$CLAUDE_MD" ]]; then
    echo "✗ No CLAUDE.md at project root. Run without --check to create."
    exit 2
  fi
  if ! grep -qF "$MANAGED_BEGIN" "$CLAUDE_MD"; then
    echo "✗ CLAUDE.md exists but has no managed import block."
    exit 2
  fi
  # Extract lines between begin/end markers (exclusive) using sed.
  # Markers contain no forward slashes so sed's / delimiter is safe.
  block_content="$(sed -n "/$MANAGED_BEGIN/,/$MANAGED_END/p" "$CLAUDE_MD")"
  for rel in "${KIT_IMPORTS[@]}"; do
    if ! printf '%s\n' "$block_content" | grep -qF "@$rel"; then
      echo "✗ CLAUDE.md managed block is missing @$rel"
      exit 2
    fi
  done
  echo "✓ CLAUDE.md context is up-to-date."
  exit 0
fi

# ---------------------------------------------------------------------------
# Write / refresh CLAUDE.md — preserve project-specific content
# ---------------------------------------------------------------------------
if [[ -f "$CLAUDE_MD" ]] && grep -qF "$MANAGED_BEGIN" "$CLAUDE_MD"; then
  # Replace the managed block by splicing head-before-BEGIN + new block
  # + tail-after-END. Avoids awk multi-line -v quoting issues.
  begin_line="$(grep -nF "$MANAGED_BEGIN" "$CLAUDE_MD" | head -1 | cut -d: -f1)"
  end_line="$(grep -nF "$MANAGED_END"   "$CLAUDE_MD" | head -1 | cut -d: -f1)"
  if [[ -z "$begin_line" || -z "$end_line" || "$end_line" -le "$begin_line" ]]; then
    echo "✗ Managed markers malformed in $CLAUDE_MD — fix by hand." >&2
    exit 1
  fi
  tmp="$(mktemp)"
  {
    if [[ "$begin_line" -gt 1 ]]; then
      sed -n "1,$((begin_line - 1))p" "$CLAUDE_MD"
    fi
    printf '%s\n' "$MANAGED_BLOCK"
    sed -n "$((end_line + 1)),\$p" "$CLAUDE_MD"
  } > "$tmp"
  mv "$tmp" "$CLAUDE_MD"
  echo "✓ Refreshed managed block in $CLAUDE_MD"
else
  # Fresh CLAUDE.md — prepend managed block, leave a Project-specific
  # section for the team to fill in.
  existing=""
  if [[ -f "$CLAUDE_MD" ]]; then
    existing="$(cat "$CLAUDE_MD")"
  fi
  {
    echo "# $(basename "$PROJECT_ROOT") — project rules"
    echo ""
    echo "$MANAGED_BLOCK"
    echo ""
    echo "## Project-specific"
    echo ""
    echo "_Add project-specific rules, positioning, personas, and wedge here._"
    if [[ -n "$existing" ]]; then
      echo ""
      echo "---"
      echo "<!-- previous CLAUDE.md content preserved below -->"
      echo ""
      echo "$existing"
    fi
  } > "$CLAUDE_MD"
  echo "✓ Wrote new $CLAUDE_MD"
fi

# ---------------------------------------------------------------------------
# Ensure .claude/skills exists + symlinks for kit-tied skills
# ---------------------------------------------------------------------------
mkdir -p "$PROJECT_ROOT/.claude/skills"

# Kit-tied skills live in .claude/skills inside the kit (or symlinked there
# from teamz-company-automation today). Either way, the host project just
# needs a symlink pointing at the kit's skills dir per skill.
KIT_SKILLS_DIR="$KIT_ROOT/.claude/skills"
if [[ -d "$KIT_SKILLS_DIR" ]]; then
  for skill_path in "$KIT_SKILLS_DIR"/*; do
    [[ -e "$skill_path" ]] || continue
    name="$(basename "$skill_path")"
    target="$PROJECT_ROOT/.claude/skills/$name"
    if [[ -L "$target" ]] || [[ ! -e "$target" ]]; then
      rm -f "$target"
      ln -s "../../team_mvp_kit/.claude/skills/$name" "$target"
      echo "✓ Linked skill: $name"
    else
      echo "⚠ Skipped $name — $target exists and is not a symlink"
    fi
  done
fi

# ---------------------------------------------------------------------------
# (Optional) install auto-refresh git hook
# ---------------------------------------------------------------------------
if [[ $INSTALL_HOOKS -eq 1 ]]; then
  HOOKS_DIR="$PROJECT_ROOT/.teamz-githooks"
  mkdir -p "$HOOKS_DIR"
  cat > "$HOOKS_DIR/post-merge" <<'HOOK'
#!/usr/bin/env bash
# Auto-installed by team_mvp_kit/teamz-company-automation/sh/install-claude-context.sh
# Re-runs the Claude context refresh if the kit submodule changed in
# this merge/pull. Safe no-op otherwise.
set -e
if git diff --name-only HEAD@{1} HEAD 2>/dev/null | grep -q '^team_mvp_kit'; then
  bash team_mvp_kit/teamz-company-automation/sh/install-claude-context.sh || true
fi
HOOK
  chmod +x "$HOOKS_DIR/post-merge"
  # Also refresh on checkout (branch switch pulls in a different kit SHA).
  cp "$HOOKS_DIR/post-merge" "$HOOKS_DIR/post-checkout"
  chmod +x "$HOOKS_DIR/post-checkout"

  git -C "$PROJECT_ROOT" config core.hooksPath ".teamz-githooks"
  echo "✓ Installed auto-refresh git hooks at $HOOKS_DIR"
  echo "  (git config core.hooksPath set to .teamz-githooks)"
fi

echo ""
echo "Done. Claude Code sessions in this project will now auto-load:"
for rel in "${KIT_IMPORTS[@]}"; do echo "   @$rel"; done
