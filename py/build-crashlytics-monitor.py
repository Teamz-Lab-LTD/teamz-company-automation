#!/usr/bin/env python3
"""
Crashlytics Monitor — push-based alerting for every Teamz Lab app.
==================================================================

Why this exists
---------------
Top3Picks shipped a bug that silently broke product search for 4 of 12 Android
users (33%) for three months. Nobody was notified, because:

  1. Firebase's default email alert only fires on FATAL crashes or a velocity
     spike above 1% of sessions. The bug produced NON_FATAL events.
  2. 18 events across 12 users never crosses a 1%-of-sessions threshold, even
     though it is a third of the user base. Firebase counts events; humans
     should be reading *ratios*.
  3. Monitoring was pull-based: you had to remember to open the console.

This script inverts that. It runs on a cron, computes impact as a RATIO of the
app's active users, diffs against the last run so you only hear about what is
new or worsening, and pushes the result to WhatsApp / email.

Two ways this monitor could lie to you (both are defended against)
-----------------------------------------------------------------
1. Silent zero. Call the endpoint with no interval filter and it returns
   `{"groups": []}` with HTTP 200 — no error, just nothing. (A comma-joined
   error_types list, by contrast, fails loudly with a 400.) A monitor that
   reads that empty list as "no issues" is worse than no monitor: it actively
   reassures you while blind. `selftest()` runs before every scan and asserts
   that a 89-day window across the fleet returns a non-empty result; if not, it
   exits non-zero instead of reporting all-clear.

2. Blind spots. If an app 401s or 403s, we cannot know whether it is healthy.
   Those targets are emitted as CRITICAL findings, never filtered out of the
   alert set, and the report prints explicit coverage counts. "All clear" is
   only ever printed alongside how much of the fleet was actually readable.
   HTTP 404 is different: it means the app has never sent Crashlytics data. That
   is benign, stays quiet, and is excluded from the healthy count.

Auth
----
Uses `gcloud auth print-access-token`. No `firebase login` (per standing order).
The Firebase Crashlytics API must be enabled per project; the script enables it
automatically on first 403 unless --no-enable-api.

Usage
-----
  python3 py/build-crashlytics-monitor.py                  # scan all apps, 24h window, notify on new/spiking
  python3 py/build-crashlytics-monitor.py --window-hours 168
  python3 py/build-crashlytics-monitor.py --app top3picks  # one app
  python3 py/build-crashlytics-monitor.py --dry-run        # print, never notify, never write state
  python3 py/build-crashlytics-monitor.py --force-notify   # send even if nothing changed (test the pipe)
  python3 py/build-crashlytics-monitor.py --selftest       # only verify the API contract, then exit
  python3 py/build-crashlytics-monitor.py --discover       # print app registry from local Flutter projects

Notification setup (both optional; the report file is always written)
--------------------------------------------------------------------
WhatsApp via CallMeBot (free, ~2 min, personal number):
  1. Save +34 644 51 95 23 to your contacts as "CallMeBot".
  2. WhatsApp it exactly: I allow callmebot to send me messages
  3. It replies with your API key.
  4. Write ~/.config/teamzlab/whatsapp-callmebot.env:
        CALLMEBOT_PHONE=+8801XXXXXXXXX
        CALLMEBOT_APIKEY=123456

Email via SMTP (Gmail needs an App Password, not your login password):
  Write ~/.config/teamzlab/smtp.env:
        SMTP_HOST=smtp.gmail.com
        SMTP_PORT=587
        SMTP_USER=you@gmail.com
        SMTP_PASS=your-16-char-app-password
        ALERT_EMAIL_TO=you@gmail.com

Exit codes: 0 ok / 1 hard failure (auth, selftest) / 2 critical issues found.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import smtplib
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = Path(os.getenv("TEAMZ_DATA_DIR", ROOT / "data"))
APPS_FILE = DATA_DIR / "crashlytics-apps.json"
STATE_FILE = DATA_DIR / "crashlytics-monitor-state.json"
REPORT_FILE = DATA_DIR / "crashlytics-monitor-report.md"

CONFIG_DIR = Path.home() / ".config" / "teamzlab"
WHATSAPP_ENV = CONFIG_DIR / "whatsapp-callmebot.env"
SMTP_ENV = CONFIG_DIR / "smtp.env"

GCLOUD_ACCOUNT = os.getenv("TEAMZ_GCLOUD_ACCOUNT", "teamz.lab.contact@gmail.com")
API_ROOT = "https://firebasecrashlytics.googleapis.com/v1alpha"
ERROR_TYPES = ("FATAL", "NON_FATAL", "ANR")

# The API caps the lookback window at 90 days; stay inside it.
MAX_LOOKBACK_DAYS = 89

# ── Thresholds ───────────────────────────────────────────────────────────────
# Ratio mode (we know the active-user denominator) — the mode that would have
# caught the Top3Picks bug on day one.
RATIO_CRITICAL = 0.20   # >=20% of active users impacted
RATIO_WARNING = 0.05    # >=5%

# Absolute mode (no denominator known) — deliberately conservative, because a
# raw count cannot distinguish "4 of 12 users" from "4 of 10,000".
ABS_FATAL_USERS_CRITICAL = 3
ABS_ANY_USERS_CRITICAL = 25
ABS_ANY_USERS_WARNING = 5

# A known-regressing issue: events grew this many times vs the previous run.
SPIKE_MULTIPLIER = 3.0

SEV_ORDER = {"critical": 0, "warning": 1, "info": 2}
SEV_ICON = {"critical": "[CRIT]", "warning": "[WARN]", "info": "[info]"}


# ── Small utilities ──────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(msg, flush=True)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_env_file(path: Path) -> dict[str, str]:
    """Parse a trivial KEY=VALUE env file. Missing file -> {}."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def project_number(app_id: str) -> str:
    """'1:78491713820:android:abc' -> '78491713820'."""
    parts = app_id.split(":")
    if len(parts) < 3:
        raise ValueError(f"Malformed Firebase app id: {app_id}")
    return parts[1]


# ── Auth ─────────────────────────────────────────────────────────────────────
def _mint_token() -> str:
    try:
        out = subprocess.run(
            ["gcloud", "auth", "print-access-token", f"--account={GCLOUD_ACCOUNT}"],
            capture_output=True, text=True, timeout=60, check=True,
        )
    except FileNotFoundError:
        sys.exit("FATAL: gcloud not on PATH.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"FATAL: gcloud auth failed for {GCLOUD_ACCOUNT}: {e.stderr.strip()}")
    token = out.stdout.strip()
    if not token:
        sys.exit("FATAL: gcloud returned an empty access token.")
    return token


class TokenProvider:
    """
    A scan can outlive a single access token: enabling the Crashlytics API on a
    cold project costs up to two minutes of polling, and gcloud hands out cached
    tokens that may already be close to expiry. Minting once at startup produced
    a fleet-wide 401 storm. Re-mint on a timer, and once more on demand when a
    401 proves the current token is dead.
    """

    REFRESH_AFTER_SECONDS = 900  # 15 min; tokens live ~60 min

    def __init__(self) -> None:
        self._token = ""
        self._minted_at = 0.0

    def get(self) -> str:
        import time
        if not self._token or (time.monotonic() - self._minted_at) > self.REFRESH_AFTER_SECONDS:
            self._token = _mint_token()
            self._minted_at = time.monotonic()
        return self._token

    def force_refresh(self) -> str:
        import time
        self._token = _mint_token()
        self._minted_at = time.monotonic()
        return self._token


# Projects whose API we already tried to enable this run — enabling is slow and
# each project has two platforms, so never pay that cost twice.
_ENABLE_ATTEMPTED: set[str] = set()


def enable_crashlytics_api(project_id: str) -> bool:
    if project_id in _ENABLE_ATTEMPTED:
        return False
    _ENABLE_ATTEMPTED.add(project_id)
    log(f"    enabling firebasecrashlytics.googleapis.com on {project_id} ...")
    r = subprocess.run(
        ["gcloud", "services", "enable", "firebasecrashlytics.googleapis.com",
         f"--project={project_id}", f"--account={GCLOUD_ACCOUNT}"],
        capture_output=True, text=True, timeout=180,
    )
    if r.returncode != 0:
        log(f"    could not enable API: {r.stderr.strip()[:160]}")
        return False
    return True


# ── Crashlytics API ──────────────────────────────────────────────────────────
class ApiError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:200]}")
        self.status = status
        self.body = body


def fetch_top_issues(
    token: str,
    project_id: str,
    app_id: str,
    start: dt.datetime,
    end: dt.datetime,
    page_size: int = 25,
) -> list[dict]:
    """
    GET /projects/{num}/apps/{appId}/reports/topIssues

    error_types MUST be sent as REPEATED query params. Comma-joining them makes
    the API return an empty group list with HTTP 200 — a silent false negative.
    """
    params: list[tuple[str, str]] = [
        ("filter.interval.start_time", iso(start)),
        ("filter.interval.end_time", iso(end)),
        ("page_size", str(page_size)),
    ]
    params += [("filter.issue.error_types", t) for t in ERROR_TYPES]

    url = f"{API_ROOT}/projects/{project_number(app_id)}/apps/{app_id}/reports/topIssues"
    url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": project_id,
    })
    try:
        with urllib.request.urlopen(req, timeout=45, context=ssl.create_default_context()) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise ApiError(e.code, e.read().decode("utf-8", "replace")) from None
    except urllib.error.URLError as e:
        raise ApiError(0, f"network: {e.reason}") from None

    issues: list[dict] = []
    for group in payload.get("groups", []) or []:
        issue = group.get("issue") or {}
        metrics = (group.get("metrics") or [{}])[0]
        issues.append({
            "id": issue.get("id", ""),
            "title": (issue.get("title") or "").strip(),
            "subtitle": (issue.get("subtitle") or "").strip().splitlines()[0][:160],
            "error_type": issue.get("errorType", "UNKNOWN"),
            "state": issue.get("state", ""),
            "first_seen_version": issue.get("firstSeenVersion", ""),
            "last_seen_version": issue.get("lastSeenVersion", ""),
            "uri": issue.get("uri", ""),
            "users": int(metrics.get("impactedUsersCount") or 0),
            "events": int(metrics.get("eventsCount") or 0),
        })
    return issues


class NoCrashlyticsData(RuntimeError):
    """The app exists but has never reported to Crashlytics (HTTP 404). Benign."""


def fetch_with_retry(
    tokens: "TokenProvider",
    project_id: str,
    app_id: str,
    start: dt.datetime,
    end: dt.datetime,
    allow_enable: bool = True,
) -> list[dict]:
    """
    Fetch topIssues, handling the three failure modes we actually observe:

      401 -> the access token died mid-run. Re-mint once and retry.
      403 'has not been used' -> the Crashlytics API is off for this project.
             Enable it, then poll while the change propagates.
      404 -> the app has no Crashlytics data at all. Not an error; the caller
             records it as 'no data' rather than as a monitor failure.
    """
    import time

    try:
        return fetch_top_issues(tokens.get(), project_id, app_id, start, end)
    except ApiError as e:
        if e.status == 404:
            raise NoCrashlyticsData(app_id) from None

        if e.status == 401:
            log("    token expired mid-run; re-minting and retrying")
            tokens.force_refresh()
            try:
                return fetch_top_issues(tokens.get(), project_id, app_id, start, end)
            except ApiError as e2:
                if e2.status == 404:
                    raise NoCrashlyticsData(app_id) from None
                raise

        disabled = e.status == 403 and ("has not been used" in e.body or "is disabled" in e.body)
        if disabled and allow_enable and enable_crashlytics_api(project_id):
            log("    API enabled; retrying (propagation can take ~1 min)")
            for _ in range(6):
                time.sleep(20)
                try:
                    return fetch_top_issues(tokens.get(), project_id, app_id, start, end)
                except ApiError as e2:
                    if e2.status == 404:
                        raise NoCrashlyticsData(app_id) from None
                    if e2.status == 401:
                        tokens.force_refresh()
                        continue
                    if e2.status != 403:
                        raise
            raise ApiError(403, "API enabled but still 403 after retries")
        raise


# ── Self-test: guard against the silent-zero trap ────────────────────────────
def selftest(tokens: "TokenProvider", apps: list[dict]) -> None:
    """
    Prove the API contract still holds before we trust a 'no issues' result.

    Scan a wide window across every app. If EVERY reachable app returns zero
    issues, that is far likelier to be a broken filter or a permissions change
    than a genuinely pristine fleet -- so fail loudly rather than report
    all-clear. Apps with no Crashlytics data at all (404) are excluded from the
    denominator; they cannot vouch for the contract either way.
    """
    end = utcnow()
    start = end - dt.timedelta(days=MAX_LOOKBACK_DAYS)
    total, reachable, no_data, broken = 0, 0, 0, 0

    for app in apps:
        for platform in ("android", "ios"):
            app_id = app.get(platform)
            if not app_id:
                continue
            try:
                found = fetch_with_retry(tokens, app["project_id"], app_id, start, end)
            except NoCrashlyticsData:
                no_data += 1
                continue
            except ApiError as e:
                broken += 1
                log(f"  selftest: {app['slug']}/{platform} unreachable (HTTP {e.status})")
                continue
            reachable += 1
            total += len(found)

    if reachable == 0:
        sys.exit(
            "FATAL selftest: no app returned readable Crashlytics data "
            f"({broken} unreachable, {no_data} with no data).\n"
            "Refusing to run: a monitor that cannot read anything must never report 'all clear'."
        )
    if total == 0:
        sys.exit(
            f"FATAL selftest: 0 issues across ALL {reachable} readable app/platform targets over "
            f"the last {MAX_LOOKBACK_DAYS} days.\n"
            "That is almost certainly a broken filter or a permissions change, not a clean fleet.\n"
            "Refusing to report 'all clear'. Verify the API contract before trusting this monitor."
        )
    log(f"  selftest OK — {total} issues across {reachable} readable targets "
        f"({no_data} no-data, {broken} unreachable)")


# ── Severity ─────────────────────────────────────────────────────────────────
def score(issue: dict, active_users: int | None, previous: dict | None) -> tuple[str, str]:
    """Return (severity, human-readable reason)."""
    users, events = issue["users"], issue["events"]
    fatal = issue["error_type"] in ("FATAL", "ANR")

    severity, reason = _raw_score(issue, active_users, previous, users, events, fatal)

    # A NON_FATAL is never critical. It is a recorded exception, not a dead app.
    #
    # This monitor scores impact and ignored error type in two of its three branches: the ratio
    # branch and the spike branch both returned "critical" on reach alone. So Hazira Khata's
    # `armClassListLoadDead` — which is `AppLogger.logFailure(...)` -> `recordException()`, a
    # DELIBERATE diagnostic that fires when a class list has not resolved in 12s and then shows
    # the content anyway — was reported as "1 CRITICAL crash" at 21 users, every session, for
    # days. Nothing had crashed. Filtering the same account to FATAL+ANR does not return it.
    #
    # The cost is not the wrong label. It is that this monitor's whole job is to be believed:
    # exit code 2 gates the nightly on it, the session hook opens with it, and a banner that
    # cries crash when no app died trains the reader to skip the banner — on the day a real
    # 2-user FATAL is sitting underneath it, which is exactly what was happening.
    #
    # Capped, not silenced: a widespread non-fatal still reports as "warning", and warning is
    # still alerted on while it is new (see worth_alerting). It just stops claiming a crash and
    # stops forcing exit 2.
    if severity == "critical" and not fatal:
        return "warning", f"{reason} — NON_FATAL (recorded exception, no crash), capped at warning"
    return severity, reason


def _raw_score(issue: dict, active_users: int | None, previous: dict | None,
               users: int, events: int, fatal: bool) -> tuple[str, str]:
    """Impact scoring on reach alone. Error type is applied by the caller."""
    # Regression check first: a known issue that suddenly got much worse.
    if previous:
        prev_events = previous.get("events", 0)
        if prev_events > 0 and events >= prev_events * SPIKE_MULTIPLIER:
            return "critical", f"spiking: {prev_events} -> {events} events ({events / prev_events:.1f}x)"

    if active_users and active_users > 0:
        ratio = users / active_users
        pct = f"{ratio:.0%} of {active_users} active users"
        if ratio >= RATIO_CRITICAL:
            return "critical", f"{pct} impacted"
        if ratio >= RATIO_WARNING:
            return "warning", f"{pct} impacted"
        return "info", pct

    # No denominator: absolute fallback. Say so, so nobody mistakes it for a ratio.
    if fatal and users >= ABS_FATAL_USERS_CRITICAL:
        return "critical", f"{users} users hit a {issue['error_type']} (no active-user baseline)"
    if users >= ABS_ANY_USERS_CRITICAL:
        return "critical", f"{users} users impacted (no active-user baseline)"
    if users >= ABS_ANY_USERS_WARNING:
        return "warning", f"{users} users impacted (no active-user baseline)"
    return "info", f"{users} users, {events} events (no active-user baseline)"


# ── Scan ─────────────────────────────────────────────────────────────────────
def scan(tokens: "TokenProvider", apps: list[dict], window_hours: int, state: dict) -> tuple[list[dict], dict, dict]:
    """Return (findings, coverage, coverage_by_app).

    coverage is fleet totals; coverage_by_app maps slug -> read|no_data|unreachable so a
    per-project file can distinguish "healthy" from "not looked at".
    """
    end = utcnow()
    start = end - dt.timedelta(hours=window_hours)
    findings: list[dict] = []
    coverage = {"read": 0, "no_data": 0, "unreachable": 0}
    # Per-app rollup, so write_project_status() can tell "no crashes" apart from
    # "we could not look". The fleet counters above are totals and cannot answer that.
    # Worst status across an app's platforms wins: unreachable > no_data > read.
    by_app: dict[str, str] = {}

    def note(slug: str, status: str) -> None:
        rank = {"read": 0, "no_data": 1, "unreachable": 2}
        if rank[status] >= rank.get(by_app.get(slug, "read"), 0):
            by_app[slug] = status

    for app in apps:
        slug = app["slug"]
        for platform in ("android", "ios"):
            app_id = app.get(platform)
            if not app_id:
                continue
            key_prefix = f"{slug}/{platform}"
            try:
                issues = fetch_with_retry(tokens, app["project_id"], app_id, start, end)
            except NoCrashlyticsData:
                coverage["no_data"] += 1
                note(slug, "no_data")
                log(f"  {key_prefix:<32} no Crashlytics data")
                continue
            except ApiError as e:
                coverage["unreachable"] += 1
                note(slug, "unreachable")
                log(f"  {key_prefix:<32} UNREACHABLE (HTTP {e.status})")
                # A blind spot is itself an incident. It must never be filtered
                # out of the alert set -- that is how the fleet went unwatched.
                findings.append({
                    "id": f"monitor-unreachable-{key_prefix}",
                    "app": slug, "platform": platform, "severity": "critical",
                    "title": "Crashlytics unreachable — monitor is blind here",
                    "subtitle": str(e)[:140], "uri": "",
                    "reason": f"HTTP {e.status}: cannot tell if this app is healthy",
                    "users": 0, "events": 0, "is_new": True,
                    "error_type": "MONITOR", "state_key": "",
                })
                continue

            coverage["read"] += 1
            note(slug, "read")
            active = (app.get("active_users") or {}).get(platform)
            log(f"  {key_prefix:<32} {len(issues)} issue(s)")

            for issue in issues:
                state_key = f"{key_prefix}/{issue['id']}"
                previous = state.get("issues", {}).get(state_key)
                severity, reason = score(issue, active, previous)
                findings.append({
                    **issue,
                    "app": slug, "platform": platform,
                    "severity": severity, "reason": reason,
                    "is_new": previous is None,
                    "state_key": state_key,
                })

    findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 3), -f["users"], -f["events"]))
    return findings, coverage, by_app


def worth_alerting(findings: list[dict]) -> list[dict]:
    """
    Anything critical (including monitor blind spots), plus newly-appeared
    warnings. Known, stable, low-impact issues stay quiet so the channel keeps
    its signal.
    """
    return [f for f in findings if f["severity"] == "critical" or (f["is_new"] and f["severity"] != "info")]


# ── Rendering ────────────────────────────────────────────────────────────────
def render_markdown(findings: list[dict], alerts: list[dict], window_hours: int, coverage: dict) -> str:
    now = iso(utcnow())
    lines = [
        "# Crashlytics Monitor",
        "",
        f"- Scanned: `{now}`",
        f"- Window: last **{window_hours}h**",
        f"- Coverage: **{coverage['read']} read**, {coverage['no_data']} no-data, "
        f"**{coverage['unreachable']} unreachable**",
        f"- Issues seen: **{len(findings)}**  |  Needing attention: **{len(alerts)}**",
        "",
    ]
    if not alerts:
        verdict = "Fleet is quiet for this window."
        if coverage["unreachable"]:
            verdict = ("Quiet **only where the monitor could see**. "
                       f"{coverage['unreachable']} target(s) unreachable — treat as unknown, not healthy.")
        lines += ["## No new or critical issues", "", verdict, ""]
    else:
        # Type is in this table, not only the one below it: a reader deciding whether to drop
        # everything needs "FATAL" or "NON_FATAL" in the same row as the severity. Without it the
        # top table read as a crash list even when nothing in it had crashed.
        lines += ["## Needs attention", "",
                  "| Sev | App | Platform | Type | Users | Events | Issue | Why |",
                  "|---|---|---|---|---|---|---|---|"]
        for f in alerts:
            new = " (new)" if f["is_new"] else ""
            title = (f["title"] or "?")[:52].replace("|", "\\|")
            reason = f["reason"].replace("|", "\\|")
            lines.append(
                f"| {SEV_ICON[f['severity']]} | {f['app']} | {f['platform']} | "
                f"{f['error_type']} | {f['users']} | {f['events']} | {title}{new} | {reason} |"
            )
        lines.append("")

    if findings:
        lines += ["## All issues in window", "",
                  "| Sev | App | Plat | Type | Users | Events | Issue |",
                  "|---|---|---|---|---|---|---|"]
        for f in findings:
            title = (f["title"] or "?")[:60].replace("|", "\\|")
            lines.append(
                f"| {SEV_ICON[f['severity']]} | {f['app']} | {f['platform']} | "
                f"{f['error_type']} | {f['users']} | {f['events']} | {title} |"
            )
        lines.append("")

    lines += ["---", "",
              "Impact is scored as a **ratio of active users** when a baseline exists in "
              "`data/crashlytics-apps.json`; otherwise absolute counts are used and the row says so. "
              "A raw event count cannot tell 4-of-12 users apart from 4-of-10,000.",
              "",
              "**Only FATAL and ANR can be `[CRIT]`.** A NON_FATAL is a recorded exception — the app "
              "kept running — so however far it reaches it is capped at `[WARN]`. Check the **Type** "
              "column before treating a row as an outage."]
    return "\n".join(lines)


PROJECTS_ROOT = Path.home() / "Projects" / "Teamz Lab Projects" / "teamz-projects"
# Written into each app's own repo so the next Claude/Codex session opened there is told
# about the app's open crashes. A report that only exists in teamz-company-automation is a
# report nobody reads while actually working on the app.
PROJECT_STATUS_REL = Path(".claude") / "crash-status.md"


def _project_dirs_by_firebase_id() -> dict[str, Path]:
    """Map Firebase project_id -> local repo, by reading each project's own Firebase config.

    Resolving by slug does not work: registry slugs are human-chosen and drift from the
    folder name (slug "devicegpt" lives in ./debugger). The Firebase project_id is the one
    identifier that appears in both the registry and the checked-out repo, so it is the
    only reliable join key.
    """
    import re
    out: dict[str, Path] = {}
    for gs in PROJECTS_ROOT.glob("*/app/google-services.json"):
        try:
            pid = json.loads(gs.read_text(encoding="utf-8", errors="replace"))["project_info"]["project_id"]
        except (json.JSONDecodeError, KeyError):
            continue
        out.setdefault(pid, gs.parents[1])
    for opts in PROJECTS_ROOT.glob("*/lib/firebase_options.dart"):
        m = re.search(r"projectId: '([^']+)'", opts.read_text(encoding="utf-8", errors="replace"))
        if m:
            out.setdefault(m.group(1), opts.parents[1])
    return out


def project_dir_for(app: dict, index: dict[str, Path]) -> Path | None:
    """Resolve a registry entry to its local repo, or None if it isn't checked out here."""
    pid = app.get("project_id")
    if pid and pid in index:
        return index[pid]
    # Last resort for a project with no local Firebase config: a folder named like the slug.
    slug = app.get("slug")
    if slug and (PROJECTS_ROOT / slug).is_dir():
        return PROJECTS_ROOT / slug
    return None


def write_project_status(
    apps: list[dict], findings: list[dict], window_hours: int, coverage_by_app: dict
) -> list[str]:
    """Drop a per-app crash summary into each app's own repo. Returns paths written.

    Truthfulness rules, same as the fleet report:
      * an app we could NOT read says so — it must never look like an app with no crashes;
      * the file is always rewritten, so a fixed app's file becomes an explicit all-clear
        rather than a stale warning that trains the reader to ignore it;
      * the scan timestamp is embedded so a consumer can judge staleness itself.
    """
    written: list[str] = []
    index = _project_dirs_by_firebase_id()
    by_app: dict[str, list[dict]] = {}
    for f in findings:
        by_app.setdefault(f["app"], []).append(f)

    for app in apps:
        slug = app["slug"]
        d = project_dir_for(app, index)
        if d is None:
            continue
        mine = sorted(
            by_app.get(slug, []),
            key=lambda f: (f["severity"] != "critical", -int(f.get("users") or 0)),
        )
        status = coverage_by_app.get(slug, "read")
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%MZ")

        lines = [
            f"# Crash status — {slug}",
            "",
            f"- Scanned: `{stamp}` (last **{window_hours}h**)",
            f"- Source: `teamz-company-automation/py/build-crashlytics-monitor.py`",
            "",
        ]
        if status == "unreachable":
            lines += [
                "## ⚠️ NOT VERIFIED",
                "",
                "Crashlytics could not be read for this app (auth or API error), so this is "
                "**not** an all-clear. Re-run the monitor before trusting any silence here.",
                "",
            ]
        elif status == "no_data":
            lines += [
                "## No Crashlytics data",
                "",
                "This app has never reported to Crashlytics. Either the SDK is not wired up "
                "or no build with it has shipped.",
                "",
            ]
        elif not mine:
            lines += ["## ✅ No crashes in window", ""]
        else:
            # This file is what an agent reads at session start, so the split between "the app
            # died" and "the app logged something" belongs in the HEADING, not inferred from a
            # row further down. "17 open issue(s)" over a table of non-fatals reads as 17 crashes.
            crit = [f for f in mine if f["severity"] == "critical"]
            crashes = [f for f in mine if f.get("error_type") in ("FATAL", "ANR")]
            head = f"## {len(mine)} open issue(s)"
            if crit:
                head += f" — {len(crit)} CRITICAL"
            head += f" · {len(crashes)} crash-type (FATAL/ANR), {len(mine) - len(crashes)} non-fatal"
            lines += [
                head,
                "",
                "| Sev | Type | Users | Events | Issue |",
                "|---|---|---|---|---|",
            ]
            for f in mine[:15]:
                title = (f.get("title") or "?").replace("|", "\\|")[:70]
                lines.append(
                    f"| {f['severity']} | {f.get('error_type', '?')} | "
                    f"{f.get('users', '?')} | {f.get('events', '?')} | {title} |"
                )
            if len(mine) > 15:
                lines.append(f"| … | | | | and {len(mine) - 15} more |")
            # A non-fatal cannot be critical (see score()); say so here too, because this file is
            # frequently read on its own with no access to the fleet report's footnotes.
            lines += [
                "",
                "Only FATAL/ANR rows are crashes. A `NON_FATAL` is a recorded exception — the app "
                "kept running — and is capped at `warning` however far it reaches.",
            ]
            lines += [
                "",
                "Full fleet report: `teamz-company-automation/data/crashlytics-monitor-report.md`",
                "",
                "Re-check just this app:",
                "",
                "```bash",
                f"python3 py/build-crashlytics-monitor.py --app {slug} --window-hours 168 --dry-run",
                "```",
                "",
            ]

        out = d / PROJECT_STATUS_REL
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines), encoding="utf-8")
        written.append(str(out))
    return written


def render_short(alerts: list[dict], window_hours: int, total: int, coverage: dict) -> str:
    """Compact message body for WhatsApp / email subject-adjacent use."""
    if not alerts:
        msg = f"Crashlytics OK — no new/critical issues in last {window_hours}h ({total} tracked)."
        if coverage["unreachable"]:
            msg += f" NOTE: {coverage['unreachable']} target(s) unreachable — not verified healthy."
        return msg

    crit = sum(1 for a in alerts if a["severity"] == "critical")
    head = f"Crashlytics: {len(alerts)} need attention ({crit} critical) — last {window_hours}h"
    body = [head, ""]
    for a in alerts[:8]:
        title = (a["title"] or "?")[:44]
        body.append(f"{SEV_ICON[a['severity']]} {a['app']}/{a['platform']}: {title}")
        body.append(f"    {a['users']} users, {a['events']} events — {a['reason']}")
    if len(alerts) > 8:
        body.append(f"... and {len(alerts) - 8} more")
    return "\n".join(body)


# ── Notifications ────────────────────────────────────────────────────────────
def notify_whatsapp(text: str) -> tuple[bool, str]:
    cfg = load_env_file(WHATSAPP_ENV)
    phone, key = cfg.get("CALLMEBOT_PHONE"), cfg.get("CALLMEBOT_APIKEY")
    if not phone or not key:
        return False, f"not configured ({WHATSAPP_ENV})"
    url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode(
        {"phone": phone, "text": text[:900], "apikey": key}
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return (r.status == 200), f"HTTP {r.status}"
    except Exception as e:  # noqa: BLE001 - notification must never crash the scan
        return False, str(e)[:120]


def notify_email(subject: str, text: str) -> tuple[bool, str]:
    cfg = load_env_file(SMTP_ENV)
    required = ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "ALERT_EMAIL_TO")
    if not all(cfg.get(k) for k in required):
        return False, f"not configured ({SMTP_ENV})"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["SMTP_USER"]
    msg["To"] = cfg["ALERT_EMAIL_TO"]
    msg.set_content(text)
    try:
        with smtplib.SMTP(cfg["SMTP_HOST"], int(cfg.get("SMTP_PORT", 587)), timeout=30) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(cfg["SMTP_USER"], cfg["SMTP_PASS"])
            s.send_message(msg)
        return True, "sent"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:120]


def notify_macos(text: str) -> tuple[bool, str]:
    if sys.platform != "darwin":
        return False, "not macOS"
    title = "Crashlytics Monitor"
    first = text.splitlines()[0][:180].replace('"', "'")
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{first}" with title "{title}"'],
            capture_output=True, timeout=15,
        )
        return True, "shown"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:80]


def dispatch(alerts: list[dict], short: str, dry_run: bool) -> None:
    if dry_run:
        log("\n[dry-run] would notify with:\n" + short)
        return
    subject = f"[Crashlytics] {len(alerts)} issue(s) need attention" if alerts else "[Crashlytics] all clear"
    for name, fn in (
        ("whatsapp", lambda: notify_whatsapp(short)),
        ("email", lambda: notify_email(subject, short)),
        ("macos", lambda: notify_macos(short)),
    ):
        ok, detail = fn()
        log(f"  notify/{name:<9} {'sent' if ok else 'skipped'} — {detail}")


# ── State ────────────────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log(f"  warn: {STATE_FILE.name} corrupt — starting fresh")
    return {"issues": {}}


def save_state(findings: list[dict]) -> None:
    state = {
        "last_run": iso(utcnow()),
        "issues": {
            f["state_key"]: {"users": f["users"], "events": f["events"], "severity": f["severity"]}
            for f in findings if f.get("state_key")
        },
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Discover ─────────────────────────────────────────────────────────────────
def discover() -> None:
    """Print a registry skeleton from every local project's Firebase config.

    Two sources, because two kinds of project exist here:

      * Flutter  -> lib/firebase_options.dart
      * native   -> app/google-services.json

    This used to read firebase_options.dart only. Native-Android apps have no such file, so
    they were structurally invisible: DeviceGPT shipped a bug on 2026-04-23 that sat unseen
    until 2026-07-22, when it was added to the registry by hand and the very next monitor run
    surfaced it (1,193 non-fatals, 9 users). Hazira Khata — a paying-customer app — had never
    been monitored at all for the same reason. A discovery that silently covers only one
    project type is the same class of lie as a monitor that reports "all clear" while blind.
    """
    import re
    root = Path.home() / "Projects" / "Teamz Lab Projects" / "teamz-projects"
    by_project: dict[str, dict] = {}

    def add(entry: dict) -> None:
        # Keep the richest entry when a project is found by both scanners: a Flutter hit
        # carries ios+android, a google-services.json hit carries android only.
        prev = by_project.get(entry["project_id"])
        if prev is None or len(entry) > len(prev):
            by_project[entry["project_id"]] = entry

    # Flutter projects.
    for opts in sorted(root.glob("*/lib/firebase_options.dart")):
        text = opts.read_text(encoding="utf-8", errors="replace")
        pm = re.search(r"projectId: '([^']+)'", text)
        if not pm or pm.group(1) == "YOUR_PROJECT_ID":
            continue
        entry = {"slug": opts.parents[1].name, "project_id": pm.group(1)}
        for plat in ("android", "ios"):
            m = re.search(rf"appId: '(1:\d+:{plat}:[a-f0-9]+)'", text)
            if m:
                entry[plat] = m.group(1)
        if len(entry) > 2:
            add(entry)

    # Native Android projects.
    for gs in sorted(root.glob("*/app/google-services.json")):
        try:
            cfg = json.loads(gs.read_text(encoding="utf-8", errors="replace"))
            project_id = cfg["project_info"]["project_id"]
            app_id = cfg["client"][0]["client_info"]["mobilesdk_app_id"]
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
        add({"slug": gs.parents[1].name, "project_id": project_id, "android": app_id})

    apps = sorted(by_project.values(), key=lambda a: a["slug"])
    print(json.dumps({"apps": apps}, indent=2))


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser(description="Crashlytics monitor with ratio-based alerting")
    p.add_argument("--window-hours", type=int, default=24)
    p.add_argument("--app", help="only this slug")
    p.add_argument("--dry-run", action="store_true", help="never notify, never write state")
    p.add_argument("--force-notify", action="store_true", help="notify even when nothing changed")
    p.add_argument("--selftest", action="store_true", help="verify API contract and exit")
    p.add_argument("--discover", action="store_true", help="print app registry from local projects")
    p.add_argument("--no-enable-api", action="store_true", help="never auto-enable the Crashlytics API")
    args = p.parse_args()

    if args.discover:
        discover()
        return 0

    if not APPS_FILE.is_file():
        sys.exit(f"FATAL: missing {APPS_FILE}. Run --discover to bootstrap it.")
    apps = json.loads(APPS_FILE.read_text(encoding="utf-8"))["apps"]
    if args.app:
        apps = [a for a in apps if a["slug"] == args.app]
        if not apps:
            sys.exit(f"FATAL: no app with slug '{args.app}' in {APPS_FILE.name}")

    log("=" * 68)
    log("  CRASHLYTICS MONITOR")
    log(f"  {iso(utcnow())}  |  window {args.window_hours}h  |  {len(apps)} app(s)")
    log("=" * 68)

    tokens = TokenProvider()

    log("\nSelf-test (guards against silent false-negatives)...")
    selftest(tokens, apps)
    if args.selftest:
        return 0

    log("\nScanning...")
    state = load_state()
    findings, coverage, coverage_by_app = scan(tokens, apps, args.window_hours, state)
    alerts = worth_alerting(findings)

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        render_markdown(findings, alerts, args.window_hours, coverage), encoding="utf-8"
    )
    log(f"\nCoverage: {coverage['read']} read | {coverage['no_data']} no-data | "
        f"{coverage['unreachable']} unreachable")
    log(f"Report:   {REPORT_FILE}")

    dropped = write_project_status(apps, findings, args.window_hours, coverage_by_app)
    log(f"Per-project: wrote {len(dropped)} .claude/crash-status.md file(s)")

    short = render_short(alerts, args.window_hours, len(findings), coverage)
    log("\n" + short + "\n")

    if alerts or args.force_notify:
        dispatch(alerts, short, args.dry_run)
    else:
        log("  nothing new or critical — staying quiet (use --force-notify to test the pipe)")

    if not args.dry_run:
        save_state(findings)

    return 2 if any(a["severity"] == "critical" for a in alerts) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
