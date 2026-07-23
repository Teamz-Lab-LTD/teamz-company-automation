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
from datetime import datetime, timedelta
from pathlib import Path

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
        subprocess.run([
            "osascript", "-e",
            f'display notification {json.dumps(msg)} with title "Teamz Growth Watchdog" sound name "Basso"',
        ], capture_output=True)
        print(f"ALERT: {summary}")
    else:
        print("clean — all 4 properties healthy, no notification sent")


if __name__ == "__main__":
    main()
