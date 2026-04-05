#!/usr/bin/env python3
"""
ASO Keyword Research Pipeline — produces scored CSVs for the ASO Store Publish Guide.

Combines autocomplete discovery, competitor analysis, trending extraction, and
scoring into the ``ios_keywords.csv`` / ``master_keywords.csv`` files that
``aso-store-publish-guide.md`` requires.

Uses only the Python standard library. Reads config from ``.teamz-automation.env``.

Usage::

    # Full pipeline (all seed keywords from TEAMZ_ASO_KEYWORDS)
    python3 py/aso/aso-keyword-pipeline.py

    # Custom seeds
    python3 py/aso/aso-keyword-pipeline.py --seeds "ai shopping assistant,product recommendation"

    # Specific category
    python3 py/aso/aso-keyword-pipeline.py --category shopping

    # Dry run (print results, don't write CSVs)
    python3 py/aso/aso-keyword-pipeline.py --dry-run

Output files (in TEAMZ_DATA_DIR):
    - master_keywords.csv   — All keywords (iOS + Android), scored
    - ios_keywords.csv      — iOS-only keywords, scored
    - top_by_category/      — One CSV per category
    - aso-pipeline-latest.json — Full run metadata
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _teamz_config import load_runtime  # noqa: E402

from aso._aso_common import (  # noqa: E402
    apple_autocomplete,
    ensure_data_dir,
    itunes_search,
    play_autocomplete,
    top_keywords,
)

# Import volume estimation from build-keyword-volume.py
_VOLUME_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "build-keyword-volume.py"
)
_volume_mod = None


def _get_volume_estimator():
    """Lazy-load build-keyword-volume.py as a module."""
    global _volume_mod
    if _volume_mod is not None:
        return _volume_mod
    if not os.path.exists(_VOLUME_MODULE_PATH):
        print(f"  [warn] build-keyword-volume.py not found at {_VOLUME_MODULE_PATH}")
        return None
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("keyword_volume", _VOLUME_MODULE_PATH)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    _volume_mod = mod
    return mod

_CFG = load_runtime(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py")
)
# Pipeline CSVs are PROJECT-level data (not kit-level).
# Prefer TEAMZ_DATA_DIR from the project's .env; fall back to host_site_root/automation_data.
_DATA_DIR = Path(
    os.environ.get("TEAMZ_DATA_DIR", "")
    or _CFG.get("data_dir", "")
    or str(Path(_CFG["host_site_root"]) / "automation_data")
)

# ── CSV schema (matches aso-store-publish-guide.md) ──────────────────────────
_CSV_COLUMNS = [
    "keyword",
    "platform",       # ios | android | both
    "category",       # App Store / Play Store category (snake_case)
    "avg_score",      # Average signal score across discovery methods (0.0–1.0)
    "max_score",      # Peak signal score observed (0.0–1.0)
    "trending_days",  # Number of discovery methods that surfaced this keyword
    "score",          # Composite opportunity score (0.0–1.0)
]


# ── Scoring helpers ──────────────────────────────────────────────────────────

def _platform_score(apple_hit: bool, play_hit: bool) -> float:
    """Score based on which platforms returned this keyword (0.0–1.0).

    Both = 1.0, single platform = 0.6, neither = 0.0.
    """
    if apple_hit and play_hit:
        return 1.0
    if apple_hit or play_hit:
        return 0.6
    return 0.0


def _competition_score(competitors: list[dict]) -> float:
    """Score inversely proportional to competition strength (0.0–1.0).

    Low competition (few reviews, low ratings) = higher score = bigger opportunity.
    """
    if not competitors:
        return 0.75  # No competitors found = moderate opportunity signal

    avg_reviews = sum(c.get("reviews", 0) for c in competitors) / max(len(competitors), 1)
    avg_rating = sum(c.get("rating", 0) for c in competitors if c.get("rating")) / max(
        sum(1 for c in competitors if c.get("rating")), 1
    )

    # Review volume: fewer reviews = less competition
    if avg_reviews < 100:
        review_score = 1.0
    elif avg_reviews < 1000:
        review_score = 0.75
    elif avg_reviews < 10000:
        review_score = 0.5
    elif avg_reviews < 100000:
        review_score = 0.3
    else:
        review_score = 0.15

    # Rating gap: if competitors have low ratings, room to outperform
    if avg_rating < 3.5:
        rating_bonus = 0.2
    elif avg_rating < 4.0:
        rating_bonus = 0.1
    else:
        rating_bonus = 0.0

    return min(review_score + rating_bonus, 1.0)


def _length_score(keyword: str) -> float:
    """Longer (long-tail) keywords have less competition (0.0–1.0)."""
    words = keyword.split()
    if len(words) >= 4:
        return 1.0
    if len(words) == 3:
        return 0.8
    if len(words) == 2:
        return 0.5
    return 0.2  # Single word = very competitive


def _discovery_breadth_score(discovery_count: int, max_methods: int) -> float:
    """How many discovery methods surfaced this keyword (0.0–1.0).

    More methods = stronger signal that real users search for this.
    """
    if max_methods <= 0:
        return 0.0
    return min(discovery_count / max_methods, 1.0)


def compute_scores(kw_record: dict) -> dict:
    """Compute avg_score, max_score, and composite score for a keyword record.

    kw_record must have: keyword, apple_hit, play_hit, competitors, discovery_count,
    max_discovery_methods, trending_count.
    Optional: volume_score (0-100 from build-keyword-volume.py).
    """
    platform = _platform_score(kw_record["apple_hit"], kw_record["play_hit"])
    competition = _competition_score(kw_record.get("competitors", []))
    length = _length_score(kw_record["keyword"])
    breadth = _discovery_breadth_score(
        kw_record["discovery_count"], kw_record["max_discovery_methods"]
    )
    trending = min(kw_record.get("trending_count", 0) / 3.0, 1.0)

    # Volume score from build-keyword-volume.py (0-100 → normalized to 0-1)
    raw_volume = kw_record.get("volume_score", 0)
    volume = raw_volume / 100.0 if raw_volume else 0.0

    has_volume = raw_volume is not None and raw_volume > 0

    # avg_score: average of all signal dimensions
    signals = [platform, competition, length, breadth, trending]
    if has_volume:
        signals.append(volume)
    avg_score = sum(signals) / len(signals)

    # max_score: strongest single signal
    max_score = max(signals)

    if has_volume:
        # With real volume data: volume is the DOMINANT signal (35%)
        #   volume (35%) — does anyone actually search this?
        #   competition (25%) — can we rank for it?
        #   platform presence (20%) — confirmed on both stores?
        #   discovery breadth (10%) — how many methods found it?
        #   length/specificity (5%) — long-tail advantage
        #   trending (5%) — category trending signal
        score = (
            0.35 * volume
            + 0.25 * competition
            + 0.20 * platform
            + 0.10 * breadth
            + 0.05 * length
            + 0.05 * trending
        )
    else:
        # Without volume data: fall back to discovery-based scoring
        score = (
            0.30 * platform
            + 0.25 * competition
            + 0.20 * breadth
            + 0.15 * length
            + 0.10 * trending
        )

    return {
        "avg_score": round(avg_score, 4),
        "max_score": round(max_score, 4),
        "score": round(score, 4),
    }


# ── Discovery methods ────────────────────────────────────────────────────────

def discover_suggest(seed: str) -> list[dict]:
    """Run Apple + Play autocomplete for a seed term."""
    apple = apple_autocomplete(seed)
    play = play_autocomplete(seed)
    a_set = {x.strip().lower() for x in apple if x and x.strip()}
    p_set = {x.strip().lower() for x in play if x and x.strip()}

    results = []
    for kw in sorted(a_set | p_set):
        results.append({
            "keyword": kw,
            "apple_hit": kw in a_set,
            "play_hit": kw in p_set,
            "method": "suggest",
        })
    return results


def discover_expand(seed: str) -> list[dict]:
    """Two-level autocomplete expansion."""
    apple_l1 = apple_autocomplete(seed)
    play_l1 = play_autocomplete(seed)

    sources = {}
    seen_seeds = set()

    def ingest(items, platform):
        for raw in items:
            kw = (raw or "").strip().lower()
            if not kw:
                continue
            if kw not in sources:
                sources[kw] = {"apple": False, "play": False}
            sources[kw][platform] = True

    ingest(apple_l1, "apple")
    ingest(play_l1, "play")

    # Level 2: expand each L1 result
    for raw in apple_l1 + play_l1:
        s = (raw or "").strip().lower()
        if not s or s in seen_seeds:
            continue
        seen_seeds.add(s)
        ingest(apple_autocomplete(s), "apple")
        ingest(play_autocomplete(s), "play")

    results = []
    for kw, plats in sorted(sources.items()):
        results.append({
            "keyword": kw,
            "apple_hit": plats["apple"],
            "play_hit": plats["play"],
            "method": "expand",
        })
    return results


def discover_trending(category: str) -> list[dict]:
    """Extract trending keywords from iTunes top apps in a category."""
    apps = itunes_search(category, limit=25)
    titles = [r.get("trackName", "").strip() for r in apps if r.get("trackName")]
    blob = " ".join(titles)
    ranked = top_keywords(blob, n=40)

    results = []
    for word, freq in ranked:
        results.append({
            "keyword": word,
            "apple_hit": True,
            "play_hit": False,
            "method": "trending",
            "trending_freq": freq,
        })
    return results


def discover_long_tail(seed: str) -> list[dict]:
    """Apple autocomplete with a-z suffix."""
    seen = set()
    results = []
    for letter in "abcdefghijklmnopqrstuvwxyz":
        q = f"{seed} {letter}"
        for raw in apple_autocomplete(q):
            kw = (raw or "").strip().lower()
            if not kw or kw in seen:
                continue
            seen.add(kw)
            results.append({
                "keyword": kw,
                "apple_hit": True,
                "play_hit": False,
                "method": "long-tail",
            })
    return results


def discover_competitors(seed: str) -> tuple[list[dict], list[dict]]:
    """Find competitor apps and extract their title keywords.

    Returns (keyword_rows, competitor_records).
    """
    apps = itunes_search(seed, limit=10)
    competitor_records = []
    for app in apps:
        competitor_records.append({
            "name": app.get("trackName", ""),
            "rating": app.get("averageUserRating", 0),
            "reviews": app.get("userRatingCount", 0),
            "trackId": app.get("trackId", 0),
        })

    # Extract keywords from competitor titles + descriptions
    titles = [app.get("trackName", "") for app in apps]
    descriptions = [app.get("description", "")[:500] for app in apps]  # First 500 chars
    blob = " ".join(titles + descriptions)
    ranked = top_keywords(blob, n=30)

    results = []
    for word, freq in ranked:
        results.append({
            "keyword": word,
            "apple_hit": True,
            "play_hit": False,
            "method": "competitor",
            "trending_freq": freq,
        })
    return results, competitor_records


# ── Pipeline orchestrator ────────────────────────────────────────────────────

def run_pipeline(
    seeds: list[str],
    category: str = "shopping",
    dry_run: bool = False,
) -> list[dict]:
    """Run the full keyword research pipeline.

    1. For each seed: suggest + expand
    2. Trending for the category
    3. Long-tail for top 3 seeds
    4. Competitor keyword extraction
    5. Merge, deduplicate, score
    6. Write CSVs
    """
    # Accumulator: keyword -> metadata
    kw_data: dict[str, dict] = {}
    competitor_cache: list[dict] = []
    total_methods = 5  # suggest, expand, trending, long-tail, competitor

    def merge(rows: list[dict]):
        for row in rows:
            kw = row["keyword"]
            if kw not in kw_data:
                kw_data[kw] = {
                    "keyword": kw,
                    "apple_hit": False,
                    "play_hit": False,
                    "discovery_count": 0,
                    "methods": set(),
                    "trending_count": 0,
                    "max_discovery_methods": total_methods,
                    "competitors": [],
                }
            rec = kw_data[kw]
            rec["apple_hit"] = rec["apple_hit"] or row.get("apple_hit", False)
            rec["play_hit"] = rec["play_hit"] or row.get("play_hit", False)
            method = row.get("method", "unknown")
            if method not in rec["methods"]:
                rec["methods"].add(method)
                rec["discovery_count"] += 1
            if row.get("trending_freq", 0) > 0:
                rec["trending_count"] += row["trending_freq"]

    print(f"[pipeline] Category: {category}")
    print(f"[pipeline] Seeds: {seeds}")
    print(f"[pipeline] Starting discovery...\n")

    # ── Step 1: Suggest for each seed ─────────────────────────────────────
    for i, seed in enumerate(seeds):
        print(f"  [{i+1}/{len(seeds)}] suggest: '{seed}'")
        merge(discover_suggest(seed))

    # ── Step 2: Expand for each seed ──────────────────────────────────────
    for i, seed in enumerate(seeds):
        print(f"  [{i+1}/{len(seeds)}] expand: '{seed}'")
        merge(discover_expand(seed))

    # ── Step 3: Trending for category ─────────────────────────────────────
    print(f"  [+] trending: '{category}'")
    merge(discover_trending(category))

    # ── Step 4: Long-tail for top 3 seeds ─────────────────────────────────
    for seed in seeds[:3]:
        print(f"  [+] long-tail: '{seed}'")
        merge(discover_long_tail(seed))

    # ── Step 5: Competitor analysis ───────────────────────────────────────
    for seed in seeds[:3]:
        print(f"  [+] competitors: '{seed}'")
        comp_kws, comp_records = discover_competitors(seed)
        merge(comp_kws)
        competitor_cache.extend(comp_records)

    # Attach competitors to all keywords for scoring
    for rec in kw_data.values():
        rec["competitors"] = competitor_cache

    # ── Step 6: Volume estimation (via build-keyword-volume.py) ──────────
    vol_mod = _get_volume_estimator()
    if vol_mod:
        # Run volume estimation on top keywords (both-platform first, then singles)
        # Sort by discovery_count to prioritize well-discovered keywords
        kw_by_discovery = sorted(
            kw_data.keys(),
            key=lambda k: (
                kw_data[k]["apple_hit"] and kw_data[k]["play_hit"],  # both platforms first
                kw_data[k]["discovery_count"],
            ),
            reverse=True,
        )
        # Estimate volume for top 50 keywords (rate-limited, ~1s each)
        top_n = min(50, len(kw_by_discovery))
        print(f"\n[pipeline] Running volume estimation on top {top_n} keywords "
              f"(via build-keyword-volume.py)...")
        for i, kw in enumerate(kw_by_discovery[:top_n]):
            if i % 10 == 0 and i > 0:
                print(f"    ...{i}/{top_n} done")
            try:
                vol_result = vol_mod.estimate_volume(kw)
                kw_data[kw]["volume_score"] = vol_result.get("composite_score", 0)
                kw_data[kw]["volume_tier"] = vol_result.get("volume_tier", "UNKNOWN")
                kw_data[kw]["bing_volume"] = vol_result.get("bing_volume")
            except Exception as e:
                print(f"    [warn] Volume estimation failed for '{kw}': {e}")
                kw_data[kw]["volume_score"] = 0
        print(f"    ...{top_n}/{top_n} done")
    else:
        print("\n[pipeline] ⚠️ build-keyword-volume.py not available — skipping volume estimation")
        print("    Scores will use discovery-based fallback (less accurate)")

    # ── Step 7: Score all keywords ────────────────────────────────────────
    print(f"\n[pipeline] Scoring {len(kw_data)} keywords...")
    scored_rows = []
    for kw, rec in kw_data.items():
        scores = compute_scores(rec)

        platform = "both" if rec["apple_hit"] and rec["play_hit"] else (
            "ios" if rec["apple_hit"] else "android"
        )

        scored_rows.append({
            "keyword": kw,
            "platform": platform,
            "category": category,
            "avg_score": scores["avg_score"],
            "max_score": scores["max_score"],
            "trending_days": rec["discovery_count"],  # repurposed: # of methods that found it
            "score": scores["score"],
        })

    # Sort by composite score descending
    scored_rows.sort(key=lambda r: r["score"], reverse=True)

    # ── Step 8: Filter out noise ──────────────────────────────────────────
    # Remove single-char keywords and very low scores
    scored_rows = [r for r in scored_rows if len(r["keyword"]) > 2 and r["score"] > 0.1]

    print(f"[pipeline] {len(scored_rows)} keywords after filtering\n")

    # Print top 30
    print(f"  {'Keyword':45s} {'Platform':8s} {'Score':>6s} {'Avg':>6s} {'Max':>6s} {'Methods':>7s}")
    print(f"  {'-'*45} {'-'*8} {'-'*6} {'-'*6} {'-'*6} {'-'*7}")
    for row in scored_rows[:30]:
        print(
            f"  {row['keyword']:45s} {row['platform']:8s} "
            f"{row['score']:6.4f} {row['avg_score']:6.4f} {row['max_score']:6.4f} "
            f"{row['trending_days']:>7d}"
        )

    if dry_run:
        print("\n[pipeline] Dry run — no files written.")
        return scored_rows

    # ── Step 9: Write CSVs ────────────────────────────────────────────────
    ensure_data_dir(_CFG)

    # master_keywords.csv
    master_path = _DATA_DIR / "master_keywords.csv"
    _write_csv(master_path, scored_rows)
    print(f"\n[pipeline] Wrote {master_path} ({len(scored_rows)} rows)")

    # ios_keywords.csv
    ios_rows = [r for r in scored_rows if r["platform"] in ("ios", "both")]
    ios_path = _DATA_DIR / "ios_keywords.csv"
    _write_csv(ios_path, ios_rows)
    print(f"[pipeline] Wrote {ios_path} ({len(ios_rows)} rows)")

    # top_by_category/
    cat_dir = _DATA_DIR / "top_by_category"
    cat_dir.mkdir(exist_ok=True)
    cat_path = cat_dir / f"{category}.csv"
    _write_csv(cat_path, scored_rows[:50])
    print(f"[pipeline] Wrote {cat_path} ({min(len(scored_rows), 50)} rows)")

    # Pipeline metadata JSON
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seeds": seeds,
        "category": category,
        "total_keywords": len(scored_rows),
        "ios_keywords": len(ios_rows),
        "volume_estimation": "build-keyword-volume.py" if vol_mod else "NOT AVAILABLE",
        "scoring_weights_with_volume": {
            "volume": 0.35,
            "competition": 0.25,
            "platform_presence": 0.20,
            "discovery_breadth": 0.10,
            "keyword_length": 0.05,
            "trending": 0.05,
        },
        "scoring_weights_without_volume": {
            "platform_presence": 0.30,
            "competition": 0.25,
            "discovery_breadth": 0.20,
            "keyword_length": 0.15,
            "trending": 0.10,
        },
        "top_20": scored_rows[:20],
        "competitors_analyzed": len(competitor_cache),
    }
    meta_path = _DATA_DIR / "aso-pipeline-latest.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[pipeline] Wrote {meta_path}")

    print(f"\n[pipeline] Done! CSVs ready for aso-store-publish-guide.md")
    return scored_rows


def _write_csv(path: Path, rows: list[dict]):
    """Write rows to CSV with the standard column schema."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "ASO Keyword Research Pipeline — produces scored CSVs "
            "(master_keywords.csv, ios_keywords.csv) for the ASO Store Publish Guide."
        ),
    )
    parser.add_argument(
        "--seeds",
        default="",
        help=(
            "Comma-separated seed keywords. "
            "Default: reads TEAMZ_ASO_KEYWORDS from .teamz-automation.env"
        ),
    )
    parser.add_argument(
        "--category",
        default="shopping",
        help="App Store category for trending analysis (default: shopping)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results but don't write CSV files",
    )
    args = parser.parse_args()

    # Resolve seeds
    seeds_str = args.seeds.strip()
    if not seeds_str:
        seeds_str = os.environ.get("TEAMZ_ASO_KEYWORDS", "")
    if not seeds_str:
        print(
            "[error] No seeds provided. Use --seeds or set TEAMZ_ASO_KEYWORDS in .teamz-automation.env",
            file=sys.stderr,
        )
        sys.exit(1)

    seeds = [s.strip() for s in seeds_str.split(",") if s.strip()]

    run_pipeline(seeds=seeds, category=args.category, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
