"""
Shared utilities for the ASO automation suite.

Provides:
- iTunes Search / Lookup API wrappers
- Apple App Store + Google Play autocomplete fetchers
- iTunes RSS review parser
- Text tokenizer with stopword removal (no external deps)
- Respectful rate limiter
- SEO cross-pollination (auto-generates missing data)
- Structured logging with LLM-friendly fix guidance
"""

import json
import html as html_lib
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

_CTX = ssl.create_default_context()
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}
# Browser-like headers for HTML pages. Useful when Google Play serves limited
# markup to generic clients.
_HEADERS_HTML = {
    **_HEADERS,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.google.com/",
}
_HEADERS_APPLE_HINTS = {
    **_HEADERS,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.apple.com/",
}
_MIN_DELAY = 1.2
_last_request_time = 0.0
_PLAY_AUTOCOMPLETE_CACHE = {}


# ---------------------------------------------------------------------------
# Logging — structured, LLM-friendly
# ---------------------------------------------------------------------------

def log_ok(msg):
    print(f"  [ok] {msg}", file=sys.stderr)

def log_warn(msg):
    print(f"  [!] {msg}", file=sys.stderr)

def log_error(msg):
    print(f"  [ERROR] {msg}", file=sys.stderr)

def log_fix(msg):
    """Print an actionable fix suggestion — designed for LLMs to read and act on."""
    print(f"  [FIX] {msg}", file=sys.stderr)

def log_info(msg):
    print(f"  [info] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

def _throttle():
    global _last_request_time
    now = time.time()
    wait = _MIN_DELAY - (now - _last_request_time)
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.time()


# ---------------------------------------------------------------------------
# HTTP layer with detailed error guidance
# ---------------------------------------------------------------------------

def _get(url, timeout=20, suppress_http_codes=None, extra_headers=None):
    _throttle()
    suppress_http_codes = suppress_http_codes or set()
    req_headers = {**_HEADERS, **(extra_headers or {})}
    req = urllib.request.Request(url, headers=req_headers)
    try:
        resp = urllib.request.urlopen(req, context=_CTX, timeout=timeout)
        return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        code = e.code
        if code in suppress_http_codes:
            return ""
        short_url = url[:120]
        if code == 403:
            log_error(f"HTTP 403 Forbidden: {short_url}")
            log_fix("The server blocked this request. If scraping Google Play, try again later or reduce request rate.")
        elif code == 404:
            log_error(f"HTTP 404 Not Found: {short_url}")
            if "itunes.apple.com" in url:
                log_fix("Check the Apple ID — find it in the App Store URL: apps.apple.com/app/id<NUMBER>")
            elif "market.android.com" in url:
                log_fix("Legacy market.android.com suggest endpoints are unreliable/retired for many queries. Use Google suggest endpoint first.")
            elif "play.google.com" in url:
                log_fix("Play listing endpoint unavailable for this request/region/package. Retry with browser-like headers and hl/gl fallback.")
            else:
                log_fix("The URL doesn't exist. Double-check the ID or endpoint.")
        elif code == 429:
            log_error(f"HTTP 429 Rate Limited: {short_url}")
            log_fix("Too many requests. Wait a few minutes and try again, or reduce --limit / keyword count.")
        elif code >= 500:
            log_error(f"HTTP {code} Server Error: {short_url}")
            log_fix("Apple/Google servers are temporarily down. Retry in a few minutes.")
        else:
            log_error(f"HTTP {code}: {short_url}")
        return ""
    except urllib.error.URLError as e:
        log_error(f"Network error: {e.reason}")
        log_fix("Check your internet connection. If behind a proxy, set HTTPS_PROXY env var.")
        return ""
    except TimeoutError:
        log_error(f"Request timed out: {url[:120]}")
        log_fix(f"The server didn't respond in {timeout}s. Try again or check if the service is down.")
        return ""
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        return ""


def _get_json(url, timeout=20, extra_headers=None, suppress_http_codes=None):
    raw = _get(url, timeout, suppress_http_codes=suppress_http_codes, extra_headers=extra_headers)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log_warn(f"Invalid JSON from: {url[:100]}")
        log_fix("The server returned non-JSON data. This usually means the endpoint changed or is rate-limiting.")
        return None


# ---------------------------------------------------------------------------
# iTunes Search & Lookup
# ---------------------------------------------------------------------------

def itunes_search(term, country="us", entity="software", limit=25):
    """Search iTunes store. Returns list of result dicts."""
    q = urllib.parse.urlencode({"term": term, "country": country, "entity": entity, "limit": limit})
    data = _get_json(f"https://itunes.apple.com/search?{q}")
    results = (data or {}).get("results", [])
    if not results and data is not None:
        log_warn(f"iTunes search for '{term}' returned 0 results (country={country})")
        log_fix(f"Try broader terms, different country code, or check if '{term}' has apps in the App Store.")
    return results


def itunes_lookup(app_id, country="us"):
    """Lookup a single app by numeric Apple ID or bundle ID."""
    key = "bundleId" if "." in str(app_id) else "id"
    q = urllib.parse.urlencode({key: app_id, "country": country, "entity": "software"})
    data = _get_json(f"https://itunes.apple.com/lookup?{q}")
    results = (data or {}).get("results", [])
    if not results:
        log_error(f"iTunes lookup failed for {key}={app_id} (country={country})")
        if "." in str(app_id):
            log_fix(f"Bundle ID '{app_id}' not found. Verify it in App Store Connect or try the numeric Apple ID instead.")
        else:
            log_fix(f"Apple ID '{app_id}' not found. Find it in the App Store URL: apps.apple.com/app/id<NUMBER>")
        return None
    return results[0]


# ---------------------------------------------------------------------------
# Autocomplete (Apple + Google Play)
# ---------------------------------------------------------------------------

def apple_autocomplete(term):
    """Apple App Store autocomplete suggestions (with iTunes Search fallback)."""
    q = urllib.parse.urlencode({"term": term})
    raw = _get(
        f"https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints?{q}",
        extra_headers=_HEADERS_APPLE_HINTS,
    )
    if raw:
        # Some regions return JSON; others return Apple plist XML.
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if data:
            hints = data.get("hints", [])
            results = [h.get("term", "") for h in hints if h.get("term")]
            if results:
                return results
        if "<plist" in raw and "<key>term</key>" in raw:
            terms = re.findall(r"<key>term</key>\s*<string>(.*?)</string>", raw, flags=re.S)
            cleaned = [html_lib.unescape(t).strip() for t in terms if t and t.strip()]
            if cleaned:
                return cleaned[:20]

    # Fallback: extract keywords from top iTunes Search results for this term
    log_info(f"Apple autocomplete empty for '{term}' — falling back to iTunes Search titles")
    search_results = itunes_search(term, limit=15)
    if not search_results:
        log_warn(f"Both Apple autocomplete and iTunes Search returned empty for '{term}'")
        log_fix("Try a more common keyword, or check your network connection.")
        return []
    seen = set()
    fallback = []
    for app in search_results:
        title = (app.get("trackName") or "").strip().lower()
        for chunk in re.split(r"[:\-–—|]", title):
            chunk = chunk.strip()
            if chunk and chunk != term.lower() and len(chunk) > 3 and chunk not in seen:
                seen.add(chunk)
                fallback.append(chunk)
    return fallback[:15]


def _strip_google_jsonp(raw):
    """Google suggest can prefix JSON with )]}' plus a newline."""
    if not raw:
        return raw
    s = raw.strip()
    if s.startswith(")]}'"):
        s = s[4:].lstrip()
    return s


def _parse_google_suggest_json(data):
    """Google suggest API returns [query, [suggestions], ...]."""
    if not isinstance(data, list) or len(data) < 2:
        return []
    bucket = data[1]
    if not isinstance(bucket, list):
        return []
    out = []
    seen = set()
    for item in bucket:
        if not isinstance(item, str):
            continue
        s = item.strip()
        if not s:
            continue
        low = s.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(s)
    return out


def _google_suggest_play(term, hl):
    """
    Primary: suggestqueries.google.com. Legacy market.android.com JSON endpoints
    often return 404 for many queries.
    """
    hl_q = urllib.parse.quote(hl)
    query_variants = (term + " google play", term + " app", term)
    for client in ("chrome", "firefox"):
        for qv in query_variants:
            url = (
                "https://suggestqueries.google.com/complete/search?client="
                + client
                + "&hl="
                + hl_q
                + "&q="
                + urllib.parse.quote(qv)
            )
            raw = _get(url)
            if not raw:
                continue
            try:
                data = json.loads(_strip_google_jsonp(raw))
            except (json.JSONDecodeError, TypeError):
                continue
            parsed = _parse_google_suggest_json(data)
            if parsed:
                log_info(f"Play keyword hints via Google suggest (client={client}) for '{term}'")
                return parsed[:25]
    return []


def _legacy_market_android_suggest(term, hl):
    """Deprecated endpoint. Kept as a last-resort fallback."""
    for url_tpl in (
        "https://market.android.com/suggest/SuggRequest?json=1&query={q}&hl={hl}",
        "https://market.android.com/suggest?json=1&c=3&hl={hl}&query={q}",
    ):
        url = url_tpl.format(q=urllib.parse.quote(term), hl=hl)
        raw = _get(url, suppress_http_codes={404, 403})
        if not raw:
            continue
        try:
            data = json.loads(raw)
            results = [item.get("s", "") for item in data if isinstance(item, dict) and item.get("s")]
            if results:
                return results
        except (json.JSONDecodeError, TypeError):
            continue
    return []


def play_autocomplete(term, hl="en"):
    """Google Play keyword hints: Google suggest first, legacy endpoint last."""
    key = (term.strip().lower(), hl.strip().lower())
    if key in _PLAY_AUTOCOMPLETE_CACHE:
        return list(_PLAY_AUTOCOMPLETE_CACHE[key])

    primary = _google_suggest_play(term, hl)
    if primary:
        filtered = []
        seen = set()
        for s in primary:
            low = s.lower()
            if low in seen:
                continue
            seen.add(low)
            if "app" in low or "play" in low or "game" in low or len(low.split()) >= 2:
                filtered.append(s)
        use = filtered if len(filtered) >= 3 else primary
        _PLAY_AUTOCOMPLETE_CACHE[key] = tuple(use[:20])
        return use[:20]

    legacy = _legacy_market_android_suggest(term, hl)
    if legacy:
        log_info("Legacy market.android.com suggest responded (uncommon)")
        _PLAY_AUTOCOMPLETE_CACHE[key] = tuple(legacy[:20])
        return legacy[:20]

    log_warn(f"Play Store autocomplete returned no data for '{term}'")
    log_fix(
        "No Google suggest results for this term/locale. "
        "Try a shorter seed or another hl= language; Apple + iTunes Search still apply."
    )
    return []


# ---------------------------------------------------------------------------
# iTunes RSS Reviews
# ---------------------------------------------------------------------------

def itunes_reviews(app_id, country="us", page=1):
    """Fetch recent reviews from iTunes RSS feed. Returns list of review dicts."""
    url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
    data = _get_json(url)
    if not data:
        log_warn(f"No review data for app {app_id} (country={country})")
        log_fix(f"Apple RSS reviews may return empty for apps with few reviews or unsupported country codes. Try country='us'.")
        return []
    entries = data.get("feed", {}).get("entry", [])
    if not isinstance(entries, list):
        entries = [entries] if entries else []
    reviews = []
    for e in entries:
        if "im:rating" not in e:
            continue
        reviews.append({
            "author": (e.get("author", {}).get("name", {}) or {}).get("label", ""),
            "rating": int(e.get("im:rating", {}).get("label", "0")),
            "title": (e.get("title", {}) or {}).get("label", ""),
            "content": (e.get("content", [{}])[0] if isinstance(e.get("content"), list) else e.get("content", {})).get("label", ""),
            "version": (e.get("im:version", {}) or {}).get("label", ""),
        })
    if not reviews:
        log_info(f"RSS feed returned 0 reviews for {app_id}/{country} (app may have very few reviews)")
    return reviews


# ---------------------------------------------------------------------------
# Text tokenizer + stopword removal
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset(
    "a an the and or but in on at to for of is it this that with from by as are was were be been "
    "being have has had do does did will would shall should can could may might must not no nor "
    "so if then than too very just about above after again all also am any because before between "
    "both but each few get got had has he her here hers herself him himself his how i its itself "
    "let me more most my myself off only other our ours ourselves out own same she some such take "
    "their theirs them themselves these they those through under until up us we what when where "
    "which while who whom why you your yours yourself yourselves app apps store play free best top "
    "new use using used get one two make".split()
)


def tokenize(text):
    """Lowercase, split on non-alpha, remove stopwords, return Counter."""
    words = re.findall(r"[a-z]{2,}", text.lower())
    return Counter(w for w in words if w not in _STOPWORDS)


def top_keywords(text, n=30):
    """Return top-n keywords from text as list of (word, count)."""
    return tokenize(text).most_common(n)


# ---------------------------------------------------------------------------
# Google Play HTML scraper (basic metadata)
# ---------------------------------------------------------------------------

_GP_TITLE_RE = re.compile(r'<h1[^>]*itemprop="name"[^>]*>([^<]+)</h1>', re.I)
_GP_DESC_RE = re.compile(r'<div[^>]*itemprop="description"[^>]*>(.*?)</div>', re.I | re.S)
_GP_RATING_RE = re.compile(r'<div[^>]*itemprop="starRating"[^>]*>.*?<div[^>]*>([\d.]+)</div>', re.I | re.S)
_GP_OG_TITLE_RE = re.compile(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', re.I)
_GP_OG_DESC_RE = re.compile(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', re.I)
_GP_JSONLD_RE = re.compile(r'<script[^>]*type="application/ld\\+json"[^>]*>(.*?)</script>', re.I | re.S)


def play_store_metadata(package_id, hl="en"):
    """Scrape basic metadata from a Google Play listing page."""
    page_url = f"https://play.google.com/store/apps/details?id={urllib.parse.quote(package_id)}&hl={hl}"
    html = _get(page_url, timeout=25, extra_headers=_HEADERS_HTML)
    if not html:
        page_url = (
            f"https://play.google.com/store/apps/details?id={urllib.parse.quote(package_id)}"
            f"&hl={urllib.parse.quote(hl)}&gl=us"
        )
        html = _get(page_url, timeout=25, extra_headers=_HEADERS_HTML)
    if not html:
        log_error(f"Could not fetch Google Play page for {package_id}")
        log_fix(f"Verify the package ID. Find it in the Play Store URL: play.google.com/store/apps/details?id=<PACKAGE_ID>")
        return None
    title_m = _GP_TITLE_RE.search(html) or _GP_OG_TITLE_RE.search(html)
    desc_m = _GP_DESC_RE.search(html) or _GP_OG_DESC_RE.search(html)
    rating_m = _GP_RATING_RE.search(html)
    desc_raw = desc_m.group(1) if desc_m else ""
    desc_clean = re.sub(r"<[^>]+>", " ", desc_raw).strip()
    title = title_m.group(1).strip() if title_m else ""
    rating = float(rating_m.group(1)) if rating_m else 0.0

    # Fallback: parse application/ld+json blocks for title/description/rating.
    if not title or not desc_clean or rating <= 0:
        for block in _GP_JSONLD_RE.findall(html):
            try:
                data = json.loads(block.strip())
            except Exception:
                continue
            obj = data[0] if isinstance(data, list) and data else data
            if not isinstance(obj, dict):
                continue
            if not title:
                title = (obj.get("name") or "").strip()
            if not desc_clean:
                desc_clean = re.sub(r"<[^>]+>", " ", (obj.get("description") or "")).strip()
            if rating <= 0:
                agg = obj.get("aggregateRating") or {}
                try:
                    rating = float(agg.get("ratingValue") or 0.0)
                except (TypeError, ValueError):
                    rating = 0.0
            if title and desc_clean and rating > 0:
                break
    if not title_m:
        log_warn(f"Could not parse title from Play Store page for {package_id}")
        log_fix("Google Play may have changed their HTML structure. The scraper regex needs updating.")
    if not title:
        title = package_id
        log_warn(f"Falling back to package id as title for {package_id}")
        log_fix("Run again later or test from another network; Google Play sometimes serves stripped HTML to automated clients.")
    return {
        "package_id": package_id,
        "title": title,
        "description": desc_clean[:4000],
        "rating": rating,
        "url": page_url,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_data_dir(cfg):
    d = cfg["data_dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# SEO cross-pollination — auto-generate + load data from SEO scripts
# ---------------------------------------------------------------------------

def _load_json_safe(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _load_csv_rows(path):
    if not path.exists():
        return []
    import csv as _csv
    with path.open(newline="", encoding="utf-8") as f:
        return list(_csv.DictReader(f))


def _try_run_script(script_name, args=None, label=None):
    """Run a sibling SEO script to generate missing data. Returns (success, stderr_output)."""
    py_dir = Path(__file__).resolve().parent.parent
    script = py_dir / script_name
    if not script.exists():
        log_warn(f"Script not found: {script_name}")
        return False, ""
    cmd = [sys.executable, str(script)] + (args or [])
    try:
        result = subprocess.run(cmd, cwd=str(py_dir.parent), capture_output=True, timeout=90, text=True)
        if result.returncode == 0:
            log_ok(f"{label or script_name}: generated successfully")
            return True, result.stderr
        elif result.returncode == 2:
            log_info(f"{label or script_name}: skipped (TEAMZ_PROJECT_TYPE=app)")
            return False, result.stderr
        else:
            log_warn(f"{label or script_name}: exited with code {result.returncode}")
            stderr_tail = (result.stderr or "").strip().split("\n")[-3:]
            for line in stderr_tail:
                if line.strip():
                    log_info(f"  {line.strip()}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        log_warn(f"{label or script_name}: timed out (90s)")
        log_fix("The script took too long. It may need a Search Console token or network access.")
        return False, ""
    except Exception as e:
        log_warn(f"{label or script_name}: {e}")
        return False, ""


_SEO_DATA_SCRIPTS = {
    "rank-history.json": {
        "script": "build-rank-tracker.py",
        "args": ["record"],
        "label": "Web rank tracker",
        "needs": "Search Console token",
        "fix": "Run: python3 scripts/build-search-console-auth.py  (one-time OAuth setup)",
    },
    "competitor-gaps-latest.json": {
        "script": "build-competitor-gaps.py",
        "args": [],
        "label": "Competitor keyword gaps",
        "needs": "Search Console token + TEAMZ_COMPETITOR_DOMAINS",
        "fix": "Set TEAMZ_COMPETITOR_DOMAINS in .teamz-automation.env (e.g. 'competitor1.com,competitor2.com')",
    },
    "brand-mentions-auto.csv": {
        "script": "build-reddit-scanner.py",
        "args": [],
        "label": "Reddit/Dev.to brand scanner",
        "needs": "TEAMZ_BRAND_KEYWORDS env var",
        "fix": "Set TEAMZ_BRAND_KEYWORDS in .teamz-automation.env (e.g. 'myapp,mybrand,mysite.com')",
    },
    "serp-features-history.csv": {
        "script": "build-serp-tracker.py",
        "args": [],
        "label": "SERP feature tracker",
        "needs": "TEAMZ_SERP_KEYWORDS or rank watchlist",
        "fix": "Set TEAMZ_SERP_KEYWORDS in .teamz-automation.env, or run build-rank-tracker.py track 'keyword' first",
    },
    "gsc-anomalies-latest.json": {
        "script": "build-gsc-anomalies.py",
        "args": ["--json-only"],
        "label": "GSC anomaly alerts",
        "needs": "Search Console token",
        "fix": "Run: python3 scripts/build-search-console-auth.py",
    },
    "crawl-snapshot-latest.json": {
        "script": "build-crawl-diff.py",
        "args": [],
        "label": "Crawl snapshot",
        "needs": "TEAMZ_HOST_SITE_ROOT pointing to a static site",
        "fix": "Set TEAMZ_HOST_SITE_ROOT in .teamz-automation.env",
    },
    "topic-cluster-latest.json": {
        "script": "build-topic-cluster-report.py",
        "args": [],
        "label": "Topic cluster report",
        "needs": "TEAMZ_HOST_SITE_ROOT pointing to a static site",
        "fix": "Set TEAMZ_HOST_SITE_ROOT in .teamz-automation.env",
    },
    "uptime-latest.json": {
        "script": "build-uptime-check.py",
        "args": [],
        "label": "Uptime monitor",
        "needs": "TEAMZ_SITE_URL",
        "fix": "Set TEAMZ_SITE_URL in .teamz-automation.env",
    },
    "schema-validation-latest.json": {
        "script": "build-schema-validate.py",
        "args": [],
        "label": "Schema validator",
        "needs": "TEAMZ_HOST_SITE_ROOT with index.html pages",
        "fix": "Set TEAMZ_HOST_SITE_ROOT in .teamz-automation.env",
    },
}


def load_seo_context(data_dir):
    """Load SEO data files to enrich ASO analysis.

    For each missing data file, attempts to run the corresponding SEO script.
    On failure, prints LLM-readable guidance on what to configure.
    ASO always works even if all SEO scripts fail.

    Returns a dict with keys present only when data exists.
    """
    ctx = {}
    d = Path(data_dir) if not isinstance(data_dir, Path) else data_dir
    generated = 0
    failed = []

    for filename, info in _SEO_DATA_SCRIPTS.items():
        target = d / filename
        if target.exists():
            continue
        log_info(f"SEO data missing: {filename} — auto-generating via {info['script']}...")
        ok, _ = _try_run_script(info["script"], info["args"], info["label"])
        if ok:
            generated += 1
        else:
            failed.append(info)

    if generated:
        log_ok(f"Auto-generated {generated} SEO data file(s)")
    if failed:
        log_warn(f"{len(failed)} SEO data source(s) could not be generated:")
        for info in failed:
            log_info(f"  {info['label']}: needs {info['needs']}")
            log_fix(info["fix"])

    # Load whatever exists now
    rh = _load_json_safe(d / "rank-history.json")
    if rh and "keywords" in rh:
        kws = rh["keywords"]
        if isinstance(kws, dict):
            ctx["web_keywords"] = sorted(kws.keys())[:200]
        elif isinstance(kws, list):
            ctx["web_keywords"] = kws[:200]

    gaps = _load_json_safe(d / "competitor-gaps-latest.json")
    if gaps and "gaps" in gaps:
        ctx["web_gaps"] = gaps["gaps"][:100]

    mentions = _load_csv_rows(d / "brand-mentions-auto.csv")
    if mentions:
        ctx["brand_mentions"] = mentions[-50:]

    serp = _load_csv_rows(d / "serp-features-history.csv")
    if serp:
        ctx["serp_features"] = serp[-100:]

    anomalies = _load_json_safe(d / "gsc-anomalies-latest.json")
    if anomalies and "alerts" in anomalies:
        ctx["gsc_anomalies"] = anomalies["alerts"]

    clusters = _load_json_safe(d / "topic-cluster-latest.json")
    if clusters and "clusters" in clusters:
        ctx["topic_clusters"] = clusters["clusters"]

    uptime = _load_json_safe(d / "uptime-latest.json")
    if uptime:
        ctx["uptime"] = uptime

    loaded = len(ctx)
    if loaded:
        log_ok(f"Loaded {loaded} SEO data source(s) for ASO enrichment")
    else:
        log_info("No SEO data available — ASO will use app store APIs only")

    return ctx


def web_keywords_for_seed(seo_ctx, n=10):
    """Extract high-value web keywords usable as ASO seed terms."""
    kws = seo_ctx.get("web_keywords", [])
    return [k for k in kws if 2 <= len(k.split()) <= 4][:n]


def web_gaps_as_aso_opportunities(seo_ctx, n=15):
    """Keyword gaps from web competitors that may also apply in app stores."""
    return seo_ctx.get("web_gaps", [])[:n]


def mentions_for_content(seo_ctx, n=10):
    """Recent unlinked brand mentions — useful for ASO outreach/content ideas."""
    return [m for m in seo_ctx.get("brand_mentions", []) if m.get("linked") != "true"][:n]


def serp_app_pack_keywords(seo_ctx):
    """Keywords where Google shows app-related SERP features (video, knowledge panel)."""
    out = []
    for row in seo_ctx.get("serp_features", []):
        if row.get("video") == "true" or row.get("knowledge_panel") == "true":
            kw = row.get("keyword", "")
            if kw and kw not in out:
                out.append(kw)
    return out[:20]
