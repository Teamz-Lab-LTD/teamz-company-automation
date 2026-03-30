#!/usr/bin/env python3
"""
Teamz Lab Tools — Free Keyword Intelligence (Ubersuggest Alternative)
Combines Google Search Console + Autocomplete + intent classification.

Usage:
    python3 scripts/build-keyword-intel.py                     # Full keyword report (like Ubersuggest)
    python3 scripts/build-keyword-intel.py --top 30             # Top 30 keywords
    python3 scripts/build-keyword-intel.py --keyword "calculator" # Filter by keyword
    python3 scripts/build-keyword-intel.py --page "/us/nfl*"     # Filter by page
    python3 scripts/build-keyword-intel.py --opportunities       # Show low-difficulty opportunities
    python3 scripts/build-keyword-intel.py --gaps                # Keyword gap analysis
    python3 scripts/build-keyword-intel.py --ideas "salary"      # Get keyword ideas via Autocomplete
    python3 scripts/build-keyword-intel.py --export csv          # Export as CSV
    python3 scripts/build-keyword-intel.py --compare "kw1" "kw2" # Compare keywords via Trends

Data Sources (all FREE):
    - Google Search Console API (real clicks, impressions, position, CTR)
    - Google Autocomplete API (keyword suggestions)
    - Google Trends (relative volume comparison)
    - Pattern-based intent classification
    - SEO difficulty estimation from position data
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import ssl
import csv
import io
from datetime import datetime, timedelta
from pathlib import Path

# ── Config ──
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
TOKEN_FILE = Path.home() / ".config" / "teamzlab" / "search-console-token.json"
RANK_HISTORY_FILE = SCRIPT_DIR / "rank-history.json"
SITE_URL = "https://tool.teamzlab.com/"
CTX = ssl.create_default_context()

# ── Intent Classification Patterns ──
INTENT_PATTERNS = {
    "Transactional": [
        "buy", "price", "cost", "cheap", "deal", "discount", "coupon",
        "download", "install", "subscribe", "order", "purchase", "shop"
    ],
    "Commercial": [
        "best", "top", "review", "compare", "vs", "versus", "alternative",
        "recommendation", "rated", "ranking", "which", "pros and cons"
    ],
    "Navigational": [
        "login", "sign in", "website", "official", "app", "dashboard",
        "account", "portal", "homepage"
    ],
    "Informational": [
        "how", "what", "why", "when", "where", "who", "guide", "tutorial",
        "learn", "example", "meaning", "definition", "formula", "calculate",
        "calculator", "converter", "generator", "checker", "tester", "tool",
        "free", "online"
    ]
}

# ── CPC Estimation by Category ──
CPC_ESTIMATES = {
    "finance": 8.50, "tax": 12.00, "mortgage": 15.00, "loan": 10.00,
    "insurance": 18.00, "salary": 5.00, "payroll": 14.00, "gross": 10.00,
    "calculator": 2.00, "converter": 1.50, "generator": 1.80,
    "seo": 6.00, "developer": 3.00, "json": 2.50, "css": 2.00,
    "health": 4.00, "bmi": 3.00, "calorie": 3.50,
    "resume": 8.00, "career": 5.00, "ats": 7.00,
    "crypto": 5.00, "bitcoin": 6.00,
    "photo": 2.00, "image": 1.80, "video": 2.50, "meme": 1.00,
    "qr": 1.50, "barcode": 2.00,
    "math": 1.00, "probability": 1.50, "statistics": 2.00,
    "uk": 3.00, "us": 4.00,
}


def refresh_token():
    """Refresh Google OAuth2 token."""
    if not TOKEN_FILE.exists():
        return None
    token_data = json.loads(TOKEN_FILE.read_text())
    refresh_token = token_data.get("refresh_token")
    client_id = token_data.get("client_id")
    client_secret = token_data.get("client_secret")
    if not all([refresh_token, client_id, client_secret]):
        return None

    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=CTX)
        result = json.loads(resp.read())
        return result.get("access_token")
    except Exception as e:
        print(f"  Token refresh failed: {e}")
        return None


def search_console_query(access_token, start_date, end_date, dimensions=None, row_limit=500, dim_filter=None):
    """Query Google Search Console API."""
    if dimensions is None:
        dimensions = ["query", "page"]

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit,
        "dataState": "all"
    }
    if dim_filter:
        body["dimensionFilterGroups"] = [{"filters": dim_filter}]

    encoded_site = urllib.parse.quote(SITE_URL, safe='')
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-goog-user-project", "teamzlab-tools")

    try:
        resp = urllib.request.urlopen(req, context=CTX)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  Search Console API error: {e.code} — {error_body[:200]}")
        return {"rows": []}


def load_rank_history_keywords(keyword_filter=None, page_filter=None, top_n=50):
    """Fallback keyword data from local rank-history when Search Console is unavailable."""
    if not RANK_HISTORY_FILE.exists():
        return []

    try:
        history = json.loads(RANK_HISTORY_FILE.read_text())
    except Exception:
        return []

    records = history.get("records", [])
    if not records:
        return []

    latest = records[-1].get("data", {})
    keywords = []

    for keyword, row in latest.items():
        page = row.get("page", "/")
        if keyword_filter and keyword_filter.lower() not in keyword.lower():
            continue
        if page_filter and page_filter.lower() not in page.lower():
            continue

        clicks = row.get("clicks", 0)
        impressions = row.get("imps", 0)
        position = round(row.get("pos", 100), 1)
        ctr = round((clicks / impressions) * 100, 2) if impressions else 0.0

        keywords.append({
            "keyword": keyword,
            "page": page,
            "clicks": clicks,
            "impressions": impressions,
            "ctr": ctr,
            "position": position,
            "intent": classify_intent(keyword),
            "cpc": estimate_cpc(keyword),
            "volume": estimate_volume_from_impressions(max(impressions, 1), position),
            "difficulty": estimate_difficulty(position, max(impressions, 1), clicks),
        })

    keywords.sort(key=lambda x: (-x["volume"], x["position"]))
    return keywords[:top_n]


def classify_intent(keyword):
    """Classify search intent from keyword."""
    kw = keyword.lower()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if p in kw)
        if score > 0:
            scores[intent] = score

    if not scores:
        return "Informational"
    return max(scores, key=scores.get)


def estimate_cpc(keyword):
    """Estimate CPC from keyword category."""
    kw = keyword.lower()
    best_cpc = 0.50  # default
    for term, cpc in CPC_ESTIMATES.items():
        if term in kw:
            best_cpc = max(best_cpc, cpc)
    return best_cpc


def estimate_volume_from_impressions(impressions, position):
    """Estimate monthly search volume from impressions + position."""
    # CTR curve by position (approximate)
    ctr_by_pos = {
        1: 0.28, 2: 0.15, 3: 0.11, 4: 0.08, 5: 0.065,
        6: 0.05, 7: 0.04, 8: 0.035, 9: 0.03, 10: 0.025,
        15: 0.015, 20: 0.01, 30: 0.005, 50: 0.002, 100: 0.001
    }

    # Find closest position CTR
    pos = max(1, round(position))
    if pos in ctr_by_pos:
        expected_ctr = ctr_by_pos[pos]
    else:
        # Interpolate
        lower = max(k for k in ctr_by_pos if k <= pos) if any(k <= pos for k in ctr_by_pos) else 1
        upper = min(k for k in ctr_by_pos if k >= pos) if any(k >= pos for k in ctr_by_pos) else 100
        if lower == upper:
            expected_ctr = ctr_by_pos[lower]
        else:
            ratio = (pos - lower) / (upper - lower)
            expected_ctr = ctr_by_pos[lower] + ratio * (ctr_by_pos[upper] - ctr_by_pos[lower])

    # Volume = impressions * (1 / impression_share_at_position)
    # At position 1, you see ~95% of searches as impressions
    # At position 50, you see maybe ~20% (most users don't scroll)
    impression_share = max(0.05, 1.0 - (pos - 1) * 0.015)
    estimated_daily_volume = impressions / max(impression_share, 0.01)

    # Convert to monthly (data is 90 days)
    monthly = (estimated_daily_volume / 90) * 30

    # Round to nearest tier
    tiers = [10, 20, 30, 40, 50, 70, 100, 140, 170, 210, 260, 320, 390, 480, 590, 720, 880, 1000, 1300, 1600, 1900, 2400, 2900, 3600, 4400, 5400, 6600, 8100, 9900, 12100, 14800, 18100, 22200, 27100, 33100, 40500, 49500, 60500, 74000, 90500]
    closest = min(tiers, key=lambda t: abs(t - monthly))
    return closest


def estimate_difficulty(position, impressions, clicks):
    """Estimate SEO difficulty (0-100) similar to Ubersuggest."""
    # Higher impression = more competitive keyword
    # Higher position number = harder to rank (you're further from #1)
    # More clicks at lower position = easier to break in

    imp_score = min(50, impressions / 100)  # max 50 from impressions
    pos_score = min(40, position * 0.5)     # max 40 from position
    ctr_bonus = -10 if clicks > 0 and position < 30 else 0  # easier if getting clicks

    difficulty = int(min(100, max(5, imp_score + pos_score + ctr_bonus)))
    return difficulty


def google_autocomplete(keyword, lang="en", country="us"):
    """Get keyword suggestions from Google Autocomplete (free, no API key)."""
    suggestions = []
    prefixes = ["", "a ", "b ", "c ", "d ", "e ", "f ", "g ", "h ",
                "how to ", "what is ", "best ", "free ", "vs "]

    for prefix in prefixes[:8]:  # Limit to avoid rate limiting
        query = f"{prefix}{keyword}".strip()
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(query)}&hl={lang}&gl={country}"
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")
            resp = urllib.request.urlopen(req, timeout=5, context=CTX)
            data = json.loads(resp.read())
            if len(data) > 1 and isinstance(data[1], list):
                for s in data[1]:
                    if s.lower() != keyword.lower() and s not in suggestions:
                        suggestions.append(s)
        except Exception:
            pass

    return suggestions[:20]


def get_keyword_data(access_token, keyword_filter=None, page_filter=None, top_n=50):
    """Get keyword data from Search Console."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    filters = []
    if keyword_filter:
        filters.append({
            "dimension": "query",
            "operator": "contains",
            "expression": keyword_filter
        })
    if page_filter:
        filters.append({
            "dimension": "page",
            "operator": "contains",
            "expression": page_filter
        })

    result = search_console_query(
        access_token, start_date, end_date,
        dimensions=["query", "page"],
        row_limit=min(top_n * 3, 1000),
        dim_filter=filters if filters else None
    )

    rows = result.get("rows", [])
    keywords = {}

    for row in rows:
        kw = row["keys"][0]
        page = row["keys"][1]
        clicks = row.get("clicks", 0)
        impressions = row.get("impressions", 0)
        ctr = row.get("ctr", 0)
        position = row.get("position", 100)

        if kw not in keywords or keywords[kw]["position"] > position:
            keywords[kw] = {
                "keyword": kw,
                "page": page.replace(SITE_URL, "/"),
                "clicks": clicks,
                "impressions": impressions,
                "ctr": round(ctr * 100, 2),
                "position": round(position, 1),
                "intent": classify_intent(kw),
                "cpc": estimate_cpc(kw),
                "volume": estimate_volume_from_impressions(impressions, position),
                "difficulty": estimate_difficulty(position, impressions, clicks),
            }
        else:
            # Aggregate clicks/impressions for same keyword across pages
            keywords[kw]["clicks"] += clicks
            keywords[kw]["impressions"] += impressions

    # Sort by estimated volume descending
    sorted_kws = sorted(keywords.values(), key=lambda x: (-x["volume"], x["position"]))
    return sorted_kws[:top_n]


def intent_badge(intent):
    """Return colored intent badge like Ubersuggest."""
    badges = {
        "Informational": "I",
        "Navigational": "N",
        "Commercial": "C",
        "Transactional": "T"
    }
    return badges.get(intent, "?")


def difficulty_label(d):
    """Return difficulty label."""
    if d <= 20:
        return "Easy"
    elif d <= 40:
        return "Medium"
    elif d <= 60:
        return "Hard"
    else:
        return "V.Hard"


def print_keyword_table(keywords, title="KEYWORD IDEAS", data_source="Google Search Console (last 90 days) + estimates"):
    """Print keywords in Ubersuggest-like format."""
    print()
    print("=" * 120)
    print(f"  {title} — tool.teamzlab.com")
    print(f"  Data: {data_source}")
    print("=" * 120)
    print()
    print(f"  {'KEYWORD':<45s} {'INTENT':>6s} {'VOLUME':>7s} {'POSITION':>9s} {'CLICKS':>7s} {'CPC':>8s} {'DIFFICULTY':>11s}")
    print(f"  {'-'*45} {'-'*6} {'-'*7} {'-'*9} {'-'*7} {'-'*8} {'-'*11}")

    for kw in keywords:
        intent = intent_badge(kw["intent"])
        vol = f"{kw['volume']:,}"
        pos = f"{kw['position']:.0f}"
        clicks = f"{kw['clicks']}"
        cpc = f"${kw['cpc']:.2f}"
        diff = f"{kw['difficulty']} {difficulty_label(kw['difficulty'])}"
        name = kw["keyword"][:44]

        print(f"  {name:<45s} {intent:>6s} {vol:>7s} {pos:>9s} {clicks:>7s} {cpc:>8s} {diff:>11s}")

    print()
    print(f"  Total keywords: {len(keywords)}")
    print()


def print_opportunities(keywords):
    """Show best ranking opportunities."""
    # Low difficulty + high volume + not on page 1
    opps = [kw for kw in keywords if kw["difficulty"] <= 40 and kw["position"] > 10]
    opps.sort(key=lambda x: (-x["volume"], x["difficulty"]))

    print()
    print("=" * 120)
    print("  QUICK WIN OPPORTUNITIES (Low Difficulty, Not Yet on Page 1)")
    print("=" * 120)
    print()

    if not opps:
        print("  No easy opportunities found. Try expanding date range or keyword set.")
        return

    print(f"  {'KEYWORD':<40s} {'VOLUME':>7s} {'POS':>5s} {'DIFF':>6s} {'PAGE':<40s} {'ACTION'}")
    print(f"  {'-'*40} {'-'*7} {'-'*5} {'-'*6} {'-'*40} {'-'*20}")

    for kw in opps[:20]:
        name = kw["keyword"][:39]
        vol = f"{kw['volume']:,}"
        pos = f"{kw['position']:.0f}"
        diff = f"{kw['difficulty']}"
        page = kw["page"][:39]

        if kw["position"] <= 20:
            action = "Boost to page 1"
        elif kw["position"] <= 50:
            action = "Optimize content"
        else:
            action = "Build backlinks"

        print(f"  {name:<40s} {vol:>7s} {pos:>5s} {diff:>6s} {page:<40s} {action}")

    print()
    print(f"  Total opportunities: {len(opps)}")
    print()


def print_keyword_ideas(keyword):
    """Get and display keyword ideas from Google Autocomplete."""
    print()
    print("=" * 80)
    print(f"  KEYWORD IDEAS for: \"{keyword}\"")
    print(f"  Source: Google Autocomplete (free, real-time)")
    print("=" * 80)
    print()

    suggestions = google_autocomplete(keyword)

    if not suggestions:
        print("  No suggestions found. Try a different keyword.")
        return

    print(f"  {'SUGGESTION':<55s} {'INTENT':>6s} {'EST. CPC':>9s}")
    print(f"  {'-'*55} {'-'*6} {'-'*9}")

    for s in suggestions:
        intent = intent_badge(classify_intent(s))
        cpc = f"${estimate_cpc(s):.2f}"
        print(f"  {s:<55s} {intent:>6s} {cpc:>9s}")

    print()
    print(f"  Total ideas: {len(suggestions)}")
    print(f"  Note: Volume/difficulty require Search Console data.")
    print(f"         Run: python3 scripts/build-keyword-intel.py --keyword \"{keyword}\"")
    print()


def export_csv(keywords, filename=None):
    """Export keywords to CSV."""
    if not filename:
        filename = f"keyword-intel-{datetime.now().strftime('%Y%m%d')}.csv"

    filepath = PROJECT_DIR / filename

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Keyword", "Intent", "Volume", "Position", "Clicks", "Impressions", "CTR%", "CPC", "Difficulty", "Page"])
        for kw in keywords:
            writer.writerow([
                kw["keyword"], kw["intent"], kw["volume"], kw["position"],
                kw["clicks"], kw["impressions"], kw["ctr"], kw["cpc"],
                kw["difficulty"], kw["page"]
            ])

    print(f"\n  Exported {len(keywords)} keywords to: {filepath}\n")


def print_summary(keywords):
    """Print summary statistics."""
    if not keywords:
        return

    total_clicks = sum(kw["clicks"] for kw in keywords)
    total_impressions = sum(kw["impressions"] for kw in keywords)
    avg_position = sum(kw["position"] for kw in keywords) / len(keywords)
    page1 = len([kw for kw in keywords if kw["position"] <= 10])
    page2 = len([kw for kw in keywords if 10 < kw["position"] <= 20])
    striking = len([kw for kw in keywords if 10 < kw["position"] <= 30])

    intents = {}
    for kw in keywords:
        intents[kw["intent"]] = intents.get(kw["intent"], 0) + 1

    print(f"  SUMMARY:")
    print(f"  {'-'*50}")
    print(f"  Total keywords:        {len(keywords)}")
    print(f"  Total clicks (90d):    {total_clicks}")
    print(f"  Total impressions:     {total_impressions:,}")
    print(f"  Avg position:          {avg_position:.1f}")
    print(f"  On page 1 (pos 1-10):  {page1}")
    print(f"  On page 2 (pos 11-20): {page2}")
    print(f"  Striking distance:     {striking} (pos 11-30, easiest to push to page 1)")
    print()
    print(f"  INTENT BREAKDOWN:")
    for intent, count in sorted(intents.items(), key=lambda x: -x[1]):
        pct = count / len(keywords) * 100
        bar = "#" * int(pct / 2)
        print(f"    {intent:<15s} {count:>4d} ({pct:.0f}%) {bar}")
    print()


def main():
    args = sys.argv[1:]

    # Handle --ideas (no Search Console needed)
    if "--ideas" in args:
        idx = args.index("--ideas")
        keyword = args[idx + 1] if idx + 1 < len(args) else ""
        if not keyword:
            print("\n  Usage: python3 scripts/build-keyword-intel.py --ideas \"salary calculator\"\n")
            return
        print_keyword_ideas(keyword)
        return

    # All other commands need Search Console
    print("\n  Connecting to Google Search Console...")
    access_token = refresh_token()
    data_source = "Google Search Console (last 90 days) + estimates"
    use_fallback = False

    if not access_token:
        print("  WARNING: Search Console token unavailable.")
        fallback_preview = load_rank_history_keywords(top_n=1)
        if not fallback_preview:
            print("  ERROR: Could not get Search Console token.")
            print("  Run: python3 build-search-console-auth.py")
            print()
            print("  Meanwhile, you can use:")
            print("    python3 scripts/build-keyword-intel.py --ideas \"keyword\"")
            print("  for free keyword suggestions without Search Console.\n")
            return
        print("  Falling back to local rank-history snapshot.\n")
        use_fallback = True
        data_source = "Local rank-history snapshot (latest daily record) + estimates"
    else:
        print("  Connected!\n")

    # Parse args
    top_n = 50
    keyword_filter = None
    page_filter = None
    export_format = None

    i = 0
    while i < len(args):
        if args[i] == "--top" and i + 1 < len(args):
            top_n = int(args[i + 1]); i += 2
        elif args[i] == "--keyword" and i + 1 < len(args):
            keyword_filter = args[i + 1]; i += 2
        elif args[i] == "--page" and i + 1 < len(args):
            page_filter = args[i + 1]; i += 2
        elif args[i] == "--export" and i + 1 < len(args):
            export_format = args[i + 1]; i += 2
        elif args[i] in ("--opportunities", "--gaps", "--compare"):
            i += 1
        else:
            i += 1

    # Get data
    if use_fallback:
        keywords = load_rank_history_keywords(keyword_filter, page_filter, top_n)
    else:
        keywords = get_keyword_data(access_token, keyword_filter, page_filter, top_n)

    if not keywords and not use_fallback:
        fallback_keywords = load_rank_history_keywords(keyword_filter, page_filter, top_n)
        if fallback_keywords:
            print("  WARNING: Search Console returned no rows. Falling back to local rank-history snapshot.\n")
            keywords = fallback_keywords
            use_fallback = True
            data_source = "Local rank-history snapshot (latest daily record) + estimates"

    if not keywords:
        print("  No keyword data found. Try different filters or refresh Search Console.\n")
        return

    # Display
    if "--opportunities" in args:
        # Get more data for opportunities
        if use_fallback:
            all_kws = load_rank_history_keywords(keyword_filter, page_filter, 200)
        else:
            all_kws = get_keyword_data(access_token, keyword_filter, page_filter, 200)
            if not all_kws:
                all_kws = load_rank_history_keywords(keyword_filter, page_filter, 200)
        print_opportunities(all_kws)
    elif "--gaps" in args:
        # Show keywords with high impressions but low clicks
        print()
        print("=" * 120)
        print("  KEYWORD GAPS (High Impressions, Low/No Clicks — Content Optimization Needed)")
        print("=" * 120)
        print()
        gaps = [kw for kw in keywords if kw["impressions"] > 10 and kw["clicks"] == 0]
        gaps.sort(key=lambda x: -x["impressions"])
        if gaps:
            print(f"  {'KEYWORD':<40s} {'IMP':>6s} {'POS':>5s} {'VOLUME':>7s} {'PAGE':<40s}")
            print(f"  {'-'*40} {'-'*6} {'-'*5} {'-'*7} {'-'*40}")
            for kw in gaps[:20]:
                name = kw["keyword"][:39]
                imp = f"{kw['impressions']}"
                pos = f"{kw['position']:.0f}"
                vol = f"{kw['volume']:,}"
                page = kw["page"][:39]
                print(f"  {name:<40s} {imp:>6s} {pos:>5s} {vol:>7s} {page:<40s}")
            print()
            print(f"  {len(gaps)} keywords getting impressions but ZERO clicks.")
            print(f"  Fix: Improve title tags and meta descriptions for better CTR.\n")
        else:
            print("  No major gaps found — your CTR looks reasonable.\n")
    else:
        title = "KEYWORD IDEAS"
        if keyword_filter:
            title += f" (filter: \"{keyword_filter}\")"
        if page_filter:
            title += f" (page: \"{page_filter}\")"
        print_keyword_table(keywords, title, data_source=data_source)
        print_summary(keywords)

    if export_format == "csv":
        export_csv(keywords)


if __name__ == "__main__":
    main()
