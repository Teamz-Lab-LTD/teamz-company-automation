#!/usr/bin/env python3
"""
Teamz Lab Tools — Rank Tracker (FREE, replaces Ubersuggest Rank Tracking)
Tracks keyword positions daily using Google Search Console.

Usage:
    python3 scripts/build-rank-tracker.py                    # Record today's rankings + show trends
    python3 scripts/build-rank-tracker.py record              # Record today's positions to history
    python3 scripts/build-rank-tracker.py report              # Show ranking trends (last 30 days)
    python3 scripts/build-rank-tracker.py report --keyword "calc"  # Filter by keyword
    python3 scripts/build-rank-tracker.py movers              # Biggest position changes (up/down)
    python3 scripts/build-rank-tracker.py track "keyword"     # Add keyword to watchlist
    python3 scripts/build-rank-tracker.py untrack "keyword"   # Remove from watchlist
    python3 scripts/build-rank-tracker.py watchlist            # Show tracked keywords

Setup:
    - Requires Google Search Console token (~/.config/teamzlab/search-console-token.json)
    - Run daily (manually or via cron) to build position history
    - History stored in scripts/rank-history.json

RECOMMENDED: Add to daily workflow or cron:
    python3 scripts/build-rank-tracker.py record
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
import ssl
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
HISTORY_FILE = SCRIPT_DIR / "rank-history.json"
WATCHLIST_FILE = SCRIPT_DIR / "rank-watchlist.json"
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


def sc_query(token, start, end, dims=None, limit=500, filters=None):
    encoded = urllib.parse.quote(SITE_URL, safe="")
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query"
    body = {"startDate": start, "endDate": end, "dimensions": dims or ["query", "page"], "rowLimit": limit, "dataState": "all"}
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-goog-user-project", "teamzlab-tools")
    try:
        resp = urllib.request.urlopen(req, context=CTX)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  API error: {e.code} — {e.read().decode()[:200]}")
        return {"rows": []}


def load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return {"records": [], "keywords": {}}


def save_history(history):
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def load_watchlist():
    if WATCHLIST_FILE.exists():
        return json.loads(WATCHLIST_FILE.read_text())
    return {"keywords": []}


def save_watchlist(wl):
    WATCHLIST_FILE.write_text(json.dumps(wl, indent=2))


def record_rankings(token):
    """Record today's keyword positions."""
    print("\n  Recording today's keyword rankings...")

    end = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

    result = sc_query(token, start, end, ["query", "page"], 500)
    rows = result.get("rows", [])

    if not rows:
        print("  No data returned from Search Console. Try again later.\n")
        return

    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")

    # Deduplicate: keep best position per keyword
    kw_data = {}
    for row in rows:
        kw = row["keys"][0]
        page = row["keys"][1].replace(SITE_URL, "/")
        pos = round(row.get("position", 100), 1)
        clicks = row.get("clicks", 0)
        imps = row.get("impressions", 0)

        if kw not in kw_data or kw_data[kw]["position"] > pos:
            kw_data[kw] = {"position": pos, "page": page, "clicks": clicks, "impressions": imps}

    # Save today's snapshot
    snapshot = {"date": today, "keyword_count": len(kw_data), "data": {}}
    for kw, d in kw_data.items():
        snapshot["data"][kw] = {"pos": d["position"], "page": d["page"], "clicks": d["clicks"], "imps": d["impressions"]}

    # Update history — keep last 90 days
    history["records"] = [r for r in history["records"] if r["date"] != today]
    history["records"].append(snapshot)
    history["records"] = sorted(history["records"], key=lambda x: x["date"])[-90:]

    # Update keyword tracking
    for kw, d in kw_data.items():
        if kw not in history["keywords"]:
            history["keywords"][kw] = {"first_seen": today, "best_pos": d["position"], "best_date": today}
        if d["position"] < history["keywords"][kw]["best_pos"]:
            history["keywords"][kw]["best_pos"] = d["position"]
            history["keywords"][kw]["best_date"] = today
        history["keywords"][kw]["last_pos"] = d["position"]
        history["keywords"][kw]["last_seen"] = today
        history["keywords"][kw]["page"] = d["page"]

    save_history(history)
    print(f"  Recorded {len(kw_data)} keywords for {today}")
    print(f"  Total history: {len(history['records'])} days, {len(history['keywords'])} unique keywords\n")


def show_report(keyword_filter=None):
    """Show ranking trends."""
    history = load_history()
    if not history["records"]:
        print("\n  No ranking history. Run: python3 scripts/build-rank-tracker.py record\n")
        return

    records = history["records"]
    latest = records[-1]
    previous = records[-2] if len(records) >= 2 else None
    week_ago = None
    month_ago = None

    target_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    target_month = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    for r in records:
        if r["date"] <= target_week:
            week_ago = r
        if r["date"] <= target_month:
            month_ago = r

    print()
    print("=" * 110)
    print(f"  RANK TRACKER — tool.teamzlab.com")
    print(f"  Latest: {latest['date']} | History: {len(records)} days | Keywords: {latest['keyword_count']}")
    print("=" * 110)
    print()

    # Build keyword list with trends
    kw_list = []
    for kw, d in latest["data"].items():
        if keyword_filter and keyword_filter.lower() not in kw.lower():
            continue

        entry = {"keyword": kw, "pos": d["pos"], "page": d.get("page", ""), "clicks": d.get("clicks", 0), "imps": d.get("imps", 0)}

        # Calculate changes
        if previous and kw in previous["data"]:
            entry["prev"] = previous["data"][kw]["pos"]
            entry["change_1d"] = entry["prev"] - entry["pos"]  # positive = improved
        else:
            entry["prev"] = None
            entry["change_1d"] = 0

        if week_ago and kw in week_ago["data"]:
            entry["change_7d"] = week_ago["data"][kw]["pos"] - entry["pos"]
        else:
            entry["change_7d"] = 0

        if month_ago and kw in month_ago["data"]:
            entry["change_30d"] = month_ago["data"][kw]["pos"] - entry["pos"]
        else:
            entry["change_30d"] = 0

        kw_list.append(entry)

    # Sort by position
    kw_list.sort(key=lambda x: x["pos"])

    # Check watchlist
    wl = load_watchlist()
    watched = set(w.lower() for w in wl.get("keywords", []))

    print(f"  {'KEYWORD':<40s} {'POS':>5s} {'1d':>6s} {'7d':>6s} {'30d':>6s} {'CLICKS':>7s} {'IMPS':>7s} {'PAGE':<30s}")
    print(f"  {'-'*40} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*7} {'-'*7} {'-'*30}")

    for kw in kw_list[:50]:
        name = kw["keyword"][:39]
        pos = f"{kw['pos']:.0f}"
        c1 = format_change(kw["change_1d"])
        c7 = format_change(kw["change_7d"])
        c30 = format_change(kw["change_30d"])
        clicks = f"{kw['clicks']}"
        imps = f"{kw['imps']}"
        page = kw.get("page", "")[:29]
        star = "*" if kw["keyword"].lower() in watched else " "

        print(f" {star}{name:<40s} {pos:>5s} {c1:>6s} {c7:>6s} {c30:>6s} {clicks:>7s} {imps:>7s} {page:<30s}")

    # Summary
    page1 = len([k for k in kw_list if k["pos"] <= 10])
    page2 = len([k for k in kw_list if 10 < k["pos"] <= 20])
    improved = len([k for k in kw_list if k["change_7d"] > 0])
    declined = len([k for k in kw_list if k["change_7d"] < 0])

    print()
    print(f"  Page 1 (pos 1-10): {page1} | Page 2 (pos 11-20): {page2}")
    print(f"  7-day movers: {improved} improved, {declined} declined")
    if watched:
        print(f"  * = tracked keyword ({len(watched)} in watchlist)")
    print()


def format_change(val):
    if val > 0:
        return f"+{val:.0f}"
    elif val < 0:
        return f"{val:.0f}"
    return "-"


def show_movers():
    """Show biggest position changes."""
    history = load_history()
    if len(history["records"]) < 2:
        print("\n  Need at least 2 days of data. Run 'record' daily.\n")
        return

    latest = history["records"][-1]

    # Compare with 7 days ago if available, else earliest
    target = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    compare = None
    for r in history["records"]:
        if r["date"] <= target:
            compare = r
    if not compare:
        compare = history["records"][0]

    movers = []
    for kw, d in latest["data"].items():
        if kw in compare["data"]:
            old_pos = compare["data"][kw]["pos"]
            new_pos = d["pos"]
            change = old_pos - new_pos  # positive = improved
            if abs(change) >= 2:
                movers.append({"keyword": kw, "old": old_pos, "new": new_pos, "change": change, "page": d.get("page", "")})

    winners = sorted([m for m in movers if m["change"] > 0], key=lambda x: -x["change"])
    losers = sorted([m for m in movers if m["change"] < 0], key=lambda x: x["change"])

    print()
    print("=" * 100)
    print(f"  BIGGEST MOVERS — {compare['date']} → {latest['date']}")
    print("=" * 100)

    if winners:
        print(f"\n  WINNERS (moved UP):")
        print(f"  {'KEYWORD':<40s} {'OLD':>5s} {'NEW':>5s} {'CHANGE':>8s} {'PAGE':<30s}")
        print(f"  {'-'*40} {'-'*5} {'-'*5} {'-'*8} {'-'*30}")
        for m in winners[:15]:
            name = m["keyword"][:39]
            print(f"  {name:<40s} {m['old']:>5.0f} {m['new']:>5.0f} {'+' + str(int(m['change'])):>8s} {m['page'][:29]:<30s}")

    if losers:
        print(f"\n  LOSERS (moved DOWN):")
        print(f"  {'KEYWORD':<40s} {'OLD':>5s} {'NEW':>5s} {'CHANGE':>8s} {'PAGE':<30s}")
        print(f"  {'-'*40} {'-'*5} {'-'*5} {'-'*8} {'-'*30}")
        for m in losers[:15]:
            name = m["keyword"][:39]
            print(f"  {name:<40s} {m['old']:>5.0f} {m['new']:>5.0f} {str(int(m['change'])):>8s} {m['page'][:29]:<30s}")

    print(f"\n  Total: {len(winners)} improved, {len(losers)} declined, {len(movers)} moved 2+ positions\n")


def manage_watchlist(action, keyword=None):
    wl = load_watchlist()
    if action == "show":
        if not wl["keywords"]:
            print("\n  Watchlist is empty. Add keywords:")
            print("    python3 scripts/build-rank-tracker.py track \"passer rating calculator\"\n")
            return
        print(f"\n  WATCHLIST ({len(wl['keywords'])} keywords):")
        history = load_history()
        for kw in wl["keywords"]:
            if kw in history.get("keywords", {}):
                info = history["keywords"][kw]
                print(f"    {kw:<45s} pos:{info.get('last_pos', '?'):>5} best:{info.get('best_pos', '?'):>5} page:{info.get('page', '?')}")
            else:
                print(f"    {kw:<45s} (no data yet)")
        print()

    elif action == "add" and keyword:
        if keyword not in wl["keywords"]:
            wl["keywords"].append(keyword)
            save_watchlist(wl)
            print(f"\n  Added '{keyword}' to watchlist ({len(wl['keywords'])} total)\n")
        else:
            print(f"\n  '{keyword}' already in watchlist\n")

    elif action == "remove" and keyword:
        wl["keywords"] = [k for k in wl["keywords"] if k.lower() != keyword.lower()]
        save_watchlist(wl)
        print(f"\n  Removed '{keyword}' from watchlist\n")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else ""

    if cmd == "record":
        token = refresh_token()
        if not token:
            print("  ERROR: No Search Console token. Run: python3 build-search-console-auth.py\n")
            return
        record_rankings(token)

    elif cmd == "report":
        kw_filter = None
        if "--keyword" in args:
            idx = args.index("--keyword")
            kw_filter = args[idx + 1] if idx + 1 < len(args) else None
        show_report(kw_filter)

    elif cmd == "movers":
        show_movers()

    elif cmd == "track":
        if len(args) < 2:
            print("\n  Usage: python3 scripts/build-rank-tracker.py track \"keyword\"\n")
            return
        manage_watchlist("add", " ".join(args[1:]))

    elif cmd == "untrack":
        if len(args) < 2:
            print("\n  Usage: python3 scripts/build-rank-tracker.py untrack \"keyword\"\n")
            return
        manage_watchlist("remove", " ".join(args[1:]))

    elif cmd == "watchlist":
        manage_watchlist("show")

    else:
        # Default: record + report
        token = refresh_token()
        if not token:
            print("  ERROR: No Search Console token. Run: python3 build-search-console-auth.py\n")
            return
        record_rankings(token)
        show_report()


if __name__ == "__main__":
    main()
