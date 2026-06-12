#!/usr/bin/env python3
"""
ASO Keyword-Data Gate — FORCES the authoritative Keyword Planner pull.
=====================================================================
The free volume estimator (build-keyword-volume.py) prints
"Keyword Planner: PENDING (using free estimates)" when it has no exact
Google volumes. An LLM can SEE that line and still ship a listing on
estimates (this happened on voltline 2026-06-12). This gate turns that
soft warning into a HARD non-zero exit so the listing can never be
called "final/locked" on estimate-only data.

WHAT IT CHECKS (per app dir):
  1. A keyword_volume_*.txt exists at all (research was actually run).
  2. EITHER exact Planner data is present:
        <app>/automation_data/manual-pull/2-DROP-RESULTS-HERE/*.csv
     OR the volume file already says Planner "ACTIVE".
  3. OR the owner explicitly waived it:
        <app>/automation_data/.planner-waived   (one-line reason inside)

EXIT CODES:
  0  PASS  — exact volumes present, or explicit waiver on file.
  1  FAIL  — estimate-only and no waiver. Caller MUST stop and either
             run the manual pull (manual-pull/README.txt) or waive.
  2  ERROR — no research run yet / bad args.

USAGE:
  python3 aso-keyword-data-gate.py --app-dir /path/to/apps/<slug>
  python3 aso-keyword-data-gate.py --app-dir . --waive "niche too small for Planner volume"

This is generic — works for ANY app via --app-dir. Called by the
/aso-refresh skill as a refusal condition before any locked listing.
"""
import argparse
import glob
import os
import sys


def find_volume_file(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "keyword_volume_*.txt")))
    return files[-1] if files else None


def planner_active_in_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4000)
    except OSError:
        return False
    return "Keyword Planner: ACTIVE" in head


def main():
    ap = argparse.ArgumentParser(description="ASO Keyword-Data Gate")
    ap.add_argument("--app-dir", required=True, help="app dir (contains automation_data/)")
    ap.add_argument("--waive", help="record an explicit waiver with this reason, then PASS")
    args = ap.parse_args()

    app_dir = os.path.abspath(args.app_dir)
    data_dir = os.path.join(app_dir, "automation_data")
    waiver = os.path.join(data_dir, ".planner-waived")
    drop_dir = os.path.join(data_dir, "manual-pull", "2-DROP-RESULTS-HERE")

    if not os.path.isdir(data_dir):
        print(f"GATE ERROR: no automation_data/ in {app_dir}", file=sys.stderr)
        return 2

    # Recording a waiver is an explicit owner action.
    if args.waive:
        os.makedirs(data_dir, exist_ok=True)
        with open(waiver, "w", encoding="utf-8") as f:
            f.write(args.waive.strip() + "\n")
        print(f"GATE: waiver recorded -> {waiver}")
        print(f"      reason: {args.waive.strip()}")
        print("GATE PASS (waived).")
        return 0

    vol_file = find_volume_file(data_dir)
    if not vol_file:
        print("GATE FAIL: no keyword_volume_*.txt — keyword research was never run.", file=sys.stderr)
        print("  Fix: /aso-refresh <slug> (runs build-keyword-volume.py).", file=sys.stderr)
        return 1

    # PASS conditions
    if planner_active_in_file(vol_file):
        print(f"GATE PASS: exact Planner volumes ACTIVE in {os.path.basename(vol_file)}.")
        return 0

    dropped = glob.glob(os.path.join(drop_dir, "*.csv"))
    if dropped:
        print(f"GATE PASS: Planner export present ({len(dropped)} CSV in 2-DROP-RESULTS-HERE/).")
        print("  Next: run keyword_volume_manual.py to fold exact volumes in, then re-score.")
        return 0

    if os.path.isfile(waiver):
        with open(waiver, "r", encoding="utf-8") as f:
            reason = f.read().strip()
        print(f"GATE PASS: Planner pull waived. reason: {reason}")
        return 0

    # FAIL — estimate-only, no waiver.
    print("GATE FAIL: listing is on FREE ESTIMATES only — exact Google volume missing.", file=sys.stderr)
    print(f"  volume file: {os.path.basename(vol_file)}  (Keyword Planner: PENDING)", file=sys.stderr)
    print("  Do ONE of:", file=sys.stderr)
    print("   1) Manual pull — see automation_data/manual-pull/README.txt, then drop the", file=sys.stderr)
    print("      Planner CSV into manual-pull/2-DROP-RESULTS-HERE/ and re-run this gate.", file=sys.stderr)
    print("   2) Waive — python3 aso-keyword-data-gate.py --app-dir <dir> --waive \"<reason>\"", file=sys.stderr)
    print("  Until then the listing is PROVISIONAL — do not call it final/locked.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
