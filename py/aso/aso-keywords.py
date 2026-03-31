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


def main():
    parser = argparse.ArgumentParser(
        description="App Store keyword research (autocomplete, expand, trending, long-tail)."
    )
    mx = parser.add_mutually_exclusive_group(required=True)
    mx.add_argument("--suggest", metavar="TERM", help="Apple + Play autocomplete for TERM")
    mx.add_argument("--expand", metavar="TERM", help="Two-level autocomplete expansion")
    mx.add_argument("--trending", metavar="CATEGORY", help="Top title keywords from iTunes search")
    mx.add_argument("--long-tail", dest="long_tail", metavar="TERM", help="Apple autocomplete for TERM + a-z")
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
