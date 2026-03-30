#!/usr/bin/env python3
"""
Google Ads Keyword Planner — OAuth Setup
=========================================
One-time auth script. Opens browser to authenticate with Google Ads.
Saves token to ~/.config/teamzlab/google-ads-token.json

Usage:
  python3 scripts/build-keyword-planner-auth.py

Prerequisites:
  pip3 install --break-system-packages google-auth google-auth-oauthlib
"""

import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow

CRED_FILE = os.path.expanduser("~/.config/teamzlab/google-ads-credentials.json")
TOKEN_FILE = os.path.expanduser("~/.config/teamzlab/google-ads-token.json")

# Google Ads API scope
SCOPES = ["https://www.googleapis.com/auth/adwords"]

def main():
    if not os.path.exists(CRED_FILE):
        print(f"ERROR: Credentials file not found at {CRED_FILE}")
        print("Download it from Google Cloud Console → APIs & Services → Credentials")
        return

    print("Opening browser for Google Ads authentication...")
    print("Sign in with: teamz.lab.contact@gmail.com")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(CRED_FILE, scopes=SCOPES)
    credentials = flow.run_local_server(port=0)  # auto-pick available port

    # Load client details from credentials file
    with open(CRED_FILE) as f:
        client_data = json.load(f)["installed"]

    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": client_data["client_id"],
        "client_secret": client_data["client_secret"],
        "scopes": SCOPES,
    }

    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\nToken saved to: {TOKEN_FILE}")
    print("You can now use: ./build-seo-audit.sh --volume \"keyword\"")

if __name__ == "__main__":
    main()
