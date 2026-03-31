#!/usr/bin/env python3
"""
ASO metadata auditor and optimizer for Apple App Store listings (iTunes Lookup API).

Uses shared helpers in aso/_aso_common.py and runtime paths from _teamz_config.

Examples:
  ./aso-metadata.py --audit 284882215
  ./aso-metadata.py --score 1234567890
  ./aso-metadata.py --compare 284882215 310633997
  ./aso-metadata.py --optimize 284882215 --keywords "photo,editor,filter"

Output is written to data/aso-metadata-latest.json (under TEAMZ_DATA_DIR / automation data).
Requires network access for iTunes Lookup. Stdlib only.
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from aso._aso_common import (  # noqa: E402
    ensure_data_dir,
    itunes_lookup,
    itunes_search,  # noqa: F401 — suite API surface; optional future cross-store flows
    play_store_metadata,  # noqa: F401
    tokenize,
    top_keywords,
)
from _teamz_config import load_runtime  # noqa: E402

_CFG = load_runtime(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py"))

_IOS_TITLE_MAX = 30
_IOS_SUBTITLE_MAX = 30
_CTA_PATTERN = re.compile(
    r"\b(get|download|try|install|free|today|now|start|join|subscribe|upgrade|"
    r"discover|learn more|click|tap here)\b",
    re.I,
)


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_release_date(raw):
    if not raw or not isinstance(raw, str):
        return None
    s = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _int_size(val):
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _screenshot_count(app):
    urls = app.get("screenshotUrls") or []
    ipad = app.get("ipadScreenshotUrls") or []
    if not isinstance(urls, list):
        urls = [urls] if urls else []
    if not isinstance(ipad, list):
        ipad = [ipad] if ipad else []
    return len(urls) + len(ipad)


def _rating_and_count(app):
    r = app.get("averageUserRating")
    if r is None:
        r = app.get("averageUserRatingForCurrentVersion")
    try:
        rating = float(r) if r is not None else 0.0
    except (TypeError, ValueError):
        rating = 0.0
    c = app.get("userRatingCount")
    if c is None:
        c = app.get("userRatingCountForCurrentVersion")
    try:
        count = int(c) if c is not None else 0
    except (TypeError, ValueError):
        count = 0
    return rating, count


def _analyze_description(description):
    desc = (description or "").strip()
    lines = [ln.strip() for ln in desc.splitlines() if ln.strip()]
    first_three = lines[:3]
    first_three_chars = sum(len(ln) for ln in first_three)
    cta_hits = bool(_CTA_PATTERN.search(desc))
    kw = top_keywords(desc, n=40)
    return {
        "char_len": len(desc),
        "line_count": len(lines),
        "first_three_lines": first_three,
        "first_three_char_count": first_three_chars,
        "cta_detected": cta_hits,
        "top_keywords": [{"word": w, "count": c} for w, c in kw[:20]],
    }


def _title_keyword_overlap(title, desc_top_words):
    if not title or not desc_top_words:
        return 0, []
    title_tokens = set(tokenize(title).keys())
    top_set = {w for w, _ in desc_top_words[:15]}
    overlap = sorted(title_tokens & top_set)
    return len(overlap), overlap


def analyze_app(app):
    """Build structured analysis dict for one iTunes result."""
    title = app.get("trackName") or ""
    desc = app.get("description") or ""
    desc_info = _analyze_description(desc)
    overlap_n, overlap_words = _title_keyword_overlap(title, desc_info["top_keywords"])
    rating, review_count = _rating_and_count(app)
    shots = _screenshot_count(app)
    rel = _parse_release_date(app.get("currentVersionReleaseDate") or app.get("releaseDate"))
    days_since = None
    if rel:
        rutc = rel.replace(tzinfo=timezone.utc) if rel.tzinfo is None else rel.astimezone(timezone.utc)
        days_since = (_utc_now() - rutc).days

    devices = app.get("supportedDevices")
    if not isinstance(devices, list):
        devices = [devices] if devices else []

    return {
        "bundle_id": app.get("bundleId"),
        "track_id": app.get("trackId"),
        "title": title,
        "title_char_len": len(title),
        "title_within_ios_limit": len(title) <= _IOS_TITLE_MAX,
        "subtitle_note": (
            "iTunes Lookup API does not expose the App Store subtitle field (30 char limit). "
            "Audit subtitle only inside App Store Connect."
        ),
        "description_analysis": desc_info,
        "title_desc_keyword_overlap_count": overlap_n,
        "title_desc_keyword_overlap_words": overlap_words,
        "rating": round(rating, 2),
        "review_count": review_count,
        "screenshot_total_count": shots,
        "iphone_screenshot_count": len(app.get("screenshotUrls") or []) if isinstance(app.get("screenshotUrls"), list) else 0,
        "ipad_screenshot_count": len(app.get("ipadScreenshotUrls") or []) if isinstance(app.get("ipadScreenshotUrls"), list) else 0,
        "last_updated": app.get("currentVersionReleaseDate") or app.get("releaseDate"),
        "days_since_update": days_since,
        "file_size_bytes": _int_size(app.get("fileSizeBytes")),
        "minimum_os_version": app.get("minimumOsVersion"),
        "content_advisory_rating": app.get("contentAdvisoryRating"),
        "supported_devices_sample": devices[:12],
        "supported_devices_count": len(devices),
        "version": app.get("version"),
        "primary_genre": app.get("primaryGenreName"),
        "artist_name": app.get("artistName"),
        "track_view_url": app.get("trackViewUrl"),
    }


def _score_component_title_length(char_len):
    if char_len <= 0:
        return 0, "empty title"
    if char_len <= _IOS_TITLE_MAX:
        return 10, "title within 30 chars"
    over = char_len - _IOS_TITLE_MAX
    pts = max(0, int(10 - min(10, over * 0.8)))
    return pts, f"title over limit by {over} chars"


def _score_component_title_keywords(overlap_n, desc_kw_count):
    if desc_kw_count == 0:
        return 0, "no description keywords to align"
    cap = min(5, max(1, desc_kw_count // 3))
    ratio = min(1.0, overlap_n / cap)
    pts = int(round(7 * ratio))
    return pts, f"title/description keyword overlap: {overlap_n}"


def _score_component_description(desc_info):
    ln = desc_info["char_len"]
    pts_len = 0
    if ln >= 1200:
        pts_len = 8
    elif ln >= 500:
        pts_len = 7
    elif ln >= 200:
        pts_len = 4
    elif ln > 0:
        pts_len = 2
    uniq_kw = len([x for x in desc_info["top_keywords"] if x["count"] >= 1])
    pts_kw = min(6, uniq_kw)
    pts_open = 0
    if desc_info["first_three_char_count"] >= 80 and len(desc_info["first_three_lines"]) >= 2:
        pts_open = 5
    elif desc_info["first_three_char_count"] >= 40:
        pts_open = 3
    pts_cta = 5 if desc_info["cta_detected"] else 0
    return (
        pts_len + pts_kw + pts_open + pts_cta,
        {
            "description_length": pts_len,
            "description_keyword_breadth": pts_kw,
            "description_opening_lines": pts_open,
            "description_cta": pts_cta,
        },
    )


def _score_component_rating(rating):
    if rating <= 0:
        return 0, "no average rating"
    pts = int(round(15 * min(1.0, rating / 5.0)))
    return pts, f"rating {rating:.2f} / 5"


def _score_component_reviews(count):
    if count <= 0:
        return 0, "no review count"
    pts = int(round(10 * min(1.0, math.log10(count + 1) / math.log10(10_001))))
    return min(10, pts), f"reviews: {count}"


def _score_component_screenshots(n):
    if n >= 8:
        return 15, f"{n} screenshots (strong)"
    if n >= 5:
        return 10, f"{n} screenshots"
    if n >= 3:
        return 7, f"{n} screenshots"
    if n >= 1:
        return 4, f"{n} screenshots"
    return 0, "no screenshots in API payload"


def _score_component_freshness(days_since):
    if days_since is None:
        return 0, "unknown update date"
    if days_since <= 90:
        return 10, f"updated {days_since}d ago"
    if days_since <= 180:
        return 6, f"updated {days_since}d ago"
    if days_since <= 365:
        return 3, f"updated {days_since}d ago"
    return 1, f"stale ({days_since}d)"


def _score_component_extras(app, analysis):
    pts = 0
    notes = []
    if analysis.get("file_size_bytes"):
        pts += 3
        notes.append("file size present")
    if analysis.get("content_advisory_rating"):
        pts += 3
        notes.append("content rating present")
    if analysis.get("minimum_os_version"):
        pts += 2
        notes.append("min OS present")
    if analysis.get("supported_devices_count", 0) > 0:
        pts += 2
        notes.append("supported devices listed")
    pts = min(10, pts)
    return pts, "; ".join(notes) if notes else "sparse listing metadata"


def compute_aso_score(app, analysis):
    """Return (0-100 int, breakdown dict, messages)."""
    breakdown = {}
    messages = []

    p, m = _score_component_title_length(analysis["title_char_len"])
    breakdown["title_length"] = p
    messages.append(m)

    desc_kw = analysis["description_analysis"]["top_keywords"]
    p, m = _score_component_title_keywords(analysis["title_desc_keyword_overlap_count"], len(desc_kw))
    breakdown["title_keyword_alignment"] = p
    messages.append(m)

    p, sub = _score_component_description(analysis["description_analysis"])
    breakdown.update(sub)
    messages.append("description bundle scored")

    p, m = _score_component_rating(analysis["rating"])
    breakdown["rating"] = p
    messages.append(m)

    p, m = _score_component_reviews(analysis["review_count"])
    breakdown["review_volume"] = p
    messages.append(m)

    p, m = _score_component_screenshots(analysis["screenshot_total_count"])
    breakdown["screenshots"] = p
    messages.append(m)

    p, m = _score_component_freshness(analysis["days_since_update"])
    breakdown["update_recency"] = p
    messages.append(m)

    p, m = _score_component_extras(app, analysis)
    breakdown["listing_completeness"] = p
    messages.append(m)

    raw = sum(v for k, v in breakdown.items() if isinstance(v, int))
    total = max(0, min(100, raw))
    breakdown["raw_sum"] = raw
    breakdown["total"] = total
    return total, breakdown, messages


def _print_audit(analysis, score, breakdown):
    print("=== ASO metadata audit (iTunes Lookup) ===\n")
    print("Title:", analysis["title"])
    print(f"  Length: {analysis['title_char_len']} chars (iOS app name limit: {_IOS_TITLE_MAX})")
    print(f"  Within limit: {analysis['title_within_ios_limit']}")
    print(f"  Keyword overlap with description top terms: {analysis['title_desc_keyword_overlap_count']}")
    if analysis["title_desc_keyword_overlap_words"]:
        print("    Shared:", ", ".join(analysis["title_desc_keyword_overlap_words"]))

    print("\nSubtitle:")
    print(" ", analysis["subtitle_note"])

    da = analysis["description_analysis"]
    print("\nDescription:")
    print(f"  Length: {da['char_len']} chars, {da['line_count']} non-empty lines")
    print("  First 3 lines:")
    for i, line in enumerate(da["first_three_lines"], 1):
        preview = line[:120] + ("…" if len(line) > 120 else "")
        print(f"    {i}. {preview}")
    print(f"  CTA language detected: {da['cta_detected']}")
    print("  Top keywords (frequency):")
    for row in da["top_keywords"][:10]:
        print(f"    - {row['word']}: {row['count']}")

    print("\nOther signals:")
    print(f"  Rating: {analysis['rating']} ({analysis['review_count']} reviews)")
    print(f"  Screenshots (API): {analysis['screenshot_total_count']} total")
    print(f"  Last updated: {analysis['last_updated']}")
    if analysis["days_since_update"] is not None:
        print(f"  Days since update: {analysis['days_since_update']}")
    print(f"  File size (bytes): {analysis['file_size_bytes']}")
    print(f"  Min iOS: {analysis['minimum_os_version']}")
    print(f"  Content rating: {analysis['content_advisory_rating']}")
    print(f"  Supported devices (count): {analysis['supported_devices_count']}")

    print(f"\n--- ASO score: {score} / 100 ---")
    for k, v in breakdown.items():
        if k in ("raw_sum", "total"):
            continue
        if isinstance(v, int):
            print(f"  {k}: {v}")


def _print_compare(a1, an1, s1, a2, an2, s2):
    rows = [
        ("Metric", "App 1", "App 2"),
        ("trackId", str(an1.get("track_id")), str(an2.get("track_id"))),
        ("Title", (a1.get("trackName") or "")[:40], (a2.get("trackName") or "")[:40]),
        ("Title len", str(an1["title_char_len"]), str(an2["title_char_len"])),
        ("Desc chars", str(an1["description_analysis"]["char_len"]), str(an2["description_analysis"]["char_len"])),
        ("Rating", str(an1["rating"]), str(an2["rating"])),
        ("Reviews", str(an1["review_count"]), str(an2["review_count"])),
        ("Screenshots", str(an1["screenshot_total_count"]), str(an2["screenshot_total_count"])),
        ("Days since upd.", str(an1["days_since_update"]), str(an2["days_since_update"])),
        ("ASO score", str(s1), str(s2)),
    ]
    widths = [max(len(str(r[i])) for r in rows) for i in range(3)]
    fmt = f"{{:{widths[0]}}} | {{:{widths[1]}}} | {{:{widths[2]}}}"
    for i, row in enumerate(rows):
        print(fmt.format(row[0], row[1], row[2]))
        if i == 0:
            print(fmt.format("-" * widths[0], "-" * widths[1], "-" * widths[2]))


def _build_optimize_prompt(app, analysis, keywords):
    kws = [k.strip() for k in keywords.split(",") if k.strip()]
    da = analysis["description_analysis"]
    desc_preview = (app.get("description") or "")[:3500]
    lines = [
        "You are an App Store Optimization (ASO) expert. Propose improved metadata for this iOS app.",
        "",
        "## Constraints",
        f"- App name on the App Store: max {_IOS_TITLE_MAX} characters.",
        f"- Subtitle: max {_IOS_SUBTITLE_MAX} characters (not available via public API; still output a subtitle suggestion).",
        "- Description: compelling first lines, clear features, natural keyword use (no stuffing), include a soft CTA.",
        "",
        "## Target keywords to emphasize (use naturally)",
        ", ".join(kws) if kws else "(none provided — infer from app)",
        "",
        "## Current listing (from iTunes Lookup)",
        f"Title: {app.get('trackName', '')}",
        f"Bundle ID: {app.get('bundleId', '')}",
        f"Primary genre: {app.get('primaryGenreName', '')}",
        f"Current version: {app.get('version', '')}",
        f"Average rating / reviews: {analysis['rating']} / {analysis['review_count']}",
        "",
        "### Current description",
        desc_preview,
        "",
        "## Top terms in current description (frequency)",
        json.dumps(da["top_keywords"][:15], indent=2),
        "",
        "## Deliverables",
        "1. Optimized app name (≤30 chars).",
        "2. Optimized subtitle (≤30 chars).",
        "3. Full rewritten description (structured with short paragraphs; strong opening).",
        "4. Bullet list of changes vs current and why.",
    ]
    return "\n".join(lines)


def _write_output(payload):
    data_dir = ensure_data_dir(_CFG)
    path = data_dir / "aso-metadata-latest.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="App Store metadata audit / compare / score / optimize (iTunes Lookup).")
    parser.add_argument("--audit", metavar="APP_ID", help="Full audit for one Apple app id or bundle id")
    parser.add_argument("--compare", nargs=2, metavar=("APP_ID1", "APP_ID2"), help="Side-by-side comparison")
    parser.add_argument("--score", metavar="APP_ID", help="Print numeric ASO score with breakdown")
    parser.add_argument("--optimize", metavar="APP_ID", help="Print LLM-ready optimization prompt")
    parser.add_argument("--keywords", help='Comma-separated keywords for --optimize (e.g. "fitness,tracker,health")')
    parser.add_argument("--country", default="us", help="iTunes country code (default: us)")
    args = parser.parse_args()

    modes = [args.audit, args.compare, args.score, args.optimize]
    active = [m for m in modes if m]
    if len(active) != 1:
        parser.error("Specify exactly one of: --audit, --compare, --score, --optimize")
    if args.optimize and not args.keywords:
        parser.error("--optimize requires --keywords")

    payload = {"generated_at": _utc_now().isoformat(), "country": args.country}

    if args.audit:
        app = itunes_lookup(args.audit, country=args.country)
        if not app:
            print("Lookup failed: no results.", file=sys.stderr)
            sys.exit(1)
        analysis = analyze_app(app)
        score, breakdown, _ = compute_aso_score(app, analysis)
        payload["mode"] = "audit"
        payload["app"] = app
        payload["analysis"] = analysis
        payload["score"] = score
        payload["breakdown"] = breakdown
        _print_audit(analysis, score, breakdown)
        _write_output(payload)
        return

    if args.score:
        app = itunes_lookup(args.score, country=args.country)
        if not app:
            print("Lookup failed: no results.", file=sys.stderr)
            sys.exit(1)
        analysis = analyze_app(app)
        score, breakdown, _ = compute_aso_score(app, analysis)
        payload["mode"] = "score"
        payload["app"] = app
        payload["analysis"] = analysis
        payload["score"] = score
        payload["breakdown"] = breakdown
        print(score)
        for k, v in sorted(breakdown.items()):
            if k not in ("raw_sum", "total") and isinstance(v, int):
                print(f"  {k}: {v}")
        _write_output(payload)
        return

    if args.compare:
        id1, id2 = args.compare
        app1 = itunes_lookup(id1, country=args.country)
        app2 = itunes_lookup(id2, country=args.country)
        if not app1 or not app2:
            print("Lookup failed: one or both apps missing.", file=sys.stderr)
            sys.exit(1)
        an1, an2 = analyze_app(app1), analyze_app(app2)
        s1, b1, _ = compute_aso_score(app1, an1)
        s2, b2, _ = compute_aso_score(app2, an2)
        payload["mode"] = "compare"
        payload["apps"] = [app1, app2]
        payload["analyses"] = [an1, an2]
        payload["scores"] = [s1, s2]
        payload["breakdowns"] = [b1, b2]
        _print_compare(app1, an1, s1, app2, an2, s2)
        _write_output(payload)
        return

    if args.optimize:
        app = itunes_lookup(args.optimize, country=args.country)
        if not app:
            print("Lookup failed: no results.", file=sys.stderr)
            sys.exit(1)
        analysis = analyze_app(app)
        score, breakdown, _ = compute_aso_score(app, analysis)
        prompt = _build_optimize_prompt(app, analysis, args.keywords)
        payload["mode"] = "optimize"
        payload["app"] = app
        payload["analysis"] = analysis
        payload["score"] = score
        payload["breakdown"] = breakdown
        payload["target_keywords"] = [k.strip() for k in args.keywords.split(",") if k.strip()]
        payload["llm_prompt"] = prompt
        print(prompt)
        _write_output(payload)


if __name__ == "__main__":
    main()
