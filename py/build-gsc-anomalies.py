#!/usr/bin/env python3
"""
Google Search Console — URL + query anomaly alerts (free, uses existing SC token).

Compares two equal-length windows (default: last 7 days vs prior 7 days) on dimensions
page + query. Flags:
  - CTR drop (relative + minimum impression floors)
  - Impression spike / drop

Usage:
    python3 scripts/build-gsc-anomalies.py
    python3 scripts/build-gsc-anomalies.py --days 14          # 14d vs prior 14d
    python3 scripts/build-gsc-anomalies.py --json-only        # write JSON, minimal stdout
    python3 scripts/build-gsc-anomalies.py --min-impr 50      # raise noise floor

Output:
    TEAMZ_DATA_DIR/gsc-anomalies-latest.json (and dated copy)

Requires: TEAMZ_SC_TOKEN_FILE, TEAMZ_SITE_PROPERTY, TEAMZ_GOOGLE_CLOUD_PROJECT
"""

import argparse
import json
import ssl
import time
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from _teamz_config import load_runtime

_CTX = ssl.create_default_context()


def _refresh_token(token_path: Path, project: str) -> Optional[str]:
    if not token_path.exists():
        return None
    data = json.loads(token_path.read_text())
    body = urllib.parse.urlencode(
        {
            "client_id": data["client_id"],
            "client_secret": data["client_secret"],
            "refresh_token": data["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=_CTX)
        return json.loads(resp.read()).get("access_token")
    except Exception as e:
        print(f"ERROR: token refresh failed: {e}", file=sys.stderr)
        return None


def _sc_query(
    token: str,
    site_url: str,
    project: str,
    start: str,
    end: str,
    dimensions: list[str],
    row_limit: int = 25000,
    start_row: int = 0,
) -> List[dict]:
    encoded = urllib.parse.quote(site_url, safe="")
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query"
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": dimensions,
        "rowLimit": row_limit,
        "startRow": start_row,
        "dataState": "all",
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-goog-user-project", project)
    # RETRY, AND NEVER RETURN [] ON FAILURE.
    #
    # Two defects, both hit in production on 2026-08-29. This check died with
    # `TimeoutError: [Errno 60] Operation timed out` for the third night running and
    # took the crown-page bleed alert down with it, so the owner's only warning that
    # ~493 clicks/day were leaving the site simply did not fire. Nothing retried a
    # transient blip on a home Wi-Fi connection that is known to drop mid-run.
    #
    # Worse, the HTTPError branch returned an EMPTY LIST. _fetch_all_page_query breaks
    # its pagination loop on empty rows, so an API error produced a partial or empty
    # map, and an empty map has no anomalies in it. A failed fetch could therefore
    # print a clean bill of health. "Could not check" and "nothing wrong" must never
    # look alike — that confusion is the reason this whole monitoring layer exists.
    #
    # So: retry transient failures with backoff, and raise on real ones. main() already
    # exits non-zero, which nightly-build.sh records as a health alert. Loud beats wrong.
    last = None
    for attempt in range(4):
        try:
            resp = urllib.request.urlopen(req, context=_CTX, timeout=120)
            return json.loads(resp.read()).get("rows", [])
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:400]
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                last = f"HTTP {e.code}"
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"Search Console API {e.code}: {body}") from e
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as e:
            # The exact class that killed this check three nights running.
            last = f"{type(e).__name__}: {e}"
            if attempt < 3:
                print(f"  (Search Console {last} — retry {attempt + 1}/3)", file=sys.stderr)
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(
                f"Search Console unreachable after 4 attempts ({last}). Anomalies are "
                f"UNCHECKED tonight, not clean.") from e
    raise RuntimeError(f"Search Console unreachable ({last})")


def _fetch_all_page_query(
    token: str, site_url: str, project: str, start: str, end: str
) -> Dict[Tuple[str, str], dict]:
    """Map (page_url, query) -> {clicks, impressions, ctr, position}."""
    out: Dict[Tuple[str, str], dict] = {}
    start_row = 0
    batch = 25000
    while True:
        rows = _sc_query(token, site_url, project, start, end, ["page", "query"], batch, start_row)
        if not rows:
            break
        for row in rows:
            keys = row.get("keys") or []
            if len(keys) < 2:
                continue
            page, query = keys[0], keys[1]
            k = (page, query)
            out[k] = {
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": float(row.get("ctr", 0.0)),
                "position": float(row.get("position", 0.0)),
            }
        if len(rows) < batch:
            break
        start_row += batch
    return out


# A bleed row must have roughly the impressions it had before. Above this multiple
# the page is riding a demand surge, and CTR dilution there is not a loss.
HELD_IMPRESSIONS_MAX = 1.5

def _ctr(clicks: int, impressions: int) -> float:
    if impressions <= 0:
        return 0.0
    return clicks / impressions


def main() -> int:
    ap = argparse.ArgumentParser(description="GSC page+query anomaly detection")
    ap.add_argument("--days", type=int, default=7, help="Length of each comparison window (default 7)")
    ap.add_argument("--lag-days", type=int, default=3, help="End date offset for GSC data lag (default 3)")
    ap.add_argument("--min-impr", type=int, default=25, help="Minimum impressions in prior window to consider a row")
    ap.add_argument("--min-impr-recent", type=int, default=8, help="Minimum impressions in recent window for CTR alerts")
    ap.add_argument("--ctr-drop-ratio", type=float, default=0.65, help="Flag CTR if recent < prior * this (default 0.65)")
    ap.add_argument("--impr-drop-ratio", type=float, default=0.45, help="Flag if recent impr < prior * this")
    ap.add_argument("--impr-spike-ratio", type=float, default=2.0, help="Flag if recent impr > prior * this")
    ap.add_argument("--baseline-days", type=int, default=28,
                    help="Days of history the bleed ranking compares against (default 28). "
                         "Never shorten to one week: a single spike would set an unreachable bar.")
    ap.add_argument("--bleed-alert", type=float, default=10.0,
                    help="Alert when a PAGE loses this many clicks/day to CTR decline (default 10)")
    ap.add_argument("--json-only", action="store_true", help="Minimal console output")
    args = ap.parse_args()

    cfg = load_runtime(__file__)
    if cfg["project_type"] == "app":
        print("Skipped: TEAMZ_PROJECT_TYPE=app (website-only tooling).", file=sys.stderr)
        return 2

    token_path = cfg["sc_token_file"]
    site_url = cfg["site_property"]
    project = cfg["google_project"]
    data_dir: Path = cfg["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)

    token = _refresh_token(token_path, project)
    if not token:
        print("ERROR: Could not refresh Search Console token.", file=sys.stderr)
        return 1

    lag = max(0, args.lag_days)
    days = max(1, args.days)
    end_recent = datetime.now() - timedelta(days=lag)
    start_recent = end_recent - timedelta(days=days - 1)
    end_prior = start_recent - timedelta(days=1)
    start_prior = end_prior - timedelta(days=days - 1)

    rs, re = start_recent.strftime("%Y-%m-%d"), end_recent.strftime("%Y-%m-%d")
    ps, pe = start_prior.strftime("%Y-%m-%d"), end_prior.strftime("%Y-%m-%d")

    if not args.json_only:
        print("=" * 72)
        print(f"  GSC ANOMALIES — {site_url.rstrip('/')}")
        print(f"  Recent: {rs} .. {re}   vs   Prior: {ps} .. {pe}")
        print("=" * 72)

    if not args.json_only:
        print("\n  Fetching prior window (page + query)...")
    prior_map = _fetch_all_page_query(token, site_url, project, ps, pe)
    if not args.json_only:
        print(f"  Rows: {len(prior_map)}")
        print("  Fetching recent window (page + query)...")
    recent_map = _fetch_all_page_query(token, site_url, project, rs, re)
    if not args.json_only:
        print(f"  Rows: {len(recent_map)}")

    # A LONG baseline, used only by the bleed ranking below — never by the 7v7
    # anomaly rows, which have other readers.
    #
    # Why: on 2026-08-28 this check reported /games/arrow-escape-3d/ "bleeding ~15
    # clicks/day". It was not. The page had a traffic spike 11-18 Aug (CTR 2.59%
    # against a normal 1.72%), the 7-day prior window landed exactly on that spike,
    # and coming back down to normal was scored as a loss. Measured against 28 days
    # its CTR is 2.06% versus a 2.03% baseline — slightly ABOVE normal.
    #
    # A one-week baseline is one event wide. Any spike installs a bar the page can
    # never clear again, and the alert that follows is guaranteed and meaningless —
    # which is precisely how an alert section trains its reader to skip it. The
    # crown page still reports ~813 clicks/day against the longer baseline, so the
    # real signal does not need the short window to be visible.
    bstart = (end_prior - timedelta(days=max(days, args.baseline_days) - 1)).strftime("%Y-%m-%d")
    if not args.json_only:
        print(f"  Fetching {args.baseline_days}d baseline for bleed ranking ({bstart} .. {pe})...")
    baseline_map = _fetch_all_page_query(token, site_url, project, bstart, pe)
    if not args.json_only:
        print(f"  Rows: {len(baseline_map)}")

    keys = set(prior_map) | set(recent_map)
    ctr_alerts = []
    impr_drop = []
    impr_spike = []

    min_prior = args.min_impr
    min_rec = args.min_impr_recent
    ctr_ratio = args.ctr_drop_ratio
    drop_ratio = args.impr_drop_ratio
    spike_ratio = args.impr_spike_ratio

    for k in keys:
        page, query = k
        pr = prior_map.get(k, {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0})
        rc = recent_map.get(k, {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0})
        ip, ir = pr["impressions"], rc["impressions"]
        cp, cr = pr["clicks"], rc["clicks"]

        if ip >= min_prior and ir >= min_rec:
            p_ctr = _ctr(cp, ip)
            r_ctr = _ctr(cr, ir)
            if p_ctr >= 0.008 and r_ctr < p_ctr * ctr_ratio and r_ctr < p_ctr - 0.003:
                ctr_alerts.append(
                    {
                        "page": page,
                        "query": query,
                        "prior_clicks": cp,
                        "prior_impressions": ip,
                        "prior_ctr": round(p_ctr * 100, 3),
                        "recent_clicks": cr,
                        "recent_impressions": ir,
                        "recent_ctr": round(r_ctr * 100, 3),
                        "kind": "ctr_drop",
                    }
                )

        if ip >= min_prior:
            if ir < ip * drop_ratio:
                impr_drop.append(
                    {
                        "page": page,
                        "query": query,
                        "prior_impressions": ip,
                        "recent_impressions": ir,
                        "kind": "impression_drop",
                    }
                )
            elif ir > ip * spike_ratio and ip >= min_prior:
                impr_spike.append(
                    {
                        "page": page,
                        "query": query,
                        "prior_impressions": ip,
                        "recent_impressions": ir,
                        "kind": "impression_spike",
                    }
                )

    ctr_alerts.sort(key=lambda x: (-x["prior_impressions"], x["query"]))
    impr_drop.sort(key=lambda x: (-x["prior_impressions"], x["query"]))
    impr_spike.sort(key=lambda x: (-x["recent_impressions"], x["query"]))

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "site": site_url,
        "recent_start": rs,
        "recent_end": re,
        "prior_start": ps,
        "prior_end": pe,
        "window_days": days,
        "thresholds": {
            "min_prior_impressions": min_prior,
            "min_recent_impressions": min_rec,
            "ctr_drop_ratio": ctr_ratio,
            "impression_drop_ratio": drop_ratio,
            "impression_spike_ratio": spike_ratio,
        },
        "counts": {
            "prior_keys": len(prior_map),
            "recent_keys": len(recent_map),
            "ctr_drop": len(ctr_alerts),
            "impression_drop": len(impr_drop),
            "impression_spike": len(impr_spike),
        },
        "alerts": {"ctr_drop": ctr_alerts[:200], "impression_drop": impr_drop[:200], "impression_spike": impr_spike[:200]},
    }

    # ---------------------------------------------------------------------
    # RANK THE BLEED BY WHAT IT COSTS, AND SAY SO OUT LOUD.
    #
    # This check was already right and already running. On 2026-08-28 the row
    # for 'premier league predictor' — the biggest money term on the site, CTR
    # 21% -> 12% — was literally the FIRST entry in gsc-anomalies-latest.json,
    # and the owner still found out by asking a question, because the file also
    # held 454 other rows and the nightly runs this with --json-only. 455
    # undifferentiated rows is a database, not a monitor. Nothing ranked them,
    # so nothing could be delivered.
    #
    # Aggregating to the PAGE and sorting by estimated clicks lost per day turns
    # those 455 rows into 2 worth waking anyone for.
    #
    # Only CTR drops are alerted, never impression drops. An impression drop is
    # usually demand moving — the Premier League predictor's own August peak
    # halves on its own every September — and alerting on seasonality is how an
    # alert section teaches its reader to skip it. A CTR drop at held
    # impressions is the opposite: the searches are still there and something
    # else is now taking them. Impression rows stay in the JSON for diagnosis.
    baseline_days = max(days, args.baseline_days)
    by_page: Dict[str, dict] = {}
    for row in ctr_alerts:                      # full list, not the capped copy
        base = baseline_map.get((row["page"], row["query"]))
        if not base or base["impressions"] < min_prior:
            continue                            # no baseline -> no claim, never a zero
        base_ctr = base["clicks"] / base["impressions"] * 100.0

        # "AT HELD IMPRESSIONS" HAS TO BE TESTED, NOT JUST ASSERTED.
        #
        # 2026-08-31: this alerted that /football/ucl-group-stage-simulator/ was
        # "bleeding ~75 clicks/day (ucl simulator CTR 14%->4%)". Measured, that term
        # went 315 impressions / 34 clicks -> 5,405 impressions / 207 clicks. The UCL
        # draw landed on 28 Aug; impressions rose 17x and CLICKS ROSE 6x. CTR fell only
        # because the denominator exploded.
        #
        # The estimate below multiplies the CTR delta by RECENT impressions, so a
        # demand surge inflates a phantom loss in direct proportion to how well the
        # page is doing. The headline already promised "at held impressions" — it was
        # simply never checked. Two guards, in the order that makes the reasoning
        # obvious:
        #
        #   1. Clicks. A page cannot be bleeding clicks while receiving more of them.
        #      This is per-row and unarguable: compare like for like, per day.
        #   2. Held impressions. A large surge is a different event — new demand
        #      arriving at diluted CTR — and belongs in the impression-spike block,
        #      not in a bleed alert.
        #
        # Deliberately NOT widened into a "significance" heuristic. The Premier League
        # predictor's real loss the same night (impressions flat at 12,154 -> 12,312,
        # clicks 3,569 -> 1,948) passes both guards and still alerts, which is the
        # test that matters. See feedback_judge_rank_loss_in_clicks_not_positions.
        base_days = max(days, baseline_days)
        base_clicks_day = base["clicks"] / base_days
        recent_clicks_day = row["recent_clicks"] / days
        if recent_clicks_day >= base_clicks_day:
            continue                            # more clicks than baseline: not a bleed

        base_impr_day = base["impressions"] / base_days
        recent_impr_day = row["recent_impressions"] / days
        if base_impr_day > 0 and recent_impr_day > base_impr_day * HELD_IMPRESSIONS_MAX:
            continue                            # demand surged; not "held impressions"

        lost = row["recent_impressions"] * (base_ctr - row["recent_ctr"]) / 100.0 / days
        # Never claim more than the clicks actually lost against baseline.
        lost = min(lost, base_clicks_day - recent_clicks_day)
        if lost <= 0:
            continue
        e = by_page.setdefault(row["page"], {"page": row["page"], "lost_day": 0.0,
                                             "queries": 0, "worst": None})
        e["lost_day"] += lost
        e["queries"] += 1
        if e["worst"] is None or lost > e["worst"]["lost_day"]:
            e["worst"] = {"query": row["query"], "lost_day": round(lost, 1),
                          "prior_ctr": round(base_ctr, 2), "recent_ctr": row["recent_ctr"]}
    bleeding = sorted(by_page.values(), key=lambda e: -e["lost_day"])
    for e in bleeding:
        e["lost_day"] = round(e["lost_day"], 1)
    report["bleeding_pages"] = bleeding[:25]
    report["bleeding_total_day"] = round(sum(e["lost_day"] for e in bleeding), 1)
    report["bleed_alert_threshold_day"] = args.bleed_alert
    report["bleed_baseline_days"] = args.baseline_days

    over = [e for e in bleeding if e["lost_day"] >= args.bleed_alert]
    if over:
        # This line is what reaches the owner. nightly-build.sh's
        # extract_health_issue() greps the first /ERROR:/ out of a phase's
        # output and records it as a health alert, which growth-watchdog then
        # sends to email/WhatsApp at 23:55. It has to carry the number and the
        # page, because a count on its own ("3 anomalies") sent him into a
        # 49k-line log last time.
        head = "; ".join(
            f"{e['page'].rstrip('/').rsplit('/', 1)[-1] or '/'} ~{e['lost_day']:.0f} clicks/day"
            f" (worst: '{e['worst']['query']}' CTR {e['worst']['prior_ctr']:.0f}%"
            f"->{e['worst']['recent_ctr']:.0f}%)"
            for e in over[:3])
        print(f"ERROR: {len(over)} page(s) bleeding clicks at held impressions — {head}"
              + (f" (+{len(over) - 3} more)" if len(over) > 3 else ""))

    latest = data_dir / "gsc-anomalies-latest.json"
    dated = data_dir / f"gsc-anomalies-{datetime.now().strftime('%Y-%m-%d')}.json"
    for path in (latest, dated):
        path.write_text(json.dumps(report, indent=2))

    if not args.json_only:
        print(f"\n  Wrote {latest.name} and {dated.name}\n")

        def _print_block(title: str, rows: List[dict], fields: List[str]) -> None:
            print(f"  {title} ({len(rows)} shown, cap 200)")
            print("  " + "-" * 68)
            if not rows:
                print("  (none)")
                return
            for row in rows[:40]:
                bits = [str(row.get(f, ""))[:56] for f in fields]
                print("  " + " | ".join(bits))
            if len(rows) > 40:
                print(f"  ... +{len(rows) - 40} more (see JSON)")

        _print_block(
            "CTR DROP (high prior visibility)",
            ctr_alerts,
            ["query", "prior_ctr", "recent_ctr", "prior_impressions", "recent_impressions"],
        )
        print()
        _print_block(
            "IMPRESSION DROP",
            impr_drop,
            ["query", "prior_impressions", "recent_impressions", "page"],
        )
        print()
        _print_block(
            "IMPRESSION SPIKE",
            impr_spike,
            ["query", "prior_impressions", "recent_impressions", "page"],
        )
        print()
        print(f"  BLEEDING PAGES — clicks/day lost to CTR decline at held impressions")
        print("  " + "-" * 68)
        if not bleeding:
            print("  (none)")
        for e in bleeding[:15]:
            mark = "  <== ALERT" if e["lost_day"] >= args.bleed_alert else ""
            print(f"  {e['page'].replace(site_url.rstrip('/'), '')[:46]:46} "
                  f"{e['lost_day']:8.1f}/day  {e['queries']:3d}q{mark}")
        print(f"\n  Site total: ~{report['bleeding_total_day']:.0f} clicks/day "
              f"(alerts at {args.bleed_alert:.0f}/page/day)")
        print("\n  Tip: tighten noise with --min-impr 50 or shorter --days 7 windows.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
