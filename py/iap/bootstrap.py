#!/usr/bin/env python3
"""TeamzLab IAP bootstrap orchestrator.

One-command setup: fills App Store Connect + Google Play Console +
RevenueCat catalogs for any new TeamzLab app.

Usage:
  cd <project>
  python3 team_mvp_kit/teamz-company-automation/py/iap/bootstrap.py \\
    --config iap-config.yaml

Idempotent — skips what already exists. Safe to re-run.

Per-stage flags (debug):
  --skip-asc      Skip iOS work
  --skip-play     Skip Android work
  --skip-rc       Skip RevenueCat sync
  --skip-global   Don't expand to 175 territories
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml  # pip install pyyaml

# Add this dir to import path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lib_asc as asc
import lib_play as play
import lib_rc as rc


def stage_asc(cfg: dict, expand_global: bool = True) -> dict:
    """Create + price + localize all iOS products. Returns the
    {sub_id, iap_id} map for use by other stages."""
    print("\n=== ASC iOS ===")
    token = asc.make_jwt()
    bundle = cfg["app"]["ios_bundle_id"]
    app = asc.find_app_by_bundle(token, bundle)
    if not app:
        print(f"  [!] App not found for {bundle}.")
        print(f"      Register the bundle ID at developer.apple.com first.")
        print(f"      Then create the App record in App Store Connect.")
        return {}
    app_id = app["id"]
    cfg["app"]["apple_app_id"] = app_id
    print(f"  [+] App {app['attributes']['name']} (id={app_id})")

    # Subscription group
    grp_ref = (
        cfg["subscription_group"]["reference_name"]
        .replace("{ios_bundle_id}", bundle)
        .replace(".", "_")
    )
    group_id = asc.ensure_subscription_group(token, app_id, grp_ref)
    asc.set_subscription_group_localization(
        token, group_id, cfg["app"]["app_name"],
    )
    print(f"  [+] Sub group: {grp_ref} (id={group_id})")

    existing_subs = asc.list_existing_subscriptions(token, group_id)
    existing_iaps = asc.list_existing_iaps(token, app_id)

    created = {"subscriptions": {}, "iaps": {}}

    # Subscriptions
    for s in cfg["subscriptions"]:
        pid = s["product_id_ios"]
        if pid in existing_subs:
            sub_id = existing_subs[pid]
            print(f"  [=] sub {pid}")
        else:
            sub_id = asc.create_subscription(
                token, group_id, pid, s["reference_name"],
                s["period"],
            )
            asc.add_subscription_localization(
                token, sub_id,
                s["locale_en_us_name"], s["locale_en_us_description"],
            )
            print(f"  [+] sub {pid} (id={sub_id})")
        created["subscriptions"][pid] = sub_id

        # Availability
        territories = (
            asc.list_territory_ids(token)
            if expand_global
            else ["USA"]
        )
        asc.set_subscription_availability_all_territories(
            token, sub_id, territories,
        )
        print(f"      → {len(territories)} territories")

        # Price (USA + equalize globally)
        pp_id = asc.find_sub_price_point(token, sub_id, s["price_usd"])
        if pp_id:
            if asc.set_sub_price_usa(token, sub_id, pp_id):
                print(f"      → USA price ${s['price_usd']} set")
            if expand_global:
                ok, fail = asc.equalize_sub_price_globally(
                    token, sub_id, pp_id,
                )
                print(f"      → equalized to {ok} territories ({fail} failed)")

    # IAPs
    for o in cfg.get("one_time_products", []):
        pid = o["product_id_ios"]
        if pid in existing_iaps:
            iap_id = existing_iaps[pid]
            print(f"  [=] iap {pid}")
        else:
            iap_id = asc.create_iap(
                token, app_id, pid, o["reference_name"], o["ios_kind"],
            )
            asc.add_iap_localization(
                token, iap_id,
                o["locale_en_us_name"], o["locale_en_us_description"],
            )
            pp_id = asc.find_iap_price_point(token, iap_id, o["price_usd"])
            if pp_id:
                if asc.set_iap_price_with_schedule(token, iap_id, pp_id):
                    print(f"  [+] iap {pid} (id={iap_id}, ${o['price_usd']})")
        created["iaps"][pid] = iap_id

    # Review screenshots
    mode = cfg.get("review_screenshot", "placeholder")
    if mode == "placeholder":
        png = asc.make_placeholder_png()
    elif mode.startswith("file:"):
        png = Path(mode[5:]).read_bytes()
    else:
        png = None
    if png:
        for pid, sid in created["subscriptions"].items():
            asc.upload_sub_review_screenshot(token, sid, png)
        for pid, iid in created["iaps"].items():
            asc.upload_iap_review_screenshot(token, iid, png)
        print(f"  [+] review screenshots uploaded for all products")

    return created


def stage_play(cfg: dict) -> None:
    print("\n=== Play Android ===")
    svc = play.make_service()
    pkg = cfg["app"]["android_package_name"]
    existing = play.list_existing(svc, pkg)

    # Subs (multi-base-plan grouping)
    sub_groups: dict[str, list[dict]] = {}
    for s in cfg["subscriptions"]:
        ids = s["product_id_android"].split(":")
        sub_product = ids[0]
        base_plan_id = ids[1] if len(ids) > 1 else "monthly"
        sub_groups.setdefault(sub_product, []).append({
            "id": base_plan_id,
            "period": s["play_period"],
            "price_usd": s["price_usd"],
            "title": s["reference_name"].split()[0],  # "Pro" or "Creator"
            "description": s["locale_en_us_description"],
        })

    for product, plans in sub_groups.items():
        if product in existing["subscriptions"]:
            print(f"  [=] sub {product}")
            continue
        title = plans[0]["title"]
        desc = plans[0]["description"][:80]
        ok = play.create_subscription(svc, pkg, product, title, desc, plans)
        print(f"  [{'+' if ok else '!'}] sub {product} + {len(plans)} base plans")

    # One-time products
    for o in cfg.get("one_time_products", []):
        pid = o["product_id_android"]
        if pid in existing["managed"]:
            print(f"  [=] onetime {pid}")
            continue
        ok = play.create_one_time_product(
            svc, pkg, pid,
            o["locale_en_us_name"], o["locale_en_us_description"],
            o["price_usd"],
        )
        print(f"  [{'+' if ok else '!'}] onetime {pid}")


def stage_rc(cfg: dict) -> None:
    print("\n=== RevenueCat ===")
    key = os.environ.get("REVENUECAT_SECRET_KEY")
    if not key:
        print("  [!] REVENUECAT_SECRET_KEY not set. Skipping RC sync.")
        print("      Set in ~/.zshrc, source it, re-run.")
        return
    project_id = cfg["revenuecat"]["project_id"]
    apps = rc.list_apps(key, project_id)
    print(f"  [+] {len(apps)} RC apps in project {project_id}")

    ios_public_key: str | None = None
    android_public_key: str | None = None

    # Upload ASC API key to iOS apps + fetch public SDK keys.
    for app in apps:
        if app["type"] == "app_store":
            ios_app_id = app["id"]
            configured = app.get("app_store", {}).get(
                "app_store_connect_api_key_configured"
            )
            if not configured:
                try:
                    p8 = asc.DEFAULT_KEY_PATH.read_text()
                    ok = rc.upload_asc_api_key(
                        key, project_id, ios_app_id,
                        p8, asc.DEFAULT_KEY_ID, asc.DEFAULT_ISSUER_ID,
                    )
                    print(
                        f"  [{'+' if ok else '!'}] "
                        f"{app['name']}: ASC key uploaded"
                    )
                except Exception as e:
                    print(f"  [!] {app['name']}: ASC key failed: {e}")
            else:
                print(f"  [=] {app['name']}: ASC key already configured")
            ios_public_key = rc.get_app_public_sdk_key(
                key, project_id, ios_app_id,
            )
        elif app["type"] == "play_store":
            android_public_key = rc.get_app_public_sdk_key(
                key, project_id, app["id"],
            )

    # Paywall theming — if config has design_tokens, push to RC paywall.
    pw_cfg = cfg.get("paywall", {})
    if pw_cfg.get("design_tokens"):
        offering_id = pw_cfg.get("offering_id")
        if not offering_id:
            # Best-effort: pick the first non-archived offering
            offerings = rc.list_offerings(key, project_id)
            if offerings:
                offering_id = offerings[0]["id"]
        if offering_id:
            pw = rc.get_paywall(key, project_id, offering_id)
            pw_id = pw.get("id") if pw else None
            if pw_id:
                ok = rc.update_paywall_theme(
                    key, project_id, pw_id, pw_cfg["design_tokens"],
                )
                print(
                    f"  [{'+' if ok else '!'}] "
                    f"paywall theme synced to design tokens"
                )
            else:
                print(
                    "  [!] no paywall attached to offering "
                    f"{offering_id}; create one in RC dashboard first"
                )

    # Emit Flutter snippet (printed at end of stage).
    entitlement = pw_cfg.get("default_entitlement_id", "premium")
    snippet = rc.emit_flutter_revenuecat_snippet(
        ios_public_key, android_public_key, entitlement,
    )
    print("\n  --- Flutter snippet (paste into main.dart) ---")
    for line in snippet.splitlines():
        print(f"  {line}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="iap-config.yaml")
    parser.add_argument("--skip-asc", action="store_true")
    parser.add_argument("--skip-play", action="store_true")
    parser.add_argument("--skip-rc", action="store_true")
    parser.add_argument("--skip-global", action="store_true")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        sys.exit(f"Config file not found: {cfg_path}")
    cfg = yaml.safe_load(cfg_path.read_text())

    if not args.skip_asc:
        stage_asc(cfg, expand_global=not args.skip_global)
    if not args.skip_play:
        stage_play(cfg)
    if not args.skip_rc:
        stage_rc(cfg)

    print("\nDone. Review remaining manual steps in")
    print("`team_mvp_kit/prompts/iap-bootstrap-guide.md`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
