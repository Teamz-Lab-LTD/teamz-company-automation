#!/usr/bin/env python3
"""GA4 Data API puller — daily engagement metrics.

Supports both service-account JSON and OAuth user tokens in the same
file (distinguished by the "type" field), because different apps in
the kit were set up with different auth flows historically.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def load_client(token_path: Path) -> BetaAnalyticsDataClient:
    data = json.loads(token_path.read_text())
    if data.get("type") == "service_account":
        creds = service_account.Credentials.from_service_account_info(data, scopes=SCOPES)
    else:
        creds = UserCredentials.from_authorized_user_info(data, SCOPES)
        if not creds.valid:
            creds.refresh(Request())
    return BetaAnalyticsDataClient(credentials=creds)


def range_window(range_key: str) -> tuple[str, str]:
    today = date.today()
    if range_key == "last-30d":
        return (today - timedelta(days=30)).isoformat(), today.isoformat()
    if range_key == "last-90d":
        return (today - timedelta(days=90)).isoformat(), today.isoformat()
    if range_key == "ytd":
        return date(today.year, 1, 1).isoformat(), today.isoformat()
    # GA4 rejects dates before its own property creation; 2020-01-01 is a safe floor.
    return "2020-01-01", today.isoformat()


def main() -> int:
    range_key = sys.argv[1] if len(sys.argv) > 1 else "lifetime"
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    property_id = os.environ.get("GA4_PROPERTY_ID")
    token_file = os.path.expanduser(os.environ.get("ANALYTICS_TOKEN_FILE", "~/.config/teamzlab/analytics-token.json"))
    if not property_id:
        print("missing GA4_PROPERTY_ID", file=sys.stderr)
        return 1
    if not Path(token_file).exists():
        print(f"analytics token not found: {token_file}", file=sys.stderr)
        return 1

    client = load_client(Path(token_file))
    start, end = range_window(range_key)

    req = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="newUsers"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(start_date=start, end_date=end)],
        limit=100000,
    )
    resp = client.run_report(req)

    out = out_dir / "ga4.csv"
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "active_users", "new_users", "sessions", "screen_page_views", "avg_session_duration_s"])
        for row in resp.rows:
            w.writerow([row.dimension_values[0].value] + [mv.value for mv in row.metric_values])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
