#!/usr/bin/env python3
"""
build-season-radar.py — which pages are about to have their season, learned from LAST YEAR.

THE GAP THIS CLOSES
-------------------
Everything watching seasonality in this repo is either hand-written or reactive:

  data/event-calendar.json   5 events, typed by a human. Only those pages ever get
                             seasonal attention. Every other page on a 6,845-page site is
                             invisible to it — tax deadlines, exam months, Christmas,
                             hurricane season, whatever else the site happens to serve.
  build-revenue-watchdog.py  fires when revenue DROPS. By then the money is already gone,
                             and it is silent on the opposite and more valuable case: a page
                             whose traffic is about to rise, which is worth preparing for.

Owner, 2026-08-14: "it should be also for any other pages genericly which demand this type of
adjustment to grow". He is right. A calendar is a list of the seasons somebody remembered.

WHAT THIS DOES INSTEAD
----------------------
It asks the data, not a human. For every page, using Search Console's 16-month history:

    LAST YEAR, was this page busier in the month AFTER this date than in the month BEFORE it?

If yes, that page has a season and the season starts about now. Compare that to what the page
is doing THIS year at the same point, and each page falls into one of:

    RISING    its season is starting and it is already climbing  -> on track, leave it
    ASLEEP    its season started last year but it is flat now    -> THIS is the alert
    n/a       no repeatable pattern                              -> ignored, most pages

ASLEEP is the whole point. It is a page that made money at this exact time last year and is not
moving yet — found without anybody having written its date down anywhere.

WHY LAST YEAR AND NOT A TREND LINE
----------------------------------
A trend line cannot tell "this rose because it is September" from "this rose because we fixed
it". Same-period-last-year controls for both: the comparison is the page against itself, one
year apart, at the same point in the calendar. It is the same control-cohort discipline the
growth engine already uses — a measurement without a control taught us that a +6,205-click
"win" was the World Cup, not us.

LIMITS, STATED
--------------
- Needs ~13 months of history. A page younger than that has no last-year to compare and is
  reported as such, never as "no season".
- One year of evidence is one year of evidence. A page that rose last September because of a
  one-off event will look seasonal. The output says how many clicks it is based on so a small
  number can be discounted.
- GSC caps at 16 months, so this can never look back two seasons. Stated, not worked around.

Usage:
  python3 build-season-radar.py                    # tools property
  python3 build-season-radar.py --site apps        # another property
  python3 build-season-radar.py --lead-days 30     # how far ahead to look
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

CFG = Path.home() / ".config" / "teamzlab"
PROJECTS = Path(__file__).resolve().parent.parent.parent

SITES = {
    "tools":   ("teamzlab-tools", "https://tool.teamzlab.com/"),
    "apps":    ("teamz-lab-generic-landing-pages", "https://apps.teamzlab.com/"),
    "learn":   ("teamz-lab-learning", "https://learn.teamzlab.com/"),
    "goalkit": ("goalkit-bd", "sc-domain:goalkit.teamzlab.com"),
}

# A page must have earned at least this many clicks in its last-year peak window before its
# pattern counts. Below it, a 3-click "season" is noise wearing a costume.
MIN_PEAK_CLICKS = int(os.getenv("TEAMZ_SEASON_MIN_CLICKS", "20"))
# How much busier the coming window has to be than the current one, last year, to call it a
# season rather than ordinary drift.
RISE_RATIO = float(os.getenv("TEAMZ_SEASON_RISE_RATIO", "2.0"))
# This year, a page is "already rising" if it has grown by at least this much versus its own
# preceding window. Below it, the season is starting without the page.
AWAKE_RATIO = float(os.getenv("TEAMZ_SEASON_AWAKE_RATIO", "1.3"))


def token():
    t = json.loads((CFG / "search-console-token.json").read_text())
    data = urllib.parse.urlencode({
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data),
        timeout=30))["access_token"]


def gsc(prop, tok, start, end, row_limit=25000):
    """{path: clicks} for one window. Raises on failure — an empty dict from a broken call
    would read as 'this page had no season', which is the lie this file must not tell."""
    body = json.dumps({"startDate": start.isoformat(), "endDate": end.isoformat(),
                       "dimensions": ["page"], "rowLimit": row_limit}).encode()
    url = ("https://www.googleapis.com/webmasters/v3/sites/"
           f"{urllib.parse.quote(prop, safe='')}/searchAnalytics/query")
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    out = {}
    for r in json.load(urllib.request.urlopen(req, timeout=180)).get("rows", []):
        p = r["keys"][0].split("teamzlab.com", 1)[-1] or "/"
        out[p] = out.get(p, 0.0) + r["clicks"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="tools", choices=sorted(SITES))
    ap.add_argument("--lead-days", type=int, default=30,
                    help="how far ahead the 'coming' window starts (default 30)")
    ap.add_argument("--window", type=int, default=28)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    repo, prop = SITES[args.site]
    tok = token()
    today = date.today()
    W = args.window
    YEAR = 364          # whole weeks, so weekday effects line up

    # Last year: the window we are ABOUT to enter, and the one we are in now.
    ly_coming_end = today + timedelta(days=args.lead_days) - timedelta(days=YEAR)
    ly_coming = (ly_coming_end - timedelta(days=W - 1), ly_coming_end)
    ly_now_end = today - timedelta(days=3) - timedelta(days=YEAR)
    ly_now = (ly_now_end - timedelta(days=W - 1), ly_now_end)
    # This year: the current window and the one before it.
    ty_now_end = today - timedelta(days=3)
    ty_now = (ty_now_end - timedelta(days=W - 1), ty_now_end)
    ty_prev_end = ty_now[0] - timedelta(days=1)
    ty_prev = (ty_prev_end - timedelta(days=W - 1), ty_prev_end)

    try:
        a = gsc(prop, tok, *ly_coming)   # last year, the season we are approaching
        b = gsc(prop, tok, *ly_now)      # last year, this time of year
        c = gsc(prop, tok, *ty_now)      # this year, now
        d = gsc(prop, tok, *ty_prev)     # this year, just before now
    except Exception as e:  # noqa: BLE001
        print(f"season-radar: UNREACHABLE — Search Console failed ({type(e).__name__}). "
              "No verdict this run.", file=sys.stderr)
        return 1

    # NO LAST YEAR = NO VERDICT. This must never print "0 pages asleep", which reads as
    # "checked, all fine". Measured 2026-08-14 on tool.teamzlab.com:
    #
    #     2026-01-19..02-15      0 clicks
    #     2026-02-18..03-17      3
    #     2026-03-20..04-16    259
    #     2026-04-19..05-16    763
    #     2026-05-19..06-15  3,031
    #     2026-06-18..07-15 14,307
    #     2026-07-18..08-14 38,378
    #
    # The property had no Google traffic at all before roughly February 2026. There IS no last
    # year to compare against on any property here, so this radar cannot return a real answer
    # until the first full cycle completes — around February 2027 for tools. Saying that plainly
    # is the entire job; a silent zero here would be indistinguishable from "nothing seasonal is
    # asleep", which is the failure mode this whole monitoring layer exists to prevent.
    ly_total = sum(a.values()) + sum(b.values())
    if ly_total < MIN_PEAK_CLICKS:
        print(f"season-radar [{args.site}]: NO VERDICT — only {int(ly_total)} click(s) exist in "
              f"the last-year comparison windows ({ly_now[0]}..{ly_coming[1]}). This property has "
              f"no season to compare against yet.")
        print(f"    This year, same window: {int(sum(c.values()))} clicks. The site is younger "
              f"than one seasonal cycle.")
        print(f"    Earliest useful run: about {ty_now[1].replace(year=ty_now[1].year + 1)}.")
        (PROJECTS / repo / "data").mkdir(parents=True, exist_ok=True)
        (PROJECTS / repo / "data" / "season-radar.json").write_text(json.dumps({
            "generated_at": today.isoformat(), "site": args.site,
            "state": "no-last-year-data",
            "last_year_clicks_in_windows": int(ly_total),
            "this_year_clicks_now": int(sum(c.values())),
            "note": "Property has less than one full year of Search Console history. "
                    "Not 'no seasonal pages' — 'cannot tell yet'.",
        }, indent=2))
        return 0

    rising, asleep = [], []
    for path, peak in a.items():
        if peak < MIN_PEAK_CLICKS:
            continue
        base_ly = b.get(path, 0.0)
        # +1 keeps a page that was at zero last year from dividing by zero while still
        # letting a genuine 0 -> 200 jump register as a season.
        if peak / (base_ly + 1.0) < RISE_RATIO:
            continue
        now_ty, prev_ty = c.get(path, 0.0), d.get(path, 0.0)
        row = {"path": path, "last_year_peak": round(peak),
               "last_year_before": round(base_ly),
               "this_year_now": round(now_ty), "this_year_before": round(prev_ty),
               "lift_last_year": round(peak / (base_ly + 1.0), 1)}
        (rising if now_ty >= prev_ty * AWAKE_RATIO else asleep).append(row)

    asleep.sort(key=lambda r: -r["last_year_peak"])
    rising.sort(key=lambda r: -r["last_year_peak"])

    out_dir = PROJECTS / repo / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "season-radar.json").write_text(json.dumps({
        "generated_at": today.isoformat(),
        "site": args.site,
        "windows": {"last_year_coming": [x.isoformat() for x in ly_coming],
                    "last_year_now": [x.isoformat() for x in ly_now],
                    "this_year_now": [x.isoformat() for x in ty_now]},
        "thresholds": {"min_peak_clicks": MIN_PEAK_CLICKS, "rise_ratio": RISE_RATIO,
                       "awake_ratio": AWAKE_RATIO},
        "asleep": asleep, "rising": rising,
    }, indent=2))

    print(f"season-radar [{args.site}]: {len(asleep)} page(s) ASLEEP, {len(rising)} already rising"
          f"  (last year {ly_coming[0]}..{ly_coming[1]} vs {ly_now[0]}..{ly_now[1]})")
    if asleep:
        print(f"\n  ASLEEP — earned at this time LAST year, flat now:")
        for r in asleep[:args.top]:
            print(f"    {r['last_year_peak']:>6} clicks last yr ({r['lift_last_year']}x)  "
                  f"now {r['this_year_now']:>5}  {r['path'][:58]}")
    if rising:
        print(f"\n  RISING — season starting and the page is moving. Leave alone:")
        for r in rising[:5]:
            print(f"    {r['last_year_peak']:>6} clicks last yr  now {r['this_year_now']:>5}  "
                  f"{r['path'][:58]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
