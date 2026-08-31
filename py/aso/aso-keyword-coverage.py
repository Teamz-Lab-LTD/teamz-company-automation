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


def load_keywords(data):
    """Return [(keyword, volume)] from either producer shape.

    Two shapes exist on disk and the gate used to understand only the first:
      list: [{"keyword": "camera test", "exact_vol": 27100}, ...]
            (ai_resume_checker, chopstick_landing_games)
      dict: {"camera test": {"avg_monthly_searches": 27100, ...}, ...}
            (debugger — the newer keyword_volume_manual fold)
    Reading the dict shape as a list yields bare strings, so `k["keyword"]` raised
    `TypeError: string indices must be integers` and the gate died before it could
    check anything. A gate that crashes is not a gate that passes.
    """
    kw = data.get("keywords", [])
    if isinstance(kw, dict):
        out = []
        for k, v in kw.items():
            if isinstance(v, dict):
                vol = v.get("avg_monthly_searches") or v.get("exact_vol") or 0
            else:
                vol = v or 0
            out.append((k, vol))
        return out
    return [(k["keyword"], k.get("exact_vol") or k.get("avg_monthly_searches") or 0)
            for k in kw if isinstance(k, dict)]


def app_package(app):
    """This app's Play package, from its .teamz-automation.env."""
    env = os.path.join(app, ".teamz-automation.env")
    if not os.path.exists(env):
        return ""
    for line in open(env):
        if line.startswith("TEAMZ_PLAY_PACKAGE_NAME="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _pick_listing(app, pattern, label):
    """Choose ONE listing file, and never guess between apps.

    debugger/automation_data/ holds a Top3Picks listing alongside its own, plus a
    generic play-listing-new-en-US.json. Globbing and taking the alphabetically-last
    match graded DeviceGPT's keywords against whichever file happened to sort last —
    a confident answer about the wrong app. Match the package name; if that is not
    possible, fall back to newest-by-mtime and SAY so rather than pretend certainty.
    """
    hits = glob.glob(os.path.join(app, "automation_data", pattern))
    if not hits:
        return None, ""
    # A draft is what we might publish; the live pull is what IS published. Coverage is a
    # statement about the live listing, so never let a draft outrank it.
    live = [h for h in hits if "draft" not in os.path.basename(h).lower()]
    pool = live or hits
    pkg = app_package(app)
    if pkg:
        dashed = pkg.replace(".", "-")
        owned = [h for h in pool if pkg in os.path.basename(h)
                 or dashed in os.path.basename(h)]
        if owned:
            p = max(owned, key=os.path.getmtime)
            return p, f"{label}: {os.path.basename(p)} (matched package {pkg})"
    p = max(pool, key=os.path.getmtime)
    note = f"{label}: {os.path.basename(p)} (newest by mtime"
    note += f"; NO file matched package {pkg!r} — verify this is the right app)" if pkg \
        else "; no TEAMZ_PLAY_PACKAGE_NAME to match against)"
    return p, note


def read_play_json(app):
    """Live Play listing as pulled by build-play-console.py listing-pull."""
    p, note = _pick_listing(app, "play-listing-*.json", "Play listing")
    if not p:
        return {}
    print(note)
    d = json.load(open(p))
    return {"title": d.get("title", ""), "short": d.get("shortDescription", ""),
            "full": d.get("fullDescription", "")}


def read_apple_json(app):
    """Apple listing draft as written by aso-metadata.py."""
    p, note = _pick_listing(app, "apple-listing-*.json", "Apple listing")
    if not p:
        return {}
    print(note)
    d = json.load(open(p))
    return {"name": d.get("name", ""), "subtitle": d.get("subtitle", ""),
            "keywords": d.get("keywords", "")}


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
    kws = load_keywords(data)
    kws = [(k, v) for k, v in kws if v and v >= args.min_vol]

    # The Planner pull is an EXPANSION, not a target list: debugger's 15,303-row file
    # carries "xfinity internet speed check" (90,500/mo) and chopstick's carries "roblox"
    # (5,000,000/mo). Enforcing placement of those is not coverage, it is keyword stuffing
    # with terms the app has nothing to do with — and the gate used to print exactly that
    # as required work. When the app declares its own targets, enforce THOSE.
    seed_path = os.path.join(app, "automation_data", "seed_keywords.txt")
    targeted = os.path.exists(seed_path)
    if targeted:
        seeds = {norm(l).strip() for l in open(seed_path) if l.strip()
                 and not l.lstrip().startswith("#")}
        before = len(kws)
        kws = [(k, v) for k, v in kws if norm(k).strip() in seeds]
        print(f"Scope: {len(kws)} of {before} keyword(s) >= {args.min_vol}/mo are in this "
              f"app's seed_keywords.txt; the rest are Planner expansion and are NOT enforced.")
    else:
        # Without a declared target set the gate cannot know what the app is FOR, so it
        # must not hard-fail. On chopstick it demanded "roblox", "starlink" and "subway"
        # (5,000,000/mo each) be woven into a chopstick-landing game's listing. A gate
        # that orders keyword stuffing gets ignored, and an ignored gate protects nothing.
        print(f"Scope: no automation_data/seed_keywords.txt for this app, so there is no "
              f"target list to enforce. Reporting all {len(kws)} Planner-expansion "
              f"keyword(s) >= {args.min_vol}/mo as ADVISORY ONLY (exit 0). Add "
              f"seed_keywords.txt to make this a real gate.")

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

    # Those store/*.txt paths exist in NO project on disk. read() swallowed the OSError
    # and handed back "", so the gate compared every keyword against an empty listing and
    # reported all of them "placed NOWHERE" — on chopstick that was 104 false gaps
    # instructing the owner to weave "roblox" and "starlink" into the listing. The real
    # listings live in automation_data/*-listing-*.json. Fall back to them.
    if not any(v.strip() for v in play.values()):
        play.update(read_play_json(app))
    if not any(v.strip() for v in apple.values()):
        apple.update(read_apple_json(app))

    # A gate must never grade against a listing it could not read. Silence here is what
    # turned "I found no listing" into "your listing covers nothing".
    if not any(v.strip() for v in list(play.values()) + list(apple.values())):
        print("COVERAGE ERROR: found no listing text for this app — looked in "
              "store/play/listings/en-US/, store/apple/en-US/ and "
              "automation_data/{play,apple}-listing-*.json. Refusing to report coverage "
              "against an empty listing.", file=sys.stderr)
        return 2
    for label, surf in (("Play", play), ("Apple", apple)):
        got = [n for n, t in surf.items() if t.strip()]
        print(f"{label} surfaces read: {', '.join(got) if got else 'NONE (not graded)'}")
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
        verdict = "COVERAGE FAIL" if targeted else "COVERAGE ADVISORY (not enforced)"
        print(f"\n{verdict}: {len(gaps)} keyword(s) with real volume placed NOWHERE:",
              file=sys.stderr)
        for k, v in gaps:
            print(f"  - {k} ({v:,}/mo) → weave into Play full-description or iOS keywords", file=sys.stderr)
        if not targeted:
            print("  (advisory only — no seed_keywords.txt, so these are unvetted "
                  "Planner-expansion terms, not chosen targets. Do NOT place one without "
                  "checking the app actually has the feature.)", file=sys.stderr)
        return 1 if targeted else 0
    print("\nCOVERAGE PASS: every enforced keyword is placed on at least one store.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
