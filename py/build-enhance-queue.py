#!/usr/bin/env python3
"""
Enhance Queue Builder — multi-source target selector for the nightly enhance agent.

Reads ALL available data sources (Google GSC + Bing Webmaster + Autocomplete +
Trends) and outputs a SCRIPTED target queue. The Claude enhance agent then reads
this queue file as its single source of truth — no risk of missing a data source
because the prompt forgot to mention it.

Sources read (graceful on missing):
  1. data/rising-tools-latest.json        — Google GSC risers (7d vs prior 7d)
  2. /tmp/nightly-opportunities.txt        — GSC CTR wins + striking distance
  3. data/bing-data-latest.json           — Bing top queries
  4. /tmp/nightly-suggestions.txt          — Google Autocomplete (Phase 0)
  5. /tmp/nightly-trends.txt               — Google Trends (Phase 0)

Output:
  data/enhance-queue.json — top N targets, structured, with citations per pool

Usage:
  python3 build-enhance-queue.py             # default cap from prompt (7)
  python3 build-enhance-queue.py --cap 14    # nightly total (both fires)
  python3 build-enhance-queue.py --cooldown 7 # skip tools enhanced in N days
  python3 build-enhance-queue.py --dry-run    # don't write, just print
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _teamz_config import load_runtime  # noqa: E402


def safe_read_json(path):
    try:
        return json.loads(Path(path).read_text()) if Path(path).exists() else None
    except Exception as e:
        print(f"  warn: could not read {path}: {e}", file=sys.stderr)
        return None


def safe_read_text(path):
    try:
        return Path(path).read_text() if Path(path).exists() else ""
    except Exception:
        return ""


def url_to_slug(url, site_url):
    """Convert https://tool.teamzlab.com/finance/foo/ → /finance/foo/"""
    if not url:
        return None
    if url.startswith(site_url):
        rel = url[len(site_url) - 1:]  # keep leading slash
    elif url.startswith('http'):
        # different host — skip
        return None
    else:
        rel = url if url.startswith('/') else '/' + url
    if not rel.endswith('/'):
        # strip everything after last /
        rel = rel.rsplit('/', 1)[0] + '/'
    return rel


def slug_exists(slug, host_root):
    """Check if /hub/tool/index.html exists for this slug."""
    if not slug:
        return False
    path = host_root / slug.strip('/') / 'index.html'
    return path.exists()


def get_cooldown_slugs(host_root, days):
    """Return set of slugs touched in last N days (git log)."""
    try:
        result = subprocess.run(
            ['git', '-C', str(host_root), 'log',
             f'--since={days} days ago', '--name-only', '--pretty=format:'],
            capture_output=True, text=True, timeout=30
        )
        touched = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.endswith('/index.html'):
                slug = '/' + line.rsplit('/', 1)[0] + '/'
                touched.add(slug)
        return touched
    except Exception:
        return set()


# -----------------------------------------------------------------------------
# Pool readers — each returns list of candidate dicts
#   {slug, query, signal_score, mode, source, citation}
# -----------------------------------------------------------------------------

def pool_rising_tools(cfg, host_root):
    """Pool 1: Google GSC risers."""
    data = safe_read_json(host_root / 'data' / 'rising-tools-latest.json')
    if not data:
        return []
    site = cfg['site_url']
    candidates = []
    for item in data.get('top', []):
        page = item.get('page', '')
        slug = url_to_slug(page, site)
        if not slug or not slug_exists(slug, host_root):
            continue
        clicks = item.get('recent_clicks', 0)
        pos = item.get('recent_position', 0)
        if clicks < 3 or not (5 <= pos <= 30):
            continue
        # Score: position-improvement weighted, capped
        delta = item.get('position_delta') or item.get('position_improvement') or 0
        if isinstance(delta, str):
            try:
                delta = float(delta)
            except Exception:
                delta = 0
        score = (clicks * 2) + max(0, 30 - pos) + max(0, abs(delta))
        candidates.append({
            'slug': slug,
            'query': item.get('top_query', '') or '(no query — improve content)',
            'signal_score': round(score, 2),
            'mode': 'A',  # content enhance for risers
            'source': 'google-rising-7d',
            'citation': f"rank {pos:.1f}, {clicks} clicks, delta {delta} [data/rising-tools-latest.json]",
        })
    return candidates


def pool_gsc_opportunities(cfg, host_root):
    """Pool 2: GSC opportunities from /tmp/nightly-opportunities.txt."""
    txt = safe_read_text('/tmp/nightly-opportunities.txt')
    if not txt:
        # Try to generate now
        try:
            host_site_root = cfg['host_site_root']
            result = subprocess.run(
                [str(host_site_root / 'scripts' / 'build-search-console.sh'), '--opportunities'],
                capture_output=True, text=True, timeout=60, cwd=str(host_site_root)
            )
            txt = result.stdout
            Path('/tmp/nightly-opportunities.txt').write_text(txt)
        except Exception:
            return []

    candidates = []
    # Parse CTR QUICK WINS + STRIKING DISTANCE sections
    sections = re.split(r'(CTR QUICK WINS|STRIKING DISTANCE|HIGH IMPRESSIONS, ZERO CLICKS)', txt)
    current_mode = None
    for i, section in enumerate(sections):
        s_upper = section.strip().upper()
        if 'CTR QUICK WINS' in s_upper:
            current_mode = 'B'
            continue
        if 'STRIKING DISTANCE' in s_upper:
            current_mode = 'A'
            continue
        if 'HIGH IMPRESSIONS' in s_upper:
            current_mode = 'B'
            continue
        if current_mode is None:
            continue
        # Parse rows: "query  /path/  pos  impr"
        for line in section.splitlines():
            line = line.rstrip()
            if not line or line.startswith(('-', '=', '#')):
                continue
            # Match: query (text) /slug/ pos impr
            m = re.search(r'(/\S+/)\s+(\d+\.?\d*)\s+(\d+)', line)
            if not m:
                continue
            slug = m.group(1)
            pos = float(m.group(2))
            impr = int(m.group(3))
            if not slug_exists(slug, host_root):
                continue
            query = line[:line.find(slug)].strip()[:80]
            score = impr / 10 + max(0, 20 - pos) * 2
            candidates.append({
                'slug': slug,
                'query': query,
                'signal_score': round(score, 2),
                'mode': current_mode,
                'source': 'gsc-opportunities-' + ('ctr-wins' if current_mode == 'B' else 'striking-distance'),
                'citation': f"GSC pos {pos:.1f}, {impr} impr [GSC opportunities]",
            })
    return candidates


def pool_bing(cfg, host_root):
    """Pool 3: Bing Webmaster queries."""
    data = safe_read_json(host_root / 'data' / 'bing-data-latest.json')
    if not data:
        return []
    site = cfg['site_url']
    candidates = []
    for q in data.get('queries', []):
        clicks = q.get('Clicks', 0)
        pos = q.get('AvgImpressionPosition', 0)
        if clicks < 3 or not (5 <= pos <= 30):
            continue
        query_text = q.get('Query', '')
        # Bing sometimes puts URL in Query field
        slug = None
        if query_text.startswith('http'):
            slug = url_to_slug(query_text, site)
        # Otherwise we can't reliably map query → slug without GSC join
        # So include only URL-typed entries for now
        if not slug or not slug_exists(slug, host_root):
            continue
        score = clicks * 3 + max(0, 30 - pos)
        candidates.append({
            'slug': slug,
            'query': '(Bing query as URL)',
            'signal_score': round(score, 2),
            'mode': 'A',
            'source': 'bing-webmaster',
            'citation': f"Bing pos {pos:.1f}, {clicks} clicks [data/bing-data-latest.json]",
        })
    # Also use pages section if available
    for p in data.get('pages', []):
        url = p.get('Page') or p.get('Query', '')
        slug = url_to_slug(url, site)
        if not slug or not slug_exists(slug, host_root):
            continue
        clicks = p.get('Clicks', 0)
        impr = p.get('Impressions', 0)
        if clicks < 2 or impr < 5:
            continue
        score = clicks * 3 + impr / 10
        candidates.append({
            'slug': slug,
            'query': '(Bing top page — improve content)',
            'signal_score': round(score, 2),
            'mode': 'A',
            'source': 'bing-pages',
            'citation': f"Bing {clicks} clicks, {impr} impr [data/bing-data-latest.json]",
        })
    return candidates


def pool_autocomplete_trends(cfg, host_root):
    """Pool 4: Google Autocomplete + Trends from Phase 0 /tmp files.
    These provide *new keyword ideas* — used to enrich enhance content
    rather than pick targets. Returned as metadata, not target candidates.
    """
    suggestions = safe_read_text('/tmp/nightly-suggestions.txt')
    trends = safe_read_text('/tmp/nightly-trends.txt')
    # Extract first 20 suggestions, first 10 trending
    sug_list = [s.strip() for s in suggestions.splitlines() if s.strip()][:20]
    trend_list = [s.strip() for s in trends.splitlines() if s.strip()][:10]
    return {'suggestions': sug_list, 'trends': trend_list}


# -----------------------------------------------------------------------------
# Main: assemble + dedupe + cap
# -----------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cap', type=int, default=7, help='Max targets per run (default 7)')
    p.add_argument('--cooldown', type=int, default=7, help='Skip tools enhanced in N days (default 7)')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    cfg = load_runtime(__file__)
    host_root = cfg['host_site_root']

    print(f"[enhance-queue] cap={args.cap}, cooldown={args.cooldown}d")
    print(f"[enhance-queue] host={host_root}")
    print(f"[enhance-queue] site={cfg['site_url']}")

    # Cooldown set
    cooldown_set = get_cooldown_slugs(host_root, args.cooldown)
    print(f"[enhance-queue] cooldown excludes {len(cooldown_set)} slugs touched in last {args.cooldown}d")

    # Pull from all pools
    p1 = pool_rising_tools(cfg, host_root)
    p2 = pool_gsc_opportunities(cfg, host_root)
    p3 = pool_bing(cfg, host_root)
    p4 = pool_autocomplete_trends(cfg, host_root)

    print(f"[enhance-queue] pool1 google-rising:     {len(p1)} candidates")
    print(f"[enhance-queue] pool2 gsc-opportunities: {len(p2)} candidates")
    print(f"[enhance-queue] pool3 bing:              {len(p3)} candidates")
    print(f"[enhance-queue] pool4 keyword-enrichment: {len(p4.get('suggestions', []))} sug + {len(p4.get('trends', []))} trends (enrichment, not targets)")

    # Merge + dedupe by slug, keep highest score
    by_slug = {}
    for cand in p1 + p2 + p3:
        if cand['slug'] in cooldown_set:
            continue
        existing = by_slug.get(cand['slug'])
        if not existing or cand['signal_score'] > existing['signal_score']:
            by_slug[cand['slug']] = cand

    # Sort by signal_score desc
    ranked = sorted(by_slug.values(), key=lambda x: x['signal_score'], reverse=True)

    # Cap, but try to keep variety: aim for 4 Mode A + 2 Mode B + 1 Bing
    final = []
    mode_a_quota = max(1, args.cap // 2)
    mode_b_quota = max(1, args.cap // 4)
    bing_quota = max(1, args.cap // 7)
    counts = {'A_google': 0, 'B_google': 0, 'bing': 0, 'other': 0}
    for c in ranked:
        if len(final) >= args.cap:
            break
        is_bing = 'bing' in c['source']
        is_a = c['mode'] == 'A'
        is_b = c['mode'] == 'B'
        if is_bing and counts['bing'] < bing_quota:
            final.append(c)
            counts['bing'] += 1
        elif is_a and not is_bing and counts['A_google'] < mode_a_quota:
            final.append(c)
            counts['A_google'] += 1
        elif is_b and counts['B_google'] < mode_b_quota:
            final.append(c)
            counts['B_google'] += 1
        else:
            # Fill remainder with whatever scores best
            final.append(c)
            counts['other'] += 1

    queue = {
        'generated_at': datetime.now().isoformat(),
        'cap': args.cap,
        'cooldown_days': args.cooldown,
        'cooldown_excluded': len(cooldown_set),
        'pool_counts': {
            'google_rising': len(p1),
            'gsc_opportunities': len(p2),
            'bing': len(p3),
        },
        'mode_mix': counts,
        'targets': final,
        'enrichment': p4,
    }

    out_path = host_root / 'data' / 'enhance-queue.json'
    if args.dry_run:
        print(json.dumps(queue, indent=2)[:2000])
        print('... (dry-run, not written)')
    else:
        out_path.write_text(json.dumps(queue, indent=2))
        print(f"[enhance-queue] wrote {len(final)} targets → {out_path}")

    # Print summary table
    print()
    print(f"  {'#':<3} {'slug':<48} {'mode':<6} {'source':<26} score")
    print("  " + "-" * 95)
    for i, c in enumerate(final, 1):
        print(f"  {i:<3} {c['slug'][:48]:<48} {c['mode']:<6} {c['source'][:26]:<26} {c['signal_score']}")
    print()


if __name__ == '__main__':
    main()
