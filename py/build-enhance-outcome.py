#!/usr/bin/env python3
"""Grade the enhancement engine against a control group. THE MISSING FEEDBACK LOOP.

The nightly picks ~10 pages a night by GSC rank and rewrites them. Until 2026-07-22
nothing had ever checked whether a rewritten page then improved: no script read
data/enhancement-log.json, and the engine's own commits were the only record that
an edit ever happened. Months of nightly compute with no evidence it works.

First controlled run, 2026-07-22 on teamzlab-tools, 28d windows, 167 enhanced pages
(151 after excluding event-driven sections):

    ENHANCED   718 -> 4,230 clicks   +489%
    CONTROL    654 -> 2,180 clicks   +233%

Enhanced pages beat the untouched control. Read that as WEAK POSITIVE, not proof:
116 of 151 pages moved zero clicks, so the aggregate rides on a handful of winners, and
the engine deliberately selects struggling pages (rank 11-25, weak CTR), which cuts both
ways — they start behind, but mean-reversion also flatters them.

Four traps this script exists to avoid. Every one of them produced a confident, wrong,
plausible-looking answer during development, and three of them failed SILENTLY:

1. No control => you measure the season, not the work. The raw before/after on the
   treated group alone scored +6,205 clicks and looked like a triumph. The movers were
   /football/fifa-world-cup-2026-* and the World Cup ran through the window.
2. Misaligned windows => you measure backwards. An earlier attempt used per-page dates
   for the treated group but ONE fixed split date for the control, so every page
   enhanced after that date had its post-edit traffic counted in its "before" window.
   That inversion reported the engine as 4x WORSE than doing nothing. Both cohorts must
   use the same window.
3. Treated cohort swallows the site => no control left. Counting file ADDS, or any
   modification at all, marked 7,023-7,199 of tools' ~7,119 pages as enhanced and left a
   control group worth 4 clicks. Bulk maintenance is the culprit: one commit on
   2026-07-22 modified 1,473 pages. Hence all three filters in enhanced_pages() —
   subject grep for intent, diff-filter=M, and a files-per-commit cap.
4. Portability failures that look like "no data". Each of these reported a healthy,
   empty result on some property: parsing the commit subject (only tools puts a URL
   there), excluding "(^|/)index.html" (that IS the page on tools), and bounding the
   cohort at today-W*4 (excluded the April burst that is 753 of learn's 781 pages).
   That is why an empty cohort now prints WHICH reason applies and the date range it saw.

So: always report the control beside the treatment, never the raw before/after alone —
and never let "found nothing" and "nothing to find" print the same line.

Usage:
    python3 scripts/build-enhance-outcome.py                 # 28d windows
    python3 scripts/build-enhance-outcome.py --window 56
    python3 scripts/build-enhance-outcome.py --json-only

Output:
    data/enhance-outcome.json   — full per-page table + cohort summary
    stdout                      — verdict lines (nightly greps these)

Requires: TEAMZ_SC_TOKEN_FILE, TEAMZ_SITE_PROPERTY, TEAMZ_GOOGLE_CLOUD_PROJECT
"""

import argparse
import json
import time
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _teamz_config import load_runtime  # noqa: E402

# MUST come from load_runtime, never from Path(__file__).parent.parent. Every host repo
# exposes this file as a SYMLINK in its scripts/ dir, so resolve() collapses to
# <automation>/py and every property would score tool.teamzlab.com instead of itself —
# the same wrong-property bug that made goalkit read as 0 clicks for months.
# load_runtime also normalises the GSC property correctly: URL-prefix properties MUST end
# in "/", sc-domain properties MUST NOT (goalkit is sc-domain:goalkit.teamzlab.com).
_RT = load_runtime(__file__)
ROOT = _RT["host_site_root"]
PROP = _RT["site_property"]
PROJECT = _RT["google_project"]
TOKEN_FILE = _RT["sc_token_file"]
SITE = _RT["site_url"].rstrip("/")
CTX = ssl.create_default_context()

# Sections whose traffic is driven by a fixed-date external event. A World Cup or a
# league final moves these by 100x regardless of anything we write, so including them
# in either cohort makes the comparison meaningless in exactly the weeks we most want
# to read it. Reported separately, never mixed into the verdict.
EVENT_DRIVEN = re.compile(r"/(football|cricket|games|gaming)/")




def access_token():
    t = json.loads(TOKEN_FILE.read_text())
    data = urllib.parse.urlencode({
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    return json.loads(urllib.request.urlopen(req, context=CTX, timeout=60).read())["access_token"]


def pages_in_window(tok, start, end):
    """page -> (clicks, impressions). Raises on API failure — NEVER returns {} quietly.

    An empty dict here would read as 'every page got zero clicks', which would score
    the engine as catastrophic on a network blip. Fail loud instead.
    """
    out = {}
    url = ("https://www.googleapis.com/webmasters/v3/sites/"
           + urllib.parse.quote(PROP, safe="") + "/searchAnalytics/query")
    # PAGE SIZE, not the timeout, was the problem. Asking GSC for 25,000 page rows at a
    # time stopped fitting inside 180s as the site grew past ~7,000 pages, and this phase
    # had failed every night since 2026-08-20 with "The read operation timed out" — eight
    # nights with no proof that any enhancement worked. GSC answers a 5,000-row request in
    # a small fraction of the time, so five smaller calls beat one that never lands.
    PAGE = 5000
    for offset in range(0, 100000, PAGE):
        body = json.dumps({"startDate": str(start), "endDate": str(end),
                           "dimensions": ["page"], "rowLimit": PAGE,
                           "startRow": offset, "dataState": "all"}).encode()
        rows = None
        for attempt in range(3):
            req = urllib.request.Request(url, data=body, method="POST", headers={
                "Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                "x-goog-user-project": PROJECT})
            try:
                rows = json.loads(
                    urllib.request.urlopen(req, context=CTX, timeout=180).read()
                ).get("rows", [])
                break
            except (TimeoutError, urllib.error.URLError, OSError):
                # Retry a slow or dropped call rather than failing the whole phase. The
                # raise on the last attempt is deliberate and matches this function's
                # contract above: an empty result must never be mistaken for "no clicks".
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
        for r in rows:
            out[r["keys"][0].rstrip("/") + "/"] = (r["clicks"], r["impressions"])
        if len(rows) < PAGE:
            break
    return out


# Generated every run and touched by almost every commit. Counting these as "enhanced"
# would put the entire site in the treated cohort and leave no control group.
# NOTE the anchoring: "^index\.html$" is the ROOT homepage only. An earlier version used
# "(^|/)index\.html$", which matched every <section>/<page>/index.html — i.e. all ~7,100
# tools pages — so the treated cohort came back empty and the script reported "no page
# has a complete window yet". Same silent-skip failure mode as the subject parser it
# replaced: on tools, <dir>/index.html IS the page, not a generated artifact.
GENERATED = re.compile(
    r"(^|/)(sitemap[^/]*\.xml|llms(-full)?\.txt|robots\.txt|search-index\.js|tools\.json|"
    r"sw\.js)$|^index\.html$|^(data|logs|docs|scripts|shared|\.claude)/")


def to_url_path(f):
    """Repo file -> the URL path it renders as, or None if that is not 1:1.

    Two site shapes across the properties:
      static HTML (tools, learn, goalkit)  us/foo/index.html -> /us/foo/
                                           c/slug.html       -> /c/slug.html
      Astro collections (apps)             src/content/<coll>/<slug>.md -> URL depends on
                                            the COLLECTION's own page router, NOT the
                                            collection folder name — they are not the same
                                            string. Checked each router directly (2026-08-11):
                                              apps      -> src/pages/[slug].astro       -> /<slug>/   (NO prefix)
                                              blog      -> src/pages/blog/[slug].astro  -> /blog/<slug>/
                                              roadmaps  -> src/pages/roadmap/[slug].astro -> /roadmap/<slug>/  (singular!)
                                            hazira-guides/hazira-tutorials have NO dedicated
                                            router at all — they render as an embedded
                                            component inside another page (HaziraGuides.astro),
                                            not as their own addressable URL. Stays unmappable.

    2026-08-11 bug found live: this used to return f"/{collection}/{slug}/" for EVERY
    collection, so 'apps' commits (the collection with the most pages) mapped to
    /apps/<slug>/ — a URL that has never existed. enhance-outcome.json was silently querying
    a 404 for every apps page: /no-trace-chat/ (the REAL, live page, 49 real impressions)
    got read as 0/0 forever, reported "inconclusive: not enough baseline clicks" — the
    learning loop could never tell whether any apps edit worked. Root-caused from apps'
    own nightly content-agent report flagging it, not found independently — see
    data/last-night-content.md 2026-08-10 for the original catch.

    Returns None rather than guessing. apps' commits frequently edit src/data/services.ts,
    a single file backing MANY service pages — attributing that to one URL would be a
    fabricated data point, and attributing it to all of them would flood the treated
    cohort. Unmappable edits are COUNTED and reported, never silently dropped: a shrinking
    measurable share is itself the signal that this mapping needs extending.
    """
    if f.endswith("/index.html"):
        return "/" + f[: -len("index.html")]
    if f.endswith(".html"):
        return "/" + f
    COLLECTION_URL_PREFIX = {"apps": "", "blog": "blog/", "roadmaps": "roadmap/"}
    m = re.match(r"^src/content/([^/]+)/(.+)\.(md|mdx)$", f)
    if m:
        coll, slug = m.group(1), m.group(2)
        if coll not in COLLECTION_URL_PREFIX:
            return None   # no confirmed router for this collection — don't guess
        return f"/{COLLECTION_URL_PREFIX[coll]}{slug}/"
    return None


def enhanced_pages():
    """page path -> FIRST date it was enhanced, from the FILES each commit changed.

    Deliberately does NOT parse the commit subject. Every property words these
    differently and a subject parser fails SILENTLY — it finds nothing and the script
    prints "no page has a complete window yet", which is indistinguishable from a young
    property with no history:
        tools    enhance(rising): /gaming/kd-ratio-calculator/ — rank 4.6 ...
        apps     content(rag-development-company): add discovery-call shortlist FAQ
        goalkit  content(barcelona-2025-26-away): cold-start — seo_title '...'
        learn    content(radar): park the Bangla batch — US-only pull
    Only tools puts a URL path in the subject. Parsing it scored tools correctly and
    reported the other three as having no data at all.

    data/enhancement-log.json is not usable either: on tools it tracks 4 hand-edited
    pages and was last written 2026-05-05, against 366 pages the engine has enhanced.

    The changed file list is the one record every property keeps the same way.
    """
    # Three filters, each removing a distinct class of false positive. Dropping any one of
    # them put essentially the whole site in the treated cohort and left no control:
    #   1. --grep on the subject   -> INTENT. A page touched by a schema sweep was not
    #                                 "enhanced". Every property prefixes deliberate
    #                                 content work with enhance(...) or content(...).
    #   2. --diff-filter=M         -> "A" is the commit that CREATED the page. Creating is
    #                                 not enhancing. With A included tools reported 7,199
    #                                 enhanced pages against ~7,119 that exist.
    #   3. MAX_FILES_PER_COMMIT    -> bulk maintenance still slips through the subject
    #                                 filter. The related-tools repair on 2026-07-22 was a
    #                                 single commit touching 1,473 pages; counting it would
    #                                 mark 20% of the site as enhanced on one day. A real
    #                                 enhancement edits one page, occasionally a few.
    # The subject supplies intent only — never the page identity. Subject FORMATS differ by
    # property (only tools puts a URL path there), so WHICH page always comes from the
    # changed-file list, which every property records the same way.
    MAX_FILES_PER_COMMIT = 5
    log = subprocess.run(
        ["git", "log", "--all", "-E", "--grep=^(enhance|content)\\(",
         "--pretty=format:%x00%as", "--name-only", "--diff-filter=M",
         "--", "*.html", "*.md", "*.mdx"],
        cwd=ROOT, capture_output=True, text=True).stdout

    commits, cur, files = [], None, []
    for line in log.splitlines():
        if line.startswith("\x00"):
            if cur:
                commits.append((cur, files))
            cur, files = line[1:].strip(), []
            continue
        f = line.strip()
        if cur and f and not GENERATED.search(f):
            files.append(f)
    if cur:
        commits.append((cur, files))

    first = {}
    unmappable = 0
    for d, fs in commits:
        if not fs or len(fs) > MAX_FILES_PER_COMMIT:
            continue
        for f in fs:
            p = to_url_path(f)
            if p is None:
                unmappable += 1
                continue
            if p not in first or d < first[p]:
                first[p] = d
    return first, unmappable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=28, help="days before/after (default 28)")
    ap.add_argument("--max-age", type=int, default=180,
                    help="oldest enhance date to score, in days (default 180)")
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()
    W = args.window

    today = date.today()
    # A page needs a full W-day "after" window that has already elapsed. The older bound
    # is only about GSC retention (~16 months), NOT about W: an earlier version used
    # today - W*4, which on learn excluded the April burst that is 753 of its 781 pages,
    # so it reported "no data" every night while holding four months of measurable history.
    newest = today - timedelta(days=W + 3)
    oldest = today - timedelta(days=args.max_age)

    first, unmappable = enhanced_pages()
    cohort = {p: d for p, d in first.items()
              if oldest <= date.fromisoformat(d) <= newest}
    if not cohort:
        # Say WHICH of the two reasons applies. "no pages in window" and "this property
        # has no page history at all" demand completely different responses, and a single
        # message for both is how a monitor starts lying.
        if not first:
            print(f"enhance-outcome: no attributable page edits found "
                  f"({unmappable} edits touched files that map to no single URL) — nothing to score")
        else:
            ds = sorted(first.values())
            print(f"enhance-outcome: {len(first)} pages known ({ds[0]} .. {ds[-1]}) but NONE fall "
                  f"in the scoring window {oldest} .. {newest} — "
                  f"raise --max-age or wait for the {W}d after-window to elapse")
        return 0

    try:
        tok = access_token()
    except Exception as e:  # noqa: BLE001
        print(f"enhance-outcome: FAILED to authenticate ({type(e).__name__}) — NOT scoring", file=sys.stderr)
        return 1

    cache = {}

    def win(s, e):
        if (s, e) not in cache:
            cache[(s, e)] = pages_in_window(tok, s, e)
        return cache[(s, e)]

    by_date = defaultdict(list)
    for p, d in cohort.items():
        by_date[d].append(p)

    rows = []
    try:
        for d, ps in sorted(by_date.items()):
            ed = date.fromisoformat(d)
            before = win(ed - timedelta(days=W + 1), ed - timedelta(days=1))
            after = win(ed + timedelta(days=1), ed + timedelta(days=W + 1))
            for p in ps:
                u = SITE + p
                bc, bi = before.get(u, (0, 0))
                ac, ai = after.get(u, (0, 0))
                rows.append({"page": p, "enhanced": d, "clicks_before": bc,
                             "clicks_after": ac, "impr_before": bi, "impr_after": ai,
                             "event_driven": bool(EVENT_DRIVEN.search(p))})
    except urllib.error.HTTPError as e:
        print(f"enhance-outcome: GSC HTTP {e.code} — NOT scoring (a partial pull would "
              f"score the engine on missing data)", file=sys.stderr)
        return 1

    # --- control cohort: same calendar window, pages the engine never touched -------
    # Without this the verdict is worthless. The first run scored +6,205 clicks on the
    # treatment group and would have read as a triumph; the control grew 4x faster.
    mid = sorted(cohort.values())[len(cohort) // 2]
    md = date.fromisoformat(mid)
    cb = win(md - timedelta(days=W + 1), md - timedelta(days=1))
    ca = win(md + timedelta(days=1), md + timedelta(days=W + 1))
    treated = {SITE + p for p in cohort}
    allu = set(cb) | set(ca)

    def agg(urls):
        return (sum(cb.get(u, (0, 0))[0] for u in urls),
                sum(ca.get(u, (0, 0))[0] for u in urls))

    steady = {u for u in allu if not EVENT_DRIVEN.search(u)}
    t_b, t_a = agg(treated & steady)
    c_b, c_a = agg((allu - treated) & steady)
    t_g = ((t_a - t_b) / t_b * 100) if t_b else None
    c_g = ((c_a - c_b) / c_b * 100) if c_b else None

    steady_rows = [r for r in rows if not r["event_driven"]]
    summary = {
        "generated_for": str(today),
        "window_days": W,
        "cohort_range": [str(oldest), str(newest)],
        "pages_measured": len(rows),
        "pages_steady": len(steady_rows),
        "up": sum(1 for r in steady_rows if r["clicks_after"] > r["clicks_before"]),
        "down": sum(1 for r in steady_rows if r["clicks_after"] < r["clicks_before"]),
        "flat": sum(1 for r in steady_rows if r["clicks_after"] == r["clicks_before"]),
        "treated_clicks": [t_b, t_a], "treated_growth_pct": t_g,
        "control_clicks": [c_b, c_a], "control_growth_pct": c_g,
        "verdict": None,
    }
    if t_g is None or c_g is None:
        summary["verdict"] = "inconclusive: not enough baseline clicks"
    elif t_g >= c_g:
        summary["verdict"] = "enhanced pages outperformed the untouched control"
    else:
        summary["verdict"] = ("enhanced pages UNDERPERFORMED the untouched control "
                              "(expected in part: the engine selects struggling pages)")

    out = ROOT / "data" / "enhance-outcome.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "pages": rows}, indent=2))

    if not args.json_only:
        print(f"  enhance-outcome ({W}d windows, {len(rows)} pages, "
              f"{len(steady_rows)} excluding event-driven sections"
              + (f", {unmappable} edits unattributable" if unmappable else "") + ")")
        print(f"    up {summary['up']}  /  down {summary['down']}  /  flat {summary['flat']}")
        g = lambda v: "n/a" if v is None else f"{v:+.0f}%"  # noqa: E731
        print(f"    ENHANCED  {t_b:6} -> {t_a:6} clicks   {g(t_g)}")
        print(f"    CONTROL   {c_b:6} -> {c_a:6} clicks   {g(c_g)}")
        print(f"    verdict: {summary['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
