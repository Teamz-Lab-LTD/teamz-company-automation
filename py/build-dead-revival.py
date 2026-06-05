#!/usr/bin/env python3
"""
Dead-tool revival — turn indexed-but-no-demand pages into live ones.

For each dead page (already indexed, zero impressions because its keyword has no
demand) this finds a RELATED keyword that DOES have demand + looks winnable, and
queues the page to be RE-TARGETED toward it (Phase 4 rewrites title+content).
Pages with no winnable demand sibling go to a PRUNE list instead of rotting.

Key idea: you cannot CREATE search demand, but you can REDIRECT an already-indexed
page to demand that already exists. An indexed page re-pointed at a real keyword
ranks faster than a brand-new page.

Modes:
  python3 py/build-dead-revival.py            # find revival targets (writes JSON)
  python3 py/build-dead-revival.py --cap 8    # only process N dead pages (network-bound)
  python3 py/build-dead-revival.py --status   # "are any dead tools rising?" — track revived pages

Outputs (in host data/):
  dead-revival-targets.json   RE-TARGET list (slug -> new demand keyword)  [feeds the nightly queue]
  dead-revival-prune.json     PRUNE list (no winnable demand sibling)
  dead-revival-log.json       tracking log: each revived page + baseline, for --status

SAFE: read-only analysis + writes its own data files. Does NOT edit site pages or
push. The nightly consumes dead-revival-targets.json at lowest priority + a hard cap.
"""
import os, sys, csv, json, re, importlib.util
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
AUTO = os.path.dirname(HERE)
HOST = os.path.dirname(AUTO)
DATA = os.path.join(HOST, "data")
AUDIT = os.path.join(DATA, "zero-visitor-audit")

TODAY = datetime.now().strftime("%Y-%m-%d")
CAP = 15
if "--cap" in sys.argv:
    try: CAP = int(sys.argv[sys.argv.index("--cap") + 1])
    except Exception: pass

# tool-type words we strip to find the core TOPIC of a dead page
TOOL_TYPES = {'rewriter','generator','calculator','checker','maker','tracker','planner',
              'converter','estimator','analyzer','simulator','tool','template','builder',
              'predictor','counter','finder','scanner','validator','formatter','editor'}
# high-intent suffixes people actually search
INTENT_SUFFIXES = ['generator','calculator','template','checker','tool','maker','examples','free','online']

MIN_SCORE = 45            # demand threshold (MEDIUM+) — below this, no point
MAX_BING_UNWINNABLE = 40000  # heuristic: huge volume + we don't rank = likely a head-term wall, skip


def load_kv():
    spec = importlib.util.spec_from_file_location("kv", os.path.join(HERE, "build-keyword-volume.py"))
    kv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kv)
    # Skip Google Trends here: it 429-rate-limits under the many rapid lookups this
    # engine does, and the backoff makes it crawl. Autocomplete + Bing + GSC are
    # enough to judge demand for revival. (Trends still runs in normal keyword-volume.)
    kv.fetch_google_trends_score = lambda *a, **k: None
    return kv


def topic_and_current(slug):
    """slug 'ai/proposal-rewriter' -> core='proposal', current='proposal rewriter'."""
    last = slug.strip('/').split('/')[-1]
    current = last.replace('-', ' ').strip()
    parts = current.split()
    if len(parts) > 1 and parts[-1] in TOOL_TYPES:
        core = ' '.join(parts[:-1])
    else:
        core = current
    return core, current


def candidates(core, current):
    out, seen = [], set()
    for suf in INTENT_SUFFIXES:
        out.append(f"{core} {suf}")
    out.append(core)
    res = []
    for k in out:
        k = k.strip()
        if k and k != current and k not in seen:
            seen.add(k); res.append(k)
    return res[:6]


def read_dead_slugs():
    """INDEXED_NO_DEMAND pages = indexed, zero demand on current keyword."""
    p = os.path.join(AUDIT, "index-status-prune.csv")
    if not os.path.exists(p):
        sys.exit(f"ERROR: {p} not found — run build-index-status-check.py first.")
    slugs = []
    for r in csv.DictReader(open(p)):
        if r.get("verdict") == "INDEXED_NO_DEMAND":
            slugs.append(r["key"].strip("/"))
    return slugs


# ----------------------------------------------------------------- find targets
def find_targets():
    kv = load_kv()
    slugs = read_dead_slugs()
    print(f"  INDEXED_NO_DEMAND pages available: {len(slugs)}  (processing {min(CAP,len(slugs))})")
    revive, prune = [], []
    for slug in slugs[:CAP]:
        core, current = topic_and_current(slug)
        best = None
        for kw in candidates(core, current):
            try:
                r = kv.estimate_volume(kw)
            except Exception:
                continue
            score = r.get("composite_score", 0) or 0
            bing = (r.get("bing_volume") or {}).get("exact_monthly") or 0
            if bing and bing > MAX_BING_UNWINNABLE:
                continue                       # likely a head-term wall — skip (winnability heuristic)
            if score >= MIN_SCORE and (best is None or score > best["score"]):
                best = {"keyword": kw, "score": score, "tier": r.get("volume_tier"), "bing": bing}
        if best:
            revive.append({"slug": slug, "old_target": current, "new_target": best["keyword"],
                           "score": best["score"], "tier": best["tier"], "bing_exact": best["bing"]})
            print(f"    REVIVE  /{slug}/  '{current}' -> '{best['keyword']}'  ({best['tier']} {best['score']})")
        else:
            prune.append({"slug": slug, "old_target": current, "reason": "no winnable demand sibling"})
            print(f"    prune   /{slug}/  ('{current}' — nothing winnable)")

    revive.sort(key=lambda x: -x["score"])
    with open(os.path.join(DATA, "dead-revival-targets.json"), "w") as f:
        json.dump({"generated": TODAY, "targets": revive}, f, indent=2)
    with open(os.path.join(DATA, "dead-revival-prune.json"), "w") as f:
        json.dump({"generated": TODAY, "prune": prune}, f, indent=2)

    # tracking log: record each revival with a slot for the GSC baseline (filled by --status first run)
    logp = os.path.join(DATA, "dead-revival-log.json")
    log = json.load(open(logp)) if os.path.exists(logp) else {"revived": {}}
    for r in revive:
        if r["slug"] not in log["revived"]:
            log["revived"][r["slug"]] = {"new_target": r["new_target"], "old_target": r["old_target"],
                                          "queued": TODAY, "baseline_impr": None, "baseline_pos": None}
    with open(logp, "w") as f:
        json.dump(log, f, indent=2)

    print(f"\n  -> {len(revive)} pages RE-TARGETABLE (queued for nightly), {len(prune)} for prune")
    print(f"     targets: data/dead-revival-targets.json   prune: data/dead-revival-prune.json")
    if revive:
        print(f"     Top wins:")
        for r in revive[:5]:
            print(f"       /{r['slug']}/  ->  '{r['new_target']}'  ({r['tier']} {r['score']})")


# ----------------------------------------------------------------- status / tracking
def gsc_for(slugs):
    import requests
    from urllib.parse import quote
    TOK = os.path.expanduser("~/.config/teamzlab/search-console-token.json")
    SITE = "https://tool.teamzlab.com/"
    td = json.load(open(TOK))
    tok = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": td["client_id"], "client_secret": td["client_secret"],
        "refresh_token": td["refresh_token"], "grant_type": "refresh_token"}, timeout=20).json()["access_token"]
    API = f'https://searchconsole.googleapis.com/webmasters/v3/sites/{quote(SITE, safe="")}/searchAnalytics/query'
    H = {"Authorization": f"Bearer {tok}", "x-goog-user-project": "teamzlab-tools", "Content-Type": "application/json"}
    end = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
    rows, sr = [], 0
    while True:
        r = requests.post(API, headers=H, json={"startDate": start, "endDate": end,
                          "dimensions": ["page"], "rowLimit": 25000, "startRow": sr}, timeout=90).json().get("rows", [])
        rows += r
        if len(r) < 25000: break
        sr += len(r)
    by = {}
    for row in rows:
        u = row["keys"][0].replace("https://tool.teamzlab.com/", "").strip("/")
        by[u] = (row.get("impressions", 0), round(row.get("position", 0), 1))
    return by


def status():
    logp = os.path.join(DATA, "dead-revival-log.json")
    if not os.path.exists(logp):
        sys.exit("No revival log yet — run without --status first.")
    log = json.load(open(logp))
    revived = log.get("revived", {})
    if not revived:
        print("  No pages revived yet."); return
    cur = gsc_for(list(revived.keys()))
    rising, flat, dead = [], [], []
    for slug, rec in revived.items():
        impr, pos = cur.get(slug, (0, 0))
        base = rec.get("baseline_impr")
        if base is None:                       # first status run = set baseline
            rec["baseline_impr"] = impr; rec["baseline_pos"] = pos
        delta = impr - (rec.get("baseline_impr") or 0)
        row = (slug, rec["new_target"], impr, pos, delta)
        if impr > 0 and (base is None or delta > 0): rising.append(row)
        elif impr > 0: flat.append(row)
        else: dead.append(row)
    json.dump(log, open(logp, "w"), indent=2)
    print(f"\n  DEAD-TOOL REVIVAL STATUS ({len(revived)} revived pages, 28d GSC)")
    print("  " + "=" * 60)
    print(f"  RISING (gaining impressions): {len(rising)}")
    for s, kw, i, p, d in sorted(rising, key=lambda x: -x[2])[:15]:
        print(f"    /{s[:40]:<40} '{kw[:20]}' impr={i} pos={p} (+{d})")
    print(f"  flat (some impressions, not growing): {len(flat)}")
    print(f"  still dead (0 impressions yet): {len(dead)}")
    print(f"\n  (re-targeted pages take days-weeks for Google to re-rank — check weekly)")


if __name__ == "__main__":
    if "--status" in sys.argv:
        status()
    else:
        find_targets()
