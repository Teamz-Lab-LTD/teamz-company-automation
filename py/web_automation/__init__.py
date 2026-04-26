"""Generic browser-automation framework for tasks without API/MCP support.

Designed for the Teamz Lab solo-dev workflow: write a small Recipe
class, run it once with `--debug` to log into the target site, then
re-run any time without re-authenticating. Each site gets its own
persistent Chromium profile so cookies + 2FA survive across runs.

Use cases this is built for:
  * Play Console / App Store Connect manual UI work that the REST APIs
    don't expose (achievement icons, A/B experiment buttons, certain
    settings toggles).
  * Bulk blog post drafting (Blogger, Medium, Substack, WordPress).
  * Cross-platform commenting / posting (Reddit, LinkedIn, X, GitHub
    issues / discussions, Discord webhooks via UI).
  * Form-filling on legal / vendor / partner portals that expect
    humans.

What it does NOT solve:
  * CAPTCHA-walled flows.
  * Sites with active anti-bot defences (e.g. Cloudflare's
    Turnstile/Bot Fight, Akamai). Don't go there — risk of account
    flag outweighs the convenience.
  * High-volume scraping. This is for low-volume `O(n)` admin work.

Quickstart:
  from web_automation import BrowserSession, run, Recipe

  class MyRecipe(Recipe):
      name = "blogger_post"
      profile = "blogger"        # ~/.cache/teamzlab/web-profiles/blogger

      def items(self):
          # Yield one dict per row of work — flexible shape.
          for post in load_posts_yaml():
              yield post

      def process(self, sess, item):
          sess.goto("https://www.blogger.com/blog/posts/" + item["blog_id"])
          sess.click_button("New post")
          sess.fill('[aria-label="Title"]', item["title"])
          sess.fill_rich_text('[aria-label="Body"]', item["body"])
          sess.click_button("Publish")
          sess.wait_text("Published", timeout=15_000)

  if __name__ == "__main__":
      run(MyRecipe())

CLI dispatch:
  python3 -m web_automation list              # print all known recipes
  python3 -m web_automation run <name> --debug
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

try:
    from playwright.sync_api import (
        sync_playwright,
        BrowserContext,
        Page,
        TimeoutError as PWTimeout,
        Locator,
    )
except ImportError:
    sync_playwright = None
    BrowserContext = Page = Locator = None  # type: ignore[assignment]
    PWTimeout = TimeoutError  # type: ignore[assignment]


PROFILES_ROOT = Path.home() / ".cache" / "teamzlab" / "web-profiles"
SCREENSHOTS_ROOT = Path.home() / ".cache" / "teamzlab" / "web-screenshots"


def _require_playwright() -> None:
    if sync_playwright is None:
        raise SystemExit(
            "Missing playwright. Install:\n"
            "  pip install --user playwright\n"
            "  python3 -m playwright install chromium"
        )


# ─────────────────────────────────────────────────────────────────────
# BrowserSession — high-level wrapper with project-shaped helpers.
# ─────────────────────────────────────────────────────────────────────

class BrowserSession:
    """Wrap a Playwright BrowserContext with verb-shaped helpers.

    Designed so a Recipe.process() implementation reads like a
    human-readable script: goto / fill / click / upload / wait_text.
    The page can still be accessed via `sess.page` for anything not
    covered.
    """

    def __init__(
        self,
        profile: str,
        *,
        headless: bool = True,
        slow_mo_ms: int = 0,
        viewport: tuple[int, int] = (1440, 900),
        login_redirect_hosts: tuple[str, ...] = (
            "accounts.google.com",
            "appleid.apple.com",
            "login.microsoftonline.com",
            "github.com/login",
            "facebook.com/login",
            "twitter.com/login",
            "x.com/login",
            "reddit.com/login",
            "linkedin.com/login",
            "auth0.com",
            "okta.com",
            "/signin",
        ),
        screenshot_on_fail: bool = True,
    ) -> None:
        _require_playwright()
        self.profile = profile
        self.profile_dir = PROFILES_ROOT / profile
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.viewport = viewport
        self.login_redirect_hosts = login_redirect_hosts
        self.screenshot_on_fail = screenshot_on_fail
        self._pw = None
        self._ctx: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    # ── Lifecycle ────────────────────────────────────────────────────

    def __enter__(self) -> "BrowserSession":
        self._pw = sync_playwright().start()
        self._ctx = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            slow_mo=self.slow_mo_ms,
            viewport={"width": self.viewport[0], "height": self.viewport[1]},
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self._ctx:
                self._ctx.close()
        finally:
            if self._pw:
                self._pw.stop()

    # ── Accessors ────────────────────────────────────────────────────

    @property
    def page(self) -> Page:
        assert self._page is not None, "BrowserSession not entered"
        return self._page

    # ── Navigation + auth ────────────────────────────────────────────

    def goto(self, url: str, *, wait_idle: bool = True, timeout_ms: int = 60_000) -> None:
        self.page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        if wait_idle:
            try:
                self.page.wait_for_load_state("networkidle", timeout=30_000)
            except PWTimeout:
                pass  # some pages stream forever; fall through

    def wait_for_login(self, *, budget_seconds: int = 600) -> bool:
        """Block until URL redirects away from any known login host.

        First runs hit auth pages; the script polls + the user logs in
        manually in the spawned window. Returns True if logged-in URL
        achieved within budget.
        """
        deadline = time.time() + budget_seconds
        last_logged = 0.0
        while time.time() < deadline:
            url = self.page.url
            if not any(h in url for h in self.login_redirect_hosts):
                return True
            now = time.time()
            if now - last_logged > 8:
                print(f"  → waiting for login… url={url}")
                last_logged = now
            time.sleep(3)
        return False

    # ── Verb helpers ────────────────────────────────────────────────

    def fill(self, selector: str, value: str, *, clear_first: bool = True) -> None:
        loc = self.page.locator(selector).first
        loc.wait_for(state="visible", timeout=15_000)
        if clear_first:
            loc.fill("")
        loc.fill(value)

    def fill_rich_text(self, selector: str, html_or_text: str) -> None:
        """Type into contenteditable rich-text editors (Medium, Blogger,
        LinkedIn). Falls back to clipboard paste for HTML content."""
        loc = self.page.locator(selector).first
        loc.wait_for(state="visible", timeout=15_000)
        loc.click()
        # Plain text path
        if "<" not in html_or_text or ">" not in html_or_text:
            loc.type(html_or_text, delay=10)
            return
        # Pseudo-HTML path — paste via clipboard JS
        self.page.evaluate(
            "(html) => navigator.clipboard.writeText(html)",
            html_or_text,
        )
        self.page.keyboard.press("Meta+V")

    def click(self, selector: str, *, timeout_ms: int = 15_000) -> None:
        loc = self.page.locator(selector).first
        loc.wait_for(state="visible", timeout=timeout_ms)
        loc.click()

    def click_button(self, name: str, *, exact: bool = True, timeout_ms: int = 15_000) -> None:
        """Click a <button>/role=button by accessible name."""
        loc = self.page.get_by_role("button", name=name, exact=exact).first
        loc.wait_for(state="visible", timeout=timeout_ms)
        # Wait briefly for enable
        for _ in range(30):
            if not loc.is_disabled():
                break
            self.page.wait_for_timeout(300)
        loc.click()

    def click_link(self, name: str, *, exact: bool = True, timeout_ms: int = 15_000) -> None:
        loc = self.page.get_by_role("link", name=name, exact=exact).first
        loc.wait_for(state="visible", timeout=timeout_ms)
        loc.click()

    def click_text(self, text: str, *, timeout_ms: int = 15_000) -> None:
        loc = self.page.get_by_text(text, exact=False).first
        loc.wait_for(state="visible", timeout=timeout_ms)
        loc.click()

    def upload(self, selector: str, path: str | Path, *, timeout_ms: int = 15_000) -> None:
        loc = self.page.locator(selector).first
        loc.wait_for(state="attached", timeout=timeout_ms)
        loc.set_input_files(str(path))

    def select(self, selector: str, value: str) -> None:
        loc = self.page.locator(selector).first
        loc.select_option(value=value)

    def check(self, selector: str) -> None:
        self.page.locator(selector).first.check()

    def uncheck(self, selector: str) -> None:
        self.page.locator(selector).first.uncheck()

    # ── Waiting ──────────────────────────────────────────────────────

    def wait(self, ms: int) -> None:
        self.page.wait_for_timeout(ms)

    def wait_text(self, pattern: str, *, timeout_ms: int = 20_000) -> bool:
        """Wait for text matching `pattern` (regex if it contains
        regex metacharacters, else substring) to appear anywhere on
        the page. Returns True on match, False on timeout."""
        try:
            self.page.wait_for_selector(f"text=/{pattern}/i", timeout=timeout_ms)
            return True
        except PWTimeout:
            return False

    def wait_url(self, pattern: str, *, timeout_ms: int = 20_000) -> bool:
        """Wait for the URL to match a regex/substring."""
        try:
            self.page.wait_for_url(re.compile(pattern), timeout=timeout_ms)
            return True
        except PWTimeout:
            return False

    def wait_visible(self, selector: str, *, timeout_ms: int = 20_000) -> bool:
        try:
            self.page.locator(selector).first.wait_for(
                state="visible", timeout=timeout_ms
            )
            return True
        except PWTimeout:
            return False

    # ── Diagnostics ──────────────────────────────────────────────────

    def screenshot(self, label: str) -> Path:
        SCREENSHOTS_ROOT.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        path = SCREENSHOTS_ROOT / f"{self.profile}-{label}-{ts}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return path


# ─────────────────────────────────────────────────────────────────────
# Recipe — small base contract.
# ─────────────────────────────────────────────────────────────────────

class Recipe(ABC):
    """A site/task automation. Subclass + override the abstract bits.

    Lifecycle on each `run(recipe)`:
      1. Browser opens with persistent profile `recipe.profile`.
      2. setup(sess) → optional one-shot prep (e.g. wait_for_login).
      3. for item in items():
         a. is_done(sess, item)? skip if already done.
         b. process(sess, item)
         c. on exception → screenshot + continue.
    """

    name: str = ""
    profile: str = ""           # cache dir name under ~/.cache/teamzlab/web-profiles/
    headless_default: bool = False  # most flows need user interaction

    def setup(self, sess: BrowserSession) -> None:
        """Override to do one-shot prep — e.g. navigate to a base URL
        and call sess.wait_for_login()."""
        return None

    @abstractmethod
    def items(self) -> Iterable[dict]:
        """Yield dicts describing each unit of work."""

    def is_done(self, sess: BrowserSession, item: dict) -> bool:
        """Optional idempotency hook — return True to skip."""
        return False

    @abstractmethod
    def process(self, sess: BrowserSession, item: dict) -> None:
        """Do the work for one item. Throw on hard failure."""

    def label(self, item: dict) -> str:
        """Human-readable label for logs (override for clarity)."""
        return item.get("id") or item.get("name") or repr(item)[:50]


# ─────────────────────────────────────────────────────────────────────
# Runner — what binds the CLI to recipes.
# ─────────────────────────────────────────────────────────────────────

@dataclass
class RunResult:
    ok: int = 0
    skip: int = 0
    fail: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)


def run(
    recipe: Recipe,
    *,
    debug: bool = False,
    dry_run: bool = False,
    only: Optional[set[str]] = None,
    headless: Optional[bool] = None,
) -> RunResult:
    """Drive a recipe end-to-end. Returns counts."""
    if not recipe.profile:
        raise SystemExit(f"recipe {recipe.name!r} has no profile name set")

    is_headless = (
        headless if headless is not None else (recipe.headless_default and not debug)
    )
    slow_mo = 200 if debug else 0
    res = RunResult()

    print(f"=== running recipe: {recipe.name} ===")
    print(f"  profile : ~/.cache/teamzlab/web-profiles/{recipe.profile}")
    print(f"  mode    : {'debug (headed, slow)' if debug else 'normal'}")
    print(f"  dry-run : {dry_run}")

    with BrowserSession(
        profile=recipe.profile, headless=is_headless, slow_mo_ms=slow_mo
    ) as sess:
        recipe.setup(sess)

        for item in recipe.items():
            label = recipe.label(item)
            if only and label not in only and item.get("id") not in only:
                continue
            print(f"\n  → {label}")
            try:
                if recipe.is_done(sess, item):
                    print("    (skip) already done")
                    res.skip += 1
                    continue
                if dry_run:
                    print("    (dry-run) would process")
                    continue
                recipe.process(sess, item)
                print("    ok ✓")
                res.ok += 1
            except Exception as e:
                if sess.screenshot_on_fail:
                    try:
                        snap = sess.screenshot(f"fail-{label}")
                        print(f"    ✗ {type(e).__name__}: {e}\n    screenshot → {snap}")
                    except Exception:
                        print(f"    ✗ {type(e).__name__}: {e}")
                else:
                    print(f"    ✗ {type(e).__name__}: {e}")
                res.fail += 1
                res.errors.append((label, f"{type(e).__name__}: {e}"))

    print(f"\nDone. ok={res.ok}  skip={res.skip}  fail={res.fail}")
    return res


__all__ = [
    "BrowserSession",
    "Recipe",
    "RunResult",
    "run",
    "PROFILES_ROOT",
    "SCREENSHOTS_ROOT",
]
