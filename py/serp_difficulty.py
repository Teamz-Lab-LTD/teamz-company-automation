"""
Shared: organic SERP difficulty -> a winnability score (1-10) for any keyword.

Fills the gap that Planner's "Competition" column does NOT: that column is AD competition,
not SEO difficulty. A keyword can be Low ad-comp yet have NerdWallet + Wikipedia owning
page 1 organically = unwinnable. This checks WHO actually ranks and scores authority.

FREE + no key: scrapes DuckDuckGo HTML (html.duckduckgo.com) — Google blocks scraping, Bing
Search API was retired 2025, so DDG is the durable free organic-results source. Results are
CACHED in <data_dir>/serp-difficulty-cache.json (its OWN file — no collision with any other
script) so we never re-fetch; SERP authority barely moves, refresh maybe 1-2x/year.

  from serp_difficulty import winnability
  w = winnability("paycheck calculator", data_dir)   # 1 (walled) .. 10 (easy win)

Returns 5 (neutral) on any fetch failure — never blocks the pipeline.
"""
import os, json, re, time, urllib.request, urllib.parse, html

CACHE_NAME = "serp-difficulty-cache.json"
CACHE_TTL_DAYS = 240          # SERP authority is slow-moving; ~yearly refresh
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# high-authority domains a re-targeted tool page realistically cannot outrank
AUTHORITY = {
    "wikipedia.org", "investopedia.com", "nerdwallet.com", "bankrate.com", "forbes.com",
    "irs.gov", "gov.uk", "ato.gov.au", "calculator.net", "omnicalculator.com",
    "fidelity.com", "vanguard.com", "schwab.com", "hrblock.com", "turbotax.intuit.com",
    "smartasset.com", "creditkarma.com", "experian.com", "healthline.com", "webmd.com",
    "mayoclinic.org", "cdc.gov", "nih.gov", "wikihow.com", "indeed.com", "linkedin.com",
    "amazon.com", "reddit.com", "youtube.com", "zillow.com", "realtor.com",
    "thecalculatorsite.com", "gigacalculator.com", "businessinsider.com", "cnbc.com",
    "money.com", "ramseysolutions.com", "rocketmortgage.com", "lendingtree.com",
}
_AUTH_TLD = (".gov", ".edu", ".gov.uk", ".gov.au")


def _domain(u):
    try:
        h = urllib.parse.urlparse(u).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def _is_authority(dom):
    if not dom:
        return False
    if dom in AUTHORITY:
        return True
    return any(dom.endswith(t) for t in _AUTH_TLD)


def _parse_domains(raw):
    doms = []
    for m in re.finditer(r'uddg=([^&"]+)', raw):
        d = _domain(urllib.parse.unquote(m.group(1)))
        if d and d not in doms:
            doms.append(d)
    if not doms:
        for m in re.finditer(r'class="result__url"[^>]*>([^<]+)<', raw):
            d = _domain("http://" + html.unescape(m.group(1)).strip())
            if d and d not in doms:
                doms.append(d)
    return doms[:10]


def _fetch_ddg_domains(keyword, retries=2):
    """Top organic result domains from DuckDuckGo HTML. [] on persistent failure.
    DDG throttles rapid bursts -> retry with backoff + endpoint fallback."""
    endpoints = ["https://html.duckduckgo.com/html/?q=",
                 "https://lite.duckduckgo.com/lite/?q="]
    for attempt in range(retries + 1):
        ep = endpoints[attempt % len(endpoints)]
        try:
            req = urllib.request.Request(ep + urllib.parse.quote(keyword),
                                         headers={"User-Agent": _UA})
            raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
            doms = _parse_domains(raw)
            if doms:
                return doms
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))   # politeness backoff between tries
    return []


def _score(domains):
    """0 authority sites -> 9 (easy); more big sites -> lower. 1-10."""
    if not domains:
        return 5, 0
    auth = sum(1 for d in domains if _is_authority(d))
    if auth == 0:   w = 9
    elif auth <= 2: w = 7
    elif auth <= 4: w = 5
    elif auth <= 6: w = 3
    else:           w = 2
    return w, auth


def _cache_path(data_dir):
    return os.path.join(data_dir, CACHE_NAME)


def _load_cache(data_dir):
    p = _cache_path(data_dir)
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except Exception:
            return {}
    return {}


def winnability(keyword, data_dir, now_ts=None, force=False):
    """1 (walled by big sites) .. 10 (easy). Cached. now_ts passed in (scripts can't use
    Date.now-style calls in some contexts); falls back to time.time()."""
    now_ts = now_ts or time.time()
    key = keyword.strip().lower()
    cache = _load_cache(data_dir)
    hit = cache.get(key)
    if hit and not force and (now_ts - hit.get("ts", 0)) < CACHE_TTL_DAYS * 86400:
        return hit["winnability"]
    try:
        domains = _fetch_ddg_domains(keyword)
        w, auth = _score(domains)
    except Exception:
        return (hit or {}).get("winnability", 5)   # stale cache or neutral, never block
    cache[key] = {"winnability": w, "authority_count": auth,
                  "top_domains": domains[:6], "ts": now_ts}
    try:
        tmp = _cache_path(data_dir) + ".tmp"
        json.dump(cache, open(tmp, "w"), indent=2)
        os.replace(tmp, _cache_path(data_dir))
    except Exception:
        pass
    return w


def stats(data_dir):
    c = _load_cache(data_dir)
    return {"cached_keywords": len(c),
            "walled": sum(1 for v in c.values() if v["winnability"] <= 3),
            "winnable": sum(1 for v in c.values() if v["winnability"] >= 7)}
