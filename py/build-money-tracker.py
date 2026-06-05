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
AUTO = os.path.dirname(HERE)            # the submodule
HOST = os.path.dirname(AUTO)            # the consumer repo (has tools.json + data/)
DATA = os.path.join(HOST, "data")
SNAP_DIR = os.path.join(DATA, "money-snapshots")
TOK = os.path.expanduser("~/.config/teamzlab/search-console-token.json")
SITE = "https://tool.teamzlab.com"
MONEY_NICHES = {"finance", "tax", "mortgage", "insurance", "legal", "real-estate", "b2b-leadgen"}


def money_pages():
    """High-RPM tool pages with real demand -> [(slug, url, vol, rpm)]."""
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
        if niche not in MONEY_NICHES:
            continue
        hit = kvm.manual_lookup(mv, last)
        vol = hit["vol"] if hit else 0
        if vol < 1000:
            continue
        rpm = rp.expected_dollars(slug, hub, t.get("title", ""), 100, 7)["rpm_mid"]
        out.append({"slug": slug, "url": url, "vol": int(vol), "rpm": rpm, "niche": niche})
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
    for p in pages:
        full = SITE + p["url"]
        c = cur.get(full); pr = prev.get(full)
        cc = int(c["clicks"]) if c else 0
        pc = int(pr["clicks"]) if pr else 0
        impr = int(c["impressions"]) if c else 0
        pos = round(c["position"], 1) if c else 0
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
            "buckets": agg, "pages": rows}
    os.makedirs(SNAP_DIR, exist_ok=True)
    json.dump(snap, open(os.path.join(SNAP_DIR, f"{today_str}.json"), "w"), indent=2)
    json.dump(snap, open(os.path.join(SNAP_DIR, "latest.json"), "w"), indent=2)
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
