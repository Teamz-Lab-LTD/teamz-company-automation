#!/usr/bin/env python3
"""
ASO↔SEO Master Keyword Merge — single source of truth per CLAUDE.md global rule.

Merges 3 data sources into one scored master CSV:
  1. ASO score  — from {data}/master_keywords.csv or ios_keywords.csv
  2. SEO volume — from {data}/keyword-volume-latest.json (build-keyword-volume.py)
  3. Web rank   — from {data}/rank-history.json (build-rank-tracker.py)

Plus optional Deep Research column from {data}/deep-research-keywords.json
(user-pasted ChatGPT Deep Research output).

Output: {data}/aso-seo-master.csv with columns:
  keyword,aso_score,web_volume,web_rank,dr_competition,source_count,combined_score

combined_score = weighted sum (ASO 0.5 + Volume 0.3 + inverse rank 0.15 + DR 0.05),
normalized 0–100. Keywords present in more sources rank higher via source_count bonus.

Usage:
    python3 py/aso/aso-seo-merge.py
    python3 py/aso/aso-seo-merge.py --top 50    # print top 50 to stdout
"""

from __future__ import annotations

import argparse
import csv
import json
import os
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


def _load_aso() -> dict[str, float]:
    out: dict[str, float] = {}
    for name in ("master_keywords.csv", "ios_keywords.csv"):
        p = _DATA_DIR / name
        if not p.exists():
            continue
        for row in csv.DictReader(p.open(encoding="utf-8")):
            k = (row.get("keyword") or "").strip().lower()
            if not k:
                continue
            try:
                score = float(row.get("score") or 0)
            except ValueError:
                score = 0.0
            out[k] = max(out.get(k, 0.0), score)
        break
    return out


def _load_volume() -> dict[str, int]:
    p = _DATA_DIR / "keyword-volume-latest.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, int] = {}
    entries = data.get("keywords") if isinstance(data, dict) else data
    if isinstance(entries, dict):
        for k, v in entries.items():
            vol = v.get("volume") if isinstance(v, dict) else v
            try:
                out[k.strip().lower()] = int(vol or 0)
            except (ValueError, TypeError):
                out[k.strip().lower()] = 0
    elif isinstance(entries, list):
        for row in entries:
            if not isinstance(row, dict):
                continue
            k = (row.get("keyword") or "").strip().lower()
            if k:
                try:
                    out[k] = int(row.get("volume") or 0)
                except (ValueError, TypeError):
                    out[k] = 0
    return out


def _load_ranks() -> dict[str, float]:
    p = _DATA_DIR / "rank-history.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    kws = data.get("keywords", {})
    out: dict[str, float] = {}
    if isinstance(kws, dict):
        for k, v in kws.items():
            if isinstance(v, list) and v:
                last = v[-1]
                pos = last.get("position") if isinstance(last, dict) else last
                try:
                    out[k.strip().lower()] = float(pos or 100)
                except (ValueError, TypeError):
                    out[k.strip().lower()] = 100.0
            elif isinstance(v, (int, float)):
                out[k.strip().lower()] = float(v)
    return out


def _load_deep_research() -> dict[str, float]:
    p = _DATA_DIR / "deep-research-keywords.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, float] = {}
    entries = data.get("keywords", data) if isinstance(data, dict) else data
    if isinstance(entries, list):
        for row in entries:
            if isinstance(row, dict):
                k = (row.get("keyword") or "").strip().lower()
                try:
                    out[k] = float(row.get("competition") or row.get("difficulty") or 50)
                except (ValueError, TypeError):
                    out[k] = 50.0
    elif isinstance(entries, dict):
        for k, v in entries.items():
            try:
                out[k.strip().lower()] = float(v) if not isinstance(v, dict) else float(
                    v.get("competition", 50))
            except (ValueError, TypeError):
                out[k.strip().lower()] = 50.0
    return out


def _normalize(values: dict[str, float], invert: bool = False) -> dict[str, float]:
    if not values:
        return {}
    nums = [v for v in values.values() if isinstance(v, (int, float))]
    if not nums:
        return {k: 0.0 for k in values}
    lo, hi = min(nums), max(nums)
    span = hi - lo or 1
    out = {}
    for k, v in values.items():
        n = (v - lo) / span * 100
        out[k] = 100 - n if invert else n
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=20, help="Print top N to stdout")
    args = ap.parse_args()

    aso = _load_aso()
    vol = _load_volume()
    rnk = _load_ranks()
    dr = _load_deep_research()

    sources = sum([bool(aso), bool(vol), bool(rnk), bool(dr)])
    print(f"  [info] Sources loaded: ASO={len(aso)} Volume={len(vol)} "
          f"Rank={len(rnk)} DeepResearch={len(dr)}", file=sys.stderr)
    if sources == 0:
        print("[ERROR] No data sources found. Run aso-keyword-pipeline.py first.", file=sys.stderr)
        return 1

    all_keys = set(aso) | set(vol) | set(rnk) | set(dr)

    n_aso = _normalize(aso)
    n_vol = _normalize(vol)
    n_rnk = _normalize(rnk, invert=True)  # rank 1 = best → highest score
    n_dr = _normalize(dr, invert=True)    # low competition = higher score

    rows = []
    for k in sorted(all_keys):
        src_count = sum([k in aso, k in vol, k in rnk, k in dr])
        combined = (
            n_aso.get(k, 0) * 0.50
            + n_vol.get(k, 0) * 0.30
            + n_rnk.get(k, 0) * 0.15
            + n_dr.get(k, 0) * 0.05
        )
        combined += (src_count - 1) * 3  # cross-source bonus
        rows.append({
            "keyword": k,
            "aso_score": round(aso.get(k, 0), 2),
            "web_volume": vol.get(k, 0),
            "web_rank": rnk.get(k, ""),
            "dr_competition": dr.get(k, ""),
            "source_count": src_count,
            "combined_score": round(combined, 2),
        })
    rows.sort(key=lambda r: r["combined_score"], reverse=True)

    out = _DATA_DIR / "aso-seo-master.csv"
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader()
        w.writerows(rows)
    print(f"  [ok] Wrote {out} ({len(rows)} keywords)", file=sys.stderr)

    print(f"\nTop {args.top} by combined score:")
    print(f"{'keyword':<32} {'aso':>6} {'vol':>8} {'rank':>6} {'src':>4} {'combined':>10}")
    for r in rows[: args.top]:
        print(f"{r['keyword'][:32]:<32} {r['aso_score']:>6} {r['web_volume']:>8} "
              f"{str(r['web_rank'])[:6]:>6} {r['source_count']:>4} {r['combined_score']:>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
