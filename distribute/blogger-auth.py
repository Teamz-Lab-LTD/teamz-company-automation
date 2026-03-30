#!/usr/bin/env python3
"""
Blogger OAuth2 Authentication Script
Run once to get access token for Blogger API.

Prerequisites:
1. Go to https://console.cloud.google.com/apis/library/blogger.googleapis.com
2. Enable "Blogger API v3" for your project
3. Use existing OAuth2 credentials or create new ones

Usage:
    python3 scripts/distribute/blogger-auth.py

This will:
1. Open browser for Google OAuth2 authorization
2. Get access + refresh token for Blogger API
3. Find your blog ID automatically
4. Save everything to config.json
"""

import json
import sys
import os
import webbrowser
import urllib.request
import urllib.parse
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
CREDS_FILE = os.path.expanduser("~/.config/teamzlab/blogger-credentials.json")
SSL_CTX = ssl.create_default_context()

# Google OAuth2 endpoints
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "http://localhost:9997"
SCOPES = "https://www.googleapis.com/auth/blogger"

# Try to reuse existing Google Cloud credentials
EXISTING_CREDS_LOCATIONS = [
    os.path.expanduser("~/.config/teamzlab/google-ads-credentials.json"),
    os.path.expanduser("~/.config/teamzlab/search-console-credentials.json"),
]


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
            <h1>Blogger Authorization Successful!</h1>
            <p>You can close this tab.</p>
            </body></html>""")
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h1>Error: {error}</h1></body></html>".encode())

    def log_message(self, format, *args):
        pass


def find_google_credentials():
    """Find existing Google OAuth2 client credentials."""
    for path in EXISTING_CREDS_LOCATIONS:
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            # Handle different credential file formats
            if "installed" in data:
                creds = data["installed"]
                return creds.get("client_id"), creds.get("client_secret"), path
            elif "web" in data:
                creds = data["web"]
                return creds.get("client_id"), creds.get("client_secret"), path
            elif "client_id" in data:
                return data["client_id"], data.get("client_secret"), path
    return None, None, None


def main():
    if len(sys.argv) >= 3:
        client_id = sys.argv[1]
        client_secret = sys.argv[2]
    else:
        client_id, client_secret, creds_path = find_google_credentials()
        if client_id:
            print(f"\n  Found existing Google credentials: {creds_path}")
        else:
            print("Usage: python3 scripts/distribute/blogger-auth.py CLIENT_ID CLIENT_SECRET")
            sys.exit(1)

    print(f"  Client ID: {client_id[:30]}...")

    # Step 2: Open browser for authorization
    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print(f"\n  Opening browser for Google authorization...")
    print(f"  If browser doesn't open, go to:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # Step 3: Wait for callback
    print(f"  Waiting for authorization on {REDIRECT_URI}...")
    server = HTTPServer(("localhost", 9997), OAuthHandler)
    server.handle_request()

    if not OAuthHandler.auth_code:
        print("  ERROR: No authorization code received")
        sys.exit(1)

    print(f"  Authorization code received!")

    # Step 4: Exchange for tokens
    print(f"  Exchanging for access token...")
    token_data = urllib.parse.urlencode({
        "code": OAuthHandler.auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=token_data,
        headers={"User-Agent": "TeamzLabDistribute/1.0"})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            tokens = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERROR: HTTP {e.code}: {body}")
        sys.exit(1)

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if not access_token:
        print(f"  ERROR: No access token: {tokens}")
        sys.exit(1)

    print(f"  Access token received!")

    # Step 5: Find blog ID
    print(f"  Finding your blog...")
    req = urllib.request.Request(
        "https://www.googleapis.com/blogger/v3/users/self/blogs",
        headers={"Authorization": f"Bearer {access_token}", "User-Agent": "TeamzLabDistribute/1.0"}
    )
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            blogs_data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERROR getting blogs: HTTP {e.code}: {body}")
        print(f"  Make sure Blogger API v3 is enabled in Google Cloud Console")
        sys.exit(1)

    blogs = blogs_data.get("items", [])
    if not blogs:
        print("  ERROR: No blogs found. Create one at https://www.blogger.com first.")
        sys.exit(1)

    # Pick the first blog (or the one matching teamzlab)
    blog = blogs[0]
    for b in blogs:
        if "teamzlab" in b.get("url", "").lower():
            blog = b
            break

    blog_id = blog["id"]
    blog_url = blog.get("url", "")
    blog_name = blog.get("name", "")
    print(f"  Blog: {blog_name} ({blog_url})")
    print(f"  Blog ID: {blog_id}")

    # Step 6: Save credentials
    os.makedirs(os.path.dirname(CREDS_FILE), exist_ok=True)
    creds = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "token_type": "Bearer",
    }
    with open(CREDS_FILE, "w") as f:
        json.dump(creds, f, indent=2)
    print(f"  Credentials saved to {CREDS_FILE}")

    # Step 7: Update config
    with open(CONFIG_FILE) as f:
        config = json.load(f)

    config["blogger"] = {
        "enabled": True,
        "blog_id": blog_id,
        "credentials_file": CREDS_FILE,
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n  Config updated! Blogger is now enabled.")
    print(f"  Test with: python3 scripts/distribute/distribute.py test")


if __name__ == "__main__":
    main()
