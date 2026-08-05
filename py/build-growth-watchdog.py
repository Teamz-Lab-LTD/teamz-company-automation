#!/usr/bin/env python3
"""
Nightly cross-property watchdog. Runs AFTER every property's own nightly job
has finished (all 4 are done by ~23:30). Reads the same preflight-status.json
+ nightly-status.json files /growth reads, decides if anything is genuinely
alert-worthy, and fires exactly ONE Mac notification only when it is.

Why this exists: tools' internal-link health_alerts count sat in
nightly-status.json for two months with nothing ever surfacing it — the
owner only found out because he happened to ask. This closes that gap
without a human having to remember to run /growth.

Deliberately silent on a clean night. A notification for "all fine" trains
the owner to ignore notifications, which defeats the one time it matters.
Always writes data/growth-watchdog-status.json though, clean or not — so
"no notification" and "watchdog didn't run" are never the same shape on
disk (a monitor that goes silent by crashing must not look like all-clear).
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Shared notifier (WhatsApp -> email -> macOS). Imported defensively: if it is
# missing or broken, the watchdog must still RUN and still popup — a reporting
# dependency that can silence the whole monitor is worse than no notifier.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import teamz_notify as notify
except Exception:  # noqa: BLE001
    notify = None

ROOT = Path("/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects")
OUT = ROOT / "teamz-company-automation" / "data" / "growth-watchdog-status.json"
STALE_HOURS = 30

PROPERTIES = {
    "apps": "teamz-lab-generic-landing-pages",
    "goalkit": "goalkit-bd",
    "learn": "teamz-lab-learning",
    "tools": "teamzlab-tools",
}


def load(path):
    try:
        return json.loads(path.read_text()), None
    except FileNotFoundError:
        return None, "missing"
    except (json.JSONDecodeError, OSError) as e:
        return None, f"unreadable ({e})"


def check_property(name, repo):
    data_dir = ROOT / repo / "data"
    issues = []

    preflight, err = load(data_dir / "preflight-status.json")
    if err:
        issues.append(f"preflight-status.json {err}")
    elif not preflight.get("ok", False):
        issues.append(f"preflight FAILED: {preflight.get('failures')}")

    nightly, err = load(data_dir / "nightly-status.json")
    if err:
        issues.append(f"nightly-status.json {err}")
    else:
        if nightly.get("exit_code", 0) != 0:
            issues.append(f"nightly exit_code={nightly.get('exit_code')}")
        build = nightly.get("build", "")
        if build and build != "ok":
            # Relay WHAT was wrong, not just how many. "ok:11-health-alerts" sent
            # the owner into a 49k-line log to find out; the texts are written by
            # nightly-build.sh's status trap and cost nothing to carry.
            texts = nightly.get("health_alert_texts") or []
            if texts:
                issues.append(f"build={build} -> " + " | ".join(t[:120] for t in texts[:3]))
                if len(texts) > 3:
                    issues[-1] += f" (+{len(texts) - 3} more)"
            else:
                issues.append(f"build={build}")
        if nightly.get("deploy") == "failed":
            issues.append("deploy=failed")
        if nightly.get("push") == "failed":
            issues.append("push=failed")
        ts = nightly.get("finished_at")
        if ts:
            try:
                age = datetime.now() - datetime.fromisoformat(ts)
                if age > timedelta(hours=STALE_HOURS):
                    hrs = int(age.total_seconds() // 3600)
                    issues.append(f"stale — last ran {hrs}h ago")
            except ValueError:
                issues.append(f"finished_at unparseable: {ts}")

    return issues


def main():
    report = {}
    for name, repo in PROPERTIES.items():
        report[name] = check_property(name, repo)

    alerting = {k: v for k, v in report.items() if v}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "ran_at": datetime.now().isoformat(timespec="seconds"),
        "properties": report,
        "alert_count": len(alerting),
    }, indent=2))

    if alerting:
        summary = "; ".join(f"{k}: {v[0]}" for k, v in alerting.items())
        msg = f"Growth watchdog — {len(alerting)} propert{'y' if len(alerting)==1 else 'ies'} need attention: {summary}"
        if len(msg) > 200:
            msg = msg[:197] + "..."

        # Full detail for WhatsApp/email; the macOS popup truncates to one line
        # anyway, and a one-line popup is what made these alerts invisible.
        body = [msg, ""]
        for name, issues in alerting.items():
            body.append(f"{name}:")
            body.extend(f"  - {i}" for i in issues)
        body.append("")
        body.append(f"detail: {OUT}")
        detail_text = "\n".join(body)

        # WHY NOT osascript ALONE. This watchdog correctly caught apps'
        # dirty-tree lock on 5 nights (2026-07-26/27, 08-01/02/04) and
        # goalkit+learn push failures on 08-03/04. Every one of those fired a
        # macOS popup at a Mac the owner was not sitting at — he drives Uber —
        # so the engine skipped content for a week and nobody knew until he
        # happened to ask on 08-06. A monitor that cannot leave the machine has
        # not reported anything.
        delivered = {}
        if notify is not None:
            delivered = notify.dispatch(
                subject=f"[Teamz] watchdog: {len(alerting)} propert"
                        f"{'y' if len(alerting)==1 else 'ies'} need attention",
                text=detail_text, title="Teamz Growth Watchdog",
            )
        else:
            subprocess.run([
                "osascript", "-e",
                f'display notification {json.dumps(msg)} with title "Teamz Growth Watchdog" sound name "Basso"',
            ], capture_output=True)
            print("  notify/            teamz_notify unavailable — macOS popup only")

        print(f"ALERT: {summary}")

        # Say plainly when the alert never left this machine. Reporting a
        # delivered-nowhere alert as sent is the same failure one layer up.
        if notify is not None and not notify.reached_owner(delivered):
            print("  ⚠️  This alert reached the Mac ONLY — no WhatsApp/email channel is")
            print("      configured, so nobody sees it away from this machine. Fill in")
            print(f"      {notify.WHATSAPP_ENV}")
            print(f"      or {notify.SMTP_ENV}  (both ship as .example)")
    else:
        print("clean — all 4 properties healthy, no notification sent")


if __name__ == "__main__":
    main()
