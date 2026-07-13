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

# What actually happened tonight. Written to data/nightly-status.json at the end and read by
# build-growth-digest.py. The digest used to infer health from the log file's MODIFICATION TIME,
# which only ever proved the script RAN — never that it WORKED. On 2026-07-13 apps and learn both
# skipped their content agent AND failed to deploy, and the digest called both of them "ok".
# A monitor that cannot tell "worked" from "ran" is not a monitor.
CONTENT_STATUS="not-enabled"
BUILD_STATUS="skipped"
DEPLOY_STATUS="skipped"

# Retry a flaky NETWORK step.
#
# The Mac sleeps. launchd fires the job the instant it wakes — before the WiFi has associated —
# so the first attempt at anything networked can fail for a few seconds through no fault of ours.
# That cost two properties their entire night on 2026-07-12: the api.anthropic.com preflight
# failed on apps (22:39) and on learn (23:39), while goalkit, which happened to run at 23:32,
# sailed through. The deploy died the same way ("Can't assign requested address"). Nothing was
# broken and nothing was misconfigured. There was simply no second attempt.
#
# Patience, not a different timeout: the check itself is fine (ping + nc both pass 6/6 on a
# settled network). What it lacked was the willingness to wait for the network to come up.
retry() {
  local tries="$1" gap="$2"; shift 2
  local i=1
  while :; do
    "$@" && return 0
    [ "$i" -ge "$tries" ] && return 1
    echo "    attempt $i/$tries failed — retrying in ${gap}s (network may still be waking)"
    sleep "$gap"
    i=$((i + 1))
  done
}

api_up() {
  ping -c1 -W2 api.anthropic.com >/dev/null 2>&1 || nc -z -G5 api.anthropic.com 443 2>/dev/null
}

# Armed as an EXIT trap so the status lands on EVERY path out of this script — including the
# `exit 1` on a failed build, and including a crash. A status file that only appears when the
# run succeeded would be the same lie in a new place: absence would mean both "never ran" and
# "died early", and the digest could not tell them apart.
write_status() {
  local rc=$?
  mkdir -p "$ROOT/data" 2>/dev/null || return 0
  python3 - "$ROOT/data/nightly-status.json" "$rc" "$SITE" "$LABEL" \
           "$CONTENT_STATUS" "$BUILD_STATUS" "$DEPLOY_STATUS" <<'PYEOF' 2>/dev/null || true
import json, sys, datetime
path, rc, site, label, content, build, deploy = sys.argv[1:8]
json.dump({
    "site": site,
    "label": label,
    "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "exit_code": int(rc),
    "content": content,
    "build": build,
    "deploy": deploy,
}, open(path, "w"), indent=2)
PYEOF
}
trap write_status EXIT

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

# 4.5 CONTENT AGENT — the part that makes a site grow itself.
#
#   queue (build-content-queue.py) → claude reads scripts/nightly-content-prompt.md →
#   polishes near-winning pages / writes ONE demand-backed post → per-target commits.
#
# Opt-in per property: TEAMZ_NIGHTLY_CONTENT=1 AND a host-local prompt must exist. A prompt
# is host-local on purpose — an Astro content collection, a static HTML shop and a lessons
# site have nothing in common structurally, and one generic prompt would write slop for all
# three.
#
# MODEL SPLIT: polishing a title is mechanical → sonnet. Writing a post that has to win an
# Upwork client is not → opus. Running opus on every page every night across four properties
# would burn the user's subscription quota during the day, when he needs Claude himself.
if [ "${TEAMZ_NIGHTLY_CONTENT:-0}" = "1" ]; then
  echo ""
  echo "=== content agent ==="
  CONTENT_PROMPT="$ROOT/scripts/nightly-content-prompt.md"
  if [ ! -f "$CONTENT_PROMPT" ]; then
    CONTENT_STATUS="skipped:no-prompt"
    echo "  SKIP: TEAMZ_NIGHTLY_CONTENT=1 but no scripts/nightly-content-prompt.md"
  elif ! command -v claude >/dev/null 2>&1; then
    CONTENT_STATUS="skipped:no-claude-cli"
    echo "  SKIP: claude CLI not installed"
  # BE PATIENT. Genuinely patient.
  #
  # The first version of this waited 60 seconds, because I had assumed the failure was "the Mac
  # woke and the WiFi is not up yet". That assumption was wrong: the power log shows a
  # `caffeinate -s` job holding PreventSystemSleep — the machine was never asleep.
  #
  # What actually happened on 2026-07-12 was an upstream outage. api.anthropic.com AND github.com
  # both went unreachable in the same window, and two unrelated services do not fail together —
  # so it was DNS or the ISP link. It lasted from at LEAST 22:31 (apps failed) to 23:01 (learn
  # failed) and had recovered by 23:21 (goalkit sailed through). Thirty to fifty minutes.
  #
  # A 60-second retry would have saved none of them. This job starts at 22:30 and owns the whole
  # night; nothing else wants the machine. Waiting out a 20-minute blip is free, and losing a
  # night of work is not. On a healthy network the first attempt passes and this costs nothing.
  #
  # For anything longer than this window, the answer is not more waiting — it is the morning
  # catch-up sweep (sh/nightly-catchup.sh), which re-runs any site whose status file says it
  # skipped. Patience handles the blip; the sweep handles the outage.
  # DIAGNOSTIC: 2026-07-13's log showed a SKIP with none of the "attempt N/tries" lines this
  # loop prints, and a message shorter than the one two lines below — inconsistent with this
  # code ever having run, though it was committed hours earlier and reproduces correctly in
  # isolation. Unexplained. This line exists so the next occurrence is diagnosable instead of
  # a repeat mystery: if tries/gap ever print wrong, or don't print at all, that's the fault.
  elif { echo "  [diag] retry tries=${TEAMZ_NET_RETRIES:-20} gap=${TEAMZ_NET_GAP:-60}s"; \
         ! retry "${TEAMZ_NET_RETRIES:-20}" "${TEAMZ_NET_GAP:-60}" api_up; }; then
    CONTENT_STATUS="skipped:api-unreachable"
    echo "  SKIP: api.anthropic.com unreachable after ~${TEAMZ_NET_RETRIES:-20} min."
    echo "        The morning catch-up sweep will retry this site."
  else
    python3 scripts/build-content-queue.py 2>&1 | sed 's/^/  /'
    QUEUE="$ROOT/data/content-queue.json"
    N_TARGETS=$(python3 -c "import json,sys;print(len(json.load(open('$QUEUE'))['targets']))" 2>/dev/null || echo 0)
    if [ "$N_TARGETS" = "0" ]; then
      CONTENT_STATUS="ok:empty-queue"
      echo "  Nothing actionable tonight — skipping the agent. (A valid outcome, not an error:"
      echo "  a queue with no target means no page is close enough and no demand is unserved.)"
    else
      # opus only when a NEW post is on the docket tonight; sonnet for pure polish.
      HAS_NEW=$(python3 -c "import json;print(any(t['mode']=='NEW' for t in json.load(open('$QUEUE'))['targets']))" 2>/dev/null || echo False)
      if [ "$HAS_NEW" = "True" ]; then
        CONTENT_MODEL="${TEAMZ_CONTENT_MODEL_NEW:-opus}"
      else
        CONTENT_MODEL="${TEAMZ_CONTENT_MODEL_ENHANCE:-sonnet}"
      fi
      echo "  targets: $N_TARGETS   new-post tonight: $HAS_NEW   model: $CONTENT_MODEL"

      # Hang-watchdog. macOS has no `timeout`, and a frozen agent that zombies for hours
      # blocks every later launchd fire — this exact failure locked the tools site for 29h
      # (2026-05-31 → 06-01). TERM at the limit, KILL 60s later, watchdog cancelled on a
      # normal finish.
      AGENT_MAX_SECONDS="${TEAMZ_CONTENT_MAX_SECONDS:-1800}"
      claude --print --verbose --dangerously-skip-permissions \
             --model "$CONTENT_MODEL" -p "$(cat "$CONTENT_PROMPT")" 2>&1 | sed 's/^/  /' &
      AGENT_PID=$!

      # `set -m` gives the watchdog subshell its OWN process group, so cancelling it below can
      # take the `sleep` down with it.
      #
      # Without that, `kill $WD_PID` kills only the subshell — and the `sleep` it forked survives,
      # reparented to PID 1, holding every fd it inherited from us for the remainder of the
      # timeout. On 2026-07-12 that left `bash nightly-site.sh | tee log` hanging for 25 minutes
      # AFTER the work was finished and deployed, because `tee` never saw EOF on a pipe an
      # orphaned `sleep 1800` was still holding open. Harmless under launchd (which redirects to
      # a file, not a pipe) — which is exactly why it could have sat there unnoticed for months.
      #
      # Cancel the GROUP, and cancel it before it can act: the subshell must die mid-sleep, never
      # reaching its `kill -TERM "$AGENT_PID"`. If it were killed the other way round it could
      # fire that TERM at a PID the OS had already recycled to somebody else's process.
      set -m
      ( sleep "$AGENT_MAX_SECONDS"; kill -TERM "$AGENT_PID" 2>/dev/null; sleep 60; kill -KILL "$AGENT_PID" 2>/dev/null ) &
      WD_PID=$!
      set +m

      wait "$AGENT_PID"; AGENT_EXIT=$?
      kill -- "-$WD_PID" 2>/dev/null || kill "$WD_PID" 2>/dev/null   # group first, subshell as fallback
      wait "$WD_PID" 2>/dev/null
      case "$AGENT_EXIT" in
        0)       CONTENT_STATUS="ok"
                 echo "  ✓ content agent finished" ;;
        143|137) CONTENT_STATUS="failed:timeout"
                 echo "  ✗ content agent TIMED OUT (>${AGENT_MAX_SECONDS}s) — killed to prevent a zombie. Next run retries fresh."
                 osascript -e "display notification \"Content agent TIMED OUT on $LABEL\" with title \"Teamz Content\" sound name \"Basso\"" 2>/dev/null ;;
        *)       CONTENT_STATUS="failed:exit-$AGENT_EXIT"
                 echo "  ✗ content agent failed (exit $AGENT_EXIT) — build+deploy continue with whatever it committed." ;;
      esac
    fi
  fi
fi

# 5. build (static sites have no build step — that is normal, not an error)
if [ -n "$BUILD_CMD" ]; then
  echo ""
  echo "=== build: $BUILD_CMD ==="
  if eval "$BUILD_CMD" 2>&1 | tail -8; then
    BUILD_STATUS="ok"
  else
    BUILD_STATUS="failed"
    echo "BUILD FAILED — not deploying."
    exit 1   # the EXIT trap still writes nightly-status.json, so the digest sees this
  fi
fi

# 5.5 ORPHAN GATE — did the agent create a page the sitemap never learned about?
#
# On goalkit's first night the agent built a Real Madrid collection hub: correct page, 9
# products, sound title, deployed cleanly. It was INVISIBLE. The sitemap generator had a
# hardcoded list of collections and nothing added the new one, so Google would never have
# learned the page existed. All that work, zero effect, and not one error anywhere.
#
# A page that ships but is not in the sitemap is worse than no page: it costs a night and
# returns nothing, silently, forever. This is the cheapest possible check for it.
if [ -f "$ROOT/sitemap.xml" ]; then
  NEW_PAGES=$(git log --diff-filter=A --name-only --pretty=format: -1 2>/dev/null \
              | grep -E '/index\.html$' | head -20)
  ORPHANS=""
  for p in $NEW_PAGES; do
    slug=$(dirname "$p")
    grep -q "$slug" "$ROOT/sitemap.xml" 2>/dev/null || ORPHANS="$ORPHANS $slug"
  done
  if [ -n "$ORPHANS" ]; then
    echo ""
    echo "  ⚠️  ORPHAN PAGE(S) — created but NOT in sitemap.xml. Google will never find them:"
    for o in $ORPHANS; do echo "      $o"; done
    echo "      The sitemap generator probably has a hardcoded list. Derive it from disk."
    osascript -e "display notification \"Orphan page not in sitemap on $LABEL\" with title \"Teamz Content\" sound name \"Basso\"" 2>/dev/null
  fi
fi

# 6. commit whatever the build regenerated.
#
# This was a HARDCODED list of eight filenames, and it held only for as long as no site's build
# produced anything else. Then goalkit's chain began regenerating 179x2 product pages and 24
# collection hubs every night. That output was never committed, so it stayed dirty — and the NEXT
# night's dirty-guard would have refused to run the site at all. Silently. Every night. Forever.
#
# That is the "leftover build output deadlocks the cron" freeze that already cost tools a week in
# 2026-06, and it is the same shape as the hardcoded collection list that made goalkit's Real
# Madrid hub invisible to Google: a list a human has to remember to update. Stop writing them.
#
# `git add -A` is safe HERE, and only here, and for one specific reason: the dirty-guard at step 1
# already refused to run at all if the tree held any human source WIP. So by this point everything
# uncommitted is either an artifact the guard chose to ignore, or output this build just produced.
# Both are ours to commit. (.gitignore still applies, so the images stay out.)
if [ -n "$(git status --porcelain --ignore-submodules)" ]; then
  git add -A
  git commit -m "chore(nightly): refresh generated site output" --no-verify 2>/dev/null \
    && git push origin HEAD --no-verify 2>&1 | tail -1 \
    || echo "  (nothing to commit)"
fi

# 7. deploy — or say plainly that we cannot
#
# Retried, because the failure mode here is a waking network, not a broken one. On 2026-07-12
# both apps and learn died on "Can't assign requested address" — the machine had woken seconds
# earlier and the interface was not up yet. A single attempt turned a two-second hiccup into a
# whole night of work sitting undeployed.
echo ""
deploy_attempt() { eval "$DEPLOY_CMD" 2>&1 | tail -5; }
if [ -n "$DEPLOY_CMD" ]; then
  echo "=== deploy: $DEPLOY_CMD ==="
  if retry 3 20 deploy_attempt; then
    DEPLOY_STATUS="ok"
  else
    DEPLOY_STATUS="failed"
    echo "  ✗ DEPLOY FAILED after 3 attempts — site still serving the previous build."
    osascript -e "display notification \"Deploy FAILED on $LABEL\" with title \"Teamz Nightly\" sound name \"Basso\"" 2>/dev/null
  fi
else
  DEPLOY_STATUS="n/a:signal-only"
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
