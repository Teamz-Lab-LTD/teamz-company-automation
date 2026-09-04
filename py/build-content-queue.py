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
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _teamz_config import load_runtime  # noqa: E402
from keyword_volume_manual import load_manual_volume, _norm  # noqa: E402

GSC_API = "https://www.googleapis.com/webmasters/v3/sites"

# Manual Keyword Planner volume (optional, per property). When a property has pulled a batch,
# this tells the engine the TRUE monthly search volume behind a query. It is used to refuse a
# VANITY head term — but ONLY for a brand-NEW post: writing a new page to compete for a 50,000/mo
# head term (apps' "web design") is a doomed 2-8 week bet a small site never wins. It is
# DELIBERATELY NOT used to skip a RETARGET — a retarget publishes nothing, spends no budget, and
# strengthens a page we already own, so even a head term earns an additive pass (it is only
# deprioritised so winnable retargets take the limited slots first). This split matters: an
# earlier version skipped BOTH, which binned real demand on pages we own (goalkit "argentina
# jersey" 12k/mo at #26 on our own product page would have evaporated). With NO volume file every
# lookup returns None and target SELECTION is unchanged.
VANITY_VOL = int(os.getenv("TEAMZ_KW_VANITY_VOL", "10000"))


def kw_winnability(q, kw_vol):
    """Look up MANUAL Keyword Planner volume for a query, if we have it.

    Returns None when there is no volume file or no entry for this query — the engine then
    behaves exactly as before (fail-open: absence of data never changes a decision). Otherwise
    {vol, comp, vanity}: vol may be None = UNKNOWN (a blank Planner cell — never coerced to 0,
    per keyword_volume_manual's unknown!=zero rule). vanity=True means a head term too big for a
    brand-new page to win (vol >= VANITY_VOL); it is advisory and only acted on in the NEW branch.
    """
    if not kw_vol:
        return None
    d = kw_vol.get(_norm(q))
    if not d:
        return None
    vol = d.get("vol")          # may be None = UNKNOWN; do NOT coerce to 0
    return {"vol": vol, "comp": d.get("comp"),
            "vanity": vol is not None and vol >= VANITY_VOL}


_SERP_WIN = {}   # keyword -> measured winnability 1-10, loaded once per run from serp-difficulty.json


def load_serp_winnability(data_dir):
    """Measured SERP winnability, if this property has run build-serp-difficulty.py.

    Missing file -> {} -> notes fall back to volume alone. Never guessed."""
    p = Path(data_dir) / "serp-difficulty.json"
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        return {}
    if not d.get("calibrated", True):
        # Scored on a corpus too small to calibrate — every keyword reads near-unwinnable there.
        # Publishing that into a brief would tell the writer to give up on winnable terms.
        print("  serp win   : serp-difficulty.json is calibrated=false — ignoring (corpus too small)")
        return {}
    return {k.lower(): v for k, v in (d.get("keywords") or {}).items()
            if not v.get("thin_serp")}


def _kw_note(win, q=None):
    """The '[Keyword Planner: ...]' clause for a target's why-string.

    THE WORD "COMPETITION" HERE USED TO BE A LIE BY OMISSION.
    This note is read by the nightly agent that writes the page, and it used to render as
    "~1200/mo, Low competition". That column is Google Ads ADVERTISER competition — how many
    accounts bid — and it is NOT SEO difficulty. The two disagree hard: measured on this property
    2026-08-13, every keyword marked "Low" scored 4.0-5.6 out of 10 on real SERP composition, and
    one marked "Low" (`how to detect spyware on android`) has 7 of 10 slots held by authorities.
    A writer told "Low competition" reasonably concludes the term is winnable and it is not.

    So: the ad metric is now labelled as the ad metric, and where build-serp-difficulty.py has
    MEASURED the SERP, that number leads. Unmeasured stays unmeasured — never substituted."""
    if not win or win.get("vol") is None:
        return ""
    note = f" [Keyword Planner: ~{int(win['vol'])}/mo"
    sw = _SERP_WIN.get((q or "").strip().lower())
    if sw:
        note += f"; MEASURED SERP winnability {sw['winnability']}/10 ({sw['why']})"
    else:
        note += "; SERP not measured"
    comp = win.get("comp")
    if comp:
        note += f"; {comp} ADVERTISER competition (ad bidding, NOT SEO difficulty)"
    return note + "]"


def _attach_kw(target, win):
    """Attach kw_volume/kw_comp ONLY when we actually have volume, so a property with no Planner
    file yields byte-identical targets (no null keys). Returns the dict for chaining."""
    if win and win.get("vol") is not None:
        target["kw_volume"] = win["vol"]
        target["kw_comp"] = win.get("comp")
    return target


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
    # A bulk/sitewide commit that only bumps a cosmetic field (a <meta name="date"> or JSON-LD
    # dateModified stamp) must not cool every file it happens to touch for a full week — that IS
    # a real regression this system hit: learn.teamzlab.com's a03e699 (2026-07-19, "noindex 8
    # zero-click courses, require citations in new lessons") touched 772 files as a side effect,
    # and its ONLY change to most of them was that one date stamp — yet cooldown_paths() treated
    # every one of those 772 pages as freshly rewritten, blocking real enhance candidates (222 of
    # them, measured) for the full 7 days. --numstat instead of --name-only lets us see how much
    # a commit actually changed PER FILE; a touch below the line-count floor is presumed cosmetic
    # and does not cool that file (other, larger touches to the same file in the window still
    # count normally).
    #
    # Floor is 6, not a smaller number, because the cosmetic touch itself isn't uniform: a per-
    # lesson page has ONE date field (2 changed lines), but a course LANDING page
    # (c/<course>.html) restamps THREE separate fields — <meta name="date">, <meta
    # name="last-modified">, and the JSON-LD dateModified — totaling exactly 6 changed lines
    # (confirmed via `git show a03e699 -- c/microprocessor-a-z.html`). A floor of 4 caught the
    # lesson pages but not the landing pages, which is what silently kept blocking the very
    # candidates this fix exists to rescue. This can occasionally let a genuinely tiny real edit
    # through without cooling — a far smaller risk than blanket-cooling the whole site every time
    # a maintenance script runs.
    cosmetic_floor = int(os.getenv("TEAMZ_CONTENT_COOLDOWN_MIN_LINES", "6"))
    try:
        out = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--numstat", "--pretty=format:"],
            cwd=str(host_root), capture_output=True, text=True, timeout=60,
        ).stdout
    except Exception:
        return set()

    real_edit_files = set()
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        ins, dele, fname = parts
        try:
            changed = int(ins) + int(dele)
        except ValueError:
            changed = cosmetic_floor + 1   # binary file ("-\t-\tpath") — can't measure, don't guess small
        if changed > cosmetic_floor:
            real_edit_files.add(fname)

    # Language mirrors of one page share a source row (goalkit's manifest) and are always edited
    # together, so touching /bn/products/foo/ must also cool /products/foo/ — otherwise the pair
    # just take turns being re-targeted. Explicit list, not a blind "strip the first directory":
    # tools really does have a /de/ section whose pages are NOT mirrors of the root ones.
    lang_prefixes = {s.strip() for s in os.getenv("TEAMZ_CONTENT_LANG_PREFIXES", "bn").split(",") if s.strip()}

    # 2026-08-11: apps' own nightly agent flagged src/data/services.ts as invisible to
    # cooldown — content edited there twice in one week and re-served straight away. Root
    # cause: this file backs 18 DIFFERENT pages (a many-to-1 relationship), but the
    # basename-stem heuristic below only ever produces ONE token ("services", from
    # services.ts) — which can't match any of the 18 individual URLs anyway (e.g.
    # "services" is not a substring of "/claude-code-development-service/", singular). No
    # mechanism here has ever been able to cool a shared-data-file page. Fix: when this file
    # is touched, parse the CURRENT file for every `slug: '...'` entry and cool all of
    # them — parsed at runtime (not a hardcoded list) so it can't silently drift out of sync
    # if a service is renamed or added later. Slightly coarse (cools all 18 even if the edit
    # only changed one) but that's the safe direction to be wrong in, same tradeoff already
    # accepted for the cosmetic-floor logic above.
    SHARED_DATA_SLUG_SOURCES = {
        "src/data/services.ts": (host_root / "src" / "data" / "services.ts",
                                  re.compile(r"slug:\s*['\"]([^'\"]+)['\"]")),
    }

    touched = set()
    for line in real_edit_files:
        touched.add(line)                       # the raw file, for source-file matches
        p = Path(line)

        if p.name == "index.html" and p.parent != Path("."):
            parts = p.parent.parts
            touched.add("/" + "/".join(parts) + "/")            # /bn/products/foo/
            if parts and parts[0] in lang_prefixes and len(parts) > 1:
                touched.add("/" + "/".join(parts[1:]) + "/")    # ...also cools /products/foo/

        if line in SHARED_DATA_SLUG_SOURCES:
            src_path, slug_re = SHARED_DATA_SLUG_SOURCES[line]
            try:
                for m in slug_re.finditer(src_path.read_text()):
                    touched.add(f"/{m.group(1)}/")
            except OSError:
                pass   # file unreadable — falls back to the (useless-but-harmless) stem match below

        stem = p.stem
        if stem and stem != "index":
            touched.add(stem)
    return touched


def load_ledger(host_root):
    """Returns (ledger, corrupt). A MISSING file is a legitimate fresh start (empty ledger,
    corrupt=False). A file that EXISTS but won't parse is a silent-killer: the old bare
    `except: pass` treated it as empty, which re-opened the FULL NEW-post budget every night
    (max posts forever — the #1 scaled-content-abuse risk). Signal corruption so the caller
    fails CLOSED (new_budget=0) rather than open."""
    p = host_root / "data" / "content-log.json"
    if not p.exists():
        return {"new_posts": []}, False
    try:
        return json.loads(p.read_text()), False
    except (json.JSONDecodeError, ValueError, OSError) as e:
        sys.stderr.write(
            f"WARNING: {p} exists but is unreadable ({e}). Failing CLOSED — NO new posts "
            f"tonight — so a corrupt ledger cannot silently unlock the rate limiter.\n")
        return {"new_posts": []}, True


def save_ledger(host_root, ledger):
    """Persist the ledger. Same file the NEW-post rate limiter reads (data/content-log.json) —
    one ledger, not two, so a human fixing a corrupt file only has one thing to fix. Caller
    MUST skip this when load_ledger() reported the file corrupt: overwriting a corrupt file
    with a fresh one would silently erase the evidence the NEW-post limiter's fail-closed
    check depends on, and would also wipe retarget history for no reason."""
    p = host_root / "data" / "content-log.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ledger, indent=2))


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


def is_navigational(q, site_url):
    """A query where the searcher ALREADY knows us — there is no ranking upside to win.

    Two shapes:
      site:teamzlab.com      an operator search, not demand (165 impressions on
                             apps.teamzlab.com across 39 pages, 0 clicks — our own auditing)
      teamzlab               the bare brand. We rank #1.1 and #1.6 for it. Rewriting a page to
                             rank better for our own name cannot add a visitor: everyone typing
                             it has already found us.

    Deliberately narrow — it matches the BARE brand only. 'hazira khata' is a product name that
    happens to be the only term that app has, and we rank nowhere near #1 for it, so it must
    stay a legitimate target. Same for 'teamz lab tools', which is brand + a real category word.

    Reuses brand_tokens(), which already derives these from the domain for the NEW-post
    expansion seeds — one definition of "our own name" for the whole queue.
    """
    ql = q.lower().strip()
    if "site:" in ql:
        return True
    squashed = "".join(ch for ch in ql if ch.isalnum())
    return squashed in brand_tokens(site_url)


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


def redirected_paths(host):
    """Paths this site 301s away, read from public/.htaccess — never a queue target.

    GSC keeps reporting a redirected URL for weeks after the redirect ships, because the
    rows are historical and Google consolidates slowly. The queue read those rows as live
    pages and proposed work on them: on 2026-09-04 it queued TWO NEW posts whose stated
    justification was "Google serves it today with: /vibe-coding-consultants/" — a URL
    that had 301'd to /vibe-coding-agency/ since 2026-08-13. Writing new pages into a
    cluster that was just deliberately consolidated is the exact opposite of the fix, and
    the cluster it would have grown was already 3 pages sharing ~1,500 impressions and
    ZERO clicks.

    Editing a redirected page is equally wasted: the file still builds, so an edit looks
    successful, but no visitor can ever reach it.

    Returned lowercased and substring-shaped so they drop straight into deny_paths, which
    every pool already honours.
    """
    ht = Path(host) / "public" / ".htaccess"
    if not ht.exists():
        return []
    out = []
    for line in ht.read_text(errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("#") or "redirectmatch" not in s.lower():
            continue
        parts = s.split()
        if len(parts) < 3:
            continue
        # RedirectMatch [status] <pattern> <target>
        pat = parts[2] if parts[1].isdigit() else parts[1]
        # deny_paths is matched as a SUBSTRING, so only whole-subtree rules are safe to
        # return. `^/vibe-coding-consultants(/.*)?$` redirects the segment and everything
        # under it, so the substring "/vibe-coding-consultants/" can never over-match.
        # `^/hazira-khata/?$` redirects ONLY that exact URL — /hazira-khata/tutorials/*
        # are live pages, and returning the bare prefix here would have denied every one
        # of them. Under-deny rather than silently starve a live section.
        m = re.match(r"\^/([A-Za-z0-9._-]+)\(/\.\*\)\?\$$", pat)
        if m:
            out.append(f"/{m.group(1).lower()}/")
    return sorted(set(out))


def denied(text, patterns):
    t = text.lower()
    return any(p in t for p in patterns)


# ----------------------------------------------------------------- AI channel
AI_SOURCES = ("chatgpt", "openai", "perplexity", "claude", "copilot", "gemini",
              "you.com", "phind", "poe.com", "deepseek", "grok", "mistral")


def ga4_ai_sessions(cfg, days=28):
    """Sessions this property earned from AI assistants, per landing page.

    WHY A GSC-ONLY ENGINE NEEDED THIS. edit_mode decided additive-vs-full from Google clicks
    alone, and on 2026-07-17 that was measured wrong on goalkit's second-best page:

        /products/adidas-argentina-2026-home-jersey-mens/   81 AI sessions   0 Google clicks

    Google clicks = 0, so the rule said "full — nothing to lose, rewrite the title freely". In
    fact ChatGPT sends that page more traffic than Google sends the entire site's top ten. Four
    pages and 171 AI sessions sat unprotected behind a guard that could only see one channel —
    on a property where AI is 42.5% of all sessions and beats Google outright.

    Returns {} on failure. The CALLER must treat {} as "unknown", never as "no AI traffic":
    a guard that cannot read its signal must fail closed, not quietly wave everything through.
    """
    import ssl as _ssl
    tok_path = Path(cfg["ga4_token_file"])
    pid = cfg.get("ga4_property_id")
    if not tok_path.exists() or not pid:
        return {}
    ctx = _ssl.create_default_context()
    try:
        t = json.loads(tok_path.read_text())
        data = urllib.parse.urlencode({
            "client_id": t["client_id"], "client_secret": t["client_secret"],
            "refresh_token": t["refresh_token"], "grant_type": "refresh_token",
        }).encode()
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
        token = json.load(urllib.request.urlopen(req, context=ctx, timeout=30))["access_token"]

        body = json.dumps({
            "dateRanges": [{"startDate": f"{days}daysAgo", "endDate": "today"}],
            "dimensions": [{"name": "landingPagePlusQueryString"}, {"name": "sessionSource"}],
            "metrics": [{"name": "sessions"}],
            "limit": 500,
        }).encode()
        req = urllib.request.Request(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport",
            data=body, method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        rows = json.load(urllib.request.urlopen(req, context=ctx, timeout=90)).get("rows", [])
    except Exception as e:
        print(f"  ⚠️  AI-channel signal UNAVAILABLE ({type(e).__name__}). Failing CLOSED:")
        print("      established pages will be treated as additive-only tonight.")
        return {}

    out = {}
    for r in rows:
        lp = r["dimensionValues"][0]["value"]
        src = r["dimensionValues"][1]["value"].lower()
        if not any(a in src for a in AI_SOURCES):
            continue
        if not lp.startswith("/"):
            continue
        path = lp.split("?")[0]
        path = path if path.endswith("/") else path + "/"
        out[path] = out.get(path, 0) + int(r["metricValues"][0]["value"])
    return out


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


# A title is only "proven" if it EARNS. These are the floors below which, at a given position,
# a title has demonstrably failed rather than merely been untested.
SNIPPET_MIN_IMPR = int(os.getenv("TEAMZ_SNIPPET_MIN_IMPR", "100"))
SNIPPET_CTR_TOP10 = float(os.getenv("TEAMZ_SNIPPET_CTR_TOP10", "0.015"))   # 1.5% by position 10
SNIPPET_CTR_TOP20 = float(os.getenv("TEAMZ_SNIPPET_CTR_TOP20", "0.007"))   # 0.7% by position 20


def title_is_disproven(pos, impr, ctr):
    """True when this page's own Google CTR says the title FAILED, not that it is untested.

    THE HOLE THIS PLUGS. edit_mode_for() is right that a title earning clicks must not be
    rewritten — a single variant has been measured costing 16% of organic traffic. But its test is
    `clicks > floor`, floor defaults to 0, and one click is indistinguishable from a thousand under
    `> 0`. So on apps.teamzlab.com the listicle sitting at position 9.9 with 1,657 impressions and
    ONE click was classified ADDITIVE, and the brief told the agent in as many words: "Its title is
    proven; do not rewrite it." It is the opposite of proven. Measured 2026-08-14: 18 pages, all
    inside the top 25, 6,027 impressions, 22 clicks between them — and the queue had been correctly
    picking several of them for months while forbidding the one edit that addresses the defect. The
    agent rewrote bodies instead, which Google's snippet does not show.

    AI SESSIONS CANNOT VOUCH FOR A TITLE. _enhance_entry adds ai_sessions into the same
    `attention` number. ChatGPT never renders your title tag, so an AI-heavy page can be locked
    into "title proven" by traffic that never saw the title. Only Google CTR is evidence here.

    Conservative on purpose: needs real impressions (noise cannot convict a title), only judges
    inside the top 20 where position sets a fair expectation, and stays silent otherwise — silence
    means today's behaviour, unchanged."""
    if impr < SNIPPET_MIN_IMPR or pos > 20:
        return False
    return ctr < (SNIPPET_CTR_TOP10 if pos <= 10 else SNIPPET_CTR_TOP20)


def _enhance_entry(path, query, pos, impr, clicks, ctr, score, source, why,
                   ai_by_path, ai_known, force_additive, click_floor, extra=None):
    # ATTENTION, not Google clicks. A page can earn nothing from Google and still be
    # one of the property's best performers via ChatGPT — goalkit's Argentina jersey
    # had 81 AI sessions and 0 Google clicks, and the clicks-only rule called it
    # "nothing to lose". If the AI signal could not be read we do NOT assume zero:
    # unknown means fail closed (additive), never "wave it through".
    ai_hits = (ai_by_path or {}).get(path, 0)
    attention = clicks + ai_hits
    # SNIPPET REPAIR outranks the additive lock — but never the explicit --additive flag, and never
    # a failed AI read (fail-closed stays fail-closed). See title_is_disproven().
    snippet = (not force_additive) and ai_known and title_is_disproven(pos, impr, ctr)
    if force_additive or not ai_known:
        emode = "additive"
    elif snippet:
        emode = "full"
    else:
        emode = edit_mode_for(attention, click_floor)
    entry = {
        "mode": "ENHANCE", "path": path, "query": query,
        "edit_mode": emode,
        "impressions": int(impr), "clicks": int(clicks),
        "position": round(pos, 1), "ctr": round(ctr * 100, 2),
        "score": round(score, 1), "source": source,
        "why": why,
        "ai_sessions": int(ai_hits),
        "fix_type": "snippet" if snippet else "content",
        "edit_mode_why": (
            f"SNIPPET REPAIR — this page ranks #{pos:.0f} and Google showed it {int(impr)} times "
            f"for {int(clicks)} click(s) ({ctr * 100:.2f}% CTR). At that position the title has "
            f"FAILED, not gone untested, so the additive lock does not apply. Rewrite the "
            f"metaTitle and description to match how people actually phrase this search — the "
            f"measured queries are listed below. Do NOT pad the body: the body is not what the "
            f"searcher sees. Change the snippet and nothing else, so the next reading of CTR "
            f"attributes cleanly."
            if snippet else
            (f"ADDITIVE — this page already earns {int(clicks)} Google clicks and "
             f"{int(ai_hits)} AI-assistant sessions. Its title is proven; do not rewrite "
             f"it. Add depth only."
             if ai_known else
             "ADDITIVE — the AI-channel signal could not be read tonight, so we cannot "
             "tell what this page earns outside Google. Failing closed: add depth only.")
            if emode == "additive" else
            f"FULL — {int(clicks)} Google clicks and {int(ai_hits)} AI sessions. Nothing "
            f"to lose; title/meta rewrite allowed."
        ),
    }
    if extra:
        entry.update(extra)
    return entry


_NOINDEX_CACHE = {}


def noindex_paths(host):
    """Site paths whose BUILT html carries <meta name="robots" ... noindex>.

    A noindex page cannot gain a search click no matter what is written on it — Google was
    explicitly told to drop it. Queueing one spends a slot on work that is dead by definition.

    apps.teamzlab.com's `/search/` (noindex since 3432b3f, 2026-06-04) consumed an enhance slot
    two nights running; the nightly agent re-verified the noindex with curl and reported it
    BOTH times before this existed. Its 86 impressions are the decaying tail of the 90-day GSC
    window, which is exactly why the GSC-only picker could not see the page was already gone.

    FAILS OPEN. A missing/unbuilt HTML root returns an empty set, so the queue behaves exactly
    as it did before this function existed. The opposite (treating "cannot read" as "noindex")
    would silently empty the enhance pool on any property whose dist/ is not present at pick
    time — a far worse failure than the wasted slot this prevents.
    """
    key = str(host)
    if key in _NOINDEX_CACHE:
        return _NOINDEX_CACHE[key]
    import re as _re
    found = set()
    root = host / os.getenv("TEAMZ_CONTENT_HTML_ROOT", "")
    if not root.exists():
        # FAILING OPEN IS FINE. FAILING OPEN QUIETLY IS NOT. A guard that switches itself
        # off in silence is indistinguishable from a guard that found nothing wrong, and
        # this one returns an empty set on any property whose HTML is not built yet.
        # (This is a separate hole from the /search/ incident of 2026-08-12 — that one was
        # pool_enhance's Pass 3 never consulting `dead` at all. Both were live at once,
        # which is exactly why the empty set needs to announce itself: while chasing that
        # bug, an empty return here was a completely plausible explanation for it.)
        print(f"  noindex guard: OFF tonight — no built HTML at {root} "
              f"(set TEAMZ_CONTENT_HTML_ROOT, or build before queueing). "
              f"noindex pages CAN reach the queue in this state.")
    else:
        for f in root.rglob("index.html"):
            try:
                head = f.read_text(errors="ignore")[:4000]
            except OSError:
                continue
            if _re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex',
                          head, _re.I):
                p = "/" + str(f.parent.relative_to(root)).strip(".").strip("/")
                found.add("/" if p == "/" else p.rstrip("/") + "/")
    _NOINDEX_CACHE[key] = found
    return found


def pool_enhance(prop, token, site_url, cooldown, cfg_min_impr, deny_paths, deny_topics,
                 force_additive=False, click_floor=0, ai_by_path=None, ai_known=True,
                 host=None):
    """Existing pages that are CLOSE. position 5-25 = one good push from page 1.

    Demand is not always one head term. A blog post can rank #10 across 8 different
    long-tail phrasings (35 impr, 22 impr, 14 impr, ...) where NO single phrase clears
    cfg_min_impr alone, even though the page's real opportunity — summed across
    phrasings — is hundreds of impressions. apps.teamzlab.com's
    best-disappearing-messages-apps-2026 post is exactly this: 850 impressions at
    position 10.7 in aggregate, zero queries individually above 25. Pass 1 below is
    the original single-query bar, unchanged — properties whose demand concentrates
    on one head term (tools.teamzlab.com) see no behavior change. Pass 2 rescues
    pages that only clear the bar in aggregate, using their single best-performing
    phrase as the actual content target.
    """
    rows = gsc_query(prop, token, ["page", "query"], days=90, row_limit=2000)
    dead = noindex_paths(host) if host is not None else set()
    grouped = {}   # path -> list of qualifying (position/deny/junk/cooldown-filtered) rows
    best = {}      # path -> best opportunity on that page
    for r in rows:
        page, query = r["keys"]
        pos, impr, clicks = r["position"], r["impressions"], r["clicks"]
        if not (5 <= pos <= 25):
            continue
        if looks_like_junk(query):
            continue
        path = url_to_path(page, site_url)
        if any(c in path for c in cooldown):
            continue
        # NOINDEX = already dead. See noindex_paths(). GSC still reports a decaying 90-day
        # tail for these pages, so position/impressions look like a live opportunity when the
        # page is gone from the index by our own instruction.
        if path in dead:
            continue
        # DENY LIST — the domain-mismatch guard. A page can rank beautifully and still be
        # worthless: apps.teamzlab.com's price-comparison listicle sits at position 6 with
        # 920 impressions and 0.0% CTR, because nobody clicks a dev-agency subdomain for
        # shopping advice. Ranking is not the goal; the RIGHT ranking is. Without this the
        # agent would polish that dead end every single night, forever.
        if denied(path, deny_paths) or denied(query, deny_topics):
            continue
        grouped.setdefault(path, []).append(r)
        if impr < cfg_min_impr:
            continue
        # score: impressions we are failing to convert, weighted by how close we are
        proximity = 1.6 if pos <= 12 else (1.2 if pos <= 18 else 1.0)
        score = impr * proximity * (1.0 - min(r["ctr"], 0.10) * 5)
        cur = best.get(path)
        if not cur or score > cur["score"]:
            why = (f"ranks #{pos:.0f} for '{query}' with {int(impr)} impressions but only "
                   f"{int(clicks)} clicks ({r['ctr']*100:.1f}% CTR) — page 1 is one push away")
            best[path] = _enhance_entry(path, query, pos, impr, clicks, r["ctr"], score,
                                        "striking-distance", why, ai_by_path, ai_known,
                                        force_additive, click_floor)

    # Pass 2 — rescue pages whose demand is real but fragmented across long-tail
    # phrasings, none of which alone clears cfg_min_impr (see docstring above).
    for path, prows in grouped.items():
        if path in best:
            continue
        total_impr = sum(r["impressions"] for r in prows)
        if total_impr < cfg_min_impr:
            continue
        total_clicks = sum(r["clicks"] for r in prows)
        top = max(prows, key=lambda r: r["impressions"])
        query, pos = top["keys"][1], top["position"]
        avg_ctr = total_clicks / total_impr
        proximity = 1.6 if pos <= 12 else (1.2 if pos <= 18 else 1.0)
        score = total_impr * proximity * (1.0 - min(avg_ctr, 0.10) * 5)
        why = (f"ranks position ~{pos:.0f} but demand is split across {len(prows)} phrasings "
               f"(top: '{query}') summing to {int(total_impr)} impressions / {int(total_clicks)} "
               f"clicks — no single phrase alone, but the page is a real page-1 opportunity")
        best[path] = _enhance_entry(path, query, pos, total_impr, total_clicks, avg_ctr, score,
                                    "striking-distance-aggregate", why, ai_by_path, ai_known,
                                    force_additive, click_floor,
                                    extra={"phrase_count": len(prows)})

    # A snippet rewrite is only as good as the wording it is aimed at. Attach the page's real
    # top queries so the agent writes the title against how people actually type the search
    # instead of against the page's own vocabulary. Measured 2026-08-14: the disappearing-messages
    # post ranked #10.5 on "what apps have disappearing messages" / "app that deletes messages
    # after read" — pure question intent — while its title promised "Delete-on-Read vs Timer",
    # a concept comparison. Nobody asking "which app" clicks that. Without these lines the agent
    # would have to guess the intent from the slug, which is how that mismatch happened.
    for path, entry in best.items():
        if entry.get("fix_type") != "snippet":
            continue
        prows = sorted((r for r in grouped.get(path, []) if not looks_like_junk(r["keys"][1])),
                       key=lambda r: -r["impressions"])[:6]
        entry["snippet_queries"] = [
            {"query": r["keys"][1], "impressions": int(r["impressions"]),
             "clicks": int(r["clicks"]), "position": round(r["position"], 1)}
            for r in prows
        ]

    # Pass 3 — rescue pages whose demand GSC has almost entirely anonymized away at the query
    # level. Google suppresses individual query rows for rare/long-tail searches, and on some
    # properties that means Pass 1+2 above — which both only ever see the crossed [page,query]
    # dimension — are structurally blind to most real demand no matter how the aggregation is
    # done, because the crossed rows they operate on never contained that impression volume in
    # the first place. Measured live: learn.teamzlab.com's crossed dimension sees only ~4% of
    # true page-level impressions (extreme long-tail — interview questions, exact error strings),
    # apps ~35%, goalkit ~16%. The [page]-only dimension is aggregated by GSC itself server-side
    # before the same per-query suppression applies, so it recovers the true totals directly.
    # Confirmed on learn: 222 real striking-distance pages (position 5-25, real impressions
    # >=30) exist that Pass 1+2 combined find 3 of.
    anchor_query = {}
    visible_rows = {}      # path -> EVERY visible query row, unfiltered by position
    for r in rows:
        page, query = r["keys"]
        path = url_to_path(page, site_url)
        visible_rows.setdefault(path, []).append(r)
        if looks_like_junk(query) or is_navigational(query, site_url):
            continue           # e.g. 'site:teamzlab.com' — a real top-impression row, not real demand
        cur = anchor_query.get(path)
        if not cur or r["impressions"] > cur["impressions"]:
            anchor_query[path] = {"query": query, "impressions": r["impressions"]}

    page_rows = gsc_query(prop, token, ["page"], days=90, row_limit=2000)
    for r in page_rows:
        path = url_to_path(r["keys"][0], site_url)
        pos, impr, clicks = r["position"], r["impressions"], r["clicks"]
        if path in best or not (5 <= pos <= 25) or impr < cfg_min_impr:
            continue
        if any(c in path for c in cooldown):
            continue
        # NOINDEX — the same gate Pass 1 and Pass 2 apply. Pass 3 was added later and never
        # got it, which made noindex_paths() look broken when it was not: on 2026-08-12 all
        # four of apps.teamzlab.com's ENHANCE targets came from this pass, led by /search/ —
        # noindex since 2026-06-04 and Disallow'd in robots.txt, so nothing written there can
        # ever be read. Running noindex_paths() by hand the next day correctly returned
        # {'/search/', '/fedex-shipping-for-woocommerce/'}; the set was right, this loop just
        # never consulted it. Pass 3 is the pass that finds the most candidates on
        # long-tail-heavy properties, so the one place the gate was missing is the place it
        # mattered most. Found and reported by the nightly agent that same night.
        if path in dead:
            continue
        # THE PAGE-LEVEL AVERAGE CAN BE AN ARTEFACT, AND THE VISIBLE ROWS SAY SO.
        # This pass assumes a page-level position of 5-25 means "page 1 is one push away",
        # which holds only when GSC really is hiding the phrases. When it is NOT hiding them,
        # the average can be a blend of terms we already own and long-tail we can never reach.
        # apps.teamzlab.com, 2026-09-04: "/" was queued at a page-level #10.1 labelled
        # 'teamzlab' — a query we rank #1.6 for. Its other visible rows were site:teamzlab.com
        # (#3.0) and one-impression junk. Same for /teamz-lab-tools/ at #8.4, already #4.9 for
        # its own name and #1.1 for the brand. Two of four ENHANCE slots went, every night, to
        # pages with no reachable upside at all.
        # So: when most of the page's impressions ARE visible, require that at least some of
        # them sit in the striking band on a non-navigational query. If none do, the average is
        # an artefact and there is nothing here to win.
        vis = visible_rows.get(path, [])
        vis_impr = sum(v["impressions"] for v in vis)
        if vis and vis_impr >= 0.5 * impr:
            winnable = sum(v["impressions"] for v in vis
                           if 5 <= v["position"] <= 25
                           and not is_navigational(v["keys"][1], site_url)
                           and not looks_like_junk(v["keys"][1]))
            if winnable == 0:
                continue
        anchor = anchor_query.get(path)
        # A path with zero visible crossed-dimension rows has no query text to check against
        # deny_topics — deny_paths (path-based) still applies and is the primary safety net.
        query = anchor["query"] if anchor else None
        if denied(path, deny_paths) or (query and denied(query, deny_topics)):
            continue
        proximity = 1.6 if pos <= 12 else (1.2 if pos <= 18 else 1.0)
        score = impr * proximity * (1.0 - min(r["ctr"], 0.10) * 5)
        why = (f"ranks #{pos:.0f} with {int(impr)} real impressions / {int(clicks)} clicks "
               f"({r['ctr']*100:.1f}% CTR) — Google hides the individual search phrases here "
               f"(common on long-tail-heavy properties) but the page-level total is a real "
               f"page-1 opportunity" + (f"; closest visible phrase: '{query}'" if query else ""))
        best[path] = _enhance_entry(path, query or "(no individual phrase disclosed by GSC)",
                                    pos, impr, clicks, r["ctr"], score,
                                    "striking-distance-page-level", why, ai_by_path, ai_known,
                                    force_additive, click_floor)

    return sorted(best.values(), key=lambda x: -x["score"])


SIMILARITY_KILL = 0.5   # >= this token overlap with an existing page = NOT a gap


# EXHAUSTION for the retarget cap. TEAMZ_CONTENT_RETARGET_CAP hands out only 2 slots a night,
# by score alone, forever. On apps.teamzlab.com that meant /vibe-coding-agency/ (position ~55)
# and /rag-development-company/ (position ~73) won BOTH slots on 6 and 5 separate nights (git
# log, 2026-07-15 through 07-24) with 0 clicks the entire time — a 45-60 position gap that an
# additive content pass cannot close (needs backlinks/authority, or the sibling-cannibalisation
# consolidation a past nightly run already flagged by hand). Every night they win is a night
# some OTHER real candidate gets nothing.
#
# "Stalled" = still 0 clicks AND position has not improved by RETARGET_STALL_DELTA versus the
# snapshot from RETARGET_EXHAUST_AFTER passes ago (baseline-N-back, not night-to-night — GSC
# position on a 90-day window drifts a couple of points from noise alone, and comparing only
# to the PREVIOUS night would flag genuine slow progress as stalled).
RETARGET_EXHAUST_AFTER = int(os.getenv("TEAMZ_CONTENT_RETARGET_EXHAUST_AFTER", "3"))
RETARGET_EXHAUST_COOLDOWN_DAYS = int(os.getenv("TEAMZ_CONTENT_RETARGET_EXHAUST_COOLDOWN", "60"))
RETARGET_STALL_DELTA = float(os.getenv("TEAMZ_CONTENT_RETARGET_STALL_DELTA", "10"))


def retarget_exhausted_paths(ledger):
    """Paths currently serving an exhaustion cooldown — excluded from tonight's retarget pool
    before the cap runs, so a fresh candidate gets the freed slot instead of nothing."""
    today = date.today().isoformat()
    return {p for p, rec in ledger.get("retargets", {}).items()
            if rec.get("exhausted_until") and rec["exhausted_until"] > today}


def update_retarget_ledger(ledger, chosen):
    """Record tonight's live position/clicks for every path that WON one of the capped
    retarget slots, and demote a path that has now burned RETARGET_EXHAUST_AFTER slots in a
    row with no real payoff into a long cooldown. Uses only numbers pool_new already pulled
    from GSC tonight — no extra API calls, and no dependency on the nightly Claude agent
    remembering to log anything (this is a safety rail, not a nice-to-have)."""
    book = ledger.setdefault("retargets", {})
    today = date.today().isoformat()
    for t in chosen:
        rec = book.setdefault(t["path"], {"history": [], "exhausted_until": None})
        # A path re-surfacing after its cooldown expired gets a clean slate — the 60-day gap
        # is exactly the time a backlink push or a consolidation decision needs to land, and
        # judging it on stale pre-cooldown history would exhaust it again on sight.
        if rec["exhausted_until"] and rec["exhausted_until"] <= today:
            rec["history"], rec["exhausted_until"] = [], None
        hist = rec["history"]
        baseline = hist[-RETARGET_EXHAUST_AFTER] if len(hist) >= RETARGET_EXHAUST_AFTER else None
        hist.append({"date": today, "query": t["query"], "position": t["position"],
                     "clicks": t["clicks"]})
        rec["history"] = hist[-(RETARGET_EXHAUST_AFTER + 1):]   # bounded trend log
        moved = t["clicks"] > 0 or (
            baseline is not None and baseline["position"] - t["position"] >= RETARGET_STALL_DELTA)
        if not moved and len(rec["history"]) > RETARGET_EXHAUST_AFTER \
                and all(e["clicks"] == 0 for e in rec["history"]):
            rec["exhausted_until"] = (date.today()
                                       + timedelta(days=RETARGET_EXHAUST_COOLDOWN_DAYS)).isoformat()


def pool_new(prop, token, site_url, min_impr, existing_paths, deny_topics, kw_vol=None,
             deny_paths=()):
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

    out, retarget, vanity_skipped = [], [], []
    for r in qrows:
        q = r["keys"][0]
        pos, impr, clicks = r["position"], r["impressions"], r["clicks"]
        if impr < min_impr or pos < 25 or clicks > 0:
            continue          # weak demand, we already rank OK, or it already earns clicks
        if looks_like_junk(q):
            continue          # pasted code / IDs / exact-match searches are not demand
        if denied(q, deny_topics):
            continue          # off-domain topic (see the deny-list note in pool_enhance)

        # WINNABILITY — look up the real Planner volume (None when we have no data → no effect).
        # NOT acted on here: the decision differs by branch below. A vanity head term is REFUSED
        # only as a brand-NEW post (a doomed new page), and merely DEPRIORITISED as a retarget (a
        # cheap, safe, additive pass on a page we already own). Skipping here would bin owned-page
        # demand — the exact dead-zone the retarget path exists to fix.
        win = kw_winnability(q, kw_vol)

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
            # A vanity head term is NOT skipped as a retarget (it publishes nothing and
            # strengthens a page we own) — it is only pushed down by a score penalty so genuinely
            # winnable retargets take the limited slots first.
            vanity = bool(win and win["vanity"])
            t = {
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
                "score": round(impr * (1.0 if pos < 50 else 0.6) * (0.3 if vanity else 1.0), 1),
                "why": (f"'{q}' has {int(impr)} impressions in 90 days and we sit at #{pos:.0f} "
                        f"with 0 clicks. We are NOT writing a new page for it — {owner} already "
                        f"owns this topic, and a second page would cannibalise it. Make THAT page "
                        f"actually answer '{q}': it is already indexed, so it can move in days."
                        + _kw_note(win, q)
                        + (" (head term — deprioritised: worth an additive pass but do not expect "
                           "to win it)" if vanity else "")),
            }
            retarget.append(_attach_kw(t, win))
            continue

        # NEW post. This is the ONLY place a vanity head term is refused: a brand-new page needs
        # 2-8 weeks just to index, then competes from scratch against entrenched incumbents — for
        # a 50k/mo head term on a small site that is a guaranteed loss and a wasted NEW-post slot.
        if win and win["vanity"]:
            vanity_skipped.append((q, win["vol"], round(pos, 1)))
            continue

        # If the page Google currently serves for this query is one we 301 away, the whole
        # premise of a NEW post ("real demand, no page serving it") is false — the demand
        # already belongs to the redirect TARGET, and adding a page re-splits the cluster
        # that the redirect was created to consolidate. 2026-09-04: this pool proposed two
        # new pages for 'vibecoding fixing services' and 'vibecoding service and repair',
        # both justified by /vibe-coding-consultants/, which had 301'd three weeks earlier.
        if rp and deny_paths and denied(rp, deny_paths):
            continue

        t = {
            "mode": "NEW", "topic": q, "slug": slugify(q),
            "impressions": int(impr), "clicks": int(clicks), "position": round(pos, 1),
            "score": round(impr * (1.0 if pos < 50 else 0.6), 1),
            "source": "demand-gap",
            "serving_page_today": rp or "(none)",
            "why": (f"Google shows us for '{q}' {int(impr)} times in 90 days but we sit at "
                    f"#{pos:.0f} with 0 clicks, and the page it picks ({rp or 'n/a'}) is not "
                    f"about it — real demand, no page serving it" + _kw_note(win, q)),
        }
        out.append(_attach_kw(t, win))
    return (sorted(out, key=lambda x: -x["score"]),
            sorted(retarget, key=lambda x: -x["score"]),
            vanity_skipped)


def app_blog_coverage(host):
    """{app_slug: how many blog posts link to /app-slug/}.

    Measured on apps.teamzlab.com 2026-08-14, and the result is the clearest correlation on the
    property:

        no-trace-chat      13 posts  -> real non-brand queries ('invisible chat application' etc)
        top3picks           7 posts  -> real non-brand queries
        always-ready-care   4 posts  -> real non-brand queries
        the other 14 apps   0 posts  -> shown almost ONLY for their own brand name
                                        (/devicegpt/ got 5 impressions in 90 days, 4 of them
                                         for the string "device_gpt")

    Nobody searches "brimful". An app landing page has no query of its own to rank for, so the
    blog posts around it are not a nice-to-have — they are the entire non-brand door into it.
    An app with zero posts is structurally unreachable, however good its landing page is."""
    apps_dir = host / "src" / "content" / "apps"
    blog_dir = host / "src" / "content" / "blog"
    if not apps_dir.exists():
        return {}
    slugs = {f.stem for f in apps_dir.glob("*.md")} - {"README", "readme"}
    cov = {s: 0 for s in slugs}
    if blog_dir.exists():
        for f in blog_dir.glob("*.md"):
            txt = f.read_text(errors="ignore")
            for s in slugs:
                if re.search(rf'\]\(/{re.escape(s)}/\)|href="/{re.escape(s)}/"', txt):
                    cov[s] += 1
    return cov


def pool_app_coverage(host, existing, deny_topics, kw_vol=None, cov=None, max_out=1):
    """A NEW post for the app with NO blog behind it — the last-resort NEW candidate.

    This runs only when the measured-demand pool and the autocomplete-expansion pool both came
    back empty, so it can never outrank a measured signal and never inflates the weekly NEW cap.
    It exists because both of those pools ask "which QUERY is unserved", and neither ever asks
    "which of our own products has nothing pointing at it" — so 14 naked apps stayed naked
    indefinitely while the engine polished the three that were already covered.

    The topic comes from the app's OWN declared secondaryKeywords, never invented, and is skipped
    if the site already has a page for it. Volume-ranked where a Keyword Planner pull exists."""
    cov = app_blog_coverage(host) if cov is None else cov
    if not cov:
        return []
    naked = sorted((s for s, n in cov.items() if n == 0), key=lambda s: (cov[s], s))
    out = []
    for slug in naked:
        f = host / "src" / "content" / "apps" / f"{slug}.md"
        try:
            head = f.read_text(errors="ignore").split("\n---", 1)[0]
        except OSError:
            continue
        kws = re.findall(r"^\s{2}-\s+['\"]?(.+?)['\"]?\s*$",
                         (re.search(r"^secondaryKeywords:\n((?:\s{2}-.*\n)+)", head, re.M) or
                          type("x", (), {"group": lambda *_: ""})()).group(1) or "", re.M)
        # NEVER the app page's own primaryKeyword. The first version used it as first choice and
        # produced 'dental practice management software' -> a new blog post, while /alignflow/
        # targets that exact term. That is not coverage, it is a self-inflicted clash: the post
        # would fight the landing page it was written to support. A supporting post must take a
        # DIFFERENT query and hand the authority over via the link. Secondary keywords only.
        pk = re.search(r"^primaryKeyword:\s*['\"]?(.+?)['\"]?\s*$", head, re.M)
        primary = pk.group(1).strip().lower() if pk else None
        cands = [k.strip() for k in kws if k.strip().lower() != primary]
        # Non-Latin targets are a different geo's demand; a US-pull volume on them reads ~0 and
        # would silently rank them last. Skipped rather than mis-scored.
        cands = [c for c in cands if c and all(ord(ch) < 128 for ch in c)]
        best = None
        for c in cands:
            if c.lower() in deny_topics or f"/blog/{slugify(c)}/" in existing:
                continue
            vol = (kw_vol or {}).get(_norm(c), {}).get("vol")
            if best is None or (vol or 0) > (best[1] or 0):
                best = (c, vol)
        if not best:
            continue
        topic, vol = best
        out.append({
            "mode": "NEW", "topic": topic, "slug": slugify(topic),
            "impressions": 0, "clicks": 0, "position": 0.0,
            "score": float(vol or 1),
            "source": "app-coverage",
            "must_link": f"/{slug}/",
            "why": (f"/{slug}/ has ZERO blog posts linking to it. Nobody searches the app's own "
                    f"name, so its landing page has no non-brand door into it — measured on this "
                    f"property, the only three apps with blog coverage are the only three that "
                    f"get non-brand impressions at all. Write a post answering '{topic}' (the "
                    f"app's own declared keyword) and link it to /{slug}/ in the body."
                    + (f" [Keyword Planner: ~{int(vol)}/mo]" if vol else "")),
        })
        if len(out) >= max_out:
            break
    return out


def family_key(path):
    """Pages that are the SAME thing in a different season. The clash-prevention primitive.

    Strip the year from the PATH and see what is left:

        arsenal-2025-26-home-jersey  ->  arsenal--home-jersey   \\ one family:
        arsenal-2026-27-home-jersey  ->  arsenal--home-jersey   / same shirt, two seasons
        arsenal-2025-26-away-jersey  ->  arsenal--away-jersey   <- a DIFFERENT product

    Note this is exact-match on a normalised path, NOT token overlap. Token overlap on these
    same slugs gets it backwards (home-vs-away scores 0.71, the real season duplicate 0.50),
    which is why pool_cannibalization compares titles instead. But for finding season twins
    BEFORE a title exists, the year-stripped path is exactly right.
    """
    import re as _re
    p = YEAR_RE.sub("", path.lower())
    return _re.sub(r"[^a-z]+", "-", p).strip("-")


def title_of(host, path):
    """The <title> a page currently ships, or '' — read from the built HTML on disk."""
    import re as _re
    f = host / path.strip("/") / "index.html"
    if not f.exists():
        return ""
    try:
        m = _re.search(r"<title[^>]*>(.*?)</title>", f.read_text(errors="ignore")[:4000],
                       _re.S | _re.I)
    except OSError:
        return ""
    return _re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


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

    # SEASON TWINS, indexed before we queue anything. Cold-start was a CLASH FACTORY and the
    # proof is in goalkit's git log for 2026-07-17: handed /products/arsenal-2026-27-home-jersey/
    # as a cold-start target, the agent wrote "Arsenal 2026/27 Home Jersey Price in Bangladesh"
    # — a perfect intent-duplicate of the 2025/26 page's existing title. One run, one brand-new
    # clash, and a commit message reporting success.
    #
    # That is not the agent being careless. The catalogue stocks a 2025/26 AND a 2026/27 Home
    # shirt for the same club at the same price, so ANY formulaic "<Club> <Season> Home Jersey
    # Price in Bangladesh" title collides with its twin by construction. Detecting the mess
    # afterwards while another pool manufactures it nightly is mopping the floor with the tap
    # running. So: every cold-start target now arrives KNOWING its twin and what that twin ships.
    all_paths = [url_to_path(u, site_url) for u in urls]
    family = {}
    for p in all_paths:
        family.setdefault(family_key(p), []).append(p)

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
        twins = [{"path": s, "title": title_of(host, s)}
                 for s in family.get(family_key(path), []) if s != path]
        rank = next((i for i, p in enumerate(priority) if p in path.lower()), len(priority))
        out.append({
            "_rank": rank,
            "mode": "ENHANCE", "path": path, "query": "", "source": "cold-start",
            # Non-empty = this page has a season twin. Its title MUST NOT duplicate the twin's
            # intent, however tempting the formula is.
            "season_twins": twins,
            "impressions": 0, "clicks": 0, "position": 0.0, "ctr": 0.0,
            "score": 0.0, "one_shot": True,
            "why": ("this page exists and is in the sitemap but has ZERO impressions in 90 days "
                    "— Google has not decided it is about anything. Give it a real title, an "
                    "honest description and internal links from pages that DO rank. One shot: "
                    "it will not be queued again."
                    + ("" if not twins else
                       " ⚠️ SEASON TWIN: " + "; ".join(
                           f"{t['path']} already ships \"{t['title']}\"" for t in twins)
                       + ". Your title MUST NOT be an intent-duplicate of that. Adding the season "
                         "year is NOT a difference — nobody searching a price types a season. If "
                         "the twin already owns the head term, give THIS page a genuinely "
                         "different intent, or leave its title generic and say so in the report.")),
        })
    out.sort(key=lambda x: x["_rank"])
    for o in out:
        o.pop("_rank", None)
    return out[:max_out]


# ---------------------------------------------------------------- cannibalisation
YEAR_RE = __import__("re").compile(r"\b(?:20\d{2}\s*[/-]\s*\d{2}|20\d{2}|\d{2}\s*/\s*\d{2})\b")


def intent_key(title):
    """What actually competes in a SERP: the title minus the season/year."""
    import re as _re
    # THE STRIPPING ORDER MATTERS, and getting it wrong destroyed a correct fix. The first
    # version cut everything after the FIRST dash. Sites build titles as
    # "{seo_title} — {price} · {brand}", so that was meant to drop the shared brand — but it
    # also deleted any differentiator the agent put in seo_title after a dash. On 2026-07-17 the
    # agent correctly fixed a Bayern clash with:
    #     "Bayern Munich 2025/26 Home Jersey — Last Season — ৳599 · Goalkit"
    #     "Bayern Munich 2026/27 Home Jersey — ৳599 · Goalkit"
    # and this cut BOTH back to "bayern munich home jersey", reported the clash as still live,
    # and would have sent the agent to re-fix a page it had ALREADY fixed — forever, because the
    # fix could never register. The detector was grading work it had already thrown away.
    #
    # So strip precisely what the BUILD adds, and nothing else. Everything the agent wrote
    # survives, dashes included.
    t = (title or "").lower()
    t = _re.sub(r"\s*[·|]\s*[^·|]*$", " ", t)                  # "· Goalkit" / "| Teamz Lab"
    t = _re.sub(r"\s*[—-]\s*[৳$£€₹]\s*[\d,.]+\s*$", " ", t)    # "— ৳599"
    t = YEAR_RE.sub(" ", t)
    return " ".join(sorted(set(_re.findall(r"[a-z']{2,}", t))))


def gsc_cannibalization(prop, token, site_url, deny_paths, min_impr=25, min_pages=2, max_out=8):
    """Cannibalisation MEASURED in GSC: one query, two or more of OUR pages ranking for it.

    pool_cannibalization() below INFERS the same problem from <title> token overlap. That is
    the right tool when Google has not yet shown us both pages, but it cannot see a clash
    whose titles honestly describe different things. apps.teamzlab.com, measured 2026-08-13:

        "vibe coding agency"  950 impressions, 0 clicks
            /vibe-coding-agency/       644 impr  position 69.2
            /vibe-coding-consultants/  306 impr  position 28.6

    Their titles are "Vibe Coding Agency - AI-First App Developers" and "Vibe Coding
    Consultants - AI Dev Tool Stack & Audit": overlap ~0.43, under the 0.5 gate, and the gate
    was RIGHT — an agency and an audit really are different offers. Google disagrees, and
    Google is the one ranking them. The same split runs across the whole cluster ("vibe coding
    consultant", "vibe coding agencies", "vibe coding team"), and the page named for the term
    is the one buried at 69 while its sibling sits at 28. This is the single biggest query on
    that property and it earns nothing.

    Inference is a proxy. This is the measurement. Both stay: this one needs Google to have
    already shown both pages, so it is blind to a clash that has not surfaced yet, which is
    precisely the case the title check catches before it costs anything.

    REPORT ONLY, DELIBERATELY. Fixing a real clash means merging pages, redirecting a URL or
    rewriting an offer — outward-facing decisions with no undo. pool_cannibalization can
    auto-fix its finds because it only touches clashes where every page earns zero clicks;
    here the whole point is that the cluster HAS demand. So this surfaces it and stops.
    """
    rows = gsc_query(prop, token, ["query", "page"], days=90, row_limit=25000)
    by_q = {}
    for r in rows:
        query, page = r["keys"]
        if looks_like_junk(query):
            continue
        path = url_to_path(page, site_url)
        if denied(path, deny_paths):
            continue
        by_q.setdefault(query, []).append(
            {"path": path, "impressions": r["impressions"],
             "clicks": r["clicks"], "position": round(r["position"], 1)})

    out = []
    for query, pages in by_q.items():
        # Only pages with real presence count as competitors — a single stray impression on
        # a fifth page is not a clash, it is noise.
        real = [p for p in pages if p["impressions"] >= 5]
        total = sum(p["impressions"] for p in real)
        if len(real) < min_pages or total < min_impr:
            continue
        real.sort(key=lambda p: -p["impressions"])
        best = min(real, key=lambda p: p["position"])
        out.append({
            "query": query,
            "total_impressions": total,
            "total_clicks": sum(p["clicks"] for p in real),
            "pages": real,
            "best_position": best["position"],
            "best_path": best["path"],
            "why": (f"{len(real)} of our pages rank for '{query}' ({total} impr, "
                    f"{sum(p['clicks'] for p in real)} clicks). Best is {best['path']} at "
                    f"position {best['position']}. Google is splitting the site's signal "
                    f"across them; one page should own this query."),
        })
    out.sort(key=lambda c: -c["total_impressions"])
    return out[:max_out]


def pool_cannibalization(host, site_url, click_by_path, cooldown, deny_paths, max_out=1,
                         ai_by_path=None, ai_known=True):
    """Two of OUR pages chasing ONE query. Detect it nightly and fix it — never by hand.

    The 0.5-token-overlap gate stops a NEW post from duplicating an existing page. Nothing
    stopped ENHANCE and cold-start from doing it one night at a time — and they did. goalkit's
    git log says it in its own words:

        2026-07-15  manchester-city-2025-26-home  -> 'manchester city jersey price in bangladesh'
        2026-07-16  manchester-city-2026-27-home  -> 'manchester city jersey price in bangladesh'

    Two Home pages whose titles differ only by season. Nobody searching that query names a
    season, so Google picks one and the other is dead weight — the same mechanism that put a
    vibe-* page at #59 for its own exact-match term on apps.

    WHY THIS IS A POOL AND NOT A BUILD GATE. A gate would fail the build and hand the fix back
    to a human every time it fired. The owner drives Uber; a guard that needs him is a guard
    that does not run. So the engine finds its own mess and queues it as work.

    WHY IT READS BUILT <title> AND NOT SLUGS. Token overlap on paths gets this exactly backwards
    — measured on the real goalkit slugs:

        2025-26-home vs 2026-27-home  -> 0.50   <- the REAL duplicate (same product, diff season)
        2025-26-home vs 2025-26-away  -> 0.71   <- LEGITIMATE (different product)

    A path-similarity gate blocks the good pair and allows the bad one. The title is what
    competes, so the title is what we compare. Home/away and men's/youth survive, because they
    genuinely separate intent; only the year is discarded.

    SAFETY. Only clashes where EVERY page earns 0 clicks are auto-fixable — nothing to lose, so
    a rewrite is free. If any page in the clash is earning clicks, both are working for someone
    and this is not obviously broken: flag it in the report, change nothing.
    """
    root = host / os.getenv("TEAMZ_CONTENT_HTML_ROOT", "")
    if not root.exists():
        return [], []
    import re as _re

    groups = {}
    for f in root.rglob("index.html"):
        try:
            head = f.read_text(errors="ignore")[:4000]
        except OSError:
            continue
        # NOINDEX PAGES CANNOT CANNIBALISE — Google never indexes them, so they compete for
        # nothing. Skipping this check produced a live false positive on the very first run:
        # apps ships /fedex-shipping-for-woocommerce/ (noindex) and
        # /launch/fedex-shipping-for-woocommerce/ (index) with a byte-identical <title>. That
        # looks like a textbook clash and is not one — the noindex page is invisible to Google
        # by design. Left in, the agent would have spent its highest-priority slot rewriting a
        # page nobody can find, and might have damaged the launch page that actually ranks.
        if _re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex',
                      head, _re.I):
            continue
        m = _re.search(r"<title[^>]*>(.*?)</title>", head, _re.S | _re.I)
        if not m:
            continue
        title = _re.sub(r"\s+", " ", m.group(1)).strip()
        path = "/" + str(f.parent.relative_to(root)).strip(".").strip("/")
        path = "/" if path == "/" else path.rstrip("/") + "/"
        if denied(path, deny_paths):
            continue
        k = intent_key(title)
        if len(k) < 8:
            continue                       # too generic to be a real clash signal
        groups.setdefault(k, []).append((path, title))

    fixable, flagged = [], []
    for members in groups.values():
        if len(members) < 2:
            continue
        # ATTENTION = Google clicks + AI sessions. A clash where one page earns AI citations
        # is not obviously broken — auto-rewriting it could kill a ChatGPT-cited page to "fix"
        # a conflict Google never sees. If the AI signal is unknown, fail closed: flag, never fix.
        aib = ai_by_path or {}
        attention = {p: click_by_path.get(p, 0) + aib.get(p, 0) for p, _ in members}
        protect_at = int(os.getenv("TEAMZ_CONTENT_PROTECT_ATTENTION", "1"))
        if (not ai_known) or any(a >= protect_at for a in attention.values()):
            flagged.append({"paths": [p for p, _ in members],
                            "titles": [t for _, t in members],
                            "attention": attention,
                            "reason": ("AI signal unavailable — failing closed"
                                       if not ai_known else "a page here earns clicks/AI sessions")})
            continue
        # NO COOLDOWN CHECK HERE — deliberately, and this cost a real bug to learn.
        #
        # The first run of this pool did honour the cooldown, and therefore missed the exact
        # clash that motivated it: goalkit's two Man City Home pages were edited the night
        # before, so they were inside the 7-day window and skipped. The cooldown was protecting
        # the defect the engine had itself just created, and would have kept protecting it for
        # a week while both pages split one query.
        #
        # Cooldown exists to stop us re-polishing the same page forever. This is not polish; it
        # is a correctness fix. And it is self-limiting: once the titles genuinely differ there
        # is no clash, so no target. If a fix does not work, retrying tomorrow is what we want.
        fixable.append({
            "mode": "ENHANCE", "source": "cannibalization",
            "path": members[0][0],
            "rival_paths": [p for p, _ in members[1:]],
            "query": "", "edit_mode": "full",
            "edit_mode_why": ("FULL — every page in this clash earns 0 clicks. Nothing to lose; "
                              "differentiating the titles is the whole fix."),
            "impressions": 0, "clicks": 0, "position": 0.0, "ctr": 0.0,
            "score": 0.0,
            "competing": [{"path": p, "title": t} for p, t in members],
            "why": ("these pages carry near-identical titles once the season/year is stripped, so "
                    "they chase ONE query and split it between them. Google will pick one; the rest "
                    "are dead weight. Decide which page best matches what a buyer searching this "
                    "actually wants, let THAT one keep the head term, and differentiate the others "
                    "so each owns a distinct intent. All are at 0 clicks — nothing can be lost."),
        })
    return fixable[:max_out], flagged


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
    # A 301'd URL is not a page. GSC still reports it for weeks, so it must be denied
    # explicitly or the queue proposes work no visitor can ever reach.
    _redirected = redirected_paths(host)
    if _redirected:
        deny_paths = sorted(set(deny_paths) | set(_redirected))
        print(f"  redirected : {_redirected}  (auto-denied — 301s, not pages)")
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

    # Manual Keyword Planner volume, if this property has pulled a batch. Turns on winnability:
    # the engine can now refuse vanity head terms instead of chasing impressions it can't convert.
    # Absent -> {} -> every winnability check returns None -> engine behaves exactly as before.
    try:
        kw_vol = load_manual_volume(host / "data")
        _SERP_WIN.update(load_serp_winnability(host / "data"))
    except Exception:
        kw_vol = {}
    if kw_vol:
        print(f"  kw volume  : {len(kw_vol)} terms (winnability ON — head terms >= {VANITY_VOL}/mo "
              f"refused as NEW posts, deprioritised as retargets)")
    else:
        print("  kw volume  : none pulled yet (winnability off — pull a Keyword Planner batch to enable)")

    # AI-channel signal, fetched once and shared by every pool. ai_known=False when the fetch
    # failed — the pools then fail CLOSED (treat established pages as additive, flag clashes
    # rather than auto-fix), because a guard that cannot read its signal must not wave work
    # through. This is the "pull the funnel, never the total" rule made structural.
    ai_by_path = ga4_ai_sessions(cfg)
    ai_known = bool(ai_by_path)
    if ai_known:
        print(f"  AI channel : {sum(ai_by_path.values())} sessions across {len(ai_by_path)} pages (28d)")
    else:
        print("  AI channel : UNAVAILABLE — pools fail closed (additive/flag-only) tonight")

    # APP COVERAGE — reported every night whether or not it drives a target tonight, because a
    # naked app is a standing structural gap, not a one-off task. 14 of 17 were naked on
    # 2026-08-14 and nothing in this engine had ever mentioned it.
    _app_cov = app_blog_coverage(host)
    if _app_cov:
        _naked = sorted(s for s, n in _app_cov.items() if n == 0)
        _covered = sum(1 for n in _app_cov.values() if n)
        print(f"  app coverage: {_covered}/{len(_app_cov)} app page(s) have a blog behind them"
              + (f" — NAKED: {', '.join(_naked[:8])}" + ("…" if len(_naked) > 8 else "")
                 if _naked else " — all covered"))


    enhance = pool_enhance(prop, token, site_url, cool, args.min_impressions,
                           deny_paths, deny_topics,
                           force_additive=force_additive, click_floor=click_floor,
                           ai_by_path=ai_by_path, ai_known=ai_known, host=host)

    # Value weighting. Until now this queue ranked purely on impressions x rank proximity,
    # so on apps.teamzlab.com a page with 500 impressions and zero store clicks outranked one
    # with 200 impressions and 12 — the queue could not see conversion at all. Multiply the
    # SORT KEY by how well each page converts its own visitors, using whichever event this
    # property declares as valuable (TEAMZ_VALUE_EVENTS in its .teamz-automation.env).
    # Unset, unreachable, or no page with enough data -> None -> ranking untouched.
    try:
        import revenue_signals as _rs
        _val = _rs.conversion_value(cfg)
    except Exception as e:  # noqa: BLE001
        print(f"  value layer skipped ({type(e).__name__}) — impressions-only ranking")
        _val = None
    if _val:
        import statistics as _st
        _med = _st.median(_val.values())
        # Section medians carry the signal to candidates too small to have their own rate —
        # which is most of them, since this queue targets underperforming pages by design.
        _sect = _rs.section_value(_val)
        _srcs = {}
        for t in enhance:
            rate, src = _rs.value_for(t["path"], _val, _sect)
            _srcs[src] = _srcs.get(src, 0) + 1
            # 'none' -> weight 1.0: unknown must not be scored as zero-value, or every page
            # the layer cannot see gets pushed below every page it can.
            w = _rs.value_weight(rate, _med) if rate is not None else 1.0
            t["value_per_1k"] = rate
            t["value_source"] = src
            t["value_weight"] = round(w, 2)
            t["score"] = round(t["score"] * w, 1)
        enhance.sort(key=lambda x: -x["score"])
        print(f"  value layer: re-ranked by measured conversion "
              f"(median {_med:.2f} per 1k sessions; {len(_sect)} section(s) calibrated) — "
              + ", ".join(f"{k}={v}" for k, v in sorted(_srcs.items())))

    existing = {e["path"] for e in enhance}
    # every page the property has ANY impression for — so NEW never duplicates a real page
    click_by_path = {}
    for r in gsc_query(prop, token, ["page"], days=90, row_limit=1000):
        p = url_to_path(r["keys"][0], site_url)
        existing.add(p)
        click_by_path[p] = click_by_path.get(p, 0) + int(r["clicks"])

    # Cold-start reserves a slot or two for pages Google has never shown. Without it, a page
    # with no impressions can never enter the engine at all — see pool_coldstart.
    cold = []
    if os.getenv("TEAMZ_CONTENT_COLDSTART", "0") == "1":
        cold = pool_coldstart(host, site_url, existing, cool, deny_paths,
                              max_out=int(os.getenv("TEAMZ_CONTENT_COLDSTART_CAP", "2")))

    # CANNIBALISATION — our own pages fighting each other. Queued as WORK, never as a build
    # failure: a gate that fires would hand the fix back to a human every night, and the whole
    # point of this engine is that nobody is there to catch it.
    canni, canni_flagged = pool_cannibalization(
        host, site_url, click_by_path, cool, deny_paths,
        max_out=int(os.getenv("TEAMZ_CONTENT_CANNIBAL_CAP", "1")),
        ai_by_path=ai_by_path, ai_known=ai_known)

    # Measured clashes, from GSC rather than from title similarity. Report-only — see the
    # docstring for why this one never auto-fixes.
    try:
        gsc_canni = gsc_cannibalization(prop, token, site_url, deny_paths)
    except Exception as e:  # noqa: BLE001
        # An API failure here must not take the night's queue down, but it must also not be
        # mistaken for "no clashes found".
        print(f"  ⚠️  measured-cannibalisation check UNAVAILABLE ({type(e).__name__}) — "
              f"title-overlap check still ran")
        gsc_canni = None
    if gsc_canni:
        top = gsc_canni[0]
        print(f"  cannibalisation (measured): {len(gsc_canni)} quer(y/ies) split across our own "
              f"pages — worst '{top['query']}' {top['total_impressions']} impr / "
              f"{top['total_clicks']} clicks over {len(top['pages'])} pages")
    elif gsc_canni is not None:
        print("  cannibalisation (measured): none — no query has 2+ of our pages ranking")

    ledger, ledger_corrupt = load_ledger(host)
    recent_new = new_posts_this_week(ledger)
    # Corrupt ledger => fail CLOSED. Treating an unreadable log as "0 posts this week" would
    # reopen the full weekly budget every night — exactly the scaled-content flood the cap exists
    # to prevent. No trustworthy count => no new posts.
    new_budget = 0 if ledger_corrupt else max(0, args.new_cap - len(recent_new))

    # pool_new returns BOTH: the queries with no page behind them (NEW), and the queries it
    # refused to write a post for because a page we already own is about them (RETARGET).
    new, retarget, vanity_skipped = pool_new(prop, token, site_url, args.min_impressions,
                                             existing, deny_topics, kw_vol=kw_vol,
                                             deny_paths=deny_paths)

    # A QUERY WE ARE ALREADY SPLITTING IS NOT AN UNSERVED GAP.
    # pool_new's demand-gap test is "impressions are real AND our best position is >= 25" —
    # nobody of ours RANKS, so it reads as open ground. That test cannot tell "no page
    # addresses this" from "two pages address it and cancel each other out". Measured on
    # apps.teamzlab.com 2026-08-13, the queue's only NEW candidate was:
    #
    #     'cqc audit software'  33 impr, best position #65
    #         /blog/best-care-home-compliance-software-uk-2026/   #63.7
    #         /always-ready-care/                                 #83.4
    #
    # Two pages already trying and both buried — so the engine was about to write a THIRD
    # and split it three ways. It even printed "Google serves it today with: <page>" one line
    # before queueing the duplicate. gsc_cannibalization() knows this; nothing consulted it.
    #
    # RETARGET is untouched on purpose: pointing an existing page at the query is the correct
    # response to a clash. Only writing a brand-new competitor is refused.
    if new and gsc_canni:
        clashing = {c["query"].strip().lower() for c in gsc_canni}
        kept = []
        for t in new:
            topic = str(t.get("topic", "")).strip().lower()
            if topic in clashing:
                pages = next(c["pages"] for c in gsc_canni
                             if c["query"].strip().lower() == topic)
                print(f"  NEW refused (cannibalisation): '{t.get('topic')}' — "
                      f"{len(pages)} of our pages already compete for it "
                      + ", ".join(f"{p['path']} #{p['position']}" for p in pages[:3])
                      + ". A third page would split it further; strengthen one of these instead.")
                continue
            kept.append(t)
        new = kept

    if new_budget:
        # 2nd choice: net-new ground adjacent to what this site already converts. Only when
        # there is no measured gap — a proxy signal must never outrank a measured one.
        if not new:
            country = os.getenv("TEAMZ_CONTENT_COUNTRY", "us")
            new = pool_expand(prop, token, site_url, existing, deny_topics, country)

        # 3rd choice: an app with NOTHING pointing at it. Last, so a measured query always wins,
        # and inside new_budget, so the weekly NEW cap is untouched. See pool_app_coverage().
        if not new:
            new = pool_app_coverage(host, existing, deny_topics, kw_vol=kw_vol, cov=_app_cov)
            for t in new:
                print(f"  NEW (app coverage): '{t['topic']}' -> must link {t['must_link']} "
                      f"— that app has zero blog posts behind it.")

        # DO NOT SHIP TOMORROW'S CANNIBALISATION TONIGHT.
        # pool_expand scores autocomplete suggestions independently, so near-duplicates of
        # each other both survive. Measured on apps.teamzlab.com 2026-08-13, the two NEW
        # candidates for one night were:
        #
        #     'offline chat app without internet'
        #     'offline chat app without internet for android'
        #
        # One topic is a strict superset of the other. Writing both creates exactly the clash
        # gsc_cannibalization() now reports and that the vibe cluster took a month and a 301
        # to undo — self-inflicted, on the same night, from one seed.
        #
        # Containment, not similarity: 'offline chat app' vs 'offline chat app for android'
        # is one topic phrased twice, while 'ios chat app' vs 'android chat app' overlaps
        # heavily and is genuinely two pages. Only a full subset is refused, and the SHORTER
        # topic is kept — the broader phrasing can rank for the narrower one, never the
        # reverse.
        if len(new) > 1:
            ordered = sorted(new, key=lambda t: len(str(t.get("topic", "")).split()))
            kept = []
            for t in ordered:
                tok = set(str(t.get("topic", "")).lower().split())
                dup = next((k for k in kept
                            if set(str(k.get("topic", "")).lower().split()) <= tok), None)
                if dup:
                    print(f"  NEW refused (same-batch overlap): '{t.get('topic')}' contains "
                          f"'{dup.get('topic')}', already queued tonight. Two pages, one topic.")
                    continue
                kept.append(t)
            # Restore the pool's own ranking; the sort above was only to test containment
            # shortest-first, and must not become the order work is done in.
            new = [t for t in new if t in kept]
        new = new[:new_budget]
    else:
        new = []
        if ledger_corrupt:
            print("\n  NEW-post budget FORCED to 0 — content-log.json is unreadable, failing "
                  "CLOSED. Enhance-only tonight. Fix the ledger to re-enable new posts.")
        else:
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
    exhausted = retarget_exhausted_paths(ledger)
    retarget = [
        t for t in retarget
        if t["path"] not in booked
        and not any(c in t["path"] for c in cool)
        and not denied(t["path"], deny_paths)
        and t["path"] not in exhausted
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

    # Persist tonight's snapshot for whoever WON a slot, so the exhaustion count is checked
    # against real GSC outcomes next run. Skipped when the ledger was corrupt on read — do not
    # overwrite a file a human still needs to fix, and do not fabricate exhaustion history from
    # a forced-empty ledger. Also skipped in --dry-run: "print, write nothing" must stay true,
    # every other tool in this pipeline is trusted to have zero side effects under this flag.
    if not ledger_corrupt and not args.dry_run:
        update_retarget_ledger(ledger, retarget)
        save_ledger(host, ledger)

    # Cannibalisation goes FIRST. Polishing a page while a rival page splits its demand is
    # rearranging furniture in a burning room — fix the split, then optimise the survivor.
    targets = canni + enhance_capped + cold + retarget + new

    queue = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "site": site_url, "property": prop,
        "caps": {"enhance": args.enhance_cap, "new": args.new_cap,
                 "new_budget_tonight": new_budget, "cooldown_days": args.cooldown},
        "pool_counts": {"enhance_found": len(enhance), "cold_start": len(cold),
                        "retarget": len(retarget),
                        "cannibalization": len(canni),
                        "cannibalization_flagged": len(canni_flagged),
                        "new_found_after_budget": len(new), "cooldown_excluded": len(cool),
                        "additive_protected": sum(1 for t in targets
                                                  if t.get("edit_mode") == "additive")},
        # Clashes we deliberately did NOT auto-fix because a page in them earns clicks. Not
        # silence — the report must name them so a human can judge.
        "cannibalization_flagged": canni_flagged,
        # None (not []) when the GSC check could not run, so "we looked and found nothing"
        # and "we could not look" stay distinguishable to every downstream reader.
        "cannibalization_measured": gsc_canni,
        "targets": targets,
    }

    if canni or canni_flagged:
        print(f"\n  CANNIBALISATION: {len(canni)} fixable, {len(canni_flagged)} flagged-only")
        for t in canni:
            print(f"    FIX  {len(t['competing'])} pages chase one query (all 0 clicks):")
            for c in t["competing"]:
                print(f"           {c['path'][:44]:<46} {c['title'][:50]}")
        for f in canni_flagged:
            print(f"    FLAG ({f.get('reason','earning attention')} — human call, not touching):")
            for pth in f["paths"]:
                a = f.get("attention", {}).get(pth, 0)
                print(f"           {a:>4} attention  {pth[:56]}")

    print(f"\n  ENHANCE candidates: {len(enhance)}  (queueing {len(enhance[:args.enhance_cap])})")
    for t in enhance[:args.enhance_cap]:
        guard = "🔒 additive" if t.get("edit_mode") == "additive" else "✏️  full"
        print(f"    #{t['position']:<5} {t['impressions']:>5} impr  {guard:<12} {t['path'][:44]}")
        print(f"           └─ '{t['query'][:56]}'")
    if cold:
        print(f"\n  COLD-START (zero impressions, one shot each): {len(cold)}")
        for t in cold:
            print(f"    never seen by Google:  {t['path'][:56]}")
    if vanity_skipped:
        print(f"\n  NEW-post head-terms refused ({len(vanity_skipped)} — too big to win with a new page; "
              f"an owned page would still be retargeted):")
        for q, v, p in sorted(vanity_skipped, key=lambda x: -(x[1] or 0))[:6]:
            print(f"    ~{int(v):>6}/mo  #{p:<5} '{q[:48]}'  (a new page can't crack this)")

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
