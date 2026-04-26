#!/usr/bin/env python3
"""Cross-store In-App Purchase automation for Teamz Lab apps.

One script that creates a non-consumable IAP on App Store Connect AND
Google Play Console for any Teamz Lab project, then attaches it to a
RevenueCat entitlement + offering — fully automated where the API
allows.

Why this exists:
    Manual IAP setup is a 30+ minute trip across 3 dashboards (ASC,
    Play Console, RevenueCat) per product per app. Same Teamz Lab
    developer account hosts every game/app, so the credentials never
    change — only the app-level identifiers do. Encoding the flow once
    here removes re-learning per app and the gotchas already surfaced
    by previous launches (Apple price-point IDs, Google API casing
    inconsistency, billing-permission gate, AAB-required pre-condition,
    DRAFT-on-create ignored ACTIVE state, etc).

Canonical credentials (shared across every Teamz Lab project):
    Apple ASC API
        team-wide P8 key:  ~/.config/teamzlab/AuthKey_559DD92MBH.p8
        Key ID:            559DD92MBH
        Issuer ID:         100d6ef8-7452-4aff-85a4-990158b60b3d

    Google Play Android Publisher API
        team service account JSON:
            ~/.config/teamzlab/play-console-service-account.json
        SA email:
            play-console-automation@teamz-lab-app-landing-pages.iam.gserviceaccount.com
        Per-app permission: must grant `Manage orders and subscriptions`
                            + `View financial data` to the SA inside
                            the new app's `App permissions` page.

    RevenueCat
        umbrella project: "Teamz Lab Mobile Apps" (proj8d8322e7)
        secret key (rotate via dashboard, store in `.env.local`):
            REVENUECAT_SECRET_API_KEY=sk_...

Per-app config (host project's `.teamz-automation.env`):
    TEAMZ_APPLE_APP_ID            numeric ASC app id (e.g. 6739433404)
    TEAMZ_PLAY_PACKAGE_NAME       e.g. com.teamz.lab.chopstick_landing_games
    TEAMZ_PLAY_SERVICE_ACCOUNT_JSON   path override (defaults to ~/.config/teamzlab/...)
    TEAMZ_ASC_KEY_FILEPATH        path override (defaults to ~/.config/teamzlab/AuthKey_*.p8)
    TEAMZ_ASC_KEY_ID              key ID
    TEAMZ_ASC_ISSUER_ID           issuer ID

Per-app secret (host project's gitignored `.env.local`):
    REVENUECAT_SECRET_API_KEY     full-access RC API key
    REVENUECAT_PROJECT_ID         e.g. proj8d8322e7
    REVENUECAT_IOS_APP_ID         e.g. app698784e782
    REVENUECAT_ANDROID_APP_ID     e.g. appb3f78299da

Usage:
    # Naming convention is per-app — every Teamz Lab project picks its own
    # brand-fitting bundle name. The PATTERN stays the same: one $2.99
    # single-SKU bundle = ads off + all current cosmetics + bonus currency.
    # Pick a name that fits the app's voice. Examples:
    #
    #   chopstick_landing_games (SpaceX) -> "Captains Bundle"
    #   pet_portrait_ai          (creative) -> "Studio Pass" / "Pro Bundle"
    #   note_tube_ai             (utility)  -> "Pro Pack"
    #   decorion                 (design)   -> "Designer Bundle"
    #   debugger / DeviceGPT     (utility)  -> "Pro Diagnostic"
    #
    # Full flow (Apple + Google + RC entitlement attach):
    python3 iap.py setup \\
        --sku com.teamz.<app>.<bundle_slug> \\
        --price-usd 2.99 \\
        --name "<Bundle Name>" \\
        --description "Remove ads + unlock all bundled cosmetics." \\
        --rc-entitlement remove_ads \\
        --rc-offering default \\
        --rc-package <bundle_slug>

    # Individual platforms:
    python3 iap.py apple-create --sku ... --price-usd ... --name ... --description ...
    python3 iap.py google-create --sku ... --price-usd ... --name ... --description ...
    python3 iap.py rc-attach --sku ... --rc-entitlement ...

Gotchas baked in:
    * Google's androidpublisher REST has casing inconsistency:
        PATCH path uses `onetimeproducts` (lowercase)
        GET / list / batch / activate use `oneTimeProducts` (camelCase)
      The discovery doc (https://androidpublisher.googleapis.com/$discovery/rest?version=v3)
      is canonical. Hitting the wrong casing returns generic Google
      404 HTML, not a JSON error — easy to misread as missing-resource.
    * Initial Google PATCH lands purchaseOption in DRAFT regardless of
      `state: ACTIVE` in body. Activation must use the camelCase
      `oneTimeProducts/{sku}/purchaseOptions:batchUpdateStates` endpoint.
    * Google IAP creation requires at least one uploaded build (Internal
      Testing track minimum) on the app, otherwise Play returns
      `Can't create product. To fix, request billing permission` —
      misleading error since real cause is "no build to gate against".
    * Apple description max length = 55 chars. Truncate input.
    * Apple price points are encoded JWT-like tokens (e.g.
        `eyJzIjoiNjc2Mzg5MzM1NyIsInQiOiJVU0EiLCJwIjoiMTAwMzYifQ` for
        $2.99 USA). Must be looked up per-product after creation.
    * RC public SDK keys are safe in source. Secret keys NEVER are —
      gitignore `.env.local`.
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


def _die(msg: str, code: int = 1) -> None:
    print(f"[iap] error: {msg}", file=sys.stderr)
    sys.exit(code)


def _load_dotenv(project_root: Optional[Path] = None) -> None:
    """Load `.env.local` then `.teamz-automation.env` from the project."""
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


def _http_request(
    method: str,
    url: str,
    *,
    token: str,
    body: Optional[dict] = None,
    raw_body: Optional[bytes] = None,
    extra_headers: Optional[dict] = None,
) -> tuple[int, bytes]:
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    elif raw_body is not None:
        data = raw_body
    else:
        data = None
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _asc_jwt() -> str:
    if pyjwt is None:
        _die("pyjwt missing — `pip install pyjwt cryptography`")
    key_path = Path(os.getenv("TEAMZ_ASC_KEY_FILEPATH", str(_DEFAULT_ASC_KEY))).expanduser()
    if not key_path.exists():
        _die(f"ASC P8 key not found: {key_path}")
    key_id = os.getenv("TEAMZ_ASC_KEY_ID", _DEFAULT_ASC_KEY_ID)
    issuer = os.getenv("TEAMZ_ASC_ISSUER_ID", _DEFAULT_ASC_ISSUER_ID)
    payload = {
        "iss": issuer,
        "iat": int(time.time()),
        "exp": int(time.time()) + 1200,
        "aud": "appstoreconnect-v1",
    }
    return pyjwt.encode(  # type: ignore[union-attr]
        payload,
        key_path.read_text(),
        algorithm="ES256",
        headers={"alg": "ES256", "kid": key_id, "typ": "JWT"},
    )


def _play_token() -> str:
    if service_account is None:
        _die("google-auth missing — `pip install google-auth`")
    sa_path = Path(
        os.getenv("TEAMZ_PLAY_SERVICE_ACCOUNT_JSON", str(_DEFAULT_PLAY_SA))
    ).expanduser()
    if not sa_path.exists():
        _die(f"Play service account JSON not found: {sa_path}")
    creds = service_account.Credentials.from_service_account_file(  # type: ignore[union-attr]
        str(sa_path), scopes=["https://www.googleapis.com/auth/androidpublisher"]
    )
    creds.refresh(google.auth.transport.requests.Request())  # type: ignore[union-attr]
    return creds.token  # type: ignore[union-attr]


def _need(env: str) -> str:
    val = os.getenv(env, "").strip()
    if not val:
        _die(f"missing env {env}")
    return val


def _print_json(label: str, payload: bytes) -> None:
    try:
        parsed = json.loads(payload)
        print(f"[iap] {label}: {json.dumps(parsed, indent=2)[:600]}")
    except Exception:
        print(f"[iap] {label} (non-JSON): {payload[:300].decode(errors='replace')}")


def apple_create(
    sku: str, price_usd: float, name: str, description: str
) -> Optional[str]:
    """Create non-consumable iOS IAP + en-US localization + price.

    Returns the ASC IAP id, or None on failure.
    Description is auto-truncated to 55 chars (Apple cap).
    """
    apple_app_id = _need("TEAMZ_APPLE_APP_ID")
    if len(description) > 55:
        description = description[:52].rstrip() + "..."
        print(f"[iap] apple description truncated to 55 chars: {description}")
    jwt_token = _asc_jwt()

    # 1. Create the IAP shell.
    code, payload = _http_request(
        "POST",
        "https://api.appstoreconnect.apple.com/v2/inAppPurchases",
        token=jwt_token,
        body={
            "data": {
                "type": "inAppPurchases",
                "attributes": {
                    "name": name,
                    "productId": sku,
                    "inAppPurchaseType": "NON_CONSUMABLE",
                    "reviewNote": "Removes ads + unlocks all bundled cosmetics.",
                    "familySharable": False,
                },
                "relationships": {
                    "app": {"data": {"type": "apps", "id": apple_app_id}}
                },
            }
        },
    )
    if code >= 300:
        _print_json(f"apple-create http {code}", payload)
        return None
    iap_id = json.loads(payload)["data"]["id"]
    print(f"[iap] apple iap created id={iap_id}")

    # 2. Localization.
    code, payload = _http_request(
        "POST",
        "https://api.appstoreconnect.apple.com/v1/inAppPurchaseLocalizations",
        token=jwt_token,
        body={
            "data": {
                "type": "inAppPurchaseLocalizations",
                "attributes": {
                    "name": name,
                    "description": description,
                    "locale": "en-US",
                },
                "relationships": {
                    "inAppPurchaseV2": {
                        "data": {"type": "inAppPurchases", "id": iap_id}
                    }
                },
            }
        },
    )
    if code >= 300:
        _print_json(f"apple-localize http {code}", payload)
        return iap_id

    # 3. Price schedule — find the price point that matches the requested USD value.
    price_str = f"{price_usd:.2f}"
    cursor: Optional[str] = None
    target_pp_id: Optional[str] = None
    for _ in range(20):
        suffix = f"&cursor={cursor}" if cursor else ""
        code, payload = _http_request(
            "GET",
            f"https://api.appstoreconnect.apple.com/v2/inAppPurchases/{iap_id}/pricePoints?filter%5Bterritory%5D=USA&limit=200{suffix}",
            token=jwt_token,
        )
        if code >= 300:
            _print_json(f"apple-price-list http {code}", payload)
            return iap_id
        data = json.loads(payload)
        for pp in data.get("data", []):
            if pp.get("attributes", {}).get("customerPrice") == price_str:
                target_pp_id = pp["id"]
                break
        if target_pp_id:
            break
        next_link = data.get("links", {}).get("next")
        if not next_link:
            break
        cursor = urllib.parse.parse_qs(urllib.parse.urlparse(next_link).query).get(
            "cursor", [None]
        )[0]
    if not target_pp_id:
        print(f"[iap] apple price point ${price_str} not found — set price manually")
        return iap_id

    code, payload = _http_request(
        "POST",
        "https://api.appstoreconnect.apple.com/v1/inAppPurchasePriceSchedules",
        token=jwt_token,
        body={
            "data": {
                "type": "inAppPurchasePriceSchedules",
                "relationships": {
                    "inAppPurchase": {
                        "data": {"type": "inAppPurchases", "id": iap_id}
                    },
                    "manualPrices": {
                        "data": [
                            {"type": "inAppPurchasePrices", "id": "${price1}"}
                        ]
                    },
                    "baseTerritory": {
                        "data": {"type": "territories", "id": "USA"}
                    },
                },
            },
            "included": [
                {
                    "type": "inAppPurchasePrices",
                    "id": "${price1}",
                    "attributes": {"startDate": None},
                    "relationships": {
                        "inAppPurchasePricePoint": {
                            "data": {
                                "type": "inAppPurchasePricePoints",
                                "id": target_pp_id,
                            }
                        }
                    },
                }
            ],
        },
    )
    if code >= 300:
        _print_json(f"apple-price-schedule http {code}", payload)
    else:
        print(f"[iap] apple price set to ${price_str} USD")

    print(
        f"[iap] apple done. State: MISSING_METADATA until you upload an "
        f"App Review screenshot (any in-game PNG/JPG) under "
        f"App Store Connect -> IAP -> {name} -> App Review Information."
    )
    return iap_id


def google_create(
    sku: str, price_usd: float, name: str, description: str
) -> bool:
    """Create + activate Google Play one-time product.

    Activation uses the camelCase batchUpdateStates endpoint per
    Google's discovery doc.
    """
    package = _need("TEAMZ_PLAY_PACKAGE_NAME")
    token = _play_token()

    # 1. Upsert the product (PATCH lowercase path).
    units = int(price_usd)
    nanos = int(round((price_usd - units) * 1_000_000_000))
    update_mask = urllib.parse.quote(
        "purchase_options,listings,tax_and_compliance_settings"
    )
    upsert_url = (
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/"
        f"applications/{package}/onetimeproducts/{sku}"
        f"?regionsVersion.version=2022%2F02&allowMissing=true"
        f"&latencyTolerance=PRODUCT_UPDATE_LATENCY_TOLERANCE_LATENCY_TOLERANT"
        f"&updateMask={update_mask}"
    )
    code, payload = _http_request(
        "PATCH",
        upsert_url,
        token=token,
        body={
            "productId": sku,
            "packageName": package,
            "purchaseOptions": [
                {
                    "purchaseOptionId": "buy",
                    "state": "ACTIVE",
                    "buyOption": {
                        "legacyCompatible": True,
                        "multiQuantityEnabled": False,
                    },
                    "newRegionsConfig": {
                        "availability": "AVAILABLE",
                        "usdPrice": {
                            "currencyCode": "USD",
                            "units": str(units),
                            "nanos": nanos,
                        },
                        "eurPrice": {
                            "currencyCode": "EUR",
                            "units": str(units),
                            "nanos": nanos,
                        },
                    },
                    "regionalPricingAndAvailabilityConfigs": [
                        {
                            "regionCode": "US",
                            "price": {
                                "currencyCode": "USD",
                                "units": str(units),
                                "nanos": nanos,
                            },
                            "availability": "AVAILABLE",
                        }
                    ],
                }
            ],
            "listings": [
                {"languageCode": "en-US", "title": name, "description": description}
            ],
            "taxAndComplianceSettings": {"isTokenizedDigitalAsset": False},
        },
    )
    if code >= 300:
        _print_json(f"google-upsert http {code}", payload)
        return False
    print(f"[iap] google product created/updated: {sku}")

    # 2. Activate purchase option (camelCase path).
    activate_url = (
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/"
        f"applications/{package}/oneTimeProducts/{sku}/purchaseOptions:batchUpdateStates"
    )
    code, payload = _http_request(
        "POST",
        activate_url,
        token=token,
        body={
            "requests": [
                {
                    "purchaseOptionId": "buy",
                    "activate": {},
                    "latencyTolerance": "PRODUCT_UPDATE_LATENCY_TOLERANCE_LATENCY_TOLERANT",
                }
            ]
        },
    )
    if code >= 300:
        # Activation failures are mostly soft — product still exists, user
        # can flip it via Play Console UI manually.
        _print_json(f"google-activate http {code} (flip manually)", payload)
        return True
    print("[iap] google product ACTIVATED")
    return True


def rc_attach(
    sku: str, entitlement: str, offering: str, package: str
) -> bool:
    """Attach a store SKU to a RevenueCat entitlement + offering package.

    Requires REVENUECAT_SECRET_API_KEY + REVENUECAT_PROJECT_ID +
    REVENUECAT_IOS_APP_ID + REVENUECAT_ANDROID_APP_ID in env.
    """
    secret = _need("REVENUECAT_SECRET_API_KEY")
    project_id = _need("REVENUECAT_PROJECT_ID")
    print(f"[iap] rc-attach {sku} -> entitlement {entitlement}, offering {offering}/{package}")
    print(
        f"[iap] WARNING: rc-attach is currently a stub — RC v2 REST does not "
        f"expose a single 'attach product to entitlement' verb. The Apple/"
        f"Play products you just created will only auto-import into RC's "
        f"Products list AFTER you've wired the ASC API key + Play service "
        f"account JSON in the RC dashboard for this project. Once imported, "
        f"flip Entitlement {entitlement} -> Attach products in the RC UI."
    )
    # Sanity: confirm the entitlement exists so the user knows the lookup_key is right.
    code, payload = _http_request(
        "GET",
        f"https://api.revenuecat.com/v2/projects/{project_id}/entitlements",
        token=secret,
    )
    if code >= 300:
        _print_json(f"rc-list-entitlements http {code}", payload)
        return False
    items = json.loads(payload).get("items", [])
    matched = [e for e in items if e.get("lookup_key") == entitlement]
    if not matched:
        print(
            f"[iap] entitlement '{entitlement}' not found in project {project_id}. "
            f"Create it via:\n"
            f"  curl -H 'Authorization: Bearer $REVENUECAT_SECRET_API_KEY' "
            f"-d '{{\"lookup_key\":\"{entitlement}\",\"display_name\":\"...\"}}' "
            f"https://api.revenuecat.com/v2/projects/{project_id}/entitlements"
        )
        return False
    print(f"[iap] rc entitlement '{entitlement}' confirmed (id={matched[0]['id']})")
    return True


def cmd_setup(args: argparse.Namespace) -> int:
    apple_id = apple_create(args.sku, args.price_usd, args.name, args.description)
    google_ok = google_create(args.sku, args.price_usd, args.name, args.description)
    if args.rc_entitlement:
        rc_attach(args.sku, args.rc_entitlement, args.rc_offering, args.rc_package)
    print("[iap] setup complete. Manual steps remaining:")
    print("  1. Apple: upload App Review screenshot in App Store Connect")
    print("  2. RC dashboard: import products + attach to entitlement + offering")
    return 0 if apple_id and google_ok else 1


def cmd_apple(args: argparse.Namespace) -> int:
    return 0 if apple_create(args.sku, args.price_usd, args.name, args.description) else 1


def cmd_google(args: argparse.Namespace) -> int:
    return 0 if google_create(args.sku, args.price_usd, args.name, args.description) else 1


def cmd_rc(args: argparse.Namespace) -> int:
    return 0 if rc_attach(args.sku, args.rc_entitlement, args.rc_offering, args.rc_package) else 1


def _add_product_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--sku", required=True, help="Product ID, e.g. com.teamz.<app>.captains_bundle")
    p.add_argument("--price-usd", type=float, required=True, help="USD price (e.g. 2.99)")
    p.add_argument("--name", required=True, help="Display name (max 30 char Apple, 25 Google)")
    p.add_argument(
        "--description",
        required=True,
        help="Description (Apple cap 55; Google cap 200; auto-truncated for Apple)",
    )


def _add_rc_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--rc-entitlement",
        default="",
        help="RC entitlement lookup_key (canonical for ad removal: 'remove_ads'). "
        "Pick what the app actually unlocks — entitlements are app-specific.",
    )
    p.add_argument("--rc-offering", default="default", help="RC offering lookup_key")
    p.add_argument(
        "--rc-package",
        default="",
        help="RC package identifier inside offering. Pick something app-themed "
        "(e.g. 'captains_bundle' for a SpaceX game, 'studio_pass' for a creative "
        "tool, 'pro_pack' for a utility). Leave empty when only running setup.",
    )


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(prog="iap.py", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    s_setup = sub.add_parser("setup", help="Apple + Google + RC attach")
    _add_product_args(s_setup)
    _add_rc_args(s_setup)
    s_setup.set_defaults(func=cmd_setup)

    s_apple = sub.add_parser("apple-create", help="Apple side only")
    _add_product_args(s_apple)
    s_apple.set_defaults(func=cmd_apple)

    s_google = sub.add_parser("google-create", help="Google side only")
    _add_product_args(s_google)
    s_google.set_defaults(func=cmd_google)

    s_rc = sub.add_parser("rc-attach", help="RC entitlement + offering wiring (verify only — RC UI required)")
    s_rc.add_argument("--sku", required=True)
    _add_rc_args(s_rc)
    s_rc.set_defaults(func=cmd_rc)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
