#!/usr/bin/env python3
"""Purge Cloudflare cache for a Teamz site. Stdlib-only.

Use from any Teamz project (every host repo that vendors this submodule
can call it). Token is shared at ~/.config/teamzlab/cloudflare-api-token.txt
so one setup covers every project.

Usage:
  python3 cloudflare-purge.py                      # purge $TEAMZ_SITE_URL zone (everything)
  python3 cloudflare-purge.py --site apps.teamzlab.com
  python3 cloudflare-purge.py --url https://apps.teamzlab.com/ https://apps.teamzlab.com/devicegpt/
  python3 cloudflare-purge.py --everything --site notetube.ai

Token setup (one-time, covers every project):
  1. https://dash.cloudflare.com/profile/api-tokens → Create Token → Custom
  2. Permissions: Zone → Cache Purge → Purge (for every Teamz zone you own)
  3. Save: echo 'cfut_...' > ~/.config/teamzlab/cloudflare-api-token.txt
  4. chmod 600 ~/.config/teamzlab/cloudflare-api-token.txt
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

TOKEN_FILE = os.path.expanduser(
    os.environ.get("TEAMZ_CLOUDFLARE_TOKEN_FILE", "~/.config/teamzlab/cloudflare-api-token.txt")
)
API_BASE = "https://api.cloudflare.com/client/v4"


def _token():
    if not os.path.exists(TOKEN_FILE):
        sys.exit(
            f"ERROR: Cloudflare token not found at {TOKEN_FILE}\n"
            "Create one: https://dash.cloudflare.com/profile/api-tokens\n"
            "Permission: Zone → Cache Purge → Purge (all zones you own)"
        )
    return open(TOKEN_FILE).read().strip()


def _api(method, path, body=None):
    req = urllib.request.Request(
        API_BASE + path,
        method=method,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
    )
    if body is not None:
        req.data = json.dumps(body).encode()
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Cloudflare API {method} {path}: HTTP {e.code}\n{e.read().decode()[:500]}")


def _root_domain(host):
    """Cloudflare zones register at the apex. apps.teamzlab.com → teamzlab.com."""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    # Two-level TLDs (.co.uk, .com.au, .org.uk) — trim three. Good enough for Teamz.
    two_level = {"co.uk", "com.au", "org.uk", "co.in", "com.bd"}
    tail = ".".join(parts[-2:])
    if tail in two_level:
        return ".".join(parts[-3:])
    return tail


def _zone_id(host):
    apex = _root_domain(host)
    data = _api("GET", f"/zones?name={urllib.parse.quote(apex)}")
    results = data.get("result", [])
    if not results:
        sys.exit(f"No Cloudflare zone found for {apex} (token may not have access)")
    return results[0]["id"], results[0]["name"]


def purge(site, urls=None, everything=False):
    host = urllib.parse.urlparse(site).hostname or site
    zone_id, apex = _zone_id(host)
    print(f"Zone: {apex} ({zone_id})")

    if everything or not urls:
        body = {"purge_everything": True}
        label = "ALL"
    else:
        body = {"files": urls}
        label = f"{len(urls)} URL(s)"

    print(f"Purging {label}...")
    res = _api("POST", f"/zones/{zone_id}/purge_cache", body=body)
    if res.get("success"):
        print(f"OK  Cloudflare purge accepted (id={res['result']['id']})")
    else:
        sys.exit(f"Purge failed: {json.dumps(res.get('errors', []), indent=2)}")


def main():
    ap = argparse.ArgumentParser(description="Purge Cloudflare cache for a Teamz site.")
    ap.add_argument(
        "--site",
        default=os.environ.get("TEAMZ_SITE_URL", ""),
        help="Site URL or hostname (default: $TEAMZ_SITE_URL)",
    )
    ap.add_argument("--url", nargs="+", help="Purge specific URL(s) only")
    ap.add_argument("--everything", action="store_true", help="Force purge-everything")
    args = ap.parse_args()

    if not args.site:
        sys.exit("ERROR: --site required (or set TEAMZ_SITE_URL in .teamz-automation.env)")

    purge(args.site, urls=args.url, everything=args.everything)


if __name__ == "__main__":
    main()
