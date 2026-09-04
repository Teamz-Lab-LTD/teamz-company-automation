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
import re
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
    "https://www.googleapis.com/auth/devstorage.read_only",
)


def _credentials(json_path: Path):
    return service_account.Credentials.from_service_account_file(str(json_path), scopes=SCOPES)


def _bulk_bucket(creds) -> str:
    """Bulk reports bucket name = ``pubsite_prod_<devAccountId>``.

    The dev account id is part of the Play Console URL the user opens, e.g.
    ``play.google.com/console/u/0/developers/7194763656319643086/...``. We
    accept it via env var ``TEAMZ_PLAY_DEV_ACCOUNT_ID`` so this script stays
    org-agnostic. As a fallback we try to read it from
    ``play_dev_account_id`` in the runtime config.
    """
    raw = os.getenv("TEAMZ_PLAY_DEV_ACCOUNT_ID", "").strip()
    if not raw:
        raise RuntimeError(
            "Set TEAMZ_PLAY_DEV_ACCOUNT_ID to your Play developer account id "
            "(the long number in the Play Console URL after /developers/)."
        )
    return f"pubsite_prod_{raw}"


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


def _bulk_get(creds, bucket: str, name: str) -> Optional[bytes]:
    import google.auth.transport.requests
    import urllib.request
    import urllib.parse

    creds.refresh(google.auth.transport.requests.Request())
    encoded = urllib.parse.quote(name, safe="")
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{encoded}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {creds.token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except Exception:
        return None


def _parse_bulk_csv(blob: bytes) -> list[dict]:
    text = blob.decode("utf-16", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = [h.strip() for h in lines[0].split(",")]
    rows = []
    for ln in lines[1:]:
        cells = ln.split(",")
        if len(cells) < len(header):
            continue
        rows.append({header[i]: cells[i].strip() for i in range(len(header))})
    return rows


def cmd_bulk_reports(
    cfg: dict,
    package: str,
    months: int,
    out: Optional[Path],
) -> int:
    """Pull installs + store_performance + reviews from the bulk-reports bucket.

    Bulk-reports bucket is the only source for Play Console acquisition data
    — the Reporting API exposes only crash/ANR/render vitals. We fetch the
    last ``months`` months of CSVs and roll them up to a single JSON shaped
    for downstream content/ASO tools.
    """
    sa_path = _require_paths(cfg, package)
    creds = _credentials(sa_path)
    bucket = _bulk_bucket(creds)
    today = date.today()

    payload: Dict[str, Any] = {
        "package": package,
        "bucket": bucket,
        "generated_at": today.isoformat(),
        "months_requested": months,
        "installs": {"overview": [], "country": [], "language": [], "device": [], "os_version": [], "app_version": [], "carrier": []},
        "store_performance": {"country": [], "traffic_source": []},
        "reviews": [],
        "missing_files": [],
    }

    # The comment here used to say Play only writes a month's CSV after the month
    # closes. Wrong: hazira's 202608 file existed on 2026-09-04 with rows through
    # 08-21 — Play appends to the CURRENT month's file with a ~2-week lag. So try the
    # current month too (a missing blob costs one 404 and lands in missing_files),
    # then the ``months`` completed months before it.
    cursor = today.replace(day=1)
    yyyymm_list: list[str] = []
    for _ in range(months + 1):
        yyyymm_list.append(cursor.strftime("%Y%m"))
        prev = (cursor - timedelta(days=1)).replace(day=1)
        cursor = prev

    install_dims = ["overview", "country", "language", "device", "os_version", "app_version", "carrier"]
    perf_dims = ["country", "traffic_source"]

    for yyyymm in yyyymm_list:
        for dim in install_dims:
            name = f"stats/installs/installs_{package}_{yyyymm}_{dim}.csv"
            blob = _bulk_get(creds, bucket, name)
            if blob is None:
                payload["missing_files"].append(name)
                continue
            payload["installs"][dim].extend(_parse_bulk_csv(blob))

        for dim in perf_dims:
            name = f"stats/store_performance/store_performance_{package}_{yyyymm}_{dim}.csv"
            blob = _bulk_get(creds, bucket, name)
            if blob is None:
                payload["missing_files"].append(name)
                continue
            payload["store_performance"][dim].extend(_parse_bulk_csv(blob))

        name = f"reviews/reviews_{package}_{yyyymm}.csv"
        blob = _bulk_get(creds, bucket, name)
        if blob is not None:
            payload["reviews"].extend(_parse_bulk_csv(blob))

    # Roll up totals for the headline numbers any caller will want first.
    perf_country = payload["store_performance"]["country"]
    if perf_country:
        total_visitors = sum(int(r.get("Store listing visitors", 0) or 0) for r in perf_country)
        total_acq = sum(int(r.get("Store listing acquisitions", 0) or 0) for r in perf_country)
        payload["summary"] = {
            "total_store_listing_visitors": total_visitors,
            "total_store_listing_acquisitions": total_acq,
            "store_listing_conversion_rate": (total_acq / total_visitors) if total_visitors else 0.0,
        }

    install_overview = payload["installs"]["overview"]
    if install_overview:
        try:
            payload.setdefault("summary", {})["total_install_events"] = sum(
                int(r.get("Install events", 0) or 0) for r in install_overview
            )
            # Rows are appended newest-month-first, so install_overview[-1] is the
            # OLDEST month's last day. Sort by date before reading "latest".
            dated = sorted((r for r in install_overview if (r.get("Date") or "").strip()),
                           key=lambda r: r["Date"])
            latest = dated[-1] if dated else install_overview[-1]
            payload["summary"]["active_devices_latest"] = int(
                latest.get("Active Device Installs", 0) or 0
            )
            payload["summary"]["data_through"] = latest.get("Date")
        except Exception:
            pass

        # 28-day install/UNINSTALL roll-up for the fleet verdict. Added 2026-09-05:
        # the uninstall columns were in every row already and no summary surfaced
        # them, so the one number that explains a flat active-device count was
        # invisible. "Daily User Uninstalls" is the per-user figure; the "events"
        # columns count devices/re-installs and are the fallback when it is blank.
        try:
            def _i(r, *keys):
                for k in keys:
                    v = (r.get(k) or "").strip()
                    if v not in ("", "0") or k == keys[-1]:
                        try:
                            return int(float(v or 0))
                        except ValueError:
                            return 0
                return 0
            through = payload["summary"].get("data_through")
            if through:
                import datetime as _dt
                end = _dt.date.fromisoformat(through)
                start = end - _dt.timedelta(days=27)
                win = [r for r in dated if start.isoformat() <= r["Date"] <= end.isoformat()]
                payload["summary"]["window_28d"] = {
                    "start": start.isoformat(), "end": end.isoformat(), "days": len(win),
                    "user_installs": sum(_i(r, "Daily User Installs", "Install events") for r in win),
                    "user_uninstalls": sum(_i(r, "Daily User Uninstalls", "Uninstall events") for r in win),
                    "install_events": sum(_i(r, "Install events") for r in win),
                    "uninstall_events": sum(_i(r, "Uninstall events") for r in win),
                }
        except Exception as e:  # noqa: BLE001 — a roll-up bug must not lose the raw pull
            payload["summary"]["window_28d_error"] = f"{type(e).__name__}: {e}"

    reviews = payload.get("reviews") or []
    if reviews:
        try:
            stars = []
            for r in reviews:
                try:
                    stars.append(int(float((r.get("Star Rating") or "").strip() or 0)))
                except ValueError:
                    continue
            stars = [x for x in stars if 1 <= x <= 5]
            payload.setdefault("summary", {})["reviews_total"] = len(stars)
            payload["summary"]["reviews_avg_star"] = round(sum(stars) / len(stars), 2) if stars else None
            payload["summary"]["reviews_with_text"] = sum(1 for r in reviews if (r.get("Review Text") or "").strip())
        except Exception as e:  # noqa: BLE001
            payload["summary"]["reviews_error"] = f"{type(e).__name__}: {e}"

    if out is None:
        out = cfg["data_dir"] / f"play-bulk-reports-{package.replace('.', '-')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    if "summary" in payload:
        s = payload["summary"]
        print(
            "summary: visitors={v}  acquisitions={a}  conv={c:.2%}  "
            "installs={i}  active={ad}".format(
                v=s.get("total_store_listing_visitors", "?"),
                a=s.get("total_store_listing_acquisitions", "?"),
                c=s.get("store_listing_conversion_rate", 0.0),
                i=s.get("total_install_events", "?"),
                ad=s.get("active_devices_latest", "?"),
            )
        )
    return 0


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

    def _query(b):
        return reporting.vitals().crashrate().query(name=name, body=b).execute()

    try:
        try:
            resp = _query(body)
        except HttpError as e:
            # The API names its own freshness in the 400 — "should be at most the current
            # freshness 2026-09-02 00:00". A fixed 2-day lag is wrong whenever the run
            # happens after local midnight or Play is slow; take the date it gives us and
            # retry once instead of failing every app in the fleet (2026-09-05).
            err = e.content.decode() if e.content else str(e)
            m = re.search(r"current freshness (\d{4}-\d{2}-\d{2})", err) if e.resp.status == 400 else None
            if not m:
                raise
            fresh = date.fromisoformat(m.group(1))
            print(f"note: API freshness is {fresh}; retrying with that end date", file=sys.stderr)
            new_start = fresh - timedelta(days=max(1, days) - 1)
            body["timelineSpec"]["endTime"].update({"year": fresh.year, "month": fresh.month, "day": fresh.day})
            body["timelineSpec"]["startTime"].update({"year": new_start.year, "month": new_start.month, "day": new_start.day})
            resp = _query(body)
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
    # DEFAULTS ITS OUTPUT, like `bulk` above already does.
    #
    # It used not to, and the consequence was invisible for months: nightly-app.sh calls this as
    # `report --package X` with no --out, so the crash-rate report was printed to stdout and thrown
    # away. The step exited 0 every night, the nightly reported success, and automation_data/vitals.json
    # sat at a June snapshot — release monitoring was blind while looking exactly like it was working.
    #
    # That is the failure mode this repo keeps meeting from different directions: a command that
    # "refuses to work" is easy to spot, and a command that SUCCEEDS at doing nothing is not. A report
    # generator whose whole purpose is a file on disk should not have "print it and forget it" as its
    # default; --out still overrides, so any caller that wanted stdout can ask for it.
    if out is None:
        out = cfg["data_dir"] / "vitals.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out}")
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


# ── Company defaults (shared across all Teamz Lab apps) ──────────────────────
TEAMZ_CONTACT = {
    "email": "hello@teamzlab.com",
    "phone": "+44 7490 356046",
    "website": "https://teamzlab.com/",
}


def cmd_store_settings(cfg: dict, package: str, category: str, commit: bool) -> int:
    """Set app category, contact details, and default language via API."""
    sa_path = _require_paths(cfg, package)
    creds = _credentials(sa_path)
    pub = _publisher(creds)
    try:
        edit = pub.edits().insert(packageName=package, body={}).execute()
        eid = edit["id"]
        print(f"  Edit created: {eid}")

        # Set contact details + category via edits().details()
        details_body = {
            "contactEmail": TEAMZ_CONTACT["email"],
            "contactPhone": TEAMZ_CONTACT["phone"],
            "contactWebsite": TEAMZ_CONTACT["website"],
            "defaultLanguage": "en-US",
        }
        pub.edits().details().update(
            packageName=package, editId=eid, body=details_body
        ).execute()
        print(f"  Contact details set: {TEAMZ_CONTACT['email']}, {TEAMZ_CONTACT['phone']}")
        print(f"  Website: {TEAMZ_CONTACT['website']}")
        print(f"  Default language: en-US")

        if commit:
            try:
                pub.edits().commit(packageName=package, editId=eid).execute()
                print("  Committed store settings to Google Play.")
            except HttpError as commit_err:
                if commit_err.resp.status == 400:
                    print("  App is in draft state — settings saved but not published yet.")
                else:
                    raise
        else:
            pub.edits().delete(packageName=package, editId=eid).execute()
            print("  Dry-run OK: settings validated; draft discarded.")
    except HttpError as e:
        err = e.content.decode() if e.content else str(e)
        print(f"ERROR: {e.resp.status} {err[:800]}", file=sys.stderr)
        return 1

    # Note: Category and tags cannot be set via the Android Publisher API.
    # They must be set manually in Play Console → Store settings → App category.
    if category:
        print(f"\n  ⚠️ Category '{category}' must be set MANUALLY in Play Console.")
        print(f"     Go to: Store settings → App category → Edit → Select '{category}'")
        print(f"     Tags must also be set manually via 'Manage tags'.")

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
        print(f"  Edit created: {eid}")
        try:
            current = (
                pub.edits()
                .listings()
                .get(packageName=package, editId=eid, language=language)
                .execute()
            )
            print(f"  Fetched existing listing for {language}")
        except HttpError:
            # No existing listing for this language — start fresh
            current = {}
            print(f"  No existing listing for {language} — creating new")
        merged: Dict[str, Any] = dict(current)
        for k, v in data.items():
            if v is None:
                continue
            merged[k] = v
        allowed = {"title", "shortDescription", "fullDescription", "video"}
        body = {k: merged[k] for k in allowed if k in merged}
        print(f"  Updating listing: title='{body.get('title', '')[:30]}', short={len(body.get('shortDescription', ''))}c, desc={len(body.get('fullDescription', ''))}c")
        pub.edits().listings().update(
            packageName=package, editId=eid, language=language, body=body
        ).execute()
        print(f"  Listing updated for {language}")
        if commit:
            try:
                pub.edits().commit(packageName=package, editId=eid).execute()
                print("Committed listing changes to Google Play.")
            except HttpError as commit_err:
                err_body = str(commit_err.content) if commit_err.content else ""
                if "draft" in err_body.lower() or commit_err.resp.status == 400:
                    print("App is in draft state — listing saved but not published yet.")
                    print("Go to Play Console → Publishing overview to review and publish.")
                else:
                    raise
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


def _get_next_version_code(pub, package: str) -> Optional[int]:
    """Query Play Console for the highest existing versionCode and return next."""
    try:
        edit = pub.edits().insert(packageName=package, body={}).execute()
        eid = edit["id"]
        bundles = pub.edits().bundles().list(packageName=package, editId=eid).execute()
        pub.edits().delete(packageName=package, editId=eid).execute()
        codes = [int(b.get("versionCode", 0)) for b in bundles.get("bundles", [])]
        return max(codes) + 1 if codes else None
    except Exception:
        return None


def _bump_pubspec_version_code(project_root: Path, target_code: int) -> bool:
    """Bump versionCode in pubspec.yaml to target_code."""
    pubspec = project_root / "pubspec.yaml"
    if not pubspec.exists():
        return False
    import re
    text = pubspec.read_text()
    m = re.search(r'^(version:\s*\S+\+)(\d+)', text, re.MULTILINE)
    if not m:
        return False
    old_code = int(m.group(2))
    if old_code >= target_code:
        return False  # Already at or above target
    new_text = text[:m.start(2)] + str(target_code) + text[m.end(2):]
    pubspec.write_text(new_text)
    print(f"  Auto-bumped pubspec.yaml versionCode: {old_code} → {target_code}")
    return True


def cmd_upload(cfg: dict, package: str, aab_path: Path, track: str, release_name: str, notes: str, commit: bool) -> int:
    """Upload AAB to a Play Console track (internal/alpha/beta/production).

    If the AAB's versionCode already exists on Play, auto-bumps pubspec.yaml
    and rebuilds before uploading.
    """
    sa_path = _require_paths(cfg, package)
    creds = _credentials(sa_path)
    pub = _publisher(creds)

    # Check if we need to bump versionCode
    next_code = _get_next_version_code(pub, package)
    if next_code is not None:
        project_root = Path(cfg.get("host_site_root", "."))
        pubspec = project_root / "pubspec.yaml"
        if pubspec.exists():
            import re
            text = pubspec.read_text()
            m = re.search(r'^version:\s*\S+\+(\d+)', text, re.MULTILINE)
            if m:
                current_code = int(m.group(1))
                if current_code < next_code:
                    print(f"  ⚠️ versionCode {current_code} already used on Play. Need ≥{next_code}.")
                    _bump_pubspec_version_code(project_root, next_code)
                    # Rebuild AAB
                    build_script = project_root / "scripts" / "build-playstore-aab.sh"
                    if build_script.exists():
                        import subprocess
                        print(f"  Rebuilding AAB with versionCode {next_code}...")
                        result = subprocess.run(
                            ["bash", str(build_script)],
                            cwd=str(project_root),
                            capture_output=True, text=True
                        )
                        if result.returncode != 0:
                            print(f"ERROR: Build failed:\n{result.stderr[-500:]}", file=sys.stderr)
                            return 1
                        # Find the new AAB
                        import glob
                        new_aabs = sorted(glob.glob(str(project_root / "dist" / f"*versionCode{next_code}*.aab")))
                        if new_aabs:
                            aab_path = Path(new_aabs[-1])
                            print(f"  Using rebuilt AAB: {aab_path.name}")
                        else:
                            print("ERROR: Rebuilt AAB not found in dist/", file=sys.stderr)
                            return 1
                    else:
                        print("ERROR: build-playstore-aab.sh not found — bump pubspec manually and rebuild.", file=sys.stderr)
                        return 1

    try:
        # Create edit
        edit = pub.edits().insert(packageName=package, body={}).execute()
        eid = edit["id"]
        print(f"  Edit created: {eid}")

        # Upload AAB
        from googleapiclient.http import MediaFileUpload
        media = MediaFileUpload(str(aab_path), mimetype="application/octet-stream", resumable=True)
        print(f"  Uploading {aab_path.name} ({aab_path.stat().st_size / 1024 / 1024:.1f} MB)...")
        bundle = pub.edits().bundles().upload(
            packageName=package, editId=eid, media_body=media
        ).execute()
        version_code = bundle["versionCode"]
        print(f"  Uploaded: versionCode={version_code}")

        # Assign to track
        # Always use "draft" for the release status.
        # The edit commit/discard controls whether changes go live.
        # Using "completed" fails on draft/unpublished apps.
        track_body: Dict[str, Any] = {
            "track": track,
            "releases": [{
                "versionCodes": [str(version_code)],
                "status": "draft",
            }],
        }
        if release_name:
            track_body["releases"][0]["name"] = release_name
        if notes:
            track_body["releases"][0]["releaseNotes"] = [
                {"language": "en-US", "text": notes}
            ]

        pub.edits().tracks().update(
            packageName=package, editId=eid, track=track, body=track_body
        ).execute()
        print(f"  Assigned to track: {track} (status=draft)")

        # Validate
        pub.edits().validate(packageName=package, editId=eid).execute()
        print("  Validation passed.")

        if commit:
            pub.edits().commit(packageName=package, editId=eid).execute()
            print(f"  Committed! Release is live on '{track}' track.")
        else:
            pub.edits().delete(packageName=package, editId=eid).execute()
            print(f"  Dry-run OK: validated and discarded. Re-run with --commit to publish.")

    except HttpError as e:
        err = e.content.decode() if e.content else str(e)
        print(f"ERROR: {e.resp.status} {err[:1000]}", file=sys.stderr)
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

    p_settings = sub.add_parser("store-settings", help="Set contact details + category hint via API")
    p_settings.add_argument("--package", help=pkg_help)
    p_settings.add_argument("--category", default="Shopping", help="Category name (set manually in console, printed as reminder)")
    p_settings.add_argument("--commit", action="store_true", help="Commit changes")

    p_bulk = sub.add_parser(
        "bulk-reports",
        help="Pull installs + store_performance + reviews CSVs from the bulk-reports GCS bucket",
    )
    p_bulk.add_argument("--package", help=pkg_help)
    p_bulk.add_argument("--months", type=int, default=3, help="How many recent months to pull (default 3)")
    p_bulk.add_argument("--out", type=Path, help="Output JSON path (default: TEAMZ_DATA_DIR/play-bulk-reports-<pkg>.json)")

    p_upload = sub.add_parser("upload", help="Upload AAB to a Play Console track")
    p_upload.add_argument("--package", help=pkg_help)
    p_upload.add_argument("--aab", type=Path, required=True, help="Path to .aab file")
    p_upload.add_argument("--track", default="internal", choices=["internal", "alpha", "beta", "production"],
                          help="Target track (default: internal)")
    p_upload.add_argument("--release-name", default="", help="Release name (e.g. '1.0.0 (1)')")
    p_upload.add_argument("--notes", default="", help="Release notes text (en-US)")
    p_upload.add_argument("--commit", action="store_true",
                          help="Commit the release. Without this, validates then discards.")

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
    if args.cmd == "store-settings":
        return cmd_store_settings(cfg, pkg, args.category, args.commit)
    if args.cmd == "listing-push":
        return cmd_listing_push(cfg, pkg, args.file, args.commit)
    if args.cmd == "upload":
        return cmd_upload(cfg, pkg, args.aab, args.track, args.release_name, args.notes, args.commit)
    if args.cmd == "bulk-reports":
        return cmd_bulk_reports(cfg, pkg, args.months, args.out)
    return 1


if __name__ == "__main__":
    sys.exit(main())
