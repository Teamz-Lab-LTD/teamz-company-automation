#!/usr/bin/env python3
"""
ASO Velocity — download & install velocity tracker for Play Console + ASC.

Closes the last ASO-specific analytics gap:
  - Download velocity (installs/day, trend 7/14/28 day)
  - Install → active user conversion (Play only; retention proxy)
  - Country/locale breakdown (where growth is happening)
  - Release timing signal (day-of-week install patterns)
  - Category benchmark bookkeeping (track own KPIs over time for comparison)

Data sources (both use existing kit credentials — no new setup needed):
  - **Play Console**: `playdeveloperreporting` v1beta1 (via service account JSON
    already configured as TEAMZ_PLAY_SERVICE_ACCOUNT_JSON). Same creds used by
    build-play-console.py. Metrics: installsUniqueDevice, activeDevices,
    crashRate, ratingsAverage.
  - **App Store Connect** (optional): Sales & Trends reports via JWT signed
    with your P8 key (AuthKey_559DD92MBH.p8). Auto-skipped if key missing.
    Shells out to `openssl` for ES256 signing (no extra pip deps).

Usage::

    python3 py/aso/aso-velocity.py                      # snapshot last 28 days
    python3 py/aso/aso-velocity.py --days 7             # last 7 days only
    python3 py/aso/aso-velocity.py --platform play      # Play only (skip ASC)
    python3 py/aso/aso-velocity.py --platform ios       # ASC only
    python3 py/aso/aso-velocity.py --history            # append to aso-velocity-history.csv

Outputs:
  {data}/aso-velocity-latest.json   — current snapshot
  {data}/aso-velocity-history.csv   — appended row per run (for trend charts)
  {data}/aso-velocity-report.md     — human-readable summary

Dependencies (Play side): already installed for build-play-console.py —
  pip3 install google-api-python-client google-auth
"""

from __future__ import annotations

import argparse
import base64
import csv
import gzip
import io
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _teamz_config import load_runtime  # noqa: E402

_CFG = load_runtime(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py")
)
_DATA_DIR = Path(
    os.environ.get("TEAMZ_DATA_DIR", "")
    or _CFG.get("data_dir", "")
    or str(Path(_CFG["host_site_root"]) / "automation_data")
)


# ─────────────────────────── Play Developer Reporting API ────────────────────

def _play_client():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("[ERROR] Missing deps: pip3 install google-api-python-client google-auth",
              file=sys.stderr)
        return None
    sa_path = os.environ.get("TEAMZ_PLAY_SERVICE_ACCOUNT_JSON", "")
    if not sa_path:
        print("[WARN] TEAMZ_PLAY_SERVICE_ACCOUNT_JSON not set — Play velocity skipped",
              file=sys.stderr)
        return None
    sa_path = os.path.expanduser(sa_path)
    if not Path(sa_path).exists():
        print(f"[WARN] Service account JSON not found: {sa_path}", file=sys.stderr)
        return None
    creds = service_account.Credentials.from_service_account_file(
        sa_path, scopes=["https://www.googleapis.com/auth/playdeveloperreporting"]
    )
    return build("playdeveloperreporting", "v1beta1", credentials=creds, cache_discovery=False)


def _play_velocity(days: int) -> dict | None:
    client = _play_client()
    if not client:
        return None
    pkg = os.environ.get("TEAMZ_PLAY_PACKAGE_NAME", "")
    if not pkg:
        print("[WARN] TEAMZ_PLAY_PACKAGE_NAME not set", file=sys.stderr)
        return None

    end = datetime.now(timezone.utc).date() - timedelta(days=2)  # 2-day reporting lag
    start = end - timedelta(days=days)

    metric_set = f"apps/{pkg}/installsMetricSet"
    body = {
        "timelineSpec": {
            "aggregationPeriod": "DAILY",
            "startTime": {"year": start.year, "month": start.month, "day": start.day,
                          "timeZone": {"id": "UTC"}},
            "endTime": {"year": end.year, "month": end.month, "day": end.day,
                        "timeZone": {"id": "UTC"}},
        },
        "metrics": ["activeDevices", "installsUniqueDevice", "uninstallsUniqueDevice"],
        "dimensions": [],
    }
    try:
        resp = client.vitals().installs().query(name=metric_set, body=body).execute()
    except Exception as e:
        print(f"[WARN] Play Reporting API error: {e}", file=sys.stderr)
        return None

    rows = resp.get("rows", [])
    installs_series, active_series, uninstall_series = [], [], []
    for r in rows:
        interval = r.get("startTime", {})
        d = f"{interval.get('year')}-{interval.get('month'):02d}-{interval.get('day'):02d}"
        metrics = {m["metric"]: m.get("decimalValue", {}).get("value") or
                   m.get("int64Value") or 0 for m in r.get("metrics", [])}
        try:
            installs_series.append((d, int(float(metrics.get("installsUniqueDevice", 0)))))
            active_series.append((d, int(float(metrics.get("activeDevices", 0)))))
            uninstall_series.append((d, int(float(metrics.get("uninstallsUniqueDevice", 0)))))
        except (ValueError, TypeError):
            continue

    total_inst = sum(v for _, v in installs_series)
    total_unin = sum(v for _, v in uninstall_series)
    avg_daily = total_inst / max(1, len(installs_series))
    # 7-day trend slope: installs_last7 vs prior 7
    def _sum(series, n): return sum(v for _, v in series[-n:])
    trend = None
    if len(installs_series) >= 14:
        last7 = _sum(installs_series, 7)
        prev7 = _sum(installs_series[:-7], 7)
        trend = ((last7 - prev7) / max(1, prev7) * 100)

    # Day-of-week signal
    dow: dict[int, list[int]] = {}
    for d, v in installs_series:
        try:
            w = datetime.fromisoformat(d).weekday()
            dow.setdefault(w, []).append(v)
        except ValueError:
            continue
    dow_avg = {w: sum(vs)/len(vs) for w, vs in dow.items() if vs}
    best_day = max(dow_avg, key=dow_avg.get) if dow_avg else None

    return {
        "platform": "play",
        "package": pkg,
        "period": f"{start} → {end}",
        "days": len(installs_series),
        "total_installs": total_inst,
        "total_uninstalls": total_unin,
        "net_installs": total_inst - total_unin,
        "avg_installs_per_day": round(avg_daily, 1),
        "trend_pct_7d": round(trend, 1) if trend is not None else None,
        "active_devices_latest": active_series[-1][1] if active_series else None,
        "best_day_of_week": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][best_day] if best_day is not None else None,
        "daily_installs": installs_series,
    }


# ─────────────────────────── App Store Connect ────────────────────────────────

def _asc_jwt(issuer: str, key_id: str, p8_path: str) -> str | None:
    """Sign an ASC API JWT via `openssl` CLI (ES256). No pip deps needed."""
    header = {"alg": "ES256", "kid": key_id, "typ": "JWT"}
    payload = {
        "iss": issuer,
        "iat": int(time.time()),
        "exp": int(time.time()) + 1200,
        "aud": "appstoreconnect-v1",
    }

    def _b64(obj):
        raw = json.dumps(obj, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    signing_input = f"{_b64(header)}.{_b64(payload)}".encode()
    try:
        r = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", p8_path],
            input=signing_input, capture_output=True, timeout=10,
        )
        if r.returncode != 0:
            print(f"[WARN] openssl sign failed: {r.stderr.decode(errors='replace')}",
                  file=sys.stderr)
            return None
        # openssl outputs DER-encoded ECDSA signature; JWT needs raw r||s (64 bytes)
        sig = _der_to_raw_ecdsa(r.stdout)
        if sig is None:
            return None
        sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
        return f"{signing_input.decode()}.{sig_b64}"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[WARN] openssl not usable: {e}", file=sys.stderr)
        return None


def _der_to_raw_ecdsa(der: bytes) -> bytes | None:
    """Convert DER-encoded ECDSA signature to raw r||s (64 bytes for P-256)."""
    try:
        if der[0] != 0x30:
            return None
        # Skip sequence header
        i = 2 if der[1] < 0x80 else 2 + (der[1] & 0x7F)
        # r
        if der[i] != 0x02:
            return None
        rlen = der[i+1]
        r = der[i+2:i+2+rlen].lstrip(b"\x00").rjust(32, b"\x00")
        i += 2 + rlen
        # s
        if der[i] != 0x02:
            return None
        slen = der[i+1]
        s = der[i+2:i+2+slen].lstrip(b"\x00").rjust(32, b"\x00")
        return r + s
    except (IndexError, ValueError):
        return None


# Apple's "Product Type Identifier" column. Only these are first-time downloads.
# Everything else in the report is an update or a re-download, and counting them
# as installs is how this script once overstated Top3Picks by 374x.
#   1, 1F, 1T, F1  -> first-time download (iPhone / universal / iPad / free)
#   3, 3F, 7, 7F   -> UPDATE (an existing user re-downloading a new build)
#   IA1            -> in-app purchase
_ASC_DOWNLOAD_TYPES = {"1", "1F", "1T", "F1"}


def _asc_velocity(days: int) -> dict | None:
    issuer = os.environ.get("TEAMZ_ASC_ISSUER_ID", "100d6ef8-7452-4aff-85a4-990158b60b3d")
    key_id = os.environ.get("TEAMZ_ASC_KEY_ID", "559DD92MBH")
    p8 = os.path.expanduser(
        os.environ.get("TEAMZ_ASC_P8_PATH",
                       f"~/.config/teamzlab/AuthKey_{key_id}.p8"))
    vendor = os.environ.get("TEAMZ_ASC_VENDOR_NUMBER", "93213066")
    if not Path(p8).exists():
        print(f"[WARN] ASC P8 key not found: {p8} — iOS velocity skipped",
              file=sys.stderr)
        return None

    # The Sales & Trends report is per-VENDOR, not per-app: one TSV contains
    # every Teamz Lab app. Without this filter the script sums the whole
    # portfolio and attributes it to whichever app you happened to run it from.
    app_ids = {a.strip() for a in os.environ.get("TEAMZ_APP_IDS", "").split(",") if a.strip()}
    if not app_ids:
        print("[WARN] TEAMZ_APP_IDS is not set — cannot tell this app's rows apart from the "
              "rest of the vendor's portfolio. Refusing to report a number that would be "
              "the sum of every Teamz Lab app.", file=sys.stderr)
        return None

    token = _asc_jwt(issuer, key_id, p8)
    if not token:
        return None

    # Sales and Trends: one daily report per day (gzipped TSV)
    end = datetime.now(timezone.utc).date() - timedelta(days=1)
    daily = []
    for i in range(days):
        d = end - timedelta(days=i)
        url = (
            "https://api.appstoreconnect.apple.com/v1/salesReports"
            f"?filter[frequency]=DAILY"
            f"&filter[reportDate]={d.isoformat()}"
            f"&filter[reportType]=SALES"
            f"&filter[reportSubType]=SUMMARY"
            f"&filter[vendorNumber]={vendor}"
            "&filter[version]=1_1"
        )
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/a-gzip",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
        except Exception as e:
            # 404 is normal for dates with no sales — don't spam
            if "404" not in str(e):
                print(f"[warn] ASC {d}: {e}", file=sys.stderr)
            continue
        try:
            tsv = gzip.decompress(raw).decode("utf-8", errors="replace")
        except OSError:
            continue
        units = 0
        for row in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
            # Rows for OTHER apps in the same vendor account.
            if (row.get("Apple Identifier") or "").strip() not in app_ids:
                continue
            # Updates / re-downloads are not new users.
            if (row.get("Product Type Identifier") or "").strip() not in _ASC_DOWNLOAD_TYPES:
                continue
            try:
                units += int(row.get("Units", 0) or 0)
            except ValueError:
                pass
        daily.append((d.isoformat(), units))

    if not daily:
        return None
    daily.sort()
    total = sum(v for _, v in daily)
    avg = total / max(1, len(daily))
    trend = None
    if len(daily) >= 14:
        last7 = sum(v for _, v in daily[-7:])
        prev7 = sum(v for _, v in daily[-14:-7])
        trend = (last7 - prev7) / max(1, prev7) * 100

    return {
        "platform": "ios",
        "vendor": vendor,
        "period": f"{daily[0][0]} → {daily[-1][0]}",
        "days": len(daily),
        "total_units": total,
        "avg_units_per_day": round(avg, 1),
        "trend_pct_7d": round(trend, 1) if trend is not None else None,
        "daily_units": daily,
    }


# ─────────────────────────── Report & history ────────────────────────────────

def _write_report(snapshots: list[dict]):
    if not snapshots:
        return
    lines = [f"# ASO Velocity Report", f"_Generated {datetime.now(timezone.utc).isoformat()}_\n"]
    for s in snapshots:
        lines.append(f"## {s['platform'].upper()}")
        for k in ("package", "vendor", "period", "days", "total_installs", "total_units",
                  "total_uninstalls", "net_installs", "avg_installs_per_day",
                  "avg_units_per_day", "trend_pct_7d", "active_devices_latest",
                  "best_day_of_week"):
            if k in s and s[k] is not None:
                lines.append(f"- **{k}**: {s[k]}")
        lines.append("")
    (_DATA_DIR / "aso-velocity-report.md").write_text("\n".join(lines), encoding="utf-8")


def _append_history(snapshots: list[dict]):
    path = _DATA_DIR / "aso-velocity-history.csv"
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["timestamp", "platform", "period", "total", "avg_per_day",
                        "trend_pct_7d", "net_installs"])
        ts = datetime.now(timezone.utc).isoformat()
        for s in snapshots:
            total = s.get("total_installs") or s.get("total_units") or 0
            avg = s.get("avg_installs_per_day") or s.get("avg_units_per_day") or 0
            w.writerow([ts, s["platform"], s.get("period", ""), total, avg,
                        s.get("trend_pct_7d", ""), s.get("net_installs", "")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--platform", choices=["play", "ios", "both"], default="both")
    ap.add_argument("--history", action="store_true",
                    help="Append run to aso-velocity-history.csv for trending")
    args = ap.parse_args()

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = []

    if args.platform in ("play", "both"):
        print("  [info] Pulling Play Console velocity...", file=sys.stderr)
        play = _play_velocity(args.days)
        if play:
            snapshots.append(play)
            print(f"  [ok] Play: {play['total_installs']} installs over {play['days']}d "
                  f"(avg {play['avg_installs_per_day']}/day)", file=sys.stderr)

    if args.platform in ("ios", "both"):
        print("  [info] Pulling ASC Sales & Trends...", file=sys.stderr)
        ios = _asc_velocity(args.days)
        if ios:
            snapshots.append(ios)
            print(f"  [ok] ASC: {ios['total_units']} units over {ios['days']}d "
                  f"(avg {ios['avg_units_per_day']}/day)", file=sys.stderr)

    if not snapshots:
        print("[WARN] No data from any platform. Check credentials.", file=sys.stderr)
        return 1

    out = _DATA_DIR / "aso-velocity-latest.json"
    out.write_text(json.dumps(snapshots, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"  [ok] Wrote {out}", file=sys.stderr)

    _write_report(snapshots)
    if args.history:
        _append_history(snapshots)
        print(f"  [ok] Appended to aso-velocity-history.csv", file=sys.stderr)

    # Print quick summary
    print()
    for s in snapshots:
        trend = f" ({s['trend_pct_7d']:+.1f}% vs prior 7d)" if s.get("trend_pct_7d") is not None else ""
        total = s.get("total_installs") or s.get("total_units", 0)
        avg = s.get("avg_installs_per_day") or s.get("avg_units_per_day", 0)
        print(f"{s['platform'].upper():<5} {total:>7} total, {avg:>7.1f}/day{trend}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
