#!/usr/bin/env python3
"""Pull Firebase Analytics events from BigQuery for behavior analysis.

Prerequisites (one-time setup):

1. Firebase Console -> Project Settings -> Integrations -> BigQuery -> Link.
2. Upgrade the Firebase project to the Blaze plan (free for low usage; the
   BigQuery free tier covers 1TB query / month + 10GB storage which is
   plenty for early-stage apps).
3. Wait ~24h after enabling for the first analytics_<id>.events_YYYYMMDD
   table to appear.

Credentials reuse: this script reuses TEAMZ_PLAY_SERVICE_ACCOUNT_JSON if
it has BigQuery access. For the no-trace-chat project the service account
at ~/.config/teamzlab/play-console-service-account.json needs the
BigQuery Data Viewer + BigQuery Job User roles on the Firebase GCP
project. Add them in IAM if missing.

Usage:
    python3 aso-firebase-events.py \
        --project no-trace-chat \
        --days 30 \
        [--funnel gate_unlocked,home_create_room_clicked,room_created,message_sent,credits_exhausted,premium_modal_shown] \
        [--out events.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
except ImportError:
    print(
        "ERROR: Missing dependencies. Run:\n"
        "  pip3 install google-cloud-bigquery google-auth",
        file=sys.stderr,
    )
    sys.exit(1)


def _credentials(json_path: Path):
    return service_account.Credentials.from_service_account_file(
        str(json_path),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


def _sa_path() -> Path:
    raw = os.getenv("TEAMZ_PLAY_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raw = os.path.expanduser("~/.config/teamzlab/play-console-service-account.json")
    p = Path(raw)
    if not p.is_file():
        print(f"ERROR: Service account JSON not found at {p}", file=sys.stderr)
        sys.exit(1)
    return p


def _discover_dataset(client: bigquery.Client, project: str) -> str:
    """Firebase Analytics exports go to analytics_<property_id>.

    There is typically exactly one per Firebase project. We discover it by
    listing datasets that start with ``analytics_``.
    """
    for ds in client.list_datasets(project=project):
        if ds.dataset_id.startswith("analytics_"):
            return ds.dataset_id
    raise RuntimeError(
        f"No analytics_<id> dataset found in BigQuery project {project}. "
        "Confirm Firebase Analytics is linked to BigQuery and at least one day has elapsed."
    )


def _event_counts(client: bigquery.Client, project: str, dataset: str, days: int) -> dict:
    end = date.today()
    start = end - timedelta(days=days)
    sql = f"""
        SELECT
          event_name,
          COUNT(*) AS event_count,
          COUNT(DISTINCT user_pseudo_id) AS distinct_users
        FROM `{project}.{dataset}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start.strftime("%Y%m%d")}' AND '{end.strftime("%Y%m%d")}'
        GROUP BY event_name
        ORDER BY event_count DESC
    """
    rows = list(client.query(sql).result())
    return {
        "window_days": days,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "events": [
            {"name": r.event_name, "count": int(r.event_count), "distinct_users": int(r.distinct_users)}
            for r in rows
        ],
    }


def _funnel(client: bigquery.Client, project: str, dataset: str, days: int, steps: list[str]) -> dict:
    """Sequential funnel: count distinct users who reached each step in order.

    Order is enforced by event timestamp — a user must hit step N before
    step N+1 to count. This catches the realistic drop-off shape.
    """
    end = date.today()
    start = end - timedelta(days=days)
    # Build per-step CTEs each restricting to users who passed the prior step.
    steps_quoted = ", ".join(f"'{s}'" for s in steps)
    sql = f"""
        WITH base AS (
          SELECT
            user_pseudo_id AS uid,
            event_name AS name,
            TIMESTAMP_MICROS(event_timestamp) AS ts
          FROM `{project}.{dataset}.events_*`
          WHERE _TABLE_SUFFIX BETWEEN '{start.strftime("%Y%m%d")}' AND '{end.strftime("%Y%m%d")}'
            AND event_name IN ({steps_quoted})
        ),
        ordered AS (
          SELECT
            uid,
            name,
            ts,
            ROW_NUMBER() OVER (PARTITION BY uid, name ORDER BY ts) AS rn
          FROM base
        )
        SELECT name, COUNT(DISTINCT uid) AS users FROM ordered WHERE rn = 1 GROUP BY name
    """
    rows = list(client.query(sql).result())
    by_name = {r.name: int(r.users) for r in rows}
    funnel = [{"step": s, "users": by_name.get(s, 0)} for s in steps]
    return {"steps": funnel}


def main() -> int:
    parser = argparse.ArgumentParser(description="Firebase Analytics event counts + funnel via BigQuery.")
    parser.add_argument("--project", required=True, help="GCP project id (Firebase project id)")
    parser.add_argument("--days", type=int, default=30, help="Look-back window in days (default 30)")
    parser.add_argument(
        "--funnel",
        default="",
        help="Comma-separated ordered event names for a sequential funnel",
    )
    parser.add_argument("--out", type=Path, help="Output JSON path (default: stdout)")
    args = parser.parse_args()

    creds = _credentials(_sa_path())
    client = bigquery.Client(credentials=creds, project=args.project)
    dataset = _discover_dataset(client, args.project)

    payload: dict = {
        "project": args.project,
        "dataset": dataset,
        "event_counts": _event_counts(client, args.project, dataset, args.days),
    }

    if args.funnel:
        steps = [s.strip() for s in args.funnel.split(",") if s.strip()]
        payload["funnel"] = _funnel(client, args.project, dataset, args.days, steps)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
