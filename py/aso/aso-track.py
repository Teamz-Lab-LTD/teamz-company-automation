#!/usr/bin/env python3
"""
ASO rank tracking — record daily App Store search positions for watched keywords.

Uses the iTunes Search API (via ``itunes_search``) with ``limit=200``. Data lives under
``TEAMZ_DATA_DIR`` (default: ``teamz-company-automation/data/``).

Examples::

    python3 py/aso/aso-track.py --record 1234567890
    python3 py/aso/aso-track.py --report 1234567890
    python3 py/aso/aso-track.py --movers 1234567890
    python3 py/aso/aso-track.py --track 1234567890 "fitness tracker"
    python3 py/aso/aso-track.py --untrack 1234567890 "fitness tracker"
    python3 py/aso/aso-track.py --watchlist

Watchlist file: ``aso-rank-watchlist.json`` — ``{"apps": {"APP_ID": {"keywords": ["kw1"]}}}``

History file: ``aso-rank-history.json`` — ``{"records": [{"date", "app_id", "keyword", "position", "country"}]}``

Set ``TEAMZ_ASO_COUNTRIES`` to a comma-separated list (e.g. ``us,gb,de``). Default single country is the first code; use ``--countries-all`` to record every code in the list.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _teamz_config import load_runtime  # noqa: E402

from aso._aso_common import _get_json, ensure_data_dir, itunes_lookup, itunes_search  # noqa: E402

_CFG = load_runtime(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py")
)

_WATCHLIST_NAME = "aso-rank-watchlist.json"
_HISTORY_NAME = "aso-rank-history.json"
_BEYOND_LIMIT = 201  # sentinel when app not in top N results


def _parse_countries_env() -> List[str]:
    raw = os.getenv("TEAMZ_ASO_COUNTRIES", "us")
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    return parts or ["us"]


def _default_country() -> str:
    return _parse_countries_env()[0]


def _norm_country(rec: dict) -> str:
    c = (rec.get("country") or "").strip().lower()
    return c or "us"


def _multi_country_records(recs: List[dict]) -> bool:
    if not recs:
        return False
    seen = {_norm_country(r) for r in recs}
    return len(seen) > 1


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _paths():
    d = ensure_data_dir(_CFG)
    return d / _WATCHLIST_NAME, d / _HISTORY_NAME


def _load_json(path, default):
    if not path.exists():
        return json.loads(json.dumps(default))  # deep copy default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(default))


def _save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _position_for_app(results, app_id: str) -> int:
    aid = str(app_id).strip()
    for i, r in enumerate(results, start=1):
        tid = r.get("trackId")
        if tid is not None and str(tid) == aid:
            return i
    return 0


def _get_watchlist_apps(data) -> dict:
    apps = data.get("apps")
    if not isinstance(apps, dict):
        return {}
    return apps


def _keywords_for_app(data, app_id: str) -> List[str]:
    apps = _get_watchlist_apps(data)
    entry = apps.get(str(app_id))
    if not isinstance(entry, dict):
        return []
    kws = entry.get("keywords")
    if not isinstance(kws, list):
        return []
    out = []
    for k in kws:
        if isinstance(k, str) and k.strip():
            out.append(k.strip())
    return out


def cmd_record(app_id: str, country: str, countries_all: bool) -> int:
    wl_path, hist_path = _paths()
    wl = _load_json(wl_path, {"apps": {}})
    keywords = _keywords_for_app(wl, app_id)
    if not keywords:
        print(f"No keywords in watchlist for app_id {app_id}. Use --track to add some.", file=sys.stderr)
        return 1

    countries = _parse_countries_env() if countries_all else [country.strip().lower()]

    hist = _load_json(hist_path, {"records": []})
    records = hist.get("records")
    if not isinstance(records, list):
        records = []
    today = _today_iso()
    rows: List[tuple] = []

    for cc in countries:
        for kw in keywords:
            results = itunes_search(kw, country=cc, limit=200)
            pos = _position_for_app(results, app_id)
            rec = {
                "date": today,
                "app_id": str(app_id),
                "keyword": kw,
                "position": pos,
                "country": cc,
            }
            records.append(rec)
            rows.append((cc, kw, pos))

    hist["records"] = records
    _save_json(hist_path, hist)

    # table
    show_cc = len(countries) > 1
    w_kw = max(len("keyword"), max(len(k) for _, k, _ in rows) if rows else 8)
    w_pos = max(len("position"), 3)
    w_cc = max(len("country"), max(len(c) for c, _, _ in rows) if rows else 7)
    if show_cc:
        print(f"{'country'.ljust(w_cc)}  {'keyword'.ljust(w_kw)}  {'position'.rjust(w_pos)}")
        print(f"{'-' * w_cc}  {'-' * w_kw}  {'-' * w_pos}")
        for cc, kw, pos in rows:
            disp = str(pos) if pos else "0 (not in top 200)"
            print(f"{cc.ljust(w_cc)}  {kw.ljust(w_kw)}  {disp.rjust(w_pos) if pos else disp}")
    else:
        print(f"{'keyword'.ljust(w_kw)}  {'position'.rjust(w_pos)}")
        print(f"{'-' * w_kw}  {'-' * w_pos}")
        for _, kw, pos in rows:
            disp = str(pos) if pos else "0 (not in top 200)"
            print(f"{kw.ljust(w_kw)}  {disp.rjust(w_pos) if pos else disp}")
    return 0


def _records_for_app(hist, app_id: str) -> List[dict]:
    records = hist.get("records")
    if not isinstance(records, list):
        return []
    aid = str(app_id)
    return [r for r in records if isinstance(r, dict) and str(r.get("app_id", "")) == aid]


def _group_key(rec: dict) -> tuple:
    kw = (rec.get("keyword") or "").strip()
    return (kw, _norm_country(rec))


def _group_sorted_by_time(recs: List[dict]) -> Dict[tuple, List[dict]]:
    """Group by (keyword, country); each list sorted by date then list order."""
    by_key: Dict[tuple, list] = {}
    for i, r in enumerate(recs):
        kw = (r.get("keyword") or "").strip()
        if not kw:
            continue
        key = _group_key(r)
        by_key.setdefault(key, []).append((r.get("date") or "", i, r))
    out: Dict[tuple, List[dict]] = {}
    for key, items in by_key.items():
        items.sort(key=lambda x: (x[0], x[1]))
        out[key] = [x[2] for x in items]
    return out


def _trend_label(prev_pos: int, curr_pos: int) -> str:
    if prev_pos == curr_pos:
        return "stable"
    # Lower rank number is better. Entering chart from 0 = improvement.
    if prev_pos == 0 and curr_pos > 0:
        return "up"
    if prev_pos > 0 and curr_pos == 0:
        return "down"
    if curr_pos < prev_pos:
        return "up"
    if curr_pos > prev_pos:
        return "down"
    return "stable"


def cmd_report(app_id: str) -> int:
    _, hist_path = _paths()
    hist = _load_json(hist_path, {"records": []})
    recs = _records_for_app(hist, app_id)
    if not recs:
        print(f"No history for app_id {app_id}.", file=sys.stderr)
        return 1

    grouped = _group_sorted_by_time(recs)
    multi_cc = _multi_country_records(recs)
    w_kw = max(len("keyword"), max(len(k[0]) for k in grouped) if grouped else 8)
    w_pos = max(len("position"), len("prev"), 4)
    w_tr = max(len("trend"), 6)
    w_cc = max(len("country"), max(len(_norm_country(grouped[key][-1])) for key in grouped) if grouped else 2)
    if multi_cc:
        print(
            f"{'country'.ljust(w_cc)}  {'keyword'.ljust(w_kw)}  {'position'.rjust(w_pos)}  {'prev'.rjust(w_pos)}  {'trend'.ljust(w_tr)}"
        )
        print(f"{'-' * w_cc}  {'-' * w_kw}  {'-' * w_pos}  {'-' * w_pos}  {'-' * w_tr}")
    else:
        print(f"{'keyword'.ljust(w_kw)}  {'position'.rjust(w_pos)}  {'prev'.rjust(w_pos)}  {'trend'.ljust(w_tr)}")
        print(f"{'-' * w_kw}  {'-' * w_pos}  {'-' * w_pos}  {'-' * w_tr}")

    for key in sorted(grouped.keys(), key=lambda x: (x[1], x[0])):
        kw, cc = key[0], key[1]
        chain = grouped[key]
        last = chain[-1]
        curr = int(last.get("position") or 0)
        if len(chain) >= 2:
            prev = int(chain[-2].get("position") or 0)
            trend = _trend_label(prev, curr)
            p_disp = str(prev) if prev else "0"
        else:
            trend = "new"
            p_disp = "—"
        c_disp = str(curr) if curr else "0"
        if multi_cc:
            print(
                f"{cc.ljust(w_cc)}  {kw.ljust(w_kw)}  {c_disp.rjust(w_pos)}  {str(p_disp).rjust(w_pos)}  {trend.ljust(w_tr)}"
            )
        else:
            print(f"{kw.ljust(w_kw)}  {c_disp.rjust(w_pos)}  {str(p_disp).rjust(w_pos)}  {trend.ljust(w_tr)}")
    return 0


def _effective_rank(p: int) -> int:
    return p if p and p > 0 else _BEYOND_LIMIT


def cmd_movers(app_id: str) -> int:
    _, hist_path = _paths()
    hist = _load_json(hist_path, {"records": []})
    recs = _records_for_app(hist, app_id)
    if not recs:
        print(f"No history for app_id {app_id}.", file=sys.stderr)
        return 1

    grouped = _group_sorted_by_time(recs)
    movers = []
    for key, chain in grouped.items():
        kw, cc = key[0], key[1]
        if len(chain) < 2:
            continue
        old = int(chain[-2].get("position") or 0)
        new = int(chain[-1].get("position") or 0)
        eff_old = _effective_rank(old)
        eff_new = _effective_rank(new)
        movement = eff_old - eff_new  # positive = improved (lower rank)
        movers.append((abs(movement), movement, kw, cc, old, new))

    movers.sort(key=lambda x: (-x[0], x[3], x[2]))
    if not movers:
        print("Need at least two recordings per keyword to compute movers.")
        return 0

    multi_cc = _multi_country_records(recs)
    w_kw = max(len("keyword"), max(len(x[2]) for x in movers))
    w_cc = max(len("country"), max(len(x[3]) for x in movers))
    if multi_cc:
        print(f"{'country'.ljust(w_cc)}  {'keyword'.ljust(w_kw)}  {'was':>6}  {'now':>6}  {'movement':>10}")
        print(f"{'-' * w_cc}  {'-' * w_kw}  {'------'}  {'------'}  {'----------'}")
        for _, mov, kw, cc, old, new in movers:
            o = str(old) if old else "0"
            n = str(new) if new else "0"
            label = f"{mov:+d}" if mov else "0"
            print(f"{cc.ljust(w_cc)}  {kw.ljust(w_kw)}  {o:>6}  {n:>6}  {label:>10}")
    else:
        print(f"{'keyword'.ljust(w_kw)}  {'was':>6}  {'now':>6}  {'movement':>10}")
        print(f"{'-' * w_kw}  {'------'}  {'------'}  {'----------'}")
        for _, mov, kw, _, old, new in movers:
            o = str(old) if old else "0"
            n = str(new) if new else "0"
            label = f"{mov:+d}" if mov else "0"
            print(f"{kw.ljust(w_kw)}  {o:>6}  {n:>6}  {label:>10}")
    return 0


def cmd_track(app_id: str, keyword: str) -> int:
    wl_path, _ = _paths()
    wl = _load_json(wl_path, {"apps": {}})
    apps = _get_watchlist_apps(wl)
    aid = str(app_id)
    entry = apps.get(aid)
    if not isinstance(entry, dict):
        entry = {"keywords": []}
        apps[aid] = entry
    kws = entry.get("keywords")
    if not isinstance(kws, list):
        kws = []
        entry["keywords"] = kws
    kw = keyword.strip()
    if kw in kws:
        print(f"Already tracking {kw!r} for {aid}.")
    else:
        kws.append(kw)
        wl["apps"] = apps
        _save_json(wl_path, wl)
        print(f"Added {kw!r} for app_id {aid}.")
    return 0


def cmd_untrack(app_id: str, keyword: str) -> int:
    wl_path, _ = _paths()
    wl = _load_json(wl_path, {"apps": {}})
    apps = _get_watchlist_apps(wl)
    aid = str(app_id)
    entry = apps.get(aid)
    if not isinstance(entry, dict):
        print(f"No watchlist entry for app_id {aid}.", file=sys.stderr)
        return 1
    kws = entry.get("keywords")
    if not isinstance(kws, list):
        kws = []
    kw = keyword.strip()
    if kw not in kws:
        print(f"Keyword {kw!r} not in watchlist for {aid}.", file=sys.stderr)
        return 1
    entry["keywords"] = [k for k in kws if k != kw]
    wl["apps"] = apps
    _save_json(wl_path, wl)
    print(f"Removed {kw!r} for app_id {aid}.")
    return 0


def cmd_watchlist() -> int:
    wl_path, _ = _paths()
    wl = _load_json(wl_path, {"apps": {}})
    apps = _get_watchlist_apps(wl)
    if not apps:
        print("Watchlist is empty. Use --track APP_ID \"keyword\" to add.")
        return 0
    for aid in sorted(apps.keys(), key=lambda x: str(x)):
        entry = apps.get(aid)
        kws = []
        if isinstance(entry, dict):
            raw = entry.get("keywords")
            if isinstance(raw, list):
                kws = [k for k in raw if isinstance(k, str) and k.strip()]
        print(f"app_id {aid}:")
        if not kws:
            print("  (no keywords)")
        else:
            for k in kws:
                print(f"  - {k}")
    return 0


def cmd_category(app_id: str, country: str) -> int:
    """Check app's position in its category top chart via Apple RSS."""
    rec = itunes_lookup(app_id, country=country)
    if not rec:
        print(f"Lookup failed for app_id {app_id}.", file=sys.stderr)
        return 1

    genre_id = rec.get("primaryGenreId")
    genre_name = rec.get("primaryGenreName", "Unknown")
    app_name = rec.get("trackName", str(app_id))
    track_id = str(rec.get("trackId", app_id))

    if not genre_id:
        print(f"No primaryGenreId found for {app_name}.", file=sys.stderr)
        return 1

    price = rec.get("price", 0)
    chart = "topfreeapplications" if price == 0 else "toppaidapplications"
    url = f"https://itunes.apple.com/{country}/rss/{chart}/genre={genre_id}/limit=200/json"
    data = _get_json(url)
    if not data:
        print(f"Could not fetch category chart for genre {genre_id}.", file=sys.stderr)
        return 1

    entries = (data.get("feed") or {}).get("entry") or []
    if not isinstance(entries, list):
        entries = [entries] if entries else []

    position = 0
    for i, entry in enumerate(entries, start=1):
        eid_obj = entry.get("id") or {}
        eid = str((eid_obj.get("attributes") or {}).get("im:id", "")) if isinstance(eid_obj, dict) else ""
        if eid == track_id:
            position = i
            break

    if position:
        print(f"App: {app_name} | Category: {genre_name} | Position: #{position}")
    else:
        print(f"App: {app_name} | Category: {genre_name} | Position: Not in top 200")

    _, hist_path = _paths()
    hist = _load_json(hist_path, {"records": []})
    records = hist.get("records")
    if not isinstance(records, list):
        records = []
    records.append({
        "date": _today_iso(),
        "app_id": str(app_id),
        "keyword": f"category:{genre_name}",
        "position": position,
        "country": country,
        "type": "category",
        "genre_id": genre_id,
        "genre_name": genre_name,
    })
    hist["records"] = records
    _save_json(hist_path, hist)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="ASO keyword rank tracking (iTunes Search, top 200).")
    p.add_argument("--record", metavar="APP_ID", help="Record today's positions for all watched keywords")
    p.add_argument("--report", metavar="APP_ID", help="Show latest position and trend vs previous record")
    p.add_argument("--movers", metavar="APP_ID", help="Largest rank movements between last two recordings")
    p.add_argument("--track", nargs=2, metavar=("APP_ID", "KEYWORD"), help="Add a keyword to the watchlist")
    p.add_argument("--untrack", nargs=2, metavar=("APP_ID", "KEYWORD"), help="Remove a keyword from the watchlist")
    p.add_argument("--watchlist", action="store_true", help="List all apps and keywords")
    p.add_argument("--category", metavar="APP_ID", help="Check position in category top chart")
    p.add_argument("--experiment", nargs=2, metavar=("APP_ID", "CHANGE_DATE"), help="Before/after rank comparison around a metadata change (YYYY-MM-DD)")
    p.add_argument(
        "--country",
        default=None,
        metavar="CC",
        help="App Store country code for search (default: first value in TEAMZ_ASO_COUNTRIES, else us)",
    )
    p.add_argument(
        "--countries-all",
        action="store_true",
        help="With --record: record for every country in TEAMZ_ASO_COUNTRIES (comma-separated)",
    )

    args = p.parse_args(argv)
    modes = sum(
        [
            args.record is not None,
            args.report is not None,
            args.movers is not None,
            args.track is not None,
            args.untrack is not None,
            args.watchlist,
            args.category is not None,
            getattr(args, "experiment", None) is not None,
        ]
    )
    if modes != 1:
        p.error("Specify exactly one of: --record, --report, --movers, --track, --untrack, --watchlist, --category")

    if args.countries_all and args.record is None:
        p.error("--countries-all is only valid with --record")

    record_country = (args.country or _default_country()).strip().lower()

    if args.record is not None:
        return cmd_record(args.record, record_country, args.countries_all)
    if args.report is not None:
        return cmd_report(args.report)
    if args.movers is not None:
        return cmd_movers(args.movers)
    if args.track is not None:
        return cmd_track(args.track[0], args.track[1])
    if args.untrack is not None:
        return cmd_untrack(args.untrack[0], args.untrack[1])
    if args.category is not None:
        return cmd_category(args.category, record_country)
    if getattr(args, "experiment", None) is not None:
        return cmd_experiment(args.experiment[0], args.experiment[1])
    return cmd_watchlist()


def cmd_experiment(app_id: str, change_date: str):
    """Compare rank positions before vs after a metadata change date."""
    _, hist_path = _paths()
    history = _load_history(hist_path)
    records = [r for r in history.get("records", []) if str(r.get("app_id")) == str(app_id)]
    if not records:
        print(f"No rank history for app {app_id}. Run --record first.", file=sys.stderr)
        return 1

    before = [r for r in records if r.get("date", "") < change_date]
    after = [r for r in records if r.get("date", "") >= change_date]
    if not before:
        print(f"No records before {change_date}.", file=sys.stderr)
        return 1
    if not after:
        print(f"No records after {change_date} yet — keep running --record daily.", file=sys.stderr)
        return 1

    def avg_pos(recs):
        by_kw = {}
        for r in recs:
            kw = r.get("keyword", "")
            pos = r.get("position", 0)
            by_kw.setdefault(kw, []).append(pos if pos > 0 else _BEYOND_LIMIT)
        return {kw: sum(ps) / len(ps) for kw, ps in by_kw.items()}

    before_avg = avg_pos(before)
    after_avg = avg_pos(after)
    all_kws = sorted(set(before_avg) | set(after_avg))

    print(f"\n  ASO Experiment: app {app_id}")
    print(f"  Change date: {change_date}")
    print(f"  Before: {len(before)} records | After: {len(after)} records\n")
    print(f"  {'Keyword':<35} {'Before':>8} {'After':>8} {'Change':>8}")
    print("  " + "-" * 63)
    improved = 0
    declined = 0
    for kw in all_kws:
        b = before_avg.get(kw, _BEYOND_LIMIT)
        a = after_avg.get(kw, _BEYOND_LIMIT)
        delta = b - a
        sign = "+" if delta > 0 else ""
        if delta > 0.5:
            improved += 1
        elif delta < -0.5:
            declined += 1
        b_str = f"{b:.0f}" if b < _BEYOND_LIMIT else "N/A"
        a_str = f"{a:.0f}" if a < _BEYOND_LIMIT else "N/A"
        d_str = f"{sign}{delta:.1f}" if b < _BEYOND_LIMIT and a < _BEYOND_LIMIT else "—"
        print(f"  {kw:<35} {b_str:>8} {a_str:>8} {d_str:>8}")

    print(f"\n  Summary: {improved} improved, {declined} declined, {len(all_kws) - improved - declined} stable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
