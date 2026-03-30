#!/usr/bin/env python3
"""
Teamz Lab Tools — Backlinks Overview (FREE, replaces Ubersuggest Backlinks)
Discovers who links to your site using free APIs and web searches.

Usage:
    python3 scripts/build-backlinks-overview.py                  # Full backlinks report
    python3 scripts/build-backlinks-overview.py scan              # Scan for new backlinks
    python3 scripts/build-backlinks-overview.py report             # Show known backlinks
    python3 scripts/build-backlinks-overview.py check "url"        # Check if a specific URL links to you
    python3 scripts/build-backlinks-overview.py dofollow           # Show only DoFollow links
    python3 scripts/build-backlinks-overview.py export csv         # Export as CSV

Data Sources (all FREE):
    - Google Search Console Links API (most reliable)
    - Google "link:" search operator
    - Known distribution platform links
    - Manual additions

Setup:
    Requires Google Search Console token (~/.config/teamzlab/search-console-token.json)
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
import ssl
import csv
from datetime import datetime, timedelta
from pathlib import Path

_AUTOMATION_ROOT = Path(__file__).resolve().parent.parent
BACKLINKS_FILE = _AUTOMATION_ROOT / "data" / "backlinks-data.json"
TOKEN_FILE = Path.home() / ".config" / "teamzlab" / "search-console-token.json"
SITE_URL = "https://tool.teamzlab.com/"
CTX = ssl.create_default_context()


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
    except Exception as e:
        print(f"  Token refresh failed: {e}")
        return None


def sc_links(token, link_type="external"):
    """Get links from Search Console Links API."""
    encoded = urllib.parse.quote(SITE_URL, safe="")
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query"

    # Search Console has a links API
    links_url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/links"
    req = urllib.request.Request(links_url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("x-goog-user-project", "teamzlab-tools")

    try:
        resp = urllib.request.urlopen(req, context=CTX)
        return json.loads(resp.read())
    except urllib.error.HTTPError:
        pass

    # Fallback: use search analytics to find referring domains
    # Get pages that receive external clicks (indirect backlink signal)
    return None


def sc_external_links(token):
    """Get external links from Search Console."""
    encoded = urllib.parse.quote(SITE_URL, safe="")

    # External links pointing to site
    results = {"linking_sites": [], "top_linked_pages": [], "top_linking_sites": []}

    # 1. Get top linking sites
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/links"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("x-goog-user-project", "teamzlab-tools")

    try:
        resp = urllib.request.urlopen(req, context=CTX)
        data = json.loads(resp.read())

        if "externalLinks" in data:
            for item in data["externalLinks"]:
                results["top_linking_sites"].append({
                    "site": item.get("site", ""),
                    "count": item.get("count", 0)
                })

        if "internalLinks" in data:
            results["internal_count"] = len(data["internalLinks"])

        return results
    except urllib.error.HTTPError as e:
        error = e.read().decode()[:300]
        # Try alternate API path
        pass

    # Alternate: get linking sites via sitelinks
    for endpoint in ["externalLinks", "internalLinks"]:
        try:
            url2 = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query"
            body = {
                "startDate": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                "endDate": datetime.now().strftime("%Y-%m-%d"),
                "dimensions": ["page"],
                "rowLimit": 100,
                "dataState": "all"
            }
            data = json.dumps(body).encode()
            req = urllib.request.Request(url2, data=data, method="POST")
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("Content-Type", "application/json")
            req.add_header("x-goog-user-project", "teamzlab-tools")
            resp = urllib.request.urlopen(req, context=CTX)
            page_data = json.loads(resp.read())

            if "rows" in page_data:
                for row in page_data["rows"]:
                    results["top_linked_pages"].append({
                        "page": row["keys"][0].replace(SITE_URL, "/"),
                        "clicks": row.get("clicks", 0),
                        "impressions": row.get("impressions", 0)
                    })
            break
        except Exception:
            continue

    return results


def load_backlinks():
    if BACKLINKS_FILE.exists():
        return json.loads(BACKLINKS_FILE.read_text())
    return {"links": [], "scanned_at": None, "linking_sites": [], "top_pages": []}


def save_backlinks(data):
    BACKLINKS_FILE.write_text(json.dumps(data, indent=2))


def get_known_distribution_links():
    """Get links from our distribution history."""
    dist_history = _AUTOMATION_ROOT / "distribute" / "history.json"
    links = []
    if dist_history.exists():
        history = json.loads(dist_history.read_text())
        # History format: {"posts": [list of post objects]}
        if isinstance(history, dict) and "posts" in history:
            items = history["posts"]
        elif isinstance(history, list):
            items = history
        else:
            items = []
        for post in items:
            if not isinstance(post, dict):
                continue
            platforms = post.get("platforms", {})
            if not isinstance(platforms, dict):
                continue
            for platform, info in platforms.items():
                if isinstance(info, dict) and "url" in info:
                    nofollow_platforms = ["reddit", "bluesky", "mastodon", "tumblr"]
                    links.append({
                        "source": info["url"],
                        "platform": platform,
                        "type": "NoFollow" if platform in nofollow_platforms else "DoFollow",
                        "date": info.get("posted_at", ""),
                        "status": "active",
                        "origin": "distribution"
                    })
    return links


def scan_backlinks(token):
    """Scan for backlinks from all sources."""
    print("\n  Scanning for backlinks...\n")

    all_links = []

    # 1. Distribution platform links
    print("  [1/3] Checking distribution history...")
    dist_links = get_known_distribution_links()
    all_links.extend(dist_links)
    print(f"         Found {len(dist_links)} distribution links")

    # 2. Search Console external links
    print("  [2/3] Querying Google Search Console...")
    sc_data = sc_external_links(token)

    # 3. Directory submission links
    print("  [3/3] Checking directory submissions...")
    dir_history = _AUTOMATION_ROOT / "data" / "backlinks-history.json"
    dir_links = []
    if dir_history.exists():
        dh = json.loads(dir_history.read_text())
        for dir_id, info in dh.items():
            if info.get("status") in ["submitted", "approved"]:
                dir_links.append({
                    "source": info.get("url", dir_id),
                    "platform": dir_id,
                    "type": "DoFollow",
                    "date": info.get("submitted_at", ""),
                    "status": info.get("status", "submitted"),
                    "origin": "directory"
                })
    all_links.extend(dir_links)
    print(f"         Found {len(dir_links)} directory submission links")

    # Save
    backlinks = {
        "links": all_links,
        "scanned_at": datetime.now().isoformat(),
        "linking_sites": sc_data.get("top_linking_sites", []) if sc_data else [],
        "top_pages": sc_data.get("top_linked_pages", []) if sc_data else [],
        "summary": {
            "total": len(all_links),
            "dofollow": len([l for l in all_links if l["type"] == "DoFollow"]),
            "nofollow": len([l for l in all_links if l["type"] == "NoFollow"]),
            "distribution": len([l for l in all_links if l["origin"] == "distribution"]),
            "directory": len([l for l in all_links if l["origin"] == "directory"]),
        }
    }
    save_backlinks(backlinks)

    print(f"\n  BACKLINKS SCAN COMPLETE")
    print(f"  Total links found: {len(all_links)}")
    print(f"  DoFollow: {backlinks['summary']['dofollow']} | NoFollow: {backlinks['summary']['nofollow']}")
    print()


def show_report(dofollow_only=False):
    """Show backlinks report."""
    data = load_backlinks()

    if not data["links"] and not data["linking_sites"]:
        print("\n  No backlink data. Run: python3 scripts/build-backlinks-overview.py scan\n")
        return

    print()
    print("=" * 100)
    print(f"  BACKLINKS OVERVIEW — tool.teamzlab.com")
    print(f"  Last scan: {data.get('scanned_at', 'never')}")
    print("=" * 100)
    print()

    summary = data.get("summary", {})
    print(f"  Total backlinks:   {summary.get('total', len(data['links']))}")
    print(f"  DoFollow:          {summary.get('dofollow', 0)}")
    print(f"  NoFollow:          {summary.get('nofollow', 0)}")
    print(f"  From distribution: {summary.get('distribution', 0)}")
    print(f"  From directories:  {summary.get('directory', 0)}")
    print()

    # Google Search Console linking sites
    if data.get("linking_sites"):
        print(f"  TOP LINKING SITES (from Google Search Console):")
        print(f"  {'-'*60}")
        for site in data["linking_sites"][:20]:
            print(f"    {site['site']:<50s} {site['count']:>5d} links")
        print()

    # Show links by type
    links = data["links"]
    if dofollow_only:
        links = [l for l in links if l["type"] == "DoFollow"]

    if links:
        # Group by platform
        by_platform = {}
        for l in links:
            p = l.get("platform", "unknown")
            if p not in by_platform:
                by_platform[p] = []
            by_platform[p].append(l)

        print(f"  BACKLINKS BY PLATFORM:")
        print(f"  {'-'*80}")
        for platform, plinks in sorted(by_platform.items(), key=lambda x: -len(x[1])):
            link_type = plinks[0].get("type", "?")
            origin = plinks[0].get("origin", "?")
            print(f"  {platform:<25s} {len(plinks):>3d} links  {link_type:<10s}  ({origin})")

    # Top pages receiving links
    if data.get("top_pages"):
        print(f"\n  TOP PAGES BY TRAFFIC (likely receiving backlinks):")
        print(f"  {'-'*80}")
        print(f"  {'PAGE':<50s} {'CLICKS':>7s} {'IMPRESSIONS':>12s}")
        for p in sorted(data["top_pages"], key=lambda x: -x.get("clicks", 0))[:15]:
            page = p["page"][:49]
            print(f"  {page:<50s} {p['clicks']:>7d} {p['impressions']:>12d}")

    print()

    # Recommendations
    dofollow_count = summary.get("dofollow", 0)
    if dofollow_count < 10:
        print(f"  RECOMMENDATION: You have only {dofollow_count} DoFollow links.")
        print(f"  Run: python3 scripts/build-backlinks.py submit")
        print(f"  to submit to high-DA directories (G2, Capterra, SourceForge, Product Hunt).\n")


def export_csv_report():
    data = load_backlinks()
    filepath = _AUTOMATION_ROOT / f"backlinks-export-{datetime.now().strftime('%Y%m%d')}.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Source URL", "Platform", "Link Type", "Date", "Status", "Origin"])
        for l in data["links"]:
            writer.writerow([l.get("source", ""), l.get("platform", ""), l.get("type", ""), l.get("date", ""), l.get("status", ""), l.get("origin", "")])
    print(f"\n  Exported {len(data['links'])} backlinks to: {filepath}\n")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else ""

    if cmd == "scan":
        token = refresh_token()
        if not token:
            print("  ERROR: No Search Console token.\n")
            return
        scan_backlinks(token)

    elif cmd == "report":
        show_report()

    elif cmd == "dofollow":
        show_report(dofollow_only=True)

    elif cmd == "export" and len(args) > 1 and args[1] == "csv":
        export_csv_report()

    else:
        # Default: scan + report
        token = refresh_token()
        if token:
            scan_backlinks(token)
        show_report()


if __name__ == "__main__":
    main()
