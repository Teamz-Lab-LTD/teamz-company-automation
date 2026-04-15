#!/usr/bin/env python3
"""
ASO Release Notes Generator — auto-generate release-notes-v{version}.json from git log.

Bridges the gap between `changelog-generator` (markdown) and `aso-copy-helper.py`/
`aso-store-release.py` (which validate release-notes-*.json but expect manual auth).

Usage::

    # Auto-detect version from pubspec.yaml, use last tag as base
    python3 py/aso/aso-release-notes-gen.py

    # Explicit version
    python3 py/aso/aso-release-notes-gen.py --version 1.4.0

    # Explicit git range
    python3 py/aso/aso-release-notes-gen.py --since v1.3.0

    # Use `claude` CLI for locale translation (if available), else template fallback
    python3 py/aso/aso-release-notes-gen.py --translate

Locale coverage matches aso-store-release.py release_notes validator:
en, ar, ca, zh-Hans, zh-Hant, hr, cs, da, nl, fi, fr, fr-CA, de, el, he, hi, hu,
id, it, ja, ko, ms, nb, pl, pt-BR, pt-PT, ro, ru, sk, es-MX, es-ES, sv, th, tr, uk, vi

Each locale ≤500 chars (Play Console limit, also safe for App Store).
Writes: {data_dir}/release-notes-v{version}.json

Chains into aso-store-release.py `release_notes` step validator.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _teamz_config import load_runtime  # noqa: E402

_CFG = load_runtime(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py")
)
_DATA_DIR = Path(
    os.environ.get("TEAMZ_DATA_DIR", "")
    or _CFG.get("data_dir", "")
    or str(Path(_CFG["host_site_root"]) / "automation_data")
)
_PROJECT_ROOT = Path(_CFG.get("host_site_root", "."))

# Aligned with aso-store-release.py _LANG_MAP
LOCALES = [
    "en", "ar", "ca", "zh-Hans", "zh-Hant", "hr", "cs", "da", "nl", "fi",
    "fr", "fr-CA", "de", "el", "he", "hi", "hu", "id", "it", "ja",
    "ko", "ms", "nb", "pl", "pt-BR", "pt-PT", "ro", "ru", "sk",
    "es-MX", "es-ES", "sv", "th", "tr", "uk", "vi",
]

# Commit prefix → user-facing verb
PREFIX_MAP = {
    "feat": "Added",
    "add": "Added",
    "fix": "Fixed",
    "bug": "Fixed",
    "perf": "Improved performance of",
    "improve": "Improved",
    "update": "Updated",
    "refactor": "Improved",
    "ui": "Improved UI for",
    "design": "Improved design of",
}

SKIP_PREFIXES = {"chore", "docs", "test", "ci", "build", "style", "revert", "wip"}


def _sh(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except Exception:
        return ""


def _detect_version() -> str:
    pubspec = _PROJECT_ROOT / "pubspec.yaml"
    if pubspec.exists():
        for line in pubspec.read_text(errors="replace").splitlines():
            m = re.match(r"^version:\s*([0-9][0-9.]*)", line.strip())
            if m:
                return m.group(1)
    pkg = _PROJECT_ROOT / "package.json"
    if pkg.exists():
        try:
            return json.loads(pkg.read_text()).get("version", "1.0.0")
        except Exception:
            pass
    return datetime.now().strftime("%Y.%m.%d")


def _detect_since() -> str:
    tag = _sh(["git", "describe", "--tags", "--abbrev=0"], cwd=_PROJECT_ROOT)
    if tag:
        return tag
    # fallback: last 30 commits
    return "HEAD~30"


def _git_log(since: str) -> list[str]:
    rng = f"{since}..HEAD" if since and not since.startswith("HEAD~") else since
    out = _sh(["git", "log", rng, "--pretty=format:%s", "--no-merges"], cwd=_PROJECT_ROOT)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _classify(msg: str) -> tuple[str, str] | None:
    m = re.match(r"^([a-z]+)(\([^)]*\))?!?:\s*(.+)$", msg, re.I)
    if m:
        prefix = m.group(1).lower()
        body = m.group(3).strip()
    else:
        parts = msg.split(":", 1)
        if len(parts) == 2 and len(parts[0]) < 15:
            prefix = parts[0].strip().lower()
            body = parts[1].strip()
        else:
            prefix, body = "update", msg
    if prefix in SKIP_PREFIXES:
        return None
    verb = PREFIX_MAP.get(prefix, "Improved")
    body = body[0].lower() + body[1:] if body else body
    return verb, body


def _build_english(commits: list[str]) -> str:
    bullets = []
    seen = set()
    for c in commits:
        cls = _classify(c)
        if not cls:
            continue
        verb, body = cls
        line = f"• {verb} {body}".rstrip(".")
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        bullets.append(line)
    if not bullets:
        return "• Bug fixes and performance improvements."
    text = "\n".join(bullets)
    # Trim to 500 chars by dropping bullets from the end
    while len(text) > 500 and len(bullets) > 1:
        bullets.pop()
        text = "\n".join(bullets) + "\n• And more."
    return text[:500]


def _translate_claude(text: str, locale: str) -> str | None:
    """Best-effort translation via `claude` CLI if available. Returns None on failure."""
    claude = _sh(["which", "claude"])
    if not claude:
        return None
    prompt = (
        f"Translate the following app release notes to locale '{locale}'. "
        f"Keep bullet structure (• ...), max 500 characters, natural for app-store users. "
        f"Output ONLY the translated text, no preamble.\n\n{text}"
    )
    try:
        r = subprocess.run(
            [claude, "-p", prompt],
            capture_output=True, text=True, timeout=60,
        )
        out = (r.stdout or "").strip()
        if out and len(out) <= 500:
            return out
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None)
    ap.add_argument("--since", default=None, help="Git ref to diff from (default: last tag)")
    ap.add_argument("--translate", action="store_true",
                    help="Use `claude` CLI to translate each locale (else English fallback)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing file")
    args = ap.parse_args()

    version = args.version or _detect_version()
    since = args.since or _detect_since()
    out_path = _DATA_DIR / f"release-notes-v{version}.json"

    if out_path.exists() and not args.force:
        print(f"[skip] {out_path.name} already exists. Use --force to overwrite.", file=sys.stderr)
        return 0

    commits = _git_log(since)
    if not commits:
        print(f"[ERROR] No commits between {since}..HEAD", file=sys.stderr)
        return 1

    print(f"  [info] {len(commits)} commits since {since}", file=sys.stderr)
    english = _build_english(commits)
    print(f"  [ok] English release notes built ({len(english)} chars)", file=sys.stderr)

    out: dict = {"version": version, "en": english}
    translated = 0
    for loc in LOCALES:
        if loc == "en":
            continue
        txt = None
        if args.translate:
            txt = _translate_claude(english, loc)
        out[loc] = txt or english  # fallback: English copy (better than missing)
        if txt:
            translated += 1

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  [ok] Wrote {out_path}", file=sys.stderr)
    print(f"  [info] Translated: {translated}/{len(LOCALES)-1} (others fall back to English)",
          file=sys.stderr)
    print(f"  [next] Run: python3 py/aso/aso-store-release.py --step release_notes",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
