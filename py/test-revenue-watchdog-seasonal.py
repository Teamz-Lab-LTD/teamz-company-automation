#!/usr/bin/env python3
"""Regression test for the SEASONAL classifier in build-revenue-watchdog.py.

    python3 py/test-revenue-watchdog-seasonal.py

WHY THIS FILE EXISTS. The seasonal bucket was added on 2026-09-04 after the
watchdog reported "~$192.46/month at risk" on a page whose lifetime earnings
were $197. A classifier that only ever SILENCES things is indistinguishable
from a mute, and a mute on a revenue alarm is worse than the false alarm it
replaced. So the cases below deliberately include the ones that must STILL be
loud — a steady page collapsing, and a failed concentration pull.

Shapes are taken from real measured pages (2026-09-04, GA4 528521795):
  /football/premier-league-table-predictor/  peak-4-week share 86.0%  -> seasonal
  /games/arrow-escape-3d/                    peak-4-week share 49.6%  -> year-round
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("wd", HERE / "build-revenue-watchdog.py")
wd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wd)

STEADY, BURST, GHOST = "/steady/", "/burst/", "/ghost/"
FADER = "/fader/"


def run(case, weeks, conc):
    """Drive check_property with canned weeks and a canned concentration result."""
    wd.pull = lambda mod, tok, pid, s, e: weeks.pop(0)
    wd.concentration = lambda mod, tok, pid, paths: conc
    real = wd.mod_property if hasattr(wd, "mod_property") else None  # noqa: F841

    class M:
        GA4_PROPERTY = {"repo": "1"}
    return wd.check_property(M(), "tok", "repo")


def weeks_for(spec):
    """spec = {path: [w0, w1, w2, w3]} in $/day -> the 4 pulls, newest first."""
    return [{p: v[i] * 7 for p, v in spec.items()} for i in range(4)]


FAILS = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


print("1. a STEADY page collapsing must still be a CLIFF with a $/month figure")
r = run("steady", weeks_for({STEADY: [0.20, 6.00, 6.00, 6.00]}),
        {STEADY: {"peak4wk_share_pct": 49.6, "earning_weeks": 19, "total_180d": 48.61}})
check("steady collapse -> cliffs", [d["page"] for d in r["cliffs"]] == [STEADY],
      f"cliffs={[d['page'] for d in r['cliffs']]} seasonal={[d['page'] for d in r['seasonal']]}")
check("steady collapse keeps its $/month",
      bool(r["cliffs"]) and r["cliffs"][0]["monthly_at_risk"] is not None,
      f"at_risk={r['cliffs'][0]['monthly_at_risk'] if r['cliffs'] else None}")
check("steady collapse marked reliable",
      bool(r["cliffs"]) and r["cliffs"][0]["run_rate_reliable"] is True)

print("2. a BURST page collapsing must be SEASONAL and carry NO $/month")
r = run("burst", weeks_for({BURST: [0.87, 7.57, 7.63, 5.72]}),
        {BURST: {"peak4wk_share_pct": 86.0, "earning_weeks": 8, "total_180d": 193.55}})
check("burst collapse -> seasonal", [d["page"] for d in r["seasonal"]] == [BURST],
      f"cliffs={[d['page'] for d in r['cliffs']]} seasonal={[d['page'] for d in r['seasonal']]}")
check("burst collapse has NO $/month",
      bool(r["seasonal"]) and r["seasonal"][0]["monthly_at_risk"] is None)
check("burst collapse raises no cliff", not r["cliffs"])

print("3. a FAILED concentration pull must stay LOUD, not fall silent")
r = run("unreachable", weeks_for({BURST: [0.87, 7.57, 7.63, 5.72]}), None)
check("unreadable history -> still a cliff", [d["page"] for d in r["cliffs"]] == [BURST])
check("unreadable history -> reliability is None, not True",
      bool(r["cliffs"]) and r["cliffs"][0]["run_rate_reliable"] is None)
check("unreadable history -> concentration_state says so",
      r.get("concentration_state") == "unreachable", r.get("concentration_state"))

print("4. a page GA4 has no history for must also stay loud, not be muted")
r = run("ghost", weeks_for({GHOST: [0.10, 6.00, 6.00, 6.00]}), {})
check("no history -> still a cliff", [d["page"] for d in r["cliffs"]] == [GHOST])
check("no history -> reliability None", bool(r["cliffs"]) and
      r["cliffs"][0]["run_rate_reliable"] is None)

print("5. the FADE rule is untouched — a slide that started earlier is still a fade")
r = run("fade", weeks_for({FADER: [0.50, 2.00, 4.00, 6.00]}),
        {FADER: {"peak4wk_share_pct": 45.0, "earning_weeks": 20, "total_180d": 60.0}})
check("prior decline -> fades", [d["page"] for d in r["fades"]] == [FADER],
      f"fades={[d['page'] for d in r['fades']]}")
check("fade is not double-counted as seasonal", not r["seasonal"])

print()
if FAILS:
    print(f"{len(FAILS)} FAILURE(S): " + ", ".join(FAILS))
    sys.exit(1)
print("all seasonal-classifier cases pass")
