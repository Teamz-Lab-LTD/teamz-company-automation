#!/usr/bin/env python3
"""
Topic cluster summary — groups static site pages by top-level hub (folder under site root).

Intent: complement hub-centric views with a roll-up of URL counts per cluster for planning.
Outputs JSON under TEAMZ_DATA_DIR (topic-cluster-latest.json).

Usage:
    python3 scripts/build-topic-cluster-report.py
    python3 scripts/build-topic-cluster-report.py --csv   # also print CSV to stdout
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from _teamz_config import load_runtime

_SKIP = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        "teamz-company-automation",
        "branding",
        "icons",
        "og-images",
    }
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Topic cluster roll-up by top-level hub folder")
    ap.add_argument("--csv", action="store_true", help="Print CSV summary to stdout")
    args = ap.parse_args()

    cfg = load_runtime(__file__)
    if cfg["project_type"] == "app":
        print("Skipped: TEAMZ_PROJECT_TYPE=app (website-only tooling).", file=sys.stderr)
        return 2

    root: Path = cfg["host_site_root"]
    data_dir: Path = cfg["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)

    if not root.is_dir():
        print(f"ERROR: invalid TEAMZ_HOST_SITE_ROOT: {root}", file=sys.stderr)
        return 1

    # cluster -> list of relative path keys like /ai/meme-maker/
    clusters: Dict[str, List[str]] = defaultdict(list)

    for p in root.rglob("index.html"):
        if any(x in _SKIP for x in p.parts):
            continue
        try:
            rel = p.parent.relative_to(root)
        except ValueError:
            continue
        parts = rel.parts
        if not parts:
            clusters["/"].append("/")
            continue
        top = parts[0]
        key = rel.as_posix()
        path_key = "/" if key == "." else f"/{key}/"
        clusters[top].append(path_key)

    rows = []
    for hub, paths in sorted(clusters.items(), key=lambda x: (-len(x[1]), x[0])):
        rows.append(
            {
                "cluster": hub,
                "tool_pages": len(paths),
                "sample_paths": sorted(paths)[:8],
            }
        )

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(root),
        "cluster_count": len(rows),
        "total_index_pages": sum(r["tool_pages"] for r in rows),
        "clusters": rows,
    }

    latest = data_dir / "topic-cluster-latest.json"
    dated = data_dir / f"topic-cluster-{datetime.now().strftime('%Y-%m-%d')}.json"
    latest.write_text(json.dumps(out, indent=2))
    dated.write_text(json.dumps(out, indent=2))

    print("=" * 72)
    print(f"  TOPIC CLUSTERS — {root}")
    print(f"  Clusters: {len(rows)}  |  index.html pages: {out['total_index_pages']}")
    print(f"  Wrote {latest.name}")
    print("=" * 72)
    print(f"  {'Cluster':<28} {'Pages':>8}")
    print("  " + "-" * 40)
    for r in rows[:40]:
        print(f"  {r['cluster']:<28} {r['tool_pages']:>8}")
    if len(rows) > 40:
        print(f"  ... +{len(rows) - 40} clusters (see JSON)")

    if args.csv:
        w = csv.writer(sys.stdout)
        w.writerow(["cluster", "tool_pages"])
        for r in rows:
            w.writerow([r["cluster"], r["tool_pages"]])

    return 0


if __name__ == "__main__":
    sys.exit(main())
