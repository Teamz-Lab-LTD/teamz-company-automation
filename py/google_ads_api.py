"""
Shared Google Ads API access: auth + a version that does not rot.

WHY THIS MODULE EXISTS. The Google Ads REST endpoint carries its version in the URL
(/v21/customers/...) and Google sunsets versions on a rolling schedule. Two distinct failure
shapes come out of that, and BOTH look like "the API is not available yet":

  * a version Google no longer routes at all answers with a generic 404 HTML error page —
    not a JSON API error, so JSON-parsing error handlers see garbage
  * a version mid-deprecation answers HTTP 400 UNSUPPORTED_VERSION, and does so
    INTERMITTENTLY while the rollout progresses — some calls succeed, some are blocked

Under the broad `except Exception: pass` that the callers use to mean "not approved yet",
both read as silence. v18 sat dead in build-keyword-volume.py for months that way. It was
fixed to v21 on 2026-08-08 and v21 began being blocked the same day — which is exactly why
hardcoding the next number is not the fix.

So: probe once, newest-first, cache the answer, and re-probe automatically the moment the
cached version starts failing. Nobody has to notice a deprecation again.
"""
import json
import time
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "teamzlab"
ADS_CONFIG = CONFIG_DIR / "google-ads-config.json"
ADS_TOKEN = CONFIG_DIR / "google-ads-token.json"
VERSION_CACHE = CONFIG_DIR / "google-ads-version.json"

# Newest first. Versions above the current release simply 404 and cost one cheap probe each;
# the ceiling is deliberately far ahead so this keeps working for years without an edit.
CANDIDATES = [f"v{n}" for n in range(34, 17, -1)]
CACHE_TTL_DAYS = 14


def credentials():
    """(config, access_token). Raises — callers decide how loud to be."""
    import requests
    cfg = json.loads(ADS_CONFIG.read_text())
    tok = json.loads(ADS_TOKEN.read_text())
    r = requests.post(tok.get("token_uri", "https://oauth2.googleapis.com/token"),
                      data={"client_id": tok["client_id"],
                            "client_secret": tok["client_secret"],
                            "refresh_token": tok["refresh_token"],
                            "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return cfg, r.json()["access_token"]


def _cid(cfg):
    # Config may hold the dashed Google Ads form (123-456-7890); the REST path wants digits.
    return str(cfg["customer_id"]).replace("-", "")


def headers(cfg, access):
    cid = _cid(cfg)
    return {"Authorization": f"Bearer {access}",
            "developer-token": cfg["developer_token"],
            "login-customer-id": cfg.get("login_customer_id", cid)}


def _probe(cfg, hdrs, version):
    """True if this version answers a minimal real request."""
    import requests
    try:
        r = requests.post(
            f"https://googleads.googleapis.com/{version}/customers/{_cid(cfg)}"
            f":generateKeywordIdeas",
            headers=hdrs,
            json={"keywordSeed": {"keywords": ["mortgage calculator"]},
                  "language": "languageConstants/1000",
                  "geoTargetConstants": ["geoTargetConstants/2840"],
                  "keywordPlanNetwork": "GOOGLE_SEARCH"}, timeout=45)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def _read_cache():
    try:
        c = json.loads(VERSION_CACHE.read_text())
        age = (time.time() - c.get("checked_at", 0)) / 86400
        if c.get("version") and age < CACHE_TTL_DAYS:
            return c["version"]
    except Exception:  # noqa: BLE001
        pass
    return None


def _write_cache(version):
    try:
        VERSION_CACHE.parent.mkdir(parents=True, exist_ok=True)
        VERSION_CACHE.write_text(json.dumps(
            {"version": version, "checked_at": time.time(),
             "checked_on": time.strftime("%Y-%m-%d")}, indent=2))
    except Exception:  # noqa: BLE001
        pass


def live_version(cfg, hdrs, force_reprobe=False):
    """Newest Google Ads API version this account can actually call. None if none answer."""
    if not force_reprobe:
        cached = _read_cache()
        if cached and _probe(cfg, hdrs, cached):
            return cached
    for v in CANDIDATES:
        if _probe(cfg, hdrs, v):
            _write_cache(v)
            print(f"  google-ads: using API {v}"
                  + ("" if not _read_cache() else " (probed)"))
            return v
    return None


def endpoint(cfg, hdrs, method="generateKeywordIdeas"):
    """Full URL for `method`, or None if no version answers."""
    v = live_version(cfg, hdrs)
    if not v:
        return None
    return f"https://googleads.googleapis.com/{v}/customers/{_cid(cfg)}:{method}"
