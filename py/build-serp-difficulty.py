#!/usr/bin/env python3
"""
build-serp-difficulty.py — MEASURED SEO winnability from real SERP composition.

WHY THIS EXISTS
---------------
build-course-radar.py scored winnability from the Keyword Planner "Competition" column via
_win_from_comp(). That column is ADVERTISER competition — how many people bid on the keyword.
It is not SEO difficulty. A term can be "Low" competition (nobody bids) and still have a top-10
owned entirely by Bankrate and Wells Fargo. Ranking a zero-authority site by that number points
it straight at keywords it cannot win.

This measures the thing we actually care about: WHO ALREADY RANKS. If the top 10 for a keyword
is wall-to-wall national brands, no new page wins it, whatever the CPM says.

SELF-CALIBRATING AUTHORITY — no hardcoded brand list
----------------------------------------------------
A hand-written "big sites" list is just my judgement wearing a data costume. Instead, authority is
derived from the corpus itself: fetch the SERP for every keyword in the batch, count how many
DISTINCT keyword-SERPs each domain appears in, and treat cross-SERP ubiquity as authority. A domain
ranking for 30 of 96 unrelated queries is an authority by demonstration, not by opinion. Re-run on a
different keyword set and the authority set re-derives itself.

Two more measured signals, both standard and both cheap:
  - UGC/forum presence (reddit, quora, stackexchange, forums). Google surfacing UGC is Google saying
    no good dedicated page exists — an opening.
  - Domain diversity. Ten different domains = a contestable SERP; five domains taking ten slots =
    a locked one.

OUTPUT
------
data/serp-difficulty.json — {keyword: {difficulty 1-10, winnability 1-10, domains, ugc, why}}
Cached: a keyword already scored is never re-fetched (Firecrawl credits are finite). --force refetches.

  python3 build-serp-difficulty.py --keywords-from <dir-of-batch-csvs>   # score a batch
  python3 build-serp-difficulty.py --report                              # print, no fetching
  python3 build-serp-difficulty.py --limit N                             # cap credits burned
"""
import csv
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

FIRECRAWL_KEY = Path(os.path.expanduser("~/.config/teamzlab/firecrawl-api-key.txt"))
SEARCH_URL = "https://api.firecrawl.dev/v1/search"
CREDIT_URL = "https://api.firecrawl.dev/v1/team/credit-usage"
TOP_N = int(os.getenv("TEAMZ_SERP_TOP_N", "10"))
RESERVE_CREDITS = int(os.getenv("TEAMZ_FIRECRAWL_RESERVE", "50"))   # never spend the account to zero
# A SERP score is a PERISHABLE measurement, not a fact. Competitors publish, Google reshuffles, a
# term that was open in July can be locked by winter. The first version cached forever, which meant
# the engine would keep ranking clusters on a stale reading and never notice it had gone wrong —
# the failure mode is silent and gets worse with time. Anything older than this is re-measured.
STALE_DAYS = int(os.getenv("TEAMZ_SERP_STALE_DAYS", "90"))

UGC_HOSTS = ("reddit.com", "quora.com", "stackexchange.com", "stackoverflow.com",
             "medium.com", "youtube.com", "facebook.com", "linkedin.com")
UGC_HINTS = ("forum", "community", "answers", "discussion")


def _key():
    if not FIRECRAWL_KEY.exists():
        sys.exit("no firecrawl key at ~/.config/teamzlab/firecrawl-api-key.txt")
    return FIRECRAWL_KEY.read_text().strip()


def credits_left(key):
    try:
        req = urllib.request.Request(CREDIT_URL, headers={"Authorization": f"Bearer {key}"})
        return json.load(urllib.request.urlopen(req, timeout=30))["data"]["remaining_credits"]
    except Exception as e:
        # Unknown balance must never read as "plenty" — fail closed so a batch cannot drain the account.
        sys.stderr.write(f"WARNING: credit check failed ({str(e)[:80]}) — assuming 0 to fail closed.\n")
        return 0


def domain_of(url):
    return re.sub(r"^https?://(www\.)?", "", url or "").split("/")[0].lower()


def fetch_serp(key, kw):
    """Top-N domains for one query. Returns None on failure — NEVER an empty list, which would
    score as a wide-open SERP and promote a keyword on the strength of a network error."""
    req = urllib.request.Request(
        SEARCH_URL,
        data=json.dumps({"query": kw, "limit": TOP_N}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=120))
            return [{"domain": domain_of(x.get("url")), "url": x.get("url", ""),
                     "title": x.get("title", "")} for x in r.get("data", [])]
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            sys.stderr.write(f"  serp fail [{kw}]: {e.code}\n")
            return None
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
                continue
            sys.stderr.write(f"  serp fail [{kw}]: {str(e)[:80]}\n")
            return None
    return None


def authority_index(serps):
    """domain -> how many DISTINCT keyword-SERPs it appears in. Ubiquity == authority, derived
    from this corpus rather than asserted from a hardcoded brand list."""
    c = Counter()
    for results in serps.values():
        for d in {r["domain"] for r in (results or []) if r["domain"]}:
            c[d] += 1
    return c


def _slot_authority(dom, kw, results, auth, corpus_size):
    """Per-slot authority weight in [0,1] — the MAX of four independent measured signals.

    v1 used only cross-SERP ubiquity above a hard cutoff, and it had two defects that a live run on
    96 keywords exposed immediately:
      - SINGLE-TOPIC authorities were invisible. va.gov owns "va loan" outright but appears in one
        SERP of 96, so it scored as a non-authority and the keyword came back max-winnable. Wrong.
      - A hard cutoff made the signal binary, so a dozen keywords tied at the ceiling and the top of
        the range stopped ranking anything.
    Continuous weights + three ubiquity-independent signals fix both.
    """
    # 1) cross-SERP ubiquity, continuous: present in 15% of the corpus = full authority
    w = min(1.0, auth.get(dom, 0) / max(1.0, corpus_size * 0.15))
    # 2) institutional TLD — verifiable from the string, not an opinion about the brand
    if dom.endswith(".gov") or dom.endswith(".edu") or ".gov." in dom or ".edu." in dom:
        w = max(w, 0.9)
    # 3) entrenched on THIS query — one domain holding 2+ of the ten slots
    if sum(1 for r in results if r["domain"] == dom) >= 2:
        w = max(w, 0.7)
    # 4) exact/partial-match domain — a business named after the query is hard to outrank on it
    core = re.sub(r"[^a-z0-9]", "", kw)
    host = re.sub(r"[^a-z0-9]", "", dom.rsplit(".", 1)[0])
    if core and len(core) >= 6 and core in host:
        w = max(w, 0.8)
    return w


def score(kw, results, auth, corpus_size):
    """difficulty 1-10 (10 = hopeless) and its inverse winnability, from measured SERP signals."""
    if not results:
        return None
    doms = [r["domain"] for r in results if r["domain"]]
    if not doms:
        return None
    uniq = set(doms)

    # 1) authority saturation — mean per-slot authority weight across the top 10
    weights = [_slot_authority(d, kw, results, auth, corpus_size) for d in doms]
    auth_share = sum(weights) / len(weights)
    strong = sum(1 for w in weights if w >= 0.5)

    # 2) UGC presence — Google showing forums/Q&A means no strong dedicated page exists.
    ugc = sum(1 for r in results
              if any(h in r["domain"] for h in UGC_HOSTS)
              or any(h in (r["url"] or "").lower() for h in UGC_HINTS))

    # 3) diversity — few domains holding many slots = a locked SERP.
    diversity = len(uniq) / len(doms)

    difficulty = 1.0 + 9.0 * auth_share            # authority saturation is the dominant term
    difficulty -= min(ugc, 3) * 0.4                # UGC opens a SERP, but must not slam it to the floor
    difficulty -= (diversity - 0.8) * 1.5          # diversity measured against a typical 8/10-distinct SERP
    difficulty = max(1.0, min(10.0, difficulty))

    why = f"{strong}/{len(doms)} strong slots (auth {auth_share:.2f})"
    if ugc:
        why += f"; {ugc} UGC = opening"
    if diversity < 0.8:
        why += f"; {len(uniq)} distinct domains"

    return {
        "keyword": kw,
        "difficulty": round(difficulty, 1),
        "winnability": round(11.0 - difficulty, 1),   # 1-10, matches radar's serp_winnability scale
        "authority_share": round(auth_share, 2),
        "strong_slots": strong,
        "ugc_results": ugc,
        "distinct_domains": len(uniq),
        "top_domains": doms[:TOP_N],
        "why": why,
    }


def load_keywords(src):
    kws = []
    for p in sorted(glob.glob(os.path.join(src, "*.csv"))):
        with open(p, newline="", encoding="utf-8-sig") as f:
            for i, row in enumerate(csv.reader(f)):
                if i == 0 or not row or not row[0].strip():
                    continue
                kws.append(row[0].strip().lower())
    seen, out = set(), []
    for k in kws:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def main():
    argv = sys.argv[1:]
    host = Path(os.getenv("TEAMZ_HOST_DIR", ".")).resolve()
    out_p = host / "data" / "serp-difficulty.json"
    cache = {}
    if out_p.exists():
        try:
            cache = json.loads(out_p.read_text()).get("keywords", {})
        except Exception:
            cache = {}

    if "--report" in argv:
        rows = sorted(cache.values(), key=lambda r: r["winnability"], reverse=True)
        print(f"{len(rows)} scored keywords (winnable first)\n")
        for r in rows:
            print(f"  win {r['winnability']:>4}  diff {r['difficulty']:>4}  {r['keyword'][:44]:<46} {r['why']}")
        return 0

    src = None
    if "--keywords-from" in argv:
        src = argv[argv.index("--keywords-from") + 1]
    if not src and "--from-radar" not in argv:
        sys.exit("need --keywords-from <dir with batch CSVs>, --from-radar, or --report")
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 10 ** 6
    force = "--force" in argv

    def _age_days(iso):
        if not iso:
            return 10 ** 6                       # never stamped = treat as maximally stale
        try:
            y, m, d = (int(x) for x in str(iso).split("-")[:3])
            import datetime
            return (datetime.date.today() - datetime.date(y, m, d)).days
        except Exception:
            return 10 ** 6

    key = _key()
    if src:
        kws = load_keywords(src)
    else:
        # Nightly mode: score the member keywords of the clusters the radar ranks highest, so
        # winnability upgrades from inferred to measured exactly where a course might be built.
        # Radar missing = nothing to score = clean no-op, never an error (it runs before the gate).
        rp = host / "data" / "course-radar.json"
        if not rp.exists():
            print("  no course-radar.json yet — nothing to SERP-score.")
            return 0
        try:
            radar = json.loads(rp.read_text())
        except Exception as e:
            print(f"  course-radar.json unreadable ({str(e)[:60]}) — skipping SERP scoring.")
            return 0
        kws = []
        for c in radar.get("clusters", []):
            if c.get("status", "").startswith("refused"):
                continue
            for m in c.get("members", []):
                k = (m.get("kw") or "").strip().lower()
                if k and k not in kws:
                    kws.append(k)
    # Never-scored keywords first (they can unlock a course tonight), then the stalest refreshes.
    # Refreshes ride the same nightly budget, so staleness is worked off continuously instead of
    # needing a human to remember that the numbers have aged.
    fresh = [k for k in kws if k not in cache]
    stale = sorted((k for k in kws if k in cache
                    and _age_days(cache[k].get("scored_at")) >= STALE_DAYS),
                   key=lambda k: -_age_days(cache[k].get("scored_at")))
    todo = (kws if force else fresh + stale)[:limit]
    if stale and not force:
        print(f"  {len(stale)} score(s) older than {STALE_DAYS}d queued for re-measurement")
    left = credits_left(key)
    budget = max(0, left - RESERVE_CREDITS)
    if len(todo) > budget:
        print(f"  credit guard: {len(todo)} keywords but only {budget} spendable "
              f"({left} left, {RESERVE_CREDITS} reserved) — trimming.")
        todo = todo[:budget]
    print(f"{len(kws)} keywords, {len(cache)} cached, fetching {len(todo)} (credits left {left})")

    serps = {k: v.get("_results") for k, v in cache.items() if v.get("_results")}
    today = time.strftime("%Y-%m-%d")
    stamped, failed = {}, []
    for i, kw in enumerate(todo, 1):
        res = fetch_serp(key, kw)
        if res is None:
            failed.append(kw)             # keep the old score rather than dropping the keyword
            continue
        serps[kw] = res
        stamped[kw] = today
        if i % 10 == 0:
            print(f"  … {i}/{len(todo)}")

    auth = authority_index(serps)
    corpus = len(serps)
    scored, moved = {}, []
    for kw, res in serps.items():
        s = score(kw, res, auth, corpus)
        if not s:
            continue
        s["_results"] = res               # cached so a re-run recomputes authority without refetching
        # Keep the ORIGINAL measurement date for anything not refetched this run, so a keyword can
        # never look freshly-verified just because some other keyword was scored today.
        s["scored_at"] = stamped.get(kw) or cache.get(kw, {}).get("scored_at") or today
        prev = cache.get(kw, {}).get("winnability")
        if kw in stamped and prev is not None and abs(prev - s["winnability"]) >= 1.5:
            moved.append((kw, prev, s["winnability"]))
        scored[kw] = s

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%d"),
        "corpus_size": corpus,
        "top_authorities": auth.most_common(25),
        "failed": failed,
        "keywords": scored,
    }, indent=2, ensure_ascii=False))

    ranked = sorted(scored.values(), key=lambda r: r["winnability"], reverse=True)
    print(f"\nscored {len(scored)} keywords; {len(failed)} failed")
    if moved:
        # A SERP that shifted materially is the whole point of re-measuring — say so out loud,
        # otherwise the decay this TTL exists to catch happens silently in a JSON file.
        print("\nWINNABILITY MOVED since last measurement:")
        for kw, old, new in sorted(moved, key=lambda m: m[2] - m[1])[:10]:
            arrow = "↓ harder" if new < old else "↑ easier"
            print(f"  {arrow}  {kw[:40]:<42} {old} -> {new}")
    print("\nMOST WINNABLE:")
    for r in ranked[:12]:
        print(f"  win {r['winnability']:>4}  {r['keyword'][:40]:<42} {r['why']}")
    print("\nLEAST WINNABLE:")
    for r in ranked[-8:]:
        print(f"  win {r['winnability']:>4}  {r['keyword'][:40]:<42} {r['why']}")
    print(f"\ntop authorities: {', '.join(d for d, _ in auth.most_common(10))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
