#!/usr/bin/env python3
"""AdMob network report puller.

We chunk lifetime requests into yearly windows because AdMob's
networkReport endpoint has historically 400'd on multi-year ranges
with fine-grained dimensions.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/admob.readonly"]


def load_creds(token_path: Path) -> Credentials:
    data = json.loads(token_path.read_text())
    creds = Credentials.from_authorized_user_info(data, SCOPES)
    if not creds.valid:
        creds.refresh(Request())
    return creds


def date_to_obj(d: date) -> dict:
    return {"year": d.year, "month": d.month, "day": d.day}


def range_window(range_key: str) -> tuple[date, date]:
    today = date.today()
    if range_key == "last-30d":
        return today - timedelta(days=30), today
    if range_key == "last-90d":
        return today - timedelta(days=90), today
    if range_key == "ytd":
        return date(today.year, 1, 1), today
    return date(2020, 1, 1), today


def yearly_chunks(start: date, end: date) -> list[tuple[date, date]]:
    chunks = []
    cursor = start
    while cursor <= end:
        chunk_end = min(date(cursor.year, 12, 31), end)
        chunks.append((cursor, chunk_end))
        cursor = date(cursor.year + 1, 1, 1)
    return chunks


def fetch_chunk(creds: Credentials, publisher_id: str, start: date, end: date) -> list[dict]:
    url = f"https://admob.googleapis.com/v1/accounts/{publisher_id}/networkReport:generate"
    body = {
        "reportSpec": {
            "dateRange": {"startDate": date_to_obj(start), "endDate": date_to_obj(end)},
            "dimensions": ["APP", "MONTH"],
            "metrics": ["ESTIMATED_EARNINGS", "IMPRESSIONS", "CLICKS"],
            "localizationSettings": {"currencyCode": "USD"},
        }
    }
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"AdMob {r.status_code}: {r.text[:300]}")
    return r.json() if isinstance(r.json(), list) else [r.json()]


def extract_rows(payload_items: list[dict]) -> list[dict]:
    rows = []
    for item in payload_items:
        if isinstance(item, list):
            inner = item
        else:
            inner = [item]
        for entry in inner:
            row = entry.get("row") if isinstance(entry, dict) else None
            if not row:
                continue
            dims = row.get("dimensionValues", {})
            mets = row.get("metricValues", {})
            rows.append({
                "month": dims.get("MONTH", {}).get("value", ""),
                "app": dims.get("APP", {}).get("displayLabel") or dims.get("APP", {}).get("value", ""),
                # AdMob returns earnings in micros.
                "earnings_usd": int(mets.get("ESTIMATED_EARNINGS", {}).get("microsValue", 0)) / 1_000_000,
                "impressions": int(mets.get("IMPRESSIONS", {}).get("integerValue", 0)),
                "clicks": int(mets.get("CLICKS", {}).get("integerValue", 0)),
            })
    return rows


def main() -> int:
    range_key = sys.argv[1] if len(sys.argv) > 1 else "lifetime"
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    publisher = os.environ.get("ADMOB_PUBLISHER_ID")
    token_file = os.path.expanduser(os.environ.get("ADMOB_TOKEN_FILE", "~/.config/teamzlab/admob-token.json"))
    if not publisher:
        print("missing ADMOB_PUBLISHER_ID", file=sys.stderr)
        return 1
    if not Path(token_file).exists():
        print(f"admob token not found: {token_file}", file=sys.stderr)
        return 1

    creds = load_creds(Path(token_file))
    start, end = range_window(range_key)

    all_rows: list[dict] = []
    try:
        all_rows.extend(extract_rows(fetch_chunk(creds, publisher, start, end)))
    except RuntimeError as exc:
        if "400" not in str(exc):
            raise
        for cs, ce in yearly_chunks(start, end):
            all_rows.extend(extract_rows(fetch_chunk(creds, publisher, cs, ce)))

    out = out_dir / "admob.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["month", "app", "earnings_usd", "impressions", "clicks"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
