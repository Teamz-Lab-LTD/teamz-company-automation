"""Play Console achievement icon uploader.

Replacement for the standalone py/gpgs_icon_push.py — same DOM
selectors, but plugged into the generic web_automation framework
so the same browser-session machinery can power any other recipe.

Reads:
  automation_data/achievements.yaml   (host project's truth file)
  lib/app_config.dart                 (Play Games encoded IDs map)

Writes:
  Play Console drafts via UI — set_input_files on the file input on
  /games/edit-achievement?id=<encoded>, then click 'Save as draft'.

CLI:
  python3 -m web_automation run play_console_icons -- \\
      --dev-id 7194763656319643086 --app-id 4973867897764761646
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

import yaml

from .. import BrowserSession, Recipe


_DEFAULT_DEV_ID = "7194763656319643086"
_DEFAULT_APP_ID = "4973867897764761646"
_LIST_URL = (
    "https://play.google.com/console/u/0/developers/{dev_id}/app/{app_id}/"
    "games/achievements"
)
_EDIT_URL = (
    "https://play.google.com/console/u/0/developers/{dev_id}/app/{app_id}/"
    "games/edit-achievement?id={ach_id}"
)


def _read_id_map(yaml_data: dict, host_root: Path) -> dict[str, str]:
    ac = host_root / "lib" / "app_config.dart"
    if not ac.exists():
        return {}
    text = ac.read_text()
    var = yaml_data.get("google_id_map_var", "_kPlayGamesAchievementIds")
    idx = text.find(f"{var} = {{")
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
        out[k.strip().strip("'").strip('"')] = (
            rest.strip().rstrip(",").strip().strip("'").strip('"')
        )
    return out


class PlayConsoleIconsRecipe(Recipe):
    name = "play_console_icons"
    profile = "play-console"
    headless_default = False  # needs first-run login

    def __init__(
        self,
        *,
        dev_id: str = _DEFAULT_DEV_ID,
        app_id: str = _DEFAULT_APP_ID,
        yaml_path: Optional[Path] = None,
        icons_dir: Optional[Path] = None,
    ) -> None:
        self.dev_id = dev_id
        self.app_id = app_id
        self.yaml_path = (
            yaml_path or Path.cwd() / "automation_data" / "achievements.yaml"
        )
        self.icons_dir = (
            icons_dir or Path.cwd() / "automation_data" / "achievement_icons"
        )
        self._yaml_data: Optional[dict] = None
        self._id_map: dict[str, str] = {}

    def _load(self) -> None:
        if self._yaml_data is not None:
            return
        if not self.yaml_path.exists():
            raise SystemExit(f"yaml missing at {self.yaml_path}")
        self._yaml_data = yaml.safe_load(self.yaml_path.read_text())
        self._id_map = _read_id_map(self._yaml_data, Path.cwd())
        if not self._id_map:
            raise SystemExit(
                "Could not parse encoded achievement IDs from "
                "lib/app_config.dart"
            )

    def setup(self, sess: BrowserSession) -> None:
        self._load()
        list_url = _LIST_URL.format(dev_id=self.dev_id, app_id=self.app_id)
        sess.goto(list_url)
        if not sess.wait_for_login(budget_seconds=600):
            raise SystemExit("login timed out")
        sess.goto(list_url)

    def items(self) -> Iterable[dict]:
        self._load()
        for entry in self._yaml_data.get("achievements") or []:
            local_id = entry["id"]
            ach_id = self._id_map.get(local_id, "")
            if not ach_id or ach_id.startswith("TODO_"):
                continue
            png = self.icons_dir / f"{local_id}.png"
            if not png.exists():
                continue
            yield {
                "id": local_id,
                "name": entry["name"],
                "ach_id": ach_id,
                "png_path": str(png),
            }

    def label(self, item: dict) -> str:
        return f"{item['name']} ({item['id']})"

    def process(self, sess: BrowserSession, item: dict) -> None:
        url = _EDIT_URL.format(
            dev_id=self.dev_id, app_id=self.app_id, ach_id=item["ach_id"]
        )
        sess.goto(url)
        sess.upload("input[type='file']", item["png_path"])
        sess.wait(2500)  # let Play Console pre-process
        sess.click_button("Save as draft")
        # Save toast / draft saved confirmation
        sess.wait_text(r"Saved|Draft saved|saved as draft", timeout_ms=20_000)


# ─────────────────────────────────────────────────────────────────────
# CLI integration
# ─────────────────────────────────────────────────────────────────────

def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--dev-id", default=_DEFAULT_DEV_ID)
    p.add_argument("--app-id", default=_DEFAULT_APP_ID)
    p.add_argument("--yaml")
    p.add_argument("--icons-dir")


def build_recipe(args: argparse.Namespace) -> Recipe:
    return PlayConsoleIconsRecipe(
        dev_id=args.dev_id,
        app_id=args.app_id,
        yaml_path=Path(args.yaml).expanduser() if args.yaml else None,
        icons_dir=Path(args.icons_dir).expanduser() if args.icons_dir else None,
    )
