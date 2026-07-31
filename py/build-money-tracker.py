#!/usr/bin/env python3
"""
Money-growth tracker — answers "are my money-making pages actually growing, flat, or dead?"
with real GSC data, anytime. No guessing.

A "money page" = a tool in a high-RPM niche (finance/tax/mortgage/insurance/legal/real-estate)
that has real Google search demand. For each, it pulls GSC clicks/impressions/position for the
last 28 days vs the prior 28 days and buckets it: GROWING / FLAT / STUCK (ranks but page 2+,
0 clicks) / DEAD (no impressions). Saves a snapshot so week-over-week trend is visible.

  python3 build-money-tracker.py            # pull + print + snapshot
  python3 build-money-tracker.py --report   # show last snapshot, no network

Honest: clicks come weeks after enhancement. Run weekly, judge over a month — not daily.
"""
import os, sys, json, importlib.util
from urllib import parse
import urllib.request as u
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO = os.path.dirname(HERE)            # the automation submodule
# HOST = the consumer repo (has tools.json + data/). abspath() does NOT follow the invocation
# back to a stable place: run as teamz-company-automation/py/... this used to resolve HOST to
# teamz-projects/ (empty) — money-tracker then silently found 0 money pages. TEAMZ_HOST_SITE_ROOT
# is exported by config.sh in every nightly; trust it, FAIL LOUD if it lands on the wrong tree.
HOST = os.environ.get("TEAMZ_HOST_SITE_ROOT") or os.path.dirname(AUTO)
if os.path.basename(os.path.normpath(HOST)) == "teamz-company-automation" \
        or not os.path.exists(os.path.join(HOST, "tools.json")):
    sys.stderr.write(
        f"FATAL: build-money-tracker resolved HOST to {HOST}, which is not a Teamz Lab content "
        f"site (no tools.json). Set TEAMZ_HOST_SITE_ROOT to the host repo. Refusing to run "
        f"against the wrong tree and report a false 'no money pages'.\n")
    sys.exit(2)
DATA = os.path.join(HOST, "data")
SNAP_DIR = os.path.join(DATA, "money-snapshots")
TOK = os.path.expanduser("~/.config/teamzlab/search-console-token.json")
SITE = "https://tool.teamzlab.com"
MONEY_NICHES = {"finance", "tax", "mortgage", "insurance", "legal", "real-estate", "b2b-leadgen"}
# A page enters the snapshot if the ORIGINAL rule accepts it (niche in MONEY_NICHES AND Planner
# volume >= 1000) **OR** Google is already showing it this often in 28d. The OR is deliberate:
# replacing the original rule outright dropped 35 of the 82 pages the striking-distance pool can
# currently pick, so the gate is strictly additive — nothing selectable today can be lost.
#
# Why the demand arm exists at all: the niche list + Planner volume are both GUESSES, and both
# were wrong about this site. Measured 2026-08-01, hubs OUTSIDE MONEY_NICHES earned $196.56 of
# July's $198.76 — 98.9%. football maps to "entertainment", games to "gaming", nfl to
# "productivity", so the three hubs that actually pay could never enter. Planner volume is no
# better: "penalty shootout simulator" is rated 50/mo and produces 2,239 clicks/28d, while
# "paycheck calculator montana" is rated 5,000/mo and earns $0.00. GSC impressions are MEASURED,
# self-updating, and come from the same call this script already makes — no new API, no new token.
DEMAND_MIN_IMPR = 10        # matches pool_thin_faq_demand's own floor, so no consumer loses rows


def money_pages():
    """Candidate pages -> [{slug, url, vol, rpm, niche, old_rule}].

    Returns EVERY tool plus the flag saying whether the original niche+volume rule accepts it.
    The demand half of the gate needs GSC, which is only fetched in run(), so the final
    admission decision happens there (see DEMAND_MIN_IMPR)."""
    sys.path.insert(0, HERE)
    import keyword_volume_manual as kvm, revenue_priority as rp
    mv = kvm.load_manual_volume(DATA)
    d = json.load(open(os.path.join(HOST, "tools.json")))
    out = []
    for t in d["tools"]:
        slug = (t.get("slug") or "").strip("/"); url = t.get("url")
        if not slug or not url:
            continue
        last = slug.split("/")[-1].replace("-", " ")
        hub = slug.split("/")[0]
        niche = rp.niche_for(hub, slug, t.get("title", ""))
        hit = kvm.manual_lookup(mv, last)
        vol = hit["vol"] if hit and hit["vol"] is not None else 0   # blank Planner cell = unknown
        old_rule = niche in MONEY_NICHES and vol >= 1000
        rpm = rp.expected_dollars(slug, hub, t.get("title", ""), 100, 7)["rpm_mid"]
        out.append({"slug": slug, "url": url, "vol": int(vol), "rpm": rpm, "niche": niche,
                    "old_rule": old_rule})
    # dedupe by url, keep highest vol
    by = {}
    for r in out:
        if r["url"] not in by or r["vol"] > by[r["url"]]["vol"]:
            by[r["url"]] = r
    return sorted(by.values(), key=lambda r: -r["vol"] * r["rpm"])


def _gsc_token():
    td = json.load(open(TOK))
    return json.load(u.urlopen(u.Request("https://oauth2.googleapis.com/token",
        data=parse.urlencode({"client_id": td["client_id"], "client_secret": td["client_secret"],
        "refresh_token": td["refresh_token"], "grant_type": "refresh_token"}).encode(),
        method="POST")))["access_token"]


def _gsc(tok, start, end):
    api = f'https://searchconsole.googleapis.com/webmasters/v3/sites/{parse.quote(SITE + "/", safe="")}/searchAnalytics/query'
    body = json.dumps({"startDate": start, "endDate": end, "dimensions": ["page"], "rowLimit": 25000}).encode()
    r = u.urlopen(u.Request(api, data=body, headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}))
    return {row["keys"][0]: row for row in json.load(r).get("rows", [])}


def run(today_str):
    today = datetime.strptime(today_str, "%Y-%m-%d")
    ds = lambda d: d.strftime("%Y-%m-%d")
    pages = money_pages()
    tok = _gsc_token()
    cur = _gsc(tok, ds(today - timedelta(days=31)), ds(today - timedelta(days=3)))
    prev = _gsc(tok, ds(today - timedelta(days=59)), ds(today - timedelta(days=31)))
    rows, agg = [], {"GROWING": 0, "FLAT": 0, "STUCK": 0, "DEAD": 0}
    tot_clicks = tot_prev = 0
    admitted = {"old_rule": 0, "demand": 0}
    for p in pages:
        full = SITE + p["url"]
        c = cur.get(full); pr = prev.get(full)
        cc = int(c["clicks"]) if c else 0
        pc = int(pr["clicks"]) if pr else 0
        impr = int(c["impressions"]) if c else 0
        pos = round(c["position"], 1) if c else 0
        # union gate — original rule OR measured Google demand (see DEMAND_MIN_IMPR)
        if not (p["old_rule"] or impr >= DEMAND_MIN_IMPR):
            continue
        admitted["old_rule" if p["old_rule"] else "demand"] += 1
        tot_clicks += cc; tot_prev += pc
        if impr == 0:
            bucket = "DEAD"
        elif cc == 0:
            bucket = "STUCK"           # ranks but page 2+ -> no clicks
        elif cc > pc:
            bucket = "GROWING"
        else:
            bucket = "FLAT"
        agg[bucket] += 1
        rows.append({**p, "clicks": cc, "prev_clicks": pc, "impr": impr, "pos": pos, "bucket": bucket})
    snap = {"date": today_str, "total_clicks_28d": tot_clicks, "prev_clicks_28d": tot_prev,
            "buckets": agg, "admitted": admitted, "pages": rows}
    os.makedirs(SNAP_DIR, exist_ok=True)

    # NEVER SHRINK SILENTLY. The snapshot is the ONLY input to the enhance queue's two biggest
    # pools. A GSC outage returns few/no rows, which would quietly write a near-empty snapshot and
    # starve the queue with everything still reporting success. Refuse the write and say so loudly
    # instead — a monitor that can only ever look healthy is not a monitor.
    prev_path = os.path.join(SNAP_DIR, "latest.json")
    if os.path.exists(prev_path):
        try:
            old_n = len(json.load(open(prev_path)).get("pages", []))
        except Exception:
            old_n = 0
        if old_n and len(rows) < old_n * 0.5:
            sys.stderr.write(
                f"ERROR: money snapshot collapsed {old_n} -> {len(rows)} pages (>50% drop). "
                f"Keeping the previous snapshot; NOT overwriting. Likely a GSC fetch failure — "
                f"cur={len(cur)} prev={len(prev)} rows returned.\n")
            return json.load(open(prev_path))

    json.dump(snap, open(os.path.join(SNAP_DIR, f"{today_str}.json"), "w"), indent=2)
    json.dump(snap, open(prev_path, "w"), indent=2)
    return snap


def report(snap):
    print(f"\n  MONEY-PAGE GROWTH ({snap['date']}) — {len(snap['pages'])} high-RPM pages with demand")
    print("  " + "=" * 64)
    b = snap["buckets"]
    print(f"  GROWING {b['GROWING']}   FLAT {b['FLAT']}   STUCK(page2+,0 clicks) {b['STUCK']}   DEAD {b['DEAD']}")
    print(f"  total clicks 28d: {snap['total_clicks_28d']}  (prev 28d: {snap['prev_clicks_28d']})")
    delta = snap["total_clicks_28d"] - snap["prev_clicks_28d"]
    print(f"  -> money traffic {'GROWING +' + str(delta) if delta > 0 else 'flat/down ' + str(delta)} WoW-ish")
    print(f"\n  Top money pages by potential (vol x rpm):")
    print(f"    {'bucket':<8} {'clk':>4} {'pos':>5} {'rpm':>5} {'vol':>7}  page")
    for r in snap["pages"][:20]:
        print(f"    {r['bucket']:<8} {r['clicks']:>4} {r['pos']:>5} ${r['rpm']:>3} {r['vol']:>7}  {r['url']}")
    stuck = [r for r in snap["pages"] if r["bucket"] == "STUCK"]
    if stuck:
        print(f"\n  {len(stuck)} STUCK pages rank but sit on page 2+ (the trapped money — enhance to page 1).")


def main():
    if "--report" in sys.argv:
        p = os.path.join(SNAP_DIR, "latest.json")
        if not os.path.exists(p):
            sys.exit("No snapshot yet — run without --report first.")
        report(json.load(open(p)))
        return
    # date passed in or derived at call-site (scripts can't call Date in some contexts)
    today = sys.argv[sys.argv.index("--today") + 1] if "--today" in sys.argv \
        else datetime.now().strftime("%Y-%m-%d")
    report(run(today))


if __name__ == "__main__":
    main()
