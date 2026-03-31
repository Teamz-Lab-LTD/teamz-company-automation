#!/usr/bin/env python3
"""
SEO competitor keyword gap analysis using GSC + Google Autocomplete.

Pulls your top 100 GSC queries, expands the top 20 via Autocomplete, then
cross-references to find keywords Google suggests that you do NOT yet rank for.

Usage:
    python3 py/build-competitor-gaps.py              # full analysis
    python3 py/build-competitor-gaps.py --top 10     # expand only top N queries
    python3 py/build-competitor-gaps.py --report      # show latest saved report

Env (optional):
    TEAMZ_COMPETITOR_DOMAINS  comma-separated competitor domains (noted in report)

Data: TEAMZ_DATA_DIR/competitor-gaps-latest.json
Website mode only (exit 2 for app).
"""

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from _teamz_config import load_runtime

_CFG = load_runtime(__file__)
_CTX = ssl.create_default_context()

TOKEN_FILE = _CFG["sc_token_file"]
SITE_URL = _CFG["site_property"]
GOOGLE_PROJECT = _CFG["google_project"]

_AUTOCOMPLETE_DELAY = 1.0


def _refresh_token() -> str:
    """Refresh GSC OAuth token; returns access_token or empty string."""
    if not TOKEN_FILE.exists():
        return ""
    token_data = json.loads(TOKEN_FILE.read_text())
    data = urllib.parse.urlencode({
        "client_id": token_data["client_id"],
        "client_secret": token_data["client_secret"],
        "refresh_token": token_data["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=_CTX)
        return json.loads(resp.read()).get("access_token", "")
    except Exception as e:
        print(f"  Token refresh failed: {e}")
        return ""


def _sc_query(token: str, start: str, end: str, limit: int = 100) -> list:
    """Query GSC searchAnalytics for top queries."""
    encoded = urllib.parse.quote(SITE_URL, safe="")
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query"
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["query"],
        "rowLimit": limit,
        "dataState": "all",
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-goog-user-project", GOOGLE_PROJECT)
    try:
        resp = urllib.request.urlopen(req, context=_CTX)
        return json.loads(resp.read()).get("rows", [])
    except urllib.error.HTTPError as e:
        print(f"  GSC API error: {e.code} — {e.read().decode()[:200]}")
        return []


def _fetch_autocomplete(query: str) -> list:
    """Fetch Google Autocomplete suggestions for *query*."""
    q = urllib.parse.quote_plus(query)
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={q}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        resp = urllib.request.urlopen(req, timeout=10, context=_CTX)
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
        if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
            return [s for s in data[1] if isinstance(s, str)]
        return []
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
        print(f"    Autocomplete error for '{query}': {e}")
        return []


def _show_report(report_path: Path) -> None:
    if not report_path.exists():
        print("\n  No report yet. Run without --report first.\n")
        return

    report = json.loads(report_path.read_text())
    gaps = report.get("gaps", [])
    competitors = report.get("competitor_domains", [])

    print()
    print("=" * 90)
    print("  COMPETITOR KEYWORD GAPS — Latest Report")
    print(f"  Generated: {report.get('generated_at', '?')}")
    print(f"  Your queries: {report.get('your_query_count', 0)} | Suggestions expanded: {report.get('queries_expanded', 0)}")
    print(f"  Gaps found: {len(gaps)}")
    if competitors:
        print(f"  Competitor domains: {', '.join(competitors)}")
    print("=" * 90)

    if gaps:
        print(f"\n  {'GAP KEYWORD':<50s} {'SEED QUERY':<40s}")
        print(f"  {'-'*50} {'-'*40}")
        for g in gaps[:50]:
            print(f"  {g['suggestion'][:49]:<50s} {g['seed'][:39]:<40s}")
        if len(gaps) > 50:
            print(f"\n  ... +{len(gaps) - 50} more (see competitor-gaps-latest.json)")
    print()


def main() -> int:
    if _CFG["project_type"] == "app":
        print("Skipped: TEAMZ_PROJECT_TYPE=app (website-only tooling).", file=sys.stderr)
        return 2

    args = sys.argv[1:]
    data_dir: Path = _CFG["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)
    report_path = data_dir / "competitor-gaps-latest.json"

    if "--report" in args:
        _show_report(report_path)
        return 0

    expand_top = 20
    if "--top" in args:
        idx = args.index("--top")
        if idx + 1 < len(args):
            try:
                expand_top = int(args[idx + 1])
            except ValueError:
                pass

    # Refresh GSC token
    token = _refresh_token()
    if not token:
        print("\n  ERROR: No Search Console token. Run: python3 py/build-search-console-auth.py\n")
        return 1

    print()
    print("=" * 72)
    print("  COMPETITOR KEYWORD GAP ANALYSIS")
    print("=" * 72)

    # 1. Get your top 100 queries
    end = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    print(f"\n  Fetching your top 100 GSC queries ({start} to {end})...")

    rows = _sc_query(token, start, end, limit=100)
    if not rows:
        print("  No GSC data returned. Try again later.\n")
        return 0

    your_queries = set()
    top_queries = []
    for row in rows:
        kw = row["keys"][0].lower().strip()
        your_queries.add(kw)
        top_queries.append({
            "query": kw,
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "position": round(row.get("position", 100), 1),
        })

    top_queries.sort(key=lambda x: x["impressions"], reverse=True)
    print(f"  Found {len(your_queries)} unique queries")

    # 2. Expand top N via Autocomplete
    seeds = top_queries[:expand_top]
    print(f"\n  Expanding top {len(seeds)} queries via Autocomplete...")

    all_suggestions = {}
    for i, q in enumerate(seeds):
        query = q["query"]
        print(f"    [{i+1}/{len(seeds)}] {query}", end="")
        suggestions = _fetch_autocomplete(query)
        all_suggestions[query] = suggestions
        print(f" → {len(suggestions)} suggestions")
        if i < len(seeds) - 1:
            time.sleep(_AUTOCOMPLETE_DELAY)

    # 3. Cross-reference: find gaps
    gaps = []
    seen_suggestions = set()
    for seed, suggestions in all_suggestions.items():
        for s in suggestions:
            s_lower = s.lower().strip()
            if s_lower in your_queries:
                continue
            if s_lower in seen_suggestions:
                continue
            if s_lower == seed:
                continue
            seen_suggestions.add(s_lower)
            gaps.append({"suggestion": s_lower, "seed": seed})

    gaps.sort(key=lambda x: x["suggestion"])

    # 4. Competitor domains (informational)
    competitor_raw = os.getenv("TEAMZ_COMPETITOR_DOMAINS", "").strip()
    competitors = [d.strip() for d in competitor_raw.split(",") if d.strip()] if competitor_raw else []

    # 5. Write report
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "site_url": _CFG["site_url"],
        "your_query_count": len(your_queries),
        "queries_expanded": len(seeds),
        "total_suggestions": sum(len(v) for v in all_suggestions.values()),
        "gaps_found": len(gaps),
        "competitor_domains": competitors,
        "top_queries": top_queries[:20],
        "gaps": gaps,
    }
    report_path.write_text(json.dumps(report, indent=2))

    # 6. Print summary
    print(f"\n  Your GSC queries:      {len(your_queries)}")
    print(f"  Autocomplete total:    {report['total_suggestions']}")
    print(f"  Keyword gaps found:    {len(gaps)}")
    if competitors:
        print(f"  Competitor domains:    {', '.join(competitors)}")
        print(f"  (Note: we can't query competitors' GSC — these are for your reference)")

    if gaps:
        print(f"\n  Top 20 gaps:")
        print(f"  {'GAP KEYWORD':<50s} {'FROM QUERY':<30s}")
        print(f"  {'-'*50} {'-'*30}")
        for g in gaps[:20]:
            print(f"  {g['suggestion'][:49]:<50s} {g['seed'][:29]:<30s}")

    print(f"\n  Full report → {report_path.name}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
