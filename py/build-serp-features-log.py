#!/usr/bin/env python3
"""
SERP feature log (manual / low-cost) — append structured rows for snippet / PAA / video / local / AI overview.

No paid API: you record what you see in the SERP (or paste from another tool) and keep history in CSV.
Optional: import a batch from JSON for backfill.

Usage:
    python3 scripts/build-serp-features-log.py --keyword "salary calculator" \\
        --snippet true --paa 4 --video false --local false --ai-overview true

    python3 scripts/build-serp-features-log.py --report   # last 20 rows per keyword

Data: TEAMZ_DATA_DIR/serp-features-log.csv (date,keyword,snippet,paa_count,video,local,ai_overview,notes)
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from _teamz_config import load_runtime

_COLUMNS = ["date", "keyword", "snippet", "paa_count", "video", "local", "ai_overview", "notes"]


def _read_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser(description="Append or report SERP feature observations")
    ap.add_argument("--keyword", default="", help="Keyword phrase")
    ap.add_argument("--snippet", default="", help="true/false — classic snippet present")
    ap.add_argument("--paa", type=int, default=-1, help="People Also Ask count (0 if none)")
    ap.add_argument("--video", default="", help="true/false")
    ap.add_argument("--local", default="", help="true/false — local pack")
    ap.add_argument("--ai-overview", dest="ai_overview", default="", help="true/false — AI overview style block")
    ap.add_argument("--notes", default="", help="Free text")
    ap.add_argument("--report", action="store_true", help="Show recent rows grouped by keyword")
    args = ap.parse_args()

    cfg = load_runtime(__file__)
    if cfg["project_type"] == "app":
        print("Skipped: TEAMZ_PROJECT_TYPE=app (website-only tooling).", file=sys.stderr)
        return 2

    data_dir: Path = cfg["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "serp-features-log.csv"

    if args.report:
        rows = _read_rows(log_path)
        if not rows:
            print("No rows yet. Append with --keyword ...")
            return 0
        by_kw: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            by_kw.setdefault(r.get("keyword", ""), []).append(r)
        print("=" * 72)
        print("  SERP FEATURE LOG (latest 5 per keyword)")
        print("=" * 72)
        for kw in sorted(by_kw.keys()):
            chunk = sorted(by_kw[kw], key=lambda x: x.get("date", ""))[-5:]
            print(f"\n  {kw}")
            for r in chunk:
                print(
                    f"    {r.get('date')} | snippet={r.get('snippet')} paa={r.get('paa_count')} "
                    f"video={r.get('video')} local={r.get('local')} ai={r.get('ai_overview')}"
                )
        return 0

    if not args.keyword.strip():
        print("ERROR: --keyword is required (or use --report)", file=sys.stderr)
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
        "keyword": args.keyword.strip(),
        "snippet": norm_bool(args.snippet) or "",
        "paa_count": str(args.paa) if args.paa >= 0 else "",
        "video": norm_bool(args.video) or "",
        "local": norm_bool(args.local) or "",
        "ai_overview": norm_bool(args.ai_overview) or "",
        "notes": args.notes.replace("\n", " ").strip(),
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
