#!/usr/bin/env python3
"""
Pinterest OAuth2 — one-time setup for scripts/distribute/distribute.py

Creates a refreshable access token and saves it to the path in config
(pinterest.credentials_file).

Prerequisites:
  - Pinterest developer app at https://developers.pinterest.com/apps/
  - Redirect URI must match EXACTLY (e.g. http://localhost:8085/)
  - Scopes: pins:write, boards:read, user_accounts:read

Usage:
  python3 scripts/distribute/pinterest-auth.py

  # Or with env vars (optional; config.json pinterest section is preferred):
  PINTEREST_APP_ID=... PINTEREST_APP_SECRET=... python3 scripts/distribute/pinterest-auth.py
"""

import base64
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from webbrowser import open_new

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
SSL_CTX = ssl.create_default_context()
OAUTH_BASE = "https://www.pinterest.com"
TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
DEFAULT_REDIRECT = "http://localhost:8085/"
DEFAULT_CREDS = "~/.config/teamzlab/pinterest-credentials.json"


def make_oauth_handler(expected_state):
    """Closure so BaseHTTPRequestHandler gets (request, client_address, server) only."""

    class OAuthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(parsed.query)
            state = (q.get("state") or [None])[0]
            code = (q.get("code") or [None])[0]

            landing = os.environ.get(
                "PINTEREST_LANDING_URI",
                "https://developers.pinterest.com/apps/",
            )
            self.send_response(301)
            self.send_header("Location", landing)
            self.end_headers()

            if state != expected_state:
                self.server.oauth_error = "OAuth state mismatch"
                return
            if not code:
                self.server.oauth_error = "No authorization code in redirect"
                return
            self.server.auth_code = code
            self.server.oauth_error = None

        def log_message(self, *args):
            pass

    return OAuthHandler


def api_form(url, fields, basic_auth_b64):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Basic {basic_auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "TeamzLabDistribute/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"error": body}


def load_pinterest_section():
    if not CONFIG_FILE.exists():
        print(f"  ERROR: {CONFIG_FILE} not found.")
        print("  Copy scripts/distribute/config.example.json to scripts/distribute/config.json")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    p = cfg.get("pinterest") or {}
    app_id = p.get("app_id") or os.environ.get("PINTEREST_APP_ID", "")
    app_secret = p.get("app_secret") or os.environ.get("PINTEREST_APP_SECRET", "")
    redirect_uri = p.get("redirect_uri") or DEFAULT_REDIRECT
    creds_file = os.path.expanduser(p.get("credentials_file") or DEFAULT_CREDS)
    return app_id, app_secret, redirect_uri, creds_file, cfg


def list_boards_sample(access_token):
    """Fetch first page of boards to help user copy board_id into config."""
    req = urllib.request.Request(
        "https://api.pinterest.com/v5/boards?page_size=25",
        headers={
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "TeamzLabDistribute/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError:
        return
    items = data.get("items") or []
    if not items:
        return
    print("\n  Your boards (copy board_id into pinterest.board_id):")
    for b in items:
        bid = b.get("id", "")
        name = b.get("name", "")
        print(f"    {bid}  —  {name}")


def main():
    app_id, app_secret, redirect_uri, creds_file, _full_cfg = load_pinterest_section()
    if not app_id or not app_secret:
        print("  ERROR: Set pinterest.app_id and pinterest.app_secret in scripts/distribute/config.json")
        print("  Create an app: https://developers.pinterest.com/apps/")
        print(f"  Add this redirect URI to the app: {redirect_uri}")
        sys.exit(1)

    parsed = urllib.parse.urlparse(redirect_uri)
    port = parsed.port
    if not port:
        print("  ERROR: redirect_uri must include a port, e.g. http://localhost:8085/")
        sys.exit(1)

    scopes = "pins:write,boards:read,user_accounts:read"
    oauth_state = secrets.token_hex(16)
    r_uri_enc = urllib.parse.quote(redirect_uri, safe="")
    auth_url = (
        f"{OAUTH_BASE}/oauth/"
        f"?consumer_id={urllib.parse.quote(app_id, safe='')}"
        f"&redirect_uri={r_uri_enc}"
        f"&response_type=code"
        f"&refreshable=true"
        f"&scope={urllib.parse.quote(scopes, safe='')}"
        f"&state={oauth_state}"
    )

    print("\n  Opening browser for Pinterest login…")
    print(f"  If nothing opens, visit:\n  {auth_url}\n")
    open_new(auth_url)

    server = HTTPServer(("localhost", port), make_oauth_handler(oauth_state))
    server.auth_code = None
    server.oauth_error = None

    print(f"  Waiting for redirect on {redirect_uri} …")
    try:
        server.handle_request()
    except OSError as e:
        print(f"  ERROR: Could not listen on port {port}: {e}")
        print("  Choose another port: set pinterest.redirect_uri in config (and in Pinterest app settings).")
        sys.exit(1)

    if getattr(server, "oauth_error", None):
        print(f"  ERROR: {server.oauth_error}")
        sys.exit(1)
    code = server.auth_code
    if not code:
        print("  ERROR: No authorization code received.")
        sys.exit(1)

    basic = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
    status, resp = api_form(
        TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        basic,
    )

    if status != 200:
        print(f"  ERROR: Token exchange failed HTTP {status}: {json.dumps(resp)[:400]}")
        sys.exit(1)

    access_token = resp.get("access_token")
    refresh_token = resp.get("refresh_token")
    if not access_token:
        print(f"  ERROR: No access_token in response: {json.dumps(resp)[:300]}")
        sys.exit(1)

    out = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "scope": resp.get("scope", scopes),
    }
    os.makedirs(os.path.dirname(creds_file) or ".", exist_ok=True)
    with open(creds_file, "w") as f:
        json.dump(out, f, indent=2)
    try:
        os.chmod(creds_file, 0o600)
    except OSError:
        pass

    print(f"\n  Saved tokens to: {creds_file}")
    print("  Next: set pinterest.board_id in config.json (see list below).")
    list_boards_sample(access_token)
    print("\n  Then: python3 scripts/distribute/distribute.py test\n")


if __name__ == "__main__":
    main()
