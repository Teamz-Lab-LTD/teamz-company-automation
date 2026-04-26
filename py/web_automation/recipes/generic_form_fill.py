"""Generic form-fill recipe — drives any form from a yaml spec.

For one-off vendor / partner / legal portals where building a custom
recipe isn't worth it. Each row in the yaml is a sequence of steps
the runner walks linearly.

Yaml shape:

    base_url: "https://partner.example.com/dashboard"
    rows:
      - id: row-2026-04-29-acme
        steps:
          - action: goto
            url: "https://partner.example.com/forms/new"
          - action: fill
            selector: '#legal-name'
            value: "Teamz Lab LTD"
          - action: select
            selector: '#country'
            value: "GB"
          - action: check
            selector: '#agree-terms'
          - action: upload
            selector: 'input[type=file][name=logo]'
            path: "automation_data/logo.png"
          - action: click_button
            name: "Submit"
          - action: wait_text
            pattern: "Submitted"
            timeout_ms: 30000

Supported actions:
  goto, fill, fill_rich_text, click, click_button, click_link, click_text,
  upload, select, check, uncheck, wait, wait_text, wait_url, wait_visible,
  screenshot

CLI:
    python3 -m web_automation run generic_form_fill -- --yaml my_form.yaml --profile <profile_name>
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

import yaml

from .. import BrowserSession, Recipe


class GenericFormFillRecipe(Recipe):
    name = "generic_form_fill"
    headless_default = False

    def __init__(self, yaml_path: Path, profile: str) -> None:
        self.yaml_path = yaml_path
        self.profile = profile  # override class-level default
        self._data: Optional[dict] = None

    def _load(self) -> dict:
        if self._data is None:
            self._data = yaml.safe_load(self.yaml_path.read_text())
        return self._data

    def setup(self, sess: BrowserSession) -> None:
        data = self._load()
        if data.get("base_url"):
            sess.goto(data["base_url"])
            if not sess.wait_for_login(budget_seconds=600):
                raise SystemExit("login timed out")

    def items(self) -> Iterable[dict]:
        for row in self._load().get("rows") or []:
            yield row

    def label(self, item: dict) -> str:
        return item.get("id", "row")

    def process(self, sess: BrowserSession, item: dict) -> None:
        for step in item.get("steps") or []:
            action = step.get("action")
            if action == "goto":
                sess.goto(step["url"])
            elif action == "fill":
                sess.fill(step["selector"], str(step["value"]))
            elif action == "fill_rich_text":
                sess.fill_rich_text(step["selector"], str(step["value"]))
            elif action == "click":
                sess.click(step["selector"])
            elif action == "click_button":
                sess.click_button(step["name"], exact=step.get("exact", True))
            elif action == "click_link":
                sess.click_link(step["name"], exact=step.get("exact", True))
            elif action == "click_text":
                sess.click_text(step["text"])
            elif action == "upload":
                sess.upload(step["selector"], step["path"])
            elif action == "select":
                sess.select(step["selector"], step["value"])
            elif action == "check":
                sess.check(step["selector"])
            elif action == "uncheck":
                sess.uncheck(step["selector"])
            elif action == "wait":
                sess.wait(int(step["ms"]))
            elif action == "wait_text":
                sess.wait_text(
                    step["pattern"],
                    timeout_ms=int(step.get("timeout_ms", 20_000)),
                )
            elif action == "wait_url":
                sess.wait_url(
                    step["pattern"],
                    timeout_ms=int(step.get("timeout_ms", 20_000)),
                )
            elif action == "wait_visible":
                sess.wait_visible(
                    step["selector"],
                    timeout_ms=int(step.get("timeout_ms", 20_000)),
                )
            elif action == "screenshot":
                sess.screenshot(step.get("label", "step"))
            else:
                raise SystemExit(f"unknown action: {action!r}")


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--yaml", required=True, help="path to form yaml")
    p.add_argument(
        "--profile",
        required=True,
        help="profile dir name under ~/.cache/teamzlab/web-profiles/",
    )


def build_recipe(args: argparse.Namespace) -> Recipe:
    return GenericFormFillRecipe(
        yaml_path=Path(args.yaml).expanduser(), profile=args.profile
    )
