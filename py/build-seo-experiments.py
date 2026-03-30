#!/usr/bin/env python3
"""
SEO experiment helper — before/after Search Console aggregates for listed page URLs.

Edit TEAMZ_DATA_DIR/seo-experiments.json (see example below). Each experiment defines a
page URL prefix (or full URL) and a change date. The script compares two equal windows
before and after the change (default 14 days each), respecting GSC lag on the recent end.

Example seo-experiments.json:
{
  "window_days": 14,
  "experiments": [
    {
      "id": "title-test-1",
      "page_expression": "https://example.com/tools/my-tool/",
      "change_date": "2026-02-01",
      "notes": "Shorter title tag"
    }
  ]
}

Usage:
    python3 scripts/build-seo-experiments.py
    python3 scripts/build-seo-experiments.py --dry-run   # show windows only
"""

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def _sc_sum_page(
    token: str,
    site_url: str,
    project: str,
    start: str,
    end: str,
    page_expression: str,
) -> Dict[str, float]:
    encoded = urllib.parse.quote(site_url, safe="")
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query"
    body: Dict[str, Any] = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["page"],
        "rowLimit": 25000,
        "dataState": "all",
        "dimensionFilterGroups": [
            {
                "filters": [
                    {
                        "dimension": "page",
                        "operator": "contains",
                        "expression": page_expression,
                    }
                ]
            }
        ],
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-goog-user-project", project)
    try:
        resp = urllib.request.urlopen(req, context=_CTX)
        rows = json.loads(resp.read()).get("rows", [])
    except urllib.error.HTTPError as e:
        print(f"  API error: {e.code} {e.read().decode()[:300]}", file=sys.stderr)
        return {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}

    clicks = sum(int(r.get("clicks", 0)) for r in rows)
    impr = sum(int(r.get("impressions", 0)) for r in rows)
    ctr = (clicks / impr) if impr else 0.0
    pos = sum(float(r.get("position", 0)) * int(r.get("impressions", 0)) for r in rows) / impr if impr else 0.0
    return {"clicks": clicks, "impressions": impr, "ctr": ctr, "position": pos}


def main() -> int:
    ap = argparse.ArgumentParser(description="SEO experiment before/after (Search Console)")
    ap.add_argument("--dry-run", action="store_true", help="Print date windows only")
    args = ap.parse_args()

    cfg = load_runtime(__file__)
    if cfg["project_type"] == "app":
        print("Skipped: TEAMZ_PROJECT_TYPE=app (website-only tooling).", file=sys.stderr)
        return 2

    data_dir: Path = cfg["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = data_dir / "seo-experiments.json"
    if not cfg_path.exists():
        example = {
            "window_days": 14,
            "lag_days": 3,
            "experiments": [
                {
                    "id": "example",
                    "page_expression": cfg["site_url"].rstrip("/") + "/",
                    "change_date": datetime.now().strftime("%Y-%m-%d"),
                    "notes": "Replace with your real change date and URL prefix",
                }
            ],
        }
        cfg_path.write_text(json.dumps(example, indent=2))
        print(f"Created template {cfg_path} — edit it and re-run.")
        return 0

    spec = json.loads(cfg_path.read_text())
    window = int(spec.get("window_days", 14))
    lag = int(spec.get("lag_days", 3))
    experiments: List[dict] = spec.get("experiments") or []

    token = _refresh_token(cfg["sc_token_file"], cfg["google_project"])
    if not token and not args.dry_run:
        print("ERROR: Search Console token missing or invalid.", file=sys.stderr)
        return 1

    today = datetime.now().date()
    latest_end = today - timedelta(days=lag)

    print("=" * 72)
    print("  SEO EXPERIMENTS — before/after (Search Console)")
    print(f"  Config: {cfg_path}")
    print("=" * 72)

    results = []

    for ex in experiments:
        eid = ex.get("id", "?")
        page_expr = ex.get("page_expression", "").strip()
        cd = ex.get("change_date", "")
        notes = ex.get("notes", "")
        if not page_expr or not cd:
            print(f"\n  [{eid}] SKIP — need page_expression and change_date")
            continue

        try:
            change = datetime.strptime(cd, "%Y-%m-%d").date()
        except ValueError:
            print(f"\n  [{eid}] SKIP — bad change_date {cd!r}")
            continue

        before_end = change - timedelta(days=1)
        before_start = before_end - timedelta(days=window - 1)
        after_start = change + timedelta(days=1)
        after_end = after_start + timedelta(days=window - 1)
        if after_end > latest_end:
            after_end = latest_end
        if after_start > after_end:
            print(f"\n  [{eid}] SKIP — after window not available yet (lag)")
            continue

        bs, be = before_start.strftime("%Y-%m-%d"), before_end.strftime("%Y-%m-%d")
        afs, afe = after_start.strftime("%Y-%m-%d"), after_end.strftime("%Y-%m-%d")

        print(f"\n  Experiment: {eid}")
        print(f"  Page contains: {page_expr[:70]}...")
        print(f"  Change date:   {cd}  |  {notes}")
        print(f"  Before: {bs} .. {be}  ({window}d)")
        print(f"  After:  {afs} .. {afe}  ({(after_end - after_start).days + 1}d)")

        if args.dry_run:
            continue

        b = _sc_sum_page(token, cfg["site_property"], cfg["google_project"], bs, be, page_expr)
        a = _sc_sum_page(token, cfg["site_property"], cfg["google_project"], afs, afe, page_expr)

        def pct(old: float, new: float) -> str:
            if old <= 0:
                return "n/a"
            return f"{(new - old) / old * 100:+.1f}%"

        print(
            f"  Impressions: {b['impressions']} → {a['impressions']} ({pct(float(b['impressions']), float(a['impressions']))})"
        )
        print(
            f"  Clicks:      {b['clicks']} → {a['clicks']} ({pct(float(b['clicks']), float(a['clicks']))})"
        )
        print(f"  CTR:         {b['ctr']*100:.2f}% → {a['ctr']*100:.2f}%")
        print(f"  Avg pos (w): {b['position']:.1f} → {a['position']:.1f}")

        results.append(
            {
                "id": eid,
                "before": b,
                "after": a,
                "windows": {"before": [bs, be], "after": [afs, afe]},
            }
        )

    out_path = data_dir / "seo-experiments-result-latest.json"
    if results:
        out_path.write_text(json.dumps({"generated_at": datetime.now().isoformat(), "results": results}, indent=2))
        print(f"\n  Wrote {out_path.name}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
