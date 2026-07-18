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
# HOST via __file__ math is WRONG under the nightly: scripts/nightly-build.sh and the nested
# teamz-company-automation are BOTH symlinks, and `readlink -f` resolves the chain so __file__
# lands in teamz-projects/teamz-company-automation/py — making HOST=teamz-projects, DATA=an empty
# dir with no manual-pull. Then load_manual_volume() returned {} and the whole authoritative
# Google-volume branch silently no-op'd while dead-revival-targets.json froze at its last good run.
# Every other builder resolves the host from config; do the same. The nightly exports
# TEAMZ_HOST_SITE_ROOT (=teamzlab-tools); fall back to __file__ math only when run standalone.
HOST = os.environ.get("TEAMZ_HOST_SITE_ROOT") or os.path.dirname(AUTO)
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


# ----------------------------------------------------------- manual Google volume
# Exact search volume exported by hand from Google Ads Keyword Planner (free, no API
# token). This is the AUTHORITATIVE demand source — when a topic is present here we
# trust it over the free-signal estimate (autocomplete/Bing/GSC), which only guesses.
# Export how-to: Keyword Planner -> Get search volume -> Saved keywords -> Download .csv
MANUAL_DIR = os.path.join(DATA, "manual-pull")   # drop any number of Planner .csv exports here
REVIVE_MIN_VOL = 100        # real Google searches/mo below this = not worth re-targeting
WALL_VOL       = 10000      # above this = head-term authority wall; a solo re-targeted tool
                            #   page can't beat nerdwallet/.gov here (was 100000 — that let the
                            #   50k Planner bucket through and aimed the agent at sure losses)
import math
sys.path.insert(0, HERE)
# Use the ONE shared Planner-volume loader (no more verbatim copy living here). Behavior is
# unchanged: we delegate but pass THIS script's own TOOL_TYPES/INTENT_SUFFIXES so the
# core-topic fallback strips exactly the words it always did.
from keyword_volume_manual import (
    load_manual_volume as _shared_load_volume,
    manual_lookup as _shared_manual_lookup,
)


def load_manual_volume():
    """Merge every Planner export under data/manual-pull/ into one map (shared loader)."""
    return _shared_load_volume(DATA)


def manual_lookup(mv, kw, core_fallback=True):
    """Exact match, else (when core_fallback) strip a trailing tool/intent word to the core topic."""
    return _shared_manual_lookup(mv, kw, TOOL_TYPES, INTENT_SUFFIXES, core_fallback=core_fallback)


def vol_to_score(vol, comp):
    s = min(100.0, 30.0 + 14.0 * math.log10(max(vol, 1)))   # 100->58, 5k->82, 50k->96
    if comp == "Medium":
        s -= 8
    return round(max(0.0, s), 1)


def vol_to_tier(vol):
    return "HIGH" if vol >= 10000 else "MEDIUM" if vol >= 1000 else "LOW"


# ----------------------------------------------------------------- find targets
def find_targets():
    kv = load_kv()
    mv = load_manual_volume()
    slugs = read_dead_slugs()
    # Manual lookups are instant (no network), so when the Planner export is present we
    # classify EVERY dead page from real Google data instead of the network-capped sample.
    work = slugs if mv else slugs[:CAP]
    print(f"  INDEXED_NO_DEMAND pages: {len(slugs)}  |  manual Google volume: "
          f"{len(mv)} keywords  |  processing {len(work)}")
    revive, prune = [], []
    for slug in work:
        core, current = topic_and_current(slug)

        # --- authoritative path: real Google volume for this topic ---
        # Exact-match the page's SPECIFIC tool phrase only — never inherit the bare head noun's
        # (much larger, unwinnable) volume. A blank Planner cell = UNKNOWN (not zero), so it
        # falls through to the free-signal estimate instead of being pruned as "no demand".
        m = manual_lookup(mv, current, core_fallback=False)
        if m is not None and m["vol"] is not None:
            vol, comp = m["vol"], m["comp"]
            if vol < REVIVE_MIN_VOL:
                prune.append({"slug": slug, "old_target": current,
                              "reason": f"google: {int(vol)}/mo — real no demand"})
                print(f"    prune   /{slug}/  ('{current}' — Google {int(vol)}/mo)")
            elif vol > WALL_VOL or comp == "High":
                prune.append({"slug": slug, "old_target": current,
                              "reason": f"google: {int(vol)}/mo {comp} — head-term wall, can't win"})
                print(f"    wall    /{slug}/  ('{core}' — Google {int(vol)}/mo {comp})")
            else:
                # The page's own topic cluster has real, winnable Google demand. It's "dead"
                # only because the page doesn't RANK (0 GSC impressions) — not because nobody
                # searches. So enhance toward the page's specific tool phrase (current), which
                # sits in a proven-demand cluster — never dumb it down to a bare head noun.
                target = current
                score = vol_to_score(vol, comp)
                revive.append({"slug": slug, "old_target": current, "new_target": target,
                               "score": score, "tier": vol_to_tier(vol), "cluster": core,
                               "google_vol": int(vol), "competition": comp,
                               "source": "google-planner"})
                print(f"    REVIVE  /{slug}/  enhance for '{target}'  (cluster '{core}' Google {int(vol)}/mo {comp}, {score})")
            continue

        # --- fallback: topic not in the manual pull -> free-signal estimate ---
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
                           "score": best["score"], "tier": best["tier"], "bing_exact": best["bing"],
                           "source": "free-signal"})
            print(f"    revive? /{slug}/  '{current}' -> '{best['keyword']}'  ({best['tier']} {best['score']} est)")
        else:
            prune.append({"slug": slug, "old_target": current, "reason": "no winnable demand sibling"})
            print(f"    prune   /{slug}/  ('{current}' — nothing winnable)")

    # --- revenue + SERP-difficulty re-ranking: enhance the highest-EARNING winnable page
    # first, not just the highest-volume one. Reuses the existing revenue-velocity scorer
    # (revenue_priority) + organic SERP difficulty (serp_difficulty). Both degrade safely:
    # if a module/network fails we fall back to the old volume sort. ---
    try:
        sys.path.insert(0, HERE)
        import revenue_priority as rp
        import serp_difficulty as sd
        for r in revive:
            hub = r["slug"].split("/")[0]
            vol = r.get("google_vol") or r.get("bing_exact") or 0
            r["est_visitors_mo"] = int(vol * 0.10)          # rough mo3 capture if it ranks
            ed = rp.expected_dollars(r["slug"], hub, "", r["est_visitors_mo"], serp_winnability=5)
            r.update({"niche": ed["niche"], "rpm_mid": ed["rpm_mid"],
                      "expected_dollars_mo": ed["expected_dollars_mo"]})
        revive.sort(key=lambda x: -x["expected_dollars_mo"])
        # refine real SERP difficulty ONLY for the top targets (DDG throttles; cap the calls).
        # HARD FILTER: a confirmed authority wall (winnability <= 3) is moved to PRUNE, not
        # revived — on-page edits can't outrank nerdwallet/.gov. A failed fetch returns None
        # (winnability unknown) -> DEFER: keep the page, score it neutral, never wave it through
        # as if winnable. (Only the top 8 are SERP-checked; pages below stay on the volume sort.)
        import time as _t, signal as _sig
        # HARD per-call timeout: sd.winnability() scrapes the live SERP and has no internal
        # timeout — when Google throttles it, the call blocks forever and freezes the whole
        # nightly (observed: 10h hang 2026-06-11). Cap each check; timeout -> unknown -> neutral.
        class _WinTimeout(Exception):
            pass
        def _on_alarm(signum, frame):
            raise _WinTimeout()
        _have_alarm = hasattr(_sig, "SIGALRM")
        if _have_alarm:
            _sig.signal(_sig.SIGALRM, _on_alarm)
        for r in revive[:8]:
            try:
                if _have_alarm:
                    _sig.alarm(45)
                w = sd.winnability(r["new_target"], DATA)
            except _WinTimeout:
                w = None
                print(f"  (winnability timeout >45s on {r['new_target']!r} -> neutral)")
            except Exception as _we:
                w = None
                print(f"  (winnability error on {r['new_target']!r}: {type(_we).__name__} -> neutral)")
            finally:
                if _have_alarm:
                    _sig.alarm(0)
            r["serp_winnability"] = w
            if w is not None and w <= 3:
                r["_serp_wall"] = True
                continue
            wkt = w if w is not None else 5      # None = unknown -> neutral sort weight, not excluded
            ed = rp.expected_dollars(r["slug"], r["slug"].split("/")[0], "",
                                     r.get("est_visitors_mo", 0), serp_winnability=wkt)
            r["expected_dollars_mo"] = ed["expected_dollars_mo"]
            _t.sleep(2)
        walls = [r for r in revive if r.get("_serp_wall")]
        if walls:
            revive = [r for r in revive if not r.get("_serp_wall")]
            for r in walls:
                prune.append({"slug": r["slug"], "old_target": r["old_target"],
                              "reason": f"SERP wall: top-10 owned by authority sites "
                                        f"(winnability {r['serp_winnability']})"})
            print(f"  SERP hard-filter: {len(walls)} authority-walled page(s) -> prune")
        revive.sort(key=lambda x: -x["expected_dollars_mo"])
        print(f"  ranked {len(revive)} targets by expected $/mo (RPM x winnability); "
              f"top: /{revive[0]['slug']}/ ~${revive[0]['expected_dollars_mo']}/mo" if revive else "")
    except Exception as e:
        print(f"  (revenue/SERP re-rank skipped: {type(e).__name__} — using volume sort)")
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
    try:
        cur = gsc_for(list(revived.keys()))
    except Exception as e:
        print(f"\n  GSC unavailable ({type(e).__name__}) — offline mode, showing the "
              f"{len(revived)} revived pages from the local log:")
        for slug, rec in revived.items():
            b = rec.get("baseline_impr")
            print(f"    /{slug[:45]:<45} '{rec.get('new_target','')[:22]}' "
                  f"baseline_impr={b if b is not None else 'unset'}")
        print("  (run online to pull live 28d impressions + rising/flat/dead buckets.)")
        return
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
