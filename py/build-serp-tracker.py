#!/usr/bin/env python3
"""
Automated SERP feature detection for tracked keywords.

Reads keywords from the rank tracker watchlist (or TEAMZ_SERP_KEYWORDS env),
fetches Google search results, and detects SERP features via regex/string
matching (featured snippet, PAA, video carousel, knowledge panel, AI overview,
image pack).

Usage:
    python3 py/build-serp-tracker.py                # detect + append to CSV
    python3 py/build-serp-tracker.py --report        # show latest per keyword
    python3 py/build-serp-tracker.py --dry-run       # print keyword list only

Data: TEAMZ_DATA_DIR/serp-features-history.csv
Respectful: 3s delay between requests, max 30 keywords per run.
"""

import csv
import json
import os
import re
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

_CSV_COLUMNS = [
    "date", "keyword", "featured_snippet", "paa", "video",
    "knowledge_panel", "ai_overview", "image_pack",
]

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_MAX_KEYWORDS = 30
_DELAY_SECONDS = 3


def _load_keywords() -> list:
    """Load keywords from env or rank-watchlist.json."""
    env_kw = os.getenv("TEAMZ_SERP_KEYWORDS", "").strip()
    if env_kw:
        return [k.strip() for k in env_kw.split(",") if k.strip()]

    watchlist_path = _CFG["data_dir"] / "rank-watchlist.json"
    if watchlist_path.exists():
        try:
            data = json.loads(watchlist_path.read_text())
            kws = data.get("keywords", [])
            if isinstance(kws, list):
                return [k for k in kws if isinstance(k, str) and k.strip()]
        except (json.JSONDecodeError, KeyError):
            pass

    return []


def _fetch_serp(keyword: str) -> str:
    """Fetch Google search HTML for *keyword*."""
    q = urllib.parse.quote_plus(keyword)
    url = f"https://www.google.com/search?q={q}&hl=en"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", _UA)
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=_CTX)
        return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"    Fetch error for '{keyword}': {e}")
        return ""


def _detect_features(html: str) -> dict:
    """Detect SERP features from raw HTML via regex/string matching."""
    h = html.lower()
    return {
        "featured_snippet": bool(
            re.search(r'class="[^"]*kno-rdesc[^"]*"', h)
            or re.search(r'data-attrid="wa:/description"', h)
            or re.search(r'class="[^"]*IZ6rdc[^"]*"', h)
            or re.search(r'<div[^>]*class="[^"]*xpdopen[^"]*"[^>]*>.*?<span', h, re.DOTALL)
        ),
        "paa": bool(
            "people also ask" in h
            or re.search(r'class="[^"]*related-question-pair[^"]*"', h)
            or re.search(r'data-q="', h)
        ),
        "video": bool(
            re.search(r'class="[^"]*video-result[^"]*"', h)
            or "youtube.com/watch" in h
            or re.search(r'class="[^"]*MjjYud[^"]*"[^>]*>.*?video', h, re.DOTALL)
        ),
        "knowledge_panel": bool(
            re.search(r'class="[^"]*kp-wholepage[^"]*"', h)
            or re.search(r'class="[^"]*knowledge-panel[^"]*"', h)
            or re.search(r'data-attrid="title"', h)
        ),
        "ai_overview": bool(
            "ai overview" in h
            or re.search(r'class="[^"]*aipromo[^"]*"', h)
            or re.search(r'data-sgs=', h)
        ),
        "image_pack": bool(
            re.search(r'class="[^"]*img-brk[^"]*"', h)
            or re.search(r'id="imagebox_bigimages"', h)
            or re.search(r'class="[^"]*islrc[^"]*"', h)
            or re.search(r'<g-scrolling-carousel[^>]*>.*?<img', h, re.DOTALL)
        ),
    }


def _append_csv(row: dict, csv_path: Path) -> None:
    new_file = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
        if new_file:
            w.writeheader()
        w.writerow(row)


def _show_report(csv_path: Path) -> None:
    if not csv_path.exists():
        print("\n  No data yet. Run without --report first.\n")
        return

    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Group by keyword, keep latest per keyword
    latest = {}
    for r in rows:
        kw = r.get("keyword", "")
        latest[kw] = r

    print()
    print("=" * 100)
    print("  SERP FEATURES — Latest per Keyword")
    print("=" * 100)
    print(f"\n  {'KEYWORD':<35s} {'SNIPPET':>8s} {'PAA':>5s} {'VIDEO':>6s} {'KP':>4s} {'AI':>4s} {'IMGS':>5s} {'DATE':>12s}")
    print(f"  {'-'*35} {'-'*8} {'-'*5} {'-'*6} {'-'*4} {'-'*4} {'-'*5} {'-'*12}")

    for kw in sorted(latest.keys()):
        r = latest[kw]
        def _yn(key):
            return "Y" if r.get(key, "").lower() == "true" else "-"
        print(
            f"  {kw[:34]:<35s} {_yn('featured_snippet'):>8s} {_yn('paa'):>5s} "
            f"{_yn('video'):>6s} {_yn('knowledge_panel'):>4s} {_yn('ai_overview'):>4s} "
            f"{_yn('image_pack'):>5s} {r.get('date', ''):>12s}"
        )

    print(f"\n  Total keywords tracked: {len(latest)}")
    print(f"  Total rows in history:  {len(rows)}\n")


def main() -> int:
    args = sys.argv[1:]
    csv_path = _CFG["data_dir"] / "serp-features-history.csv"
    _CFG["data_dir"].mkdir(parents=True, exist_ok=True)

    if "--report" in args:
        _show_report(csv_path)
        return 0

    keywords = _load_keywords()
    if not keywords:
        print("\n  No keywords found.")
        print("  Set TEAMZ_SERP_KEYWORDS env or add to rank-watchlist.json via build-rank-tracker.py\n")
        return 0

    keywords = keywords[:_MAX_KEYWORDS]

    if "--dry-run" in args:
        print(f"\n  Keywords ({len(keywords)}):")
        for kw in keywords:
            print(f"    - {kw}")
        print()
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    print()
    print("=" * 72)
    print(f"  SERP FEATURE TRACKER — {today}")
    print(f"  Keywords: {len(keywords)} | Delay: {_DELAY_SECONDS}s between requests")
    print("=" * 72)

    for i, kw in enumerate(keywords):
        print(f"\n  [{i+1}/{len(keywords)}] {kw}")
        html = _fetch_serp(kw)
        if not html:
            print("    Skipped (fetch failed)")
            continue

        features = _detect_features(html)
        detected = [k for k, v in features.items() if v]
        print(f"    Detected: {', '.join(detected) if detected else 'none'}")

        row = {"date": today, "keyword": kw}
        for feat_key in ["featured_snippet", "paa", "video", "knowledge_panel", "ai_overview", "image_pack"]:
            row[feat_key] = "true" if features.get(feat_key) else "false"

        _append_csv(row, csv_path)

        if i < len(keywords) - 1:
            time.sleep(_DELAY_SECONDS)

    print(f"\n  Results appended → {csv_path.name}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
