#!/bin/bash
# ─── Internal Link Health Check — Teamz Lab Tools ─────────────────
# Validates ALL internal links across 900+ tools.
# Usage:
#   ./build-internal-links.sh              # Full report
#   ./build-internal-links.sh --quick      # Just errors
#   ./build-internal-links.sh --orphans    # Only orphan detection
# ───────────────────────────────────────────────────────────────────

SCRIPTS="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")" && pwd)"
source "$SCRIPTS/lib/config.sh"
teamz_load_config "$0"
BASE="$TEAMZ_HOST_SITE_ROOT"

if [[ "${TEAMZ_PROJECT_TYPE:-website}" == "app" ]]; then
  echo "INFO: build-internal-links.sh is website-focused and disabled for TEAMZ_PROJECT_TYPE=app."
  exit 2
fi

MODE="${1:---full}"

python3 - "$BASE" "$MODE" << 'PYEOF'
import os
import re
import sys
import glob
from collections import defaultdict
from datetime import datetime

BASE = sys.argv[1]
MODE = sys.argv[2]

EXCLUDE = {
    'about', 'contact', 'privacy', 'terms', 'docs', 'shared', 'branding',
    'node_modules', '.git', 'icons', 'fonts', 'images', 'css', 'js',
    'assets', '.github', '.vscode', 'scripts', 'og-images'
}

print("=" * 70)
print("  INTERNAL LINK HEALTH CHECK — tool.teamzlab.com")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 70)

# ─── 1. Discover all tool pages ──────────────────────────────────
print("\n[1/7] Discovering all tool pages...")
tools = {}  # slug → filepath
hub_tools = defaultdict(list)  # hub → [slugs]

for filepath in glob.glob(os.path.join(BASE, '*', '*', 'index.html')):
    rel = os.path.relpath(filepath, BASE)
    parts = rel.split(os.sep)
    if len(parts) < 3:
        continue
    hub = parts[0]
    tool = parts[1]
    if hub in EXCLUDE or hub.startswith('.'):
        continue
    slug = f"{hub}/{tool}"
    tools[slug] = filepath
    hub_tools[hub].append(slug)

print(f"  Found {len(tools)} tool pages across {len(hub_tools)} hubs")

# ─── 2. Extract related tools from each page ─────────────────────
print("\n[2/7] Checking renderRelatedTools in all pages...")
missing_related = []
has_related = []
all_related_data = {}  # slug → [{slug, name, desc}]
incoming_links = defaultdict(int)  # slug → count

for slug, filepath in tools.items():
    try:
        with open(filepath, 'r', errors='ignore') as f:
            content = f.read()
    except Exception:
        continue

    # Check if renderRelatedTools exists
    if 'renderRelatedTools' not in content:
        missing_related.append(slug)
        continue

    has_related.append(slug)

    # Extract the related tools array — supports multiple patterns:
    # 1. renderRelatedTools([ ... ])  (inline)
    # 2. var RELATED_TOOLS = [ ... ]; ... renderRelatedTools(RELATED_TOOLS)
    # 3. window.RELATED_TOOLS = [ ... ];
    block = None
    m = re.search(r'renderRelatedTools\(\s*\[(.*?)\]\s*\)', content, re.DOTALL)
    if m:
        block = m.group(1)
    else:
        # Try RELATED_TOOLS variable pattern
        m2 = re.search(r'(?:var|const|let)\s+RELATED_TOOLS\s*=\s*\[(.*?)\]\s*;', content, re.DOTALL)
        if m2:
            block = m2.group(1)
        else:
            m3 = re.search(r'window\.RELATED_TOOLS\s*=\s*\[(.*?)\]\s*;', content, re.DOTALL)
            if m3:
                block = m3.group(1)

    if not block:
        continue

    # Extract slugs in both formats: slug: 'x/y' and url: '/x/y/'
    slugs = re.findall(r"slug\s*:\s*['\"]([^'\"]+)['\"]", block)
    urls = re.findall(r"url\s*:\s*['\"]/?([^'\"]+?)/?\s*['\"]", block)
    names = re.findall(r"name\s*:\s*['\"]([^'\"]+)['\"]", block)
    descs = re.findall(r"(?:description|desc)\s*:\s*['\"]([^'\"]*?)['\"]", block)

    # Combine slug and url entries
    all_slugs = [s.strip('/') for s in slugs] + [u.strip('/') for u in urls if '/' in u and not u.startswith('http')]

    related = []
    for i, s in enumerate(all_slugs):
        n = names[i] if i < len(names) else ''
        d = descs[i] if i < len(descs) else ''
        related.append({'slug': s, 'name': n, 'desc': d})
        incoming_links[s] += 1

    all_related_data[slug] = related

coverage = len(has_related) * 100 // len(tools) if tools else 0
print(f"  With related tools:    {len(has_related)} / {len(tools)} ({coverage}%)")
print(f"  Missing related tools: {len(missing_related)} / {len(tools)}")

if missing_related and MODE != '--quick':
    print(f"\n  Tools WITHOUT renderRelatedTools:")
    for s in sorted(missing_related)[:30]:
        print(f"    MISSING: /{s}/")
    if len(missing_related) > 30:
        print(f"    ... and {len(missing_related) - 30} more")

# ─── 3. Validate slugs ───────────────────────────────────────────
print("\n[3/7] Validating related tool slugs...")
broken_links = []
self_links = []
too_few = []
empty_fields = []

for slug, related in all_related_data.items():
    # Check count
    if len(related) < 3:
        too_few.append((slug, len(related)))

    for r in related:
        rs = r['slug']

        # Broken: target doesn't exist
        if rs not in tools and not os.path.isfile(os.path.join(BASE, rs, 'index.html')):
            broken_links.append((slug, rs))

        # Self-link
        if rs == slug:
            self_links.append(slug)

        # Empty fields
        if not r['name'] or not r['desc']:
            empty_fields.append((slug, rs))

print(f"  Broken slugs:     {len(broken_links)}")
print(f"  Self-links:       {len(self_links)}")
print(f"  Too few (<3):     {len(too_few)}")
print(f"  Empty fields:     {len(empty_fields)}")

if broken_links:
    print(f"\n  BROKEN RELATED TOOL LINKS:")
    for src, dst in sorted(broken_links)[:30]:
        # Suggest closest match
        suggestion = ""
        dst_parts = dst.split('/')
        if len(dst_parts) >= 2:
            dst_tool = dst_parts[-1]
            matches = [s for s in tools if dst_tool in s]
            if matches:
                suggestion = f" (did you mean: /{matches[0]}/)"
        print(f"    /{src}/ → /{dst}/ BROKEN{suggestion}")
    if len(broken_links) > 30:
        print(f"    ... and {len(broken_links) - 30} more")

if self_links:
    print(f"\n  SELF-LINKS (tool links to itself):")
    for s in sorted(self_links)[:20]:
        print(f"    /{s}/")

if too_few and MODE == '--full':
    print(f"\n  TOO FEW RELATED TOOLS (<3):")
    for s, count in sorted(too_few)[:20]:
        print(f"    /{s}/ — only {count} related tools")

# ─── 4. Orphan detection ──────────────────────────────────────────
print("\n[4/7] Detecting orphan pages...")
orphans = []
for slug in tools:
    if incoming_links.get(slug, 0) == 0:
        orphans.append(slug)

print(f"  Orphan pages (0 incoming related links): {len(orphans)} / {len(tools)}")

if orphans and MODE in ('--full', '--orphans'):
    print(f"\n  ORPHAN PAGES (no other tool links here):")
    for s in sorted(orphans)[:40]:
        print(f"    /{s}/")
    if len(orphans) > 40:
        print(f"    ... and {len(orphans) - 40} more")

# ─── 5. Hub page coverage ────────────────────────────────────────
print("\n[5/7] Checking hub pages link to their tools...")
hub_unlinked = []

for hub, slugs in hub_tools.items():
    hub_index = os.path.join(BASE, hub, 'index.html')
    if not os.path.isfile(hub_index):
        continue
    try:
        with open(hub_index, 'r', errors='ignore') as f:
            hub_content = f.read()
    except Exception:
        continue

    for slug in slugs:
        tool_name = slug.split('/')[-1]
        if tool_name not in hub_content:
            hub_unlinked.append(slug)

print(f"  Tools not linked from hub page: {len(hub_unlinked)}")

if hub_unlinked and MODE != '--quick':
    print(f"\n  TOOLS NOT LINKED FROM THEIR HUB:")
    for s in sorted(hub_unlinked)[:30]:
        print(f"    /{s}/")
    if len(hub_unlinked) > 30:
        print(f"    ... and {len(hub_unlinked) - 30} more")

# ─── 6. All href broken link check ───────────────────────────────
print("\n[6/7] Validating all href internal links...")
all_hrefs = set()
href_broken = []

for filepath in glob.glob(os.path.join(BASE, '**', '*.html'), recursive=True):
    rel = os.path.relpath(filepath, BASE)
    if any(rel.startswith(ex) for ex in EXCLUDE):
        continue
    try:
        with open(filepath, 'r', errors='ignore') as f:
            content = f.read()
        links = re.findall(r'href="(/[^"]*?/)"', content)
        for link in links:
            all_hrefs.add(link)
    except Exception:
        continue

for link in sorted(all_hrefs):
    path = link.strip('/')
    if path and not os.path.isfile(os.path.join(BASE, path, 'index.html')) \
            and not os.path.isdir(os.path.join(BASE, path)):
        href_broken.append(link)

print(f"  Total unique internal links: {len(all_hrefs)}")
print(f"  Broken href links: {len(href_broken)}")

if href_broken:
    print(f"\n  BROKEN HREF LINKS:")
    for link in href_broken[:20]:
        print(f"    {link}")
    if len(href_broken) > 20:
        print(f"    ... and {len(href_broken) - 20} more")

# ─── 7. Top linked tools (most incoming) ─────────────────────────
print("\n[7/7] Most linked tools (strongest internal authority)...")
top_linked = sorted(incoming_links.items(), key=lambda x: x[1], reverse=True)
if top_linked and MODE == '--full':
    print(f"\n  TOP 20 MOST-LINKED TOOLS:")
    print(f"  {'Tool':<45} {'Incoming Links':>15}")
    print("  " + "-" * 62)
    for slug, count in top_linked[:20]:
        print(f"  /{slug + '/':<44} {count:>15}")

# ─── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  INTERNAL LINK HEALTH SCORE")
print("=" * 70)

print(f"\n  Related Tools coverage:  {coverage}% ({len(has_related)} / {len(tools)})")
print(f"  Broken related slugs:    {len(broken_links)}")
print(f"  Self-links:              {len(self_links)}")
print(f"  Orphan pages:            {len(orphans)}")
print(f"  Hub unlinked tools:      {len(hub_unlinked)}")
print(f"  Broken href links:       {len(href_broken)}")
print(f"  Empty name/description:  {len(empty_fields)}")
print(f"  Too few related (<3):    {len(too_few)}")

# Score
score = 100
score -= len(missing_related) // 5
score -= len(broken_links) * 3
score -= len(self_links) * 2
score -= min(30, len(orphans) // 20)  # Cap orphan penalty at -30
score -= len(hub_unlinked) // 3
score -= len(href_broken) * 5
score = max(0, min(100, score))

print(f"\n  HEALTH SCORE: {score} / 100")
if score >= 90:
    print("  EXCELLENT — Internal linking is strong")
elif score >= 70:
    print("  GOOD — Minor issues to fix")
elif score >= 50:
    print("  NEEDS WORK — Several linking gaps")
else:
    print("  CRITICAL — Major internal linking issues")

print("\n" + "=" * 70)
print("  Run: ./build-internal-links.sh --quick     (errors only)")
print("  Run: ./build-internal-links.sh --orphans   (orphan detection)")
print("  Run: ./build-internal-links.sh --full      (full report)")
print("=" * 70)

# Exit code
if broken_links or href_broken:
    sys.exit(1)
PYEOF
