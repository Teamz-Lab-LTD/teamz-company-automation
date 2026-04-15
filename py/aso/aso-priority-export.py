#!/usr/bin/env python3
"""
ASO Priority Export — derives tools_priority.json from existing ASO data.

Reads (in order of preference):
- {data}/deep-research-keywords.json  _recommended_clusters (primary/secondary/tertiary)
- {data}/aso-seo-master.csv            top-N keywords by combined_score
- {data}/ios_keywords.csv              iOS keyword list (optional enrichment)

Writes: {data}/tools_priority.json

The file is consumed by the host app at launch to boost tools whose title/tags/
hub/slug match the current ASO positioning — so the store listing language
and the in-app list ordering stay in lock-step. When the user pivots ASO
(edits deep-research-keywords.json clusters or regenerates aso-seo-master.csv),
running this script (or the full orchestrator) re-exports the priority JSON.

Schema (v1)::

    {
      "version": 1,
      "generated_at": "ISO-8601",
      "generated_by": "aso-priority-export.py",
      "source": { "app_name": "...", "positioning": "..." },
      "keywords": [ { "term": "paycheck calculator", "weight": 100 }, ... ],
      "hub_boosts": { "freelance": 60, "money": 50, ... }
    }

Usage::

    python3 py/aso/aso-priority-export.py
    python3 py/aso/aso-priority-export.py --top-master 40
    python3 py/aso/aso-priority-export.py --print
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import re
import sys
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

# Weight scheme — intentionally coarse, in 10-point buckets.
W_PRIMARY = 100
W_SECONDARY = 80
W_TERTIARY = 60
W_INTERNATIONAL = 40
W_MASTER_MAX = 60
W_MASTER_MIN = 20

# Hub boost table — maps cluster names to canonical hub slugs in the app.
# Kept broad so multiple hub-naming conventions all get the same lift.
_CLUSTER_HUB_HINTS: dict[str, list[str]] = {
    "Freelance & Paycheck": ["freelance", "career", "job", "work"],
    "Money & Mortgage": ["money", "finance", "mortgage", "loan", "tax"],
    "Universal Calculators": ["math", "calculator", "convert", "units"],
}


def _read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _normalize(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


def _collect_cluster_keywords(clusters: dict) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    tiers = (
        ("primary", W_PRIMARY),
        ("secondary", W_SECONDARY),
        ("tertiary", W_TERTIARY),
        ("international_localization", W_INTERNATIONAL),
    )
    for key, weight in tiers:
        cluster = clusters.get(key) or {}
        for kw in cluster.get("keywords", []) or []:
            term = _normalize(str(kw))
            if term:
                out.append((term, weight))
    return out


def _collect_hub_boosts(clusters: dict) -> dict[str, int]:
    boosts: dict[str, int] = {}
    weights = {"primary": 60, "secondary": 50, "tertiary": 40}
    for key, weight in weights.items():
        cluster = clusters.get(key) or {}
        name = cluster.get("name")
        if not name:
            continue
        for hub in _CLUSTER_HUB_HINTS.get(name, []):
            # Keep the highest weight per hub if it appears in multiple tiers.
            boosts[hub] = max(boosts.get(hub, 0), weight)
    return boosts


def _collect_master_keywords(csv_path: Path, top_n: int) -> list[tuple[str, int]]:
    if not csv_path.exists():
        return []
    rows: list[tuple[str, float]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term = _normalize(row.get("keyword", ""))
            if not term:
                continue
            try:
                score = float(row.get("combined_score", "0") or 0)
            except ValueError:
                score = 0.0
            rows.append((term, score))
    if not rows:
        return []
    rows.sort(key=lambda r: r[1], reverse=True)
    rows = rows[:top_n]
    max_score = max((r[1] for r in rows), default=0.0)
    if max_score <= 0:
        return []
    out: list[tuple[str, int]] = []
    for term, score in rows:
        # Map [0..max_score] → [W_MASTER_MIN..W_MASTER_MAX]
        norm = score / max_score
        weight = int(W_MASTER_MIN + norm * (W_MASTER_MAX - W_MASTER_MIN))
        out.append((term, weight))
    return out


def _merge(*sources: list[tuple[str, int]]) -> list[dict]:
    # Keep highest weight per term; preserve first-seen order when weights tie.
    seen: dict[str, int] = {}
    order: list[str] = []
    for source in sources:
        for term, weight in source:
            if term not in seen:
                order.append(term)
            if weight > seen.get(term, 0):
                seen[term] = weight
    return [{"term": t, "weight": seen[t]} for t in order]


def export(top_master: int = 30) -> dict:
    dr_path = _DATA_DIR / "deep-research-keywords.json"
    master_path = _DATA_DIR / "aso-seo-master.csv"

    dr = _read_json(dr_path) or {}
    clusters = dr.get("_recommended_clusters") or {}

    cluster_kws = _collect_cluster_keywords(clusters)
    master_kws = _collect_master_keywords(master_path, top_master)
    hub_boosts = _collect_hub_boosts(clusters)

    # Cluster keywords first (higher priority by design) so they win ties.
    merged = _merge(cluster_kws, master_kws)

    # Sort final list by weight desc so consumers can truncate cheaply.
    merged.sort(key=lambda d: (-d["weight"], d["term"]))

    app_name = (
        os.environ.get("TEAMZ_APP_NAME")
        or _CFG.get("app_name")
        or dr.get("_app_facts", {}).get("name")
        or ""
    )
    positioning = (clusters.get("primary") or {}).get("name", "")

    out = {
        "version": 1,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_by": "aso-priority-export.py",
        "source": {
            "app_name": app_name,
            "positioning": positioning,
            "cluster_kw_count": len(cluster_kws),
            "master_kw_count": len(master_kws),
        },
        "keywords": merged,
        "hub_boosts": hub_boosts,
    }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--top-master",
        type=int,
        default=30,
        help="Top-N keywords from aso-seo-master.csv (default 30)",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print the generated JSON to stdout (still writes the file)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="Override output path (default: {data}/tools_priority.json)",
    )
    args = parser.parse_args()

    result = export(top_master=args.top_master)

    out_path = Path(args.out) if args.out else (_DATA_DIR / "tools_priority.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    out_path.write_text(payload, encoding="utf-8")
    print(f"✅ Wrote {out_path}")

    # Also mirror into the host app's Flutter asset folder when present, so the
    # bundled fallback stays fresh on every release build without manual copies.
    # TEAMZ_DATA_DIR is conventionally <project>/automation_data, so its parent
    # is the Flutter project root — more reliable than _CFG host_site_root,
    # which may point at a kit submodule when scripts are invoked from inside.
    for candidate in (_DATA_DIR.parent, Path(_CFG.get("host_site_root", "."))):
        assets_path = candidate / "assets" / "data" / "tools_priority.json"
        if assets_path.parent.exists():
            assets_path.write_text(payload, encoding="utf-8")
            print(f"✅ Mirrored → {assets_path}")
            break
    print(
        f"   {len(result['keywords'])} keywords, "
        f"{len(result['hub_boosts'])} hub boosts, "
        f"positioning={result['source']['positioning'] or '—'}"
    )

    if not result["keywords"]:
        print(
            "⚠️  No keywords exported — check that deep-research-keywords.json has "
            "_recommended_clusters or that aso-seo-master.csv exists.",
            file=sys.stderr,
        )
        return 2

    if args.print:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
