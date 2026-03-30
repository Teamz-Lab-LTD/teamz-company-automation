#!/usr/bin/env python3
"""
Teamz Lab Tools — Content Ideas Engine (FREE, replaces Ubersuggest Content Ideas)
Generates trending content ideas using free APIs.

Usage:
    python3 scripts/build-content-ideas.py                       # Auto-generate ideas for your top niches
    python3 scripts/build-content-ideas.py --niche "calculator"   # Ideas for a specific niche
    python3 scripts/build-content-ideas.py --trending             # Trending topics right now
    python3 scripts/build-content-ideas.py --gaps                 # Content gaps (keywords with no tool)
    python3 scripts/build-content-ideas.py --seasonal             # Seasonal content calendar
    python3 scripts/build-content-ideas.py --competitors          # Ideas from competitor keywords

Data Sources (all FREE):
    - Google Autocomplete (real-time keyword suggestions)
    - Google Trends (trending topics)
    - Your Search Console data (what users search for)
    - Reddit trending (popular topics)
    - Seasonal calendar
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import ssl
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
TOKEN_FILE = Path.home() / ".config" / "teamzlab" / "search-console-token.json"
SITE_URL = "https://tool.teamzlab.com/"
CTX = ssl.create_default_context()

# ── Your existing tool niches (auto-detected from hub structure) ──
NICHES = [
    "calculator", "converter", "generator", "checker", "tester",
    "tax", "salary", "loan", "mortgage", "bmi", "calorie",
    "json", "css", "html", "regex", "developer",
    "resume", "career", "ats",
    "seo", "meta tag", "schema",
    "qr code", "barcode",
    "image", "photo", "meme", "video",
    "crypto", "bitcoin",
    "math", "probability", "statistics",
    "uk tax", "us tax", "india tax",
]

# ── Seasonal Calendar ──
SEASONAL = {
    1: ["new year resolution tools", "budget calculator 2026", "tax season prep", "fitness goal tracker", "detox calculator"],
    2: ["valentine gift calculator", "heart health calculator", "tax refund estimator", "love compatibility test"],
    3: ["spring cleaning checklist", "tax filing tools", "daylight saving time", "ramadan tools", "march madness bracket"],
    4: ["tax deadline calculator", "easter tools", "earth day carbon calculator", "spring allergy tracker", "eid tools"],
    5: ["mother's day gift ideas", "summer budget planner", "graduation tools", "memorial day", "garden planner"],
    6: ["father's day tools", "summer vacation budget", "back to school prep", "world cup tools", "pride month"],
    7: ["summer fitness tools", "vacation cost calculator", "independence day", "heat index calculator"],
    8: ["back to school tools", "college cost calculator", "fall budget planner", "football season tools"],
    9: ["fall tools", "budget reset calculator", "school year planner", "apple event tools", "football stats"],
    10: ["halloween tools", "holiday budget planner", "black friday prep", "fall fitness", "oktoberfest"],
    11: ["black friday calculator", "thanksgiving tools", "holiday shopping budget", "gift budget tracker", "cyber monday"],
    12: ["christmas tools", "new year tools", "holiday gift calculator", "year in review", "annual tax recap"],
}


def refresh_token():
    if not TOKEN_FILE.exists():
        return None
    token_data = json.loads(TOKEN_FILE.read_text())
    data = urllib.parse.urlencode({
        "client_id": token_data["client_id"],
        "client_secret": token_data["client_secret"],
        "refresh_token": token_data["refresh_token"],
        "grant_type": "refresh_token"
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=CTX)
        return json.loads(resp.read()).get("access_token")
    except Exception:
        return None


def google_autocomplete(keyword, lang="en", country="us"):
    suggestions = []
    prefixes = ["", "best ", "free ", "online ", "how to ", "what is ", "why ", "vs "]
    for prefix in prefixes:
        query = f"{prefix}{keyword}".strip()
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(query)}&hl={lang}&gl={country}"
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")
            resp = urllib.request.urlopen(req, timeout=5, context=CTX)
            data = json.loads(resp.read())
            if len(data) > 1:
                for s in data[1]:
                    if s.lower() != keyword.lower() and s not in suggestions:
                        suggestions.append(s)
        except Exception:
            pass
    return suggestions[:15]


def google_trends_suggestions(keyword):
    """Get related queries from Google Trends."""
    url = f"https://trends.google.com/trends/api/autocomplete/{urllib.parse.quote(keyword)}?hl=en-US"
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=5, context=CTX)
        raw = resp.read().decode()
        # Google Trends prepends ")]}'"
        if raw.startswith(")]}'"):
            raw = raw[5:]
        data = json.loads(raw)
        topics = []
        for item in data.get("default", {}).get("topics", []):
            title = item.get("title", "")
            if title:
                topics.append(title)
        return topics
    except Exception:
        return []


def sc_top_queries(token, limit=100):
    """Get top queries from Search Console."""
    encoded = urllib.parse.quote(SITE_URL, safe="")
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query"
    body = {
        "startDate": (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d"),
        "endDate": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        "dimensions": ["query"],
        "rowLimit": limit,
        "dataState": "all"
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-goog-user-project", "teamzlab-tools")
    try:
        resp = urllib.request.urlopen(req, context=CTX)
        result = json.loads(resp.read())
        return [(r["keys"][0], r.get("impressions", 0), r.get("clicks", 0), r.get("position", 100)) for r in result.get("rows", [])]
    except Exception:
        return []


def get_existing_tools():
    """Get set of existing tool slugs."""
    tools = set()
    for html_file in PROJECT_DIR.rglob("*/index.html"):
        rel = str(html_file.relative_to(PROJECT_DIR).parent)
        if rel.count("/") == 1 and not rel.startswith(("shared", "branding", "icons", "docs", "scripts", "og-", ".")):
            tools.add(rel)
    return tools


def classify_idea_type(keyword):
    """Classify what type of tool this keyword suggests."""
    kw = keyword.lower()
    if any(w in kw for w in ["calculator", "calculate", "compute"]):
        return "Calculator"
    elif any(w in kw for w in ["converter", "convert", "to"]):
        return "Converter"
    elif any(w in kw for w in ["generator", "generate", "maker", "creator"]):
        return "Generator"
    elif any(w in kw for w in ["checker", "check", "validator", "tester", "test"]):
        return "Checker"
    elif any(w in kw for w in ["how to", "guide", "tutorial"]):
        return "Guide/Content"
    elif any(w in kw for w in ["best", "top", "compare", "vs"]):
        return "Comparison"
    else:
        return "Tool"


def estimate_priority(keyword, impressions=0):
    """Estimate content priority (1=highest)."""
    kw = keyword.lower()
    # High-value niches
    if any(w in kw for w in ["tax", "salary", "mortgage", "loan", "insurance", "payroll"]):
        return 1
    if any(w in kw for w in ["resume", "career", "ats", "interview"]):
        return 1
    if any(w in kw for w in ["seo", "schema", "meta"]):
        return 2
    if any(w in kw for w in ["calculator", "converter"]):
        return 2
    if impressions > 50:
        return 2
    return 3


def show_niche_ideas(niche):
    """Generate content ideas for a specific niche."""
    print(f"\n  Generating ideas for: \"{niche}\"...\n")

    suggestions = google_autocomplete(niche)
    trends = google_trends_suggestions(niche)

    all_ideas = []
    seen = set()

    for s in suggestions:
        if s.lower() not in seen:
            seen.add(s.lower())
            all_ideas.append({"keyword": s, "source": "Autocomplete", "type": classify_idea_type(s), "priority": estimate_priority(s)})

    for t in trends:
        kw = t.lower()
        if kw not in seen:
            seen.add(kw)
            all_ideas.append({"keyword": t, "source": "Trends", "type": classify_idea_type(t), "priority": estimate_priority(t)})

    all_ideas.sort(key=lambda x: x["priority"])

    print(f"  {'IDEA':<50s} {'TYPE':<15s} {'SOURCE':<12s} {'PRI':>4s}")
    print(f"  {'-'*50} {'-'*15} {'-'*12} {'-'*4}")

    for idea in all_ideas:
        name = idea["keyword"][:49]
        print(f"  {name:<50s} {idea['type']:<15s} {idea['source']:<12s} {'P' + str(idea['priority']):>4s}")

    print(f"\n  Total ideas: {len(all_ideas)}\n")


def show_content_gaps(token):
    """Find keywords people search for where we have no matching tool."""
    print("\n  Finding content gaps (high-impression keywords with no dedicated tool)...\n")

    queries = sc_top_queries(token, 200)
    existing = get_existing_tools()

    gaps = []
    for kw, imps, clicks, pos in queries:
        # Check if any existing tool slug contains main words from query
        words = set(kw.lower().split())
        has_tool = any(
            len(words & set(tool.lower().replace("/", " ").replace("-", " ").split())) >= 2
            for tool in existing
        )
        if not has_tool and imps >= 5:
            gaps.append({"keyword": kw, "impressions": imps, "clicks": clicks, "position": round(pos, 1), "type": classify_idea_type(kw), "priority": estimate_priority(kw, imps)})

    gaps.sort(key=lambda x: (-x["impressions"], x["priority"]))

    print(f"  {'KEYWORD (no dedicated tool)':<45s} {'IMPS':>6s} {'POS':>5s} {'TYPE':<15s} {'PRI':>4s}")
    print(f"  {'-'*45} {'-'*6} {'-'*5} {'-'*15} {'-'*4}")

    for g in gaps[:25]:
        name = g["keyword"][:44]
        print(f"  {name:<45s} {g['impressions']:>6d} {g['position']:>5.0f} {g['type']:<15s} {'P' + str(g['priority']):>4s}")

    print(f"\n  {len(gaps)} content gaps found. Build tools for P1 keywords first.\n")


def show_seasonal():
    """Show seasonal content calendar."""
    month = datetime.now().month
    next_month = (month % 12) + 1

    print()
    print("=" * 70)
    print(f"  SEASONAL CONTENT CALENDAR")
    print("=" * 70)
    print()

    months = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
              7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}

    print(f"  THIS MONTH ({months[month]}):")
    for topic in SEASONAL.get(month, []):
        pri = estimate_priority(topic)
        print(f"    P{pri}  {topic}")

    print(f"\n  NEXT MONTH ({months[next_month]}):")
    for topic in SEASONAL.get(next_month, []):
        pri = estimate_priority(topic)
        print(f"    P{pri}  {topic}")

    print(f"\n  BUILD NOW: Start building next month's tools TODAY for SEO indexing time.\n")


def show_trending():
    """Show trending topics from Google Autocomplete across niches."""
    print()
    print("=" * 80)
    print(f"  TRENDING CONTENT IDEAS — {datetime.now().strftime('%B %Y')}")
    print(f"  Source: Google Autocomplete + Trends (real-time, free)")
    print("=" * 80)
    print()

    all_ideas = []
    seen = set()

    # Check trending queries for top niches
    trending_seeds = [
        "free online calculator 2026",
        "free online tool",
        "free ai tool 2026",
        "best free tool for",
    ]

    for seed in trending_seeds:
        print(f"  Checking: \"{seed}\"...")
        suggestions = google_autocomplete(seed)
        for s in suggestions[:5]:
            if s.lower() not in seen:
                seen.add(s.lower())
                all_ideas.append({
                    "keyword": s,
                    "type": classify_idea_type(s),
                    "priority": estimate_priority(s),
                    "seed": seed
                })

    all_ideas.sort(key=lambda x: x["priority"])

    print()
    print(f"  {'TRENDING IDEA':<55s} {'TYPE':<15s} {'PRI':>4s}")
    print(f"  {'-'*55} {'-'*15} {'-'*4}")

    for idea in all_ideas:
        name = idea["keyword"][:54]
        print(f"  {name:<55s} {idea['type']:<15s} {'P' + str(idea['priority']):>4s}")

    print(f"\n  {len(all_ideas)} trending ideas found.")
    print(f"  Build P1 ideas first — they have the highest revenue potential.\n")


def show_auto_ideas(token=None):
    """Auto-generate ideas combining all sources."""
    print()
    print("=" * 90)
    print(f"  CONTENT IDEAS ENGINE — tool.teamzlab.com")
    print(f"  {datetime.now().strftime('%B %d, %Y')} | All data from FREE sources")
    print("=" * 90)

    # 1. Seasonal ideas
    month = datetime.now().month
    months_name = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                   7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    print(f"\n  SEASONAL ({months_name[month]}):")
    for topic in SEASONAL.get(month, [])[:5]:
        print(f"    -> {topic}")

    # 2. Top Search Console keywords (to expand on)
    if token:
        print(f"\n  FROM YOUR SEARCH DATA (expand these topics):")
        queries = sc_top_queries(token, 20)
        for kw, imps, clicks, pos in queries[:10]:
            action = "Optimize" if pos < 30 else "Build dedicated tool"
            print(f"    [{action}] \"{kw}\" (pos {pos:.0f}, {imps} impressions)")

    # 3. Quick autocomplete for top niche
    print(f"\n  FRESH IDEAS (Google Autocomplete):")
    for niche in ["free calculator", "free online tool"]:
        suggestions = google_autocomplete(niche)
        for s in suggestions[:3]:
            print(f"    -> {s}")

    print()
    print("  NEXT STEPS:")
    print("    python3 scripts/build-content-ideas.py --niche \"keyword\"  # Deep dive into a niche")
    print("    python3 scripts/build-content-ideas.py --gaps              # Find content gaps")
    print("    python3 scripts/build-content-ideas.py --seasonal          # Full seasonal calendar")
    print()


def main():
    args = sys.argv[1:]

    token = None
    if TOKEN_FILE.exists():
        token = refresh_token()

    if "--niche" in args:
        idx = args.index("--niche")
        niche = args[idx + 1] if idx + 1 < len(args) else "calculator"
        show_niche_ideas(niche)

    elif "--trending" in args:
        show_trending()

    elif "--gaps" in args:
        if not token:
            print("\n  ERROR: --gaps requires Search Console. Run: python3 build-search-console-auth.py\n")
            return
        show_content_gaps(token)

    elif "--seasonal" in args:
        show_seasonal()

    elif "--competitors" in args:
        # Use autocomplete to find what competitors target
        print("\n  Generating competitor content ideas...\n")
        for seed in ["calculator.net", "tinywow", "smallseotools"]:
            print(f"  Competitor: {seed}")
            suggestions = google_autocomplete(seed)
            for s in suggestions[:5]:
                print(f"    -> {s}")
            print()

    else:
        show_auto_ideas(token)


if __name__ == "__main__":
    main()
