#!/bin/bash
# MASTER BUILD SCRIPT — Run after ANY changes
# Usage: ./build.sh
# This prevents all common mistakes by auto-fixing everything

_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
SCRIPTS="$(cd "$(dirname "$_SCRIPT")" && pwd)"
PY="$(cd "$SCRIPTS/../py" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPTS/lib/config.sh"
teamz_load_config "$_SCRIPT"
BASE="$TEAMZ_HOST_SITE_ROOT"
ERRORS=0

echo "============================================="
echo "  Teamz Lab Tools — Build & Validate"
echo "============================================="
echo ""

# 1. Rebuild search index
echo "[1/7] Rebuilding search index..."
bash "$SCRIPTS/build-search-index.sh"

# 2. Rebuild sitemap
echo ""
echo "[2/7] Rebuilding sitemap..."
bash "$SCRIPTS/build-sitemap.sh"

# 3. Update homepage card counts
echo ""
echo "[3/7] Checking homepage card counts..."
for hub in work diagnostic freelance creator student housing career software dev text image compliance eu ramadan tools ai apple auto evergreen health kids music sports weather; do
  actual=$(find "$BASE/$hub" -name "index.html" -not -path "$BASE/$hub/index.html" 2>/dev/null | wc -l | tr -d ' ')
  shown=$(grep "href=\"/$hub/\"" "$BASE/index.html" | grep -o '<p>[0-9]* ' | grep -o '[0-9]*')
  if [ -n "$shown" ] && [ "$shown" != "$actual" ]; then
    echo "  MISMATCH: /$hub/ shows $shown but has $actual tools"
    ERRORS=$((ERRORS + 1))
  fi
done
if [ $ERRORS -eq 0 ]; then
  echo "  All card counts correct!"
fi

# 3b. Validate hub page card structure (must use <div class="card"> wrapper)
echo ""
echo "[3b] Checking hub page card structure..."
hub_card_issues=0
for hub_file in "$BASE"/*/index.html; do
  hub_name=$(basename "$(dirname "$hub_file")")
  # Skip non-hub directories
  case "$hub_name" in about|contact|privacy|terms|docs|shared|branding|og-images|icons|__pycache__) continue ;; esac
  # Only check files that have tools-grid (hub pages)
  if grep -q 'tools-grid' "$hub_file" 2>/dev/null; then
    # Check if any tool-card links are missing <div class="card"> wrapper
    if grep -q 'class="tool-card"' "$hub_file" && ! grep -q '<div class="card">' "$hub_file" 2>/dev/null; then
      echo "  BROKEN: /$hub_name/index.html — tool-card links missing <div class=\"card\"> wrapper"
      hub_card_issues=$((hub_card_issues + 1))
      ERRORS=$((ERRORS + 1))
    fi
  fi
done
if [ $hub_card_issues -eq 0 ]; then
  echo "  All hub pages have correct card structure!"
fi

# 4. Check for hardcoded colors in new/modified files
echo ""
echo "[4/7] Checking for hardcoded colors..."
changed_files=$(git diff --name-only HEAD~1 2>/dev/null | grep '\.html$')
if [ -n "$changed_files" ]; then
  color_violations=0
  for f in $changed_files; do
    if [ -f "$BASE/$f" ]; then
      # Check for color: #fff with accent background (the neon text issue)
      if grep -q 'background.*var(--accent).*color.*#fff\|color.*#fff.*background.*var(--accent)' "$BASE/$f" 2>/dev/null; then
        echo "  WARNING: $f has white text on accent background"
        color_violations=$((color_violations + 1))
      fi
    fi
  done
  if [ $color_violations -eq 0 ]; then
    echo "  No color violations found!"
  fi
else
  echo "  No changed HTML files to check"
fi

# 5. Check for unlinked tools (tools with no hub reference)
echo ""
echo "[5/7] Checking for unlinked tools..."
unlinked=0
for tooldir in "$BASE"/tools/*/; do
  toolname=$(basename "$tooldir")
  if [ -f "$tooldir/index.html" ]; then
    # Check if any hub page links to this tool
    if ! grep -rq "$toolname" "$BASE/tools/index.html" "$BASE/ai/index.html" "$BASE/index.html" 2>/dev/null; then
      echo "  UNLINKED: /tools/$toolname/ — not referenced in any hub"
      unlinked=$((unlinked + 1))
    fi
  fi
done
if [ $unlinked -eq 0 ]; then
  echo "  All tools are linked!"
fi

# 6. Check for duplicate tools (same slug name in different hubs)
echo ""
echo "[6/7] Checking for duplicate tools..."
dupes=$(find "$BASE" -name "index.html" -path "*/*/index.html" \
  -not -path "*/about/*" -not -path "*/contact/*" -not -path "*/privacy/*" \
  -not -path "*/terms/*" -not -path "*/docs/*" -not -path "*/node_modules/*" \
  -not -path "*/.git/*" | sed "s|$BASE/||;s|/index.html||" | awk -F/ '{print $NF}' | sort | uniq -d)
if [ -n "$dupes" ]; then
  echo "  DUPLICATES FOUND (same tool name in multiple hubs):"
  for d in $dupes; do
    echo "    '$d' exists in:"
    find "$BASE" -path "*/$d/index.html" | sed "s|$BASE/|      /|;s|/index.html||"
    ERRORS=$((ERRORS + 1))
  done
else
  echo "  No duplicate tool names found!"
fi

# Also check for very similar tool names (potential overlaps)
similar=$(find "$BASE" -name "index.html" -path "*/*/index.html" \
  -not -path "*/about/*" -not -path "*/contact/*" -not -path "*/privacy/*" \
  -not -path "*/terms/*" -not -path "*/docs/*" -not -path "*/node_modules/*" \
  -not -path "*/.git/*" | sed "s|$BASE/||;s|/index.html||" | awk -F/ '{print $NF}' | sort | \
  awk 'prev && index($0, prev)==1 || index(prev, $0)==1 {print prev " <-> " $0} {prev=$0}')
if [ -n "$similar" ]; then
  echo "  SIMILAR names (possible overlaps):"
  echo "$similar" | sed 's/^/    /'
fi

# 7. SEO Keyword Audit (automated keyword placement check)
echo ""
echo "[7/7] Running SEO keyword audit..."
if [ -f "$PY/seo-keyword-engine.py" ] && command -v python3 &>/dev/null; then
  SEO_OUTPUT=$(python3 "$PY/seo-keyword-engine.py" audit 2>&1)
  # Extract just the summary lines
  AVG_SCORE=$(echo "$SEO_OUTPUT" | grep "Average score" | awk '{print $3}')
  CRITICAL_COUNT=$(echo "$SEO_OUTPUT" | grep "CRITICAL" | head -1 | grep -o '[0-9]* tools' | awk '{print $1}')
  echo "  SEO average score: $AVG_SCORE"
  if [ -n "$CRITICAL_COUNT" ] && [ "$CRITICAL_COUNT" -gt 0 ] 2>/dev/null; then
    echo "  WARNING: $CRITICAL_COUNT tools scoring below 50 — run './build-seo-audit.sh --verbose' for details"
  else
    echo "  All tools passing SEO keyword checks!"
  fi
  echo "  Full report: ./build-seo-audit.sh --report"
else
  echo "  SKIPPED: seo-keyword-engine.py or python3 not found"
fi

# 8. Technical SEO validation (viewport, hreflang, lang, OG, JSON-LD)
echo ""
echo "[8/8] Running technical SEO validation..."
TECH_ISSUES=0

if command -v python3 &>/dev/null; then
  TECH_OUTPUT=$(python3 -c "
import glob, re, os

hub_lang = {'de':'de','fr':'fr','jp':'ja','ae':'ar','eg':'ar','sa':'ar','ma':'ar','id':'id','vn':'vi','no':'nb','fi':'fi','se':'sv','nl':'nl'}
issues = {'viewport':0,'hreflang':0,'lang_attr':0,'og_image':0,'brand_title':0,'canonical':0}

for f in sorted(glob.glob('*/*/index.html')):
    hub = f.split('/')[0]
    if hub in ('about','contact','privacy','terms','docs','shared','branding','og-images','.git','icons'):
        continue
    try:
        with open(f,'r',errors='ignore') as fh:
            content = fh.read()
    except:
        continue

    if 'name=\"viewport\"' not in content:
        issues['viewport'] += 1
    if 'og:image' not in content:
        issues['og_image'] += 1
    if 'rel=\"canonical\"' not in content:
        issues['canonical'] += 1

    title_m = re.search(r'<title>(.*?)</title>', content)
    if title_m and 'Teamz Lab' not in title_m.group(1):
        issues['brand_title'] += 1

    expected_lang = hub_lang.get(hub)
    if expected_lang:
        if f'hreflang=\"{expected_lang}\"' not in content:
            issues['hreflang'] += 1
        if f'lang=\"{expected_lang}\"' not in content[:500]:
            issues['lang_attr'] += 1

total = sum(issues.values())
for k, v in issues.items():
    if v > 0:
        print(f'  {k}: {v} pages')
if total == 0:
    print('  All technical checks passing!')
print(f'TOTAL:{total}')
" 2>&1)
  echo "$TECH_OUTPUT" | grep -v "^TOTAL:"
  TECH_ISSUES=$(echo "$TECH_OUTPUT" | grep "^TOTAL:" | cut -d: -f2)
  if [ -n "$TECH_ISSUES" ] && [ "$TECH_ISSUES" -gt 0 ] 2>/dev/null; then
    ERRORS=$((ERRORS + TECH_ISSUES))
  fi
fi

# 9. Schema/layout consistency check
echo ""
echo "[9/11] Checking schema/layout consistency..."
if [ -f "$PY/qa-schema-layout.py" ] && command -v python3 &>/dev/null; then
  SCHEMA_OUTPUT=$(python3 "$PY/qa-schema-layout.py" 2>&1)
  SCHEMA_ERRORS=$(echo "$SCHEMA_OUTPUT" | grep "Error pages:" | grep -o '[0-9]*')
  SCHEMA_WARNINGS=$(echo "$SCHEMA_OUTPUT" | grep "Warning pages:" | grep -o '[0-9]*')
  if [ -n "$SCHEMA_ERRORS" ] && [ "$SCHEMA_ERRORS" -gt 0 ] 2>/dev/null; then
    echo "$SCHEMA_OUTPUT" | grep -A 20 "Errors:"
    ERRORS=$((ERRORS + SCHEMA_ERRORS))
  else
    echo "  No duplicate schemas or layout issues!"
  fi
  if [ -n "$SCHEMA_WARNINGS" ] && [ "$SCHEMA_WARNINGS" -gt 0 ] 2>/dev/null; then
    echo "  Warnings: $SCHEMA_WARNINGS pages have redundant JS inject calls"
  fi
else
  echo "  SKIPPED: qa-schema-layout.py or python3 not found"
fi

# 9b. SEO bulk fix stats (informational — shows what build-seo-fix-all.py can auto-fix)
echo ""
echo "[9b] SEO bulk fix opportunities..."
if [ -f "$PY/build-seo-fix-all.py" ] && command -v python3 &>/dev/null; then
  FIX_OUTPUT=$(python3 "$PY/build-seo-fix-all.py" --stats 2>&1)
  FIX_DISPLAY=$(echo "$FIX_OUTPUT" | grep "display.*bug" | grep -o '[0-9]*')
  FIX_CONTENT=$(echo "$FIX_OUTPUT" | grep "Low content" | grep -o '[0-9]*')
  FIX_H2=$(echo "$FIX_OUTPUT" | grep "How Works" | grep -o '[0-9]*')
  FIX_FAQ=$(echo "$FIX_OUTPUT" | grep "Low FAQ" | grep -o '[0-9]*')
  echo "  display='' bugs:     ${FIX_DISPLAY:-0} pages (auto-fixable)"
  echo "  Low content (<300w): ${FIX_CONTENT:-0} pages (needs content)"
  echo "  Missing How Works:   ${FIX_H2:-0} pages (needs content)"
  echo "  Low FAQs (<5):       ${FIX_FAQ:-0} pages (needs content)"
  if [ -n "$FIX_DISPLAY" ] && [ "$FIX_DISPLAY" -gt 0 ] 2>/dev/null; then
    echo "  → Run: python3 scripts/build-seo-fix-all.py --apply"
  fi
else
  echo "  SKIPPED: build-seo-fix-all.py or python3 not found"
fi

# 10. Broken internal link check + related tools validation
echo ""
echo "[10/11] Checking for broken internal links..."
BROKEN=0
BROKEN_OUTPUT=$(grep -roh 'href="/[^"]*/"' --include="*.html" "$BASE" 2>/dev/null | sort -u | sed 's/href="//;s/"$//' | while IFS= read -r link; do
  DIR="${link#/}"
  DIR="${DIR%/}"
  if [ -n "$DIR" ] && [ ! -f "$BASE/${DIR}/index.html" ] && [ ! -d "$BASE/${DIR}" ]; then
    echo "  BROKEN: $link"
  fi
done)
if [ -n "$BROKEN_OUTPUT" ]; then
  echo "$BROKEN_OUTPUT"
  BROKEN_COUNT=$(echo "$BROKEN_OUTPUT" | wc -l | tr -d ' ')
  echo "  $BROKEN_COUNT broken internal link(s) found!"
  ERRORS=$((ERRORS + BROKEN_COUNT))
else
  echo "  All internal links valid!"
fi

# 10. Related tools & internal link health
echo ""
echo "[11/11] Related tools & internal link health..."
LINK_HEALTH=$(bash "$SCRIPTS/build-internal-links.sh" --quick 2>&1)
LINK_BROKEN=$(echo "$LINK_HEALTH" | awk -F':' '/Broken related slugs:/ {if (match($2, /[0-9]+/)) print substr($2, RSTART, RLENGTH); exit}')
LINK_ORPHANS=$(echo "$LINK_HEALTH" | awk -F':' '/Orphan pages/ {if (match($2, /[0-9]+/)) print substr($2, RSTART, RLENGTH); exit}')
LINK_MISSING=$(echo "$LINK_HEALTH" | awk -F':' '/Missing related tools:/ {if (match($2, /[0-9]+/)) print substr($2, RSTART, RLENGTH); exit}')
LINK_COVERAGE=$(echo "$LINK_HEALTH" | awk -F':' '/Related Tools coverage:/ {if (match($2, /[0-9]+%/)) print substr($2, RSTART, RLENGTH); exit}')
echo "  Related Tools coverage: $LINK_COVERAGE"
echo "  Broken related slugs:  ${LINK_BROKEN:-0}"
echo "  Orphan pages:          ${LINK_ORPHANS:-0}"
echo "  Missing related tools: ${LINK_MISSING:-0}"
if [ -n "$LINK_BROKEN" ] && [ "$LINK_BROKEN" -gt 0 ] 2>/dev/null; then
  echo ""
  echo "$LINK_HEALTH" | grep "BROKEN RELATED" -A 20 | head -15
  ERRORS=$((ERRORS + LINK_BROKEN))
fi
# Auto-fix orphan pages if any found
if [ -n "$LINK_ORPHANS" ] && [ "$LINK_ORPHANS" -gt 0 ] 2>/dev/null; then
  echo ""
  echo "  Auto-fixing $LINK_ORPHANS orphan pages..."
  python3 "$PY/build-fix-orphans.py" fix 2>/dev/null | tail -5
fi
# Warn about hub-unlinked tools
LINK_HUBUNLINKED=$(echo "$LINK_HEALTH" | awk -F':' '/Hub unlinked tools/ {if (match($2, /[0-9]+/)) print substr($2, RSTART, RLENGTH); exit}')
if [ -n "$LINK_HUBUNLINKED" ] && [ "$LINK_HUBUNLINKED" -gt 0 ] 2>/dev/null; then
  echo "  ⚠ $LINK_HUBUNLINKED tool(s) not linked from their hub page!"
  echo "  Run: scripts/build-internal-links.sh --full | grep 'NOT LINKED' -A99"
fi

echo ""
echo "============================================="
total=$(grep -c '<url>' "$BASE/sitemap.xml")
search_count=$(grep -c "^  {" "$BASE/shared/js/search-index.js" 2>/dev/null)
echo "  Total tools in sitemap: $total"
echo "  Total tools in search: $search_count"
echo "  Errors found: $ERRORS"
if [ $ERRORS -gt 0 ] || [ $unlinked -gt 0 ]; then
  echo "  STATUS: NEEDS ATTENTION"
else
  echo "  STATUS: ALL GOOD"
fi
echo "============================================="
