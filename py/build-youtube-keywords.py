#!/usr/bin/env python3
"""
YouTube-specific keyword / content research — FREE (no paid APIs).
====================================================================
For every project where we produce YouTube videos, Shorts, or Reels we must
treat YouTube as a separate search engine from Google Search. What ranks on
Google Search often flops on YouTube (developer-audience vs buyer-audience,
tutorial-intent vs commercial-intent). This script pulls real YouTube-specific
signals:

  1. YouTube Autocomplete (suggestqueries.google.com, ds=yt)
     — actual queries YouTube users type, ranked by popularity
  2. YouTube SERP top 10 titles per seed (via yt Data API when available,
     otherwise via the public watch endpoint)
  3. Composite YT-Score (0-100) = autocomplete position + depth of expansions
     + SERP title overlap

Outputs a table + JSON report for producing data-driven title, tags,
description, and thumbnail prompts. This is the script our internal workflow
runs BEFORE writing any YouTube metadata — never skip it, never assume.

Usage:
    python3 py/build-youtube-keywords.py "uber clone" "flutter uber clone"
    python3 py/build-youtube-keywords.py --seed-file seeds.txt
    python3 py/build-youtube-keywords.py --expand "uber clone" --top 20
    python3 py/build-youtube-keywords.py --serp "flutter uber clone" --top 10
    python3 py/build-youtube-keywords.py --report        # show last saved report

Data sources (all FREE):
    - YouTube Autocomplete (http://suggestqueries.google.com/complete/search?ds=yt)
    - YouTube watch SERP (https://www.youtube.com/results?search_query=...)

Outputs:
    TEAMZ_DATA_DIR/youtube-keywords-latest.json
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from _teamz_config import load_runtime
    _CFG = load_runtime(__file__)
    DATA_DIR = _CFG["data_dir"]
except Exception:
    # Script is runnable standalone without the host repo present.
    DATA_DIR = Path.cwd() / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

_CTX = ssl.create_default_context()
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
_AUTOCOMPLETE_DELAY = 0.6
_SERP_DELAY = 1.2


def yt_autocomplete(query: str, hl: str = "en", gl: str = "us") -> list[str]:
    """Call YouTube Autocomplete. Returns up to 10 suggestions."""
    url = (
        "http://suggestqueries.google.com/complete/search?"
        + urllib.parse.urlencode({"client": "firefox", "ds": "yt", "hl": hl, "gl": gl, "q": query})
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        resp = urllib.request.urlopen(req, context=_CTX, timeout=8)
        payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        raw = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        return [s for s in raw if isinstance(s, str)]
    except Exception as e:
        print(f"  autocomplete error for {query!r}: {e}", file=sys.stderr)
        return []


def yt_serp_titles(query: str, limit: int = 10) -> list[str]:
    """Scrape top video titles from the YouTube watch SERP for a query.

    We parse `"title":{"runs":[{"text":"..."}]` occurrences from the page. This
    is brittle vs the official Data API but costs nothing and matches what a
    human creator sees in the browser. Falls back to empty on failure.
    """
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": query, "sp": "EgIQAQ%253D%253D"})
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _UA,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        resp = urllib.request.urlopen(req, context=_CTX, timeout=10)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  serp error for {query!r}: {e}", file=sys.stderr)
        return []

    # Pattern covers "title":{"runs":[{"text":"..."}]} and "title":{"simpleText":"..."}
    titles: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r'"title"\s*:\s*\{\s*"runs"\s*:\s*\[\s*\{\s*"text"\s*:\s*"((?:[^"\\]|\\.)*)"', html):
        t = _decode(m.group(1))
        if _is_video_title(t, seen):
            titles.append(t)
            seen.add(t)
            if len(titles) >= limit:
                return titles
    for m in re.finditer(r'"title"\s*:\s*\{\s*"simpleText"\s*:\s*"((?:[^"\\]|\\.)*)"', html):
        t = _decode(m.group(1))
        if _is_video_title(t, seen):
            titles.append(t)
            seen.add(t)
            if len(titles) >= limit:
                return titles
    return titles


def _decode(s: str) -> str:
    # Basic JSON string unescape.
    try:
        return json.loads(f'"{s}"')
    except Exception:
        return s


_JUNK_TITLES = {"YouTube", "Search", "Trending", "Music", "Gaming", "News", "Live", ""}


def _is_video_title(t: str, seen: set[str]) -> bool:
    t = (t or "").strip()
    if not t or t in seen or t in _JUNK_TITLES:
        return False
    if len(t) < 6 or len(t) > 200:
        return False
    return True


def yt_score(seed: str, suggestions: list[str], serp_titles: list[str]) -> int:
    """Composite YT-Score 0-100.

    Heuristics:
      +40 if the seed itself appears in its own autocomplete (engine routes traffic)
      +6 per unique autocomplete suggestion (up to 10 suggestions = +60)
      +2 per SERP title that contains the seed as a phrase (up to 10 = +20)
      -10 if autocomplete returns 0 (cold topic on YT)

    Clamped 0-100.
    """
    seed_l = seed.lower().strip()
    score = 0
    sugg_l = [s.lower() for s in suggestions]
    if not sugg_l:
        score -= 10
    else:
        if any(s == seed_l for s in sugg_l):
            score += 40
        score += min(60, 6 * len(sugg_l))
    hits = sum(1 for t in serp_titles if seed_l in t.lower())
    score += min(20, 2 * hits)
    return max(0, min(100, score))


def tier(score: int) -> str:
    if score >= 80:
        return "VERY HIGH"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    if score >= 20:
        return "LOW"
    return "VERY LOW"


def analyse_seed(seed: str, with_serp: bool = True, hl: str = "en", gl: str = "us") -> dict:
    suggestions = yt_autocomplete(seed, hl=hl, gl=gl)
    time.sleep(_AUTOCOMPLETE_DELAY)
    serp = yt_serp_titles(seed) if with_serp else []
    if with_serp:
        time.sleep(_SERP_DELAY)
    return {
        "seed": seed,
        "suggestions": suggestions[:10],
        "serp_titles": serp[:10],
        "score": yt_score(seed, suggestions, serp),
    }


def print_table(results: list[dict]) -> None:
    print("\n  Keyword                              Score Tier        Sugg  SERP")
    print("  " + "-" * 72)
    for r in results:
        kw = r["seed"][:36]
        print(f"  {kw:<36} {r['score']:>3}/100 {tier(r['score']):<10} {len(r['suggestions']):>4}   {len(r['serp_titles']):>3}")


def print_details(results: list[dict]) -> None:
    for r in results:
        print(f"\n=== {r['seed']} (score {r['score']}/100, {tier(r['score'])}) ===")
        if r["suggestions"]:
            print("  YT Autocomplete:")
            for s in r["suggestions"]:
                print(f"    - {s}")
        else:
            print("  YT Autocomplete: (empty — cold topic on YouTube)")
        if r["serp_titles"]:
            print("  YT SERP top titles:")
            for t in r["serp_titles"]:
                print(f"    • {t}")


def save_report(results: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "source": "YouTube Autocomplete + watch SERP",
        "count": len(results),
        "results": results,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))


def load_report(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="YouTube-specific keyword research (autocomplete + SERP top titles).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("seeds", nargs="*", help="Seed query strings (space-separated).")
    ap.add_argument("--seed-file", help="Path to a text file with one seed per line.")
    ap.add_argument("--expand", help="Single seed — print full autocomplete list (up to 10).")
    ap.add_argument("--serp", help="Single seed — print top SERP titles (up to --top).")
    ap.add_argument("--top", type=int, default=10, help="Limit for --serp titles (default 10).")
    ap.add_argument("--details", action="store_true", help="Also print full per-seed details.")
    ap.add_argument("--no-serp", action="store_true", help="Skip SERP scrape (autocomplete only).")
    ap.add_argument("--hl", default="en", help="Language code (default 'en').")
    ap.add_argument("--gl", default="us", help="Region code (default 'us'). Use 'ae', 'ng', 'ke', etc.")
    ap.add_argument("--report", action="store_true", help="Print the last saved report and exit.")
    ap.add_argument("--output", help="Override output JSON path.")
    return ap.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    report_path = Path(args.output) if args.output else (DATA_DIR / "youtube-keywords-latest.json")

    if args.report:
        rep = load_report(report_path)
        if not rep:
            print(f"No saved report at {report_path}")
            return 1
        print(f"Saved report: {report_path} (generated {rep.get('generated_at')})")
        print_table(rep.get("results", []))
        return 0

    if args.expand:
        sugg = yt_autocomplete(args.expand, hl=args.hl, gl=args.gl)
        print(f"\nYT autocomplete for {args.expand!r}:")
        for s in sugg:
            print(f"  - {s}")
        return 0

    if args.serp:
        titles = yt_serp_titles(args.serp, limit=args.top)
        print(f"\nYT SERP top {len(titles)} titles for {args.serp!r}:")
        for t in titles:
            print(f"  • {t}")
        return 0

    seeds: list[str] = list(args.seeds)
    if args.seed_file:
        p = Path(args.seed_file).expanduser()
        seeds.extend([line.strip() for line in p.read_text().splitlines() if line.strip() and not line.startswith("#")])
    if not seeds:
        print("No seeds given. Examples:", file=sys.stderr)
        print("  python3 py/build-youtube-keywords.py 'uber clone' 'flutter uber clone'", file=sys.stderr)
        print("  python3 py/build-youtube-keywords.py --seed-file seeds.txt", file=sys.stderr)
        return 2

    print("=" * 72)
    print("  YOUTUBE KEYWORD RESEARCH (free — Autocomplete + SERP)")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}Z  |  seeds={len(seeds)}  hl={args.hl} gl={args.gl}")
    print("=" * 72)

    results: list[dict] = []
    for i, s in enumerate(seeds, 1):
        print(f"  Analysing [{i}/{len(seeds)}]: {s}...")
        results.append(analyse_seed(s, with_serp=not args.no_serp, hl=args.hl, gl=args.gl))

    print_table(results)
    if args.details:
        print_details(results)

    save_report(results, report_path)
    print(f"\nFull report -> {report_path}")
    print("Tier legend: 80-100 VERY HIGH | 60-79 HIGH | 40-59 MEDIUM | 20-39 LOW | 0-19 VERY LOW")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
