#!/usr/bin/env python3
"""
SEO & ASO Keyword Engine — Teamz Lab Tools
============================================
Fully automated SEO + ASO keyword audit, research, and optimization.
No paid tools. No manual effort. Works for websites AND mobile apps.

SEO Modes (Web):
  audit          — Audit ALL tools for keyword placement issues
  suggest        — Keyword suggestions (Google Autocomplete)
  trends         — Google Trends analysis
  validate-new   — Validate a new tool idea before building (includes Product Hunt)
  cannibalize    — Find keyword cannibalization
  report         — Full SEO report with scores
  fix            — Auto-fix keyword placement issues
  internal-links — Check internal linking
  batch-trends   — Trends for all hubs
  freshness      — Content freshness check
  viral          — Virality & share readiness
  ph-search      — Search Product Hunt for competing products
  ph-trending    — Show trending Product Hunt products (spot opportunities)

ASO Modes (Mobile Apps):
  aso-suggest    — App Store + Play Store autocomplete suggestions
  aso-audit      — Audit app metadata (title, subtitle, description, keywords)
  aso-validate   — Validate a new app idea before building
  aso-compare    — Compare two app name ideas

Usage:
  python3 seo-keyword-engine.py audit
  python3 seo-keyword-engine.py suggest "fuel cost calculator"
  python3 seo-keyword-engine.py aso-suggest "sleep tracker" --store both
  python3 seo-keyword-engine.py aso-audit --title "Sleep Tracker" --subtitle "Track your sleep" --keywords "sleep,tracker,alarm"
  python3 seo-keyword-engine.py aso-validate "habit tracker app"
  python3 seo-keyword-engine.py aso-compare "Sleep Tracker Pro" "Better Sleep App"
"""

import os
import re
import sys
import json
import html
import glob
import unicodedata
import urllib.request
import urllib.parse
import urllib.error
import time
from collections import defaultdict, Counter
from pathlib import Path

import ssl

from _teamz_config import load_runtime

RUNTIME = load_runtime(__file__)
BASE_DIR = str(RUNTIME["host_site_root"])
SITE_URL = RUNTIME["site_url"].rstrip("/")
PROJECT_TYPE = RUNTIME.get("project_type", "website")
PH_TOKEN_FILE = os.path.expanduser(os.getenv("TEAMZ_PRODUCTHUNT_TOKEN_FILE", "~/.config/teamzlab/producthunt-token.txt"))
BING_API_KEY_FILE = os.path.expanduser(os.getenv("TEAMZ_BING_API_KEY_FILE", "~/.config/teamzlab/bing-webmaster-api-key.txt"))
PH_API_URL = "https://api.producthunt.com/v2/api/graphql"
BING_API_BASE = "https://ssl.bing.com/webmaster/api.svc/json"
SSL_CTX = ssl.create_default_context()

# Directories to exclude from tool discovery
EXCLUDE_DIRS = {
    'about', 'contact', 'privacy', 'terms', 'docs', 'shared', 'branding',
    'node_modules', '.git', 'icons', 'fonts', 'images', 'css', 'js',
    'assets', '.github', '.vscode', 'scripts'
}

WEB_ONLY_COMMANDS = {
    "audit", "cannibalize", "report", "internal-links",
    "batch-trends", "freshness", "viral", "fix"
}

# ─── UTILITY FUNCTIONS ────────────────────────────────────────────────

def find_all_tools():
    """Discover all tool pages using the same pattern as build scripts."""
    tools = []
    for filepath in glob.glob(os.path.join(BASE_DIR, '*', '*', 'index.html')):
        rel = os.path.relpath(filepath, BASE_DIR)
        parts = rel.split(os.sep)
        if len(parts) >= 3:
            hub = parts[0]
            if hub in EXCLUDE_DIRS or hub.startswith('.'):
                continue
            tools.append(filepath)
    return sorted(tools)


def extract_metadata(filepath):
    """Extract all SEO-relevant metadata from a tool page."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return None

    rel = os.path.relpath(filepath, BASE_DIR)
    parts = rel.replace('index.html', '').strip('/').split('/')
    hub = parts[0] if parts else ''
    slug = parts[1] if len(parts) > 1 else ''

    meta = {
        'filepath': filepath,
        'rel_path': rel,
        'hub': hub,
        'slug': slug,
        'url': f"/{hub}/{slug}/",
    }

    # Page language
    m = re.search(r'<html[^>]+lang=["\']([^"\']+)["\']', content)
    meta['lang'] = m.group(1).split('-')[0].lower() if m else 'en'

    # Title tag
    m = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
    meta['title'] = html.unescape(m.group(1).strip()) if m else ''

    # Meta description — match same quote type to handle apostrophes in content
    m = re.search(r'<meta\s+name="description"\s+content="(.*?)"', content, re.DOTALL)
    if not m:
        m = re.search(r"<meta\s+name='description'\s+content='(.*?)'", content, re.DOTALL)
    meta['description'] = html.unescape(m.group(1).strip()) if m else ''

    # Exclude redirect/noindex pages from audit
    if re.search(r'meta\s+(http-equiv=["\']refresh["\']|name=["\']robots["\']\s+content=["\']noindex)', content):
        return None

    # H1 (html.unescape to handle &amp; &eacute; etc.)
    m = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
    meta['h1'] = html.unescape(re.sub(r'<[^>]+>', '', m.group(1)).strip()) if m else ''

    # H2s (html.unescape)
    meta['h2s'] = [html.unescape(re.sub(r'<[^>]+>', '', h).strip())
                   for h in re.findall(r'<h2[^>]*>(.*?)</h2>', content, re.DOTALL)]

    # H3s (html.unescape)
    meta['h3s'] = [html.unescape(re.sub(r'<[^>]+>', '', h).strip())
                   for h in re.findall(r'<h3[^>]*>(.*?)</h3>', content, re.DOTALL)]

    # Tool description (first paragraph after H1)
    m = re.search(r'<p\s+class=["\']tool-description["\'][^>]*>(.*?)</p>', content, re.DOTALL)
    meta['intro'] = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''

    # All visible text (for keyword density)
    text_only = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    text_only = re.sub(r'<style[^>]*>.*?</style>', '', text_only, flags=re.DOTALL)
    text_only = re.sub(r'<[^>]+>', ' ', text_only)
    text_only = re.sub(r'\s+', ' ', text_only).strip()
    meta['body_text'] = text_only
    meta['word_count'] = len(text_only.split())

    # Image alt texts
    meta['img_alts'] = re.findall(r'<img[^>]+alt=["\']([^"\']*)["\']', content)

    # OG image
    meta['has_og_image'] = bool(re.search(r'og:image', content))

    # Canonical URL
    m = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']', content)
    meta['canonical'] = m.group(1) if m else ''

    # FAQ count
    faq_matches = re.findall(r'"@type"\s*:\s*"Question"', content)
    meta['faq_count'] = len(faq_matches)

    # Content section word count
    m = re.search(r'<section\s+class=["\']tool-content["\']>(.*?)</section>', content, re.DOTALL)
    if m:
        content_text = re.sub(r'<[^>]+>', ' ', m.group(1))
        meta['content_words'] = len(content_text.split())
    else:
        meta['content_words'] = 0

    return meta


def extract_primary_keyword(meta):
    """
    Step 1: Generate seed/primary keyword from tool metadata.
    Smart extraction: strips subtitles, privacy prefixes, handles non-Latin scripts.
    """
    h1 = meta.get('h1', '')
    slug = meta.get('slug', '')

    if not h1:
        return slug.replace('-', ' ').lower()

    kw = h1

    # Step 1: Strip brand suffixes
    kw = re.sub(r'\s*[—–|]\s*Teamz Lab.*$', '', kw, flags=re.IGNORECASE)

    # Step 2: Strip em-dash/en-dash subtitles ("Tool — Subtitle Here")
    stripped = re.split(r'\s*[—–]\s+', kw, maxsplit=1)[0]
    if len(stripped.split()) >= 2:
        kw = stripped
    elif len(stripped.split()) == 1 and slug:
        # Left side too short (e.g., "OCR — Extract Text"), fall back to slug
        return slug.replace('-', ' ').lower()

    # Step 3: Strip long parentheticals (>10 chars) — "(Duckworth-Lewis-Stern)", "(ASRS v1.1)"
    kw = re.sub(r'\s*\([^)]{10,}\)\s*$', '', kw)
    # Strip short parens with version numbers
    kw = re.sub(r'\s*\([^)]*v\d[^)]*\)\s*$', '', kw, flags=re.IGNORECASE)

    # Step 4: Strip privacy/free/confidential prefixes that aren't the real keyword
    kw = re.sub(r'^(Free\s+)?(Private\s+|Confidential\s+)', '', kw, flags=re.IGNORECASE)

    kw = kw.strip()

    # Step 5: If H1 is predominantly non-Latin script (Arabic, Japanese, CJK, etc.), prefer slug
    if slug:
        latin_chars = len(re.findall(r'[a-zA-Z]', kw))
        total_alpha = len(re.findall(r'[^\s\d\W]', kw)) or 1
        if latin_chars / total_alpha < 0.5:
            return slug.replace('-', ' ').lower()

    # Step 6: If H1 is a question ("What is...", "How much...", "Which..."), extract from title first
    if re.match(r'^(what|how|where|when|why|which|is|do|does|can|should|are|who)\s', kw, re.IGNORECASE):
        title = meta.get('title', '')
        title_kw = re.sub(r'\s*[—–|]\s*Teamz Lab.*$', '', title, flags=re.IGNORECASE).strip()
        title_kw = re.sub(r'\s*[—–]\s+.*$', '', title_kw).strip()
        if title_kw and len(title_kw.split()) >= 2:
            return title_kw.lower()
        elif slug:
            slug_kw = slug.replace('-', ' ')
            if len(slug_kw.split()) >= 2:
                return slug_kw.lower()

    # Step 7: If keyword is very long (>6 words), cross-reference with slug to shorten
    words = kw.split()
    if len(words) > 6 and slug:
        slug_kw = slug.replace('-', ' ')
        # Use slug if it has meaningful words (>= 3) and overlaps with H1
        slug_word_set = set(slug_kw.split())
        kw_word_set = set(w.lower() for w in words)
        if len(slug_word_set & kw_word_set) >= 2 and len(slug_kw.split()) >= 3:
            return slug_kw.lower()
        # Otherwise, keep first 6 words of H1
        kw = ' '.join(words[:6])

    return kw.lower().strip() if kw else slug.replace('-', ' ').lower()


def extract_secondary_keywords(meta):
    """Extract secondary/LSI keywords from description, H2s, H3s."""
    keywords = set()

    # From slug words
    slug_words = meta.get('slug', '').split('-')
    if len(slug_words) >= 2:
        keywords.add(' '.join(slug_words).lower())

    # From title (without brand)
    title = re.sub(r'\s*[—–|-]\s*Teamz Lab.*$', '', meta.get('title', ''), flags=re.IGNORECASE)
    if title.strip():
        keywords.add(title.strip().lower())

    # From H2s — extract key phrases
    for h2 in meta.get('h2s', []):
        # "How the Fuel Cost Calculator Works" → "fuel cost calculator"
        cleaned = re.sub(r'^(How|Why|What|When|Where|Tips for|Understanding)\s+(the\s+)?', '', h2, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+(Works?|Matters?|Guide|Tips|Explained)$', '', cleaned, flags=re.IGNORECASE)
        if cleaned.strip() and len(cleaned.strip().split()) >= 2:
            keywords.add(cleaned.strip().lower())

    # From description — extract noun phrases (simple heuristic)
    desc = meta.get('description', '').lower()
    # Find quoted phrases
    quoted = re.findall(r'"([^"]+)"', desc)
    keywords.update(q.lower() for q in quoted if len(q.split()) >= 2)

    return list(keywords)


def fetch_google_autocomplete(query, lang='en', country=''):
    """
    Step 2: FREE keyword research using Google Autocomplete API.
    No API key needed. Returns real search suggestions.
    country='' means worldwide (no geo filter).
    """
    try:
        encoded = urllib.parse.quote(query)
        geo_param = f"&gl={country}" if country else ""
        url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={encoded}&hl={lang}{geo_param}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if isinstance(data, list) and len(data) > 1:
                return [s for s in data[1] if s.lower() != query.lower()]
    except Exception:
        pass
    return []


def fetch_related_searches(query):
    """Get 'People Also Search For' style suggestions using autocomplete variants."""
    suggestions = set()

    # Base autocomplete
    base = fetch_google_autocomplete(query)
    suggestions.update(base)

    # Prefix variations for long-tail keywords
    prefixes = ['how to', 'best', 'free', 'online', 'what is', 'why']
    for prefix in prefixes:
        results = fetch_google_autocomplete(f"{prefix} {query}")
        suggestions.update(results[:3])  # Top 3 per prefix
        time.sleep(0.1)  # Be polite

    # Suffix variations
    suffixes = ['calculator', 'tool', 'online', 'free', 'app']
    for suffix in suffixes:
        if suffix not in query.lower():
            results = fetch_google_autocomplete(f"{query} {suffix}")
            suggestions.update(results[:3])
            time.sleep(0.1)

    return list(suggestions)


# ─── GOOGLE TRENDS (FREE) ─────────────────────────────────────────

def fetch_google_trends(keyword, geo='', timeframe='today 12-m'):
    """
    Fetch Google Trends data for a keyword using the public embed/explore endpoint.
    Returns interest over time data (relative 0-100 scale).
    No API key needed — uses the same endpoint as the Trends website.
    """
    try:
        # Google Trends explore URL — returns a token we need
        encoded = urllib.parse.quote(keyword)
        # Use the trending searches daily API for related queries
        url = f"https://trends.google.com/trends/api/autocomplete/{encoded}?hl=en-US&tz=-360"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode('utf-8')
            # Google prepends ")]}'\n" to JSON responses
            if raw.startswith(")]}'"):
                raw = raw[raw.index('\n')+1:]
            data = json.loads(raw)
            topics = []
            if 'default' in data and 'topics' in data['default']:
                for topic in data['default']['topics']:
                    mid = topic.get('mid', '')
                    title = topic.get('title', '')
                    topic_type = topic.get('type', '')
                    topics.append({'mid': mid, 'title': title, 'type': topic_type})
            return topics
    except Exception:
        pass
    return []


def _get_trends_opener():
    """Create a urllib opener with session cookies from Google Trends homepage."""
    import http.cookiejar
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    # Visit homepage to get NID cookie (required for API access)
    try:
        req = urllib.request.Request('https://trends.google.com/trends/?geo=US', headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        })
        opener.open(req, timeout=10)
    except Exception:
        pass
    return opener


def fetch_trends_interest(keyword, compare_keyword=None, geo='', timeframe='today 12-m'):
    """
    Fetch interest-over-time data from Google Trends.
    Uses session cookie + public widget endpoint. Returns monthly interest values (0-100).
    """
    try:
        opener = _get_trends_opener()

        # Build the comparison request
        kw_list = [keyword]
        if compare_keyword:
            kw_list.append(compare_keyword)

        # Google Trends explore API — get widget tokens
        req_obj = {
            'comparisonItem': [
                {'keyword': kw, 'geo': geo, 'time': timeframe}
                for kw in kw_list
            ],
            'category': 0,
            'property': ''
        }
        req_json = json.dumps(req_obj)
        explore_url = f"https://trends.google.com/trends/api/explore?hl=en-US&tz=-360&req={urllib.parse.quote(req_json)}&tz=-360"

        req = urllib.request.Request(explore_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        })
        with opener.open(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
            if raw.startswith(")]}'"):
                raw = raw[raw.index('\n')+1:]
            data = json.loads(raw)

            # Extract the TIMESERIES widget token
            widgets = data.get('widgets', [])
            time_widget = None
            related_widget = None
            for w in widgets:
                if w.get('id') == 'TIMESERIES':
                    time_widget = w
                elif w.get('id') == 'RELATED_QUERIES':
                    related_widget = w

            results = {'interest': [], 'related': [], 'keywords': kw_list}

            # Fetch interest over time
            if time_widget:
                token = time_widget.get('token', '')
                req_inner = time_widget.get('request', '')
                ts_url = f"https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=-360&req={urllib.parse.quote(json.dumps(req_inner))}&token={token}&tz=-360"
                req2 = urllib.request.Request(ts_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                })
                with opener.open(req2, timeout=10) as resp2:
                    raw2 = resp2.read().decode('utf-8')
                    if raw2.startswith(")]}'"):
                        raw2 = raw2[raw2.index('\n')+1:]
                    ts_data = json.loads(raw2)

                    timeline = ts_data.get('default', {}).get('timelineData', [])
                    for point in timeline:
                        time_str = point.get('formattedTime', '')
                        values = point.get('value', [])
                        results['interest'].append({
                            'time': time_str,
                            'values': values
                        })

            # Fetch related queries
            if related_widget:
                token = related_widget.get('token', '')
                req_inner = related_widget.get('request', '')
                rq_url = f"https://trends.google.com/trends/api/widgetdata/relatedsearches?hl=en-US&tz=-360&req={urllib.parse.quote(json.dumps(req_inner))}&token={token}&tz=-360"
                req3 = urllib.request.Request(rq_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                })
                with opener.open(req3, timeout=10) as resp3:
                    raw3 = resp3.read().decode('utf-8')
                    if raw3.startswith(")]}'"):
                        raw3 = raw3[raw3.index('\n')+1:]
                    rq_data = json.loads(raw3)

                    # Rising queries
                    ranked = rq_data.get('default', {}).get('rankedList', [])
                    for group in ranked:
                        for item in group.get('rankedKeyword', []):
                            query_text = item.get('query', '')
                            value = item.get('formattedValue', '')
                            link = item.get('link', '')
                            results['related'].append({
                                'query': query_text,
                                'value': value,
                            })

            return results
    except Exception as e:
        return {'error': str(e), 'interest': [], 'related': [], 'keywords': [keyword]}


def run_trends(keywords, geo=''):
    """
    Run Google Trends analysis for one or two keywords.
    Shows interest over time, trend direction, seasonal patterns, and related queries.
    """
    if not keywords:
        print("Usage: python3 seo-keyword-engine.py trends \"keyword1\" [\"keyword2\"]")
        return

    kw1 = keywords[0]
    kw2 = keywords[1] if len(keywords) > 1 else None

    print(f"\n{'='*60}")
    print(f"  GOOGLE TRENDS ANALYSIS")
    print(f"{'='*60}")
    print(f"  Keyword 1: \"{kw1}\"")
    if kw2:
        print(f"  Keyword 2: \"{kw2}\" (comparison)")
    print(f"  Region:    {geo if geo else 'Worldwide'}")
    print(f"  Period:    Last 12 months")
    print()

    # Step 1: Topic matching
    print(f"  [1/3] Finding trending topics for \"{kw1}\"...")
    topics = fetch_google_trends(kw1)
    if topics:
        print(f"  Google recognizes these related topics:")
        for t in topics[:5]:
            print(f"    -> {t['title']} ({t['type']})")
    else:
        print(f"  No topic matches found (niche keyword)")

    # Step 2: Interest over time
    print(f"\n  [2/3] Fetching interest over time...")
    data = fetch_trends_interest(kw1, kw2, geo=geo)

    if 'error' in data:
        print(f"  Error: {data['error']}")
        print(f"  Note: Google Trends may rate-limit automated requests.")
        print(f"  Try manually: https://trends.google.com/trends/explore?q={urllib.parse.quote(kw1)}")
        print(f"\n{'='*60}\n")
        return

    interest = data.get('interest', [])
    kw_names = data.get('keywords', [kw1])

    if interest:
        print(f"\n  Interest Over Time (0-100 scale):")
        print(f"  {'Month':<20s}", end='')
        for name in kw_names:
            print(f"  {name[:20]:<20s}", end='')
        print()
        print(f"  {'-'*20}", end='')
        for _ in kw_names:
            print(f"  {'-'*20}", end='')
        print()

        # Show data points
        values_per_kw = [[] for _ in kw_names]
        for point in interest:
            time_str = point['time']
            vals = point['values']
            print(f"  {time_str:<20s}", end='')
            for i, v in enumerate(vals):
                bar = '#' * (v // 5) if v > 0 else ''
                print(f"  {v:>3d} {bar:<15s}", end='')
                if i < len(values_per_kw):
                    values_per_kw[i].append(v)
            print()

        # Trend analysis
        print(f"\n  TREND ANALYSIS:")
        for i, name in enumerate(kw_names):
            if values_per_kw[i]:
                vals = values_per_kw[i]
                avg = sum(vals) / len(vals)
                peak = max(vals)
                low = min(vals)
                recent_3 = vals[-3:] if len(vals) >= 3 else vals
                early_3 = vals[:3] if len(vals) >= 3 else vals
                recent_avg = sum(recent_3) / len(recent_3)
                early_avg = sum(early_3) / len(early_3)

                if recent_avg > early_avg * 1.15:
                    direction = "RISING"
                elif recent_avg < early_avg * 0.85:
                    direction = "FALLING"
                else:
                    direction = "STABLE"

                print(f"    \"{name}\":")
                print(f"      Average interest:  {avg:.0f}/100")
                print(f"      Peak:              {peak}/100")
                print(f"      Low:               {low}/100")
                print(f"      Trend:             {direction}")
                print(f"      Seasonality:       {'Yes (>{0}pt swing)'.format(peak-low) if peak - low > 30 else 'Low variation'}")

        # Winner comparison
        if kw2 and len(values_per_kw) >= 2:
            avg1 = sum(values_per_kw[0]) / len(values_per_kw[0]) if values_per_kw[0] else 0
            avg2 = sum(values_per_kw[1]) / len(values_per_kw[1]) if values_per_kw[1] else 0
            print(f"\n  COMPARISON:")
            if avg1 > avg2 * 1.1:
                print(f"    WINNER: \"{kw_names[0]}\" (avg {avg1:.0f} vs {avg2:.0f})")
            elif avg2 > avg1 * 1.1:
                print(f"    WINNER: \"{kw_names[1]}\" (avg {avg2:.0f} vs {avg1:.0f})")
            else:
                print(f"    TIE: Both keywords have similar interest ({avg1:.0f} vs {avg2:.0f})")
    else:
        print(f"  No interest data returned.")
        print(f"  This usually means the keyword is too niche for Trends to track.")
        print(f"  Try a broader term or check manually:")
        print(f"  https://trends.google.com/trends/explore?q={urllib.parse.quote(kw1)}")

    # Step 3: Related queries
    print(f"\n  [3/3] Related & rising queries...")
    related = data.get('related', [])
    if related:
        # Split into top and rising
        rising = [r for r in related if 'Breakout' in r.get('value', '') or '%' in r.get('value', '')]
        top = [r for r in related if r not in rising]

        if rising:
            print(f"\n  RISING QUERIES (opportunities):")
            for r in rising[:10]:
                print(f"    {r['query']:<45s}  {r['value']}")

        if top:
            print(f"\n  TOP RELATED QUERIES:")
            for r in top[:10]:
                print(f"    {r['query']:<45s}  {r['value']}")
    else:
        print(f"  No related queries returned.")

    # Helpful link
    trends_url = f"https://trends.google.com/trends/explore?q={urllib.parse.quote(kw1)}"
    if kw2:
        trends_url += f",{urllib.parse.quote(kw2)}"
    print(f"\n  Full interactive chart: {trends_url}")
    print(f"\n{'='*60}\n")


def classify_search_intent(keyword):
    """
    Step 3: Classify search intent (informational, transactional, navigational).
    """
    kw = keyword.lower()

    transactional = ['buy', 'price', 'cost', 'cheap', 'deal', 'discount',
                     'download', 'free', 'tool', 'calculator', 'generator',
                     'converter', 'checker', 'maker', 'builder', 'creator']
    informational = ['how to', 'what is', 'why', 'guide', 'tutorial',
                     'tips', 'best way', 'vs', 'versus', 'compare',
                     'difference', 'meaning', 'definition', 'explain']
    navigational = ['login', 'sign in', 'official', 'website', 'app']

    for word in transactional:
        if word in kw:
            return 'transactional'
    for word in informational:
        if word in kw:
            return 'informational'
    for word in navigational:
        if word in kw:
            return 'navigational'
    return 'transactional'  # Default for tool pages


def is_long_tail(keyword):
    """Check if keyword is long-tail (3+ words, more specific)."""
    return len(keyword.split()) >= 3


def normalize_for_match(text):
    """Normalize text for keyword matching across ASCII and accented Latin slugs."""
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = (text
            .replace('ß', 'ss')
            .replace('æ', 'ae')
            .replace('œ', 'oe')
            .replace('ø', 'o')
            .replace('å', 'a')
            .replace('ł', 'l'))
    text = text.lower()
    # Replace & with space, strip commas, periods, colons, question marks, hyphens used as words
    text = re.sub(r'[&,.:;!?/+]', ' ', text)
    text = re.sub(r"['\"]", '', text)
    # Normalize hyphens between letter sequences to spaces for matching
    text = re.sub(r'(?<=[^\W\d_])-(?=[^\W\d_])', ' ', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def word_overlap_score(keyword, text):
    """Calculate what fraction of keyword words appear in text (0.0-1.0)."""
    kw_norm = normalize_for_match(keyword)
    text_norm = normalize_for_match(text)
    # First check exact normalized match
    if kw_norm in text_norm:
        return 1.0
    # Also check if joined keyword (compound word) exists in text
    # Handles German: "mietbelastungs rechner" → "mietbelastungsrechner"
    kw_joined = kw_norm.replace(' ', '')
    text_joined = text_norm.replace(' ', '')
    if kw_joined in text_joined:
        return 1.0
    # Word overlap
    kw_words = set(kw_norm.split())
    text_words = set(text_norm.split())
    if not kw_words:
        return 0.0
    # Also check if keyword words appear as substrings of text words (compound word matching)
    # e.g., "mietbelastungs" is in "mietbelastungsrechner"
    kw_significant = set(w for w in kw_words if len(w) > 2)
    if not kw_significant:
        kw_significant = kw_words
    overlap = set()
    for kw_w in kw_significant:
        if kw_w in text_words:
            overlap.add(kw_w)
        else:
            # Check if keyword word is substring of any text word (compound words)
            for tw in text_words:
                if kw_w in tw or tw in kw_w:
                    overlap.add(kw_w)
                    break
    return len(overlap) / len(kw_significant)


# ─── AUDIT FUNCTIONS ──────────────────────────────────────────────────

def audit_keyword_placement(meta):
    """
    Step 4: Audit strategic keyword placement.
    Returns score (0-100) and list of issues.
    """
    primary_kw = extract_primary_keyword(meta)
    if not primary_kw:
        return 0, ['NO PRIMARY KEYWORD FOUND'], primary_kw

    issues = []
    score = 0
    max_score = 0

    # Detect non-Latin H1 (Arabic, Japanese, etc.) — these get relaxed scoring
    h1_raw = meta.get('h1', '')
    latin_in_h1 = len(re.findall(r'[a-zA-Z]', h1_raw))
    total_alpha_h1 = len(re.findall(r'[^\s\d\W]', h1_raw)) or 1
    is_non_latin = (latin_in_h1 / total_alpha_h1) < 0.5 if h1_raw else False

    # 1. Title tag — keyword near beginning (25 points)
    max_score += 25
    title = meta.get('title', '').lower()
    title_clean = re.sub(r'\s*[—–|-]\s*teamz lab.*$', '', title)
    title_overlap = word_overlap_score(primary_kw, title_clean)
    if primary_kw in title_clean:
        if title_clean.startswith(primary_kw) or title_clean.find(primary_kw) < 10:
            score += 25
        else:
            score += 15
            issues.append(f'TITLE: Keyword "{primary_kw}" not near beginning of title')
    elif normalize_for_match(primary_kw) in normalize_for_match(title_clean):
        # Exact match after normalizing punctuation (& → space, hyphens → space)
        score += 23
    elif title_overlap >= 0.8:
        score += 20
    elif is_non_latin and title:
        score += 20
    elif title_overlap >= 0.5:
        score += 12
        issues.append(f'TITLE: Only {title_overlap:.0%} keyword word overlap in title')
    else:
        issues.append(f'TITLE: Primary keyword "{primary_kw}" missing from title tag')

    # 2. URL slug — contains keyword words (15 points)
    max_score += 15
    slug = meta.get('slug', '').lower()
    slug_words = set(normalize_for_match(slug).split())
    # Hyphen-aware: "self-employment" → {"self", "employment"} for matching
    kw_words = set(normalize_for_match(primary_kw).split())
    # Filter out very short words (1-2 chars) that cause false matches
    kw_words = set(w for w in kw_words if len(w) > 2)
    overlap = kw_words & slug_words
    if len(overlap) == len(kw_words):
        score += 15
    elif len(overlap) >= len(kw_words) * 0.5:
        score += 10
        missing = kw_words - slug_words
        issues.append(f'URL: Slug missing keyword words: {", ".join(missing)}')
    else:
        issues.append(f'URL: Slug "{slug}" poorly matches keyword "{primary_kw}"')

    # 3. H1 — exact or near match (20 points)
    max_score += 20
    h1 = meta.get('h1', '').lower()
    h1_overlap = word_overlap_score(primary_kw, h1)
    if primary_kw in h1 or normalize_for_match(primary_kw) in normalize_for_match(h1):
        score += 20
    elif is_non_latin:
        score += 20
    elif h1_overlap >= 0.7:
        score += 15
    elif h1_overlap >= 0.4:
        score += 10
        issues.append(f'H1: Partial keyword match ({h1_overlap:.0%}). H1="{meta["h1"]}"')
    else:
        issues.append(f'H1: Primary keyword "{primary_kw}" missing from H1')

    # 4. Intro/description — keyword in first 100 words (15 points)
    max_score += 15
    intro = meta.get('intro', '').lower()
    desc = meta.get('description', '').lower()
    intro_desc_combined = f"{intro} {desc}"
    intro_overlap = word_overlap_score(primary_kw, intro_desc_combined)
    if primary_kw in intro or primary_kw in desc:
        score += 15
    elif normalize_for_match(primary_kw) in normalize_for_match(intro_desc_combined):
        score += 14
    elif is_non_latin and (intro or desc):
        score += 12
    elif intro_overlap >= 0.7:
        score += 12
    elif intro_overlap >= 0.4:
        score += 8
        issues.append(f'INTRO: Only {intro_overlap:.0%} keyword overlap in intro/description')
    else:
        issues.append(f'INTRO: Primary keyword missing from intro/description')

    # 5. H2/H3 subheadings — keyword in at least one (10 points)
    max_score += 10
    all_headings = ' '.join(meta.get('h2s', []) + meta.get('h3s', [])).lower()
    headings_overlap = word_overlap_score(primary_kw, all_headings)
    if primary_kw in all_headings or normalize_for_match(primary_kw) in normalize_for_match(all_headings):
        score += 10
    elif is_non_latin and all_headings:
        score += 8
    elif headings_overlap >= 0.6:
        score += 8
    elif headings_overlap >= 0.3:
        score += 5
        issues.append(f'HEADINGS: Keyword not fully present in any H2/H3')
    else:
        issues.append(f'HEADINGS: Primary keyword "{primary_kw}" missing from all H2/H3 tags')

    # 6. Meta description quality (10 points)
    max_score += 10
    desc_text = meta.get('description', '')
    desc_len = len(desc_text)
    if desc_len == 0:
        issues.append('META DESC: Missing meta description!')
    elif desc_len < 70:
        score += 3
        issues.append(f'META DESC: Too short ({desc_len} chars, aim for 120-155)')
    elif desc_len > 155:
        score += 5
        issues.append(f'META DESC: Too long ({desc_len} chars, max 155)')
    else:
        score += 10

    # Check for action verb in description (English pages only)
    page_lang = meta.get('lang', 'en')
    if desc_text and not is_non_latin and page_lang == 'en':
        action_verbs = ['calculate', 'check', 'find', 'get', 'create', 'build',
                        'generate', 'convert', 'test', 'analyze', 'compare',
                        'discover', 'explore', 'learn', 'make', 'plan', 'rate',
                        'scan', 'search', 'track', 'try', 'use', 'estimate',
                        'measure', 'evaluate', 'assess', 'paste', 'enter', 'take',
                        'predict', 'decide', 'see', 'view', 'answer', 'log',
                        'spin', 'pick', 'choose', 'select', 'run', 'verify',
                        'identify', 'determine', 'solve', 'count', 'compute',
                        'free', 'instantly', 'quickly', 'easily']
        first_word = desc_text.split()[0].lower().rstrip('.,!') if desc_text.split() else ''
        if first_word not in action_verbs:
            issues.append(f'META DESC: Should start with action verb, starts with "{first_word}"')

    # 7. Keyword density check (5 points)
    max_score += 5
    body = meta.get('body_text', '').lower()
    word_count = meta.get('word_count', 0)
    if word_count > 0:
        body_norm = normalize_for_match(body)
        primary_kw_norm = normalize_for_match(primary_kw)
        kw_count = body_norm.count(primary_kw_norm)
        density = (kw_count * len(primary_kw.split()) / word_count) * 100
        if is_non_latin:
            # Non-Latin: slug keyword density in native text is irrelevant — give full credit
            score += 5
        elif 0.5 <= density <= 2.5:
            score += 5
        elif density < 0.5:
            issues.append(f'DENSITY: Keyword density too low ({density:.1f}%, aim for 1-2%)')
        elif density > 2.5:
            issues.append(f'DENSITY: Keyword stuffing risk ({density:.1f}%, max 2.5%)')

    # Bonus checks (non-scoring but important)
    if not meta.get('has_og_image'):
        issues.append('OG IMAGE: Missing og:image tag')
    if not meta.get('canonical'):
        issues.append('CANONICAL: Missing canonical URL')
    if meta.get('faq_count', 0) < 3:
        issues.append(f'FAQs: Only {meta.get("faq_count", 0)} FAQs (aim for 5-8)')
    if meta.get('content_words', 0) < 300:
        issues.append(f'CONTENT: Only {meta.get("content_words", 0)} words in content section (aim for 300-600)')

    # Normalize score to 0-100
    final_score = int((score / max_score) * 100) if max_score > 0 else 0
    return final_score, issues, primary_kw


def find_cannibalization(all_meta):
    """Find tools competing for the same keywords."""
    keyword_map = defaultdict(list)
    for meta in all_meta:
        kw = extract_primary_keyword(meta)
        if kw:
            keyword_map[kw].append(meta['rel_path'])
            # Also check 2-word subsets
            words = kw.split()
            if len(words) >= 3:
                for i in range(len(words) - 1):
                    bigram = f"{words[i]} {words[i+1]}"
                    keyword_map[bigram].append(meta['rel_path'])

    conflicts = {}
    for kw, paths in keyword_map.items():
        if len(paths) > 1 and len(kw.split()) >= 2:
            conflicts[kw] = paths
    return conflicts


# ─── REPORT GENERATION ────────────────────────────────────────────────

def generate_score_badge(score):
    """Generate a letter grade from score."""
    if score >= 90: return 'A+'
    if score >= 80: return 'A'
    if score >= 70: return 'B'
    if score >= 60: return 'C'
    if score >= 50: return 'D'
    return 'F'


def run_audit(tools=None, verbose=False):
    """Run full SEO keyword audit on all tools."""
    if tools is None:
        tools = find_all_tools()

    print(f"\n{'='*60}")
    print(f"  SEO KEYWORD AUDIT — {len(tools)} tools")
    print(f"{'='*60}\n")

    all_meta = []
    scores = []
    all_issues = defaultdict(list)
    grade_counts = Counter()

    for filepath in tools:
        meta = extract_metadata(filepath)
        if not meta:
            continue
        all_meta.append(meta)

        score, issues, primary_kw = audit_keyword_placement(meta)
        scores.append(score)
        grade = generate_score_badge(score)
        grade_counts[grade] += 1

        if verbose or score < 70 or issues:
            if score < 70:
                print(f"  [{grade}] {score:3d}/100  {meta['rel_path']}")
                if verbose:
                    for issue in issues:
                        print(f"           -> {issue}")

        for issue in issues:
            category = issue.split(':')[0]
            all_issues[category].append(meta['rel_path'])

    # Summary
    avg_score = sum(scores) / len(scores) if scores else 0
    print(f"\n{'='*60}")
    print(f"  AUDIT SUMMARY")
    print(f"{'='*60}")
    print(f"  Tools audited:    {len(scores)}")
    print(f"  Average score:    {avg_score:.0f}/100 ({generate_score_badge(avg_score)})")
    print(f"  ")
    print(f"  Grade distribution:")
    for grade in ['A+', 'A', 'B', 'C', 'D', 'F']:
        count = grade_counts.get(grade, 0)
        bar = '#' * (count // 5) if count > 0 else ''
        print(f"    {grade:3s}: {count:4d} tools  {bar}")

    print(f"\n  Top issues (by frequency):")
    for category, paths in sorted(all_issues.items(), key=lambda x: -len(x[1])):
        print(f"    {category}: {len(paths)} tools affected")

    # Find critical issues (score < 50)
    critical = [(s, m) for s, m in zip(scores, all_meta) if s < 50]
    if critical:
        print(f"\n  CRITICAL ({len(critical)} tools scoring below 50):")
        for s, m in sorted(critical, key=lambda x: x[0])[:20]:
            print(f"    [{generate_score_badge(s)}] {s}/100  {m['rel_path']}")

    print(f"\n{'='*60}\n")
    return all_meta, scores


def run_suggest(query):
    """Get keyword suggestions for a topic using free Google Autocomplete."""
    print(f"\n{'='*60}")
    print(f"  KEYWORD SUGGESTIONS: \"{query}\"")
    print(f"{'='*60}\n")

    print("  [1/3] Fetching Google Autocomplete suggestions...")
    base_suggestions = fetch_google_autocomplete(query)
    if base_suggestions:
        print(f"  Found {len(base_suggestions)} direct suggestions:")
        for s in base_suggestions:
            intent = classify_search_intent(s)
            tail = "  (long-tail)" if is_long_tail(s) else ""
            print(f"    -> {s}  [{intent}]{tail}")
    else:
        print("  No direct suggestions found (may be rate-limited)")

    print(f"\n  [2/3] Fetching related searches (question-based)...")
    question_prefixes = ['how to', 'what is', 'why', 'can i', 'best']
    for prefix in question_prefixes:
        results = fetch_google_autocomplete(f"{prefix} {query}")
        if results:
            print(f"    \"{prefix} {query}\":")
            for r in results[:3]:
                print(f"      -> {r}")
        time.sleep(0.15)

    print(f"\n  [3/3] Long-tail variations...")
    suffixes = ['calculator', 'online free', 'tool', 'formula', 'example', 'app', 'template']
    for suffix in suffixes:
        if suffix not in query.lower():
            results = fetch_google_autocomplete(f"{query} {suffix}")
            if results:
                for r in results[:2]:
                    if is_long_tail(r):
                        print(f"    -> {r}  (long-tail)")
            time.sleep(0.15)

    # Bing site health check (if API key available)
    bing_key = load_bing_api_key()
    if bing_key:
        print(f"\n  [+] Bing Webmaster site health...")
        crawl = fetch_bing_crawl_stats()
        if crawl and isinstance(crawl, list) and len(crawl) > 0:
            latest = crawl[-1]
            print(f"    Pages in Bing index: {latest.get('InIndex', 0):,}")
            print(f"    Pages crawled/day: {latest.get('CrawledPages', 0):,}")
        traffic = fetch_bing_traffic_stats()
        if traffic and isinstance(traffic, list) and len(traffic) > 0:
            total_imp = sum(e.get('Impressions', 0) for e in traffic)
            total_clicks = sum(e.get('Clicks', 0) for e in traffic)
            print(f"    Bing impressions (period): {total_imp:,}")
            print(f"    Bing clicks (period): {total_clicks:,}")

    print(f"\n{'='*60}\n")


def run_cannibalize():
    """Find keyword cannibalization across all tools."""
    print(f"\n{'='*60}")
    print(f"  KEYWORD CANNIBALIZATION CHECK")
    print(f"{'='*60}\n")

    tools = find_all_tools()
    all_meta = []
    for filepath in tools:
        meta = extract_metadata(filepath)
        if meta:
            all_meta.append(meta)

    conflicts = find_cannibalization(all_meta)

    if not conflicts:
        print("  No keyword cannibalization found!")
    else:
        # Sort by number of competing pages
        sorted_conflicts = sorted(conflicts.items(), key=lambda x: -len(x[1]))
        print(f"  Found {len(sorted_conflicts)} keyword conflicts:\n")
        for kw, paths in sorted_conflicts[:30]:
            if len(paths) <= 5:  # Skip overly generic matches
                print(f"  Keyword: \"{kw}\" ({len(paths)} pages competing)")
                for p in paths:
                    print(f"    -> {p}")
                print()

    print(f"{'='*60}\n")


def run_report():
    """Generate comprehensive SEO report."""
    tools = find_all_tools()
    all_meta, scores = run_audit(tools, verbose=False)

    print(f"\n{'='*60}")
    print(f"  DETAILED SEO KEYWORD REPORT")
    print(f"{'='*60}\n")

    # Missing elements summary
    missing_desc = [m for m in all_meta if not m.get('description')]
    missing_h1 = [m for m in all_meta if not m.get('h1')]
    missing_canonical = [m for m in all_meta if not m.get('canonical')]
    missing_og = [m for m in all_meta if not m.get('has_og_image')]
    low_faq = [m for m in all_meta if m.get('faq_count', 0) < 3]
    low_content = [m for m in all_meta if m.get('content_words', 0) < 300]
    short_desc = [m for m in all_meta if 0 < len(m.get('description', '')) < 100]
    long_desc = [m for m in all_meta if len(m.get('description', '')) > 155]

    print("  MISSING ELEMENTS:")
    print(f"    No meta description:    {len(missing_desc)} tools")
    print(f"    No H1 tag:              {len(missing_h1)} tools")
    print(f"    No canonical URL:       {len(missing_canonical)} tools")
    print(f"    No og:image:            {len(missing_og)} tools")
    print(f"    < 3 FAQs:              {len(low_faq)} tools")
    print(f"    < 300 words content:   {len(low_content)} tools")
    print(f"    Description too short:  {len(short_desc)} tools")
    print(f"    Description too long:   {len(long_desc)} tools")

    # Title length distribution
    title_lengths = [len(m.get('title', '')) for m in all_meta]
    print(f"\n  TITLE LENGTHS:")
    print(f"    Average: {sum(title_lengths)/len(title_lengths):.0f} chars")
    print(f"    Too long (>60): {sum(1 for t in title_lengths if t > 60)}")
    print(f"    Too short (<20): {sum(1 for t in title_lengths if t < 20)}")

    # Keyword density stats
    print(f"\n  CONTENT STATS:")
    word_counts = [m.get('word_count', 0) for m in all_meta]
    content_counts = [m.get('content_words', 0) for m in all_meta]
    print(f"    Avg total words:    {sum(word_counts)/len(word_counts):.0f}")
    print(f"    Avg content words:  {sum(content_counts)/len(content_counts):.0f}")

    # Hub-level scores
    hub_scores = defaultdict(list)
    for meta, score in zip(all_meta, scores):
        hub_scores[meta['hub']].append(score)

    print(f"\n  SCORES BY HUB:")
    for hub, hub_s in sorted(hub_scores.items(), key=lambda x: -sum(x[1])/len(x[1])):
        avg = sum(hub_s) / len(hub_s)
        print(f"    {hub:25s}  avg {avg:.0f}/100  ({len(hub_s)} tools)")

    print(f"\n{'='*60}\n")


# ─── AUTO-FIX FUNCTIONS ──────────────────────────────────────────────

def generate_fix_suggestions(meta):
    """Generate auto-fixable suggestions for a tool."""
    fixes = []
    primary_kw = extract_primary_keyword(meta)
    if not primary_kw:
        return fixes

    # Fix: Meta description starts with action verb
    desc = meta.get('description', '')
    if desc:
        action_verbs = ['calculate', 'check', 'find', 'get', 'create', 'build',
                        'generate', 'convert', 'test', 'analyze', 'compare',
                        'discover', 'explore', 'learn', 'make', 'plan', 'rate',
                        'scan', 'search', 'track', 'try', 'use', 'estimate',
                        'measure', 'evaluate', 'assess', 'paste', 'enter', 'take']
        first_word = desc.split()[0].lower().rstrip('.,!') if desc.split() else ''
        if first_word not in action_verbs:
            fixes.append({
                'type': 'meta_description_verb',
                'message': f'Description should start with action verb (currently: "{first_word}")',
                'file': meta['filepath'],
            })

    # Fix: Description too short or too long
    if len(desc) < 100 and desc:
        fixes.append({
            'type': 'meta_description_short',
            'message': f'Description too short ({len(desc)} chars, aim for 120-155)',
            'file': meta['filepath'],
        })
    elif len(desc) > 155:
        fixes.append({
            'type': 'meta_description_long',
            'message': f'Description too long ({len(desc)} chars, max 155)',
            'file': meta['filepath'],
        })

    # Fix: H1 doesn't match primary keyword
    h1 = meta.get('h1', '').lower()
    if primary_kw and primary_kw not in h1:
        fixes.append({
            'type': 'h1_keyword_mismatch',
            'message': f'H1 "{meta["h1"]}" doesn\'t contain primary keyword "{primary_kw}"',
            'file': meta['filepath'],
        })

    # Fix: No "How [Tool] Works" H2
    h2_text = ' '.join(meta.get('h2s', [])).lower()
    if 'how' not in h2_text or 'works' not in h2_text:
        fixes.append({
            'type': 'missing_how_works_h2',
            'message': f'Missing "How {meta["h1"]} Works" H2 section',
            'file': meta['filepath'],
        })

    # Fix: Low FAQ count
    if meta.get('faq_count', 0) < 3:
        fixes.append({
            'type': 'low_faq_count',
            'message': f'Only {meta.get("faq_count", 0)} FAQs (aim for 5-8)',
            'file': meta['filepath'],
        })

    # Fix: Low content word count
    if meta.get('content_words', 0) < 300:
        fixes.append({
            'type': 'low_content',
            'message': f'Only {meta.get("content_words", 0)} words in content section (aim for 300-600)',
            'file': meta['filepath'],
        })

    return fixes


def run_fix(dry_run=True):
    """Auto-fix keyword placement issues."""
    tools = find_all_tools()
    print(f"\n{'='*60}")
    print(f"  SEO AUTO-FIX {'(DRY RUN)' if dry_run else '(LIVE)'} — {len(tools)} tools")
    print(f"{'='*60}\n")

    total_fixes = 0
    for filepath in tools:
        meta = extract_metadata(filepath)
        if not meta:
            continue

        fixes = generate_fix_suggestions(meta)
        if fixes:
            print(f"  {meta['rel_path']}:")
            for fix in fixes:
                print(f"    [{fix['type']}] {fix['message']}")
                total_fixes += 1
            print()

    print(f"\n  Total fixable issues: {total_fixes}")
    if dry_run:
        print(f"  Run with 'fix' (no --dry-run) to apply auto-fixes")
    print(f"\n{'='*60}\n")


# ─── FEATURE: AUTO-TRENDS FOR NEW TOOLS ──────────────────────────────

# ─── PRODUCT HUNT API ────────────────────────────────────────────────

def load_ph_token():
    """Load Product Hunt developer token from file."""
    if not os.path.exists(PH_TOKEN_FILE):
        return None
    with open(PH_TOKEN_FILE) as f:
        return f.read().strip()


def ph_graphql(query, token):
    """Execute a Product Hunt GraphQL query."""
    data = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(PH_API_URL, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "TeamzLabSEO/1.0"
    })
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        return {"error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def fetch_ph_trending(token, count=20):
    """Fetch trending products from Product Hunt (by votes)."""
    query = f"""{{
      posts(order: RANKING, first: {count}) {{
        edges {{
          node {{
            name
            tagline
            votesCount
            commentsCount
            url
            topics(first: 5) {{ edges {{ node {{ name }} }} }}
          }}
        }}
      }}
    }}"""
    return ph_graphql(query, token)


def fetch_ph_search(keyword, token, count=15):
    """Search Product Hunt for products matching a keyword.
    PH API doesn't have direct text search, so we fetch recent top posts
    and filter client-side. Also searches by topic."""

    results = []

    # Strategy 1: Search by topic slug (e.g., "baking" -> topic "baking")
    topic_slug = keyword.lower().replace(' ', '-')
    query = f"""{{
      topic(slug: "{topic_slug}") {{
        name
        postsCount
        posts(first: {count}, order: VOTES) {{
          edges {{
            node {{
              name
              tagline
              votesCount
              commentsCount
              url
              topics(first: 5) {{ edges {{ node {{ name }} }} }}
            }}
          }}
        }}
      }}
    }}"""
    resp = ph_graphql(query, token)
    if not resp.get("error") and resp.get("data", {}).get("topic"):
        topic_data = resp["data"]["topic"]
        edges = topic_data.get("posts", {}).get("edges", [])
        for edge in edges:
            node = edge["node"]
            topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])]
            results.append({
                "name": node["name"],
                "tagline": node["tagline"],
                "votes": node["votesCount"],
                "comments": node["commentsCount"],
                "url": node["url"],
                "topics": topics,
                "match": "topic"
            })

    # Strategy 2: Fetch trending and filter by keyword in name/tagline
    query2 = f"""{{
      posts(order: VOTES, first: 50) {{
        edges {{
          node {{
            name
            tagline
            votesCount
            commentsCount
            url
            topics(first: 5) {{ edges {{ node {{ name }} }} }}
          }}
        }}
      }}
    }}"""
    resp2 = ph_graphql(query2, token)
    if not resp2.get("error") and resp2.get("data", {}).get("posts"):
        kw_lower = keyword.lower()
        kw_words = set(kw_lower.split())
        for edge in resp2["data"]["posts"]["edges"]:
            node = edge["node"]
            text = f"{node['name']} {node['tagline']}".lower()
            topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])]
            topic_text = " ".join(topics).lower()
            # Match if any keyword word appears in name/tagline/topics
            if any(w in text or w in topic_text for w in kw_words):
                # Avoid duplicates
                if not any(r["name"] == node["name"] for r in results):
                    results.append({
                        "name": node["name"],
                        "tagline": node["tagline"],
                        "votes": node["votesCount"],
                        "comments": node["commentsCount"],
                        "url": node["url"],
                        "topics": topics,
                        "match": "keyword"
                    })

    # Sort by votes descending
    results.sort(key=lambda x: -x["votes"])
    return results


def run_ph_search(keyword):
    """Standalone Product Hunt search command."""
    token = load_ph_token()
    if not token:
        print(f"\n  Product Hunt API token not found.")
        print(f"  To set up:")
        print(f"    1. Go to https://api.producthunt.com/v2/oauth/applications")
        print(f"    2. Create an app → get Developer Token")
        print(f"    3. Save it: mkdir -p ~/.config/teamzlab && echo 'YOUR_TOKEN' > {PH_TOKEN_FILE}")
        return

    print(f"\n{'='*60}")
    print(f"  PRODUCT HUNT SEARCH: \"{keyword}\"")
    print(f"{'='*60}\n")

    results = fetch_ph_search(keyword, token)

    if not results:
        print(f"  No products found for \"{keyword}\"")
        print(f"  This could mean:")
        print(f"    -> Untapped niche (opportunity!)")
        print(f"    -> Keyword too specific (try broader terms)")
        return

    print(f"  Found {len(results)} related products:\n")
    for i, r in enumerate(results[:15], 1):
        topics_str = ", ".join(r["topics"][:3]) if r["topics"] else "—"
        print(f"  {i:2}. {r['name']}")
        print(f"      {r['tagline']}")
        print(f"      {r['votes']} upvotes | {r['comments']} comments | Topics: {topics_str}")
        print(f"      {r['url']}")
        print()

    # Analysis
    avg_votes = sum(r["votes"] for r in results) / len(results) if results else 0
    top_votes = results[0]["votes"] if results else 0
    all_topics = []
    for r in results:
        all_topics.extend(r["topics"])
    topic_counts = Counter(all_topics).most_common(5)

    print(f"  {'─'*50}")
    print(f"  ANALYSIS:")
    print(f"    Products found:    {len(results)}")
    print(f"    Avg upvotes:       {avg_votes:.0f}")
    print(f"    Top product:       {top_votes} upvotes")
    print(f"    Common topics:     {', '.join(t[0] for t in topic_counts)}")
    if avg_votes > 500:
        print(f"    Market signal:     HOT — established market, high competition")
    elif avg_votes > 100:
        print(f"    Market signal:     WARM — validated demand, room for new tools")
    elif results:
        print(f"    Market signal:     COOL — early market, first-mover advantage")
    else:
        print(f"    Market signal:     COLD — untapped or non-existent market")
    print(f"\n{'='*60}\n")


def run_ph_trending():
    """Show trending Product Hunt products."""
    token = load_ph_token()
    if not token:
        print(f"\n  Product Hunt API token not found.")
        print(f"  To set up:")
        print(f"    1. Go to https://api.producthunt.com/v2/oauth/applications")
        print(f"    2. Create an app → get Developer Token")
        print(f"    3. Save it: mkdir -p ~/.config/teamzlab && echo 'YOUR_TOKEN' > {PH_TOKEN_FILE}")
        return

    print(f"\n{'='*60}")
    print(f"  PRODUCT HUNT — TRENDING NOW")
    print(f"{'='*60}\n")

    resp = fetch_ph_trending(token, count=20)
    if resp.get("error"):
        print(f"  ERROR: {resp['error']}")
        return

    edges = resp.get("data", {}).get("posts", {}).get("edges", [])
    if not edges:
        print("  No trending products found.")
        return

    for i, edge in enumerate(edges, 1):
        node = edge["node"]
        topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])]
        topics_str = ", ".join(topics[:3]) if topics else "—"
        print(f"  {i:2}. {node['name']}  ({node['votesCount']} upvotes)")
        print(f"      {node['tagline']}")
        print(f"      Topics: {topics_str}")
        print(f"      {node['url']}")
        print()

    # Spot opportunities
    all_topics = []
    for edge in edges:
        for t in edge["node"].get("topics", {}).get("edges", []):
            all_topics.append(t["node"]["name"])
    topic_counts = Counter(all_topics).most_common(10)

    print(f"  {'─'*50}")
    print(f"  HOT TOPICS (build tools in these areas):")
    for topic, count in topic_counts:
        bar = "█" * count
        print(f"    {topic:25s} {bar} ({count})")
    print(f"\n{'='*60}\n")


def ph_validate_signal(keyword, token):
    """Get Product Hunt signal for validate-new. Returns (score_delta, summary)."""
    results = fetch_ph_search(keyword, token, count=10)
    if not results:
        return 5, "No PH products found — untapped niche or too specific"

    avg_votes = sum(r["votes"] for r in results) / len(results)
    top_name = results[0]["name"]
    top_votes = results[0]["votes"]

    if avg_votes > 500:
        return -5, f"HIGH competition on PH — {len(results)} products, top: {top_name} ({top_votes} votes)"
    elif avg_votes > 100:
        return 10, f"VALIDATED market — {len(results)} products, avg {avg_votes:.0f} votes. Room for a free tool"
    else:
        return 8, f"EARLY market — {len(results)} products, avg {avg_votes:.0f} votes. First-mover advantage"


# ─── BING WEBMASTER TOOLS API ────────────────────────────────────────
# Available endpoints: GetRankAndTrafficStats, GetCrawlStats, GetQueryStats,
# GetLinkCounts, GetUrlInfo. Keyword research endpoints (GetKeywordData,
# GetRelatedKeywords) were removed by Microsoft.

def load_bing_api_key():
    """Load Bing Webmaster Tools API key."""
    if os.path.exists(BING_API_KEY_FILE):
        with open(BING_API_KEY_FILE) as f:
            return f.read().strip()
    return None


def _bing_api_get(endpoint, params=None):
    """Make a Bing Webmaster Tools API request."""
    api_key = load_bing_api_key()
    if not api_key:
        return None
    base_params = f"siteUrl={urllib.parse.quote(SITE_URL + '/', safe='')}&apikey={api_key}"
    if params:
        base_params += f"&{params}"
    url = f"{BING_API_BASE}/{endpoint}?{base_params}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            raw = resp.read().decode('utf-8-sig')
            data = json.loads(raw)
            return data.get('d', data)
    except Exception as e:
        return {'error': str(e)}


def fetch_bing_traffic_stats():
    """Get Bing rank and traffic stats (clicks + impressions over time)."""
    return _bing_api_get('GetRankAndTrafficStats')


def fetch_bing_crawl_stats():
    """Get Bing crawl stats (pages crawled, indexed, errors)."""
    return _bing_api_get('GetCrawlStats')


def fetch_bing_url_info(url):
    """Get info about a specific URL on Bing."""
    return _bing_api_get('GetUrlInfo', f"url={urllib.parse.quote(url, safe='')}")


def _parse_bing_date(date_str):
    """Parse Bing's /Date(...)/ format to YYYY-MM-DD."""
    import datetime
    try:
        ts = int(date_str.split('(')[1].split('-')[0].split('+')[0]) / 1000
        return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except Exception:
        return date_str


def run_bing_stats():
    """Standalone Bing Webmaster Tools stats command."""
    api_key = load_bing_api_key()
    if not api_key:
        print(f"\n  Bing Webmaster API key not found.")
        print(f"  Get it from: Bing Webmaster Tools > Settings > API access > API Key")
        print(f"  Save it:     echo 'YOUR_KEY' > {BING_API_KEY_FILE}")
        return

    print(f"\n{'='*60}")
    print(f"  BING WEBMASTER TOOLS REPORT")
    print(f"  Site: {SITE_URL}")
    print(f"{'='*60}")

    # 1. Traffic stats
    print(f"\n  TRAFFIC (Bing Search)")
    print(f"  {'-'*50}")
    traffic = fetch_bing_traffic_stats()
    if traffic and isinstance(traffic, list) and len(traffic) > 0:
        total_clicks = sum(e.get('Clicks', 0) for e in traffic)
        total_imp = sum(e.get('Impressions', 0) for e in traffic)
        print(f"  Period: {len(traffic)} days")
        print(f"  Total clicks: {total_clicks:,}")
        print(f"  Total impressions: {total_imp:,}")
        if total_imp > 0:
            ctr = (total_clicks / total_imp) * 100
            print(f"  CTR: {ctr:.1f}%")
        print(f"\n  {'Date':<14} {'Clicks':>8} {'Impressions':>12}")
        print(f"  {'-'*14} {'-'*8} {'-'*12}")
        for e in traffic:
            dt = _parse_bing_date(e.get('Date', ''))
            print(f"  {dt:<14} {e.get('Clicks',0):>8,} {e.get('Impressions',0):>12,}")
    else:
        print(f"  No traffic data yet")

    # 2. Crawl stats
    print(f"\n  CRAWL STATS")
    print(f"  {'-'*50}")
    crawl = fetch_bing_crawl_stats()
    if crawl and isinstance(crawl, list) and len(crawl) > 0:
        latest = crawl[-1]
        print(f"  Date: {_parse_bing_date(latest.get('Date', ''))}")
        print(f"  Pages in Bing index: {latest.get('InIndex', 0):,}")
        print(f"  Pages crawled: {latest.get('CrawledPages', 0):,}")
        print(f"  2xx responses: {latest.get('Code2xx', 0):,}")
        print(f"  4xx errors: {latest.get('Code4xx', 0):,}")
        print(f"  5xx errors: {latest.get('Code5xx', 0):,}")
        print(f"  Blocked by robots.txt: {latest.get('BlockedByRobotsTxt', 0):,}")
        print(f"  Crawl errors: {latest.get('CrawlErrors', 0):,}")
        print(f"  DNS failures: {latest.get('DnsFailures', 0):,}")
    else:
        print(f"  No crawl data yet")

    # 3. Link counts
    print(f"\n  BACKLINKS")
    print(f"  {'-'*50}")
    links = _bing_api_get('GetLinkCounts')
    if links and isinstance(links, dict):
        total_pages = links.get('TotalPages', 0)
        link_list = links.get('Links', [])
        print(f"  Total linking pages: {total_pages:,}")
        if link_list:
            for lnk in link_list[:10]:
                print(f"    -> {lnk.get('Url', '?')}  ({lnk.get('LinkCount', 0)} links)")
        else:
            print(f"  No external backlinks detected yet")

    print(f"\n{'='*60}\n")


def bing_validate_signal():
    """
    Bing site validation for use in validate-new.
    Uses crawl stats to check if Bing is indexing the site well.
    Returns (score_delta, summary_string).
    """
    crawl = fetch_bing_crawl_stats()
    if not crawl or not isinstance(crawl, list) or len(crawl) == 0:
        return 0, "No Bing crawl data available"

    latest = crawl[-1]
    in_index = latest.get('InIndex', 0)
    crawled = latest.get('CrawledPages', 0)
    errors = latest.get('CrawlErrors', 0) + latest.get('Code4xx', 0) + latest.get('Code5xx', 0)

    traffic = fetch_bing_traffic_stats()
    total_imp = 0
    total_clicks = 0
    if traffic and isinstance(traffic, list):
        total_imp = sum(e.get('Impressions', 0) for e in traffic)
        total_clicks = sum(e.get('Clicks', 0) for e in traffic)

    summary = f"Bing: {in_index} indexed, {crawled} crawled/day, {total_imp} impressions, {total_clicks} clicks"
    if errors > 0:
        summary += f", {errors} errors"

    if in_index >= 500 and total_imp >= 100:
        return 10, f"STRONG Bing presence — {summary}"
    elif in_index >= 100:
        return 5, f"GROWING Bing presence — {summary}"
    elif in_index > 0:
        return 2, f"EARLY Bing presence — {summary}"
    else:
        return 0, f"NOT indexed on Bing yet — {summary}"


def run_validate_new_tool(keyword, geo=''):
    """
    Before building a new tool, validate it has search demand.
    Runs: Google Trends + Autocomplete + Bing Volume + Cannibalization + Product Hunt.
    Returns a GO/CAUTION/STOP recommendation.
    """
    print(f"\n{'='*60}")
    print(f"  NEW TOOL VALIDATION: \"{keyword}\"")
    print(f"{'='*60}\n")

    issues = []
    score = 0  # 0-100 viability score
    ph_token = load_ph_token()
    bing_key = load_bing_api_key()
    # Count available steps
    total_steps = 4  # Trends + Autocomplete + Cannibalization + Intent
    if bing_key:
        total_steps += 1
    if ph_token:
        total_steps += 1
    steps = str(total_steps)

    # 1. Check Google Trends interest
    print(f"  [1/{steps}] Checking Google Trends demand...")
    data = fetch_trends_interest(keyword, geo=geo)
    interest = data.get('interest', [])
    if interest:
        values = [p['values'][0] for p in interest if p['values']]
        avg_interest = sum(values) / len(values) if values else 0
        peak = max(values) if values else 0
        recent_3 = values[-3:] if len(values) >= 3 else values
        early_3 = values[:3] if len(values) >= 3 else values
        recent_avg = sum(recent_3) / len(recent_3) if recent_3 else 0
        early_avg = sum(early_3) / len(early_3) if early_3 else 0

        if recent_avg > early_avg * 1.15:
            direction = "RISING"
        elif recent_avg < early_avg * 0.85:
            direction = "FALLING"
        else:
            direction = "STABLE"

        print(f"    Average interest: {avg_interest:.0f}/100")
        print(f"    Peak: {peak}/100")
        print(f"    Trend: {direction}")

        if avg_interest >= 50:
            score += 35
            print(f"    HIGH demand keyword")
        elif avg_interest >= 20:
            score += 25
            print(f"    MODERATE demand keyword")
        elif avg_interest >= 5:
            score += 15
            print(f"    LOW demand keyword")
        else:
            score += 5
            issues.append("Very low search demand (avg interest < 5)")
            print(f"    VERY LOW demand — niche keyword")

        if direction == "RISING":
            score += 10
            print(f"    BONUS: Trend is rising!")
        elif direction == "FALLING":
            issues.append("Keyword interest is declining")
    else:
        print(f"    No Trends data (too niche for Google Trends)")
        score += 10  # Give benefit of doubt for niche keywords
        issues.append("No Google Trends data available")

    # 2. Check autocomplete (real searches)
    print(f"\n  [2/{steps}] Checking Google Autocomplete...")
    suggestions = fetch_google_autocomplete(keyword)
    long_tails = [s for s in suggestions if is_long_tail(s)]
    print(f"    {len(suggestions)} autocomplete suggestions found")
    print(f"    {len(long_tails)} long-tail variations")
    if suggestions:
        score += 20
        for s in suggestions[:5]:
            print(f"      -> {s}")
    else:
        score += 5
        issues.append("No autocomplete suggestions — very niche or new keyword")

    # Next step counter
    step_num = 3

    # Bing Webmaster Tools site health (optional — requires API key)
    if bing_key:
        print(f"\n  [{step_num}/{steps}] Checking Bing indexing & traffic...")
        bing_delta, bing_summary = bing_validate_signal()
        score += bing_delta
        print(f"    {bing_summary}")
        step_num += 1
    else:
        print(f"\n  [—] Bing Webmaster — SKIPPED (no API key)")
        print(f"    Set up: Get key from Bing Webmaster Tools > Settings > API access")
        print(f"    Save:   echo 'YOUR_KEY' > {BING_API_KEY_FILE}")

    # Check for cannibalization with existing tools
    print(f"\n  [{step_num}/{steps}] Checking cannibalization with existing tools...")
    tools = find_all_tools()
    all_meta = [extract_metadata(fp) for fp in tools]
    all_meta = [m for m in all_meta if m]

    kw_lower = keyword.lower()
    kw_words = set(kw_lower.split())
    overlapping = []
    for meta in all_meta:
        existing_kw = extract_primary_keyword(meta)
        if not existing_kw:
            continue
        existing_words = set(existing_kw.split())
        overlap = kw_words & existing_words
        if len(overlap) >= min(len(kw_words), len(existing_words)) * 0.6:
            overlapping.append((meta['rel_path'], existing_kw, len(overlap)))

    if overlapping:
        print(f"    WARNING: {len(overlapping)} existing tools target similar keywords:")
        for path, ekw, _ in sorted(overlapping, key=lambda x: -x[2])[:5]:
            print(f"      -> {path}  (keyword: \"{ekw}\")")
        if len(overlapping) >= 3:
            score -= 10
            issues.append(f"High cannibalization risk — {len(overlapping)} similar tools exist")
        else:
            score += 5
    else:
        score += 15
        print(f"    No cannibalization found — unique keyword!")

    # Check search intent match
    step_num += 1
    print(f"\n  [{step_num}/{steps}] Analyzing search intent...")
    intent = classify_search_intent(keyword)
    print(f"    Intent: {intent}")
    if intent == 'transactional':
        score += 10
        print(f"    Users want a TOOL — perfect for your site")
    elif intent == 'informational':
        score += 5
        print(f"    Users want INFO — consider adding educational content")
    else:
        score += 3

    # Rising queries (opportunities)
    related = data.get('related', [])
    rising = [r for r in related if 'Breakout' in r.get('value', '') or '%' in r.get('value', '')]
    if rising:
        score += 10
        print(f"\n  RISING RELATED QUERIES (trend-jack these!):")
        for r in rising[:5]:
            print(f"    -> {r['query']}  ({r['value']})")

    # Product Hunt market signal (optional)
    if ph_token:
        step_num += 1
        print(f"\n  [{step_num}/{steps}] Checking Product Hunt market signal...")
        ph_delta, ph_summary = ph_validate_signal(keyword, ph_token)
        score += ph_delta
        print(f"    {ph_summary}")
        if ph_delta < 0:
            issues.append(ph_summary)
    else:
        print(f"\n  [—] Product Hunt — SKIPPED (no token)")
        print(f"    Set up: echo 'TOKEN' > {PH_TOKEN_FILE}")

    # Final recommendation
    score = min(score, 100)
    print(f"\n{'='*60}")
    print(f"  VIABILITY SCORE: {score}/100")
    if score >= 70:
        print(f"  RECOMMENDATION:  GO — Build this tool!")
    elif score >= 45:
        print(f"  RECOMMENDATION:  CAUTION — Build it, but differentiate")
    else:
        print(f"  RECOMMENDATION:  STOP — Low demand or high competition")

    if issues:
        print(f"\n  Concerns:")
        for i in issues:
            print(f"    - {i}")

    print(f"\n  Suggested title: \"{keyword.title()} — Teamz Lab Tools\"")
    slug = keyword.lower().replace(' ', '-').replace('&', 'and')
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    print(f"  Suggested slug:  /{slug}/")
    if long_tails:
        print(f"\n  Long-tail keywords to include in content:")
        for lt in long_tails[:8]:
            print(f"    -> {lt}")

    print(f"\n{'='*60}\n")


# ─── FEATURE: INTERNAL LINKING CHECKER ───────────────────────────────

def run_internal_links():
    """
    Check internal linking between related tools.
    Finds tools that should link to each other but don't.
    """
    print(f"\n{'='*60}")
    print(f"  INTERNAL LINKING CHECKER")
    print(f"{'='*60}\n")

    tools = find_all_tools()
    all_meta = []
    for fp in tools:
        meta = extract_metadata(fp)
        if meta:
            all_meta.append(meta)

    print(f"  Scanning {len(all_meta)} tools for internal links...\n")

    # Check 1: Related tools section exists
    missing_related = []
    has_related = 0
    for meta in all_meta:
        filepath = meta['filepath']
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if 'id="related-tools"' in content or 'related-tools' in content:
                has_related += 1
            else:
                missing_related.append(meta['rel_path'])
        except Exception:
            pass

    print(f"  [1/3] Related tools section:")
    print(f"    Have related section: {has_related} tools")
    print(f"    Missing related section: {len(missing_related)} tools")
    if missing_related:
        print(f"    Examples missing related tools:")
        for p in missing_related[:10]:
            print(f"      -> {p}")

    # Check 2: Hub pages link to their tools
    print(f"\n  [2/3] Hub-to-tool linking:")
    hub_issues = 0
    hubs_checked = set()
    for meta in all_meta:
        hub = meta['hub']
        if hub in hubs_checked:
            continue
        hubs_checked.add(hub)
        hub_index = os.path.join(BASE_DIR, hub, 'index.html')
        if not os.path.exists(hub_index):
            print(f"    MISSING: /{hub}/index.html — no hub page!")
            hub_issues += 1
            continue

        try:
            with open(hub_index, 'r', encoding='utf-8', errors='ignore') as f:
                hub_content = f.read()
        except Exception:
            continue

        hub_tools = [m for m in all_meta if m['hub'] == hub]
        unlinked = []
        for tool_meta in hub_tools:
            slug = tool_meta['slug']
            if slug and slug not in hub_content and f"/{hub}/{slug}" not in hub_content:
                unlinked.append(slug)

        if unlinked:
            print(f"    /{hub}/ — {len(unlinked)} tools NOT linked from hub page:")
            for u in unlinked[:5]:
                print(f"      -> /{hub}/{u}/")
            if len(unlinked) > 5:
                print(f"      ... and {len(unlinked) - 5} more")
            hub_issues += len(unlinked)

    if hub_issues == 0:
        print(f"    All hub pages link to their tools!")

    # Check 3: Cross-hub linking opportunities (tools in same domain)
    print(f"\n  [3/3] Cross-linking opportunities:")
    # Group tools by keyword similarity
    keyword_groups = defaultdict(list)
    for meta in all_meta:
        kw = extract_primary_keyword(meta)
        if kw:
            for word in kw.split():
                if len(word) > 4:  # Only meaningful words
                    keyword_groups[word].append(meta)

    opportunities = 0
    seen_pairs = set()
    for word, tools_list in sorted(keyword_groups.items(), key=lambda x: -len(x[1])):
        if len(tools_list) < 2 or len(tools_list) > 6:
            continue
        # Check if these tools link to each other
        for i, t1 in enumerate(tools_list):
            for t2 in tools_list[i+1:]:
                if t1['hub'] == t2['hub']:
                    continue  # Same hub, already linked via hub page
                pair = tuple(sorted([t1['rel_path'], t2['rel_path']]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                # Check if t1 links to t2 or vice versa
                try:
                    with open(t1['filepath'], 'r', encoding='utf-8', errors='ignore') as f:
                        c1 = f.read()
                    with open(t2['filepath'], 'r', encoding='utf-8', errors='ignore') as f:
                        c2 = f.read()
                except Exception:
                    continue

                t1_links_t2 = t2['slug'] in c1 or t2['url'] in c1
                t2_links_t1 = t1['slug'] in c2 or t1['url'] in c2

                if not t1_links_t2 and not t2_links_t1 and opportunities < 20:
                    print(f"    {t1['rel_path']}  <->  {t2['rel_path']}")
                    opportunities += 1

    if opportunities == 0:
        print(f"    No obvious cross-linking gaps found!")
    else:
        print(f"\n    Total: {opportunities}+ cross-linking opportunities")

    print(f"\n{'='*60}\n")


# ─── FEATURE: BATCH TRENDS FOR ALL HUBS ─────────────────────────────

def run_batch_trends():
    """
    Run Google Trends on the top keyword from each hub.
    Shows which categories are rising/falling/stable.
    """
    print(f"\n{'='*60}")
    print(f"  BATCH TRENDS — ALL HUBS")
    print(f"{'='*60}\n")

    tools = find_all_tools()
    # Group by hub, pick the most representative keyword
    hub_keywords = defaultdict(list)
    for fp in tools:
        meta = extract_metadata(fp)
        if not meta:
            continue
        kw = extract_primary_keyword(meta)
        if kw:
            hub_keywords[meta['hub']].append(kw)

    # Hub to geo mapping
    hub_geo = {
        'uk': 'GB', 'au': 'AU', 'de': 'DE', 'fr': 'FR', 'nl': 'NL',
        'in': 'IN', 'jp': 'JP', 'ng': 'NG', 'za': 'ZA', 'ph': 'PH',
        'ke': 'KE', 'sa': 'SA', 'ae': 'AE', 'eg': 'EG', 'ma': 'MA',
        'sg': 'SG', 'id': 'ID', 'vn': 'VN', 'se': 'SE', 'fi': 'FI',
        'no': 'NO', 'ca': 'CA', 'us': 'US', 'eu': '', 'gh': 'GH',
    }

    print(f"  Checking {len(hub_keywords)} hubs...\n")
    print(f"  {'Hub':<20s} {'Top Keyword':<35s} {'Interest':>8s} {'Trend':>10s} {'Geo':>5s}")
    print(f"  {'-'*20} {'-'*35} {'-'*8} {'-'*10} {'-'*5}")

    results = []
    for hub in sorted(hub_keywords.keys()):
        keywords = hub_keywords[hub]
        # Pick the shortest keyword (usually the most generic/popular)
        top_kw = min(keywords, key=lambda k: len(k))

        geo = hub_geo.get(hub, '')

        try:
            data = fetch_trends_interest(top_kw, geo=geo)
            interest = data.get('interest', [])
            if interest:
                values = [p['values'][0] for p in interest if p['values']]
                avg = sum(values) / len(values) if values else 0
                recent = values[-3:] if len(values) >= 3 else values
                early = values[:3] if len(values) >= 3 else values
                r_avg = sum(recent) / len(recent) if recent else 0
                e_avg = sum(early) / len(early) if early else 0
                if r_avg > e_avg * 1.15:
                    trend = "RISING"
                elif r_avg < e_avg * 0.85:
                    trend = "FALLING"
                else:
                    trend = "STABLE"
                print(f"  {hub:<20s} {top_kw[:35]:<35s} {avg:>6.0f}/100 {trend:>10s} {geo:>5s}")
                results.append((hub, top_kw, avg, trend))
            else:
                print(f"  {hub:<20s} {top_kw[:35]:<35s} {'N/A':>8s} {'N/A':>10s} {geo:>5s}")
                results.append((hub, top_kw, 0, 'N/A'))
        except Exception as e:
            print(f"  {hub:<20s} {top_kw[:35]:<35s} {'ERROR':>8s} {'':>10s} {geo:>5s}")
            results.append((hub, top_kw, 0, 'ERROR'))

        time.sleep(0.5)  # Be polite to Google

    # Summary
    rising = [r for r in results if r[3] == 'RISING']
    falling = [r for r in results if r[3] == 'FALLING']
    high_demand = [r for r in results if r[2] >= 50]

    print(f"\n  SUMMARY:")
    if rising:
        print(f"  RISING hubs (build more tools here):")
        for hub, kw, avg, _ in rising:
            print(f"    -> /{hub}/  ({kw}, avg {avg:.0f})")
    if falling:
        print(f"  FALLING hubs (update or pivot):")
        for hub, kw, avg, _ in falling:
            print(f"    -> /{hub}/  ({kw}, avg {avg:.0f})")
    if high_demand:
        print(f"  HIGH DEMAND hubs (avg interest >= 50):")
        for hub, kw, avg, _ in sorted(high_demand, key=lambda x: -x[2])[:10]:
            print(f"    -> /{hub}/  ({kw}, avg {avg:.0f})")

    print(f"\n{'='*60}\n")


# ─── FEATURE: CONTENT FRESHNESS TRACKER ──────────────────────────────

def run_freshness():
    """
    Check all tools for stale content — outdated years, old data references,
    tools that haven't been updated recently.
    """
    import subprocess

    print(f"\n{'='*60}")
    print(f"  CONTENT FRESHNESS TRACKER")
    print(f"{'='*60}\n")

    current_year = time.strftime('%Y')
    prev_year = str(int(current_year) - 1)
    two_years_ago = str(int(current_year) - 2)

    tools = find_all_tools()
    stale_tools = []
    outdated_year = []
    no_update_6mo = []
    no_update_1yr = []

    print(f"  Scanning {len(tools)} tools for freshness...\n")

    for filepath in tools:
        rel = os.path.relpath(filepath, BASE_DIR)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue

        # Check for outdated year references in titles and descriptions
        title_match = re.search(r'<title>(.*?)</title>', content)
        title = title_match.group(1) if title_match else ''

        # Check if title has previous year
        if prev_year in title or two_years_ago in title:
            outdated_year.append((rel, f'Title contains "{prev_year}" or "{two_years_ago}"'))

        # Check if content references old year rates/data
        desc_match = re.search(r'name="description"\s+content="(.*?)"', content)
        desc = desc_match.group(1) if desc_match else ''
        if prev_year in desc:
            outdated_year.append((rel, f'Description references {prev_year}'))

        # Check git last modified date
        try:
            result = subprocess.run(
                ['git', '-C', BASE_DIR, 'log', '-1', '--format=%as', '--', filepath],
                capture_output=True, text=True, timeout=5
            )
            last_mod = result.stdout.strip()
            if last_mod:
                from datetime import datetime, timedelta
                mod_date = datetime.strptime(last_mod, '%Y-%m-%d')
                now = datetime.now()
                days_since = (now - mod_date).days

                if days_since > 365:
                    no_update_1yr.append((rel, last_mod, days_since))
                elif days_since > 180:
                    no_update_6mo.append((rel, last_mod, days_since))
        except Exception:
            pass

    # Report
    print(f"  [1/3] Outdated year references:")
    if outdated_year:
        print(f"    {len(outdated_year)} tools with old year references:")
        for path, issue in outdated_year[:15]:
            print(f"      -> {path}: {issue}")
        if len(outdated_year) > 15:
            print(f"      ... and {len(outdated_year) - 15} more")
    else:
        print(f"    All tools reference current year!")

    print(f"\n  [2/3] Not updated in 6+ months:")
    if no_update_6mo:
        print(f"    {len(no_update_6mo)} tools (6-12 months old):")
        for path, date, days in sorted(no_update_6mo, key=lambda x: -x[2])[:10]:
            print(f"      -> {path}  (last: {date}, {days} days ago)")
    else:
        print(f"    All tools updated within 6 months!")

    print(f"\n  [3/3] Not updated in 1+ year:")
    if no_update_1yr:
        print(f"    {len(no_update_1yr)} tools (12+ months old):")
        for path, date, days in sorted(no_update_1yr, key=lambda x: -x[2])[:15]:
            print(f"      -> {path}  (last: {date}, {days} days ago)")
        if len(no_update_1yr) > 15:
            print(f"      ... and {len(no_update_1yr) - 15} more")
    else:
        print(f"    All tools updated within 1 year!")

    # Summary
    total_stale = len(outdated_year) + len(no_update_1yr)
    print(f"\n  FRESHNESS SUMMARY:")
    print(f"    Total tools:           {len(tools)}")
    print(f"    Outdated years:        {len(outdated_year)}")
    print(f"    Not updated 6+ months: {len(no_update_6mo)}")
    print(f"    Not updated 1+ year:   {len(no_update_1yr)}")
    if total_stale == 0:
        print(f"    STATUS: ALL FRESH")
    elif total_stale < 10:
        print(f"    STATUS: MOSTLY FRESH — {total_stale} tools need attention")
    else:
        print(f"    STATUS: NEEDS REFRESH — {total_stale} tools are stale")

    print(f"\n{'='*60}\n")


# ─── FEATURE: VIRALITY CHECKER ───────────────────────────────────────

def run_viral_check():
    """
    Check all tools for viral-readiness:
    - Share buttons / OG tags
    - Mobile-friendliness indicators
    - Page speed indicators (file size)
    - Engagement features (results to share, download, etc.)
    """
    print(f"\n{'='*60}")
    print(f"  VIRALITY & SHARE-READINESS CHECK")
    print(f"{'='*60}\n")

    tools = find_all_tools()
    all_meta = []
    issues_summary = Counter()

    missing_og_image = []
    missing_og_desc = []
    no_share_features = []
    large_files = []
    missing_brand = []
    no_teamzlab_title = []

    for filepath in tools:
        meta = extract_metadata(filepath)
        if not meta:
            continue
        all_meta.append(meta)
        rel = meta['rel_path']

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            file_size = os.path.getsize(filepath)
        except Exception:
            continue

        # 1. OG tags (critical for social sharing)
        if 'og:image' not in content or 'og-default.png' in content:
            missing_og_image.append(rel)
            issues_summary['No custom OG image'] += 1

        if 'og:description' not in content:
            missing_og_desc.append(rel)
            issues_summary['Missing OG description'] += 1

        # 2. Share/download features
        has_share = any(x in content.lower() for x in [
            'share', 'copy to clipboard', 'download', 'export',
            'navigator.share', 'clipboard', 'copytoclipboard',
            'whatsapp', 'twitter.com/intent', 'facebook.com/sharer'
        ])
        if not has_share:
            no_share_features.append(rel)
            issues_summary['No share/copy/download feature'] += 1

        # 3. Brand consistency
        if 'Teamz Lab Tools' not in content and 'teamzlab' not in content.lower():
            missing_brand.append(rel)

        title = meta.get('title', '')
        if 'Teamz Lab' not in title and 'teamzlab' not in title.lower():
            no_teamzlab_title.append(rel)
            issues_summary['No brand in title'] += 1

        # 4. File size (affects load speed)
        if file_size > 100000:  # 100KB
            large_files.append((rel, file_size))
            issues_summary['Large HTML (>100KB)'] += 1

    # Report
    print(f"  Tools checked: {len(all_meta)}\n")

    print(f"  [1/5] OG Image (social sharing preview):")
    custom_og = len(all_meta) - len(missing_og_image)
    print(f"    Custom OG image: {custom_og} tools")
    print(f"    Using default/missing: {len(missing_og_image)} tools")
    if missing_og_image:
        print(f"    (All {len(missing_og_image)} use og-default.png — consider tool-specific images for top tools)")

    print(f"\n  [2/5] Share & Download Features:")
    has_share_count = len(all_meta) - len(no_share_features)
    print(f"    Have share/copy/download: {has_share_count} tools")
    print(f"    No share features: {len(no_share_features)} tools")
    if no_share_features:
        print(f"    Examples missing share features:")
        for p in no_share_features[:8]:
            print(f"      -> {p}")

    print(f"\n  [3/5] Brand Consistency:")
    print(f"    Title has brand: {len(all_meta) - len(no_teamzlab_title)} tools")
    print(f"    Title missing brand: {len(no_teamzlab_title)} tools")
    if no_teamzlab_title:
        for p in no_teamzlab_title[:5]:
            print(f"      -> {p}")

    print(f"\n  [4/5] Page Size (affects load speed & SEO):")
    if large_files:
        print(f"    {len(large_files)} tools over 100KB:")
        for path, size in sorted(large_files, key=lambda x: -x[1])[:10]:
            print(f"      -> {path}  ({size // 1024}KB)")
    else:
        print(f"    All tools under 100KB — good!")

    # 5. Virality score
    print(f"\n  [5/5] VIRALITY SCORECARD:")
    total = len(all_meta)
    og_score = ((total - len(missing_og_image)) / total) * 100 if total else 0
    share_score = ((total - len(no_share_features)) / total) * 100 if total else 0
    brand_score = ((total - len(no_teamzlab_title)) / total) * 100 if total else 0

    print(f"    OG images:        {og_score:.0f}% have custom images")
    print(f"    Share features:   {share_score:.0f}% have share/copy/download")
    print(f"    Brand in title:   {brand_score:.0f}%")

    viral_score = (og_score + share_score + brand_score) / 3
    print(f"\n    VIRAL READINESS:  {viral_score:.0f}/100")

    if viral_score >= 80:
        print(f"    STATUS: GOOD — Most tools are share-ready")
    elif viral_score >= 50:
        print(f"    STATUS: NEEDS WORK — Many tools lack share features")
    else:
        print(f"    STATUS: LOW — Tools need share buttons, OG images, and branding")

    # Actionable recommendations
    print(f"\n  TOP ACTIONS TO INCREASE VIRALITY:")
    if len(no_share_features) > 50:
        print(f"    1. Add 'Copy Result' or 'Share' button to {len(no_share_features)} tools")
    if len(missing_og_image) > 100:
        print(f"    2. Create custom OG images for top-traffic tools")
    if len(no_teamzlab_title) > 5:
        print(f"    3. Add '— Teamz Lab Tools' to {len(no_teamzlab_title)} tool titles")
    print(f"    4. Add Web Share API (navigator.share) for mobile sharing")
    print(f"    5. Add 'Share on WhatsApp/Twitter' buttons to result sections")
    print(f"    6. Add embed codes for tools (let bloggers embed your calculators)")

    print(f"\n{'='*60}\n")


# ═══════════════════════════════════════════════════════════════════════
# ASO (APP STORE OPTIMIZATION) MODULE
# Works for Apple App Store + Google Play Store
# Free autocomplete APIs — no accounts or API keys needed
# ═══════════════════════════════════════════════════════════════════════

# ASO character limits
ASO_LIMITS = {
    'apple': {
        'title': 30,
        'subtitle': 30,
        'keywords': 100,    # keyword field (comma-separated)
        'promo_text': 170,
        'description': 4000,
    },
    'play': {
        'title': 30,
        'short_desc': 80,
        'description': 4000,
    }
}


def fetch_appstore_autocomplete(query, country='us', limit=10):
    """Fetch Apple App Store search suggestions (free, no API key)."""
    try:
        encoded = urllib.parse.quote(query)
        url = f'https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints?media=software&term={encoded}&country={country}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            hints = data.get('hints', [])
            return [h.get('term', '') for h in hints if h.get('term')][:limit]
    except Exception:
        pass

    # Fallback: use iTunes Search API to find apps with this keyword
    try:
        encoded = urllib.parse.quote(query)
        url = f'https://itunes.apple.com/search?term={encoded}&country={country}&media=software&limit={limit}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('results', [])
            # Extract app names as keyword ideas
            names = []
            for app in results:
                name = app.get('trackName', '')
                if name and name.lower() != query.lower():
                    names.append(name)
            return names[:limit]
    except Exception:
        return []


def fetch_playstore_autocomplete(query, lang='en', country='us', limit=10):
    """Fetch Google Play Store search suggestions (free, no API key).
    Uses Google Suggest with 'app' suffix to get app-relevant completions."""
    try:
        # Primary: Google suggest with app-context query
        app_query = f"{query} app" if 'app' not in query.lower() else query
        encoded = urllib.parse.quote(app_query)
        url = f'https://suggestqueries.google.com/complete/search?client=firefox&q={encoded}&hl={lang}'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Pixel 7)',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            suggestions = data[1] if len(data) > 1 else []
            return [s for s in suggestions if s.lower() != query.lower()][:limit]
    except Exception:
        return []


def fetch_itunes_top_apps(query, country='us', limit=5):
    """Search iTunes for top apps matching a keyword — get competitor intel."""
    try:
        encoded = urllib.parse.quote(query)
        url = f'https://itunes.apple.com/search?term={encoded}&country={country}&media=software&limit={limit}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = []
            for app in data.get('results', []):
                results.append({
                    'name': app.get('trackName', ''),
                    'developer': app.get('artistName', ''),
                    'price': app.get('formattedPrice', 'Free'),
                    'rating': app.get('averageUserRating', 0),
                    'reviews': app.get('userRatingCount', 0),
                    'category': app.get('primaryGenreName', ''),
                    'url': app.get('trackViewUrl', ''),
                })
            return results
    except Exception:
        return []


def aso_keyword_score(keyword, appstore_results, playstore_results, competitors):
    """Score a keyword for ASO viability (0-100)."""
    score = 0

    # Autocomplete presence (people search for this)
    if appstore_results:
        score += 20
    if playstore_results:
        score += 20

    # Competition analysis
    if competitors:
        avg_rating = sum(c['rating'] for c in competitors if c['rating']) / max(len(competitors), 1)
        avg_reviews = sum(c['reviews'] for c in competitors) / max(len(competitors), 1)

        # Less competition = better opportunity
        if avg_reviews < 100:
            score += 20  # Low competition
        elif avg_reviews < 1000:
            score += 15
        elif avg_reviews < 10000:
            score += 10
        else:
            score += 5   # Heavy competition

        # If average rating is low, there's room to do better
        if avg_rating < 3.5:
            score += 10
        elif avg_rating < 4.0:
            score += 5
    else:
        score += 15  # No competitors found = opportunity

    # Keyword properties
    words = keyword.split()
    if len(words) >= 3:
        score += 10  # Long-tail = less competition
    elif len(words) == 2:
        score += 5

    return min(score, 100)


def run_aso_suggest(query, store='both', country='us'):
    """Get ASO keyword suggestions from App Store + Play Store autocomplete."""
    print(f"\n{'='*60}")
    print(f"  ASO KEYWORD SUGGESTIONS: \"{query}\"")
    print(f"  Store: {store.upper()}  |  Country: {country.upper()}")
    print(f"{'='*60}\n")

    appstore_results = []
    playstore_results = []

    # Apple App Store
    if store in ('both', 'apple', 'ios'):
        print("  [1/4] Apple App Store Autocomplete...")
        appstore_results = fetch_appstore_autocomplete(query, country=country)
        if appstore_results:
            print(f"    {len(appstore_results)} suggestions:")
            for s in appstore_results:
                tail = "  (long-tail)" if len(s.split()) >= 3 else ""
                print(f"      -> {s}{tail}")
        else:
            print("    No autocomplete data (trying iTunes Search...)")
            appstore_results = fetch_appstore_autocomplete(query, country=country)
            if appstore_results:
                for s in appstore_results[:5]:
                    print(f"      -> {s}")

    # Google Play Store
    if store in ('both', 'play', 'android'):
        print(f"\n  [2/4] Google Play Store Autocomplete...")
        playstore_results = fetch_playstore_autocomplete(query, country=country)
        if playstore_results:
            print(f"    {len(playstore_results)} suggestions:")
            for s in playstore_results:
                tail = "  (long-tail)" if len(s.split()) >= 3 else ""
                print(f"      -> {s}{tail}")
        else:
            print("    No autocomplete data returned")

    # Google web autocomplete (bonus — captures broader intent)
    print(f"\n  [3/4] Google Web Autocomplete (bonus)...")
    web_results = fetch_google_autocomplete(f"{query} app")
    if web_results:
        for s in web_results[:5]:
            print(f"      -> {s}")

    # Competitor apps
    print(f"\n  [4/4] Top competing apps...")
    competitors = fetch_itunes_top_apps(query, country=country)
    if competitors:
        for app in competitors:
            stars = f"{'★' * int(app['rating'])}{'☆' * (5 - int(app['rating']))}" if app['rating'] else "No rating"
            print(f"    {app['name'][:40]:<40s}  {app['price']:<8s}  {stars}  ({app['reviews']:,} reviews)")
    else:
        print("    No competing apps found — wide open market!")

    # Combined suggestions (deduplicated)
    all_suggestions = set()
    for s in appstore_results + playstore_results:
        all_suggestions.add(s.lower().strip())

    if all_suggestions:
        print(f"\n  COMBINED UNIQUE KEYWORDS ({len(all_suggestions)}):")
        for s in sorted(all_suggestions):
            # Check character count for App Store keyword field
            char_flag = " (fits in 100-char keyword field)" if len(s) <= 30 else ""
            print(f"    -> {s}{char_flag}")

    print(f"\n{'='*60}\n")
    return appstore_results, playstore_results, competitors


def run_aso_audit(title='', subtitle='', keywords='', short_desc='', description=''):
    """
    Audit app metadata against ASO best practices.
    Works for BOTH Apple App Store and Google Play Store.
    Pass your app's metadata and get a score + fix suggestions.
    """
    print(f"\n{'='*60}")
    print(f"  ASO METADATA AUDIT")
    print(f"{'='*60}\n")

    issues = []
    score = 100

    # ─── APPLE APP STORE ───
    print("  APPLE APP STORE:")

    # Title (30 chars max)
    if title:
        tlen = len(title)
        print(f"    Title: \"{title}\" ({tlen} chars)")
        if tlen > 30:
            issues.append(f'Apple title too long: {tlen}/30 chars')
            score -= 15
            print(f"      FAIL: Over 30 char limit by {tlen - 30}")
        elif tlen < 15:
            issues.append('Apple title too short — use more characters')
            score -= 5
            print(f"      WARN: Only {tlen} chars — use all 30 for SEO value")
        else:
            print(f"      OK")
    else:
        issues.append('No title provided')
        score -= 20
        print(f"    Title: MISSING")

    # Subtitle (30 chars max)
    if subtitle:
        slen = len(subtitle)
        print(f"    Subtitle: \"{subtitle}\" ({slen} chars)")
        if slen > 30:
            issues.append(f'Apple subtitle too long: {slen}/30 chars')
            score -= 10
            print(f"      FAIL: Over 30 char limit by {slen - 30}")
        else:
            print(f"      OK")

        # Check if subtitle repeats title words
        title_words = set(title.lower().split())
        sub_words = set(subtitle.lower().split())
        overlap = title_words & sub_words - {'the', 'a', 'an', 'for', 'and', 'or', 'to', 'in', 'of', 'with', '-', '&'}
        if overlap:
            issues.append(f'Subtitle repeats title words: {overlap} — use different keywords')
            score -= 5
            print(f"      WARN: Repeats title words: {overlap}")
    else:
        issues.append('No subtitle — you\'re losing 30 chars of keyword space')
        score -= 10
        print(f"    Subtitle: MISSING (losing 30 chars of keyword space!)")

    # Keywords field (100 chars, comma-separated)
    if keywords:
        klen = len(keywords)
        kw_list = [k.strip() for k in keywords.split(',') if k.strip()]
        print(f"    Keywords: {klen} chars, {len(kw_list)} terms")
        if klen > 100:
            issues.append(f'Keywords field too long: {klen}/100 chars')
            score -= 15
            print(f"      FAIL: Over 100 char limit by {klen - 100}")
        elif klen < 70:
            issues.append(f'Keywords field underused: only {klen}/100 chars')
            score -= 5
            print(f"      WARN: Only using {klen}/100 chars — add more keywords")
        else:
            print(f"      OK")

        # Check for wasted characters
        if any(' ' in k.strip() for k in kw_list):
            # Spaces between words within a keyword are fine, but spaces after commas waste chars
            pass
        if any(k.strip().lower() in title.lower() for k in kw_list):
            issues.append('Keywords field repeats title words — Apple already indexes title')
            score -= 5
            print(f"      WARN: Don't repeat title words in keyword field")

        # Check for plurals (Apple handles these automatically)
        for k in kw_list:
            if k.endswith('s') and k[:-1] in ','.join(kw_list):
                issues.append(f'Remove plural "{k}" — Apple auto-matches singular/plural')
                score -= 2
                print(f"      WARN: Remove plural \"{k}\" — Apple handles this")
    else:
        issues.append('No keywords field — critical for Apple ASO!')
        score -= 20
        print(f"    Keywords: MISSING (this is critical!)")

    # ─── GOOGLE PLAY STORE ───
    print(f"\n  GOOGLE PLAY STORE:")

    # Title (30 chars for Play too)
    if title:
        if len(title) > 30:
            print(f"    Title: FAIL — {len(title)}/30 chars")
        else:
            print(f"    Title: OK — \"{title}\" ({len(title)}/30)")

    # Short description (80 chars)
    if short_desc:
        sdlen = len(short_desc)
        print(f"    Short desc: \"{short_desc}\" ({sdlen} chars)")
        if sdlen > 80:
            issues.append(f'Play short description too long: {sdlen}/80 chars')
            score -= 10
            print(f"      FAIL: Over 80 char limit by {sdlen - 80}")
        elif sdlen < 40:
            issues.append('Play short description too short — use more of the 80 chars')
            score -= 5
            print(f"      WARN: Only {sdlen}/80 chars — add more keywords")
        else:
            print(f"      OK")
    else:
        issues.append('No short description — critical for Google Play ASO!')
        score -= 15
        print(f"    Short desc: MISSING (critical for Play Store!)")

    # Full description (4000 chars)
    if description:
        dlen = len(description)
        print(f"    Description: {dlen} chars")
        if dlen < 300:
            issues.append('Play description too short — aim for 2500-4000 chars')
            score -= 10
            print(f"      WARN: Very short — aim for 2500-4000 chars")
        elif dlen < 1000:
            score -= 5
            print(f"      OK but could be longer (aim for 2500+)")
        else:
            print(f"      OK")
    else:
        print(f"    Description: Not provided for audit")

    # ─── GENERAL ASO TIPS ───
    print(f"\n  GENERAL CHECKS:")

    # Keywords in title
    if title:
        # Check if title is purely brand name (no keywords)
        common_words = {'app', 'pro', 'lite', 'free', 'plus', 'premium', '-', ':', '—'}
        title_meaningful = [w for w in title.lower().split() if w not in common_words and len(w) > 2]
        if len(title_meaningful) < 2:
            issues.append('Title is too brand-heavy — add a keyword')
            score -= 10
            print(f"    WARN: Title needs a keyword, not just brand name")
        else:
            print(f"    OK: Title contains keywords: {title_meaningful}")

    # Action verb in subtitle
    if subtitle:
        action_verbs = ['track', 'find', 'calculate', 'check', 'scan', 'monitor', 'manage',
                        'plan', 'create', 'convert', 'analyze', 'compare', 'build', 'test',
                        'learn', 'record', 'measure', 'detect', 'generate', 'estimate']
        has_verb = any(subtitle.lower().startswith(v) or f' {v}' in subtitle.lower() for v in action_verbs)
        if has_verb:
            print(f"    OK: Subtitle has action verb")
        else:
            issues.append('Subtitle should start with an action verb (Track, Find, Calculate...)')
            score -= 3
            print(f"    WARN: Add action verb to subtitle for better CTR")

    # Score
    score = max(score, 0)
    print(f"\n{'='*60}")
    print(f"  ASO SCORE: {score}/100")
    grade = 'A+' if score >= 90 else 'A' if score >= 80 else 'B' if score >= 70 else 'C' if score >= 60 else 'D' if score >= 50 else 'F'
    print(f"  GRADE: {grade}")

    if issues:
        print(f"\n  ISSUES ({len(issues)}):")
        for i in issues:
            print(f"    - {i}")

    # Recommendations
    print(f"\n  ASO TIPS:")
    print(f"    1. Title = Brand + Top Keyword (e.g., \"Teamz Sleep Tracker\")")
    print(f"    2. Subtitle = Action verb + benefit (e.g., \"Track & Improve Your Sleep\")")
    print(f"    3. Apple keyword field: no spaces after commas, no plurals, no title repeats")
    print(f"    4. Play short desc: front-load keywords, use all 80 chars")
    print(f"    5. Update keywords monthly based on autocomplete trends")

    print(f"\n{'='*60}\n")
    return score, issues


def run_aso_validate(keyword, country='us'):
    """
    Validate an app idea before building it.
    Checks: App Store + Play Store demand, competition, Google Trends.
    Returns GO / CAUTION / STOP.
    """
    print(f"\n{'='*60}")
    print(f"  ASO APP IDEA VALIDATION: \"{keyword}\"")
    print(f"  Market: {country.upper()}")
    print(f"{'='*60}\n")

    score = 0
    issues = []

    # 1. App Store autocomplete
    print("  [1/5] Apple App Store demand...")
    appstore = fetch_appstore_autocomplete(keyword, country=country)
    if appstore:
        score += 20
        print(f"    {len(appstore)} autocomplete suggestions — people search for this!")
        for s in appstore[:5]:
            print(f"      -> {s}")
    else:
        print(f"    No autocomplete data — niche or new category")
        score += 5

    # 2. Play Store autocomplete
    print(f"\n  [2/5] Google Play Store demand...")
    playstore = fetch_playstore_autocomplete(keyword, country=country)
    if playstore:
        score += 20
        print(f"    {len(playstore)} autocomplete suggestions!")
        for s in playstore[:5]:
            print(f"      -> {s}")
    else:
        print(f"    No autocomplete data")
        score += 5

    # 3. Google Trends (overall interest)
    print(f"\n  [3/5] Google Trends interest...")
    app_query = f"{keyword} app"
    data = fetch_trends_interest(app_query)
    interest = data.get('interest', [])
    if interest:
        values = [p['values'][0] for p in interest if p['values']]
        avg = sum(values) / len(values) if values else 0
        recent = values[-3:] if len(values) >= 3 else values
        early = values[:3] if len(values) >= 3 else values
        r_avg = sum(recent) / len(recent) if recent else 0
        e_avg = sum(early) / len(early) if early else 0

        if r_avg > e_avg * 1.15:
            trend = "RISING"
        elif r_avg < e_avg * 0.85:
            trend = "FALLING"
        else:
            trend = "STABLE"

        print(f"    \"{app_query}\": avg {avg:.0f}/100, trend: {trend}")
        if avg >= 30:
            score += 15
        elif avg >= 10:
            score += 10
        else:
            score += 5
        if trend == "RISING":
            score += 5
            print(f"    BONUS: Rising trend!")
        elif trend == "FALLING":
            issues.append("Search interest is declining")
    else:
        print(f"    No Trends data for \"{app_query}\"")
        score += 5

    # 4. Competition analysis
    print(f"\n  [4/5] Competition analysis...")
    competitors = fetch_itunes_top_apps(keyword, country=country, limit=5)
    if competitors:
        print(f"    Top {len(competitors)} competing apps:")
        total_reviews = 0
        for app in competitors:
            stars = f"{app['rating']:.1f}★" if app['rating'] else "N/A"
            print(f"      {app['name'][:40]:<40s}  {app['price']:<8s}  {stars}  ({app['reviews']:,} reviews)")
            total_reviews += app['reviews']

        avg_reviews = total_reviews / len(competitors)
        if avg_reviews < 500:
            score += 15
            print(f"\n    LOW competition (avg {avg_reviews:.0f} reviews) — good opportunity!")
        elif avg_reviews < 5000:
            score += 10
            print(f"\n    MODERATE competition (avg {avg_reviews:.0f} reviews)")
        elif avg_reviews < 50000:
            score += 5
            print(f"\n    HIGH competition (avg {avg_reviews:.0f} reviews)")
            issues.append(f"High competition — avg {avg_reviews:.0f} reviews per competitor")
        else:
            score += 2
            print(f"\n    VERY HIGH competition (avg {avg_reviews:.0f} reviews)")
            issues.append(f"Very high competition — dominated by major apps")

        # Check if there's a gap (low-rated competitors)
        low_rated = [c for c in competitors if c['rating'] and c['rating'] < 3.5]
        if low_rated:
            score += 5
            print(f"    GAP FOUND: {len(low_rated)} competitors rated below 3.5★ — room to do better!")
    else:
        score += 15
        print(f"    No competing apps found — blue ocean!")

    # 5. Monetization potential
    print(f"\n  [5/5] Monetization potential...")
    high_value_categories = ['finance', 'health', 'business', 'productivity', 'education']
    kw_lower = keyword.lower()
    is_high_value = any(cat in kw_lower for cat in high_value_categories)
    if is_high_value:
        score += 10
        print(f"    HIGH value category — good ad/IAP potential")
    elif competitors:
        paid = [c for c in competitors if c['price'] != 'Free']
        if paid:
            score += 8
            print(f"    {len(paid)} paid competitors — users willing to pay")
        else:
            score += 5
            print(f"    All competitors are free — monetize with ads/IAP")
    else:
        score += 5
        print(f"    Unknown monetization potential")

    # Final recommendation
    score = min(score, 100)
    print(f"\n{'='*60}")
    print(f"  VIABILITY SCORE: {score}/100")
    if score >= 70:
        print(f"  RECOMMENDATION:  GO — Build this app!")
    elif score >= 45:
        print(f"  RECOMMENDATION:  CAUTION — Build it, but differentiate")
    else:
        print(f"  RECOMMENDATION:  STOP — Low demand or too competitive")

    if issues:
        print(f"\n  Concerns:")
        for i in issues:
            print(f"    - {i}")

    # Suggest metadata
    print(f"\n  SUGGESTED METADATA:")
    # Smart title (30 chars)
    brand = "Teamz"
    kw_title = keyword.title()
    if len(f"{brand} {kw_title}") <= 30:
        print(f"    Apple Title: \"{brand} {kw_title}\"")
    elif len(kw_title) <= 30:
        print(f"    Apple Title: \"{kw_title}\"")
    else:
        print(f"    Apple Title: \"{kw_title[:30]}\"")

    # Subtitle suggestion
    print(f"    Subtitle:    \"Track & {keyword.title().split()[0]} with Ease\"")

    # Play short description
    print(f"    Play Short:  \"Free {keyword.lower()} — no sign-up, works offline.\"")

    # Long-tail keywords from autocomplete
    all_kw = set()
    for s in (appstore or []) + (playstore or []):
        all_kw.add(s.lower())
    if all_kw:
        print(f"\n  KEYWORD IDEAS FOR APPLE KEYWORD FIELD:")
        # Build a comma-separated list that fits in 100 chars
        kw_field = []
        char_count = 0
        for k in sorted(all_kw):
            # Remove the original query to save space
            words = k.replace(keyword.lower(), '').strip()
            if words and char_count + len(words) + 1 <= 100:
                kw_field.append(words)
                char_count += len(words) + 1
        if kw_field:
            field_str = ','.join(kw_field)
            print(f"    Keywords ({len(field_str)} chars): {field_str}")

    print(f"\n{'='*60}\n")
    return score


def run_aso_compare(name1, name2, country='us'):
    """Compare two app name/keyword ideas side by side."""
    print(f"\n{'='*60}")
    print(f"  ASO COMPARISON")
    print(f"  A: \"{name1}\"")
    print(f"  B: \"{name2}\"")
    print(f"{'='*60}\n")

    results = {}
    for label, name in [('A', name1), ('B', name2)]:
        print(f"  --- {label}: \"{name}\" ---")

        # Length check
        fits_title = len(name) <= 30
        print(f"    Length: {len(name)} chars {'(fits title)' if fits_title else '(TOO LONG for title)'}")

        # App Store autocomplete
        appstore = fetch_appstore_autocomplete(name, country=country)
        print(f"    App Store suggestions: {len(appstore)}")

        # Play Store autocomplete
        playstore = fetch_playstore_autocomplete(name, country=country)
        print(f"    Play Store suggestions: {len(playstore)}")

        # Google autocomplete
        web = fetch_google_autocomplete(name)
        print(f"    Google suggestions: {len(web)}")

        # Competitors
        competitors = fetch_itunes_top_apps(name, country=country, limit=3)
        if competitors:
            avg_reviews = sum(c['reviews'] for c in competitors) / len(competitors)
            print(f"    Competition: {len(competitors)} apps, avg {avg_reviews:.0f} reviews")
        else:
            avg_reviews = 0
            print(f"    Competition: None found")

        total_suggestions = len(appstore) + len(playstore) + len(web)
        comp_score = 100 - min(avg_reviews / 1000, 50)  # Lower reviews = better

        results[label] = {
            'name': name,
            'fits': fits_title,
            'suggestions': total_suggestions,
            'competition': avg_reviews,
            'score': total_suggestions * 2 + comp_score + (10 if fits_title else 0)
        }
        print()
        time.sleep(0.3)

    # Winner
    a, b = results['A'], results['B']
    print(f"  COMPARISON:")
    print(f"    {'Metric':<25s} {'A':>10s} {'B':>10s}")
    print(f"    {'-'*25} {'-'*10} {'-'*10}")
    print(f"    {'Fits 30-char title':<25s} {'Yes' if a['fits'] else 'No':>10s} {'Yes' if b['fits'] else 'No':>10s}")
    print(f"    {'Total suggestions':<25s} {a['suggestions']:>10d} {b['suggestions']:>10d}")
    print(f"    {'Avg competitor reviews':<25s} {a['competition']:>10,.0f} {b['competition']:>10,.0f}")
    print(f"    {'Overall score':<25s} {a['score']:>10.0f} {b['score']:>10.0f}")

    if a['score'] > b['score']:
        print(f"\n  WINNER: A — \"{name1}\"")
    elif b['score'] > a['score']:
        print(f"\n  WINNER: B — \"{name2}\"")
    else:
        print(f"\n  TIE — Both are equally viable")

    print(f"\n{'='*60}\n")


# ─── MAIN ─────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1].lower()

    if PROJECT_TYPE == "app" and command in WEB_ONLY_COMMANDS:
        print(f"INFO: '{command}' is website-focused and disabled for TEAMZ_PROJECT_TYPE=app.")
        print("      Use ASO commands instead: aso-suggest, aso-audit, aso-validate, aso-compare.")
        sys.exit(2)

    if command == 'audit':
        verbose = '--verbose' in sys.argv or '-v' in sys.argv
        run_audit(verbose=verbose)

    elif command == 'suggest':
        if len(sys.argv) < 3:
            print("Usage: python3 seo-keyword-engine.py suggest \"keyword\"")
            sys.exit(1)
        query = ' '.join(sys.argv[2:])
        query = query.strip('"\'')
        run_suggest(query)

    elif command == 'cannibalize':
        run_cannibalize()

    elif command == 'report':
        run_report()

    elif command == 'trends':
        # Parse --geo flag
        geo = ''
        args = sys.argv[2:]
        filtered = []
        i = 0
        while i < len(args):
            if args[i] == '--geo' and i + 1 < len(args):
                geo = args[i+1].upper()
                i += 2
            elif args[i].startswith('--geo='):
                geo = args[i].split('=', 1)[1].upper()
                i += 1
            elif not args[i].startswith('-'):
                filtered.append(args[i].strip('"\''))
                i += 1
            else:
                i += 1
        if not filtered:
            print("Usage: python3 seo-keyword-engine.py trends \"keyword1\" [\"keyword2\"] [--geo US]")
            print("  Single:   trends \"bmi calculator\"")
            print("  Compare:  trends \"bmi calculator\" \"body mass index calculator\"")
            print("  Regional: trends \"tax calculator\" --geo GB")
            print("  Geo codes: US, GB, DE, FR, IN, AU, NL, JP, etc.")
            sys.exit(1)
        run_trends(filtered, geo=geo)

    elif command == 'validate-new':
        keywords = [a for a in sys.argv[2:] if not a.startswith('-')]
        keywords = [k.strip('"\'') for k in keywords]
        geo = ''
        for i, a in enumerate(sys.argv):
            if a == '--geo' and i + 1 < len(sys.argv):
                geo = sys.argv[i+1].upper()
        if not keywords:
            print("Usage: python3 seo-keyword-engine.py validate-new \"keyword\" [--geo US]")
            sys.exit(1)
        run_validate_new_tool(keywords[0], geo=geo)

    elif command == 'bing-stats':
        run_bing_stats()

    elif command == 'internal-links':
        run_internal_links()

    elif command == 'batch-trends':
        run_batch_trends()

    elif command == 'freshness':
        run_freshness()

    elif command == 'viral':
        run_viral_check()

    elif command == 'aso-suggest':
        keywords = [a for a in sys.argv[2:] if not a.startswith('-')]
        keywords = [k.strip('"\'') for k in keywords]
        store = 'both'
        country = 'us'
        for i, a in enumerate(sys.argv):
            if a == '--store' and i + 1 < len(sys.argv):
                store = sys.argv[i+1].lower()
            if a == '--country' and i + 1 < len(sys.argv):
                country = sys.argv[i+1].lower()
        if not keywords:
            print("Usage: python3 seo-keyword-engine.py aso-suggest \"keyword\" [--store both|apple|play] [--country us]")
            sys.exit(1)
        run_aso_suggest(keywords[0], store=store, country=country)

    elif command == 'aso-audit':
        title = subtitle = keywords_field = short_desc = description = ''
        for i, a in enumerate(sys.argv):
            if a == '--title' and i + 1 < len(sys.argv):
                title = sys.argv[i+1]
            if a == '--subtitle' and i + 1 < len(sys.argv):
                subtitle = sys.argv[i+1]
            if a == '--keywords' and i + 1 < len(sys.argv):
                keywords_field = sys.argv[i+1]
            if a == '--short-desc' and i + 1 < len(sys.argv):
                short_desc = sys.argv[i+1]
            if a == '--description' and i + 1 < len(sys.argv):
                description = sys.argv[i+1]
        if not title:
            print('Usage: python3 seo-keyword-engine.py aso-audit --title "App Name" --subtitle "Tagline" --keywords "kw1,kw2,kw3" --short-desc "Play Store short"')
            sys.exit(1)
        run_aso_audit(title=title, subtitle=subtitle, keywords=keywords_field, short_desc=short_desc, description=description)

    elif command == 'aso-validate':
        keywords = [a for a in sys.argv[2:] if not a.startswith('-')]
        keywords = [k.strip('"\'') for k in keywords]
        country = 'us'
        for i, a in enumerate(sys.argv):
            if a == '--country' and i + 1 < len(sys.argv):
                country = sys.argv[i+1].lower()
        if not keywords:
            print('Usage: python3 seo-keyword-engine.py aso-validate "app idea keyword" [--country us]')
            sys.exit(1)
        run_aso_validate(keywords[0], country=country)

    elif command == 'aso-compare':
        keywords = [a for a in sys.argv[2:] if not a.startswith('-')]
        keywords = [k.strip('"\'') for k in keywords]
        country = 'us'
        for i, a in enumerate(sys.argv):
            if a == '--country' and i + 1 < len(sys.argv):
                country = sys.argv[i+1].lower()
        if len(keywords) < 2:
            print('Usage: python3 seo-keyword-engine.py aso-compare "Name A" "Name B" [--country us]')
            sys.exit(1)
        run_aso_compare(keywords[0], keywords[1], country=country)

    elif command == 'ph-search':
        keywords = [a for a in sys.argv[2:] if not a.startswith('-')]
        keywords = [k.strip('"\'') for k in keywords]
        if not keywords:
            print("Usage: python3 seo-keyword-engine.py ph-search \"keyword\"")
            sys.exit(1)
        run_ph_search(keywords[0])

    elif command == 'ph-trending':
        run_ph_trending()

    elif command == 'fix':
        dry_run = '--dry-run' in sys.argv
        run_fix(dry_run=dry_run)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
