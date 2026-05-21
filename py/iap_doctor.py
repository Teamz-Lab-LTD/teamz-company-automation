#!/usr/bin/env python3
"""IAP doctor — runtime diagnosis for a LIVE app whose purchases fail or
whose entitlement never activates.

Different from `iap_preflight.py`: preflight is a BEFORE-you-create gate.
This is an AFTER-it-broke diagnosis. Run it the moment a user reports
"I bought it but still see ads", or the app log shows purchase errors.

    cd <app project root>
    python3 team_mvp_kit/teamz-company-automation/py/iap_doctor.py
    # with a failing purchase token pulled from the app log:
    python3 team_mvp_kit/teamz-company-automation/py/iap_doctor.py \\
        --purchase-token <token> --sku com.teamz.<app>.<bundle_slug>

Always run from the host app's project root — it reads `.env.local` +
`.teamz-automation.env` from the current directory.

Checks (each PASS / FAIL with a fix line):

    1. RC secret key + project id present in env
    2. Play package name present in env
    3. RC project reachable with the secret key — catches a wrong key /
       wrong project (e.g. a RevenueCat MCP key bound to a different
       account). For TeamzLab apps ALWAYS use the REST secret key from
       .env.local, never the MCP.
    4. RC standard entitlement `remove_ads` exists
    5. Products attached to the entitlement — an entitlement with zero
       products = "buys succeed but the entitlement never grants"
    6. RC has both an app_store and a play_store app registered
    7. Play service account validates against the live Google Play API
    8. RC <-> Play credential link — THE #1 silent revenue killer.
       RevenueCat cannot validate Android purchases when no Service
       Account Credentials JSON is uploaded to the RC dashboard. The
       REST API does not expose this, so:
         * with --purchase-token: probes the token against Google. A
           purchase that is purchaseState=0 (valid) yet still
           acknowledgementState=0 after >10 min means RevenueCat is not
           acknowledging it -> the credential link is broken.
         * without a token: prints the manual dashboard check + the
           exact app-log symptom string to grep for.

Exit code = number of failed checks (capped at 254). Zero = healthy.

Symptom this tool exists to catch fast (chopstick_landing_games,
2026-05-22): every Android purchase failed with `InvalidCredentialsError
/ Invalid Play Store credentials`, entitlement never granted, IAP
revenue read $0 — because the RC dashboard had no Play service-account
credentials uploaded. Took 5 manual investigation rounds; this script
makes it one command.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

# Reuse the preflight helpers — same directory, already battle-tested.
from iap_preflight import CheckResult, _http, _load_dotenv, _play_token

RC_BASE = "https://api.revenuecat.com/v2"
PLAY_BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3"
STANDARD_ENTITLEMENT = "remove_ads"          # Teamz Lab standard lookup key
BUNDLE_TYPES = {"one_time", "non_consumable"}  # the $2.99 single-SKU pattern
ACK_GRACE_SECONDS = 600                       # 10 min: past this, unacked = broken


def _rc_get(path: str, token: str) -> tuple[int, dict]:
    code, body = _http("GET", f"{RC_BASE}{path}", token=token)
    try:
        return code, (json.loads(body) if body else {})
    except Exception:
        return code, {}


def _check_env(results: list[CheckResult]) -> tuple[str, str, str]:
    secret = os.getenv("REVENUECAT_SECRET_API_KEY", "").strip()
    proj = os.getenv("REVENUECAT_PROJECT_ID", "").strip()
    pkg = os.getenv("TEAMZ_PLAY_PACKAGE_NAME", "").strip()
    results.append(CheckResult(
        id=1,
        label="RC secret key + project id in env",
        passed=secret.startswith("sk_") and proj.startswith("proj"),
        detail=f"key={'set' if secret else 'MISSING'}, project={proj or 'MISSING'}",
        fix="Add REVENUECAT_SECRET_API_KEY=sk_... and REVENUECAT_PROJECT_ID=proj... "
            "to the app's .env.local (gitignored). TeamzLab umbrella project is "
            "proj8d8322e7. Never use the RevenueCat MCP — its key is bound to a "
            "different account and returns 403 for TeamzLab projects.",
    ))
    results.append(CheckResult(
        id=2,
        label="Play package name in env",
        passed=bool(pkg) and "." in pkg,
        detail=pkg or "MISSING",
        fix="Add TEAMZ_PLAY_PACKAGE_NAME=com.teamz.lab.<app> to .teamz-automation.env",
    ))
    return secret, proj, pkg


def _check_revenuecat(results: list[CheckResult], secret: str, proj: str) -> None:
    if not secret or not proj:
        for cid, label in ((3, "RC project reachable"),
                            (4, f"Entitlement '{STANDARD_ENTITLEMENT}' exists"),
                            (5, "Products attached to entitlement"),
                            (6, "RC has iOS + Android apps")):
            results.append(CheckResult(id=cid, label=label, passed=False,
                                       fix="Fix env checks 1-2 first"))
        return

    # Check 3 — reachability. GET /v2/projects/{id} alone is not a v2 API
    # endpoint (returns 404); only sub-resources are. Probe /entitlements,
    # and reuse that same response for check 4 so it is not called twice.
    code, body = _rc_get(f"/projects/{proj}/entitlements", secret)
    reachable = code == 200
    results.append(CheckResult(
        id=3,
        label="RC project reachable with secret key",
        passed=reachable,
        detail=f"http {code}",
        fix="403 = the secret key does not belong to this project. "
            "404 = REVENUECAT_PROJECT_ID is wrong. Confirm both values in "
            ".env.local match (TeamzLab umbrella project = proj8d8322e7). "
            "Never use the RevenueCat MCP for TeamzLab apps — its key is "
            "bound to a different account.",
    ))
    if not reachable:
        for cid, label in ((4, f"Entitlement '{STANDARD_ENTITLEMENT}' exists"),
                           (5, "Products attached to entitlement"),
                           (6, "RC has iOS + Android apps")):
            results.append(CheckResult(id=cid, label=label, passed=False,
                                       fix="Fix check 3 first"))
        return

    # Check 4 — entitlement exists (reuses `body` from the check-3 call).
    ent_id = None
    for ent in body.get("items", []):
        if ent.get("lookup_key") == STANDARD_ENTITLEMENT:
            ent_id = ent.get("id")
            break
    results.append(CheckResult(
        id=4,
        label=f"Entitlement '{STANDARD_ENTITLEMENT}' exists",
        passed=ent_id is not None,
        detail=ent_id or "not found",
        fix=f"Create the entitlement with lookup key '{STANDARD_ENTITLEMENT}' "
            "in the RC dashboard. Every TeamzLab app standardizes on it.",
    ))

    # Check 5 — products attached to the entitlement.
    if ent_id:
        code, body = _rc_get(
            f"/projects/{proj}/entitlements/{ent_id}/products", secret)
        prods = body.get("items", [])
        types = {p.get("type") for p in prods}
        stores = {p.get("store") for p in prods}
        bad_type = bool(types) and not (types & BUNDLE_TYPES)
        results.append(CheckResult(
            id=5,
            label="Products attached to entitlement",
            passed=len(prods) >= 1 and not bad_type,
            detail=f"{len(prods)} product(s), types={sorted(t for t in types if t)}, "
                   f"stores={sorted(s for s in stores if s)}",
            fix="Attach the store products to the entitlement in the RC "
                "dashboard (Entitlements -> remove_ads -> Attach). Zero "
                "attached products = purchases succeed but the entitlement "
                "never activates. For the $2.99 bundle the type must be "
                "one_time / non_consumable, never subscription.",
        ))
    else:
        results.append(CheckResult(
            id=5, label="Products attached to entitlement", passed=False,
            fix="Fix check 4 first"))

    # Check 6 — both apps registered.
    code, body = _rc_get(f"/projects/{proj}/apps", secret)
    apps = body.get("items", [])
    has_ios = any(a.get("type") == "app_store" for a in apps)
    has_android = any(a.get("type") == "play_store" for a in apps)
    results.append(CheckResult(
        id=6,
        label="RC has iOS + Android apps registered",
        passed=has_ios and has_android,
        detail=f"ios={has_ios}, android={has_android}",
        fix="Register the missing platform app in the RC dashboard "
            "(Project settings -> Apps -> + New).",
    ))


def _check_play_sa(results: list[CheckResult], pkg: str) -> None:
    if not pkg:
        results.append(CheckResult(id=7, label="Play service account works",
                                   passed=False, fix="Fix check 2 first"))
        return
    try:
        token = _play_token()
    except Exception as e:  # noqa: BLE001
        token = None
        results.append(CheckResult(
            id=7, label="Play service account works", passed=False,
            detail=f"token mint failed: {e}",
            fix="Service account JSON is missing or malformed at "
                "~/.config/teamzlab/play-console-service-account.json",
        ))
        return
    if not token:
        results.append(CheckResult(
            id=7, label="Play service account works", passed=False,
            fix="Place the Teamz Lab service account JSON at "
                "~/.config/teamzlab/play-console-service-account.json",
        ))
        return
    code, _ = _http("GET", f"{PLAY_BASE}/applications/{pkg}/reviews", token=token)
    results.append(CheckResult(
        id=7,
        label="Play service account works against Google API",
        passed=code == 200,
        detail=f"http {code}",
        fix="401/403 = the service account lacks permission on this app, or "
            "the Google Play Android Developer API is not enabled. Play "
            "Console -> Setup -> API access -> grant 'View financial data' + "
            "'Manage orders and subscriptions' to the service account.",
    ))


def _check_credential_link(results: list[CheckResult], pkg: str,
                           sku: str, token: str) -> None:
    """Check 8 — the RC <-> Play credential link. The silent revenue killer."""
    if not (token and sku and pkg):
        results.append(CheckResult(
            id=8,
            label="RC <-> Play credential link (manual — pass a token to auto-check)",
            passed=True,
            detail="no --purchase-token given",
            fix="",
        ))
        print(
            "\n  NOTE check 8: the REST API cannot see whether the RC dashboard\n"
            "  has Play Service Account credentials uploaded. Verify by hand:\n"
            "    RC dashboard -> the Android app -> Service Account Credentials\n"
            "    JSON must be uploaded (drag in "
            "~/.config/teamzlab/play-console-service-account.json).\n"
            "  App-log symptom when missing: 'InvalidCredentialsError /\n"
            "  Invalid Play Store credentials'. Re-run with --purchase-token\n"
            "  <token> --sku <sku> (pull the token from the app log) to turn\n"
            "  this into a hard PASS/FAIL.\n"
        )
        return

    try:
        sa_token = _play_token()
    except Exception:  # noqa: BLE001
        sa_token = None
    if not sa_token:
        results.append(CheckResult(
            id=8, label="RC <-> Play credential link", passed=False,
            fix="Fix check 7 first — service account not loadable"))
        return

    url = (f"{PLAY_BASE}/applications/{pkg}/purchases/products/"
           f"{sku}/tokens/{token}")
    code, body = _http("GET", url, token=sa_token)
    if code != 200:
        results.append(CheckResult(
            id=8, label="RC <-> Play credential link", passed=False,
            detail=f"purchase lookup http {code}",
            fix="Token may be wrong/stale, or sku mismatch. Re-copy both "
                "from a recent app-log purchase line.",
        ))
        return

    try:
        d = json.loads(body)
    except Exception:  # noqa: BLE001
        d = {}
    pstate = d.get("purchaseState")
    ack = d.get("acknowledgementState")
    ms = int(d.get("purchaseTimeMillis", "0") or "0")
    age = time.time() - ms / 1000.0 if ms else 0.0

    if pstate == 1:
        results.append(CheckResult(
            id=8,
            label="RC <-> Play credential link",
            passed=False,
            detail="purchase is CANCELED (purchaseState=1)",
            fix="An unacknowledged purchase Google auto-voids after ~3 days. "
                "The usual root cause is RevenueCat never acknowledged it "
                "because the RC dashboard has no Play credentials. Upload the "
                "Service Account JSON to the RC Android app, then test with a "
                "fresh purchase.",
        ))
        return
    if pstate == 0 and ack == 1:
        results.append(CheckResult(
            id=8,
            label="RC <-> Play credential link",
            passed=True,
            detail="purchase validated AND acknowledged by RevenueCat",
        ))
        return
    if pstate == 0 and ack == 0 and age > ACK_GRACE_SECONDS:
        results.append(CheckResult(
            id=8,
            label="RC <-> Play credential link",
            passed=False,
            detail=f"valid purchase still UNACKNOWLEDGED after {age/60:.0f} min",
            fix="RevenueCat is not acknowledging the purchase -> it cannot "
                "validate it. Upload the Play Service Account Credentials "
                "JSON to the RC dashboard (the Android app -> Service Account "
                "Credentials). Then trigger restorePurchases() in the app.",
        ))
        return
    # purchaseState 0, ack 0, fresh — inconclusive.
    results.append(CheckResult(
        id=8,
        label="RC <-> Play credential link",
        passed=True,
        detail=f"purchase too fresh ({age/60:.1f} min) — re-run after 10 min "
               "if the entitlement has not activated",
    ))


def _format(results: list[CheckResult]) -> str:
    lines = []
    failures = sum(1 for r in results if not r.passed)
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        lines.append(f"[{mark}] #{r.id:02d} {r.label}: {r.detail}")
        if not r.passed and r.fix:
            lines.append(f"        fix: {r.fix}")
    lines.append("")
    if failures:
        lines.append(f"-> {failures} check(s) failed. The failing line's fix "
                     "is the IAP bug. Start there.")
    else:
        lines.append("-> All checks passed. IAP wiring is healthy. If a user "
                     "still reports a problem, it is device-side (wrong store "
                     "account, no network, app build stale).")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Runtime IAP / RevenueCat diagnosis for a live app.")
    parser.add_argument("--purchase-token", default="",
                        help="a purchase token from the app log (enables check 8)")
    parser.add_argument("--sku", default="",
                        help="the product id for --purchase-token")
    parser.add_argument("--json", action="store_true",
                        help="emit a machine-readable report")
    args = parser.parse_args()

    _load_dotenv()  # reads .env.local + .teamz-automation.env from cwd
    results: list[CheckResult] = []
    secret, proj, pkg = _check_env(results)
    _check_revenuecat(results, secret, proj)
    _check_play_sa(results, pkg)
    _check_credential_link(results, pkg, args.sku, args.purchase_token)

    if args.json:
        print(json.dumps([r.__dict__ for r in results], indent=2))
    else:
        print(_format(results))
    return min(254, sum(1 for r in results if not r.passed))


if __name__ == "__main__":
    sys.exit(main())
