#!/usr/bin/env python3
"""
Tumblr OAuth1 Authentication Script
Run once to get access tokens, then use them in distribute.py

Usage:
    python3 scripts/distribute/tumblr-auth.py CONSUMER_KEY CONSUMER_SECRET
"""

import sys
import json
import webbrowser
import urllib.request
import urllib.parse
import ssl
import hmac
import hashlib
import base64
import time
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
SSL_CTX = ssl.create_default_context()

REQUEST_TOKEN_URL = "https://www.tumblr.com/oauth/request_token"
AUTHORIZE_URL = "https://www.tumblr.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://www.tumblr.com/oauth/access_token"
CALLBACK_URL = "http://localhost:9998"


class OAuthHandler(BaseHTTPRequestHandler):
    oauth_verifier = None
    oauth_token = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "oauth_verifier" in params:
            OAuthHandler.oauth_verifier = params["oauth_verifier"][0]
            OAuthHandler.oauth_token = params.get("oauth_token", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <html><body style="font-family:sans-serif;text-align:center;padding:50px">
            <h1>Tumblr Authorization Successful!</h1>
            <p>You can close this tab.</p>
            </body></html>""")
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Error</h1></body></html>")

    def log_message(self, format, *args):
        pass


def oauth_sign(method, url, params, consumer_secret, token_secret=""):
    sorted_params = "&".join(
        f"{urllib.parse.quote(k, safe='')}"
        f"={urllib.parse.quote(v, safe='')}"
        for k, v in sorted(params.items())
    )
    base_string = (
        f"{method}&"
        f"{urllib.parse.quote(url, safe='')}&"
        f"{urllib.parse.quote(sorted_params, safe='')}"
    )
    signing_key = (
        f"{urllib.parse.quote(consumer_secret, safe='')}&"
        f"{urllib.parse.quote(token_secret, safe='')}"
    )
    signature = base64.b64encode(
        hmac.new(
            signing_key.encode(),
            base_string.encode(),
            hashlib.sha1
        ).digest()
    ).decode()
    return signature


def oauth_header(params):
    items = ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(params.items())
        if k.startswith("oauth_")
    )
    return f"OAuth {items}"


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/distribute/tumblr-auth.py CONSUMER_KEY CONSUMER_SECRET")
        sys.exit(1)

    consumer_key = sys.argv[1]
    consumer_secret = sys.argv[2]

    # Step 1: Get request token
    print("\n  Getting request token...")
    params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
        "oauth_callback": CALLBACK_URL,
    }
    params["oauth_signature"] = oauth_sign(
        "POST", REQUEST_TOKEN_URL, params, consumer_secret
    )

    req = urllib.request.Request(
        REQUEST_TOKEN_URL,
        data=b"",
        headers={
            "Authorization": oauth_header(params),
            "Content-Length": "0",
            "User-Agent": "TeamzLabDistribute/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, context=SSL_CTX) as resp:
        body = resp.read().decode()

    request_tokens = dict(urllib.parse.parse_qsl(body))
    request_token = request_tokens["oauth_token"]
    request_secret = request_tokens["oauth_token_secret"]
    print(f"  Request token received!")

    # Step 2: Open browser for authorization
    auth_url = f"{AUTHORIZE_URL}?oauth_token={request_token}"
    print(f"  Opening browser for Tumblr authorization...")
    print(f"  If browser doesn't open, go to:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # Step 3: Wait for callback
    print(f"  Waiting for authorization on {CALLBACK_URL}...")
    server = HTTPServer(("localhost", 9998), OAuthHandler)
    server.handle_request()

    if not OAuthHandler.oauth_verifier:
        print("  ERROR: No verifier received")
        sys.exit(1)

    print(f"  Authorization received!")

    # Step 4: Exchange for access token
    print(f"  Exchanging for access token...")
    params = {
        "oauth_consumer_key": consumer_key,
        "oauth_token": request_token,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
        "oauth_verifier": OAuthHandler.oauth_verifier,
    }
    params["oauth_signature"] = oauth_sign(
        "POST", ACCESS_TOKEN_URL, params, consumer_secret, request_secret
    )

    req = urllib.request.Request(
        ACCESS_TOKEN_URL,
        data=b"",
        headers={
            "Authorization": oauth_header(params),
            "Content-Length": "0",
            "User-Agent": "TeamzLabDistribute/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, context=SSL_CTX) as resp:
        body = resp.read().decode()

    access_tokens = dict(urllib.parse.parse_qsl(body))
    oauth_token = access_tokens["oauth_token"]
    oauth_secret = access_tokens["oauth_token_secret"]

    print(f"  Access token received!")

    # Step 5: Get blog name
    print(f"  Getting blog info...")
    info_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_token": oauth_token,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
    }
    info_url = "https://api.tumblr.com/v2/user/info"
    info_params["oauth_signature"] = oauth_sign(
        "GET", info_url, info_params, consumer_secret, oauth_secret
    )

    req = urllib.request.Request(
        info_url,
        headers={
            "Authorization": oauth_header(info_params),
            "User-Agent": "TeamzLabDistribute/1.0",
        },
    )
    with urllib.request.urlopen(req, context=SSL_CTX) as resp:
        user_data = json.loads(resp.read())

    blogs = user_data.get("response", {}).get("user", {}).get("blogs", [])
    blog_name = blogs[0]["name"] if blogs else "unknown"
    print(f"  Blog: {blog_name}")

    # Step 6: Update config
    with open(CONFIG_FILE) as f:
        config = json.load(f)

    config["tumblr"] = {
        "enabled": True,
        "blog_name": blog_name,
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
        "oauth_token": oauth_token,
        "oauth_secret": oauth_secret,
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n  Config updated! Tumblr is now enabled.")
    print(f"  Test with: python3 scripts/distribute/distribute.py test")


if __name__ == "__main__":
    main()
