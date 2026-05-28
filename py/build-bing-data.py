#!/usr/bin/env python3
"""
Bing Webmaster Tools — Data Fetcher (top queries, top pages, crawl stats).

Pulls Bing search performance + crawl health for the current Teamz project.
Generic across Teamz projects — uses _teamz_config to resolve site + data paths.

Reads:
  TEAMZ_BING_KEY_FILE (env)  default: ~/.config/teamzlab/bing-webmaster-api-key.txt
  TEAMZ_SITE_URL      (env)  default: https://tool.teamzlab.com/

Writes (inside host_site_root/data/):
  bing-data-latest.json         (overwritten each run)
  bing-data-YYYY-MM-DD.json     (dated snapshot)

Usage:
  python3 build-bing-data.py             # full pull + summary
  python3 build-bing-data.py --quiet     # JSON only, no human output
  python3 build-bing-data.py --top 20    # show top N per category
"""
import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# Load shared Teamz config (env, paths, site URL).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _teamz_config import load_runtime  # noqa: E402

BASE = 'https://ssl.bing.com/webmaster/api.svc/json'
SSL_CTX = ssl.create_default_context()


def load_key(cfg):
    key_file = Path(
        os.path.expanduser(
            os.getenv('TEAMZ_BING_KEY_FILE', str(cfg['config_dir'] / 'bing-webmaster-api-key.txt'))
        )
    )
    if not key_file.exists():
        print(f"ERROR: Bing API key not found at {key_file}", file=sys.stderr)
        sys.exit(1)
    return key_file.read_text().strip()


def fetch(endpoint, key, site, extra_params=None):
    params = {'siteUrl': site, 'apikey': key}
    if extra_params:
        params.update(extra_params)
    url = f'{BASE}/{endpoint}?{urllib.parse.urlencode(params)}'
    try:
        with urllib.request.urlopen(url, context=SSL_CTX, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'_error': f'HTTP {e.code}', '_body': e.read().decode('utf-8', errors='ignore')[:500]}
    except Exception as e:
        return {'_error': str(e)}


def normalize_list(raw, key='d'):
    """Bing wraps responses in {'d': [...]} or {'d': {...}}. Unwrap."""
    if not isinstance(raw, dict):
        return []
    if '_error' in raw:
        return raw
    d = raw.get(key, raw)
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        return [d]
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quiet', action='store_true', help='JSON only, no human-readable output')
    parser.add_argument('--top', type=int, default=10, help='Show top N per category (default 10)')
    args = parser.parse_args()

    cfg = load_runtime(__file__)
    site = cfg['site_url']
    key = load_key(cfg)
    out_dir = cfg['host_site_root'] / 'data'
    out_dir.mkdir(exist_ok=True)

    if not args.quiet:
        print("=" * 64)
        print(f"  BING WEBMASTER DATA PULL — {site}")
        print("=" * 64)

    # 1. Top search queries (last 6 months default)
    queries_raw = fetch('GetQueryStats', key, site)
    queries = normalize_list(queries_raw)

    # 2. Top pages by clicks
    pages_raw = fetch('GetPageStats', key, site)
    pages = normalize_list(pages_raw)

    # 3. Crawl stats (errors, blocked URLs, indexed)
    crawl_raw = fetch('GetCrawlStats', key, site)
    crawl = normalize_list(crawl_raw)

    # 4. Rank & traffic summary (impressions/clicks over time)
    rank_raw = fetch('GetRankAndTrafficStats', key, site)
    rank = normalize_list(rank_raw)

    # 5. URL submission quota
    quota_raw = fetch('GetUrlSubmissionQuota', key, site)
    quota = quota_raw.get('d', {}) if isinstance(quota_raw, dict) and '_error' not in quota_raw else {'_error': quota_raw.get('_error')}

    # Assemble snapshot
    snapshot = {
        'site': site,
        'fetched_at': datetime.now().isoformat(),
        'queries': queries if isinstance(queries, list) else [],
        'pages': pages if isinstance(pages, list) else [],
        'crawl': crawl if isinstance(crawl, list) else [],
        'rank': rank if isinstance(rank, list) else [],
        'quota': quota,
        'errors': {},
    }
    for label, raw in [('queries', queries_raw), ('pages', pages_raw), ('crawl', crawl_raw),
                       ('rank', rank_raw), ('quota', quota_raw)]:
        if isinstance(raw, dict) and '_error' in raw:
            snapshot['errors'][label] = raw['_error']

    # Save
    out_latest = out_dir / 'bing-data-latest.json'
    out_dated = out_dir / f'bing-data-{datetime.now().strftime("%Y-%m-%d")}.json'
    out_latest.write_text(json.dumps(snapshot, indent=2))
    out_dated.write_text(json.dumps(snapshot, indent=2))

    if args.quiet:
        return

    # Human summary
    print()
    if snapshot['errors']:
        print("  ⚠️  Endpoint errors:")
        for label, err in snapshot['errors'].items():
            print(f"     {label}: {err}")
        print()

    print(f"  📊 TOP {args.top} BING SEARCH QUERIES")
    print("  " + "-" * 60)
    if queries and isinstance(queries, list):
        sorted_q = sorted(queries, key=lambda q: q.get('Clicks', 0), reverse=True)[:args.top]
        for q in sorted_q:
            qstr = q.get('Query', '?')[:48].ljust(48)
            clicks = q.get('Clicks', 0)
            impr = q.get('Impressions', 0)
            pos = q.get('AvgImpressionPosition', 0)
            print(f"  {qstr} clicks={clicks:>4} impr={impr:>5} pos={pos:>4.1f}")
    else:
        print("  (no query data — check errors above)")
    print()

    print(f"  📄 TOP {args.top} BING PAGES (by clicks)")
    print("  " + "-" * 60)
    if pages and isinstance(pages, list):
        sorted_p = sorted(pages, key=lambda p: p.get('Clicks', 0), reverse=True)[:args.top]
        for p in sorted_p:
            url = (p.get('Page') or p.get('Query') or '?').replace(site, '/')[:50].ljust(50)
            clicks = p.get('Clicks', 0)
            impr = p.get('Impressions', 0)
            print(f"  {url} clicks={clicks:>4} impr={impr:>5}")
    else:
        print("  (no page data — check errors above)")
    print()

    print("  🕷️  CRAWL HEALTH (last 30 days)")
    print("  " + "-" * 60)
    if crawl and isinstance(crawl, list):
        latest = crawl[0] if crawl else {}
        print(f"  Crawled pages:        {latest.get('CrawledPages', 0)}")
        print(f"  In Bing index:        {latest.get('InIndex', 0)}")
        print(f"  Crawl errors:         {latest.get('CrawlErrors', 0)}")
        print(f"  Blocked by robots:    {latest.get('BlockedByRobotsTxt', 0)}")
    else:
        print("  (no crawl data — check errors above)")
    print()

    print("  📮 URL SUBMISSION QUOTA")
    print("  " + "-" * 60)
    if quota and '_error' not in quota:
        print(f"  Daily remaining:     {quota.get('DailyQuota', '?')}")
        print(f"  Monthly remaining:   {quota.get('MonthlyQuota', '?')}")
    else:
        print(f"  (error: {quota.get('_error', 'unknown')})")
    print()

    print("=" * 64)
    print(f"  Saved: {out_latest}")
    print(f"         {out_dated}")
    print("=" * 64)


if __name__ == '__main__':
    main()
