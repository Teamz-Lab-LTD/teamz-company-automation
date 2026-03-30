#!/usr/bin/env python3
"""Generate 30 city-specific salary comparison pages from the base tool."""
import os, re, json

SITE_URL = "https://tool.teamzlab.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Read the base tool
with open(os.path.join(ROOT, "evergreen/salary-comparison-by-city/index.html"), "r") as f:
    base_html = f.read()

# Extract the JS block
script_match = re.search(
    r'<script src="/shared/js/tool-engine\.js"></script>\s*<script>(.*?)</script>',
    base_html, re.DOTALL
)
js_block = script_match.group(1) if script_match else ""

CITIES = {
    "new-york":      {"name": "New York", "country": "USA", "index": 100, "avg": "$85,000", "note": "the financial capital of the world. Manhattan rents average over $3,500/month, but salaries in finance and tech compensate."},
    "san-francisco": {"name": "San Francisco", "country": "USA", "index": 95, "avg": "$95,000", "note": "the tech capital with some of the highest rents in the US. Software engineers command premium salaries."},
    "los-angeles":   {"name": "Los Angeles", "country": "USA", "index": 80, "avg": "$65,000", "note": "the entertainment capital with moderate costs. Housing varies from affordable suburbs to expensive Westside."},
    "chicago":       {"name": "Chicago", "country": "USA", "index": 68, "avg": "$60,000", "note": "an affordable major city with strong finance, healthcare, and tech job markets."},
    "houston":       {"name": "Houston", "country": "USA", "index": 60, "avg": "$58,000", "note": "one of the most affordable major US cities with no state income tax. Energy sector drives high salaries."},
    "miami":         {"name": "Miami", "country": "USA", "index": 78, "avg": "$55,000", "note": "a growing tech and finance hub with no state income tax. Housing costs have risen sharply since 2020."},
    "seattle":       {"name": "Seattle", "country": "USA", "index": 82, "avg": "$80,000", "note": "a major tech hub (Amazon, Microsoft) with no state income tax. High housing costs offset by strong salaries."},
    "boston":        {"name": "Boston", "country": "USA", "index": 85, "avg": "$70,000", "note": "a biotech and education hub with high housing costs. World-class universities and hospitals drive demand."},
    "denver":        {"name": "Denver", "country": "USA", "index": 70, "avg": "$62,000", "note": "a growing tech scene with moderate costs compared to coastal cities and an attractive outdoor lifestyle."},
    "austin":        {"name": "Austin", "country": "USA", "index": 65, "avg": "$65,000", "note": "a booming tech hub with no state income tax. Tesla, Apple, and Google have significant presences."},
    "dallas":        {"name": "Dallas", "country": "USA", "index": 58, "avg": "$57,000", "note": "one of the most affordable major US cities with no state income tax and a strong job market."},
    "atlanta":       {"name": "Atlanta", "country": "USA", "index": 62, "avg": "$55,000", "note": "an affordable Southern hub with growing tech and media sectors and a diverse economy."},
    "washington-dc": {"name": "Washington DC", "country": "USA", "index": 83, "avg": "$75,000", "note": "the seat of US government with high salaries in policy, consulting, and government contracting."},
    "london":        {"name": "London", "country": "UK", "index": 85, "avg": "\u00a345,000", "note": "Europe's financial capital with high housing costs. Salaries in finance and tech are among Europe's highest."},
    "zurich":        {"name": "Zurich", "country": "Switzerland", "index": 115, "avg": "CHF 100,000", "note": "the most expensive city on this list. Swiss salaries are the highest in Europe but groceries and housing match."},
    "paris":         {"name": "Paris", "country": "France", "index": 78, "avg": "\u20ac42,000", "note": "Europe's cultural capital with moderate costs. High income taxes are offset by strong social benefits."},
    "berlin":        {"name": "Berlin", "country": "Germany", "index": 60, "avg": "\u20ac45,000", "note": "one of the most affordable capitals in Western Europe with a growing tech startup scene."},
    "amsterdam":     {"name": "Amsterdam", "country": "Netherlands", "index": 72, "avg": "\u20ac50,000", "note": "a compact city with a strong tech and creative sector. Housing is tight but cycling reduces transport costs."},
    "munich":        {"name": "Munich", "country": "Germany", "index": 75, "avg": "\u20ac55,000", "note": "Germany's most expensive city and a hub for automotive and engineering. BMW, Siemens drive high salaries."},
    "stockholm":     {"name": "Stockholm", "country": "Sweden", "index": 70, "avg": "SEK 42,000/mo", "note": "a tech-forward Nordic capital with high taxes but excellent public services. Home to Spotify."},
    "dublin":        {"name": "Dublin", "country": "Ireland", "index": 73, "avg": "\u20ac50,000", "note": "Europe's tech hub hosting Apple, Google, and Meta's European HQs. High housing costs but competitive salaries."},
    "copenhagen":    {"name": "Copenhagen", "country": "Denmark", "index": 80, "avg": "DKK 45,000/mo", "note": "a high-cost Nordic city with excellent work-life balance and world-class public services."},
    "singapore":     {"name": "Singapore", "country": "Singapore", "index": 82, "avg": "SGD 65,000", "note": "Asia's financial hub with low income taxes but high housing and car costs."},
    "tokyo":         {"name": "Tokyo", "country": "Japan", "index": 75, "avg": "\u00a55,500,000", "note": "the world's largest metro area with surprisingly moderate housing costs compared to other global cities."},
    "sydney":        {"name": "Sydney", "country": "Australia", "index": 78, "avg": "AUD 85,000", "note": "Australia's largest city with high housing costs, especially near the harbor. Strong finance and tech jobs."},
    "melbourne":     {"name": "Melbourne", "country": "Australia", "index": 72, "avg": "AUD 78,000", "note": "Australia's cultural capital with slightly lower costs than Sydney and a growing tech sector."},
    "hong-kong":     {"name": "Hong Kong", "country": "Hong Kong", "index": 88, "avg": "HKD 350,000", "note": "one of the most expensive housing markets in the world. Low income taxes attract financial professionals."},
    "auckland":      {"name": "Auckland", "country": "New Zealand", "index": 65, "avg": "NZD 70,000", "note": "New Zealand's largest city with a growing housing crisis but beautiful lifestyle and strong healthcare."},
    "toronto":       {"name": "Toronto", "country": "Canada", "index": 68, "avg": "CAD 62,000", "note": "Canada's financial capital with a diverse economy and growing tech scene. Housing costs have risen sharply."},
    "vancouver":     {"name": "Vancouver", "country": "Canada", "index": 72, "avg": "CAD 60,000", "note": "consistently ranked among the world's most livable cities but with very expensive real estate."},
}

NO_TAX_STATES = {"houston", "miami", "seattle", "austin", "dallas"}

count = 0
for slug, data in sorted(CITIES.items()):
    name = data["name"]
    country = data["country"]
    idx = data["index"]
    avg = data["avg"]
    note = data["note"]

    dir_path = f"evergreen/salary-comparison-{slug}"
    os.makedirs(os.path.join(ROOT, dir_path), exist_ok=True)

    vs_ny = f"{abs(100 - idx)}% {'cheaper' if idx < 100 else 'more expensive'} than New York"
    if idx == 100:
        vs_ny = "equal to New York (the baseline)"

    title_tag = f"Cost of Living Salary {name} \u2014 Teamz Lab Tools"
    if len(title_tag) > 60:
        title_tag = f"Salary Calculator {name} \u2014 Teamz Lab Tools"
    if len(title_tag) > 60:
        title_tag = f"{name} Salary Compare \u2014 Teamz Lab Tools"

    desc = f"Compare salaries to {name} (COL index {idx}). See what salary you need to maintain your lifestyle. Free, private calculator."
    if len(desc) > 155:
        desc = desc[:152] + "..."

    expensive = idx > 70
    eq_100k = int(100000 * idx / 100)
    eq_80k_60 = int(80000 * idx / 60)

    tax_note = "Tax advantages (no state income tax)" if slug in NO_TAX_STATES else "Local tax rates"

    # Modify JS to pre-select city
    modified_js = js_block.replace("default: 'new-york'", f"default: '{slug}'", 1)
    modified_js = modified_js.replace("slug: 'evergreen/salary-comparison-by-city'", f"slug: '{dir_path}'")
    modified_js = modified_js.replace("title: 'Salary Comparison by City'", f"title: 'Cost of Living & Salary in {name}'")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_tag}</title>
  <meta name="description" content="{desc}">
  <meta property="og:title" content="{title_tag}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{SITE_URL}/{dir_path}/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Teamz Lab Tools">
  <meta property="og:image" content="{SITE_URL}/og-images/evergreen.png">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{title_tag}">
  <meta name="twitter:description" content="{desc}">
  <link rel="canonical" href="{SITE_URL}/{dir_path}/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/branding/css/teamz-branding.css">
  <link rel="stylesheet" href="/shared/css/tools.css">
</head>
<body>
  <header id="site-header" class="site-header"></header>
  <main class="site-main">
    <div id="breadcrumbs"></div>
    <section class="tool-hero">
      <h1>Cost of Living &amp; Salary in {name}</h1>
      <p class="tool-description">Compare your salary to {name} ({country}). With a cost of living index of {idx} (NYC = 100), {name} is {vs_ny}. See what salary you need \u2014 calculated privately in your browser.</p>
    </section>
    <section id="tool-calculator" class="tool-calculator"></section>
    <div class="ad-slot">Ad Space</div>
    <section class="tool-content">
      <h2>Cost of Living in {name}</h2>
      <p>{name} is {note} The city has a cost of living index of {idx} relative to New York City (100), making it {vs_ny}. Average salaries in {name} are around {avg} per year, though this varies significantly by industry and experience level.</p>
      <p>Housing is typically the largest expense, accounting for 35-40% of total living costs. In {name}, housing costs are {"above" if expensive else "below"} the global city average. Food, transportation, and healthcare make up most of the remaining budget.</p>

      <h2>Salary Comparison: {name} vs Other Cities</h2>
      <p>When comparing salaries across cities, raw numbers can be misleading. A {"higher" if expensive else "lower"} salary in {name} {"may not stretch as far" if expensive else "can go further"} due to {"higher" if expensive else "lower"} living costs. Use this calculator to find the equivalent salary you would need in {name} to match your current standard of living.</p>
      <p>For example, someone earning $100,000 in New York (index 100) would need approximately ${eq_100k:,} in {name} (index {idx}) to maintain the same purchasing power. This accounts for housing, groceries, transport, healthcare, and entertainment.</p>

      <h2>Working and Living in {name}</h2>
      <p>{name} offers {"a high cost of living but strong career opportunities" if expensive else "a relatively affordable lifestyle with growing opportunities"} for professionals. The city's job market is {"competitive but rewarding" if expensive else "growing with increasing demand for skilled workers"}.</p>
      <p>Beyond salary, consider quality of life factors: commute times, public transportation, healthcare access, cultural amenities, and climate. {tax_note} can also significantly impact your take-home pay and should be factored into any relocation decision.</p>
    </section>
    <section id="tool-faqs"></section>
    <section id="related-tools"></section>
  </main>
  <footer id="site-footer" class="site-footer"></footer>
  <script src="/branding/js/theme.js"></script>
  <script src="/shared/js/common.js"></script>
  <script src="/shared/js/tool-engine.js"></script>
  <script>
{modified_js}
    BREADCRUMBS = [
      {{ name: 'Home', url: '/' }},
      {{ name: 'Evergreen Tools', url: '/evergreen/' }},
      {{ name: 'Salary Comparison {name}' }}
    ];

    FAQS = [
      {{ q: 'What is {name}\\'s cost of living index?', a: '{name} has a cost of living index of {idx} relative to New York City (100). This means {name} is approximately {vs_ny} when considering housing, food, transport, and entertainment.' }},
      {{ q: 'What salary do I need in {name} to match $100,000 in New York?', a: 'To match the purchasing power of $100,000 in New York, you would need approximately ${eq_100k:,} in {name}. This accounts for differences in housing, food, and other living costs.' }},
      {{ q: 'What is the average salary in {name}?', a: 'The average salary in {name} is approximately {avg} per year, though this varies by industry, experience, and role. Tech, finance, and healthcare tend to pay above average.' }},
      {{ q: 'Is {name} expensive to live in?', a: '{"Yes, " + name + " is above the global city average for cost of living." if expensive else name + " is relatively affordable compared to other major global cities."} Housing is the biggest factor, accounting for 35-40% of total costs.' }},
      {{ q: 'Does this calculator account for taxes?', a: 'No. This calculator compares purchasing power based on cost of living indices only. Tax rates vary between countries and states. For a complete picture, factor in local income tax, sales tax, and any other applicable taxes.' }}
    ];

    RELATED_TOOLS = [
      {{ slug: 'evergreen/salary-comparison-by-city', name: 'Salary Comparison by City', description: 'Compare salaries across 30+ global cities.' }},
      {{ slug: 'evergreen/salary-negotiation-calculator', name: 'Salary Negotiation Calculator', description: 'Plan your salary negotiation with data.' }},
      {{ slug: 'career/take-home-pay-estimator', name: 'Take-Home Pay Estimator', description: 'Calculate net pay after deductions.' }},
      {{ slug: 'career/offer-comparison-calculator', name: 'Job Offer Comparison', description: 'Compare job offers side by side.' }},
      {{ slug: 'housing/rent-burden-calculator', name: 'Rent Burden Calculator', description: 'Check if your rent is affordable.' }},
      {{ slug: 'evergreen/50-30-20-budget-calculator', name: '50/30/20 Budget Calculator', description: 'Allocate income using the 50/30/20 rule.' }}
    ];
  </script>
</body>
</html>"""

    filepath = os.path.join(ROOT, dir_path, "index.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"  Created: /{dir_path}/")
    count += 1

print(f"\nCreated {count} city salary comparison pages.")
