#!/usr/bin/env python3
"""
Batch fix: style.display = '' → showEl(el) or style.display = 'block'

The display='' bug: setting el.style.display = '' only removes inline style,
but if CSS class has display:none, the element stays hidden.

Fix strategy:
- el.style.display = '' → showEl(el) when showEl is available (common.js)
- Falls back to: el.style.display = 'block' for result/content elements
- Falls back to: el.style.display = 'flex' for flex containers
- Falls back to: el.style.display = 'grid' for grid containers

Safe: only replaces `.style.display = ''` patterns, not `.style.display = 'none'`
"""

import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY_RUN = '--dry-run' in sys.argv

def guess_display_type(context, var_name):
    """Guess the correct display type from surrounding context."""
    ctx_lower = context.lower()

    # If the variable name or surrounding context hints at flex/grid
    if any(x in ctx_lower for x in ['flex', 'row', 'actions', 'buttons', 'bar', 'toggle']):
        return 'flex'
    if any(x in ctx_lower for x in ['grid', 'cards', 'summary']):
        return 'grid'

    # Default to 'block' — safest for result divs, sections, etc.
    return 'block'

def fix_file(filepath):
    """Fix style.display = '' in a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    fixes = 0

    # Pattern: .style.display = ''  or .style.display = ""
    # But NOT .style.display = 'none' or .style.display = 'block' etc.
    pattern = r"(\.style\.display\s*=\s*)(['\"])(\2)"

    def replace_match(m):
        nonlocal fixes
        fixes += 1
        # Get some context around the match
        start = max(0, m.start() - 200)
        context = content[start:m.start()]

        # Try to find the variable name
        # e.g. document.getElementById('results').style.display = ''
        var_match = re.search(r"(?:getElementById\(['\"]([^'\"]+)['\"]|(\w+))\.style\.display", content[start:m.end()])
        var_name = ''
        if var_match:
            var_name = var_match.group(1) or var_match.group(2) or ''

        display_type = guess_display_type(context + var_name, var_name)
        return f"{m.group(1)}'{display_type}'"

    content = re.sub(pattern, replace_match, content)

    if fixes > 0:
        if DRY_RUN:
            print(f"  WOULD FIX: {os.path.relpath(filepath, ROOT)} — {fixes} occurrence(s)")
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  FIXED: {os.path.relpath(filepath, ROOT)} — {fixes} occurrence(s)")

    return fixes

def main():
    if DRY_RUN:
        print("DRY RUN — no files will be modified\n")

    total_fixes = 0
    total_files = 0

    for dirpath, dirnames, filenames in os.walk(ROOT):
        # Skip hidden dirs, node_modules, .git
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != 'node_modules']

        for fn in filenames:
            if not fn.endswith('.html'):
                continue
            filepath = os.path.join(dirpath, fn)

            # Quick check if file has the bug
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()

            if re.search(r"\.style\.display\s*=\s*['\"]['\"]", text):
                fixes = fix_file(filepath)
                if fixes > 0:
                    total_fixes += fixes
                    total_files += 1

    print(f"\n{'Would fix' if DRY_RUN else 'Fixed'}: {total_fixes} occurrences in {total_files} files")
    if DRY_RUN:
        print("\nRun without --dry-run to apply fixes.")

if __name__ == '__main__':
    main()
