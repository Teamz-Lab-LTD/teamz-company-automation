"""Blogger.com post drafter / publisher.

Drives the Blogger UI to create draft or published posts in bulk
from a yaml file. Useful when the Blogger v3 API is too rigid or
when you want WYSIWYG behaviour the API can't reproduce
(line-spacing, embedded gadgets, custom CSS classes).

Yaml shape (host project's `automation_data/blogger_posts.yaml`):

    blog_id: "1234567890123456789"     # numeric blog id, see Blogger URL
    posts:
      - id: 2026-04-29-launch-recap
        title: "Launch recap — week 17"
        body: |
            <p>Body in HTML or plain text.</p>
            <p>Multi-paragraph fine.</p>
        labels: [release, weekly]      # optional
        publish: true                   # default false → save as draft

CLI:
    python3 -m web_automation run blogger_post -- --yaml automation_data/blogger_posts.yaml

First run: log into the Blogger account once, profile cached at
~/.cache/teamzlab/web-profiles/blogger.

NOTE: Selectors below are first-pass and will need live calibration
on your Blogger UI version (Google reskins frequently). Run with
--debug to step through and surface any selector mismatches before
running the full batch.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

import yaml

from .. import BrowserSession, Recipe


class BloggerPostRecipe(Recipe):
    name = "blogger_post"
    profile = "blogger"
    headless_default = False

    def __init__(self, yaml_path: Path) -> None:
        self.yaml_path = yaml_path
        self._data: Optional[dict] = None

    def _load(self) -> dict:
        if self._data is None:
            self._data = yaml.safe_load(self.yaml_path.read_text())
        return self._data

    def setup(self, sess: BrowserSession) -> None:
        data = self._load()
        sess.goto(f"https://www.blogger.com/blog/posts/{data['blog_id']}")
        if not sess.wait_for_login(budget_seconds=600):
            raise SystemExit("login timed out")
        sess.goto(f"https://www.blogger.com/blog/posts/{data['blog_id']}")

    def items(self) -> Iterable[dict]:
        data = self._load()
        for post in data.get("posts") or []:
            yield post

    def label(self, item: dict) -> str:
        return item.get("title", item.get("id", "?"))

    def process(self, sess: BrowserSession, item: dict) -> None:
        # Open new-post editor
        sess.click_button("New post")
        # The Blogger editor opens at /blog/post/edit/...
        sess.wait_url(r"/blog/post/edit", timeout_ms=15_000)
        sess.wait(1500)

        # Title
        sess.fill('input[aria-label="Title" i]', item["title"])

        # Body — Blogger uses an iframe or contenteditable. Try
        # contenteditable first; if missing, switch to HTML view.
        try:
            sess.fill_rich_text(
                '[role="textbox"], [contenteditable="true"]', item["body"]
            )
        except Exception:
            # Fallback: open HTML view via the toolbar button
            sess.click_button("HTML view")
            sess.fill('textarea', item["body"])

        # Labels
        for lab in item.get("labels") or []:
            sess.click_button("Labels")
            sess.fill('input[aria-label*="Label" i]', lab)
            sess.page.keyboard.press("Enter")

        # Publish or save as draft
        if item.get("publish"):
            sess.click_button("Publish")
            sess.click_button("Confirm")  # confirmation modal
            sess.wait_text(r"Published|Post published", timeout_ms=20_000)
        else:
            sess.click_button("Save")
            sess.wait_text(r"Saved|Draft saved", timeout_ms=20_000)


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--yaml",
        default="automation_data/blogger_posts.yaml",
        help="path to posts yaml",
    )


def build_recipe(args: argparse.Namespace) -> Recipe:
    return BloggerPostRecipe(yaml_path=Path(args.yaml).expanduser())
