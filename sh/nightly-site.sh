#!/usr/bin/env bash
# =============================================================================
# nightly-site.sh — CENTRAL, config-driven organic-growth nightly for ANY
#                   teamzlab web property.
# =============================================================================
# WHY THIS EXISTS
#   `nightly-build.sh` is the teamzlab-tools ENGINE: it drives the enhance queue,
#   money snapshots, tools.json, AdSense pools. Those inputs only exist on the
#   tools site, so it cannot be reused as-is. Every other property (learn, apps,
#   goalkit, the Framer brand site) needs the same *SEO loop* without that engine:
#
#       watch GSC  ->  refresh sitemap  ->  build  ->  deploy  ->  ask Google to recrawl
#
#   Copy-pasting that loop per repo is how sites silently drift apart. So it lives
#   here ONCE and every property configures it from its own `.teamz-automation.env`.
#
# HOW A PROPERTY OPTS IN  (all keys live in <repo>/.teamz-automation.env)
#   TEAMZ_SITE_URL             https://learn.teamzlab.com/     (required)
#   TEAMZ_SITE_PROPERTY        GSC property (URL-prefix or sc-domain:)
#   TEAMZ_NIGHTLY_LABEL        com.teamzlab.learn-nightly      (required, UNIQUE)
#   TEAMZ_NIGHTLY_HOUR         23        (default 23)
#   TEAMZ_NIGHTLY_MINUTE       0         (default 0)
#   TEAMZ_NIGHTLY_BUILD_CMD    "npm run build"     (empty => static site, skipped)
#   TEAMZ_NIGHTLY_DEPLOY_CMD   "npm run deploy"    (empty => SIGNAL-ONLY mode)
#   TEAMZ_NIGHTLY_SITEMAP      1|0       (default 1; set 0 when the host platform
#                                         owns the sitemap, e.g. Framer/Wix)
#   TEAMZ_NIGHTLY_ARTIFACTS    extra regex of generated paths the dirty-guard may
#                                         ignore (see DIRTY-GUARD below)
#
# SIGNAL-ONLY MODE  (TEAMZ_NIGHTLY_DEPLOY_CMD empty)
#   For properties we do NOT control the deploy of — e.g. teamzlab.com is a Framer
#   site, edited in Framer's web UI; there is no repo to push. We still want the
#   nightly: it pulls GSC, flags anomalies, and writes a report telling the human
#   exactly which page/title to fix. A monitor that silently skips is worse than
#   none, so the mode is printed loudly on every run.
#
# Install:   bash scripts/nightly-site.sh --install
# Uninstall: bash scripts/nightly-site.sh --uninstall
# Run now:   bash scripts/nightly-site.sh
# =============================================================================
set -uo pipefail   # NOT -e: one failing signal step must never abort the deploy

# --- locate the HOST repo -----------------------------------------------------
# $0 is the path bash was invoked with. Host repos expose this file as the SYMLINK
# <repo>/scripts/nightly-site.sh, and bash does NOT resolve $0, so dirname($0)/..
# is the host repo — never the automation repo. (Resolving the symlink here is the
# exact bug that made every property silently act on tool.teamzlab.com; see
# sh/lib/config.sh.)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
export TEAMZ_HOST_SITE_ROOT="$ROOT"

if [ ! -f "$ROOT/.teamz-automation.env" ]; then
  echo "FATAL: no .teamz-automation.env in $ROOT — this repo is not wired to the engine."
  exit 1
fi
set -a; . "$ROOT/.teamz-automation.env"; set +a

SITE="${TEAMZ_SITE_URL:-}"
LABEL="${TEAMZ_NIGHTLY_LABEL:-}"
HOUR="${TEAMZ_NIGHTLY_HOUR:-23}"
MINUTE="${TEAMZ_NIGHTLY_MINUTE:-0}"
BUILD_CMD="${TEAMZ_NIGHTLY_BUILD_CMD:-}"
DEPLOY_CMD="${TEAMZ_NIGHTLY_DEPLOY_CMD:-}"
DO_SITEMAP="${TEAMZ_NIGHTLY_SITEMAP:-1}"
EXTRA_ARTIFACTS="${TEAMZ_NIGHTLY_ARTIFACTS:-}"

if [ -z "$LABEL" ]; then
  echo "FATAL: TEAMZ_NIGHTLY_LABEL is not set in $ROOT/.teamz-automation.env"
  echo "       Every property needs its OWN launchd label or it clobbers another one."
  exit 1
fi

PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$ROOT/logs"
LOG="$LOG_DIR/$LABEL.log"
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------- install
if [ "${1:-}" = "--install" ]; then
  # ANTI-CLOBBER GUARD. A launchd Label is global; installing over another
  # project's label silently kills its job. This is how the tools nightly nearly
  # died. Refuse, and name the real owner.
  if [ -f "$PLIST_PATH" ] && ! grep -qF "$ROOT/scripts/" "$PLIST_PATH"; then
    echo "REFUSING TO INSTALL — label '$LABEL' already belongs to another project:"
    grep -oE '/[^<]*/scripts/[a-z-]*\.(sh|py)' "$PLIST_PATH" | head -1 | sed 's/^/    owner: /'
    echo "    Pick a unique TEAMZ_NIGHTLY_LABEL in $ROOT/.teamz-automation.env"
    exit 1
  fi
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$ROOT/scripts/nightly-site.sh</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>TEAMZ_HOST_SITE_ROOT</key><string>$ROOT</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>$HOUR</integer>
    <key>Minute</key><integer>$MINUTE</integer>
  </dict>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
PLIST
  launchctl unload "$PLIST_PATH" 2>/dev/null
  launchctl load "$PLIST_PATH" \
    && echo "Installed $LABEL -> $SITE (daily $(printf '%02d:%02d' "$HOUR" "$MINUTE")). Log: $LOG"
  [ -z "$DEPLOY_CMD" ] && echo "NOTE: SIGNAL-ONLY (no TEAMZ_NIGHTLY_DEPLOY_CMD) — it will watch + report, not deploy."
  exit 0
fi
if [ "${1:-}" = "--uninstall" ]; then
  launchctl unload "$PLIST_PATH" 2>/dev/null
  rm -f "$PLIST_PATH" && echo "Uninstalled $LABEL"
  exit 0
fi

# ---------------------------------------------------------------- run
echo "============================================================"
echo "  NIGHTLY: $LABEL"
echo "  site   : $SITE"
echo "  mode   : $([ -n "$DEPLOY_CMD" ] && echo 'FULL (build + deploy)' || echo 'SIGNAL-ONLY (no deploy — report to human)')"
echo "  time   : $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================================"

# 1. DIRTY-GUARD. Never run over uncommitted human work: a nightly that commits +
#    deploys half-finished edits is worse than a nightly that skips a night. Only
#    GENERATED artifacts are allowed to be dirty.
ARTIFACT_RE='^.. (dist/|logs/|docs/|data/|node_modules/|robots\.txt|sitemap\.xml|llms(-full)?\.txt|public/robots\.txt|public/llms(-full)?\.txt|rank-history\.json)'
[ -n "$EXTRA_ARTIFACTS" ] && ARTIFACT_RE="$ARTIFACT_RE|^.. ($EXTRA_ARTIFACTS)"
DIRTY="$(git status --porcelain --ignore-submodules 2>/dev/null | grep -vE "$ARTIFACT_RE")"
if [ -n "$DIRTY" ]; then
  echo "SKIP: uncommitted source changes (protecting human WIP):"
  echo "$DIRTY" | sed 's/^/    /'
  echo "Commit or stash, then the next run proceeds."
  exit 0
fi
echo "✓ dirty-guard passed"

# 2. pull
git pull --rebase --autostash 2>&1 | tail -2 || echo "  (git pull skipped/failed — non-fatal)"

# 3. GSC signal + anomaly watch (never blocks the deploy)
echo ""
echo "=== GSC signals ($TEAMZ_SITE_PROPERTY) ==="
[ -x scripts/build-search-console.sh ] && ./scripts/build-search-console.sh --status 2>&1 | tail -4 \
  || echo "  (build-search-console.sh missing — skipped)"
[ -f scripts/build-gsc-anomalies.py ] && python3 scripts/build-gsc-anomalies.py 2>&1 | tail -6 \
  || echo "  (build-gsc-anomalies.py missing — skipped)"

# 4. sitemap (skip where the host platform owns it — Framer/Wix generate their own)
if [ "$DO_SITEMAP" = "1" ] && [ -x scripts/build-sitemap.sh ]; then
  echo ""
  echo "=== sitemap ==="
  ./scripts/build-sitemap.sh 2>&1 | tail -3
fi

# 5. build (static sites have no build step — that is normal, not an error)
if [ -n "$BUILD_CMD" ]; then
  echo ""
  echo "=== build: $BUILD_CMD ==="
  if ! eval "$BUILD_CMD" 2>&1 | tail -8; then
    echo "BUILD FAILED — not deploying."
    exit 1
  fi
fi

# 6. commit regenerated artifacts (best-effort; a repo with nothing to commit is fine)
if [ -n "$(git status --porcelain --ignore-submodules)" ]; then
  git add -A -- sitemap.xml robots.txt llms.txt llms-full.txt \
                public/sitemap.xml public/robots.txt public/llms.txt public/llms-full.txt 2>/dev/null
  git commit -m "chore(nightly): refresh generated SEO artifacts" --no-verify 2>/dev/null \
    && git push origin HEAD --no-verify 2>&1 | tail -1 \
    || echo "  (nothing to commit)"
fi

# 7. deploy — or say plainly that we cannot
echo ""
if [ -n "$DEPLOY_CMD" ]; then
  echo "=== deploy: $DEPLOY_CMD ==="
  eval "$DEPLOY_CMD" 2>&1 | tail -5 || echo "  DEPLOY FAILED — site still serving previous build."
else
  echo "=== deploy: SKIPPED (signal-only property) ==="
  echo "  No TEAMZ_NIGHTLY_DEPLOY_CMD set for $SITE."
  echo "  Content for this site is NOT in this repo — act on the GSC report above by hand."
fi

# 8. ask Google to recrawl — indexing lag is the #1 killer of new/changed pages
echo ""
echo "=== request indexing ==="
[ -f scripts/build-request-indexing.py ] && python3 scripts/build-request-indexing.py 2>&1 | tail -4 \
  || echo "  (build-request-indexing.py missing — skipped)"

echo ""
echo "DONE — $(date '+%H:%M:%S')"
