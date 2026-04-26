"""CLI dispatch for web_automation.

Usage:
    python3 -m web_automation list
    python3 -m web_automation run <recipe_name> [recipe-specific flags...]

Recipe modules live under web_automation/recipes/<name>.py and must
expose either:
  * a top-level `Recipe` class, OR
  * a `build_recipe(args)` factory that returns a Recipe instance.

The CLI passes any extra argv to the recipe's argparse parser if it
defines `add_args(parser)`. This keeps each recipe self-contained.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
from pathlib import Path

from . import run, Recipe  # type: ignore
from . import recipes as _recipes_pkg


def _list_recipes() -> list[str]:
    out: list[str] = []
    for info in pkgutil.iter_modules(_recipes_pkg.__path__):
        if info.name.startswith("_"):
            continue
        out.append(info.name)
    return sorted(out)


def _load_recipe(name: str, recipe_argv: list[str]):
    mod = importlib.import_module(f"web_automation.recipes.{name}")
    if hasattr(mod, "build_recipe"):
        # Let the recipe parse its own args
        rp = argparse.ArgumentParser(prog=f"web_automation run {name}")
        if hasattr(mod, "add_args"):
            mod.add_args(rp)
        recipe_args = rp.parse_args(recipe_argv)
        return mod.build_recipe(recipe_args)
    if hasattr(mod, "Recipe"):
        return mod.Recipe()
    raise SystemExit(
        f"recipe {name!r} must export Recipe or build_recipe(args)."
    )


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        argv = ["--help"]

    p = argparse.ArgumentParser(
        prog="python3 -m web_automation",
        description="Generic browser-automation runner",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="List installed recipes")
    s_run = sub.add_parser("run", help="Run a recipe")
    s_run.add_argument("recipe", help="Recipe module name under recipes/")
    s_run.add_argument("--debug", action="store_true", help="Headed + slow-mo")
    s_run.add_argument("--dry-run", action="store_true")
    s_run.add_argument(
        "--only", help="Comma-separated item ids/labels to limit to"
    )
    s_run.add_argument(
        "--headless", action="store_true", help="Force headless"
    )

    # Two-stage parse: outer flags up to '--', recipe flags after.
    if "--" in argv:
        cut = argv.index("--")
        outer, inner = argv[:cut], argv[cut + 1 :]
    else:
        outer, inner = argv, []
    args = p.parse_args(outer)

    if args.cmd == "list":
        print("Installed recipes:")
        for n in _list_recipes():
            print(f"  - {n}")
        return 0

    if args.cmd == "run":
        recipe = _load_recipe(args.recipe, inner)
        only = (
            {s.strip() for s in args.only.split(",")} if args.only else None
        )
        res = run(
            recipe,
            debug=args.debug,
            dry_run=args.dry_run,
            only=only,
            headless=args.headless or None,
        )
        return 0 if res.fail == 0 else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
