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

echo "setup-symlinks: created $created, skipped $skipped (already exist)"
echo "Run scripts via: python3 scripts/<name>.py  or  ./scripts/<name>.sh"
if [ -d "$SCRIPT_DIR/skills" ]; then
  echo "Claude Code skills linked under .claude/skills/ — reload your editor or re-open Claude to pick them up."
fi
