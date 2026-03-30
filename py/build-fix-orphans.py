#!/usr/bin/env python3
"""
Fix orphan pages by adding them to related tools of same-hub siblings.

Orphan = a tool page that no other tool links to via renderRelatedTools.
Fix = find tools in the same hub that DO have related tools, and add
the orphan as one of them.

Strategy:
1. First pass: add orphans to siblings with <6 related tools
2. Second pass: add orphans to siblings with 6 related tools (up to 8 max)
3. Third pass: for still-orphaned tools, try cross-hub linking to
   tools in related categories
4. Distribute evenly — track how many additions each sibling gets,
   prefer siblings with fewer additions

Handles both slug: and url: formats for incoming link detection.
"""

import os
import re
import json
import sys
from collections import defaultdict
from _teamz_config import load_runtime

RUNTIME = load_runtime(__file__)
ROOT = str(RUNTIME["host_site_root"])
PROJECT_TYPE = RUNTIME.get("project_type", "website")

# Track modifications per file to avoid overloading any single file
file_additions = defaultdict(int)

# Max related tools per page (original is 6, allow up to 8 for orphan fixing)
MAX_RELATED = 8
# Max additions per single file in one run
MAX_ADDITIONS_PER_FILE = 2


def find_all_tools():
    """Find all tool pages (hub/tool/index.html)."""
    tools = []
    skip_prefixes = ('.', 'shared', 'scripts', 'docs', 'branding', 'icons',
                     'og-images', 'node_modules', 'fonts', 'config')
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        if any(rel.startswith(p) for p in skip_prefixes):
            continue
        if 'index.html' in filenames:
            parts = rel.split(os.sep)
            if len(parts) == 2:  # hub/tool/
                tools.append({
                    'hub': parts[0],
                    'slug': parts[0] + '/' + parts[1],
                    'filepath': os.path.join(dirpath, 'index.html'),
                    'rel_path': rel + '/index.html'
                })
    return tools


def read_file(filepath):
    """Read file content safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return None


def extract_tool_meta(filepath, content=None):
    """Extract title, description, related tools from a tool page."""
    if content is None:
        content = read_file(filepath)
    if not content:
        return None

    # Get H1
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
    h1 = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip() if h1_match else ''

    # Get meta description
    desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', content)
    desc = desc_match.group(1) if desc_match else ''

    # Get related tools - both slug: and url: formats
    related_slugs = set()

    # Format 1: slug: 'hub/tool'
    for m in re.finditer(r"slug:\s*['\"]([^'\"]+)['\"]", content):
        s = m.group(1).strip('/')
        if '/' in s:  # Must be hub/tool format
            related_slugs.add(s)

    # Format 2: url: '/hub/tool/'
    for m in re.finditer(r"url:\s*['\"]/?([^'\"]+?)/?\s*['\"]", content):
        s = m.group(1).strip('/')
        if '/' in s and not s.startswith('http'):
            related_slugs.add(s)

    # Count total related tool entries in the renderRelatedTools call
    rt_match = re.search(r'renderRelatedTools\s*\(\s*\[', content)
    related_count = 0
    if rt_match:
        # Find the matching closing bracket
        bracket_start = content.index('[', rt_match.start())
        depth = 0
        i = bracket_start
        while i < len(content):
            if content[i] == '[':
                depth += 1
            elif content[i] == ']':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        array_content = content[bracket_start:i+1]
        # Count objects (entries) by counting opening braces
        related_count = array_content.count('{')

    # Check if it's a redirect page
    is_redirect = bool(re.search(r'window\.location\s*[=.]\s*|<meta\s+http-equiv="refresh"', content))

    return {
        'h1': h1,
        'description': desc,
        'related_slugs': related_slugs,
        'related_count': related_count,
        'has_render_related': 'renderRelatedTools' in content,
        'is_redirect': is_redirect,
        'content': content
    }


def extract_related_slugs_only(content, own_slug):
    """Extract only the slugs/urls from renderRelatedTools or RELATED_TOOLS arrays.
    Excludes the tool's own slug references (e.g. from injectWebAppSchema)."""
    related = set()

    # Find the renderRelatedTools([...]) or RELATED_TOOLS = [...] block
    patterns = [
        r'(?:var|const|let)\s+RELATED_TOOLS\s*=\s*\[([\s\S]*?)\]\s*;',
        r'window\.RELATED_TOOLS\s*(?:=|===)\s*[^[]*\[([\s\S]*?)\]\s*;',
        r'renderRelatedTools\s*\(\s*\[([\s\S]*?)\]\s*\)',
    ]

    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            array_content = match.group(1)
            # Extract slug: 'hub/tool' format
            for m in re.finditer(r"slug:\s*['\"]([^'\"]+)['\"]", array_content):
                s = m.group(1).strip('/')
                if '/' in s and s != own_slug:
                    related.add(s)
            # Extract url: '/hub/tool/' format
            for m in re.finditer(r"url:\s*['\"]/?([^'\"]+?)/?\s*['\"]", array_content):
                s = m.group(1).strip('/')
                if '/' in s and not s.startswith('http') and s != own_slug:
                    related.add(s)
            break  # Only process first match

    return related


def get_incoming_links(tools):
    """Build a map of slug -> set of tools that link to it."""
    incoming = defaultdict(set)
    tool_metas = {}

    for t in tools:
        content = read_file(t['filepath'])
        meta = extract_tool_meta(t['filepath'], content)
        if meta:
            tool_metas[t['slug']] = meta
            # Use precise extraction for incoming links
            related = extract_related_slugs_only(content, t['slug'])
            meta['related_slugs'] = related  # Override with precise set
            for rs in related:
                incoming[rs].add(t['slug'])

    return incoming, tool_metas


def find_orphans(tools, incoming, tool_metas):
    """Find tools with 0 incoming related links, excluding redirects."""
    orphans = []
    for t in tools:
        meta = tool_metas.get(t['slug'])
        if meta and meta['is_redirect']:
            continue  # Skip redirect pages
        if len(incoming.get(t['slug'], set())) == 0:
            orphans.append(t)
    return orphans


def detect_related_format(content):
    """Detect which format the related tools array uses."""
    # Check for RELATED_TOOLS variable
    var_match = re.search(r'(?:var|const|let)\s+RELATED_TOOLS\s*=\s*\[', content)
    if var_match:
        return 'variable'

    # Check for inline renderRelatedTools([...])
    inline_match = re.search(r'renderRelatedTools\s*\(\s*\[', content)
    if inline_match:
        return 'inline'

    # Check for window.RELATED_TOOLS
    win_match = re.search(r'window\.RELATED_TOOLS\s*=\s*\[', content)
    if win_match:
        return 'window_var'

    return None


def detect_entry_format(content):
    """Detect whether entries use slug: or url: format."""
    # Look inside renderRelatedTools or RELATED_TOOLS
    if re.search(r"slug:\s*['\"]", content):
        return 'slug'
    if re.search(r"url:\s*['\"]", content):
        return 'url'
    return 'slug'  # default


def add_related_entry(content, orphan_slug, orphan_name, orphan_desc, entry_format):
    """Add a related tool entry to the content, matching existing format."""
    # Escape quotes in name and description
    name = orphan_name.replace("'", "\\'").replace('"', '\\"')
    desc = orphan_desc.replace("'", "\\'").replace('"', '\\"')

    if entry_format == 'url':
        new_entry_single = "{ name: '%s', url: '/%s/' }" % (name, orphan_slug)
        new_entry_full = "{ name: '%s', url: '/%s/', desc: '%s' }" % (name, orphan_slug, desc)
    else:
        new_entry_single = '{ slug: "%s", name: "%s", description: "%s" }' % (orphan_slug, name, desc)
        new_entry_full = new_entry_single

    # Strategy: find the last } before the ] that closes the related tools array
    # We need to find the renderRelatedTools([...]) or RELATED_TOOLS = [...] block

    # Pattern 1: var RELATED_TOOLS = [ ... ];
    patterns = [
        (r'((?:var|const|let)\s+RELATED_TOOLS\s*=\s*\[[\s\S]*?)(]\s*;)', 'variable'),
        (r'(window\.RELATED_TOOLS\s*=\s*\[[\s\S]*?)(]\s*;)', 'window_var'),
        (r'(renderRelatedTools\s*\(\s*\[[\s\S]*?)(]\s*\))', 'inline'),
    ]

    for pattern, ptype in patterns:
        match = re.search(pattern, content)
        if match:
            before_bracket = match.group(1)
            closing = match.group(2)

            # Check if array has existing entries
            has_entries = '{' in before_bracket

            if has_entries:
                # Add comma after last entry, then new entry
                new_content = before_bracket.rstrip() + ',\n      ' + new_entry_full + '\n    ' + closing
            else:
                # Empty array - just add entry
                new_content = before_bracket + '\n      ' + new_entry_full + '\n    ' + closing

            return content[:match.start()] + new_content + content[match.end():]

    return None  # Could not find insertion point


def fix_orphans_aggressive(tools, orphans, tool_metas, incoming, dry_run=True):
    """Fix orphans with multi-pass strategy."""
    # Group tools by hub
    hub_tools = defaultdict(list)
    for t in tools:
        hub_tools[t['hub']].append(t)

    # Track which files we've modified (need to re-read after modification)
    modified_files = {}  # filepath -> new content
    fixed_orphans = set()
    fix_log = []

    # Sort orphans by hub for better grouping
    orphans_by_hub = defaultdict(list)
    for o in orphans:
        orphans_by_hub[o['hub']].append(o)

    # ─── PASS 1: Add to siblings with < 6 related tools ───
    print("  Pass 1: Adding to siblings with <6 related tools...")
    pass1_count = 0
    for orphan in orphans:
        if orphan['slug'] in fixed_orphans:
            continue
        result = try_fix_orphan(orphan, hub_tools, tool_metas, modified_files, max_related=6, dry_run=dry_run)
        if result:
            fixed_orphans.add(orphan['slug'])
            fix_log.append(result)
            pass1_count += 1
    print(f"    Fixed: {pass1_count}")

    # ─── PASS 2: Add to siblings with 6 related tools (allow up to 8) ───
    print("  Pass 2: Adding to siblings with 6 related (expanding to 8 max)...")
    pass2_count = 0
    for orphan in orphans:
        if orphan['slug'] in fixed_orphans:
            continue
        result = try_fix_orphan(orphan, hub_tools, tool_metas, modified_files, max_related=MAX_RELATED, dry_run=dry_run)
        if result:
            fixed_orphans.add(orphan['slug'])
            fix_log.append(result)
            pass2_count += 1
    print(f"    Fixed: {pass2_count}")

    # ─── PASS 3: Cross-hub linking for still-orphaned tools ───
    print("  Pass 3: Cross-hub linking for remaining orphans...")
    # Define related hub groups for cross-linking
    hub_groups = {
        'health': ['evergreen', 'fitness', 'sports', 'kids', 'eldercare'],
        'fitness': ['health', 'sports', 'evergreen'],
        'sports': ['fitness', 'health', 'cricket', 'football'],
        'ai': ['tools', 'dev', 'career'],
        'dev': ['tools', 'ai', 'security'],
        'tools': ['dev', 'ai', 'evergreen'],
        'evergreen': ['tools', 'health', 'math'],
        'math': ['evergreen', 'tools', 'student'],
        'career': ['ai', 'work', 'freelance'],
        'work': ['career', 'freelance', 'evergreen'],
        'freelance': ['work', 'career', 'creator'],
        'creator': ['freelance', 'video', 'design', 'image'],
        'design': ['creator', 'image', 'dev'],
        'image': ['design', 'creator', 'video'],
        'video': ['image', 'creator', 'tools'],
        'finance': ['evergreen', 'crypto', 'auto'],
        'crypto': ['finance', 'dev'],
        'auto': ['evergreen', 'finance'],
        'weather': ['evergreen', 'travel'],
        'travel': ['weather', 'evergreen'],
        'student': ['math', 'evergreen', 'tools'],
        'cooking': ['evergreen', 'health'],
        'pet': ['health', 'evergreen'],
        'home': ['evergreen', 'garden'],
        'garden': ['home', 'weather'],
        'uk': ['evergreen', 'finance'],
        'us': ['evergreen', 'finance'],
        'au': ['evergreen', 'finance'],
        'bd': ['evergreen', 'finance'],
        'in': ['evergreen', 'finance'],
        'de': ['evergreen', 'finance'],
        'fr': ['evergreen', 'finance'],
        'no': ['evergreen', 'finance'],
        'se': ['evergreen', 'finance'],
        'nl': ['evergreen', 'finance'],
        'za': ['evergreen', 'finance'],
        'ng': ['evergreen', 'finance'],
        'ae': ['evergreen', 'finance'],
        'eg': ['evergreen', 'finance'],
        'sa': ['evergreen', 'finance'],
        'id': ['evergreen', 'finance'],
        'vn': ['evergreen', 'finance'],
        'jp': ['evergreen', 'tools'],
        'ma': ['evergreen', 'finance'],
        'fi': ['evergreen', 'finance'],
        'ramadan': ['bd', 'ae', 'sa', 'eg'],
        'military': ['career', 'work', 'health'],
        'legal': ['evergreen', 'finance', 'uk', 'us'],
        'real-estate': ['evergreen', 'finance', 'home'],
        'security': ['dev', 'tools', 'diagnostic'],
        'diagnostic': ['dev', 'tools', 'security'],
        'accessibility': ['health', 'dev', 'tools'],
        'compliance': ['legal', 'dev', 'uk'],
        'amazon': ['creator', 'freelance', 'finance'],
        'apple': ['tools', 'dev'],
        'gaming': ['tools', 'evergreen'],
        'grooming': ['health', 'design'],
        'restaurant': ['cooking', 'evergreen'],
        'astrology': ['evergreen', 'tools'],
        'baby': ['health', 'kids'],
        'kids': ['baby', 'health', 'student'],
        'wedding': ['evergreen', 'tools'],
        'diy': ['home', 'tools'],
        '3d': ['design', 'dev'],
        'eldercare': ['health', 'evergreen'],
    }

    pass3_count = 0
    for orphan in orphans:
        if orphan['slug'] in fixed_orphans:
            continue
        hub = orphan['hub']
        related_hubs = hub_groups.get(hub, ['evergreen', 'tools'])

        found = False
        for related_hub in related_hubs:
            if found:
                break
            # Create a fake hub_tools with just this related hub
            cross_hub = {related_hub: hub_tools.get(related_hub, [])}
            # Temporarily change orphan's hub to try cross-hub
            orphan_copy = dict(orphan)
            orphan_copy['hub'] = related_hub
            result = try_fix_orphan(orphan_copy, cross_hub, tool_metas, modified_files, max_related=MAX_RELATED, dry_run=dry_run)
            if result:
                fixed_orphans.add(orphan['slug'])
                fix_log.append(result)
                pass3_count += 1
                found = True

    print(f"    Fixed: {pass3_count}")

    # ─── Write all modified files ───
    if not dry_run:
        print(f"\n  Writing {len(modified_files)} modified files...")
        for filepath, content in modified_files.items():
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        print("  Done!")

    return fix_log, fixed_orphans


def try_fix_orphan(orphan, hub_tools, tool_metas, modified_files, max_related=6, dry_run=True):
    """Try to add an orphan to a same-hub sibling's related tools."""
    hub = orphan['hub']
    siblings = hub_tools.get(hub, [])

    orphan_meta = tool_metas.get(orphan['slug'])
    if not orphan_meta or not orphan_meta['h1']:
        return None

    # Short description
    short_desc = orphan_meta['description'][:80] if orphan_meta['description'] else orphan_meta['h1']

    # Sort siblings: prefer those with fewer additions and fewer existing related tools
    siblings_scored = []
    for s in siblings:
        if s['slug'] == orphan['slug']:
            continue
        s_meta = tool_metas.get(s['slug'])
        if not s_meta or not s_meta['has_render_related'] or s_meta['is_redirect']:
            continue
        if orphan['slug'] in [rs.strip('/') for rs in s_meta['related_slugs']]:
            continue

        # Get current content (may have been modified)
        current_content = modified_files.get(s['filepath'], s_meta['content'])
        # Recount related tools in current content
        current_count = current_content.count("slug:") + current_content.count("url:")
        # Rough count - count { in the renderRelatedTools array
        rt_match = re.search(r'renderRelatedTools\s*\(\s*\[', current_content)
        if rt_match:
            bracket_start = current_content.index('[', rt_match.start())
            depth = 0
            i = bracket_start
            while i < len(current_content):
                if current_content[i] == '[':
                    depth += 1
                elif current_content[i] == ']':
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            array_str = current_content[bracket_start:i+1]
            current_count = array_str.count('{')
        else:
            # Check RELATED_TOOLS variable
            rt_match2 = re.search(r'RELATED_TOOLS\s*=\s*\[', current_content)
            if rt_match2:
                bracket_start = current_content.index('[', rt_match2.start())
                depth = 0
                i = bracket_start
                while i < len(current_content):
                    if current_content[i] == '[':
                        depth += 1
                    elif current_content[i] == ']':
                        depth -= 1
                        if depth == 0:
                            break
                    i += 1
                array_str = current_content[bracket_start:i+1]
                current_count = array_str.count('{')
            else:
                continue

        if current_count >= max_related:
            continue

        additions = file_additions[s['filepath']]
        if additions >= MAX_ADDITIONS_PER_FILE:
            continue

        # Score: prefer fewer related tools, fewer additions
        score = current_count * 10 + additions
        siblings_scored.append((score, s, current_content, current_count))

    if not siblings_scored:
        return None

    # Pick the best sibling (lowest score)
    siblings_scored.sort(key=lambda x: x[0])
    _, best_sibling, current_content, current_count = siblings_scored[0]

    # Detect entry format
    entry_format = detect_entry_format(current_content)

    # Add the entry
    new_content = add_related_entry(current_content, orphan['slug'], orphan_meta['h1'], short_desc, entry_format)
    if not new_content:
        return None

    # Store the modification
    modified_files[best_sibling['filepath']] = new_content
    file_additions[best_sibling['filepath']] += 1

    action = "WOULD ADD" if dry_run else "FIXED"
    msg = f"  {action}: {orphan['slug']} → {best_sibling['rel_path']} (was {current_count} related)"
    print(msg)

    return {
        'orphan': orphan['slug'],
        'target': best_sibling['rel_path'],
        'previous_count': current_count
    }


def main():
    if PROJECT_TYPE == "app":
        print("INFO: build-fix-orphans.py is website-focused and disabled for TEAMZ_PROJECT_TYPE=app.")
        sys.exit(2)

    dry_run = '--dry-run' in sys.argv
    if len(sys.argv) < 2 or sys.argv[1] == '--dry-run':
        dry_run = True
    elif sys.argv[1] == 'fix':
        dry_run = '--dry-run' in sys.argv

    print(f"\n{'='*60}")
    print(f"  ORPHAN PAGE FIXER v2 {'(DRY RUN)' if dry_run else '(LIVE)'}")
    print(f"{'='*60}\n")

    print("  Finding all tools...")
    tools = find_all_tools()
    print(f"  Found {len(tools)} tools\n")

    print("  Building incoming link map (slug + url formats)...")
    incoming, tool_metas = get_incoming_links(tools)

    orphans = find_orphans(tools, incoming, tool_metas)
    print(f"  Found {len(orphans)} orphan pages (excluding redirects)\n")

    if not orphans:
        print("  No orphans found! All tools have incoming links.")
        return

    fix_log, fixed = fix_orphans_aggressive(tools, orphans, tool_metas, incoming, dry_run=dry_run)

    unfixed = [o for o in orphans if o['slug'] not in fixed]

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Total orphans:       {len(orphans)}")
    print(f"  Fixed:               {len(fixed)}")
    print(f"  Still orphaned:      {len(unfixed)}")
    print(f"  Files modified:      {len([f for f in file_additions if file_additions[f] > 0])}")

    if unfixed:
        print(f"\n  STILL ORPHANED ({len(unfixed)} tools):")
        for u in unfixed[:50]:
            meta = tool_metas.get(u['slug'])
            reason = "no sibling with room" if meta else "no metadata"
            if meta and not meta['has_render_related']:
                reason = "no renderRelatedTools in any sibling"
            print(f"    {u['slug']} — {reason}")
        if len(unfixed) > 50:
            print(f"    ... and {len(unfixed) - 50} more")

    if dry_run:
        print(f"\n  Run with 'fix' to apply: python3 scripts/build-fix-orphans.py fix")
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()
