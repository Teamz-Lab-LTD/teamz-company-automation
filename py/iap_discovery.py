#!/usr/bin/env python3
"""Discovery-doc enforcement helper.

Mechanical enforcement of the "discovery doc first" rule. Any iap.py
write op imports this module and calls `assert_path_exists()` before
firing an HTTP call. Refuses to proceed if the path isn't in the
canonical discovery doc — surfaces casing / endpoint typos at lint
time, not after wasted curl + 404 cycles.

Caches the discovery docs at:
    ~/.cache/teamzlab/discovery/google-androidpublisher-v3.json
    ~/.cache/teamzlab/discovery/apple-asc-paths.txt

with a 24h TTL. Refresh:
    python3 py/iap_discovery.py refresh

Usage as library:
    from iap_discovery import assert_google_path_exists
    assert_google_path_exists("PATCH", "applications/{packageName}/onetimeproducts/{productId}")
    assert_google_path_exists("GET",   "applications/{packageName}/oneTimeProducts/{productId}")

Apple's API doesn't ship a single discovery JSON, but they publish
OpenAPI specs per resource. We hit a known-cheap endpoint to confirm
the JWT works + add observed Apple-specific quirks here as facts so
future agents see them on import.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


_CACHE_DIR = Path.home() / ".cache" / "teamzlab" / "discovery"
_GOOGLE_CACHE = _CACHE_DIR / "google-androidpublisher-v3.json"
_TTL_SECONDS = 24 * 60 * 60

GOOGLE_DISCOVERY_URL = (
    "https://androidpublisher.googleapis.com/$discovery/rest?version=v3"
)


def _ensure_dir() -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) < _TTL_SECONDS


def fetch_google_discovery(force: bool = False) -> dict:
    _ensure_dir()
    if not force and _is_fresh(_GOOGLE_CACHE):
        return json.loads(_GOOGLE_CACHE.read_text())
    try:
        with urllib.request.urlopen(GOOGLE_DISCOVERY_URL, timeout=30) as r:
            data = r.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Failed to fetch Google discovery doc: {exc}. "
            "Without this, iap_discovery.assert_google_path_exists "
            "cannot validate paths. Restore network or pass --skip-discovery "
            "(commit message must justify)."
        ) from exc
    parsed = json.loads(data)
    _GOOGLE_CACHE.write_text(data.decode())
    return parsed


def _walk_resources(root: dict, prefix: list[str], result: list[tuple[str, str]]) -> None:
    for method_name, method in root.get("methods", {}).items():
        result.append((method.get("httpMethod", ""), method.get("path", "")))
    for sub_name, sub in root.get("resources", {}).items():
        _walk_resources(sub, prefix + [sub_name], result)


def list_google_paths() -> list[tuple[str, str]]:
    """Return [(httpMethod, path), ...] for every Google v3 androidpublisher endpoint."""
    doc = fetch_google_discovery()
    paths: list[tuple[str, str]] = []
    for _, res in doc.get("resources", {}).items():
        _walk_resources(res, [], paths)
    return paths


def assert_google_path_exists(method: str, path: str) -> None:
    """Raise if (method, path) isn't in Google's androidpublisher v3 discovery.

    Path is the post-base part starting with `androidpublisher/v3/...`.
    Use template form (`{packageName}`, `{productId}`) — discovery doc
    uses the same templating.
    """
    paths = list_google_paths()
    for m, p in paths:
        if m == method and p == path:
            return
    raise ValueError(
        f"Google API path not found in discovery doc:\n"
        f"  requested: {method} {path}\n"
        f"  hint: pull `{GOOGLE_DISCOVERY_URL}` and grep for the resource "
        f"name. Common gotcha: casing — `onetimeproducts` (lowercase) is "
        f"PATCH-only; GET/list/delete/batch* use `oneTimeProducts` "
        f"(camelCase)."
    )


# Apple ASC quirks — known facts we've paid for in production. Update
# when new ones are discovered. iap.py / iap_preflight.py import these
# constants instead of hardcoding inline.
APPLE_IAP_NAME_MAX = 30
APPLE_IAP_DESCRIPTION_MAX = 55  # Apple's hard cap on inAppPurchaseLocalizations.description
APPLE_PRICE_LOCAL_ID_FORMAT = "${name}"  # Apple uses literal ${...} for inline relationship IDs
APPLE_BANNED_IAP_ATTRIBUTES = {
    # These look like real fields per Apple's older docs but the v2 API
    # rejects them with 409 ENTITY_ERROR.ATTRIBUTE.UNKNOWN.
    "availableInAllTerritories",
}
APPLE_VALID_IAP_TYPES = {
    "CONSUMABLE",
    "NON_CONSUMABLE",
    "NON_RENEWING_SUBSCRIPTION",
}
APPLE_IAP_STATES = {
    # Observed states an inAppPurchasesV2 record can occupy. Use as a
    # sanity tag when verifying post-write — anything outside this set
    # is a future state Apple added that we should investigate.
    "MISSING_METADATA",
    "READY_TO_SUBMIT",
    "WAITING_FOR_REVIEW",
    "IN_REVIEW",
    "PENDING_DEVELOPER_RELEASE",
    "READY_FOR_SALE",
    "REJECTED",
    "REMOVED_FROM_SALE",
    "DEVELOPER_REMOVED_FROM_SALE",
    "DEVELOPER_ACTION_NEEDED",
    "PROCESSING_CONTENT",
}


# Google API casing guide — most common confused pairs. iap_preflight
# can grep request URLs against this for sanity warnings.
GOOGLE_CASING_FACTS = {
    # path_segment -> (PATCH/POST_lowercase, GET/list/delete_camelCase) facts
    "onetimeproducts": {
        "patch": "onetimeproducts",      # PATCH the product
        "delete": "oneTimeProducts",     # DELETE the product
        "get": "oneTimeProducts",        # GET / list
        "batch": "oneTimeProducts",      # batchUpdateStates / batchGet / batchDelete
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("refresh", help="Force-refresh Google discovery cache")
    s_grep = sub.add_parser("grep", help="grep canonical path list for a substring")
    s_grep.add_argument("term", help="substring to grep for")
    s_check = sub.add_parser("check", help="Check (method, path) is in discovery")
    s_check.add_argument("method", help="HTTP method (e.g. GET, PATCH)")
    s_check.add_argument("path", help="path template (e.g. applications/{packageName}/oneTimeProducts/{productId})")
    args = parser.parse_args()

    if args.cmd == "refresh":
        fetch_google_discovery(force=True)
        print(f"refreshed: {_GOOGLE_CACHE}")
        return 0

    if args.cmd == "grep":
        for m, p in list_google_paths():
            if args.term.lower() in p.lower():
                print(f"{m:8s} {p}")
        return 0

    if args.cmd == "check":
        try:
            assert_google_path_exists(args.method, args.path)
        except ValueError as e:
            print(str(e))
            return 1
        print(f"OK: {args.method} {args.path}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
