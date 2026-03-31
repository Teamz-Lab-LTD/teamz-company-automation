#!/usr/bin/env python3
"""
Auto-scan Reddit + Dev.to for brand mentions.

Fetches Reddit JSON search and Dev.to API for configured keywords, deduplicates
by URL, flags whether TEAMZ_SITE_URL is linked, and appends new mentions to CSV.

Usage:
    python3 py/build-reddit-scanner.py              # scan + append new mentions
    python3 py/build-reddit-scanner.py --report      # show recent unlinked mentions

Env:
    TEAMZ_BRAND_KEYWORDS   comma-separated keywords (default: "teamzlab,teamz lab tools")
    TEAMZ_REDDIT_SUBS      comma-separated subreddits (default: "InternetIsBeautiful,webdev,SEO")

Data: TEAMZ_DATA_DIR/brand-mentions-auto.csv
Respectful: 2s delay between requests.
"""

import csv
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from _teamz_config import load_runtime

_CFG = load_runtime(__file__)
_CTX = ssl.create_default_context()

_CSV_COLUMNS = ["date", "source", "subreddit_or_tag", "title", "url", "linked"]

_UA = "TeamzBrandScanner/1.0 (brand mention monitoring)"
_DELAY_SECONDS = 2


def _get_keywords() -> list:
    raw = os.getenv("TEAMZ_BRAND_KEYWORDS", "teamzlab,teamz lab tools").strip()
    return [k.strip() for k in raw.split(",") if k.strip()]


def _get_subreddits() -> list:
    raw = os.getenv("TEAMZ_REDDIT_SUBS", "InternetIsBeautiful,webdev,SEO").strip()
    return [s.strip() for s in raw.split(",") if s.strip()]


def _fetch_json(url: str) -> dict:
    """Fetch JSON from a URL with User-Agent header."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", _UA)
    req.add_header("Accept", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=_CTX)
        return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
        print(f"    Fetch error: {url[:80]}… — {e}")
        return {}


def _load_existing_urls(csv_path: Path) -> set:
    """Load already-seen URLs to deduplicate."""
    if not csv_path.exists():
        return set()
    with csv_path.open(newline="", encoding="utf-8") as f:
        return {r.get("url", "") for r in csv.DictReader(f)}


def _append_rows(rows: list, csv_path: Path) -> int:
    if not rows:
        return 0
    new_file = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
        if new_file:
            w.writeheader()
        for row in rows:
            w.writerow(row)
    return len(rows)


def _is_linked(text: str, site_url: str) -> bool:
    """Check if the text/URL contains our site domain."""
    domain = urllib.parse.urlparse(site_url).hostname or ""
    text_lower = text.lower()
    return domain.lower() in text_lower or site_url.lower().rstrip("/") in text_lower


def _scan_reddit(subreddits: list, keywords: list, site_url: str, seen: set) -> list:
    """Search Reddit JSON API for keyword mentions."""
    mentions = []
    for sub in subreddits:
        for kw in keywords:
            q = urllib.parse.quote_plus(kw)
            url = (
                f"https://www.reddit.com/r/{sub}/search.json"
                f"?q={q}&restrict_sr=1&sort=new&limit=10"
            )
            print(f"    r/{sub} + '{kw}'", end="")
            data = _fetch_json(url)
            children = []
            if isinstance(data, dict):
                children = data.get("data", {}).get("children", [])
            found = 0
            for child in children:
                d = child.get("data", {})
                post_url = d.get("url", "") or f"https://www.reddit.com{d.get('permalink', '')}"
                if post_url in seen:
                    continue
                seen.add(post_url)
                title = (d.get("title") or "").replace("\n", " ")[:500]
                selftext = d.get("selftext", "") or ""
                created = d.get("created_utc")
                post_date = (
                    datetime.utcfromtimestamp(created).strftime("%Y-%m-%d")
                    if created else datetime.now().strftime("%Y-%m-%d")
                )
                linked = _is_linked(selftext + " " + post_url + " " + title, site_url)
                mentions.append({
                    "date": post_date,
                    "source": "reddit",
                    "subreddit_or_tag": sub,
                    "title": title,
                    "url": post_url,
                    "linked": "true" if linked else "false",
                })
                found += 1
            print(f" → {found} new")
            time.sleep(_DELAY_SECONDS)
    return mentions


def _scan_devto(keywords: list, site_url: str, seen: set) -> list:
    """Search Dev.to API for keyword-tagged articles."""
    mentions = []
    for kw in keywords:
        tag = kw.replace(" ", "").lower()
        url = f"https://dev.to/api/articles?tag={urllib.parse.quote_plus(tag)}&per_page=10"
        print(f"    dev.to tag='{tag}'", end="")
        data = _fetch_json(url)
        if not isinstance(data, list):
            print(" → 0 new")
            time.sleep(_DELAY_SECONDS)
            continue
        found = 0
        for article in data:
            art_url = article.get("url", "")
            if art_url in seen:
                continue
            seen.add(art_url)
            title = (article.get("title") or "").replace("\n", " ")[:500]
            body = article.get("description", "") or ""
            pub_date = (article.get("published_at") or "")[:10] or datetime.now().strftime("%Y-%m-%d")
            linked = _is_linked(body + " " + art_url + " " + title, site_url)
            mentions.append({
                "date": pub_date,
                "source": "devto",
                "subreddit_or_tag": tag,
                "title": title,
                "url": art_url,
                "linked": "true" if linked else "false",
            })
            found += 1
        print(f" → {found} new")
        time.sleep(_DELAY_SECONDS)
    return mentions


def _show_report(csv_path: Path) -> None:
    if not csv_path.exists():
        print("\n  No data yet. Run without --report first.\n")
        return

    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    unlinked = [r for r in rows if r.get("linked", "").lower() != "true"]
    linked = [r for r in rows if r.get("linked", "").lower() == "true"]

    print()
    print("=" * 90)
    print("  BRAND MENTION SCANNER — Report")
    print("=" * 90)
    print(f"\n  Total mentions:   {len(rows)}")
    print(f"  Linked (has URL): {len(linked)}")
    print(f"  Unlinked:         {len(unlinked)}  ← outreach opportunities")

    if unlinked:
        print(f"\n  UNLINKED MENTIONS (newest first, top 30):")
        print(f"  {'-'*85}")
        for r in sorted(unlinked, key=lambda x: x.get("date", ""), reverse=True)[:30]:
            src = f"{r.get('source', '')}/{r.get('subreddit_or_tag', '')}"
            print(f"    {r.get('date', '')} | {src:<25s} | {r.get('title', '')[:50]}")
            print(f"      {r.get('url', '')}")
    print()


def main() -> int:
    args = sys.argv[1:]
    data_dir: Path = _CFG["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "brand-mentions-auto.csv"

    if "--report" in args:
        _show_report(csv_path)
        return 0

    site_url = _CFG["site_url"]
    keywords = _get_keywords()
    subreddits = _get_subreddits()

    print()
    print("=" * 72)
    print(f"  BRAND MENTION SCANNER")
    print(f"  Keywords:   {', '.join(keywords)}")
    print(f"  Subreddits: {', '.join(subreddits)}")
    print(f"  Site URL:   {site_url}")
    print("=" * 72)

    seen = _load_existing_urls(csv_path)
    all_new = []

    print(f"\n  Scanning Reddit...")
    all_new.extend(_scan_reddit(subreddits, keywords, site_url, seen))

    print(f"\n  Scanning Dev.to...")
    all_new.extend(_scan_devto(keywords, site_url, seen))

    written = _append_rows(all_new, csv_path)
    unlinked = sum(1 for m in all_new if m.get("linked") == "false")

    print(f"\n  New mentions found:  {len(all_new)}")
    print(f"  Appended to CSV:     {written}")
    print(f"  Unlinked (outreach): {unlinked}")
    print(f"  Data file: {csv_path.name}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
