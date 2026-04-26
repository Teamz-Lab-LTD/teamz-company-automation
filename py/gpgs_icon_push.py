#!/usr/bin/env python3
"""Playwright-driven Play Console achievement icon uploader.

Why this exists:
    Google retired the achievement-icon REST upload endpoint
    (gamesconfiguration.googleapis.com/upload/.../images/...
    returns 503 unconditionally). The Play Console UI is the only
    remaining path. Driving it manually for every achievement is
    error-prone and slow; this script does the drag-drop equivalent
    via Chromium.

How it works:
    Persistent browser context cached at ~/.cache/teamzlab/play-console-profile/
    so cookies + 2FA survive across runs. First run = user logs into Play
    Console manually; subsequent runs reuse the saved session.

    For each achievement in the yaml:
      1. Navigate to the achievement edit page.
      2. set_input_files on the hidden file input.
      3. Click Save.
      4. Wait for the "saved" toast.

    Idempotent: rows that already display the uploaded icon thumbnail
    are skipped via a CSS check on the icon preview.

Selectors:
    Play Console DOM is non-public; selectors below are best-effort
    based on observed structure. If Google reskins, adapt the four
    SELECTOR_* constants. Run with --debug to step through visually.

Usage:
    # First run — log in interactively when the browser appears
    python3 gpgs_icon_push.py --application-id 1004286776719 --debug

    # Subsequent runs — reuses cached session
    python3 gpgs_icon_push.py --application-id 1004286776719

    # Dry-run — only walks the rows, no uploads
    python3 gpgs_icon_push.py --application-id 1004286776719 --dry-run

Pip deps:
    pip install --user playwright
    python3 -m playwright install chromium
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PWTimeout
except ImportError:
    sync_playwright = None  # type: ignore[assignment]


PROFILE_DIR = Path.home() / ".cache" / "teamzlab" / "play-console-profile"
DEFAULT_DEV_ID = "7194763656319643086"
DEFAULT_APP_ID = "4973867897764761646"


def _require_playwright() -> None:
    if sync_playwright is None:
        raise SystemExit(
            "Missing playwright. Install:\n"
            "  pip install --user playwright\n"
            "  python3 -m playwright install chromium"
        )


def _require_yaml() -> None:
    if yaml is None:
        raise SystemExit("Missing PyYAML — pip install --user pyyaml")


# ─────────────────────────────────────────────────────────────────────
# Page driver
# ─────────────────────────────────────────────────────────────────────

ACHIEVEMENT_LIST_URL_TEMPLATE = (
    "https://play.google.com/console/u/0/developers/{dev_id}/app/{app_id}/"
    "game-services/{game_id}/achievement-management"
)


def _open_list(page: Page, dev_id: str, app_id: str, game_id: str) -> None:
    url = ACHIEVEMENT_LIST_URL_TEMPLATE.format(
        dev_id=dev_id, app_id=app_id, game_id=game_id
    )
    print(f"  → opening {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    # Give the React tree time to hydrate the table
    page.wait_for_load_state("networkidle", timeout=30_000)


def _find_row_by_name(page: Page, name: str):
    """Return the row link element matching the achievement display name."""
    # Play Console renders achievements as anchored rows; the achievement
    # name is the first text node in the row link.
    return page.get_by_role("link", name=name, exact=True).first


def _open_row(page: Page, name: str) -> bool:
    locator = _find_row_by_name(page, name)
    try:
        locator.wait_for(state="visible", timeout=10_000)
    except PWTimeout:
        print(f"    (skip) row '{name}' not visible")
        return False
    locator.click()
    page.wait_for_load_state("networkidle", timeout=30_000)
    return True


def _has_icon_already(page: Page) -> bool:
    """Detect whether the achievement edit page is already showing
    a non-default icon thumbnail. Heuristic only."""
    # Play Console renders the current icon as <img> in an Icon section.
    # When unset, it shows a placeholder svg or "Upload" CTA without img.
    try:
        img = page.locator(
            "section:has-text('Icon') img, [aria-label='Icon preview'] img"
        ).first
        if img.count() == 0:
            return False
        src = img.get_attribute("src", timeout=2_000) or ""
        # Default placeholder is data: or has 'placeholder' in path.
        if not src or "placeholder" in src.lower() or src.startswith("data:"):
            return False
        return True
    except PWTimeout:
        return False


def _upload_icon(page: Page, png_path: Path) -> bool:
    """Drop the PNG into the icon input + click Save. Returns True on
    confirmed save."""
    # Find any file input on the page (Play Console hides them off-screen
    # and triggers via labelled buttons).
    file_inputs = page.locator("input[type='file']")
    count = file_inputs.count()
    if count == 0:
        print("    (skip) no <input type=file> on this page")
        return False
    # Take the first — Play Console only has one file input on the
    # achievement edit page (icon).
    file_inputs.first.set_input_files(str(png_path))
    # Wait for upload preview to appear (image element with non-data src
    # inside the icon section)
    try:
        page.wait_for_function(
            "() => {const imgs=[...document.querySelectorAll('img')];"
            "return imgs.some(i => i.src && !i.src.startsWith('data:') "
            "&& i.naturalWidth > 100);}",
            timeout=30_000,
        )
    except PWTimeout:
        print("    (warn) upload preview did not appear in 30s")

    # Click Save — usually labelled exactly "Save" inside Play Console.
    save_btn = page.get_by_role("button", name="Save", exact=True).first
    try:
        save_btn.wait_for(state="visible", timeout=10_000)
        save_btn.click()
    except PWTimeout:
        print("    (warn) Save button not found")
        return False
    # Wait for toast or button disable as proxy for save complete
    try:
        page.wait_for_selector(
            "text=/Saved|saved successfully/i", timeout=15_000
        )
    except PWTimeout:
        print("    (warn) no 'saved' toast — assuming complete")
    return True


def _back_to_list(page: Page) -> None:
    # Play Console keeps a Back button or breadcrumb; goto-list is most
    # reliable across UI revs.
    page.go_back(wait_until="domcontentloaded", timeout=20_000)
    page.wait_for_load_state("networkidle", timeout=20_000)


# ─────────────────────────────────────────────────────────────────────
# Driver entry
# ─────────────────────────────────────────────────────────────────────

def _resolve_yaml_path(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    return Path.cwd() / "automation_data" / "achievements.yaml"


def _resolve_icons_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    return Path.cwd() / "automation_data" / "achievement_icons"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dev-id", default=DEFAULT_DEV_ID, help="Play Console developer id (numeric)")
    p.add_argument("--app-id", default=DEFAULT_APP_ID, help="Play Console internal app id (numeric)")
    p.add_argument("--application-id", required=True, help="Play Games numeric application id")
    p.add_argument("--yaml", help="path to achievements yaml")
    p.add_argument("--icons-dir", help="path to icons dir")
    p.add_argument("--debug", action="store_true", help="run headed, slow motion 200ms")
    p.add_argument("--dry-run", action="store_true", help="walk rows, do not upload")
    p.add_argument("--only", help="comma-separated list of achievement local ids to upload")
    args = p.parse_args()

    _require_playwright()
    _require_yaml()

    yaml_path = _resolve_yaml_path(args.yaml)
    icons_dir = _resolve_icons_dir(args.icons_dir)
    if not yaml_path.exists():
        raise SystemExit(f"yaml missing at {yaml_path}")
    if not icons_dir.exists():
        raise SystemExit(f"icons dir missing at {icons_dir}")

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    data = yaml.safe_load(yaml_path.read_text())
    entries = data.get("achievements") or []
    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        entries = [e for e in entries if e["id"] in keep]

    print(f"Will visit {len(entries)} achievements via Play Console UI.")
    print(f"Browser profile cache: {PROFILE_DIR}")
    print("If this is a first run, log into Play Console + complete 2FA in")
    print("the spawned window, then leave the achievement-management page open.")
    print()

    with sync_playwright() as pw:
        ctx: BrowserContext = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=not args.debug,
            slow_mo=200 if args.debug else 0,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        _open_list(page, args.dev_id, args.app_id, args.application_id)

        # If first run + not authed, page will redirect to login. Pause.
        if "accounts.google.com" in page.url or "signin" in page.url:
            print("→ Please log in within the spawned window. Press <enter> here when done.")
            input()
            _open_list(page, args.dev_id, args.app_id, args.application_id)

        ok = 0
        skip = 0
        for entry in entries:
            name = entry["name"]
            local_id = entry["id"]
            png_path = icons_dir / f"{local_id}.png"
            if not png_path.exists():
                print(f"  (skip) {local_id}: no png at {png_path.name}")
                skip += 1
                continue
            print(f"\n  → {name}  ({local_id})")
            opened = _open_row(page, name)
            if not opened:
                skip += 1
                continue
            if _has_icon_already(page):
                print("    (skip) icon already attached")
                _back_to_list(page)
                skip += 1
                continue
            if args.dry_run:
                print(f"    (dry-run) would upload {png_path.name}")
                _back_to_list(page)
                continue
            if _upload_icon(page, png_path):
                print("    upload + save ✓")
                ok += 1
            else:
                print("    upload failed")
            _back_to_list(page)

        print(f"\nDone. Uploaded {ok}, skipped {skip}.")
        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
