#!/usr/bin/env python3
"""
build-reddit-rpm-tracker.py — Pull "what's your RPM/eCPM" community data.

Scrapes public Reddit JSON endpoints (no auth required, rate-limited)
for posts/comments mentioning RPM/EPMV/CPM/eCPM/ARPDAU in the last 90 days.

Modes:
  --niche web   (default) → AdSense/SEO publishers (r/Adsense, r/SEO, r/Mediavine_Publishers, ...)
                            Output: data/reddit-rpm-crowd.json
  --niche aso             → Mobile-app monetization (r/AdMob, r/iOSProgramming, r/androiddev, ...)
                            Output: data/reddit-aso-rpm-crowd.json

Extracts: $XX.XX RPM/eCPM mentions + niche context. Aggregates into JSON.

Used by /ideas (web) and ASO orchestrator (mobile) to validate or correct
static benchmarks with crowd-current data.

Reddit JSON endpoints are public + free, but throttle to ~1 request/sec
and use a real User-Agent. We retrieve top + new posts, plus comments.

Usage:
  python3 build-reddit-rpm-tracker.py                  # web mode, full refresh
  python3 build-reddit-rpm-tracker.py --quick          # web mode, top 25 only
  python3 build-reddit-rpm-tracker.py --niche aso      # ASO mode, full
  python3 build-reddit-rpm-tracker.py --niche aso --quick
  python3 build-reddit-rpm-tracker.py --report         # show web aggregated
  python3 build-reddit-rpm-tracker.py --niche aso --report
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

UA = 'TeamzLabTools-RPM-Research/1.0 (research; not a bot)'

# Web-publisher mode: AdSense / Mediavine / Ezoic / SEO crowds
WEB_SUBREDDITS = [
    'Adsense',
    'juststart',
    'SEO',
    'Blogging',
    'Mediavine_Publishers',
    'Ezoic',
    'NicheSiteProject',
]

WEB_NICHE_KEYWORDS = {
    'finance': ['finance', 'money', 'investing', 'invest', 'stock', 'crypto'],
    'tax': ['tax', 'taxes', 'irs', 'hmrc', 'iras', 'cra', 'ato'],
    'insurance': ['insurance', 'policy', 'premium'],
    'mortgage': ['mortgage', 'home loan', 'real estate'],
    'health-supplements': ['supplement', 'vitamin', 'nutrition'],
    'health-general': ['health', 'medical', 'wellness'],
    'longevity': ['longevity', 'biohack', 'phenoage', 'biological age'],
    'business-saas': ['saas', 'b2b', 'software', 'tech business'],
    'parenting-family': ['parenting', 'parent', 'baby', 'mom blog', 'family'],
    'food-recipes': ['recipe', 'food', 'cooking', 'baking'],
    'travel': ['travel', 'trip', 'destination'],
    'productivity': ['productivity', 'tool', 'app review'],
    'fitness-workout': ['fitness', 'workout', 'gym'],
    'gaming': ['gaming', 'game review'],
    'lifestyle': ['lifestyle', 'fashion', 'beauty'],
    'home-improvement': ['home improvement', 'diy'],
    'auto': ['auto', 'car', 'vehicle'],
    'real-estate': ['real estate', 'realtor'],
    'education': ['education', 'tutorial', 'course'],
    'legal': ['legal', 'lawyer', 'attorney'],
    'entertainment': ['entertainment', 'celebrity', 'movie'],
}

# ASO mode: AdMob / IAP / app monetization crowds
ASO_SUBREDDITS = [
    'admob',
    'iOSProgramming',
    'androiddev',
    'AppDevelopers',
    'PlayConsole',
    'ASO',
    'mobiledev',
    'indiedev',
    'gamedev',
    'playstore',
]

ASO_NICHE_KEYWORDS = {
    'casual-games': ['casual game', 'puzzle game', 'idle game', 'hyper casual', 'arcade'],
    'word-trivia-games': ['word game', 'trivia game', 'crossword', 'wordle'],
    'rpg-strategy-games': ['rpg', 'strategy game', 'card game', 'tcg', '4x'],
    'simulation-games': ['simulation', 'tycoon', 'farming sim', 'idle clicker'],
    'productivity-apps': ['productivity', 'todo app', 'note app', 'planner'],
    'finance-apps': ['finance app', 'budget app', 'expense tracker', 'investing app'],
    'health-fitness-apps': ['fitness app', 'workout app', 'health app', 'meditation app'],
    'photo-video-apps': ['photo editor', 'video editor', 'camera app', 'filter app'],
    'social-dating-apps': ['social app', 'dating app', 'chat app', 'messaging'],
    'utility-apps': ['utility app', 'tool app', 'calculator app', 'converter app'],
    'kids-education-apps': ['kids app', 'education app', 'learning app', 'language app'],
    'shopping-apps': ['shopping app', 'ecommerce app', 'marketplace app'],
    'news-magazines': ['news app', 'magazine app', 'reader app'],
    'lifestyle-apps': ['lifestyle app', 'horoscope', 'recipe app', 'travel app'],
    'web3-crypto-apps': ['crypto app', 'wallet app', 'web3 app', 'nft app'],
}

NICHE_MODES = {
    'web': {
        'subreddits': WEB_SUBREDDITS,
        'keywords': WEB_NICHE_KEYWORDS,
        'output': ROOT / 'data' / 'reddit-rpm-crowd.json',
        'context_re': re.compile(r'(rpm|epmv|cpm|earnings|revenue)', re.I),
        'label': 'web AdSense/SEO publishers',
    },
    'aso': {
        'subreddits': ASO_SUBREDDITS,
        'keywords': ASO_NICHE_KEYWORDS,
        'output': ROOT / 'data' / 'reddit-aso-rpm-crowd.json',
        'context_re': re.compile(r'(rpm|ecpm|epmv|cpm|arpdau|arppu|iap revenue|ad revenue|monetization|earnings|revenue|rev share)', re.I),
        'label': 'mobile-app AdMob/IAP monetization',
    },
}

# RPM/EPMV/CPM/eCPM dollar pattern: e.g. "$5", "$5.50", "$15-25 eCPM", "RPM of $8"
DOLLAR_RE = re.compile(r'\$\s?(\d{1,3}(?:\.\d{1,2})?)\s*(?:RPM|EPMV|CPM|ECPM|ARPDAU|ARPPU)?', re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print(f'  ERROR {url}: {e}', file=sys.stderr)
        return None


def detect_niche(text, niche_keywords):
    text_l = text.lower()
    for niche, kws in niche_keywords.items():
        if any(kw in text_l for kw in kws):
            return niche
    return 'unknown'


def extract_rpm_mentions(text, mode_cfg):
    """Return list of (rpm_dollars, niche) tuples found in text."""
    if not text or not mode_cfg['context_re'].search(text):
        return []
    matches = []
    for m in DOLLAR_RE.finditer(text):
        try:
            val = float(m.group(1))
            # Filter: realistic RPM/eCPM is $0.10 - $200
            if 0.1 <= val <= 200:
                niche = detect_niche(text, mode_cfg['keywords'])
                matches.append({'rpm': val, 'niche': niche})
        except ValueError:
            continue
    return matches


def scan_subreddit(sub, mode_cfg, limit=50):
    print(f'  Scanning r/{sub} (top + new, last {limit} posts each)...')
    rpm_data = []
    for endpoint in ['top.json?t=year&limit=' + str(limit),
                     'new.json?limit=' + str(limit)]:
        url = f'https://www.reddit.com/r/{sub}/{endpoint}'
        data = fetch(url)
        time.sleep(1.2)  # rate-limit politely
        if not data:
            continue
        for child in data.get('data', {}).get('children', []):
            post = child.get('data', {})
            text = (post.get('title', '') + '\n' +
                    post.get('selftext', ''))
            mentions = extract_rpm_mentions(text, mode_cfg)
            for m in mentions:
                m['source_sub'] = sub
                m['source_url'] = 'https://reddit.com' + post.get('permalink', '')
                m['post_score'] = post.get('score', 0)
                rpm_data.append(m)

            # Also scan top-level comments
            permalink = post.get('permalink')
            if permalink and post.get('num_comments', 0) > 5:
                cmt_data = fetch(f'https://www.reddit.com{permalink}.json?limit=20')
                time.sleep(1.2)
                if cmt_data and len(cmt_data) > 1:
                    for cmt in cmt_data[1].get('data', {}).get('children', [])[:20]:
                        cmt_text = cmt.get('data', {}).get('body', '')
                        for m in extract_rpm_mentions(cmt_text, mode_cfg):
                            m['source_sub'] = sub
                            m['source_url'] = 'https://reddit.com' + permalink
                            m['comment_score'] = cmt.get('data', {}).get('score', 0)
                            rpm_data.append(m)
    print(f'    Found {len(rpm_data)} RPM mentions in r/{sub}')
    return rpm_data


def aggregate(all_mentions):
    by_niche = defaultdict(list)
    for m in all_mentions:
        by_niche[m['niche']].append(m['rpm'])

    summary = {}
    for niche, vals in by_niche.items():
        if len(vals) < 3:
            continue
        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        median = vals_sorted[n // 2]
        p25 = vals_sorted[n // 4] if n >= 4 else vals_sorted[0]
        p75 = vals_sorted[3 * n // 4] if n >= 4 else vals_sorted[-1]
        summary[niche] = {
            'count': n,
            'median': round(median, 2),
            'p25': round(p25, 2),
            'p75': round(p75, 2),
            'min': round(min(vals), 2),
            'max': round(max(vals), 2),
        }
    return summary


def get_niche_arg():
    if '--niche' in sys.argv:
        idx = sys.argv.index('--niche')
        if idx + 1 < len(sys.argv):
            val = sys.argv[idx + 1].lower()
            if val in NICHE_MODES:
                return val
            print(f'ERROR: --niche must be one of: {", ".join(NICHE_MODES.keys())}', file=sys.stderr)
            sys.exit(2)
    return 'web'


def main():
    quick = '--quick' in sys.argv
    report_only = '--report' in sys.argv
    niche = get_niche_arg()
    mode_cfg = NICHE_MODES[niche]
    OUT = mode_cfg['output']

    if report_only:
        if not OUT.exists():
            print(f'No data yet for niche={niche} — run without --report first.')
            return
        d = json.loads(OUT.read_text())
        print(f'Niche: {niche} ({mode_cfg["label"]})')
        print(f'Last refreshed: {d.get("last_refreshed", "?")}')
        print(f'Total mentions: {len(d.get("mentions", []))}')
        print()
        print(f'{"NICHE":<24} {"N":>4} {"P25":>7} {"MED":>7} {"P75":>7}  {"RANGE":>20}')
        print('-' * 80)
        for n, s in sorted(d.get('aggregated', {}).items(),
                           key=lambda x: -x[1]['median']):
            rng = f'${s["min"]:.1f}-${s["max"]:.1f}'
            print(f'{n:<24} {s["count"]:>4} ${s["p25"]:>6.2f} ${s["median"]:>6.2f} ${s["p75"]:>6.2f}  {rng:>20}')
        return

    limit = 25 if quick else 75
    print(f'=== Reddit RPM Tracker — niche={niche} ({mode_cfg["label"]}), limit={limit}/sub ===')
    all_mentions = []
    for sub in mode_cfg['subreddits']:
        all_mentions.extend(scan_subreddit(sub, mode_cfg, limit=limit))

    aggregated = aggregate(all_mentions)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'niche': niche,
        'last_refreshed': time.strftime('%Y-%m-%d'),
        'subreddits_scanned': mode_cfg['subreddits'],
        'total_mentions': len(all_mentions),
        'aggregated': aggregated,
        'mentions': all_mentions[:500],  # cap stored mentions
    }, indent=2), encoding='utf-8')
    print()
    print(f'Wrote {OUT.relative_to(ROOT)}')
    print(f'  Total mentions: {len(all_mentions)}')
    print(f'  Niches with data: {len(aggregated)}')


if __name__ == '__main__':
    main()
