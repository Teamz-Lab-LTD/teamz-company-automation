#!/bin/bash
# ============================================================
# Teamz Lab Tools — Google PageSpeed Insights Checker
# Checks Core Web Vitals and performance scores — NO AUTH NEEDED
#
# Usage:
#   ./build-pagespeed.sh                           # Check top 10 pages
#   ./build-pagespeed.sh --url /ramadan/eid-salami-qr-card-generator/
#   ./build-pagespeed.sh --top20                   # Check top 20 by traffic
#   ./build-pagespeed.sh --slow                    # Find slowest pages
# ============================================================

_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
cd "$(dirname "$_SCRIPT")"
SITE="https://tool.teamzlab.com"
API_KEY_FILE="$HOME/.config/teamzlab/pagespeed-api-key.txt"

if [ ! -f "$API_KEY_FILE" ]; then
    echo "  ERROR: No PageSpeed API key found"
    echo "  Save your API key to: $API_KEY_FILE"
    echo "  Run: echo 'YOUR_API_KEY' > ~/.config/teamzlab/pagespeed-api-key.txt"
    exit 1
fi
API_KEY=$(cat "$API_KEY_FILE" | tr -d '[:space:]')

check_page() {
    local path="$1"
    local url="${SITE}${path}"
    local strategy="${2:-mobile}"

    local result=$(curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$url'))")&strategy=$strategy&category=performance&category=accessibility&category=seo&key=${API_KEY}" 2>/dev/null)

    echo "$result" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except:
    print(f'  {\"$path\":<50} ERROR')
    sys.exit()

lhr = data.get('lighthouseResult', {})
cats = lhr.get('categories', {})
perf = cats.get('performance', {}).get('score', 0)
access = cats.get('accessibility', {}).get('score', 0)
seo = cats.get('seo', {}).get('score', 0)

audits = lhr.get('audits', {})
fcp = audits.get('first-contentful-paint', {}).get('displayValue', 'N/A')
lcp = audits.get('largest-contentful-paint', {}).get('displayValue', 'N/A')
cls = audits.get('cumulative-layout-shift', {}).get('displayValue', 'N/A')
tbt = audits.get('total-blocking-time', {}).get('displayValue', 'N/A')

perf_pct = int(perf * 100) if perf else 0
access_pct = int(access * 100) if access else 0
seo_pct = int(seo * 100) if seo else 0

# Color coding
def grade(score):
    if score >= 90: return 'GOOD'
    elif score >= 50: return 'OKAY'
    else: return 'POOR'

print(f'  {\"$path\":<50} Perf:{perf_pct:>3} A11y:{access_pct:>3} SEO:{seo_pct:>3}  FCP:{fcp:>6} LCP:{lcp:>6} CLS:{cls:>6}  [{grade(perf_pct)}]')
" 2>/dev/null
}

# Default top pages to check
TOP_PAGES=(
    "/"
    "/ramadan/eid-salami-qr-card-generator/"
    "/ramadan/eid-salami-cheque-book/"
    "/bd/family-card-generator/"
    "/ramadan/eid-salami-scratch-challenge/"
    "/tools/ai-background-remover/"
    "/work/notice-period-calculator/"
    "/weather/wind-chill-calculator/"
    "/ai/plain-english-rewriter/"
    "/diagnostic/dns-leak-test/"
)

MODE="${1:---top10}"

case "$MODE" in
    --url)
        PAGE="${2:-/}"
        echo ""
        echo "============================================================"
        echo "  PAGESPEED CHECK — ${PAGE}"
        echo "============================================================"
        echo ""
        echo "  Mobile:"
        check_page "$PAGE" "mobile"
        echo ""
        echo "  Desktop:"
        check_page "$PAGE" "desktop"
        echo ""
        ;;
    --top10|"")
        echo ""
        echo "============================================================"
        echo "  PAGESPEED — Top 10 Pages (Mobile)"
        echo "============================================================"
        echo ""
        echo "  Page                                               Perf A11y  SEO    FCP    LCP    CLS  Grade"
        echo "  -------------------------------------------------- ---- ---- ----  ------ ------ ------  -----"
        for page in "${TOP_PAGES[@]}"; do
            check_page "$page" "mobile"
        done
        echo ""
        ;;
    --top20)
        echo ""
        echo "============================================================"
        echo "  PAGESPEED — Top 20 Pages (Mobile)"
        echo "============================================================"
        echo ""
        # Get top pages from analytics if available
        if [ -f "$HOME/.config/teamzlab/analytics-token.json" ]; then
            PAGES=$(python3 -c "
import json, urllib.request, urllib.parse, ssl
ctx = ssl.create_default_context()
with open('$HOME/.config/teamzlab/analytics-token.json') as f:
    t = json.load(f)
# Refresh token
data = urllib.parse.urlencode({
    'refresh_token': t['refresh_token'],
    'client_id': t['client_id'],
    'client_secret': t['client_secret'],
    'grant_type': 'refresh_token'
}).encode()
try:
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    with urllib.request.urlopen(req, context=ctx) as r:
        token = json.loads(r.read())['access_token']
except:
    token = t['token']

body = json.dumps({
    'dateRanges': [{'startDate': '7daysAgo', 'endDate': 'today'}],
    'dimensions': [{'name': 'pagePath'}],
    'metrics': [{'name': 'screenPageViews'}],
    'orderBys': [{'metric': {'metricName': 'screenPageViews'}, 'desc': True}],
    'limit': 20
}).encode()
req = urllib.request.Request('https://analyticsdata.googleapis.com/v1beta/properties/528521795:runReport',
    data=body, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'TeamzLab/1.0'})
with urllib.request.urlopen(req, context=ctx) as r:
    result = json.loads(r.read())
    for row in result.get('rows', []):
        path = row['dimensionValues'][0]['value']
        if path != '/' and not path.endswith('/index.html'):
            if not path.endswith('/'):
                path += '/'
            print(path)
" 2>/dev/null)
            echo "  (Using top pages from GA4 analytics)"
            echo ""
            while IFS= read -r page; do
                check_page "$page" "mobile"
            done <<< "$PAGES"
        else
            echo "  (No analytics token — using default pages)"
            for page in "${TOP_PAGES[@]}"; do
                check_page "$page" "mobile"
            done
        fi
        echo ""
        ;;
    *)
        echo "Usage: ./build-pagespeed.sh [--top10|--top20|--url /path/]"
        ;;
esac
