#!/usr/bin/env python3
"""
ASO Keyword Coverage Gate — every exact-volume keyword must be PLACED.
======================================================================
Companion to aso-keyword-data-gate.py (which forces the Keyword Planner pull).
This gate forces the USE of that data: it cross-checks every keyword with real
Planner volume against every listing surface and FAILs if a nonzero-volume
keyword is placed nowhere.

Why it exists: on voltline (2026-06-13) the Planner data was folded but two
5,000/mo keywords ("skill", "patience") were never placed in any surface —
the LLM verified placement by eye instead of by code. This script is the
mechanical check that should have run at lock time.

Apple indexing note: Apple concatenates name + subtitle + keywords, so a
multi-word phrase counts as covered if ALL its words appear across those
three fields. Play indexes title + short + full description verbatim.

USAGE:
  python3 aso-keyword-coverage.py --app-dir apps/<slug> [--min-vol 50]

Reads:
  <app>/automation_data/keyword_exact_volume_*.json   (from keyword_volume_manual fold)
  <app>/store/apple/en-US/{name,subtitle,keywords}.txt
  <app>/store/play/listings/en-US/{title,short-description,full-description}.txt

EXIT: 0 = every keyword >= --min-vol covered on at least one store. 1 = gaps.
"""
import argparse
import glob
import json
import os
import re
import sys


def norm(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).replace("dont", "don't")


def words(s):
    return set(norm(s).replace("'", "").split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-dir", required=True)
    ap.add_argument("--min-vol", type=int, default=500,
                    help="enforce keywords with at least this monthly volume (default 500 — "
                         "the 50/mo long-tail expansion seeds are advisory, not mandatory)")
    args = ap.parse_args()
    app = os.path.abspath(args.app_dir)

    vol_files = sorted(glob.glob(os.path.join(app, "automation_data", "keyword_exact_volume_*.json")))
    if not vol_files:
        print("COVERAGE ERROR: no keyword_exact_volume_*.json — run the Planner fold first "
              "(keyword_volume_manual.py).", file=sys.stderr)
        return 2
    data = json.load(open(vol_files[-1]))
    kws = [(k["keyword"], k.get("exact_vol") or 0) for k in data.get("keywords", [])]
    kws = [(k, v) for k, v in kws if v and v >= args.min_vol]

    # deliberate skips: <app>/automation_data/keyword-coverage-skip.txt
    # one keyword per line, "# reason" after — a skip MUST carry a reason.
    skip_path = os.path.join(app, "automation_data", "keyword-coverage-skip.txt")
    skips = {}
    if os.path.exists(skip_path):
        for line in open(skip_path):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            kw, _, reason = line.partition("#")
            skips[norm(kw).strip()] = reason.strip() or "(no reason given)"
    skipped = [(k, v) for k, v in kws if norm(k).strip() in skips]
    kws = [(k, v) for k, v in kws if norm(k).strip() not in skips]
    for k, v in skipped:
        print(f"SKIP {k} ({v:,.0f}/mo) — {skips[norm(k).strip()]}")
    if not kws:
        print("COVERAGE: no keywords at/above --min-vol; nothing to enforce.")
        return 0

    def read(*p):
        try:
            return open(os.path.join(app, *p)).read()
        except OSError:
            return ""

    apple = {
        "name": read("store", "apple", "en-US", "name.txt"),
        "subtitle": read("store", "apple", "en-US", "subtitle.txt"),
        "keywords": read("store", "apple", "en-US", "keywords.txt"),
    }
    play = {
        "title": read("store", "play", "listings", "en-US", "title.txt"),
        "short": read("store", "play", "listings", "en-US", "short-description.txt"),
        "full": read("store", "play", "listings", "en-US", "full-description.txt"),
    }
    apple_words = words(" ".join(apple.values()).replace(",", " "))
    play_text = norm(" ".join(play.values()))

    print(f"{'keyword':<26}{'vol/mo':>9}  {'Apple':<7}{'Play':<6} placed in")
    print("-" * 70)
    gaps = []
    for k, v in sorted(kws, key=lambda x: -x[1]):
        kn = norm(k)
        a = words(k) <= apple_words                      # Apple combines fields
        p = kn in play_text
        locs = [f"apple:{n}" for n, t in apple.items() if kn in norm(t)] + \
               [f"play:{n}" for n, t in play.items() if kn in norm(t)]
        if a and not locs:
            locs = ["apple:combined"]
        if not a and not p:
            gaps.append((k, v))
        print(f"{k:<26}{v:>9}  {'YES' if a else 'no':<7}{'YES' if p else 'no':<6} {', '.join(locs) or '-'}")

    if gaps:
        print(f"\nCOVERAGE FAIL: {len(gaps)} keyword(s) with real volume placed NOWHERE:", file=sys.stderr)
        for k, v in gaps:
            print(f"  - {k} ({v:,}/mo) → weave into Play full-description or iOS keywords", file=sys.stderr)
        return 1
    print("\nCOVERAGE PASS: every enforced keyword is placed on at least one store.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
