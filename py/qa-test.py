#!/usr/bin/env python3
"""Teamz Lab Tools — Fast QA Test Suite. Tests ALL tool pages."""

import os, re, sys, glob
from _teamz_config import load_runtime

RUNTIME = load_runtime(__file__)
ROOT = str(RUNTIME["host_site_root"])
PROJECT_TYPE = RUNTIME.get("project_type", "website")
os.chdir(ROOT)

if PROJECT_TYPE == "app":
    print("INFO: qa-test.py is website-focused and disabled for TEAMZ_PROJECT_TYPE=app.")
    sys.exit(2)

critical, fails, warns, passed = [], [], [], []

pages = sorted(glob.glob('**/index.html', recursive=True))
pages = [p for p in pages if not p.startswith('.git/') and not p.startswith('node_modules/')]

print(f"\n{'='*60}")
print(f"  TEAMZ LAB TOOLS — QA TEST SUITE")
print(f"  Testing {len(pages)} pages...")
print(f"{'='*60}\n")

for page in pages:
    issues = []
    with open(page, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # --- STRUCTURAL ---
    if '<!DOCTYPE' not in content[:50].upper() and '<!doctype' not in content[:50]:
        issues.append(('CRITICAL', 'Missing <!DOCTYPE html>'))

    if 'lang="' not in content[:500]:
        issues.append(('FAIL', 'Missing lang attribute'))

    if 'viewport' not in content:
        issues.append(('CRITICAL', 'Missing viewport meta'))

    if '<title>' not in content:
        issues.append(('CRITICAL', 'Missing <title> tag'))

    # Title length
    m = re.search(r'<title>([^<]*)</title>', content)
    if m:
        t = m.group(1)
        if len(t) > 60:
            issues.append(('WARN', f'Title too long ({len(t)} chars)'))
        if len(t) < 5:
            issues.append(('FAIL', f'Title too short ({len(t)} chars)'))

    # Meta description
    if 'name="description"' not in content:
        issues.append(('FAIL', 'Missing meta description'))
    else:
        dm = re.search(r'name="description"\s+content="([^"]*)"', content)
        if dm and len(dm.group(1)) > 155:
            issues.append(('WARN', f'Description too long ({len(dm.group(1))} chars)'))

    # H1
    if '<h1' not in content:
        issues.append(('CRITICAL', 'Missing <h1> tag'))

    # Canonical
    if 'rel="canonical"' not in content:
        issues.append(('FAIL', 'Missing canonical URL'))

    # OG tags
    if 'og:title' not in content:
        issues.append(('FAIL', 'Missing og:title'))
    if 'og:image' not in content:
        issues.append(('WARN', 'Missing og:image'))

    # --- DESIGN SYSTEM ---
    # Neon accent as text color
    accent_text = len(re.findall(r'[^-]color:\s*var\(--accent\)', content))
    if accent_text > 0:
        issues.append(('FAIL', f'Neon accent as text color ({accent_text}x) — unreadable'))

    # --- TOOL PAGE CHECKS (skip hub pages) ---
    parts = page.split('/')
    is_tool = len(parts) >= 3 and parts[-1] == 'index.html'

    if is_tool:
        if 'id="site-header"' not in content:
            issues.append(('FAIL', 'Missing site-header'))
        if 'id="site-footer"' not in content:
            issues.append(('FAIL', 'Missing site-footer'))
        if 'theme.js' not in content:
            issues.append(('FAIL', 'Missing theme.js'))
        if 'common.js' not in content:
            issues.append(('FAIL', 'Missing common.js'))
        if 'teamz-branding.css' not in content:
            issues.append(('FAIL', 'Missing branding CSS'))
        if 'tools.css' not in content:
            issues.append(('FAIL', 'Missing tools CSS'))
        if 'ad-slot' not in content:
            issues.append(('WARN', 'Missing ad-slot'))
        if 'id="breadcrumbs"' not in content:
            issues.append(('FAIL', 'Missing breadcrumbs'))
        if 'id="tool-faqs"' not in content and 'FAQS' not in content:
            issues.append(('WARN', 'Missing FAQs section'))
        if 'id="related-tools"' not in content and 'RELATED_TOOLS' not in content:
            issues.append(('WARN', 'Missing related tools'))

    # Skip redirect pages
    if 'http-equiv="refresh"' in content:
        passed.append(page)
        continue

    # Script tag balance — skip this check as JSON-LD and inline JS strings
    # cause too many false positives with naive counting

    # Classify
    crits = [i for i in issues if i[0] == 'CRITICAL']
    fls = [i for i in issues if i[0] == 'FAIL']
    wns = [i for i in issues if i[0] == 'WARN']

    if crits:
        critical.append((page, crits))
    if fls:
        fails.append((page, fls))
    if wns:
        warns.append((page, wns))
    if not issues:
        passed.append(page)

# --- RESULTS ---
total = len(pages)
print(f"{'='*60}")
print(f"  QA TEST RESULTS")
print(f"{'='*60}\n")
print(f"  Pages tested:   {total}")
print(f"  ✅ Passed:       {len(passed)}")
print(f"  ⚠️  Warnings:     {len(warns)}")
print(f"  ❌ Failures:     {len(fails)}")
print(f"  🚨 Critical:     {len(critical)}")
print()

if critical:
    print(f"  🚨 CRITICAL ISSUES ({len(critical)} pages):")
    for page, issues in critical:
        for _, msg in issues:
            print(f"    ✗ {page}: {msg}")
    print()

if fails:
    print(f"  ❌ FAILURES ({len(fails)} pages):")
    for page, issues in fails:
        for _, msg in issues:
            print(f"    • {page}: {msg}")
    print()

if warns and '--verbose' in sys.argv:
    print(f"  ⚠️  WARNINGS ({len(warns)} pages):")
    for page, issues in warns:
        for _, msg in issues:
            print(f"    • {page}: {msg}")
    print()

pass_rate = len(passed) * 100 // total if total > 0 else 0
print(f"  Pass rate: {pass_rate}% ({len(passed)} / {total})")
print()

if critical:
    print("  STATUS: 🚨 CRITICAL ISSUES FOUND")
elif fails:
    print("  STATUS: ❌ FAILURES FOUND")
elif warns:
    print("  STATUS: ⚠️  WARNINGS ONLY (non-blocking)")
else:
    print("  STATUS: ✅ ALL TESTS PASSED")
print()
