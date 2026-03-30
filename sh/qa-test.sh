#!/bin/bash
# ============================================================
# Teamz Lab Tools — Automated QA Test Suite
# Tests ALL tool pages for common issues
# Usage: ./qa-test.sh [--fix] [--verbose] [--category health]
# ============================================================

set -euo pipefail
SCRIPTS="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")" && pwd)"
source "$SCRIPTS/lib/config.sh"
teamz_load_config "$0"
cd "$TEAMZ_HOST_SITE_ROOT"

if [[ "${TEAMZ_PROJECT_TYPE:-website}" == "app" ]]; then
  echo "INFO: qa-test.sh is website-focused and disabled for TEAMZ_PROJECT_TYPE=app."
  exit 2
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

FIX_MODE=false
VERBOSE=false
FILTER_CAT=""
for arg in "$@"; do
  case $arg in
    --fix) FIX_MODE=true ;;
    --verbose) VERBOSE=true ;;
    --category) FILTER_CAT="next" ;;
    *) if [ "$FILTER_CAT" = "next" ]; then FILTER_CAT="$arg"; fi ;;
  esac
done

# Counters
TOTAL=0
PASS=0
WARN=0
FAIL=0
CRITICAL=0

declare -a CRITICAL_ISSUES=()
declare -a FAIL_ISSUES=()
declare -a WARN_ISSUES=()

log_critical() { CRITICAL=$((CRITICAL+1)); CRITICAL_ISSUES+=("$1: $2"); }
log_fail() { FAIL=$((FAIL+1)); FAIL_ISSUES+=("$1: $2"); }
log_warn() { WARN=$((WARN+1)); WARN_ISSUES+=("$1: $2"); }

echo ""
echo "============================================================"
echo "  TEAMZ LAB TOOLS — QA TEST SUITE"
echo "============================================================"
echo ""

# Find all tool pages
if [ -n "$FILTER_CAT" ] && [ "$FILTER_CAT" != "next" ]; then
  PAGES=$(find "./$FILTER_CAT" -name "index.html" -not -path "./.git/*" | sort)
else
  PAGES=$(find . -name "index.html" -not -path "./.git/*" -not -path "./node_modules/*" | sort)
fi

PAGE_COUNT=$(echo "$PAGES" | wc -l | tr -d ' ')
echo "  Testing $PAGE_COUNT pages..."
echo ""

for page in $PAGES; do
  TOTAL=$((TOTAL+1))
  rel_path="${page#./}"
  issues_found=0

  content=$(cat "$page")

  # ─── 1. STRUCTURAL CHECKS ───

  # Has DOCTYPE
  if ! echo "$content" | head -1 | grep -qi "doctype"; then
    log_critical "$rel_path" "Missing <!DOCTYPE html>"
    issues_found=1
  fi

  # Has <html lang>
  if ! echo "$content" | grep -q 'lang="'; then
    log_fail "$rel_path" "Missing lang attribute on <html>"
    issues_found=1
  fi

  # Has viewport meta
  if ! echo "$content" | grep -q 'viewport'; then
    log_critical "$rel_path" "Missing viewport meta tag"
    issues_found=1
  fi

  # Has <title>
  if ! echo "$content" | grep -q '<title>'; then
    log_critical "$rel_path" "Missing <title> tag"
    issues_found=1
  fi

  # Title length check
  title=$(echo "$content" | grep -o '<title>[^<]*</title>' | sed 's/<[^>]*>//g' | head -1)
  title_len=${#title}
  if [ "$title_len" -gt 60 ] 2>/dev/null; then
    log_warn "$rel_path" "Title too long ($title_len chars): $title"
    issues_found=1
  fi
  if [ "$title_len" -lt 10 ] 2>/dev/null; then
    log_fail "$rel_path" "Title too short ($title_len chars): $title"
    issues_found=1
  fi

  # Has meta description
  if ! echo "$content" | grep -q 'name="description"'; then
    log_fail "$rel_path" "Missing meta description"
    issues_found=1
  fi

  # Meta description length
  desc=$(echo "$content" | grep -o 'name="description" content="[^"]*"' | sed 's/name="description" content="//;s/"$//' | head -1)
  desc_len=${#desc}
  if [ "$desc_len" -gt 155 ] 2>/dev/null; then
    log_warn "$rel_path" "Description too long ($desc_len chars)"
    issues_found=1
  fi

  # ─── 2. SEO CHECKS ───

  # Has canonical URL
  if ! echo "$content" | grep -q 'rel="canonical"'; then
    log_fail "$rel_path" "Missing canonical URL"
    issues_found=1
  fi

  # Has OG tags
  if ! echo "$content" | grep -q 'og:title'; then
    log_fail "$rel_path" "Missing og:title"
    issues_found=1
  fi
  if ! echo "$content" | grep -q 'og:description'; then
    log_warn "$rel_path" "Missing og:description"
    issues_found=1
  fi
  if ! echo "$content" | grep -q 'og:image'; then
    log_warn "$rel_path" "Missing og:image"
    issues_found=1
  fi

  # Has H1
  if ! echo "$content" | grep -q '<h1'; then
    log_critical "$rel_path" "Missing <h1> tag"
    issues_found=1
  fi

  # ─── 3. DESIGN SYSTEM CHECKS ───

  # Hardcoded hex colors (excluding canvas/SVG/schema)
  hex_matches=$(echo "$content" | grep -c '#[0-9a-fA-F]\{3,6\}' 2>/dev/null || echo "0")
  # Allow some — schema, SVG viewBox, etc. use hex. Flag if excessive.
  if [ "$hex_matches" -gt 20 ] 2>/dev/null; then
    log_warn "$rel_path" "Excessive hardcoded hex colors ($hex_matches occurrences)"
    issues_found=1
  fi

  # Neon accent used as text color (the recurring issue)
  accent_text=$(echo "$content" | grep -c '[^-]color: var(--accent)' 2>/dev/null || echo "0")
  if [ "$accent_text" -gt 0 ] 2>/dev/null; then
    log_fail "$rel_path" "Neon accent used as text color ($accent_text occurrences) — unreadable on light bg"
    issues_found=1
  fi

  # ─── 4. REQUIRED SECTIONS ───

  # Skip hub/index pages for tool-specific checks
  is_tool_page=false
  if echo "$rel_path" | grep -q '/[a-z-]*/[a-z-]*/index.html'; then
    is_tool_page=true
  fi

  if $is_tool_page; then
    # Has ad-slot
    if ! echo "$content" | grep -q 'ad-slot'; then
      log_warn "$rel_path" "Missing ad-slot div"
      issues_found=1
    fi

    # Has breadcrumbs div
    if ! echo "$content" | grep -q 'id="breadcrumbs"'; then
      log_fail "$rel_path" "Missing breadcrumbs container"
      issues_found=1
    fi

    # Has FAQs section
    if ! echo "$content" | grep -q 'id="tool-faqs"'; then
      log_warn "$rel_path" "Missing FAQs section"
      issues_found=1
    fi

    # Has related tools
    if ! echo "$content" | grep -q 'id="related-tools"'; then
      log_warn "$rel_path" "Missing related-tools section"
      issues_found=1
    fi

    # Has tool-calculator or tool-area
    if ! echo "$content" | grep -q 'tool-calculator\|tool-area\|quiz-container\|quiz-area'; then
      log_warn "$rel_path" "Missing tool calculator/area section"
      issues_found=1
    fi

    # Loads theme.js
    if ! echo "$content" | grep -q 'theme.js'; then
      log_fail "$rel_path" "Missing theme.js script"
      issues_found=1
    fi

    # Loads common.js
    if ! echo "$content" | grep -q 'common.js'; then
      log_fail "$rel_path" "Missing common.js script"
      issues_found=1
    fi

    # Loads branding CSS
    if ! echo "$content" | grep -q 'teamz-branding.css'; then
      log_fail "$rel_path" "Missing teamz-branding.css"
      issues_found=1
    fi

    # Loads tools CSS
    if ! echo "$content" | grep -q 'tools.css'; then
      log_fail "$rel_path" "Missing tools.css"
      issues_found=1
    fi

    # Has header
    if ! echo "$content" | grep -q 'id="site-header"'; then
      log_fail "$rel_path" "Missing site-header"
      issues_found=1
    fi

    # Has footer
    if ! echo "$content" | grep -q 'id="site-footer"'; then
      log_fail "$rel_path" "Missing site-footer"
      issues_found=1
    fi
  fi

  # ─── 5. JAVASCRIPT CHECKS ───

  # Unclosed script tags
  open_scripts=$(echo "$content" | grep -c '<script' 2>/dev/null || echo "0")
  close_scripts=$(echo "$content" | grep -c '</script>' 2>/dev/null || echo "0")
  if [ "$open_scripts" != "$close_scripts" ] 2>/dev/null; then
    log_critical "$rel_path" "Mismatched script tags (open: $open_scripts, close: $close_scripts)"
    issues_found=1
  fi

  # ─── 6. MOBILE CHECKS ───

  # Has responsive meta
  if ! echo "$content" | grep -q 'width=device-width'; then
    log_critical "$rel_path" "Missing responsive viewport meta"
    issues_found=1
  fi

  # ─── 7. ACCESSIBILITY ───

  # Images without alt (basic check)
  img_no_alt=$(echo "$content" | grep -c '<img [^>]*[^a]>' 2>/dev/null || echo "0")
  # This is a rough check — skip for now

  # ─── RESULT ───
  if [ "$issues_found" -eq 0 ]; then
    PASS=$((PASS+1))
    if $VERBOSE; then
      echo -e "  ${GREEN}✓${NC} $rel_path"
    fi
  else
    if $VERBOSE; then
      echo -e "  ${RED}✗${NC} $rel_path"
    fi
  fi

  # Progress indicator every 100 pages
  if [ $((TOTAL % 100)) -eq 0 ]; then
    echo -e "  ... tested $TOTAL / $PAGE_COUNT pages"
  fi
done

# ─── SUMMARY ───
echo ""
echo "============================================================"
echo "  QA TEST RESULTS"
echo "============================================================"
echo ""
echo -e "  Pages tested:   ${BOLD}$TOTAL${NC}"
echo -e "  ${GREEN}Passed:${NC}         $PASS"
echo -e "  ${YELLOW}Warnings:${NC}       $WARN"
echo -e "  ${RED}Failures:${NC}       $FAIL"
echo -e "  ${RED}Critical:${NC}       $CRITICAL"
echo ""

# Show critical issues
if [ ${#CRITICAL_ISSUES[@]} -gt 0 ]; then
  echo -e "  ${RED}${BOLD}CRITICAL ISSUES (must fix):${NC}"
  for issue in "${CRITICAL_ISSUES[@]}"; do
    echo -e "    ${RED}✗${NC} $issue"
  done
  echo ""
fi

# Show failures
if [ ${#FAIL_ISSUES[@]} -gt 0 ]; then
  echo -e "  ${RED}${BOLD}FAILURES:${NC}"
  for issue in "${FAIL_ISSUES[@]}"; do
    echo -e "    ${RED}•${NC} $issue"
  done
  echo ""
fi

# Show warnings (only in verbose mode)
if $VERBOSE && [ ${#WARN_ISSUES[@]} -gt 0 ]; then
  echo -e "  ${YELLOW}${BOLD}WARNINGS:${NC}"
  for issue in "${WARN_ISSUES[@]}"; do
    echo -e "    ${YELLOW}•${NC} $issue"
  done
  echo ""
fi

# Score
if [ "$TOTAL" -gt 0 ]; then
  PASS_RATE=$((PASS * 100 / TOTAL))
  echo -e "  Pass rate: ${BOLD}$PASS_RATE%${NC} ($PASS / $TOTAL)"
fi

echo ""

if [ "$CRITICAL" -gt 0 ]; then
  echo -e "  ${RED}STATUS: CRITICAL ISSUES FOUND${NC}"
  exit 1
elif [ "$FAIL" -gt 0 ]; then
  echo -e "  ${RED}STATUS: FAILURES FOUND${NC}"
  exit 1
elif [ "$WARN" -gt 0 ]; then
  echo -e "  ${YELLOW}STATUS: WARNINGS (non-blocking)${NC}"
  exit 0
else
  echo -e "  ${GREEN}STATUS: ALL TESTS PASSED${NC}"
  exit 0
fi
