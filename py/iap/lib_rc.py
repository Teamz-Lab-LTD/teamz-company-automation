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
