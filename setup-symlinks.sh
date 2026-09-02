#!/bin/bash
# Creates scripts/ symlinks in the host project pointing to this submodule.
# Run from the host project root:
#   bash teamz-company-automation/setup-symlinks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")" && pwd)"
SUBMOD_REL="teamz-company-automation"

# The host project is where you RAN this from — not where the script lives.
#
# Deriving it from the script path breaks when a project reaches this repo through a
# SYMLINK instead of a real submodule (ai_resume_checker does: teamz-company-automation ->
# ../teamz-company-automation). `readlink -f` follows that link to the real directory, so
# SCRIPT_DIR/.. lands on the shared PARENT of every project — and the whole scripts/ tree
# plus .claude/ get written one level too high, outside any repo. Happened on 2026-07-28.
if [ -e "$PWD/$SUBMOD_REL" ]; then
  HOST_ROOT="$PWD"
elif [ -e "$PWD/pubspec.yaml" ] || [ -e "$PWD/package.json" ] || [ -e "$PWD/.git" ]; then
  # Invoked by absolute path from the canonical clone, inside a project that has never
  # been wired up — notetube_ai, top_3_picks and zoyiai were all in this state, with
  # hand-written scripts/ and no link to the toolkit at all. Refusing here is what kept
  # them unwired: the only documented invocation assumes the link already exists, so a
  # NEW project could never get one without someone knowing to make it by hand.
  #
  # Adopt $PWD and create the link the rest of this script expects. The guard below
  # still refuses a directory that is not a project, which is what stops this from
  # littering the shared parent.
  HOST_ROOT="$PWD"
  if [ ! -e "$HOST_ROOT/$SUBMOD_REL" ]; then
    rel="$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$SCRIPT_DIR" "$HOST_ROOT")"
    ln -s "$rel" "$HOST_ROOT/$SUBMOD_REL"
    echo "wired up: $SUBMOD_REL -> $rel"
  fi
else
  HOST_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

# Refuse to litter a directory that is not a project. A host project has a manifest;
# the shared parent directory does not.
if [ ! -e "$HOST_ROOT/pubspec.yaml" ] && [ ! -e "$HOST_ROOT/package.json" ] && [ ! -e "$HOST_ROOT/.git" ]; then
  echo "ERROR: '$HOST_ROOT' does not look like a project root (no pubspec.yaml, package.json or .git)."
  echo "       cd into the project first, then: bash $SUBMOD_REL/setup-symlinks.sh"
  exit 1
fi

cd "$HOST_ROOT"
mkdir -p scripts

created=0
skipped=0
clobber_refused=0

# Replacing a file that git TRACKS with a symlink silently swaps committed content
# for a link, and leaves a type change (`T` in git status) that nothing can ignore
# — .git/info/exclude does not apply to tracked paths, so it blocks the nightly
# dirty guard forever. Two of these already exist: teamzlab-tools
# scripts/build-static-schema.py and the landing pages' scripts/build-internal-links.sh,
# whose repo copy and submodule copy had diverged by 393 lines before anyone noticed.
# Refuse, and say so. Whether the shared copy should win is a human call.
refuse_if_tracked() {
  git -C "$HOST_ROOT" ls-files --error-unmatch "$1" >/dev/null 2>&1 || return 1
  echo "  REFUSED $1 — git tracks a real file here; not replacing it with a symlink"
  clobber_refused=$((clobber_refused + 1))
  return 0
}

for f in "$SCRIPT_DIR"/py/*.py; do
  [ -f "$f" ] || continue
  base="$(basename "$f")"
  [ "$base" = "_teamz_config.py" ] && continue
  target="../$SUBMOD_REL/py/$base"
  if [ -L "scripts/$base" ]; then
    skipped=$((skipped + 1))
  elif refuse_if_tracked "scripts/$base"; then
    :
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
  elif refuse_if_tracked "scripts/$base"; then
    :
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

  # 2b) Company-wide knowledge -> <project>/.claude/knowledge/
  #
  # Strategy documents that are true for EVERY app (the Shipaton knowledge base, the
  # RevenueCat growth playbook). One canonical copy lives here; each project gets a link,
  # so updating the source updates every project at once and no app repo can drift into
  # holding a stale private fork of the plan.
  #
  # NOT in team_mvp_kit: that submodule is shared Dart code owned by a teammate, it is
  # consumed by other apps, and a strategy document has no business shipping inside a
  # package. NOT copied per-project either — copies are how two versions of a "locked"
  # plan come to disagree.
  if [ -d "$SCRIPT_DIR/claude-config/knowledge" ]; then
    mkdir -p "$HOST_ROOT/.claude/knowledge"
    for kb_file in "$SCRIPT_DIR"/claude-config/knowledge/*.md; do
      [ -f "$kb_file" ] || continue
      kb_base="$(basename "$kb_file")"
      link_path="$HOST_ROOT/.claude/knowledge/$kb_base"
      if [ -L "$link_path" ] && [ "$(readlink "$link_path")" = "$kb_file" ]; then
        user_skipped=$((user_skipped + 1))
      else
        rm -f "$link_path" 2>/dev/null
        ln -sf "$kb_file" "$link_path"
        user_created=$((user_created + 1))
      fi
    done
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

# ── Keep this machine's symlinks out of `git status` ────────────────────────
# Every link above is untracked, and the nightly dirty guard reads
# `git status --porcelain`. On 2026-09-03 that meant 127 links in goalkit-bd, 60
# in teamzlab-tools, 46 in teamz-lab-learning and 38 in the landing pages — four
# properties reporting `skipped:dirty-tree` and tools reporting
# "BLOCKED at start: dirty source WIP" for a second night. Nothing shipped
# anywhere. The links were the entire blockage.
#
# .git/info/exclude, NOT .gitignore: which links exist is a property of THIS
# clone, so committing the list would push one machine's layout to everyone.
# Regenerated on every run, so a newly added shared script is covered the moment
# it is linked rather than blocking that night's run.
write_git_exclude() {
  git -C "$HOST_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
  gitdir="$(git -C "$HOST_ROOT" rev-parse --git-dir 2>/dev/null)" || return 0
  case "$gitdir" in /*) ;; *) gitdir="$HOST_ROOT/$gitdir" ;; esac
  mkdir -p "$gitdir/info"
  exclude="$gitdir/info/exclude"
  begin="# >>> teamz setup-symlinks (generated, do not edit by hand) >>>"
  end="# <<< teamz setup-symlinks <<<"

  # A tracked path must NOT be listed: info/exclude does not apply to tracked
  # files, so listing one hides nothing while implying it does.
  links=""
  while IFS= read -r l; do
    [ -n "$l" ] || continue
    git -C "$HOST_ROOT" ls-files --error-unmatch "$l" >/dev/null 2>&1 && continue
    links="$links$l
"
  done <<EOF
$(cd "$HOST_ROOT" && find scripts .claude/skills -maxdepth 1 -type l 2>/dev/null | sed 's|^\./||' | sort)
EOF

  tmp="$(mktemp)"
  [ -f "$exclude" ] && awk -v b="$begin" -v e="$end" \
    '$0==b{skip=1} !skip{print} $0==e{skip=0}' "$exclude" > "$tmp"
  {
    printf '%s\n' "$begin"
    printf '# Symlinks into %s, rewritten by setup-symlinks.sh.\n' "$SUBMOD_REL"
    printf '# Delete this block and re-run the script to regenerate it.\n'
    printf '%s' "$links"
    printf '%s\n' "$end"
  } >> "$tmp"
  mv "$tmp" "$exclude"
  n="$(printf '%s' "$links" | grep -c . || true)"
  echo "git-exclude: $n symlink(s) hidden from git status (.git/info/exclude)"
}
write_git_exclude

echo "setup-symlinks: created $created, skipped $skipped (already exist)"
[ "$clobber_refused" -gt 0 ] && echo "  ^ $clobber_refused tracked file(s) left alone — decide by hand whether the shared copy should replace them"
echo "Run scripts via: python3 scripts/<name>.py  or  ./scripts/<name>.sh"
if [ -d "$SCRIPT_DIR/skills" ]; then
  echo "Claude Code skills linked under .claude/skills/ — reload your editor or re-open Claude to pick them up."
fi
