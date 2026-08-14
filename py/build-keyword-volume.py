#!/usr/bin/env python3
"""
Keyword Volume Estimator — FREE (No Paid APIs)
================================================
Estimates relative search volume using free data sources:
1. Google Trends (relative interest 0-100)
2. Google Autocomplete (position = popularity signal)
3. Google Search result count (competition proxy)
4. Search Console impressions (real data if available)

Outputs a composite "Volume Score" (0-100) that lets you compare
keywords and prioritize which tools to build.

Usage:
  python3 scripts/build-keyword-volume.py "fuel cost calculator"
  python3 scripts/build-keyword-volume.py "bac calculator" "tip calculator" "bmi calculator"
  python3 scripts/build-keyword-volume.py --bulk          # check all tools
  python3 scripts/build-keyword-volume.py --top 20        # top 20 by score

Google Ads Basic Access WAS approved (2026-08-08) and exact Keyword Planner
volumes now feed the composite score at the highest weight (2026-08-14). Before
that they were fetched, printed in a table, and thrown away — the score itself was
built from Bing. Set TEAMZ_KW_GEO to choose the country being measured; the banner
prints it, because a volume number without its country is not a number.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONSOLE_TOKEN = os.path.expanduser("~/.config/teamzlab/search-console-token.json")
ADS_CONFIG = os.path.expanduser("~/.config/teamzlab/google-ads-config.json")
ADS_TOKEN = os.path.expanduser("~/.config/teamzlab/google-ads-token.json")
BING_API_KEY_FILE = os.path.expanduser("~/.config/teamzlab/bing-webmaster-api-key.txt")

# Which country Keyword Planner measures. This used to be hardcoded to the US
# constant with no way to change it, which quietly made every Bangladesh-market
# pull meaningless: measured 2026-08-14, "bkash" reads 1,900/mo on geo 2840 and
# 246,000/mo on geo 2050, and "manchester united jersey" reads 27,100 vs 2,400.
# Every goalkit and Hazira keyword decision ever taken through this script was
# therefore reading American demand for a Bangladeshi query. Default stays US so
# nothing about the tools property changes; BD callers set TEAMZ_KW_GEO=2050.
#
# IDs are Google Ads geoTargetConstants. Verified live, by effect, not assumed:
# 2840 = United States, 2050 = Bangladesh. 1000352 — which
# build-distribution-drafts.py was passing for BD — is not a valid constant at
# all and returns HTTP 400 INVALID_ARGUMENT.
KW_GEO = os.getenv("TEAMZ_KW_GEO", "2840").strip() or "2840"
KW_LANG = os.getenv("TEAMZ_KW_LANG", "1000").strip() or "1000"


def fetch_bing_keyword_volume(keyword, country='us', language='en-US'):
    """
    Get real search volume from Bing Webmaster Tools Keyword Research API.
    Returns dict with weekly avg impressions (exact + broad) or None on failure.
    """
    cache_key = f"bing:{keyword}:{country}"
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        api_key = ''
        if os.path.exists(BING_API_KEY_FILE):
            with open(BING_API_KEY_FILE) as f:
                api_key = f.read().strip()
        if not api_key:
            _cache[cache_key] = None
            return None

        encoded = urllib.parse.quote(keyword)
        url = (f"https://ssl.bing.com/webmaster/api.svc/json/GetKeywordStats"
               f"?q={encoded}&country={country}&language={language}&apikey={api_key}")
        req = urllib.request.Request(url, headers={
            'User-Agent': 'TeamzLabTools/1.0'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        entries = data.get('d', [])
        if not entries:
            _cache[cache_key] = {'exact_weekly': 0, 'broad_weekly': 0, 'exact_monthly': 0, 'broad_monthly': 0, 'weeks': 0}
            return _cache[cache_key]

        # Average over available weeks (last 6 months typically)
        exact_total = sum(e.get('Impressions', 0) for e in entries)
        broad_total = sum(e.get('BroadImpressions', 0) for e in entries)
        weeks = len(entries)

        result = {
            'exact_weekly': round(exact_total / weeks) if weeks else 0,
            'broad_weekly': round(broad_total / weeks) if weeks else 0,
            'exact_monthly': round(exact_total / weeks * 4.33) if weeks else 0,
            'broad_monthly': round(broad_total / weeks * 4.33) if weeks else 0,
            'weeks': weeks,
        }
        _cache[cache_key] = result
        return result
    except Exception:
        _cache[cache_key] = None
        return None

# Cache to avoid re-fetching
_cache = {}

# Google Trends fetch state — shared cookie session + honest failure tracking
# (bare requests to the Trends API get 429'd; a primed session helps, and we
#  record WHY a fetch failed so the run reports a reason instead of silent "---")
_TRENDS_OPENER = None
_TRENDS_STATUS = {"reason": None, "fails": 0, "ok": 0}


def _trends_session():
    """Lazily build a cookie-backed opener and prime Google's NID cookie."""
    global _TRENDS_OPENER
    if _TRENDS_OPENER is None:
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        op.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'),
            ('Accept-Language', 'en-US,en;q=0.9'),
        ]
        try:
            op.open('https://trends.google.com/trends/explore?geo=US', timeout=8)
        except Exception:
            pass
        _TRENDS_OPENER = op
    return _TRENDS_OPENER


def fetch_google_autocomplete(query):
    """Get autocomplete suggestions. Position in list = popularity signal."""
    cache_key = f"ac:{query}"
    if cache_key in _cache:
        return _cache[cache_key]
    try:
        encoded = urllib.parse.quote(query)
        url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={encoded}&hl=en"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            suggestions = data[1] if isinstance(data, list) and len(data) > 1 else []
            _cache[cache_key] = suggestions
            return suggestions
    except Exception:
        _cache[cache_key] = []
        return []


def get_autocomplete_score(keyword):
    """
    Score 0-100 based on multiple autocomplete signals:
    1. Does the keyword appear when typing just the first word? (very high volume)
    2. Position in suggestions (lower = more popular)
    3. How many long-tail variations exist? (more = more search activity)
    4. Does it appear with just 2-letter prefix? (extremely high volume)
    """
    words = keyword.lower().split()
    if not words:
        return 0

    signals = {
        'first_word_match': 0,       # 0-30: appears when typing first word only
        'two_word_match': 0,         # 0-25: appears when typing first two words
        'position_score': 0,         # 0-20: position in suggestion list
        'variation_count': 0,        # 0-15: number of long-tail variations
        'short_prefix_match': 0,     # 0-10: appears with 3-char prefix
    }

    # Signal 1: Type just the first word — does our keyword appear?
    first_word = words[0]
    suggestions = fetch_google_autocomplete(first_word)
    time.sleep(0.1)
    if suggestions:
        for pos, s in enumerate(suggestions):
            if _keyword_similarity(keyword.lower(), s.lower()) > 0.6:
                # Appearing for a single word = very competitive/high volume
                signals['first_word_match'] = max(5, 30 - (pos * 3))
                signals['position_score'] = max(0, 20 - (pos * 2))
                break

    # Signal 2: Type first two words (if multi-word keyword)
    if len(words) >= 2:
        prefix2 = ' '.join(words[:2])
        suggestions2 = fetch_google_autocomplete(prefix2)
        time.sleep(0.1)
        if suggestions2:
            for pos, s in enumerate(suggestions2):
                if _keyword_similarity(keyword.lower(), s.lower()) > 0.7:
                    signals['two_word_match'] = max(5, 25 - (pos * 3))
                    if signals['position_score'] == 0:
                        signals['position_score'] = max(0, 15 - (pos * 2))
                    break

    # Signal 3: How many long-tail variations exist?
    full_suggestions = fetch_google_autocomplete(keyword)
    time.sleep(0.1)
    if full_suggestions:
        signals['variation_count'] = min(15, len(full_suggestions) * 2)

    # Signal 4: 3-character prefix match (extremely popular keywords only)
    if len(first_word) >= 3:
        short_prefix = first_word[:3]
        short_suggestions = fetch_google_autocomplete(short_prefix)
        time.sleep(0.1)
        if short_suggestions:
            for s in short_suggestions:
                if keyword.lower() in s.lower() or _keyword_similarity(keyword.lower(), s.lower()) > 0.5:
                    signals['short_prefix_match'] = 10
                    break

    total = sum(signals.values())
    return min(100, total)


def _keyword_similarity(kw1, kw2):
    """Simple word overlap similarity."""
    words1 = set(kw1.split())
    words2 = set(kw2.split())
    if not words1 or not words2:
        return 0
    overlap = len(words1 & words2)
    return overlap / max(len(words1), len(words2))


def fetch_google_trends_score(keyword, retries=3):
    """
    Get Google Trends interest score (0-100) using the embedded data endpoint.
    Retries with backoff on 429/transient errors and records WHY it failed,
    so the run reports a clear reason instead of a silent "---".
    """
    cache_key = f"trends:{keyword}"
    if cache_key in _cache:
        return _cache[cache_key]

    # The req= value is a JSON blob; it MUST be percent-encoded or urllib raises
    # InvalidURL (raw braces/quotes/spaces). This was the real reason Trends always
    # returned "---" — the request never even reached Google.
    _req_payload = (
        '{"comparisonItem":[{"keyword":"' + keyword + '","geo":"","time":"today 12-m"}],'
        '"category":0,"property":""}'
    )
    explore_url = (
        "https://trends.google.com/trends/api/explore?hl=en-US&tz=0&req="
        + urllib.parse.quote(_req_payload)
    )
    op = _trends_session()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(explore_url)
            with op.open(req, timeout=10) as resp:
                raw = resp.read().decode('utf-8')
                # Google prepends an XSSI guard like ")]}'" (length varies per
                # endpoint) — strip to the first '{' instead of a fixed prefix.
                i = raw.find('{')
                if i > 0:
                    raw = raw[i:]
                data = json.loads(raw)
                for widget in data.get('widgets', []):
                    if widget.get('id') == 'TIMESERIES':
                        token = widget.get('token', '')
                        req_data = widget.get('request', {})
                        if token and req_data:
                            score = _fetch_trends_timeseries(token, req_data, op)
                            _cache[cache_key] = score
                            _TRENDS_STATUS["ok"] += 1
                            return score
                # parsed OK but no timeseries widget -> genuine no-data, do not retry
                _cache[cache_key] = None
                return None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                _TRENDS_STATUS["reason"] = "rate-limited (HTTP 429)"
                if attempt == 0:
                    sys.stderr.write("  WARN Google Trends: HTTP 429 (rate-limited) — backing off + retrying...\n")
                time.sleep(3 * (attempt + 1))   # 3s, 6s, 9s
                continue
            _TRENDS_STATUS["reason"] = f"HTTP {e.code}"
            break
        except Exception as e:
            _TRENDS_STATUS["reason"] = type(e).__name__
            time.sleep(2)
            continue

    _TRENDS_STATUS["fails"] += 1
    _cache[cache_key] = None
    return None


def _fetch_trends_timeseries(token, req_data, opener=None):
    """Fetch actual trend data using the widget token (reuses the cookie session)."""
    try:
        req_json = urllib.parse.quote(json.dumps(req_data))
        url = f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=0&req={req_json}&token={token}"
        req = urllib.request.Request(url)
        _open = (opener.open if opener is not None else urllib.request.urlopen)
        with _open(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
            # strip the XSSI guard robustly (this endpoint uses a different
            # prefix than /explore — the real reason scores never came back)
            i = raw.find('{')
            if i > 0:
                raw = raw[i:]
            data = json.loads(raw)
            timeline = data.get('default', {}).get('timelineData', [])
            if timeline:
                values = [int(p['value'][0]) for p in timeline if p.get('value')]
                if values:
                    # Return average of last 3 months
                    recent = values[-12:] if len(values) >= 12 else values
                    return int(sum(recent) / len(recent))
    except Exception:
        pass
    return None


def get_search_result_count(keyword):
    """
    Estimate result count from Google search.
    More results = more competitive = usually more volume.
    """
    cache_key = f"results:{keyword}"
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        encoded = urllib.parse.quote(f'"{keyword}"')
        url = f"https://www.google.com/search?q={encoded}&num=1"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            # Extract "About X results"
            m = re.search(r'About\s+([\d,]+)\s+results', html)
            if m:
                count = int(m.group(1).replace(',', ''))
                _cache[cache_key] = count
                return count
    except Exception:
        pass

    _cache[cache_key] = None
    return None


def get_search_console_impressions(keyword):
    """
    Check Search Console for real impression data on this keyword.
    Most accurate signal we have.
    """
    if not os.path.exists(CONSOLE_TOKEN):
        return None

    try:
        import requests
        with open(CONSOLE_TOKEN) as f:
            token_data = json.load(f)

        token = token_data.get('token', '')
        site_url = "https://tool.teamzlab.com/"
        encoded_site = urllib.parse.quote(site_url, safe='')
        api_url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query"

        headers = {
            'Authorization': f'Bearer {token}',
            'x-goog-user-project': 'teamzlab-tools',
            'Content-Type': 'application/json'
        }

        end_date = datetime.now().strftime('%Y-%m-%d')
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

        r = requests.post(api_url, headers=headers, json={
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['query'],
            'dimensionFilterGroups': [{
                'filters': [{
                    'dimension': 'query',
                    'operator': 'contains',
                    'expression': keyword
                }]
            }],
            'rowLimit': 10
        })

        if r.status_code == 200:
            rows = r.json().get('rows', [])
            total_impr = sum(row.get('impressions', 0) for row in rows)
            return total_impr if total_impr > 0 else None
    except Exception:
        pass
    return None


def try_google_ads_volume(keywords):
    """
    Try Google Ads API if Basic Access is approved.
    Returns None if not available yet.
    """
    if not os.path.exists(ADS_CONFIG) or not os.path.exists(ADS_TOKEN):
        return None

    try:
        import requests
        with open(ADS_CONFIG) as f:
            config = json.load(f)
        with open(ADS_TOKEN) as f:
            token_data = json.load(f)

        # The stored access token is ~1h from the OAuth exchange and expires.
        # Refresh it every call (same pattern as ga4_token()/other loaders in
        # this repo) so this doesn't just work for the first hour and then
        # silently fall back to the manual-CSV path with no error shown —
        # "Returns None if not available yet" below would read as "still
        # waiting on approval" when the real cause is a stale token.
        refresh_resp = requests.post(token_data.get('token_uri', 'https://oauth2.googleapis.com/token'), data={
            'client_id': token_data['client_id'],
            'client_secret': token_data['client_secret'],
            'refresh_token': token_data['refresh_token'],
            'grant_type': 'refresh_token',
        }, timeout=30)
        refresh_resp.raise_for_status()
        token = refresh_resp.json()['access_token']
        customer_id = config['customer_id'].replace('-', '')
        dev_token = config['developer_token']
        login_id = config.get('login_customer_id', customer_id).replace('-', '')

        headers = {
            'Authorization': f'Bearer {token}',
            'developer-token': dev_token,
            'login-customer-id': login_id,
            'Content-Type': 'application/json'
        }

        # The version is NEGOTIATED, never hardcoded. This line used to pin v18, which had
        # been sunset for months while the broad `except` below reported it as "API not
        # available yet"; pinning v21 instead lasted hours before Google began blocking that
        # one mid-rollout. google_ads_api probes newest-first and caches the answer, so a
        # sunset re-resolves itself instead of silently disabling this function again.
        import sys as _sys, os as _os
        _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
        import google_ads_api as _ads
        url = _ads.endpoint(config, headers)
        if not url:
            return None
        r = requests.post(url, headers=headers, json={
            'keywordSeed': {'keywords': keywords[:10]},
            'language': f'languageConstants/{KW_LANG}',
            'geoTargetConstants': [f'geoTargetConstants/{KW_GEO}'],
            'keywordPlanNetwork': 'GOOGLE_SEARCH'
        })

        if r.status_code == 200:
            results = {}
            for idea in r.json().get('results', []):
                kw = idea.get('text', '').lower()
                metrics = idea.get('keywordIdeaMetrics', {})
                results[kw] = {
                    'volume': int(metrics.get('avgMonthlySearches', 0)),
                    'competition': metrics.get('competition', 'UNSPECIFIED'),
                    'cpc_low': round(int(metrics.get('lowTopOfPageBidMicros', 0)) / 1_000_000, 2),
                    'cpc_high': round(int(metrics.get('highTopOfPageBidMicros', 0)) / 1_000_000, 2),
                }
            return results
        # Non-200: surface it. A silent `pass` here is the exact trap this function's own
        # docstring warns about for token refresh — "not approved yet" and "broke today" both
        # read as None otherwise. Verified live 2026-08-08: Basic Access IS approved and this
        # path returns real data (e.g. "calculator" -> 24.9M avg monthly searches) — so from
        # today, a non-200 here means something is actually wrong, not "still waiting."
        sys.stderr.write(f"  ! Google Ads keyword-volume call failed: HTTP {r.status_code}: "
                          f"{r.text[:200]}\n")
    except Exception as e:
        sys.stderr.write(f"  ! Google Ads keyword-volume call raised {type(e).__name__}: {e}\n")
    return None


_ADS_VOLUME_CACHE = {}


def prefetch_ads_volumes(keywords):
    """Fill _ADS_VOLUME_CACHE for a whole run, 10 keywords per API call.

    Keyword Planner takes up to 10 seeds per request, so this is batched once per
    run rather than called inside estimate_volume — a per-keyword call would turn a
    50-keyword run into 50 requests against a quota'd API for data one request can
    return.
    """
    todo = [k for k in dict.fromkeys(k.lower() for k in keywords)
            if k not in _ADS_VOLUME_CACHE]
    for i in range(0, len(todo), 10):
        got = try_google_ads_volume(todo[i:i + 10])
        if not got:
            continue
        for k, v in got.items():
            _ADS_VOLUME_CACHE[k.lower()] = v
    return _ADS_VOLUME_CACHE


def estimate_volume(keyword):
    """
    Composite volume estimation from multiple free signals.
    Returns dict with score (0-100) and breakdown.
    """
    result = {
        'keyword': keyword,
        'autocomplete_score': 0,
        'trends_score': None,
        'result_count': None,
        'console_impressions': None,
        'ads_volume': None,
        'bing_volume': None,
        'composite_score': 0,
        'volume_tier': 'UNKNOWN',
    }

    # Signal 1: Autocomplete (always available, fast)
    result['autocomplete_score'] = get_autocomplete_score(keyword)

    # Signal 2: Google Trends (rate limited, may fail)
    trends = fetch_google_trends_score(keyword)
    result['trends_score'] = trends

    # Signal 3: Search result count
    count = get_search_result_count(keyword)
    result['result_count'] = count
    time.sleep(0.3)  # Be polite to Google

    # Signal 4: Search Console impressions (if available)
    impressions = get_search_console_impressions(keyword)
    result['console_impressions'] = impressions

    # Signal 5: Bing Keyword Research API (real search volume data)
    bing = fetch_bing_keyword_volume(keyword)
    result['bing_volume'] = bing

    # Signal 6: Google Ads Keyword Planner — Google's own exact monthly volume.
    # This was already being fetched and PRINTED in a table below the results, and
    # then thrown away: `ads_volume` was initialised to None above and never assigned,
    # so the 0-100 tier every downstream consumer reads was built from autocomplete,
    # Trends, a result count and BING. For a site optimising for Google, Bing volume
    # was standing in for Google volume while Google volume sat unread on the same page.
    #
    # It matters more now, not less: the nightly SEO health-check has been RED on
    # "Trends returned '---'" and Trends carried weight 4. Reviving a scraped Trends
    # endpoint Google actively blocks is the wrong repair — using the authoritative
    # number that is already on disk makes Trends' absence stop mattering.
    ads = _ADS_VOLUME_CACHE.get(keyword.lower())
    if ads is None and os.path.exists(ADS_CONFIG) and os.path.exists(ADS_TOKEN):
        got = try_google_ads_volume([keyword])
        if got:
            for k, v in got.items():
                _ADS_VOLUME_CACHE[k.lower()] = v
            ads = _ADS_VOLUME_CACHE.get(keyword.lower())
    result['ads_volume'] = ads

    # Compute composite score (weighted average of available signals)
    scores = []
    weights = []

    # Autocomplete: always available, decent signal
    scores.append(result['autocomplete_score'])
    weights.append(3)

    # Trends: good relative signal when available
    if trends is not None:
        scores.append(trends)
        weights.append(4)

    # Result count: normalize to 0-100 scale
    if count is not None:
        if count > 10_000_000:
            count_score = 95
        elif count > 1_000_000:
            count_score = 80
        elif count > 100_000:
            count_score = 60
        elif count > 10_000:
            count_score = 40
        elif count > 1_000:
            count_score = 25
        else:
            count_score = 10
        scores.append(count_score)
        weights.append(2)

    # Console impressions: strong signal (real data from YOUR site)
    if impressions is not None and impressions > 0:
        if impressions > 100:
            impr_score = 90
        elif impressions > 50:
            impr_score = 70
        elif impressions > 10:
            impr_score = 50
        else:
            impr_score = 30
        scores.append(impr_score)
        weights.append(5)  # High weight — real data

    # Bing volume: strongest signal — actual search volume from Bing API
    if bing is not None and bing.get('exact_monthly', 0) > 0:
        monthly = bing['exact_monthly']
        if monthly > 50000:
            bing_score = 98
        elif monthly > 10000:
            bing_score = 90
        elif monthly > 5000:
            bing_score = 80
        elif monthly > 1000:
            bing_score = 65
        elif monthly > 500:
            bing_score = 50
        elif monthly > 100:
            bing_score = 35
        elif monthly > 10:
            bing_score = 20
        else:
            bing_score = 10
        scores.append(bing_score)
        weights.append(6)  # Real search volume — but from Bing, not Google

    # Google Ads exact volume: outranks everything else here. Same banding as Bing so
    # the two are directly comparable, weight 9 vs Bing's 6 — when both are present the
    # Google number should decide the tier, because Google is the engine being ranked in.
    if ads is not None and ads.get('volume', 0) > 0:
        gv = ads['volume']
        if gv > 50000:
            ads_score = 98
        elif gv > 10000:
            ads_score = 90
        elif gv > 5000:
            ads_score = 80
        elif gv > 1000:
            ads_score = 65
        elif gv > 500:
            ads_score = 50
        elif gv > 100:
            ads_score = 35
        elif gv > 10:
            ads_score = 20
        else:
            ads_score = 10
        scores.append(ads_score)
        weights.append(9)

    # Weighted average
    if scores and weights:
        composite = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        result['composite_score'] = round(composite)

    # Volume tier based on composite
    cs = result['composite_score']
    if cs >= 80:
        result['volume_tier'] = 'VERY HIGH'
    elif cs >= 60:
        result['volume_tier'] = 'HIGH'
    elif cs >= 40:
        result['volume_tier'] = 'MEDIUM'
    elif cs >= 20:
        result['volume_tier'] = 'LOW'
    else:
        result['volume_tier'] = 'VERY LOW'

    return result


def fetch_all_tool_keywords():
    """Extract primary keywords from all tools."""
    try:
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("seo", os.path.join(BASE_DIR, "scripts", "seo-keyword-engine.py"))
        seo = module_from_spec(spec)
        spec.loader.exec_module(seo)
        tools = seo.find_all_tools()
        keywords = []
        for filepath in tools:
            meta = seo.extract_metadata(filepath)
            if meta:
                kw = seo.extract_primary_keyword(meta)
                if kw:
                    keywords.append((kw, meta.get('url', '')))
        return keywords
    except Exception as e:
        print(f"  WARNING: Could not load SEO engine ({e}), using slug-based keywords")
        import glob
        keywords = []
        for fp in glob.glob(os.path.join(BASE_DIR, "*", "*", "index.html")):
            parts = os.path.relpath(fp, BASE_DIR).split(os.sep)
            if len(parts) >= 3 and not parts[0].startswith('.'):
                slug = parts[1].replace('-', ' ')
                url = f"/{parts[0]}/{parts[1]}/"
                keywords.append((slug, url))
        return keywords


def print_single_results(results):
    """Print results for 1-10 keyword lookups."""
    print(f"\n  {'Keyword':<35} {'Score':>6} {'Tier':<10} {'AC':>4} {'Trends':>7} {'Bing/mo':>9} {'BingBrd':>9} {'Impr':>6}")
    print("  " + "-" * 92)
    for r in results:
        kw = r['keyword'][:35]
        score = r['composite_score']
        tier = r['volume_tier']
        ac = r['autocomplete_score']
        trends = f"{r['trends_score']}" if r['trends_score'] is not None else "---"
        bing = r.get('bing_volume')
        bing_exact = f"{bing['exact_monthly']:,}" if bing and bing.get('exact_monthly') else "---"
        bing_broad = f"{bing['broad_monthly']:,}" if bing and bing.get('broad_monthly') else "---"
        impr = f"{r['console_impressions']}" if r['console_impressions'] is not None else "---"
        print(f"  {kw:<35} {score:>5}/100 {tier:<10} {ac:>4} {trends:>7} {bing_exact:>9} {bing_broad:>9} {impr:>6}")

    if _TRENDS_STATUS["fails"]:
        print(f"\n  WARN Google Trends MISSING for {_TRENDS_STATUS['fails']} keyword(s) — {_TRENDS_STATUS['reason']}.")
        print(f"       Score used Autocomplete + Bing + GSC only (Trends not counted). Re-run later / smaller batch.")

    # Recommendations
    print(f"\n  LEGEND:")
    print(f"  Score  = Composite volume estimate (0-100)")
    print(f"  AC     = Autocomplete position score")
    print(f"  Trends = Google Trends interest (0-100)")
    print(f"  Bing/mo= Bing exact-match monthly search volume (real data)")
    print(f"  BingBrd= Bing broad-match monthly search volume")
    print(f"  Impr   = Your Search Console impressions (last 90 days)")
    print(f"\n  VOLUME TIERS:")
    print(f"  80-100 = VERY HIGH — Goldmine keyword, build immediately")
    print(f"  60-79  = HIGH      — Strong keyword, worth building")
    print(f"  40-59  = MEDIUM    — Decent, build if low competition")
    print(f"  20-39  = LOW       — Niche, only build if passionate")
    print(f"  0-19   = VERY LOW  — Skip unless uniquely valuable")

    # If Google Ads API is available, add exact volumes
    if os.path.exists(ADS_CONFIG) and os.path.exists(ADS_TOKEN):
        keywords = [r['keyword'] for r in results]
        ads_data = try_google_ads_volume(keywords)
        if ads_data:
            print(f"\n  EXACT VOLUMES (Google Ads Keyword Planner):")
            print(f"  {'Keyword':<40} {'Monthly Vol':>12} {'Competition':>12} {'CPC':>12}")
            print("  " + "-" * 78)
            for kw, data in ads_data.items():
                vol = f"{data['volume']:,}" if data['volume'] else "N/A"
                comp = data['competition'][:6]
                cpc = f"${data['cpc_low']}-${data['cpc_high']}" if data['cpc_high'] else "N/A"
                print(f"  {kw:<40} {vol:>12} {comp:>12} {cpc:>12}")


def fetch_dataforseo_volume(keywords, location_code=2840, language_code="en"):
    """DataForSEO Live Search Volume — paid, real Google data.

    Requires ``~/.config/teamzlab/dataforseo-credentials.json`` with
    ``login`` and ``password`` keys. Caches per (keyword, location, language,
    YYYYMM) under data/dataforseo-volume-cache.json so re-runs in the same
    month don't double-bill.
    """
    import base64
    import datetime as _dt
    import urllib.request

    cred_path = os.path.expanduser("~/.config/teamzlab/dataforseo-credentials.json")
    if not os.path.exists(cred_path):
        print(f"  DataForSEO credentials missing at {cred_path}; skipping paid source.")
        return {}
    with open(cred_path, "r") as fh:
        creds = json.load(fh)
    login = creds.get("login") or creds.get("username")
    password = creds.get("password")
    if not login or not password:
        print("  DataForSEO credentials malformed; need login + password.")
        return {}

    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "dataforseo-volume-cache.json")
    cache_path = os.path.abspath(cache_path)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as fh:
                cache = json.load(fh)
        except Exception:
            cache = {}

    yyyymm = _dt.date.today().strftime("%Y%m")
    cache_key = f"{location_code}:{language_code}:{yyyymm}"
    cache.setdefault(cache_key, {})

    to_fetch = [kw for kw in keywords if kw not in cache[cache_key]]
    results = {kw: cache[cache_key][kw] for kw in keywords if kw in cache[cache_key]}

    if to_fetch:
        auth = base64.b64encode(f"{login}:{password}".encode()).decode()
        # DataForSEO accepts up to 1000 keywords per request; we batch 100 for safety.
        for i in range(0, len(to_fetch), 100):
            batch = to_fetch[i:i + 100]
            body = json.dumps([{
                "location_code": location_code,
                "language_code": language_code,
                "keywords": batch,
            }]).encode("utf-8")
            req = urllib.request.Request(
                "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live",
                data=body,
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    payload = json.load(resp)
            except Exception as e:
                print(f"  DataForSEO error: {e}")
                continue
            for task in payload.get("tasks", []) or []:
                for item in (task.get("result") or []):
                    kw = item.get("keyword")
                    if not kw:
                        continue
                    rec = {
                        "search_volume": item.get("search_volume"),
                        "competition": item.get("competition"),
                        "cpc": item.get("cpc"),
                        "low_top_of_page_bid": item.get("low_top_of_page_bid"),
                        "high_top_of_page_bid": item.get("high_top_of_page_bid"),
                    }
                    cache[cache_key][kw] = rec
                    results[kw] = rec
            time.sleep(0.5)

        try:
            with open(cache_path, "w") as fh:
                json.dump(cache, fh, indent=2)
        except Exception as e:
            print(f"  cache write failed: {e}")

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print('  python3 scripts/build-keyword-volume.py "fuel cost calculator"')
        print('  python3 scripts/build-keyword-volume.py "kw1" "kw2" "kw3"')
        print('  python3 scripts/build-keyword-volume.py --bulk')
        print('  python3 scripts/build-keyword-volume.py --top 20')
        print('  python3 scripts/build-keyword-volume.py --source dataforseo "kw1" "kw2"')
        print('  python3 scripts/build-keyword-volume.py --source dataforseo --keywords-file kws.txt --out volumes.json')
        sys.exit(1)

    if sys.argv[1] == "--source" and len(sys.argv) > 2 and sys.argv[2] == "dataforseo":
        rest = sys.argv[3:]
        kws = []
        out_path = None
        i = 0
        while i < len(rest):
            tok = rest[i]
            if tok == "--keywords-file" and i + 1 < len(rest):
                with open(rest[i + 1], "r") as fh:
                    kws.extend([ln.strip() for ln in fh if ln.strip()])
                i += 2
            elif tok == "--out" and i + 1 < len(rest):
                out_path = rest[i + 1]
                i += 2
            else:
                kws.append(tok)
                i += 1
        if not kws:
            print("ERROR: provide keywords inline or --keywords-file path")
            sys.exit(2)
        data = fetch_dataforseo_volume(kws)
        if out_path:
            with open(out_path, "w") as fh:
                json.dump(data, fh, indent=2)
            print(f"wrote {out_path}")
        else:
            print(json.dumps(data, indent=2))
        return

    print("=" * 70)
    print("  KEYWORD VOLUME ESTIMATOR (Free — No Paid APIs)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Check if Google Ads API is available
    if os.path.exists(ADS_CONFIG):
        ads_data = try_google_ads_volume(["test"])
        if ads_data is not None:
            # Name the country in the banner. A volume number is meaningless without
            # it, and reading a US number as a Bangladeshi one is the exact mistake
            # this script made silently for months.
            geo_name = {"2840": "United States", "2050": "Bangladesh", "2826": "United Kingdom",
                        "2124": "Canada", "2036": "Australia", "2276": "Germany",
                        "2250": "France", "2356": "India"}.get(KW_GEO, "UNKNOWN GEO")
            print(f"  Google Ads Keyword Planner: ACTIVE (exact volumes) — "
                  f"measuring {geo_name} (geo {KW_GEO}; set TEAMZ_KW_GEO to change)")
        else:
            print("  Google Ads Keyword Planner: PENDING (using free estimates)")
    else:
        print("  Google Ads Keyword Planner: NOT CONFIGURED (using free estimates)")

    print("  Signals: Google Ads exact volume (w9) + Bing volume (w6) + Search Console (w5)\n          + Google Trends (w4) + Autocomplete (w3) + Result Count (w2)")

    if sys.argv[1] == '--bulk' or sys.argv[1] == '--top':
        top_n = 50
        if sys.argv[1] == '--top' and len(sys.argv) > 2:
            top_n = int(sys.argv[2])

        print(f"\n  Loading all tool keywords...")
        tool_keywords = fetch_all_tool_keywords()
        print(f"  Found {len(tool_keywords)} tools. Estimating volumes...")
        print(f"  (This takes ~1 sec per keyword due to rate limiting)")
        print()

        # One Planner call per 10 keywords instead of one per keyword. Without this,
        # wiring Google volume into the score would turn a 6,800-keyword bulk run into
        # 6,800 requests against a quota'd API.
        prefetch_ads_volumes([kw for kw, _ in tool_keywords])

        results = []
        total = len(tool_keywords)
        for i, (kw, url) in enumerate(tool_keywords):
            if i % 25 == 0 and i > 0:
                print(f"  ... processed {i}/{total} keywords")
            try:
                r = estimate_volume(kw)
                r['url'] = url
                results.append(r)
            except Exception as e:
                print(f"  WARNING: Failed for '{kw}': {e}")
            time.sleep(0.2)

        # Sort by composite score
        results.sort(key=lambda x: x['composite_score'], reverse=True)

        # Top tools
        print(f"\n  TOP {top_n} TOOLS BY ESTIMATED VOLUME")
        print(f"  {'#':<4} {'Keyword':<40} {'Score':>6} {'Tier':<10} {'URL':<30}")
        print("  " + "-" * 92)
        for i, r in enumerate(results[:top_n], 1):
            kw = r['keyword'][:40]
            url = r.get('url', '')[:30]
            print(f"  {i:<4} {kw:<40} {r['composite_score']:>5}/100 {r['volume_tier']:<10} {url:<30}")

        # Bottom tools (zero/low volume — consider removing)
        low = [r for r in results if r['composite_score'] < 20]
        if low:
            print(f"\n  LOWEST VOLUME TOOLS ({len(low)} tools scoring <20 — consider improving or removing)")
            print(f"  {'Keyword':<45} {'Score':>6} {'URL':<30}")
            print("  " + "-" * 83)
            for r in low[:20]:
                kw = r['keyword'][:45]
                url = r.get('url', '')[:30]
                print(f"  {kw:<45} {r['composite_score']:>5}/100 {url:<30}")

        # Summary stats
        scores = [r['composite_score'] for r in results]
        avg = sum(scores) / len(scores) if scores else 0
        high = len([s for s in scores if s >= 60])
        med = len([s for s in scores if 40 <= s < 60])
        low_count = len([s for s in scores if s < 20])
        print(f"\n  SUMMARY:")
        print(f"  Average volume score: {avg:.0f}/100")
        print(f"  High volume (60+):    {high} tools")
        print(f"  Medium volume (40-59):{med} tools")
        print(f"  Very low volume (<20):{low_count} tools")

    else:
        keywords = sys.argv[1:]
        print(f"\n  Checking {len(keywords)} keyword(s)...")
        results = []
        for kw in keywords:
            print(f"  Analyzing: {kw}...")
            r = estimate_volume(kw)
            results.append(r)
            time.sleep(0.3)

        print_single_results(results)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
