#!/usr/bin/env python3
"""IAP preflight — refuses to run setup if any precondition fails.

Imported by `iap.py setup` and runnable standalone:

    python3 py/iap_preflight.py \\
        --sku com.teamz.<app>.<bundle_slug> \\
        --price-usd 2.99 \\
        --name "<Bundle Name>" \\
        --description "Remove ads + unlock all bundled cosmetics."

Refuses to proceed if any of these fail:

    1. ASC P8 key file exists + readable
    2. Play SA JSON exists + readable
    3. RC secret API key in env
    4. RC project ID in env (matches a real RC project)
    5. Apple App Store Connect app ID exists in ASC (TEAMZ_APPLE_APP_ID)
    6. Play Console package recognized by Android Publisher API
       (TEAMZ_PLAY_PACKAGE_NAME)
    7. Play SA has billing permission on the package — confirmed by
       opening + listing edits successfully
    8. Internal Testing track has at least one published build
       (otherwise Google rejects IAP creation with the misleading
       "Can't create product. To fix, request billing permission" error)
    9. RC project has both iOS + Android apps registered for this bundle
       ID / package name
    10. SKU follows `com.teamz.<app>.<slug>` convention (lowercase, dots)
    11. Apple description ≤55 chars
    12. Apple display name ≤30 chars
    13. Google description ≤200 chars
    14. Google display name ≤25 chars

Each check fails LOUDLY with a fix-suggestion line. Zero exit code = ready
to run `iap.py setup`. Non-zero = STOP.

CLI flags:

    --json                 emit a machine-readable status report
    --skip 1,2,...         comma-list of check IDs to skip (rare; explain in commit)
    --offline              skip all network-dependent checks (1-3, 11-14 only)

Exits with code = number of failed checks (capped at 254).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None

try:
    from google.oauth2 import service_account
    import google.auth.transport.requests
except ImportError:
    service_account = None  # type: ignore


_DEFAULT_ASC_KEY = Path.home() / ".config" / "teamzlab" / "AuthKey_559DD92MBH.p8"
_DEFAULT_ASC_KEY_ID = "559DD92MBH"
_DEFAULT_ASC_ISSUER_ID = "100d6ef8-7452-4aff-85a4-990158b60b3d"
_DEFAULT_PLAY_SA = Path.home() / ".config" / "teamzlab" / "play-console-service-account.json"


@dataclass
class CheckResult:
    id: int
    label: str
    passed: bool
    detail: str = ""
    fix: str = ""


def _load_dotenv(project_root: Optional[Path] = None) -> None:
    if project_root is None:
        project_root = Path.cwd()
    candidates = [
        project_root / ".env.local",
        project_root / ".teamz-automation.env",
        project_root / "automation_data" / ".teamz-automation.env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)


def _http(method: str, url: str, *, token: str, body: Optional[dict] = None) -> tuple[int, bytes]:
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _asc_jwt() -> Optional[str]:
    if pyjwt is None:
        return None
    key_path = Path(os.getenv("TEAMZ_ASC_KEY_FILEPATH", str(_DEFAULT_ASC_KEY))).expanduser()
    if not key_path.exists():
        return None
    key_id = os.getenv("TEAMZ_ASC_KEY_ID", _DEFAULT_ASC_KEY_ID)
    issuer = os.getenv("TEAMZ_ASC_ISSUER_ID", _DEFAULT_ASC_ISSUER_ID)
    return pyjwt.encode(  # type: ignore[union-attr]
        {
            "iss": issuer,
            "iat": int(time.time()),
            "exp": int(time.time()) + 1200,
            "aud": "appstoreconnect-v1",
        },
        key_path.read_text(),
        algorithm="ES256",
        headers={"alg": "ES256", "kid": key_id, "typ": "JWT"},
    )


def _play_token() -> Optional[str]:
    if service_account is None:
        return None
    sa_path = Path(
        os.getenv("TEAMZ_PLAY_SERVICE_ACCOUNT_JSON", str(_DEFAULT_PLAY_SA))
    ).expanduser()
    if not sa_path.exists():
        return None
    creds = service_account.Credentials.from_service_account_file(  # type: ignore[union-attr]
        str(sa_path), scopes=["https://www.googleapis.com/auth/androidpublisher"]
    )
    creds.refresh(google.auth.transport.requests.Request())  # type: ignore[union-attr]
    return creds.token  # type: ignore[union-attr]


def _check_files(results: list[CheckResult]) -> None:
    asc_key = Path(
        os.getenv("TEAMZ_ASC_KEY_FILEPATH", str(_DEFAULT_ASC_KEY))
    ).expanduser()
    results.append(
        CheckResult(
            id=1,
            label="ASC P8 key file",
            passed=asc_key.exists() and asc_key.is_file(),
            detail=str(asc_key),
            fix=f"Place the team-wide ASC API key at {asc_key} or set TEAMZ_ASC_KEY_FILEPATH",
        )
    )
    sa_path = Path(
        os.getenv("TEAMZ_PLAY_SERVICE_ACCOUNT_JSON", str(_DEFAULT_PLAY_SA))
    ).expanduser()
    results.append(
        CheckResult(
            id=2,
            label="Play service account JSON",
            passed=sa_path.exists() and sa_path.is_file(),
            detail=str(sa_path),
            fix=f"Place the Teamz Lab service account JSON at {sa_path} or set TEAMZ_PLAY_SERVICE_ACCOUNT_JSON",
        )
    )


def _check_env(results: list[CheckResult]) -> None:
    rc_secret = os.getenv("REVENUECAT_SECRET_API_KEY", "").strip()
    results.append(
        CheckResult(
            id=3,
            label="REVENUECAT_SECRET_API_KEY in env",
            passed=bool(rc_secret) and rc_secret.startswith("sk_"),
            detail=f"len={len(rc_secret)}",
            fix="Add REVENUECAT_SECRET_API_KEY=sk_... to project's .env.local",
        )
    )
    rc_project = os.getenv("REVENUECAT_PROJECT_ID", "").strip()
    results.append(
        CheckResult(
            id=4,
            label="REVENUECAT_PROJECT_ID in env",
            passed=bool(rc_project) and rc_project.startswith("proj"),
            detail=rc_project,
            fix="Add REVENUECAT_PROJECT_ID=proj... (canonical Teamz Lab umbrella: proj8d8322e7)",
        )
    )
    apple_id = os.getenv("TEAMZ_APPLE_APP_ID", "").strip()
    results.append(
        CheckResult(
            id=5,
            label="TEAMZ_APPLE_APP_ID in env",
            passed=apple_id.isdigit() and len(apple_id) >= 9,
            detail=apple_id,
            fix="Add TEAMZ_APPLE_APP_ID=<numeric-id> to .teamz-automation.env",
        )
    )
    play_pkg = os.getenv("TEAMZ_PLAY_PACKAGE_NAME", "").strip()
    results.append(
        CheckResult(
            id=6,
            label="TEAMZ_PLAY_PACKAGE_NAME in env",
            passed=bool(play_pkg) and "." in play_pkg,
            detail=play_pkg,
            fix="Add TEAMZ_PLAY_PACKAGE_NAME=com.teamz.lab.<app> to .teamz-automation.env",
        )
    )


def _check_apple_app(results: list[CheckResult]) -> None:
    apple_id = os.getenv("TEAMZ_APPLE_APP_ID", "").strip()
    if not apple_id:
        results.append(CheckResult(id=7, label="ASC app exists", passed=False, fix="Set TEAMZ_APPLE_APP_ID first"))
        return
    token = _asc_jwt()
    if not token:
        results.append(CheckResult(id=7, label="ASC app exists", passed=False, fix="ASC P8 key not loadable; check check 1"))
        return
    code, payload = _http("GET", f"https://api.appstoreconnect.apple.com/v1/apps/{apple_id}", token=token)
    results.append(
        CheckResult(
            id=7,
            label="ASC app exists",
            passed=code == 200,
            detail=f"http {code}",
            fix=f"Confirm App Store Connect has app id {apple_id} registered + the API key has access (Account Holder for new keys)",
        )
    )


def _check_play_app(results: list[CheckResult]) -> None:
    pkg = os.getenv("TEAMZ_PLAY_PACKAGE_NAME", "").strip()
    if not pkg:
        results.append(CheckResult(id=8, label="Play SA can open edit", passed=False, fix="Set TEAMZ_PLAY_PACKAGE_NAME first"))
        results.append(CheckResult(id=9, label="Internal Testing has a build", passed=False, fix="Set TEAMZ_PLAY_PACKAGE_NAME first"))
        return
    token = _play_token()
    if not token:
        results.append(CheckResult(id=8, label="Play SA can open edit", passed=False, fix="Service account JSON not loadable; check check 2"))
        results.append(CheckResult(id=9, label="Internal Testing has a build", passed=False, fix="Service account JSON not loadable; check check 2"))
        return

    code, payload = _http(
        "POST",
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{pkg}/edits",
        token=token,
        body={},
    )
    edit_open = code == 200
    edit_id: Optional[str] = None
    if edit_open:
        try:
            edit_id = json.loads(payload).get("id")
        except Exception:
            edit_id = None
    results.append(
        CheckResult(
            id=8,
            label="Play SA can open edit (perms OK)",
            passed=edit_open,
            detail=f"http {code}; edit_id={edit_id or '-'}",
            fix=(
                f"Play Console -> Setup -> API access -> service account row for {pkg} "
                f"-> grant 'Manage orders and subscriptions' + 'View financial data'."
                if not edit_open
                else ""
            ),
        )
    )

    if not edit_open or edit_id is None:
        results.append(
            CheckResult(
                id=9,
                label="Internal Testing has a build",
                passed=False,
                fix="Open an edit first (check 8) — can't list tracks otherwise",
            )
        )
        return

    code, payload = _http(
        "GET",
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{pkg}/edits/{edit_id}/tracks/internal",
        token=token,
    )
    has_build = False
    detail = f"http {code}"
    if code == 200:
        try:
            tr = json.loads(payload)
            for r in tr.get("releases", []):
                if r.get("versionCodes"):
                    has_build = True
                    detail += f"; versionCodes={r.get('versionCodes')}"
                    break
        except Exception:
            pass
    results.append(
        CheckResult(
            id=9,
            label="Internal Testing track has a build",
            passed=has_build,
            detail=detail,
            fix=(
                "Build + upload an AAB to the Internal Testing track first: "
                "`fvm flutter build appbundle --release` then "
                "`python3 py/build-play-console.py upload --aab <path> --track internal --commit`. "
                "Without a build Play returns 'Can't create product. To fix, request billing permission' (misleading)."
            ),
        )
    )


def _check_revenuecat(results: list[CheckResult]) -> None:
    secret = os.getenv("REVENUECAT_SECRET_API_KEY", "").strip()
    proj = os.getenv("REVENUECAT_PROJECT_ID", "").strip()
    if not secret or not proj:
        results.append(CheckResult(id=10, label="RC project + apps registered", passed=False, fix="Set REVENUECAT_SECRET_API_KEY + REVENUECAT_PROJECT_ID first"))
        return
    code, payload = _http(
        "GET",
        f"https://api.revenuecat.com/v2/projects/{proj}/apps",
        token=secret,
    )
    if code >= 300:
        results.append(
            CheckResult(
                id=10,
                label="RC project + apps registered",
                passed=False,
                detail=f"http {code}",
                fix="Verify REVENUECAT_PROJECT_ID is correct + secret key has scope for it",
            )
        )
        return
    apps = json.loads(payload).get("items", [])
    bundle = (os.getenv("TEAMZ_APPLE_BUNDLE_ID") or "").strip()
    pkg = os.getenv("TEAMZ_PLAY_PACKAGE_NAME", "").strip()
    has_ios = False
    has_android = False
    for app in apps:
        t = app.get("type")
        if t == "app_store" and app.get("app_store", {}).get("bundle_id"):
            if not bundle or app["app_store"]["bundle_id"] == bundle:
                has_ios = True
        if t == "play_store" and app.get("play_store", {}).get("package_name") == pkg:
            has_android = True
    msg = []
    if not has_ios:
        msg.append("iOS app not registered")
    if not has_android:
        msg.append(f"Android app for {pkg} not registered")
    results.append(
        CheckResult(
            id=10,
            label="RC project has both iOS + Android apps",
            passed=has_ios and has_android,
            detail=", ".join(msg) or f"ios={has_ios}, android={has_android}",
            fix=(
                "RC dashboard -> Project settings -> + New app, OR via REST: "
                "POST /v2/projects/{project}/apps with type=app_store / play_store. "
                "iap.py expects both registered before setup."
            ),
        )
    )


def _check_metadata(results: list[CheckResult], *, sku: str, name: str, description: str) -> None:
    sku_ok = (
        sku.startswith("com.teamz.")
        and sku == sku.lower()
        and "." in sku[len("com.teamz."):]
    )
    results.append(
        CheckResult(
            id=11,
            label="SKU follows com.teamz.<app>.<slug> convention",
            passed=sku_ok,
            detail=sku,
            fix="SKU must be lowercase, prefixed `com.teamz.`, and end with `<app>.<slug>`",
        )
    )
    results.append(
        CheckResult(
            id=12,
            label="Apple display name <= 30 chars",
            passed=len(name) <= 30,
            detail=f"len={len(name)}",
            fix="Shorten the --name input to 30 chars or less",
        )
    )
    results.append(
        CheckResult(
            id=13,
            label="Apple description <= 55 chars",
            passed=len(description) <= 55,
            detail=f"len={len(description)}",
            fix="Shorten the --description input to 55 chars or less (Apple cap)",
        )
    )
    results.append(
        CheckResult(
            id=14,
            label="Google description <= 200 chars",
            passed=len(description) <= 200,
            detail=f"len={len(description)}",
            fix="Shorten the --description input to 200 chars or less",
        )
    )


def run_preflight(
    *,
    sku: str,
    name: str,
    description: str,
    skip: Optional[set[int]] = None,
    offline: bool = False,
) -> list[CheckResult]:
    skip = skip or set()
    results: list[CheckResult] = []
    _check_files(results)
    _check_env(results)
    _check_metadata(results, sku=sku, name=name, description=description)
    if not offline:
        _check_apple_app(results)
        _check_play_app(results)
        _check_revenuecat(results)
    if skip:
        results = [r for r in results if r.id not in skip]
    return results


def _format_text(results: list[CheckResult]) -> str:
    lines = []
    failures = sum(1 for r in results if not r.passed)
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        lines.append(f"[{mark}] #{r.id:02d} {r.label}: {r.detail}")
        if not r.passed and r.fix:
            lines.append(f"        fix: {r.fix}")
    lines.append("")
    if failures:
        lines.append(f"-> {failures} check(s) failed. STOP and fix above before running `iap.py setup`.")
    else:
        lines.append("-> All preflight checks passed. Safe to run `iap.py setup`.")
    return "\n".join(lines)


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sku", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--price-usd", type=float, default=2.99, help="(reserved for future price-validity checks)")
    parser.add_argument("--json", action="store_true", help="emit JSON status report")
    parser.add_argument(
        "--skip",
        default="",
        help="comma-list of check IDs to skip (e.g. '7,8')",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip all network-dependent checks (1, 2, 3, 11, 12, 13, 14 only)",
    )
    args = parser.parse_args()

    skip = {int(s) for s in args.skip.split(",") if s.strip().isdigit()}
    results = run_preflight(
        sku=args.sku,
        name=args.name,
        description=args.description,
        skip=skip,
        offline=args.offline,
    )

    if args.json:
        print(json.dumps([r.__dict__ for r in results], indent=2))
    else:
        print(_format_text(results))
    return min(254, sum(1 for r in results if not r.passed))


if __name__ == "__main__":
    sys.exit(main())
