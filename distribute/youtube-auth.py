#!/usr/bin/env python3
"""
YouTube API Auth — Teamz Lab Tools
Reuses existing OAuth client to get YouTube Data API token.

Usage:
    python3 scripts/youtube-auth.py          # Authenticate (opens browser)
    python3 scripts/youtube-auth.py --test   # Test connection + show channel info
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import http.server
import webbrowser
import threading
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "teamzlab"
OAUTH_CONFIG = CONFIG_DIR / "oauth-client-config.json"
TOKEN_FILE = CONFIG_DIR / "youtube-token.json"

# YouTube scopes: upload, manage, read analytics
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

REDIRECT_PORT = 8888
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"


def load_oauth_config():
    if not OAUTH_CONFIG.exists():
        print(f"ERROR: OAuth config not found at {OAUTH_CONFIG}")
        print("Run: python3 build-search-console-auth.py first")
        sys.exit(1)
    data = json.loads(OAUTH_CONFIG.read_text())
    key = list(data.keys())[0]
    return data[key]


def exchange_code(client_id, client_secret, code):
    """Exchange authorization code for tokens"""
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def refresh_token(client_id, client_secret, refresh_tok):
    """Refresh an expired access token"""
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_tok,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    result["refresh_token"] = refresh_tok  # Google doesn't return refresh_token on refresh
    return result


def get_valid_token():
    """Get a valid access token, refreshing if needed"""
    if not TOKEN_FILE.exists():
        print(f"ERROR: No YouTube token. Run: python3 scripts/youtube-auth.py")
        sys.exit(1)
    token_data = json.loads(TOKEN_FILE.read_text())
    config = load_oauth_config()

    # Try to use existing token first, refresh if needed
    try:
        # Test if token works
        req = urllib.request.Request(
            "https://www.googleapis.com/youtube/v3/channels?part=id&mine=true",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        urllib.request.urlopen(req)
        return token_data["access_token"]
    except urllib.error.HTTPError:
        # Token expired, refresh it
        new_tokens = refresh_token(config["client_id"], config["client_secret"], token_data["refresh_token"])
        TOKEN_FILE.write_text(json.dumps(new_tokens, indent=2))
        return new_tokens["access_token"]


def authenticate():
    """Run OAuth flow — opens browser for user to authorize"""
    config = load_oauth_config()
    client_id = config["client_id"]
    client_secret = config["client_secret"]

    # Build auth URL
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    })
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{params}"

    # Start local server to catch redirect
    auth_code = [None]

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            if "code" in params:
                auth_code[0] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>YouTube Connected!</h1><p>You can close this tab.</p></body></html>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authorization failed")

        def log_message(self, format, *args):
            pass  # Suppress logs

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), Handler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    print(f"Opening browser for YouTube authorization...")
    print(f"Sign in with: teamz.lab.contact@gmail.com\n")
    webbrowser.open(auth_url)

    thread.join(timeout=120)
    server.server_close()

    if not auth_code[0]:
        print("ERROR: No authorization code received")
        sys.exit(1)

    print("Exchanging code for tokens...")
    tokens = exchange_code(client_id, client_secret, auth_code[0])
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
    print(f"Token saved to {TOKEN_FILE}")
    print("YouTube API connected!\n")
    return tokens["access_token"]


def test_connection():
    """Test the connection and show channel info"""
    token = get_valid_token()

    # Get channel info
    url = "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails&mine=true"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        resp = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"API Error {e.code}: {body[:500]}")
        print("\nIf 403: YouTube Data API may need a few minutes to activate.")
        print("Wait 2-3 minutes and run: python3 scripts/youtube-auth.py --test")
        return
    data = json.loads(resp.read())

    if not data.get("items"):
        print("ERROR: No channel found for this account")
        return

    ch = data["items"][0]
    snippet = ch["snippet"]
    stats = ch["statistics"]

    print("=" * 50)
    print(f"  Channel: {snippet['title']}")
    print(f"  ID: {ch['id']}")
    print(f"  Handle: @{snippet.get('customUrl', 'N/A')}")
    print(f"  Subscribers: {stats.get('subscriberCount', '?')}")
    print(f"  Videos: {stats.get('videoCount', '?')}")
    print(f"  Views: {stats.get('viewCount', '?')}")
    print(f"  Created: {snippet.get('publishedAt', '?')[:10]}")
    print("=" * 50)
    print("\nYouTube API is working!")


def main():
    if "--test" in sys.argv:
        test_connection()
    else:
        authenticate()
        print("Testing connection...\n")
        test_connection()


if __name__ == "__main__":
    main()
