#!/bin/bash
# ============================================
# Teamz Lab Tools — Unified QA + UX Checker
# Covers: SEO structure, runtime safety, UX usability, design system
# Run: ./build-qa-check.sh [--hub ai] [--verbose]
# ============================================

SCRIPTS="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")" && pwd)"
source "$SCRIPTS/lib/config.sh"
teamz_load_config "$0"
BASE="$TEAMZ_HOST_SITE_ROOT"
cd "$BASE"

if [[ "${TEAMZ_PROJECT_TYPE:-website}" == "app" ]]; then
  echo "INFO: build-qa-check.sh is website-focused and disabled for TEAMZ_PROJECT_TYPE=app."
  exit 2
fi

RED='\033[0;31m'
YEL='\033[1;33m'
GRN='\033[0;32m'
CYN='\033[0;36m'
NC='\033[0m'

HUB_FILTER=""
VERBOSE=false
FIX_MODE=false
CHANGED_MODE=false
for arg in "$@"; do
  case "$arg" in
    --verbose) VERBOSE=true ;;
    --fix) FIX_MODE=true ;;
    --changed) CHANGED_MODE=true ;;
    --hub) HUB_FILTER="next" ;;
    *)
      if [ "$HUB_FILTER" = "next" ]; then HUB_FILTER="$arg"; fi
      ;;
  esac
done

echo "============================================"
echo "  Teamz Lab Tools — QA + UX Checker"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo "============================================"
echo ""

# Build tool list (only actual tool pages, not hubs or redirects)
TMPFILE=$(mktemp)
if [ "$CHANGED_MODE" = true ]; then
  # Scope to tool pages actually being pushed, not the whole site. Added
  # 2026-08-08 after the full sweep (~15 min over 6,847 pages) got SIGKILLed
  # mid-push twice in a row when a caller retried without realising the prior
  # scan was still running. This mode answers "is what I'm about to ship
  # okay", not "is the whole site okay" — that's still ./build-qa-check.sh
  # with no flags, run explicitly, never from a push hook.
  RANGE_BASE=""
  if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
    RANGE_BASE='@{u}'
  elif git rev-parse HEAD~1 >/dev/null 2>&1; then
    RANGE_BASE='HEAD~1'
  fi
  if [ -n "$RANGE_BASE" ]; then
    git diff --name-only --diff-filter=d "${RANGE_BASE}...HEAD" -- '*/index.html' 2>/dev/null \
      | grep -v -E '^[^/]+/index\.html$' \
      | grep -vE '^(shared|branding|docs|node_modules|scripts|about|contact|privacy|terms|\.claude|teamzlab-website|flutter_[^/]*|ai_[^/]*|hazira[^/]*|chopstick[^/]*|notetube[^/]*|jiwer[^/]*|no-trace[^/]*|room_[^/]*|toss_[^/]*|top_3[^/]*|youtube_[^/]*|zoyiai|apps[^/]*)/' \
      | while read -r f; do [ -f "$f" ] && echo "$f"; done \
      | sort -u > "$TMPFILE"
  fi
elif [ -n "$HUB_FILTER" ] && [ "$HUB_FILTER" != "next" ]; then
  find "$HUB_FILTER" -mindepth 2 -maxdepth 2 -name "index.html" 2>/dev/null | sort > "$TMPFILE"
else
  find . -name "index.html" -not -path "./index.html" \
    -not -path "./shared/*" -not -path "./branding/*" -not -path "./docs/*" \
    -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./scripts/*" \
    -not -path "./about/*" -not -path "./contact/*" -not -path "./privacy/*" -not -path "./terms/*" \
    -not -path "./.claude*" -not -path "./teamzlab-website/*" \
    -not -path "./flutter_*/*" -not -path "./ai_*/*" -not -path "./hazira*/*" \
    -not -path "./chopstick*/*" -not -path "./notetube*/*" -not -path "./jiwer*/*" \
    -not -path "./no-trace*/*" -not -path "./room_*/*" -not -path "./toss_*/*" \
    -not -path "./top_3*/*" -not -path "./youtube_*/*" -not -path "./zoyiai/*" \
    -not -path "./apps*/*" \
    | grep -v -E "^./[^/]+/index.html$" \
    | sort > "$TMPFILE"
fi

TOOL_COUNT=$(wc -l < "$TMPFILE" | tr -d ' ')
if [ "$CHANGED_MODE" = true ] && [ "$TOOL_COUNT" -eq 0 ]; then
  echo "  No tool pages changed vs upstream — nothing to check."
  echo ""
  rm -f "$TMPFILE"
  exit 0
fi
echo "  Scanning $TOOL_COUNT tool pages..."
echo ""

# --- Counters ---
TOTAL=0
# SEO
NO_JS=0; LOW_CONTENT=0; NO_FAQS=0; NO_RELATED=0; NO_SCHEMA=0; NO_COPY_HANDLER=0; BAD_FAQ_ID=0; BAD_RELATED_ID=0; BAD_BREADCRUMB_ID=0; NO_OG_IMAGE=0; NO_HREFLANG=0
# Runtime
ALERT_COUNT=0; AI_NO_ENGINE=0; NULL_BG=0; DISPLAY_EMPTY=0
# UX
NO_HERO=0; NO_DESC=0; NO_LABELS=0; NO_IDS=0; NO_MOBILE=0; NO_SCROLL=0
WHITE_ACCENT=0; NO_LOADING=0

# Issue lists for verbose
ISSUES_SEO=""
ISSUES_RUNTIME=""
ISSUES_UX=""

while IFS= read -r f; do
  [ -z "$f" ] && continue
  TOTAL=$((TOTAL + 1))
  CONTENT=$(cat "$f" 2>/dev/null)
  SLUG=$(echo "$f" | sed "s|^\./||" | sed "s|/index\.html$||")

  # Redirect pages — check basic SEO tags + best practices, then skip full checks
  is_redirect=$(echo "$CONTENT" | grep -c 'window\.location\.replace' 2>/dev/null || true)
  has_meta_refresh=$(echo "$CONTENT" | grep -c 'http-equiv="refresh"' 2>/dev/null || true)
  if [ "$is_redirect" -gt 0 ] || [ "$has_meta_refresh" -gt 0 ]; then
    # Even redirect pages need these for Bing Site Scan
    has_meta_desc=$(echo "$CONTENT" | grep -c '<meta name="description"' 2>/dev/null || true)
    has_title=$(echo "$CONTENT" | grep -c '<title>' 2>/dev/null || true)
    has_canonical=$(echo "$CONTENT" | grep -c 'rel="canonical"' 2>/dev/null || true)
    has_noindex=$(echo "$CONTENT" | grep -c 'noindex' 2>/dev/null || true)
    has_viewport=$(echo "$CONTENT" | grep -c 'name="viewport"' 2>/dev/null || true)
    has_h1=$(echo "$CONTENT" | grep -c '<h1' 2>/dev/null || true)
    has_noscript=$(echo "$CONTENT" | grep -c '<noscript>' 2>/dev/null || true)
    redir_issues=""
    [ "$has_meta_desc" -eq 0 ] && redir_issues="${redir_issues} meta-desc"
    [ "$has_title" -eq 0 ] && redir_issues="${redir_issues} title"
    [ "$has_canonical" -eq 0 ] && redir_issues="${redir_issues} canonical"
    [ "$has_noindex" -eq 0 ] && redir_issues="${redir_issues} noindex"
    [ "$has_viewport" -eq 0 ] && redir_issues="${redir_issues} viewport"
    [ "$has_h1" -eq 0 ] && redir_issues="${redir_issues} h1"
    # Meta refresh should be inside <noscript>, not bare in <head>
    if [ "$has_meta_refresh" -gt 0 ] && [ "$has_noscript" -eq 0 ]; then
      redir_issues="${redir_issues} meta-refresh-not-in-noscript"
    fi
    # Check redirect target exists
    redir_target=$(echo "$CONTENT" | grep -o 'url=/[^"]*' 2>/dev/null | head -1 | sed 's|url=||')
    if [ -n "$redir_target" ]; then
      target_file="${BASE}${redir_target}index.html"
      [ ! -f "$target_file" ] && redir_issues="${redir_issues} broken-target(${redir_target})"
    fi
    if [ -n "$redir_issues" ]; then
      ISSUES_SEO="$ISSUES_SEO
  ${RED}REDIRECT MISSING:${NC} $SLUG —${redir_issues}"
    fi
    continue
  fi

  # ===== SEO STRUCTURE =====

  # No JS logic
  has_js=$(echo "$CONTENT" | grep -c 'addEventListener\|function ' 2>/dev/null || true)
  if [ "$has_js" -eq 0 ]; then
    NO_JS=$((NO_JS + 1))
    ISSUES_SEO="$ISSUES_SEO
  ${RED}NO JS:${NC} $SLUG"
  fi

  # Low content
  # Accept either tool-content or tool-content-section and avoid penalizing
  # CJK-heavy content where whitespace word counts are misleading.
  content_metrics=$(printf '%s' "$CONTENT" | python3 -c '
import re, sys
content = sys.stdin.read()
match = re.search(r"<section class=\"(?:tool-content|tool-content-section)\">([\s\S]*?)</section>", content, re.I)
text = re.sub(r"<[^>]*>", " ", match.group(1)) if match else ""
words = len(text.split())
cjk = len(re.findall(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))
print(f"{words}:{cjk}")
')
  words=${content_metrics%%:*}
  cjk_chars=${content_metrics##*:}
  if [ "$words" -lt 150 ] 2>/dev/null && [ "$cjk_chars" -lt 400 ] 2>/dev/null; then
    LOW_CONTENT=$((LOW_CONTENT + 1))
    ISSUES_SEO="$ISSUES_SEO
  ${YEL}LOW CONTENT (${words}w):${NC} $SLUG"
  fi

  # Missing FAQs
  has_faq=$(echo "$CONTENT" | grep -c 'renderFAQs\|injectFAQSchema\|FAQPage' 2>/dev/null || true)
  if [ "$has_faq" -eq 0 ]; then NO_FAQS=$((NO_FAQS + 1)); fi

  # Wrong FAQ container ID (renderFAQs expects id="tool-faqs", not "faqs-section" etc.)
  calls_renderFAQs=$(echo "$CONTENT" | grep -c 'renderFAQs' 2>/dev/null || true)
  has_tool_faqs_id=$(echo "$CONTENT" | grep -c 'id="tool-faqs"' 2>/dev/null || true)
  if [ "$calls_renderFAQs" -gt 0 ] && [ "$has_tool_faqs_id" -eq 0 ]; then
    BAD_FAQ_ID=$((BAD_FAQ_ID + 1))
    if [ "$FIX_MODE" = true ]; then
      # Auto-fix: replace any wrong FAQ ID with the correct one
      wrong_faq_id=$(grep -oE 'id="[^"]*faq[^"]*"' "$f" 2>/dev/null | head -1)
      if [ -n "$wrong_faq_id" ]; then
        sed -i '' "s|${wrong_faq_id}|id=\"tool-faqs\"|" "$f"
        ISSUES_SEO="$ISSUES_SEO
  ${GRN}FIXED FAQ ID:${NC} $SLUG — ${wrong_faq_id} → id=\"tool-faqs\""
      else
        # No FAQ div at all — insert one before </main> or before footer
        sed -i '' 's|</main>|    <div id="tool-faqs"></div>\n  </main>|' "$f"
        ISSUES_SEO="$ISSUES_SEO
  ${GRN}ADDED FAQ DIV:${NC} $SLUG — inserted <div id=\"tool-faqs\"></div>"
      fi
    else
      ISSUES_SEO="$ISSUES_SEO
  ${RED}WRONG FAQ ID:${NC} $SLUG — calls renderFAQs() but missing id=\"tool-faqs\" (run --fix to auto-repair)"
    fi
  fi

  # Missing related tools
  has_related=$(echo "$CONTENT" | grep -c 'renderRelatedTools\|related-tools' 2>/dev/null || true)
  if [ "$has_related" -eq 0 ]; then NO_RELATED=$((NO_RELATED + 1)); fi

  # Wrong related-tools container ID (renderRelatedTools expects id="related-tools")
  calls_renderRelated=$(echo "$CONTENT" | grep -c 'renderRelatedTools' 2>/dev/null || true)
  has_related_id=$(echo "$CONTENT" | grep -c 'id="related-tools"' 2>/dev/null || true)
  if [ "$calls_renderRelated" -gt 0 ] && [ "$has_related_id" -eq 0 ]; then
    BAD_RELATED_ID=$((BAD_RELATED_ID + 1))
    if [ "$FIX_MODE" = true ]; then
      wrong_rel_id=$(grep -oE 'id="[a-zA-Z0-9_-]*related[a-zA-Z0-9_-]*"' "$f" 2>/dev/null | head -1)
      if [ -n "$wrong_rel_id" ]; then
        sed -i '' "s|${wrong_rel_id}|id=\"related-tools\"|" "$f"
        ISSUES_SEO="$ISSUES_SEO
  ${GRN}FIXED RELATED ID:${NC} $SLUG — ${wrong_rel_id} → id=\"related-tools\""
      else
        sed -i '' 's|</main>|    <div id="related-tools"></div>\n  </main>|' "$f"
        ISSUES_SEO="$ISSUES_SEO
  ${GRN}ADDED RELATED DIV:${NC} $SLUG — inserted <div id=\"related-tools\"></div>"
      fi
    else
      ISSUES_SEO="$ISSUES_SEO
  ${RED}WRONG RELATED ID:${NC} $SLUG — calls renderRelatedTools() but missing id=\"related-tools\" (run --fix to auto-repair)"
    fi
  fi

  # Wrong breadcrumbs container ID (renderBreadcrumbs expects id="breadcrumbs")
  calls_renderBreadcrumbs=$(echo "$CONTENT" | grep -c 'renderBreadcrumbs' 2>/dev/null || true)
  has_breadcrumbs_id=$(echo "$CONTENT" | grep -c 'id="breadcrumbs"' 2>/dev/null || true)
  if [ "$calls_renderBreadcrumbs" -gt 0 ] && [ "$has_breadcrumbs_id" -eq 0 ]; then
    BAD_BREADCRUMB_ID=$((BAD_BREADCRUMB_ID + 1))
    if [ "$FIX_MODE" = true ]; then
      wrong_bc_id=$(grep -oE 'id="[a-zA-Z0-9_-]*bread[a-zA-Z0-9_-]*"' "$f" 2>/dev/null | head -1)
      if [ -n "$wrong_bc_id" ]; then
        sed -i '' "s|${wrong_bc_id}|id=\"breadcrumbs\"|" "$f"
        ISSUES_SEO="$ISSUES_SEO
  ${GRN}FIXED BREADCRUMB ID:${NC} $SLUG — ${wrong_bc_id} → id=\"breadcrumbs\""
      fi
    else
      ISSUES_SEO="$ISSUES_SEO
  ${RED}WRONG BREADCRUMB ID:${NC} $SLUG — calls renderBreadcrumbs() but missing id=\"breadcrumbs\" (run --fix to auto-repair)"
    fi
  fi

  # Missing WebApp schema
  has_webapp=$(echo "$CONTENT" | grep -c 'injectWebAppSchema\|WebApplication' 2>/dev/null || true)
  if [ "$has_webapp" -eq 0 ]; then NO_SCHEMA=$((NO_SCHEMA + 1)); fi

  # Missing og:image
  has_og_image=$(echo "$CONTENT" | grep -c 'og:image' 2>/dev/null || true)
  if [ "$has_og_image" -eq 0 ]; then
    NO_OG_IMAGE=$((NO_OG_IMAGE + 1))
    ISSUES_SEO="$ISSUES_SEO
  ${RED}NO OG:IMAGE:${NC} $SLUG"
  fi

  # Non-English tools missing hreflang
  page_lang=$(echo "$CONTENT" | sed -n 's/.*<html lang="\([^"]*\)".*/\1/p' | head -1)
  if [ -n "$page_lang" ] && [ "$page_lang" != "en" ]; then
    has_hreflang=$(echo "$CONTENT" | grep -c 'hreflang' 2>/dev/null || true)
    if [ "$has_hreflang" -eq 0 ]; then
      NO_HREFLANG=$((NO_HREFLANG + 1))
      ISSUES_SEO="$ISSUES_SEO
  ${RED}NO HREFLANG:${NC} $SLUG (lang=$page_lang)"
    fi
  fi

  # Broken Copy Image
  has_copy_img=$(echo "$CONTENT" | grep -ci 'Copy Image' 2>/dev/null || true)
  has_clipboard_item=$(echo "$CONTENT" | grep -c 'ClipboardItem' 2>/dev/null || true)
  if [ "$has_copy_img" -gt 0 ] && [ "$has_clipboard_item" -eq 0 ]; then
    NO_COPY_HANDLER=$((NO_COPY_HANDLER + 1))
    ISSUES_SEO="$ISSUES_SEO
  ${RED}BROKEN COPY IMAGE:${NC} $SLUG"
  fi

  # ===== RUNTIME SAFETY =====

  # alert() calls (overridden centrally, but still warn for cleanup)
  has_alert=$(echo "$CONTENT" | grep -c 'alert(' 2>/dev/null || true)
  if [ "$has_alert" -gt 0 ]; then ALERT_COUNT=$((ALERT_COUNT + 1)); fi

  # AI tool without ai-engine.js
  has_chrome_ai=$(echo "$CONTENT" | grep -c 'self\.ai\|chromeAI\|Rewriter' 2>/dev/null || true)
  has_ai_engine=$(echo "$CONTENT" | grep -c 'ai-engine\.js' 2>/dev/null || true)
  if [ "$has_chrome_ai" -gt 0 ] && [ "$has_ai_engine" -eq 0 ]; then
    AI_NO_ENGINE=$((AI_NO_ENGINE + 1))
    ISSUES_RUNTIME="$ISSUES_RUNTIME
  ${RED}AI NO ENGINE:${NC} $SLUG"
  fi

  # html2canvas null bg
  has_null_bg=$(echo "$CONTENT" | grep -c 'backgroundColor: null' 2>/dev/null || true)
  is_fake=$(echo "$SLUG" | grep -c 'fake-\|tweet' 2>/dev/null || true)
  if [ "$has_null_bg" -gt 0 ] && [ "$is_fake" -eq 0 ]; then
    NULL_BG=$((NULL_BG + 1))
    ISSUES_RUNTIME="$ISSUES_RUNTIME
  ${YEL}NULL BG:${NC} $SLUG"
  fi

  # style.display='' on elements hidden by stylesheet rules can be a real bug.
  # Do not flag pages that only hide elements inline, because clearing the inline
  # style is a valid way to reveal them.
  has_display_empty=$(echo "$CONTENT" | grep -c "style\.display\s*=\s*['\"]['\"]" 2>/dev/null || true)
  has_stylesheet_display_none=$(printf '%s' "$CONTENT" | python3 -c '
import re, sys
content = sys.stdin.read()
styles = "\n".join(re.findall(r"<style[^>]*>([\s\S]*?)</style>", content, re.I))
print(1 if re.search(r"display\s*:\s*none", styles) else 0)
')
  has_inline_display_none=$(echo "$CONTENT" | grep -c "style=['\"][^>]*display:none" 2>/dev/null || true)
  if [ "$has_display_empty" -gt 0 ] && [ "$has_stylesheet_display_none" -gt 0 ] && [ "$has_inline_display_none" -eq 0 ]; then
    DISPLAY_EMPTY=$((DISPLAY_EMPTY + 1))
    ISSUES_RUNTIME="$ISSUES_RUNTIME
  ${RED}DISPLAY BUG:${NC} $SLUG — style.display='' with CSS display:none (use block/flex/grid)"
  fi

  # ===== UX USABILITY =====

  # Missing hero / intro section
  has_hero=$(echo "$CONTENT" | grep -c 'tool-hero\|class="hero"\|tool-intro' 2>/dev/null || true)
  if [ "$has_hero" -eq 0 ]; then
    NO_HERO=$((NO_HERO + 1))
    ISSUES_UX="$ISSUES_UX
  ${YEL}NO HERO:${NC} $SLUG"
  fi

  # Missing tool-description
  has_desc=$(echo "$CONTENT" | grep -c 'tool-description' 2>/dev/null || true)
  if [ "$has_desc" -eq 0 ]; then NO_DESC=$((NO_DESC + 1)); fi

  # Inputs without labels
  input_count=$(echo "$CONTENT" | grep -c '<input\|<textarea\|<select' 2>/dev/null || true)
  label_count=$(echo "$CONTENT" | grep -c '<label\|tool-label\|aria-label' 2>/dev/null || true)
  if [ "$input_count" -gt 0 ] && [ "$label_count" -eq 0 ]; then
    NO_LABELS=$((NO_LABELS + 1))
    ISSUES_UX="$ISSUES_UX
  ${YEL}NO LABELS:${NC} $SLUG ($input_count inputs, 0 labels)"
  fi

  # No mobile CSS (skip tool-engine tools — handled centrally)
  has_mobile=$(echo "$CONTENT" | grep -c 'max-width.*600\|max-width.*480\|max-width.*768' 2>/dev/null || true)
  uses_engine=$(echo "$CONTENT" | grep -c 'tool-engine\.js\|utility-engine\.js\|TOOL_CONFIG' 2>/dev/null || true)
  if [ "$has_mobile" -eq 0 ] && [ "$uses_engine" -eq 0 ]; then
    NO_MOBILE=$((NO_MOBILE + 1))
  fi

  # White text on accent
  has_white_accent=$(echo "$CONTENT" | grep -c 'color:\s*#fff.*accent\|color:\s*white.*accent\|accent.*color:\s*#fff\|accent.*color:\s*white' 2>/dev/null || true)
  if [ "$has_white_accent" -gt 0 ]; then
    WHITE_ACCENT=$((WHITE_ACCENT + 1))
    ISSUES_UX="$ISSUES_UX
  ${RED}WHITE ON ACCENT:${NC} $SLUG"
  fi

  # Async operations without loading indicator
  has_async=$(echo "$CONTENT" | grep -c 'async function\|await ' 2>/dev/null || true)
  has_loading=$(echo "$CONTENT" | grep -c 'Loading\|loading\|Generating\|Processing\|Analyzing\|\.disabled' 2>/dev/null || true)
  if [ "$has_async" -gt 0 ] && [ "$has_loading" -eq 0 ]; then
    NO_LOADING=$((NO_LOADING + 1))
  fi

done < "$TMPFILE"

# --- Print Results ---
echo "============================================"
echo "  QA + UX RESULTS"
echo "============================================"
echo ""

echo "  SEO STRUCTURE:"
printf "    No JS logic:          %s%d%s\n" "$RED" "$NO_JS" "$NC"
printf "    Low content (<150w):  %s%d%s\n" "$YEL" "$LOW_CONTENT" "$NC"
printf "    Missing FAQs:         %s%d%s\n" "$YEL" "$NO_FAQS" "$NC"
printf "    Missing related:      %s%d%s\n" "$YEL" "$NO_RELATED" "$NC"
printf "    Missing WebApp:       %s%d%s\n" "$YEL" "$NO_SCHEMA" "$NC"
printf "    Wrong FAQ container:  %s%d%s\n" "$RED" "$BAD_FAQ_ID" "$NC"
printf "    Wrong related ID:     %s%d%s\n" "$RED" "$BAD_RELATED_ID" "$NC"
printf "    Wrong breadcrumb ID:  %s%d%s\n" "$RED" "$BAD_BREADCRUMB_ID" "$NC"
printf "    Missing og:image:     %s%d%s\n" "$RED" "$NO_OG_IMAGE" "$NC"
printf "    Missing hreflang:     %s%d%s\n" "$RED" "$NO_HREFLANG" "$NC"
printf "    Broken Copy Image:    %s%d%s\n" "$RED" "$NO_COPY_HANDLER" "$NC"
echo ""

echo "  RUNTIME SAFETY:"
printf "    alert() calls:        %s%d%s (overridden centrally)\n" "$YEL" "$ALERT_COUNT" "$NC"
printf "    AI no ai-engine.js:   %s%d%s\n" "$RED" "$AI_NO_ENGINE" "$NC"
printf "    html2canvas null bg:  %s%d%s\n" "$YEL" "$NULL_BG" "$NC"
printf "    display='' bug:       %s%d%s\n" "$RED" "$DISPLAY_EMPTY" "$NC"
echo ""

echo "  UX USABILITY:"
printf "    No tool-hero:         %s%d%s\n" "$YEL" "$NO_HERO" "$NC"
printf "    No tool-description:  %s%d%s\n" "$YEL" "$NO_DESC" "$NC"
printf "    Inputs no labels:     %s%d%s\n" "$YEL" "$NO_LABELS" "$NC"
printf "    No mobile CSS:        %s%d%s (excl. engine tools + central CSS)\n" "$YEL" "$NO_MOBILE" "$NC"
printf "    White on accent:      %s%d%s\n" "$RED" "$WHITE_ACCENT" "$NC"
printf "    No loading state:     %s%d%s\n" "$YEL" "$NO_LOADING" "$NC"
echo ""

TOTAL_ISSUES=$((NO_JS + LOW_CONTENT + NO_FAQS + NO_RELATED + NO_SCHEMA + NO_COPY_HANDLER + BAD_FAQ_ID + BAD_RELATED_ID + BAD_BREADCRUMB_ID + NO_OG_IMAGE + NO_HREFLANG + AI_NO_ENGINE + NULL_BG + DISPLAY_EMPTY + NO_HERO + NO_LABELS + WHITE_ACCENT))
printf "  Total tools:  %d\n" "$TOTAL"
printf "  Key issues:   %s%d%s\n" "$RED" "$TOTAL_ISSUES" "$NC"
echo ""

# Structural/safety defects vs content backlog. Only the former can block a
# push in --changed mode: a broken renderer or a11y violation is very likely
# something THIS push introduced, while missing FAQs/hreflang/og:image on an
# old page is legacy backlog (hundreds of pages, unrelated to most edits) and
# would false-positive-block unrelated fixes if treated the same way.
HARD_BLOCKERS=$((NO_JS + BAD_FAQ_ID + BAD_RELATED_ID + BAD_BREADCRUMB_ID + DISPLAY_EMPTY + WHITE_ACCENT + AI_NO_ENGINE + NO_COPY_HANDLER))

# Show details for verbose or small hub
if [ "$VERBOSE" = true ]; then
  if [ -n "$ISSUES_SEO" ]; then echo "  --- SEO Issues ---"; echo "$ISSUES_SEO"; echo ""; fi
  if [ -n "$ISSUES_RUNTIME" ]; then echo "  --- Runtime Issues ---"; echo "$ISSUES_RUNTIME"; echo ""; fi
  if [ -n "$ISSUES_UX" ]; then echo "  --- UX Issues ---"; echo "$ISSUES_UX"; echo ""; fi
fi

echo "============================================"
echo "  CENTRAL PROTECTIONS IN PLACE:"
echo "    common.js: alert()→showToast, safeClipboard, safeHtml2Canvas, autoScroll, autoIds"
echo "    tools.css: mobile responsive base rules for all tools"
echo "    pre-commit: 25+ automated checks on every commit"
echo "============================================"
echo ""
echo "  Run: ./build-qa-check.sh               (all tools)"
echo "  Run: ./build-qa-check.sh --hub ai       (one hub)"
echo "  Run: ./build-qa-check.sh --verbose      (show all issues)"
echo "  Run: ./build-qa-check.sh --fix          (auto-fix FAQ IDs)"
echo "  Run: ./build-qa-check.sh --fix --verbose (fix + show details)"
echo "============================================"

rm -f "$TMPFILE"

if [ "$CHANGED_MODE" = true ] && [ "$HARD_BLOCKERS" -gt 0 ]; then
  echo ""
  printf "  %s✗ %d structural/safety defect(s) in files this push touches — see counts above%s\n" "$RED" "$HARD_BLOCKERS" "$NC"
  exit 1
fi

exit 0
