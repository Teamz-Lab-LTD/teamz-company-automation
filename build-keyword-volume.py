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

Note: When Google Ads API Basic Access is approved, this script will
also pull exact monthly volumes. Until then, scores are relative estimates.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSOLE_TOKEN = os.path.expanduser("~/.config/teamzlab/search-console-token.json")
ADS_CONFIG = os.path.expanduser("~/.config/teamzlab/google-ads-config.json")
ADS_TOKEN = os.path.expanduser("~/.config/teamzlab/google-ads-token.json")
BING_API_KEY_FILE = os.path.expanduser("~/.config/teamzlab/bing-webmaster-api-key.txt")


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


def fetch_google_trends_score(keyword):
    """
    Get Google Trends interest score (0-100) using the embedded data endpoint.
    """
    cache_key = f"trends:{keyword}"
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        encoded = urllib.parse.quote(keyword)
        url = f"https://trends.google.com/trends/api/dailytrends?hl=en-US&tz=0&geo=US&ns=15"
        # Use explore endpoint for specific keyword
        explore_url = (
            f"https://trends.google.com/trends/api/explore?hl=en-US&tz=0&req="
            f'{{"comparisonItem":[{{"keyword":"{keyword}","geo":"","time":"today 12-m"}}],'
            f'"category":0,"property":""}}'
        )
        req = urllib.request.Request(explore_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode('utf-8')
            # Google Trends prepends ")]}'" to prevent XSSI
            if raw.startswith(')]}\'\n'):
                raw = raw[5:]
            data = json.loads(raw)
            # Extract the token for interest over time
            widgets = data.get('widgets', [])
            for widget in widgets:
                if widget.get('id') == 'TIMESERIES':
                    token = widget.get('token', '')
                    req_data = widget.get('request', {})
                    if token and req_data:
                        score = _fetch_trends_timeseries(token, req_data)
                        _cache[cache_key] = score
                        return score
    except Exception:
        pass

    _cache[cache_key] = None
    return None


def _fetch_trends_timeseries(token, req_data):
    """Fetch actual trend data using the widget token."""
    try:
        req_json = urllib.parse.quote(json.dumps(req_data))
        url = f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=0&req={req_json}&token={token}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode('utf-8')
            if raw.startswith(')]}\'\n'):
                raw = raw[5:]
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

        token = token_data.get('token', '')
        customer_id = config['customer_id'].replace('-', '')
        dev_token = config['developer_token']
        login_id = config.get('login_customer_id', customer_id).replace('-', '')

        headers = {
            'Authorization': f'Bearer {token}',
            'developer-token': dev_token,
            'login-customer-id': login_id,
            'Content-Type': 'application/json'
        }

        url = f"https://googleads.googleapis.com/v18/customers/{customer_id}:generateKeywordIdeas"
        r = requests.post(url, headers=headers, json={
            'keywordSeed': {'keywords': keywords[:10]},
            'language': 'languageConstants/1000',
            'geoTargetConstants': ['geoTargetConstants/2840'],
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
    except Exception:
        pass
    return None


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
        weights.append(6)  # Highest weight — real search volume data

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


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print('  python3 scripts/build-keyword-volume.py "fuel cost calculator"')
        print('  python3 scripts/build-keyword-volume.py "kw1" "kw2" "kw3"')
        print('  python3 scripts/build-keyword-volume.py --bulk')
        print('  python3 scripts/build-keyword-volume.py --top 20')
        sys.exit(1)

    print("=" * 70)
    print("  KEYWORD VOLUME ESTIMATOR (Free — No Paid APIs)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Check if Google Ads API is available
    if os.path.exists(ADS_CONFIG):
        ads_data = try_google_ads_volume(["test"])
        if ads_data is not None:
            print("  Google Ads Keyword Planner: ACTIVE (exact volumes available)")
        else:
            print("  Google Ads Keyword Planner: PENDING (using free estimates)")
    else:
        print("  Google Ads Keyword Planner: NOT CONFIGURED (using free estimates)")

    print("  Signals: Autocomplete + Google Trends + Result Count + Search Console + Bing Volume")

    if sys.argv[1] == '--bulk' or sys.argv[1] == '--top':
        top_n = 50
        if sys.argv[1] == '--top' and len(sys.argv) > 2:
            top_n = int(sys.argv[2])

        print(f"\n  Loading all tool keywords...")
        tool_keywords = fetch_all_tool_keywords()
        print(f"  Found {len(tool_keywords)} tools. Estimating volumes...")
        print(f"  (This takes ~1 sec per keyword due to rate limiting)")
        print()

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
