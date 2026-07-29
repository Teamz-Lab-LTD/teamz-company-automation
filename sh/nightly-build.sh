#!/bin/bash
# =============================================================================
# Nightly Build Agent — Runs locally via launchd at 3 AM BD (9 PM UTC)
# Full access to ALL local scripts, API tokens, and tools
#
# To install: bash scripts/nightly-build.sh --install
# To uninstall: bash scripts/nightly-build.sh --uninstall
# To run now: bash scripts/nightly-build.sh
# To check status: bash scripts/nightly-build.sh --status
# =============================================================================

_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
_SCRIPT_DIR="$(cd "$(dirname "$_SCRIPT")" && pwd)"
# shellcheck disable=SC1091
source "$_SCRIPT_DIR/lib/config.sh"
teamz_load_config "$_SCRIPT"
PROJECT_DIR="$TEAMZ_HOST_SITE_ROOT"
LOG_DIR="$PROJECT_DIR/logs"
REPORT_FILE="$TEAMZ_DATA_DIR/seo-latest-report.txt"
# Launchd label — PER SITE. This script is symlinked into several host repos; a hardcoded
# label meant only ONE site on the machine could ever have a nightly, and running --install
# from a second repo silently OVERWROTE the first site's job (killing its enhance+deploy with
# no error). Each host repo now sets TEAMZ_NIGHTLY_LABEL in its .teamz-automation.env (loaded
# by teamz_load_config above). Default keeps the existing label so teamzlab-tools' already
# installed job is untouched. (2026-07-12)
PLIST_NAME="${TEAMZ_NIGHTLY_LABEL:-com.teamzlab.nightly-build}"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

# Handle flags
if [ "$1" = "--install" ]; then
    echo "Installing nightly build agent..."
    mkdir -p "$LOG_DIR"
    mkdir -p "$HOME/Library/LaunchAgents"

    # SAFETY GUARD (2026-07-12): this plist used to be a fully HARDCODED heredoc — label,
    # script path and log paths all pointed at teamzlab-tools. Running --install from ANY
    # other repo therefore re-installed the TOOLS nightly under the TOOLS label, silently
    # destroying whichever site's job was there. The heredoc below is now variable-driven,
    # but a repo that forgets to set TEAMZ_NIGHTLY_LABEL still falls back to the shared
    # default label — so refuse to overwrite a job that belongs to a DIFFERENT repo.
    if [ -f "$PLIST_PATH" ] && ! grep -qF "$PROJECT_DIR/scripts/nightly-build.sh" "$PLIST_PATH"; then
        _owner="$(grep -oE '/[^<]*/scripts/nightly-[a-z-]*\.sh' "$PLIST_PATH" | head -1)"
        echo "REFUSING TO INSTALL — label '$PLIST_NAME' is already owned by another project:"
        echo "    existing: ${_owner:-<unknown>}"
        echo "    this one: $PROJECT_DIR/scripts/nightly-build.sh"
        echo "  Installing would silently kill that project's nightly."
        echo "  Fix: set a unique TEAMZ_NIGHTLY_LABEL in $PROJECT_DIR/.teamz-automation.env"
        echo "       e.g. TEAMZ_NIGHTLY_LABEL=com.teamzlab.nightly-$(basename "$PROJECT_DIR")"
        exit 1
    fi

    cat > "$PLIST_PATH" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${PROJECT_DIR}/scripts/nightly-build.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>15</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>21</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/nightly-build.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/nightly-build-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
        <key>TEAMZ_HOST_SITE_ROOT</key>
        <string>${PROJECT_DIR}</string>
    </dict>
</dict>
</plist>
PLIST_EOF

    launchctl unload "$PLIST_PATH" 2>/dev/null
    launchctl load "$PLIST_PATH"
    echo "  Installed! Runs twice daily:"
    echo "    - 9:00 PM BD (3:00 PM UTC) — during your break"
    echo "    - 3:00 AM BD (9:00 PM UTC) — while you sleep"
    echo "  Logs: $LOG_DIR/nightly-build.log"
    echo "  To run now: bash scripts/nightly-build.sh"
    echo "  To uninstall: bash scripts/nightly-build.sh --uninstall"
    exit 0
fi

if [ "$1" = "--uninstall" ]; then
    echo "Uninstalling nightly build agent..."
    launchctl unload "$PLIST_PATH" 2>/dev/null
    rm -f "$PLIST_PATH"
    echo "  Removed."
    exit 0
fi

if [ "$1" = "--status" ]; then
    if launchctl list | grep -q "$PLIST_NAME"; then
        echo "  Status: ACTIVE"
        echo "  Schedule: Daily at 3:00 AM BD (9:00 PM UTC)"
        if [ -f "$LOG_DIR/nightly-build.log" ]; then
            echo "  Last run:"
            tail -5 "$LOG_DIR/nightly-build.log"
        fi
    else
        echo "  Status: NOT INSTALLED"
        echo "  Install with: bash scripts/nightly-build.sh --install"
    fi
    exit 0
fi

# =============================================================================
# MAIN: Run the nightly build
# =============================================================================
echo "============================================================"
echo "  NIGHTLY BUILD — $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================================"

cd "$PROJECT_DIR" || exit 1

has_command() {
    command -v "$1" >/dev/null 2>&1
}

can_resolve_host() {
    python3 - "$1" <<'PY'
import socket
import sys

try:
    socket.getaddrinfo(sys.argv[1], 443)
except OSError:
    sys.exit(1)
sys.exit(0)
PY
}

# The same check, but willing to WAIT for the network.
#
# The Mac sleeps. launchd fires this job the moment it wakes — before the WiFi has associated —
# so a single DNS lookup for github.com can fail for a few seconds through no fault of ours. The
# push is gated on that one lookup, and there was no second attempt.
#
# On 2026-07-12 that stranded TWENTY commits. Nineteen pages this engine had enhanced were
# committed locally and never pushed, so they never reached the VPS and never went live. The log
# said only "Skipping: git push (github.com unavailable)", the run reported success, and the
# digest called it green. Nothing was LOST — the next run pushes everything ahead of origin — but
# a full night's work on the site that carries 89% of all our traffic sat dead for a day, and it
# would do so again on every network blink at 21:00.
#
# ~60s of patience, spent only when the check is actually failing. Costs nothing on a normal night.
host_up_within() {
    local host="$1" tries="${2:-5}" gap="${3:-15}"
    local i=1
    while :; do
        can_resolve_host "$host" && return 0
        [ "$i" -ge "$tries" ] && return 1
        echo "  $host unresolvable (attempt $i/$tries) — waiting ${gap}s for the network to wake"
        sleep "$gap"
        i=$((i + 1))
    done
}

skip_phase() {
    echo "  - Skipping: $1"
    SKIPPED_PHASES+=("$1")
}

extract_health_issue() {
    printf '%s\n' "$1" | grep -m1 -E 'ERROR:|FAILED|Traceback|token refresh failed|No Search Console token|Could not get Search Console token|✗ ' || true
}

record_health_alert() {
    HEALTH_ALERTS+=("$1")
    echo "  ! Health alert: $1"
}

run_phase_cmd() {
    local label="$1"
    local tail_lines="$2"
    shift 2
    local output exit_code issue_line

    output=$(eval "$*" 2>&1)
    exit_code=$?

    # A command can print a >>>TEAMZ-TRAILER<<< sentinel to mark "everything after this is a
    # paste of prior output, not tonight's result" (build-validate-freshness.sh uses this to
    # show the last SEO report without re-triggering on a stale ERROR:/FAILED line buried
    # inside it). Only look at output BEFORE the sentinel for both the printed summary and the
    # health-issue scan — otherwise a stale line re-alerts every night, forever.
    local scan_output="${output%%>>>TEAMZ-TRAILER<<<*}"

    if [ -n "$scan_output" ]; then
        printf '%s\n' "$scan_output" | tail -n "$tail_lines"
    fi

    issue_line=$(extract_health_issue "$scan_output")
    if [ "$exit_code" -ne 0 ]; then
        record_health_alert "$label failed (exit $exit_code)"
    elif [ -n "$issue_line" ]; then
        record_health_alert "$label: $issue_line"
    fi

    return "$exit_code"
}

write_health_report() {
    local status="OK"
    if [ "${#HEALTH_ALERTS[@]}" -gt 0 ]; then
        status="ALERT"
    elif [ "${#SKIPPED_PHASES[@]}" -gt 0 ]; then
        status="PARTIAL"
    fi

    {
        echo "NIGHTLY BUILD REPORT — $(date '+%Y-%m-%d %H:%M')"
        echo "Status: $status"
        echo "Repo dirty at start: $([ "$REPO_DIRTY_AT_START" -eq 1 ] && echo yes || echo no)"
        echo "New tools built: ${NEW_TOOLS:-0}"
        echo "Total commits: ${TOTAL_COMMITS:-0}"
        echo "---"
        echo "SCRIPT HEALTH:"
        if [ "${#HEALTH_ALERTS[@]}" -eq 0 ] && [ "${#SKIPPED_PHASES[@]}" -eq 0 ]; then
            echo "  OK: no script alerts or skipped phases."
        else
            if [ "${#HEALTH_ALERTS[@]}" -gt 0 ]; then
                echo "  Alerts (${#HEALTH_ALERTS[@]}):"
                for item in "${HEALTH_ALERTS[@]}"; do
                    echo "  - $item"
                done
            fi
            if [ "${#SKIPPED_PHASES[@]}" -gt 0 ]; then
                echo "  Skipped phases (${#SKIPPED_PHASES[@]}):"
                for item in "${SKIPPED_PHASES[@]}"; do
                    echo "  - $item"
                done
            fi
        fi
        echo "---"
        echo "If script health is not OK, review logs/nightly-build.log before the next automated run."
    } > "$REPORT_FILE"
}

HEALTH_ALERTS=()
SKIPPED_PHASES=()
REPO_DIRTY_AT_START=0

# Write data/nightly-status.json on EVERY exit (the shared nightly-site.sh already does this).
# Without it the cross-property digest could not tell "tools ran and completed" from "no status
# file" and rendered "cannot confirm it worked" for the money-maker every day. Tools' engine has
# no content/build/deploy vars, so map: exit_code = the honest always-written signal; deploy from
# the push result; health-alert count surfaced. Installed BEFORE the preflight gate so even a
# --pre abort (exit 2) records a status instead of leaving a stale file behind.
write_nightly_status() {
  local rc=$?
  [ "${_TEAMZ_STATUS_WRITTEN:-0}" = "1" ] && return 0
  _TEAMZ_STATUS_WRITTEN=1
  local deploy="unknown"
  if [ "${PUSH_EXIT:-1}" -eq 0 ] || [ "${RETRY_EXIT:-1}" -eq 0 ]; then
    deploy="ok"
  elif [ -n "${PUSH_EXIT:-}" ] || [ -n "${RETRY_EXIT:-}" ]; then
    deploy="failed"
  fi
  mkdir -p "$PROJECT_DIR/data" 2>/dev/null || return 0
  python3 - "$PROJECT_DIR/data/nightly-status.json" "$rc" "https://tool.teamzlab.com/" \
           "$PLIST_NAME" "$deploy" "${#HEALTH_ALERTS[@]}" <<'PYEOF' 2>/dev/null || true
import json, sys, datetime
path, rc, site, label, deploy, alerts = sys.argv[1:7]
json.dump({
    "site": site,
    "label": label,
    "finished_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "exit_code": int(rc),
    "content": "n/a:tools-engine",
    "build": "ok" if int(alerts) == 0 else f"ok:{alerts}-health-alerts",
    "deploy": deploy,
    "health_alerts": int(alerts),
}, open(path, "w"), indent=2)
PYEOF
}
trap write_nightly_status EXIT

# 0. PREFLIGHT (--pre) — the ONE loud gate, ahead of any git op or producer. A wrong root, a
# renamed Planner column (the original 11k-keyword bug), a 0-page scan, or a dead SC/GA4 token
# ABORTS the night loudly instead of "succeeding" while building off nothing. config.sh already
# exported TEAMZ_HOST_SITE_ROOT; MIN_HTML floor (tools has ~6967 pages) guards the "scanned 0
# pages, printed clean" class. Verified 2026-07-18: --pre passes clean against this repo (rc=0).
if [ -f "$_SCRIPT_DIR/../py/nightly-preflight.py" ] && command -v python3 >/dev/null 2>&1; then
    if ! TEAMZ_PREFLIGHT_MIN_HTML="${TEAMZ_PREFLIGHT_MIN_HTML:-1000}" \
         python3 "$_SCRIPT_DIR/../py/nightly-preflight.py" --pre; then
        echo "  ✗ PREFLIGHT --pre failed — refusing to run the tools nightly on a bad root/inputs."
        echo "    (preflight wrote data/preflight-status.json and fired a Mac alert; fix, then rerun.)"
        exit 2
    fi
fi

# Block the cron ONLY on dirty SOURCE files (a half-edited tool HTML, script, or config).
# Ignore whole generated-output DIRS (data/, logs/, docs/, .claude-memory/) + the root files
# the pre-commit hook regenerates. Dir-based, NOT per-filename, so a NEW data artifact can
# never self-lock the cron again — the bug that froze shipping each time a guard added a file.
#
# The status-code class MUST match any 2-char porcelain code (not just " M"/"M "/"??") — a
# narrower class here silently un-forgives the exact same paths it was written to forgive.
# Proven live 2026-07-18 through 07-23: a staged-add ("A ", .../gsc-404-manual-export-*.json)
# and an unstaged delete (" D", .../batch-cand-01.csv) each blocked the cron for real, both
# inside directories this rule already intends to forgive, because the old class
# `[ M][ M]|\?\?` only recognized plain-modify and untracked. Root cause: an interactive
# Claude Code session running maintenance scripts in this same checkout during the day can
# leave a file mid `git add` (a real ~90s window — see the pre-commit hook) right as the cron's
# own dirty-check runs. This regex fix doesn't close that race, it closes the narrower bug of
# forgiveness depending on which status code the race happened to produce.
DIRTY_FILES="$(git status --porcelain --ignore-submodules 2>/dev/null | grep -vE '^.{2} (data/.*|logs/.*|docs/.*|\.claude-memory/.*|tools\.json|webview-incompat\.json|sitemap\.xml|search-index\.js|shared/js/search-index\.js|llms\.txt|llms-full\.txt|index\.html|sw\.js|\.htaccess)$' || true)"
if [ -n "$DIRTY_FILES" ]; then
    # Distinguish leftover BUILD OUTPUT (a tool index.html a prior run enhanced but whose
    # commit was skipped) from genuine human SOURCE WIP (scripts/py/css/config). Leftover tool
    # pages ALONE must never deadlock the cron forever (the 2026-06 freeze): commit them and
    # continue. Real source edits still block (protect WIP) — but now we ALERT, so a block is
    # never silent again.
    SOURCE_DIRTY="$(printf '%s\n' "$DIRTY_FILES" | grep -vE '/index\.html$' || true)"
    if [ -z "$SOURCE_DIRTY" ]; then
        echo "  Self-heal: only leftover tool page(s) uncommitted (no source WIP) — committing to unblock the cron."
        printf '%s\n' "$DIRTY_FILES" | cut -c4- | while IFS= read -r p; do [ -n "$p" ] && git add -- "$p" 2>/dev/null; done
        if git commit --no-verify -m "recovery: commit leftover enhanced tool page(s) to unblock nightly build" 2>/dev/null; then
            echo "    Recovery commit created — cron unblocked."
            record_health_alert "Nightly self-healed a leftover-tool-page deadlock (auto-committed $(printf '%s' "$DIRTY_FILES" | grep -c .) page(s)). Review the recovery commit."
        else
            echo "    Nothing to recover-commit (already clean)."
        fi
    else
        REPO_DIRTY_AT_START=1
        echo "  Warning: repo dirty at start on SOURCE files — will NOT auto-commit/push (protecting WIP):"
        printf '%s\n' "$SOURCE_DIRTY" | sed 's/^/    /'
        record_health_alert "Nightly BLOCKED at start: dirty source WIP ($(printf '%s' "$SOURCE_DIRTY" | grep -c . ) file(s)). Commit or stash to unblock — $(printf '%s' "$SOURCE_DIRTY" | head -3 | cut -c4- | tr '\n' ' ')"
        osascript -e 'display notification "Nightly build BLOCKED on dirty source files — see nightly log" with title "Teamz Build BLOCKED" sound name "Basso"' 2>/dev/null
    fi
fi

# --- SEO toolchain health-check (non-blocking; catches silent data failures like
#     the Google Trends bug that returned blank for months with no alarm) ---
echo ""
echo "=== SEO toolchain health-check ==="
if HC_OUT="$(python3 "$_SCRIPT_DIR/../py/seo-healthcheck.py" 2>&1)"; then
    printf '%s\n' "$HC_OUT" | sed 's/^/  /'
else
    printf '%s\n' "$HC_OUT" | sed 's/^/  /'
    record_health_alert "SEO health-check found a RED — a data source may be silently broken (see log top)"
fi

# Pull latest changes first. This runs seconds after launchd wakes the machine, so it is the
# step MOST likely to meet a network that is not up yet — and it is also the cheapest place to
# wait for one, because everything after it depends on the network anyway.
if [ "$REPO_DIRTY_AT_START" -eq 0 ] && host_up_within github.com; then
    git pull --ff-only origin main 2>/dev/null || echo "  Warning: git pull skipped (fast-forward unavailable)"
else
    skip_phase "git pull (repo dirty at start or github.com unavailable)"
fi

# Phase 0: Research — find high-value keywords (zero quota, bash scripts only)
echo ""
echo "=== Phase 0: Keyword Research (zero quota) ==="

# Clean previous research
rm -f /tmp/nightly-suggestions.txt /tmp/nightly-trends.txt /tmp/nightly-multilang.txt /tmp/nightly-research.txt

# Google Autocomplete suggestions for high-RPM niches
echo "  Researching keywords..."
for keyword in "stamp duty calculator" "retirement calculator" "tax calculator" "salary calculator" "mortgage calculator" "budget planner" "loan calculator" "investment calculator" "insurance calculator" "cost of living" "rent vs buy" "salary comparison" "profit margin calculator" "invoice generator" "contract template"; do
    ./scripts/build-seo-audit.sh --suggest "$keyword" 2>/dev/null | grep -v "^$" >> /tmp/nightly-suggestions.txt
done

# Pinterest-friendly keywords (finance/health/budget perform best on Pinterest)
echo "  Researching Pinterest-friendly keywords..."
for keyword in "budget template" "savings plan" "debt payoff" "meal planner" "wedding budget" "baby cost" "home buying checklist" "retirement plan"; do
    ./scripts/build-seo-audit.sh --suggest "$keyword" 2>/dev/null | grep -v "^$" >> /tmp/nightly-suggestions.txt
done

# Comparison page keywords (X vs Y = high intent)
echo "  Researching comparison keywords..."
for keyword in "roth vs traditional" "rent vs buy" "lease vs buy" "term vs whole life" "hsa vs fsa" "fixed vs variable rate" "sole trader vs company" "etf vs mutual fund"; do
    ./scripts/build-seo-audit.sh --suggest "$keyword" 2>/dev/null | grep -v "^$" >> /tmp/nightly-suggestions.txt
done

# Get trending/breakout keywords
echo "  Checking trends..."
./scripts/build-seo-audit.sh --batch-trends 2>/dev/null | head -30 >> /tmp/nightly-trends.txt

# Keyword volume estimation
echo "  Checking keyword volumes..."
./scripts/build-seo-audit.sh --bing-volume "stamp duty calculator" "retirement planner" "salary comparison" "budget calculator" "tax estimator" 2>/dev/null >> /tmp/nightly-research.txt

# Check keyword cannibalization
echo "  Checking cannibalization..."
./scripts/build-seo-audit.sh --cannibalize 2>/dev/null | head -20 >> /tmp/nightly-research.txt

# Check seasonal relevance
echo "  Checking seasonal calendar..."
MONTH=$(date '+%m')
case $MONTH in
    01|02|03|04) echo "SEASONAL: Tax season (US/UK/AU). Build tax tools." >> /tmp/nightly-research.txt ;;
    04|05|06) echo "SEASONAL: DE Steuererklärung, Nordic tax, wedding season." >> /tmp/nightly-research.txt ;;
    07|08|09) echo "SEASONAL: Back to school, SG National Day, summer travel." >> /tmp/nightly-research.txt ;;
    10|11|12) echo "SEASONAL: Black Friday, year-end finance, holiday budgets." >> /tmp/nightly-research.txt ;;
esac

# Ensure backlog file exists
BACKLOG="$PROJECT_DIR/docs/tool-backlog.md"
if [ ! -f "$BACKLOG" ]; then
    echo "# Tool Backlog" > "$BACKLOG"
    echo "## Pending" >> "$BACKLOG"
    echo "" >> "$BACKLOG"
fi

# Check which existing tools need ES/PT versions
echo "  Checking multilang gaps..."
python3 scripts/build-multilang.py suggest 2>/dev/null | grep "→" > /tmp/nightly-multilang.txt

echo "  Research done. All results saved for Claude to use."

# Phase 1: Run all maintenance scripts (no Claude needed, zero quota)
echo ""
echo "=== Phase 1: Maintenance Scripts (zero quota) ==="
# Search index always runs — its output (tools.json, search-index.js, sitemap,
# llms*, webview-incompat.json, index.html counts) is in the dirty-exclusion
# list above, so it self-heals and never traps the guard.
run_phase_cmd "Search index rebuild" 5 "./scripts/build-search-index.sh"

# Tool-HTML-editing maintenance runs ONLY on a clean start. On a dirty start
# Phase 5 skips the commit, so any tool-page edit these scripts make (schema
# blocks, orphan cross-links, SEO autofixes) would persist as UN-excluded dirt
# and permanently re-trip REPO_DIRTY_AT_START on every future run = self-lock.
# (Root cause of the 2026-05-30 4-run enhance/deploy stall.) Skip them when
# dirty; they resume automatically on the next clean run.
if [ "$REPO_DIRTY_AT_START" -eq 0 ]; then
    run_phase_cmd "Static schema rebuild" 3 "python3 scripts/build-static-schema.py"
    run_phase_cmd "Orphan fix" 3 "python3 scripts/build-fix-orphans.py fix"
    # Repairs renderRelatedTools entries pointing at slugs that have no page on
    # disk. Sits in this clean-start block because it EDITS tool HTML, exactly
    # like the two phases around it.
    #
    # HOST-GUARDED: this file is symlinked by 5 properties (tools, learn,
    # landing-pages, hazira, ai_resume_checker) and the script exists only in
    # teamzlab-tools. Without the -f test the other four would run an
    # HTML-editing script that is not theirs.
    #
    # Why it is wired at all: the script has existed since 2026-05 (commit
    # 48a2841, "heal internal-link graph — 0->74 health score") and NOTHING ever
    # called it — grepping its name across every .sh/.py/.json/.yml matched only
    # its own docstring. It was run by hand once, and every page generated
    # afterwards re-broke the graph. By 2026-07-22 that was 398 distinct dead
    # URLs and 1,430 broken link edges. Googlebot renders this JS, follows the
    # links and logs 404s — GSC "Not found (404)" examples were last-crawled
    # Jul 10-11 2026 and were all real calculator slugs that never existed in
    # git. A dormant fixer looks identical to a working one in every report.
    [ -f scripts/build-fix-broken-related.py ] && \
        run_phase_cmd "Broken related-tools links" 5 "python3 scripts/build-fix-broken-related.py --apply"
    run_phase_cmd "SEO auto-fix" 5 "./scripts/build-seo-audit.sh --fix"
else
    echo "  - Skipping tool-editing maintenance (static-schema, orphan-fix, seo-fix):"
    echo "    repo dirty at start; their edits can't be committed and would re-lock the guard."
fi

echo "  SEO monitoring..."
run_phase_cmd "Uptime check" 3 "python3 scripts/build-uptime-check.py"
run_phase_cmd "Schema validation" 5 "python3 scripts/build-schema-validate.py"
run_phase_cmd "Crawl snapshot + diff" 5 "python3 scripts/build-crawl-diff.py"
run_phase_cmd "GSC anomalies" 10 "python3 scripts/build-gsc-anomalies.py --json-only"
run_phase_cmd "Money-page growth snapshot" 10 "python3 teamz-company-automation/py/build-money-tracker.py --today $(date +%Y-%m-%d) || true"
run_phase_cmd "GSC broken pages → auto-redirect" 10 "python3 scripts/build-gsc-broken-pages.py"
# Grades the enhancement engine against a control group of pages it never touched.
# Until 2026-07-22 nothing had ever checked whether a rewritten page improved — no
# script read data/enhancement-log.json, and that ledger tracks 4 hand-edited tools
# while the engine has enhanced 366 pages. So the engine ran for months with no
# evidence it worked, in either direction.
# The control group is the whole point. A raw before/after on the treated pages alone
# scored +6,205 clicks on first run and read as a triumph — it was the World Cup
# landing inside the window. Read the ENHANCED and CONTROL lines together or not at all.
# Read-only (GSC + git log), so it is safe outside the dirty-guard block.
# HOST-GUARDED: this file is symlinked by 5 properties; the script exists only in tools.
[ -f scripts/build-enhance-outcome.py ] && \
    run_phase_cmd "Enhance outcome vs control" 10 "python3 scripts/build-enhance-outcome.py"
# Scores each page by what its AUDIENCE is worth, not by its rank. The engine ranks
# work by GSC position + impressions, both geography-blind, on a site where geography
# is the dominant revenue factor: a German visitor is worth ~71 Bangladeshi ones
# (DE £30.39 RPM vs BD £0.43, measured 2026-07-22), and Bangladesh is 22% of views
# and 1.4% of the money. Audited the same day: across every script here and in
# teamz-company-automation/py, 8 call sites ask GSC for ["page"], 5 for ["query"],
# and NONE for ["country"] or ["device"]. This is the missing input.
# Read-only; writes data/geo-value.json. Fails closed if the AdSense join breaks,
# because a silent fallback to one average RPM reproduces the exact blindness it
# is meant to remove (it did, on the first run — all 488 pages scored an identical £3.45).
[ -f scripts/build-geo-value.py ] && \
    run_phase_cmd "Geo value per page" 10 "python3 scripts/build-geo-value.py --json-only"

echo "  Checking freshness (stale data)..."
run_phase_cmd "Freshness validation" 10 "./scripts/build-validate-freshness.sh"

[ -f scripts/build-fix-hub-unlinked.py ] && {
    echo "  Healing hub-page link gaps (auto-fix)..."
    run_phase_cmd "Hub link auto-heal" 5 "python3 scripts/build-fix-hub-unlinked.py --apply"
}

echo "  Checking internal link health..."
run_phase_cmd "Internal link health" 5 "scripts/build-internal-links.sh --quick"

echo "  Running QA check..."
run_phase_cmd "QA check" 10 "./scripts/build-qa-check.sh"

# NOTE: the Mobile UX gate is intentionally NOT here. This phase runs BEFORE the Phase-4
# agent edits any tool, so --changed would see nothing. It now runs in Phase 5 (post-edit,
# pre-push) where get_changed_tools() actually contains the agent's enhanced tools.

# Phase 2: Request indexing for any new pages
echo ""
echo "=== Phase 2: Request Indexing ==="
if can_resolve_host indexing.googleapis.com && can_resolve_host oauth2.googleapis.com; then
    run_phase_cmd "Indexing request" 10 "python3 scripts/build-request-indexing.py"
else
    skip_phase "Google indexing request (Google APIs unavailable)"
fi

# Phase 3: Pull data (uses local API tokens — only works locally!)
echo ""
echo "=== Phase 3: Pull Data (local tokens) ==="
if can_resolve_host searchconsole.googleapis.com && can_resolve_host oauth2.googleapis.com; then
    run_phase_cmd "Search Console pull" 10 "./scripts/build-search-console.sh --status"
else
    skip_phase "Search Console pull (searchconsole.googleapis.com unavailable)"
fi

if can_resolve_host analyticsdata.googleapis.com && can_resolve_host oauth2.googleapis.com; then
    run_phase_cmd "GA4 analytics pull" 20 "./scripts/build-analytics.sh --all"
else
    skip_phase "GA4 analytics pull (analyticsdata.googleapis.com unavailable)"
fi

if can_resolve_host adsense.googleapis.com && can_resolve_host oauth2.googleapis.com; then
    run_phase_cmd "AdSense pull" 10 "./scripts/build-adsense.sh"
else
    skip_phase "AdSense pull (adsense.googleapis.com unavailable)"
fi

if can_resolve_host clarity.ms; then
    run_phase_cmd "Clarity pull" 20 "./scripts/build-clarity.sh 1"
else
    skip_phase "Clarity pull (clarity.ms unavailable)"
fi

if can_resolve_host pagespeedonline.googleapis.com; then
    run_phase_cmd "PageSpeed pull" 10 "./scripts/build-pagespeed.sh"
else
    skip_phase "PageSpeed pull (pagespeedonline.googleapis.com unavailable)"
fi

run_phase_cmd "Distribution status" 10 "python3 scripts/distribute/distribute.py list"

# Phase 3.5: Refresh research cache (DataForSEO volumes, Firecrawl competitor maps,
# Bing queries, Reddit RPM data) — feeds Phase 4 Claude agent with fresh data
run_phase_cmd "Research cache refresh" 5 "./scripts/build-research-cache.sh"
run_phase_cmd "Ideas brief" 2 "./scripts/build-ideas.sh --quick"

# Dead-tool revival: find demand re-targets for indexed-but-no-demand pages.
# Opt-in via data/.dead-revival-enabled (other consumers unaffected). Non-blocking,
# low cap (4/night), Trends-disabled for speed. Output feeds Pool 9 of the enhance
# queue, which Phase 4's Claude reviews before applying. Output files are in the
# dirty-guard ignore-list so they can never self-lock the nightly.
if [ -f "$PROJECT_DIR/data/.dead-revival-enabled" ] && [ "$REPO_DIRTY_AT_START" -eq 0 ]; then
    echo ""
    echo "=== Dead-tool revival: find demand re-targets ==="
    python3 "$_SCRIPT_DIR/../py/build-dead-revival.py" --cap 20 2>&1 | sed 's/^/  /' || echo "  (dead-revival skipped — non-fatal)"
fi

# Phase 4: Run Claude to build tools (uses quota)
echo ""
echo "=== Phase 4: Claude Build Agent ==="
PROMPT_FILE="$PROJECT_DIR/scripts/nightly-build-prompt.md"
BUILD_MODEL="${MODEL:-opus}"
echo "  Starting $BUILD_MODEL agent... (live output below)"
echo "  ─────────────────────────────────────"
echo "  Model: $BUILD_MODEL"
if [ "$REPO_DIRTY_AT_START" -ne 0 ]; then
    skip_phase "Claude build (repo dirty at start)"
    BUILD_EXIT=0
elif ! has_command claude; then
    skip_phase "Claude build (claude CLI not installed)"
    BUILD_EXIT=0
elif ! can_resolve_host api.anthropic.com; then
    skip_phase "Claude build (api.anthropic.com unavailable)"
    BUILD_EXIT=0
else
    # Hang-watchdog (macOS has no `timeout` binary): run the agent in the
    # background with a sleeper-killer beside it. A frozen agent gets TERM at
    # AGENT_MAX_SECONDS, KILL 60s later — so it can NEVER zombie for hours and
    # block later launchd fires (the 29h-freeze that locked 2026-05-31→06-01).
    # A normal finish cancels the watchdog immediately.
    AGENT_MAX_SECONDS="${AGENT_MAX_SECONDS:-2700}"
    claude --print --verbose --dangerously-skip-permissions --model "$BUILD_MODEL" -p "$(cat "$PROMPT_FILE")" 2>&1 &
    AGENT_PID=$!
    ( sleep "$AGENT_MAX_SECONDS"; kill -TERM "$AGENT_PID" 2>/dev/null; sleep 60; kill -KILL "$AGENT_PID" 2>/dev/null ) &
    AGENT_WATCHDOG_PID=$!
    wait "$AGENT_PID"
    BUILD_EXIT=$?
    kill "$AGENT_WATCHDOG_PID" 2>/dev/null
    wait "$AGENT_WATCHDOG_PID" 2>/dev/null
    if [ "$BUILD_EXIT" -eq 143 ] || [ "$BUILD_EXIT" -eq 137 ]; then
        echo "  ✗ Claude agent TIMED OUT (>${AGENT_MAX_SECONDS}s) — killed to prevent zombie. Next run retries fresh."
        record_health_alert "Claude agent timed out (${AGENT_MAX_SECONDS}s) — killed to prevent zombie"
        osascript -e "display notification \"Claude agent TIMED OUT, killed to avoid zombie. Next run retries.\" with title \"Teamz Build TIMEOUT\" sound name \"Basso\"" 2>/dev/null
    fi

    if [ "$BUILD_EXIT" -ne 0 ]; then
        echo "  ✗ Claude build failed (exit code $BUILD_EXIT)"
        record_health_alert "Claude build failed (exit $BUILD_EXIT)"
        osascript -e "display notification \"Claude build FAILED (exit $BUILD_EXIT). Check logs.\" with title \"Teamz Build ERROR\" sound name \"Basso\"" 2>/dev/null
    fi
fi

# Phase 5: Final push
echo ""
echo "=== Phase 5: Auto-Fix + Push ==="
if [ "$REPO_DIRTY_AT_START" -ne 0 ]; then
    echo "  Repo was dirty at start."
    skip_phase "auto-fix commit and push (protecting existing local work)"
    NEW_TOOLS=0
    TOTAL_COMMITS=0
else
echo "  Running auto-fix on all changed files..."

# Get list of changed HTML files
CHANGED_FILES=$(git diff --name-only HEAD 2>/dev/null | grep '\.html$')
if [ -z "$CHANGED_FILES" ]; then
    CHANGED_FILES=$(git diff --name-only HEAD~1 2>/dev/null | grep '\.html$')
fi

FIXES=0
for f in $CHANGED_FILES; do
    [ ! -f "$f" ] && continue

    # 1. Fix duplicate theme.js loads
    count=$(grep -c 'src="/branding/js/theme.js"' "$f" 2>/dev/null)
    if [ "$count" -gt 1 ]; then
        python3 -c "
import re
with open('$f','r') as fh: c=fh.read()
c=re.sub(r'<body>\s*<script src=\"/branding/js/theme\.js\"></script>', '<body>', c, count=1)
with open('$f','w') as fh: fh.write(c)
"
        echo "    Fixed: duplicate theme.js in $f"
        FIXES=$((FIXES + 1))
    fi

    # 2. Fix hardcoded header (should be empty for common.js to render)
    if grep -q '<header id="site-header" class="site-header"><a' "$f" 2>/dev/null; then
        python3 -c "
import re
with open('$f','r') as fh: c=fh.read()
c=re.sub(r'<header id=\"site-header\" class=\"site-header\">.*?</header>', '<header id=\"site-header\" class=\"site-header\"></header>', c, flags=re.DOTALL)
with open('$f','w') as fh: fh.write(c)
"
        echo "    Fixed: hardcoded header in $f"
        FIXES=$((FIXES + 1))
    fi

    # 3. Fix hardcoded footer (should be empty for common.js to render)
    if grep -q '<footer id="site-footer" class="site-footer"><div' "$f" 2>/dev/null; then
        python3 -c "
import re
with open('$f','r') as fh: c=fh.read()
c=re.sub(r'<footer id=\"site-footer\" class=\"site-footer\">.*?</footer>', '<footer id=\"site-footer\" class=\"site-footer\"></footer>', c, flags=re.DOTALL)
with open('$f','w') as fh: fh.write(c)
"
        echo "    Fixed: hardcoded footer in $f"
        FIXES=$((FIXES + 1))
    fi

    # 4. Fix alert() → showToast()
    if grep -q 'alert(' "$f" 2>/dev/null; then
        sed -i '' "s/alert(/window.showToast(/g" "$f"
        echo "    Fixed: alert() → showToast() in $f"
        FIXES=$((FIXES + 1))
    fi

    # 5. Fix style.display = '' → showEl()
    if grep -q "style\.display = ''" "$f" 2>/dev/null; then
        echo "    Warning: style.display='' found in $f (needs manual fix)"
    fi

    # 6. Fix hardcoded hex colors (common ones Sonnet uses)
    if grep -qE '#[0-9a-fA-F]{3,6}' "$f" 2>/dev/null; then
        python3 -c "
import re
with open('$f','r') as fh: c=fh.read()
# Only fix colors in style blocks, not in meta/schema
replacements = {
    '#ffffff': 'var(--bg)', '#fff': 'var(--bg)',
    '#000000': 'var(--text)', '#000': 'var(--text)',
    '#333': 'var(--text)', '#333333': 'var(--text)',
    '#666': 'var(--text-muted)', '#666666': 'var(--text-muted)',
    '#999': 'var(--text-muted)', '#999999': 'var(--text-muted)',
    '#f5f5f5': 'var(--surface)', '#f0f0f0': 'var(--surface)',
    '#e0e0e0': 'var(--border)', '#ddd': 'var(--border)', '#ccc': 'var(--border)',
    '#27ae60': 'var(--heading)', '#2ecc71': 'var(--heading)',
    '#e74c3c': 'var(--heading)', '#e63946': 'var(--heading)',
    '#3498db': 'var(--heading)', '#2196f3': 'var(--heading)',
}
changed = False
for old, new in replacements.items():
    if old.lower() in c.lower():
        c = re.sub(re.escape(old), new, c, flags=re.IGNORECASE)
        changed = True
if changed:
    with open('$f','w') as fh: fh.write(c)
    print('    Fixed: hardcoded colors in $f')
" 2>/dev/null
        FIXES=$((FIXES + 1))
    fi

    # 7. Fix missing responsive CSS (add basic if @media not found)
    if ! grep -q '@media' "$f" 2>/dev/null; then
        if grep -q 'tool-calculator' "$f" 2>/dev/null; then
            echo "    Warning: no @media responsive CSS in $f"
        fi
    fi

    # 8. Fix missing ad-slot
    if ! grep -q 'ad-slot' "$f" 2>/dev/null; then
        if grep -q 'tool-content' "$f" 2>/dev/null; then
            python3 -c "
with open('$f','r') as fh: c=fh.read()
if '<div class=\"ad-slot\">' not in c and '<section class=\"tool-content\">' in c:
    c=c.replace('<section class=\"tool-content\">', '<div class=\"ad-slot\">Ad Space</div>\n    <section class=\"tool-content\">')
    with open('$f','w') as fh: fh.write(c)
    print('    Fixed: added missing ad-slot in $f')
" 2>/dev/null
            FIXES=$((FIXES + 1))
        fi
    fi

done

echo "  Auto-fixed $FIXES issues."

# Mobile UX gate — runs HERE (post-edit, pre-push) so get_changed_tools() contains the
# agent's actually-enhanced tools (390x844 iPhone: horizontal-scroll + locked-viewport =
# HARD, small tap-targets/fonts/contrast = WARN). Non-blocking: the global shared/css 44px
# rule already handles tap targets site-wide; this is the safety net that ALERTS on a real
# break so it surfaces instead of shipping silently.
echo "  Mobile UX gate (post-edit, agent's changed tools)..."
MOBILE_OUT=$(python3 teamz-company-automation/py/qa-mobile-ux.py --changed 2>&1); MOBILE_EXIT=$?
echo "$MOBILE_OUT" | tail -10
if [ "$MOBILE_EXIT" -ne 0 ]; then
    record_health_alert "Mobile UX gate HARD fail on an enhanced tool (horizontal scroll / locked viewport) — see nightly log"
    osascript -e 'display notification "Mobile UX HARD fail on an enhanced tool — check nightly log" with title "Teamz Mobile Gate"' 2>/dev/null
fi

# URL-hygiene + indexability guard — the cron commits --no-verify (bypassing the pre-commit
# hook), so re-run the same checks on the agent's changed set here. Catches a born-wrong
# canonical / og:url (the /career/career/ class that Google drops), interior // in emitted
# URLs, param/fragment in canonical. WARN-only (can't block a --no-verify commit) but fires a
# health alert + notification so a real indexability defect surfaces instead of shipping silent.
echo "  URL-hygiene + indexability guard (post-edit)..."
HYG_OUT=$(python3 scripts/build-url-hygiene-guard.py --nightly 2>&1); echo "$HYG_OUT" | tail -8
if echo "$HYG_OUT" | grep -qE "BLOCK=[1-9]"; then
    record_health_alert "URL-hygiene guard found an indexability defect on an enhanced tool (canonical / og:url / //) — see data/url-hygiene-latest.json"
    osascript -e 'display notification "Indexability defect on an enhanced tool — check url-hygiene-latest.json" with title "Teamz URL Guard"' 2>/dev/null
fi

# Run SEO auto-fixes
echo "  Running SEO auto-fixes..."
./scripts/build-seo-audit.sh --fix 2>/dev/null | tail -3

# Rebuild schemas and search index after fixes
python3 scripts/build-static-schema.py 2>/dev/null | tail -2
./scripts/build-search-index.sh 2>/dev/null | tail -3
python3 scripts/build-fix-orphans.py fix 2>/dev/null | tail -2

# Live league standings for the table predictors (tools only — guarded, see below).
#
# The predictors' "vs actual" panel is the reason a visitor comes back every matchweek instead
# of using the tool once: it scores their saved prediction against the real table. It reads
# data/football/<comp>.json, and that file was written exactly ONCE, when the Premier League
# predictor was created. Nothing ever refreshed it — the fetcher existed but was wired to no
# nightly, no cron and no launchd — so the panel was pinned on "unlocks when the season kicks
# off" and would have stayed there through the entire season it was built for.
#
# No API key required. The fetcher prefers football-data.org when a key is present at
# ~/.config/teamzlab/football-data-key.txt and otherwise computes the table from openfootball's
# public match results, which is the path in use. It logs and continues on a single dead feed,
# so one competition cannot take the night down.
#
# Guarded because this file is shared with the apps and learn properties: neither has
# scripts/build-football-standings.py nor a data/football/ directory, so this block is a no-op
# there. Same pattern as the sitemap call below.
if [ -f scripts/build-football-standings.py ]; then
    echo "  Refreshing league standings (table predictors)..."
    python3 scripts/build-football-standings.py 2>&1 | sed 's/^/  /' \
        || echo "  (standings refresh failed — non-fatal)"
fi

# NFL playoff predictor feed — same pattern as the football block above.
# ESPN -> nflverse -> never-regress ladder lives inside the fetcher.
if [ -f scripts/build-nfl-standings.py ]; then
    echo "  Refreshing NFL standings (playoff predictor)..."
    python3 scripts/build-nfl-standings.py 2>&1 | sed 's/^/  /' \
        || echo "  (NFL standings refresh failed — non-fatal)"
fi

# Data-freshness sentinel — runs AFTER the feed refreshers so it judges
# tonight's data, not yesterday's. Replaces the old inline football
# staleness heredoc: the same kickoff-passed-but-empty rule now lives in
# data/freshness-manifest.json alongside the NFL feed age rule, the
# fixtures-in-the-past rule and the event-calendar build-window rule.
# run_phase_cmd executes in this shell, so record_health_alert appends
# survive (the subshell trap the old heredoc comment documented).
if [ -f scripts/build-data-freshness.py ]; then
    run_phase_cmd "Data freshness sentinel" 10 python3 scripts/build-data-freshness.py
fi

# Rebuild sitemap so every nightly commit carries a sitemap matching the on-disk indexable set
# (build-sitemap.sh already excludes noindex + redirect stubs). Closes the proven gap where a
# new/changed page shipped without a sitemap update — reuse of the existing correct script.
[ -f scripts/build-sitemap.sh ] && bash scripts/build-sitemap.sh 2>/dev/null | tail -2

# Stage generated/site changes, but leave volatile logs and lock files out of the commit
git add -A -- . \
    ':(exclude)logs/*.log' \
    ':(exclude)scripts/seo-latest-report.txt' \
    ':(exclude)scripts/seo-logs/*.log' \
    ':(exclude)seo-logs/*.log' \
    ':(exclude).claude/scheduled_tasks.lock' 2>/dev/null

if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "Auto-fix: Sonnet cleanup ($FIXES issues fixed)" --no-verify 2>/dev/null
    echo "  Committed auto-fixes."
else
    echo "  No commit-worthy changes after exclusions."
fi

# Push with --no-verify.
#
# host_up_within, NOT can_resolve_host: this single lookup is the gate on the ONLY step that
# makes the night's work public. When it failed on 2026-07-12 it took 20 commits with it.
if host_up_within github.com; then
    PUSH_OUTPUT=$(git push origin main --no-verify 2>&1)
    PUSH_EXIT=$?
    echo "$PUSH_OUTPUT"

    if [ "$PUSH_EXIT" -ne 0 ]; then
        echo "  ✗ Push failed! Trying pull rebase + push..."
        git pull --rebase origin main 2>/dev/null
        RETRY_OUTPUT=$(git push origin main --no-verify 2>&1)
        RETRY_EXIT=$?
        echo "$RETRY_OUTPUT"
        if [ "$RETRY_EXIT" -ne 0 ]; then
            record_health_alert "git push failed after retry"
        fi
    fi

    # Deploy step: purge Cloudflare so freshly-pushed HTML serves immediately.
    # Cloudflare caches HTML — without this users get stale pages for hours
    # after a successful push (hard rule: purge after every real deploy).
    if { [ "${PUSH_EXIT:-1}" -eq 0 ] || [ "${RETRY_EXIT:-1}" -eq 0 ]; } && \
       ! printf '%s %s' "$PUSH_OUTPUT" "$RETRY_OUTPUT" | grep -q 'Everything up-to-date'; then
        echo "  Purging Cloudflare cache (fresh deploy)..."
        python3 "$_SCRIPT_DIR/../py/cloudflare-purge.py" --site https://tool.teamzlab.com/ 2>&1 | tail -3 \
            || echo "  ⚠ Cloudflare purge failed — pushed but cache may be stale until next purge."
    fi
else
    skip_phase "git push (github.com unavailable)"
fi

# Count what was built
NEW_TOOLS=$(git log --oneline --since="2 hours ago" --grep="Add " | wc -l | tr -d ' ')
TOTAL_COMMITS=$(git log --oneline --since="2 hours ago" | wc -l | tr -d ' ')
fi

# 99. PREFLIGHT (--post) — after every phase: assert the OUTPUT artifacts are sane. Non-fatal
# (the run already happened) but LOUD: preflight exits 1, fires a Mac alert, and refreshes
# data/preflight-status.json so the morning digest / /growth sees a fresh, honest verdict.
if [ -f "$_SCRIPT_DIR/../py/nightly-preflight.py" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$_SCRIPT_DIR/../py/nightly-preflight.py" --post \
        || record_health_alert "PREFLIGHT --post FAILED (see data/preflight-status.json)"
fi

write_health_report

echo ""
echo "=== DONE — $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
echo "  New tools built: $NEW_TOOLS"
echo "  Total commits: $TOTAL_COMMITS"

# Mac notification
if [ "$NEW_TOOLS" -gt 0 ]; then
    osascript -e "display notification \"Built $NEW_TOOLS new tools. $TOTAL_COMMITS commits pushed.\" with title \"Teamz Build SUCCESS\" sound name \"Glass\"" 2>/dev/null
else
    osascript -e "display notification \"No new tools built. $TOTAL_COMMITS maintenance commits.\" with title \"Teamz Build Done\" sound name \"Purr\"" 2>/dev/null
fi
