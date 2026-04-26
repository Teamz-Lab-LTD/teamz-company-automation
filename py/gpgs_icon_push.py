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
    "games/achievements"
)
ACHIEVEMENT_EDIT_URL_TEMPLATE = (
    "https://play.google.com/console/u/0/developers/{dev_id}/app/{app_id}/"
    "games/edit-achievement?id={ach_id}"
)


def _open_list(page: Page, dev_id: str, app_id: str, game_id: str) -> None:
    # game_id no longer in URL — keep param for backward compat
    url = ACHIEVEMENT_LIST_URL_TEMPLATE.format(dev_id=dev_id, app_id=app_id)
    print(f"  → opening {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    # Give the React tree time to hydrate the table
    page.wait_for_load_state("networkidle", timeout=30_000)


def _open_edit(page: Page, dev_id: str, app_id: str, ach_id: str) -> None:
    """Direct deep-link to a single achievement edit page."""
    url = ACHIEVEMENT_EDIT_URL_TEMPLATE.format(
        dev_id=dev_id, app_id=app_id, ach_id=ach_id
    )
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(1500)


def _find_row_by_name(page: Page, name: str):
    """Return the achievement row element matching the display name.

    Play Console renders the table as Angular `<ess-cell>` cells inside
    `[role=row]`. The achievement name is in `div.line` inside an image
    cell. Filter rows by `has_text=` and pick the one with an exact
    match in the name column.
    """
    # has_text uses substring + regex so we anchor with word boundary.
    return page.locator("[role=row]").filter(has_text=name).first


def _open_row(page: Page, name: str) -> bool:
    locator = _find_row_by_name(page, name)
    try:
        locator.wait_for(state="visible", timeout=10_000)
    except PWTimeout:
        print(f"    (skip) row '{name}' not visible")
        return False
    # Clicking the row navigates to the achievement edit page.
    # Click the name cell specifically — clicking row sometimes hits
    # the checkbox cell.
    name_cell = locator.locator("div.line", has_text=name).first
    try:
        name_cell.wait_for(state="visible", timeout=5_000)
        name_cell.click()
    except PWTimeout:
        # Fallback to row click
        locator.click()
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(1500)
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
    """Drop the PNG into the icon file input + click 'Save as draft'.

    Play Console edit page has exactly one input[type=file] (accepts
    .png/.jpg/.jpeg) and the save button reads 'Save as draft'.
    """
    file_inputs = page.locator("input[type='file']")
    if file_inputs.count() == 0:
        print("    (skip) no <input type=file> on this page")
        return False
    file_inputs.first.set_input_files(str(png_path))
    # Wait for the page to register the new file — Play Console swaps
    # the existing thumbnail or shows a 'Replace' button when the new
    # image is staged.
    page.wait_for_timeout(2500)

    # 'Save as draft' is exact button text on this page
    save_btn = page.get_by_role("button", name="Save as draft", exact=True).first
    try:
        save_btn.wait_for(state="visible", timeout=10_000)
        # Button is sometimes disabled briefly while upload preprocesses —
        # poll for enabled state.
        for _ in range(30):
            if not save_btn.is_disabled():
                break
            page.wait_for_timeout(500)
        save_btn.click()
    except PWTimeout:
        print("    (warn) 'Save as draft' button not found")
        return False
    # Wait for save confirmation — the URL typically navigates back to
    # the list, or a 'Saved' toast appears.
    try:
        page.wait_for_selector(
            "text=/Saved|Draft saved|saved as draft/i", timeout=20_000
        )
    except PWTimeout:
        # Fallback: wait for the save button to disappear or the URL to change
        page.wait_for_timeout(5000)
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


def _read_id_map(yaml_data: dict, host_root: Path) -> dict[str, str]:
    """Parse _kPlayGamesAchievementIds map out of lib/app_config.dart."""
    ac = host_root / "lib" / "app_config.dart"
    if not ac.exists():
        return {}
    text = ac.read_text()
    map_var = yaml_data.get("google_id_map_var", "_kPlayGamesAchievementIds")
    idx = text.find(f"{map_var} = {{")
    if idx == -1:
        return {}
    end = text.find("};", idx)
    block = text[idx:end]
    out: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("'") and not line.startswith('"'):
            continue
        if ":" not in line:
            continue
        k, _, rest = line.partition(":")
        v = rest.strip().rstrip(",").strip()
        out[k.strip().strip("'").strip('"')] = v.strip().strip("'").strip('"')
    return out


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

    id_map = _read_id_map(data, Path.cwd())
    if not id_map:
        raise SystemExit(
            "Could not parse _kPlayGamesAchievementIds from lib/app_config.dart. "
            "Need encoded ach IDs (CgkI…) for direct edit URLs."
        )

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

        # If first run + not authed, page redirects to Google sign-in.
        # Poll for the redirect back to play.google.com — handles 2FA,
        # device prompt, account picker, etc, without needing stdin.
        deadline = time.time() + 600  # 10 min budget for login
        while time.time() < deadline and (
            "accounts.google.com" in page.url or "signin" in page.url
        ):
            print("→ Waiting for login in the browser window…")
            time.sleep(5)
        if "accounts.google.com" in page.url or "signin" in page.url:
            print("login timeout — re-run after authenticating once")
            ctx.close()
            return 2
        # Re-navigate after login completes
        _open_list(page, args.dev_id, args.app_id, args.application_id)

        ok = 0
        skip = 0
        for entry in entries:
            name = entry["name"]
            local_id = entry["id"]
            ach_id = id_map.get(local_id, "")
            if not ach_id or ach_id.startswith("TODO_"):
                print(f"  (skip) {local_id}: no encoded id mapped")
                skip += 1
                continue
            png_path = icons_dir / f"{local_id}.png"
            if not png_path.exists():
                print(f"  (skip) {local_id}: no png at {png_path.name}")
                skip += 1
                continue

            print(f"\n  → {name}  ({local_id} / {ach_id})")
            _open_edit(page, args.dev_id, args.app_id, ach_id)
            if args.dry_run:
                print(f"    (dry-run) would upload {png_path.name}")
                continue
            if _upload_icon(page, png_path):
                print("    upload + save ✓")
                ok += 1
            else:
                print("    upload failed")

        print(f"\nDone. Uploaded {ok}, skipped {skip}.")
        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
