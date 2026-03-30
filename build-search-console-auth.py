#!/usr/bin/env python3
"""
One-time OAuth setup for Google Search Console API.
Run this once: python3 build-search-console-auth.py
It will open your browser to sign in, then save the token for future use.
"""
import json
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/webmasters',  # Needed for URL Inspection API
]
TOKEN_FILE = os.path.expanduser('~/.config/teamzlab/search-console-token.json')
CLIENT_CONFIG_FILE = os.path.expanduser('~/.config/teamzlab/oauth-client-config.json')

def main():
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)

    if not os.path.exists(CLIENT_CONFIG_FILE):
        print(f'ERROR: OAuth client config not found at {CLIENT_CONFIG_FILE}')
        print(f'Create it with your Google OAuth client_id and client_secret:')
        print(f'  {{"installed": {{"client_id": "YOUR_ID", "client_secret": "YOUR_SECRET", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": ["http://localhost"]}}}}')
        sys.exit(1)

    with open(CLIENT_CONFIG_FILE) as f:
        CLIENT_CONFIG = json.load(f)

    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    token_data = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes) if creds.scopes else SCOPES
    }

    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f, indent=2)

    print(f'✅ Token saved to {TOKEN_FILE}')
    print(f'   Sign in as: {creds.token[:20]}...')
    print(f'   Now run: ./build-search-console.sh')

if __name__ == '__main__':
    main()
