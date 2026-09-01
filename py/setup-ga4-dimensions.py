#!/usr/bin/env python3
"""Register the GA4 custom dimensions every teamzlab property is silently throwing away.

WHY THIS EXISTS
---------------
Every teamzlab site sends rich event parameters. GA4 DISCARDS all of them unless the
parameter is registered as a custom dimension first — and on 2026-07-12 all four
properties had ZERO registered:

    tool.teamzlab.com   0        apps.teamzlab.com   0
    goalkit             0        learn.teamzlab.com  0

What that cost, concretely:

  * apps.teamzlab.com fired 194 `cta_click` events in 90 days, each carrying
    cta_type = app_store | play_store | web_open | scroll_to_section.
    GA4 kept the count and threw away the label. So "how many people clicked
    INSTALL?" — the single number that defines "organic downloads while I sleep" —
    was unanswerable. A stray `outbound_click` count of 1 got mistaken for the
    real install number for months.

  * goalkit fired 284 `product_order_click` with channel (whatsapp|messenger) and
    size. Which product, which channel, which size actually sells? Discarded.

  * The tools -> apps cross-link (shared/js/app-cta.js) sends cluster + app_slug so a
    cluster that gets clicks but never converts can be found and deleted. Without
    registration that judgement is impossible and the links can never be evaluated.

NOTE ON RETROACTIVITY: registration is NOT retroactive. Data already collected without
a registered dimension is gone. Every day this is not run is a day of blind data — which
is exactly why it is worth two minutes now.

AUTH
----
The shared analytics-token.json is scoped `analytics.readonly` — enough to read, not to
create dimensions (the API returns 403). This script does its own one-time browser
consent for `analytics.edit` and caches the result separately, so the read-only token
used by every reporting script stays untouched.

USAGE
-----
    python3 py/setup-ga4-dimensions.py            # register everything (idempotent)
    python3 py/setup-ga4-dimensions.py --dry-run  # show what would change
"""
import json
import os
import sys
import urllib.parse
import urllib.request

CFG = os.path.expanduser("~/.config/teamzlab")
READ_TOKEN = os.path.join(CFG, "analytics-token.json")     # existing, readonly — DO NOT overwrite
EDIT_TOKEN = os.path.join(CFG, "analytics-edit-token.json")  # created by this script
SCOPE = "https://www.googleapis.com/auth/analytics.edit"

# param name -> display name. Registered per property only where that param is actually sent.
COMMON = [
    ("app_slug", "App Slug"),
    ("location", "CTA Location"),
    ("page_type", "Page Type"),
]
PROPERTIES = {
    "apps.teamzlab.com": ("524940073", COMMON + [
        ("cta_type", "CTA Type"),        # app_store | play_store | web_open | scroll_to_section
        ("link_url", "Link URL"),
        ("link_domain", "Link Domain"),
        ("cluster", "Cross-link Cluster"),
    ]),
    "tool.teamzlab.com": ("528521795", [
        ("cluster", "Cross-link Cluster"),   # from shared/js/app-cta.js
        ("app_slug", "App Slug"),
        ("source", "Source"),
        ("action", "Action"),
        # web -> app install funnel on the /games/ pages (install_bar_* / install_modal_*).
        # Without these five the events still count, but "which surface sent the installs"
        # and "which store did they pick" are discarded — the same class of loss that made
        # apps.teamzlab.com's 194 cta_click events unreadable for months.
        ("store", "Store"),                  # app_store | play_store | both
        ("surface", "Install Surface"),      # install_bar | win_modal | desktop_modal
        ("game", "Game Slug"),
        ("reason", "Offer Trigger"),         # after_win | qr_scan
        ("how", "Dismiss Method"),           # x | later | backdrop | escape
    ]),
    "goalkit.teamzlab.com": ("537333788", [
        ("channel", "Order Channel"),        # whatsapp | messenger
        ("size", "Selected Size"),
        ("handle", "Product Handle"),
        ("source", "Source"),
        ("action", "Action"),
    ]),
    "learn.teamzlab.com": ("527372960", COMMON),
}
MAX_PER_PROPERTY = 50  # GA4 hard cap on event-scoped custom dimensions


def load_client():
    """Reuse the OAuth client from the read-only token — same Google Cloud app."""
    with open(READ_TOKEN) as f:
        t = json.load(f)
    return t["client_id"], t["client_secret"]


def get_edit_token():
    if os.path.exists(EDIT_TOKEN):
        with open(EDIT_TOKEN) as f:
            t = json.load(f)
        return refresh(t["client_id"], t["client_secret"], t["refresh_token"])

    cid, secret = load_client()
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
    print("\n  ONE-TIME CONSENT — open this URL, approve, paste the code back here:\n")
    print("   ", auth_url, "\n")
    code = input("  paste code: ").strip()
    data = urllib.parse.urlencode({
        "code": code, "client_id": cid, "client_secret": secret,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob", "grant_type": "authorization_code",
    }).encode()
    tok = json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data)))
    payload = {"client_id": cid, "client_secret": secret, "refresh_token": tok["refresh_token"]}
    with open(EDIT_TOKEN, "w") as f:
        json.dump(payload, f, indent=2)
    os.chmod(EDIT_TOKEN, 0o600)
    print(f"  saved {EDIT_TOKEN} (0600)\n")
    return tok["access_token"]


def refresh(cid, secret, rt):
    data = urllib.parse.urlencode({
        "client_id": cid, "client_secret": secret,
        "refresh_token": rt, "grant_type": "refresh_token",
    }).encode()
    return json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data)))["access_token"]


def main():
    dry = "--dry-run" in sys.argv
    at = get_edit_token()
    H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
    created = skipped = failed = 0

    for name, (pid, wanted) in PROPERTIES.items():
        base = f"https://analyticsadmin.googleapis.com/v1beta/properties/{pid}/customDimensions"
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(base, headers=H)))
            existing = {c["parameterName"] for c in r.get("customDimensions", [])}
        except urllib.error.HTTPError as e:
            print(f"  {name}: ❌ cannot read dimensions (HTTP {e.code})")
            failed += 1
            continue

        room = MAX_PER_PROPERTY - len(existing)
        print(f"\n  {name}  ({len(existing)} registered, {room} slots free)")
        for param, display in wanted:
            if param in existing:
                print(f"    — {param:<12} already registered")
                skipped += 1
                continue
            if room <= 0:
                print(f"    ⚠️  {param:<12} SKIPPED — property is at the {MAX_PER_PROPERTY}-dimension cap")
                continue
            if dry:
                print(f"    + {param:<12} would create → '{display}'")
                continue
            body = json.dumps({"parameterName": param, "displayName": display,
                               "scope": "EVENT"}).encode()
            try:
                urllib.request.urlopen(urllib.request.Request(base, data=body, headers=H, method="POST"))
                print(f"    ✅ {param:<12} → '{display}'")
                created += 1
                room -= 1
            except urllib.error.HTTPError as e:
                print(f"    ❌ {param:<12} HTTP {e.code} {e.read()[:80].decode()}")
                failed += 1

    print(f"\n  {'would create' if dry else 'created'}: {created}   already there: {skipped}   failed: {failed}")
    if created and not dry:
        print("  ⚠️  NOT retroactive — these populate from NOW on. Check back in ~48h:")
        print("      cta_click broken down by cta_type = your real install-intent number.")


if __name__ == "__main__":
    main()
