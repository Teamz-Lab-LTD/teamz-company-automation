#!/usr/bin/env python3
"""
build-app-fleet-digest.py — ONE verdict per app, every night, from the store signals
sh/app-fleet-nightly.sh (and hazira's own nightly-app.sh) already pulled.

Why: until 2026-09-05 the growth engine could only see apps through their WEB pages.
It would happily spend a content slot on an app whose users were uninstalling it the
same week, and it could not tell "no ratings" from "no problem". This is the missing
consumer: it reads each app's automation_data and says which of six states the app is
in, so the web queue, the ASO cadence and the owner's to-do list can act on it.

Verdicts, in precedence order (first match wins):
  UNMEASURED         no readable bulk data — says WHICH step failed, never renders a zero
  RETENTION-BLOCKED  uninstalls >= 60% of installs AND active devices flat/shrinking (28d,
                     >= 20 installs), or GA4 D1 < 10%
  CRASH-BLOCKED      user-perceived crash rate above Play's 1.09% bad-behaviour line,
                     or a [CRIT] row in the Crashlytics monitor
  RATINGS-STARVED    fewer than 10 ratings (store listing conversion is capped without them)
  ASO-DUE            signal pull older than 14d, or a rewrite floor (28d iOS / 56d Android) open
  GROW               healthy — worth sending traffic to

Outputs:
  data/app-fleet-verdicts.json   the machine contract (content queue + watchdog read it)
  docs/app-fleet-digest.md       the human table
  docs/app-fleet/<slug>.md       a brief for every app automation cannot fix itself

Honesty rules (same as build-growth-digest.py): Play bulk CSVs lag up to a month and
the digest prints the data_through date beside every number; a missing file is a
finding, not a zero; an app with no GA4 property says NOT MEASURED, not 0%.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

AUT = Path(__file__).resolve().parent.parent
MANIFEST = AUT / "data" / "app-fleet.json"
OUT_JSON = AUT / "data" / "app-fleet-verdicts.json"
OUT_MD = AUT / "docs" / "app-fleet-digest.md"
BRIEF_DIR = AUT / "docs" / "app-fleet"
CRASH_REPORT = AUT / "data" / "crashlytics-monitor-report.md"
CFG = Path.home() / ".config" / "teamzlab"

# --- thresholds (see docstring) --------------------------------------------------------
RETENTION_UNINSTALL_RATIO = 0.60
RETENTION_MIN_INSTALLS = 20
D1_FLOOR = 0.10
CRASH_BAD_BEHAVIOUR_PCT = 1.09
RATINGS_MIN = 10
ASO_SIGNAL_DAYS = 14
ASO_IOS_REWRITE_DAYS = 28
ASO_ANDROID_REWRITE_DAYS = 56
STALE_PULL_HOURS = 30
STALE_DATA_DAYS = 75   # bulk CSVs older than this are too old to judge retention on

# What each verdict does to the web content queue's app-coverage / NEW scoring
# (build-content-queue.py reads this; bounded like the tools RPM weighting).
QUEUE_MULTIPLIER = {
    "GROW": 1.5, "ASO-DUE": 1.0, "UNMEASURED": 1.0,
    "RATINGS-STARVED": 0.8, "RETENTION-BLOCKED": 0.3, "CRASH-BLOCKED": 0.3,
}
VERDICT_ORDER = ["RETENTION-BLOCKED", "CRASH-BLOCKED", "RATINGS-STARVED", "ASO-DUE", "GROW", "UNMEASURED"]


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def load_json(path: Path):
    try:
        return json.loads(path.read_text()), None
    except FileNotFoundError:
        return None, "missing"
    except (json.JSONDecodeError, OSError) as e:
        return None, f"unreadable ({type(e).__name__})"


def _int(v):
    try:
        return int(float(str(v or "0").strip() or 0))
    except ValueError:
        return 0


# --- per-signal readers ------------------------------------------------------------------
def read_bulk(data_dir: Path, pkg: str | None):
    """28-day installs/uninstalls + ratings from the Play bulk-reports pull."""
    if not pkg:
        return None, "no Play package"
    fp = data_dir / f"play-bulk-reports-{pkg.replace('.', '-')}.json"
    d, err = load_json(fp)
    if err:
        return None, f"{fp.name} {err}"
    rows = [r for r in (d.get("installs", {}).get("overview") or []) if (r.get("Date") or "").strip()]
    if not rows:
        missing = d.get("missing_files") or []
        return None, f"no install rows ({len(missing)} bulk files missing)" if missing else "no install rows"
    rows.sort(key=lambda r: r["Date"])
    end = dt.date.fromisoformat(rows[-1]["Date"])
    start = end - dt.timedelta(days=27)
    win = [r for r in rows if start.isoformat() <= r["Date"] <= end.isoformat()]

    def pick(r, primary, fallback):
        v = _int(r.get(primary))
        return v if v else _int(r.get(fallback))

    installs = sum(pick(r, "Daily User Installs", "Install events") for r in win)
    uninstalls = sum(pick(r, "Daily User Uninstalls", "Uninstall events") for r in win)
    # Did the active base actually move? A mature app at steady state has uninstalls ≈
    # installs (hazira: 1053 in / 973 out, 4.47★) and is NOT broken — the ratio alone
    # would call every stable app "retention-blocked". Blocked means the bucket is
    # leaking faster than it fills: high ratio AND a flat-or-shrinking active base.
    active_start = _int(win[0].get("Active Device Installs")) if win else 0
    active_end = _int(win[-1].get("Active Device Installs")) if win else 0
    reviews = d.get("reviews") or []
    stars = [_int(r.get("Star Rating")) for r in reviews]
    stars = [s for s in stars if 1 <= s <= 5]
    summ = d.get("summary") or {}
    return {
        "data_through": end.isoformat(),
        "data_age_days": (dt.date.today() - end).days,
        "window_days": len(win),
        "installs_28d": installs,
        "uninstalls_28d": uninstalls,
        "uninstall_ratio": round(uninstalls / installs, 2) if installs else None,
        "active_devices": _int(rows[-1].get("Active Device Installs")),
        "active_start_28d": active_start,
        "active_delta_28d": active_end - active_start,
        "active_delta_pct": round((active_end - active_start) / active_start, 3) if active_start else None,
        "play_ratings": len(stars),
        "play_avg_star": round(sum(stars) / len(stars), 2) if stars else None,
        "store_conversion": summ.get("store_listing_conversion_rate"),
        "pulled_at": d.get("generated_at"),
    }, None


def read_vitals(data_dir: Path):
    d, err = load_json(data_dir / "vitals.json")
    if err:
        return None, f"vitals.json {err}"
    rows = (d.get("response") or {}).get("rows") or []
    if not rows:
        return None, "vitals: no rows"

    def key(r):
        s = r.get("startTime") or {}
        return (s.get("year", 0), s.get("month", 0), s.get("day", 0))

    newest = max(rows, key=key)
    out = {"date": "%04d-%02d-%02d" % key(newest)}
    for m in newest.get("metrics") or []:
        val = (m.get("decimalValue") or {}).get("value")
        if m.get("metric") == "userPerceivedCrashRate":
            out["user_perceived_crash_pct"] = round(float(val) * 100, 3) if val is not None else None
        elif m.get("metric") == "crashRate":
            out["crash_pct"] = round(float(val) * 100, 3) if val is not None else None
        elif m.get("metric") == "distinctUsers":
            out["distinct_users"] = _int(val)
    return out, None


def read_status(data_dir: Path):
    d, err = load_json(data_dir / "nightly-app-status.json")
    if err:
        return None, f"nightly-app-status.json {err}"
    age_h = None
    try:
        fin = dt.datetime.strptime(d["finished_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        age_h = round((utcnow() - fin).total_seconds() / 3600, 1)
    except (KeyError, ValueError):
        pass
    steps = d.get("steps") or {}
    return {
        "label": d.get("label"),
        "age_hours": age_h,
        "failed_steps": sorted(k for k, v in steps.items() if v == "failed"),
        "ok_steps": sorted(k for k, v in steps.items() if v == "ok"),
    }, None


def read_ios_reviews(data_dir: Path, asc: str | None):
    if not asc:
        return None, "no App Store id"
    fp = data_dir / f"aso-reviews-{asc}.json"
    d, err = load_json(fp)
    if err:
        return None, f"{fp.name} {err}"
    ratings = []

    def walk(o):
        if isinstance(o, dict):
            if "rating" in o and isinstance(o.get("rating"), (int, float, str)):
                try:
                    ratings.append(int(float(o["rating"])))
                except ValueError:
                    pass
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(d)
    ratings = [r for r in ratings if 1 <= r <= 5]
    return {"ios_reviews": len(ratings),
            "ios_avg_star": round(sum(ratings) / len(ratings), 2) if ratings else None}, None


def refresh_ages(data_dir: Path, repo: Path):
    """Days since each /aso-refresh sentinel. Kit games keep the sentinels at kit level."""
    out = {}
    for name in ("signal", "android_rewrite", "ios_rewrite"):
        val = None
        for base in (data_dir, repo / "automation_data"):
            fp = base / f".last_refresh.{name}"
            if fp.exists():
                try:
                    ts = int(fp.read_text().strip() or 0)
                    if ts > 0:
                        val = (utcnow() - dt.datetime.fromtimestamp(ts, dt.timezone.utc)).days
                except ValueError:
                    pass
                break
        out[name] = val
    return out


def crashlytics_critical(slugs: list[str]):
    """[CRIT] rows in the 'Needs attention' table naming any of this app's monitor slugs."""
    if not slugs or not CRASH_REPORT.exists():
        return []
    text = CRASH_REPORT.read_text()
    m = re.search(r"## Needs attention(.*?)(?:\n## |\Z)", text, re.S)
    if not m:
        return []
    hits = []
    for line in m.group(1).splitlines():
        if not line.startswith("|") or "[CRIT]" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 7 and cells[1] in slugs:
            hits.append(cells[6][:80])
    return hits


_GA4_TOKEN = None


def ga4_token():
    global _GA4_TOKEN
    if _GA4_TOKEN:
        return _GA4_TOKEN
    t = json.loads((CFG / "analytics-token.json").read_text())
    data = urllib.parse.urlencode({
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    _GA4_TOKEN = json.load(urllib.request.urlopen(
        urllib.request.Request(t.get("token_uri", "https://oauth2.googleapis.com/token"), data=data),
        timeout=30))["access_token"]
    return _GA4_TOKEN


def ga4_d1(property_id: str | None):
    """D1 retention for users first seen 33..5 days ago. None + reason when unknowable."""
    if not property_id:
        return None, "no GA4 property in manifest"
    today = dt.date.today()
    body = {
        "dimensions": [{"name": "cohort"}, {"name": "cohortNthDay"}],
        "metrics": [{"name": "cohortActiveUsers"}],
        "cohortSpec": {
            "cohorts": [{"name": "c", "dimension": "firstSessionDate",
                         "dateRange": {"startDate": (today - dt.timedelta(days=33)).isoformat(),
                                       "endDate": (today - dt.timedelta(days=5)).isoformat()}}],
            "cohortsRange": {"granularity": "DAILY", "startOffset": 0, "endOffset": 1},
        },
    }
    try:
        req = urllib.request.Request(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {ga4_token()}", "Content-Type": "application/json"})
        res = json.load(urllib.request.urlopen(req, timeout=60))
    except Exception as e:  # noqa: BLE001
        return None, f"GA4 {type(e).__name__}"
    day = {}
    for r in res.get("rows", []):
        nth = r["dimensionValues"][1]["value"]
        day[nth] = day.get(nth, 0) + _int(r["metricValues"][0]["value"])
    d0, d1 = day.get("0000", 0), day.get("0001", 0)
    if d0 < 20:
        return None, f"GA4 cohort too small ({d0} users)"
    return round(d1 / d0, 3), None


# --- verdict ------------------------------------------------------------------------------
def judge(app: dict, f: dict):
    bulk, vit, ios = f.get("bulk"), f.get("vitals"), f.get("ios")
    hooks = app.get("hooks") or {}
    slug = app["slug"]
    android = bool(app.get("play_package"))
    measured = bulk is not None or (not android and ios is not None)
    if not measured:
        why = f["errors"].get("bulk") or f["errors"].get("ios") or "no data"
        st = f.get("status")
        if st and st["failed_steps"]:
            why += f"; failed steps: {', '.join(st['failed_steps'])}"
        return ("UNMEASURED", why,
                f"Run `bash sh/app-fleet-nightly.sh --only={slug}` and read logs/app-fleet/{slug}/steps/.")

    if bulk and bulk["installs_28d"] >= RETENTION_MIN_INSTALLS and bulk["uninstall_ratio"] is not None \
            and bulk["uninstall_ratio"] >= RETENTION_UNINSTALL_RATIO and bulk["data_age_days"] <= STALE_DATA_DAYS \
            and (bulk["active_delta_28d"] or 0) <= 0:
        return ("RETENTION-BLOCKED",
                f"{bulk['uninstalls_28d']} uninstalls vs {bulk['installs_28d']} installs "
                f"({bulk['uninstall_ratio']:.0%}) and active devices {bulk['active_delta_28d']:+d} "
                f"in the 28d to {bulk['data_through']}",
                f"Stop buying traffic for it. Fix the first session + the D1 return hook "
                f"(push: {hooks.get('push') or 'unknown'}). Measure D1 in GA4 "
                f"({'property ' + app['ga4_property_id'] if app.get('ga4_property_id') else 'NONE — add a property'}).")
    if f.get("d1") is not None and f["d1"] < D1_FLOOR:
        return ("RETENTION-BLOCKED", f"GA4 D1 retention {f['d1']:.0%} (floor {D1_FLOOR:.0%})",
                f"Fix the first session before spending anything upstream (push: {hooks.get('push') or 'unknown'}).")

    crash = (vit or {}).get("user_perceived_crash_pct")
    if crash is not None and crash > CRASH_BAD_BEHAVIOUR_PCT:
        return ("CRASH-BLOCKED", f"user-perceived crash rate {crash}% on {vit['date']} (Play bad-behaviour line {CRASH_BAD_BEHAVIOUR_PCT}%)",
                "Fix the live-version crash first — Play demotes above this line. Cross-check Crashlytics; vitals only sees opted-in devices.")
    if f.get("crash_crit"):
        return ("CRASH-BLOCKED", f"Crashlytics [CRIT]: {f['crash_crit'][0]}",
                "Fix the critical Crashlytics issue before any growth work (data/crashlytics-monitor-report.md).")

    ratings = (bulk or {}).get("play_ratings", 0) + (ios or {}).get("ios_reviews", 0)
    if ratings < RATINGS_MIN:
        return ("RATINGS-STARVED", f"{ratings} ratings/reviews on record (need {RATINGS_MIN}+ for social proof)",
                f"Earn ratings before chasing installs. Review prompt: {hooks.get('review_prompt') or 'unknown — audit the app'}. "
                f"Fire it at the peak moment (a win, a completed task), never on launch.")

    ages = f["refresh"]
    due = []
    if ages["signal"] is None:
        due.append("never signal-pulled")
    elif ages["signal"] > ASO_SIGNAL_DAYS:
        due.append(f"signal {ages['signal']}d old")
    if android and (ages["android_rewrite"] is None or ages["android_rewrite"] > ASO_ANDROID_REWRITE_DAYS):
        due.append("Android rewrite floor open" + (f" ({ages['android_rewrite']}d)" if ages["android_rewrite"] is not None else " (never)"))
    if app.get("asc_app_id") and (ages["ios_rewrite"] is None or ages["ios_rewrite"] > ASO_IOS_REWRITE_DAYS):
        due.append("iOS rewrite floor open" + (f" ({ages['ios_rewrite']}d)" if ages["ios_rewrite"] is not None else " (never)"))
    if due:
        return ("ASO-DUE", "; ".join(due), f"`/aso-refresh {slug}` — the skill picks SIGNAL_ONLY vs FULL_REWRITE from the sentinels.")

    lp = app.get("landing_path")
    return ("GROW", "no blocker found in the signals we have",
            f"Give it the web slots: a problem-intent page/post feeding {lp}." if lp else
            "Give it a landing page + a problem-intent post (it has none).")


def collect(app: dict):
    data_dir, repo = Path(app["data_dir"]), Path(app["repo"])
    f = {"errors": {}}
    f["bulk"], err = read_bulk(data_dir, app.get("play_package"))
    if err:
        f["errors"]["bulk"] = err
    f["vitals"], err = read_vitals(data_dir)
    if err:
        f["errors"]["vitals"] = err
    f["status"], err = read_status(data_dir)
    if err:
        f["errors"]["status"] = err
    f["ios"], err = read_ios_reviews(data_dir, app.get("asc_app_id"))
    if err:
        f["errors"]["ios"] = err
    f["refresh"] = refresh_ages(data_dir, repo)
    f["crash_crit"] = crashlytics_critical(app.get("crashlytics_slugs") or [])
    f["d1"], err = ga4_d1(app.get("ga4_property_id"))
    if err:
        f["errors"]["d1"] = err
    return f


def brief(app: dict, verdict: str, reason: str, action: str, f: dict) -> str:
    b, v = f.get("bulk") or {}, f.get("vitals") or {}
    hooks = app.get("hooks") or {}
    L = [f"# {app['name']} — {verdict}", "",
         f"_Generated {dt.date.today().isoformat()} by build-app-fleet-digest.py. Overwritten nightly; do not edit._", "",
         f"**Why:** {reason}", "", f"**Do this first:** {action}", "",
         "## Numbers behind it", "", "| signal | value |", "|---|---|"]
    if b:
        L += [f"| installs (28d to {b['data_through']}) | {b['installs_28d']} |",
              f"| uninstalls (same window) | {b['uninstalls_28d']} |",
              f"| active devices | {b['active_devices']} ({b.get('active_delta_28d', 0):+d} over the window) |",
              f"| Play ratings on record | {b['play_ratings']} (avg {b['play_avg_star']}) |",
              f"| store listing conversion | {b['store_conversion']:.1%} |" if b.get("store_conversion") is not None else "| store listing conversion | n/a |"]
    if f.get("ios"):
        L.append(f"| App Store reviews on record | {f['ios']['ios_reviews']} (avg {f['ios']['ios_avg_star']}) |")
    if v:
        L.append(f"| user-perceived crash rate ({v.get('date')}) | {v.get('user_perceived_crash_pct')}% |")
    L.append(f"| GA4 D1 retention | {f['d1']:.0%} |" if f.get("d1") is not None else f"| GA4 D1 retention | not measured — {f['errors'].get('d1')} |")
    L += ["", "## What the app already has", "",
          f"- Review prompt: {hooks.get('review_prompt') or 'not audited'}",
          f"- Push / return hook: {hooks.get('push') or 'not audited'}",
          f"- Landing page: {app.get('landing_path') or 'NONE'}", "",
          "## Rules", "",
          "- The web nightly weights this app at ×%.1f until the verdict changes." % QUEUE_MULTIPLIER[verdict],
          "- Nothing here edits the app. This is the owner's to-do, written from data, not memory."]
    return "\n".join(L) + "\n"


def main():
    m, err = load_json(MANIFEST)
    if err:
        sys.exit(f"FATAL: {MANIFEST} {err}")
    rows = []
    for app in m["apps"]:
        f = collect(app)
        verdict, reason, action = judge(app, f)
        rows.append({
            "slug": app["slug"], "name": app["name"], "verdict": verdict, "reason": reason,
            "next_action": action, "queue_multiplier": QUEUE_MULTIPLIER[verdict],
            "landing_path": app.get("landing_path"), "platforms": app.get("platforms"),
            "facts": {"bulk": f.get("bulk"), "vitals": f.get("vitals"), "ios": f.get("ios"),
                      "d1": f.get("d1"), "refresh_age_days": f["refresh"],
                      "crashlytics_critical": f.get("crash_crit"), "pull_status": f.get("status"),
                      "errors": f["errors"]},
        })
        if verdict in ("RETENTION-BLOCKED", "CRASH-BLOCKED", "RATINGS-STARVED"):
            BRIEF_DIR.mkdir(parents=True, exist_ok=True)
            (BRIEF_DIR / f"{app['slug']}.md").write_text(brief(app, verdict, reason, action, f))

    rows.sort(key=lambda r: (VERDICT_ORDER.index(r["verdict"]), -((r["facts"]["bulk"] or {}).get("installs_28d") or 0)))
    counts = {v: sum(1 for r in rows if r["verdict"] == v) for v in VERDICT_ORDER}
    stale_pulls = [r["slug"] for r in rows
                   if (r["facts"]["pull_status"] or {}).get("age_hours") is None
                   or (r["facts"]["pull_status"] or {}).get("age_hours", 0) > STALE_PULL_HOURS]

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "generated_at": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": counts, "stale_pulls": stale_pulls, "apps": rows,
    }, indent=2) + "\n")

    L = [f"# App Fleet Digest — {dt.date.today().isoformat()}", "",
         "One verdict per app from Play bulk reports (installs / uninstalls / ratings — Google publishes "
         "these MONTHLY, the `data through` column is the truth of how fresh each row is), Play vitals, "
         "App Store reviews, the Crashlytics monitor and the /aso-refresh sentinels.", "",
         "| " + " | ".join(f"{v} {counts[v]}" for v in VERDICT_ORDER) + " |", ""]
    if stale_pulls:
        L += [f"⚠️ **{len(stale_pulls)} app(s) with no pull in {STALE_PULL_HOURS}h**: {', '.join(stale_pulls)} — "
              "their rows below are only as fresh as their last run.", ""]
    L += ["| app | verdict | installs 28d | uninstalls | ratio | active (Δ28d) | ratings | crash % | ASO signal | data through | do this |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        b, v, i = r["facts"]["bulk"] or {}, r["facts"]["vitals"] or {}, r["facts"]["ios"] or {}
        ratings = (b.get("play_ratings") or 0) + (i.get("ios_reviews") or 0)
        ratio = f"{b['uninstall_ratio']:.0%}" if b.get("uninstall_ratio") is not None else "—"
        sig = r["facts"]["refresh_age_days"]["signal"]
        L.append(f"| {r['slug']} | **{r['verdict']}** | {b.get('installs_28d', '—')} | {b.get('uninstalls_28d', '—')} | {ratio} | "
                 f"{(str(b['active_devices']) + ' (' + format(b.get('active_delta_28d', 0), '+d') + ')') if b else '—'} | {ratings if (b or i) else '—'} | "
                 f"{v.get('user_perceived_crash_pct', '—')} | {str(sig) + 'd' if sig is not None else 'never'} | "
                 f"{b.get('data_through', '—')} | {r['next_action'][:110]} |")
    un = [r for r in rows if r["verdict"] == "UNMEASURED"]
    if un:
        L += ["", "## ⚠️ UNMEASURED — unknown, not zero", ""]
        L += [f"- **{r['slug']}** — {r['reason']}" for r in un]
    due = [r for r in rows if r["verdict"] == "ASO-DUE"]
    if due:
        L += ["", "## ASO due (paste one line; the skill decides signal vs rewrite)", ""]
        L += [f"- `/aso-refresh {r['slug']}` — {r['reason']}" for r in due]
    blocked = [r for r in rows if r["verdict"] in ("RETENTION-BLOCKED", "CRASH-BLOCKED", "RATINGS-STARVED")]
    if blocked:
        L += ["", "## Needs a human (briefs in docs/app-fleet/)", ""]
        L += [f"- **{r['slug']}** ({r['verdict']}): {r['next_action']}" for r in blocked]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\n  wrote {OUT_JSON}\n  wrote {OUT_MD}")


if __name__ == "__main__":
    main()
