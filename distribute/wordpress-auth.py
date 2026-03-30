#!/usr/bin/env python3
"""
WordPress.com OAuth2 Authentication Script
Run once to get an access token, then use it in distribute.py

Usage:
    python3 scripts/distribute/wordpress-auth.py CLIENT_ID CLIENT_SECRET

This will:
1. Open your browser to authorize the app
2. Listen for the redirect on localhost:9999
3. Exchange the code for an access token
4. Save the token to config.json
"""

import sys
import json
import webbrowser
import urllib.request
import urllib.parse
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
SSL_CTX = ssl.create_default_context()


class OAuthHandler(BaseHTTPRequestHandler):
    """Handle the OAuth2 redirect."""
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
            <h1>Authorization Successful!</h1>
            <p>You can close this tab and go back to the terminal.</p>
            </body></html>
            """)
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h1>Error: {error}</h1></body></html>".encode())

    def log_message(self, format, *args):
        pass  # Suppress server logs


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/distribute/wordpress-auth.py CLIENT_ID CLIENT_SECRET")
        print("\nGet these from: https://developer.wordpress.com/apps/")
        sys.exit(1)

    client_id = sys.argv[1]
    client_secret = sys.argv[2]
    redirect_uri = "http://localhost:9999"

    # Step 1: Open browser for authorization
    auth_url = (
        f"https://public-api.wordpress.com/oauth2/authorize?"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"response_type=code&"
        f"scope=global"
    )

    print(f"\n  Opening browser for WordPress.com authorization...")
    print(f"  If browser doesn't open, go to:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # Step 2: Start local server to catch redirect
    print(f"  Waiting for authorization on {redirect_uri}...")
    server = HTTPServer(("localhost", 9999), OAuthHandler)
    server.handle_request()  # Handle one request then stop

    if not OAuthHandler.auth_code:
        print("  ERROR: No authorization code received")
        sys.exit(1)

    print(f"  Authorization code received!")

    # Step 3: Exchange code for access token
    print(f"  Exchanging code for access token...")
    token_data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": OAuthHandler.auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }).encode()

    req = urllib.request.Request(
        "https://public-api.wordpress.com/oauth2/token",
        data=token_data,
        headers={"User-Agent": "TeamzLabDistribute/1.0"}
    )

    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERROR: HTTP {e.code}: {body}")
        sys.exit(1)

    access_token = result.get("access_token")
    blog_id = result.get("blog_id")
    blog_url = result.get("blog_url", "")

    if not access_token:
        print(f"  ERROR: No access token in response: {result}")
        sys.exit(1)

    print(f"  Access token received!")
    print(f"  Blog ID: {blog_id}")
    print(f"  Blog URL: {blog_url}")

    # Step 4: Update config.json
    with open(CONFIG_FILE) as f:
        config = json.load(f)

    config["wordpress"] = {
        "enabled": True,
        "site": blog_url.replace("https://", "").replace("http://", "").rstrip("/") if blog_url else config.get("wordpress", {}).get("site", ""),
        "access_token": access_token,
        "blog_id": str(blog_id) if blog_id else "",
        "username": config.get("wordpress", {}).get("username", ""),
        "app_password": config.get("wordpress", {}).get("app_password", "")
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n  Config updated! WordPress.com is now enabled.")
    print(f"  Test with: python3 scripts/distribute/distribute.py test")


if __name__ == "__main__":
    main()
