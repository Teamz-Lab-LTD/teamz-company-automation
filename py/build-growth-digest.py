#!/usr/bin/env python3
"""
Growth Digest — one page that answers "is any of this working?" across every property.

WHY THIS EXISTS
---------------
The owner drives Uber. He is not going to read four nightly logs. He needs ONE artefact that
says, in plain numbers, whether the engine is earning its keep — and, just as importantly,
whether a nightly has quietly stopped running.

THE RULE THIS OBEYS (learned the hard way, twice, in one day)
-------------------------------------------------------------
"All clear" and "could not check" must NEVER look the same.

Both of the big misses on 2026-07-12 were monitors that returned an empty result on failure
and got read as good news:
  * config.sh sent 'sc-domain:goalkit.teamzlab.com/' (invalid) -> HTTP 400 -> the script
    swallowed it into an empty list and printed "0 clicks". goalkit really had 938, at the
    best CTR of any property. It looked dead for months.
  * the GA4 read-only token returns an EMPTY custom-dimension list instead of a 403, so the
    estate looked like it was discarding every event parameter. It was not.

So here: a property that cannot be read is rendered as UNREACHABLE, loudly, and never as a
zero. A stale nightly (no log activity) is a FINDING, not a blank row.

Usage:
  python3 py/build-growth-digest.py              # writes docs/growth-digest.md + prints it
  python3 py/build-growth-digest.py --days 28
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

CFG = Path.home() / ".config" / "teamzlab"
PROJECTS = Path(__file__).resolve().parent.parent.parent

# repo -> (GSC property, launchd label, nightly log name)
SITES = [
    ("teamzlab-tools",                  "https://tool.teamzlab.com/",     "com.teamzlab.nightly-build"),
    ("teamz-lab-generic-landing-pages", "https://apps.teamzlab.com/",     "com.teamzlab.landing-nightly"),
    ("goalkit-bd",                      "sc-domain:goalkit.teamzlab.com",  "com.teamzlab.goalkit-nightly"),
    ("teamz-lab-learning",              "https://learn.teamzlab.com/",    "com.teamzlab.learn-nightly"),
    ("teamzlab-website",                "https://teamzlab.com/",          "com.teamzlab.brand-nightly"),
]


def token():
    t = json.loads((CFG / "search-console-token.json").read_text())
    data = urllib.parse.urlencode({
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30))["access_token"]


def totals(prop, tok, start, end):
    """Returns (clicks, impressions, ctr, position) or raises. NEVER returns zeros on error."""
    body = json.dumps({"startDate": start.isoformat(), "endDate": end.isoformat()}).encode()
    url = (f"https://www.googleapis.com/webmasters/v3/sites/"
           f"{urllib.parse.quote(prop, safe='')}/searchAnalytics/query")
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    rows = json.load(urllib.request.urlopen(req, timeout=60)).get("rows", [])
    if not rows:
        return (0, 0, 0.0, 0.0)
    r = rows[0]
    return (int(r["clicks"]), int(r["impressions"]), r["ctr"] * 100, r["position"])


def arrow(now, prev):
    if prev == 0:
        return "new" if now else "—"
    d = (now - prev) / prev * 100
    if abs(d) < 5:
        return "flat"
    return f"{'+' if d > 0 else ''}{d:.0f}%"


def nightly_health(repo, label):
    """Is the nightly actually still running? A silent cron is the failure nobody notices.

    Three states, and they must stay distinguishable — a monitor that cries wolf gets ignored
    as fast as one that stays silent:
      NOT INSTALLED       -> there is no launchd job at all. Real problem.
      awaiting first run  -> job exists, just has not fired yet (e.g. installed this afternoon,
                             fires at 22:30). NOT a failure. Saying "NEVER RAN" here is a lie.
      STALE               -> job exists, has run before, and has gone quiet. Real problem.
    """
    plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    installed = plist.exists()
    logs = PROJECTS / repo / "logs"
    cands = list(logs.glob(f"{label}.log")) if logs.is_dir() else []

    if not cands:
        if not installed:
            return "❌ NOT INSTALLED"
        age_h = (datetime.now().timestamp() - plist.stat().st_mtime) / 3600
        return f"awaiting 1st run ({age_h:.0f}h since install)"

    newest = max(cands, key=lambda p: p.stat().st_mtime)
    age_h = (datetime.now().timestamp() - newest.stat().st_mtime) / 3600
    if not installed:
        return "❌ JOB GONE (log exists, no plist)"
    if age_h > 48:
        return f"⚠️ STALE — {age_h/24:.0f}d since last run"
    return f"ok ({age_h:.0f}h ago)"


def content_activity(repo, days):
    """What did the agent actually DO? Read its own commits, not its promises."""
    try:
        out = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--oneline", "--no-merges"],
            cwd=str(PROJECTS / repo), capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return []
    return [l for l in out.splitlines() if l.split(" ", 1)[-1].startswith(("content(", "chore(nightly)"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    args = ap.parse_args()

    end = date.today() - timedelta(days=3)          # GSC lags
    start = end - timedelta(days=args.days)
    pstart, pend = start - timedelta(days=args.days), start - timedelta(days=1)
    tok = token()

    L = []
    L.append(f"# Growth Digest — {date.today().isoformat()}")
    L.append("")
    L.append(f"Window: **{start} → {end}** ({args.days}d) vs the {args.days}d before it.")
    L.append("")
    L.append("| property | clicks | vs prev | impressions | CTR | avg pos | nightly |")
    L.append("|---|---|---|---|---|---|---|")

    unreachable = []
    for repo, prop, label in SITES:
        health = nightly_health(repo, label)
        try:
            c, i, ctr, pos = totals(prop, tok, start, end)
            pc, _, _, _ = totals(prop, tok, pstart, pend)
            L.append(f"| {prop} | **{c:,}** | {arrow(c, pc)} | {i:,} | {ctr:.2f}% | {pos:.1f} | {health} |")
        except urllib.error.HTTPError as e:
            # NEVER a zero row. A property we cannot read is a FINDING.
            unreachable.append((prop, e.code))
            L.append(f"| {prop} | ⚠️ **UNREACHABLE** | — | HTTP {e.code} | — | — | {health} |")

    if unreachable:
        L.append("")
        L.append("## ⚠️ COULD NOT CHECK — these are UNKNOWN, not zero")
        for prop, code in unreachable:
            L.append(f"- `{prop}` → HTTP {code}. URL-prefix properties end in `/`; "
                     f"domain properties (`sc-domain:`) must NOT. This exact mistake made "
                     f"goalkit read as 0 clicks for months while it really had 938.")

    L.append("")
    L.append("## What the engine actually did")
    for repo, prop, _ in SITES:
        acts = content_activity(repo, args.days)
        if acts:
            L.append(f"\n**{prop}** — {len(acts)} change(s)")
            for a in acts[:8]:
                L.append(f"- {a}")
    L.append("")
    L.append("_A quiet property is not necessarily a broken one: the queue skips a night when "
             "no page is close enough and no demand is unserved. Inventing work would be worse._")

    text = "\n".join(L)
    out = PROJECTS / "teamz-company-automation" / "docs" / "growth-digest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(text)
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
