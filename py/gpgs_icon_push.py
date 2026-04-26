#!/usr/bin/env python3
"""Compatibility shim — delegates to web_automation/recipes/play_console_icons.

The original standalone implementation moved into the generic
web_automation framework so the same Playwright machinery (persistent
profile, screenshot-on-fail, recipe lifecycle) powers every
browser-driven task. This file remains so old commands keep working:

    python3 py/gpgs_icon_push.py --application-id <id> --debug

is now equivalent to:

    python3 -m web_automation run play_console_icons --debug

Both call the same code path. Single source of truth lives in
`web_automation/recipes/play_console_icons.py`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the package is importable when this file runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

from web_automation import run  # noqa: E402
from web_automation.recipes.play_console_icons import (  # noqa: E402
    PlayConsoleIconsRecipe,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dev-id", default="7194763656319643086")
    p.add_argument("--app-id", default="4973867897764761646")
    p.add_argument(
        "--application-id",
        required=False,
        help="(retained for back-compat — Play Games numeric application id)",
    )
    p.add_argument("--yaml")
    p.add_argument("--icons-dir")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", help="comma-separated local ids")
    args = p.parse_args()

    recipe = PlayConsoleIconsRecipe(
        dev_id=args.dev_id,
        app_id=args.app_id,
        yaml_path=Path(args.yaml).expanduser() if args.yaml else None,
        icons_dir=Path(args.icons_dir).expanduser() if args.icons_dir else None,
    )
    only = {s.strip() for s in args.only.split(",")} if args.only else None
    res = run(recipe, debug=args.debug, dry_run=args.dry_run, only=only)
    return 0 if res.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
