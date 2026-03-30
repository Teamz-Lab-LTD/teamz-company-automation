#!/usr/bin/env python3
"""
Local crawl snapshot + diff — canonical, robots meta, JSON-LD block count, first H1.

Walks TEAMZ_HOST_SITE_ROOT for index.html (skips .git, node_modules, submodule dirs).
Writes JSON snapshots under TEAMZ_DATA_DIR; compares to previous snapshot when present.

Usage:
    python3 scripts/build-crawl-diff.py              # snapshot + diff vs last
    python3 scripts/build-crawl-diff.py --snapshot-only
    python3 scripts/build-crawl-diff.py --compare path/to/old.json

No network calls — safe for CI or weekly cron.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from _teamz_config import load_runtime

_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "teamz-company-automation",
    }
)

_CANONICAL_RE = re.compile(
    r'<link[^>]+rel\s*=\s*["\']canonical["\'][^>]*href\s*=\s*["\']([^"\']+)["\']',
    re.I,
)
_CANONICAL_RE_ALT = re.compile(
    r'<link[^>]+href\s*=\s*["\']([^"\']+)["\'][^>]+rel\s*=\s*["\']canonical["\']',
    re.I,
)
_ROBOTS_RE = re.compile(
    r'<meta[^>]+name\s*=\s*["\']robots["\'][^>]+content\s*=\s*["\']([^"\']*)["\']',
    re.I,
)
_LDJSON_RE = re.compile(r'<script[^>]+type\s*=\s*["\']application/ld\+json["\']', re.I)
_TITLE_RE = re.compile(r"<title[^>]*>([^<]{1,500})</title>", re.I)
_H1_RE = re.compile(r"<h1[^>]*>([^<]{1,500})</h1>", re.I)


def _strip_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _extract(html: str) -> dict:
    m = _CANONICAL_RE.search(html) or _CANONICAL_RE_ALT.search(html)
    canonical = _strip_ws(m.group(1)) if m else ""
    rm = _ROBOTS_RE.search(html)
    robots = _strip_ws(rm.group(1)).lower() if rm else ""
    tm = _TITLE_RE.search(html)
    title = _strip_ws(tm.group(1)) if tm else ""
    h1m = _H1_RE.search(html)
    h1 = _strip_ws(h1m.group(1)) if h1m else ""
    schema_blocks = len(_LDJSON_RE.findall(html))
    return {
        "canonical": canonical,
        "robots": robots,
        "schema_blocks": schema_blocks,
        "title": title,
        "h1": h1,
    }


def _iter_index_files(root: Path):
    for p in root.rglob("index.html"):
        if any(part in _SKIP_DIR_NAMES for part in p.parts):
            continue
        yield p


def _rel_key(root: Path, file: Path) -> str:
    try:
        rel = file.parent.relative_to(root)
    except ValueError:
        return str(file)
    s = rel.as_posix()
    return "/" if s == "." else f"/{s}/"


def _load_snapshot(path: Path) -> dict:
    return json.loads(path.read_text())


def _diff_pages(old_pages: dict, new_pages: dict) -> List[dict]:
    changes = []
    all_keys = sorted(set(old_pages) | set(new_pages))
    for key in all_keys:
        o = old_pages.get(key)
        n = new_pages.get(key)
        if o is None:
            changes.append({"path": key, "change": "added", "new": n})
            continue
        if n is None:
            changes.append({"path": key, "change": "removed", "old": o})
            continue
        field_diff = {}
        for f in ("canonical", "robots", "schema_blocks", "title", "h1"):
            if o.get(f) != n.get(f):
                field_diff[f] = {"old": o.get(f), "new": n.get(f)}
        if field_diff:
            changes.append({"path": key, "change": "modified", "fields": field_diff})
    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description="Local HTML crawl snapshot + diff")
    ap.add_argument("--snapshot-only", action="store_true", help="Write snapshot only, no diff")
    ap.add_argument("--compare", type=str, default="", help="Explicit prior JSON to diff against")
    args = ap.parse_args()

    cfg = load_runtime(__file__)
    if cfg["project_type"] == "app":
        print("Skipped: TEAMZ_PROJECT_TYPE=app (website-only tooling).", file=sys.stderr)
        return 2

    root: Path = cfg["host_site_root"]
    data_dir: Path = cfg["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)

    if not root.is_dir():
        print(f"ERROR: TEAMZ_HOST_SITE_ROOT is not a directory: {root}", file=sys.stderr)
        return 1

    pages: dict[str, dict] = {}
    errors: list[str] = []

    for f in sorted(_iter_index_files(root), key=lambda p: str(p)):
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            errors.append(f"{f}: {e}")
            continue
        key = _rel_key(root, f)
        pages[key] = _extract(raw)

    snap = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(root),
        "page_count": len(pages),
        "errors": errors,
        "pages": pages,
    }

    ts = datetime.now().strftime("%Y-%m-%d")
    latest = data_dir / "crawl-snapshot-latest.json"
    dated = data_dir / f"crawl-snapshot-{ts}.json"

    prior_path: Optional[Path] = None
    prior_snapshot: Optional[dict] = None
    if args.compare:
        prior_path = Path(args.compare).expanduser()
        if not prior_path.is_file():
            print(f"ERROR: --compare file not found: {prior_path}", file=sys.stderr)
            return 1
        prior_snapshot = _load_snapshot(prior_path)
    elif latest.exists():
        # Compare to last run before overwriting (same-day reruns still get a diff).
        prior_path = latest
        prior_snapshot = _load_snapshot(latest)

    latest.write_text(json.dumps(snap, indent=2))
    dated.write_text(json.dumps(snap, indent=2))

    print("=" * 72)
    print(f"  CRAWL SNAPSHOT — {root}")
    print(f"  Pages: {len(pages)} index.html   → {latest.name} (+ dated copy)")
    if errors:
        print(f"  Read errors: {len(errors)}")
    print("=" * 72)

    if args.snapshot_only:
        return 0

    if prior_snapshot is None:
        print("\n  No prior snapshot to diff (run again after this baseline).")
        return 0

    old = prior_snapshot
    old_pages = old.get("pages") or {}
    changes = _diff_pages(old_pages, pages)

    diff_out = {
        "generated_at": snap["generated_at"],
        "prior_file": str(prior_path),
        "current_file": str(dated),
        "change_count": len(changes),
        "changes": changes,
    }
    diff_latest = data_dir / "crawl-diff-latest.json"
    diff_dated = data_dir / f"crawl-diff-{ts}.json"
    diff_latest.write_text(json.dumps(diff_out, indent=2))
    diff_dated.write_text(json.dumps(diff_out, indent=2))

    print(f"\n  Diff vs {prior_path.name}  → {diff_latest.name}")
    print(f"  Total changes: {len(changes)}\n")

    mods = [c for c in changes if c.get("change") == "modified"]
    adds = [c for c in changes if c.get("change") == "added"]
    rms = [c for c in changes if c.get("change") == "removed"]

    def _show(lst: List[dict], title: str, limit: int = 25) -> None:
        print(f"  {title} ({len(lst)})")
        print("  " + "-" * 60)
        for c in lst[:limit]:
            print(f"  {c['path']}")
            if c.get("change") == "modified":
                for fname, delta in (c.get("fields") or {}).items():
                    print(f"    {fname}: {delta.get('old')!r} → {delta.get('new')!r}")
            elif c.get("change") == "added":
                print(f"    + {c.get('new')}")
            else:
                print(f"    - {c.get('old')}")
        if len(lst) > limit:
            print(f"  ... +{len(lst) - limit} more (see {diff_latest.name})")
        print()

    _show(mods, "Modified")
    _show(adds, "Added pages")
    _show(rms, "Removed pages")

    return 0


if __name__ == "__main__":
    sys.exit(main())
