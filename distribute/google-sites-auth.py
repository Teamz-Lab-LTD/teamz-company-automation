#!/usr/bin/env python3
"""
Google Sites Bridge — Setup Helper

Interactive script to configure the Google Sites distribution platform.
Guides you through deploying the Apps Script web app and configuring distribute.py.

Usage:
    python3 scripts/distribute/google-sites-auth.py
    python3 scripts/distribute/google-sites-auth.py --test
    python3 scripts/distribute/google-sites-auth.py --list
"""

import json
import os
import sys
import secrets
import urllib.request
import urllib.error
import ssl
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
KEY_FILE = Path(os.path.expanduser("~/.config/teamzlab/google-sites-key.txt"))
BRIDGE_SCRIPT = SCRIPT_DIR / "google-sites-bridge.gs"
SSL_CTX = ssl.create_default_context()


def generate_secret_key():
    """Generate a secure random key."""
    return secrets.token_urlsafe(32)


def test_bridge(webapp_url, secret_key):
    """Test the Apps Script bridge connection."""
    print("\n  Testing bridge connection...")

    # Health check
    health_url = webapp_url + ("&" if "?" in webapp_url else "?") + "action=health"
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "TeamzLabDistribute/1.0"})
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") == "ok":
            print(f"  OK — Bridge v{data.get('version', '?')} is running")
            print(f"  Site URL: {data.get('site_url', 'not set')}")
        else:
            print(f"  WARNING — Unexpected response: {json.dumps(data)[:200]}")
            return False
    except Exception as e:
        print(f"  FAILED — Could not reach bridge: {e}")
        return False

    # List pages test
    list_url = webapp_url + ("&" if "?" in webapp_url else "?") + f"action=list&key={secret_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "TeamzLabDistribute/1.0"})
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if "error" in data:
            print(f"  WARNING — List failed: {data['error']}")
            if "key" in data["error"].lower():
                print(f"  → Secret key mismatch. Update the key in Apps Script Properties.")
            return False
        count = data.get("count", 0)
        print(f"  OK — {count} page(s) tracked")
    except Exception as e:
        print(f"  WARNING — List test failed: {e}")
        return False

    print("\n  All tests passed!")
    return True


def list_pages(webapp_url, secret_key):
    """List all pages created via the bridge."""
    list_url = webapp_url + ("&" if "?" in webapp_url else "?") + f"action=list&key={secret_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "TeamzLabDistribute/1.0"})
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        pages = data.get("pages", [])
        if not pages:
            print("\n  No pages created yet.\n")
            return

        print(f"\n{'=' * 70}")
        print(f"  GOOGLE SITES PAGES ({len(pages)} total)")
        print(f"{'=' * 70}\n")

        for p in pages:
            print(f"  {p.get('title', 'Untitled')}")
            print(f"    URL: {p.get('url', 'N/A')}")
            print(f"    Tags: {p.get('tags', 'none')}")
            print(f"    Created: {p.get('created', 'unknown')[:10]}")
            print()

    except Exception as e:
        print(f"\n  ERROR: {e}\n")


def interactive_setup():
    """Guide the user through setting up the Google Sites bridge."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  Google Sites Bridge — Setup                                 ║
╚══════════════════════════════════════════════════════════════╝

This will set up automated posting to Google Sites via an Apps Script bridge.
Articles are created as publicly-shared Google Docs (dofollow backlinks, DA 96+).

""")

    # Step 1: Generate secret key
    print("Step 1: Secret Key")
    print("─" * 40)
    secret_key = generate_secret_key()
    print(f"  Generated secret key: {secret_key}")
    print(f"  (You'll need this in both Apps Script and distribute config)")

    # Save key to file
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(secret_key)
    print(f"  Saved to: {KEY_FILE}")

    # Step 2: Deploy Apps Script
    print(f"""
Step 2: Deploy the Apps Script Web App
─{"─" * 39}
  1. Go to https://script.google.com → New Project
  2. Name it: "Teamz Lab Google Sites Bridge"
  3. Delete any default code in Code.gs
  4. Paste the ENTIRE contents of:
     {BRIDGE_SCRIPT}
  5. Go to Project Settings (gear icon) → Script Properties
     Add these properties:
       SECRET_KEY = {secret_key}
       SITE_URL   = https://sites.google.com/view/YOUR-SITE-NAME
  6. Click Deploy → New deployment
     - Type: Web app
     - Execute as: Me (your Google account)
     - Who has access: Anyone
  7. Click Deploy → Copy the web app URL
""")

    # Step 3: Get the web app URL
    print("Step 3: Enter your Web App URL")
    print("─" * 40)
    webapp_url = input("  Paste your Apps Script web app URL: ").strip()

    if not webapp_url:
        print("\n  No URL provided. You can set it later in config.json:")
        print('    "google_sites": { "webapp_url": "YOUR_URL", "secret_key": "YOUR_KEY" }')
        return

    # Step 4: Test connection
    print("\nStep 4: Testing connection...")
    print("─" * 40)
    success = test_bridge(webapp_url, secret_key)

    # Step 5: Update config
    print(f"\nStep 5: Updating config")
    print("─" * 40)

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    else:
        config = {}

    config["google_sites"] = {
        "enabled": success,
        "webapp_url": webapp_url,
        "secret_key": secret_key
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    if success:
        print(f"  Config updated — google_sites ENABLED")
    else:
        print(f"  Config updated — google_sites DISABLED (fix issues above, then set enabled=true)")

    print(f"""
{"═" * 60}
  SETUP COMPLETE!
{"═" * 60}

  Web App URL:  {webapp_url}
  Secret Key:   {secret_key}
  Key File:     {KEY_FILE}
  Status:       {"ENABLED" if success else "DISABLED — fix issues above"}

  Test:   python3 {__file__} --test
  List:   python3 {__file__} --list
  Post:   python3 scripts/distribute/distribute.py post "Title" article.md --platforms google_sites
""")


def load_credentials():
    """Load webapp_url and secret_key from config."""
    if not CONFIG_FILE.exists():
        print("  ERROR: config.json not found. Run setup first.")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    cfg = config.get("google_sites", {})
    webapp_url = cfg.get("webapp_url", "").strip()
    secret_key = cfg.get("secret_key", "")

    if not secret_key and KEY_FILE.exists():
        secret_key = KEY_FILE.read_text().strip()

    if not webapp_url:
        print("  ERROR: No webapp_url configured. Run setup first:")
        print(f"    python3 {__file__}")
        sys.exit(1)

    return webapp_url, secret_key


def main():
    args = sys.argv[1:]

    if "--test" in args:
        webapp_url, secret_key = load_credentials()
        test_bridge(webapp_url, secret_key)
    elif "--list" in args:
        webapp_url, secret_key = load_credentials()
        list_pages(webapp_url, secret_key)
    else:
        interactive_setup()


if __name__ == "__main__":
    main()
