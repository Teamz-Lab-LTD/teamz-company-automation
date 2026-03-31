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

History file: ``aso-rank-history.json`` — ``{"records": [{"date", "app_id", "keyword", "position"}]}``
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _teamz_config import load_runtime  # noqa: E402

from aso._aso_common import ensure_data_dir, itunes_search  # noqa: E402

_CFG = load_runtime(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py")
)

_WATCHLIST_NAME = "aso-rank-watchlist.json"
_HISTORY_NAME = "aso-rank-history.json"
_BEYOND_LIMIT = 201  # sentinel when app not in top N results


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


def cmd_record(app_id: str) -> int:
    wl_path, hist_path = _paths()
    wl = _load_json(wl_path, {"apps": {}})
    keywords = _keywords_for_app(wl, app_id)
    if not keywords:
        print(f"No keywords in watchlist for app_id {app_id}. Use --track to add some.", file=sys.stderr)
        return 1

    hist = _load_json(hist_path, {"records": []})
    records = hist.get("records")
    if not isinstance(records, list):
        records = []
    today = _today_iso()
    rows = []

    for kw in keywords:
        results = itunes_search(kw, limit=200)
        pos = _position_for_app(results, app_id)
        rec = {
            "date": today,
            "app_id": str(app_id),
            "keyword": kw,
            "position": pos,
        }
        records.append(rec)
        rows.append((kw, pos))

    hist["records"] = records
    _save_json(hist_path, hist)

    # table
    w_kw = max(len("keyword"), max(len(k) for k, _ in rows) if rows else 8)
    w_pos = max(len("position"), 3)
    print(f"{'keyword'.ljust(w_kw)}  {'position'.rjust(w_pos)}")
    print(f"{'-' * w_kw}  {'-' * w_pos}")
    for kw, pos in rows:
        disp = str(pos) if pos else "0 (not in top 200)"
        print(f"{kw.ljust(w_kw)}  {disp.rjust(w_pos) if pos else disp}")
    return 0


def _records_for_app(hist, app_id: str) -> List[dict]:
    records = hist.get("records")
    if not isinstance(records, list):
        return []
    aid = str(app_id)
    return [r for r in records if isinstance(r, dict) and str(r.get("app_id", "")) == aid]


def _group_sorted_by_time(recs: List[dict]) -> Dict[str, List[dict]]:
    """Group by keyword; each list sorted by date then list order."""
    by_kw = {}
    for i, r in enumerate(recs):
        kw = (r.get("keyword") or "").strip()
        if not kw:
            continue
        by_kw.setdefault(kw, []).append((r.get("date") or "", i, r))
    out: Dict[str, List[dict]] = {}
    for kw, items in by_kw.items():
        items.sort(key=lambda x: (x[0], x[1]))
        out[kw] = [x[2] for x in items]
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
    w_kw = max(len("keyword"), max(len(k) for k in grouped) if grouped else 8)
    w_pos = max(len("position"), len("prev"), 4)
    w_tr = max(len("trend"), 6)
    print(f"{'keyword'.ljust(w_kw)}  {'position'.rjust(w_pos)}  {'prev'.rjust(w_pos)}  {'trend'.ljust(w_tr)}")
    print(f"{'-' * w_kw}  {'-' * w_pos}  {'-' * w_pos}  {'-' * w_tr}")

    for kw in sorted(grouped.keys()):
        chain = grouped[kw]
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
        print(
            f"{kw.ljust(w_kw)}  {c_disp.rjust(w_pos)}  {str(p_disp).rjust(w_pos)}  {trend.ljust(w_tr)}"
        )
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
    for kw, chain in grouped.items():
        if len(chain) < 2:
            continue
        old = int(chain[-2].get("position") or 0)
        new = int(chain[-1].get("position") or 0)
        eff_old = _effective_rank(old)
        eff_new = _effective_rank(new)
        movement = eff_old - eff_new  # positive = improved (lower rank)
        movers.append((abs(movement), movement, kw, old, new))

    movers.sort(key=lambda x: (-x[0], x[2]))
    if not movers:
        print("Need at least two recordings per keyword to compute movers.")
        return 0

    w_kw = max(len("keyword"), max(len(x[2]) for x in movers))
    print(f"{'keyword'.ljust(w_kw)}  {'was':>6}  {'now':>6}  {'movement':>10}")
    print(f"{'-' * w_kw}  {'------'}  {'------'}  {'----------'}")
    for _, mov, kw, old, new in movers:
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


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="ASO keyword rank tracking (iTunes Search, top 200).")
    p.add_argument("--record", metavar="APP_ID", help="Record today's positions for all watched keywords")
    p.add_argument("--report", metavar="APP_ID", help="Show latest position and trend vs previous record")
    p.add_argument("--movers", metavar="APP_ID", help="Largest rank movements between last two recordings")
    p.add_argument("--track", nargs=2, metavar=("APP_ID", "KEYWORD"), help="Add a keyword to the watchlist")
    p.add_argument("--untrack", nargs=2, metavar=("APP_ID", "KEYWORD"), help="Remove a keyword from the watchlist")
    p.add_argument("--watchlist", action="store_true", help="List all apps and keywords")

    args = p.parse_args(argv)
    modes = sum(
        [
            args.record is not None,
            args.report is not None,
            args.movers is not None,
            args.track is not None,
            args.untrack is not None,
            args.watchlist,
        ]
    )
    if modes != 1:
        p.error("Specify exactly one of: --record, --report, --movers, --track, --untrack, --watchlist")

    if args.record is not None:
        return cmd_record(args.record)
    if args.report is not None:
        return cmd_report(args.report)
    if args.movers is not None:
        return cmd_movers(args.movers)
    if args.track is not None:
        return cmd_track(args.track[0], args.track[1])
    if args.untrack is not None:
        return cmd_untrack(args.untrack[0], args.untrack[1])
    return cmd_watchlist()


if __name__ == "__main__":
    raise SystemExit(main())
