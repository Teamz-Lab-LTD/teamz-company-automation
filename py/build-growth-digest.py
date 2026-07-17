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
import os
import json
import re
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


def log_from_plist(plist):
    """Where does launchd ACTUALLY write this job's log? Ask launchd — never guess.

    This function exists because the digest used to guess: it globbed for "<label>.log". Every
    job the shared runner installs follows that convention, so it looked correct. But tools'
    job predates the shared runner: its label is com.teamzlab.nightly-build while it writes to
    logs/nightly-build.log. The glob matched nothing, so the digest reported the engine behind
    89% OF ALL TRAFFIC as "awaiting 1st run (725h since install)" — for a job that had run every
    single night for months, and had written that very log two hours earlier.

    A monitor that says "never ran" about a healthy job is exactly as broken as one that says
    "all clear" about a dead one. Both make the human stop reading it.

    StandardOutPath in the plist is the single source of truth. Deriving it removes the second
    hardcoded list that has to be kept in sync by hand — the same bug class that made goalkit's
    new collection hub invisible to Google.
    """
    if not plist.exists():
        return None
    m = re.search(r"<key>StandardOutPath</key>\s*<string>([^<]+)</string>", plist.read_text())
    return Path(m.group(1)) if m else None


def nightly_health(repo, label):
    """Did the nightly actually WORK? Not: did a file get touched.

    The states must stay distinguishable — a monitor that cries wolf gets ignored as fast as one
    that stays silent:
      NOT INSTALLED       -> there is no launchd job at all. Real problem.
      awaiting first run  -> job exists, just has not fired yet (e.g. installed this afternoon,
                             fires at 22:30). NOT a failure. Saying "NEVER RAN" here is a lie.
      STALE               -> job exists, has run before, and has gone quiet. Real problem.
      ran, but ...        -> it fired and something inside it failed. THE STATE THIS FUNCTION
                             USED TO BE BLIND TO.

    That blindness cost a whole night. On 2026-07-13 apps and learn each skipped their content
    agent (the network was still waking after the Mac did) AND then failed to deploy — and this
    function called both of them "ok", because "ok" only ever meant "the log file has a recent
    mtime". A log file gets its mtime updated by a script that fails just as reliably as by one
    that succeeds. "Ran" and "worked" are different questions and this only ever asked the first.

    So the runner now writes data/nightly-status.json from an EXIT trap, and we READ it. The
    mtime path below remains only as a fallback for a run that predates the status file.
    """
    plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    installed = plist.exists()

    # What the run itself says it did — the only source that knows.
    status_file = PROJECTS / repo / "data" / "nightly-status.json"
    status = None
    if status_file.exists():
        try:
            status = json.loads(status_file.read_text())
        except Exception:
            status = None

    declared = log_from_plist(plist)
    cands = [declared] if declared and declared.exists() else []
    if not cands:                       # no StandardOutPath declared — fall back to the convention
        logs = PROJECTS / repo / "logs"
        cands = list(logs.glob(f"{label}.log")) if logs.is_dir() else []

    if status:
        age_h = (datetime.now().timestamp() - status_file.stat().st_mtime) / 3600
        if not installed:
            return "❌ JOB GONE (ran before, no plist)"
        if age_h > 48:
            return f"⚠️ STALE — {age_h/24:.0f}d since last run"
        # Report the FIRST thing that went wrong, loudest first. Deploy failing is worse than the
        # agent skipping: a skipped agent loses one night, an undeployed build loses the work.
        if status.get("deploy", "").startswith("failed"):
            return f"⚠️ ran, but DEPLOY FAILED ({age_h:.0f}h ago) — serving the old build"
        if status.get("build", "").startswith("failed"):
            return f"⚠️ ran, but BUILD FAILED ({age_h:.0f}h ago) — nothing deployed"
        content = status.get("content", "")
        if content.startswith("failed"):
            return f"⚠️ ran, agent FAILED: {content.split(':', 1)[-1]} ({age_h:.0f}h ago)"
        if content.startswith("skipped"):
            return f"⚠️ ran, agent SKIPPED: {content.split(':', 1)[-1]} ({age_h:.0f}h ago)"
        return f"ok ({age_h:.0f}h ago)"

    if not cands:
        if not installed:
            return "❌ NOT INSTALLED"
        age_h = (datetime.now().timestamp() - plist.stat().st_mtime) / 3600
        return f"awaiting 1st run ({age_h:.0f}h since install)"

    # FALLBACK — a run that predates the status file (or one that died before its EXIT trap).
    #
    # This path must NEVER be able to return "ok". "ok" is a CLAIM, and without the status file
    # there is no basis for it. That was the whole bug: the old code reached this point, saw a
    # recent mtime, and said "ok" about apps and learn on a night when both of them skipped their
    # content agent AND failed to deploy. Not knowing and being fine must never render the same.
    #
    # Best effort instead: read the failure markers the runner prints. If they are there, report
    # them. If they are not, say plainly that we cannot confirm anything.
    newest = max(cands, key=lambda p: p.stat().st_mtime)
    age_h = (datetime.now().timestamp() - newest.stat().st_mtime) / 3600
    if not installed:
        return "❌ JOB GONE (log exists, no plist)"
    if age_h > 48:
        return f"⚠️ STALE — {age_h/24:.0f}d since last run"

    try:
        text = newest.read_text(errors="replace")
    except Exception:
        text = ""
    # Only the LAST run. The log accumulates, so a DEPLOY FAILED from three nights ago must not
    # be reported as tonight's.
    blocks = text.split("=" * 60)
    tail = blocks[-1] if len(blocks) > 1 else text[-8000:]

    if "DEPLOY FAILED" in tail:
        return f"⚠️ ran, but DEPLOY FAILED ({age_h:.0f}h ago) — serving the old build"
    if "BUILD FAILED" in tail:
        return f"⚠️ ran, but BUILD FAILED ({age_h:.0f}h ago) — nothing deployed"
    if "SKIP: api.anthropic.com" in tail:
        return f"⚠️ ran, agent SKIPPED: api-unreachable ({age_h:.0f}h ago)"
    if "SKIP: uncommitted source" in tail:
        return f"⚠️ SKIPPED: dirty tree — protecting your WIP ({age_h:.0f}h ago)"
    return f"? ran {age_h:.0f}h ago — no status file, cannot confirm it worked"

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



# Keyword-volume freshness. Planner volume is roughly valid ~1 year; ordering stock or gating
# SEO/GEO on year-old numbers is a real risk the owner named explicitly. WARN before it expires,
# and treat "never pulled" as a finding, not silence. Cross-property so one digest triggers all.
KW_STALE_DAYS = int(os.getenv("TEAMZ_KW_STALE_DAYS", "300"))   # warn ~2 months before the year

def kw_volume_freshness(repo):
    """(state, age_days_or_None, n_results). state in fresh/aging/STALE/never/no-store."""
    base = PROJECTS / repo / "data"
    store = base / "keyword-candidates.json"
    drop = base / "manual-pull" / "2-DROP-RESULTS-HERE"
    if not store.exists():
        return ("no-store", None, 0)
    results = list(drop.glob("*.csv")) if drop.exists() else []
    if not results:
        return ("never", None, 0)
    newest = max(r.stat().st_mtime for r in results)
    age = int((datetime.now() - datetime.fromtimestamp(newest)).days)
    if age >= 365:
        return ("EXPIRED", age, len(results))
    if age >= KW_STALE_DAYS:
        return ("STALE", age, len(results))
    if age >= KW_STALE_DAYS - 60:
        return ("aging", age, len(results))
    return ("fresh", age, len(results))


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

    # --- Keyword-volume freshness — the "trigger me before it expires" section ---
    L.append("")
    L.append("## Keyword volume — pull freshness (Planner data ~1yr valid)")
    L.append("| property | volume data | age | action |")
    L.append("|---|---|---|---|")
    triggers = []
    ICON = {"fresh": "✅", "aging": "🟡", "STALE": "🔴", "EXPIRED": "⛔", "never": "⬜", "no-store": "—"}
    for repo, prop, _ in SITES:
        state, age, n = kw_volume_freshness(repo)
        agetxt = "—" if age is None else f"{age}d"
        if state in ("STALE", "EXPIRED"):
            act = f"**RE-PULL NOW** — ordering/SEO on {age}d-old volume is unsafe"
            triggers.append((prop, state, age))
        elif state == "aging":
            act = f"re-pull soon (expires ~{365-age}d)"
        elif state == "never":
            act = "no volume yet — first pull pending"
        elif state == "no-store":
            act = "keyword engine not wired here"
        else:
            act = "ok"
        L.append(f"| {prop} | {ICON[state]} {state} ({n} file(s)) | {agetxt} | {act} |")
    if triggers:
        L.append("")
        L.append("### 🔔 TRIGGER — keyword volume expiring across your business")
        for prop, state, age in triggers:
            L.append(f"- **{prop}** — {state}, {age} days old. Re-pull before you order stock or "
                     f"trust its SEO/GEO gating. This is the cross-project alert you asked for.")

    text = "\n".join(L)
    out = PROJECTS / "teamz-company-automation" / "docs" / "growth-digest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(text)
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
