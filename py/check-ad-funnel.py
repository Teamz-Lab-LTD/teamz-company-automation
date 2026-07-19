#!/usr/bin/env python3
"""Ad-funnel watchdog: scream when AdMob FILLS ads the app never SHOWS.

The condition `matched_requests > 0 AND impressions == 0` is never legitimate.
It means the network handed the app a paid ad and the app threw it away — always
a code bug, never a market condition.

This has now bitten twice:
  - DeviceGPT : AdMob filled 18,600 ads, the app showed 374.
  - chopstick : app_open filled 2,017/mo, showed 0, for two months (2026-05-16
                -> 2026-07-13). A wrapper armed `skipNextAppOpenAd` immediately
                before calling `showAppOpen()`, so the ad suppressed itself.
                419 requested, 419 skipped. Cost ~$2.55 -- but only because the
                app is small; the same bug on a real audience is real money.

Both times the *totals* looked merely "low" and got blamed on traffic. Only the
funnel exposed it. So: never read the total. Read requests -> matched -> shown.

Exit 1 on any DEAD or STARVED format so cron/launchd surfaces it.

Usage:
    python3 check-ad-funnel.py                 # all apps, last 7 days
    python3 check-ad-funnel.py --days 30
    python3 check-ad-funnel.py --app ca-app-pub-7088022825081956~1409670657
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ADMOB = Path(__file__).with_name("admob.py")

# A format that filled at least this many ads but showed none is DEAD.
DEAD_MIN_MATCHED = 20
# Showing under this fraction of what was filled is STARVED (waste, not a
# hard bug -- user-initiated formats like `rewarded` legitimately sit here).
STARVED_SHOW_RATE = 0.10
# Formats the user must opt into. A low show-rate is expected; only a hard zero
# is reportable.
USER_INITIATED = {"rewarded", "rewarded_interstitial"}


def run(args: list[str]) -> tuple[str, bool]:
    """Returns (stdout, ok). A timeout or non-zero exit is NOT 'no findings' --
    the caller must surface it, or an unreachable app looks identical to a
    healthy one. A monitor that cannot check must never print 'all clear'."""
    try:
        out = subprocess.run(
            [sys.executable, str(ADMOB), *args],
            capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        return "", False
    if out.returncode != 0:
        print(f"  ! admob.py failed: {out.stderr.strip()[:160]}", file=sys.stderr)
        return "", False
    return out.stdout, True


def apps() -> list[tuple[str, str]]:
    rows = []
    out, _ = run(["apps"])
    for line in out.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split("\t")
        if len(f) >= 4:
            rows.append((f[0], f[3]))  # (ad_app_id, package/bundle)
    return rows


def funnel(app_id: str, days: int) -> tuple[dict[str, dict[str, int]], bool]:
    out, ok = run([
        "report", "--app", app_id, "--days", str(days),
        "--dimensions", "FORMAT",
        "--metrics", "AD_REQUESTS,MATCHED_REQUESTS,IMPRESSIONS,ESTIMATED_EARNINGS",
    ])
    got: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for line in out.splitlines():
        f = line.split("\t")
        if len(f) < 5 or f[0] in ("FORMAT", "") or not f[1].isdigit():
            continue
        fmt = f[0]
        got[fmt]["requests"] += int(f[1])
        got[fmt]["matched"] += int(f[2])
        got[fmt]["impressions"] += int(f[3])
        got[fmt]["micros"] += int(f[4])
    return got, ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--app", help="single AdMob app id; default = every app")
    args = ap.parse_args()

    targets = [(args.app, args.app)] if args.app else apps()
    if not targets:
        # A monitor that cannot check must never look like a monitor that found
        # nothing. Unreachable is CRITICAL, not "all clear".
        print("CRITICAL: could not enumerate AdMob apps — funnel UNCHECKED.")
        return 1

    dead, starved, unchecked = [], [], []
    for app_id, name in targets:
        got, ok = funnel(app_id, args.days)
        if not ok:
            unchecked.append(name)
            continue
        for fmt, m in got.items():
            matched, impr = m["matched"], m["impressions"]
            if matched < DEAD_MIN_MATCHED:
                continue  # too little volume to judge
            if impr == 0:
                dead.append((name, fmt, matched))
            elif fmt not in USER_INITIATED and impr / matched < STARVED_SHOW_RATE:
                starved.append((name, fmt, matched, impr, impr / matched))

    print(f"=== ad funnel, last {args.days}d, {len(targets)} app(s) ===")
    if dead:
        print("\n🚨 DEAD — network filled these, app showed ZERO. Always a code bug:")
        for name, fmt, matched in dead:
            print(f"   {name:<45} {fmt:<22} {matched:>6} filled → 0 shown")
    if starved:
        print(f"\n⚠️  STARVED — showing <{STARVED_SHOW_RATE:.0%} of what was filled:")
        for name, fmt, matched, impr, rate in starved:
            print(f"   {name:<45} {fmt:<22} {matched:>6} filled → "
                  f"{impr:>5} shown ({rate:.1%})")
    if unchecked:
        print(f"\n❓ UNCHECKED — {len(unchecked)} app(s) failed to report. NOT 'clean':")
        for name in unchecked:
            print(f"   {name}")
    if not dead and not starved and not unchecked:
        print("\n✅ every format with volume is reaching users.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
