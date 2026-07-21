#!/usr/bin/env python3
"""
build-course-radar.py — RPM-first demand radar for NEW learn.teamzlab.com courses.

A blog post targets one query; a COURSE needs a whole topic cluster. This clusters real demand
(GSC gap queries + hand-pulled Keyword Planner volumes + autocomplete expansion) into course-sized
opportunities and ranks them by EXPECTED MONEY — RPM (niche x country) x winnable volume — not by
raw traffic. The owner's rule: no language/track boundary, money decides. So a $6-RPM US Android-
testing cluster outranks an equal-volume $0.3-RPM Bangla cluster unless the Bangla volume dominates.

Reuses the proven pieces (never reimplemented): build-content-queue.py's GSC auth/query, winnability,
autocomplete, overlap/tokens/slugify; keyword_volume_manual's Planner CSV parser; revenue_priority's
expected_dollars (RPM scorer). Geo isolation: US volumes come from the flat manual-pull loader; BD
volumes from a bd/ SUBDIR the flat loader cannot see, so a BD number can never corrupt US winnability.

Modes:
  (default)          read-only: cluster + score, write data/course-radar.json. Safe to run nightly.
  --prepare-batches  emit paste-ready Planner batches (BD + US) into manual-pull/1-UPLOAD-THESE/,
                     cadence-gated. The owner's one manual job: pull them, drop results back.
  --gate             decide the ONE course action for tonight (create-pilot | expand | null) and
                     write data/course-task.json. The agent never authorizes itself.
  --self-test        prove the refusal paths (vanity, duplicate) fire. Guards the guard.
  --dry-run          print, do not write.
"""
import csv
import glob
import json
import os
import re
import sys
import importlib.util
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("_bcq", HERE / "build-content-queue.py")
_bcq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bcq)                       # defines functions only; main() is __main__-gated
from _teamz_config import load_runtime               # noqa: E402
from keyword_volume_manual import load_manual_volume, _parse_planner_csv, _norm  # noqa: E402
try:
    from revenue_priority import expected_dollars, niche_for    # noqa: E402
    _HAVE_RPM = True
except Exception:                                    # scorer/deps missing — degrade, never crash
    _HAVE_RPM = False

# ------------------------------------------------------------------ gates (env-overridable)
MIN_CLUSTER_KW   = int(os.getenv("TEAMZ_RADAR_MIN_KW", "5"))        # a course needs a cluster
MIN_CLUSTER_VOL  = int(os.getenv("TEAMZ_RADAR_MIN_VOL", "300"))     # ...or measurable demand
MIN_GAP_IMPR     = int(os.getenv("TEAMZ_RADAR_MIN_GAP_IMPR", "100"))
GAP_IMPR_FLOOR   = int(os.getenv("TEAMZ_RADAR_GAP_FLOOR", "10"))    # per-query gap floor (< content-queue's 25: clusters aggregate)
DUP_OVERLAP      = float(os.getenv("TEAMZ_RADAR_DUP_OVERLAP", "0.5"))
ONE_HEAD_MAX     = float(os.getenv("TEAMZ_RADAR_ONE_HEAD_MAX", "0.7"))  # >70% vol from one term = a head, not a course
RADAR_MIN_NEW    = int(os.getenv("TEAMZ_RADAR_MIN_NEW", "100"))
RADAR_MIN_DAYS   = int(os.getenv("TEAMZ_RADAR_MIN_DAYS", "21"))
PILOT_CADENCE    = int(os.getenv("TEAMZ_PILOT_CADENCE_DAYS", "14"))
# PILOT_IMPR_FLOOR is DEPRECATED and deliberately unused. It gated promotion on IMPRESSIONS, and
# a 2026-07-19 audit of this site's 747 lessons showed why that is the wrong metric: 585 pages
# (78.3%) earn impressions and NEVER a single click, and the worst offender takes 1,563 impressions
# at position 13.5 for zero clicks. An impression floor would have promoted exactly the failure
# mode. Promotion now gates on CLICKS. Kept only so an existing env var cannot silently change
# behaviour by being read somewhere unexpected.
PILOT_IMPR_FLOOR = int(os.getenv("TEAMZ_PILOT_IMPR_FLOOR", "100"))
PILOT_CLICK_FLOOR = int(os.getenv("TEAMZ_PILOT_CLICK_FLOOR", "3"))    # clicks/28d to graduate to expanding
PILOT_DORMANT_DAYS = int(os.getenv("TEAMZ_PILOT_DORMANT_DAYS", "56"))  # 0 clicks after this = dormant
# Query LENGTH is the only AI-Overview signal that survived adversarial verification (Ahrefs, 146M
# SERPs, Sept 2025): P(AI Overview) climbs monotonically 9.5% at 1 word -> 19.5% at 4 -> 46.4% at 7+.
# Volume was never measured by anyone as an AIO driver, so "go long-tail to dodge AIO" is unsourced
# and this site already disproves it in practice: its 9-word "8255 control word 80h all ports output
# mode 0" ranks position 4 and takes ZERO clicks because Google prints the two-character answer.
# A cluster whose members are mostly long queries is demand Google answers itself — refuse it.
AIO_LEN_MAX      = int(os.getenv("TEAMZ_RADAR_AIO_LEN_MAX", "6"))     # median member words >= this = refuse
MAX_ACTIVE       = int(os.getenv("TEAMZ_RADAR_MAX_ACTIVE_PILOTS", "2"))
EXPAND_SPACING   = int(os.getenv("TEAMZ_PILOT_EXPAND_SPACING", "7"))
BATCH_MAX        = int(os.getenv("TEAMZ_KW_BATCH_MAX", "700"))

# competition string -> a 1-10 SERP winnability proxy (Low comp = easy to win)
def _win_from_comp(comp):
    c = (comp or "").strip().lower()
    if "high" in c:   return 3
    if "med" in c:    return 5
    if "low" in c:    return 8
    return 5                                          # unknown competition = neutral


def _today():
    return date.today().isoformat()


def _days_since(iso):
    if not iso:
        return 10 ** 6
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return (date.today() - date(y, m, d)).days
    except Exception:
        return 10 ** 6


# ------------------------------------------------------------------ geo-isolated volume
def load_bd_volume(data_dir):
    """BD volumes live in manual-pull/2-DROP-RESULTS-HERE/bd/*.csv — a subdir the flat US loader
    (load_manual_volume) never globs, so BD and US demand can never merge. Higher known vol wins."""
    base = Path(data_dir) / "manual-pull" / "2-DROP-RESULTS-HERE" / "bd"
    merged = {}
    if base.exists():
        for p in sorted(glob.glob(str(base / "*.csv"))):
            for k, v in _parse_planner_csv(p).items():
                nv = v.get("vol")
                if k not in merged or (nv is not None and (merged[k].get("vol") is None or nv > merged[k]["vol"])):
                    merged[k] = v
    return merged


def volume_for_geo(geo, us_vol, bd_vol):
    return bd_vol if geo == "bd" else us_vol


# ------------------------------------------------------------------ seeds / courses / ledger
def load_seeds(host):
    p = host / "data" / "course-radar-seeds.json"
    if not p.exists():
        return {"themes": [], "open_clustering": True}
    try:
        return json.loads(p.read_text())
    except Exception as e:
        sys.stderr.write(f"WARNING: {p} unreadable ({e}) — open-clustering only.\n")
        return {"themes": [], "open_clustering": True}


def existing_courses(host):
    """(slugs, title_tokens_by_slug) for duplicate detection against what already exists."""
    cdir = host / "courses"
    slugs, titles = [], {}
    if cdir.exists():
        for d in sorted(cdir.iterdir()):
            cfg = d / "config.js"
            if not cfg.exists():
                continue
            slugs.append(d.name)
            m = re.search(r"title:\s*(['\"])(.*?)\1", cfg.read_text(errors="ignore"))
            titles[d.name] = f"{d.name.replace('-', ' ')} {m.group(2) if m else ''}"
    return slugs, titles


def load_ledger(host):
    """(ledger, corrupt). Missing = fresh start; corrupt = fail CLOSED (pilot budget 0), same
    discipline as build-content-queue.load_ledger — a broken ledger must never unlock creation."""
    p = host / "data" / "course-ledger.json"
    if not p.exists():
        return {"pilots": []}, False
    try:
        return json.loads(p.read_text()), False
    except Exception as e:
        sys.stderr.write(f"WARNING: {p} unreadable ({e}); failing CLOSED (no course action).\n")
        return {"pilots": []}, True


# ------------------------------------------------------------------ demand gathering
def gap_queries(cfg):
    """GSC queries with impressions that no page serves well (position >= 20) — the raw material
    for a new course. Raises on a GSC HTTP error (never silently empty)."""
    token = _bcq.gsc_token(cfg)
    rows = _bcq.gsc_query(cfg["site_property"], token, ["query"], days=90, row_limit=5000)
    out = {}
    for r in rows:
        q = _norm(r["keys"][0])
        impr = int(r.get("impressions", 0))
        pos = float(r.get("position", 99))
        if not q or _bcq.looks_like_junk(q) or len(q.split()) > 10:
            continue
        if impr < GAP_IMPR_FLOOR or pos < 20:         # already ranks well = not a gap
            continue
        out[q] = max(out.get(q, 0), impr)
    return out


def cluster(seeds, us_vol, bd_vol, gaps):
    """Assign every keyword to the first seed theme whose pattern tokens overlap >= 0.5; leftovers
    become open clusters keyed by their head bigram. Returns {cluster_id: {...}}."""
    themes = seeds.get("themes", [])
    clusters = {}

    def ensure(cid, meta):
        if cid not in clusters:
            clusters[cid] = {"id": cid, **meta, "members": {}}
        return clusters[cid]

    def add(cid, kw, vol, comp, impr, source, yoy=None, bid=None):
        m = clusters[cid]["members"]
        if kw not in m or (vol is not None and (m[kw]["vol"] is None or vol > m[kw]["vol"])):
            m[kw] = {"kw": kw, "vol": vol, "comp": comp, "impr": impr, "source": source,
                     "yoy": yoy, "bid_hi": bid}

    def match_theme(kw):
        # 0.6 not 0.5: a single token shared with a pattern (e.g. the word "android") is 0.5 for a
        # 2-word keyword and would cross-assign "android contentprovider" to an android-testing
        # theme. 0.6 demands more than one generic word in common.
        for t in themes:
            patt = " ".join(t.get("patterns", []))
            if patt and _bcq.overlap(kw, patt) >= 0.6:
                return t
        return None

    # seed themes get a cluster each so an empty pull still lists them as candidates
    for t in themes:
        ensure(t["id"], {"geo": t.get("geo", "us"), "language": t.get("language", "en"),
                         "proposed_title": t.get("proposed_title", t["id"]),
                         "proven_sibling": t.get("proven_sibling"), "seeded": True})

    open_on = seeds.get("open_clustering", True)
    # every keyword we have a signal for
    seen = set()
    for geo, store in (("us", us_vol), ("bd", bd_vol)):
        for kw, d in store.items():
            seen.add(kw)
            t = match_theme(kw)
            if t and t.get("geo", "us") == geo:
                add(t["id"], kw, d.get("vol"), d.get("comp"), 0, f"planner-{geo}",
                    d.get("yoy"), d.get("bid_hi"))
            elif t is None and open_on:
                toks = [w for w in kw.split() if len(w) > 2][:2]
                if len(toks) >= 2:
                    cid = "open-" + "-".join(toks)
                    ensure(cid, {"geo": geo, "language": "en", "proposed_title": " ".join(toks).title(),
                                 "proven_sibling": None, "seeded": False, "unseeded": True})
                    add(cid, kw, d.get("vol"), d.get("comp"), 0, f"planner-{geo}",
                        d.get("yoy"), d.get("bid_hi"))
    # GSC gaps (impressions, unknown volume) — attach to a theme if matched, else open cluster
    for kw, impr in gaps.items():
        t = match_theme(kw)
        if t:
            add(t["id"], kw, None, None, impr, "gsc-gap")
        elif open_on:
            toks = [w for w in kw.split() if len(w) > 2][:2]
            if len(toks) >= 2:
                cid = "open-" + "-".join(toks)
                ensure(cid, {"geo": "us", "language": "en", "proposed_title": " ".join(toks).title(),
                             "proven_sibling": None, "seeded": False, "unseeded": True})
                add(cid, kw, None, None, impr, "gsc-gap")
    return clusters


# ------------------------------------------------------------------ scoring & refusals
# The course FORMAT should follow what searchers are actually asking for, not a fixed template.
# Classified from the cluster's own member keywords; written into course-task.json so the course
# agent adapts structure (see course-style-guide.md "Intent adaptation"). First match wins, checked
# from most-specific to least; a cluster with no signal defaults to learn-basics (the site's
# established analogy-first format).
_INTENT_RULES = [
    ("troubleshooting", {"error", "fix", "not", "problem", "failed", "issue", "wont", "denied"}),
    ("comparison",      {"vs", "versus", "best", "top", "difference", "better", "alternative"}),
    ("how-to",          {"how", "steps", "guide", "setup", "tutorial", "checklist", "apply", "file"}),
    ("transactional",   {"calculator", "template", "form", "cost", "price", "rates", "quote"}),
]


def classify_intent(members):
    counts = {k: 0 for k, _ in _INTENT_RULES}
    for m in members:
        toks = set(m["kw"].split())
        for name, words in _INTENT_RULES:
            if toks & words:
                counts[name] += 1
                break
    best = max(counts, key=lambda k: counts[k])
    # require a real plurality — at least a third of members — before overriding the default
    return best if counts[best] * 3 >= max(len(members), 1) else "learn-basics"


def trend_multiplier(members):
    """Volume-weighted Planner YoY change -> bounded score nudge. 0.8 (dying) .. 1.4 (growing).
    Bounded because Planner YoY is coarse (+900% breakouts, -100% cliffs) — it should tilt a
    ranking between otherwise-similar clusters, never dominate RPM x volume. None when no member
    has trend data (older exports): multiplier 1.0, and the radar reports trend as unknown."""
    pts = [(m.get("yoy"), (m.get("vol") or 1)) for m in members if m.get("yoy") is not None]
    if not pts:
        return 1.0, None
    wsum = sum(w for _, w in pts)
    yoy = sum(y * w for y, w in pts) / wsum
    return 1.0 + max(-0.5, min(1.0, yoy)) * 0.4, round(yoy, 3)


def score_cluster(c, existing_slugs, existing_titles, us_vol):
    members = list(c["members"].values())
    geo = c.get("geo", "us")
    known = [m for m in members if m["vol"] is not None]
    known_vol = sum(m["vol"] for m in known)
    gap_impr = sum(m["impr"] for m in members)
    # vanity + one-head refusals
    vanity = []
    for m in members:
        win = _bcq.kw_winnability(m["kw"], us_vol) if geo == "us" else None
        if win and win.get("vanity"):
            vanity.append(m["kw"])
    scored_vol = sum(m["vol"] for m in known if m["kw"] not in vanity)
    top_share = (max((m["vol"] for m in known), default=0) / known_vol) if known_vol else 0.0

    # median words per member keyword — the AIO-density proxy (see AIO_LEN_MAX)
    _lens = sorted(len(m["kw"].split()) for m in members) or [0]
    med_len = _lens[len(_lens) // 2]

    status = "candidate"
    if not members:
        status = "empty"
    elif known_vol and top_share > ONE_HEAD_MAX:
        status = "refused-one-head"
    elif med_len >= AIO_LEN_MAX:
        status = "refused-aio-risk"
    else:
        cid_text = f"{c['id']} {c.get('proposed_title','')}"
        for s in existing_slugs:
            if _bcq.overlap(cid_text, existing_titles.get(s, s)) >= DUP_OVERLAP:
                status = "refused-duplicate"
                c["duplicate_of"] = s
                break

    # winnability proxy: median-ish from members' competition
    wins = [_win_from_comp(m["comp"]) for m in known] or [5]
    win = round(sum(wins) / len(wins))
    title_text = " ".join(m["kw"] for m in members[:8]) or c.get("proposed_title", c["id"])
    visitors = int(scored_vol + gap_impr / 3.0)       # rough monthly-visitor proxy

    usd, niche, rpm = 0.0, "unknown", 0.0
    if _HAVE_RPM and status not in ("empty", "refused-one-head", "refused-duplicate", "refused-aio-risk"):
        try:
            # hub=geo is what country_for() needs, but that same argument makes niche_for()
            # skip its hub lookup and keyword-match the title instead — which returned the
            # 'productivity' default ($6.5) for every cluster, so RPM ranked nothing. Resolve the
            # SUBJECT niche separately from the cluster's own keywords and pass it explicitly.
            subject_niche = niche_for("", slug=c["id"], title=title_text)
            r = expected_dollars(slug=c["id"], hub=geo, title=title_text,
                                 visitors_mo=visitors, serp_winnability=win,
                                 niche=subject_niche)
            usd, niche, rpm = r["expected_dollars_mo"], r["niche"], r.get("rpm_mid", 0.0)
        except Exception as e:
            sys.stderr.write(f"  (rpm scoring failed for {c['id']}: {e})\n")

    sibling_bonus = 1.2 if c.get("proven_sibling") else 1.0
    trend_mult, trend_yoy = trend_multiplier(members)
    intent = classify_intent(members)
    # Google's own top-of-page bid for the cluster's keywords — a per-keyword price signal that is
    # sharper than the niche benchmark table. Reported for humans + the course agent; deliberately
    # NOT multiplied into the score (no defensible formula maps bid -> AdSense RPM).
    bids = [m["bid_hi"] for m in members if m.get("bid_hi") is not None]
    avg_bid = round(sum(bids) / len(bids), 2) if bids else None
    score = round(usd * sibling_bonus * trend_mult, 2)
    needs_volume = (known_vol == 0)
    # `and not needs_volume` used to be here. It made the gap_impr branch DEAD CODE: known_vol comes
    # only from manually-exported Planner CSVs, so no pilot could ever be created unless a human sat
    # in Keyword Planner first. That is the one step the owner cannot automate, and it blocked the
    # whole "grows while I sleep" premise. GSC gap impressions are Google's own measured demand for
    # THIS property — a stronger signal than a Planner estimate, not a weaker one. Planner volume is
    # now an accelerator (it sharpens winnability + RPM), never a precondition.
    # `needs_volume` stays in the output so a human reading course-radar.json can still see which
    # clusters are running on GSC evidence alone.
    eligible = (status == "candidate" and len(members) >= MIN_CLUSTER_KW
                and (known_vol >= MIN_CLUSTER_VOL or gap_impr >= MIN_GAP_IMPR))

    return {
        "id": c["id"], "geo": geo, "language": c.get("language", "en"),
        "proposed_title": c.get("proposed_title", c["id"]),
        "proposed_slug": _bcq.slugify(c.get("proposed_title", c["id"]))[:60],
        "status": status, "eligible_for_pilot": eligible, "needs_volume": needs_volume,
        "expected_dollars_mo": score, "niche": niche, "rpm_mid": rpm,
        "intent": intent, "trend_yoy": trend_yoy, "avg_top_bid": avg_bid,
        "known_vol": known_vol, "gap_impressions": gap_impr, "win_proxy": win,
        "median_query_words": med_len,
        "member_count": len(members), "vanity_excluded": vanity,
        "proven_sibling": c.get("proven_sibling"), "duplicate_of": c.get("duplicate_of"),
        "members": sorted(members, key=lambda m: (m["vol"] or 0, m["impr"]), reverse=True)[:40],
        "pilot_outline": [m["kw"] for m in sorted(members, key=lambda m: (m["vol"] or 0, m["impr"]), reverse=True)][:10],
    }


# ------------------------------------------------------------------ outputs
def build_radar(host, cfg):
    data = host / "data"
    us_vol = load_manual_volume(data)
    bd_vol = load_bd_volume(data)
    seeds = load_seeds(host)
    try:
        gaps = gap_queries(cfg)
    except SystemExit as e:
        sys.stderr.write(f"  (GSC gap pull failed: {e})\n")
        gaps = {}
    existing_slugs, existing_titles = existing_courses(host)
    clusters = cluster(seeds, us_vol, bd_vol, gaps)
    scored = [score_cluster(c, existing_slugs, existing_titles, us_vol) for c in clusters.values()]
    scored.sort(key=lambda c: c["expected_dollars_mo"], reverse=True)
    return {
        "generated_at": _today(),
        "site": cfg.get("site_url"),
        "us_keywords": len(us_vol), "bd_keywords": len(bd_vol), "gap_queries": len(gaps),
        "clusters": scored,
    }


def write_radar(host, radar, dry):
    if dry:
        return
    p = host / "data" / "course-radar.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(radar, indent=2, ensure_ascii=False))


# ------------------------------------------------------------------ batch preparation
def prepare_batches(host, radar, dry, force=False):
    """Emit paste-ready Planner batches for clusters that still lack volume. Separate BD + US
    files, each with a LOCATION marker; results drop into 2-DROP-RESULTS-HERE/{bd/,}."""
    data = host / "data"
    state_p = data / "course-radar-batches.json"
    state = {}
    if state_p.exists():
        try:
            state = json.loads(state_p.read_text())
        except Exception:
            state = {}
    if not force and _days_since(state.get("last_prepared")) < RADAR_MIN_DAYS:
        print(f"  batch gate: last prepared {state.get('last_prepared')} < {RADAR_MIN_DAYS}d ago — skip (use --force to override).")
        return
    us_have, bd_have = load_manual_volume(data), load_bd_volume(data)
    need = {"us": [], "bd": []}
    for c in radar["clusters"]:
        if c["status"].startswith("refused"):
            continue
        have = bd_have if c["geo"] == "bd" else us_have
        for m in c["members"]:
            kw = m["kw"]
            if kw and kw not in have and len(kw.split()) <= 10:
                need[c["geo"]].append(kw)
    # ALSO seed each theme's own patterns — a fresh BD theme has no members yet, so without this
    # the owner would never get a batch to pull for it and no BD pilot could ever start.
    for t in load_seeds(host).get("themes", []):
        geo = t.get("geo", "us")
        have = bd_have if geo == "bd" else us_have
        for p in t.get("patterns", []):
            kw = _norm(p)
            if kw and kw not in have and len(kw.split()) <= 10:
                need[geo].append(kw)
    total_new = len(set(need["us"])) + len(set(need["bd"]))
    if not force and total_new < RADAR_MIN_NEW:
        print(f"  batch gate: only {total_new} unpulled cluster keywords (< {RADAR_MIN_NEW}) — skip.")
        return
    up = data / "manual-pull" / "1-UPLOAD-THESE"
    if not dry:
        up.mkdir(parents=True, exist_ok=True)
        (data / "manual-pull" / "2-DROP-RESULTS-HERE" / "bd").mkdir(parents=True, exist_ok=True)
    wrote = []
    for geo, kws in need.items():
        uniq = sorted(set(kws))[:BATCH_MAX]
        if not uniq:
            continue
        fname = f"batch-radar-{geo}-01.csv"
        loc = "Bangladesh" if geo == "bd" else "United States"
        dst = "2-DROP-RESULTS-HERE/bd/" if geo == "bd" else "2-DROP-RESULTS-HERE/"
        if not dry:
            with open(up / fname, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Keyword"])
                for kw in uniq:
                    w.writerow([kw])
            (up / f"_SET-LOCATION-radar-{geo}.txt").write_text(
                f"SET KEYWORD PLANNER LOCATION = {loc}\n{'='*40}\n\n"
                f"Upload {fname} in Keyword Planner (Get search volume and forecasts),\n"
                f"set LOCATIONS = {loc}, then SAVE the results CSV into:\n"
                f"  data/manual-pull/{dst}\n\n"
                f"Wrong location = wrong volume = wasted pull.\n")
        wrote.append(f"{fname} ({len(uniq)} kw, {loc})")
    if not dry:
        state["last_prepared"] = _today()
        state_p.write_text(json.dumps(state, indent=2))
    print("  prepared: " + ("; ".join(wrote) if wrote else "nothing"))


# ------------------------------------------------------------------ lifecycle (measured, not assumed)
def promote(host, cfg, dry):
    """Move pilots through pilot -> expanding -> dormant from MEASURED CLICKS.

    This did not exist. `PILOT_IMPR_FLOOR` was defined and never referenced, and nothing anywhere
    ever set status='expanding', so gate()'s expand branch was unreachable: a pilot could be created
    and then never grow, forever. "Expansion earned by real impressions" was documented as shipped
    and was dead code.

    It gates on CLICKS, not impressions, because impressions are this site's proven failure mode:
    of 747 lessons audited over 90 days, 585 earn impressions and zero clicks, and one takes 1,563
    impressions at position 13.5 for nothing. Promoting on impressions would reward exactly that.
    Dormant is reversible — a course that starts earning clicks is re-promoted, never deleted.
    """
    ledger, corrupt = load_ledger(host)
    pilots = ledger.get("pilots", [])
    if corrupt or not pilots:
        return ledger, []
    try:
        token = _bcq.gsc_token(cfg)
        rows = _bcq.gsc_query(cfg["site_property"], token, ["page"], days=28, row_limit=25000)
    except Exception as e:
        # Never guess a promotion from missing data — a silent GSC failure must not read as
        # "zero clicks" and mark every live course dormant.
        sys.stderr.write(f"  (promotion skipped — GSC page pull failed: {e})\n")
        return ledger, []

    clicks = {}
    for r in rows:
        page = r["keys"][0]
        for p in pilots:
            if f"/lessons/{p.get('slug')}/" in page:
                clicks[p["slug"]] = clicks.get(p["slug"], 0) + int(r.get("clicks", 0))

    changes, today = [], _today()
    for p in pilots:
        c, age, old = clicks.get(p.get("slug"), 0), _days_since(p.get("created")), p.get("status")
        if old in ("pilot", "dormant") and c >= PILOT_CLICK_FLOOR:
            p["status"] = "expanding"
            changes.append(f"{p['slug']}: {old} -> expanding ({c} clicks/28d >= {PILOT_CLICK_FLOOR})")
        elif old in ("pilot", "expanding") and c == 0 and age >= PILOT_DORMANT_DAYS:
            p["status"] = "dormant"
            changes.append(f"{p['slug']}: {old} -> dormant (0 clicks/28d at {age}d old)")
        p["clicks_28d"] = c
        if p.get("status") != old:
            p.setdefault("history", []).append({"date": today, "event": p["status"], "clicks_28d": c})

    if changes and not dry:
        (host / "data" / "course-ledger.json").write_text(
            json.dumps(ledger, indent=2, ensure_ascii=False))
    for ch in changes:
        print(f"  promote -> {ch}")
    return ledger, changes


# ------------------------------------------------------------------ gate (one action for tonight)
def gate(host, radar, dry):
    ledger, corrupt = load_ledger(host)
    existing_slugs, _ = existing_courses(host)
    pilots = ledger.get("pilots", [])
    active = [p for p in pilots if p.get("status") == "pilot"]
    expanding = [p for p in pilots if p.get("status") == "expanding"]

    def emit(task):
        if not dry:
            (host / "data" / "course-task.json").write_text(json.dumps(task, indent=2, ensure_ascii=False))
        print(f"  gate -> {task.get('action')}: {task.get('why','')}")
        return task

    if corrupt:
        return emit({"action": None, "why": "course-ledger.json unreadable — failing closed."})
    # 1) create a pilot?
    last_create = max((_days_since(p.get("created")) for p in pilots), default=10 ** 6)
    top = next((c for c in radar["clusters"] if c["eligible_for_pilot"]
                and c["proposed_slug"] not in existing_slugs), None)
    if top and last_create >= PILOT_CADENCE and len(active) < MAX_ACTIVE:
        return emit({
            "action": "create-pilot", "slug": top["proposed_slug"], "title": top["proposed_title"],
            "language": top["language"], "geo": top["geo"],
            # measured, not assumed: the course agent shapes lesson STRUCTURE to what searchers in
            # this cluster actually ask for (style guide "Intent adaptation" section)
            "intent": top.get("intent", "learn-basics"),
            "trend_yoy": top.get("trend_yoy"), "avg_top_bid": top.get("avg_top_bid"),
            "member_keywords": top["members"], "outline": top["pilot_outline"],
            "style_guide": "scripts/course-style-guide.md",
            "why": f"cluster ${top['expected_dollars_mo']}/mo, niche {top['niche']}, win {top['win_proxy']}/10"
                   + (f", intent {top.get('intent')}" if top.get("intent") else "")
                   + (f", sibling {top['proven_sibling']}" if top['proven_sibling'] else ""),
        })
    # 2) else expand an expanding course
    exp = next((p for p in expanding if _days_since(p.get("last_expanded") or p.get("created")) >= EXPAND_SPACING), None)
    if exp:
        return emit({
            "action": "expand", "slug": exp["slug"],
            "add_lessons": int(os.getenv("TEAMZ_PILOT_EXPAND_PER_WEEK", "5")),
            "why": f"{exp['slug']} is expanding; last grew {exp.get('last_expanded') or exp.get('created')}",
        })
    # 3) nothing
    why = "no eligible cluster" if not top else ("cadence/active-cap not met" if top else "")
    if top and last_create < PILOT_CADENCE:
        why = f"top cluster ready but only {last_create}d since last pilot (< {PILOT_CADENCE})"
    elif top and len(active) >= MAX_ACTIVE:
        why = f"{len(active)} pilots already active (cap {MAX_ACTIVE})"
    return emit({"action": None, "why": why})


# ------------------------------------------------------------------ self-test
def self_test():
    us = {"paycheck calculator": {"vol": 500000.0, "comp": "Low"},
          "1031 exchange rules": {"vol": 400.0, "comp": "Low"},
          "1031 exchange timeline": {"vol": 300.0, "comp": "Low"},
          "1031 exchange calculator": {"vol": 350.0, "comp": "Low"},
          "1031 exchange example": {"vol": 250.0, "comp": "Low"},
          "1031 exchange states": {"vol": 200.0, "comp": "Low"}}
    seeds = {"themes": [
        {"id": "vanity-head", "geo": "us", "patterns": ["paycheck calculator"], "proposed_title": "Paycheck"},
        {"id": "exchange-1031", "geo": "us", "patterns": ["1031 exchange"], "proposed_title": "1031 Exchange"},
    ], "open_clustering": False}
    clusters = cluster(seeds, us, {}, {})
    scored = [score_cluster(c, [], {}, us) for c in clusters.values()]
    by = {c["id"]: c for c in scored}
    ok = True
    # a 500k/mo head term must be refused as one-head (its whole cluster is one dominant term)
    if by["vanity-head"]["status"] != "refused-one-head":
        print(f"  SELFTEST FAIL: vanity head not refused (got {by['vanity-head']['status']})"); ok = False
    else:
        print("  selftest: 500k head term correctly refused-one-head ✓")
    # duplicate refusal
    dupers = [score_cluster(c, ["1031-exchange"], {"1031-exchange": "1031 exchange guide"}, us)
              for c in clusters.values() if c["id"] == "exchange-1031"]
    if dupers and dupers[0]["status"] != "refused-duplicate":
        print(f"  SELFTEST FAIL: duplicate not refused (got {dupers[0]['status']})"); ok = False
    else:
        print("  selftest: overlapping existing course correctly refused-duplicate ✓")
    return 0 if ok else 1


# ------------------------------------------------------------------ main
def main():
    argv = sys.argv[1:]
    if "--self-test" in argv:
        return self_test()
    dry = "--dry-run" in argv
    cfg = load_runtime(__file__)
    host = Path(cfg["host_site_root"])
    radar = build_radar(host, cfg)
    write_radar(host, radar, dry)

    top = [c for c in radar["clusters"] if not c["status"].startswith("refused")][:8]
    print(f"course-radar: {len(radar['clusters'])} clusters "
          f"({radar['us_keywords']} US kw, {radar['bd_keywords']} BD kw, {radar['gap_queries']} gaps)")
    for c in top:
        flag = " ELIGIBLE" if c["eligible_for_pilot"] else (" needs-volume" if c["needs_volume"] else "")
        print(f"  ${c['expected_dollars_mo']:>7}/mo  {c['geo']}  {c['niche']:<14} "
              f"{c['member_count']:>2}kw vol={c['known_vol']:>6} {c['id']}{flag}")
    refused = [c for c in radar["clusters"] if c["status"].startswith("refused")]
    if refused:
        print(f"  ({len(refused)} refused: " + ", ".join(f"{c['id']}:{c['status'].split('-',1)[1]}" for c in refused[:6]) + ")")

    if "--prepare-batches" in argv:
        prepare_batches(host, radar, dry, force="--force" in argv)
    if "--gate" in argv:
        # Lifecycle BEFORE the gate, every night: a course promoted to 'expanding' tonight must be
        # visible to the very gate call that decides tonight's action, or growth lags a full day
        # behind the evidence for it.
        promote(host, cfg, dry)
        gate(host, radar, dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
