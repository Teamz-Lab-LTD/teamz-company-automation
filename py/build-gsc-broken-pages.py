#!/usr/bin/env python3
"""
Auto-detect + redirect GSC 404 pages.

Pulls top N pages from Google Search Console searchAnalytics for the last
28 days. For each page that does NOT exist as a local HTML file, fuzzy-matches
the URL slug against the live inventory and appends a `RedirectMatch 301` rule
to .htaccess. Idempotent — skips rules that already exist.

Designed to run in the nightly cron Phase 1. Zero quota (no LLM).

Usage:
    python3 scripts/build-gsc-broken-pages.py
    python3 scripts/build-gsc-broken-pages.py --days 90 --row-limit 5000
    python3 scripts/build-gsc-broken-pages.py --dry-run        # show without writing
    python3 scripts/build-gsc-broken-pages.py --threshold 0.7  # match strictness

Output:
    .htaccess (appended) — only new rules added under AUTO-GSC-404 marker
    data/gsc-broken-pages-latest.json — full list of detected 404s + matches

Requires: TEAMZ_SC_TOKEN_FILE, TEAMZ_SITE_PROPERTY, TEAMZ_GOOGLE_CLOUD_PROJECT
"""

import argparse
import difflib
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _teamz_config import load_runtime  # noqa: E402

_CTX = ssl.create_default_context()
AUTO_MARKER = "# AUTO-GSC-404 (managed by build-gsc-broken-pages.py — do not edit between markers)"
AUTO_END = "# END AUTO-GSC-404"


def _refresh_token(token_path: Path, project: str) -> Optional[str]:
    if not token_path.exists():
        return None
    data = json.loads(token_path.read_text())
    body = urllib.parse.urlencode(
        {
            "client_id": data["client_id"],
            "client_secret": data["client_secret"],
            "refresh_token": data["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=body, method="POST"
    )
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=30) as r:
            return json.loads(r.read())["access_token"]
    except urllib.error.HTTPError as e:
        print(f"ERROR refreshing token: {e.code} {e.read().decode()[:200]}", file=sys.stderr)
        return None


def _gsc_pages(token: str, site: str, start: str, end: str, row_limit: int) -> List[dict]:
    payload = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["page"],
        "rowLimit": row_limit,
    }
    req = urllib.request.Request(
        f"https://searchconsole.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(site, safe='')}/searchAnalytics/query",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=60) as r:
            return json.loads(r.read()).get("rows", [])
    except urllib.error.HTTPError as e:
        print(f"ERROR GSC query: {e.code} {e.read().decode()[:200]}", file=sys.stderr)
        return []


def _inventory(host_root: Path) -> set:
    skip_prefix = ("scripts", ".git", "node_modules", ".claude", "teamz-company-automation", "logs")
    paths = set()
    for p in host_root.rglob("index.html"):
        try:
            rel = p.relative_to(host_root).parent.as_posix()
        except ValueError:
            continue
        if rel == "." or any(rel.startswith(s) for s in skip_prefix):
            continue
        paths.add("/" + rel + "/")
    return paths


_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _norm_slug(path: str) -> str:
    return _NORMALIZE_RE.sub("-", path.lower()).strip("-")


def _fuzzy_match(broken: str, inventory: set, threshold: float) -> Optional[str]:
    """Pick best-matching existing slug for a broken URL path."""
    broken_norm = _norm_slug(broken)
    if not broken_norm:
        return None
    # Build a search corpus of slug → path for quick fuzzy lookup
    candidates = {p: _norm_slug(p) for p in inventory}
    best = difflib.get_close_matches(
        broken_norm, list(candidates.values()), n=1, cutoff=threshold
    )
    if not best:
        return None
    for path, norm in candidates.items():
        if norm == best[0]:
            return path
    return None


GARBAGE_RE = re.compile(r"[)<>?=&]|[^\x00-\x7F]")
FILE_EXT_RE = re.compile(r"\.(txt|xml|json|js|css|png|jpg|jpeg|gif|svg|webp|ico|pdf|map|webmanifest)/?$", re.IGNORECASE)


def _is_garbage(path: str) -> bool:
    """Googlebot misparsed inline text — skip these."""
    return bool(GARBAGE_RE.search(path)) or len(path) > 200


def _is_file_path(path: str, host_root: Path) -> bool:
    """Skip paths that map to real static files at site root (llms.txt, sitemap.xml, etc.)."""
    if FILE_EXT_RE.search(path):
        bare = path.rstrip("/").lstrip("/")
        if (host_root / bare).is_file():
            return True
    return False


def _existing_redirects(htaccess: str) -> set:
    """Pull paths already covered by RedirectMatch 301/410/404 rules so we don't double-add."""
    covered = set()
    for line in htaccess.splitlines():
        m = re.match(r"^RedirectMatch\s+(?:301|410|404)\s+\^([^\s$?]+)", line)
        if m:
            covered.add(m.group(1).rstrip("\\"))
    return covered


def _update_htaccess(htaccess_path: Path, new_rules: List[Tuple[str, str]], dry_run: bool) -> int:
    """Insert/replace AUTO-GSC-404 block in .htaccess. Returns count added."""
    if not new_rules:
        return 0
    content = htaccess_path.read_text() if htaccess_path.exists() else ""
    # Remove existing AUTO block if present (we always rewrite it idempotently)
    block_re = re.compile(
        r"\n?" + re.escape(AUTO_MARKER) + r".*?" + re.escape(AUTO_END) + r"\n?",
        re.DOTALL,
    )
    content_without = block_re.sub("", content).rstrip() + "\n"
    block_lines = [AUTO_MARKER, f"# Generated {datetime.now().isoformat()}"]
    for path_from, path_to in sorted(new_rules):
        # Escape regex metas in source path
        path_from_re = re.escape(path_from.rstrip("/"))
        block_lines.append(f"RedirectMatch 301 ^{path_from_re}/?$ {path_to}")
    block_lines.append(AUTO_END)
    new_content = content_without + "\n" + "\n".join(block_lines) + "\n"
    if dry_run:
        print(f"[dry-run] would write {len(new_rules)} rules between {AUTO_MARKER!r} markers")
        return len(new_rules)
    htaccess_path.write_text(new_content)
    return len(new_rules)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28, help="lookback window")
    ap.add_argument("--row-limit", type=int, default=2000, help="max pages to fetch from GSC")
    ap.add_argument("--threshold", type=float, default=0.78, help="fuzzy match cutoff (0-1)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_runtime(__file__)
    host_root: Path = cfg["host_site_root"]
    site_property: str = cfg["site_property"]
    token_path: Path = cfg["sc_token_file"]
    project: str = cfg["google_project"]
    data_dir: Path = cfg["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)

    token = _refresh_token(token_path, project)
    if not token:
        print("ERROR: could not refresh GSC token.", file=sys.stderr)
        return 1

    end = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=2 + args.days)).strftime("%Y-%m-%d")
    print(f"[broken-pages] fetching top {args.row_limit} GSC pages, {start} .. {end}")
    rows = _gsc_pages(token, site_property, start, end, args.row_limit)
    if not rows:
        print("[broken-pages] no GSC data returned")
        return 0

    inventory = _inventory(host_root)
    print(f"[broken-pages] live inventory: {len(inventory)} pages")

    htaccess_path = host_root / ".htaccess"
    htaccess = htaccess_path.read_text() if htaccess_path.exists() else ""
    covered = _existing_redirects(htaccess)
    print(f"[broken-pages] existing redirect coverage: {len(covered)} paths")

    base = site_property.rstrip("/")
    broken_404s: List[dict] = []
    matched: List[Tuple[str, str]] = []
    unmatched: List[dict] = []
    skipped_garbage = 0

    for row in rows:
        page = row.get("keys", [""])[0]
        if not page.startswith(base):
            continue
        path = page[len(base):]
        if not path.startswith("/"):
            path = "/" + path
        if not path.endswith("/"):
            # Pages without trailing slash are still real if INDEX.html exists at the path
            path = path + "/"
        if path in inventory:
            continue  # page is live
        if _is_file_path(path, host_root):
            continue  # real static file (llms.txt, sitemap.xml, etc.)
        if _is_garbage(path):
            skipped_garbage += 1
            continue
        if path.rstrip("/") in covered or path in covered:
            continue  # already redirected
        clicks = row.get("clicks", 0)
        impr = row.get("impressions", 0)
        entry = {
            "path": path,
            "clicks": clicks,
            "impressions": impr,
        }
        broken_404s.append(entry)
        match = _fuzzy_match(path, inventory, args.threshold)
        if match:
            entry["match"] = match
            matched.append((path, match))
        else:
            unmatched.append(entry)

    report = {
        "generated_at": datetime.now().isoformat(),
        "site": site_property,
        "window_days": args.days,
        "row_limit": args.row_limit,
        "threshold": args.threshold,
        "counts": {
            "gsc_pages": len(rows),
            "live_inventory": len(inventory),
            "existing_redirects": len(covered),
            "broken_404s": len(broken_404s),
            "auto_matched": len(matched),
            "unmatched": len(unmatched),
            "garbage_skipped": skipped_garbage,
        },
        "matched": [{"from": f, "to": t} for f, t in matched],
        "unmatched": unmatched[:50],
    }
    out_latest = data_dir / "gsc-broken-pages-latest.json"
    out_latest.write_text(json.dumps(report, indent=2))
    print(f"[broken-pages] report → {out_latest}")
    print(
        f"[broken-pages] detected {len(broken_404s)} broken pages "
        f"({len(matched)} auto-redirectable, {len(unmatched)} unmatched, {skipped_garbage} garbage)"
    )

    added = _update_htaccess(htaccess_path, matched, args.dry_run)
    if added:
        print(f"[broken-pages] wrote {added} new 301 rules to .htaccess")
    else:
        print("[broken-pages] no new redirects needed — .htaccess already covers everything")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
