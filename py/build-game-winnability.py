#!/usr/bin/env python3
"""
build-game-winnability — the gate that decides which retro game concepts are worth building.

WHY THIS EXISTS. Seven webview game apps shipped without this check. Four of them have never
had a single install, and eighteen of nineteen web pages draw under 260 impressions between
them. They failed for two different reasons that look identical afterwards: some targeted a
concept nobody searches (invented names), and some targeted a concept a giant already owns.
Volume alone catches neither. `daily-word-grid` sits on 673,000 searches a month and gets five
impressions, because the term belongs to the NYT; `arrow-escape-3d` sits on 1,900 and gets
78,000 impressions, because nobody owns "arrow puzzle game".

So the question this asks is not "is this popular" but "is this WINNABLE" — demand that exists
AND an incumbent field weak enough to displace. Two independent sources, because either one
alone has already produced a wrong answer:

  * Google Keyword Planner (web search demand, the same API the content engine uses)
  * Google Play top results (the store field: rating, installs, how stale)

The verdict is a FILTER, not a decision. It narrows forty concepts to a handful worth looking
at by hand. A BUILD verdict still needs an eyeball on the live SERP before anyone writes code —
the SERP-brand check is the thing that cannot be automated, and skipping it is what produced
the solitaire pages that sit at position 59 behind solitaired.com.

Ads "competition" is deliberately NOT used as a difficulty signal. It measures ADVERTISERS
bidding, not organic difficulty. Misreading that column is how "Arrow Jam" got its name.

Usage:
  python3 py/build-game-winnability.py --seeds <file> --out <dir>
  python3 py/build-game-winnability.py --seeds <file> --out <dir> --skip-play   # volumes only
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Planner geo target ids. US and GB are the revenue geos; BD is carried as information only
# because it is where the owner's network lives, and its ad revenue per session is a fraction
# of the others — a BD-only term is an audience, not a business.
GEOS = {"US": 2840, "GB": 2826, "BD": 2050}
REVENUE_GEOS = ("US", "GB")

SEEDS_PER_CALL = 10          # Google Ads caps generateKeywordIdeas seeds at 10
PLAY_TOP_N = 6               # how many store results define "the field" for a term
PLAY_PAUSE = 1.1             # seconds between Play requests; unthrottled scraping gets 429s

# Verdict thresholds. Deliberately conservative: a wrong SKIP costs one idea, a wrong BUILD
# costs weeks of building plus a store listing that then has to be maintained forever.
MIN_REVENUE_VOL = 1000       # US+GB monthly searches below this is not a business
STRONG_RATING = 4.4          # a field of these is not displaceable by a new app
STRONG_INSTALLS = 1_000_000
WEAK_RATING = 4.2            # median below this = the incumbents are annoying people
SMALL_FIELD_INSTALLS = 500_000


# ---------------------------------------------------------------- keyword volume

def planner_volumes(keywords, geo_id, max_calls=40):
    """{keyword: vol} for the seeds we asked about. Related ideas are kept too — Planner
    badly underreports the long tail, and the neighbours it returns are often the phrasing
    people actually type."""
    import requests
    import google_ads_api as _ads
    try:
        cfg, access = _ads.credentials()
    except Exception as e:  # noqa: BLE001
        return {}, f"credentials unavailable ({type(e).__name__})"
    hdrs = _ads.headers(cfg, access)
    url = _ads.endpoint(cfg, hdrs)
    if not url:
        return {}, "no Google Ads API version answered"

    got, calls = {}, 0
    for i in range(0, len(keywords), SEEDS_PER_CALL):
        if calls >= max_calls:
            break
        seeds = keywords[i:i + SEEDS_PER_CALL]
        calls += 1
        try:
            r = requests.post(url, headers=hdrs, json={
                "keywordSeed": {"keywords": seeds},
                "language": "languageConstants/1000",
                "geoTargetConstants": [f"geoTargetConstants/{geo_id}"],
                "keywordPlanNetwork": "GOOGLE_SEARCH",
            }, timeout=60)
            if r.status_code != 200:
                print(f"    HTTP {r.status_code}: {r.text[:120]}", file=sys.stderr)
                continue
            for idea in r.json().get("results", []):
                m = idea.get("keywordIdeaMetrics") or {}
                got[idea.get("text", "").strip().lower()] = int(m.get("avgMonthlySearches", 0) or 0)
        except Exception as e:  # noqa: BLE001
            print(f"    call failed ({type(e).__name__}) — continuing", file=sys.stderr)
        time.sleep(0.4)
    return got, f"{calls} call(s), {len(got)} ideas"


# ---------------------------------------------------------------- play store field

def _http(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return fh.read().decode("utf-8", "ignore")


def play_search_ids(term, country="us", limit=PLAY_TOP_N):
    """Package ids for the top store results.

    google_play_scraper's own search() is broken against the current Play markup (it indexes
    a dataset key, ds:4, that no longer exists), so the ids come from the page directly. The
    detail endpoint that library uses still works, and is used below.
    """
    q = urllib.parse.quote(term)
    url = f"https://play.google.com/store/search?q={q}&c=apps&hl=en&gl={country}"
    try:
        html = _http(url)
    except Exception:  # noqa: BLE001
        return []
    ids, seen = [], set()
    for m in re.finditer(r"/store/apps/details\?id=([A-Za-z0-9._]+)", html):
        pkg = m.group(1)
        if pkg not in seen:
            seen.add(pkg)
            ids.append(pkg)
        if len(ids) >= limit:
            break
    return ids


def play_field(term, country="us"):
    """The incumbent field for one term: who ranks, how well rated, how big, how stale."""
    from google_play_scraper import app as play_app
    out = []
    for pkg in play_search_ids(term, country):
        time.sleep(PLAY_PAUSE)
        try:
            d = play_app(pkg, lang="en", country=country)
        except Exception:  # noqa: BLE001
            continue
        out.append({
            "pkg": pkg,
            "title": (d.get("title") or "")[:60],
            "developer": (d.get("developer") or "")[:40],
            # score is None for apps with too few ratings to show one — that is a real
            # signal (a fresh or ignored app), not missing data, so it is kept as None
            # and excluded from the median rather than defaulted to zero.
            "score": round(d["score"], 2) if d.get("score") else None,
            "ratings": d.get("ratings"),
            "installs": d.get("realInstalls"),
            "released": d.get("released"),
            "updated": d.get("updated"),
        })
    return out


# ---------------------------------------------------------------- verdict

def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else round((xs[n // 2 - 1] + xs[n // 2]) / 2, 2)


def verdict(row):
    """BUILD / CONTESTED / SKIP, plus the one sentence that says why.

    Every BUILD still requires a manual SERP check before any code is written. This function
    cannot see who owns the web result, and that is the signal that killed the solitaires.
    """
    rev_vol = sum(row["vol"].get(g, 0) for g in REVENUE_GEOS)
    field = row.get("play") or []
    scores = [a["score"] for a in field]
    installs = [a["installs"] for a in field if a["installs"] is not None]
    med = _median(scores)
    top_installs = max(installs) if installs else 0
    strong = sum(1 for a in field
                 if (a["score"] or 0) >= STRONG_RATING
                 and (a["installs"] or 0) >= STRONG_INSTALLS)

    row["rev_vol"] = rev_vol
    row["median_rating"] = med
    row["top_installs"] = top_installs
    row["strong_incumbents"] = strong

    if rev_vol < MIN_REVENUE_VOL:
        return "SKIP", f"only {rev_vol:,}/mo in US+GB — not enough demand to matter"
    if not field:
        return "CONTESTED", f"{rev_vol:,}/mo but the store field could not be read — check by hand"
    if strong >= 3:
        return "SKIP", (f"{strong} of the top {len(field)} are ≥{STRONG_RATING}★ with "
                        f"{STRONG_INSTALLS//1_000_000}M+ installs — an established field")
    if med is not None and med < WEAK_RATING:
        return "BUILD", (f"{rev_vol:,}/mo and the field is weak — median {med}★ "
                         f"across the top {len(field)}")
    if top_installs and top_installs < SMALL_FIELD_INSTALLS:
        return "BUILD", (f"{rev_vol:,}/mo and nobody is big — best incumbent has "
                         f"{top_installs:,} installs")
    return "CONTESTED", (f"{rev_vol:,}/mo, median {med}★, best {top_installs:,} installs — "
                         f"real demand behind a decent field; needs a SERP check")


# ---------------------------------------------------------------- report

def write_markdown(path, rows, meta):
    order = {"BUILD": 0, "CONTESTED": 1, "SKIP": 2}
    rows = sorted(rows, key=lambda r: (order[r["verdict"]], -r["rev_vol"]))
    L = []
    L.append("# Retro game winnability — Phase 0 research gate\n")
    L.append(f"Generated {meta['generated']} · {meta['n_terms']} terms · "
             f"Planner geos {'/'.join(GEOS)} · Play field = top {PLAY_TOP_N} results (US store)\n")
    L.append("**A BUILD verdict is a shortlist entry, not a decision.** It means demand is real "
             "and the store field looks soft. Before any code is written, the live web SERP for "
             "the term has to be looked at by hand: if the first page belongs to a giant portal, "
             "the term is dead regardless of what the store looks like. That check is what the "
             "solitaire pages skipped, and they sit at position 59.\n")
    L.append("| verdict | term | US/mo | GB/mo | BD/mo | med ★ | best installs | top incumbent | why |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        top = (r.get("play") or [{}])[0]
        med = r["median_rating"] if r["median_rating"] is not None else "—"
        L.append("| {v} | {t} | {us:,} | {gb:,} | {bd:,} | {m} | {inst} | {top} | {why} |".format(
            v=r["verdict"], t=r["term"],
            us=r["vol"].get("US", 0), gb=r["vol"].get("GB", 0), bd=r["vol"].get("BD", 0),
            m=med,
            inst=f"{r['top_installs']:,}" if r["top_installs"] else "—",
            top=(top.get("title") or "—").replace("|", "/"),
            why=r["why"]))
    L.append("")

    build = [r for r in rows if r["verdict"] == "BUILD"]
    L.append(f"## Shortlist — {len(build)} term(s) reached BUILD\n")
    if not build:
        L.append("None. Nothing on this seed list clears the gate: either the demand is not "
                 "there or the field is already strong. The right move is a new seed list, "
                 "not a build.\n")
    for r in build:
        L.append(f"### {r['term']} — {r['rev_vol']:,}/mo US+GB\n")
        L.append(f"{r['why']}.\n")
        L.append("| # | app | developer | ★ | ratings | installs | released |")
        L.append("|---|---|---|---|---|---|---|")
        for i, a in enumerate(r.get("play") or [], 1):
            L.append("| {i} | {t} | {d} | {s} | {n} | {inst} | {rel} |".format(
                i=i, t=(a["title"] or "").replace("|", "/"),
                d=(a["developer"] or "").replace("|", "/"),
                s=a["score"] if a["score"] is not None else "—",
                n=f"{a['ratings']:,}" if a.get("ratings") else "—",
                inst=f"{a['installs']:,}" if a.get("installs") else "—",
                rel=a.get("released") or "—"))
        L.append("")
    Path(path).write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="file with one term per line, # for comments")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--skip-play", action="store_true", help="volumes only, no store scan")
    ap.add_argument("--max-calls", type=int, default=40)
    args = ap.parse_args()

    terms = [ln.strip() for ln in Path(args.seeds).read_text().splitlines()]
    terms = [t for t in terms if t and not t.startswith("#")]
    if not terms:
        print("no seed terms", file=sys.stderr)
        return 1
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Phase 0 winnability gate — {len(terms)} terms")

    vols = {}
    for name, gid in GEOS.items():
        print(f"  Keyword Planner {name}...")
        got, note = planner_volumes(terms, gid, args.max_calls)
        print(f"    {note}")
        vols[name] = got

    rows = []
    for t in terms:
        key = t.strip().lower()
        rows.append({"term": t, "vol": {g: vols[g].get(key, 0) for g in GEOS}})

    if not args.skip_play:
        # Only terms with real revenue-geo demand get a store scan. Scraping the field for a
        # term nobody searches is a request budget spent to learn nothing.
        scan = [r for r in rows if sum(r["vol"].get(g, 0) for g in REVENUE_GEOS) >= MIN_REVENUE_VOL]
        print(f"  Play field scan for {len(scan)} of {len(rows)} terms "
              f"(the rest are below {MIN_REVENUE_VOL:,}/mo US+GB)...")
        for i, r in enumerate(scan, 1):
            print(f"    [{i}/{len(scan)}] {r['term']}")
            r["play"] = play_field(r["term"])

    for r in rows:
        r["verdict"], r["why"] = verdict(r)

    meta = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "n_terms": len(rows), "geos": GEOS, "play_top_n": PLAY_TOP_N}
    (outdir / "winnability.json").write_text(
        json.dumps({"meta": meta, "rows": rows}, indent=1), encoding="utf-8")
    write_markdown(outdir / "winnability.md", rows, meta)

    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("\n  " + " · ".join(f"{v}: {counts.get(v, 0)}" for v in ("BUILD", "CONTESTED", "SKIP")))
    print(f"  wrote {outdir/'winnability.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
