#!/usr/bin/env python3
"""
CLI for App Store (iTunes RSS) review analysis: fetch, keywords, sentiment,
complaints, praise, reply prompts, and historical trends.

Uses TEAMZ_ASO_COUNTRIES (comma-separated, default us) for storefronts.
Python standard library only.
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from statistics import mean

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from aso._aso_common import (  # noqa: E402
    ensure_data_dir,
    itunes_lookup,
    itunes_reviews,
    top_keywords,
    tokenize,  # noqa: F401
)
from _teamz_config import load_runtime  # noqa: E402

_CFG = load_runtime(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py")
)


def _countries():
    raw = os.getenv("TEAMZ_ASO_COUNTRIES", "us")
    return [c.strip().lower() for c in raw.split(",") if c.strip()]


def _review_key(r):
    return (r.get("author", ""), r.get("title", ""), (r.get("content") or "")[:200])


def fetch_reviews_merged(app_id, countries):
    """Fetch page 1 per country and merge with dedupe."""
    seen = set()
    out = []
    for country in countries:
        for r in itunes_reviews(str(app_id), country):
            k = _review_key(r)
            if k in seen:
                continue
            seen.add(k)
            out.append(r)
    return out


def _distribution(reviews):
    dist = {str(i): 0 for i in range(1, 6)}
    for r in reviews:
        rt = r.get("rating")
        if rt is None:
            continue
        k = str(int(rt))
        if k in dist:
            dist[k] += 1
    return dist


def _avg_rating(reviews):
    ratings = [r["rating"] for r in reviews if r.get("rating") is not None]
    if not ratings:
        return 0.0
    return round(mean(ratings), 3)


def _reviews_path(app_id):
    return ensure_data_dir(_CFG) / f"aso-reviews-{app_id}.json"


def _history_path():
    return ensure_data_dir(_CFG) / "aso-reviews-history.json"


def _load_saved_reviews(app_id):
    p = _reviews_path(app_id)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data.get("reviews", [])


def _save_reviews_snapshot(app_id, countries, reviews):
    payload = {
        "app_id": str(app_id),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "countries": countries,
        "reviews": reviews,
        "summary": {
            "total": len(reviews),
            "avg_rating": _avg_rating(reviews),
            "distribution": _distribution(reviews),
        },
    }
    p = _reviews_path(app_id)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload["summary"]


def _load_history():
    p = _history_path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "entries" in data:
        return data["entries"]
    return []


def _save_history(entries):
    _history_path().write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _append_history_today(app_id, summary):
    today = date.today().isoformat()
    entries = _load_history()
    filtered = [e for e in entries if not (e.get("app_id") == str(app_id) and e.get("date") == today)]
    filtered.append(
        {
            "app_id": str(app_id),
            "date": today,
            "review_count": summary["total"],
            "avg_rating": summary["avg_rating"],
            "distribution": summary["distribution"],
        }
    )
    filtered.sort(key=lambda e: (e.get("app_id", ""), e.get("date", "")))
    _save_history(filtered)


def _get_reviews_for_analysis(app_id, countries):
    saved = _load_saved_reviews(app_id)
    if saved is not None:
        return saved
    return fetch_reviews_merged(app_id, countries)


def _review_text_blob(reviews):
    parts = []
    for r in reviews:
        t = (r.get("title") or "").strip()
        c = (r.get("content") or "").strip()
        if t:
            parts.append(t)
        if c:
            parts.append(c)
    return "\n".join(parts)


def _print_fetch_summary(reviews):
    dist = _distribution(reviews)
    avg = _avg_rating(reviews)
    print(f"Total reviews: {len(reviews)}")
    print(f"Average rating: {avg}")
    print("Rating distribution:")
    for star in range(1, 6):
        n = dist[str(star)]
        print(f"  {star}★: {n}")


def cmd_fetch(app_id, countries):
    reviews = fetch_reviews_merged(app_id, countries)
    summary = _save_reviews_snapshot(app_id, countries, reviews)
    _append_history_today(app_id, summary)
    _print_fetch_summary(reviews)


def cmd_keywords(app_id, countries):
    reviews = _get_reviews_for_analysis(app_id, countries)
    if not reviews:
        print("No reviews. Run --fetch first or check APP_ID / storefronts.", file=sys.stderr)
        sys.exit(1)
    blob = _review_text_blob(reviews)
    for word, count in top_keywords(blob, 30):
        print(f"{count:5d}  {word}")


def cmd_sentiment(app_id, countries):
    reviews = _get_reviews_for_analysis(app_id, countries)
    pos = [r for r in reviews if r.get("rating") in (4, 5)]
    neg = [r for r in reviews if r.get("rating") in (1, 2)]
    pos_blob = _review_text_blob(pos)
    neg_blob = _review_text_blob(neg)
    print("=== Positive (4–5★) top keywords ===")
    for word, count in top_keywords(pos_blob, 30):
        print(f"{count:5d}  {word}")
    print()
    print("=== Negative (1–2★) top keywords ===")
    for word, count in top_keywords(neg_blob, 30):
        print(f"{count:5d}  {word}")


def _truncate(s, n):
    s = s or ""
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 3] + "..."


def cmd_complaints(app_id, countries):
    reviews = _get_reviews_for_analysis(app_id, countries)
    bad = [r for r in reviews if r.get("rating") in (1, 2)]
    if not bad:
        print("No 1–2 star reviews in dataset.")
        return
    for i, r in enumerate(bad, 1):
        title = (r.get("title") or "").strip()
        body = _truncate(r.get("content") or "", 200)
        print(f"--- #{i} ({r.get('rating')}★) ---")
        print(title)
        print(body)
        print()


def cmd_praise(app_id, countries):
    reviews = _get_reviews_for_analysis(app_id, countries)
    good = [r for r in reviews if r.get("rating") in (4, 5)]
    if not good:
        print("No 4–5 star reviews in dataset.")
        return
    for i, r in enumerate(good, 1):
        title = (r.get("title") or "").strip()
        body = _truncate(r.get("content") or "", 200)
        print(f"--- #{i} ({r.get('rating')}★) ---")
        print(title)
        print(body)
        print()


def _app_context_blurb(app_id, countries):
    cc = countries[0] if countries else "us"
    info = itunes_lookup(str(app_id), cc)
    if not info:
        return "Unknown app", "No description available from iTunes lookup."
    name = (info.get("trackName") or info.get("trackCensoredName") or "App").strip()
    desc = (info.get("description") or "")[:400].replace("\n", " ").strip()
    if not desc:
        desc = "No description available from iTunes lookup."
    return name, desc


def cmd_reply_prompts(app_id, countries):
    reviews = _get_reviews_for_analysis(app_id, countries)
    neg = [r for r in reviews if r.get("rating") in (1, 2)]
    if not neg:
        print("No negative reviews for prompts.")
        return
    app_name, app_desc = _app_context_blurb(app_id, countries)
    top5 = neg[:5]
    for i, r in enumerate(top5, 1):
        text = " ".join(
            [
                (r.get("title") or "").strip(),
                (r.get("content") or "").strip(),
            ]
        ).strip()
        prompt = (
            f"Reply to this review professionally: {text}. "
            f"App context: {app_name}, {app_desc}"
        )
        print(f"--- Prompt {i} ---")
        print(prompt)
        print()


def cmd_trends(app_id, countries):
    """Append today's snapshot from disk or fresh fetch, then print trend."""
    saved = _load_saved_reviews(app_id)
    if saved is not None:
        summary = {
            "total": len(saved),
            "avg_rating": _avg_rating(saved),
            "distribution": _distribution(saved),
        }
    else:
        reviews = fetch_reviews_merged(app_id, countries)
        summary = {
            "total": len(reviews),
            "avg_rating": _avg_rating(reviews),
            "distribution": _distribution(reviews),
        }
        _save_reviews_snapshot(app_id, countries, reviews)
    _append_history_today(app_id, summary)

    entries = [e for e in _load_history() if e.get("app_id") == str(app_id)]
    entries.sort(key=lambda e: e.get("date", ""))
    if not entries:
        print("No history entries yet.")
        return
    print(f"Trend for app_id={app_id} (newest last)")
    print(f"{'date':<12} {'reviews_in_snapshot':>20} {'avg_rating':>12}")
    for e in entries:
        print(
            f"{e.get('date',''):<12} {e.get('review_count', 0):>20} "
            f"{e.get('avg_rating', 0):>12}"
        )

    if len(entries) >= 2:
        cur = entries[-1]
        prev = entries[-2]
        cur_count = cur.get("review_count", 0)
        prev_count = prev.get("review_count", 0)
        delta = cur_count - prev_count
        cur_date = date.fromisoformat(cur["date"])
        prev_date = date.fromisoformat(prev["date"])
        days_gap = max(1, (cur_date - prev_date).days)
        print(f"\nRating velocity: +{delta} new ratings since last check ({days_gap} days ago)")

        if len(entries) >= 3:
            older = entries[-3]
            older_count = older.get("review_count", 0)
            prior_delta = prev_count - older_count
            older_date = date.fromisoformat(older["date"])
            prior_days = max(1, (prev_date - older_date).days)
            cur_rate = delta / days_gap
            prior_rate = prior_delta / prior_days
            if prior_rate > 0 and cur_rate < prior_rate:
                print("[!] Rating velocity declining — consider prompting happy users to rate")


def main():
    parser = argparse.ArgumentParser(
        description="App Store review analysis (iTunes RSS + local history)."
    )
    parser.add_argument("app_id", help="Numeric Apple app ID or bundle ID for lookup modes")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--fetch", action="store_true", help="Fetch reviews per country, save JSON + history")
    g.add_argument("--keywords", action="store_true", help="Top 30 keywords across review text")
    g.add_argument("--sentiment", action="store_true", help="Top keywords for positive vs negative")
    g.add_argument("--complaints", action="store_true", help="1–2★ reviews with title + excerpt")
    g.add_argument("--praise", action="store_true", help="4–5★ reviews with title + excerpt")
    g.add_argument(
        "--reply-prompts",
        action="store_true",
        help="LLM-ready reply prompts for top 5 negative reviews",
    )
    g.add_argument(
        "--trends",
        action="store_true",
        help="Update history with today and print time series",
    )
    args = parser.parse_args()
    countries = _countries()

    if args.fetch:
        cmd_fetch(args.app_id, countries)
    elif args.keywords:
        cmd_keywords(args.app_id, countries)
    elif args.sentiment:
        cmd_sentiment(args.app_id, countries)
    elif args.complaints:
        cmd_complaints(args.app_id, countries)
    elif args.praise:
        cmd_praise(args.app_id, countries)
    elif args.reply_prompts:
        cmd_reply_prompts(args.app_id, countries)
    elif args.trends:
        cmd_trends(args.app_id, countries)


if __name__ == "__main__":
    main()
