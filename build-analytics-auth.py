#!/usr/bin/env python3
"""
Google Analytics (GA4) OAuth2 Authentication
Run once to get access token for Analytics Data API.

Usage:
    python3 scripts/build-analytics-auth.py
    python3 scripts/build-analytics-auth.py CLIENT_ID CLIENT_SECRET
"""

import json
import sys
import os
import webbrowser
import urllib.request
import urllib.parse
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN_FILE = os.path.expanduser("~/.config/teamzlab/analytics-token.json")
SCOPES = "https://www.googleapis.com/auth/analytics.readonly"
REDIRECT_URI = "http://localhost:9996"

SSL_CTX = ssl.create_default_context()


class OAuthHandler(BaseHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            OAuthHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <html><body style="font-family:sans-serif;text-align:center;padding:50px">
            <h1>Analytics Authorization Successful!</h1>
            <p>You can close this tab.</p>
            </body></html>""")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    # Get credentials
    if len(sys.argv) >= 3:
        client_id = sys.argv[1]
        client_secret = sys.argv[2]
    else:
        # Try reusing existing Google credentials
        creds_locations = [
            os.path.expanduser("~/.config/teamzlab/blogger-credentials.json"),
            os.path.expanduser("~/.config/teamzlab/google-ads-credentials.json"),
        ]
        client_id = client_secret = None

        # Check blogger credentials (has client_id/secret directly)
        for path in creds_locations:
            if os.path.exists(path):
                with open(path) as f:
                    data = json.load(f)
                if "client_id" in data and "client_secret" in data:
                    client_id = data["client_id"]
                    client_secret = data["client_secret"]
                    print(f"\n  Reusing credentials from: {path}")
                    break
                elif "installed" in data:
                    client_id = data["installed"]["client_id"]
                    client_secret = data["installed"]["client_secret"]
                    print(f"\n  Reusing credentials from: {path}")
                    break

        if not client_id:
            print("Usage: python3 scripts/build-analytics-auth.py CLIENT_ID CLIENT_SECRET")
            sys.exit(1)

    print(f"  Client ID: {client_id[:30]}...")

    # Open browser
    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(auth_params)}"

    print(f"\n  Opening browser for Google Analytics authorization...")
    print(f"  If browser doesn't open, go to:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    print(f"  Waiting for authorization on {REDIRECT_URI}...")
    server = HTTPServer(("localhost", 9996), OAuthHandler)
    server.handle_request()

    if not OAuthHandler.auth_code:
        print("  ERROR: No authorization code received")
        sys.exit(1)

    print(f"  Authorization code received!")

    # Exchange for tokens
    print(f"  Exchanging for access token...")
    token_data = urllib.parse.urlencode({
        "code": OAuthHandler.auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=token_data,
        headers={"User-Agent": "TeamzLab/1.0"})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            tokens = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  ERROR: HTTP {e.code}: {e.read().decode()}")
        sys.exit(1)

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if not access_token:
        print(f"  ERROR: {tokens}")
        sys.exit(1)

    # Save token
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    token_data = {
        "token": access_token,
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"  Token saved to {TOKEN_FILE}")

    # Test: fetch property metadata
    print(f"  Testing connection...")
    req = urllib.request.Request(
        "https://analyticsdata.googleapis.com/v1beta/properties/528521795/metadata",
        headers={"Authorization": f"Bearer {access_token}", "User-Agent": "TeamzLab/1.0"})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            print(f"  Connected to GA4 property 528521795!")
    except urllib.error.HTTPError as e:
        print(f"  Warning: API test returned {e.code} — may need a moment to propagate")

    print(f"\n  Setup complete! Run: ./build-analytics.sh")


if __name__ == "__main__":
    main()
