#!/bin/bash
# ============================================================
# Teamz Lab Tools — Google AdSense Data Fetcher
# Pulls live AdSense revenue, RPM, clicks, impressions
#
# Usage:
#   ./build-adsense.sh              # Last 7 days overview
#   ./build-adsense.sh --today      # Today's earnings
#   ./build-adsense.sh --30days     # Last 30 days
#   ./build-adsense.sh --pages      # Top earning pages
#   ./build-adsense.sh --all        # Full report
# ============================================================

cd "$(dirname "$0")"

TOKEN_FILE="$HOME/.config/teamzlab/adsense-token.json"

if [ ! -f "$TOKEN_FILE" ]; then
    echo "  ERROR: No AdSense token found"
    echo "  Run: python3 build-adsense-auth.py  (from teamz-company-automation/)"
    exit 1
fi

# Get account ID and refresh token
RESULT=$(python3 -c "
import json, urllib.request, urllib.parse, ssl
ctx = ssl.create_default_context()
with open('$TOKEN_FILE') as f:
    t = json.load(f)

token = t['token']

# Test token, refresh if needed
req = urllib.request.Request('https://adsense.googleapis.com/v2/accounts',
    headers={'Authorization': f'Bearer {token}', 'User-Agent': 'TeamzLab/1.0'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        data = json.loads(r.read())
except:
    # Refresh
    rd = urllib.parse.urlencode({
        'refresh_token': t['refresh_token'],
        'client_id': t['client_id'],
        'client_secret': t['client_secret'],
        'grant_type': 'refresh_token'
    }).encode()
    req2 = urllib.request.Request('https://oauth2.googleapis.com/token', data=rd)
    with urllib.request.urlopen(req2, context=ctx) as r2:
        new = json.loads(r2.read())
        token = new['access_token']
        t['token'] = token
        with open('$TOKEN_FILE', 'w') as f:
            json.dump(t, f, indent=2)

    req = urllib.request.Request('https://adsense.googleapis.com/v2/accounts',
        headers={'Authorization': f'Bearer {token}', 'User-Agent': 'TeamzLab/1.0'})
    with urllib.request.urlopen(req, context=ctx) as r:
        data = json.loads(r.read())

accounts = data.get('accounts', [])
if accounts:
    print(f\"{token}|{accounts[0]['name']}\")
else:
    print(f\"{token}|\")
" 2>/dev/null)

ACCESS_TOKEN=$(echo "$RESULT" | cut -d'|' -f1)
ACCOUNT=$(echo "$RESULT" | cut -d'|' -f2)

if [ -z "$ACCESS_TOKEN" ] || [ -z "$ACCOUNT" ]; then
    echo "  ERROR: Could not get AdSense account. Re-run auth."
    exit 1
fi

# ── API Request Helper ──────────────────────────────────────
adsense_report() {
    local start_date="$1"
    local end_date="$2"
    local dimensions="$3"
    local metrics="${4:-ESTIMATED_EARNINGS,PAGE_VIEWS,IMPRESSIONS,CLICKS,PAGE_VIEWS_RPM,COST_PER_CLICK}"
    local limit="${5:-20}"

    local url="https://adsense.googleapis.com/v2/${ACCOUNT}/reports:generate"
    url+="?dateRange=CUSTOM"
    url+="&startDate.year=$(echo $start_date | cut -d- -f1)"
    url+="&startDate.month=$(echo $start_date | cut -d- -f2)"
    url+="&startDate.day=$(echo $start_date | cut -d- -f3)"
    url+="&endDate.year=$(echo $end_date | cut -d- -f1)"
    url+="&endDate.month=$(echo $end_date | cut -d- -f2)"
    url+="&endDate.day=$(echo $end_date | cut -d- -f3)"

    # Add metrics
    IFS=',' read -ra M <<< "$metrics"
    for m in "${M[@]}"; do
        url+="&metrics=$m"
    done

    # Add dimensions
    if [ -n "$dimensions" ]; then
        IFS=',' read -ra D <<< "$dimensions"
        for d in "${D[@]}"; do
            url+="&dimensions=$d"
        done
    fi

    url+="&limit=$limit"
    url+="&orderBy=%2BESTIMATED_EARNINGS"

    curl -s "$url" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "User-Agent: TeamzLab/1.0"
}

# ── Date Helpers ────────────────────────────────────────────
TODAY=$(date +%Y-%m-%d)
DAYS7=$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d "7 days ago" +%Y-%m-%d)
DAYS30=$(date -v-30d +%Y-%m-%d 2>/dev/null || date -d "30 days ago" +%Y-%m-%d)

# ── Report Functions ────────────────────────────────────────

overview_report() {
    local start="$1"
    local end="$2"
    local label="$3"

    echo ""
    echo "============================================================"
    echo "  ADSENSE OVERVIEW — ${label}"
    echo "============================================================"

    local result=$(adsense_report "$start" "$end" "" "ESTIMATED_EARNINGS,PAGE_VIEWS,IMPRESSIONS,CLICKS,PAGE_VIEWS_RPM,COST_PER_CLICK")

    echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
rows = data.get('rows', [])
headers = [h.get('name','') for h in data.get('headers',[])]
if not rows:
    print('  No data available')
    sys.exit()
cells = rows[0].get('cells', [])
labels = {
    'ESTIMATED_EARNINGS': 'Earnings',
    'PAGE_VIEWS': 'Page Views',
    'IMPRESSIONS': 'Ad Impressions',
    'CLICKS': 'Clicks',
    'PAGE_VIEWS_RPM': 'Page RPM',
    'COST_PER_CLICK': 'CPC',
}
for i, h in enumerate(headers):
    val = cells[i].get('value', '0') if i < len(cells) else '0'
    label = labels.get(h, h)
    if h in ('ESTIMATED_EARNINGS', 'PAGE_VIEWS_RPM', 'COST_PER_CLICK'):
        # Convert micros to currency
        try:
            v = float(val) / 1000000
            val = f'£{v:.2f}'
        except:
            pass
    print(f'  {label:.<30} {val}')
"
    echo ""
}

daily_report() {
    local start="$1"
    local end="$2"
    local label="$3"

    echo "============================================================"
    echo "  DAILY BREAKDOWN — ${label}"
    echo "============================================================"

    local result=$(adsense_report "$start" "$end" "DATE" "ESTIMATED_EARNINGS,PAGE_VIEWS,IMPRESSIONS,CLICKS" "30")

    echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
rows = data.get('rows', [])
if not rows:
    print('  No data')
    sys.exit()
print(f'  {\"Date\":<15} {\"Earnings\":>10} {\"Views\":>8} {\"Impr\":>8} {\"Clicks\":>7}')
print(f'  {\"-\"*15} {\"-\"*10} {\"-\"*8} {\"-\"*8} {\"-\"*7}')
for r in rows:
    cells = r.get('cells', [])
    date = cells[0].get('value', '') if len(cells) > 0 else ''
    earnings = cells[1].get('value', '0') if len(cells) > 1 else '0'
    views = cells[2].get('value', '0') if len(cells) > 2 else '0'
    impr = cells[3].get('value', '0') if len(cells) > 3 else '0'
    clicks = cells[4].get('value', '0') if len(cells) > 4 else '0'
    try:
        e = float(earnings) / 1000000
        earnings = f'£{e:.2f}'
    except:
        pass
    print(f'  {date:<15} {earnings:>10} {views:>8} {impr:>8} {clicks:>7}')
"
    echo ""
}

pages_report() {
    local start="$1"
    local end="$2"
    local label="$3"

    echo "============================================================"
    echo "  TOP EARNING PAGES — ${label}"
    echo "============================================================"

    local result=$(adsense_report "$start" "$end" "PAGE_URL" "ESTIMATED_EARNINGS,PAGE_VIEWS,IMPRESSIONS,CLICKS,PAGE_VIEWS_RPM" "20")

    echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
rows = data.get('rows', [])
if not rows:
    print('  No data')
    sys.exit()
print(f'  {\"Page\":<50} {\"Earnings\":>9} {\"Views\":>7} {\"RPM\":>8}')
print(f'  {\"-\"*50} {\"-\"*9} {\"-\"*7} {\"-\"*8}')
for r in rows:
    cells = r.get('cells', [])
    page = cells[0].get('value', '')[:50] if len(cells) > 0 else ''
    earnings = cells[1].get('value', '0') if len(cells) > 1 else '0'
    views = cells[2].get('value', '0') if len(cells) > 2 else '0'
    rpm = cells[5].get('value', '0') if len(cells) > 5 else '0'
    try:
        e = float(earnings) / 1000000
        earnings = f'£{e:.2f}'
    except:
        pass
    try:
        r_val = float(rpm) / 1000000
        rpm = f'£{r_val:.2f}'
    except:
        pass
    print(f'  {page:<50} {earnings:>9} {views:>7} {rpm:>8}')
"
    echo ""
}

countries_report() {
    local start="$1"
    local end="$2"

    echo "============================================================"
    echo "  EARNINGS BY COUNTRY"
    echo "============================================================"

    local result=$(adsense_report "$start" "$end" "COUNTRY_NAME" "ESTIMATED_EARNINGS,PAGE_VIEWS,CLICKS" "10")

    echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
rows = data.get('rows', [])
if not rows:
    print('  No data')
    sys.exit()
print(f'  {\"Country\":<25} {\"Earnings\":>9} {\"Views\":>8} {\"Clicks\":>7}')
print(f'  {\"-\"*25} {\"-\"*9} {\"-\"*8} {\"-\"*7}')
for r in rows:
    cells = r.get('cells', [])
    country = cells[0].get('value', '')[:25] if len(cells) > 0 else ''
    earnings = cells[1].get('value', '0') if len(cells) > 1 else '0'
    views = cells[2].get('value', '0') if len(cells) > 2 else '0'
    clicks = cells[3].get('value', '0') if len(cells) > 3 else '0'
    try:
        e = float(earnings) / 1000000
        earnings = f'£{e:.2f}'
    except:
        pass
    print(f'  {country:<25} {earnings:>9} {views:>8} {clicks:>7}')
"
    echo ""
}

# ── Main ────────────────────────────────────────────────────

MODE="${1:---7days}"

case "$MODE" in
    --today)
        overview_report "$TODAY" "$TODAY" "Today"
        ;;
    --7days|"")
        overview_report "$DAYS7" "$TODAY" "Last 7 Days"
        daily_report "$DAYS7" "$TODAY" "Last 7 Days"
        ;;
    --30days)
        overview_report "$DAYS30" "$TODAY" "Last 30 Days"
        daily_report "$DAYS30" "$TODAY" "Last 30 Days"
        ;;
    --pages)
        pages_report "$DAYS7" "$TODAY" "Last 7 Days"
        ;;
    --countries)
        countries_report "$DAYS7" "$TODAY"
        ;;
    --all)
        overview_report "$DAYS7" "$TODAY" "Last 7 Days"
        daily_report "$DAYS7" "$TODAY" "Last 7 Days"
        pages_report "$DAYS7" "$TODAY" "Last 7 Days"
        countries_report "$DAYS7" "$TODAY"
        ;;
    *)
        echo "Usage: ./build-adsense.sh [--today|--7days|--30days|--pages|--countries|--all]"
        ;;
esac
