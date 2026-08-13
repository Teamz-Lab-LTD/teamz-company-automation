#!/usr/bin/env python3
"""
Keyword TARGET audit — is each page aimed at a keyword anyone actually searches?

THE BLIND SPOT THIS CLOSES.
build-content-queue.py decides which page to improve, and it is good at that. But it takes
each page's declared target as a given: it ranks candidates by GSC impressions and rank
proximity, so a page aimed at a keyword with 10 searches a month looks "fine, just small"
forever. Nothing in the engine has ever asked whether the target itself is worth owning.

Measured on apps.teamzlab.com, 2026-08-13, Google Keyword Planner (US), against each page's
own declared primaryKeyword:

    notetube-ai    'youtube to flashcards'       10 /mo   <- 'youtube video summarizer' 8,100/mo Low
    devicegpt      'phone health check app'      20 /mo   <- 'battery health android'   1,000/mo Low
    arrow-jam-3d   '3d arrow puzzle'             10 /mo   <- 'arrow puzzles'            1,600/mo Low
    brimful        'color sort puzzle'          140 /mo   <- 'water sort puzzle'        2,900/mo Med
    top3picks      'AI gift finder app'           0 /mo   <- its own <title> already said
                                                              'price comparison app' 2,400/mo Low
    chopstick      'rocket landing simulator'    50 /mo   <- nothing better exists, correctly small

Five of seven pages were built around terms almost nobody types. That is not a writing
problem and no amount of nightly enhancement fixes it — the engine was faithfully polishing
pages aimed at nothing. This is the check that would have caught it on day one.

WHAT IT DOES NOT DO.
It never edits a page. Retargeting rewrites a title, a tagline and body copy, and picking the
replacement needs judgement this script does not have: 'unblock puzzle game' outranks 'arrow
puzzles' on volume but means a different genre, and 'hourly rate calculator' beats every Toss
term while belonging to tool.teamzlab.com, which already owns three pages for it. So this
reports, ranks by opportunity, and stops.

QUOTA.
Keyword Planner is rate-limited and this repo has already been bitten by re-pulling the world
nightly. Results cache for TEAMZ_KWAUDIT_TTL_DAYS (default 14) and a cached run costs zero
API calls, so wiring it into a nightly is safe.

Usage:
  python3 build-keyword-target-audit.py                 # cached if fresh
  python3 build-keyword-target-audit.py --force         # ignore cache
  python3 build-keyword-target-audit.py --geo 2840      # US (default)
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TTL_DAYS = int(os.getenv("TEAMZ_KWAUDIT_TTL_DAYS", "14"))
# A target under this is treated as "aimed at nothing worth owning".
DEAD_TARGET_VOL = int(os.getenv("TEAMZ_KWAUDIT_DEAD_VOL", "150"))
# A replacement must clear this to be worth the disruption of a retarget.
MIN_ALT_VOL = int(os.getenv("TEAMZ_KWAUDIT_MIN_ALT", "500"))
# Above this, a term is a vanity head term: real volume, no realistic chance for this site.
# Same doctrine build-content-queue already applies to NEW posts.
VANITY_VOL = int(os.getenv("TEAMZ_KWAUDIT_VANITY", "10000"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    return mod


def page_targets(host):
    """[(slug, primaryKeyword, source_path)] from this property's content frontmatter.

    Reads the markdown directly rather than the built HTML: the declared target is the thing
    being audited, and a page can rank for something its author never intended.
    """
    out = []
    for d in ("src/content/apps", "src/content/blog"):
        root = host / d
        if not root.exists():
            continue
        for f in sorted(root.glob("*.md")):
            if f.stem.lower() == "readme":
                continue
            head = f.read_text(errors="ignore")[:4000]
            mk = re.search(r"^primaryKeyword:\s*['\"]?(.+?)['\"]?\s*$", head, re.M)
            if mk:
                out.append((f.stem, mk.group(1).strip(), str(f.relative_to(host))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", default=os.getenv("TEAMZ_KWAUDIT_GEO", "2840"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    host = Path(os.getenv("TEAMZ_HOST_SITE_ROOT", "")).resolve()
    if not host.exists():
        print("ERROR: TEAMZ_HOST_SITE_ROOT is not set to a real directory", file=sys.stderr)
        return 1

    targets = page_targets(host)
    if not targets:
        print("keyword-target audit: no primaryKeyword declared on this property — nothing to audit")
        return 0

    out_path = host / "data" / "keyword-target-audit.json"
    if out_path.exists() and not args.force:
        try:
            prev = json.loads(out_path.read_text())
            age = datetime.now() - datetime.fromisoformat(prev["generated_at"])
            if age < timedelta(days=TTL_DAYS):
                n = len(prev.get("retarget_candidates", []))
                print(f"keyword-target audit: cached ({age.days}d old, TTL {TTL_DAYS}d) — "
                      f"{n} page(s) flagged. --force to re-pull.")
                for c in prev.get("retarget_candidates", [])[:8]:
                    cv = c.get("current_vol")
                    print(f"    {cv if cv is not None else 'n/a':>5}/mo  {c['slug']}  "
                          f"<- '{c['current']}'")
                return 0
        except (ValueError, KeyError, OSError):
            pass  # unreadable cache -> re-pull, never silently skip the audit

    kva = _load("build-keyword-volume-auto")
    seeds = [kw for _, kw, _ in targets]
    got = {}
    for i in range(0, len(seeds), 8):
        batch = seeds[i:i + 8]
        for attempt in range(3):
            g, _ = kva.fetch(batch, args.geo, max_calls=1)
            if g:
                got.update(g)
                break
            time.sleep(4)

    if not got:
        # Loud, and NOT written to the status file as "0 flagged" — an API outage must never
        # read as "every page is well targeted".
        print("keyword-target audit: UNREACHABLE — Keyword Planner returned nothing. "
              "No verdict this run.", file=sys.stderr)
        return 1

    flagged, ok, wrong_geo = [], 0, []
    for slug, kw, src in targets:
        # GEO TRAP. Volume is pulled for ONE country (default US). A Bangla or otherwise
        # non-Latin target measured against US demand always reads ~0, which is a property of
        # the query, not of the page. The first run duly flagged 'হাজিরা খাতা' and 'hazira
        # khata' as dead targets; Hazira Khata is a Bangladesh product with real BD demand.
        # Reporting those as badly targeted would be a lie, and the loudest kind — it points
        # at a page that is doing fine. Excluded and listed separately, so the gap is visible
        # rather than silently dropped. Re-run with --geo 1016 (Bangladesh) to audit them.
        if any(ord(ch) > 127 for ch in kw):
            wrong_geo.append({"slug": slug, "current": kw,
                              "why": f"non-Latin target not auditable against geo {args.geo}"})
            continue
        cur = got.get(kw.lower())
        cur_vol = cur["vol"] if cur else None
        if cur_vol is not None and cur_vol > DEAD_TARGET_VOL:
            ok += 1
            continue
        flagged.append({
            "slug": slug, "source": src,
            "current": kw, "current_vol": cur_vol,
        })

    # NO AUTOMATIC REPLACEMENT SUGGESTION. This deliberately reports the problem and stops.
    #
    # The first version did suggest one, by taking the highest-volume idea from the same pull
    # that shared a word with the current target. Its actual output:
    #
    #     'care home compliance software uk'  ->  'best black friday sales'   (shared: "best")
    #     'how to compare prices online'      ->  'free video talk to strangers online'
    #     'uber clone'                        ->  'app cloner'
    #
    # Token overlap cannot do this job. Tightening it to the head noun does not rescue it
    # either: the real notetube-ai win was 'youtube to flashcards' -> 'youtube video
    # summarizer', which shares no head noun at all and would have been filtered out. Every
    # correct retarget this session came from judgement no keyword list encodes — 'unblock
    # puzzle game' has more volume than 'arrow puzzles' but means a different genre; 'hourly
    # rate calculator' beats every Toss term but belongs to tool.teamzlab.com, which already
    # owns three pages for it.
    #
    # A confident wrong suggestion is worse than none, because it is the one thing likely to
    # get acted on unread. The volume of the DECLARED target is the reliable half of this
    # check, and it is the half that would have caught all five pages on day one.
    flagged.sort(key=lambda c: (c["current_vol"] if c["current_vol"] is not None else -1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "geo": args.geo,
        "thresholds": {"dead_target_vol": DEAD_TARGET_VOL, "min_alt_vol": MIN_ALT_VOL,
                       "vanity_vol": VANITY_VOL},
        "pages_audited": len(targets),
        "pages_well_targeted": ok,
        "not_auditable_wrong_geo": wrong_geo,
        "retarget_candidates": flagged,
    }, indent=2))

    print(f"keyword-target audit: {len(targets)} page(s), {ok} aimed at a real term, "
          f"{len(flagged)} flagged"
          + (f", {len(wrong_geo)} not auditable at geo {args.geo}" if wrong_geo else ""))
    for w in wrong_geo:
        print(f"    (skipped) {w['slug']} <- '{w['current']}' — {w['why']}")
    for c in flagged:
        cv = f"{c['current_vol']:>5}/mo" if c["current_vol"] is not None else " no data"
        print(f"    {cv}  {c['slug']}  <- '{c['current']}'")
    if flagged:
        print(f"    (threshold: a declared target under {DEAD_TARGET_VOL}/mo. No replacement is "
              "suggested — picking one needs judgement token overlap cannot supply. Research "
              "the page's real intent, then retarget.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
