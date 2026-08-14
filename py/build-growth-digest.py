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
from datetime import date, datetime, timedelta, timezone
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

# repo -> GA4 property ID, read from each repo's own .teamz-automation.env
# (TEAMZ_GA4_PROPERTY_ID). teamzlab-website is a KNOWN GA4 blind spot (prop
# 469101682 gets no traffic — the Framer site is missing the tag); it stays
# in this map so a failed pull renders as UNREACHABLE, not a silent zero.
GA4_PROPERTY = {
    "teamzlab-tools":                  "528521795",
    "teamz-lab-generic-landing-pages": "524940073",
    "goalkit-bd":                      "537333788",
    "teamz-lab-learning":              "527372960",
    "teamzlab-website":                "469101682",
}


def token():
    t = json.loads((CFG / "search-console-token.json").read_text())
    data = urllib.parse.urlencode({
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30))["access_token"]


def ga4_token():
    """Separate failure domain from the GSC token — GA4 can be down while GSC
    is fine, or vice versa. Never let one silently mask the other."""
    t = json.loads((CFG / "analytics-token.json").read_text())
    data = urllib.parse.urlencode({
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(
        urllib.request.Request(t.get("token_uri", "https://oauth2.googleapis.com/token"),
                                data=data), timeout=30))["access_token"]


def _ga4_report(property_id, tok, body):
    req = urllib.request.Request(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def ai_channel_totals(property_id, tok, start, end):
    """Sessions + ad revenue by sessionDefaultChannelGroup. Raises on failure —
    NEVER returns an empty/zero result silently; the caller renders that as
    UNREACHABLE. Query window must be D-2 or older: session-scoped derived
    dimensions (this one included) come back ~58% blank on D-0/D-1 — GSC's
    existing `end = today - 3d` window (passed in here) already satisfies that.

    Also: GA4 created the "AI Assistant" channel group around June 2026 and
    moved chatgpt.com out of "Referral" into it. Never diff `Referral` totals
    across that boundary — it reads as a collapse that never happened.
    """
    res = _ga4_report(property_id, tok, {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": "sessionDefaultChannelGroup"}],
        "metrics": [{"name": "sessions"}, {"name": "totalAdRevenue"}],
        "limit": 25,
    })
    out = []
    for r in res.get("rows", []):
        ch = r["dimensionValues"][0]["value"]
        sess = int(r["metricValues"][0]["value"])
        rev = float(r["metricValues"][1]["value"])
        out.append((ch, sess, rev))
    return out


def ai_weekly_trend(property_id, tok, weeks=6):
    """AI Assistant sessions by ISO week, most recent `weeks` — the durable-base
    signal. A collapse or a surge should be visible the week it starts, not
    require someone to open GA4 by hand and eyeball a chart (which is exactly
    how this whole workstream started)."""
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=7 * weeks + 7)
    res = _ga4_report(property_id, tok, {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": "week"}],
        "metrics": [{"name": "sessions"}, {"name": "totalAdRevenue"}],
        "dimensionFilter": {"filter": {"fieldName": "sessionDefaultChannelGroup",
                                       "stringFilter": {"value": "AI Assistant"}}},
        "limit": 20,
    })
    rows = []
    for r in res.get("rows", []):
        wk = r["dimensionValues"][0]["value"]
        sess = int(r["metricValues"][0]["value"])
        rev = float(r["metricValues"][1]["value"])
        rows.append((wk, sess, rev))
    rows.sort(key=lambda x: x[0])
    return rows[-weeks:]


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
        # This one first: it is a DIFFERENT failure from "the deploy command errored".
        # Here the command exited 0 and reported success, and the live site still does
        # not serve the pages — so the generic "serving the old build" wording would
        # send the owner to look at a deploy log that says everything went fine.
        if status.get("deploy", "") == "failed:built-but-not-live":
            return (f"🔴 ran, deploy REPORTED SUCCESS but pages are NOT live ({age_h:.0f}h ago) "
                    f"— the deploy command lied; check the live-site verify block in the log")
        if status.get("deploy", "").startswith("failed"):
            return f"⚠️ ran, but DEPLOY FAILED ({age_h:.0f}h ago) — serving the old build"
        if status.get("build", "").startswith("failed"):
            return f"⚠️ ran, but BUILD FAILED ({age_h:.0f}h ago) — nothing deployed"
        # `push` is the SAME unread-field bug as `courses` below, caught 2026-08-08. The runner has
        # written it for years, nothing here ever read it, and three of the four properties sat at
        # "push": "failed" for six nights (Aug 2 -> Aug 8) while this column printed a clean "ok".
        # Cause was real: origin was an SSH URL and the machine's only GitHub SSH key authenticates
        # as an account with no access to the private Teamz-Lab-LTD repos, so every fetch AND push
        # 404'd. Deploy is rsync and kept working, so the SITE stayed fine and nothing else went
        # red — exactly why it needs its own line here.
        #
        # Checked BEFORE the deploy-unknown branch below on purpose. The tools runner DERIVES its
        # deploy value from the push result, so one git-auth failure surfaces in both fields; if
        # deploy spoke first it would send the owner to look at rsync for a problem that is in git.
        # A real, independent deploy failure still outranks this — it matches "failed" above.
        if status.get("push", "").startswith("failed"):
            return (f"⚠️ ran, but GIT PUSH FAILED ({age_h:.0f}h ago) — commits are local-only and "
                    f"the remote backup is not receiving them; check `git ls-remote origin`")
        # "unknown" is what the tools runner writes when it never reached a conclusion about the
        # deploy. It is NOT a pass, and matching only on "failed" let it read as one — tools has
        # been carrying deploy="unknown" while this column printed "ok". Anything that is not an
        # explicit ok / n/a is an unknown, and an unknown must look different from all-clear.
        dep = status.get("deploy", "")
        if dep and not dep.startswith(("ok", "n/a", "skipped")):
            return (f"⚠️ ran, but DEPLOY state is {dep.upper()!s} ({age_h:.0f}h ago) — "
                    f"cannot confirm the new build is live")
        # "ok:unverified" starts with "ok", so the branch above waves it through — which
        # is right, it is not a failure. But it is not the same as "ok:verified-live"
        # either: it means the deploy command exited 0 and the live-site check could not
        # be completed. Added with verify-deploy-live.py (2026-08-14); before that every
        # deploy on every property was in this state permanently and unlabelled.
        if dep.startswith("ok:unverified"):
            return (f"✅ ran ({age_h:.0f}h ago) — deploy exited 0 but was NOT verified "
                    f"against the live site")
        content = status.get("content", "")
        if content.startswith("failed"):
            return f"⚠️ ran, agent FAILED: {content.split(':', 1)[-1]} ({age_h:.0f}h ago)"
        if content.startswith("skipped"):
            return f"⚠️ ran, agent SKIPPED: {content.split(':', 1)[-1]} ({age_h:.0f}h ago)"
        # The COURSE agent (nightly-site.sh phase 4.7) writes its own status field. nightly-site.sh
        # started writing `courses` on 2026-07-19 and nothing read it — the one property that runs
        # it could have failed, or silently no-opped, every night while this digest still printed
        # "ok". A monitor that cannot see a phase is not monitoring that phase.
        courses = status.get("courses", "")
        if courses.startswith("failed"):
            return f"⚠️ ran, COURSE agent FAILED: {courses.split(':', 1)[-1]} ({age_h:.0f}h ago)"
        if courses.startswith("skipped"):
            return f"⚠️ ran, COURSE agent SKIPPED: {courses.split(':', 1)[-1]} ({age_h:.0f}h ago)"
        # exit_code is the one UNAMBIGUOUS signal the runner ALWAYS writes. The per-phase strings
        # above only cover content/build/deploy; any OTHER phase that aborts (GSC pull, sitemap,
        # keyword harvest, preflight) shows up ONLY here. Never claim "ok" while the process
        # exited non-zero — that discarded bit was why crashed nights rendered green.
        try:
            rc = int(status.get("exit_code", 0))
        except (TypeError, ValueError):
            rc = 0
        if rc != 0:
            return f"⚠️ ran but EXITED NON-ZERO (code {rc}) — a phase failed ({age_h:.0f}h ago)"
        # health_alerts: the tools runner reports internal faults by INCREMENTING this and setting
        # build to "ok:N-health-alerts" — which does not start with "failed", so every check above
        # waves it through. On 2026-08-08 tools sat at 6 alerts (including "Claude build failed
        # (exit 1)" and a dead-JS guard hit) while this column printed a clean "ok". The runner
        # also writes health_alert_texts, so name the first one: a count is not a diagnosis, and
        # the owner should not have to open a 49k-line log to learn what broke.
        try:
            n_alerts = int(status.get("health_alerts", 0))
        except (TypeError, ValueError):
            n_alerts = 0
        if n_alerts:
            texts = status.get("health_alert_texts") or []
            first = str(texts[0])[:90] if texts else "see the nightly log"
            more = f" (+{n_alerts - 1} more)" if n_alerts > 1 else ""
            return f"⚠️ ran, {n_alerts} HEALTH ALERT(S) ({age_h:.0f}h ago) — {first}{more}"
        # The preflight guard's verdict, if it ran. A failed preflight means the night may have
        # proceeded on a broken root or dropped inputs; a STALE/missing preflight-status once the
        # guard is wired in means the guard itself did not run — both must not read as "ok".
        pf = status_file.parent / "preflight-status.json"
        if pf.exists():
            try:
                pfd = json.loads(pf.read_text())
            except Exception:
                return f"⚠️ preflight-status.json unreadable ({age_h:.0f}h ago)"
            if not pfd.get("ok", True):
                names = ", ".join(f.get("name", "?") for f in pfd.get("failures", [])) or "?"
                return f"⚠️ PREFLIGHT FAILED: {names} ({age_h:.0f}h ago)"
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



# Distribution engine status — articles (distribute/history.json) + video
# (distribute/remotion/reel-history.json). Lives only under teamzlab-tools;
# this is a single cross-business system, not a per-SITES loop like GSC/AI.
#
# WHY THIS EXISTS: the nightly used to run `distribute.py list` (always exits
# 0, proves nothing) and neither build-growth-digest.py nor
# build-growth-watchdog.py ever read history.json at all. 72 days of
# Published:0 went unnoticed by every monitor the owner had. Mirrors the same
# freshness+TRIGGER idiom as kw_volume_freshness() below on purpose — same
# "how stale, what to do about it" shape the owner already reads nightly.
DIST_STALE_DAYS = int(os.getenv("TEAMZ_DIST_STALE_DAYS", "7"))
DIST_HOSTS = ("dev.to", "hashnode", "blogspot", "blogger", "bsky", "bluesky", "mastodon",
              "pinterest", "telegraph", "substack", "github", "tumblr", "medium",
              "gitlab", "sites.google", "tiktok", "youtube", "wordpress")


def _iso_age_days(iso_ts):
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)
        return (datetime.now() - ts).total_seconds() / 86400
    except (ValueError, AttributeError, TypeError):
        return None


def distribution_status():
    """Returns a dict — never raises. A missing/unreadable file is reported
    as its own row state, not silently skipped (same discipline as
    kw_volume_freshness's 'no-store')."""
    base = PROJECTS / "teamzlab-tools" / "scripts" / "distribute"
    out = {"articles": None, "video": None, "config_enabled": []}

    try:
        history = json.loads((base / "history.json").read_text())
        latest, plat, cnt = None, None, 0
        for post in history.get("posts", []):
            for p, info in (post.get("platforms") or {}).items():
                ts = (info or {}).get("posted_at")
                if not ts:
                    continue
                cnt += 1
                a = _iso_age_days(ts)
                if a is not None and (latest is None or a < latest):
                    latest, plat = a, p
        out["articles"] = {"age_days": latest, "platform": plat, "total_posts": cnt}
    except FileNotFoundError:
        out["articles"] = {"error": "history.json not found"}
    except (json.JSONDecodeError, KeyError) as e:
        out["articles"] = {"error": f"history.json unreadable: {e}"}

    try:
        reels = json.loads((base / "remotion" / "reel-history.json").read_text()).get("reels", [])
        latest, plat, title = None, None, None
        for reel in reels:
            for p, info in (reel.get("platforms") or {}).items():
                if p not in ("youtube", "tiktok") or not (info or {}).get("posted"):
                    continue
                ts = info.get("postedAt")
                a = _iso_age_days(ts) if ts else None
                if a is not None and (latest is None or a < latest):
                    latest, plat, title = a, p, reel.get("youtubeTitle") or reel.get("title")
        out["video"] = {"age_days": latest, "platform": plat, "last_title": title}
    except FileNotFoundError:
        out["video"] = {"error": "reel-history.json not found"}
    except (json.JSONDecodeError, KeyError) as e:
        out["video"] = {"error": f"reel-history.json unreadable: {e}"}

    try:
        cfg = json.loads((base / "config.json").read_text())
        out["config_enabled"] = sorted(p for p, v in cfg.items()
                                        if isinstance(v, dict) and v.get("enabled"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return out


def distribution_ga4_outcome(days=28):
    """What distribution actually EARNED, not just what it posted — activity
    and outcome are different questions and conflating them is how a 72-day
    silent failure happened in the first place. Fail-loud: GA4 unreachable
    returns None, rendered by the caller as 'couldn't check', never a zero."""
    prop = GA4_PROPERTY.get("teamzlab-tools")
    if not prop:
        return None
    try:
        tok = ga4_token()
        end = date.today() - timedelta(days=3)
        start = end - timedelta(days=days)
        res = _ga4_report(prop, tok, {
            "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
            "dimensions": [{"name": "sessionSource"}],
            "metrics": [{"name": "sessions"}, {"name": "totalAdRevenue"}],
            "limit": 500,
        })
        rows = res.get("rows", [])
        if not rows:
            return None  # zero rows from a live call is ambiguous — treat as unreachable
        sess = rev = 0.0
        for r in rows:
            src = r["dimensionValues"][0]["value"].lower()
            if any(h in src for h in DIST_HOSTS):
                sess += int(r["metricValues"][0]["value"])
                rev += float(r["metricValues"][1]["value"])
        return {"sessions": int(sess), "revenue": rev, "days": days}
    except Exception:  # noqa: BLE001 — any failure here means "couldn't check"
        return None


# Keyword-volume freshness. Planner volume is roughly valid ~1 year; ordering stock or gating
# SEO/GEO on year-old numbers is a real risk the owner named explicitly. WARN before it expires,
# and treat "never pulled" as a finding, not silence. Cross-property so one digest triggers all.
KW_STALE_DAYS = int(os.getenv("TEAMZ_KW_STALE_DAYS", "300"))   # warn ~2 months before the year

def _alert_channel_ready():
    """True only if an alert can actually LEAVE this Mac.

    Reuses teamz_notify's own definition of "configured" rather than restating
    it, so the two can never drift into disagreeing about whether the owner is
    reachable. Fails closed: if the module cannot be imported we report NOT
    ready, because claiming reachability we cannot verify is the worse error.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import teamz_notify as tn
        wa = tn.load_env_file(tn.WHATSAPP_ENV)
        if wa.get("CALLMEBOT_PHONE") and wa.get("CALLMEBOT_APIKEY"):
            return True
        sm = tn.load_env_file(tn.SMTP_ENV)
        return all(sm.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "ALERT_EMAIL_TO"))
    except Exception:  # noqa: BLE001
        return False


# A segment needs at least this many clicks in the window before a trend arrow means anything.
# apps.teamzlab.com took 48 clicks in the 28 days to 2026-08-13, split four ways. On numbers that
# small, ordinary week-to-week noise swamps any real change: 6 clicks vs 9 clicks is "+50%" and
# also completely meaningless. Printing an arrow there would be the monitor telling a comforting
# story, which is the one thing this file is not allowed to do. Below the floor it says so.
SEGMENT_TREND_FLOOR = 25


def _segment_of(path, apps, saas, services):
    p = [x for x in path.strip("/").split("/") if x]
    if not p:
        return "home"
    if p[0] == "blog":
        return "blog"
    if p[0] in saas:
        return "SaaS"
    if p[0] in apps:
        return "app"
    if p[0] in services:
        return "service"
    return "other"


def _segment_slugs(repo_root):
    """(app slugs, saas slugs, service slugs) read from the property's own source of truth.

    Hardcoding the three lists here is the defect class this repo has been bitten by repeatedly
    (MONEY_NICHES, HIGH_RPM_HUBS, rpm-benchmarks): a new app ships, the list is not updated, and
    the new page silently lands in 'other' where nobody looks at it. These are derived, so adding
    a landing page enrols it automatically."""
    import re as _re
    apps_dir = repo_root / "src" / "content" / "apps"
    apps = {f.stem for f in apps_dir.glob("*.md")} - {"README", "readme"} if apps_dir.exists() else set()
    # AlignFlow and AlwaysReady Care live in the apps collection but are sold as SaaS, at a price
    # per deal that dwarfs an install. They are broken out because averaging them into 'app' hides
    # the highest-value surface on the property behind the noisiest one.
    saas = {s for s in ("alignflow", "always-ready-care") if s in apps}
    apps -= saas
    svc_file = repo_root / "src" / "data" / "services.ts"
    services = set()
    if svc_file.exists():
        services = set(_re.findall(r"^\s*slug: '([a-z0-9-]+)',", svc_file.read_text(errors="ignore"), _re.M))
    return apps, saas, services


def segment_section(tok):
    """apps.teamzlab.com is THREE businesses in one Search Console property.

    App landing pages sell installs, AlignFlow/AlwaysReady sell SaaS deals, and the service pages
    sell agency work. The digest reported one clicks number for all of them, so a service cluster
    could sit at 1 click on 1,320 impressions for months while the property line read 'flat' — and
    it did. The owner has said plainly that apps, SaaS and services are separate businesses to him;
    the monitor now separates them too.

    Measured 2026-08-13, 28 days: app 32 clicks / 2.65% CTR, blog 15 / 0.60%, service 1 / 0.08%,
    SaaS 0 on 29 impressions. Same property, four completely different stories."""
    repo = PROJECTS / "teamz-lab-generic-landing-pages"
    prop = "https://apps.teamzlab.com/"
    L = ["", "## Apps property, split by business", ""]
    apps, saas, services = _segment_slugs(repo)
    if not apps and not services:
        L.append("- couldn't check — could not read the app/service slug lists from the repo.")
        return L

    def _window(days_back, days):
        end = date.today() - timedelta(days=days_back)
        start = end - timedelta(days=days - 1)
        body = json.dumps({"startDate": start.isoformat(), "endDate": end.isoformat(),
                           "dimensions": ["page"], "rowLimit": 1000}).encode()
        url = ("https://www.googleapis.com/webmasters/v3/sites/"
               f"{urllib.parse.quote(prop, safe='')}/searchAnalytics/query")
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        agg = {}
        for r in json.load(urllib.request.urlopen(req, timeout=60)).get("rows", []):
            path = r["keys"][0].split("teamzlab.com", 1)[-1]
            s = _segment_of(path, apps, saas, services)
            a = agg.setdefault(s, [0.0, 0.0])
            a[0] += r["clicks"]
            a[1] += r["impressions"]
        return agg

    try:
        now, prev = _window(3, 28), _window(31, 28)
    except Exception as e:  # noqa: BLE001
        # Unreadable must never render as zero — see the monitor-honesty rule.
        L.append(f"- couldn't check — Search Console unreachable ({type(e).__name__}).")
        return L

    L.append("| business | clicks 28d | vs prior 28d | impressions | CTR |")
    L.append("|---|---|---|---|---|")
    order = ["app", "SaaS", "service", "blog", "home", "other"]
    for s in order:
        c, i = now.get(s, [0.0, 0.0])
        pc = prev.get(s, [0.0, 0.0])[0]
        trend = arrow(c, pc) if c >= SEGMENT_TREND_FLOOR or pc >= SEGMENT_TREND_FLOOR \
            else f"too small to judge (<{SEGMENT_TREND_FLOOR})"
        ctr = f"{100 * c / i:.2f}%" if i else "—"
        L.append(f"| {s} | {int(c)} | {trend} | {int(i)} | {ctr} |")

    # The failure this table exists to surface: a segment Google shows a lot and nobody clicks.
    # Impressions without clicks is demand arriving at a page that is ranked too low to be seen,
    # and it is invisible in a whole-property total.
    for s in ("service", "SaaS", "app"):
        c, i = now.get(s, [0.0, 0.0])
        if i >= 300 and c <= 2:
            L.append("")
            L.append(f"🔔 **{s}: {int(i)} impressions, {int(c)} click(s) in 28 days.** Google is "
                     f"showing these pages and nobody is reaching them — that is a ranking-depth "
                     f"problem, not a copy problem. Check position before rewriting anything.")
    return L


def apps_revenue_section():
    """Do the mobile apps earn anything, and can we even see it?

    THE GAP THIS CLOSES. The owner's stated goal is that the apps side eventually earns what the
    tools site earns. Every part of that sentence is measured except the apps side: this digest
    reports AdSense (web) revenue and GSC clicks, and NOTHING reads AdMob. Checked 2026-08-13,
    `admob` appears in pre-release-verify.sh and aso-refresh-runner.sh and in no nightly, no
    watchdog, and no cron. So the apps could have earned nothing for a year, or tripled, and this
    page would have looked identical either way.

    Worse, when it was first called by hand the pipe turned out to be broken: the stored AdMob
    refresh token returns invalid_grant, i.e. revoked. A dead credential behind a check nobody runs
    is exactly the shape of every silent killer this file exists to catch.

    This does NOT try to fix the token — re-auth is a browser flow only the owner can complete
    (`python3 py/admob.py auth`). It makes the breakage LOUD, every single morning, until it is."""
    import subprocess as _sp
    L = ["", "## Apps — are the mobile apps earning?"]

    # THE OWNER ALREADY KNOWS THE NUMBER. He said so: ~£9/month, 2026-08-14.
    # The first version of this section shouted ❌ UNMEASURED every morning and demanded a
    # re-auth. That is a monitor arguing with the person it reports to. A figure he states is
    # better evidence than an API this machine cannot currently reach, so if TEAMZ_APPS_REVENUE_
    # GBP_MONTH is set, that is the answer and the re-auth becomes a quiet footnote — the API is
    # worth having for the PER-APP split (which of the ~20 carry the £9), never for the total.
    # Read the env FILE too, not just the process environment: /growth is run by hand from an
    # arbitrary shell that has never sourced automation.base.env, so os.getenv alone would find
    # nothing and the section would fall back to shouting — the exact behaviour being fixed.
    manual = os.getenv("TEAMZ_APPS_REVENUE_GBP_MONTH", "").strip()
    if not manual:
        try:
            for line in (CFG / "automation.base.env").read_text().splitlines():
                line = line.strip()
                if line.startswith("TEAMZ_APPS_REVENUE_GBP_MONTH="):
                    manual = line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass
    tok_file = CFG / "admob-token.json"
    if manual:
        L.append("")
        L.append(f"**£{manual}/month**, owner-stated. Compare: tools ≈ £140/month.")
        L.append("")
        L.append("_Per-app split unavailable (AdMob not connected), so which of the apps carry "
                 "this is unknown. Run `python3 py/admob.py auth` when the split matters._")
        return L

    if not tok_file.exists():
        L.append("")
        L.append("⚠️ **couldn't check** — no `~/.config/teamzlab/admob-token.json`. Nothing has "
                 "ever read AdMob earnings on this machine.")
        L.append("")
        L.append("🔔 **TRIGGER:** run `python3 py/admob.py auth` (browser flow, one time).")
        return L
    try:
        t = json.loads(tok_file.read_text())
        data = urllib.parse.urlencode({
            "client_id": t["client_id"], "client_secret": t["client_secret"],
            "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
        urllib.request.urlopen(
            urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30)
    except Exception as e:  # noqa: BLE001
        detail = ""
        if isinstance(e, urllib.error.HTTPError):
            body = e.read().decode(errors="ignore")
            detail = " (`invalid_grant` — the token was revoked)" if "invalid_grant" in body else ""
        L.append("")
        L.append(f"❌ **AdMob UNREACHABLE — apps revenue is UNMEASURED**{detail}. This is not "
                 "\"the apps earned nothing\"; it is \"nobody can tell\".")
        L.append("")
        L.append("🔔 **TRIGGER:** `cd teamz-company-automation && python3 py/admob.py auth`, then "
                 "this section starts reporting per-app earnings.")
        return L

    try:
        out = _sp.run([sys.executable, str(Path(__file__).resolve().parent / "admob.py"),
                       "report", "--days", "28", "--dimensions", "APP",
                       "--metrics", "ESTIMATED_EARNINGS,IMPRESSIONS"],
                      capture_output=True, text=True, timeout=180)
    except Exception as e:  # noqa: BLE001
        L.append(f"\n⚠️ **couldn't check** — AdMob report failed ({type(e).__name__}).")
        return L
    if out.returncode != 0:
        L.append(f"\n⚠️ **couldn't check** — AdMob report exited {out.returncode}: "
                 f"`{(out.stderr or '').strip().splitlines()[-1][:120] if out.stderr else 'no stderr'}`")
        return L
    body = (out.stdout or "").strip()
    if not body:
        # Empty output is ambiguous — it could be a real zero or a silent API change. Say which
        # one we cannot distinguish rather than printing £0.00 and letting it read as fact.
        L.append("\n⚠️ **couldn't check** — AdMob returned no rows. Cannot distinguish "
                 "\"earned nothing\" from \"query returned nothing\".")
        return L
    L.append("")
    L.append("```")
    L.extend(body.splitlines()[:25])
    L.append("```")
    L.append("")
    L.append("_Store/AdMob earnings, the only valid revenue source. Never analytics events._")
    return L


def revenue_section():
    """The money section: is revenue holding, and how concentrated is it?

    /growth is where the owner looks — he drives Uber and has said plainly he
    cannot check dashboards daily — so the revenue watchdog's verdict has to
    surface HERE, not only in a notification he might be driving through.

    Reads data/revenue-watchdog-status.json, written by build-revenue-watchdog.py
    on EVERY run, clean or not. Three states that must never collapse into each
    other:

        file missing / stale  -> "couldn't check" (the watchdog is not running)
        state == unreachable  -> "couldn't check" (GA4 refused; NOT 'no drop')
        state == ok           -> real numbers

    Rendering an unread signal as healthy is the single bug this whole
    monitoring layer exists to prevent, so every branch below says which one it
    is in words.
    """
    L = ["", "## Money — is revenue holding?"]
    path = PROJECTS / "teamz-company-automation" / "data" / "revenue-watchdog-status.json"
    if not path.exists():
        L.append("")
        L.append("⚠️ **couldn't check** — no `revenue-watchdog-status.json`. The revenue "
                 "watchdog has never run on this machine, so nothing is watching earnings.")
        return L
    try:
        s = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        L.append("")
        L.append(f"⚠️ **couldn't check** — status file unreadable ({type(e).__name__}).")
        return L

    ran = s.get("ran_at", "")
    try:
        age_h = (datetime.now() - datetime.fromisoformat(ran)).total_seconds() / 3600
    except ValueError:
        age_h = None
    if age_h is None:
        L.append("")
        L.append(f"⚠️ **couldn't check** — unparseable `ran_at` ({ran!r}).")
        return L
    if age_h > 30:
        L.append("")
        L.append(f"⚠️ **STALE — last ran {age_h:.0f}h ago** ({ran}). Treat everything below as "
                 f"history, not today. A watchdog this old is not watching anything.")
    else:
        L.append("")
        L.append(f"_Checked {ran} ({age_h:.0f}h ago). Recent = 7d ending D-2 vs the 3 weeks "
                 f"before it; GA4 per-page revenue needs ~48h to settle._")

    for repo, r in (s.get("properties") or {}).items():
        st = r.get("state")
        if st == "unreachable":
            L.append("")
            L.append(f"### {repo}")
            L.append(f"⚠️ **couldn't check** — {r.get('why')}. This is NOT 'no drop'.")
            continue
        if st == "no-ad-revenue":
            L.append("")
            L.append(f"### {repo}")
            L.append("_No ad revenue on this property — nothing to watch._")
            continue

        now, base = r.get("site_daily_recent", 0), r.get("site_daily_baseline", 0)
        delta = -r.get("site_drop_pct", 0)
        L.append("")
        L.append(f"### {repo} — ${now}/day now vs ${base}/day baseline ({delta:+.1f}%)")
        L.append(f"_Watching {r.get('pages_watched', 0)} pages = "
                 f"**{r.get('watched_revenue_share_pct', 0)}% of revenue**._")

        top = r.get("top_pages") or []
        if top:
            L.append("")
            L.append("| top earner | $/day | share |")
            L.append("|---|---|---|")
            for t in top:
                L.append(f"| `{t['page']}` | ${t['daily']} | {t['share_pct']}% |")
            lead = top[0]
            if lead["share_pct"] >= 25:
                L.append("")
                L.append(f"🔔 **CONCENTRATION: one page is {lead['share_pct']}% of this "
                         f"property's revenue.** Losing it costs about "
                         f"${lead['daily'] * 30:.0f}/month. Diversification here means "
                         f"growing high-RPM pages, not more traffic to this one.")

        for d in r.get("cliffs", []):
            L.append("")
            L.append(f"🔔 **DROP: `{d['page']}` down {d['drop_pct']}%** — "
                     f"${d['was_daily']}/day → ${d['now_daily']}/day, "
                     f"~${d['monthly_at_risk']}/month at risk. Weekly $/day: "
                     f"{' → '.join(str(x) for x in d['weekly_daily'])}.")

        fades = r.get("fades") or []
        if fades:
            L.append("")
            L.append("**Fading (expected wind-down, not an alarm):**")
            for d in fades:
                L.append(f"- `{d['page']}` — {' → '.join(str(x) for x in d['weekly_daily'])} "
                         f"$/day, ~${d['monthly_at_risk']}/mo below its old rate")

        minor = r.get("minor") or []
        if minor:
            L.append("")
            L.append(f"_{len(minor)} smaller page(s) also fell but are under the notify "
                     f"floor — see `revenue-watchdog-status.json` for the list._")

    # An alarm nobody receives is not an alarm. Say so here, every time, until fixed.
    #
    # Test the VALUES, never the file. Both whatsapp-callmebot.env and smtp.env exist
    # on this machine and both are placeholders, so an exists() check reported the
    # alert channel as configured while teamz_notify was printing "not configured"
    # on the same run. Same rule as everywhere else here: presence is not proof.
    if not _alert_channel_ready():
        L.append("")
        L.append("⚠️ **These alerts reach the Mac only.** No WhatsApp or email channel is "
                 "configured, so a revenue drop fires into an empty room while you are out. "
                 "Two-minute one-time fix: `~/.config/teamzlab/whatsapp-callmebot.env.example`.")
    return L


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


def external_feed_health():
    """Health of third-party data feeds the money pages depend on.

    Returns a list of (name, icon, state, detail, is_trigger).

    Why this section exists: /us/fantasy-football-trade-analyzer/ autofills player values
    from a snapshot built off Sleeper's free, unauthenticated API. The site never calls
    Sleeper at runtime — it reads our own committed file — which is what keeps a dead
    upstream from breaking the page. That safety has a cost: if the pull dies, NOTHING
    visibly breaks. The tool keeps working, the numbers just quietly stop matching
    reality. That is precisely the silent-decay shape this whole digest exists to catch,
    so the freshness gets its own row instead of living only in a nightly log line.

    Reads a status file written on every run, success or failure. A missing file is
    reported as "couldn't check", never as healthy — an unread signal and a clean signal
    must never look the same.
    """
    out = []
    status_path = PROJECTS / "teamzlab-tools" / "data" / "nfl-player-values-status.json"
    data_path = PROJECTS / "teamzlab-tools" / "data" / "nfl-player-values.json"
    name = "NFL player values (Sleeper API)"
    if not status_path.exists():
        out.append((name, "—", "not wired", "no status file — feed not set up on this machine", False))
        return out
    try:
        with open(status_path) as fh:
            s = json.load(fh)
    except (OSError, ValueError) as e:
        out.append((name, "⚠️", "couldn't check", f"status file unreadable ({type(e).__name__})", True))
        return out

    n = s.get("player_count") or 0
    last_success = s.get("last_success")
    if not last_success:
        out.append((name, "⛔", "NEVER SUCCEEDED", "no successful pull on record", True))
        return out
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(last_success)).days
    except (ValueError, TypeError):
        out.append((name, "⚠️", "couldn't check", "unparseable last_success timestamp", True))
        return out

    have_data = data_path.exists()
    if not have_data:
        out.append((name, "⛔", "DATA MISSING", "snapshot file absent — autocomplete is empty", True))
    elif age > 45:
        out.append((name, "🔴", "STALE", f"{age}d since last good pull ({n} players) — "
                                        f"Sleeper pull is failing silently", True))
    elif not s.get("ok"):
        out.append((name, "🟡", "last run FAILED", f"kept previous snapshot ({n} players, {age}d old) — "
                                                  f"site unaffected: {str(s.get('message'))[:80]}", False))
    else:
        out.append((name, "✅", "fresh", f"{n} players, pulled {age}d ago", False))
    return out


FRESHNESS_STALE_HOURS = 36   # nightly runs daily; >36h means it did not run last night


def freshness_and_deadlines():
    """(state, checked_at, issues, events) for the tools property.

    Why this exists: build-data-freshness.py already watches every dated asset —
    season kickoffs, stale feeds, year-stamped titles, open build windows — and on
    2026-08-08 it correctly reported that the NFL fantasy-draft window was open and
    still 'planned'. It printed that into a nightly log among hundreds of lines and
    nobody saw it. The check was never the missing piece; visibility was.

    state is one of green / issues / STALE / unreadable / missing. 'missing' and
    'unreadable' must never render as green — an unread sentinel and a passing one
    look identical only to a monitor that lies.
    """
    base = PROJECTS / "teamzlab-tools" / "data"
    status_file = base / "freshness-status.json"
    events = []
    cal = base / "event-calendar.json"
    if cal.exists():
        try:
            raw = json.loads(cal.read_text())
            for ev in (raw if isinstance(raw, list) else raw.get("events", [])):
                ds = (ev.get("date") or ev.get("start") or "")[:10]
                try:
                    dd = datetime.fromisoformat(ds).date()
                except ValueError:
                    continue
                days = (dd - datetime.now().date()).days
                if 0 <= days <= 120:
                    # lead_weeks and build MUST travel with the event. The first version kept
                    # only (days, date, name, status) and threw `build` away — and `build` is
                    # where the actual instruction lives. See the render block for what that cost.
                    events.append((days, dd, ev.get("name") or ev.get("event") or "?",
                                   ev.get("status", "?"),
                                   int(ev.get("lead_weeks") or 4),
                                   (ev.get("build") or "").strip()))
            events.sort()
        except (ValueError, OSError):
            events = None   # distinct from [] — [] means "none due", None means "couldn't read"

    if not status_file.exists():
        return ("missing", None, [], events)
    try:
        d = json.loads(status_file.read_text())
    except (ValueError, OSError):
        return ("unreadable", None, [], events)
    checked = d.get("checked_at", "")
    age_d = _iso_age_days(checked)
    if age_d is not None and age_d * 24 > FRESHNESS_STALE_HOURS:
        return ("STALE", checked, d.get("issues", []), events)
    return ("issues" if d.get("issue_count") else "green", checked,
            d.get("issues", []), events)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    args = ap.parse_args()

    end = date.today() - timedelta(days=3)          # GSC lags
    start = end - timedelta(days=args.days)
    pstart, pend = start - timedelta(days=args.days), start - timedelta(days=1)
    # A token-refresh blip must NOT crash the whole digest into an empty file (that is exactly how
    # 2026-07-18 produced NO GSC table). Capture the failure; every property then reports UNREACHABLE
    # loudly and the health/activity sections below still render.
    tok, tok_err = None, None
    try:
        tok = token()
    except Exception as e:  # noqa: BLE001 — refresh can fail on network/DNS, not just HTTP
        tok_err = f"{type(e).__name__}: {e}"

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
        if tok is None:
            # GSC auth is down for the whole run — LOUD, per property, never a zero row.
            unreachable.append((prop, f"GSC auth down ({tok_err})"))
            L.append(f"| {prop} | ⚠️ **UNREACHABLE** | — | GSC auth down | — | — | {health} |")
            continue
        try:
            c, i, ctr, pos = totals(prop, tok, start, end)
            pc, _, _, _ = totals(prop, tok, pstart, pend)
            L.append(f"| {prop} | **{c:,}** | {arrow(c, pc)} | {i:,} | {ctr:.2f}% | {pos:.1f} | {health} |")
        except urllib.error.HTTPError as e:
            # NEVER a zero row. A property we cannot read is a FINDING.
            unreachable.append((prop, f"HTTP {e.code}"))
            L.append(f"| {prop} | ⚠️ **UNREACHABLE** | — | HTTP {e.code} | — | — | {health} |")
        except Exception as e:  # noqa: BLE001
            # A network/timeout/parse error on ONE property must not crash the whole digest into an
            # empty file. Report it loudly and keep going — the other properties still render.
            unreachable.append((prop, type(e).__name__))
            L.append(f"| {prop} | ⚠️ **UNREACHABLE** | — | {type(e).__name__} | — | — | {health} |")

    if unreachable:
        L.append("")
        L.append("## ⚠️ COULD NOT CHECK — these are UNKNOWN, not zero")
        for prop, why in unreachable:
            L.append(f"- `{prop}` → {why}. URL-prefix properties end in `/`; "
                     f"domain properties (`sc-domain:`) must NOT. This exact mistake made "
                     f"goalkit read as 0 clicks for months while it really had 938.")

    # --- AI channel (sessionDefaultChannelGroup="AI Assistant") ---
    #
    # Before this, the ONLY way to see this channel was opening GA4 by hand — which is
    # literally how this section came to exist. Separate token/failure domain from GSC on
    # purpose: GA4 down must not blank the GSC table, and vice versa.
    L.append("")
    L.append("## AI channel (ChatGPT / Perplexity / Claude / Gemini)")
    try:
        gtok = ga4_token()
        gtok_err = None
    except Exception as e:  # noqa: BLE001
        gtok, gtok_err = None, f"{type(e).__name__}: {e}"

    if gtok is None:
        L.append(f"⚠️ **UNREACHABLE** — GA4 auth down ({gtok_err}). Could not check; treat as unknown, not zero.")
    else:
        L.append("| property | AI sessions | vs prev | AI revenue | $/1k sessions | organic $/1k |")
        L.append("|---|---|---|---|---|---|")
        ai_unreachable = []
        for repo, prop, _ in SITES:
            pid = GA4_PROPERTY.get(repo)
            if not pid:
                continue
            try:
                cur = {ch: (s, r) for ch, s, r in ai_channel_totals(pid, gtok, start, end)}
                prev = {ch: (s, r) for ch, s, r in ai_channel_totals(pid, gtok, pstart, pend)}
                ai_s, ai_r = cur.get("AI Assistant", (0, 0.0))
                ai_ps, _ = prev.get("AI Assistant", (0, 0.0))
                org_s, org_r = cur.get("Organic Search", (0, 0.0))
                ai_rpm = 1000 * ai_r / ai_s if ai_s else 0.0
                org_rpm = 1000 * org_r / org_s if org_s else 0.0
                L.append(f"| {prop} | {ai_s:,} | {arrow(ai_s, ai_ps)} | ${ai_r:.2f} | "
                         f"${ai_rpm:.2f} | ${org_rpm:.2f} |")
            except Exception as e:  # noqa: BLE001
                # One property's GA4 property ID being wrong/unlinked must not blank the
                # others. teamzlab-website (prop 469101682) is a KNOWN blind spot — the
                # Framer site is missing the GA4 tag — and belongs in this list, not silently
                # dropped, so the gap stays visible instead of looking like "0 AI traffic".
                ai_unreachable.append((prop, type(e).__name__))
                L.append(f"| {prop} | ⚠️ **UNREACHABLE** | — | {type(e).__name__} | — | — |")
        if ai_unreachable:
            L.append("")
            for prop, why in ai_unreachable:
                L.append(f"- `{prop}` AI channel → {why}.")

        # Weekly trend for the property that actually carries this channel. Raw total, no
        # event filtering — trailing weeks here still carry the World Cup's decay (it ended
        # 2026-07-19), but going forward this becomes the durable-base signal on its own as
        # that recedes. Read week-over-week shape, not the absolute trailing-week numbers.
        try:
            wk = ai_weekly_trend(GA4_PROPERTY["teamzlab-tools"], gtok, weeks=6)
            if wk:
                L.append("")
                L.append("### tool.teamzlab.com — AI Assistant sessions, last 6 weeks")
                L.append("| week | sessions | revenue |")
                L.append("|---|---|---|")
                for w, s, r in wk:
                    L.append(f"| {w} | {s:,} | ${r:.2f} |")
        except Exception as e:  # noqa: BLE001
            L.append(f"\n_(weekly AI trend unavailable: {type(e).__name__})_")

    L.extend(segment_section(tok))
    L.extend(apps_revenue_section())
    L.extend(revenue_section())

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

    # --- Distribution engine — activity AND outcome, not just "did it run" ---
    L.append("")
    L.append("## Distribution (articles + video)")
    dstat = distribution_status()
    art, vid = dstat["articles"], dstat["video"]
    dist_triggers = []

    if art and "error" in art:
        L.append(f"- ⚠️ articles: **COULD NOT CHECK** — {art['error']} (not a zero, genuinely unknown)")
    elif art:
        age = art["age_days"]
        if age is None:
            L.append("- ⛔ articles: **NEVER published** anything")
            dist_triggers.append("articles have never published")
        elif age > DIST_STALE_DAYS:
            L.append(f"- 🔴 articles: **STALE** — {age:.1f}d since last publish "
                     f"({art['platform']}), {art['total_posts']} total posts on record")
            dist_triggers.append(f"articles stale {age:.0f}d (last: {art['platform']})")
        else:
            L.append(f"- ✅ articles: {age:.1f}d ago on {art['platform']}")

    if vid and "error" in vid:
        L.append(f"- ⚠️ video: **COULD NOT CHECK** — {vid['error']} (not a zero, genuinely unknown)")
    elif vid:
        age = vid["age_days"]
        if age is None:
            L.append("- ⛔ video: **NEVER published** anything")
            dist_triggers.append("video has never published")
        elif age > DIST_STALE_DAYS:
            L.append(f"- 🔴 video: **STALE** — {age:.1f}d since last upload ({vid['platform']})")
            dist_triggers.append(f"video stale {age:.0f}d (last: {vid['platform']})")
        else:
            title = f' — "{vid["last_title"]}"' if vid.get("last_title") else ""
            L.append(f"- ✅ video: {age:.1f}d ago on {vid['platform']}{title}")

    L.append(f"- enabled platforms: {', '.join(dstat['config_enabled']) or '(none)'}")

    outcome = distribution_ga4_outcome(28)
    if outcome is None:
        L.append("- outcome (28d GA4): **couldn't check** — GA4 unreachable or zero rows")
    else:
        rpm = (outcome["revenue"] / outcome["sessions"] * 1000) if outcome["sessions"] else 0
        L.append(f"- outcome (28d GA4): {outcome['sessions']:,} sessions, "
                 f"${outcome['revenue']:.2f} (${rpm:.2f}/1k) from distribution-platform referrers")

    # 2-3 month value checkpoint — owner asked explicitly (2026-08-08): "after
    # 2-3 months I would actually measure if my distribution is adding value
    # or not." A passive trend line nobody reads isn't that — this prints an
    # un-missable block once enough days have actually accumulated, with a
    # verdict computed from the real numbers, not just "here's some data."
    CHECKPOINT_DUE_DAYS = int(os.getenv("TEAMZ_DIST_CHECKPOINT_DAYS", "60"))  # ~2 months, owner's floor
    lh = PROJECTS / "teamz-company-automation" / "data" / "distribution-leads-history.jsonl"
    if lh.exists():
        try:
            snaps = [json.loads(l) for l in lh.read_text().splitlines() if l.strip()]
            if snaps:
                n_biz = len(snaps[-1].get("businesses", {}))
                span = (datetime.fromisoformat(snaps[-1]["pulled_at"])
                        - datetime.fromisoformat(snaps[0]["pulled_at"])).days
                L.append(f"- per-business leads tracking: {len(snaps)} snapshot(s) on file"
                         + (f", {span}d span" if span else "")
                         + f", {n_biz} business(es) matched last pull — "
                           "`python3 py/build-distribution-leads.py --report-only` for the full table")

                if span >= CHECKPOINT_DUE_DAYS:
                    first_sess = sum(b.get("sessions", 0) for b in snaps[0].get("businesses", {}).values())
                    last_sess = sum(b.get("sessions", 0) for b in snaps[-1].get("businesses", {}).values())
                    first_rev = sum(b.get("revenue", 0) for b in snaps[0].get("businesses", {}).values())
                    last_rev = sum(b.get("revenue", 0) for b in snaps[-1].get("businesses", {}).values())
                    if last_sess < 20 and last_rev < 1.0:
                        verdict = ("**Kill it.** Distribution-attributed sessions/revenue are still "
                                   "near-zero after 2+ months of the revived, ban-protected engine "
                                   "running. Same verdict as the pre-revival baseline "
                                   "($0.83/60d) — it did not become a real channel.")
                    elif last_sess > first_sess * 1.5 and last_sess >= 20:
                        verdict = (f"**Worth another cycle.** Sessions grew {first_sess} → "
                                   f"{last_sess} over {span}d — a real trend, not noise. Keep it "
                                   "running and re-check in another 2-3 months.")
                    else:
                        verdict = (f"**Marginal — owner's call.** {first_sess} → {last_sess} sessions "
                                   f"over {span}d, ${first_rev:.2f} → ${last_rev:.2f}. Not dead, not "
                                   "clearly proven either. Weigh against what else that cron/attention "
                                   "budget could earn.")
                    L.append("")
                    L.append(f"### 📅 CHECKPOINT DUE — {span} days of distribution-leads data on file")
                    L.append(f"- sessions: {first_sess} → {last_sess}   |   revenue: "
                             f"${first_rev:.2f} → ${last_rev:.2f}")
                    L.append(f"- {verdict}")
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    if dist_triggers:
        L.append("")
        L.append("### 🔔 TRIGGER — distribution engine needs attention")
        for t in dist_triggers:
            L.append(f"- {t}")
        L.append(f"- check: `python3 scripts/distribute/distribute.py outcome --days {DIST_STALE_DAYS}` "
                 "(tools property) or the nightly's own health_alerts.")

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

    # --- External data feeds the money pages depend on ---
    feeds = external_feed_health()
    if feeds:
        L.append("")
        L.append("## External data feeds (third-party APIs behind tool pages)")
        L.append("| feed | state | detail |")
        L.append("|---|---|---|")
        feed_triggers = []
        for fname, icon, fstate_, detail, is_trig in feeds:
            L.append(f"| {fname} | {icon} {fstate_} | {detail} |")
            if is_trig:
                feed_triggers.append((fname, fstate_, detail))
        if feed_triggers:
            L.append("")
            L.append("### 🔔 TRIGGER — a tool's data feed needs attention")
            for fname, fstate_, detail in feed_triggers:
                L.append(f"- **{fname}** — {fstate_}. {detail}. The page keeps working on the "
                         f"last good snapshot, so nothing looks broken to visitors — that is "
                         f"exactly why this needs a human.")

    # --- Deadlines the owner would otherwise have to remember ---
    # Deliberately LAST so it is the final thing read, and deliberately loud: the
    # owner's words were "I am super busy so I might forget them". The sentinel
    # already tracks all of this; this section is the part that reaches a human.
    fstate, fchecked, fissues, fevents = freshness_and_deadlines()
    L.append("")
    L.append("## ⏰ Deadlines + data health (tools)")
    if fstate == "missing":
        L.append("- ⚠️ **couldn't check** — no `data/freshness-status.json`. Either the sentinel "
                 "has not run since this was wired up, or it crashed before writing. "
                 "This is NOT 'all clear'.")
    elif fstate == "unreadable":
        L.append("- ⚠️ **couldn't check** — `freshness-status.json` is corrupt. NOT 'all clear'.")
    elif fstate == "STALE":
        L.append(f"- 🔴 **sentinel last ran {fchecked}** — over {FRESHNESS_STALE_HOURS}h ago, so the "
                 f"nightly did not run last night. Deadlines below may be out of date.")
    elif fstate == "issues":
        L.append(f"- 🔴 **{len(fissues)} open issue(s)** (checked {fchecked}):")
        for i in fissues:
            L.append(f"  - {i}")
    else:
        L.append(f"- ✅ all data-freshness checks green (checked {fchecked})")

    if fevents is None:
        L.append("- ⚠️ **couldn't read** `event-calendar.json` — upcoming windows unknown.")
    elif not fevents:
        L.append("- no calendar events inside the next 120 days.")
    else:
        L.append("")
        # "live" MEANS THE PAGE EXISTS. IT DOES NOT MEAN THE SEASON'S WORK IS DONE.
        #
        # The alarm used to fire only on status == "planned". The UCL 2026-27 row reads
        # status "live" and build "refresh existing UCL pages Aug 20-28, build NOTHING new
        # (locked decision)" — the instruction was written down, dated, and decided. The digest
        # printed the row without the `build` column and without a flag, so it rendered as
        # settled. The owner found it on 2026-08-14 by asking six questions in a row about why
        # UCL earns nothing; the answer was sitting in this file the whole time.
        #
        # A live page ranked #7 three weeks before its season is exactly the case that needs
        # work, and it was the one case guaranteed to pass silently. So the window — not the
        # status — now drives the alarm: once today is inside `lead_weeks` of the date, the row
        # fires unless it is explicitly "done". Late is louder than open, because a window that
        # has already closed is the failure this whole section exists to prevent.
        L.append("| in | date | event | status | window | what to do |")
        L.append("|---|---|---|---|---|---|")
        for days, dd, name, st, lead, build in fevents:
            lead_days = max(0, lead * 7)
            opens_in = days - lead_days
            if st == "done":
                win = "closed (done)"
                flag = ""
            elif days <= lead_days // 2 and st == "planned":
                win = f"**LATE** — needed {lead}w lead"
                flag = " 🔔 **BUILD NOW**"
            elif days <= lead_days:
                win = "**OPEN NOW**"
                flag = " 🔔 **ACT THIS WEEK**"
            else:
                win = f"opens in {opens_in}d"
                flag = ""
            L.append(f"| {days}d | {dd} | {name} | {st}{flag} | {win} | {build or '—'} |")

    text = "\n".join(L)
    out = PROJECTS / "teamz-company-automation" / "docs" / "growth-digest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(text)
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
