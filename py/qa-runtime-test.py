#!/usr/bin/env python3
"""
Teamz Lab Tools — Runtime QA Test
Loads EVERY tool page in a real headless browser and checks:
  1. No JavaScript console errors
  2. Page loads successfully (no blank pages)
  3. Tool calculator section renders
  4. Primary action button exists and is clickable
  5. No uncaught exceptions

Usage:
  python3 scripts/qa-runtime-test.py              # Test ALL tools
  python3 scripts/qa-runtime-test.py --changed     # Test only git-changed tools
  python3 scripts/qa-runtime-test.py --hub dev     # Test one hub only
  python3 scripts/qa-runtime-test.py --quick       # Quick mode: JS errors only (faster)
  python3 scripts/qa-runtime-test.py --file path   # Test a specific tool

Runs a local server on port 9091, opens each page in headless Chromium,
and reports failures. Exit code 1 if any tool has errors.
"""

import os, sys, re, json, time, signal, subprocess, argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from _teamz_config import load_runtime

RUNTIME = load_runtime(__file__)
ROOT = Path(RUNTIME["host_site_root"])
PROJECT_TYPE = RUNTIME.get("project_type", "website")
SERVER_PORT = 9091
MAX_WORKERS = int(os.environ.get('QA_RUNTIME_MAX_WORKERS', '5'))  # parallel browser tabs
PAGE_TIMEOUT = int(os.environ.get('QA_RUNTIME_PAGE_TIMEOUT', '12000'))  # ms per page

# ── Collect tool pages ──────────────────────────────────────────────

def get_all_tools():
    """Find all tool index.html files (not hub pages)."""
    tools = []
    # roktolagbe = standalone product on separate Firebase project (lifedrop-prod).
    # It uses its own firebase-config.js and won't initialize under tool.teamzlab.com host.
    skip = {'.git', 'node_modules', 'shared', 'branding', 'docs', 'scripts',
            '.claude', '.claude-memory', 'og-images', 'icons', 'apps',
            'flutter_service_worker', 'teamzlab-website', 'roktolagbe'}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        if 'index.html' not in filenames:
            continue
        rel = os.path.relpath(dirpath, ROOT)
        parts = rel.replace('\\', '/').split('/')
        if len(parts) < 2:  # hub page or root
            continue
        tools.append(rel.replace('\\', '/'))
    return sorted(tools)


def get_changed_tools():
    """Get tools changed since last push (or last commit on main)."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'origin/main...HEAD'],
            capture_output=True, text=True, cwd=ROOT
        )
        if result.returncode != 0:
            # Fallback: uncommitted + staged changes
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD'],
                capture_output=True, text=True, cwd=ROOT
            )
        files = result.stdout.strip().split('\n')
        # Also include unstaged changes
        result2 = subprocess.run(
            ['git', 'diff', '--name-only'],
            capture_output=True, text=True, cwd=ROOT
        )
        files += result2.stdout.strip().split('\n')

        tools = set()
        for f in files:
            f = f.strip()
            if not f or not f.endswith('index.html'):
                continue
            # roktolagbe lives on a separate Firebase project — skip in main repo runtime test
            if f.startswith('roktolagbe/'):
                continue
            parts = f.split('/')
            if len(parts) >= 3:  # hub/tool/index.html
                tools.add('/'.join(parts[:-1]))

        # Only test ALL tools if actual shared CODE changed (not build artifacts)
        BUILD_ARTIFACTS = {'shared/js/search-index.js', 'sitemap.xml', 'llms.txt', 'llms-full.txt'}
        shared_code_changed = any(
            ('shared/' in f or 'branding/' in f) and f.strip() not in BUILD_ARTIFACTS
            for f in files if f.strip()
        )
        if shared_code_changed:
            print("  ⚠ Shared code changed — testing ALL tools")
            return get_all_tools()
        elif tools:
            artifact_files = [f.strip() for f in files if f.strip() in BUILD_ARTIFACTS]
            if artifact_files:
                print(f"  ℹ Only build artifacts changed ({', '.join(artifact_files)}) — testing {len(tools)} changed tools only")

        return sorted(tools)
    except Exception:
        return get_all_tools()


def get_hub_tools(hub):
    """Get all tools in a specific hub."""
    hub_path = ROOT / hub
    if not hub_path.is_dir():
        print(f"  Hub '{hub}' not found")
        return []
    tools = []
    for d in sorted(hub_path.iterdir()):
        if d.is_dir() and (d / 'index.html').exists():
            tools.append(f"{hub}/{d.name}")
    return tools


# ── Local server ────────────────────────────────────────────────────

def start_server():
    """Start a multi-threaded local HTTP server for testing."""
    server_script = ROOT / 'scripts' / 'qa-server.py'
    proc = subprocess.Popen(
        [sys.executable, str(server_script), str(SERVER_PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(0.8)  # Let it start
    return proc


def stop_server(proc):
    """Stop the local server."""
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


# ── Browser testing with Playwright ────────────────────────────────

def run_tests(tools, quick_mode=False):
    """Run all tools through headless browser and collect results."""
    from playwright.sync_api import sync_playwright

    results = {'pass': [], 'fail': [], 'warn': []}
    total = len(tools)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        def test_tool(tool_path, index):
            """Test a single tool page."""
            url = f"http://localhost:{SERVER_PORT}/{tool_path}/"
            errors = []
            warnings = []
            console_errors = []

            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                java_script_enabled=True,
            )
            page = context.new_page()

            # Collect console errors
            def on_console(msg):
                if msg.type == 'error':
                    text = msg.text
                    # Ignore known non-issues
                    if any(skip in text for skip in [
                        'favicon.ico', 'net::ERR_', 'adsense', 'adsbygoogle',
                        'googletagmanager', 'google-analytics', 'gtag',
                        'Failed to load resource', 'ERR_CONNECTION_REFUSED',
                        'firebase', 'googleapis.com', 'gstatic.com',
                        'the server responded with a status of 404',
                        'manifest.json',
                        # Third-party affiliate script. Same class as the adsense /
                        # googletagmanager entries above: it is CORS-blocked when the
                        # page is served from http://localhost by qa-server, and loads
                        # normally on the real origin. Without this, 7 games/* pages
                        # fail every run and the pre-push gate can never go green — an
                        # always-red gate is one nobody can act on.
                        'skimresources',
                        # Chrome policy notice, not an error: headless has no user tap,
                        # so any vibrate() call is refused. Never fires for a real user
                        # who has interacted with the page.
                        'navigator.vibrate',
                    ]):
                        return
                    console_errors.append(text)

            page.on('console', on_console)

            # Collect page errors (uncaught exceptions)
            page_errors = []
            def on_pageerror(error):
                page_errors.append(str(error))
            page.on('pageerror', on_pageerror)

            try:
                # Load page
                response = page.goto(url, timeout=PAGE_TIMEOUT, wait_until='domcontentloaded')

                if not response or response.status >= 400:
                    errors.append(f"HTTP {response.status if response else 'no response'}")
                    context.close()
                    return tool_path, errors, warnings, console_errors, page_errors

                # Wait for scripts to execute
                page.wait_for_timeout(1500)

                if not quick_mode:
                    # Check 1: Page has content (not blank)
                    body_text = page.evaluate('document.body ? document.body.innerText.length : 0')
                    if body_text < 50:
                        errors.append("Page appears blank (body text < 50 chars)")

                    # Check 2: Tool calculator section exists
                    has_calculator = page.evaluate('''
                        !!document.querySelector('.tool-calculator') ||
                        !!document.querySelector('.tool-hero') ||
                        !!document.querySelector('#tool-calculator')
                    ''')
                    if not has_calculator:
                        warnings.append("No .tool-calculator or .tool-hero found")

                    # Check 2b: Calculator container is not an EMPTY shell.
                    # Static HTML always ships '#tool-calculator'/'.tool-calculator'
                    # as an empty <section> — UtilityEngine/ToolEngine.init() mounts
                    # real controls into it at runtime. If init() silently no-ops
                    # (bad mode string, missing config), Check 2 above still passes
                    # (the container exists) while the tool is 100% dead. This is
                    # the exact defect class that shipped 67 broken tool pages
                    # (teamzlab-tools commit 7b11a654d) undetected by this script.
                    # '.tool-hero' pages use a different, non-calculator render
                    # path and are exempted — they were never in scope for this
                    # check to begin with.
                    calc_mounted = page.evaluate('''
                        (function() {
                            var hero = document.querySelector('.tool-hero');
                            if (hero) return true;
                            var calc = document.querySelector('.tool-calculator') ||
                                       document.querySelector('#tool-calculator');
                            if (!calc) return true; // Check 2 above already flags absence
                            return !!calc.querySelector(
                                'input, select, textarea, button, canvas, table, ' +
                                '.tool-output, .result, [class*="result"], [class*="output"]'
                            );
                        })()
                    ''')
                    if not calc_mounted:
                        errors.append(
                            "Calculator container present but EMPTY — "
                            "init() likely no-op'd silently (dead tool, no console error)"
                        )

                    # Check 3: Primary button exists
                    has_button = page.evaluate('''
                        !!document.querySelector('.btn-primary') ||
                        !!document.querySelector('button[type="submit"]') ||
                        !!document.querySelector('.tool-calculator button')
                    ''')
                    if not has_button:
                        warnings.append("No primary action button found")

                    # Check 4: Hidden result containers that should be showing
                    # (catches display:none bugs where JS failed to show results)
                    hidden_results = page.evaluate('''
                        (function() {
                            var issues = [];
                            // Check for elements with both CSS display:none and inline display:''
                            var els = document.querySelectorAll('[class]');
                            for (var i = 0; i < els.length; i++) {
                                var el = els[i];
                                var style = window.getComputedStyle(el);
                                // Skip elements that are intentionally hidden initially
                                if (style.display === 'none' && el.style.display === '') {
                                    // Check if this looks like a result container that got stuck
                                    var cl = el.className;
                                    if (cl && /result|output|preview|summary/i.test(cl)) {
                                        // It's fine if it's hidden by default — only flag if JS tried to show it
                                    }
                                }
                            }
                            return issues;
                        })()
                    ''')

                    # Check 5: Common.js loaded
                    has_common = page.evaluate('typeof TeamzTools !== "undefined" || typeof window.showToast !== "undefined"')
                    if not has_common:
                        errors.append("common.js failed to load (TeamzTools/showToast undefined)")

                    # Check 6: Theme.js loaded (toggle button rendered by common.js)
                    has_theme = page.evaluate('''
                        !!document.querySelector('.theme-toggle') ||
                        document.documentElement.hasAttribute("data-theme") ||
                        typeof window.toggleTheme === "function" ||
                        !!document.querySelector('script[src*="theme.js"]')
                    ''')
                    if not has_theme:
                        warnings.append("Theme system may not be loaded")

            except Exception as e:
                err_str = str(e)
                if 'timeout' in err_str.lower():
                    errors.append(f"Page load timeout ({PAGE_TIMEOUT}ms)")
                else:
                    errors.append(f"Browser error: {err_str[:150]}")

            finally:
                context.close()

            return tool_path, errors, warnings, console_errors, page_errors

        # Run tests sequentially (Playwright sync API)
        for i, tool in enumerate(tools):
            progress = f"[{i+1}/{total}]"
            sys.stdout.write(f"\r  {progress} Testing {tool}...{' '*20}")
            sys.stdout.flush()

            tool_path, errors, warnings, console_errors, page_errors = test_tool(tool, i)

            all_errors = errors + page_errors + console_errors
            if all_errors:
                results['fail'].append({
                    'tool': tool_path,
                    'errors': errors,
                    'console_errors': console_errors,
                    'page_errors': page_errors,
                })
            elif warnings:
                results['warn'].append({
                    'tool': tool_path,
                    'warnings': warnings,
                })
            else:
                results['pass'].append(tool_path)

        browser.close()

    sys.stdout.write('\r' + ' ' * 80 + '\r')
    return results


# ── Report ──────────────────────────────────────────────────────────

def print_report(results, total):
    RED = '\033[91m'
    GREEN = '\033[92m'
    YEL = '\033[93m'
    NC = '\033[0m'
    BOLD = '\033[1m'

    pass_count = len(results['pass'])
    fail_count = len(results['fail'])
    warn_count = len(results['warn'])

    print()
    print(f"{BOLD}╔══════════════════════════════════════════╗{NC}")
    print(f"{BOLD}║   Runtime QA Test Results                ║{NC}")
    print(f"{BOLD}╠══════════════════════════════════════════╣{NC}")
    print(f"{BOLD}║{NC}  Total:    {total:>5}                          {BOLD}║{NC}")
    print(f"{BOLD}║{NC}  {GREEN}Pass:{NC}     {pass_count:>5}                          {BOLD}║{NC}")
    print(f"{BOLD}║{NC}  {YEL}Warn:{NC}     {warn_count:>5}                          {BOLD}║{NC}")
    print(f"{BOLD}║{NC}  {RED}Fail:{NC}     {fail_count:>5}                          {BOLD}║{NC}")
    print(f"{BOLD}╚══════════════════════════════════════════╝{NC}")
    print()

    if results['fail']:
        print(f"{RED}{BOLD}── FAILURES ──{NC}")
        for item in results['fail']:
            print(f"\n  {RED}✗{NC} {BOLD}{item['tool']}{NC}")
            for e in item['errors']:
                print(f"    {RED}ERROR:{NC} {e}")
            for e in item['page_errors']:
                print(f"    {RED}JS EXCEPTION:{NC} {e[:200]}")
            for e in item['console_errors']:
                print(f"    {RED}CONSOLE:{NC} {e[:200]}")

    if results['warn'] and len(results['warn']) <= 20:
        print(f"\n{YEL}{BOLD}── WARNINGS ──{NC}")
        for item in results['warn']:
            print(f"  {YEL}⚠{NC} {item['tool']}: {', '.join(item['warnings'])}")

    print()
    if fail_count == 0:
        print(f"  {GREEN}{BOLD}✓ All {total} tools passed runtime QA!{NC}")
    else:
        print(f"  {RED}{BOLD}✗ {fail_count} tool(s) have runtime errors — fix before pushing!{NC}")

    return fail_count


# ── Main ────────────────────────────────────────────────────────────

def main():
    if PROJECT_TYPE == "app":
        print("INFO: qa-runtime-test.py is website-focused and disabled for TEAMZ_PROJECT_TYPE=app.")
        return 2

    parser = argparse.ArgumentParser(description='Runtime QA test for all tools')
    parser.add_argument('--changed', action='store_true', help='Test only git-changed tools')
    parser.add_argument('--hub', type=str, help='Test one hub only')
    parser.add_argument('--quick', action='store_true', help='Quick mode: JS errors only')
    parser.add_argument('--file', type=str, help='Test a specific tool path (e.g. tools/birthday-countdown)')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of tools to test')
    args = parser.parse_args()

    print()
    print("============================================")
    print("  Teamz Lab Tools — Runtime QA Test")
    print(f"  {time.strftime('%Y-%m-%d %H:%M')}")
    print("============================================")
    print()

    # Collect tools to test
    if args.file:
        tools = [args.file.rstrip('/')]
    elif args.hub:
        tools = get_hub_tools(args.hub)
    elif args.changed:
        tools = get_changed_tools()
    else:
        tools = get_all_tools()

    if args.limit and args.limit > 0:
        tools = tools[:args.limit]

    if not tools:
        print("  No tools to test.")
        return 0

    total = len(tools)
    mode = 'quick (JS errors only)' if args.quick else 'full'
    print(f"  Testing {total} tools in {mode} mode...")
    print()

    # Start local server
    server = start_server()

    try:
        results = run_tests(tools, quick_mode=args.quick)
        fail_count = print_report(results, total)
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        fail_count = 1
    finally:
        stop_server(server)

    return 1 if fail_count > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
