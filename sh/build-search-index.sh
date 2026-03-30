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

  if [ -n "$title" ] && [ "$title" != "Teamz Lab Tools" ]; then
    echo "  {t:'$title',d:'$desc',h:'/$slug/'}," >> "$OUTPUT"
  fi
done

echo "];" >> "$OUTPUT"

search_count=$(grep -c "^  {" "$OUTPUT")
echo "  Search: $search_count tools indexed"

# === Auto-update cache buster ===
DATEVER=$(date +%Y%m%d%H%M)
sed -i '' "s|search-index.js?v=[0-9]*|search-index.js?v=$DATEVER|" "$BASE/index.html" 2>/dev/null

# === Auto-update homepage card counts ===
echo ""
echo "=== Updating homepage card counts ==="
for hub in ai evergreen dev text image uidesign tools freelance work diagnostic career student housing creator software compliance eu ramadan apple auto health kids music sports weather; do
  actual=$(find "$BASE/$hub" -name "index.html" -not -path "$BASE/$hub/index.html" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$actual" -gt 0 ]; then
    # Update the count in the homepage card for this hub
    # Match: href="/hub/" ... <p>NUMBER free ... and replace NUMBER with actual
    sed -i '' "s|href=\"/$hub/\" class=\"tool-card\"><div class=\"card\"><h3>\([^<]*\)</h3><p>[0-9]* free|href=\"/$hub/\" class=\"tool-card\"><div class=\"card\"><h3>\1</h3><p>$actual free|" "$BASE/index.html" 2>/dev/null
  fi
done

# Update search placeholder count
total_tools=$(find "$BASE" -path "*/*/index.html" -not -path "*/about/*" -not -path "*/contact/*" -not -path "*/privacy/*" -not -path "*/terms/*" -not -path "*/docs/*" -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/.claude/*" | wc -l | tr -d ' ')
sed -i '' "s|Search [0-9]*+ tools|Search ${total_tools}+ tools|" "$BASE/index.html" 2>/dev/null
echo "  Homepage: updated all card counts + search shows ${total_tools}+ tools"

echo ""
echo "=== Done ==="

# Rebuild llms.txt + llms-full.txt (AI search engine index, per llmstxt.org spec)
# Spec: https://llmstxt.org — by Jeremy Howard
# llms.txt = curated navigation index (under 10KB, like Stripe/Vercel)
# llms-full.txt = complete tool index (can be large, for RAG/deep reference)
(
cd "$BASE" || exit 1
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
    'ae':'UAE','au':'Australia','bd':'Bangladesh','ca':'Canada','de':'Germany','eg':'Egypt',
    'eu':'EU Consumer','fi':'Finland','fr':'France','gh':'Ghana','id':'Indonesia','in':'India',
    'it':'Italy','jp':'Japan','ke':'Kenya','ma':'Morocco','my':'Malaysia','ng':'Nigeria',
    'nl':'Netherlands','no':'Norway','ph':'Philippines','sa':'Saudi Arabia','se':'Sweden',
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

# ─── llms.txt (curated index, spec-compliant, under 10KB) ───
# Per llmstxt.org: H1, blockquote summary, metadata, then curated H2 sections
L = [
'# Teamz Lab Tools',
'',
f'> {total}+ free browser-based tools and calculators. All tools run client-side with zero data collection, no login, and no server processing. Covers finance, health, developer utilities, AI writing, design, and country-specific calculators across {hubs_count} categories.',
'',
'- Website: https://tool.teamzlab.com',
'- Full tool index: https://tool.teamzlab.com/llms-full.txt',
'- Sitemap: https://tool.teamzlab.com/sitemap.xml',
'',
'## Popular Tools',
'',
'- [BMI Calculator](https://tool.teamzlab.com/evergreen/bmi-calculator/): Body mass index with health categories',
'- [QR Code Generator](https://tool.teamzlab.com/evergreen/qr-code-generator/): QR codes for URLs, text, Wi-Fi, vCard',
'- [JSON Formatter](https://tool.teamzlab.com/dev/json-formatter/): Format, validate, and beautify JSON',
'- [Typing Speed Test](https://tool.teamzlab.com/tools/typing-speed-test/): WPM test with accuracy tracking',
'- [Age Calculator](https://tool.teamzlab.com/evergreen/age-calculator/): Exact age in years, months, days',
'- [Tip Calculator](https://tool.teamzlab.com/restaurant/tip-calculator/): Tip amount and bill splitting',
'- [Personal Loan Calculator](https://tool.teamzlab.com/evergreen/personal-loan-calculator/): Monthly payments and amortization',
'- [AI Text Summarizer](https://tool.teamzlab.com/ai/article-summarizer/): Summarize text privately in-browser',
'- [Resume ATS Checker](https://tool.teamzlab.com/career/ats-resume-checker/): ATS compatibility scoring',
'- [Scientific Calculator](https://tool.teamzlab.com/evergreen/scientific-calculator/): Trig, logs, constants, and expressions',
'- [Pomodoro Timer](https://tool.teamzlab.com/evergreen/pomodoro-timer/): Focus timer with work/break cycles',
'- [Color Palette Generator](https://tool.teamzlab.com/dev/color-palette-generator/): Harmonious palettes from any color',
'- [Image Resizer](https://tool.teamzlab.com/image/image-resizer/): Resize images locally, never uploaded',
'- [Countdown Timer](https://tool.teamzlab.com/tools/countdown-timer/): Timer with presets and alarm',
'- [Stopwatch](https://tool.teamzlab.com/tools/stopwatch/): Stopwatch with lap times',
'',
'## Categories',
'',
]
# List each hub as a category with tool count and hub page link
for hub in main:
    name = hub_names.get(hub, hub.title())
    count = len(tools_by_hub[hub])
    L.append(f'- [{name}](https://tool.teamzlab.com/{hub}/): {count} tools')
L.append('')

# Country hubs as Optional section (per spec)
L.append('## Optional')
L.append('')
L.append('Country-specific finance, tax, and utility tools:')
L.append('')
for hub in country:
    name = hub_names.get(hub, hub.title())
    count = len(tools_by_hub[hub])
    L.append(f'- [{name}](https://tool.teamzlab.com/{hub}/): {count} tools')
L.append('')

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

print(f'  llms.txt: {llms_size // 1024}KB, {hubs_count} categories (spec target: <10KB)')
print(f'  llms-full.txt: {total} tools (full descriptions)')
" 2>/dev/null
)
