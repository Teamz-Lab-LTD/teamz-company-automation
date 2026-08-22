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
PUSH_STATUS="n/a"
COURSE_STATUS="not-enabled"

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
           "$CONTENT_STATUS" "$BUILD_STATUS" "$DEPLOY_STATUS" "$PUSH_STATUS" "$COURSE_STATUS" <<'PYEOF' 2>/dev/null || true
import json, sys, datetime
path, rc, site, label, content, build, deploy, push, courses = sys.argv[1:10]
json.dump({
    "site": site,
    "label": label,
    "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "exit_code": int(rc),
    "content": content,
    "build": build,
    "deploy": deploy,
    "push": push,
    "courses": courses,
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

# 0. PREFLIGHT (--pre). Assert the root resolved to a REAL site repo and that known inputs are
#    non-empty, BEFORE any phase runs. This is the loud guard for the silent-killer class: a
#    path bug or a silently-dropped input (the 11k-keyword bug) aborts here with a distinct
#    status + Mac alert instead of producing a green-looking no-op night. It writes
#    data/preflight-status.json, which the digest also reads.
if [ -f "$ROOT/scripts/nightly-preflight.py" ]; then
  if ! python3 "$ROOT/scripts/nightly-preflight.py" --pre; then
    CONTENT_STATUS="failed:preflight"; BUILD_STATUS="skipped:preflight"; DEPLOY_STATUS="skipped:preflight"
    osascript -e "display notification \"$LABEL: preflight --pre FAILED — night aborted (see data/preflight-status.json)\" with title \"NIGHTLY PREFLIGHT\"" 2>/dev/null || true
    echo "ABORT: preflight --pre failed — refusing to run phases on a broken root/inputs."
    exit 2   # EXIT trap writes nightly-status.json with failed:preflight so the digest sees it
  fi
fi

# 1. DIRTY-GUARD. Never run over uncommitted human work: a nightly that commits +
#    deploys half-finished edits is worse than a nightly that skips a night. Only
#    GENERATED artifacts are allowed to be dirty.
# A file whose NAME says it is generated is never human WIP. Left out, these freeze the
# night forever: src/data/ecommerce-page.generated.ts carries a gscKeywordsExportedAt
# timestamp that a separate 01:52 cron rewrites, so the guard blocked apps.teamzlab.com
# on a file that had regenerated itself since the last commit — the same self-sustaining
# freeze the two tracked .pyc files caused on goalkit.
ARTIFACT_RE='^.. (dist/|logs/|docs/|data/|node_modules/|robots\.txt|sitemap\.xml|llms(-full)?\.txt|public/robots\.txt|public/llms(-full)?\.txt|rank-history\.json)'
ARTIFACT_RE="$ARTIFACT_RE|^.. .*\.generated\.(ts|tsx|js|json)$"
[ -n "$EXTRA_ARTIFACTS" ] && ARTIFACT_RE="$ARTIFACT_RE|^.. ($EXTRA_ARTIFACTS)"
DIRTY="$(git status --porcelain --ignore-submodules 2>/dev/null | grep -vE "$ARTIFACT_RE")"
if [ -n "$DIRTY" ]; then
  echo "SKIP: uncommitted source changes (protecting human WIP):"
  echo "$DIRTY" | sed 's/^/    /'
  echo "Commit or stash, then the next run proceeds."
  # LOUD skip, not silent. The old bare `exit 0` here WAS a silent killer: one stray source file
  # froze the whole night and the digest still rendered green (finding #1). Owner decision
  # 2026-07-18: BLOCK + alert. Record a DISTINCT status the digest treats as not-ok, fire a Mac
  # alert, and still exit 0 (a deliberate protective skip is not a crash — the status string, not
  # the exit code, carries the reason).
  CONTENT_STATUS="skipped:dirty-tree"; BUILD_STATUS="skipped:dirty-tree"; DEPLOY_STATUS="skipped:dirty-tree"
  osascript -e "display notification \"$LABEL skipped: uncommitted source changes — commit to resume the nightly\" with title \"NIGHTLY DIRTY-TREE\"" 2>/dev/null || true
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

# Did last month's content work actually move anything? Graded against a CONTROL cohort of
# pages the engine never touched — the treatment number alone measures the season, not the
# work (tools' first raw run scored +6,205 clicks; the movers were World Cup pages).
# This engine has always measured and acted, and never checked. Read-only: GSC + git log.
# Portable across properties by design — it maps changed FILES to URLs rather than parsing
# commit subjects, because only tools puts a URL path in the subject and a subject parser
# reported the other three as having no data at all.
[ -f scripts/build-enhance-outcome.py ] && python3 scripts/build-enhance-outcome.py 2>&1 | tail -6 \
  || echo "  (build-enhance-outcome.py missing — skipped)"

# 3b. Keyword-candidate HARVEST only — accumulate GSC-demand queries we have no volume for.
# HARVEST is cheap and safe nightly; it only appends to data/keyword-candidates.json. It never
# PREPARES a batch — that would nag the owner every night. Batch preparation is deliberately
# left to a human/Claude call (build-keyword-candidates.py --prepare), gated by count + cadence.
if [ -f scripts/build-keyword-candidates.py ]; then
  python3 scripts/build-keyword-candidates.py 2>&1 | sed 's/^/  /' | tail -3 \
    || echo "  (keyword-candidate harvest failed — non-fatal)"
fi

# 3c. Resolve prepared batches through the Google Ads API — the chore that used to be manual.
# Batches in data/manual-pull/1-UPLOAD-THESE/ waited for the owner to paste them into Keyword
# Planner by hand, so they piled up: apps knew volume for 131 keywords and goalkit for 90,
# which is why their content queues were picking targets on rank alone. Call-capped so it
# nibbles a few batches a night rather than hammering the API; already-resolved batches are
# skipped, and a run that resolves nothing leaves the batch pending for tomorrow.
# Absent script / no credentials / no pending batches -> prints and moves on.
if [ -f scripts/build-keyword-volume-auto.py ]; then
  echo ""
  echo "Resolving pending keyword batches (Google Ads API)..."
  # ${PIPESTATUS[0]}, not `||`. The `||` here tested `tail`, which always exits 0, so
  # this failure branch was unreachable — the script could exit non-zero and the
  # nightly would print nothing. Combined with the script returning 0 on a config
  # refusal, goalkit's keyword batches went unresolved for two nights in Aug 2026
  # with a clean log. Two layers of silence over the same fault.
  python3 scripts/build-keyword-volume-auto.py --max-calls 30 2>&1 | sed 's/^/  /' | tail -6
  KWAUTO_RC=${PIPESTATUS[0]}
  if [ "$KWAUTO_RC" -ne 0 ]; then
    # nightly-site.sh has no record_health_alert() (that lives in nightly-build.sh),
    # so this notifies directly rather than calling a function that does not exist —
    # a guarded call to a missing function would be one more layer of silence.
    echo "  ✗ keyword-volume-auto exited $KWAUTO_RC — keyword batches are NOT being priced."
    echo "    Most likely TEAMZ_KW_GEO is set to a value no script recognises."
    osascript -e "display notification \"$LABEL: keyword batches not priced (exit $KWAUTO_RC) — check TEAMZ_KW_GEO\" with title \"Teamz Nightly\"" 2>/dev/null || true
  fi
fi

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
    # Is each page even AIMED at a keyword anyone searches? The queue below answers "which
    # page should I improve" and takes every page's declared target as given, so a page built
    # around a 10/mo phrase looks merely small, forever. On apps.teamzlab.com that was 5 of 7
    # app pages. Cached for TEAMZ_KWAUDIT_TTL_DAYS (14) — a cached run costs zero Keyword
    # Planner calls, so this is safe nightly. Never fatal: a bad keyword target is a slow
    # problem, and it must not stop tonight's content work.
    # MAROONED PAGES — indexed, linked, and still unreachable because every page linking to
    # them is itself dead. build-fix-orphans.py cannot see these: it counts inbound links and
    # they HAVE inbound links. Three NFL pages passed it with 2 links each and took 0
    # impressions in 90 days, because every link came from a page with 4.
    #
    # This WRITES. It used to be report-only and this comment still said so for a while
    # after --fix was added, which is the worst kind of stale comment: it tells a future
    # reader the nightly only looks, while the nightly is editing pages. It adds ONE line
    # per page — an entry in the donor's RELATED_TOOLS array — never deletes, never touches
    # prose, and is capped by --fix-limit (10 here, 25 on tools). Non-fatal by design.
    if [ -f "$ROOT/teamz-company-automation/py/build-marooned-pages.py" ]; then
      MAROON_SITE="${TEAMZ_MAROON_SITE:-apps}"
      python3 "$ROOT/teamz-company-automation/py/build-marooned-pages.py" \
        --site "$MAROON_SITE" --top 8 --fix --fix-limit "${TEAMZ_MAROON_FIX_LIMIT:-10}" 2>&1 | sed 's/^/  /' \
        || echo "  (marooned-page scan failed — non-fatal)"
    fi

    if [ -f "$ROOT/teamz-company-automation/py/build-keyword-target-audit.py" ]; then
      python3 "$ROOT/teamz-company-automation/py/build-keyword-target-audit.py" 2>&1 \
        | sed 's/^/  /' || echo "  (keyword-target audit failed — non-fatal)"
    fi
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
      AGENT_OUT="$(mktemp -t nightly-agent 2>/dev/null || echo "$ROOT/logs/.agent-out.$$")"

      # Run claude ONCE, hang-watchdogged. Background claude DIRECTLY into a temp file — NOT
      # through `| sed` — because the old `claude … | sed & AGENT_PID=$!` got two things wrong:
      #   1. `$!` of a background PIPELINE is its LAST command (sed), so `wait "$AGENT_PID"`
      #      returned SED's exit, not claude's. It only ever looked right because `set -o pipefail`
      #      is on globally — flip pipefail off and EVERY failed agent would read as "ok" (proven:
      #      `false | sed & wait $!` => 0). Backgrounding claude alone makes AGENT_PID = claude.
      #   2. the watchdog's `kill -TERM "$AGENT_PID"` was therefore aimed at SED — a genuinely hung
      #      claude was never killed, the exact zombie the watchdog exists to prevent.
      # Output is printed (indented) after the run; under launchd (file redirect) live-vs-buffered
      # is invisible, and correct exit capture is worth it.
      #
      # 2026-08-10: that "live-vs-buffered is invisible [so it doesn't matter]" call was wrong —
      # proven on the tools property's twin of this watchdog (nightly-build.sh): a killed run's
      # output showed ZERO lines for the entire wall, even though a same-night SUCCESSFUL run
      # streamed visible progress throughout. Default text output-format fully-buffers when
      # stdout isn't a TTY (piped/backgrounded, exactly this setup) — every past timeout here was
      # therefore a black box too, no way to tell "hung on one tool" from "did real work that
      # never flushed before the kill". Switched to --output-format stream-json
      # --include-partial-messages (verified this flushes per-event to a plain file, same as the
      # tools fix) + a jq render pass so the printed output stays human-readable, and the LAST
      # tool call before a kill is captured into LAST_TOOL_CALL (a global, since $AGENT_OUT gets
      # rm'd by the caller before the timeout case statement reads it).
      LAST_TOOL_CALL=""
      _run_content_agent() {
        claude --print --verbose --output-format stream-json --include-partial-messages \
               --dangerously-skip-permissions \
               --model "$CONTENT_MODEL" -p "$(cat "$CONTENT_PROMPT")" > "$AGENT_OUT" 2>&1 &
        AGENT_PID=$!
        # `set -m` gives the watchdog subshell its OWN process group so cancelling it takes its
        # `sleep` down too; otherwise an orphaned `sleep 1800` holds inherited fds open and can
        # hang a piped parent for the whole timeout (the 2026-07-12 25-min `tee` hang).
        set -m
        ( sleep "$AGENT_MAX_SECONDS"; kill -TERM "$AGENT_PID" 2>/dev/null; sleep 60; kill -KILL "$AGENT_PID" 2>/dev/null ) &
        WD_PID=$!
        set +m
        wait "$AGENT_PID"; AGENT_EXIT=$?
        kill -- "-$WD_PID" 2>/dev/null || kill "$WD_PID" 2>/dev/null   # group first, subshell as fallback
        wait "$WD_PID" 2>/dev/null
        if command -v jq >/dev/null 2>&1 && [ -s "$AGENT_OUT" ]; then
          jq -r '
            if .type == "assistant" then
              (.message.content[]? |
                if .type == "tool_use" then "  [tool] " + .name + " " + ((.input // {}) | tostring | .[0:150])
                elif .type == "text" and (.text // "") != "" then "  " + .text
                else empty end)
            elif .type == "result" then
              "  [agent finished] " + (.result // .subtype // "no result text")
            else empty end
          ' "$AGENT_OUT" 2>/dev/null || sed 's/^/  /' "$AGENT_OUT"
          LAST_TOOL_CALL="$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .name' "$AGENT_OUT" 2>/dev/null | tail -1)"
        else
          sed 's/^/  /' "$AGENT_OUT"
        fi
      }

      HEAD_BEFORE="$(git rev-parse HEAD 2>/dev/null)"
      _run_content_agent
      # Retry ONCE on a transient failure — "API Error: Stream idle timeout" was the 2026-07-17
      # cause on BOTH apps and goalkit — but ONLY if the first attempt committed NOTHING, so a
      # partial run can never double-write a target. A stream timeout errors mid-response having
      # committed nothing, so it retries cleanly; a run that already committed is left as-is.
      if [ "$AGENT_EXIT" != "0" ] && [ "$AGENT_EXIT" != "143" ] && [ "$AGENT_EXIT" != "137" ]; then
        if [ "$(git rev-parse HEAD 2>/dev/null)" = "$HEAD_BEFORE" ]; then
          echo "  ⟳ content agent failed (exit $AGENT_EXIT), nothing committed — retrying once after a transient error."
          sleep 15
          _run_content_agent
        else
          echo "  content agent failed (exit $AGENT_EXIT) but had already committed work — NOT retrying (would risk duplicate pages)."
        fi
      fi
      rm -f "$AGENT_OUT"

      case "$AGENT_EXIT" in
        0)       CONTENT_STATUS="ok"
                 echo "  ✓ content agent finished" ;;
        143|137) CONTENT_STATUS="failed:timeout"
                 echo "  ✗ content agent TIMED OUT (>${AGENT_MAX_SECONDS}s) — killed to prevent a zombie. Next run retries fresh."
                 if [ -n "$LAST_TOOL_CALL" ]; then
                   echo "  Last tool call before kill: $LAST_TOOL_CALL — likely where it hung."
                 fi
                 osascript -e "display notification \"Content agent TIMED OUT on $LABEL\" with title \"Teamz Content\" sound name \"Basso\"" 2>/dev/null ;;
        *)       CONTENT_STATUS="failed:exit-$AGENT_EXIT"
                 echo "  ✗ content agent failed (exit $AGENT_EXIT) even after retry — build+deploy continue with whatever it committed."
                 osascript -e "display notification \"Content agent FAILED (exit $AGENT_EXIT) on $LABEL\" with title \"Teamz Content\" sound name \"Basso\"" 2>/dev/null ;;
      esac
    fi
  fi
fi

# 4.7 COURSE AGENT — creates/expands whole COURSES from measured demand (build-course-radar.py).
#
# SEPARATE from the content agent on purpose: the content prompt's "never invent course content"
# rail must hold 6 nights a week; a 10-lesson course is an opus job with its own budget; and a
# course-agent failure must not cost the night's enhancements. INERT unless TEAMZ_NIGHTLY_COURSES=1,
# so tools/apps/goalkit (which never set it) are completely unaffected — proven by bash -n + a
# tools-nightly dry run.
if [ "${TEAMZ_NIGHTLY_COURSES:-0}" = "1" ]; then
  echo ""
  echo "=== course agent ==="
  COURSE_PROMPT="$ROOT/scripts/nightly-course-prompt.md"
  if [ ! -f "$COURSE_PROMPT" ]; then
    COURSE_STATUS="skipped:no-prompt"
    echo "  SKIP: TEAMZ_NIGHTLY_COURSES=1 but no scripts/nightly-course-prompt.md"
  elif ! command -v claude >/dev/null 2>&1; then
    COURSE_STATUS="skipped:no-claude-cli"
    echo "  SKIP: claude CLI not on PATH"
  elif [ ! -f "$ROOT/scripts/build-course-radar.py" ]; then
    COURSE_STATUS="skipped:no-radar"
    echo "  SKIP: scripts/build-course-radar.py missing"
  else
    # Measure SEO winnability for cluster keywords not yet scored, BEFORE the gate reads them.
    # Without this, winnability falls back to Planner's ADVERTISER competition, which is a different
    # quantity and disagrees badly (a term with no bidders can still have a top-10 of banks and .gov).
    # Optional by design: absent script, absent Firecrawl key, or an API failure just leaves the
    # fallback in place — it must never block the night's course action. Its own credit guard caps
    # spend and reserves a floor, so a big cluster set cannot drain the account.
    if [ -f "$ROOT/scripts/build-serp-difficulty.py" ] && [ -f "$HOME/.config/teamzlab/firecrawl-api-key.txt" ]; then
      TEAMZ_HOST_DIR="$ROOT" python3 scripts/build-serp-difficulty.py --from-radar \
        --limit "${TEAMZ_SERP_NIGHTLY_LIMIT:-25}" 2>&1 | sed 's/^/  /' || \
        echo "  (serp difficulty scoring failed — winnability falls back to advertiser competition)"
    fi
    # The radar decides the ONE action for tonight (create-pilot | expand | null) — the agent never
    # authorizes itself. --gate writes data/course-task.json.
    python3 scripts/build-course-radar.py --gate 2>&1 | sed 's/^/  /'
    TASK="$ROOT/data/course-task.json"
    ACTION=$(python3 -c "import json,os;print((json.load(open('$TASK')).get('action') or '') if os.path.exists('$TASK') else '')" 2>/dev/null || echo "")
    if [ -z "$ACTION" ]; then
      COURSE_STATUS="ok:no-task"
      echo "  No course action tonight (no eligible cluster / cadence not due) — a valid outcome."
    elif ! retry 3 20 api_up; then
      COURSE_STATUS="skipped:api-unreachable"
      echo "  SKIP: api.anthropic.com unreachable after retries"
    else
      # Model per ACTION, not per night. The two actions are not the same job and do not run at
      # the same rate. create-pilot invents a course on a new YMYL topic — it picks the angle,
      # sources real figures (NAIC/NAPHIA/AVMA), and has to refuse brand traps; it fires at most
      # once per TEAMZ_PILOT_CADENCE_DAYS (14) with <=2 active pilots, so ~12-26 times a year.
      # expand appends lessons into a course whose voice, schema and structure the pilot already
      # fixed — pattern-work — and fires every TEAMZ_PILOT_EXPAND_SPACING (7) days PER expanding
      # course, so it becomes the large majority of runs as soon as anything graduates. Spending
      # the strong model on the rare, hard job and the cheap one on the frequent, easy job is the
      # opposite of one flat TEAMZ_COURSE_MODEL, which pays top rate for the pattern-work and
      # tempts a blanket downgrade that lands on the foundational content instead. Mirrors the
      # content agent's existing TEAMZ_CONTENT_MODEL_NEW / _ENHANCE split.
      case "$ACTION" in
        expand) COURSE_MODEL="${TEAMZ_COURSE_MODEL_EXPAND:-sonnet}" ;;
        *)      COURSE_MODEL="${TEAMZ_COURSE_MODEL_NEW:-${TEAMZ_COURSE_MODEL:-opus}}" ;;
      esac
      echo "  action: $ACTION   model: $COURSE_MODEL"
      COURSE_MAX_SECONDS="${TEAMZ_COURSE_MAX_SECONDS:-3600}"
      COURSE_OUT="$(mktemp -t nightly-course 2>/dev/null || echo "$ROOT/logs/.course-out.$$")"

      # Same correct-capture pattern as the content agent: background claude DIRECTLY to a temp file
      # (NOT through a pipe), so COURSE_EXIT is claude's OWN exit and the watchdog kills claude.
      _run_course_agent() {
        claude --print --verbose --dangerously-skip-permissions \
               --model "$COURSE_MODEL" -p "$(cat "$COURSE_PROMPT")" > "$COURSE_OUT" 2>&1 &
        COURSE_PID=$!
        set -m
        ( sleep "$COURSE_MAX_SECONDS"; kill -TERM "$COURSE_PID" 2>/dev/null; sleep 60; kill -KILL "$COURSE_PID" 2>/dev/null ) &
        CWD_PID=$!
        set +m
        wait "$COURSE_PID"; COURSE_EXIT=$?
        kill -- "-$CWD_PID" 2>/dev/null || kill "$CWD_PID" 2>/dev/null
        wait "$CWD_PID" 2>/dev/null
        sed 's/^/  /' "$COURSE_OUT"
      }

      CHEAD_BEFORE="$(git rev-parse HEAD 2>/dev/null)"
      _run_course_agent
      if [ "$COURSE_EXIT" != "0" ] && [ "$COURSE_EXIT" != "143" ] && [ "$COURSE_EXIT" != "137" ]; then
        if [ "$(git rev-parse HEAD 2>/dev/null)" = "$CHEAD_BEFORE" ]; then
          echo "  ⟳ course agent failed (exit $COURSE_EXIT), nothing committed — retrying once."
          sleep 15
          _run_course_agent
        else
          echo "  course agent failed (exit $COURSE_EXIT) but had already committed — NOT retrying."
        fi
      fi
      rm -f "$COURSE_OUT"
      case "$COURSE_EXIT" in
        0)       COURSE_STATUS="ok:$ACTION"
                 echo "  ✓ course agent finished ($ACTION)" ;;
        143|137) COURSE_STATUS="failed:timeout"
                 echo "  ✗ course agent TIMED OUT (>${COURSE_MAX_SECONDS}s) — killed. Next run retries fresh."
                 osascript -e "display notification \"Course agent TIMED OUT on $LABEL\" with title \"Teamz Courses\" sound name \"Basso\"" 2>/dev/null ;;
        *)       COURSE_STATUS="failed:exit-$COURSE_EXIT"
                 echo "  ✗ course agent failed (exit $COURSE_EXIT) even after retry."
                 osascript -e "display notification \"Course agent FAILED (exit $COURSE_EXIT) on $LABEL\" with title \"Teamz Courses\" sound name \"Basso\"" 2>/dev/null ;;
      esac
    fi
  fi
fi

# 5. build (static sites have no build step — that is normal, not an error)
if [ -n "$BUILD_CMD" ]; then
  echo ""
  echo "=== build: $BUILD_CMD ==="
  # `if cmd | tail -8; then` tests TAIL's exit status, and tail always succeeds — so this
  # branch could never be taken and a failed build deployed anyway, which is the exact opposite
  # of what the message below promises. Same trap as the tools pre-push gate (2026-08-21) and
  # the concept-duplicate gate. Run it unpiped, capture the real status, then show the tail.
  BUILD_LOG=$(eval "$BUILD_CMD" 2>&1)
  BUILD_EXIT=$?
  echo "$BUILD_LOG" | tail -8
  if [ "$BUILD_EXIT" -eq 0 ]; then
    BUILD_STATUS="ok"
  else
    BUILD_STATUS="failed"
    echo "BUILD FAILED (exit $BUILD_EXIT) — not deploying."
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

# 5.55 STARVED-HUB GATE (goalkit only — host-guarded on the script existing).
#
# The orphan gate above asks "is the page in the sitemap?". Being in the sitemap is not enough:
# on 2026-08-22, five goalkit club collections were in a sitemap Google downloads every few days
# and Google still reported them as "URL is unknown to Google" — never discovered. Each had
# exactly ONE inbound internal link. The hubs that WERE indexed had 19-25.
#
# WARN-only, deliberately: the nightly commits --no-verify, and a link-graph regression should
# be shouted about, not used to abort a night that otherwise shipped fine.
if [ -f "$ROOT/scripts/guard-collection-links.py" ]; then
  echo ""
  echo "=== collection link-graph ==="
  python3 "$ROOT/scripts/guard-collection-links.py" --warn 2>&1 | tail -20
fi

# 5.6 INTERNAL LINK HEALTH — was computed nowhere in this script until 2026-07-23. tools' own
# nightly (a different script, nightly-build.sh) DID run this check every night and DID compute
# a health-alert count into nightly-status.json — but nothing ever rendered that count anywhere
# a human would see it, so a real, growing problem (3499 tools not linked from their own hub
# page) sat silently for two months. This script never even ran the check at all. Both are the
# same failure with a different shape: a monitor that knows and says nothing is a monitor that
# might as well not exist. This phase is intentionally loud (console + a Mac notification) and
# intentionally non-blocking (never fails the build) — the fix for THIS finding is "tell the
# owner", not "auto-heal", since unlike tools' hub-link gap, no proven safe auto-fixer exists yet
# for whatever this site's internal-link report turns up.
if [ -f "$ROOT/scripts/build-internal-links.sh" ]; then
  LINK_HEALTH_OUT="$("$ROOT/scripts/build-internal-links.sh" --quick 2>&1)"
  LINK_HEALTH_RC=$?
  if [ "$LINK_HEALTH_RC" -ne 0 ]; then
    echo ""
    echo "  ⚠️  INTERNAL LINK HEALTH — issues found:"
    echo "$LINK_HEALTH_OUT" | tail -12 | sed 's/^/      /'
    BUILD_STATUS="${BUILD_STATUS}:link-health-alert"
    osascript -e "display notification \"Internal link health issues on $LABEL — see nightly log\" with title \"Teamz Content\"" 2>/dev/null
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
  if git commit -m "chore(nightly): refresh generated site output" --no-verify 2>/dev/null; then
    # DO NOT pipe the push straight into `tail` — without pipefail the pipe returns tail's exit
    # (0), so a FAILED push (auth expired, rejected, network) looks identical to success and the
    # remote/VPS silently never gets tonight's content. Capture push's own exit, then report.
    #
    # RETRY, added 2026-08-08. This step had ZERO retries while the deploy below had three —
    # backwards, since push is the BACKUP and was the less-protected of the two. The sibling
    # engine (nightly-build.sh, tools) grew a `host_up_within github.com` wait back in July
    # after a waking-network blink stranded TWENTY commits; that fix was only ever applied to
    # that one file, so apps/goalkit/learn — the three properties THIS script drives — never
    # got it. Observed live on 2026-08-07: apps and learn both logged `push: failed` while
    # `deploy: ok` on the same run. Nothing was lost (a later run pushed them; verified by
    # `git fetch` + HEAD comparison, not by trusting the status field), but only because a
    # later run happened to succeed. Same shape as the July incident, one blink from repeating.
    push_attempt() { PUSH_OUT="$(git push origin HEAD --no-verify 2>&1)"; }
    if retry 3 20 push_attempt; then
      echo "$PUSH_OUT" | tail -3
      PUSH_STATUS="ok"
    else
      echo "$PUSH_OUT" | tail -3
      PUSH_STATUS="failed"
      # Deploy runs AFTER this and does not depend on the push succeeding — it rsyncs the local
      # build to the VPS over SSH, a different host and a different network path. The old wording
      # here ("remote/VPS will NOT update") overstated the damage and would send you hunting for
      # a dead site that was actually live. What is genuinely at risk is the GitHub BACKUP.
      echo "  ✗ GIT PUSH FAILED after 3 attempts (last rc: see above) — commit is LOCAL ONLY."
      echo "    The VPS deploy below is unaffected and still runs; the GitHub backup is what is missing."
      osascript -e "display notification \"git push FAILED on $LABEL — GitHub backup missing, site deploy unaffected\" with title \"Teamz Nightly\" sound name \"Basso\"" 2>/dev/null
    fi
  else
    echo "  (nothing to commit)"
  fi
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
    # A zero exit from the deploy command is a claim about a command, not about the
    # internet. goalkit's deploy is an rsync followed by cloudflare-purge.py, which is
    # already known to print ERROR and still exit 0 — so "deploy ok" has been provable
    # only by hand. Ask the live site instead: does it serve every URL we just built?
    #
    # Three outcomes, deliberately distinguishable. "could not check" must never render
    # the same as "all clear" — that equivalence is the bug this whole layer exists to
    # prevent.
    if [ -f "$ROOT/teamz-company-automation/py/verify-deploy-live.py" ]; then
      echo "  --- verifying against the live site ---"
      VERIFY_OUT="$(python3 "$ROOT/teamz-company-automation/py/verify-deploy-live.py" 2>&1)"; VERIFY_RC=$?
      printf '%s\n' "$VERIFY_OUT" | sed 's/^/  /'
      case "$VERIFY_RC" in
        0) DEPLOY_STATUS="ok:verified-live" ;;
        1) DEPLOY_STATUS="failed:built-but-not-live"
           echo "  ✗ The deploy command exited 0 but the live site does not have these pages."
           osascript -e "display notification \"$LABEL: deploy exited 0 but pages are NOT live\" with title \"Teamz Nightly\" sound name \"Basso\"" 2>/dev/null || true ;;
        *) DEPLOY_STATUS="ok:unverified"
           echo "  ! Deploy exited 0 but could NOT be verified. Not proof it failed; not proof it worked." ;;
      esac
    else
      # Never silent. If the verifier goes missing, the status must say so rather than
      # inheriting a bare "ok" that now means less than it used to.
      DEPLOY_STATUS="ok:unverified"
      echo "  ! verify-deploy-live.py not found at $ROOT/teamz-company-automation/py — deploy is UNVERIFIED."
    fi
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

# 9. PREFLIGHT (--post). After all phases: assert the OUTPUT artifacts are sane (queue parses,
#    status not frozen). Fail => ALERT (exit 1 non-fatal to tonight, but the digest flags it).
#    Refreshes data/preflight-status.json so a MISSING/stale one is itself catchable.
if [ -f "$ROOT/scripts/nightly-preflight.py" ]; then
  echo ""
  echo "=== preflight --post ==="
  python3 "$ROOT/scripts/nightly-preflight.py" --post || {
    echo "  ⚠️ preflight --post flagged an output problem (see data/preflight-status.json)"
    osascript -e "display notification \"$LABEL: post-run check flagged a problem\" with title \"NIGHTLY POST-CHECK\"" 2>/dev/null || true
  }
fi

echo ""
echo "DONE — $(date '+%H:%M:%S')"
