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
    """Pages touched by git in the last N days — skip them, they need time to be re-crawled.

    THE ENTRY MUST BE A SUBSTRING OF THE URL, because that is how the caller tests it:

        any(c in path for c in cooldown)      # path == "/products/uruguay-.../"

    The old code only ever stored the FILE ("products/uruguay-.../index.html"). A file path is
    LONGER than the URL it produces, so it can never be a substring of it, so this test could
    only ever return False. The cooldown has therefore never held for any site whose pages are
    <dir>/index.html — which is every static site we own. It merely LOOKED like it worked on
    apps, where Astro's blog/foo.md leaves the usable stem "foo".

    goalkit paid for it on 2026-07-12: the agent edited uruguay-mens, uruguay-youth, netherlands
    and czech at 17:35, and then edited all four AGAIN at 23:32 — rewriting the product names on
    a live shop twice in six hours. Repeated title flips are exactly what makes Google distrust
    a page, so the bug was not just churn; it was working against the thing it exists to do.
    """
    try:
        out = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--name-only", "--pretty=format:"],
            cwd=str(host_root), capture_output=True, text=True, timeout=60,
        ).stdout
    except Exception:
        return set()

    # Language mirrors of one page share a source row (goalkit's manifest) and are always edited
    # together, so touching /bn/products/foo/ must also cool /products/foo/ — otherwise the pair
    # just take turns being re-targeted. Explicit list, not a blind "strip the first directory":
    # tools really does have a /de/ section whose pages are NOT mirrors of the root ones.
    lang_prefixes = {s.strip() for s in os.getenv("TEAMZ_CONTENT_LANG_PREFIXES", "bn").split(",") if s.strip()}

    touched = set()
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        touched.add(line)                       # the raw file, for source-file matches
        p = Path(line)

        if p.name == "index.html" and p.parent != Path("."):
            parts = p.parent.parts
            touched.add("/" + "/".join(parts) + "/")            # /bn/products/foo/
            if parts and parts[0] in lang_prefixes and len(parts) > 1:
                touched.add("/" + "/".join(parts[1:]) + "/")    # ...also cools /products/foo/

        stem = p.stem
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


def looks_like_junk(q):
    """Not every query with impressions is DEMAND. Some are noise, and chasing noise is worse
    than doing nothing — it burns a night and teaches Google nothing.

    learn.teamzlab.com's first queue was almost entirely this: '"73741817" algridtwo',
    '"semanticstester" flutter', 'nctb.claude'. Those are people pasting a code identifier, an
    error string or an exact-match search into Google. There is no page you can write that
    serves them, and no title change that earns their click.
    """
    ql = q.lower().strip()
    if '"' in q:
        return True                                  # exact-match/pasted search
    toks = ql.split()
    for t in toks:
        if t.isdigit() and len(t) >= 5:
            return True                              # an ID, a build number, an error code
        if "." in t and not t.endswith((".com", ".org", ".net", ".io", ".dev")):
            return True                              # dotted identifier: nctb.claude, foo.bar()
        if any(c in t for c in "(){}[]<>;=_"):
            return True                              # code
    # a lone token that is mostly consonants and long is usually an identifier, not a word
    if len(toks) == 1 and len(ql) > 12:
        return True
    return False


def deny_list(env_key):
    raw = os.getenv(env_key, "")
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


def denied(text, patterns):
    t = text.lower()
    return any(p in t for p in patterns)


# --------------------------------------------------------------------------- pools
def edit_mode_for(clicks, floor):
    """ADDITIVE vs FULL — which edits is the agent allowed to make on this page?

    A title rewrite is not a free bet. SearchPilot's bucketed split tests (95% confidence)
    measured a SINGLE title variant costing 16% of organic traffic — 'Flights to London' ->
    'Flights to London (LHR)'. Same corpus: removing listicle numbers -16%, '(video)' labels
    negative in both variants. Titles move traffic in BOTH directions, and Google rewrites
    ~62% of them anyway (Zyppy, n=80,959), so the SERP outcome of an auto-written title is
    even less predictable than the tag we ship.

    That risk would be acceptable if we could SEE the damage. We cannot. apps (41 clicks/28d),
    learn (29) and goalkit (544) are orders of magnitude below the traffic needed to detect a
    16% drop — the engine could degrade them permanently and no signal in this system would
    ever report it. A guard that cannot fire is not a guard.

    So the rule is per-PAGE, not per-property, because it scales itself:

      clicks > floor  -> ADDITIVE. Something already works here. Add an H2, an FAQ, schema.
                         Never touch the title/meta that is earning those clicks.
      clicks <= floor -> FULL. Nothing to lose; a rewrite is free upside.

    A page earning clicks has proven its title works better than our guess. Respect it.
    """
    return "additive" if clicks > floor else "full"


def pool_enhance(prop, token, site_url, cooldown, cfg_min_impr, deny_paths, deny_topics,
                 force_additive=False, click_floor=0):
    """Existing pages that are CLOSE. position 5-25 = one good push from page 1."""
    rows = gsc_query(prop, token, ["page", "query"], days=90, row_limit=2000)
    best = {}   # path -> best opportunity on that page
    for r in rows:
        page, query = r["keys"]
        pos, impr, clicks = r["position"], r["impressions"], r["clicks"]
        if not (5 <= pos <= 25) or impr < cfg_min_impr:
            continue
        if looks_like_junk(query):
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
            emode = "additive" if force_additive else edit_mode_for(clicks, click_floor)
            best[path] = {
                "mode": "ENHANCE", "path": path, "query": query,
                "edit_mode": emode,
                "impressions": int(impr), "clicks": int(clicks),
                "position": round(pos, 1), "ctr": round(r["ctr"] * 100, 2),
                "score": round(score, 1), "source": "striking-distance",
                "why": (f"ranks #{pos:.0f} for '{query}' with {int(impr)} impressions but only "
                        f"{int(clicks)} clicks ({r['ctr']*100:.1f}% CTR) — page 1 is one push away"),
                "edit_mode_why": (
                    f"ADDITIVE — this page already earns {int(clicks)} clicks; its title is "
                    f"proven and must not be rewritten. Add depth only."
                    if emode == "additive" else
                    f"FULL — {int(clicks)} clicks, nothing to lose. Title/meta rewrite allowed."
                ),
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

    out, retarget = [], []
    for r in qrows:
        q = r["keys"][0]
        pos, impr, clicks = r["position"], r["impressions"], r["clicks"]
        if impr < min_impr or pos < 25 or clicks > 0:
            continue          # weak demand, we already rank OK, or it already earns clicks
        if looks_like_junk(q):
            continue          # pasted code / IDs / exact-match searches are not demand
        if denied(q, deny_topics):
            continue          # off-domain topic (see the deny-list note in pool_enhance)

        # KILL 1 — a page we already have is about this query.
        best_sim, best_page = max(((overlap(q, p), p) for p in existing_paths), default=(0.0, ""))
        # KILL 2 — the page Google already picked for it is about this query
        # (covers slugs that never appear in existing_paths, e.g. deep blog URLs).
        rp = ranking_page.get(q, ("", 0))[0]
        owner = ""
        if best_sim >= SIMILARITY_KILL:
            owner = best_page
        elif rp and overlap(q, rp) >= SIMILARITY_KILL:
            owner = rp

        if owner:
            # RETARGET, not "drop".
            #
            # Both kills are RIGHT to refuse a new post — writing one would cannibalise the page
            # that already owns the topic. But the code then just `continue`d, and the demand
            # evaporated. The docstring above literally says "It needs ENHANCING, not a duplicate"
            # about 'cqc compliance software' (125 impr, #70) — and then never made the enhance
            # target. pool_enhance could not rescue it either: its filter stops at position 25.
            #
            # So a query with real demand, sitting at #25-100, on a page we ALREADY OWN, fell
            # into a dead zone that nothing in the engine could see. On apps that was 10 queries
            # and 1,151 impressions being binned every single night, against 66 total clicks.
            #
            # Retargeting beats writing a new post for this demand, and not marginally:
            #   - the URL is already indexed, so it can move in days, not the 2-8 weeks a new
            #     page needs before Google will even rank it;
            #   - it spends none of the 1-2/week NEW budget, so it adds no scaled-content risk;
            #   - it cannot cannibalise — it strengthens the page Google already chose.
            retarget.append({
                "mode": "ENHANCE", "source": "retarget",
                "path": owner, "query": q,
                # ALWAYS additive — never conditional on click count like pool_enhance.
                # The retarget query has 0 clicks BY DEFINITION of this pool, but the owner
                # page may well be earning clicks from OTHER queries we are not looking at
                # here. Rewriting its title to chase this query would gamble a working page
                # on a query it does not yet win. Add a new answer; never rip out its
                # existing identity.
                "edit_mode": "additive",
                "edit_mode_why": ("ADDITIVE — this page owns its topic and may earn clicks from "
                                  "other queries. Add an answer for this one; do not rewrite what "
                                  "already works."),
                "impressions": int(impr), "clicks": int(clicks), "position": round(pos, 1),
                "ctr": 0.0,
                "score": round(impr * (1.0 if pos < 50 else 0.6), 1),
                "why": (f"'{q}' has {int(impr)} impressions in 90 days and we sit at #{pos:.0f} "
                        f"with 0 clicks. We are NOT writing a new page for it — {owner} already "
                        f"owns this topic, and a second page would cannibalise it. Make THAT page "
                        f"actually answer '{q}': it is already indexed, so it can move in days."),
            })
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
    return (sorted(out, key=lambda x: -x["score"]),
            sorted(retarget, key=lambda x: -x["score"]))


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


def brand_tokens(site_url):
    """Tokens of our own brand, derived from the domain.

    Needed because the page-slug brand check is blind on the HOMEPAGE: overlap('teamz lab', '/')
    is zero, since '/' has no tokens. So 'teamz lab' sailed through as a "topic" seed and
    autocomplete expanded it into **'is team lab legit'** — a reputation query. Writing our own
    "are we legit?" blog post is both useless and faintly ridiculous. Brand queries are never
    expansion seeds.
    """
    host = site_url.split("//")[-1].split("/")[0]
    parts = [p for p in host.replace("-", ".").split(".")
             if p not in ("com", "net", "org", "io", "dev", "www", "co", "uk")]
    out = set()
    for p in parts:
        out.add(p)
        for chunk in ("teamz", "lab", "goalkit", "tool", "apps", "learn"):
            if chunk in p and len(chunk) > 2:
                out.add(chunk)
    return out


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

    brand = brand_tokens(site_url)
    rows = gsc_query(prop, token, ["page", "query"], days=90, row_limit=2000)
    seeds = []
    for r in rows:
        page, query = r["keys"]
        path = url_to_path(page, site_url)
        if path not in converting or r["impressions"] < 15:
            continue
        if tokens(query) & brand:
            continue          # our own brand — expands to reputation queries, never to topics
        if denied(query, deny_topics) or denied(path, deny_topics):
            continue
        # A seed must be a TOPIC, not the page's own NAME. Seeding on brand queries is
        # useless: the first run's only seed was 'no trace chat' — the app's own name — and
        # Google autocompleted it to "no trace chatgpt". Worthless. But that same page also
        # ranks for 'invisible chat application', which IS a topic and expands properly.
        # Test: if the query is mostly just the page's own slug, it is a brand query.
        if overlap(query, path) >= SIMILARITY_KILL:
            continue
        if len(tokens(query)) < 2 or looks_like_junk(query):
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
    # load_runtime() FIRST — it is what reads <repo>/.teamz-automation.env into os.environ.
    # argparse used to be built before this call, so every default read os.getenv() while the
    # env file was still unread: TEAMZ_CONTENT_ENHANCE_CAP, NEW_CAP, COOLDOWN and MIN_IMPR were
    # ALL silently ignored whenever the script was run by hand. It only appeared to work because
    # nightly-site.sh sources the env with `set -a` before calling python. Running it standalone
    # used the built-in defaults and quietly queued the wrong things.
    cfg = load_runtime(__file__)

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

    # ADDITIVE-ONLY override. The per-page click rule below already protects any page that is
    # earning clicks, which is the rule that matters. This flag exists for a property that
    # wants belt-and-braces — e.g. a live shop where a bad title costs real money, not rank.
    force_additive = os.getenv("TEAMZ_CONTENT_ADDITIVE_ONLY", "0") == "1"
    click_floor = int(os.getenv("TEAMZ_CONTENT_TITLE_CLICK_FLOOR", "0"))
    if force_additive:
        print("  edit mode  : ADDITIVE-ONLY (forced) — no title/meta rewrites on this property")
    else:
        print(f"  edit mode  : per-page — additive above {click_floor} clicks, full rewrite at or below")

    enhance = pool_enhance(prop, token, site_url, cool, args.min_impressions,
                           deny_paths, deny_topics,
                           force_additive=force_additive, click_floor=click_floor)
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

    # pool_new returns BOTH: the queries with no page behind them (NEW), and the queries it
    # refused to write a post for because a page we already own is about them (RETARGET).
    new, retarget = pool_new(prop, token, site_url, args.min_impressions, existing, deny_topics)

    if new_budget:
        # 2nd choice: net-new ground adjacent to what this site already converts. Only when
        # there is no measured gap — a proxy signal must never outrank a measured one.
        if not new:
            country = os.getenv("TEAMZ_CONTENT_COUNTRY", "us")
            new = pool_expand(prop, token, site_url, existing, deny_topics, country)
        new = new[:new_budget]
    else:
        new = []
        print(f"\n  NEW-post budget spent ({len(recent_new)}/{args.new_cap} this week) — "
              f"enhance-only tonight.")
        print("  (rate limit is deliberate: scaled-content abuse is the #1 risk to this engine)")

    # RETARGET is deliberately NOT rate-limited like NEW. The weekly cap exists to bound
    # scaled-content risk, and that risk comes from PUBLISHING PAGES. A retarget publishes
    # nothing — it is an ENHANCE that happens to carry the keyword the page is missing.
    #
    # It does still respect the cooldown (a page rewritten last night must not be rewritten
    # again tonight — that is the churn bug that rewrote goalkit's product names twice in six
    # hours), and it must never double-book a page the striking-distance pool already picked.
    enhance_capped = enhance[:args.enhance_cap]
    booked = {t["path"] for t in enhance_capped} | {t["path"] for t in cold}
    retarget = [
        t for t in retarget
        if t["path"] not in booked
        and not any(c in t["path"] for c in cool)
        and not denied(t["path"], deny_paths)
    ]

    # ONE PAGE PER DEMAND. Retargeting two pages at the same query would not double the effort —
    # it would sharpen a knife fight between our own pages.
    #
    # apps proved this on the very first run. The pool surfaced BOTH of these:
    #     550 impr  #58.9  /vibe-coding-agency/   <- "vibe coding agency"
    #     142 impr  #36.3  /vibe-coding-service/  <- "vibe coding agence"  (a MISSPELLING of it)
    # That is not two opportunities. That is one demand, already split across two of the five
    # vibe-* pages this site owns — which is precisely WHY an exact-match page sits at #59 for
    # its own exact-match term. Optimising both would have deepened the split we are trying to
    # climb out of.
    #
    # So: same demand -> keep only the strongest page. (Consolidating the five pages into one is
    # the real fix, but that means deleting and redirecting live URLs — a human decision, not a
    # thing an unattended agent should do at 23:00.)
    deduped = []
    for t in retarget:
        if any(overlap(t["query"], k["query"]) >= SIMILARITY_KILL for k in deduped):
            continue        # already retargeting a page for this same demand
        deduped.append(t)
    retarget = deduped[:int(os.getenv("TEAMZ_CONTENT_RETARGET_CAP", "2"))]

    targets = enhance_capped + cold + retarget + new

    queue = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "site": site_url, "property": prop,
        "caps": {"enhance": args.enhance_cap, "new": args.new_cap,
                 "new_budget_tonight": new_budget, "cooldown_days": args.cooldown},
        "pool_counts": {"enhance_found": len(enhance), "cold_start": len(cold),
                        "retarget": len(retarget),
                        "new_found_after_budget": len(new), "cooldown_excluded": len(cool),
                        "additive_protected": sum(1 for t in targets
                                                  if t.get("edit_mode") == "additive")},
        "targets": targets,
    }

    print(f"\n  ENHANCE candidates: {len(enhance)}  (queueing {len(enhance[:args.enhance_cap])})")
    for t in enhance[:args.enhance_cap]:
        guard = "🔒 additive" if t.get("edit_mode") == "additive" else "✏️  full"
        print(f"    #{t['position']:<5} {t['impressions']:>5} impr  {guard:<12} {t['path'][:44]}")
        print(f"           └─ '{t['query'][:56]}'")
    if cold:
        print(f"\n  COLD-START (zero impressions, one shot each): {len(cold)}")
        for t in cold:
            print(f"    never seen by Google:  {t['path'][:56]}")
    if retarget:
        print(f"\n  RETARGET (demand we own a page for but never answer): {len(retarget)}")
        for t in retarget:
            print(f"    #{t['position']:<5} {t['impressions']:>5} impr  {t['path'][:44]}")
            print(f"           └─ must answer: '{t['query'][:52]}'")

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
