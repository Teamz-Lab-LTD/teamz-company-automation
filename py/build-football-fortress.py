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


def fetch_positions(terms):
    """Exact position per fortress term, straight from Search Console.

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

    end = (datetime.now() - timedelta(days=LAG_DAYS)).strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=LAG_DAYS + WINDOW_DAYS)).strftime("%Y-%m-%d")
    try:
        result = rt.sc_query(token, start, end, ["query", "page"], 25000)
    except Exception as e:  # noqa: BLE001
        return None, f"Search Console query failed: {e}"
    if result is None:
        return None, "Search Console query returned nothing"

    rows = result.get("rows", [])
    if not rows:
        return None, f"Search Console returned 0 rows for {start}..{end}"

    wanted = {t.lower() for t in terms}
    found = {}
    for row in rows:
        kw = row["keys"][0].lower()
        if kw not in wanted:
            continue
        pos = round(row.get("position", 100), 1)
        page = row["keys"][1].replace(SITE_URL, "/")
        prev = found.get(kw)
        if prev is None or pos < prev["pos"]:
            found[kw] = {"pos": pos, "page": page,
                         "clicks": row.get("clicks", 0), "imps": row.get("impressions", 0)}
    return {"window": f"{start}..{end}", "rows": len(rows), "found": found}, None

SLIP_TOLERANCE = 3.0      # positions worse than own best before it counts as slipping
PAGE_ONE = 10.0           # worse than this is page two — revenue zero
CONSECUTIVE_DAYS = 2      # a term must be bad this many recorded days running

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
}
GAP_TERMS = [
    "europa league predictor",
    "ligue 1 table predictor",
    "championship table predictor",
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


def judge(keyword, series, seed_best):
    """Verdict for one term from the fortress's own recorded series (oldest first)."""
    kw = keyword.lower()
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

    best = min(e["pos"] for e in seen)
    seed = seed_best.get(kw)
    if seed is not None:
        best = min(best, seed)

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

    if latest_pos > PAGE_ONE and best <= PAGE_ONE and steady and all(p > PAGE_ONE for p in graded):
        return {"keyword": keyword, "state": "OFF_PAGE_ONE", "pos": latest_pos, "best": best,
                "page": latest_page, "date": latest_date,
                "why": f"pos {latest_pos} for {len(graded)} checks running; best {best}"}

    if latest_pos - best > SLIP_TOLERANCE and steady and all(p - best > SLIP_TOLERANCE for p in graded):
        return {"keyword": keyword, "state": "SLIPPING", "pos": latest_pos, "best": best,
                "page": latest_page, "date": latest_date,
                "why": f"pos {latest_pos} vs best {best} for {len(graded)} checks running"}

    return {"keyword": keyword, "state": "OK", "pos": latest_pos, "best": best,
            "page": latest_page, "date": latest_date, "why": ""}


def main():
    argv = sys.argv[1:]
    report_only = "--report" in argv

    all_terms = [t for terms in FORTRESS.values() for t in terms] + GAP_TERMS
    state, state_err = load_state()
    series_map = state["series"]

    if report_only:
        seed_best = seed_best_from_rank_history()
        for group, terms in FORTRESS.items():
            for kw in terms:
                v = judge(kw, series_map.get(kw.lower(), []), seed_best)
                print(f"  {v['state']:18} {kw[:42]:42} pos={v['pos']} best={v['best']}")
        return 0

    fetched, err = fetch_positions(all_terms)
    if err:
        # Cannot check is not the same as nothing wrong. Say which one this is.
        print(f"ERROR: football fortress could not be checked — {err}. "
              f"Positions are UNMONITORED tonight, not confirmed healthy.")
        return 1

    today = datetime.now().strftime("%Y-%m-%d")
    found = fetched["found"]
    for kw in all_terms:
        key = kw.lower()
        entries = [e for e in series_map.get(key, []) if e.get("date") != today]
        row = found.get(key)
        entries.append({"date": today, "pos": row["pos"] if row else None,
                        "page": row["page"] if row else None,
                        "clicks": row["clicks"] if row else 0,
                        "imps": row["imps"] if row else 0})
        series_map[key] = entries[-90:]

    seed_best = seed_best_from_rank_history()
    verdicts, problems = [], []
    for group, terms in FORTRESS.items():
        for kw in terms:
            v = judge(kw, series_map.get(kw.lower(), []), seed_best)
            v["group"] = group
            verdicts.append(v)
            if v["state"] not in ("OK", "NO_DATA"):
                problems.append(v)

    gaps = []
    for kw in GAP_TERMS:
        row = found.get(kw.lower())
        gaps.append({"keyword": kw, "pos": row["pos"] if row else None,
                     "page": row["page"] if row else None,
                     "imps": row["imps"] if row else 0})

    judged = [v for v in verdicts if v["state"] != "NO_DATA"]
    state.update({
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "window": fetched["window"],
        "gsc_rows_scanned": fetched["rows"],
        "tracked": len(judged),
        "problems": len(problems),
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

    if not problems:
        print(f"  All {len(judged)} fortress terms holding.")
        return 0

    worst = sorted(problems, key=lambda v: (v["state"] != "VANISHED", -(v["pos"] or 999)))
    lines = "; ".join(f"'{v['keyword']}' {v['state']} ({v['why']})" for v in worst[:3])
    print(f"ERROR: {len(problems)} fortress term(s) under threat — {lines}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
