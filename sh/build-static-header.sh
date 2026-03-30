#!/bin/bash
# ============================================================
# Teamz Lab Tools — Inject Static Header HTML
# Prevents CLS by pre-rendering header content in HTML
# (common.js then enhances it with event listeners, not replaces)
#
# EDIT THE HEADER HERE — re-run to update all pages:
#   ./build-static-header.sh           # Inject into all pages
#   ./build-static-header.sh --check   # Show pages missing static header
#
# The header HTML is defined ONCE below. When you change it,
# re-run this script and all pages get updated.
# ============================================================

_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
_SCRIPT_DIR="$(cd "$(dirname "$_SCRIPT")" && pwd)"
# shellcheck disable=SC1091
source "$_SCRIPT_DIR/lib/config.sh"
teamz_load_config "$_SCRIPT"
cd "$TEAMZ_HOST_SITE_ROOT"

# ===== EDIT HEADER HTML HERE =====
# This is the SINGLE SOURCE OF TRUTH for the static header.
# Keep it identical to what renderHeader() in common.js produces.
# common.js will skip innerHTML replacement if it detects this content.
read -r -d '' HEADER_HTML << 'HEADEREOF'
<a href="/" class="header-logo teamz-logo" aria-label="Teamz Lab Tools Home"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg><span>Teamz Lab Tools</span></a><nav class="header-nav" aria-label="Main navigation"><a href="/" class="nav-link">Home</a><a href="/about/" class="nav-link">About</a><a href="/contact/" class="nav-link">Contact</a><div class="lang-selector notranslate" translate="no"><button class="lang-btn notranslate" id="lang-toggle" type="button" aria-label="Change language" title="Change language" translate="no"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg> <span id="current-lang" class="notranslate" translate="no">EN</span></button><div class="lang-dropdown notranslate" id="lang-dropdown" translate="no"></div></div><div class="fav-header-wrap"><button id="fav-header-btn" class="header-icon-btn nav-link--icon" aria-label="Favorites" title="Your Favourites"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg><span id="fav-badge" class="fav-badge" style="display:none;">0</span></button><div id="fav-dropdown" class="fav-dropdown" style="display:none;"></div></div><button id="theme-toggle" class="header-icon-btn nav-link--icon" aria-label="Toggle theme" title="Toggle dark/light mode"><svg id="theme-icon-dark" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg><svg id="theme-icon-light" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg></button></nav>
HEADEREOF

if [ "$1" = "--check" ]; then
  echo "Pages with empty header:"
  count=0
  total=0
  while IFS= read -r f; do
    total=$((total + 1))
    if grep -q '<header id="site-header" class="site-header"></header>' "$f" 2>/dev/null; then
      count=$((count + 1))
      echo "  $f"
    fi
  done < <(find . -name "index.html" -not -path "./branding/*" -not -path "./.git/*" -not -path "./node_modules/*")
  echo ""
  echo "  $count of $total pages have empty headers"
  exit 0
fi

echo ""
echo "============================================================"
echo "  STATIC HEADER — Injecting pre-rendered header HTML"
echo "============================================================"

# Escape the header HTML for sed (handle & and / characters)
ESCAPED_HEADER=$(echo "$HEADER_HTML" | sed 's/[&/\]/\\&/g' | tr -d '\n')

count=0
total=0

# Find all index.html files and inject header content
while IFS= read -r f; do
  total=$((total + 1))
  # Only replace if header is empty (no content between tags)
  if grep -q '<header id="site-header" class="site-header"></header>' "$f" 2>/dev/null; then
    sed -i '' "s|<header id=\"site-header\" class=\"site-header\"></header>|<header id=\"site-header\" class=\"site-header\">${ESCAPED_HEADER}</header>|" "$f"
    count=$((count + 1))
  fi
done < <(find . -name "index.html" -not -path "./branding/*" -not -path "./.git/*" -not -path "./node_modules/*")

# Also handle 404.html
if grep -q '<header id="site-header" class="site-header"></header>' 404.html 2>/dev/null; then
  sed -i '' "s|<header id=\"site-header\" class=\"site-header\"></header>|<header id=\"site-header\" class=\"site-header\">${ESCAPED_HEADER}</header>|" 404.html
  count=$((count + 1))
fi

echo "  Injected static header into $count of $total pages"
echo "============================================================"
