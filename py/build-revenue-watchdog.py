#!/usr/bin/env python3
"""
Nightly REVENUE watchdog. Answers one question the rest of the engine cannot:
"did one of the pages that actually pays me just fall off a cliff?"

Why this exists, in numbers measured 2026-08-13:

    $252.04 total ad revenue / 30d across 4,126 earning pages
    $ 78.64 (31.2%)  /football/premier-league-table-predictor/   <- ONE page
    top  5 pages = 53.8% of revenue
    top 20 pages = 74.9% of revenue
    /football/   = 51.4% of revenue

Nothing in this system watched any of that. build-growth-watchdog.py checks
build exit codes, file staleness, push failures — real signals, but all of
them are about whether the MACHINE ran, never about whether the BUSINESS is
still earning. If the predictor lost 80% of its traffic tonight, every
monitor in this repo would report green and the owner would find out
whenever he next opened AdSense.

The owner drives Uber and has said three times he cannot check daily. This
is the check.

WHAT IT COMPARES
Four consecutive 7-day buckets, W0 (newest, ending D-2) back to W3:

    W0 = D-8 .. D-2     W1 = D-15 .. D-9
    W2 = D-22 .. D-16   W3 = D-29 .. D-23

D-2, not yesterday: GA4 per-page ad revenue is not complete until ~48h, so a
D-1 read shows a fake drop on every page every night. Whole 7-day buckets so
weekday seasonality cancels instead of being mistaken for a decline.

CLIFF vs FADE — the reason for four buckets instead of two
A two-window check cannot tell "Google dropped this page overnight" from
"the World Cup ended a month ago and this page is winding down as expected".
Both look like a big drop against a 28-day baseline. On this site's very
first run that mattered immediately: /football/how-to-watch-fifa-world-cup-
2026-in-germany/ read as -100%, which is true and completely unactionable —
the tournament finished on 2026-07-19.

Firing a red alert on that is how a monitor gets ignored, and an ignored
monitor is worth exactly as much as no monitor. So:

    FADE  — the decline was already underway BEFORE the newest week
            (W1 is materially below W3). Reported, never alerted.
    CLIFF — the earlier weeks were steady and the newest week collapsed.
            This is the one that wakes the owner.

A fade is still printed and still lands in the JSON, because "this page is
quietly dying" is worth knowing at the weekly review even though it is not
worth a 2am message.

    SEASONAL — the page earns in bursts, so no $/month run rate exists to be
            "at risk". Reported, never alerted, and NEVER given a $/month
            figure.

WHY SEASONAL EXISTS (added 2026-09-04, from a false alarm I relayed)
On 2026-09-04 this watchdog reported `/football/premier-league-table-predictor/`
down 84.7%, "~$192.46/month at risk", and /growth led with it. The number was
fiction. That page LAUNCHED 2026-07-12 and its entire lifetime earnings are
$197: $22.62 in July, $173.35 in August, $0.96 in September. It has never had
a normal month. The alert took the kickoff week's $/day and multiplied by 30.

The bug is structural, not a threshold: every window this file reads is inside
29 days, so it cannot tell a year-round earner from a page that launched into
one event. FADE could not catch it either — a fade needs the slide to have
started before the newest week, and this page was still climbing (W3 $5.72 ->
W1 $7.57) right up to the cliff.

This is [[feedback_a_spike_must_not_set_the_baseline]] one layer up. That
lesson was applied to the CLICK detectors (build-gsc-anomalies.py got a 28-day
baseline, build-football-fortress.py got a 75th-percentile base CTR). Nobody
applied it here. Fixing one consumer of a pattern does not fix the others.

THE TEST, AND WHY 70%
One extra GA4 pull gives each candidate page its trailing-180d weekly revenue.
If its best 4 CONSECUTIVE weeks hold >= TEAMZ_REV_SEASONAL_PCT of that 180 days,
a x30 extrapolation is unsound and we refuse to print one. Measured across the
top 25 earners on 2026-09-04 (peak-4-week share of 180d revenue):

    96.9  /football/fifa-world-cup-2026-best-third-place-calculator/
    86.3  /football/how-to-watch-fifa-world-cup-2026-in-bangladesh/
    86.0  /football/premier-league-table-predictor/
    84.8  /football/how-to-watch-fifa-world-cup-2026-in-germany/
    72.6  /tools/signature-analyzer/
    71.9  /football/fifa-world-cup-2026-bracket-maker/
    70.3  /ar/ar-measure-tape/
    ----- 70% cut -----
    65.4  /football/how-to-watch-fifa-world-cup-2026-in-france/
    63.6  /grooming/attractiveness-quiz/
    ...
    54.5  /football/ucl-bracket-predictor/
    49.6  /games/arrow-escape-3d/
    46.0  /tools/ai-emotion-detector/
    35.3  /work/probation-period-calculator/

Everything above the line is an event page; nothing genuinely year-round comes
close. A count of earning weeks was tried as a second condition and REJECTED —
ANDing it dropped the World Cup pages (13 and 16 earning weeks) that the
tournament calendar makes unambiguously seasonal. Concentration alone separates.

A brand-new page needs no special case: with only a few weeks of history its
peak-4-week share is ~100%, so "too young to price" falls out of the same test.

IF THE HISTORY PULL FAILS the page stays a CLIFF and the alert says the
concentration could not be checked. Failing into silence would turn a broken
API call into a muted revenue alarm, which is strictly worse than a noisy one.

WHAT IT WILL NOT DO
    - It will not fire on a page earning pennies. A $0.20/day page halving is
      $3/month and not worth waking anyone. MIN_DAILY_USD is the floor.
    - It will not report "no drop" when it could not read GA4. A watchdog that
      renders a failed pull as all-clear is the exact bug this repo has been
      bitten by before (GA4 readonly token, the AdSense funnel, the pre-push
      gate). Unreachable is its own state, it is LOUD, and it is in the JSON.
    - It will not silently cap coverage. If the top-N list is truncated the
      count is printed.

Always writes data/revenue-watchdog-status.json, clean night or not, so
"nothing dropped" and "the watchdog never ran" are never the same shape on
disk.

COVERAGE — why the floor is $0.10/day and not higher
Revenue here is brutally concentrated (top 1 page = 31%, top 20 = 75%), so a
tight floor still covers most of the money, and each extra page bought costs
noise. Measured on 2026-08-13:

    $0.30/day floor, top 15  ->   4 pages =  46.5% of revenue
    $0.15/day floor, top 20  ->  11 pages =  62.0%
    $0.10/day floor, top 25  ->  15 pages =  68.1%   <- chosen
    $0.05/day floor, top 30  ->  23 pages =  75.1%

$0.05/day is $1.50/month; a 40% fall there is $0.60/month, which is not worth
a message. Anything under the floor is still covered in aggregate by the
whole-site check, so nothing is unwatched — it is watched collectively rather
than individually. The share actually covered is printed and stored every run
so a tightened floor can never quietly masquerade as full coverage.

PERCENTAGE IS NOT IMPACT — the second filter
A 40% fall on a $3/month page is $1.20/month. Waking the owner for that is
the same mistake as alerting on seasonal fade, and the first tuned run made
it: three alerts fired worth $2.79, $2.03 and $2.19/month while the page
that carries 31% of the business was fine.

So a cliff must clear BOTH tests before it becomes a message:
    - it fell at least TEAMZ_REV_DROP_PCT, and
    - the fall is worth at least TEAMZ_REV_MIN_IMPACT per month.

Everything under the impact floor is still detected, still classified and
still written to the JSON as "minor" — it just does not buzz a phone. The
count of those is printed, so quiet never means unexamined.

Env overrides:
    TEAMZ_REV_DROP_PCT    default 40   per-page drop % that alerts
    TEAMZ_REV_SITE_PCT    default 25   whole-site drop % that alerts
    TEAMZ_REV_MIN_DAILY   default 0.10 min baseline $/day for a page to count
    TEAMZ_REV_MIN_IMPACT  default 10   min $/month at risk before it notifies
    TEAMZ_REV_TOP_N       default 25   how many top earners to watch
    TEAMZ_REV_SEASONAL_PCT default 70  peak-4-week share of 180d revenue above
                                       which a page gets no $/month figure
"""
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import teamz_notify as notify
except Exception:  # noqa: BLE001
    notify = None

OUT = HERE.parent / "data" / "revenue-watchdog-status.json"

DROP_PCT = float(os.getenv("TEAMZ_REV_DROP_PCT", "40"))
SITE_PCT = float(os.getenv("TEAMZ_REV_SITE_PCT", "25"))
MIN_DAILY = float(os.getenv("TEAMZ_REV_MIN_DAILY", "0.10"))
MIN_IMPACT = float(os.getenv("TEAMZ_REV_MIN_IMPACT", "10"))
TOP_N = int(os.getenv("TEAMZ_REV_TOP_N", "25"))
SEASONAL_PCT = float(os.getenv("TEAMZ_REV_SEASONAL_PCT", "70"))

# Scope: the properties that earn ad revenue. tools is ~90% of the business;
# the others are here so a future shift shows up rather than being invisible
# because nobody updated a list.
PROPERTIES = ["teamzlab-tools", "teamz-lab-generic-landing-pages"]


def _load_digest_helpers():
    """Reuse build-growth-digest's GA4 auth + report call rather than forking it.

    Imported by path because the filename has dashes. build-growth-digest.py
    guards its own main() behind __name__, so importing it runs constants and
    defs only.
    """
    spec = importlib.util.spec_from_file_location(
        "_bgd_helpers", HERE / "build-growth-digest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pull(mod, tok, prop_id, start, end):
    """-> {pagePath: revenue} for the window, or None if the pull failed.

    None and {} mean different things and must stay different: None is "GA4
    did not answer", {} is "GA4 answered, nobody earned anything".
    """
    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": "pagePath"}],
        "metrics": [{"name": "totalAdRevenue"}],
        "limit": 100000,
    }
    try:
        res = mod._ga4_report(prop_id, tok, body)
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR: GA4 pull failed ({start}..{end}): {type(e).__name__}: {e}",
              file=sys.stderr)
        return None
    if res is None:
        return None
    out = {}
    for row in res.get("rows", []) or []:
        path = row["dimensionValues"][0]["value"]
        out[path] = out.get(path, 0.0) + float(row["metricValues"][0]["value"])
    return out


def concentration(mod, tok, prop_id, paths):
    """-> {path: {"peak4wk_share_pct", "earning_weeks", "total_180d"}} or None.

    None means GA4 did not answer and the caller MUST keep alerting rather than
    assume the pages are seasonal — see the docstring at the top of this file.
    Only the candidate pages are requested (an inListFilter), so a clean night
    never pays for this call at all.
    """
    if not paths:
        return {}
    body = {
        "dateRanges": [{"startDate": "180daysAgo", "endDate": "2daysAgo"}],
        "dimensions": [{"name": "pagePath"}, {"name": "yearWeek"}],
        "metrics": [{"name": "totalAdRevenue"}],
        "dimensionFilter": {"filter": {"fieldName": "pagePath",
                                       "inListFilter": {"values": list(paths)}}},
        "limit": 100000,
    }
    try:
        res = mod._ga4_report(prop_id, tok, body)
    except Exception as e:  # noqa: BLE001
        print(f"  WARN: 180d concentration pull failed: {type(e).__name__}: {e}",
              file=sys.stderr)
        return None
    if res is None:
        return None

    by_page = {}
    weeks_seen = set()
    for row in res.get("rows", []) or []:
        path = row["dimensionValues"][0]["value"]
        week = row["dimensionValues"][1]["value"]
        val = float(row["metricValues"][0]["value"])
        if val <= 0:
            continue
        weeks_seen.add(week)
        by_page.setdefault(path, {})[week] = by_page.setdefault(path, {}).get(week, 0.0) + val

    # One shared week axis so a page's gap weeks count as zero rather than
    # closing up — four ADJACENT weeks is the whole point of the measure.
    axis = sorted(weeks_seen)
    out = {}
    for path, wk in by_page.items():
        total = sum(wk.values())
        if total <= 0:
            continue
        series = [wk.get(w, 0.0) for w in axis]
        window = 4 if len(series) >= 4 else len(series)
        peak = max(sum(series[i:i + window])
                   for i in range(max(1, len(series) - window + 1)))
        out[path] = {
            "peak4wk_share_pct": round(100.0 * peak / total, 1),
            "earning_weeks": len(wk),
            "total_180d": round(total, 2),
        }
    return out


# Four 7-day buckets, newest first. GA4 relative dates are inclusive on both
# ends, so "8daysAgo".."2daysAgo" is exactly 7 days.
BUCKETS = [("8daysAgo", "2daysAgo"), ("15daysAgo", "9daysAgo"),
           ("22daysAgo", "16daysAgo"), ("29daysAgo", "23daysAgo")]

# How much of the pre-existing decline must already have happened for a drop
# to count as a fade rather than a cliff. W1 (the week BEFORE the newest one)
# being this far under W3 means the slide started before the window we are
# alerting on, so the newest week is a continuation, not an event.
FADE_PRIOR_PCT = 25.0


def check_property(mod, tok, repo):
    prop_id = mod.GA4_PROPERTY.get(repo)
    if not prop_id:
        return {"state": "unreachable", "why": f"no GA4 property id mapped for {repo}"}

    weeks = []
    for start, end in BUCKETS:
        w = pull(mod, tok, prop_id, start, end)
        if w is None:
            return {"state": "unreachable",
                    "why": "GA4 report call failed — this is NOT a clean night"}
        weeks.append({k: v / 7.0 for k, v in w.items()})  # $/day within the week
    w0, w1, w2, w3 = weeks

    def base_of(path):
        """Baseline = max(3-week mean, last week).

        A plain trailing mean silently unprotects the fastest-growing pages,
        which are exactly the ones carrying the business. Measured here on
        2026-08-13, the page holding 31% of all revenue:

            /football/premier-league-table-predictor/
            W3 $0.27 -> W2 $1.77 -> W1 $3.46 -> W0 $5.72 per day

        Its 3-week mean is $1.83/day against a current $5.72/day. A crash from
        $5.72 to $2.00 — losing about $110/month, the single worst thing that
        could happen to this business — still reads as ABOVE a $1.83 baseline,
        so a mean-only check would have said nothing at all.

        Taking the greater of the mean and last week fixes that: for a steady
        page W1 is roughly the mean so nothing changes, for a rising page the
        higher recent level is what gets defended, and for a page already
        sliding the mean is the larger of the two, which keeps the test
        conservative and lets the fade classifier handle it.
        """
        mean3 = (w1.get(path, 0.0) + w2.get(path, 0.0) + w3.get(path, 0.0)) / 3.0
        return max(mean3, w1.get(path, 0.0))

    site_recent = sum(w0.values())
    site_base = (sum(w1.values()) + sum(w2.values()) + sum(w3.values())) / 3.0

    # A property that has never earned ad money is not a drop and not a
    # failure — it is a third thing, and collapsing it into either one is how
    # a monitor starts lying. apps.teamzlab.com runs no ad units today.
    if site_base == 0.0 and site_recent == 0.0:
        return {"state": "no-ad-revenue",
                "why": "GA4 reports no ad revenue on this property in the last 29 days"}

    # Rank by baseline earnings, then drop anything too small to be worth a
    # message. Coverage is reported so a tight floor can never be mistaken for
    # "we are watching everything".
    ranked = sorted({p: base_of(p) for p in set(w1) | set(w2) | set(w3)}.items(),
                    key=lambda kv: -kv[1])[:TOP_N]
    watch = [(p, d) for p, d in ranked if d >= MIN_DAILY]
    covered = sum(d for _, d in watch)

    cliffs, fades, minor, seasonal = [], [], [], []
    candidates = []
    for path, was in watch:
        now = w0.get(path, 0.0)
        pct = 100.0 * (was - now) / was if was else 0.0
        if pct < DROP_PCT:
            continue
        prior = w3.get(path, 0.0)
        prior_pct = 100.0 * (prior - w1.get(path, 0.0)) / prior if prior else 0.0
        row = {
            "page": path,
            "was_daily": round(was, 2),
            "now_daily": round(now, 2),
            "drop_pct": round(pct, 1),
            "monthly_at_risk": round((was - now) * 30, 2),
            "weekly_daily": [round(w.get(path, 0.0), 2) for w in (w3, w2, w1, w0)],
            "prior_decline_pct": round(prior_pct, 1),
        }
        if prior_pct >= FADE_PRIOR_PCT:
            fades.append(row)          # already declining before the newest week
        else:
            candidates.append(row)

    # The 180-day pull happens only for pages that would otherwise become a
    # cliff or a minor, so a night where nothing dropped costs one fewer GA4
    # call than before this check existed.
    conc = concentration(mod, tok, prop_id, [r["page"] for r in candidates])
    conc_state = "not-needed" if not candidates else ("unreachable" if conc is None else "ok")

    for row in candidates:
        c = (conc or {}).get(row["page"])
        if c is None:
            # Either GA4 refused, or the page has no 180-day history at all.
            # Both mean "unknown", and unknown keeps the LOUD path: a broken
            # pull must never mute a revenue alarm.
            row["run_rate_reliable"] = None
            row["run_rate_note"] = ("concentration could not be checked — "
                                    + ("GA4 did not answer" if conc is None
                                       else "no 180d revenue history for this page"))
        else:
            row.update(c)
            row["run_rate_reliable"] = c["peak4wk_share_pct"] < SEASONAL_PCT
            if not row["run_rate_reliable"]:
                # A x30 extrapolation of a burst is fiction. Refuse to invent
                # one rather than print a smaller lie.
                row["monthly_at_risk"] = None
                row["run_rate_note"] = (
                    f"seasonal — {c['peak4wk_share_pct']}% of this page's last 180 days "
                    f"of revenue (${c['total_180d']}) landed in its best 4 weeks, so it "
                    f"has no monthly run rate to be 'at risk'")
                seasonal.append(row)
                continue
        if row["monthly_at_risk"] is not None and row["monthly_at_risk"] < MIN_IMPACT:
            minor.append(row)
        else:
            cliffs.append(row)

    site_drop = 100.0 * (site_base - site_recent) / site_base if site_base else 0.0

    return {
        "state": "ok",
        "site_daily_baseline": round(site_base, 2),
        "site_daily_recent": round(site_recent, 2),
        "site_drop_pct": round(site_drop, 1),
        "site_alert": site_drop >= SITE_PCT,
        "pages_watched": len(watch),
        "pages_below_min_daily": len(ranked) - len(watch),
        "watched_revenue_share_pct": round(100.0 * covered / site_base, 1) if site_base else 0.0,
        # Recorded so /growth can show the concentration without re-querying GA4.
        # Concentration IS the risk here and it belongs where the owner looks:
        # a top page at 31% is a different business from a top page at 6%, and
        # only one of those is worth losing sleep over.
        "top_pages": [
            {"page": p,
             "daily": round(w0.get(p, 0.0), 2),
             "share_pct": round(100.0 * w0.get(p, 0.0) / site_recent, 1) if site_recent else 0.0}
            for p, _ in sorted(w0.items(), key=lambda kv: -kv[1])[:5]
        ],
        "cliffs": cliffs,
        "fades": fades,
        "minor": minor,
        "seasonal": seasonal,
        # Distinguishes "checked, nothing seasonal" from "could not check".
        "concentration_state": conc_state,
    }


def main():
    try:
        mod = _load_digest_helpers()
        tok = mod.ga4_token()
    except Exception as e:  # noqa: BLE001
        # Cannot read anything at all. Say so on disk and on screen; do not
        # exit 0 quietly pretending the night was clean.
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "state": "unreachable",
            "why": f"GA4 auth failed: {type(e).__name__}: {e}",
        }, indent=2))
        print(f"UNREACHABLE: GA4 auth failed — {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    report = {repo: check_property(mod, tok, repo) for repo in PROPERTIES}

    alerts, notes, seasonal_notes = [], [], []
    for repo, r in report.items():
        if r["state"] == "unreachable":
            alerts.append(f"{repo}: COULD NOT CHECK REVENUE — {r['why']}")
            continue
        if r["state"] == "no-ad-revenue":
            continue
        if r["site_alert"]:
            alerts.append(
                f"{repo}: whole site down {r['site_drop_pct']}% "
                f"(${r['site_daily_baseline']}/day -> ${r['site_daily_recent']}/day)")
        for d in r["cliffs"]:
            # An unchecked concentration still alerts, but it must not present
            # its $/month as verified when nothing verified it.
            caveat = ("" if d.get("run_rate_reliable")
                      else f" [{d.get('run_rate_note', 'run rate unverified')}]")
            alerts.append(
                f"{repo}: {d['page']} down {d['drop_pct']}% "
                f"(${d['was_daily']}/day -> ${d['now_daily']}/day, "
                f"~${d['monthly_at_risk']}/mo at risk){caveat}")
        for d in r.get("seasonal", []):
            seasonal_notes.append(
                f"{repo}: {d['page']} down {d['drop_pct']}% "
                f"(${d['was_daily']}/day -> ${d['now_daily']}/day) — "
                f"{d['run_rate_note']}")
        for d in r["fades"]:
            notes.append(
                f"{repo}: {d['page']} fading — weekly $/day "
                f"{' -> '.join(str(x) for x in d['weekly_daily'])} "
                f"(~${d['monthly_at_risk']}/mo below its old rate)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "ran_at": datetime.now().isoformat(timespec="seconds"),
        "window": {"recent": "7d ending D-2", "baseline": "28d ending D-9"},
        "thresholds": {"page_drop_pct": DROP_PCT, "site_drop_pct": SITE_PCT,
                       "min_daily_usd": MIN_DAILY, "top_n": TOP_N,
                       "seasonal_peak4wk_pct": SEASONAL_PCT},
        "properties": report,
        "alert_count": len(alerts),
        "alerts": alerts,
        "notes_fading": notes,
        "notes_seasonal": seasonal_notes,
    }, indent=2))

    for repo, r in report.items():
        if r["state"] == "unreachable":
            print(f"{repo:<32} UNREACHABLE — {r['why']}")
        elif r["state"] == "no-ad-revenue":
            print(f"{repo:<32} no ad revenue — nothing to watch here")
        else:
            print(f"{repo:<32} ${r['site_daily_recent']}/day now vs "
                  f"${r['site_daily_baseline']}/day baseline "
                  f"({-r['site_drop_pct']:+.1f}%), watching {r['pages_watched']} pages "
                  f"= {r['watched_revenue_share_pct']}% of revenue"
                  + (f", {r['pages_below_min_daily']} skipped under "
                     f"${MIN_DAILY}/day" if r["pages_below_min_daily"] else ""))

    # Fades and minors print every night but never notify. Silent-but-recorded
    # is the point: seasonal wind-down and small dips are context for the
    # weekly review, not an alarm.
    for n in notes:
        print(f"  fading (no alert): {n}")
    for n in seasonal_notes:
        print(f"  seasonal (no alert): {n}")
    for repo, r in report.items():
        if r.get("concentration_state") == "unreachable":
            print(f"  ⚠️  {repo}: 180d concentration pull FAILED — every drop below is "
                  f"reported at full volume with an unverified run rate. This is NOT "
                  f"'nothing seasonal'.")
    for repo, r in report.items():
        for d in r.get("minor", []):
            print(f"  minor (no alert): {repo}: {d['page']} down {d['drop_pct']}% "
                  f"but only ~${d['monthly_at_risk']}/mo — under the "
                  f"${MIN_IMPACT}/mo notify floor")

    if not alerts:
        print("clean — no watched page fell off a cliff, no notification sent")
        return 0

    text = "\n".join(["Revenue watchdog — money moved:", ""] + [f"  - {a}" for a in alerts]
                     + ["", f"detail: {OUT}"])
    subject = f"[Teamz] REVENUE ALERT: {len(alerts)} signal(s)"

    delivered = {}
    if notify is not None:
        delivered = notify.dispatch(subject=subject, text=text,
                                    title="Teamz Revenue Watchdog")
    else:
        subprocess.run([
            "osascript", "-e",
            f'display notification {json.dumps(alerts[0][:180])} '
            f'with title "Teamz Revenue Watchdog" sound name "Basso"',
        ], capture_output=True)
        print("  notify/            teamz_notify unavailable — macOS popup only")

    print(f"ALERT: {len(alerts)} signal(s)")
    for a in alerts:
        print(f"  - {a}")

    # Same honesty rule as the growth watchdog: an alert that never left this
    # Mac has not reached an owner who is out driving.
    if notify is not None and not notify.reached_owner(delivered):
        print("  ⚠️  This alert reached the Mac ONLY — no WhatsApp/email channel is")
        print("      configured, so nobody sees it away from this machine. Fill in")
        print(f"      {notify.WHATSAPP_ENV}")
        print(f"      or {notify.SMTP_ENV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
