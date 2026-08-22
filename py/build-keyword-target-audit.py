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

    notetube-ai    'youtube to flashcards'       10 /mo
    devicegpt      'phone health check app'      20 /mo
    arrow-jam-3d   '3d arrow puzzle'             10 /mo
    brimful        'color sort puzzle'          140 /mo
    top3picks      'AI gift finder app'           0 /mo
    chopstick      'rocket landing simulator'    50 /mo   (nothing bigger exists — correctly small)

Five of seven pages were built around terms almost nobody types. That is not a writing
problem and no amount of nightly enhancement fixes it — the engine was faithfully polishing
pages aimed at nothing. This is the check that would have caught it on day one.

WHAT IT DOES NOT DO.
It never edits a page, and it never says a keyword is WINNABLE — only that the current one is
too small to be worth owning. Those are different claims and conflating them is exactly the
error this file's threshold note records. Picking a replacement needs judgement this script
does not have: 'unblock puzzle game' outranks 'arrow puzzles' on volume but means a different
genre, and 'hourly rate calculator' beats every Toss term while belonging to
tool.teamzlab.com, which already owns three pages for it. So this reports and stops.

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

# VOLUME IS NOT WINNABILITY, AND THE PLANNER'S "COMPETITION" COLUMN IS NOT EITHER.
#
# That column is ADVERTISER competition — how many accounts bid on the term in Google Ads. It
# is not SEO difficulty and the two disagree hard. Every keyword chosen on 2026-08-13 read
# "Low competition" and then measured 1.0-2.3 out of 10 on real SERP composition, because all
# ten top slots were held by authority domains:
#
#     battery health android    Low comp  ->  winnability 2.3/10
#     arrow puzzles             Low comp  ->  winnability 2.1/10
#     youtube video summarizer  Low comp  ->  winnability 1.7/10
#     water sort puzzle         Low comp  ->  winnability 1.0/10
#
# So this file deliberately reports volume ONLY, and never claims a term is winnable.
# build-serp-difficulty.py measures who actually ranks; where it has scored a keyword, that
# number is shown alongside, and where it has not, the gap is stated rather than filled with
# the advertiser-competition proxy. build-course-radar.py already follows exactly this rule.
SERP_FILE = "data/serp-difficulty.json"


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
    # Markdown collections. Add a directory here and it is audited on every property that has
    # one; properties without it skip the loop, so this list is safe to extend.
    for d in ("src/content/apps", "src/content/blog", "src/content/books"):
        root = host / d
        if not root.exists():
            continue
        for f in sorted(root.glob("*.md")):
            if f.stem.lower() == "readme":
                continue
            # READ THE WHOLE FRONTMATTER, NOT A FIXED PREFIX.
            # The first version capped the read at 4000 chars. Several pages carry a long provenance
            # comment above the fields — notetube-ai.md declares primaryKeyword on line 42, past the
            # cap — so the page was reported as "no target declared" and dropped from the audit
            # silently. A page missing from a coverage report is the worst possible failure here: it
            # reads as nothing-to-fix. Frontmatter is small; read it all.
            txt = f.read_text(errors="ignore")
            head = txt.split("\n---", 1)[0] if txt.startswith("---") else txt[:8000]
            mk = re.search(r"^primaryKeyword:\s*['\"]?(.+?)['\"]?\s*$", head, re.M)
            if mk:
                out.append((f.stem, mk.group(1).strip(), str(f.relative_to(host))))
            else:
                # Undeclared is a finding, not a skip — it is how a page ends up aimed at nothing.
                out.append((f.stem, None, str(f.relative_to(host))))

    # HAND-WRITTEN .astro ROUTES — the blind spot this audit had for its whole life.
    #
    # On apps.teamzlab.com the entire agency service surface (/vibe-coding-agency/,
    # /hire-app-developer-for-startup/, /ai-agent-development/, ...) is .astro under src/pages/,
    # not markdown under src/content/. Those are the pages that actually convert visitors into
    # clients, and every one of them was invisible here: 67 pages audited, zero service pages
    # among them. An audit that silently omits the money pages reads as "the money pages are
    # fine", which is the worst failure this file can have — the same class of bug as the
    # 4000-char frontmatter cap above.
    #
    # They carry no `primaryKeyword` today (service copy lives in src/data/services.ts, which has
    # seo.title and jsonLdService but no declared target), so they land in `no_target_declared`.
    # That is the honest result, and it costs zero Keyword Planner calls: undeclared pages are
    # filtered out before the volume batches are built. Declaring targets for them is a separate
    # decision for whoever owns that file.
    #
    # Static routes only. Anything with a bracket in its path is a dynamic route whose real pages
    # come from a collection already scanned above; auditing `[slug].astro` would report one
    # fictional page instead of the many real ones.
    # Utility routes that exist on every site and can never have a search target. Listing them
    # as "no target declared" every run would bury the finding that actually matters — a service
    # page with no target — under a dozen rows nobody can act on.
    UTILITY = {
        "404", "500", "privacy", "privacy-policy", "terms", "eula", "data-deletion",
        "search", "animations", "sitemap", "robots", "offline", "thanks", "thank-you",
    }
    pages_root = host / "src" / "pages"
    if pages_root.exists():
        for f in sorted(pages_root.rglob("*.astro")):
            rel = f.relative_to(pages_root)
            if any("[" in part for part in rel.parts):
                continue
            if any(part.startswith("_") for part in rel.parts):
                continue
            slug = rel.parent.as_posix() if f.stem == "index" else (rel.parent / f.stem).as_posix()
            slug = slug.strip("./") or "index"
            if slug in UTILITY or slug.split("/")[-1] in UTILITY:
                continue
            txt = f.read_text(errors="ignore")
            mk = re.search(r"^\s*(?:const\s+)?primaryKeyword\s*[:=]\s*['\"](.+?)['\"]", txt, re.M)
            out.append((slug, mk.group(1).strip() if mk else None, str(f.relative_to(host))))
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

    undeclared = [{"slug": s, "source": src} for s, kw, src in targets if not kw]
    targets = [t for t in targets if t[1]]

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

    # Measured SERP winnability, where build-serp-difficulty.py has scored the keyword.
    serp = {}
    try:
        sd = json.loads((host / SERP_FILE).read_text())
        serp = {k.lower(): v for k, v in (sd.get("keywords") or {}).items()}
    except (OSError, ValueError):
        pass  # never scored on this property yet — reported as "not scored", never guessed

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
        sw = serp.get(kw.lower())
        flagged.append({
            "slug": slug, "source": src,
            "current": kw, "current_vol": cur_vol,
            # None means "never SERP-scored", NOT "easy". The advertiser-competition column is
            # deliberately not substituted here — see the note at the top of this file.
            "serp_winnability": sw.get("winnability") if sw else None,
            "serp_why": sw.get("why") if sw else None,
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
        "thresholds": {"dead_target_vol": DEAD_TARGET_VOL},
        "serp_scored": sum(1 for c in flagged if c["serp_winnability"] is not None),
        "pages_audited": len(targets),
        "pages_well_targeted": ok,
        "not_auditable_wrong_geo": wrong_geo,
        "no_target_declared": undeclared,
        "retarget_candidates": flagged,
    }, indent=2))

    print(f"keyword-target audit: {len(targets)} page(s), {ok} aimed at a real term, "
          f"{len(flagged)} flagged"
          + (f", {len(wrong_geo)} not auditable at geo {args.geo}" if wrong_geo else ""))
    for u in undeclared:
        print(f"    (no target) {u['slug']} — no primaryKeyword in frontmatter")
    for w in wrong_geo:
        print(f"    (skipped) {w['slug']} <- '{w['current']}' — {w['why']}")
    for c in flagged:
        cv = f"{c['current_vol']:>5}/mo" if c["current_vol"] is not None else " no data"
        w = c["serp_winnability"]
        wtxt = f"  win {w}/10" if w is not None else "  win not scored"
        print(f"    {cv}{wtxt}  {c['slug']}  <- '{c['current']}'")
    if flagged:
        print(f"    (flagged = declared target under {DEAD_TARGET_VOL}/mo. Volume is NOT "
              "winnability: run build-serp-difficulty.py for the 'win' column, and never read "
              "Planner's Low/Medium/High as SEO difficulty — that is advertiser competition.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
