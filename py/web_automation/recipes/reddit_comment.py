"""Reddit comment poster — leave one comment per thread.

Use cases:
  * Drop release-note links in r/AndroidGaming, r/iOSGaming etc when
    a new build ships (only on subs that allow it — check rules!).
  * Reply to threads asking about your app's category.
  * Bulk follow-ups on existing OP threads (own posts only).

Ethics: Reddit's content policy bans spam + brigading. Don't post
identical text across many subs, don't comment on threads that
don't ask for the kind of content you're posting, and respect each
sub's self-promotion rules (most enforce a 9:1 contribute:promote
ratio). This recipe assumes you've already vetted the targets — it
does not detect spam-likeness.

Yaml shape (host project's `automation_data/reddit_comments.yaml`):

    comments:
      - id: post_2026_04_29_release_notes_androidgaming
        thread_url: "https://www.reddit.com/r/AndroidGaming/comments/abc123/x/"
        body: |
            New v1.4.4 just dropped — added the Mechazilla world…
            (link in thread / pinned comment)
      - id: ...
        thread_url: ...
        body: ...

CLI:
    python3 -m web_automation run reddit_comment -- --yaml automation_data/reddit_comments.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

import yaml

from .. import BrowserSession, Recipe


class RedditCommentRecipe(Recipe):
    name = "reddit_comment"
    profile = "reddit"
    headless_default = False

    def __init__(self, yaml_path: Path) -> None:
        self.yaml_path = yaml_path
        self._data: Optional[dict] = None

    def _load(self) -> dict:
        if self._data is None:
            self._data = yaml.safe_load(self.yaml_path.read_text())
        return self._data

    def setup(self, sess: BrowserSession) -> None:
        sess.goto("https://www.reddit.com/")
        if not sess.wait_for_login(budget_seconds=600):
            raise SystemExit("login timed out")

    def items(self) -> Iterable[dict]:
        for c in self._load().get("comments") or []:
            yield c

    def label(self, item: dict) -> str:
        return item.get("id") or item["thread_url"][-40:]

    def process(self, sess: BrowserSession, item: dict) -> None:
        sess.goto(item["thread_url"])
        sess.wait(2500)

        # Reddit's new layout uses a custom <faceplate-textarea> for the
        # comment composer. Click into it to focus.
        composer = (
            'shreddit-composer textarea, '
            'faceplate-textarea-input, '
            '[name="text"], '
            '[contenteditable="true"]'
        )
        sess.click(composer)
        sess.fill_rich_text(composer, item["body"])

        # The Comment button is inside the same composer
        sess.click_button("Comment")
        # Confirmation: the new comment shows up; URL doesn't change.
        # Wait for the composer to clear.
        sess.wait(3000)


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--yaml",
        default="automation_data/reddit_comments.yaml",
        help="path to comments yaml",
    )


def build_recipe(args: argparse.Namespace) -> Recipe:
    return RedditCommentRecipe(yaml_path=Path(args.yaml).expanduser())
