#!/usr/bin/env bash
# ============================================================
#  Teamz Lab Tools — Microsoft Clarity Analytics
#  Pulls bot detection, traffic, engagement, and UX metrics
#  Token: ~/.config/teamzlab/clarity-token.txt
#  API: https://www.clarity.ms/export-data/api/v1/project-live-insights
#  Limit: 10 requests/day, max 3 days, max 3 dimensions
# ============================================================
set -euo pipefail

TOKEN_FILE="$HOME/.config/teamzlab/clarity-token.txt"
API="https://www.clarity.ms/export-data/api/v1/project-live-insights"
DAYS="${1:-3}"  # Default: 3 days

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "ERROR: Clarity token not found at $TOKEN_FILE"
  echo "Generate one: Clarity → Settings → Data Export → Generate new API token"
  exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")

fetch() {
  local params="$1"
  curl -sf "${API}?numOfDays=${DAYS}&${params}" \
    --header "Content-Type: application/json" \
    --header "Authorization: Bearer ${TOKEN}" 2>/dev/null
}

echo "============================================================"
echo "  CLARITY REPORT — Last ${DAYS} Day(s)"
echo "============================================================"

# --- Request 1: Traffic by Country ---
echo ""
echo "  BOT vs HUMAN TRAFFIC — By Country"
echo "  ----------------------------------------------------------"
fetch "dimension1=Country" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for m in data:
    if m['metricName'] == 'Traffic':
        rows = []
        tr, tb = 0, 0
        for i in m['information']:
            r = int(i.get('totalSessionCount',0))
            b = int(i.get('totalBotSessionCount',0))
            u = int(i.get('distinctUserCount',0))
            t = r + b
            tr += r; tb += b
            if t > 0: rows.append((i['Country'], r, b, u, t))
        print(f\"  {'Country':<25} {'Real':>8} {'Bots':>8} {'Users':>8} {'Bot%':>6}\")
        print(f\"  {'-'*57}\")
        for c,r,b,u,t in sorted(rows, key=lambda x:x[4], reverse=True):
            print(f\"  {c:<25} {r:>8} {b:>8} {u:>8} {b*100//t:>5}%\")
        g = tr + tb
        print(f\"  {'-'*57}\")
        print(f\"  {'TOTAL':<25} {tr:>8} {tb:>8} {'':>8} {tb*100//g:>5}%\")
        print()
        print(f\"  Real sessions: {tr} ({tr*100//g}%)\")
        print(f\"  Bot sessions:  {tb} ({tb*100//g}%)\")
        print(f\"  Total:         {g}\")
" 2>/dev/null || echo "  ERROR: API request failed (quota exceeded or invalid token)"

# --- Request 2: Traffic by Source + Device ---
echo ""
echo "  BOT vs HUMAN TRAFFIC — By Source & Device"
echo "  ----------------------------------------------------------"
fetch "dimension1=Source&dimension2=Device" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for m in data:
    if m['metricName'] == 'Traffic':
        rows = []
        for i in m['information']:
            src = i.get('Source','') or '(direct)'
            dev = i.get('Device','')
            r = int(i.get('totalSessionCount',0))
            b = int(i.get('totalBotSessionCount',0))
            t = r + b
            if t > 0: rows.append((src, dev, r, b, t))
        print(f\"  {'Source':<30} {'Device':<10} {'Real':>8} {'Bots':>8} {'Bot%':>6}\")
        print(f\"  {'-'*65}\")
        for s,d,r,b,t in sorted(rows, key=lambda x:x[4], reverse=True):
            print(f\"  {s:<30} {d:<10} {r:>8} {b:>8} {b*100//t:>5}%\")
" 2>/dev/null || echo "  ERROR: API request failed"

# --- Request 3: Engagement + Scroll + UX Issues ---
echo ""
echo "  ENGAGEMENT & UX METRICS — By Source"
echo "  ----------------------------------------------------------"
fetch "dimension1=Source" | python3 -c "
import json, sys
data = json.load(sys.stdin)
metrics = {}
for m in data:
    metrics[m['metricName']] = m['information']

# Engagement time
if 'EngagementTime' in metrics:
    print(f\"  {'Source':<30} {'Total(s)':>10} {'Active(s)':>10}\")
    print(f\"  {'-'*52}\")
    for i in sorted(metrics['EngagementTime'], key=lambda x: int(x.get('totalTime',0)), reverse=True):
        src = i.get('Source','') or '(direct)'
        print(f\"  {src:<30} {i.get('totalTime','0'):>10} {i.get('activeTime','0'):>10}\")

# Scroll depth
if 'ScrollDepth' in metrics:
    print()
    print(f\"  {'Source':<30} {'Avg Scroll%':>12}\")
    print(f\"  {'-'*44}\")
    for i in sorted(metrics['ScrollDepth'], key=lambda x: x.get('averageScrollDepth',0), reverse=True):
        src = i.get('Source','') or '(direct)'
        print(f\"  {src:<30} {i.get('averageScrollDepth',0):>11.1f}%\")

# Dead clicks / rage clicks
for name in ['DeadClickCount', 'RageClickCount', 'ScriptErrorCount']:
    if name in metrics:
        has_issues = any(float(i.get('sessionsWithMetricPercentage',0)) > 0 for i in metrics[name])
        if has_issues:
            print()
            print(f\"  {name}:\")
            for i in metrics[name]:
                pct = float(i.get('sessionsWithMetricPercentage',0))
                if pct > 0:
                    src = i.get('Source','') or '(direct)'
                    print(f\"    {src:<28} {pct:.1f}% of sessions affected ({i.get('subTotal','0')} total)\")
" 2>/dev/null || echo "  ERROR: API request failed"

echo ""
echo "============================================================"
echo "  Dashboard: https://clarity.microsoft.com/projects/view/w1hpj87iy0/dashboard"
echo "  API limit: ${DAYS}/3 days used, 10 requests/day max"
echo "============================================================"
