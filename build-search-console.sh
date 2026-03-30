#!/bin/bash
# =============================================================
#  Teamz Lab Tools — Search Console Data Pull
#  Usage: ./build-search-console.sh [--status|--queries|--pages|--opportunities|--all]
#  Requires: python3 + google API libs + OAuth token
#  Setup: see docs/search-console-setup.md
# =============================================================

set -e
cd "$(dirname "$0")"

TOKEN_FILE="$HOME/.config/teamzlab/search-console-token.json"
SITE_URL="https://tool.teamzlab.com/"

# Check dependencies
if ! python3 -c "import requests" 2>/dev/null; then
  echo "ERROR: Missing Python dependencies. Run:"
  echo "  pip3 install --break-system-packages google-auth google-auth-oauthlib requests"
  exit 1
fi

# Check token
if [ ! -f "$TOKEN_FILE" ]; then
  echo "ERROR: No Search Console token found."
  echo "Run: python3 build-search-console-auth.py"
  echo "See: docs/search-console-setup.md"
  exit 1
fi

MODE="${1:---all}"

python3 - "$MODE" "$TOKEN_FILE" "$SITE_URL" << 'PYEOF'
import json, sys, requests
from datetime import datetime, timedelta
from requests.exceptions import RequestException
from urllib.parse import quote

MODE = sys.argv[1]
TOKEN_FILE = sys.argv[2]
SITE_URL = sys.argv[3]
ENCODED_SITE = quote(SITE_URL, safe='')

with open(TOKEN_FILE) as f:
    token_data = json.load(f)

def fatal_api_error(message, exc=None):
    if exc is None:
        print(f"ERROR: {message}")
    else:
        print(f"ERROR: {message}: {exc}")
    sys.exit(1)

# Refresh token if needed
def get_fresh_token():
    """Try existing token, refresh if expired."""
    token = token_data.get('token', '')
    # Test token
    try:
        r = requests.get(
            'https://searchconsole.googleapis.com/webmasters/v3/sites',
            headers={'Authorization': f'Bearer {token}', 'x-goog-user-project': 'teamzlab-tools'},
            timeout=20,
        )
    except RequestException as exc:
        fatal_api_error("Search Console API unreachable", exc)
    if r.status_code == 200:
        return token
    # Refresh
    refresh = token_data.get('refresh_token')
    if not refresh:
        print("ERROR: Token expired. Re-run: python3 build-search-console-auth.py")
        sys.exit(1)
    try:
        rr = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': token_data['client_id'],
            'client_secret': token_data['client_secret'],
            'refresh_token': refresh,
            'grant_type': 'refresh_token'
        }, timeout=20)
    except RequestException as exc:
        fatal_api_error("Token refresh request failed", exc)
    if rr.status_code == 200:
        new_token = rr.json()['access_token']
        token_data['token'] = new_token
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        return new_token
    print("ERROR: Token refresh failed. Re-run: python3 build-search-console-auth.py")
    sys.exit(1)

token = get_fresh_token()
headers = {
    'Authorization': f'Bearer {token}',
    'x-goog-user-project': 'teamzlab-tools',
    'Content-Type': 'application/json'
}
API_BASE = f'https://searchconsole.googleapis.com/webmasters/v3/sites/{ENCODED_SITE}'

end_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
start_date_7d = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
start_date_30d = (datetime.now() - timedelta(days=33)).strftime('%Y-%m-%d')
# For decline detection: compare recent 14 days vs prior 14 days
recent_end = end_date
recent_start = (datetime.now() - timedelta(days=17)).strftime('%Y-%m-%d')
prior_end = (datetime.now() - timedelta(days=18)).strftime('%Y-%m-%d')
prior_start = (datetime.now() - timedelta(days=32)).strftime('%Y-%m-%d')

def query_search(dimensions, row_limit=50, start=start_date, end=end_date, filters=None):
    payload = {
        'startDate': start, 'endDate': end,
        'dimensions': dimensions, 'rowLimit': row_limit
    }
    if filters:
        payload['dimensionFilterGroups'] = [{'filters': filters}]
    try:
        r = requests.post(f'{API_BASE}/searchAnalytics/query', headers=headers, json=payload, timeout=30)
    except RequestException as exc:
        print(f"ERROR: searchAnalytics query failed: {exc}")
        return []
    if r.status_code != 200:
        return []
    return r.json().get('rows', [])

print("=" * 70)
print("  SEARCH CONSOLE REPORT — tool.teamzlab.com")
print(f"  Period: {start_date} to {end_date}")
print("=" * 70)

# --- Indexing Status ---
if MODE in ('--status', '--all'):
    print("\n📊 INDEXING STATUS")
    print("-" * 50)

    # 1) Sitemap submission info
    try:
        r = requests.get(f'{API_BASE}/sitemaps', headers=headers, timeout=20)
        sitemaps = r.json() if r.status_code == 200 else {}
    except RequestException as exc:
        print(f"  ERROR: Sitemap status request failed: {exc}")
        sitemaps = {}
    sitemap_submitted = 0
    if 'sitemap' in sitemaps:
        for s in sitemaps['sitemap']:
            contents = s.get('contents', [{}])[0]
            sitemap_submitted = contents.get('submitted', 0)
            print(f"  Sitemap: {s.get('path','?')}")
            print(f"  Submitted URLs: {sitemap_submitted}")
            print(f"  Last downloaded: {s.get('lastDownloaded','?')}")
    else:
        print("  No sitemaps found")

    # 2) Count pages with search presence (impressions > 0 = definitely indexed)
    print()
    all_pages_rows = query_search(['page'], row_limit=2000, start=start_date)
    pages_with_presence = len(all_pages_rows)
    total_page_clicks = sum(r.get('clicks', 0) for r in all_pages_rows)
    total_page_impr = sum(r.get('impressions', 0) for r in all_pages_rows)
    print(f"  Pages with search presence: {pages_with_presence}")
    print(f"  Total clicks (90 days):     {total_page_clicks}")
    print(f"  Total impressions (90 days): {total_page_impr}")

    # 3) Sample URL Inspection API for real indexing verdicts
    INSPECT_URL = 'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect'
    import random, math

    # Get sample URLs from sitemap.xml if available
    sample_urls = []
    SAMPLE_SIZE = 20  # Balance between accuracy and speed (~20 sec)
    import os, re as regex
    # Script is in scripts/, sitemap.xml is in project root
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    for candidate in [
        os.path.join(script_dir, '..', 'sitemap.xml'),
        os.path.join(script_dir, 'sitemap.xml'),
        'sitemap.xml',
    ]:
        if os.path.exists(candidate):
            sitemap_path = candidate
            break
    else:
        sitemap_path = None
    if sitemap_path:
        with open(sitemap_path) as sf:
            sitemap_content = sf.read()
        all_urls = regex.findall(r'<loc>(https://tool\.teamzlab\.com/[^<]+)</loc>', sitemap_content)
        if len(all_urls) > SAMPLE_SIZE:
            sample_urls = random.sample(all_urls, SAMPLE_SIZE)
        else:
            sample_urls = all_urls

    if sample_urls:
        indexed_count = 0
        not_indexed_count = 0
        errors = 0
        not_indexed_reasons = {}
        for url in sample_urls:
            try:
                ir = requests.post(INSPECT_URL, headers=headers, json={
                    'inspectionUrl': url,
                    'siteUrl': SITE_URL
                }, timeout=30)
                if ir.status_code == 200:
                    result = ir.json().get('inspectionResult', {})
                    index_status = result.get('indexStatusResult', {})
                    verdict = index_status.get('verdict', 'UNKNOWN')
                    if verdict == 'PASS':
                        indexed_count += 1
                    else:
                        not_indexed_count += 1
                        reason = index_status.get('indexingState', verdict)
                        not_indexed_reasons[reason] = not_indexed_reasons.get(reason, 0) + 1
                elif ir.status_code == 429:
                    # Rate limited — stop sampling
                    break
                else:
                    errors += 1
            except Exception:
                errors += 1

        total_sampled = indexed_count + not_indexed_count + errors
        if total_sampled > 0:
            pct = indexed_count / (indexed_count + not_indexed_count) * 100 if (indexed_count + not_indexed_count) > 0 else 0
            total_pages = int(sitemap_submitted) if sitemap_submitted else len(all_urls)
            estimated_indexed = int(total_pages * pct / 100) if total_pages else '?'
            print(f"\n  URL Inspection (sampled {total_sampled} of {total_pages} pages):")
            print(f"    Indexed:     {indexed_count}/{total_sampled} ({pct:.0f}%)")
            print(f"    Not indexed: {not_indexed_count}/{total_sampled}")
            if errors:
                print(f"    Errors:      {errors}")
            print(f"    Estimated total indexed: ~{estimated_indexed} / {total_pages}")
            if not_indexed_reasons:
                print(f"    Not-indexed reasons:")
                for reason, count in sorted(not_indexed_reasons.items(), key=lambda x: -x[1]):
                    print(f"      {reason}: {count}")
    else:
        print("\n  (Could not read sitemap.xml for URL inspection sampling)")

# --- Top Queries ---
if MODE in ('--queries', '--all'):
    print("\n🔍 TOP SEARCH QUERIES (Last 90 days)")
    print("-" * 90)
    rows = query_search(['query'], 100)
    if rows:
        # Sort by impressions descending to show highest-visibility queries first
        rows.sort(key=lambda r: r.get('impressions', 0), reverse=True)
        rows = rows[:30]
        print(f"  {'Keyword':<45} {'Clicks':>7} {'Impr':>8} {'CTR':>7} {'Pos':>6}")
        print("  " + "-" * 75)
        total_clicks = 0
        total_impr = 0
        for row in rows:
            q = row['keys'][0][:45]
            c = row.get('clicks', 0)
            i = row.get('impressions', 0)
            ctr = row.get('ctr', 0) * 100
            pos = row.get('position', 0)
            total_clicks += c
            total_impr += i
            print(f"  {q:<45} {c:>7} {i:>8} {ctr:>6.1f}% {pos:>5.1f}")
        print(f"\n  Total: {total_clicks} clicks, {total_impr} impressions")
    else:
        print("  No search query data yet (site may not be indexed)")

# --- Top Pages ---
if MODE in ('--pages', '--all'):
    print("\n📄 TOP PAGES (Last 90 days)")
    print("-" * 90)
    rows = query_search(['page'], 100)
    if rows:
        print(f"  {'Page':<55} {'Clicks':>7} {'Impr':>8} {'Pos':>6}")
        print("  " + "-" * 78)
        for row in rows:
            page = row['keys'][0].replace('https://tool.teamzlab.com', '')[:55]
            c = row.get('clicks', 0)
            i = row.get('impressions', 0)
            pos = row.get('position', 0)
            print(f"  {page:<55} {c:>7} {i:>8} {pos:>5.1f}")
    else:
        print("  No page data yet (site may not be indexed)")

# --- Device breakdown ---
if MODE in ('--all',):
    print("\n📱 DEVICE BREAKDOWN")
    print("-" * 50)
    rows = query_search(['device'])
    if rows:
        for row in rows:
            device = row['keys'][0]
            c = row.get('clicks', 0)
            i = row.get('impressions', 0)
            print(f"  {device:<15} {c:>7} clicks  {i:>8} impressions")
    else:
        print("  No device data yet")

# --- Country breakdown ---
if MODE in ('--all',):
    print("\n🌍 TOP COUNTRIES")
    print("-" * 50)
    rows = query_search(['country'], 15)
    if rows:
        for row in rows:
            country = row['keys'][0]
            c = row.get('clicks', 0)
            i = row.get('impressions', 0)
            print(f"  {country:<10} {c:>7} clicks  {i:>8} impressions")
    else:
        print("  No country data yet")

# --- OPPORTUNITIES: CTR Quick Wins (ranking #4-10 but low CTR) ---
if MODE in ('--opportunities', '--all'):
    print("\n" + "=" * 70)
    print("  OPPORTUNITIES ANALYZER")
    print("=" * 70)

    # 1) CTR Quick Wins — pages ranking #4-10 with below-average CTR
    print("\n🎯 CTR QUICK WINS (Ranking #4-10, Low CTR — Improve Title/Description)")
    print("-" * 90)
    rows = query_search(['query', 'page'], row_limit=500, start=start_date_30d)
    ctr_wins = []
    for row in rows:
        pos = row.get('position', 0)
        ctr = row.get('ctr', 0)
        impr = row.get('impressions', 0)
        clicks = row.get('clicks', 0)
        if 4 <= pos <= 10 and impr >= 10:
            # Expected CTR by position (industry averages)
            expected_ctr = {4: 0.06, 5: 0.04, 6: 0.03, 7: 0.025, 8: 0.02, 9: 0.018, 10: 0.015}
            exp = expected_ctr.get(round(pos), 0.03)
            if ctr < exp:
                potential_clicks = int(impr * exp) - clicks
                ctr_wins.append({
                    'query': row['keys'][0],
                    'page': row['keys'][1].replace('https://tool.teamzlab.com', ''),
                    'pos': pos, 'ctr': ctr, 'impr': impr, 'clicks': clicks,
                    'expected_ctr': exp, 'potential': potential_clicks
                })
    ctr_wins.sort(key=lambda x: x['potential'], reverse=True)
    if ctr_wins[:15]:
        print(f"  {'Query':<35} {'Page':<30} {'Pos':>4} {'CTR':>6} {'Exp':>6} {'+Clicks':>8}")
        print("  " + "-" * 91)
        total_potential = 0
        for w in ctr_wins[:15]:
            q = w['query'][:35]
            p = w['page'][:30]
            total_potential += w['potential']
            print(f"  {q:<35} {p:<30} {w['pos']:>4.1f} {w['ctr']*100:>5.1f}% {w['expected_ctr']*100:>5.1f}% {w['potential']:>+7}")
        print(f"\n  Total potential: +{total_potential} clicks/month by optimizing titles & descriptions")
        print("  ACTION: Rewrite <title> and <meta description> for these pages to be more compelling")
    else:
        print("  No CTR optimization opportunities found (or not enough data yet)")

    # 2) Striking Distance — pages ranking #11-20 (page 2, almost page 1)
    print("\n🏃 STRIKING DISTANCE (Ranking #11-20 — Small Push = Page 1)")
    print("-" * 90)
    striking = []
    for row in rows:
        pos = row.get('position', 0)
        impr = row.get('impressions', 0)
        if 11 <= pos <= 20 and impr >= 5:
            striking.append({
                'query': row['keys'][0],
                'page': row['keys'][1].replace('https://tool.teamzlab.com', ''),
                'pos': pos, 'impr': impr, 'clicks': row.get('clicks', 0)
            })
    striking.sort(key=lambda x: x['impr'], reverse=True)
    if striking[:15]:
        print(f"  {'Query':<40} {'Page':<30} {'Pos':>4} {'Impr':>7}")
        print("  " + "-" * 83)
        for s in striking[:15]:
            q = s['query'][:40]
            p = s['page'][:30]
            print(f"  {q:<40} {p:<30} {s['pos']:>4.1f} {s['impr']:>7}")
        print(f"\n  ACTION: Add more content, internal links, or backlinks to push these to page 1")
        print("  TIP: Add the query as an H2 heading, expand FAQ section, add internal links from related tools")
    else:
        print("  No striking distance pages found (or not enough data yet)")

    # 3) Declining Pages — compare recent 14 days vs prior 14 days
    print("\n📉 DECLINING PAGES (Losing Clicks — Act Before They Drop Further)")
    print("-" * 90)
    recent_rows = query_search(['page'], row_limit=200, start=recent_start, end=recent_end)
    prior_rows = query_search(['page'], row_limit=200, start=prior_start, end=prior_end)
    recent_map = {}
    for row in recent_rows:
        page = row['keys'][0].replace('https://tool.teamzlab.com', '')
        recent_map[page] = {
            'clicks': row.get('clicks', 0),
            'impr': row.get('impressions', 0),
            'pos': row.get('position', 0)
        }
    declines = []
    for row in prior_rows:
        page = row['keys'][0].replace('https://tool.teamzlab.com', '')
        prior_clicks = row.get('clicks', 0)
        prior_impr = row.get('impressions', 0)
        prior_pos = row.get('position', 0)
        recent = recent_map.get(page, {'clicks': 0, 'impr': 0, 'pos': 0})
        click_change = recent['clicks'] - prior_clicks
        impr_change = recent['impr'] - prior_impr
        pos_change = recent['pos'] - prior_pos  # positive = worse
        if prior_clicks >= 3 and (click_change < -2 or (prior_impr >= 10 and impr_change < -5)):
            declines.append({
                'page': page, 'prior_clicks': prior_clicks,
                'recent_clicks': recent['clicks'], 'click_change': click_change,
                'prior_impr': prior_impr, 'recent_impr': recent['impr'],
                'impr_change': impr_change, 'pos_change': pos_change
            })
    declines.sort(key=lambda x: x['click_change'])
    if declines[:10]:
        print(f"  {'Page':<45} {'Clicks':>13} {'Impr':>13} {'Pos':>8}")
        print(f"  {'':<45} {'Prior>Now':>13} {'Prior>Now':>13} {'Change':>8}")
        print("  " + "-" * 81)
        for d in declines[:10]:
            p = d['page'][:45]
            cc = f"{d['prior_clicks']}>{d['recent_clicks']}"
            ic = f"{d['prior_impr']}>{d['recent_impr']}"
            pc = f"{d['pos_change']:+.1f}" if d['pos_change'] else "="
            print(f"  {p:<45} {cc:>13} {ic:>13} {pc:>8}")
        print(f"\n  ACTION: Check these pages for content staleness, broken features, or algorithm changes")
        print("  TIP: Update data, add fresh content, check if competitors launched similar tools")
    else:
        print("  No significant declines detected (good news!)")

    # 4) High-Impression Zero-Click Queries (brand awareness but no traffic)
    print("\n👀 HIGH IMPRESSIONS, ZERO CLICKS (Visible But Not Clicked)")
    print("-" * 90)
    zero_click = []
    for row in rows:
        impr = row.get('impressions', 0)
        clicks = row.get('clicks', 0)
        if impr >= 20 and clicks == 0:
            zero_click.append({
                'query': row['keys'][0],
                'page': row['keys'][1].replace('https://tool.teamzlab.com', ''),
                'pos': row.get('position', 0), 'impr': impr
            })
    zero_click.sort(key=lambda x: x['impr'], reverse=True)
    if zero_click[:10]:
        print(f"  {'Query':<40} {'Page':<30} {'Pos':>4} {'Impr':>7}")
        print("  " + "-" * 83)
        for z in zero_click[:10]:
            q = z['query'][:40]
            p = z['page'][:30]
            print(f"  {q:<40} {p:<30} {z['pos']:>4.1f} {z['impr']:>7}")
        print(f"\n  ACTION: These queries show your pages in search but nobody clicks")
        print("  TIP: Rewrite title to include the exact query + add a compelling meta description")
    else:
        print("  No zero-click high-impression queries found")

    # 5) Summary score
    print("\n" + "=" * 70)
    print("  OPPORTUNITY SUMMARY")
    print("=" * 70)
    print(f"  CTR quick wins:        {len(ctr_wins)} queries (ranking well but under-clicked)")
    print(f"  Striking distance:     {len(striking)} queries (page 2 — almost page 1)")
    print(f"  Declining pages:       {len(declines)} pages (losing traffic)")
    print(f"  Zero-click queries:    {len(zero_click)} queries (seen but not clicked)")
    if ctr_wins:
        total_p = sum(w['potential'] for w in ctr_wins)
        print(f"\n  ESTIMATED UPSIDE: +{total_p} clicks/month from CTR fixes alone")
    print()

print("\n" + "=" * 70)
print("  Run: ./build-search-console.sh --queries        (queries only)")
print("  Run: ./build-search-console.sh --pages          (pages only)")
print("  Run: ./build-search-console.sh --status         (indexing only)")
print("  Run: ./build-search-console.sh --opportunities  (quick wins only)")
print("  Docs: docs/search-console-setup.md")
print("=" * 70)
PYEOF
