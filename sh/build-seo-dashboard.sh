#!/bin/bash
# ============================================================
#  Teamz Lab Tools — FREE SEO Dashboard (replaces Ubersuggest)
#
#  Combines: Google Search Console + GA4 Analytics + PageSpeed
#  into a single Ubersuggest-style report — 100% FREE
#
#  Usage:
#    ./build-seo-dashboard.sh              # Full dashboard
#    ./build-seo-dashboard.sh --quick      # Quick overview (no PageSpeed)
#    ./build-seo-dashboard.sh --rank       # Rank tracking only
#    ./build-seo-dashboard.sh --traffic    # Traffic overview only
#    ./build-seo-dashboard.sh --keywords   # Keywords by traffic only
#    ./build-seo-dashboard.sh --audit      # Site audit only
#    ./build-seo-dashboard.sh --speed      # Page speed only
#    ./build-seo-dashboard.sh --compare    # Compare 7d vs prior 7d
#
#  Related scripts (full Ubersuggest replacement suite):
#    python3 scripts/build-keyword-intel.py            # Keyword Ideas + Opportunities
#    python3 scripts/build-keyword-intel.py --ideas "x" # Keyword suggestions (Autocomplete)
#    python3 scripts/build-rank-tracker.py              # Daily rank tracking + trends
#    python3 scripts/build-rank-tracker.py movers       # Biggest position changes
#    python3 scripts/build-backlinks-overview.py        # Backlinks overview + scan
#    python3 scripts/build-backlinks.py                 # Directory submission tracker
#    python3 scripts/build-content-ideas.py             # Content ideas + seasonal + gaps
#    python3 scripts/build-content-ideas.py --trending  # Trending topics
# ============================================================

set -e
_RES="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
# sh/ → parent = teamz-company-automation repo root
AUTOMATION_ROOT="$(cd "$(dirname "$_RES")/.." && pwd)"
# shellcheck disable=SC1091
source "$AUTOMATION_ROOT/sh/lib/config.sh"
teamz_load_config "$_RES"
cd "$AUTOMATION_ROOT"

MODE="${1:---quick}"
SITE_URL="$TEAMZ_SITE_PROPERTY"
TOKEN_FILE="$TEAMZ_SC_TOKEN_FILE"
GA4_TOKEN_FILE="$TEAMZ_GA4_TOKEN_FILE"
GA4_PROPERTY_ID="$TEAMZ_GA4_PROPERTY_ID"
PAGESPEED_KEY_FILE="$TEAMZ_PAGESPEED_KEY_FILE"
GOOGLE_PROJECT="$TEAMZ_GOOGLE_CLOUD_PROJECT"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║           TEAMZ LAB — FREE SEO DASHBOARD                          ║"
echo "║           (Replaces: Ubersuggest, Ahrefs, SEMrush)                 ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "  Date: $(date '+%Y-%m-%d %H:%M')"
echo "  Site: ${SITE_URL%/}"
echo ""

# ─────────────────────────────────────────────────────────────
#  SECTION 1: TRAFFIC OVERVIEW (like Ubersuggest Traffic Overview)
#  Source: Google Analytics GA4
# ─────────────────────────────────────────────────────────────
if [[ "$MODE" == "--quick" || "$MODE" == "--traffic" || "$MODE" == "--compare" ]]; then

python3 - "$GA4_TOKEN_FILE" "$GA4_PROPERTY_ID" "$MODE" << 'PYEOF'
import json, sys, os, requests
from datetime import datetime, timedelta

TOKEN_FILE = sys.argv[1]
property_id = sys.argv[2]
COMPARE_MODE = sys.argv[3] == "--compare"

if not os.path.exists(TOKEN_FILE):
    print("  ⚠ GA4 not configured — skipping traffic overview")
    print("  Run: ./build-analytics.sh to set up")
    sys.exit(0)

with open(TOKEN_FILE) as f:
    token_data = json.load(f)

# Refresh token
def get_token():
    token = token_data.get('token', '')
    r = requests.get(
        f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}/metadata',
        headers={'Authorization': f'Bearer {token}'}
    )
    if r.status_code == 200:
        return token
    refresh = token_data.get('refresh_token')
    if not refresh:
        print("  ⚠ GA4 token expired")
        sys.exit(0)
    rr = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': token_data['client_id'],
        'client_secret': token_data['client_secret'],
        'refresh_token': refresh,
        'grant_type': 'refresh_token'
    })
    if rr.status_code == 200:
        new_token = rr.json()['access_token']
        token_data['token'] = new_token
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        return new_token
    print("  ⚠ GA4 token refresh failed")
    sys.exit(0)

token = get_token()
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
API = f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport'

def run_report(start, end, dimensions=None, metrics=None):
    payload = {
        'dateRanges': [{'startDate': start, 'endDate': end}],
        'metrics': [{'name': m} for m in (metrics or ['activeUsers', 'sessions', 'screenPageViews'])],
    }
    if dimensions:
        payload['dimensions'] = [{'name': d} for d in dimensions]
    r = requests.post(API, headers=headers, json=payload)
    if r.status_code == 200:
        return r.json()
    return {}

# Current 7 days
end = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
start_7d = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
start_30d = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

# Prior 7 days (for comparison)
prior_end = (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d')
prior_start = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')

print("┌──────────────────────────────────────────────────────────────────┐")
print("│  TRAFFIC OVERVIEW                                               │")
print("│  (Ubersuggest equivalent: Traffic Overview)                      │")
print("└──────────────────────────────────────────────────────────────────┘")

# 7-day overview
overview = run_report(start_7d, end, metrics=[
    'activeUsers', 'sessions', 'screenPageViews',
    'averageSessionDuration', 'bounceRate', 'newUsers',
    'engagedSessions'
])
rows = overview.get('rows', [{}])
if rows:
    vals = rows[0].get('metricValues', [])
    users = int(vals[0]['value']) if len(vals) > 0 else 0
    sessions = int(vals[1]['value']) if len(vals) > 1 else 0
    pageviews = int(vals[2]['value']) if len(vals) > 2 else 0
    avg_duration = float(vals[3]['value']) if len(vals) > 3 else 0
    bounce = float(vals[4]['value']) * 100 if len(vals) > 4 else 0
    new_users = int(vals[5]['value']) if len(vals) > 5 else 0
    engaged = int(vals[6]['value']) if len(vals) > 6 else 0

    # Prior period for comparison
    prior = run_report(prior_start, prior_end, metrics=[
        'activeUsers', 'sessions', 'screenPageViews',
        'averageSessionDuration', 'bounceRate', 'newUsers'
    ])
    prior_rows = prior.get('rows', [{}])
    pvals = prior_rows[0].get('metricValues', []) if prior_rows else []
    p_users = int(pvals[0]['value']) if len(pvals) > 0 else 1
    p_sessions = int(pvals[1]['value']) if len(pvals) > 1 else 1
    p_pageviews = int(pvals[2]['value']) if len(pvals) > 2 else 1

    def change_pct(current, prior):
        if prior == 0:
            return "+∞"
        pct = ((current - prior) / prior) * 100
        return f"{pct:+.0f}%"

    def change_arrow(current, prior):
        if current > prior:
            return "▲"
        elif current < prior:
            return "▼"
        return "="

    print(f"""
  ┌─────────────────────┬─────────────────────┬─────────────────────┐
  │  USERS (7d)         │  SESSIONS (7d)      │  PAGE VIEWS (7d)    │
  │  {users:<11}         │  {sessions:<11}         │  {pageviews:<11}         │
  │  {change_arrow(users, p_users)} {change_pct(users, p_users):<15} │  {change_arrow(sessions, p_sessions)} {change_pct(sessions, p_sessions):<15} │  {change_arrow(pageviews, p_pageviews)} {change_pct(pageviews, p_pageviews):<15} │
  └─────────────────────┴─────────────────────┴─────────────────────┘

  Avg Session Duration: {avg_duration:.0f}s
  Bounce Rate: {bounce:.1f}%
  New Users: {new_users}
  Engaged Sessions: {engaged}
""")

# Traffic sources
print("  TRAFFIC SOURCES (7d)")
print("  " + "-" * 60)
sources = run_report(start_7d, end, dimensions=['sessionSource', 'sessionMedium'],
                     metrics=['sessions', 'activeUsers'])
src_rows = sources.get('rows', [])
src_rows.sort(key=lambda r: int(r['metricValues'][0]['value']), reverse=True)
organic_total = 0
direct_total = 0
referral_total = 0
social_total = 0
for row in src_rows[:15]:
    src = row['dimensionValues'][0]['value']
    med = row['dimensionValues'][1]['value']
    sess = int(row['metricValues'][0]['value'])
    u = int(row['metricValues'][1]['value'])
    label = f"{src} / {med}"
    if 'organic' in med:
        organic_total += sess
    elif med == '(none)':
        direct_total += sess
    elif med == 'referral':
        referral_total += sess
        if src in ('facebook.com', 'm.facebook.com', 'l.facebook.com', 'lm.facebook.com',
                    'twitter.com', 'reddit.com', 'linkedin.com'):
            social_total += sess
    print(f"    {label:<40} {sess:>6} sessions  {u:>6} users")

total_sessions = organic_total + direct_total + referral_total
print(f"""
  ┌─────────────────────┬─────────────────────┬─────────────────────┐
  │  ORGANIC            │  DIRECT             │  REFERRAL           │
  │  {organic_total:<11}         │  {direct_total:<11}         │  {referral_total:<11}         │
  └─────────────────────┴─────────────────────┴─────────────────────┘
""")

# Countries
print("  TOP COUNTRIES (7d)")
print("  " + "-" * 50)
countries = run_report(start_7d, end, dimensions=['country'],
                       metrics=['activeUsers', 'sessions'])
c_rows = countries.get('rows', [])
c_rows.sort(key=lambda r: int(r['metricValues'][0]['value']), reverse=True)
for row in c_rows[:10]:
    country = row['dimensionValues'][0]['value']
    u = int(row['metricValues'][0]['value'])
    s = int(row['metricValues'][1]['value'])
    bar = "█" * min(int(u / max(int(c_rows[0]['metricValues'][0]['value']), 1) * 30), 30)
    print(f"    {country:<25} {u:>6} users  {bar}")

# Devices
print(f"\n  DEVICES (7d)")
print("  " + "-" * 50)
devices = run_report(start_7d, end, dimensions=['deviceCategory'],
                     metrics=['activeUsers', 'sessions'])
d_rows = devices.get('rows', [])
total_d = sum(int(r['metricValues'][0]['value']) for r in d_rows) or 1
for row in d_rows:
    device = row['dimensionValues'][0]['value']
    u = int(row['metricValues'][0]['value'])
    pct = u / total_d * 100
    bar = "█" * int(pct / 3)
    print(f"    {device:<15} {u:>6} users ({pct:.0f}%) {bar}")
print()

PYEOF
fi

# ─────────────────────────────────────────────────────────────
#  SECTION 2: RANK TRACKING (like Ubersuggest Rank Tracking)
#  Source: Google Search Console
# ─────────────────────────────────────────────────────────────
if [[ "$MODE" == "--quick" || "$MODE" == "--rank" || "$MODE" == "--keywords" ]]; then

python3 - "$TOKEN_FILE" "$SITE_URL" "$MODE" "$GOOGLE_PROJECT" << 'PYEOF'
import json, sys, os, requests
from datetime import datetime, timedelta
from urllib.parse import quote

TOKEN_FILE = sys.argv[1]
SITE_URL = sys.argv[2]
SHOW_MODE = sys.argv[3]
GOOGLE_PROJECT = sys.argv[4]
ENCODED_SITE = quote(SITE_URL, safe='')

if not os.path.exists(TOKEN_FILE):
    print("  ⚠ Search Console not configured — skipping rank tracking")
    sys.exit(0)

with open(TOKEN_FILE) as f:
    token_data = json.load(f)

def get_token():
    token = token_data.get('token', '')
    r = requests.get(
        f'https://searchconsole.googleapis.com/webmasters/v3/sites',
        headers={'Authorization': f'Bearer {token}', 'x-goog-user-project': GOOGLE_PROJECT}
    )
    if r.status_code == 200:
        return token
    refresh = token_data.get('refresh_token')
    if not refresh:
        print("  ⚠ Search Console token expired")
        sys.exit(0)
    rr = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': token_data['client_id'],
        'client_secret': token_data['client_secret'],
        'refresh_token': refresh,
        'grant_type': 'refresh_token'
    })
    if rr.status_code == 200:
        new_token = rr.json()['access_token']
        token_data['token'] = new_token
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        return new_token
    print("  ⚠ Token refresh failed")
    sys.exit(0)

token = get_token()
headers = {
    'Authorization': f'Bearer {token}',
    'x-goog-user-project': GOOGLE_PROJECT,
    'Content-Type': 'application/json'
}
API_BASE = f'https://searchconsole.googleapis.com/webmasters/v3/sites/{ENCODED_SITE}'

end = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
start_7d = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
start_30d = (datetime.now() - timedelta(days=33)).strftime('%Y-%m-%d')
start_90d = (datetime.now() - timedelta(days=93)).strftime('%Y-%m-%d')

# Prior period for comparison
prior_end = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
prior_start = (datetime.now() - timedelta(days=17)).strftime('%Y-%m-%d')

def query_search(dimensions, row_limit=50, start=start_90d, end_d=end, filters=None):
    payload = {
        'startDate': start, 'endDate': end_d,
        'dimensions': dimensions, 'rowLimit': row_limit
    }
    if filters:
        payload['dimensionFilterGroups'] = [{'filters': filters}]
    r = requests.post(f'{API_BASE}/searchAnalytics/query', headers=headers, json=payload)
    return r.json().get('rows', [])

# ── RANK TRACKING ──
if SHOW_MODE in ('--quick', '--rank'):
    print("┌──────────────────────────────────────────────────────────────────┐")
    print("│  RANK TRACKING — Your Google Rankings                           │")
    print("│  (Ubersuggest equivalent: Rank Tracking)                         │")
    print("└──────────────────────────────────────────────────────────────────┘")
    print()

    # Get current period queries
    current_rows = query_search(['query'], row_limit=500, start=start_7d)
    # Get prior period for position changes
    prior_rows = query_search(['query'], row_limit=500, start=prior_start, end_d=prior_end)

    prior_map = {}
    for row in prior_rows:
        prior_map[row['keys'][0]] = row.get('position', 0)

    # Sort by impressions (visibility)
    current_rows.sort(key=lambda r: r.get('impressions', 0), reverse=True)

    # Categorize positions
    top3 = []
    top10 = []
    top20 = []
    top50 = []
    top100 = []
    not_ranked = 0

    for row in current_rows:
        pos = row.get('position', 0)
        if pos <= 3: top3.append(row)
        elif pos <= 10: top10.append(row)
        elif pos <= 20: top20.append(row)
        elif pos <= 50: top50.append(row)
        elif pos <= 100: top100.append(row)
        else: not_ranked += 1

    total_kw = len(current_rows)
    print(f"  TRACKED KEYWORDS: {total_kw}")
    print()
    print(f"  ┌──────────┬──────────┬──────────┬──────────┬──────────┐")
    print(f"  │ Top 3    │ Top 10   │ Top 20   │ Top 50   │ Top 100  │")
    print(f"  │ {len(top3):<8} │ {len(top10):<8} │ {len(top20):<8} │ {len(top50):<8} │ {len(top100):<8} │")
    print(f"  └──────────┴──────────┴──────────┴──────────┴──────────┘")
    print()

    # Show ranked keywords with changes
    print(f"  {'#':>4}  {'KEYWORD':<45} {'POS':>5} {'CHANGE':>8} {'CLICKS':>7} {'IMPR':>7} {'CTR':>6}")
    print("  " + "-" * 90)

    for i, row in enumerate(current_rows[:50], 1):
        q = row['keys'][0][:45]
        pos = row.get('position', 0)
        clicks = row.get('clicks', 0)
        impr = row.get('impressions', 0)
        ctr = row.get('ctr', 0) * 100
        prior_pos = prior_map.get(row['keys'][0])

        if prior_pos:
            change = prior_pos - pos  # positive = improved
            if change > 0:
                change_str = f"▲ {change:.0f}"
            elif change < 0:
                change_str = f"▼ {abs(change):.0f}"
            else:
                change_str = "="
        else:
            change_str = "NEW"

        print(f"  {i:>4}  {q:<45} {pos:>5.1f} {change_str:>8} {clicks:>7} {impr:>7} {ctr:>5.1f}%")

    print()

# ── KEYWORDS BY TRAFFIC ──
if SHOW_MODE in ('--quick', '--keywords'):
    print("┌──────────────────────────────────────────────────────────────────┐")
    print("│  KEYWORDS BY TRAFFIC — Queries Driving Visits                   │")
    print("│  (Ubersuggest equivalent: Keywords by Traffic)                    │")
    print("└──────────────────────────────────────────────────────────────────┘")
    print()

    # Get query + page combinations sorted by clicks
    rows = query_search(['query', 'page'], row_limit=200, start=start_30d)
    rows.sort(key=lambda r: r.get('clicks', 0), reverse=True)

    # Show queries that actually drive traffic (clicks > 0 first)
    print(f"  {'KEYWORD':<40} {'PAGE':<35} {'POS':>5} {'CLICKS':>7} {'IMPR':>7}")
    print("  " + "-" * 96)

    shown = 0
    for row in rows:
        if shown >= 30:
            break
        q = row['keys'][0][:40]
        page = row['keys'][1].replace(SITE_URL.rstrip('/'), '')[:35]
        pos = row.get('position', 0)
        clicks = row.get('clicks', 0)
        impr = row.get('impressions', 0)
        print(f"  {q:<40} {page:<35} {pos:>5.1f} {clicks:>7} {impr:>7}")
        shown += 1

    # Summary
    total_clicks = sum(r.get('clicks', 0) for r in rows)
    total_impr = sum(r.get('impressions', 0) for r in rows)
    unique_queries = len(set(r['keys'][0] for r in rows))
    unique_pages = len(set(r['keys'][1] for r in rows))
    print(f"\n  Summary: {unique_queries} keywords → {unique_pages} pages")
    print(f"  Total: {total_clicks} clicks, {total_impr:,} impressions (30d)")
    print()

    # ── TOP PAGES BY SEARCH ──
    print("  TOP PAGES BY SEARCH TRAFFIC (30d)")
    print("  " + "-" * 80)
    page_rows = query_search(['page'], row_limit=50, start=start_30d)
    page_rows.sort(key=lambda r: r.get('clicks', 0), reverse=True)
    print(f"  {'PAGE':<55} {'CLICKS':>7} {'IMPR':>8} {'POS':>6}")
    print("  " + "-" * 78)
    for row in page_rows[:20]:
        page = row['keys'][0].replace(SITE_URL.rstrip('/'), '')[:55]
        clicks = row.get('clicks', 0)
        impr = row.get('impressions', 0)
        pos = row.get('position', 0)
        print(f"  {page:<55} {clicks:>7} {impr:>8} {pos:>5.1f}")
    print()

# ── INDEXING STATUS ──
if SHOW_MODE in ('--quick', '--rank'):
    # Sitemap info
    r = requests.get(f'{API_BASE}/sitemaps', headers=headers)
    sitemaps = r.json()
    submitted = 0
    if 'sitemap' in sitemaps:
        for s in sitemaps['sitemap']:
            contents = s.get('contents', [{}])[0]
            submitted = int(contents.get('submitted', 0))

    pages_90d = query_search(['page'], row_limit=2000, start=start_90d)
    indexed_pages = len(pages_90d)
    total_clicks_90d = sum(r.get('clicks', 0) for r in pages_90d)
    total_impr_90d = sum(r.get('impressions', 0) for r in pages_90d)

    print("  INDEXING STATUS")
    print("  " + "-" * 50)
    print(f"  Submitted URLs:         {submitted}")
    print(f"  Pages with impressions: {indexed_pages}")
    print(f"  Total clicks (90d):     {total_clicks_90d}")
    print(f"  Total impressions (90d): {total_impr_90d:,}")
    coverage_pct = (indexed_pages / submitted * 100) if submitted else 0
    print(f"  Coverage:               {coverage_pct:.1f}%")
    print()

PYEOF
fi

# ─────────────────────────────────────────────────────────────
#  SECTION 3: SITE AUDIT (like Ubersuggest Site Audit)
#  Source: Our own QA scripts
# ─────────────────────────────────────────────────────────────
if [[ "$MODE" == "--audit" ]]; then
    echo "┌──────────────────────────────────────────────────────────────────┐"
    echo "│  SITE AUDIT                                                      │"
    echo "│  (Ubersuggest equivalent: Site Audit)                             │"
    echo "└──────────────────────────────────────────────────────────────────┘"
    echo ""

    HOST_ROOT="$TEAMZ_HOST_SITE_ROOT"
    if [[ ! -d "$HOST_ROOT" ]]; then
        echo "  ERROR: TEAMZ_HOST_SITE_ROOT is not a directory: $HOST_ROOT"
        exit 1
    fi

    # Count total pages (HTML site = parent of this submodule by default)
    TOTAL_PAGES=$(find "$HOST_ROOT" -name "index.html" -not -path "*/node_modules/*" -not -path "*/.git/*" | wc -l | tr -d ' ')
    echo "  PAGES CRAWLED: $TOTAL_PAGES"
    echo ""

    # Run QA checks
    echo "  Running SEO audit..."
    echo ""

    # Count issues
    LOW_WORD=0
    SHORT_TITLE=0
    NO_FAQ=0
    NO_SCHEMA=0
    HARDCODED=0
    NO_MOBILE=0

    for f in $(find "$HOST_ROOT" -path "*/index.html" -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "$HOST_ROOT/index.html" | head -200); do
        content=$(cat "$f" 2>/dev/null)

        # Low word count
        word_count=$(echo "$content" | sed -n '/<section class="tool-content"/,/<\/section>/p' | sed 's/<[^>]*>//g' | wc -w | tr -d ' ')
        if [ "$word_count" -lt 150 ] 2>/dev/null; then
            LOW_WORD=$((LOW_WORD + 1))
        fi

        # Short title
        title=$(echo "$content" | grep -o '<title>[^<]*</title>' | head -1 | sed 's/<[^>]*>//g')
        title_len=${#title}
        if [ "$title_len" -gt 0 ] && [ "$title_len" -lt 30 ] 2>/dev/null; then
            SHORT_TITLE=$((SHORT_TITLE + 1))
        fi

        # Missing FAQs
        if ! echo "$content" | grep -q "renderFAQs\|injectFAQSchema"; then
            NO_FAQ=$((NO_FAQ + 1))
        fi

        # Missing WebApp schema
        if ! echo "$content" | grep -q "injectWebAppSchema"; then
            NO_SCHEMA=$((NO_SCHEMA + 1))
        fi

        # Hardcoded colors
        if echo "$content" | grep -q '#[0-9a-fA-F]\{6\}'; then
            HARDCODED=$((HARDCODED + 1))
        fi

        # Missing mobile responsive
        if ! echo "$content" | grep -q "max-width.*600px\|max-width:.*600px"; then
            NO_MOBILE=$((NO_MOBILE + 1))
        fi
    done

    TOTAL_ISSUES=$((LOW_WORD + SHORT_TITLE + NO_FAQ + NO_SCHEMA + HARDCODED + NO_MOBILE))

    echo "  ┌───────────────────────────────────┬───────────────────────────────┐"
    echo "  │  PAGES CRAWLED                    │  SEO ISSUES DISCOVERED       │"
    echo "  │  $TOTAL_PAGES                           │  $TOTAL_ISSUES                           │"
    echo "  └───────────────────────────────────┴───────────────────────────────┘"
    echo ""
    echo "  TOP SEO ISSUES:"
    [ "$LOW_WORD" -gt 0 ] && echo "    ⚠ $LOW_WORD pages have low word count (<150 words)"
    [ "$SHORT_TITLE" -gt 0 ] && echo "    ⚠ $SHORT_TITLE pages have a <title> tag that is too short"
    [ "$NO_FAQ" -gt 0 ] && echo "    ⚠ $NO_FAQ pages are missing FAQ schema"
    [ "$NO_SCHEMA" -gt 0 ] && echo "    ⚠ $NO_SCHEMA pages are missing WebApplication schema"
    [ "$HARDCODED" -gt 0 ] && echo "    ⚠ $HARDCODED pages have hardcoded hex colors"
    [ "$NO_MOBILE" -gt 0 ] && echo "    ⚠ $NO_MOBILE pages may not be mobile-responsive"
    echo ""
    echo "  For detailed audit: ./scripts/build-qa-check.sh (from Teamz Lab Tools site root)"
    echo "  For SEO keyword audit: ./scripts/build-seo-audit.sh --report (from site root)"
    echo ""
fi

# ─────────────────────────────────────────────────────────────
#  SECTION 4: PAGE SPEED (like Ubersuggest Site Speed)
#  Source: Google PageSpeed Insights API (free)
# ─────────────────────────────────────────────────────────────
if [[ "$MODE" == "--speed" ]]; then
    echo "┌──────────────────────────────────────────────────────────────────┐"
    echo "│  PAGE SPEED — Core Web Vitals                                    │"
    echo "│  (Ubersuggest equivalent: Site Speed)                             │"
    echo "└──────────────────────────────────────────────────────────────────┘"
    echo ""
    "$AUTOMATION_ROOT/sh/build-pagespeed.sh"
fi

# ─────────────────────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  DATA SOURCES (all 100% free):                                     ║"
echo "║  • Google Search Console API — rankings, keywords, indexing        ║"
echo "║  • Google Analytics GA4 API  — traffic, sources, countries         ║"
echo "║  • PageSpeed Insights API    — Core Web Vitals, speed scores       ║"
echo "║  • Internal QA scripts       — site audit, SEO checks             ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  Commands:                                                         ║"
echo "║  ./build-seo-dashboard.sh --quick      Quick overview              ║"
echo "║  ./build-seo-dashboard.sh --rank       Rank tracking               ║"
echo "║  ./build-seo-dashboard.sh --traffic    Traffic overview             ║"
echo "║  ./build-seo-dashboard.sh --keywords   Keywords by traffic         ║"
echo "║  ./build-seo-dashboard.sh --audit      Site audit                  ║"
echo "║  ./build-seo-dashboard.sh --speed      Page speed                  ║"
echo "║  ./build-seo-dashboard.sh --compare    Week-over-week compare      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
