#!/usr/bin/env python3
"""
Request search engines to index your pages.

Uses 3 strategies:
  1. Google URL Inspection API — checks status, triggers crawl awareness
  2. IndexNow — instant indexing for Bing, DuckDuckGo, Yandex, Seznam
  3. Sitemap ping — tells Google & Bing to re-process sitemap

Usage:
  python3 build-request-indexing.py                  # Index top 30 pages
  python3 build-request-indexing.py --all            # Index ALL pages from sitemap
  python3 build-request-indexing.py --check          # Check indexing status only
  python3 build-request-indexing.py --url URL        # Index a specific URL
  python3 build-request-indexing.py --indexnow-only  # Submit only to IndexNow
  python3 build-request-indexing.py --ping-only      # Ping sitemap endpoints only
"""
import json
import os
import sys
import ssl
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

SITE_URL = 'https://tool.teamzlab.com'
SITE_URL_SC = 'https://tool.teamzlab.com/'  # Search Console property format (trailing slash required)
SC_TOKEN_FILE = os.path.expanduser('~/.config/teamzlab/search-console-token.json')
INDEXNOW_KEY = 'teamzlab-indexnow-key'  # Will create key file on site
SITEMAP_URL = f'{SITE_URL}/sitemap.xml'

# SSL context
ctx = ssl.create_default_context()

# ─── Top pages by Search Console impressions (2026-03-24) ─────────────
TOP_PAGES = [
    '/',
    '/diagnostic/dns-leak-test/',
    '/design/logo-text-maker/',
    '/bd/electricity-bill-calculator/',
    '/career/resume-job-match-checker/',
    '/career/resume-keyword-scanner/',
    '/tools/number-typing-practice/',
    '/football/football-salary-calculator/',
    '/text/passive-voice-checker/',
    '/weather/wind-chill-calculator/',
    '/ai/resume-summary-generator/',
    '/gaming/dpi-calculator/',
    '/au/pr-points-calculator/',
    '/ramadan/eid-salami-qr-card-generator/',
    '/cricket/net-run-rate-calculator/',
    '/accessibility/ada-compliance-checker/',
    '/cricket/over-to-balls-converter/',
    '/bd/nagad-charge-calculator/',
    '/bd/bkash-charge-calculator/',
    '/ai/headline-generator/',
    '/accessibility/wcag-accessibility-checklist/',
    '/bd/cgpa-calculator/',
    '/cricket/economy-rate-calculator/',
    '/cricket/dls-calculator/',
    '/ramadan/eid-salami-scratch-challenge/',
    '/bd/freelancer-tax-calculator/',
    '/au/student-visa-cost-calculator/',
    '/football/ucl-group-stage-simulator/',
    '/health/screen-distance-checker/',
    '/health/time-blindness-calculator/',
]


def refresh_token():
    """Force-refresh the OAuth token and return new access token."""
    if not os.path.exists(SC_TOKEN_FILE):
        return None

    with open(SC_TOKEN_FILE) as f:
        td = json.load(f)

    refresh = td.get('refresh_token')
    client_id = td.get('client_id')
    client_secret = td.get('client_secret')

    if not all([refresh, client_id, client_secret]):
        return None

    try:
        data = urllib.parse.urlencode({
            'refresh_token': refresh,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token'
        }).encode()
        req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            new_token = json.loads(r.read())['access_token']
            td['token'] = new_token
            with open(SC_TOKEN_FILE, 'w') as f:
                json.dump(td, f, indent=2)
            return new_token
    except Exception as e:
        print(f'  WARN: Token refresh failed: {e}')
        return None


def get_sc_token():
    """Get a valid Search Console access token (auto-refreshes)."""
    if not os.path.exists(SC_TOKEN_FILE):
        print(f'  ERROR: No Search Console token found at {SC_TOKEN_FILE}')
        print(f'  Run: python3 scripts/build-search-console-auth.py')
        return None

    with open(SC_TOKEN_FILE) as f:
        td = json.load(f)

    token = td.get('token', '')

    # Test if token works
    req = urllib.request.Request(
        'https://searchconsole.googleapis.com/v1/sites',
        headers={'Authorization': f'Bearer {token}', 'User-Agent': 'TeamzLab/1.0'}
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10):
            return token
    except:
        pass

    # Token expired — refresh it
    new_token = refresh_token()
    if new_token:
        return new_token

    print('  ERROR: Token expired and refresh failed. Re-auth needed.')
    print('  Run: python3 scripts/build-search-console-auth.py')
    return None


def inspect_url(token, url):
    """Use Google URL Inspection API to check indexing status."""
    body = json.dumps({
        'inspectionUrl': url,
        'siteUrl': SITE_URL_SC
    }).encode()
    req = urllib.request.Request(
        'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect',
        data=body,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'x-goog-user-project': 'teamzlab-tools',
            'User-Agent': 'TeamzLab/1.0'
        }
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        try:
            err_msg = json.loads(err_body).get('error', {}).get('message', '')[:80]
        except:
            err_msg = str(e.code)
        return {'error': err_msg}
    except Exception as e:
        return {'error': str(e)[:80]}


def submit_indexnow(urls):
    """Submit URLs to IndexNow (Bing, DuckDuckGo, Yandex, Seznam)."""
    print('\n' + '=' * 66)
    print('  INDEXNOW — Bing, DuckDuckGo, Yandex, Seznam')
    print('=' * 66)

    # IndexNow accepts batch of up to 10,000 URLs
    body = json.dumps({
        'host': 'tool.teamzlab.com',
        'key': INDEXNOW_KEY,
        'keyLocation': f'{SITE_URL}/{INDEXNOW_KEY}.txt',
        'urlList': urls
    }).encode()

    engines = [
        ('Bing', 'https://www.bing.com/indexnow'),
        ('Yandex', 'https://yandex.com/indexnow'),
    ]

    for name, endpoint in engines:
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={'Content-Type': 'application/json', 'User-Agent': 'TeamzLab/1.0'}
        )
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                status = r.status
                if status in (200, 202):
                    print(f'  OK  {name}: {len(urls)} URLs submitted (HTTP {status})')
                else:
                    print(f'  ??  {name}: HTTP {status}')
        except urllib.error.HTTPError as e:
            if e.code == 202:
                print(f'  OK  {name}: {len(urls)} URLs accepted (HTTP 202)')
            elif e.code == 422:
                print(f'  !!  {name}: Key file not found at {SITE_URL}/{INDEXNOW_KEY}.txt')
                print(f'       Create it with: echo "{INDEXNOW_KEY}" > {INDEXNOW_KEY}.txt')
            else:
                print(f'  ERR {name}: HTTP {e.code}')
        except Exception as e:
            print(f'  ERR {name}: {str(e)[:60]}')


def ping_sitemaps():
    """Ping Google and Bing to re-process sitemap."""
    print('\n' + '=' * 66)
    print('  SITEMAP PING — Google & Bing')
    print('=' * 66)

    encoded = urllib.parse.quote(SITEMAP_URL, safe='')
    pings = [
        ('Google', f'https://www.google.com/ping?sitemap={encoded}'),
        ('Bing', f'https://www.bing.com/ping?sitemap={encoded}'),
    ]

    for name, url in pings:
        req = urllib.request.Request(url, headers={'User-Agent': 'TeamzLab/1.0'})
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
                print(f'  OK  {name}: Sitemap ping sent (HTTP {r.status})')
        except urllib.error.HTTPError as e:
            # Google returns various codes but still processes the ping
            print(f'  OK  {name}: Sitemap ping sent (HTTP {e.code})')
        except Exception as e:
            print(f'  ERR {name}: {str(e)[:60]}')


def get_all_urls_from_sitemap():
    """Parse sitemap.xml to get all URLs."""
    sitemap_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sitemap.xml')
    if not os.path.exists(sitemap_path):
        print(f'  ERROR: sitemap.xml not found at {sitemap_path}')
        return []
    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = []
    for url_elem in root.findall('.//ns:url/ns:loc', ns):
        urls.append(url_elem.text)
    return urls


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__.strip())
        return

    mode = '--top'
    check_only = '--check' in sys.argv
    indexnow_only = '--indexnow-only' in sys.argv
    ping_only = '--ping-only' in sys.argv
    specific_url = None

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--all':
            mode = '--all'
        elif arg == '--check':
            pass  # handled above
        elif arg == '--url' and i < len(sys.argv) - 1:
            mode = '--url'
            specific_url = sys.argv[i + 1]
        elif arg.startswith('http') and mode != '--url':
            mode = '--url'
            specific_url = arg

    # Determine which URLs to process
    if mode == '--url' and specific_url:
        full_urls = [specific_url if specific_url.startswith('http') else f'{SITE_URL}{specific_url}']
    elif mode == '--all':
        full_urls = get_all_urls_from_sitemap()
        if not full_urls:
            return
        print(f'  Found {len(full_urls)} URLs in sitemap.xml')
    else:
        full_urls = [f'{SITE_URL}{p}' for p in TOP_PAGES]

    print('=' * 66)
    print(f'  INDEXING REQUEST — {len(full_urls)} pages')
    print('=' * 66)

    if indexnow_only:
        submit_indexnow(full_urls)
        return

    if ping_only:
        ping_sitemaps()
        return

    # ─── Step 1: Google URL Inspection ───────────────────────────────
    token = get_sc_token()
    if token:
        print('\n' + '=' * 66)
        print('  GOOGLE URL INSPECTION API')
        print('=' * 66)

        indexed = 0
        not_indexed = 0
        errors = 0
        need_manual = []
        indexed_urls = []
        not_indexed_details = []
        import time

        for i, url in enumerate(full_urls):
            # Progress indicator every 100 URLs
            if len(full_urls) > 50 and i > 0 and i % 100 == 0:
                print(f'  ... checked {i}/{len(full_urls)} ({indexed} indexed, {not_indexed} not indexed, {errors} errors)', flush=True)

            result = inspect_url(token, url)

            if 'error' in result:
                err_msg = result['error']

                # Auto-refresh on auth errors
                if 'authentication' in err_msg.lower() or 'credentials' in err_msg.lower() or 'OAuth' in err_msg:
                    print(f'  ... token expired at URL #{i+1}, refreshing...')
                    new_token = refresh_token()
                    if new_token:
                        token = new_token
                        print(f'  ... token refreshed, retrying...')
                        # Retry this URL with new token
                        result = inspect_url(token, url)
                        if 'error' not in result:
                            # Fall through to normal processing below
                            pass
                        else:
                            print(f'  ERR {url}')
                            print(f'       {result["error"]}')
                            errors += 1
                            need_manual.append(url)
                            continue
                    else:
                        print(f'  ERR Token refresh failed. Remaining {len(full_urls) - i} URLs skipped.')
                        errors += len(full_urls) - i
                        need_manual.extend(full_urls[i:])
                        break

                # Rate limit — wait and retry
                elif 'rate' in err_msg.lower() or '429' in err_msg:
                    print(f'  ... rate limited at URL #{i+1}, waiting 60s...')
                    time.sleep(60)
                    result = inspect_url(token, url)
                    if 'error' in result:
                        print(f'  ERR {url}')
                        print(f'       {result["error"]}')
                        errors += 1
                        need_manual.append(url)
                        continue

                # Timeout — retry once
                elif 'timed out' in err_msg.lower() or 'timeout' in err_msg.lower():
                    time.sleep(2)
                    result = inspect_url(token, url)
                    if 'error' in result:
                        errors += 1
                        need_manual.append(url)
                        continue

                else:
                    print(f'  ERR {url}')
                    print(f'       {err_msg}')
                    errors += 1
                    need_manual.append(url)
                    continue

            # Process successful result
            inspection = result.get('inspectionResult', {})
            index_status = inspection.get('indexStatusResult', {})
            coverage = index_status.get('coverageState', 'UNKNOWN')
            verdict = index_status.get('verdict', 'UNKNOWN')
            crawled = index_status.get('lastCrawlTime', 'never')

            short_url = url.replace(SITE_URL, '')

            if verdict == 'PASS':
                print(f'  IDX {short_url}  (crawled: {crawled[:10]})')
                indexed += 1
                indexed_urls.append(short_url)
            elif coverage in ('Submitted and indexed', 'Indexed, not submitted in sitemap'):
                print(f'  IDX {short_url}  ({coverage})')
                indexed += 1
                indexed_urls.append(short_url)
            else:
                status_short = coverage[:50] if coverage else verdict
                print(f'  --- {short_url}  ({status_short})')
                not_indexed += 1
                not_indexed_details.append((short_url, status_short))
                need_manual.append(url)

        total_checked = indexed + not_indexed + errors
        print(f'\n  Summary: {indexed} indexed, {not_indexed} not indexed, {errors} errors (of {total_checked} checked)')

        if need_manual:
            print(f'\n  {len(need_manual)} pages need attention:')
            print(f'  Go to: https://search.google.com/search-console/inspect?resource_id={urllib.parse.quote(SITE_URL + "/", safe="")}')

        # ─── Save report to file ────────────────────────────────────
        report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'indexing-report.md')
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        from datetime import datetime
        with open(report_path, 'w') as f:
            f.write(f'# Indexing Report — {datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n')
            f.write(f'Total pages: {len(full_urls)}\n')
            f.write(f'Checked: {total_checked}\n')
            f.write(f'Indexed: {indexed} ({indexed*100//max(total_checked,1)}%)\n')
            f.write(f'Not indexed: {not_indexed}\n')
            f.write(f'Errors: {errors}\n\n')

            if not_indexed_details:
                f.write('## Not Indexed Pages\n\n')
                f.write('| Page | Reason |\n|---|---|\n')
                for page, reason in not_indexed_details:
                    f.write(f'| {page} | {reason} |\n')
                f.write('\n')

            if indexed_urls:
                f.write(f'## Indexed Pages ({indexed})\n\n')
                for page in indexed_urls:
                    f.write(f'- {page}\n')

        print(f'\n  Report saved: docs/indexing-report.md')
    else:
        print('\n  Skipping Google URL Inspection (no token)')
        need_manual = full_urls

    if check_only:
        return

    # ─── Step 2: IndexNow (Bing, Yandex, DuckDuckGo) ────────────────
    submit_indexnow(full_urls)

    # ─── Step 3: Sitemap ping ────────────────────────────────────────
    ping_sitemaps()

    # ─── Summary ─────────────────────────────────────────────────────
    print('\n' + '=' * 66)
    print('  WHAT HAPPENS NEXT')
    print('=' * 66)
    print('  Bing/Yandex: Pages should be indexed within hours-days')
    print('  Google:      URL Inspection triggers crawl awareness.')
    print('               For fastest results, also do manual Request Indexing')
    print('               for your top 10 pages in Search Console UI.')
    print()
    if need_manual:
        print(f'  Quick link to inspect URLs:')
        print(f'  https://search.google.com/search-console/inspect?resource_id={urllib.parse.quote(SITE_URL + "/", safe="")}')
    print()


if __name__ == '__main__':
    main()
