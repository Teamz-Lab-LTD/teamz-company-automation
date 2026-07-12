#!/usr/bin/env python3
"""
Content Queue Builder — the shared brain of the organic growth engine.

WHY THIS EXISTS
---------------
tool.teamzlab.com grows itself: build-enhance-queue.py picks targets from Search Console,
a nightly Claude agent improves them, gates verify, git commits. It works — tools holds 89%
of all Teamz Lab organic traffic. But build-enhance-queue.py is welded to that ONE site:
it needs tools.json, rising-tools.py, AdSense RPM tables, a [hub]/[slug]/index.html layout.
None of that exists on apps / goalkit / learn.

This is the site-agnostic version. It needs ONLY Search Console — which every property has —
and it answers two questions per night:

  ENHANCE : which EXISTING page is close to winning and deserves a polish?
  NEW     : which query do we get impressions for but have NO real page to serve it?

The second one is what makes the engine write blogs by itself, from demand rather than
from a human's guess.

TARGETING RULES (learned the hard way; do not loosen)
-----------------------------------------------------
  * ENHANCE pool = position 5-25. Below 5 there is little to gain. Past 25 a title tweak
    cannot move it (goalkit's Argentina hub sits at 23 with MORE content than the page that
    beats it — that is competition, not copy).
  * NEW pool = impressions >= threshold AND position >= 25. Google is already showing us for
    the query and we are losing: that is proven demand with no page behind it. The classic
    "high volume, low competition" target, except measured instead of guessed.
  * A query we already rank well for is NEVER a NEW-post topic — that is how a site
    cannibalises itself (four vibe-coding pages split one term and Google ranked the best
    one at position 76).
  * COOLDOWN via git log: a page touched in the last N days is skipped. Without this the
    agent polishes the same page nightly and never moves on.
  * NEW posts are RATE-LIMITED by a ledger (data/content-log.json), default 2/week. Google's
    scaled-content-abuse policy is the single biggest external risk to this whole engine.
    Slow + demand-backed + genuinely useful is the defence. Do not raise this to "more".

Output: <host>/data/content-queue.json   (the agent's ONLY source of targets)

Usage:
  python3 scripts/build-content-queue.py                 # write the queue
  python3 scripts/build-content-queue.py --dry-run       # print, write nothing
  python3 scripts/build-content-queue.py --enhance-cap 5 --new-cap 1
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _teamz_config import load_runtime  # noqa: E402

GSC_API = "https://www.googleapis.com/webmasters/v3/sites"


# --------------------------------------------------------------------------- auth
def gsc_token(cfg):
    tok_path = Path(cfg["sc_token_file"])
    if not tok_path.exists():
        raise SystemExit(f"FATAL: no Search Console token at {tok_path}")
    t = json.loads(tok_path.read_text())
    data = urllib.parse.urlencode({
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    return json.load(urllib.request.urlopen(req, timeout=30))["access_token"]


def gsc_query(prop, token, dimensions, days=90, row_limit=1000):
    """Raw searchAnalytics. A non-200 RAISES — it must never look like 'no data'.

    (Reporting an API rejection as an empty result is exactly how goalkit read as 0 clicks
    for months while really earning 938. An empty queue and a broken queue must never be
    indistinguishable.)
    """
    end = date.today() - timedelta(days=3)      # GSC lags ~2-3 days
    start = end - timedelta(days=days)
    body = json.dumps({
        "startDate": start.isoformat(), "endDate": end.isoformat(),
        "dimensions": dimensions, "rowLimit": row_limit,
    }).encode()
    url = f"{GSC_API}/{urllib.parse.quote(prop, safe='')}/searchAnalytics/query"
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60)).get("rows", [])
    except urllib.error.HTTPError as e:
        raise SystemExit(
            f"FATAL: Search Console returned HTTP {e.code} for property '{prop}'.\n"
            f"       This is NOT 'no data' — the query was rejected.\n"
            f"       URL-prefix properties end in '/', domain properties (sc-domain:) must NOT.\n"
            f"       {e.read()[:200].decode(errors='replace')}"
        )


# --------------------------------------------------------------------------- helpers
def url_to_path(url, site_url):
    """https://apps.teamzlab.com/blog/foo/ -> /blog/foo/"""
    if url.startswith(site_url):
        url = url[len(site_url):]
    p = "/" + url.lstrip("/")
    return p if p.endswith("/") else p + "/"


def cooldown_paths(host_root, days):
    """Pages touched by git in the last N days — skip them, they need time to be re-crawled."""
    try:
        out = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--name-only", "--pretty=format:"],
            cwd=str(host_root), capture_output=True, text=True, timeout=60,
        ).stdout
    except Exception:
        return set()
    touched = set()
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # map a source file back to the URL path it produces, best-effort per platform
        touched.add(line)
        stem = Path(line).stem
        if stem and stem != "index":
            touched.add(stem)
    return touched


def load_ledger(host_root):
    p = host_root / "data" / "content-log.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"new_posts": []}


def new_posts_this_week(ledger):
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    return [e for e in ledger.get("new_posts", []) if e.get("date", "") >= cutoff]


def slugify(q):
    keep = "".join(c if (c.isalnum() or c == " ") else " " for c in q.lower())
    return "-".join(keep.split())[:70]


STOPWORDS = {"the", "a", "an", "for", "of", "in", "to", "and", "or", "vs", "best",
             "top", "free", "online", "how", "what", "is", "are", "with", "my", "your"}


def _stem(w):
    """Crude suffix strip so 'coded' and 'coding' collide.

    Needed because the first dry-run surfaced 'fix my vibe coded app' as a NEW-post
    candidate while /vibe-coding-repair/ already exists — exact-token matching saw
    coded != coding and waved a cannibalising duplicate straight through. Erring toward
    "this is already covered, enhance it instead" is always the safe direction: a missed
    gap costs one night; a duplicate page splits a term permanently.
    """
    for suf in ("ing", "ers", "er", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokens(text):
    keep = "".join(c if (c.isalnum() or c == " ") else " " for c in text.lower())
    return {_stem(w) for w in keep.split() if len(w) > 2 and w not in STOPWORDS}


def overlap(a, b):
    """Fraction of a's meaningful tokens that b also contains. 0.0-1.0."""
    ta, tb = tokens(a), tokens(b)
    if not ta:
        return 0.0
    return len(ta & tb) / len(ta)


def deny_list(env_key):
    raw = os.getenv(env_key, "")
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


def denied(text, patterns):
    t = text.lower()
    return any(p in t for p in patterns)


# --------------------------------------------------------------------------- pools
def pool_enhance(prop, token, site_url, cooldown, cfg_min_impr, deny_paths, deny_topics):
    """Existing pages that are CLOSE. position 5-25 = one good push from page 1."""
    rows = gsc_query(prop, token, ["page", "query"], days=90, row_limit=2000)
    best = {}   # path -> best opportunity on that page
    for r in rows:
        page, query = r["keys"]
        pos, impr, clicks = r["position"], r["impressions"], r["clicks"]
        if not (5 <= pos <= 25) or impr < cfg_min_impr:
            continue
        path = url_to_path(page, site_url)
        if any(c in path for c in cooldown):
            continue
        # DENY LIST — the domain-mismatch guard. A page can rank beautifully and still be
        # worthless: apps.teamzlab.com's price-comparison listicle sits at position 6 with
        # 920 impressions and 0.0% CTR, because nobody clicks a dev-agency subdomain for
        # shopping advice. Ranking is not the goal; the RIGHT ranking is. Without this the
        # agent would polish that dead end every single night, forever.
        if denied(path, deny_paths) or denied(query, deny_topics):
            continue
        # score: impressions we are failing to convert, weighted by how close we are
        proximity = 1.6 if pos <= 12 else (1.2 if pos <= 18 else 1.0)
        score = impr * proximity * (1.0 - min(r["ctr"], 0.10) * 5)
        cur = best.get(path)
        if not cur or score > cur["score"]:
            best[path] = {
                "mode": "ENHANCE", "path": path, "query": query,
                "impressions": int(impr), "clicks": int(clicks),
                "position": round(pos, 1), "ctr": round(r["ctr"] * 100, 2),
                "score": round(score, 1), "source": "striking-distance",
                "why": (f"ranks #{pos:.0f} for '{query}' with {int(impr)} impressions but only "
                        f"{int(clicks)} clicks ({r['ctr']*100:.1f}% CTR) — page 1 is one push away"),
            }
    return sorted(best.values(), key=lambda x: -x["score"])


SIMILARITY_KILL = 0.5   # >= this token overlap with an existing page = NOT a gap


def pool_new(prop, token, site_url, min_impr, existing_paths, deny_topics):
    """Proven demand with NO page behind it.

    A true gap is NOT simply "a query we rank badly for" — every query we get impressions
    for is served by SOME page. A gap is a query whose demand is real and whose best-ranking
    page is about something ELSE. That distinction is the whole safety of this pool, and the
    first dry-run proved why:

      'vibe coding agence'      139 impr, #36  -> a MISSPELLING of a term /vibe-coding-agency/
                                                 already owns. Writing a post for it would
                                                 cannibalise the real page — the exact bug
                                                 that had four vibe pages splitting one term
                                                 until Google ranked the best one at #76.
      'cqc compliance software' 125 impr, #70  -> /blog/best-care-home-compliance-software-uk/
                                                 already targets this. It needs ENHANCING,
                                                 not a duplicate.

    Both are killed by token-overlap: if the query shares >= 50% of its meaningful tokens
    with a page we already have, it is an ENHANCE, not a NEW. Zero gaps on a night is a
    perfectly good answer — far better than inventing a reason to write.
    """
    qrows = gsc_query(prop, token, ["query"], days=90, row_limit=1000)
    prows = gsc_query(prop, token, ["query", "page"], days=90, row_limit=2000)
    ranking_page = {}
    for r in prows:
        q, page = r["keys"]
        cur = ranking_page.get(q)
        if not cur or r["impressions"] > cur[1]:
            ranking_page[q] = (url_to_path(page, site_url), r["impressions"])

    out = []
    for r in qrows:
        q = r["keys"][0]
        pos, impr, clicks = r["position"], r["impressions"], r["clicks"]
        if impr < min_impr or pos < 25 or clicks > 0:
            continue          # weak demand, we already rank OK, or it already earns clicks
        if denied(q, deny_topics):
            continue          # off-domain topic (see the deny-list note in pool_enhance)

        # KILL 1 — a page we already have is about this query.
        best_existing = max((overlap(q, p) for p in existing_paths), default=0.0)
        if best_existing >= SIMILARITY_KILL:
            continue
        # KILL 2 — the page Google already picked for it is about this query
        # (covers slugs that never appear in existing_paths, e.g. deep blog URLs).
        rp = ranking_page.get(q, ("", 0))[0]
        if rp and overlap(q, rp) >= SIMILARITY_KILL:
            continue

        out.append({
            "mode": "NEW", "topic": q, "slug": slugify(q),
            "impressions": int(impr), "clicks": int(clicks), "position": round(pos, 1),
            "score": round(impr * (1.0 if pos < 50 else 0.6), 1),
            "source": "demand-gap",
            "serving_page_today": rp or "(none)",
            "why": (f"Google shows us for '{q}' {int(impr)} times in 90 days but we sit at "
                    f"#{pos:.0f} with 0 clicks, and the page it picks ({rp or 'n/a'}) is not "
                    f"about it — real demand, no page serving it"),
        })
    return sorted(out, key=lambda x: -x["score"])


def pool_coldstart(host, site_url, seen_paths, cooldown, deny_paths, max_out=3):
    """Pages that EXIST and are in the sitemap but have ZERO impressions.

    THE CHICKEN-AND-EGG THIS SOLVES: every other pool is driven by Search Console, so it can
    only ever see pages Google already shows. A page with no impressions is invisible to the
    engine — forever. It never gets improved, so it never gets impressions, so it never gets
    improved.

    goalkit made the cost of that concrete. Its 32 CLUB jerseys (Real Madrid, Barcelona,
    Liverpool, Man Utd…) have zero impressions, so the queue could not see one of them — while
    the pages it COULD see were all World Cup products that die on 2026-07-19. Left alone, the
    engine would have spent every night polishing a dying catalogue and never touched the only
    part that survives.

    Cold-start is ONE-SHOT per page (ledger: data/coldstart-done.txt). A page gets one push —
    internal links, a real title, an honest description — and then it either earns impressions
    and graduates into the normal pools, or it does not. Pushing it forever would just be a
    slower way of ignoring the signal.
    """
    sm = host / "sitemap.xml"
    if not sm.exists():
        return []
    import re as _re
    urls = _re.findall(r"<loc>([^<]+)</loc>", sm.read_text())

    ledger = host / "data" / "coldstart-done.txt"
    done = set(ledger.read_text().split()) if ledger.exists() else set()

    # WITHOUT this, cold-start just walks the sitemap in file order — and the first run picked
    # two BLOG pages (one of them a World Cup guide that dies on 2026-07-19) while the 32 club
    # jerseys, the entire point of the pool, sat further down the file. Sitemap order is not a
    # priority signal. TEAMZ_CONTENT_COLDSTART_PRIORITY says what actually matters.
    priority = deny_list("TEAMZ_CONTENT_COLDSTART_PRIORITY")

    out = []
    for u in urls:
        path = url_to_path(u, site_url)
        if path in seen_paths or path in done:
            continue                       # already earns impressions, or already had its shot
        if denied(path, deny_paths) or any(c in path for c in cooldown):
            continue
        if path.startswith("/bn/"):
            continue                       # Bangla-script search demand is ~zero; do not spend here
        if not (host / path.strip("/") / "index.html").exists():
            continue                       # in the sitemap but not on disk — a different problem
        rank = next((i for i, p in enumerate(priority) if p in path.lower()), len(priority))
        out.append({
            "_rank": rank,
            "mode": "ENHANCE", "path": path, "query": "", "source": "cold-start",
            "impressions": 0, "clicks": 0, "position": 0.0, "ctr": 0.0,
            "score": 0.0, "one_shot": True,
            "why": ("this page exists and is in the sitemap but has ZERO impressions in 90 days "
                    "— Google has not decided it is about anything. Give it a real title, an "
                    "honest description and internal links from pages that DO rank. One shot: "
                    "it will not be queued again."),
        })
    out.sort(key=lambda x: x["_rank"])
    for o in out:
        o.pop("_rank", None)
    return out[:max_out]


def autocomplete(seed, country="us"):
    """Google Autocomplete — free, no auth. Returns suggestions in rank order.

    HONESTY NOTE: autocomplete rank is a WEAK proxy for volume, not volume. It says
    "people type this", not "how many". Every target produced from it is stamped
    volume_proxy=true so nobody downstream mistakes it for measured demand. Real volume
    needs Keyword Planner (one browser consent away — see build-keyword-planner-auth.py).
    """
    url = ("https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl="
           + country + "&q=" + urllib.parse.quote(seed))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace"))
        return data[1] if len(data) > 1 else []
    except Exception:
        return []


def pool_expand(prop, token, site_url, existing_paths, deny_topics, country, max_out=6):
    """NET-NEW topics, expanded from what this site ALREADY PROVES it can win.

    The GSC pools above can only ever see queries we already appear for — so a topic we
    have never ranked for is invisible to them, and the blog writer would never fire on a
    small site (apps.teamzlab.com: 0 gaps found, correctly). This pool is how the engine
    finds genuinely new ground.

    The seeds are NOT guesses. They are the queries where THIS domain already converts —
    its high-CTR pages. On apps.teamzlab.com that means the privacy/secure-chat cluster
    (no-trace-chat, 2.3% CTR), never the price-comparison listicle that ranks at #6 and
    earns 0.0%. Expanding from proven ground is what keeps this from drifting into the
    domain-mismatch trap: we only chase topics adjacent to something we can already win.

    Competition is NOT measured here (no SERP API). The defence is the seed rule above
    plus the hard 2-posts/week ceiling — not a difficulty score we cannot compute.
    """
    # Which pages actually EARN clicks? Those — and only those — are proven ground.
    converting = {}
    for r in gsc_query(prop, token, ["page"], days=90, row_limit=1000):
        if r["clicks"] >= 1:
            converting[url_to_path(r["keys"][0], site_url)] = r["ctr"]

    rows = gsc_query(prop, token, ["page", "query"], days=90, row_limit=2000)
    seeds = []
    for r in rows:
        page, query = r["keys"]
        path = url_to_path(page, site_url)
        if path not in converting or r["impressions"] < 15:
            continue
        if denied(query, deny_topics) or denied(path, deny_topics):
            continue
        # A seed must be a TOPIC, not the page's own NAME. Seeding on brand queries is
        # useless: the first run's only seed was 'no trace chat' — the app's own name — and
        # Google autocompleted it to "no trace chatgpt". Worthless. But that same page also
        # ranks for 'invisible chat application', which IS a topic and expands properly.
        # Test: if the query is mostly just the page's own slug, it is a brand query.
        if overlap(query, path) >= SIMILARITY_KILL:
            continue
        if len(tokens(query)) < 2:
            continue
        seeds.append((converting[path], query, path))
    seeds.sort(reverse=True)

    covered = list(existing_paths) + [r["keys"][1] for r in rows]
    out, seen = [], set()
    for ctr, seed, page in seeds[:6]:                       # top 6 proven-converting queries
        for rank, sug in enumerate(autocomplete(seed, country)):
            s = sug.strip().lower()
            if s == seed.lower() or s in seen or len(s.split()) < 2:
                continue
            if denied(s, deny_topics):
                continue
            if max((overlap(s, c) for c in covered), default=0.0) >= SIMILARITY_KILL:
                continue                                    # we already cover this
            seen.add(s)
            out.append({
                "mode": "NEW", "topic": sug, "slug": slugify(sug),
                "source": "autocomplete-expansion",
                "volume_proxy": True,          # <- NOT measured volume. Do not report as such.
                # Autocomplete DRIFTS. The first run expanded 'vanish text app' into
                # 'remove text app from ipad' — same tokens, opposite intent (that searcher
                # wants to DELETE an app, not find a private messenger). No token heuristic
                # catches that reliably, so the agent must apply the intent gate with full
                # repo context and LOG every rejection. The queue proposes; it never decides.
                "needs_intent_check": True,
                "seed": seed, "seed_page": page, "seed_ctr": round(ctr * 100, 2),
                "autocomplete_rank": rank,
                "score": round(ctr * 100 * (1.0 / (rank + 1)), 3),
                "why": (f"expanded from '{seed}' — a query this site already converts at "
                        f"{ctr*100:.1f}% CTR via {page}. Google autocompletes it, and we have "
                        f"no page for it. Volume is a PROXY (autocomplete rank {rank}), "
                        f"not measured."),
            })
    return sorted(out, key=lambda x: -x["score"])[:max_out]


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enhance-cap", type=int,
                    default=int(os.getenv("TEAMZ_CONTENT_ENHANCE_CAP", "5")))
    ap.add_argument("--new-cap", type=int,
                    default=int(os.getenv("TEAMZ_CONTENT_NEW_CAP", "2")))
    ap.add_argument("--cooldown", type=int, default=int(os.getenv("TEAMZ_CONTENT_COOLDOWN", "7")))
    ap.add_argument("--min-impressions", type=int,
                    default=int(os.getenv("TEAMZ_CONTENT_MIN_IMPR", "25")))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_runtime(__file__)
    host = Path(cfg["host_site_root"])
    site_url = cfg["site_url"]
    prop = cfg["site_property"]

    print("=" * 70)
    print(f"  CONTENT QUEUE — {prop}")
    print(f"  host: {host.name}")
    print("=" * 70)

    token = gsc_token(cfg)
    cool = cooldown_paths(host, args.cooldown)
    deny_paths = deny_list("TEAMZ_CONTENT_DENY_PATHS")
    deny_topics = deny_list("TEAMZ_CONTENT_DENY_TOPICS")
    if deny_paths or deny_topics:
        print(f"  deny paths : {deny_paths or '—'}")
        print(f"  deny topics: {deny_topics or '—'}")

    enhance = pool_enhance(prop, token, site_url, cool, args.min_impressions,
                           deny_paths, deny_topics)
    existing = {e["path"] for e in enhance}
    # every page the property has ANY impression for — so NEW never duplicates a real page
    for r in gsc_query(prop, token, ["page"], days=90, row_limit=1000):
        existing.add(url_to_path(r["keys"][0], site_url))

    # Cold-start reserves a slot or two for pages Google has never shown. Without it, a page
    # with no impressions can never enter the engine at all — see pool_coldstart.
    cold = []
    if os.getenv("TEAMZ_CONTENT_COLDSTART", "0") == "1":
        cold = pool_coldstart(host, site_url, existing, cool, deny_paths,
                              max_out=int(os.getenv("TEAMZ_CONTENT_COLDSTART_CAP", "2")))

    ledger = load_ledger(host)
    recent_new = new_posts_this_week(ledger)
    new_budget = max(0, args.new_cap - len(recent_new))

    new = []
    if new_budget:
        # 1st choice: a MEASURED gap (real impressions, no page serving it). Strongest signal.
        new = pool_new(prop, token, site_url, args.min_impressions, existing, deny_topics)
        # 2nd choice: net-new ground adjacent to what this site already converts. Only when
        # there is no measured gap — a proxy signal must never outrank a measured one.
        if not new:
            country = os.getenv("TEAMZ_CONTENT_COUNTRY", "us")
            new = pool_expand(prop, token, site_url, existing, deny_topics, country)
        new = new[:new_budget]

    if new_budget == 0:
        print(f"\n  NEW-post budget spent ({len(recent_new)}/{args.new_cap} this week) — "
              f"enhance-only tonight.")
        print("  (rate limit is deliberate: scaled-content abuse is the #1 risk to this engine)")

    targets = enhance[:args.enhance_cap] + cold + new

    queue = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "site": site_url, "property": prop,
        "caps": {"enhance": args.enhance_cap, "new": args.new_cap,
                 "new_budget_tonight": new_budget, "cooldown_days": args.cooldown},
        "pool_counts": {"enhance_found": len(enhance), "cold_start": len(cold),
                        "new_found_after_budget": len(new), "cooldown_excluded": len(cool)},
        "targets": targets,
    }

    print(f"\n  ENHANCE candidates: {len(enhance)}  (queueing {len(enhance[:args.enhance_cap])})")
    for t in enhance[:args.enhance_cap]:
        print(f"    #{t['position']:<5} {t['impressions']:>5} impr  {t['path'][:44]}")
        print(f"           └─ '{t['query'][:56]}'")
    if cold:
        print(f"\n  COLD-START (zero impressions, one shot each): {len(cold)}")
        for t in cold:
            print(f"    never seen by Google:  {t['path'][:56]}")

    print(f"\n  NEW-post candidates queued: {len(new)}")
    for t in new:
        if t["source"] == "demand-gap":
            print(f"    MEASURED  {t['impressions']:>5} impr  #{t['position']:<5} '{t['topic'][:44]}'")
            print(f"              └─ Google serves it today with: {t['serving_page_today']}")
        else:
            print(f"    PROXY     autocomplete rank {t['autocomplete_rank']}  '{t['topic'][:44]}'")
            print(f"              └─ expanded from '{t['seed'][:38]}' ({t['seed_ctr']}% CTR)")
        print(f"              └─ slug: {t['slug']}")
    if not targets:
        print("\n  Nothing actionable tonight. That is a valid outcome — not an error.")

    if args.dry_run:
        print("\n  --dry-run: nothing written.")
        return

    out = host / "data" / "content-queue.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(queue, indent=2))
    print(f"\n  Wrote {out}  ({len(targets)} targets)")


if __name__ == "__main__":
    main()
