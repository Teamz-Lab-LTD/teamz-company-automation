#!/usr/bin/env python3
"""
build-hub-subtitles.py — Auto-fill missing subtitles on hub page tool cards.

For each tool-card on every hub index.html that's missing a <p> subtitle,
reads the tool's own meta description and adds it as a short subtitle.

Usage:
  python3 scripts/build-hub-subtitles.py           # Dry-run — show what would change
  python3 scripts/build-hub-subtitles.py --fix      # Apply changes
  python3 scripts/build-hub-subtitles.py --verify   # Verify 100% coverage
"""

import os
import re
import sys
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {'.git', 'node_modules', 'shared', 'branding', 'scripts', 'icons',
             'og-images', 'docs', '.claude', '.claude-memory', 'research'}

def find_hub_pages():
    """Find all hub index.html files (directories with tools-grid)."""
    hubs = []
    for entry in sorted(ROOT.iterdir()):
        if not entry.is_dir() or entry.name in SKIP_DIRS or entry.name.startswith('.'):
            continue
        idx = entry / 'index.html'
        if idx.exists():
            content = idx.read_text(encoding='utf-8', errors='ignore')
            if 'tools-grid' in content:
                hubs.append(idx)
    return hubs

def get_meta_description(tool_path):
    """Read meta description from a tool's index.html."""
    try:
        content = Path(tool_path).read_text(encoding='utf-8', errors='ignore')
        # Try meta name="description"
        m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', content, re.IGNORECASE)
        if m:
            desc = html.unescape(m.group(1)).strip()
            # Truncate to ~80 chars for subtitle
            if len(desc) > 90:
                # Cut at word boundary
                desc = desc[:87].rsplit(' ', 1)[0] + '...'
            return desc
        # Fallback: try og:description
        m = re.search(r'<meta\s+property="og:description"\s+content="([^"]*)"', content, re.IGNORECASE)
        if m:
            desc = html.unescape(m.group(1)).strip()
            if len(desc) > 90:
                desc = desc[:87].rsplit(' ', 1)[0] + '...'
            return desc
    except Exception:
        pass
    return None

def process_hub(hub_path, fix=False):
    """Process a single hub page, find cards without subtitles, add them."""
    content = hub_path.read_text(encoding='utf-8', errors='ignore')
    hub_dir = hub_path.parent

    # Find all tool-card links
    # Pattern: <a href="/hub/tool/" class="tool-card"><div class="card"><h3>Title</h3></div></a>
    # Cards WITH subtitle: <h3>Title</h3><p>Subtitle</p>
    # Cards WITHOUT: <h3>Title</h3></div>

    pattern = re.compile(
        r'(<a\s+href="([^"]+)"\s+class="tool-card"><div\s+class="card"><h3>[^<]+</h3>)(</div></a>)'
    )

    missing = []
    fixed = 0
    new_content = content

    for match in pattern.finditer(content):
        before = match.group(1)
        href = match.group(2)
        after = match.group(3)
        full = match.group(0)

        # Check if there's already a <p> after </h3>
        # The pattern only matches cards WITHOUT <p> (</h3> immediately followed by </div>)
        tool_path = ROOT / href.strip('/') / 'index.html'
        desc = get_meta_description(tool_path)

        if desc:
            missing.append((href, desc))
            if fix:
                # Insert <p>desc</p> between </h3> and </div>
                replacement = before + '<p>' + html.escape(desc) + '</p>' + after
                new_content = new_content.replace(full, replacement, 1)
                fixed += 1

    if fix and fixed > 0:
        hub_path.write_text(new_content, encoding='utf-8')

    return missing, fixed

def verify_coverage():
    """Check all hub pages for 100% subtitle coverage."""
    hubs = find_hub_pages()
    total_cards = 0
    missing_cards = 0
    issues = []

    for hub in hubs:
        content = hub.read_text(encoding='utf-8', errors='ignore')
        hub_name = hub.parent.name

        # Count cards with and without <p>
        cards_with_p = len(re.findall(r'class="tool-card"><div class="card"><h3>[^<]+</h3><p>', content))
        cards_without_p = len(re.findall(r'class="tool-card"><div class="card"><h3>[^<]+</h3></div>', content))

        total_cards += cards_with_p + cards_without_p
        missing_cards += cards_without_p

        if cards_without_p > 0:
            issues.append(f'  {hub_name}/index.html: {cards_without_p}/{cards_with_p + cards_without_p} cards missing subtitles')

    coverage = ((total_cards - missing_cards) / total_cards * 100) if total_cards > 0 else 100
    print(f'\n=== Hub Subtitle Coverage Report ===')
    print(f'Total tool cards: {total_cards}')
    print(f'With subtitle: {total_cards - missing_cards}')
    print(f'Missing subtitle: {missing_cards}')
    print(f'Coverage: {coverage:.1f}%')

    if issues:
        print(f'\nHubs with missing subtitles:')
        for issue in issues:
            print(issue)
    else:
        print(f'\n✓ 100% subtitle coverage — all cards have subtitles!')

    return missing_cards == 0

def main():
    fix = '--fix' in sys.argv
    verify = '--verify' in sys.argv

    if verify:
        ok = verify_coverage()
        sys.exit(0 if ok else 1)

    hubs = find_hub_pages()
    total_missing = 0
    total_fixed = 0

    print(f'{"Fixing" if fix else "Checking"} subtitles across {len(hubs)} hub pages...\n')

    for hub in hubs:
        hub_name = hub.parent.name
        missing, fixed = process_hub(hub, fix=fix)
        if missing:
            print(f'{hub_name}/index.html: {len(missing)} cards {"fixed" if fix else "need subtitles"}')
            for href, desc in missing[:3]:  # Show first 3 examples
                print(f'  {href} → "{desc}"')
            if len(missing) > 3:
                print(f'  ... and {len(missing) - 3} more')
            total_missing += len(missing)
            total_fixed += fixed

    print(f'\n{"=" * 40}')
    print(f'Total cards needing subtitles: {total_missing}')
    if fix:
        print(f'Total cards fixed: {total_fixed}')
    else:
        print(f'Run with --fix to apply changes')

if __name__ == '__main__':
    main()
