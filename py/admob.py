#!/usr/bin/env python3
"""
AdMob REST API tool — cross-project account/app/ad-unit inspection + reports.

Works across every Teamz Lab app. Stores OAuth refresh token once at
~/.config/teamzlab/admob-token.json and reuses it for all calls.

Usage:
    python3 admob.py auth                            # One-time OAuth (browser flow)
    python3 admob.py accounts                        # List publisher accounts
    python3 admob.py apps [--account ACC_ID]         # List apps
    python3 admob.py ad-units --app APP_ID [--format FORMAT]
    python3 admob.py find-unit --app APP_ID --format NATIVE
    python3 admob.py report --days 7 [--metrics CLICKS,IMPRESSIONS,ESTIMATED_EARNINGS]
    python3 admob.py report --app APP_ID --days 30
"""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

CONFIG_DIR = os.path.expanduser("~/.config/teamzlab")
TOKEN_FILE = os.path.join(CONFIG_DIR, "admob-token.json")
OAUTH_CLIENT_FILE = os.path.join(CONFIG_DIR, "oauth-client-config.json")
SCOPES = "https://www.googleapis.com/auth/admob.readonly https://www.googleapis.com/auth/admob.report"
REDIRECT_URI = "http://localhost:9994"
API_BASE = "https://admob.googleapis.com/v1"
UA = "TeamzLab-AdMob/1.0"
SSL_CTX = ssl.create_default_context()


# ─── OAuth ────────────────────────────────────────────────────────

class _OAuthHandler(BaseHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            _OAuthHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body style='font-family:sans-serif;text-align:center;padding:50px'>"
                             b"<h1>AdMob authorized!</h1><p>You can close this tab.</p></body></html>")
        else:
            self.send_response(400); self.end_headers()

    def log_message(self, *a, **k): pass


def _load_oauth_client():
    if not os.path.exists(OAUTH_CLIENT_FILE):
        sys.exit(f"Missing {OAUTH_CLIENT_FILE} — run one of the existing Teamz OAuth setups first.")
    with open(OAUTH_CLIENT_FILE) as f:
        data = json.load(f)
    cfg = data.get("installed") or data.get("web") or data
    return cfg["client_id"], cfg["client_secret"]


def cmd_auth(_args):
    client_id, client_secret = _load_oauth_client()
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    print(f"Opening browser for AdMob authorization…\nIf it doesn't open:\n  {url}\n")
    webbrowser.open(url)
    server = HTTPServer(("localhost", 9994), _OAuthHandler)
    server.handle_request()
    if not _OAuthHandler.auth_code:
        sys.exit("No authorization code received.")

    token_req = urllib.parse.urlencode({
        "code": _OAuthHandler.auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=token_req,
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=SSL_CTX) as r:
        tokens = json.loads(r.read())

    if "refresh_token" not in tokens:
        sys.exit(f"No refresh_token returned: {tokens}")

    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_at": int(time.time()) + int(tokens.get("expires_in", 3600)) - 60,
            "client_id": client_id,
            "client_secret": client_secret,
        }, f, indent=2)
    print(f"Token saved → {TOKEN_FILE}")

    # Smoke test
    accs = _api_get("/accounts").get("account", [])
    if accs:
        print(f"\nFound {len(accs)} publisher account(s):")
        for a in accs:
            print(f"  {a['publisherId']}  {a.get('name','')}")
    else:
        print("Warning: no AdMob publisher accounts on this identity.")


def _load_token():
    if not os.path.exists(TOKEN_FILE):
        sys.exit("Not authenticated. Run: python3 admob.py auth")
    with open(TOKEN_FILE) as f:
        return json.load(f)


def _save_token(tok):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tok, f, indent=2)


def _get_access_token():
    tok = _load_token()
    if tok.get("expires_at", 0) > time.time():
        return tok["access_token"]
    # refresh
    body = urllib.parse.urlencode({
        "client_id": tok["client_id"],
        "client_secret": tok["client_secret"],
        "refresh_token": tok["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body,
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=SSL_CTX) as r:
        new = json.loads(r.read())
    tok["access_token"] = new["access_token"]
    tok["expires_at"] = int(time.time()) + int(new.get("expires_in", 3600)) - 60
    _save_token(tok)
    return tok["access_token"]


# ─── API helpers ──────────────────────────────────────────────────

def _api_get(path, params=None):
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {_get_access_token()}",
        "User-Agent": UA,
    })
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {e.code}: {e.read().decode()[:500]}")


def _api_post(path, body):
    req = urllib.request.Request(API_BASE + path, data=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {_get_access_token()}",
        "User-Agent": UA,
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as r:
            body = r.read().decode()
        # AdMob streams a JSON array of {header|row|footer} objects
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return [json.loads(line) for line in body.splitlines() if line.strip()]
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {e.code}: {e.read().decode()[:500]}")


def _resolve_account(account_id=None):
    if account_id:
        return account_id if account_id.startswith("accounts/") else f"accounts/{account_id}"
    accs = _api_get("/accounts").get("account", [])
    if not accs:
        sys.exit("No AdMob accounts on this identity.")
    if len(accs) > 1 and not account_id:
        print("Multiple accounts — pick one via --account:", file=sys.stderr)
        for a in accs:
            print(f"  {a['publisherId']}", file=sys.stderr)
    return accs[0]["name"]  # "accounts/pub-XXXX"


# ─── Subcommands ──────────────────────────────────────────────────

def cmd_accounts(_args):
    accs = _api_get("/accounts").get("account", [])
    for a in accs:
        print(f"{a['publisherId']}\t{a.get('name','')}\tcurrency={a.get('currencyCode','')}\ttz={a.get('reportingTimeZone','')}")


def cmd_apps(args):
    acct = _resolve_account(args.account)
    apps = _api_get(f"/{acct}/apps").get("apps", [])
    print(f"# {len(apps)} apps under {acct}")
    for a in apps:
        platform = a.get("platform", "?")
        linked = a.get("linkedAppInfo", {})
        store_id = linked.get("appStoreId") or a.get("appId", "")
        print(f"{a['appId']}\t{platform}\t{a.get('name','')}\t{store_id}")


def cmd_ad_units(args):
    acct = _resolve_account(args.account)
    units = _api_get(f"/{acct}/adUnits").get("adUnits", [])
    if args.app:
        units = [u for u in units if u.get("appId") == args.app]
    if args.format:
        want = args.format.upper()
        units = [u for u in units if want in (u.get("adFormat") or "").upper()]
    print(f"# {len(units)} ad units" + (f" (app={args.app}, format={args.format or 'any'})"))
    for u in units:
        fmt = u.get("adFormat", "?")
        types = ",".join(u.get("adTypes") or [])
        print(f"{u['adUnitId']}\t{fmt}\t{types}\t{u.get('displayName','')}")


def cmd_find_unit(args):
    args.format = args.format or "NATIVE"
    cmd_ad_units(args)


def cmd_report(args):
    acct = _resolve_account(args.account)
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=args.days)
    metrics = [m.strip() for m in (args.metrics or "CLICKS,IMPRESSIONS,ESTIMATED_EARNINGS,IMPRESSION_CTR").split(",")]
    dims = [d.strip() for d in (args.dimensions or "DATE,APP").split(",")]
    body = {
        "reportSpec": {
            "dateRange": {
                "startDate": {"year": start.year, "month": start.month, "day": start.day},
                "endDate":   {"year": end.year,   "month": end.month,   "day": end.day},
            },
            "dimensions": dims,
            "metrics": metrics,
        }
    }
    if args.app:
        body["reportSpec"]["dimensionFilters"] = [{
            "dimension": "APP", "matchesAny": {"values": [args.app]}
        }]
    rows = _api_post(f"/{acct}/networkReport:generate", body)
    # Print headers then rows
    headers = dims + metrics
    print("\t".join(headers))
    for r in rows:
        row = r.get("row")
        if not row:
            continue
        dv = row.get("dimensionValues", {})
        mv = row.get("metricValues", {})
        out = []
        for d in dims:
            out.append(dv.get(d, {}).get("value") or dv.get(d, {}).get("displayLabel", ""))
        for m in metrics:
            v = mv.get(m, {})
            out.append(v.get("microsValue") or v.get("integerValue") or v.get("doubleValue") or "")
        print("\t".join(str(x) for x in out))


# ─── CLI ──────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="AdMob REST API tool (cross-project)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("auth", help="One-time OAuth flow").set_defaults(func=cmd_auth)
    sub.add_parser("accounts", help="List publisher accounts").set_defaults(func=cmd_accounts)

    sp = sub.add_parser("apps", help="List apps")
    sp.add_argument("--account", help="Publisher ID or accounts/pub-XXX")
    sp.set_defaults(func=cmd_apps)

    sp = sub.add_parser("ad-units", help="List ad units")
    sp.add_argument("--account"); sp.add_argument("--app"); sp.add_argument("--format",
        help="Filter: NATIVE, BANNER, INTERSTITIAL, REWARDED, REWARDED_INTERSTITIAL, APP_OPEN")
    sp.set_defaults(func=cmd_ad_units)

    sp = sub.add_parser("find-unit", help="Find ad unit by format (alias)")
    sp.add_argument("--account"); sp.add_argument("--app", required=True); sp.add_argument("--format")
    sp.set_defaults(func=cmd_find_unit)

    sp = sub.add_parser("report", help="Fetch network report")
    sp.add_argument("--account"); sp.add_argument("--app")
    sp.add_argument("--days", type=int, default=7)
    sp.add_argument("--metrics", help="CSV metrics (default: CLICKS,IMPRESSIONS,ESTIMATED_EARNINGS,IMPRESSION_CTR)")
    sp.add_argument("--dimensions", help="CSV dimensions (default: DATE,APP)")
    sp.set_defaults(func=cmd_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
