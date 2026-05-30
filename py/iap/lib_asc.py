"""Shared App Store Connect API helpers for TeamzLab IAP bootstrap.

Encapsulates every Apple API quirk discovered while bootstrapping
NoteTube AI (2026-05-30) so future apps don't re-hit them.

Quirks codified:
  - JWT must be ES256 with kid header + iss/iat/exp/aud claims
  - Sub price points live at `/subscriptions/{id}/pricePoints`
  - IAP price points moved to `/v2/inAppPurchases/{id}/pricePoints`
    (the /v1/ path returns 404 since 2023)
  - `subscriptionAvailability` resource refuses DELETE + PATCH; only
    `CREATE` + `GET_INSTANCE` allowed. POSTing a new availability
    for the same subscription REPLACES the existing one (201)
  - `subscriptionPrices` POST requires `subscriptionAvailability`
    already set — otherwise 409 RELATIONSHIP.INVALID
  - `inAppPurchasePriceSchedules` POST puts `included` at TOP-LEVEL
    (sibling of `data`), NOT nested inside data
  - Review-screenshot endpoints differ for subs vs IAPs:
      subs: /v1/subscriptionAppStoreReviewScreenshots
      IAPs: /v1/inAppPurchaseAppStoreReviewScreenshots
  - Subscription description max 55 chars (longer → 409 TOO_LONG)
  - Subscription name max 30 chars
  - To go global: replace USA-only availability with all-175
    territories, then POST a `subscriptionPrice` per territory
    using the `equalizations` relationship on the USA price point
"""
from __future__ import annotations

import hashlib
import os
import struct
import time
import zlib
from pathlib import Path
from typing import Any

import jwt
import requests

API_BASE = "https://api.appstoreconnect.apple.com/v1"
API_V2 = "https://api.appstoreconnect.apple.com/v2"

# TeamzLab shared ASC API key. All Teamz apps live under the same
# Apple Developer account (NDV83KC5LC) so one key covers everything.
DEFAULT_KEY_ID = "559DD92MBH"
DEFAULT_ISSUER_ID = "100d6ef8-7452-4aff-85a4-990158b60b3d"
DEFAULT_KEY_PATH = Path(
    os.path.expanduser("~/.config/teamzlab/AuthKey_559DD92MBH.p8")
)


# ─── JWT ─────────────────────────────────────────────────────────────


def make_jwt(
    key_id: str = DEFAULT_KEY_ID,
    issuer_id: str = DEFAULT_ISSUER_ID,
    key_path: Path = DEFAULT_KEY_PATH,
) -> str:
    """Build an ASC API JWT. Valid ~18 minutes (Apple cap is 20)."""
    pem = key_path.read_text()
    now = int(time.time())
    payload = {
        "iss": issuer_id,
        "iat": now,
        "exp": now + 1100,
        "aud": "appstoreconnect-v1",
    }
    return jwt.encode(
        payload, pem, algorithm="ES256",
        headers={"kid": key_id, "typ": "JWT"},
    )


# ─── HTTP wrapper ───────────────────────────────────────────────────


def _headers(token: str, json_content: bool = True) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if json_content:
        h["Content-Type"] = "application/json"
    return h


def get(token: str, path: str) -> requests.Response:
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    return requests.get(url, headers=_headers(token, False), timeout=30)


def get_v2(token: str, path: str) -> requests.Response:
    url = path if path.startswith("http") else f"{API_V2}{path}"
    return requests.get(url, headers=_headers(token, False), timeout=30)


def post(token: str, path: str, body: dict) -> requests.Response:
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    return requests.post(url, headers=_headers(token), json=body, timeout=60)


def post_v2(token: str, path: str, body: dict) -> requests.Response:
    url = path if path.startswith("http") else f"{API_V2}{path}"
    return requests.post(url, headers=_headers(token), json=body, timeout=60)


def patch(token: str, path: str, body: dict) -> requests.Response:
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    return requests.patch(url, headers=_headers(token), json=body, timeout=60)


def paginate(token: str, start_path: str) -> list:
    out: list = []
    next_url = start_path
    while next_url:
        url = next_url if next_url.startswith("http") else f"{API_BASE}{next_url}"
        r = requests.get(url, headers=_headers(token, False), timeout=30)
        if r.status_code >= 400:
            return out
        body = r.json()
        out += body.get("data", [])
        next_url = body.get("links", {}).get("next")
    return out


# ─── Discovery ──────────────────────────────────────────────────────


def find_app_by_bundle(token: str, bundle_id: str) -> dict | None:
    r = get(token, f"/apps?filter[bundleId]={bundle_id}&limit=5")
    if r.status_code >= 400:
        return None
    items = r.json().get("data", [])
    return items[0] if items else None


def list_territory_ids(token: str) -> list[str]:
    items = paginate(token, "/territories?limit=200")
    return [t["id"] for t in items]


# ─── Subscription group + subs ──────────────────────────────────────


def ensure_subscription_group(
    token: str, app_id: str, reference_name: str,
) -> str:
    """Find by referenceName or create. Returns group ID."""
    r = get(
        token,
        f"/apps/{app_id}/subscriptionGroups"
        "?limit=50&fields[subscriptionGroups]=referenceName",
    )
    for g in r.json().get("data", []):
        if g["attributes"].get("referenceName") == reference_name:
            return g["id"]
    r = post(token, "/subscriptionGroups", {
        "data": {
            "type": "subscriptionGroups",
            "attributes": {"referenceName": reference_name},
            "relationships": {
                "app": {"data": {"type": "apps", "id": app_id}}
            },
        }
    })
    r.raise_for_status()
    return r.json()["data"]["id"]


def list_existing_subscriptions(token: str, group_id: str) -> dict[str, str]:
    items = paginate(
        token,
        f"/subscriptionGroups/{group_id}/subscriptions"
        "?limit=50&fields[subscriptions]=productId",
    )
    return {s["attributes"]["productId"]: s["id"] for s in items}


def list_existing_iaps(token: str, app_id: str) -> dict[str, str]:
    items = paginate(
        token,
        f"/apps/{app_id}/inAppPurchasesV2"
        "?limit=50&fields[inAppPurchases]=productId",
    )
    return {p["attributes"]["productId"]: p["id"] for p in items}


def create_subscription(
    token: str, group_id: str, product_id: str, ref_name: str,
    period: str, review_note: str = "",
) -> str:
    """`period` is 'ONE_MONTH' / 'ONE_YEAR' / etc."""
    body = {
        "data": {
            "type": "subscriptions",
            "attributes": {
                "name": ref_name,
                "productId": product_id,
                "familySharable": False,
                "subscriptionPeriod": period,
                "reviewNote": review_note or (
                    "Auto-renewable subscription. See app metadata."
                ),
            },
            "relationships": {
                "group": {
                    "data": {"type": "subscriptionGroups", "id": group_id}
                }
            },
        }
    }
    r = post(token, "/subscriptions", body)
    r.raise_for_status()
    return r.json()["data"]["id"]


def create_iap(
    token: str, app_id: str, product_id: str, ref_name: str,
    kind: str, review_note: str = "",
) -> str:
    """`kind` is 'non_renewing' or 'non_consumable' or 'consumable'."""
    kind_to_asc = {
        "non_renewing": "NON_RENEWING_SUBSCRIPTION",
        "non_consumable": "NON_CONSUMABLE",
        "consumable": "CONSUMABLE",
    }
    body = {
        "data": {
            "type": "inAppPurchases",
            "attributes": {
                "name": ref_name,
                "productId": product_id,
                "inAppPurchaseType": kind_to_asc[kind],
                "familySharable": False,
                "reviewNote": review_note or "One-time purchase.",
            },
            "relationships": {
                "app": {"data": {"type": "apps", "id": app_id}}
            },
        }
    }
    # IAPs use /v2/ path for create
    r = post_v2(token, "/inAppPurchases", body)
    r.raise_for_status()
    return r.json()["data"]["id"]


def add_subscription_localization(
    token: str, sub_id: str, name: str, description: str,
    locale: str = "en-US",
) -> None:
    """Description max 55 chars + name max 30. Apple returns 409 on
    overflow with code ENTITY_ERROR.ATTRIBUTE.INVALID.TOO_LONG."""
    body = {
        "data": {
            "type": "subscriptionLocalizations",
            "attributes": {
                "locale": locale,
                "name": name[:30],
                "description": description[:55],
            },
            "relationships": {
                "subscription": {
                    "data": {"type": "subscriptions", "id": sub_id}
                }
            },
        }
    }
    post(token, "/subscriptionLocalizations", body)


def add_iap_localization(
    token: str, iap_id: str, name: str, description: str,
    locale: str = "en-US",
) -> None:
    body = {
        "data": {
            "type": "inAppPurchaseLocalizations",
            "attributes": {
                "locale": locale,
                "name": name[:30],
                "description": description[:45],
            },
            "relationships": {
                "inAppPurchaseV2": {
                    "data": {"type": "inAppPurchases", "id": iap_id}
                }
            },
        }
    }
    post(token, "/inAppPurchaseLocalizations", body)


def set_subscription_group_localization(
    token: str, group_id: str, app_name: str, locale: str = "en-US",
) -> None:
    body = {
        "data": {
            "type": "subscriptionGroupLocalizations",
            "attributes": {
                "locale": locale,
                "name": app_name[:50],
                "customAppName": None,
            },
            "relationships": {
                "subscriptionGroup": {
                    "data": {"type": "subscriptionGroups", "id": group_id}
                }
            },
        }
    }
    post(token, "/subscriptionGroupLocalizations", body)


# ─── Availability (sub-only) ─────────────────────────────────────────


def set_subscription_availability_all_territories(
    token: str, sub_id: str, territory_ids: list[str],
) -> bool:
    """Apple quirk: POST overwrites existing availability. Doesn't
    support DELETE or PATCH on this resource."""
    body = {
        "data": {
            "type": "subscriptionAvailabilities",
            "attributes": {"availableInNewTerritories": True},
            "relationships": {
                "subscription": {
                    "data": {"type": "subscriptions", "id": sub_id}
                },
                "availableTerritories": {
                    "data": [
                        {"type": "territories", "id": tid}
                        for tid in territory_ids
                    ]
                },
            },
        }
    }
    r = post(token, "/subscriptionAvailabilities", body)
    return r.status_code == 201


# ─── Prices ─────────────────────────────────────────────────────────


def find_sub_price_point(
    token: str, sub_id: str, target_usd: float,
) -> str | None:
    items = paginate(
        token,
        f"/subscriptions/{sub_id}/pricePoints"
        "?filter[territory]=USA&limit=200"
        "&fields[subscriptionPricePoints]=customerPrice",
    )
    for pp in items:
        if abs(float(pp["attributes"]["customerPrice"]) - target_usd) < 0.01:
            return pp["id"]
    return None


def find_iap_price_point(
    token: str, iap_id: str, target_usd: float,
) -> str | None:
    # IAP price points moved to /v2 in 2023.
    next_url = (
        f"{API_V2}/inAppPurchases/{iap_id}/pricePoints"
        "?filter[territory]=USA&limit=200"
        "&fields[inAppPurchasePricePoints]=customerPrice"
    )
    while next_url:
        r = requests.get(
            next_url, headers=_headers(token, False), timeout=30,
        )
        if r.status_code >= 400:
            return None
        body = r.json()
        for pp in body.get("data", []):
            if abs(float(pp["attributes"]["customerPrice"]) - target_usd) < 0.01:
                return pp["id"]
        next_url = body.get("links", {}).get("next")
    return None


def set_sub_price_usa(token: str, sub_id: str, pp_id: str) -> bool:
    body = {
        "data": {
            "type": "subscriptionPrices",
            "relationships": {
                "subscription": {
                    "data": {"type": "subscriptions", "id": sub_id}
                },
                "subscriptionPricePoint": {
                    "data": {
                        "type": "subscriptionPricePoints",
                        "id": pp_id,
                    }
                },
            },
        }
    }
    r = post(token, "/subscriptionPrices", body)
    return r.status_code == 201


def equalize_sub_price_globally(
    token: str, sub_id: str, usa_pp_id: str,
) -> tuple[int, int]:
    """Returns (ok_count, fail_count). Iterates equalizations and
    POSTs a subscriptionPrice for each non-USA territory using the
    canonical equalized price point Apple returns."""
    items = paginate(
        token,
        f"/subscriptionPricePoints/{usa_pp_id}/equalizations?limit=200"
        "&fields[subscriptionPricePoints]=territory",
    )
    ok = fail = 0
    for pp in items:
        body = {
            "data": {
                "type": "subscriptionPrices",
                "relationships": {
                    "subscription": {
                        "data": {"type": "subscriptions", "id": sub_id}
                    },
                    "subscriptionPricePoint": {
                        "data": {
                            "type": "subscriptionPricePoints",
                            "id": pp["id"],
                        }
                    },
                },
            }
        }
        r = post(token, "/subscriptionPrices", body)
        if r.status_code == 201:
            ok += 1
        else:
            fail += 1
    return ok, fail


def set_iap_price_with_schedule(
    token: str, iap_id: str, pp_id: str,
) -> bool:
    """IAPs use price SCHEDULES. The `included` array goes at
    TOP-LEVEL (sibling of `data`), not nested. Auto-equalizes to all
    other territories via Apple's automaticPrices."""
    body = {
        "data": {
            "type": "inAppPurchasePriceSchedules",
            "relationships": {
                "inAppPurchase": {
                    "data": {"type": "inAppPurchases", "id": iap_id}
                },
                "manualPrices": {
                    "data": [{
                        "type": "inAppPurchasePrices",
                        "id": "${new-price}",
                    }]
                },
                "baseTerritory": {
                    "data": {"type": "territories", "id": "USA"}
                },
            },
        },
        "included": [{
            "type": "inAppPurchasePrices",
            "id": "${new-price}",
            "attributes": {"startDate": None},
            "relationships": {
                "inAppPurchasePricePoint": {
                    "data": {
                        "type": "inAppPurchasePricePoints",
                        "id": pp_id,
                    }
                },
            },
        }],
    }
    r = post(token, "/inAppPurchasePriceSchedules", body)
    return r.status_code == 201


# ─── Review screenshot upload (3-step flow) ─────────────────────────


def make_placeholder_png(width: int = 640, height: int = 920) -> bytes:
    """Minimal valid PNG (~3KB) for products that aren't visible until
    purchased. Solid dark gray. Use only if you can't supply a real
    review screenshot."""
    def chunk(t: bytes, d: bytes) -> bytes:
        return (
            struct.pack(">I", len(d)) + t + d
            + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
        )
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b""
    for _ in range(height):
        raw += b"\x00" + (bytes([32, 32, 32]) * width)
    idat = zlib.compress(raw, 9)
    return (
        sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


def _upload_3step(
    token: str,
    reserve_path: str,
    reserve_body: dict,
    type_str: str,
    png: bytes,
) -> bool:
    H = _headers(token)
    r = post(token, reserve_path, reserve_body)
    if r.status_code != 201:
        return False
    d = r.json()["data"]
    sid = d["id"]
    ops = d["attributes"]["uploadOperations"]
    for op in ops:
        hdrs = {h["name"]: h["value"] for h in op["requestHeaders"]}
        offset = op["offset"]
        length = op["length"]
        r2 = requests.request(
            op["method"], op["url"],
            headers=hdrs,
            data=png[offset:offset + length],
            timeout=60,
        )
        if r2.status_code >= 400:
            return False
    commit = {
        "data": {
            "type": type_str,
            "id": sid,
            "attributes": {
                "uploaded": True,
                "sourceFileChecksum": hashlib.md5(png).hexdigest(),
            },
        }
    }
    r3 = patch(token, f"{reserve_path}/{sid}", commit)
    return r3.status_code == 200


def upload_sub_review_screenshot(
    token: str, sub_id: str, png: bytes,
) -> bool:
    body = {
        "data": {
            "type": "subscriptionAppStoreReviewScreenshots",
            "attributes": {
                "fileName": "review.png",
                "fileSize": len(png),
            },
            "relationships": {
                "subscription": {
                    "data": {"type": "subscriptions", "id": sub_id}
                }
            },
        }
    }
    return _upload_3step(
        token, "/subscriptionAppStoreReviewScreenshots", body,
        "subscriptionAppStoreReviewScreenshots", png,
    )


def upload_iap_review_screenshot(
    token: str, iap_id: str, png: bytes,
) -> bool:
    body = {
        "data": {
            "type": "inAppPurchaseAppStoreReviewScreenshots",
            "attributes": {
                "fileName": "review.png",
                "fileSize": len(png),
            },
            "relationships": {
                "inAppPurchaseV2": {
                    "data": {"type": "inAppPurchases", "id": iap_id}
                }
            },
        }
    }
    return _upload_3step(
        token, "/inAppPurchaseAppStoreReviewScreenshots", body,
        "inAppPurchaseAppStoreReviewScreenshots", png,
    )
