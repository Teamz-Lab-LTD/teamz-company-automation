#!/usr/bin/env python3
"""
Local JSON-LD schema validator for static sites.

Walks TEAMZ_HOST_SITE_ROOT for index.html files, extracts every
<script type="application/ld+json"> block, and validates required fields
per @type (BreadcrumbList, FAQPage, WebApplication, Organization).

Usage:
    python3 py/build-schema-validate.py            # validate + print report
    python3 py/build-schema-validate.py --verbose   # show per-page detail

Data: TEAMZ_DATA_DIR/schema-validation-latest.json
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from _teamz_config import load_runtime

_CFG = load_runtime(__file__)

_SKIP_DIR_NAMES = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "teamz-company-automation", "branding",
})

_LDJSON_RE = re.compile(
    r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.DOTALL,
)


def _iter_index_files(root: Path):
    for p in root.rglob("index.html"):
        if any(part in _SKIP_DIR_NAMES for part in p.parts):
            continue
        yield p


def _rel_key(root: Path, f: Path) -> str:
    try:
        rel = f.parent.relative_to(root)
    except ValueError:
        return str(f)
    s = rel.as_posix()
    return "/" if s == "." else f"/{s}/"


def _validate_schema(obj: dict) -> list:
    """Return list of error strings for a single JSON-LD object."""
    errors = []
    schema_type = obj.get("@type", "")

    if schema_type == "BreadcrumbList":
        items = obj.get("itemListElement")
        if not isinstance(items, list) or len(items) == 0:
            errors.append("BreadcrumbList: itemListElement missing or empty")

    elif schema_type == "FAQPage":
        entities = obj.get("mainEntity")
        if not isinstance(entities, list) or len(entities) == 0:
            errors.append("FAQPage: mainEntity missing or empty")
        elif isinstance(entities, list):
            for i, e in enumerate(entities):
                if not isinstance(e, dict):
                    continue
                if not e.get("acceptedAnswer"):
                    errors.append(f"FAQPage: mainEntity[{i}] missing acceptedAnswer")

    elif schema_type == "WebApplication":
        if not obj.get("name"):
            errors.append("WebApplication: missing 'name'")
        if not obj.get("url"):
            errors.append("WebApplication: missing 'url'")

    elif schema_type == "Organization":
        if not obj.get("name"):
            errors.append("Organization: missing 'name'")

    return errors


def main() -> int:
    if _CFG["project_type"] == "app":
        print("Skipped: TEAMZ_PROJECT_TYPE=app (website-only tooling).", file=sys.stderr)
        return 2

    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    root: Path = _CFG["host_site_root"]
    data_dir: Path = _CFG["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)

    if not root.is_dir():
        print(f"ERROR: TEAMZ_HOST_SITE_ROOT not a directory: {root}", file=sys.stderr)
        return 1

    print()
    print("=" * 72)
    print(f"  JSON-LD SCHEMA VALIDATOR — {root}")
    print("=" * 72)

    total_pages = 0
    total_schemas = 0
    pages_valid = 0
    pages_with_errors = 0
    all_errors = []
    page_details = {}

    for f in sorted(_iter_index_files(root), key=lambda p: str(p)):
        total_pages += 1
        try:
            html = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        key = _rel_key(root, f)
        blocks = _LDJSON_RE.findall(html)
        page_errors = []
        page_schemas = []

        for raw_block in blocks:
            try:
                obj = json.loads(raw_block)
            except json.JSONDecodeError as e:
                page_errors.append(f"Invalid JSON: {e}")
                continue

            objs = obj if isinstance(obj, list) else [obj]
            for item in objs:
                if not isinstance(item, dict):
                    continue
                total_schemas += 1
                schema_type = item.get("@type", "unknown")
                page_schemas.append(schema_type)
                errs = _validate_schema(item)
                page_errors.extend(errs)

        page_details[key] = {
            "schemas": page_schemas,
            "errors": page_errors,
            "schema_count": len(page_schemas),
        }

        if page_errors:
            pages_with_errors += 1
            all_errors.append({"page": key, "errors": page_errors})
            if verbose:
                print(f"\n  ERRORS  {key}")
                for e in page_errors:
                    print(f"    - {e}")
        else:
            pages_valid += 1

    # Summary
    print(f"\n  Pages scanned:    {total_pages}")
    print(f"  Schemas found:    {total_schemas}")
    print(f"  Pages valid:      {pages_valid}")
    print(f"  Pages w/ errors:  {pages_with_errors}")

    if all_errors and not verbose:
        print(f"\n  First 20 pages with errors (use --verbose for all):")
        for item in all_errors[:20]:
            print(f"    {item['page']}")
            for e in item["errors"][:3]:
                print(f"      - {e}")

    # Write report
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(root),
        "total_pages": total_pages,
        "total_schemas": total_schemas,
        "pages_valid": pages_valid,
        "pages_with_errors": pages_with_errors,
        "errors": all_errors,
    }
    out_path = data_dir / "schema-validation-latest.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report saved → {out_path.name}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
