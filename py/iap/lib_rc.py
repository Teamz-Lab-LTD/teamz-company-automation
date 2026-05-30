"""Shared RevenueCat v2 REST helpers for TeamzLab IAP bootstrap.

The RC MCP integration is OAuth-bound to whichever account first
authenticated it — usually wrong for cross-account work. Direct
v2 REST API uses a `sk_*` secret key with project-scoped access and
sidesteps the MCP scope issue.

Quirks codified:
  - ASC API key upload endpoint accepts POST not PATCH to
    `/v2/projects/{id}/apps/{id}` with nested `app_store.*` body.
    Direct PATCH returns 405. (RC MCP schema field names like
    `app_store__app_store_connect_api_key` are NOT the REST shape —
    REST uses nested objects.)
  - Same nested-POST trick works for Subscription Key (StoreKit 2).
  - Play SA upload is project-scoped (configured once in RC
    dashboard for the whole RC project), not per-app.

Get a secret key at:
  https://app.revenuecat.com/projects/{project_id}/api-keys
"""
from __future__ import annotations

import os
from typing import Any

import requests

API_BASE = "https://api.revenuecat.com/v2"


def _headers(secret_key: str) -> dict:
    return {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }


def list_projects(secret_key: str) -> list[dict]:
    r = requests.get(
        f"{API_BASE}/projects?limit=50",
        headers={"Authorization": f"Bearer {secret_key}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("items", [])


def list_apps(secret_key: str, project_id: str) -> list[dict]:
    r = requests.get(
        f"{API_BASE}/projects/{project_id}/apps?limit=50",
        headers={"Authorization": f"Bearer {secret_key}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("items", [])


def get_app(secret_key: str, project_id: str, app_id: str) -> dict:
    r = requests.get(
        f"{API_BASE}/projects/{project_id}/apps/{app_id}",
        headers={"Authorization": f"Bearer {secret_key}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def upload_asc_api_key(
    secret_key: str, project_id: str, app_id: str,
    p8_pem: str, key_id: str, issuer_id: str,
) -> bool:
    """Upload ASC API key + ID + issuer to RC's iOS app so RC can
    fetch product state from Apple. Endpoint is POST (not PATCH).
    Body uses nested `app_store.*` keys."""
    body = {
        "app_store": {
            "app_store_connect_api_key": p8_pem,
            "app_store_connect_api_key_id": key_id,
            "app_store_connect_api_key_issuer": issuer_id,
        }
    }
    r = requests.post(
        f"{API_BASE}/projects/{project_id}/apps/{app_id}",
        headers=_headers(secret_key),
        json=body, timeout=30,
    )
    return r.status_code == 200


def upload_subscription_key(
    secret_key: str, project_id: str, app_id: str,
    p8_pem: str, key_id: str, issuer_id: str,
) -> bool:
    """Upload StoreKit 2 subscription key (separate from ASC API key).
    Used for server-to-server App Store Server Notifications."""
    body = {
        "app_store": {
            "subscription_private_key": p8_pem,
            "subscription_key_id": key_id,
            "subscription_key_issuer": issuer_id,
        }
    }
    r = requests.post(
        f"{API_BASE}/projects/{project_id}/apps/{app_id}",
        headers=_headers(secret_key),
        json=body, timeout=30,
    )
    return r.status_code == 200


def list_products(secret_key: str, project_id: str) -> list[dict]:
    items: list[dict] = []
    next_token: str | None = None
    while True:
        params = "?limit=50"
        if next_token:
            params += f"&starting_after={next_token}"
        r = requests.get(
            f"{API_BASE}/projects/{project_id}/products{params}",
            headers={"Authorization": f"Bearer {secret_key}"},
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        items += body.get("items", [])
        next_token = body.get("next_page")
        if not next_token:
            break
    return items


def list_public_api_keys(
    secret_key: str, project_id: str, app_id: str,
) -> list[dict]:
    """SDK-side public keys (start with `appl_` or `goog_`) — what
    Flutter passes to `RevenueCatConfig(apiKey: ...)`."""
    r = requests.get(
        f"{API_BASE}/projects/{project_id}/apps/{app_id}/public_api_keys",
        headers={"Authorization": f"Bearer {secret_key}"},
        timeout=30,
    )
    if r.status_code >= 400:
        return []
    return r.json().get("items", [])


def get_app_public_sdk_key(
    secret_key: str, project_id: str, app_id: str,
) -> str | None:
    """Return the single production public SDK key for an app
    (or sandbox if no prod yet — RC's behavior)."""
    keys = list_public_api_keys(secret_key, project_id, app_id)
    for k in keys:
        if k.get("type") == "public":
            return k.get("key")
    return keys[0].get("key") if keys else None


def list_offerings(secret_key: str, project_id: str) -> list[dict]:
    r = requests.get(
        f"{API_BASE}/projects/{project_id}/offerings?limit=20",
        headers={"Authorization": f"Bearer {secret_key}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("items", [])


def get_paywall(
    secret_key: str, project_id: str, offering_id: str,
) -> dict | None:
    """RC v2 returns the paywall config attached to an offering, if
    any. Used to read the existing paywall before applying a theme."""
    r = requests.get(
        f"{API_BASE}/projects/{project_id}/offerings/{offering_id}/paywall",
        headers={"Authorization": f"Bearer {secret_key}"},
        timeout=30,
    )
    if r.status_code == 404:
        return None
    if r.status_code >= 400:
        return None
    return r.json()


def update_paywall_theme(
    secret_key: str, project_id: str, paywall_id: str,
    design_tokens: dict,
) -> bool:
    """Apply a host-app's design-system colors + typography to RC's
    hosted paywall (RemotePaywall — purchases_ui_flutter's PaywallView
    renders this).

    `design_tokens` shape (all fields optional — RC keeps existing
    values for any field omitted):
      {
        "primary":        "#RRGGBB",  # CTA button + accents
        "background":     "#RRGGBB",  # full-bleed background
        "surface":        "#RRGGBB",  # card backgrounds
        "text_primary":   "#RRGGBB",  # body + heading text
        "text_secondary": "#RRGGBB",  # captions
        "on_primary":     "#RRGGBB",  # text on CTA button
        "font_family":    "Poppins",  # CSS font-family (must be loaded)
      }

    The paywall must already exist (created via RC dashboard or
    the create-paywall endpoint). This call patches only color +
    font tokens; layout/copy untouched.
    """
    # Build the PATCH body — only include fields the user supplied.
    components = {}
    if "primary" in design_tokens:
        components["primary_color"] = design_tokens["primary"]
    if "background" in design_tokens:
        components["background_color"] = design_tokens["background"]
    if "surface" in design_tokens:
        components["surface_color"] = design_tokens["surface"]
    if "text_primary" in design_tokens:
        components["text_color"] = design_tokens["text_primary"]
    if "text_secondary" in design_tokens:
        components["secondary_text_color"] = design_tokens["text_secondary"]
    if "on_primary" in design_tokens:
        components["primary_text_color"] = design_tokens["on_primary"]
    if "font_family" in design_tokens:
        components["font_family"] = design_tokens["font_family"]
    body = {"theme": components}
    r = requests.patch(
        f"{API_BASE}/projects/{project_id}/paywalls/{paywall_id}",
        headers=_headers(secret_key),
        json=body, timeout=30,
    )
    return r.status_code in (200, 204)


def emit_flutter_revenuecat_snippet(
    ios_public_key: str | None,
    android_public_key: str | None,
    entitlement_id: str = "premium",
) -> str:
    """Return a ready-to-paste Dart snippet for main.dart that wires
    `RevenueCatConfig` with the discovered public keys. Drop into
    `AppInitializer.createApp(revenueCatConfig: ...)`."""
    ios = ios_public_key or "<paste-from-rc-dashboard>"
    android = android_public_key or "<paste-from-rc-dashboard>"
    return f"""// In main.dart — pass to AppInitializer.createApp:
revenueCatConfig: kIsWeb ? null : RevenueCatConfig(
  apiKey: defaultTargetPlatform == TargetPlatform.iOS
      ? '{ios}'
      : '{android}',
  defaultEntitlementId: '{entitlement_id}',
  useStoreKit2IfAvailable: true,
),
"""
