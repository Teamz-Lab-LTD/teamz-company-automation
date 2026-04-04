#!/usr/bin/env python3
"""
Google Play Console — reporting + store listing (service account).

Uses the same GCP project as your Play-linked service account (can differ from
Firebase / Search Console projects). Invite the service account email in
Play Console → Users and permissions with at least:
  - View app information (read-only) — reporting
  - Manage store presence — edit listings (title, short description, full description, video)

Enable in that GCP project:
  - Google Play Android Developer API (androidpublisher)
  - Play Developer Reporting API (playdeveloperreporting)

Setup (one-time, in Google Cloud Console — not from this repo):
  1. Create a service account in your Play-API project; create JSON key; store outside git.
  2. Play Console → Users and permissions → Invite the SA email; grant permissions above.
  3. Set TEAMZ_PLAY_SERVICE_ACCOUNT_JSON and TEAMZ_PLAY_PACKAGE_NAME in .teamz-automation.env

Dependencies:
  pip install google-api-python-client google-auth

Usage:
  python3 build-play-console.py report [--package com.app] [--days 7] [--out path.json]
  python3 build-play-console.py listing-pull [--package com.app] [--language en-US] [--out path.json]
  python3 build-play-console.py listing-push [--package com.app] --file listing.json   # validate, discard draft
  python3 build-play-console.py listing-push [--package com.app] --file listing.json --commit   # LIVE
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from _teamz_config import load_runtime

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print(
        "ERROR: Missing dependencies. Run:\n"
        "  pip3 install google-api-python-client google-auth",
        file=sys.stderr,
    )
    sys.exit(1)

SCOPES = (
    "https://www.googleapis.com/auth/androidpublisher",
    "https://www.googleapis.com/auth/playdeveloperreporting",
)


def _credentials(json_path: Path):
    return service_account.Credentials.from_service_account_file(str(json_path), scopes=SCOPES)


def _package_name(cfg: dict, override: Optional[str]) -> str:
    pkg = (override or cfg.get("play_package_name") or "").strip()
    if pkg:
        return pkg
    raw = os.getenv("TEAMZ_APP_IDS", "").strip()
    for part in raw.split(","):
        part = part.strip()
        if "." in part and part.replace(".", "").replace("_", "").isalnum():
            return part
    return ""


def _require_paths(cfg: dict, package: str) -> Path:
    sa = cfg.get("play_service_account_json")
    if not sa or not Path(sa).is_file():
        print(
            "ERROR: Set TEAMZ_PLAY_SERVICE_ACCOUNT_JSON to your Play service account JSON key path.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not package:
        print(
            "ERROR: Set TEAMZ_PLAY_PACKAGE_NAME or pass --package com.your.app",
            file=sys.stderr,
        )
        sys.exit(1)
    return Path(sa)


def cmd_report(cfg: dict, package: str, days: int, out: Optional[Path]) -> int:
    sa_path = _require_paths(cfg, package)
    creds = _credentials(sa_path)
    reporting = build("playdeveloperreporting", "v1beta1", credentials=creds, cache_discovery=False)

    # Play reporting lags behind "today"; end must be <= API freshness (often 1–2 calendar days).
    lag = max(1, int(os.getenv("TEAMZ_PLAY_REPORTING_LAG_DAYS", "2")))
    end_d = date.today() - timedelta(days=lag)
    start_d = end_d - timedelta(days=max(1, days) - 1)
    timeline = {
        "aggregationPeriod": "DAILY",
        "startTime": {
            "year": start_d.year,
            "month": start_d.month,
            "day": start_d.day,
            "timeZone": {"id": "America/Los_Angeles"},
        },
        "endTime": {
            "year": end_d.year,
            "month": end_d.month,
            "day": end_d.day,
            "timeZone": {"id": "America/Los_Angeles"},
        },
    }
    body = {
        "timelineSpec": timeline,
        "metrics": ["crashRate", "userPerceivedCrashRate", "distinctUsers"],
        "dimensions": [],
        "pageSize": 100,
    }
    name = f"apps/{package}/crashRateMetricSet"
    try:
        resp = reporting.vitals().crashrate().query(name=name, body=body).execute()
    except HttpError as e:
        err = e.content.decode() if e.content else str(e)
        print(f"ERROR: Play Developer Reporting API: {e.resp.status} {err[:800]}", file=sys.stderr)
        return 1

    payload = {
        "packageName": package,
        "metricSet": "crashRate",
        "query": body,
        "response": resp,
    }
    text = json.dumps(payload, indent=2)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(f"Wrote {out}")
    else:
        print(text)
    return 0


def _publisher(creds):
    return build("androidpublisher", "v3", credentials=creds, cache_discovery=False)


def cmd_listing_pull(cfg: dict, package: str, language: str, out: Optional[Path]) -> int:
    sa_path = _require_paths(cfg, package)
    creds = _credentials(sa_path)
    pub = _publisher(creds)
    try:
        edit = pub.edits().insert(packageName=package, body={}).execute()
        eid = edit["id"]
        listing = (
            pub.edits()
            .listings()
            .get(packageName=package, editId=eid, language=language)
            .execute()
        )
        pub.edits().delete(packageName=package, editId=eid).execute()
    except HttpError as e:
        err = e.content.decode() if e.content else str(e)
        print(f"ERROR: Android Publisher API: {e.resp.status} {err[:800]}", file=sys.stderr)
        return 1

    listing["language"] = language
    text = json.dumps(listing, indent=2, ensure_ascii=False)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(f"Wrote {out}")
    else:
        print(text)
    return 0


def cmd_listing_push(cfg: dict, package: str, path: Path, commit: bool) -> int:
    data = json.loads(path.read_text())
    language = (data.pop("language", None) or "en-US").strip()

    sa_path = _require_paths(cfg, package)
    creds = _credentials(sa_path)
    pub = _publisher(creds)
    try:
        edit = pub.edits().insert(packageName=package, body={}).execute()
        eid = edit["id"]
        current = (
            pub.edits()
            .listings()
            .get(packageName=package, editId=eid, language=language)
            .execute()
        )
        merged: Dict[str, Any] = dict(current)
        for k, v in data.items():
            if v is None:
                continue
            merged[k] = v
        allowed = {"title", "shortDescription", "fullDescription", "video"}
        body = {k: merged[k] for k in allowed if k in merged}
        pub.edits().listings().update(
            packageName=package, editId=eid, language=language, body=body
        ).execute()
        pub.edits().validate(packageName=package, editId=eid).execute()
        if commit:
            pub.edits().commit(packageName=package, editId=eid).execute()
            print("Committed listing changes to Google Play (live after processing).")
        else:
            pub.edits().delete(packageName=package, editId=eid).execute()
            print(
                "Dry-run OK: listing validated; draft discarded. "
                "Re-run with --commit to publish."
            )
    except HttpError as e:
        err = e.content.decode() if e.content else str(e)
        print(f"ERROR: Android Publisher API: {e.resp.status} {err[:800]}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    cfg = load_runtime(__file__)
    parser = argparse.ArgumentParser(description="Google Play reporting + listing (service account)")
    pkg_help = "Override TEAMZ_PLAY_PACKAGE_NAME (e.g. com.example.app)"
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rep = sub.add_parser("report", help="Fetch crash-rate metrics (Play Developer Reporting API)")
    p_rep.add_argument("--package", help=pkg_help)
    p_rep.add_argument("--days", type=int, default=7, help="Days of daily aggregates (default 7)")
    p_rep.add_argument("--out", type=Path, help="Write JSON instead of stdout")

    p_pull = sub.add_parser("listing-pull", help="Export store listing JSON for one language")
    p_pull.add_argument("--package", help=pkg_help)
    p_pull.add_argument("--language", default="en-US", help="BCP-47 language (default en-US)")
    p_pull.add_argument(
        "--out",
        type=Path,
        help="Output path (default: TEAMZ_DATA_DIR/play-listing-<package>-<lang>.json)",
    )

    p_push = sub.add_parser("listing-push", help="Update listing from JSON (see script docstring)")
    p_push.add_argument("--package", help=pkg_help)
    p_push.add_argument("--file", type=Path, required=True, help="JSON with language, title, descriptions, video")
    p_push.add_argument(
        "--commit",
        action="store_true",
        help="Publish to Play. Without this, only validates then discards the draft.",
    )

    args = parser.parse_args()
    pkg = _package_name(cfg, getattr(args, "package", None))
    if args.cmd == "report":
        out = args.out
        return cmd_report(cfg, pkg, args.days, out)
    if args.cmd == "listing-pull":
        out = args.out
        if out is None:
            safe_lang = args.language.replace("/", "-")
            out = cfg["data_dir"] / f"play-listing-{pkg.replace('.', '-')}-{safe_lang}.json"
        return cmd_listing_pull(cfg, pkg, args.language, out)
    if args.cmd == "listing-push":
        return cmd_listing_push(cfg, pkg, args.file, args.commit)
    return 1


if __name__ == "__main__":
    sys.exit(main())
