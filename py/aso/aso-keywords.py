#!/usr/bin/env python3
"""
ASO keyword research CLI — App Store / Play autocomplete, expansion, and iTunes signals.

Uses only the Python standard library. Writes the latest run to
``<data_dir>/aso-keywords-latest.json`` (see ``TEAMZ_DATA_DIR`` / config).

Examples::

    python3 py/aso/aso-keywords.py --suggest "photo editor"
    python3 py/aso/aso-keywords.py --expand "meditation"
    python3 py/aso/aso-keywords.py --trending fitness
    python3 py/aso/aso-keywords.py --long-tail "budget"
    python3 py/aso/aso-keywords.py --suggest "game" --export csv
"""

import argparse
import calendar
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _teamz_config import load_runtime  # noqa: E402

from aso._aso_common import (  # noqa: E402
    apple_autocomplete,
    ensure_data_dir,
    itunes_lookup,
    itunes_search,
    load_seo_context,
    play_autocomplete,
    top_keywords,
    web_keywords_for_seed,
)

_CFG = load_runtime(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py")
)
_DATA_DIR = _CFG["data_dir"]
_JSON_NAME = "aso-keywords-latest.json"


def _row(keyword, source, chars=None, words=None, count=None):
    if chars is None:
        chars = len(keyword)
    if words is None:
        words = len(keyword.split())
    r = {"keyword": keyword, "source": source, "chars": chars, "words": words}
    if count is not None:
        r["count"] = count
    return r


def _merge_suggest(term):
    apple = apple_autocomplete(term)
    play = play_autocomplete(term)
    a_set = {x.strip() for x in apple if x and x.strip()}
    p_set = {x.strip() for x in play if x and x.strip()}
    rows = []
    for kw in sorted(a_set | p_set):
        if kw in a_set and kw in p_set:
            src = "both"
        elif kw in a_set:
            src = "apple"
        else:
            src = "play"
        rows.append(_row(kw, src))
    return rows


def _expand(term):
    sources = {}
    counts = Counter()

    def ingest(items, src):
        for raw in items:
            kw = (raw or "").strip()
            if not kw:
                continue
            counts[kw] += 1
            sources.setdefault(kw, set()).add(src)

    l1_a = apple_autocomplete(term)
    l1_p = play_autocomplete(term)
    ingest(l1_a, "apple")
    ingest(l1_p, "play")

    seeds = []
    seen = set()
    for raw in l1_a + l1_p:
        kw = (raw or "").strip()
        if kw and kw not in seen:
            seen.add(kw)
            seeds.append(kw)

    for s in seeds:
        ingest(apple_autocomplete(s), "apple")
        ingest(play_autocomplete(s), "play")

    rows = []
    for kw in sorted(counts.keys()):
        srcs = sources.get(kw, set())
        if srcs == {"apple"}:
            src = "apple"
        elif srcs == {"play"}:
            src = "play"
        else:
            src = "both"
        rows.append(_row(kw, src, count=counts[kw]))
    return rows


def _trending(category):
    results = itunes_search(category, limit=25)
    titles = []
    for r in results:
        t = (r.get("trackName") or "").strip()
        if t:
            titles.append(t)
    blob = " ".join(titles)
    ranked = top_keywords(blob, n=40)
    rows = []
    for word, freq in ranked:
        rows.append(_row(word, f"itunes:{category}", count=freq))
    return rows


def _localize(term, countries):
    rows = []
    for country in countries:
        cc = (country or "").strip().lower()
        if not cc:
            continue
        results = itunes_search(term, country=cc, limit=10)
        titles = []
        for r in results:
            t = (r.get("trackName") or "").strip()
            if t:
                titles.append(t)
        if not titles:
            continue
        blob = " ".join(titles)
        ranked = top_keywords(blob, n=40)
        for word, freq in ranked:
            rows.append(_row(word, cc, count=freq))
    rows.sort(key=lambda r: (r["source"], r["keyword"].lower()))
    return rows


def _long_tail(term):
    base = term.strip()
    seen = set()
    rows = []
    for letter in "abcdefghijklmnopqrstuvwxyz":
        q = f"{base} {letter}"
        for raw in apple_autocomplete(q):
            kw = (raw or "").strip()
            if not kw or kw in seen:
                continue
            seen.add(kw)
            rows.append(_row(kw, "apple"))
    rows.sort(key=lambda r: r["keyword"].lower())
    return rows


def _write_json(mode, query, rows):
    ensure_data_dir(_CFG)
    out = {
        "mode": mode,
        "query": query,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
    }
    path = _DATA_DIR / _JSON_NAME
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _table_headers(rows):
    base = ["keyword", "source", "chars", "words"]
    if not rows:
        return base
    if any("count" in r for r in rows):
        return base + ["count"]
    return base


def _print_table(rows):
    headers = _table_headers(rows)
    if not rows:
        print("(no rows)")
        return
    str_rows = []
    for r in rows:
        line = [str(r.get(h, "")) for h in headers]
        str_rows.append(line)
    widths = [len(h) for h in headers]
    for line in str_rows:
        for i, cell in enumerate(line):
            widths[i] = max(widths[i], len(cell))
    fmt = "  ".join("{:%ds}" % w for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in widths]))
    for line in str_rows:
        print(fmt.format(*line))


def _print_csv(rows):
    headers = _table_headers(rows)
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(headers)
    for r in rows:
        w.writerow([r.get(h, "") for h in headers])


_SEASONAL_CALENDAR = {
    1: ["budget", "resolution", "new year", "goal", "planning"],
    2: ["valentine", "love", "dating", "couple", "gift"],
    3: ["tax", "ramadan", "spring", "march madness", "declutter"],
    4: ["tax deadline", "easter", "spring cleaning", "garden", "allergy"],
    5: ["mothers day", "graduation", "wedding", "memorial day", "outdoor"],
    6: ["fathers day", "summer", "travel", "vacation", "pride"],
    7: ["fitness", "vacation", "summer", "fourth of july", "beach"],
    8: ["back to school", "college", "dorm", "school supplies", "fall prep"],
    9: ["apple event", "fall", "football", "labor day", "autumn"],
    10: ["halloween", "costume", "horror", "fall", "pumpkin"],
    11: ["black friday", "thanksgiving", "holiday shopping", "cyber monday", "deals"],
    12: ["christmas", "gift", "holiday", "new year", "winter"],
}


def _seasonal_months_for(term):
    """Find which months a term is likely to peak."""
    t = term.lower().strip()
    matches = []
    for month, keywords in _SEASONAL_CALENDAR.items():
        for kw in keywords:
            if t in kw or kw in t:
                matches.append(month)
                break
    return sorted(set(matches))


def cmd_seasonal(term, export_fmt):
    """Seasonal keyword analysis: peak months and current-month autocomplete."""
    now = datetime.now(timezone.utc)
    current_month = now.month

    peak_months = _seasonal_months_for(term)
    if peak_months:
        month_names = [calendar.month_name[m] for m in peak_months]
        print(f"Peak months for '{term}': {', '.join(month_names)}")
    else:
        print(f"Peak months for '{term}': No strong seasonal signal detected")

    current_modifiers = _SEASONAL_CALENDAR.get(current_month, [])
    print(f"\nCurrent month ({calendar.month_name[current_month]}) modifiers: {', '.join(current_modifiers)}")

    all_suggestions = []
    if current_modifiers:
        print(f"\nAutocomplete for '{term}' + current-month modifiers:")
        for mod in current_modifiers:
            query = f"{term} {mod}"
            results = apple_autocomplete(query)
            for r in results[:3]:
                if r not in all_suggestions:
                    all_suggestions.append(r)
                    print(f"  {r}  (from: '{query}')")
        if not all_suggestions:
            print("  (no suggestions found)")

    rows = []
    if peak_months:
        for m in peak_months:
            rows.append(_row(f"{term} ({calendar.month_name[m]})", "seasonal-peak"))
    for s in all_suggestions:
        rows.append(_row(s, "seasonal-autocomplete"))

    _write_json("seasonal", term, rows)
    if export_fmt == "csv":
        _print_csv(rows)


def cmd_cannibalize(export_fmt):
    """Find keywords appearing in 2+ of your own apps (TEAMZ_APP_IDS)."""
    app_ids_str = os.environ.get("TEAMZ_APP_IDS", "")
    if not app_ids_str.strip():
        print("Set TEAMZ_APP_IDS env var (comma-separated app IDs).", file=sys.stderr)
        return

    app_ids = [a.strip() for a in app_ids_str.split(",") if a.strip()]
    if len(app_ids) < 2:
        print("Need at least 2 app IDs in TEAMZ_APP_IDS.", file=sys.stderr)
        return

    app_keywords = {}
    for aid in app_ids:
        rec = itunes_lookup(aid)
        if not rec:
            print(f"  Lookup failed for {aid}", file=sys.stderr)
            continue
        name = rec.get("trackName", aid)
        text = (rec.get("trackName") or "") + " " + (rec.get("description") or "")
        kws = {w for w, _ in top_keywords(text, n=100)}
        app_keywords[name] = kws

    if len(app_keywords) < 2:
        print("Need successful lookups for at least 2 apps.", file=sys.stderr)
        return

    kw_to_apps = {}
    for name, kws in app_keywords.items():
        for kw in kws:
            kw_to_apps.setdefault(kw, []).append(name)

    cannibalized = [(kw, apps) for kw, apps in kw_to_apps.items() if len(apps) >= 2]
    cannibalized.sort(key=lambda x: (-len(x[1]), x[0]))

    if not cannibalized:
        print("No keyword cannibalization detected between your apps.")
        _write_json("cannibalize", "TEAMZ_APP_IDS", [])
        return

    print(f"Found {len(cannibalized)} cannibalized keywords:\n")
    for kw, apps in cannibalized:
        app_list = ", ".join(apps)
        print(f"  Keyword '{kw}' appears in: {app_list} \u2014 consider differentiating")

    rows = [_row(kw, "cannibalize", count=len(apps)) for kw, apps in cannibalized]
    _write_json("cannibalize", "TEAMZ_APP_IDS", rows)
    if export_fmt == "csv":
        _print_csv(rows)


def main():
    parser = argparse.ArgumentParser(
        description="App Store keyword research (autocomplete, expand, trending, long-tail)."
    )
    mx = parser.add_mutually_exclusive_group(required=True)
    mx.add_argument("--suggest", metavar="TERM", help="Apple + Play autocomplete for TERM")
    mx.add_argument("--expand", metavar="TERM", help="Two-level autocomplete expansion")
    mx.add_argument("--trending", metavar="CATEGORY", help="Top title keywords from iTunes search")
    mx.add_argument("--long-tail", dest="long_tail", metavar="TERM", help="Apple autocomplete for TERM + a-z")
    mx.add_argument("--seasonal", metavar="TERM", help="Seasonal keyword analysis: peak months + current-month autocomplete")
    mx.add_argument("--cannibalize", action="store_true", help="Find keywords cannibalizing across your apps (reads TEAMZ_APP_IDS)")
    mx.add_argument(
        "--localize",
        metavar="TERM",
        help="Autocomplete across multiple countries/languages for localization",
    )
    parser.add_argument(
        "--countries",
        default="",
        help="Comma-separated country codes (default: from TEAMZ_ASO_COUNTRIES or us,gb,de,fr,es,pt,ja,ko,zh)",
    )
    parser.add_argument(
        "--export",
        choices=["csv"],
        nargs="?",
        const="csv",
        help="Write CSV to stdout instead of a text table",
    )
    args = parser.parse_args()

    if args.suggest is not None:
        mode, query = "suggest", args.suggest
        rows = _merge_suggest(args.suggest)
    elif args.expand is not None:
        mode, query = "expand", args.expand
        rows = _expand(args.expand)
    elif args.trending is not None:
        mode, query = "trending", args.trending
        rows = _trending(args.trending)
    elif args.seasonal is not None:
        cmd_seasonal(args.seasonal, args.export)
        return
    elif args.cannibalize:
        cmd_cannibalize(args.export)
        return
    elif args.localize is not None:
        mode, query = "localize", args.localize
        countries_str = (args.countries or "").strip()
        if not countries_str:
            countries_str = os.getenv("TEAMZ_ASO_COUNTRIES", "us,gb,de,fr,es,pt,ja,ko")
        countries = [c.strip().lower() for c in countries_str.split(",") if c.strip()]
        rows = _localize(args.localize, countries)
    else:
        mode, query = "long-tail", args.long_tail
        rows = _long_tail(args.long_tail)

    seo = load_seo_context(_DATA_DIR)
    web_seeds = web_keywords_for_seed(seo)
    if web_seeds:
        existing = {r["keyword"] for r in rows}
        seo_rows = [_row(kw, "seo-web") for kw in web_seeds if kw not in existing]
        if seo_rows:
            rows.extend(seo_rows)

    _write_json(mode, query, rows)

    if args.export == "csv":
        _print_csv(rows)
    else:
        _print_table(rows)
        if web_seeds:
            print(f"\n  + {len(web_seeds)} web keyword seeds from SEO rank history (source=seo-web)")


if __name__ == "__main__":
    main()
