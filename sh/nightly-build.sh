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
PLIST_NAME="com.teamzlab.nightly-build"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

# Handle flags
if [ "$1" = "--install" ]; then
    echo "Installing nightly build agent..."
    mkdir -p "$LOG_DIR"
    mkdir -p "$HOME/Library/LaunchAgents"

    cat > "$PLIST_PATH" << 'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.teamzlab.nightly-build</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects/teamzlab-tools/scripts/nightly-build.sh</string>
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
    <string>/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects/teamzlab-tools/logs/nightly-build.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects/teamzlab-tools/logs/nightly-build-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>HOME</key>
        <string>/Users/mdgolamkibriaemon</string>
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

    if [ -n "$output" ]; then
        printf '%s\n' "$output" | tail -n "$tail_lines"
    fi

    issue_line=$(extract_health_issue "$output")
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
# Ignore files that pre-commit hook auto-regenerates after every commit (always "dirty")
# and gitignored config files. Without this filter nightly always sees dirty repo and skips.
DIRTY_FILES="$(git status --porcelain --ignore-submodules 2>/dev/null | grep -vE '^([ M][ M]|\?\?) (tools\.json|webview-incompat\.json|sitemap\.xml|search-index\.js|llms\.txt|llms-full\.txt|index\.html|sw\.js|shared/js/search-index\.js|docs/indexing-report\.md|\.htaccess|data/research-cache/.*|data/progress/.*|data/rising-tools-.*\.json|data/gsc-broken-pages-.*\.json|data/canonical-mismatches-.*\.json|data/enhance-queue\.json|data/enhancement-log\.json|data/last-night-enhance\.md|data/cold-start-done\.txt|data/cold-start-enabled|data/dead-revival-.*\.json|data/\.dead-revival-enabled|data/manual-pull/.*|data/serp-difficulty-cache\.json|data/money-snapshots/.*|data/bing-data-.*\.json|data/gsc-anomalies-.*\.json|data/keyword-mega-batch/.*|logs/.*|.claude-memory/.*)$' || true)"
if [ -n "$DIRTY_FILES" ]; then
    REPO_DIRTY_AT_START=1
    echo "  Warning: repo is dirty at start. Nightly run will not auto-commit or auto-push."
    echo "  Dirty files (excluding auto-regenerated):"
    echo "$DIRTY_FILES" | sed 's/^/    /'
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

# Pull latest changes first
if [ "$REPO_DIRTY_AT_START" -eq 0 ] && can_resolve_host github.com; then
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

echo "  Checking freshness (stale data)..."
run_phase_cmd "Freshness validation" 10 "./scripts/build-validate-freshness.sh"

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
echo "  Starting Sonnet... (live output below)"
echo "  ─────────────────────────────────────"
PROMPT_FILE="$PROJECT_DIR/scripts/nightly-build-prompt.md"
BUILD_MODEL="${MODEL:-opus}"
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

# Run SEO auto-fixes
echo "  Running SEO auto-fixes..."
./scripts/build-seo-audit.sh --fix 2>/dev/null | tail -3

# Rebuild schemas and search index after fixes
python3 scripts/build-static-schema.py 2>/dev/null | tail -2
./scripts/build-search-index.sh 2>/dev/null | tail -3
python3 scripts/build-fix-orphans.py fix 2>/dev/null | tail -2

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

# Push with --no-verify
if can_resolve_host github.com; then
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
