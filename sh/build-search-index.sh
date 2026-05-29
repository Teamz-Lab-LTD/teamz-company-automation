#!/bin/bash
# Rebuild search-index.js + auto-fix homepage counts + sitemap
# Run after ANY change: ./build-search-index.sh
# Also runs automatically via pre-commit hook

SCRIPTS="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")" && pwd)"
source "$SCRIPTS/lib/config.sh"
teamz_load_config "$0"
BASE="$TEAMZ_HOST_SITE_ROOT"
OUTPUT="$BASE/shared/js/search-index.js"

if [[ "${TEAMZ_PROJECT_TYPE:-website}" == "app" ]]; then
  echo "INFO: build-search-index.sh is website-focused and disabled for TEAMZ_PROJECT_TYPE=app."
  exit 2
fi

echo "=== Rebuilding search index ==="
echo "var TOOL_SEARCH_INDEX = [" > "$OUTPUT"

find "$BASE" -path "*/*/index.html" \
  -not -path "*/about/*" -not -path "*/contact/*" \
  -not -path "*/privacy/*" -not -path "*/terms/*" \
  -not -path "*/docs/*" -not -path "*/node_modules/*" \
  -not -path "*/.git/*" -not -path "*/.claude/*" \
  | sort | while read f; do

  slug=$(echo "$f" | sed "s|$BASE/||" | sed 's|/index.html||')

  title=$(grep -o '<h1>[^<]*</h1>' "$f" | head -1 | sed 's/<[^>]*>//g' | sed "s/'/\\\\'/g" | head -c 100)
  if [ -z "$title" ]; then
    title=$(grep -o '<title>[^<]*</title>' "$f" | head -1 | sed 's/<[^>]*>//g' | sed 's/ — .*//' | sed 's/ | .*//' | sed "s/'/\\\\'/g" | head -c 100)
  fi

  desc=$(grep -o 'name="description" content="[^"]*"' "$f" | head -1 | sed 's/name="description" content="//;s/"$//' | sed "s/'/\\\\'/g" | head -c 150)

  # English search-aliases — pages with native-language titles still findable
  # via English queries on the homepage search bar.
  aliases=$(grep -o 'name="search-aliases" content="[^"]*"' "$f" | head -1 | sed 's/name="search-aliases" content="//;s/"$//' | sed "s/'/\\\\'/g")
  if [ -n "$aliases" ]; then
    desc=$(echo "$desc · $aliases" | head -c 280)
  fi

  if [ -n "$title" ] && [ "$title" != "Teamz Lab Tools" ]; then
    echo "  {t:'$title',d:'$desc',h:'/$slug/'}," >> "$OUTPUT"
  fi
done

echo "];" >> "$OUTPUT"

search_count=$(grep -c "^  {" "$OUTPUT")
echo "  Search: $search_count tools indexed"

# === Auto-update cache buster ===
DATEVER=$(date +%Y%m%d%H%M)
sed -i '' "s|search-index.js?v=[0-9]*|search-index.js?v=$DATEVER|" "$BASE/index.html"

# === Auto-update homepage card counts ===
echo ""
echo "=== Updating homepage card counts ==="
for hub in ai evergreen dev text image uidesign tools freelance work diagnostic career student housing creator software compliance eu ramadan apple auto health kids music sports weather; do
  actual=$(find "$BASE/$hub" -name "index.html" -not -path "$BASE/$hub/index.html" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$actual" -gt 0 ]; then
    # Update the count in the homepage card for this hub
    # Match: href="/hub/" ... <p>NUMBER free ... and replace NUMBER with actual
    sed -i '' "s|href=\"/$hub/\" class=\"tool-card\"><div class=\"card\"><h3>\([^<]*\)</h3><p>[0-9]* free|href=\"/$hub/\" class=\"tool-card\"><div class=\"card\"><h3>\1</h3><p>$actual free|" "$BASE/index.html"
  fi
done

# Update search placeholder count
total_tools=$(find "$BASE" -path "*/*/index.html" -not -path "*/about/*" -not -path "*/contact/*" -not -path "*/privacy/*" -not -path "*/terms/*" -not -path "*/docs/*" -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/.claude/*" | wc -l | tr -d ' ')
sed -i '' "s|Search [0-9]*+ tools|Search ${total_tools}+ tools|" "$BASE/index.html"
echo "  Homepage: updated all card counts + search shows ${total_tools}+ tools"

echo ""
echo "=== Done ==="

# Rebuild llms.txt + llms-full.txt (AI search engine index, per llmstxt.org spec)
# Spec: https://llmstxt.org — by Jeremy Howard
# llms.txt = curated navigation index (under 10KB, like Stripe/Vercel)
# llms-full.txt = complete tool index (can be large, for RAG/deep reference)
echo ""
echo "=== Rebuilding llms.txt + llms-full.txt (AI search index) ==="
(
cd "$BASE" || { echo "ERROR: cd \$BASE failed" >&2; exit 1; }
python3 -c "
import glob, re, html

hub_names = {
    '3d':'3D Tools','ai':'AI Tools','accessibility':'Accessibility','amazon':'Amazon Seller',
    'apple':'Apple & iPhone','astrology':'Astrology','auto':'Automotive','baby':'Baby & Pregnancy',
    'career':'Career Tools','compliance':'Compliance','cooking':'Cooking','creator':'Creator Tools',
    'cricket':'Cricket','crypto':'Crypto & Web3','design':'Design','dev':'Developer Tools',
    'diagnostic':'Diagnostic Tools','diy':'DIY','eldercare':'Elder Care','evergreen':'Everyday Calculators',
    'football':'Football','freelance':'Freelance & Invoice','gaming':'Gaming','garden':'Garden',
    'grooming':'Grooming','health':'Health & Wellness','home':'Home & DIY','housing':'Housing & Energy',
    'image':'Image Tools','kids':'Kids & Education','legal':'Legal','math':'Math Tools',
    'military':'Military & Veterans','mobile':'Mobile Dev','music':'Music & Audio',
    'pest':'Pest Control','pet':'Pet Care','ramadan':'Ramadan & Eid','real-estate':'Real Estate',
    'restaurant':'Restaurant & Food','safety':'Safety','security':'Security','seo':'SEO Tools',
    'shopping':'Shopping','software':'Software Cost','sports':'Sports & Fitness',
    'student':'Student Tools','text':'Text Tools','tools':'Utilities','uidesign':'UI Design',
    'video':'Video Tools','weather':'Weather & Outdoor','wedding':'Wedding','work':'Work & Payroll',
    'ae':'UAE','at':'Austria','au':'Australia','bd':'Bangladesh','be':'Belgium','ca':'Canada',
    'ch':'Switzerland','cz':'Czech Republic','de':'Germany','dk':'Denmark','eg':'Egypt',
    'es':'Spain','eu':'EU Consumer','fi':'Finland','fr':'France','gh':'Ghana',
    'id':'Indonesia','ie':'Ireland','il':'Israel','in':'India','it':'Italy',
    'jp':'Japan','ke':'Kenya','lu':'Luxembourg','ma':'Morocco','my':'Malaysia',
    'ng':'Nigeria','nl':'Netherlands','no':'Norway','nz':'New Zealand',
    'ph':'Philippines','pl':'Poland','pt':'Portugal','sa':'Saudi Arabia','se':'Sweden',
    'sg':'Singapore','uk':'United Kingdom','us':'United States','vn':'Vietnam','za':'South Africa',
}

tools_by_hub = {}
for f in sorted(glob.glob('*/*/index.html')):
    parts = f.split('/')
    if len(parts) != 3: continue
    hub = parts[0]
    if hub in ('about','contact','privacy','terms','docs','shared','branding','og-images','icons','__pycache__','.git','config','fonts'): continue
    with open(f) as fh:
        content = fh.read()
    if 'http-equiv=\"refresh\"' in content: continue
    if 'window.location' in content and '<h1' not in content: continue
    t = re.search(r'<title>(.*?)</title>', content)
    d = re.search(r'name=\"description\" content=\"([^\"]*)\"', content)
    if not t: continue
    title = html.unescape(t.group(1).replace(' — Teamz Lab Tools','').replace(' | Teamz Lab Tools','').strip())
    full_desc = html.unescape(d.group(1).strip()) if d else ''
    short_desc = full_desc.split('. ')[0].rstrip('.') if '. ' in full_desc else full_desc[:80]
    url = 'https://tool.teamzlab.com/' + f.replace('/index.html','') + '/'
    if hub not in tools_by_hub: tools_by_hub[hub] = []
    tools_by_hub[hub].append((title, url, short_desc, full_desc))

total = sum(len(v) for v in tools_by_hub.values())
hubs_count = len(tools_by_hub)
main = sorted([h for h in tools_by_hub if len(h)>2 or h in ('ai','us','uk','eu','3d')], key=lambda h: hub_names.get(h,h))
country = sorted([h for h in tools_by_hub if len(h)<=2 and h not in ('ai','us','uk','eu','3d')], key=lambda h: hub_names.get(h,h))

# ─── llms.txt (curated index, spec-compliant, under 10KB per llmstxt.org) ───
# GEO-optimized per Princeton research: authority-first blockquote, statistics,
# data-driven Popular Tools picked by 90-day GSC clicks. AlwaysReady block is
# NOT folded in (lives in llms-full only) to keep this file under spec cap.
L = [
'# Teamz Lab Tools',
'',
f'> {total}+ free browser-based calculators and SEO/dev/AI tools across {hubs_count} categories. All tools run 100% client-side — zero data collection, no login, no server processing, no telemetry. Calculator data sourced from official regulators including IRS, HMRC, ATO, IRAS, UEFA, FIFA, BMF, Bundesbank, and national tax authorities of 40+ countries. Year stamps reflect the current tax and regulatory cycle and are updated continuously.',
'',
'- Website: https://tool.teamzlab.com',
'- Full tool index: https://tool.teamzlab.com/llms-full.txt',
'- Sitemap: https://tool.teamzlab.com/sitemap.xml',
'',
'## Popular Tools',
'',
'Ranked by 90-day Google Search clicks. Mix of evergreen calculators and active tournament / seasonal tools.',
'',
'- [IPL 2026 Playoff Calculator](https://tool.teamzlab.com/cricket/ipl-playoff-calculator/): IPL playoff qualification scenarios — Net Run Rate (NRR), points table permutations, top-4 paths for all 10 franchises with live IPL 2026 fixtures.',
'- [UK Probation Period Calculator](https://tool.teamzlab.com/work/probation-period-calculator/): UK probation end-date calculator with statutory notice rules per Employment Rights Act 1996 and business-day counting.',
'- [通勤手当 計算サイト](https://tool.teamzlab.com/jp/tsuukin-hi-keisan/): Japanese commuting allowance calculator with non-taxable limit (非課税限度額) per National Tax Agency rules for train, bus, bicycle, and car.',
'- [Bangladesh Electricity Bill Calculator](https://tool.teamzlab.com/bd/electricity-bill-calculator/): DESCO, DPDC, REB, BPDB tariff slab calculator using current BERC rates, demand charge, VAT, and meter rent.',
'- [UCL Bracket Predictor 2025/26](https://tool.teamzlab.com/football/ucl-bracket-predictor/): Predict the 2025/26 UEFA Champions League bracket from Round of 16 to the Munich Final on 30 May 2026.',
'- [UCL League Phase Simulator](https://tool.teamzlab.com/football/ucl-group-stage-simulator/): Simulate the new 36-team UEFA Champions League league phase (8 matches each, top 8 auto-qualify to R16).',
'- [FIFA World Cup 2026 Bracket Maker](https://tool.teamzlab.com/football/fifa-world-cup-2026-bracket-maker/): 48-team World Cup 2026 bracket — 12 groups of 4, top 2 + 8 best third-placed advance, 32-team knockout, MetLife Stadium final 19 July 2026.',
'- [Football Salary Calculator](https://tool.teamzlab.com/football/football-salary-calculator/): Net weekly / monthly wage after tax for EPL, La Liga, Bundesliga, Serie A, Ligue 1 with country-specific income tax rates.',
'- [ACA Subsidy Calculator 2026](https://tool.teamzlab.com/us/aca-subsidy-calculator/): US Affordable Care Act premium subsidy eligibility for 2026 plan year using federal poverty level and modified AGI.',
'- [Bangladesh Government Salary Calculator](https://tool.teamzlab.com/bd/govt-salary-calculator/): Bangladesh National Pay Scale 2015 grade-by-grade salary breakdown with house rent, medical, and 9% annual increment.',
'- [Student Attendance Percentage Calculator](https://tool.teamzlab.com/student/attendance-percentage-calculator/): Attendance percentage with classes-to-attend or classes-to-skip calculations against required threshold.',
'- [Einkommensteuer Rechner 2026](https://tool.teamzlab.com/de/einkommensteuer-rechner/): German income tax (Einkommensteuer) calculator with Solidaritätszuschlag, Kirchensteuer, and 2026 Grundfreibetrag per BMF Steuertarif.',
'',
'## Categories',
'',
]
# Compact one-line per hub (general/topical categories) — count without the word tools as suffix saves ~700B
for hub in main:
    name = hub_names.get(hub, hub.title())
    count = len(tools_by_hub[hub])
    L.append(f'- [{name}](https://tool.teamzlab.com/{hub}/): {count}')
L.append('')

# Country hubs as Optional section (per llmstxt.org spec — secondary content)
L.append('## Optional')
L.append('')
L.append('Country-specific tax, payroll, and finance tools per local regulations:')
L.append('')
for hub in country:
    name = hub_names.get(hub, hub.title())
    count = len(tools_by_hub[hub])
    L.append(f'- [{name}](https://tool.teamzlab.com/{hub}/): {count}')
L.append('')

# ─── Auto-trim to honour llmstxt.org 10KB spec target ───
# Pops trailing Popular Tools entries until <=10240B. Categories + Optional
# lists are the navigational core — never trimmed. Floor: keep >=5 popular
# tools so the section still earns its keep. Self-heals as catalog grows.
_SPEC_CAP = 10240
_MIN_POPULAR = 5
try:
    _pop_header_idx = L.index('## Popular Tools')
    _pop_start = _pop_header_idx + 1
    while _pop_start < len(L) and not L[_pop_start].startswith('- ['):
        _pop_start += 1
    _pop_end = _pop_start
    while _pop_end < len(L) and L[_pop_end].startswith('- ['):
        _pop_end += 1
    _kept_popular = _pop_end - _pop_start
    while len('\n'.join(L).encode('utf-8')) > _SPEC_CAP and _kept_popular > _MIN_POPULAR:
        _pop_end -= 1
        L.pop(_pop_end)
        _kept_popular -= 1
    _final_size = len('\n'.join(L).encode('utf-8'))
    if _final_size > _SPEC_CAP:
        print(f'  WARN: llms.txt still {_final_size - _SPEC_CAP}B over 10KB after trimming Popular Tools to floor of {_MIN_POPULAR}. Consider shortening Categories list.')
    else:
        print(f'  llms.txt auto-trimmed: {_kept_popular} popular tools kept, final {_final_size}B (under 10KB spec)')
except ValueError:
    pass

with open('llms.txt','w') as f: f.write('\n'.join(L))
llms_size = len('\n'.join(L).encode('utf-8'))

# ─── llms-full.txt (complete index, all tools with full descriptions) ───
F = [
'# Teamz Lab Tools — Complete Tool Index',
'',
f'> {total}+ free browser-based tools and calculators at tool.teamzlab.com.',
f'> All tools run 100% client-side. No data collection, no login, no server processing.',
'> Works on all devices. Inputs auto-save locally across sessions.',
'',
'- Website: https://tool.teamzlab.com',
f'- Total Tools: {total}+',
f'- Categories: {hubs_count}',
'- Sitemap: https://tool.teamzlab.com/sitemap.xml',
'',
]
for hub in main + country:
    name = hub_names.get(hub, hub.title())
    count = len(tools_by_hub[hub])
    F.append(f'## {name} ({count} tools)')
    for title, url, _, fd in sorted(tools_by_hub[hub], key=lambda x: x[0]):
        F.append(f'- [{title}]({url}): {fd}')
    F.append('')
with open('llms-full.txt','w') as f: f.write('\n'.join(F))

# ─── AlwaysReady Care — append international hub (NOT scanned as standard /hub/tool/ pattern) ───
ARC_BASE = 'https://tool.teamzlab.com/apps/always-ready-care'
ARC_REGIONS = [
    ('UK / England', '/', 'CQC compliance for UK care homes — 5 Key Questions, KLOEs, Reg 17 evidence tracking'),
    ('Australia', '/au/', 'ACQS Aged Care Quality Standards readiness, 8 Standards, Quality Indicators'),
    ('New Zealand', '/nz/', 'Ngā Paerewa NZS 8134:2021 audit readiness, 4 Pae quality domains'),
    ('Ireland', '/ie/', 'HIQA inspection readiness for designated centres, 13 most-flagged areas'),
    ('Germany (Deutsch)', '/de/', 'MD-Prüfung & Pflegegrad, 24.700+ Qualitätsprüfungen, Expertenstandards, SIS'),
    ('Germany (English)', '/de-en/', 'MD audit prep + QPR framework support for German care providers in English'),
    ('United States', '/us/', 'CMS Five-Star Quality Rating + state survey F-tag evidence tracking — waitlist'),
    ('France', '/fr/', 'HAS Qualiscope évaluation externe, 157 critères dont 18 impératifs — liste d attente'),
    ('Japan', '/jp/', 'MHLW介護保険・実地指導/運営指導対応のエビデンス管理 — ウェイティングリスト'),
    ('UAE', '/ae/', 'DoH Abu Dhabi + MoHAP healthcare facility licensing & compliance — waitlist'),
    ('Netherlands', '/nl/', 'IGJ verpleeghuiszorg toezicht + Kwaliteitskader Verpleeghuiszorg — wachtlijst'),
    ('Sweden', '/se/', 'IVO tillsyn äldreomsorg + SoL/LSS-stöd för SÄBO och hemtjänst — väntelista'),
    ('Canada', '/ca/', 'Provincial LTC inspection (Ontario CARES, BC, Alberta, Quebec) — bilingual EN/FR — waitlist'),
    ('Spain', '/es/', 'IMSERSO + 17 comunidades autónomas inspecciones residencias mayores — lista de espera'),
]
ARC_TOOLS = [
    ('CQC Inspection Checklist', '/inspection-checklist/', 'Free interactive 30-item CQC inspection checklist with live scoring'),
    ('CQC Inspection Countdown', '/cqc-inspection-countdown/', 'Predict your next CQC inspection window from your last rating + concerns'),
    ('Inspection Statistics 2025', '/inspection-statistics/', 'CQC, ACQS, MD, HIQA, HealthCERT 2025 stats compared in one page with sources'),
    ('5 Key Questions Framework', '/framework/', 'CQC Single Assessment Framework guide — Safe, Effective, Caring, Responsive, Well-led'),
]

# NOTE: AlwaysReady block intentionally NOT appended to llms.txt — it pushed
# the file 3.4KB over the llmstxt.org 10KB spec target. The product hub is
# already linked from the header bullets and the full block lives in
# llms-full.txt below for AI tools that need the deep regional breakdown.

arc_full = ['', '## AlwaysReady Care — Care Home Compliance Across 14 Countries', '',
    'AlwaysReady Care is a free care home compliance SaaS supporting 14 countries and 13 regulatory frameworks. Built for care managers, registered managers, deputy managers, quality leads, and PDLs. Captures evidence in 60 seconds, AI-tags to regulator criteria, generates inspection packs in one click. Works alongside existing systems (no rip-and-replace).',
    '',
    '### Live Regional Hubs (full product available)', '']
for name, path, desc in ARC_REGIONS[:6]:
    arc_full.append(f'- [AlwaysReady Care — {name}]({ARC_BASE}{path}): {desc}')
arc_full.append('')
arc_full.append('### Waitlist Regions (launching soon, regulator-specific framework support)')
arc_full.append('')
for name, path, desc in ARC_REGIONS[6:]:
    arc_full.append(f'- [AlwaysReady Care — {name}]({ARC_BASE}{path}): {desc}')
arc_full.append('')
arc_full.append('### Free Tools & Reference Resources')
arc_full.append('')
for name, path, desc in ARC_TOOLS:
    arc_full.append(f'- [{name}]({ARC_BASE}{path}): {desc}')
arc_full.append('')
arc_full.append('### Key Statistics (Cited from Official Regulator Reports)')
arc_full.append('')
arc_full.append('- UK: 47% of CQC Requires Improvement providers fail to improve on re-inspection (CQC State of Care 2024/25)')
arc_full.append('- Australia: 19% of residential aged care providers were non-compliant in Q3 2024-25 (ACQS Sector Performance)')
arc_full.append('- Germany: 24,700+ unannounced MD quality audits in 2023, 167,000+ residents directly assessed (MD Bund 8. Pflege-Qualitätsbericht)')
arc_full.append('- Ireland: 840 HIQA inspections in 2024, 84% unannounced (HIQA 15 Years of Regulating Nursing Homes)')
arc_full.append('- New Zealand: 100% of rest home audit summaries published publicly on health.govt.nz (Ngā Paerewa NZS 8134:2021)')
arc_full.append('- USA: CMS uses only 2 most recent surveys for star rating (tightened July 2025); F-tags publicly posted on Care Compare')
arc_full.append('- France: 34.7% of EHPAD reach top grade A; 23% public sector vs 53% private commercial (HAS Qualiscope)')
arc_full.append('- UAE: DoH Abu Dhabi conducted 4,540 licensing audits in 2025, +31% YoY')
arc_full.append('- Sweden: IVO closed 58 facilities in 2024 (47 care + 11 healthcare)')
arc_full.append('')
with open('llms-full.txt','a') as f: f.write('\n'.join(arc_full))

print(f'  AlwaysReady Care: 14 country pages + 4 tools appended to llms-full.txt only (kept out of llms.txt to stay under spec cap)')

# Compute REAL final on-disk size (previous bug: reported pre-append size)
import os
real_llms = os.path.getsize('llms.txt')
real_full = os.path.getsize('llms-full.txt')
spec_cap = 10240  # llmstxt.org target
status = 'OK' if real_llms <= spec_cap else f'OVER BY {real_llms - spec_cap}B'
print(f'  llms.txt: {real_llms}B ({real_llms/1024:.1f}KB), {hubs_count} categories, spec target <{spec_cap}B → {status}')
print(f'  llms-full.txt: {real_full}B ({real_full/1024:.1f}KB), {total} tools (full descriptions)')
if real_llms > spec_cap:
    import sys
    print(f'  WARN: llms.txt still {real_llms - spec_cap}B over 10KB after auto-trim (Popular Tools floor reached). Shorten Categories list to recover.', file=sys.stderr)
"
)

# === Build tools.json for mobile app ===
echo ""
echo "=== Building tools.json (mobile app feed) ==="
python3 "$BASE/scripts/build-tools-json.py" 2>/dev/null || \
  python3 "$SCRIPTS/build-tools-json.py" 2>/dev/null || true

# === Build webview-incompat.json (mobile app auto-redirect list) ===
echo ""
echo "=== Scanning tools for mobile-WebView incompatibilities ==="
python3 "$BASE/scripts/build-webview-incompat.py" || true
