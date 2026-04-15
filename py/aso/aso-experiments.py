#!/usr/bin/env python3
"""
ASO A/B Experiment Tracker — log App Store Product Page Optimization tests
and Play Store store-listing experiments, track variants and conversion deltas.

Stores state in {data}/aso-experiments.json. Stdlib only.

Usage::

    # Register a new experiment
    python3 py/aso/aso-experiments.py add \\
        --id icon-v2-test --type icon --platform ios \\
        --variants control,gradient,flat \\
        --start 2026-04-15 --notes "Test 3 icon styles for primary keyword intent"

    # Snapshot current impressions/conversions (run weekly via cron)
    python3 py/aso/aso-experiments.py snapshot --id icon-v2-test \\
        --variant gradient --impressions 12400 --installs 880

    # List all experiments + status
    python3 py/aso/aso-experiments.py list

    # End an experiment with winner
    python3 py/aso/aso-experiments.py end --id icon-v2-test --winner gradient

    # Generate report (markdown)
    python3 py/aso/aso-experiments.py report

Chains into aso-store-release.py post-release phase.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
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
_FILE = _DATA_DIR / "aso-experiments.json"

VALID_TYPES = {"icon", "screenshots", "subtitle", "title", "description", "preview_video", "promo_text"}
VALID_PLATFORMS = {"ios", "android", "both"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if _FILE.exists():
        try:
            return json.loads(_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"experiments": []}


def _save(data: dict):
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _find(data: dict, exp_id: str) -> dict | None:
    for e in data["experiments"]:
        if e["id"] == exp_id:
            return e
    return None


def cmd_add(args):
    data = _load()
    if _find(data, args.id):
        print(f"[ERROR] Experiment '{args.id}' already exists.", file=sys.stderr)
        return 1
    if args.type not in VALID_TYPES:
        print(f"[ERROR] --type must be one of: {sorted(VALID_TYPES)}", file=sys.stderr)
        return 1
    if args.platform not in VALID_PLATFORMS:
        print(f"[ERROR] --platform must be one of: {sorted(VALID_PLATFORMS)}", file=sys.stderr)
        return 1
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    if len(variants) < 2:
        print("[ERROR] Need at least 2 variants (e.g. control,treatment)", file=sys.stderr)
        return 1
    exp = {
        "id": args.id,
        "type": args.type,
        "platform": args.platform,
        "variants": variants,
        "start_date": args.start or _now()[:10],
        "end_date": None,
        "status": "running",
        "notes": args.notes or "",
        "snapshots": [],
        "winner": None,
        "created_at": _now(),
    }
    data["experiments"].append(exp)
    _save(data)
    print(f"  [ok] Registered experiment '{args.id}' "
          f"({args.type}/{args.platform}, {len(variants)} variants)", file=sys.stderr)
    return 0


def cmd_snapshot(args):
    data = _load()
    exp = _find(data, args.id)
    if not exp:
        print(f"[ERROR] Experiment '{args.id}' not found.", file=sys.stderr)
        return 1
    if args.variant not in exp["variants"]:
        print(f"[ERROR] Variant '{args.variant}' not in {exp['variants']}", file=sys.stderr)
        return 1
    cr = (args.installs / args.impressions * 100) if args.impressions else 0.0
    snap = {
        "timestamp": _now(),
        "variant": args.variant,
        "impressions": args.impressions,
        "installs": args.installs,
        "cvr_pct": round(cr, 3),
    }
    exp["snapshots"].append(snap)
    _save(data)
    print(f"  [ok] Snapshot: {args.variant} — {args.impressions} imp, "
          f"{args.installs} inst, CVR {cr:.2f}%", file=sys.stderr)
    return 0


def cmd_end(args):
    data = _load()
    exp = _find(data, args.id)
    if not exp:
        print(f"[ERROR] Experiment '{args.id}' not found.", file=sys.stderr)
        return 1
    if args.winner and args.winner not in exp["variants"]:
        print(f"[ERROR] Winner '{args.winner}' not in {exp['variants']}", file=sys.stderr)
        return 1
    exp["status"] = "completed"
    exp["end_date"] = _now()[:10]
    exp["winner"] = args.winner
    _save(data)
    print(f"  [ok] Ended '{args.id}' — winner: {args.winner or 'inconclusive'}",
          file=sys.stderr)
    return 0


def cmd_list(args):
    data = _load()
    if not data["experiments"]:
        print("No experiments yet. Add one with: aso-experiments.py add ...")
        return 0
    print(f"{'id':<24} {'type':<14} {'plat':<7} {'status':<10} {'start':<11} {'winner':<12} snaps")
    for e in data["experiments"]:
        print(f"{e['id'][:24]:<24} {e['type']:<14} {e['platform']:<7} "
              f"{e['status']:<10} {e['start_date']:<11} "
              f"{(e.get('winner') or '-'):<12} {len(e.get('snapshots', []))}")
    return 0


def _best_variant(exp: dict) -> tuple[str, float] | None:
    agg: dict[str, tuple[int, int]] = {}
    for s in exp.get("snapshots", []):
        v = s["variant"]
        imp, ins = agg.get(v, (0, 0))
        agg[v] = (imp + s["impressions"], ins + s["installs"])
    best = None
    for v, (imp, ins) in agg.items():
        if imp == 0:
            continue
        cvr = ins / imp * 100
        if not best or cvr > best[1]:
            best = (v, cvr)
    return best


def cmd_report(args):
    data = _load()
    if not data["experiments"]:
        print("No experiments yet.")
        return 0
    lines = ["# ASO Experiment Report", f"_Generated {_now()}_\n"]
    for e in data["experiments"]:
        lines.append(f"## {e['id']}  ({e['type']}/{e['platform']}, {e['status']})")
        lines.append(f"- **Period**: {e['start_date']} → {e.get('end_date') or 'ongoing'}")
        lines.append(f"- **Variants**: {', '.join(e['variants'])}")
        if e.get("notes"):
            lines.append(f"- **Notes**: {e['notes']}")
        best = _best_variant(e)
        if best:
            lines.append(f"- **Leader (by CVR)**: `{best[0]}` at {best[1]:.2f}%")
        if e.get("winner"):
            lines.append(f"- **Declared winner**: `{e['winner']}`")
        lines.append("")
    out = _DATA_DIR / "aso-experiments-report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [ok] Wrote {out}", file=sys.stderr)
    print("\n".join(lines))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add")
    a.add_argument("--id", required=True)
    a.add_argument("--type", required=True)
    a.add_argument("--platform", required=True)
    a.add_argument("--variants", required=True, help="Comma-separated: control,treatment[,...]")
    a.add_argument("--start", default=None, help="YYYY-MM-DD (default: today)")
    a.add_argument("--notes", default="")
    a.set_defaults(fn=cmd_add)

    s = sub.add_parser("snapshot")
    s.add_argument("--id", required=True)
    s.add_argument("--variant", required=True)
    s.add_argument("--impressions", type=int, required=True)
    s.add_argument("--installs", type=int, required=True)
    s.set_defaults(fn=cmd_snapshot)

    e = sub.add_parser("end")
    e.add_argument("--id", required=True)
    e.add_argument("--winner", default=None)
    e.set_defaults(fn=cmd_end)

    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("report").set_defaults(fn=cmd_report)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
