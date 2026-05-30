"""Shared Google Play Console helpers for TeamzLab IAP bootstrap.

Quirks codified (discovered while bootstrapping NoteTube AI 2026-05-30):

  - `inappproducts.*` is deprecated for create — returns
    "Please migrate to the new publishing API." Use the
    `monetization` namespace instead.
  - One-time products live at `monetization.onetimeproducts`. Create
    via `patch(allowMissing=True, updateMask='listings,purchaseOptions')`.
  - Subscriptions live at `monetization.subscriptions`. Initial
    create requires ≥1 base plan inline — cannot create empty shell.
  - `regionsVersion_version` query param is REQUIRED for any
    monetization create/patch. Use "2022/02" (Google's stable baseline).
  - For subs: passing explicit `regionalConfigs` triggers
    "Region code X is duplicated" because Google auto-fills regions.
    Pass only `otherRegionsConfig` with USD + EUR fallback (computed
    via `convertRegionPrices`).
  - Only ONE base plan per subscription can have `legacyCompatible: True`.
    Set it on the monthly variant; annual = False.

Authentication: service account JSON at
  ~/.config/teamzlab/play-console-service-account.json (TeamzLab
  shared) with `androidpublisher` scope.
"""
from __future__ import annotations

import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

DEFAULT_SA_PATH = Path(
    os.path.expanduser(
        "~/.config/teamzlab/play-console-service-account.json"
    )
)
REGIONS_VERSION = "2022/02"


def make_service(sa_path: Path = DEFAULT_SA_PATH):
    creds = service_account.Credentials.from_service_account_file(
        str(sa_path),
        scopes=["https://www.googleapis.com/auth/androidpublisher"],
    )
    return build(
        "androidpublisher", "v3", credentials=creds, cache_discovery=False,
    )


def list_existing(svc, package_name: str) -> dict:
    """Returns {'managed': set(productIds), 'subscriptions': set(ids)}."""
    out = {"managed": set(), "subscriptions": set()}
    # One-time products
    req = svc.monetization().onetimeproducts().list(packageName=package_name)
    while req is not None:
        resp = req.execute()
        for p in resp.get("oneTimeProducts", []):
            out["managed"].add(p["productId"])
        req = svc.monetization().onetimeproducts().list_next(req, resp)
    # Subscriptions
    req = svc.monetization().subscriptions().list(packageName=package_name)
    while req is not None:
        resp = req.execute()
        for s in resp.get("subscriptions", []):
            out["subscriptions"].add(s["productId"])
        req = svc.monetization().subscriptions().list_next(req, resp)
    return out


def convert_usd_to_other_regions_fallback(svc, package_name: str, usd: float) -> dict:
    """Calls convertRegionPrices and returns just the
    `convertedOtherRegionsPrice` (USD + EUR fallback). Pass this
    into `otherRegionsConfig` to let Google auto-spread to all 173
    regions without triggering the 'X is duplicated' bug."""
    units = int(usd)
    nanos = int(round((usd - units) * 1e9))
    resp = svc.monetization().convertRegionPrices(
        packageName=package_name,
        body={"price": {
            "currencyCode": "USD",
            "units": str(units),
            "nanos": nanos,
        }},
    ).execute()
    other = resp.get("convertedOtherRegionsPrice", {})
    return {
        "usdPrice": other.get("usdPrice", {}),
        "eurPrice": other.get("eurPrice", {}),
    }


def create_one_time_product(
    svc, package_name: str, product_id: str,
    title: str, description: str, price_usd: float,
) -> bool:
    units = int(price_usd)
    nanos = int(round((price_usd - units) * 1e9))
    body = {
        "packageName": package_name,
        "productId": product_id,
        "listings": [{
            "languageCode": "en-US",
            "title": title,
            "description": description,
        }],
        "purchaseOptions": [{
            "purchaseOptionId": "default",
            "state": "ACTIVE",
            "buyOption": {"legacyCompatible": True},
            "regionalPricingAndAvailabilityConfigs": [{
                "regionCode": "US",
                "price": {
                    "currencyCode": "USD",
                    "units": str(units),
                    "nanos": nanos,
                },
                "availability": "AVAILABLE",
            }],
        }],
    }
    try:
        svc.monetization().onetimeproducts().patch(
            packageName=package_name,
            productId=product_id,
            regionsVersion_version=REGIONS_VERSION,
            updateMask="listings,purchaseOptions",
            allowMissing=True,
            body=body,
        ).execute()
        return True
    except HttpError as e:
        if e.resp.status == 409:
            return True  # already exists
        print(f"  [!] onetime {product_id}: {e}")
        return False


def create_subscription(
    svc, package_name: str, product_id: str,
    title: str, description: str,
    base_plans: list[dict],
) -> bool:
    """`base_plans` is list of dicts: [{id, period (e.g. P1M), price_usd}, ...]
    Only ONE base plan can have legacyCompatible=True — we set it on
    the monthly variant by default."""
    bp_list = []
    for bp in base_plans:
        other = convert_usd_to_other_regions_fallback(
            svc, package_name, bp["price_usd"],
        )
        is_legacy = (bp["id"] == "monthly")
        bp_list.append({
            "basePlanId": bp["id"],
            "autoRenewingBasePlanType": {
                "billingPeriodDuration": bp["period"],
                "resubscribeState": "RESUBSCRIBE_STATE_ACTIVE",
                "prorationMode": (
                    "SUBSCRIPTION_PRORATION_MODE_"
                    "CHARGE_ON_NEXT_BILLING_DATE"
                ),
                "legacyCompatible": is_legacy,
            },
            "otherRegionsConfig": {
                "usdPrice": other["usdPrice"],
                "eurPrice": other["eurPrice"],
                "newSubscriberAvailability": True,
            },
        })
    body = {
        "productId": product_id,
        "listings": [{
            "languageCode": "en-US",
            "title": title,
            "description": description,
        }],
        "basePlans": bp_list,
    }
    try:
        svc.monetization().subscriptions().create(
            packageName=package_name,
            productId=product_id,
            regionsVersion_version=REGIONS_VERSION,
            body=body,
        ).execute()
        return True
    except HttpError as e:
        if e.resp.status == 409:
            return True  # already exists
        print(f"  [!] sub {product_id}: {e}")
        return False
