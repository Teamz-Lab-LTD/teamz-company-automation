#!/usr/bin/env python3
"""
Enhance Queue Builder — thin orchestrator over existing Teamz SEO scripts.

Pre-builds data/enhance-queue.json by CALLING existing data scripts and
merging their outputs. Does NOT re-implement what those scripts already do.

Composes these existing scripts:
  pool1  build-rising-tools.py --json              → Google GSC risers
  pool2  build-keyword-intel.py --opportunities    → GSC CTR-wins + striking distance
  pool3  data/bing-data-latest.json (read direct)  → Bing queries + pages
  pool4  build-content-ideas.py --gaps             → content gaps (no tool yet)
  pool5  build-content-ideas.py --seasonal         → seasonal opportunity calendar
  enrich build-keyword-volume.py per hub           → Trends + Autocomplete composite

Output: data/enhance-queue.json
  - targets[]: top N tools with mode (A/B), citation, signal_score, source
  - enrichment{}: keyword ideas + seasonal context for Mode A H2 generation

Usage:
  python3 build-enhance-queue.py                    # default cap 7, cooldown 7d
  python3 build-enhance-queue.py --cap 14
  python3 build-enhance-queue.py --cooldown 7
  python3 build-enhance-queue.py --dry-run

Per teamz-company-automation/CLAUDE.md Rule 1: never fabricate metrics —
always run existing scripts. This queue enforces that.
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


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def run_script(host_root, args, timeout=120, stdin=None):
    """Run an existing scripts/* and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            args, cwd=str(host_root), capture_output=True, text=True,
            timeout=timeout, input=stdin,
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), -1


def safe_read_json(path):
    try:
        return json.loads(Path(path).read_text()) if Path(path).exists() else None
    except Exception:
        return None


def url_to_slug(url, site_url):
    if not url:
        return None
    if url.startswith(site_url):
        rel = url[len(site_url) - 1:]
    elif url.startswith('http'):
        return None
    else:
        rel = url if url.startswith('/') else '/' + url
    if not rel.endswith('/'):
        rel = rel.rsplit('/', 1)[0] + '/'
    return rel


def slug_exists(slug, host_root):
    if not slug:
        return False
    return (host_root / slug.strip('/') / 'index.html').exists()


def get_cooldown_slugs(host_root, days):
    out, _, _ = run_script(host_root, ['git', 'log', f'--since={days} days ago',
                                       '--name-only', '--pretty=format:'])
    touched = set()
    for line in out.splitlines():
        line = line.strip()
        if line.endswith('/index.html'):
            touched.add('/' + line.rsplit('/', 1)[0] + '/')
    return touched


# -----------------------------------------------------------------------------
# Pool 1: Google rising tools — calls build-rising-tools.py --json
# -----------------------------------------------------------------------------

def pool_rising(host_root, cfg):
    """Calls scripts/build-rising-tools.py --json → parses risers."""
    out, _, rc = run_script(
        host_root,
        ['python3', str(host_root / 'scripts' / 'build-rising-tools.py'), '--json'],
        timeout=90,
    )
    if rc != 0 or not out:
        return [], "build-rising-tools.py --json failed or empty"
    try:
        data = json.loads(out)
    except Exception:
        return [], "build-rising-tools.py JSON parse error"
    cands = []
    for item in data.get('top', []):
        slug = item.get('slug', '')
        if slug and not slug.endswith('/'):
            slug += '/'
        if not slug_exists(slug, host_root):
            continue
        clicks = item.get('recent_clicks', 0)
        pos = item.get('recent_position', 0)
        score = item.get('score', clicks * 2)
        if clicks < 3 or not (5 <= pos <= 30):
            continue
        cands.append({
            'slug': slug,
            'query': item.get('top_query', '') or '(rising tool — content enhance)',
            'signal_score': score,
            'mode': 'A',
            'source': 'build-rising-tools',
            'citation': f"rising rank {pos:.1f}, {clicks} clicks, score {score} [build-rising-tools.py --json]",
        })
    return cands, None


# -----------------------------------------------------------------------------
# Pool 2: GSC CTR opportunities — calls build-keyword-intel.py --opportunities
# -----------------------------------------------------------------------------

def pool_opportunities(host_root, cfg):
    """Calls scripts/build-keyword-intel.py --opportunities --export json."""
    tmp_out = Path('/tmp/enhance-queue-opps.json')
    out, err, rc = run_script(
        host_root,
        ['python3', str(host_root / 'scripts' / 'build-keyword-intel.py'),
         '--opportunities', '--export', 'json', '--output', str(tmp_out)],
        timeout=120,
    )
    data = safe_read_json(tmp_out)
    if not data:
        return [], f"build-keyword-intel.py --opportunities returned no JSON ({err[:100] if err else 'no error'})"
    cands = []
    items = data if isinstance(data, list) else data.get('opportunities', data.get('keywords', []))
    if not isinstance(items, list):
        return [], "unexpected JSON structure from build-keyword-intel.py"
    for item in items:
        if not isinstance(item, dict):
            continue
        page = item.get('page') or item.get('url') or item.get('Page', '')
        slug = url_to_slug(page, cfg['site_url']) if page else None
        if not slug or not slug_exists(slug, host_root):
            continue
        query = item.get('query') or item.get('keyword') or item.get('Query', '')
        clicks = item.get('clicks', item.get('Clicks', 0))
        impr = item.get('impressions', item.get('Impressions', 0))
        pos = item.get('position', item.get('Position', 0)) or 0
        # Mode B = CTR fix (low click rate), Mode A = striking distance
        mode = 'B' if clicks <= 1 and impr > 10 else 'A'
        score = impr / 5 + max(0, 25 - pos) * 2 - clicks * 0.5
        cands.append({
            'slug': slug,
            'query': query[:80] if query else '(opportunity)',
            'signal_score': round(score, 2),
            'mode': mode,
            'source': 'build-keyword-intel-opportunities',
            'citation': f"GSC pos {pos:.1f}, {clicks} clicks / {impr} impr [build-keyword-intel.py --opportunities]",
        })
    return cands, None


# -----------------------------------------------------------------------------
# Pool 3: Bing — read data/bing-data-latest.json directly (new infra)
# -----------------------------------------------------------------------------

def pool_bing(host_root, cfg):
    data = safe_read_json(host_root / 'data' / 'bing-data-latest.json')
    if not data:
        return [], "data/bing-data-latest.json missing (run build-bing-data.py)"
    site = cfg['site_url']
    cands = []
    # Queries section (some entries have URL in Query field)
    for q in data.get('queries', []):
        url_in_query = q.get('Query', '')
        if not url_in_query.startswith('http'):
            continue
        slug = url_to_slug(url_in_query, site)
        if not slug_exists(slug, host_root):
            continue
        clicks = q.get('Clicks', 0)
        pos = q.get('AvgImpressionPosition', 0)
        if clicks < 3 or not (5 <= pos <= 30):
            continue
        cands.append({
            'slug': slug,
            'query': '(Bing top query — Mode A enhance)',
            'signal_score': clicks * 3 + max(0, 30 - pos),
            'mode': 'A',
            'source': 'bing-queries',
            'citation': f"Bing pos {pos:.1f}, {clicks} clicks [data/bing-data-latest.json]",
        })
    # Pages section
    for p in data.get('pages', []):
        url = p.get('Page') or p.get('Query', '')
        slug = url_to_slug(url, site)
        if not slug or not slug_exists(slug, host_root):
            continue
        clicks = p.get('Clicks', 0)
        impr = p.get('Impressions', 0)
        if clicks < 2 or impr < 5:
            continue
        cands.append({
            'slug': slug,
            'query': '(Bing top page — Mode A enhance)',
            'signal_score': clicks * 3 + impr / 10,
            'mode': 'A',
            'source': 'bing-pages',
            'citation': f"Bing {clicks} clicks, {impr} impr [data/bing-data-latest.json]",
        })
    return cands, None


# -----------------------------------------------------------------------------
# Pool 4: Content gaps — calls build-content-ideas.py --gaps
# Currently text-only output; parse loosely. Gaps = keyword ideas with NO existing
# tool. Used for enrichment (suggest what NEW H2/FAQ to add to existing tools).
# -----------------------------------------------------------------------------

def pool_gaps_seasonal(host_root):
    gaps_out, _, _ = run_script(
        host_root,
        ['python3', str(host_root / 'scripts' / 'build-content-ideas.py'), '--gaps'],
        timeout=90,
    )
    seasonal_out, _, _ = run_script(
        host_root,
        ['python3', str(host_root / 'scripts' / 'build-content-ideas.py'), '--seasonal'],
        timeout=60,
    )

    def extract_lines(s, n=20):
        return [l.strip() for l in s.splitlines() if l.strip() and not l.startswith(('=', '#', '-'))][:n]

    return {
        'gaps': extract_lines(gaps_out, 20),
        'seasonal': extract_lines(seasonal_out, 10),
    }


# -----------------------------------------------------------------------------
# Pool 6: GSC anomalies — read data/gsc-anomalies-latest.json directly
# Picks up CTR-drop pages (recent CTR < 65% of prior CTR with >=8 recent impr)
# that Pool 2's --opportunities filter misses because the page already ranks
# but lost clicks week-over-week. Mode B (title/meta rewrite) is the right
# tool: same content, fresher framing to recover lost CTR.
# -----------------------------------------------------------------------------

def pool_gsc_anomalies(host_root, cfg):
    """Reads gsc-anomalies-latest.json and emits Mode B candidates for CTR-drop
    alerts. Impression-drop entries are skipped (root cause is usually SERP
    volatility, not on-page)."""
    candidates_paths = [
        host_root / 'teamz-company-automation' / 'data' / 'gsc-anomalies-latest.json',
        host_root / 'data' / 'gsc-anomalies-latest.json',
    ]
    data = None
    for path in candidates_paths:
        data = safe_read_json(path)
        if data:
            break
    if not data:
        return [], "gsc-anomalies-latest.json missing (run build-gsc-anomalies.py)"
    site = cfg['site_url']
    cands = []
    for alert in data.get('alerts', {}).get('ctr_drop', []):
        page = alert.get('page', '')
        slug = url_to_slug(page, site)
        if not slug or not slug_exists(slug, host_root):
            continue
        query = alert.get('query', '')
        prior_ctr = alert.get('prior_ctr', 0)
        recent_ctr = alert.get('recent_ctr', 0)
        recent_impr = alert.get('recent_impressions', 0)
        ctr_loss = max(0, prior_ctr - recent_ctr)
        # Weight: CTR drop on an already-ranking page is higher priority than
        # a generic striking-distance opportunity — the user is BLEEDING clicks
        # week-over-week. /3 (vs /10) and +15 baseline puts these in contention
        # with Pool 2 opportunities. Cap at 80 so a single huge alert can't
        # monopolize the queue.
        score = min(80, recent_impr * ctr_loss / 3 + 15)
        cands.append({
            'slug': slug,
            'query': query[:80] if query else '(CTR drop — title/meta refresh)',
            'signal_score': round(score, 2),
            'mode': 'B',
            'source': 'gsc-anomalies-ctr-drop',
            'citation': (
                f"CTR {prior_ctr:.1f}% -> {recent_ctr:.1f}% on {recent_impr} impr "
                f"[build-gsc-anomalies.py]"
            ),
        })
    return cands, None


# -----------------------------------------------------------------------------
# Pool 7: Canonical mismatches — read data/canonical-mismatches-latest.json
# Pages where Google chose a different canonical than the page declared
# ('Alternate page with proper canonical tag' or worse — duplicate signals
# cannibalizing rankings). Mode C = canonical fix; Phase 4 Claude reviews each
# (NOT auto-rewritten because wrong canonical change can de-index a page).
# -----------------------------------------------------------------------------

def pool_canonical_mismatches(host_root, cfg):
    """Reads canonical-mismatches-latest.json from build-request-indexing.py
    output. Emits Mode C (canonical fix) candidates for the Claude agent to
    review in Phase 4. Conservative — only flagged pages, no auto-rewrite."""
    candidate_paths = [
        host_root / 'teamz-company-automation' / 'data' / 'canonical-mismatches-latest.json',
        host_root / 'data' / 'canonical-mismatches-latest.json',
    ]
    data = None
    for path in candidate_paths:
        data = safe_read_json(path)
        if data:
            break
    if not data:
        return [], "canonical-mismatches-latest.json missing (run build-request-indexing.py)"
    site = cfg['site_url']
    cands = []
    for entry in data.get('mismatches', []):
        url = entry.get('url', '')
        slug = url_to_slug(url, site)
        if not slug or not slug_exists(slug, host_root):
            continue
        user_canon = entry.get('user_canonical', '')
        google_canon = entry.get('google_canonical', '')
        coverage = entry.get('coverage', '')
        # Higher score for "Duplicate" issues — actively cannibalizing
        # vs "Alternate page" which is a softer mismatch.
        is_duplicate = 'duplicate' in coverage.lower()
        score = 55 if is_duplicate else 35
        cands.append({
            'slug': slug,
            'query': f"canonical: yours={user_canon[:40]} vs google={google_canon[:40]}",
            'signal_score': score,
            'mode': 'C',
            'source': 'canonical-mismatch',
            'citation': f"GSC '{coverage}' (declared {user_canon} → Google picked {google_canon}) [build-request-indexing.py]",
        })
    return cands, None


# -----------------------------------------------------------------------------
# Pool 5 (enrichment): Google Autocomplete + Trends via build-keyword-volume
# Not pulling here per-hub because it's slow (3-5 sec per kw). Instead read
# the cached /tmp/nightly-suggestions.txt + /tmp/nightly-trends.txt written
# by Phase 0 of the nightly cron — that's where existing Autocomplete + Trends
# data is already saved. (Falls back to empty if Phase 0 hasn't run.)
# -----------------------------------------------------------------------------

def pool_autocomplete_trends():
    sug = []
    trd = []
    try:
        if Path('/tmp/nightly-suggestions.txt').exists():
            sug = [l.strip() for l in Path('/tmp/nightly-suggestions.txt').read_text().splitlines()
                   if l.strip()][:30]
    except Exception:
        pass
    try:
        if Path('/tmp/nightly-trends.txt').exists():
            trd = [l.strip() for l in Path('/tmp/nightly-trends.txt').read_text().splitlines()
                   if l.strip()][:15]
    except Exception:
        pass
    return {'suggestions': sug, 'trends': trd}


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Pool 8 (cold-start): hidden pages — zero GSC impressions but crawlable + about
# a real keyword. Give each ONE keyword-aligned enhance + index push so it earns
# its first impressions; after that the normal pools (1-3,6,7) take over.
#
# OPT-IN + ISOLATED: runs ONLY for a host that has data/.cold-start-enabled.
# Every other repo lacks that marker -> returns [] -> zero behaviour change.
# Lowest signal_score + a hard cold-quota -> can only ever use LEFTOVER capacity,
# never displacing a proven target. Each page is cold-started at most once
# (tracked in data/cold-start-done.txt). Inputs are the read-only audit CSVs.
# -----------------------------------------------------------------------------
def pool_cold_start(host_root, cfg):
    marker = host_root / 'data' / '.cold-start-enabled'
    if not marker.exists():
        return [], None  # opt-in only — other repos unaffected

    import csv as _csv
    audit = host_root / 'data' / 'zero-visitor-audit'
    done_file = host_root / 'data' / 'cold-start-done.txt'
    done = set()
    if done_file.exists():
        done = {l.strip() for l in done_file.read_text().splitlines() if l.strip()}

    # candidates the zero-visitor audit already identified as hidden-but-wanted:
    #   index-status-prune.csv rows verdict=NOT_CRAWLED  (Google never fetched it)
    #   rescue.csv                                        (0 impr but has demand)
    sources = [(audit / 'index-status-prune.csv', 'NOT_CRAWLED'),
               (audit / 'rescue.csv', None)]
    seen, cands = set(), []
    for path, verdict_filter in sources:
        if not path.exists():
            continue
        try:
            rows = list(_csv.DictReader(path.open()))
        except Exception:
            continue
        for row in rows:
            if verdict_filter and row.get('verdict') != verdict_filter:
                continue
            key = (row.get('key') or row.get('path') or '').strip()
            if not key:
                continue
            slug = '/' + key.strip('/').removesuffix('/index.html') + '/'
            if slug in done or slug in seen or not slug_exists(slug, host_root):
                continue
            seen.add(slug)
            kw = slug.strip('/').split('/')[-1].replace('-', ' ')
            cands.append({
                'slug': slug,
                'query': kw,
                'signal_score': 0.5,        # lowest — never outranks a proven pool
                'mode': 'A',                # content align to earn first impressions
                'source': 'cold-start',
                'citation': f"hidden page (0 GSC impressions) — cold-start rescue, "
                            f"target '{kw}'",
            })
    return cands, None


# -----------------------------------------------------------------------------
# Pool 9 (dead-revival): indexed-but-no-demand pages re-targeted to a keyword that
# DOES have demand (from build-dead-revival.py). Turns dead weight into live pages.
#
# OPT-IN + ISOLATED: runs ONLY for a host with data/.dead-revival-enabled.
# Lowest signal_score (0.4, below cold-start's 0.5) + hard quota -> can only ever
# use LEFTOVER capacity, never displaces a proven target. Mode A = align content
# toward the NEW demand keyword. Phase 4 Claude reviews each before applying.
# -----------------------------------------------------------------------------
def pool_dead_revival(host_root, cfg):
    marker = host_root / 'data' / '.dead-revival-enabled'
    if not marker.exists():
        return [], None  # opt-in only — other repos unaffected
    targets_file = host_root / 'data' / 'dead-revival-targets.json'
    if not targets_file.exists():
        return [], None
    try:
        data = json.loads(targets_file.read_text())
    except Exception as e:
        return [], str(e)
    cands = []
    for t in data.get('targets', []):
        slug = '/' + t.get('slug', '').strip('/') + '/'
        if slug == '//' or not slug_exists(slug, host_root):
            continue
        new_kw = t.get('new_target', '')
        old_kw = t.get('old_target', '')
        if not new_kw:
            continue
        cands.append({
            'slug': slug,
            'query': new_kw,
            'signal_score': 0.4,        # absolute lowest — below cold-start (0.5)
            'mode': 'A',                # content-align toward the new demand keyword
            'source': 'dead-revival',
            'citation': f"DEAD-REVIVAL: re-target '{old_kw}' (no demand) -> "
                        f"'{new_kw}' ({t.get('tier','')} {t.get('score','')}) "
                        f"[build-dead-revival.py]",
        })
    return cands, None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cap', type=int, default=7)
    p.add_argument('--cooldown', type=int, default=7)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    cfg = load_runtime(__file__)
    host_root = cfg['host_site_root']

    print(f"[enhance-queue] cap={args.cap}, cooldown={args.cooldown}d, host={host_root}")
    print(f"[enhance-queue] Calling existing Teamz scripts (Rule 1: no fabricated data)")

    cooldown_set = get_cooldown_slugs(host_root, args.cooldown)
    print(f"[enhance-queue] cooldown excludes {len(cooldown_set)} slugs from last {args.cooldown}d")

    errors = {}
    p1, e1 = pool_rising(host_root, cfg)
    if e1: errors['rising'] = e1
    p2, e2 = pool_opportunities(host_root, cfg)
    if e2: errors['opportunities'] = e2
    p3, e3 = pool_bing(host_root, cfg)
    if e3: errors['bing'] = e3
    p6, e6 = pool_gsc_anomalies(host_root, cfg)
    if e6: errors['gsc_anomalies'] = e6
    p7, e7 = pool_canonical_mismatches(host_root, cfg)
    if e7: errors['canonical_mismatches'] = e7
    p8c, e8 = pool_cold_start(host_root, cfg)
    if e8: errors['cold_start'] = e8
    p8r, e9 = pool_dead_revival(host_root, cfg)
    if e9: errors['dead_revival'] = e9
    p4 = pool_gaps_seasonal(host_root)
    p5 = pool_autocomplete_trends()

    print(f"[enhance-queue] pool1 rising-tools:      {len(p1)}")
    print(f"[enhance-queue] pool2 gsc-opportunities: {len(p2)}")
    print(f"[enhance-queue] pool3 bing:              {len(p3)}")
    print(f"[enhance-queue] pool6 gsc-ctr-drops:     {len(p6)}")
    print(f"[enhance-queue] pool7 canonical-fix:     {len(p7)}")
    print(f"[enhance-queue] pool8 cold-start:        {len(p8c)}")
    print(f"[enhance-queue] pool9 dead-revival:      {len(p8r)}")
    print(f"[enhance-queue] pool4 gaps:              {len(p4['gaps'])}")
    print(f"[enhance-queue] pool4 seasonal:          {len(p4['seasonal'])}")
    print(f"[enhance-queue] pool5 autocomplete:      {len(p5['suggestions'])}")
    print(f"[enhance-queue] pool5 trends:            {len(p5['trends'])}")
    if errors:
        for k, v in errors.items():
            print(f"[enhance-queue]   ! {k}: {v}")

    # Merge target pools (1-3, 6, 7, 8-cold-start), dedupe by slug, apply cooldown
    by_slug = {}
    for c in p1 + p2 + p3 + p6 + p7 + p8c + p8r:
        if c['slug'] in cooldown_set:
            continue
        if c['slug'] not in by_slug or c['signal_score'] > by_slug[c['slug']]['signal_score']:
            by_slug[c['slug']] = c

    # Revenue weighting: bias the queue toward higher-RPM niches so enhancement effort goes
    # to pages that EARN, not just rank. Reuses revenue_priority (no new RPM math). Multiplies
    # the SORT KEY only — signal_score itself is untouched, so the source-quota logic below is
    # unaffected. Degrades to weight 1.0 if the module/data is unavailable.
    try:
        import revenue_priority as _rp
        for c in by_slug.values():
            hub = c['slug'].strip('/').split('/')[0]
            ed = _rp.expected_dollars(c['slug'], hub, c.get('title', ''),
                                      visitors_mo=1000, serp_winnability=6)
            c['rpm_mid'] = ed['rpm_mid']
            c['niche'] = ed['niche']
            c['rev_weight'] = round(max(0.5, min(3.0, ed['rpm_mid'] / 10.0)), 2)  # $10 RPM = 1.0x
    except Exception as e:
        print(f"[enhance-queue] revenue weighting skipped ({type(e).__name__}) — raw signal sort")
        for c in by_slug.values():
            c['rev_weight'] = 1.0

    ranked = sorted(by_slug.values(),
                    key=lambda x: x['signal_score'] * x.get('rev_weight', 1.0), reverse=True)

    # Cap with mode mix: target 4 Mode A google + 2 Mode B google + 1 bing
    final = []
    a_quota = max(1, args.cap // 2)
    b_quota = max(1, args.cap // 4)
    bing_quota = max(1, args.cap // 7)
    cold_quota = max(1, args.cap // 7)   # cold-start hard cap (<=1 at cap 7)
    revival_quota = max(1, args.cap // 7)  # dead-revival hard cap (<=1 at cap 7)
    counts = {'A_google': 0, 'B_google': 0, 'bing': 0, 'other': 0, 'cold': 0, 'revival': 0}
    for c in ranked:
        if len(final) >= args.cap:
            break
        if c['source'] == 'cold-start':          # lowest priority + hard quota:
            if counts['cold'] >= cold_quota:      # only ever uses leftover capacity,
                continue                          # never displaces a proven target
            final.append(c); counts['cold'] += 1
            continue
        if c['source'] == 'dead-revival':        # even lower priority + hard quota
            if counts['revival'] >= revival_quota:
                continue
            final.append(c); counts['revival'] += 1
            continue
        is_bing = 'bing' in c['source']
        is_a = c['mode'] == 'A'
        is_b = c['mode'] == 'B'
        if is_bing and counts['bing'] < bing_quota:
            final.append(c); counts['bing'] += 1
        elif is_a and not is_bing and counts['A_google'] < a_quota:
            final.append(c); counts['A_google'] += 1
        elif is_b and counts['B_google'] < b_quota:
            final.append(c); counts['B_google'] += 1
        else:
            final.append(c); counts['other'] += 1

    queue = {
        'generated_at': datetime.now().isoformat(),
        'cap': args.cap,
        'cooldown_days': args.cooldown,
        'cooldown_excluded': len(cooldown_set),
        'sources_called': [
            'scripts/build-rising-tools.py --json',
            'scripts/build-keyword-intel.py --opportunities --export json',
            'data/bing-data-latest.json',
            'data/gsc-anomalies-latest.json (CTR-drop alerts)',
            'data/canonical-mismatches-latest.json (Pool 7 canonical fix)',
            'scripts/build-content-ideas.py --gaps',
            'scripts/build-content-ideas.py --seasonal',
            '/tmp/nightly-{suggestions,trends}.txt (Phase 0 cron outputs)',
        ],
        'pool_counts': {
            'rising': len(p1),
            'opportunities': len(p2),
            'bing': len(p3),
            'gsc_ctr_drops': len(p6),
            'canonical_mismatches': len(p7),
            'cold_start': len(p8c),
            'gaps': len(p4['gaps']),
            'seasonal': len(p4['seasonal']),
            'autocomplete': len(p5['suggestions']),
            'trends': len(p5['trends']),
        },
        'mode_mix': counts,
        'errors': errors,
        'targets': final,
        'enrichment': {
            'autocomplete': p5['suggestions'],
            'trends': p5['trends'],
            'gaps': p4['gaps'],
            'seasonal': p4['seasonal'],
        },
    }

    out_path = host_root / 'data' / 'enhance-queue.json'
    if args.dry_run:
        print(json.dumps(queue, indent=2)[:3000])
        print('... (dry-run, not written)')
    else:
        out_path.write_text(json.dumps(queue, indent=2))
        print(f"[enhance-queue] wrote {len(final)} targets → {out_path}")
        # cold-start is one-shot per page: record the ones queued tonight
        picked_cold = [c['slug'] for c in final if c['source'] == 'cold-start']
        if picked_cold:
            done_file = host_root / 'data' / 'cold-start-done.txt'
            with done_file.open('a') as f:
                for s in picked_cold:
                    f.write(s + '\n')
            print(f"[enhance-queue] cold-start: marked {len(picked_cold)} done "
                  f"(one-shot) → {done_file.name}")

    print()
    print(f"  {'#':<3} {'slug':<48} {'mode':<6} {'source':<32} score")
    print("  " + "-" * 100)
    for i, c in enumerate(final, 1):
        print(f"  {i:<3} {c['slug'][:48]:<48} {c['mode']:<6} {c['source'][:32]:<32} {c['signal_score']}")
    print()


if __name__ == '__main__':
    main()
