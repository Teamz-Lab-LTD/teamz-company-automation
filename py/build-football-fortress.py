#!/usr/bin/env python3
"""
build-football-fortress.py — displacement alarm for the pages that pay the bills.

WHY THIS EXISTS
---------------
/football/premier-league-table-predictor/ earned GBP 100.37 of a GBP 228.36 month — 44% of the
entire AdSense account from one URL — and nothing watched its position. The rank watchlist held
64 care-home keywords; the newest football row in rank-history.json was 2026-06-25, three weeks
before the page was even built. The first sign of losing the top spot would have been a Google
screenshot.

build-rank-tracker.py records positions. It does not judge them: `movers` prints the biggest
changes site-wide, where a 30-position swing on a dead calculator buries a 2-position slide on
the page that pays for everything. This script judges ONLY the fortress terms, and only the ways
they actually fail.

WHAT IT ALERTS ON (each rule exists because the cheap version of it is wrong)
----------------------------------------------------------------------------
1. SLIPPING — position worse than its own best by more than SLIP_TOLERANCE. Measured against the
   term's own history, not a fixed target, because "good" differs per term: pos 5 is a win on
   'premier league table predictor' and a loss on 'ucl bracket predictor' (best 1.9).
2. OFF PAGE ONE — position worse than 10 on a term that was previously on page one. Page two is
   revenue zero regardless of how gentle the slide was.
3. VANISHED — a term with recorded history that returned no row at all today. A page that stops
   appearing does not slip gradually; it disappears. Absence must be louder than a bad number,
   never quieter (see the monitor-must-not-lie rule).

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
- It does not alert on terms with no history. The four gap leagues (Europa, Ligue 1,
  Championship, Conference) are tracked deliberately at zero to baseline them BEFORE building.
  Alerting on those would fire every night forever and train the reader to ignore the whole
  section — the failure mode that let 74 nights of repeated alerts go unread.
- It does not alert on a single bad day. GSC positions are noisy and get revised; a term must be
  worse for CONSECUTIVE_DAYS consecutive recorded days before it counts. One bad Tuesday is not
  a competitor taking your spot.
- It does not treat "absent from the snapshot" as "gone from Google". build-rank-tracker.py does
  NOT query the watchlist: it pulls Search Console's top 500 rows by clicks for a 2-day window
  and records whatever comes back. A term outside that top 500 — an off-season UCL query, say —
  is simply unrecorded. Reading that as displacement is how a monitor starts lying. A term is
  only judged VANISHED once it has been seen in this series at least once and then dropped out.

OUTPUT
------
data/football-fortress.json — full judged state for /growth to render.
stdout — human summary; `ERROR:` prefix + exit 1 when something is actually wrong, which is what
nightly-build.sh greps to raise a health alert.

  python3 build-football-fortress.py            # judge, write state, alert
  python3 build-football-fortress.py --report   # print current state, never exit non-zero
"""
import importlib.util
import json
import re
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _teamz_config import load_runtime  # noqa: E402

_CFG = load_runtime(__file__)
DATA_DIR = _CFG["data_dir"]
HISTORY_FILE = DATA_DIR / "rank-history.json"
OUT_FILE = Path("data/football-fortress.json")
SITE_URL = _CFG["site_url"]

# Search Console window. Positions for the most recent ~2 days are still settling, so the
# window ends at D-3 — the same lag build-rank-tracker.py uses.
LAG_DAYS = 3
WINDOW_DAYS = 7

# The series is re-fetched over the whole window every night rather than appended to once, so
# Search Console's own revisions to a day's position land in the record instead of being frozen
# at whatever the first read said.
SERIES_KIND = "daily-v2"


def _rank_tracker():
    """Import build-rank-tracker.py for its token refresh and query helpers.

    The filename has hyphens, so a plain import is impossible. Reusing its two functions is
    deliberate: a second copy of the OAuth refresh is a second thing to break silently.
    """
    path = Path(__file__).resolve().parent / "build-rank-tracker.py"
    spec = importlib.util.spec_from_file_location("_teamz_rank_tracker", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _term_filter(terms):
    """Restrict the query to the fortress's own terms.

    The unfiltered version asked for the site's top 25,000 rows and picked its terms out of the
    answer. That is survivable for one row per query; it is not survivable once `date` is a
    dimension, because the row count multiplies by the window length and a fortress term can be
    truncated off the end of the answer. A missing row reads as zero impressions, which reads as
    VANISHED — an alert manufactured by a row limit. Ask only for what is judged.
    """
    pattern = "^(" + "|".join(re.escape(t.lower()) for t in sorted(set(terms))) + ")$"
    return [{"dimension": "query", "operator": "includingRegex", "expression": pattern}]


def fetch_positions(terms, window_days=None):
    """Exact position per fortress term PER DAY, straight from Search Console.

    This does NOT reuse rank-history.json's snapshot. That snapshot is Search Console's top 500
    rows by clicks, so an off-season term falls out of it for lack of clicks and looks identical
    to a term Google actually dropped. Asking for our own terms removes the ambiguity: a term
    absent from a 25,000-row answer really did get zero impressions.

    Returns (positions dict, error string or None). An error is never rendered as "no data" —
    the caller must treat it as unknown, not as healthy.
    """
    try:
        rt = _rank_tracker()
    except Exception as e:  # noqa: BLE001 - any import failure means we cannot judge
        return None, f"could not load build-rank-tracker.py helpers: {e}"

    token = rt.refresh_token()
    if not token:
        return None, "Search Console token missing or refresh failed"

    span = WINDOW_DAYS if window_days is None else window_days
    end = (datetime.now() - timedelta(days=LAG_DAYS)).strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=LAG_DAYS + span)).strftime("%Y-%m-%d")
    try:
        result = rt.sc_query(token, start, end, ["date", "query", "page"], 25000,
                             filters=_term_filter(terms))
    except Exception as e:  # noqa: BLE001
        return None, f"Search Console query failed: {e}"
    if result is None:
        return None, "Search Console query returned nothing"

    rows = result.get("rows", [])
    if not rows:
        return None, f"Search Console returned 0 rows for {start}..{end}"

    wanted = {t.lower() for t in terms}
    by_day = {}
    for row in rows:
        day, kw, page = row["keys"][0], row["keys"][1].lower(), row["keys"][2]
        if kw not in wanted:
            continue
        pos = round(row.get("position", 100), 1)
        per = by_day.setdefault(kw, {})
        prev = per.get(day)
        if prev is None or pos < prev["pos"]:
            per[day] = {"pos": pos, "page": page.replace(SITE_URL, "/"),
                        "clicks": row.get("clicks", 0), "imps": row.get("impressions", 0)}

    # Only days Search Console actually answered for. Filling the calendar instead would record a
    # None for every term on a day GSC has not published yet, and CONSECUTIVE_DAYS of manufactured
    # Nones is indistinguishable from the whole site being delisted. Absence must be observed,
    # never assumed.
    days = sorted({row["keys"][0] for row in rows})
    return {"window": f"{start}..{end}", "rows": len(rows),
            "by_day": by_day, "days": days}, None

SLIP_TOLERANCE = 3.0      # positions worse than own best before it counts as slipping
PAGE_ONE = 10.0           # worse than this is page two — revenue zero
# Three REAL days. Until 2026-08-24 each recorded point was an 8-day Search Console mean taken
# once a night, so "2 checks running" meant two heavily-overlapping averages and a short
# displacement was smoothed below the alert threshold before it was ever judged: the crown term
# 'premier league predictor' sat at pos 6.3/7.4/7.1 on 18-20 Aug against a 2.3 best and the
# fortress reported OK, because the mean over the surrounding window was only 5.3 vs 3.9.
CONSECUTIVE_DAYS = 3      # a term must be bad this many recorded DAYS running
# Below this many impressions in the window, a position is not a measurement. GSC averages
# position only over searches where you actually appeared, so a term drawing 1-4 impressions
# swings between 14 and 26 on nothing. 'bundesliga tabellenrechner' fired SLIPPING on 6
# impressions in 28 days; the daily series showed three days of data. Alerting on that is how a
# whole alert section teaches its reader to ignore it.
MIN_IMPRESSIONS = 30

# The same noise rule, applied to the OTHER side of the comparison. MIN_IMPRESSIONS guards the
# position being judged; nothing guarded the position it is judged AGAINST, so a single-impression
# day could install a permanent yardstick no real traffic would ever match again. Measured after
# the daily rewrite: 'champions league simulator' best 4.0 set on 1 impression (best on a real day
# is 6.8), 'champions league predictor' 2.0 on 1 impression (real 4.7), 'ucl predictor' 1.0 on 1
# impression (real 3.3). The first of those was already firing SLIPPING against a number that
# never happened. A day must carry this many impressions before it can define "best".
BEST_MIN_IMPRESSIONS = 10
# Bumped when the rule for what may set a best changes, so a stored map computed under the old
# rule is recomputed rather than carried forward as a floor that can only ever get better.
BEST_KIND = "impr-floor-v1"


def best_from_series(entries):
    """Lowest position from days that actually carried traffic. None if no day qualifies."""
    got = [e["pos"] for e in entries
           if e.get("pos") is not None and (e.get("imps") or 0) >= BEST_MIN_IMPRESSIONS]
    return min(got) if got else None


# ---------------------------------------------------------------------------
# JUDGING IN THE UNIT THAT PAYS
#
# Position gap alone is the wrong unit, and it cost real money here. Measured on
# this site's own crown terms: position 2 carries 27-48% CTR, position 5 carries
# 12-16%, position 15 carries ~1%. So 2.0 -> 5.0 loses ~60% of the clicks while
# 12.0 -> 15.0 loses almost nothing, and an ABSOLUTE tolerance calls those two
# the same event.
#
# SLIP_TOLERANCE was 3.0. On 2026-08-28 'premier league predictor' — the single
# biggest money term on the site — sat at pos 5.0 against a best of 2.0. A gap of
# exactly 3.0, which is not > 3.0, so the fortress printed OK while the term shed
# ~156 clicks/day. Missed by 0.03 positions. Meanwhile the one term it DID alert
# on, 'ucl predictor', had improved its CTR.
#
# The fix is to judge in clicks:
#     lost/day = impressions/day now  x  (best sustained CTR - CTR now)
# It self-scales, so the noise rule becomes structural rather than a threshold: a
# term drawing 4 impressions cannot produce a big number however far it falls.
# Both inputs are already recorded per day in this file's own series.
DAY_MIN_IMPRESSIONS = 25   # below this a day is a rounding error, not a measurement
CTR_BASE_WINDOW = 3        # "best sustained CTR" = best 3-day median, never one lucky day
LOST_CLICKS_ALERT = 20.0   # clicks/day, sustained, before one term alerts on its own
LOST_CLICKS_FLOOR = 8.0    # a position slip must also cost this much to be worth saying
CROWN_LOST_ALERT = 40.0    # clicks/day summed across the crown terms


def slip_tolerance(best):
    """Positions of slack before a term counts as slipping, scaled to where it sits.

    One place off a #2 is a different event from one place off a #15; a flat number
    cannot express that. Half the best position, never tighter than a full place —
    Search Console's daily average wobbles by a few tenths on its own.
    """
    return max(1.0, best * 0.5)


def estimate_click_loss(entries):
    """Clicks/day this term is losing against its own best sustained CTR.

    Returns None when the record cannot support the estimate — never 0.0. "No
    measurement" and "no loss" reading alike is exactly how a monitor starts lying,
    and this file has that lesson written into three other guards already.
    """
    days = [e for e in entries
            if (e.get("imps") or 0) >= DAY_MIN_IMPRESSIONS and e.get("pos") is not None]
    if len(days) < CONSECUTIVE_DAYS + CTR_BASE_WINDOW:
        return None

    def ctr(e):
        return (e.get("clicks") or 0) / e["imps"]

    recent, hist = days[-CONSECUTIVE_DAYS:], days[:-CONSECUTIVE_DAYS]
    rolls = [statistics.median([ctr(x) for x in hist[i:i + CTR_BASE_WINDOW]])
             for i in range(len(hist) - CTR_BASE_WINDOW + 1)]
    if not rolls:
        return None
    # 75th percentile of the rolling medians, NOT the maximum.
    #
    # The max is one good week wide. Measured 2026-08-28 on the sibling page-level
    # check, /games/arrow-escape-3d/ was reported "bleeding ~15 clicks/day" purely
    # because a spike (CTR 2.59% against a normal 1.72%) had set the bar; against a
    # longer baseline its CTR was slightly ABOVE normal. A bar a page can never
    # clear again produces a guaranteed nightly alert, which is worse than no alert.
    #
    # Same effect inside this file: 'football inflation calculator' had a max-roll
    # of 16.9% against a median of 3.7%, and 'premier league table calculator' 3.2%
    # against 0.0%. P75 keeps a genuinely good-but-normal week as the yardstick while
    # discarding the one-off. The real losses are untouched by the change —
    # 'premier league predictor' 156 -> 134 clicks/day, still enormous.
    base = (statistics.quantiles(rolls, n=4)[2] if len(rolls) > 3
            else statistics.median(rolls))
    now = statistics.median([ctr(e) for e in recent])
    imps = statistics.median([e["imps"] for e in recent])
    return {"base_ctr": round(base, 4), "now_ctr": round(now, 4),
            "imps_day": int(round(imps)), "lost_day": round(imps * (base - now), 1)}

# The terms that carry money, grouped so the alert can say WHICH asset is under threat.
# Crown terms are the ones the 44%-of-revenue page ranks for. Sibling and UCL terms are
# real but smaller. Gap terms are tracked at zero on purpose and never alert (see docstring).
FORTRESS = {
    "crown": [
        "premier league table predictor",
        "premier league predictor",
        "prem predictor",
        "pl predictor",
        "epl predictor",
        "prem table predictor",
        "predict the premier league table",
    ],
    "siblings": [
        "la liga table predictor",
        "serie a table predictor",
        "bundesliga table predictor",
        "bundesliga tabellenrechner",
    ],
    "ucl": [
        "champions league predictor",
        "ucl predictor",
        "ucl bracket predictor",
        "champions league simulator",
        "ucl clock",
    ],
    "other": [
        "football inflation calculator",
        "penalty shootout simulator",
    ],
    # Shipped 2026-08-21. Tracked from day one so the build can be judged by effect rather than
    # by the fact that it shipped — the lesson recorded against status:"built" in
    # data/event-calendar.json.
    # The calculator ships targeting queries the PREDICTOR already ranks 5.1-8.7 for. That is a
    # deliberate, owner-approved cannibalisation risk on a page worth 44% of the account, so both
    # sides are watched: these terms here, and the crown terms above. If the crown slips while
    # these rise, the trade went bad and the calculator should be noindexed.
    "calculator": [
        "premier league table calculator",
        "premier league calculator",
        "table calculator premier league",
    ],
    "championship": [
        "championship table predictor",
        "championship predictor",
        "efl championship predictor",
    ],
}
# Terms we have no page for. Tracked to baseline demand, never alerted on — a permanent alert
# on a deliberate gap is how a whole alert section gets ignored.
GAP_TERMS = [
    "europa league predictor",
    "ligue 1 table predictor",
    "conference league predictor",
    "champions league league phase predictor",
]


def load_state():
    """Previous fortress state, or an empty shell. Unreadable is not empty — the caller checks."""
    if not OUT_FILE.exists():
        return {"series": {}}, None
    try:
        st = json.loads(OUT_FILE.read_text())
        st.setdefault("series", {})
        return st, None
    except (json.JSONDecodeError, OSError) as e:
        return {"series": {}}, f"previous state at {OUT_FILE} is unreadable ({e})"


def seed_best_from_rank_history():
    """All-time best position per term, if the shared rank history has one.

    Only a seed. Once the fortress has its own series it judges from that, but on the first
    night there is no series and a term's own best is the only honest yardstick available.
    """
    if not HISTORY_FILE.exists():
        return {}
    try:
        hist = json.loads(HISTORY_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    out = {}
    for kw, info in (hist.get("keywords") or {}).items():
        if info.get("best_pos") is not None:
            out[kw.lower()] = float(info["best_pos"])
    return out


def _judge_position(keyword, series, seed_best, all_time_best=None):
    """Verdict for one term from the fortress's own recorded series (oldest first).

    `best` is floored by all_time_best, which only ever improves. Without that floor the yardstick
    is whatever the retained window happens to contain, so a term that never recovers drags its
    own "best" down with it and the alarm quietly agrees with the decline instead of reporting it.
    """
    kw = keyword.lower()
    all_time_best = all_time_best or {}
    if not series:
        return {"keyword": keyword, "state": "NO_DATA", "pos": None, "best": seed_best.get(kw),
                "page": None, "date": None, "why": "never recorded by this check yet"}

    latest = series[-1]
    latest_pos, latest_page, latest_date = latest.get("pos"), latest.get("page"), latest.get("date")

    seen = [e for e in series if e.get("pos") is not None]
    if not seen:
        # Tracked, but has never once appeared. A gap term being baselined before we build for
        # it looks exactly like this, and it is not a fault.
        return {"keyword": keyword, "state": "NO_DATA", "pos": None, "best": seed_best.get(kw),
                "page": None, "date": latest_date, "why": "no impressions recorded yet"}

    best = best_from_series(series)
    for floor in (seed_best.get(kw), all_time_best.get(kw)):
        if floor is not None:
            best = floor if best is None else min(best, floor)
    if best is None:
        # No day in the record carried enough traffic to define a yardstick. Report the position,
        # judge nothing against it — the alternative is inventing a best out of noise.
        return {"keyword": keyword, "state": "LOW_VOLUME", "pos": latest_pos, "best": None,
                "page": latest_page, "date": latest_date,
                "why": f"no day yet with {BEST_MIN_IMPRESSIONS}+ impressions to set a best from"}

    first_idx = next(i for i, e in enumerate(series) if e.get("pos") is not None)
    judgeable = series[first_idx:]
    recent = judgeable[-CONSECUTIVE_DAYS:]

    if len(recent) >= CONSECUTIVE_DAYS and all(e.get("pos") is None for e in recent):
        return {"keyword": keyword, "state": "VANISHED", "pos": None, "best": best,
                "page": seen[-1].get("page"), "date": latest_date,
                "why": f"zero impressions for {CONSECUTIVE_DAYS} checks running (best was {best})"}

    if latest_pos is None:
        return {"keyword": keyword, "state": "OK", "pos": None, "best": best,
                "page": seen[-1].get("page"), "date": latest_date, "why": "absent this check only"}

    graded = [e["pos"] for e in recent if e.get("pos") is not None]
    steady = len(graded) >= CONSECUTIVE_DAYS

    # Too little traffic to call anything. Reported, never alerted.
    imps = sum(e.get("imps") or 0 for e in recent)
    if imps < MIN_IMPRESSIONS:
        return {"keyword": keyword, "state": "LOW_VOLUME", "pos": latest_pos, "best": best,
                "page": latest_page, "date": latest_date,
                "why": f"only {imps} impressions in the window — position is noise, not a signal"}

    if latest_pos > PAGE_ONE and best <= PAGE_ONE and steady and all(p > PAGE_ONE for p in graded):
        return {"keyword": keyword, "state": "OFF_PAGE_ONE", "pos": latest_pos, "best": best,
                "page": latest_page, "date": latest_date,
                "why": f"pos {latest_pos} for {len(graded)} checks running; best {best}"}

    tol = slip_tolerance(best)
    if latest_pos - best > tol and steady and all(p - best > tol for p in graded):
        return {"keyword": keyword, "state": "SLIPPING", "pos": latest_pos, "best": best,
                "page": latest_page, "date": latest_date,
                "why": f"pos {latest_pos} vs best {best} (tolerance {tol:.1f}) "
                       f"for {len(graded)} checks running"}

    return {"keyword": keyword, "state": "OK", "pos": latest_pos, "best": best,
            "page": latest_page, "date": latest_date, "why": ""}


def judge(keyword, series, seed_best, all_time_best=None):
    """Position verdict, then overruled by the money verdict where they disagree.

    Order matters. A term can hold a respectable-looking position and still be
    bleeding — 'premier league table predictor' sits at pos 3.0 against a best of
    2.0, which no position rule would ever call a problem, while its CTR fell 49%
    -> 28% and took ~60 clicks a day with it. Position says where you are; clicks
    say what it is worth. Report the second one first.

    A LOW_VOLUME or NO_DATA verdict is never overruled: those mean the record
    cannot support a judgement, and inventing one on top is the failure this whole
    file exists to avoid.
    """
    v = _judge_position(keyword, series, seed_best, all_time_best)
    loss = estimate_click_loss(series)
    v["loss"] = loss

    if loss is None or v["state"] in ("LOW_VOLUME", "NO_DATA", "VANISHED", "OFF_PAGE_ONE"):
        return v

    if loss["lost_day"] >= LOST_CLICKS_ALERT:
        v["state"] = "BLEEDING"
        v["why"] = (f"losing ~{loss['lost_day']:.0f} clicks/day: CTR "
                    f"{loss['base_ctr'] * 100:.0f}% -> {loss['now_ctr'] * 100:.0f}% on "
                    f"{loss['imps_day']} impressions/day (pos {v['pos']}, best {v['best']})")
        return v

    if v["state"] == "SLIPPING" and loss["lost_day"] < LOST_CLICKS_FLOOR:
        # Ranks worse, costs nothing measurable. Worth recording, not worth waking
        # anyone at 23:55 — that is how an alert section teaches its reader to skip it.
        v["state"] = "OK"
        v["why"] = (f"pos {v['pos']} vs best {v['best']} but only ~{loss['lost_day']:.0f} "
                    f"clicks/day at stake — recorded, not alerted")
    return v


def main():
    argv = sys.argv[1:]
    report_only = "--report" in argv
    # One-time history load. The nightly window is 8 days, so on the night the daily series is
    # first built `best` can only be the best of those 8 days — and the yardstick a slip is
    # measured against would silently start out worse than the position the term actually held.
    # 'premier league predictor' sat at 2.3 on 11 Aug and 3.5 was the best inside the window.
    backfill_days = None
    if "--backfill" in argv:
        i = argv.index("--backfill")
        backfill_days = int(argv[i + 1]) if len(argv) > i + 1 else 90

    all_terms = [t for terms in FORTRESS.values() for t in terms] + GAP_TERMS
    state, state_err = load_state()
    series_map = state["series"]

    if report_only:
        seed_best = seed_best_from_rank_history()
        atb = state.get("all_time_best") or {}
        for group, terms in FORTRESS.items():
            for kw in terms:
                v = judge(kw, series_map.get(kw.lower(), []), seed_best, atb)
                # Show the cost, not only the rank. A dry run that prints the same
                # column the alert no longer judges on is a dry run of the old rule.
                lost = (v.get("loss") or {}).get("lost_day")
                cost = f"{lost:+7.1f} clicks/day" if lost is not None else "     no estimate"
                print(f"  {v['state']:18} {kw[:38]:38} pos={str(v['pos']):5} "
                      f"best={str(v['best']):5} {cost}")
        crown_lost = sum((judge(kw, series_map.get(kw.lower(), []), seed_best, atb)
                          .get("loss") or {}).get("lost_day", 0.0)
                         for kw in FORTRESS["crown"])
        print(f"\n  CROWN TOTAL: ~{crown_lost:.0f} clicks/day vs own best CTR "
              f"(alerts at {CROWN_LOST_ALERT:.0f})")
        return 0

    fetched, err = fetch_positions(all_terms, window_days=backfill_days)
    if err:
        # Cannot check is not the same as nothing wrong. Say which one this is.
        print(f"ERROR: football fortress could not be checked — {err}. "
              f"Positions are UNMONITORED tonight, not confirmed healthy.")
        return 1

    all_time_best = dict(state.get("all_time_best") or {})
    migrated = state.get("series_kind") != SERIES_KIND
    if migrated:
        # Every pre-existing entry is an 8-day Search Console mean stamped with the night it was
        # taken, not a day's position. Mixing those with true daily rows would compute `best` from
        # smoothed data and go on hiding the displacement this rewrite exists to catch, so the old
        # series is retired. Its minimum is kept as a floor first: the upgrade must not be able to
        # make any term look healthier than it already measured.
        for key, entries in series_map.items():
            cur = best_from_series(entries)
            if cur is not None:
                all_time_best[key] = min(cur, all_time_best[key]) if key in all_time_best else cur
        series_map = {}
        state["series"] = series_map
        state["series_kind"] = SERIES_KIND

    by_day, fetch_days = fetched["by_day"], set(fetched["days"])
    for kw in all_terms:
        key = kw.lower()
        # Drop every day this fetch covers and re-lay them from the answer, so Search Console's
        # later revisions to a day replace the first reading instead of being frozen beside it.
        entries = [e for e in series_map.get(key, []) if e.get("date") not in fetch_days]
        per = by_day.get(key, {})
        for day in fetched["days"]:
            r = per.get(day)
            entries.append({"date": day, "pos": r["pos"] if r else None,
                            "page": r["page"] if r else None,
                            "clicks": r["clicks"] if r else 0,
                            "imps": r["imps"] if r else 0})
        entries.sort(key=lambda e: e["date"])
        series_map[key] = entries[-120:]

    if state.get("best_kind") != BEST_KIND:
        # A stored map is only ever lowered, so one computed under a looser rule can never repair
        # itself. Recompute it from the daily record under the current rule instead of inheriting
        # three UCL floors that were each set by a single impression.
        all_time_best = {}
        state["best_kind"] = BEST_KIND

    for key, entries in series_map.items():
        cur = best_from_series(entries)
        if cur is not None:
            all_time_best[key] = min(cur, all_time_best[key]) if key in all_time_best else cur
    state["all_time_best"] = all_time_best

    seed_best = seed_best_from_rank_history()
    verdicts, problems = [], []
    for group, terms in FORTRESS.items():
        for kw in terms:
            v = judge(kw, series_map.get(kw.lower(), []), seed_best, all_time_best)
            v["group"] = group
            verdicts.append(v)
            if v["state"] not in ("OK", "NO_DATA", "LOW_VOLUME"):
                problems.append(v)

    gaps = []
    for kw in GAP_TERMS:
        per = by_day.get(kw.lower(), {})
        # A gap term is being baselined, so the question is "did it appear at all this window",
        # not "where was it last night". Take its best day and the window's total impressions.
        row = min(per.values(), key=lambda r: r["pos"]) if per else None
        gaps.append({"keyword": kw, "pos": row["pos"] if row else None,
                     "page": row["page"] if row else None,
                     "imps": sum(r["imps"] for r in per.values())})

    judged = [v for v in verdicts if v["state"] not in ("NO_DATA", "LOW_VOLUME")]
    state.update({
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "window": fetched["window"],
        "gsc_rows_scanned": fetched["rows"],
        "series_kind": SERIES_KIND,
        "best_kind": BEST_KIND,
        "days_in_window": len(fetched["days"]),
        "tracked": len(judged),
        "problems": len(problems),
        # One number for the whole earner: clicks/day the crown terms are shedding
        # against their own best CTR. The owner should never have to add up six rows
        # to find out whether the page that pays for everything is in trouble.
        "crown_lost_day": round(sum((v.get("loss") or {}).get("lost_day", 0.0)
                                    for v in verdicts if v.get("group") == "crown"), 1),
        "verdicts": verdicts,
        "gap_baseline": gaps,
        "series": series_map,
    })
    try:
        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(json.dumps(state, indent=2) + "\n")
    except OSError as e:
        print(f"  (could not write {OUT_FILE}: {e})")

    crown = [v for v in verdicts if v.get("group") == "crown" and v["pos"] is not None]
    if crown:
        b = min(crown, key=lambda v: v["pos"])
        print(f"  Fortress: {len(judged)} terms judged over {fetched['window']}; "
              f"best crown term '{b['keyword']}' at pos {b['pos']}")
    else:
        print(f"  Fortress: {len(judged)} terms judged over {fetched['window']}")

    for g in gaps:
        if g["pos"] is not None:
            print(f"  Gap term now ranking: '{g['keyword']}' pos {g['pos']} "
                  f"({g['imps']} impressions) -> {g['page']}")

    if state_err:
        print(f"  (note: {state_err} — series restarted)")
    if migrated:
        print(f"  (fortress series rebuilt as true daily positions; the previous 8-day means "
              f"were retired and their minima kept as the all-time-best floor. "
              f"{len(fetched['days'])} day(s) recorded so far — SLIPPING needs "
              f"{CONSECUTIVE_DAYS}.)")

    if backfill_days:
        # A backfill re-reads months of history in one go; judging it would grade today against a
        # window that is mostly not today. Load the record, report the floors, alert on nothing.
        print(f"  Backfilled {len(fetched['days'])} day(s) over {fetched['window']}. "
              f"All-time-best floors now: " +
              ", ".join(f"{k} {v}" for k, v in sorted(all_time_best.items())[:6]) + " ...")
        return 0

    crown_lost = state["crown_lost_day"]
    if crown_lost >= 1:
        print(f"  Crown page is shedding ~{crown_lost:.0f} clicks/day vs its own best CTR.")

    # A crown that bleeds without any single term crossing its own bar is still a
    # bleeding crown. Four terms losing 15/day each is 60/day gone and would have
    # been reported as "all holding" under a per-term-only rule.
    if not problems and crown_lost >= CROWN_LOST_ALERT:
        print(f"ERROR: crown page losing ~{crown_lost:.0f} clicks/day — no single term "
              f"crossed its own bar, but the terms together did. See data/football-fortress.json")
        return 1

    if not problems:
        print(f"  All {len(judged)} fortress terms holding.")
        return 0

    # Rank the alert by what it costs, not by how deep the position is. A term at
    # pos 18 drawing 17 impressions used to outrank a pos-5 term shedding 156
    # clicks/day, purely because 18 is a bigger number than 5.
    def cost(v):
        return (v.get("loss") or {}).get("lost_day", 0.0)

    worst = sorted(problems, key=lambda v: (v["state"] != "VANISHED", -cost(v), -(v["pos"] or 0)))
    lines = "; ".join(f"'{v['keyword']}' {v['state']} ({v['why']})" for v in worst[:3])
    money = f"~{crown_lost:.0f} clicks/day off the crown page — " if crown_lost >= 1 else ""
    print(f"ERROR: {money}{len(problems)} fortress term(s) under threat — {lines}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
