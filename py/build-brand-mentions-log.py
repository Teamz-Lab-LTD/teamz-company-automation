#!/usr/bin/env python3
"""
Brand / entity mention log — manual tracking of Reddit, Dev.to, Medium, forums (no API keys).

Append rows when you spot a mention; use for follow-up and unlinked mention outreach.

Usage:
    python3 scripts/build-brand-mentions-log.py --source reddit --url "https://..." \\
        --title "thread title" --linked false --notes "suggested reply"

    python3 scripts/build-brand-mentions-log.py --report

Data: TEAMZ_DATA_DIR/brand-mentions-log.csv
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from _teamz_config import load_runtime

_COLUMNS = ["date", "source", "url", "title", "linked", "notes"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Log brand mentions (manual)")
    ap.add_argument("--source", default="", help="reddit | devto | medium | forum | other")
    ap.add_argument("--url", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--linked", default="", help="true if link to your site exists")
    ap.add_argument("--notes", default="")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    cfg = load_runtime(__file__)
    data_dir: Path = cfg["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "brand-mentions-log.csv"

    if args.report:
        if not log_path.exists():
            print("No rows yet.")
            return 0
        with log_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        print("=" * 72)
        print("  BRAND MENTIONS (newest first)")
        print("=" * 72)
        for r in reversed(rows[-50:]):
            print(f"\n  {r.get('date')} | {r.get('source')} | linked={r.get('linked')}")
            print(f"  {r.get('title', '')[:120]}")
            print(f"  {r.get('url', '')}")
            if r.get("notes"):
                print(f"  Notes: {r.get('notes')[:200]}")
        return 0

    if not args.url.strip():
        print("ERROR: --url required (or use --report)", file=sys.stderr)
        return 1

    def norm_bool(s: str) -> str:
        s = (s or "").strip().lower()
        if s in ("1", "true", "yes", "y"):
            return "true"
        if s in ("0", "false", "no", "n"):
            return "false"
        return ""

    row = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": (args.source or "other").strip(),
        "url": args.url.strip(),
        "title": (args.title or "").replace("\n", " ")[:500],
        "linked": norm_bool(args.linked) or "",
        "notes": (args.notes or "").replace("\n", " ").strip(),
    }

    new_file = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_COLUMNS)
        if new_file:
            w.writeheader()
        w.writerow(row)

    print(f"Appended row to {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
