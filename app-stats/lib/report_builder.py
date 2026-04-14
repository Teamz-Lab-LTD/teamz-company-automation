#!/usr/bin/env python3
"""Merges the per-puller CSVs under a tempdir into one markdown report."""
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

IAP_PRICE = 2.99


def na(reason: str = "not available") -> str:
    return f"N/A — {reason}"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as fh:
        return list(csv.DictReader(fh))


def sum_col(rows: list[dict], key: str) -> float:
    total = 0.0
    for r in rows:
        try:
            total += float(r.get(key) or 0)
        except ValueError:
            continue
    return total


def sum_int(rows: list[dict], key: str) -> int:
    total = 0
    for r in rows:
        try:
            total += int(float(r.get(key) or 0))
        except ValueError:
            continue
    return total


def ios_section(tmp: Path) -> tuple[str, dict]:
    rows = read_csv(tmp / "ios" / "ios_sales.csv")
    if not rows:
        return f"- {na('no iOS sales data returned')}\n", {}
    units = sum_int(rows, "units")
    proceeds = sum_col(rows, "proceeds_usd")
    months = sorted({r["month"] for r in rows if r.get("month")})
    md = [
        f"| Metric | Value |",
        f"| --- | --- |",
        f"| Total installs (units) | {units:,} |",
        f"| Developer proceeds (USD) | ${proceeds:,.2f} |",
        f"| Months covered | {months[0] if months else '-'} → {months[-1] if months else '-'} |",
    ]
    return "\n".join(md) + "\n", {"installs": units, "proceeds_usd": proceeds}


def android_section(tmp: Path) -> tuple[str, dict]:
    install_dir = tmp / "android" / "installs"
    earnings_dir = tmp / "android" / "earnings"
    installs = 0
    earnings = 0.0
    files = 0

    if install_dir.exists():
        for f in install_dir.glob("*.csv"):
            files += 1
            for row in read_csv(f):
                for k in ("Daily Device Installs", "Store Listing Acquisitions", "Install events"):
                    if k in row:
                        try:
                            installs += int(float(row[k] or 0))
                        except ValueError:
                            pass
                        break

    if earnings_dir.exists():
        for f in earnings_dir.glob("*.csv"):
            files += 1
            for row in read_csv(f):
                amt = row.get("Amount (Merchant Currency)") or row.get("Amount (Buyer Currency)") or "0"
                try:
                    earnings += float(amt)
                except ValueError:
                    pass

    if files == 0:
        return f"- {na('no Play Console CSVs downloaded — check PLAY_REPORTS_BUCKET and service-account permission')}\n", {}

    md = [
        "| Metric | Value |",
        "| --- | --- |",
        f"| Total installs | {installs:,} |",
        f"| IAP earnings (merchant currency) | {earnings:,.2f} |",
        f"| CSV files parsed | {files} |",
    ]
    return "\n".join(md) + "\n", {"installs": installs, "earnings": earnings}


def admob_section(tmp: Path) -> tuple[str, dict]:
    rows = read_csv(tmp / "admob" / "admob.csv")
    if not rows:
        return f"- {na('no AdMob data returned')}\n", {}
    earnings = sum_col(rows, "earnings_usd")
    impressions = sum_int(rows, "impressions")
    clicks = sum_int(rows, "clicks")
    ecpm = (earnings / impressions * 1000) if impressions else 0
    md = [
        "| Metric | Value |",
        "| --- | --- |",
        f"| Estimated earnings (USD) | ${earnings:,.2f} |",
        f"| Impressions | {impressions:,} |",
        f"| Clicks | {clicks:,} |",
        f"| Blended eCPM | ${ecpm:.2f} |",
    ]
    return "\n".join(md) + "\n", {"earnings_usd": earnings, "impressions": impressions}


def ga4_section(tmp: Path) -> tuple[str, dict]:
    rows = read_csv(tmp / "ga4" / "ga4.csv")
    if not rows:
        return f"- {na('no GA4 data returned')}\n", {}
    new_users = sum_int(rows, "new_users")
    sessions = sum_int(rows, "sessions")
    page_views = sum_int(rows, "screen_page_views")
    # Daily active users are not summable across days — use last-day and a 30d avg.
    sorted_rows = sorted(rows, key=lambda r: r.get("date", ""))
    latest_dau = int(float(sorted_rows[-1].get("active_users") or 0)) if sorted_rows else 0
    last_30 = sorted_rows[-30:]
    avg_dau_30 = (sum(int(float(r.get("active_users") or 0)) for r in last_30) / len(last_30)) if last_30 else 0
    md = [
        "| Metric | Value |",
        "| --- | --- |",
        f"| New users (lifetime-in-window) | {new_users:,} |",
        f"| Sessions | {sessions:,} |",
        f"| Screen/page views | {page_views:,} |",
        f"| Latest-day DAU | {latest_dau:,} |",
        f"| Avg DAU (last 30 days in window) | {avg_dau_30:,.0f} |",
    ]
    return "\n".join(md) + "\n", {"new_users": new_users, "avg_dau_30": avg_dau_30}


def break_even_section(ios: dict, android: dict, admob: dict, ga4: dict) -> str:
    ad_earnings = admob.get("earnings_usd")
    # Prefer GA4 new_users as the denominator (most accurate per-user figure);
    # fall back to summed store installs.
    users = ga4.get("new_users") or ((ios.get("installs") or 0) + (android.get("installs") or 0))
    if not ad_earnings or not users:
        return f"- {na('need AdMob earnings and a user count to compute ARPU')}\n"

    arpu = ad_earnings / users
    verdict = (
        f"Ad ARPU is **${arpu:.2f}** per lifetime user, below the ${IAP_PRICE:.2f} "
        f"break-even. Recommend adding a lifetime IAP at ${IAP_PRICE:.2f}."
        if arpu < IAP_PRICE else
        f"Ad ARPU is **${arpu:.2f}** per lifetime user, at or above ${IAP_PRICE:.2f}. "
        f"A lifetime IAP at ${IAP_PRICE:.2f} would likely cannibalize ad revenue — advise against."
    )
    md = [
        "| Metric | Value |",
        "| --- | --- |",
        f"| Lifetime ad revenue | ${ad_earnings:,.2f} |",
        f"| Users (denominator) | {users:,} |",
        f"| Lifetime ad ARPU | ${arpu:.4f} |",
        f"| IAP comparison price | ${IAP_PRICE:.2f} |",
        "",
        verdict,
    ]
    return "\n".join(md) + "\n"


def summary_section(ios: dict, android: dict, admob: dict, ga4: dict) -> str:
    total_installs = (ios.get("installs") or 0) + (android.get("installs") or 0)
    total_rev = (ios.get("proceeds_usd") or 0) + (android.get("earnings") or 0) + (admob.get("earnings_usd") or 0)
    md = [
        "| Headline | Value |",
        "| --- | --- |",
        f"| Combined installs (iOS + Android) | {total_installs:,} |",
        f"| Combined gross revenue (IAP + ads, USD) | ${total_rev:,.2f} |",
        f"| New users (GA4) | {ga4.get('new_users', 0):,}" + " |",
    ]
    return "\n".join(md) + "\n"


def main() -> int:
    tmp = Path(sys.argv[1])
    out = Path(sys.argv[2])
    app_name = os.environ.get("APP_NAME", "App")
    range_key = os.environ.get("RANGE", "lifetime")
    errors = [e for e in os.environ.get("ERRORS", "").splitlines() if e.strip()]

    ios_md, ios_d = ios_section(tmp)
    android_md, android_d = android_section(tmp)
    admob_md, admob_d = admob_section(tmp)
    ga4_md, ga4_d = ga4_section(tmp)

    lines = [
        f"# App Stats Report — {app_name} — {range_key}",
        "",
        f"_Generated {datetime.now().isoformat(timespec='seconds')}_",
        "",
        "## Summary",
        "",
        summary_section(ios_d, android_d, admob_d, ga4_d),
        "## iOS",
        "",
        ios_md,
        "## Android",
        "",
        android_md,
        "## Ad Revenue",
        "",
        admob_md,
        "## User Engagement (GA4)",
        "",
        ga4_md,
        "## IAP Break-Even Analysis",
        "",
        break_even_section(ios_d, android_d, admob_d, ga4_d),
    ]

    if errors:
        lines += ["## Puller Warnings", ""]
        lines += [f"- {e}" for e in errors]
        lines.append("")

    out.write_text("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
