#!/bin/bash
# ============================================================
# Teamz Lab Tools — Google Analytics (GA4) Data Fetcher
# Pulls live analytics data from GA4 via Analytics Data API
#
# Usage:
#   ./build-analytics.sh              # Last 7 days overview
#   ./build-analytics.sh --today      # Today's data
#   ./build-analytics.sh --30days     # Last 30 days
#   ./build-analytics.sh --pages      # Top pages
#   ./build-analytics.sh --sources    # Traffic sources
#   ./build-analytics.sh --all        # Full report
#
# Setup:
#   1. Enable Analytics Data API in Google Cloud Console
#   2. Run: python3 build-analytics-auth.py (from teamz-company-automation/)
# ============================================================

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"

TOKEN_FILE="$HOME/.config/teamzlab/analytics-token.json"
PROPERTY_ID="528521795"

# Colors
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

# Check token
if [ ! -f "$TOKEN_FILE" ]; then
    echo -e "${RED}  ERROR: No analytics token found${NC}"
    echo "  Run: python3 build-analytics-auth.py  (from teamz-company-automation/)"
    exit 1
fi

# Refresh token if needed
ACCESS_TOKEN=$(python3 -c "
import json, urllib.request, urllib.parse, ssl
ctx = ssl.create_default_context()
with open('$TOKEN_FILE') as f:
    t = json.load(f)
# Try current token
req = urllib.request.Request(
    'https://analyticsdata.googleapis.com/v1beta/properties/$PROPERTY_ID/metadata',
    headers={'Authorization': f\"Bearer {t['token']}\", 'User-Agent': 'TeamzLab/1.0'})
try:
    urllib.request.urlopen(req, context=ctx, timeout=10)
    print(t['token'])
except:
    # Refresh
    data = urllib.parse.urlencode({
        'refresh_token': t['refresh_token'],
        'client_id': t['client_id'],
        'client_secret': t['client_secret'],
        'grant_type': 'refresh_token'
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    with urllib.request.urlopen(req, context=ctx) as r:
        new = json.loads(r.read())
        t['token'] = new['access_token']
        with open('$TOKEN_FILE', 'w') as f:
            json.dump(t, f, indent=2)
        print(new['access_token'])
" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${RED}  ERROR: Could not get access token. Re-run auth:${NC}"
    echo "  python3 build-analytics-auth.py  (from teamz-company-automation/)"
    exit 1
fi

# ── API Request Helper ──────────────────────────────────────
ga4_request() {
    local endpoint="$1"
    local body="$2"
    curl -s -X POST \
        "https://analyticsdata.googleapis.com/v1beta/properties/${PROPERTY_ID}:${endpoint}" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$body"
}

# ── Report Functions ────────────────────────────────────────

overview_report() {
    local start_date="${1:-7daysAgo}"
    local end_date="${2:-today}"
    local label="${3:-Last 7 Days}"

    echo ""
    echo "============================================================"
    echo "  ANALYTICS OVERVIEW — ${label}"
    echo "============================================================"

    local result=$(ga4_request "runReport" '{
        "dateRanges": [{"startDate": "'"$start_date"'", "endDate": "'"$end_date"'"}],
        "metrics": [
            {"name": "activeUsers"},
            {"name": "sessions"},
            {"name": "screenPageViews"},
            {"name": "averageSessionDuration"},
            {"name": "bounceRate"},
            {"name": "newUsers"},
            {"name": "engagedSessions"},
            {"name": "eventCount"}
        ]
    }')

    echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
rows = data.get('rows', [{}])
if not rows:
    print('  No data available')
    sys.exit()
vals = rows[0].get('metricValues', [])
metrics = ['Active Users', 'Sessions', 'Page Views', 'Avg Session (sec)', 'Bounce Rate', 'New Users', 'Engaged Sessions', 'Total Events']
for i, m in enumerate(metrics):
    v = vals[i]['value'] if i < len(vals) else '0'
    if m == 'Bounce Rate':
        v = f'{float(v)*100:.1f}%'
    elif m == 'Avg Session (sec)':
        v = f'{float(v):.0f}s'
    print(f'  {m:.<30} {v}')
"
    echo ""
}

top_pages_report() {
    local start_date="${1:-7daysAgo}"
    local end_date="${2:-today}"
    local label="${3:-Last 7 Days}"

    echo "============================================================"
    echo "  TOP PAGES — ${label}"
    echo "============================================================"

    local result=$(ga4_request "runReport" '{
        "dateRanges": [{"startDate": "'"$start_date"'", "endDate": "'"$end_date"'"}],
        "dimensions": [{"name": "pagePath"}],
        "metrics": [
            {"name": "screenPageViews"},
            {"name": "activeUsers"},
            {"name": "averageSessionDuration"}
        ],
        "orderBys": [{"metric": {"metricName": "screenPageViews"}, "desc": true}],
        "limit": 20
    }')

    echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
rows = data.get('rows', [])
if not rows:
    print('  No data')
    sys.exit()
print(f'  {\"Page\":<50} {\"Views\":>7} {\"Users\":>7} {\"Avg Time\":>8}')
print(f'  {\"-\"*50} {\"-\"*7} {\"-\"*7} {\"-\"*8}')
for r in rows:
    page = r['dimensionValues'][0]['value'][:50]
    views = r['metricValues'][0]['value']
    users = r['metricValues'][1]['value']
    dur = f\"{float(r['metricValues'][2]['value']):.0f}s\"
    print(f'  {page:<50} {views:>7} {users:>7} {dur:>8}')
"
    echo ""
}

traffic_sources_report() {
    local start_date="${1:-7daysAgo}"
    local end_date="${2:-today}"
    local label="${3:-Last 7 Days}"

    echo "============================================================"
    echo "  TRAFFIC SOURCES — ${label}"
    echo "============================================================"

    local result=$(ga4_request "runReport" '{
        "dateRanges": [{"startDate": "'"$start_date"'", "endDate": "'"$end_date"'"}],
        "dimensions": [{"name": "sessionSource"}, {"name": "sessionMedium"}],
        "metrics": [
            {"name": "sessions"},
            {"name": "activeUsers"},
            {"name": "bounceRate"}
        ],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": true}],
        "limit": 15
    }')

    echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
rows = data.get('rows', [])
if not rows:
    print('  No data')
    sys.exit()
print(f'  {\"Source / Medium\":<40} {\"Sessions\":>8} {\"Users\":>7} {\"Bounce\":>8}')
print(f'  {\"-\"*40} {\"-\"*8} {\"-\"*7} {\"-\"*8}')
for r in rows:
    source = r['dimensionValues'][0]['value']
    medium = r['dimensionValues'][1]['value']
    sm = f'{source} / {medium}'[:40]
    sessions = r['metricValues'][0]['value']
    users = r['metricValues'][1]['value']
    bounce = f\"{float(r['metricValues'][2]['value'])*100:.0f}%\"
    print(f'  {sm:<40} {sessions:>8} {users:>7} {bounce:>8}')
"
    echo ""
}

devices_report() {
    local start_date="${1:-7daysAgo}"
    local end_date="${2:-today}"

    echo "============================================================"
    echo "  DEVICES & COUNTRIES"
    echo "============================================================"

    # Devices
    local result=$(ga4_request "runReport" '{
        "dateRanges": [{"startDate": "'"$start_date"'", "endDate": "'"$end_date"'"}],
        "dimensions": [{"name": "deviceCategory"}],
        "metrics": [{"name": "activeUsers"}, {"name": "sessions"}],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": true}]
    }')

    echo ""
    echo "  Devices:"
    echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for r in data.get('rows', []):
    device = r['dimensionValues'][0]['value']
    users = r['metricValues'][0]['value']
    sessions = r['metricValues'][1]['value']
    print(f'    {device:<15} {users:>5} users  {sessions:>5} sessions')
"

    # Countries
    local result2=$(ga4_request "runReport" '{
        "dateRanges": [{"startDate": "'"$start_date"'", "endDate": "'"$end_date"'"}],
        "dimensions": [{"name": "country"}],
        "metrics": [{"name": "activeUsers"}],
        "orderBys": [{"metric": {"metricName": "activeUsers"}, "desc": true}],
        "limit": 10
    }')

    echo ""
    echo "  Top Countries:"
    echo "$result2" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for r in data.get('rows', []):
    country = r['dimensionValues'][0]['value'][:25]
    users = r['metricValues'][0]['value']
    print(f'    {country:<25} {users:>5} users')
"
    echo ""
}

ad_events_report() {
    local start_date="${1:-7daysAgo}"
    local end_date="${2:-today}"

    echo "============================================================"
    echo "  AD PERFORMANCE EVENTS"
    echo "============================================================"

    local result=$(ga4_request "runReport" '{
        "dateRanges": [{"startDate": "'"$start_date"'", "endDate": "'"$end_date"'"}],
        "dimensions": [{"name": "eventName"}],
        "metrics": [{"name": "eventCount"}, {"name": "totalUsers"}],
        "dimensionFilter": {
            "orGroup": {
                "expressions": [
                    {"filter": {"fieldName": "eventName", "stringFilter": {"matchType": "CONTAINS", "value": "ad_"}}},
                    {"filter": {"fieldName": "eventName", "stringFilter": {"matchType": "CONTAINS", "value": "adsense"}}}
                ]
            }
        },
        "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": true}]
    }')

    echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
rows = data.get('rows', [])
if not rows:
    print('  No ad events')
    sys.exit()
print(f'  {\"Event\":<35} {\"Count\":>7} {\"Users\":>7}')
print(f'  {\"-\"*35} {\"-\"*7} {\"-\"*7}')
for r in rows:
    event = r['dimensionValues'][0]['value'][:35]
    count = r['metricValues'][0]['value']
    users = r['metricValues'][1]['value']
    print(f'  {event:<35} {count:>7} {users:>7}')
"
    echo ""
}

# ── Main ────────────────────────────────────────────────────

MODE="${1:---7days}"

case "$MODE" in
    --today)
        overview_report "today" "today" "Today"
        top_pages_report "today" "today" "Today"
        ;;
    --7days|"")
        overview_report "7daysAgo" "today" "Last 7 Days"
        top_pages_report "7daysAgo" "today" "Last 7 Days"
        ;;
    --30days)
        overview_report "30daysAgo" "today" "Last 30 Days"
        top_pages_report "30daysAgo" "today" "Last 30 Days"
        traffic_sources_report "30daysAgo" "today" "Last 30 Days"
        ;;
    --pages)
        top_pages_report "7daysAgo" "today" "Last 7 Days"
        ;;
    --sources)
        traffic_sources_report "7daysAgo" "today" "Last 7 Days"
        ;;
    --ads)
        ad_events_report "7daysAgo" "today"
        ;;
    --all)
        overview_report "7daysAgo" "today" "Last 7 Days"
        top_pages_report "7daysAgo" "today" "Last 7 Days"
        traffic_sources_report "7daysAgo" "today" "Last 7 Days"
        devices_report "7daysAgo" "today"
        ad_events_report "7daysAgo" "today"
        ;;
    --status)
        overview_report "today" "today" "Today"
        ;;
    *)
        echo "Usage: ./build-analytics.sh [--today|--7days|--30days|--pages|--sources|--ads|--all|--status]"
        ;;
esac
