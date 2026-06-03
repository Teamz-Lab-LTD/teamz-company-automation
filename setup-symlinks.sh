#!/bin/bash
# Creates scripts/ symlinks in the host project pointing to this submodule.
# Run from the host project root:
#   bash teamz-company-automation/setup-symlinks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")" && pwd)"
HOST_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SUBMOD_REL="teamz-company-automation"

cd "$HOST_ROOT"
mkdir -p scripts

created=0
skipped=0

for f in "$SCRIPT_DIR"/py/*.py; do
  [ -f "$f" ] || continue
  base="$(basename "$f")"
  [ "$base" = "_teamz_config.py" ] && continue
  target="../$SUBMOD_REL/py/$base"
  if [ -L "scripts/$base" ]; then
    skipped=$((skipped + 1))
  else
    rm -f "scripts/$base"
    ln -sf "$target" "scripts/$base"
    created=$((created + 1))
  fi
done

for f in "$SCRIPT_DIR"/sh/*.sh; do
  [ -f "$f" ] || continue
  base="$(basename "$f")"
  target="../$SUBMOD_REL/sh/$base"
  if [ -L "scripts/$base" ]; then
    skipped=$((skipped + 1))
  else
    rm -f "scripts/$base"
    ln -sf "$target" "scripts/$base"
    created=$((created + 1))
  fi
done

for d in data/rank-history.json data/backlinks-data.json data/backlinks-history.json data/seo-logs data/seo-latest-report.txt; do
  base="$(basename "$d")"
  target="../$SUBMOD_REL/$d"
  if [ -L "scripts/$base" ]; then
    skipped=$((skipped + 1))
  else
    rm -f "scripts/$base" 2>/dev/null; rm -rf "scripts/$base" 2>/dev/null
    ln -sf "$target" "scripts/$base"
    created=$((created + 1))
  fi
done

# ASO module — symlink as scripts/aso/ directory
if [ -d "$SCRIPT_DIR/py/aso" ] && [ ! -L "scripts/aso" ]; then
  rm -rf "scripts/aso" 2>/dev/null
  ln -sf "../$SUBMOD_REL/py/aso" "scripts/aso"
  created=$((created + 1))
elif [ -L "scripts/aso" ]; then
  skipped=$((skipped + 1))
fi

if [ -d "$SCRIPT_DIR/distribute" ] && [ ! -L "scripts/distribute" ]; then
  ln -sf "../$SUBMOD_REL/distribute" "scripts/distribute"
  created=$((created + 1))
fi

# Claude Code skills provided by this submodule — symlinked into the host
# project's .claude/skills/ so Claude auto-discovers them. Every skill that
# lives at skills/<name>/ here gets exposed at .claude/skills/<name>/ in the
# host project. Depth of the symlink target is 3 levels (../../..) because
# .claude/skills/<name> is three deep from the repo root.
if [ -d "$SCRIPT_DIR/skills" ]; then
  mkdir -p .claude/skills
  for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name="$(basename "$skill_dir")"
    link_path=".claude/skills/$skill_name"
    target="../../$SUBMOD_REL/skills/$skill_name"
    if [ -L "$link_path" ]; then
      skipped=$((skipped + 1))
    else
      rm -rf "$link_path" 2>/dev/null
      ln -sf "$target" "$link_path"
      created=$((created + 1))
    fi
  done
fi

# Claude Code user-global config — slash commands + memory files.
# Source-of-truth lives at claude-config/ in this submodule (git-tracked).
# Symlinks go into ~/.claude/ so Claude Code finds them at the standard
# paths. On a new machine, run this script after cloning + the files come
# right back. Memory file path is project-specific (encodes absolute project
# path), so we compute it from CWD.
if [ -d "$SCRIPT_DIR/claude-config" ]; then
  user_created=0; user_skipped=0

  # 1) Slash commands -> ~/.claude/commands/
  mkdir -p "$HOME/.claude/commands"
  for cmd_file in "$SCRIPT_DIR"/claude-config/commands/*.md; do
    [ -f "$cmd_file" ] || continue
    cmd_base="$(basename "$cmd_file")"
    link_path="$HOME/.claude/commands/$cmd_base"
    if [ -L "$link_path" ] && [ "$(readlink "$link_path")" = "$cmd_file" ]; then
      user_skipped=$((user_skipped + 1))
    else
      rm -f "$link_path" 2>/dev/null
      ln -sf "$cmd_file" "$link_path"
      user_created=$((user_created + 1))
    fi
  done

  # 2) Per-project memory files -> ~/.claude/projects/<encoded-cwd>/memory/
  # The "encoded cwd" replaces / AND space with - in the absolute project path
  # (matches how Claude Code's harness encodes project paths).
  proj_encoded="$(echo "$HOST_ROOT" | sed -e 's|/|-|g' -e 's| |-|g')"
  proj_memory_dir="$HOME/.claude/projects/$proj_encoded/memory"
  if [ -d "$proj_memory_dir" ]; then
    for mem_file in "$SCRIPT_DIR"/claude-config/memory/*.md; do
      [ -f "$mem_file" ] || continue
      mem_base="$(basename "$mem_file")"
      link_path="$proj_memory_dir/$mem_base"
      if [ -L "$link_path" ] && [ "$(readlink "$link_path")" = "$mem_file" ]; then
        user_skipped=$((user_skipped + 1))
      else
        rm -f "$link_path" 2>/dev/null
        ln -sf "$mem_file" "$link_path"
        user_created=$((user_created + 1))
      fi
    done
  else
    echo "  (memory dir $proj_memory_dir does not exist yet — skip memory symlinks; run Claude once in this project first)"
  fi

  # 3) Hooks -> ~/.claude/hooks/
  mkdir -p "$HOME/.claude/hooks"
  for hook_file in "$SCRIPT_DIR"/claude-config/hooks/*.sh; do
    [ -f "$hook_file" ] || continue
    hook_base="$(basename "$hook_file")"
    link_path="$HOME/.claude/hooks/$hook_base"
    if [ -L "$link_path" ] && [ "$(readlink "$link_path")" = "$hook_file" ]; then
      user_skipped=$((user_skipped + 1))
    else
      rm -f "$link_path" 2>/dev/null
      ln -sf "$hook_file" "$link_path"
      user_created=$((user_created + 1))
    fi
  done

  echo "claude-config: linked $user_created (skipped $user_skipped) into ~/.claude/"
  echo "  NOTE: CLAUDE.md global rules — paste manually from claude-config/CLAUDE-md-additions.md (user-specific file, not symlinked)"
  echo "  NOTE: hooks symlinked but NOT auto-registered in settings.json"
  echo "        Register manually: see claude-config/CLAUDE-md-additions.md hooks section"
fi

echo "setup-symlinks: created $created, skipped $skipped (already exist)"
echo "Run scripts via: python3 scripts/<name>.py  or  ./scripts/<name>.sh"
if [ -d "$SCRIPT_DIR/skills" ]; then
  echo "Claude Code skills linked under .claude/skills/ — reload your editor or re-open Claude to pick them up."
fi
