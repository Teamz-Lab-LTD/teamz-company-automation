#!/usr/bin/env python3
"""
ASO competitor intelligence (iTunes Search API).

Uses only the Python standard library. Reads/writes under TEAMZ_DATA_DIR (default:
teamz-company-automation/data).

Usage:
  python3 py/aso/aso-competitors.py --find "fitness tracker"
  python3 py/aso/aso-competitors.py --analyze 123456789 987654321
  python3 py/aso/aso-competitors.py --keywords 123456789
  python3 py/aso/aso-competitors.py --gaps 111111111 222222222
  python3 py/aso/aso-competitors.py --matrix "meditation"
  python3 py/aso/aso-competitors.py --release-notes 123456789

Output is printed to stdout; latest structured run is saved to data/aso-competitors-latest.json.
"""

import argparse
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from aso._aso_common import (  # noqa: E402
    _get_json,
    ensure_data_dir,
    itunes_lookup,
    itunes_search,
    load_seo_context,
    top_keywords,
    tokenize,
    web_gaps_as_aso_opportunities,
)
from _teamz_config import load_runtime  # noqa: E402

_CFG = load_runtime(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py")
)


def _rating(rec):
    if not rec:
        return None
    v = rec.get("averageUserRatingForCurrentVersion")
    if v is None:
        v = rec.get("averageUserRating")
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _reviews(rec):
    if not rec:
        return None
    n = rec.get("userRatingCountForCurrentVersion")
    if n is None:
        n = rec.get("userRatingCount")
    try:
        return int(n)
    except (TypeError, ValueError):
        return None


def _screenshot_count(rec):
    if not rec:
        return 0
    urls = rec.get("screenshotUrls") or []
    return len(urls) if isinstance(urls, list) else 0


def _desc_word_count(rec):
    if not rec:
        return 0
    desc = (rec.get("description") or "").strip()
    return len(desc.split()) if desc else 0


def _file_size_bytes(rec):
    if not rec:
        return None
    b = rec.get("fileSizeBytes")
    try:
        return int(b)
    except (TypeError, ValueError):
        return None


def _fmt_size(b):
    if b is None:
        return "—"
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / (1024 * 1024):.1f} MB"


def _updated(rec):
    if not rec:
        return "—"
    return rec.get("currentVersionReleaseDate") or rec.get("releaseDate") or "—"


def _release_notes(rec):
    if not rec:
        return ""
    return (rec.get("releaseNotes") or rec.get("release_notes") or "").strip()


def _release_notes_preview(rec, max_len=200):
    text = _release_notes(rec)
    if not text:
        return "—"
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "…"


def _keyword_set_from_record(rec, n=200):
    """Distinct keywords from title + description (top-n by frequency)."""
    if not rec:
        return set()
    text = (rec.get("trackName") or "") + "\n" + (rec.get("description") or "")
    return {w for w, _ in top_keywords(text, n=n)}


def _write_latest(obj):
    d = ensure_data_dir(_CFG)
    path = d / "aso-competitors-latest.json"
    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **obj,
    }
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {path}", file=sys.stderr)


def _print_find_table(results):
    # rank, name, developer, rating, reviews, price
    headers = ("#", "Name", "Developer", "Rating", "Reviews", "Price")
    rows = []
    for i, r in enumerate(results, start=1):
        rating = _rating(r)
        rev = _reviews(r)
        rows.append(
            (
                str(i),
                (r.get("trackName") or "")[:40],
                (r.get("artistName") or "")[:28],
                f"{rating:.2f}" if rating is not None else "—",
                str(rev) if rev is not None else "—",
                (r.get("formattedPrice") or "—")[:12],
            )
        )
    widths = [max(len(h), max((len(row[j]) for row in rows), default=0)) for j, h in enumerate(headers)]
    line = "  ".join(h.ljust(widths[j]) for j, h in enumerate(headers))
    print(line)
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(row[j].ljust(widths[j]) for j in range(len(headers))))


def cmd_find(keyword):
    results = itunes_search(keyword, limit=10)
    if not results:
        print("No results.", file=sys.stderr)
        _write_latest({"mode": "find", "keyword": keyword, "results": []})
        return
    _print_find_table(results)
    slim = []
    for i, r in enumerate(results, start=1):
        slim.append(
            {
                "rank": i,
                "trackId": r.get("trackId"),
                "name": r.get("trackName"),
                "developer": r.get("artistName"),
                "rating": _rating(r),
                "reviews": _reviews(r),
                "price": r.get("formattedPrice"),
            }
        )
    _write_latest({"mode": "find", "keyword": keyword, "results": slim})


def cmd_analyze(app_ids):
    records = []
    for aid in app_ids:
        rec = itunes_lookup(aid)
        if not rec:
            print(f"  Lookup failed for: {aid}", file=sys.stderr)
            records.append({"app_id": str(aid), "error": "not_found"})
            continue
        b = _file_size_bytes(rec)
        rn_full = _release_notes(rec)
        records.append(
            {
                "app_id": str(aid),
                "trackId": rec.get("trackId"),
                "name": rec.get("trackName"),
                "developer": rec.get("artistName"),
                "rating": _rating(rec),
                "reviews": _reviews(rec),
                "price": rec.get("formattedPrice"),
                "updated": _updated(rec),
                "description_words": _desc_word_count(rec),
                "screenshot_count": _screenshot_count(rec),
                "file_size_bytes": b,
                "file_size_human": _fmt_size(b),
                "release_notes": rn_full,
            }
        )

    ok = [r for r in records if "error" not in r]
    if ok:
        headers = (
            "App",
            "Rating",
            "Reviews",
            "Price",
            "Updated",
            "Desc words",
            "Shots",
            "Size",
        )
        rows = []
        for r in ok:
            name = (r.get("name") or str(r.get("trackId")))[:32]
            rows.append(
                (
                    name,
                    f"{r['rating']:.2f}" if r.get("rating") is not None else "—",
                    str(r["reviews"]) if r.get("reviews") is not None else "—",
                    (r.get("price") or "—")[:10],
                    str(r.get("updated", "—"))[:10],
                    str(r.get("description_words", 0)),
                    str(r.get("screenshot_count", 0)),
                    r.get("file_size_human", "—"),
                )
            )
        widths = [max(len(h), max((len(row[j]) for row in rows), default=0)) for j, h in enumerate(headers)]
        print("  ".join(h.ljust(widths[j]) for j, h in enumerate(headers)))
        print("  ".join("-" * w for w in widths))
        for row in rows:
            print("  ".join(row[j].ljust(widths[j]) for j in range(len(headers))))

        print("\nRelease Notes (first 200 characters)")
        print("-" * 40)
        for r in ok:
            label = (r.get("name") or str(r.get("trackId")))[:48]
            prev = _release_notes_preview(r, 200)
            print(f"{label}")
            print(f"  {prev}")
            print()

    _write_latest({"mode": "analyze", "app_ids": [str(x) for x in app_ids], "apps": records})


def cmd_keywords(app_id):
    rec = itunes_lookup(app_id)
    if not rec:
        print(f"Lookup failed for: {app_id}", file=sys.stderr)
        _write_latest({"mode": "keywords", "app_id": str(app_id), "error": "not_found"})
        return
    text = (rec.get("trackName") or "") + "\n" + (rec.get("description") or "")
    pairs = top_keywords(text, n=50)
    for rank, (word, count) in enumerate(pairs, start=1):
        print(f"{rank:3}  {word:24}  {count}")
    _write_latest(
        {
            "mode": "keywords",
            "app_id": str(app_id),
            "trackId": rec.get("trackId"),
            "name": rec.get("trackName"),
            "keywords": [{"word": w, "count": c} for w, c in pairs],
        }
    )


def cmd_gaps(my_id, competitor_id):
    mine = itunes_lookup(my_id)
    other = itunes_lookup(competitor_id)
    if not mine:
        print(f"Lookup failed for your app: {my_id}", file=sys.stderr)
    if not other:
        print(f"Lookup failed for competitor: {competitor_id}", file=sys.stderr)
    if not mine or not other:
        _write_latest(
            {
                "mode": "gaps",
                "my_app_id": str(my_id),
                "competitor_id": str(competitor_id),
                "error": "lookup_failed",
            }
        )
        return

    my_kw = _keyword_set_from_record(mine)
    their_kw = _keyword_set_from_record(other)
    only_theirs = sorted(their_kw - my_kw)
    print("Keywords more present in competitor title/description (top token slice):")
    if not only_theirs:
        print("  (none in this extraction window)")
    for w in only_theirs:
        print(f"  {w}")

    seo = load_seo_context(_CFG["data_dir"])
    web_gaps = web_gaps_as_aso_opportunities(seo)
    combined_gaps = only_theirs
    if web_gaps:
        web_set = set(web_gaps) - my_kw
        new_from_web = sorted(web_set - set(only_theirs))
        if new_from_web:
            print(f"\n  + {len(new_from_web)} additional gap keywords from web SEO competitor data:")
            for w in new_from_web[:15]:
                print(f"    {w}")
            combined_gaps = only_theirs + new_from_web

    _write_latest(
        {
            "mode": "gaps",
            "my_app_id": str(my_id),
            "competitor_id": str(competitor_id),
            "my_app_name": mine.get("trackName"),
            "competitor_name": other.get("trackName"),
            "competitor_only_keywords": combined_gaps,
            "web_seo_gaps_included": len(web_gaps) if web_gaps else 0,
            "my_keyword_count": len(my_kw),
            "competitor_keyword_count": len(their_kw),
        }
    )


def cmd_matrix(keyword):
    results = itunes_search(keyword, limit=5)
    if not results:
        print("No results.", file=sys.stderr)
        _write_latest({"mode": "matrix", "keyword": keyword, "rows": []})
        return

    headers = ("Name", "Rating", "Reviews", "Price", "Size", "Updated")
    rows = []
    matrix_rows = []
    for r in results:
        b = _file_size_bytes(r)
        rating = _rating(r)
        rev = _reviews(r)
        name = (r.get("trackName") or "")[:36]
        row = (
            name,
            f"{rating:.2f}" if rating is not None else "—",
            str(rev) if rev is not None else "—",
            (r.get("formattedPrice") or "—")[:10],
            _fmt_size(b),
            str(_updated(r))[:10],
        )
        rows.append(row)
        matrix_rows.append(
            {
                "trackId": r.get("trackId"),
                "name": r.get("trackName"),
                "rating": rating,
                "reviews": rev,
                "price": r.get("formattedPrice"),
                "file_size_bytes": b,
                "file_size_human": _fmt_size(b),
                "updated": _updated(r),
            }
        )

    widths = [max(len(h), max((len(row[j]) for row in rows), default=0)) for j, h in enumerate(headers)]
    print("  ".join(h.ljust(widths[j]) for j, h in enumerate(headers)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(row[j].ljust(widths[j]) for j in range(len(headers))))

    _write_latest({"mode": "matrix", "keyword": keyword, "rows": matrix_rows})


def cmd_release_notes(app_id):
    rec = itunes_lookup(app_id)
    if not rec:
        print(f"Lookup failed for: {app_id}", file=sys.stderr)
        _write_latest({"mode": "release-notes", "app_id": str(app_id), "error": "not_found"})
        return
    ver = rec.get("version") or "—"
    rel_date = rec.get("currentVersionReleaseDate") or rec.get("releaseDate") or "—"
    notes = _release_notes(rec) or "(none)"
    print(f"version: {ver}")
    print(f"currentVersionReleaseDate: {rel_date}")
    print()
    print(notes)
    _write_latest(
        {
            "mode": "release-notes",
            "app_id": str(app_id),
            "trackId": rec.get("trackId"),
            "name": rec.get("trackName"),
            "version": rec.get("version"),
            "currentVersionReleaseDate": rec.get("currentVersionReleaseDate"),
            "releaseNotes": rec.get("releaseNotes"),
        }
    )


def cmd_developer(dev_id):
    """Show all apps by a developer (artist ID)."""
    url = f"https://itunes.apple.com/lookup?id={dev_id}&entity=software"
    data = _get_json(url)
    results = (data or {}).get("results", [])
    apps = [r for r in results if r.get("wrapperType") == "software"]
    if not apps:
        print(f"No apps found for developer ID {dev_id}.", file=sys.stderr)
        _write_latest({"mode": "developer", "developer_id": str(dev_id), "apps": []})
        return

    headers = ("Name", "Rating", "Reviews", "Price", "Genre", "Updated")
    rows = []
    for r in apps:
        rating = _rating(r)
        rev = _reviews(r)
        rows.append((
            (r.get("trackName") or "")[:40],
            f"{rating:.2f}" if rating is not None else "\u2014",
            str(rev) if rev is not None else "\u2014",
            (r.get("formattedPrice") or "\u2014")[:10],
            (r.get("primaryGenreName") or "\u2014")[:20],
            str(_updated(r))[:10],
        ))

    widths = [max(len(h), max((len(row[j]) for row in rows), default=0)) for j, h in enumerate(headers)]
    print("  ".join(h.ljust(widths[j]) for j, h in enumerate(headers)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(row[j].ljust(widths[j]) for j in range(len(headers))))

    _write_latest({
        "mode": "developer",
        "developer_id": str(dev_id),
        "app_count": len(apps),
        "apps": [{
            "trackId": r.get("trackId"),
            "name": r.get("trackName"),
            "rating": _rating(r),
            "reviews": _reviews(r),
            "price": r.get("formattedPrice"),
            "genre": r.get("primaryGenreName"),
            "updated": _updated(r),
        } for r in apps],
    })


def cmd_release_history(app_id):
    """Track release history -- appends version info to aso-release-history.json."""
    rec = itunes_lookup(app_id)
    if not rec:
        print(f"Lookup failed for: {app_id}", file=sys.stderr)
        _write_latest({"mode": "release-history", "app_id": str(app_id), "error": "not_found"})
        return

    version = rec.get("version") or "unknown"
    release_date = rec.get("currentVersionReleaseDate") or rec.get("releaseDate") or ""
    notes = (rec.get("releaseNotes") or "").strip()
    app_name = rec.get("trackName", str(app_id))

    d = ensure_data_dir(_CFG)
    path = d / "aso-release-history.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (json.JSONDecodeError, OSError):
        data = {}

    aid = str(app_id)
    if aid not in data:
        data[aid] = {"name": app_name, "versions": []}

    existing = {v.get("version") for v in data[aid].get("versions", [])}
    if version not in existing:
        data[aid]["versions"].append({
            "version": version,
            "date": release_date,
            "notes": notes,
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        data[aid]["name"] = app_name
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Recorded version {version} for {app_name}.", file=sys.stderr)
    else:
        print(f"Version {version} already recorded for {app_name}.", file=sys.stderr)

    print(f"\nRelease history for {app_name} ({aid}):")
    print(f"{'Version':<12} {'Date':<24} Notes")
    print(f"{'-' * 12} {'-' * 24} {'-' * 40}")
    for v in data[aid].get("versions", []):
        ver = v.get("version", "\u2014")
        dt = v.get("date", "\u2014")[:24]
        n = v.get("notes") or "\u2014"
        preview = n[:60] + "\u2026" if len(n) > 60 else n
        print(f"{ver:<12} {dt:<24} {preview}")


def cmd_play_reviews(packages, count_per_app, score_max, lang, country, out_path):
    """Scrape Play Store reviews for a list of competitor packages.

    Pulls negative reviews (default score <= 3) so the output is a
    pain-points feed an ASO/content writer can mine for missing-feature,
    bug, or pricing complaints. Requires ``pip install google-play-scraper``.
    """
    try:
        from google_play_scraper import reviews as gp_reviews, Sort
    except ImportError:
        print(
            "ERROR: google-play-scraper not installed. Run:\n"
            "  pip3 install google-play-scraper",
            file=sys.stderr,
        )
        return 1

    aggregate = {"generated_at": _now_iso(), "competitors": {}, "themes": {}}
    keyword_buckets = {
        "missing_feature": ["missing", "lacks", "needs", "wish", "should have", "doesn't have", "no feature"],
        "slow_performance": ["slow", "lag", "freeze", "crash", "hang", "stuck", "loading"],
        "broken_bug": ["bug", "broken", "doesn't work", "not working", "error", "fail"],
        "privacy_concern": ["privacy", "data", "tracking", "leak", "spy"],
        "price_complaint": ["expensive", "subscription", "price", "paywall", "free trial", "scam"],
        "ui_complaint": ["confusing", "ugly", "outdated", "hard to use", "complicated"],
    }
    aggregate["themes"] = {k: [] for k in keyword_buckets}

    for pkg in packages:
        try:
            rows, _ = gp_reviews(
                pkg,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=count_per_app,
            )
        except Exception as e:
            aggregate["competitors"][pkg] = {"error": str(e)}
            continue

        negatives = [r for r in rows if int(r.get("score") or 5) <= score_max]
        aggregate["competitors"][pkg] = {
            "total_pulled": len(rows),
            "negative_count": len(negatives),
            "sample_negative": [
                {
                    "score": r.get("score"),
                    "at": r.get("at").isoformat() if r.get("at") else None,
                    "content": (r.get("content") or "")[:300],
                }
                for r in negatives[:25]
            ],
        }

        for r in negatives:
            text = (r.get("content") or "").lower()
            for theme, terms in keyword_buckets.items():
                if any(t in text for t in terms):
                    aggregate["themes"][theme].append({
                        "app": pkg,
                        "score": r.get("score"),
                        "content": (r.get("content") or "")[:300],
                    })

    # Rank themes by frequency for quick read.
    aggregate["theme_counts"] = {k: len(v) for k, v in aggregate["themes"].items()}

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
        print(f"wrote {out_path}")
    else:
        print(json.dumps(aggregate, indent=2))
    print("\ntheme counts:")
    for k, v in sorted(aggregate["theme_counts"].items(), key=lambda x: -x[1]):
        print(f"  {k:18s}  {v}")
    return 0


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(
        description="ASO competitor intelligence (iTunes Search / Lookup + Play reviews)."
    )
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--find", metavar="KEYWORD", help="Search App Store; show top 10")
    g.add_argument(
        "--analyze",
        nargs="+",
        metavar="APP_ID",
        help="Lookup one or more apps and compare metadata",
    )
    g.add_argument("--keywords", metavar="APP_ID", help="Top keywords from title + description")
    g.add_argument(
        "--gaps",
        nargs=2,
        metavar=("MY_APP_ID", "COMPETITOR_ID"),
        help="Keywords in competitor listing text not in yours (token overlap)",
    )
    g.add_argument(
        "--matrix",
        metavar="KEYWORD",
        help="Top 5 search results comparison matrix",
    )
    g.add_argument(
        "--release-notes",
        metavar="APP_ID",
        help="Print full release notes, version, and currentVersionReleaseDate for an app",
    )
    g.add_argument(
        "--developer",
        metavar="DEV_ID",
        help="List all apps by a developer (artist ID from iTunes Lookup)",
    )
    g.add_argument(
        "--release-history",
        metavar="APP_ID",
        help="Track release versions over time (appends to aso-release-history.json)",
    )
    g.add_argument(
        "--play-reviews",
        nargs="+",
        metavar="PACKAGE",
        help="Scrape Play Store negative reviews for one or more competitor packages "
             "(e.g. org.thoughtcrime.securesms ch.threema.app network.loki.messenger)",
    )
    parser.add_argument("--count", type=int, default=500, help="Reviews per app (default 500, --play-reviews only)")
    parser.add_argument("--score-max", type=int, default=3, help="Max star rating to keep (default 3 = complaints)")
    parser.add_argument("--lang", default="en", help="Reviews language code (default en, --play-reviews only)")
    parser.add_argument("--country", default="us", help="Reviews country code (default us, --play-reviews only)")
    parser.add_argument("--out", type=Path, help="Output JSON path (--play-reviews only)")
    args = parser.parse_args()

    if args.find is not None:
        cmd_find(args.find)
    elif args.analyze is not None:
        cmd_analyze(args.analyze)
    elif args.keywords is not None:
        cmd_keywords(args.keywords)
    elif args.gaps is not None:
        cmd_gaps(args.gaps[0], args.gaps[1])
    elif args.matrix is not None:
        cmd_matrix(args.matrix)
    elif args.release_notes is not None:
        cmd_release_notes(args.release_notes)
    elif args.developer is not None:
        cmd_developer(args.developer)
    elif args.release_history is not None:
        cmd_release_history(args.release_history)
    elif args.play_reviews is not None:
        cmd_play_reviews(
            args.play_reviews,
            args.count,
            args.score_max,
            args.lang,
            args.country,
            args.out,
        )


if __name__ == "__main__":
    main()
