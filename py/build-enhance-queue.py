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
# AI-channel guard (ported from build-content-queue.py, which goalkit/apps/learn
# already use — this file, vendored into tool.teamzlab.com, had none of it, even
# though tools carries the MOST AI traffic of the four properties). It exists
# because a goalkit page with 81 AI sessions and 0 Google clicks nearly had its
# title rewritten by a clicks-only rule that called it "nothing to lose": ChatGPT
# was sending it more traffic than Google sent the property's entire top ten.
#
# Return contract deliberately differs from the source function: that one returns
# {} for BOTH "the fetch failed" and "the fetch succeeded, zero pages had AI
# traffic" — the exact ambiguity a monitor must never have. Here None means
# "could not check", {} means "checked, zero found".
#
# NOTE: this file is symlinked into BOTH teamzlab-tools/scripts/ and
# teamz-lab-generic-landing-pages/scripts/, but apps' own nightly instructions
# never call it — apps' real pipeline is build-content-queue.py via
# nightly-site.sh. Confirmed 2026-08-03 (no reference to build-enhance-queue in
# that repo outside this vendored symlink). This guard is therefore live for
# tools only; if apps' nightly is ever wired to call this file, the guard
# already covers it for free.
# -----------------------------------------------------------------------------
AI_SOURCES = ("chatgpt", "openai", "perplexity", "claude", "copilot", "gemini",
              "you.com", "phind", "poe.com", "deepseek", "grok", "mistral")


def ga4_ai_sessions(cfg, days=28):
    """{landing_path: ai_sessions} over the trailing `days`, or None if the GA4
    call could not be made. Callers MUST treat None as unknown and fail closed —
    never as zero AI traffic."""
    import urllib.parse as _p
    import urllib.request as _u
    tok_path = Path(cfg["ga4_token_file"])
    pid = cfg.get("ga4_property_id")
    if not tok_path.exists() or not pid:
        return None
    try:
        t = json.loads(tok_path.read_text())
        data = _p.urlencode({
            "client_id": t["client_id"], "client_secret": t["client_secret"],
            "refresh_token": t["refresh_token"], "grant_type": "refresh_token",
        }).encode()
        token = json.load(_u.urlopen(_u.Request(
            t.get("token_uri", "https://oauth2.googleapis.com/token"), data=data),
            timeout=30))["access_token"]

        body = json.dumps({
            "dateRanges": [{"startDate": f"{days}daysAgo", "endDate": "today"}],
            "dimensions": [{"name": "landingPagePlusQueryString"}, {"name": "sessionSource"}],
            "metrics": [{"name": "sessions"}],
            "limit": 500,
        }).encode()
        req = _u.Request(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport",
            data=body, method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        rows = json.load(_u.urlopen(req, timeout=90)).get("rows", [])
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️  AI-channel signal UNAVAILABLE ({type(e).__name__}). Failing CLOSED: "
              f"every Mode B candidate downgrades to Mode A tonight.")
        return None

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


# Below this floor, downgrading Mode B is not worth the lost upside — a page with
# 1-2 AI sessions/28d earning nothing from Google genuinely has nothing to lose.
AI_MODE_B_GUARD_FLOOR = 5


def apply_ai_guard(cands, ai_by_path, ai_known):
    """Downgrade Mode B -> Mode A wherever the AI signal says this page is not
    actually dead. Runs AFTER every pool so it covers pool_opportunities and
    pool_gsc_anomalies — the two Mode-B-capable pools — without each pool having
    to remember to call it."""
    if not ai_known:
        # GA4 unreachable: cannot rule out AI traffic on ANY page tonight.
        # Fail closed across the board rather than per-candidate.
        for c in cands:
            if c.get('mode') == 'B':
                c['mode'] = 'A'
                c['ai_sessions'] = 0
                c['ai_guard'] = 'GA4 unreachable — failed closed to additive'
        return cands
    for c in cands:
        ai_hits = ai_by_path.get(c['slug'], 0)
        c['ai_sessions'] = ai_hits
        if c.get('mode') == 'B' and ai_hits >= AI_MODE_B_GUARD_FLOOR:
            c['mode'] = 'A'
            c['ai_guard'] = f"downgraded — {ai_hits} AI sessions/28d, title is earning traffic Google doesn't see"
    return cands


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


# Slugs dropped this run because they live inside a git submodule. Reported loudly at the
# end — a silently shrunk queue reads as "nothing was available" when the truth is
# "your highest-traffic page was offered and thrown away".
SUBMODULE_SKIPS = []
_SUBMODULE_PREFIXES = None


def submodule_prefixes(host_root):
    """Top-level paths that are git submodules, read from .gitmodules.

    Read rather than hardcoded: this repo's submodule list has changed before
    (games/, interview-coach-teamzlab/, roktolagbe/, branding/), and a stale constant
    would silently stop filtering the day one is added.
    """
    global _SUBMODULE_PREFIXES
    if _SUBMODULE_PREFIXES is None:
        prefixes = []
        gm = host_root / '.gitmodules'
        try:
            for line in gm.read_text().splitlines():
                line = line.strip()
                if line.startswith('path'):
                    _, _, val = line.partition('=')
                    val = val.strip().strip('/')
                    if val:
                        prefixes.append(val)
        except (IOError, OSError):
            pass
        _SUBMODULE_PREFIXES = prefixes
    return _SUBMODULE_PREFIXES


def is_submodule_slug(slug, host_root):
    """True when slug lives inside a submodule the nightly flow cannot commit through.

    2026-08-20: the queue ranked /games/arrow-escape-3d/ at position 3 — 646 clicks, the
    highest traffic in the whole queue — but games/ is a submodule, so the enhance agent
    edits it, fails to commit it through this repo, and the slot is wasted. Every night,
    because the page keeps re-earning its rank. Effective cap was 19, not 20.
    """
    if not slug:
        return False
    head = slug.strip('/').split('/', 1)[0]
    return head in submodule_prefixes(host_root)


def slug_exists(slug, host_root):
    if not slug:
        return False
    if is_submodule_slug(slug, host_root):
        if slug not in SUBMODULE_SKIPS:
            SUBMODULE_SKIPS.append(slug)
        return False
    return (host_root / slug.strip('/') / 'index.html').exists()


# A commit touching more than this many tool pages is a site-wide mechanical
# sweep (trust bar rollout, schema dateModified bump, bulk link fix) — not a
# per-tool content enhance. Those must not arm the cooldown: one sweep across
# 6,900 pages would otherwise freeze the entire enhance queue for `days`.
BULK_SWEEP_THRESHOLD = 50


def get_cooldown_slugs(host_root, days):
    out, _, _ = run_script(host_root, ['git', 'log', f'--since={days} days ago',
                                       '--name-only', '--pretty=format:%H'])
    touched = set()
    commit_slugs = []          # slugs seen in the commit currently being parsed

    def flush():
        if commit_slugs and len(commit_slugs) <= BULK_SWEEP_THRESHOLD:
            touched.update(commit_slugs)
        commit_slugs.clear()

    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith('/index.html'):
            commit_slugs.append('/' + line.rsplit('/', 1)[0] + '/')
        else:
            # bare sha line = start of a new commit block
            flush()
    flush()
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
        # AI-Overview cannibalization guard: page-1 rank + near-zero CTR + big
        # impressions = Google answers the query inline (AIO / SERP widget); those
        # impressions are NOT clickable and no title rewrite recovers them. A genuine
        # bad-title page at pos<=8 shows ~1-2% CTR, not <0.5%. Skip so Mode B effort
        # goes to recoverable pages (burned a run on business-day-calculator 2026-06).
        ctr = (clicks / impr) if impr else 0
        if pos <= 8 and impr >= 500 and ctr < 0.005:
            continue
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


# -----------------------------------------------------------------------------
# Pool 10 (striking-distance): GSC reality — money pages already ranking JUST below
# page 1 (position 11-20) with real impressions but ~0 clicks. The closest, highest-
# value wins: a small on-page push tips them onto page 1 where the clicks are. Scored
# HIGH so they LEAD the queue — this is the "re-anchor priority on GSC" lever: enhance
# the pages Google already shows, not pages picked from guessed volume.
#
# Sourced from the GSC-backed money snapshot (build-money-tracker.py, runs Phase 1 of
# the nightly — fresh before this queue builds in Phase 4). Tools-only: returns []
# anywhere the snapshot doesn't exist, so other consumer repos are unaffected.
# -----------------------------------------------------------------------------
def pool_striking_distance(host_root, cfg):
    snap = safe_read_json(host_root / 'data' / 'money-snapshots' / 'latest.json')
    if not snap:
        return [], None
    cands = []
    for pg in snap.get('pages', []):
        if pg.get('bucket') != 'STUCK':
            continue
        pos = pg.get('pos') or 0
        impr = pg.get('impr') or 0
        if not (8 <= pos <= 30) or impr <= 0:      # page-1-bottom (8-10) + page 2/3 — climbable demand
            continue                                # widened <=20->30 2026-06-13; floor 11->8 2026-07-12:
                                                    #  the old pos>=11 cutoff ABANDONED pages right before
                                                    #  the finish line — a page climbing 15->12->11 got
                                                    #  enhanced, then DROPPED at pos 10, stranded at
                                                    #  page-1-bottom one nudge from the high-CTR top (pos
                                                    #  3-5). Floor stops at 8 (not lower): a STUCK page at
                                                    #  pos 1-7 with ~0 clicks is usually AIO-cannibalised,
                                                    #  not a fixable rank — enhancing it wastes the cycle.
        slug = url_to_slug(pg.get('url', ''), cfg['site_url'])   # snapshot 'slug' is only the last
        if not slug or not slug_exists(slug, host_root):          # segment; the full path is in 'url'
            continue
        # closest-to-page-1 + most impressions lead; RPM bias is applied later via rev_weight
        score = min(150.0, 30.0 + impr / 3.0 + max(0, 30 - pos) * 2)
        cands.append({
            'slug': slug,
            'query': f"(striking distance — rank {pos:.1f}, push toward page 1)",
            'signal_score': round(score, 2),
            'mode': 'A',
            'source': 'striking-distance',
            'citation': f"GSC rank {pos:.1f}, {impr} impr, 0 clicks — page-2/3 money page, "
                        f"${pg.get('rpm','?')} RPM [money-snapshots/latest.json]",
        })
    return cands, None


def _faq_is_empty(html):
    """Same check the url-hygiene guard uses: a `var/const/let FAQS = [...]` block with zero
    q:/question: pairs. Returns False when there is no FAQ block at all (different template —
    not our target)."""
    fm = re.search(r'(?:var|const|let)\s+FAQS?\s*=\s*(\[.*?\])\s*;', html, re.S)
    if not fm:
        return False
    # match BOTH quoted JSON keys ("q":) and unquoted JS shorthand (q:) — the old \bq:
    # pattern missed the quoted form and mislabeled pages with rich FAQ as empty.
    return len(re.findall(r'''["']?\b(?:q|question)\b["']?\s*:''', fm.group(1), re.I)) == 0


def pool_thin_faq_demand(host_root, cfg):
    """Pages that HAVE Google demand (impressions) but ship an EMPTY FAQ = the highest-leverage
    content add on the site. The nightly enhancer writes real FAQ Q&A (prompt step 3), so feeding
    these THICKENS the page instead of pruning it — content where demand already exists. Demand
    comes from the money snapshot; emptiness from the same check the url-hygiene guard uses.
    Deliberately ignores zero-demand empty pages: content cannot rank a page nobody searches for."""
    snap = safe_read_json(host_root / 'data' / 'money-snapshots' / 'latest.json')
    if not snap:
        return [], None
    MIN_IMPR = 10                       # proven-demand floor — below this is noise
    cands = []
    for pg in snap.get('pages', []):
        impr = pg.get('impr') or 0
        if impr < MIN_IMPR:
            continue
        slug = url_to_slug(pg.get('url', ''), cfg['site_url'])
        if not slug or not slug_exists(slug, host_root):
            continue
        try:
            html = (host_root / slug.strip('/') / 'index.html').read_text(errors='ignore')
        except Exception:
            continue
        if not _faq_is_empty(html):
            continue
        pos = pg.get('pos') or 0
        # demand-weighted: empty -> full FAQ is a big content jump, so it scores aggressively,
        # but capped at 150 like striking-distance so no single pool dominates the sort.
        score = min(150.0, 40.0 + impr / 8.0)
        cands.append({
            'slug': slug,
            'query': f"(thin-FAQ + demand — {impr} impr, empty FAQ -> write real Q&A)",
            'signal_score': round(score, 2),
            'mode': 'A',
            'source': 'thin-faq',
            'citation': f"GSC {impr} impr, rank {pos:.1f}, FAQ array EMPTY — thicken with real "
                        f"Q&A (highest-leverage content add) [money-snapshots/latest.json + page scan]",
        })
    return cands, None


# Below this floor a "Google visits, AI never has" gap is noise, not demand.
AI_INVISIBLE_GOOGLE_FLOOR = 10


def pool_ai_invisible(host_root, cfg, days=90):
    """Pages with PROVEN Google demand that AI has NEVER sent a single session
    to, in `days` days. Investigation 2026-08-03: 1,065 such pages on this
    property — real searchers want them, ChatGPT/Perplexity/etc have simply
    never surfaced them. Of those, ~446 are the WebApplication/FAQPage schema
    gap (fixed separately, mechanically, for free); the rest need content —
    that's this pool. Additive-only: the goal is legibility, not a rewrite.

    UNION with the other pools, never a replacement — the picker rule that
    once hid 98.9% of revenue behind a hardcoded niche list is exactly the
    mistake a REPLACEMENT pool would repeat here."""
    import urllib.parse as _p
    import urllib.request as _u
    tok_path = Path(cfg["ga4_token_file"])
    pid = cfg.get("ga4_property_id")
    if not tok_path.exists() or not pid:
        return [], "GA4 token/property not configured"
    try:
        t = json.loads(tok_path.read_text())
        data = _p.urlencode({
            "client_id": t["client_id"], "client_secret": t["client_secret"],
            "refresh_token": t["refresh_token"], "grant_type": "refresh_token",
        }).encode()
        token = json.load(_u.urlopen(_u.Request(
            t.get("token_uri", "https://oauth2.googleapis.com/token"), data=data),
            timeout=30))["access_token"]
        body = json.dumps({
            "dateRanges": [{"startDate": f"{days}daysAgo", "endDate": "today"}],
            "dimensions": [{"name": "landingPage"}, {"name": "sessionDefaultChannelGroup"}],
            "metrics": [{"name": "sessions"}],
            "limit": 10000,
        }).encode()
        req = _u.Request(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport",
            data=body, method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        rows = json.load(_u.urlopen(req, timeout=90)).get("rows", [])
    except Exception as e:  # noqa: BLE001
        return [], f"GA4 pull failed: {type(e).__name__}: {e}"

    google, ai_seen = {}, set()
    for r in rows:
        path = r["dimensionValues"][0]["value"].split("?")[0]
        path = path if path.endswith("/") else path + "/"
        ch = r["dimensionValues"][1]["value"]
        sess = int(r["metricValues"][0]["value"])
        if ch == "Organic Search":
            google[path] = google.get(path, 0) + sess
        elif ch == "AI Assistant":
            ai_seen.add(path)

    cands = []
    for slug, sess in google.items():
        if sess < AI_INVISIBLE_GOOGLE_FLOOR or slug in ai_seen:
            continue
        if not slug_exists(slug, host_root):
            continue
        score = min(120.0, sess / 5.0)
        cands.append({
            'slug': slug,
            'query': f"(AI-invisible — {sess} Google sessions/{days}d, 0 AI sessions -> add citable structure)",
            'signal_score': round(score, 2),
            'mode': 'A',
            'source': 'ai-invisible-demand-gap',
            'citation': f"GA4 {sess} Organic Search sessions/{days}d, 0 AI Assistant sessions "
                        f"[sessionDefaultChannelGroup]",
        })
    cands.sort(key=lambda c: -c['signal_score'])
    return cands, None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cap', type=int, default=7)
    p.add_argument('--cooldown', type=int, default=7)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    cfg = load_runtime(__file__)
    host_root = cfg['host_site_root']

    # RANK_V2 — opt-in per property via .teamz-automation.env (TEAMZ_ENHANCE_RANK_V2=1).
    # OFF by default so apps/goalkit/learn/tekko keep the exact ranking they have today;
    # tools opted in 2026-08-30 after a measurement showed the queue was burying its own
    # best-earning page. Three defects, all of which only bite once several pools compete:
    #   A. pool scores were on incompatible scales (min(80,..) vs min(150.,..) vs uncapped,
    #      which reached 872) — so a page's rank was set by WHICH POOL FOUND IT, not by
    #      what it is worth. /pest/bug-bite-identifier/ (measured $9.38 RPM, 8x site median)
    #      arrived via a pool ceilinged at 80 and could never outrank a saturated 150.
    #   B. the niche-benchmark fallback was used at face value. Measured on tools the same
    #      night: /us/ benchmark $35.00 vs GA4-measured $0.75 (47x), /finance/ $31.50 vs
    #      $1.68 (19x). Invented numbers outranked counted ones.
    #   C. revival_floor filled slots BEFORE the sort, so pages scoring 0.40 pre-empted
    #      live earners.
    # Default ON for tools, OFF everywhere else, overridable by the env var either way.
    # The default lives HERE, in tracked code, and not in .teamz-automation.env — that file
    # is gitignored, so an env-only opt-in would survive exactly as long as this laptop's
    # filesystem and would then revert with no error and no log line.
    _RANK_V2_DEFAULT_HOSTS = ("tool.teamzlab.com",)
    _rv = os.getenv("TEAMZ_ENHANCE_RANK_V2", "").strip().lower()
    if _rv in ("1", "true", "yes", "on"):
        rank_v2 = True
    elif _rv in ("0", "false", "no", "off"):
        rank_v2 = False
    else:
        rank_v2 = any(h in cfg.get("site_url", "") for h in _RANK_V2_DEFAULT_HOSTS)
    if rank_v2:
        print("[enhance-queue] RANK_V2 ON — pool scores normalised, benchmark RPM capped at "
              "the site's own measured median, revival takes leftovers only")

    print(f"[enhance-queue] cap={args.cap}, cooldown={args.cooldown}d, host={host_root}")
    print(f"[enhance-queue] Calling existing Teamz scripts (Rule 1: no fabricated data)")

    cooldown_set = get_cooldown_slugs(host_root, args.cooldown)
    print(f"[enhance-queue] cooldown excludes {len(cooldown_set)} slugs from last {args.cooldown}d")
    # Experiment freeze: data/enhance-freeze.json lists slugs the engine must not pick
    # until a date — e.g. the 20 treated + 20 control pages of a hand-edit vs engine
    # comparison. One engine edit on a control page voids the whole comparison, so
    # this is a hard exclusion, not a score penalty. Expired or malformed file = no-op,
    # printed so a silent expiry cannot be mistaken for protection.
    freeze = safe_read_json(host_root / 'data' / 'enhance-freeze.json') or {}
    frozen = set(freeze.get('slugs') or [])
    if frozen:
        until = str(freeze.get('until') or '')
        if until and until < datetime.now().strftime('%Y-%m-%d'):
            print(f"[enhance-queue] freeze file EXPIRED on {until} — {len(frozen)} slugs no longer protected")
        else:
            cooldown_set |= frozen
            print(f"[enhance-queue] freeze excludes {len(frozen)} slugs until {until or 'unset'} ({freeze.get('reason','')})")

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
    p10, e10 = pool_striking_distance(host_root, cfg)
    if e10: errors['striking_distance'] = e10
    p11, e11 = pool_thin_faq_demand(host_root, cfg)
    if e11: errors['thin_faq'] = e11
    p12, e12 = pool_ai_invisible(host_root, cfg)
    if e12: errors['ai_invisible'] = e12
    p4 = pool_gaps_seasonal(host_root)
    p5 = pool_autocomplete_trends()

    print(f"[enhance-queue] pool1 rising-tools:      {len(p1)}")
    print(f"[enhance-queue] pool2 gsc-opportunities: {len(p2)}")
    print(f"[enhance-queue] pool3 bing:              {len(p3)}")
    print(f"[enhance-queue] pool6 gsc-ctr-drops:     {len(p6)}")
    print(f"[enhance-queue] pool7 canonical-fix:     {len(p7)}")
    print(f"[enhance-queue] pool8 cold-start:        {len(p8c)}")
    print(f"[enhance-queue] pool9 dead-revival:      {len(p8r)}")
    print(f"[enhance-queue] pool10 striking-dist:    {len(p10)}")
    print(f"[enhance-queue] pool11 thin-faq+demand:  {len(p11)}")
    print(f"[enhance-queue] pool12 ai-invisible:     {len(p12)}")
    print(f"[enhance-queue] pool4 gaps:              {len(p4['gaps'])}")
    print(f"[enhance-queue] pool4 seasonal:          {len(p4['seasonal'])}")
    print(f"[enhance-queue] pool5 autocomplete:      {len(p5['suggestions'])}")
    print(f"[enhance-queue] pool5 trends:            {len(p5['trends'])}")
    if errors:
        for k, v in errors.items():
            print(f"[enhance-queue]   ! {k}: {v}")

    # Merge target pools (1-3, 6, 7, 8-cold-start, 12), dedupe by slug, apply cooldown.
    # pool12 (ai_invisible) is a UNION addition, never a replacement for any pool
    # above — the last time a picker swapped a rule instead of adding one, it hid
    # 98.9% of revenue behind a hardcoded niche list.
    by_slug = {}
    for c in p10 + p11 + p12 + p1 + p2 + p3 + p6 + p7 + p8c + p8r:
        if c['slug'] in cooldown_set:
            continue
        if c['slug'] not in by_slug or c['signal_score'] > by_slug[c['slug']]['signal_score']:
            by_slug[c['slug']] = c

    # AI-channel guard — downgrade Mode B (title/meta rewrite) wherever ChatGPT/
    # Perplexity/etc already send this page real traffic Google doesn't see.
    # See ga4_ai_sessions()/apply_ai_guard() above for why this exists.
    ai_by_path = ga4_ai_sessions(cfg)
    ai_known = ai_by_path is not None
    print(f"[enhance-queue] AI channel: {'unavailable — Mode B failed closed to A' if not ai_known else f'{len(ai_by_path)} page(s) with AI traffic (28d)'}")
    apply_ai_guard(list(by_slug.values()), ai_by_path or {}, ai_known)

    # Revenue weighting: bias the queue toward higher-RPM niches so enhancement effort goes
    # to pages that EARN, not just rank. Reuses revenue_priority (no new RPM math). Multiplies
    # the SORT KEY only — signal_score itself is untouched, so the source-quota logic below is
    # unaffected. Degrades to weight 1.0 if the module/data is unavailable.
    import re as _re_pos
    def _pos_from_citation(cit):
        m = _re_pos.search(r'(?:pos|rank)\s+([0-9]+(?:\.[0-9]+)?)', cit or '', _re_pos.I)
        return float(m.group(1)) if m else None
    # Layer 1 (measured): what each page ACTUALLY earned, from GA4 totalAdRevenue. The niche
    # benchmarks below are community-sourced averages (see rpm-benchmarks.json `sources`) and
    # they put 34 of 105 measurable pages on the wrong side of the 1.0x line — /amazon/
    # weighted 2.20x while earning $4.99 RPM, the German World Cup page weighted 0.50x while
    # earning $71.71. Measured wins wherever it exists; every other page keeps the benchmark.
    # None (GA4 unreachable) or a page below the session floor -> unchanged behaviour.
    try:
        import revenue_signals as _rs
        _measured = _rs.measured_rpm(cfg)
    except Exception as e:  # noqa: BLE001
        print(f"[enhance-queue] measured-RPM layer skipped ({type(e).__name__}) — benchmarks only")
        _measured = None
    print(f"[enhance-queue] revenue: "
          + ("measured RPM unavailable — niche benchmarks for every page"
             if _measured is None else
             f"{len(_measured)} page(s) weighted by MEASURED revenue, rest by niche benchmark"))

    try:
        import revenue_priority as _rp

        # Carry the measured signal to candidates that have no traffic of their own: the
        # median real RPM of this site's pages in the same niche. See calibrated_niche_rpm()
        # — the published benchmarks overrate every commercial niche 2-5x for a TOOLS site.
        # 2026-08-10: was `s.strip('/').split('/')[0]` as hub — wrong whenever slug has no "/"
        # (the normal case), silently mispriced 702 pages to niche="productivity" ($6.5 RPM).
        # rp.hub_for() reads tools.json's real hub field instead. See revenue_priority.py's
        # 2026-08-10 note for the full story.
        _niche_rpm = _rs.calibrated_niche_rpm(
            _measured, lambda s: _rp.niche_for(_rp.hub_for(s, host_root), s, ''))
        if _niche_rpm:
            print(f"[enhance-queue] revenue: {len(_niche_rpm)} niche(s) re-priced from this "
                  f"site's own earnings: "
                  + ", ".join(f"{n} ${v}" for n, v in sorted(_niche_rpm.items())))

        _median_rpm = _rs.median_rpm(_measured)
        if _median_rpm:
            print(f"[enhance-queue] revenue: anchoring rev_weight to this site's own median "
                  f"page RPM ${_median_rpm:.2f} (1.0x); a hardcoded $10 anchor put ~every "
                  f"page on the 0.5 clamp floor")
        else:
            print("[enhance-queue] revenue: no measured median available — rev_weight falls "
                  "back to the $10 benchmark anchor (weighting will be weak; not silent)")

        _src_counts = {}
        for c in by_slug.values():
            hub = _rp.hub_for(c['slug'], host_root)
            ed = _rp.expected_dollars(c['slug'], hub, c.get('title', ''),
                                      visitors_mo=1000, serp_winnability=6)
            c['niche'] = ed['niche']
            rpm, rpm_src = (_rs.rpm_for(c['slug'], _measured, ed['rpm_mid'],
                                        niche=ed['niche'], niche_rpm=_niche_rpm)
                            if _measured is not None else (ed['rpm_mid'], 'niche-benchmark'))
            _src_counts[rpm_src] = _src_counts.get(rpm_src, 0) + 1
            c['rpm_mid'] = rpm
            c['rpm_source'] = rpm_src
            # Anchored to this site's OWN median RPM, not a hardcoded $10. With the
            # constant, every page under $5 RPM collapsed onto the 0.5 clamp floor —
            # which on a $1.16-RPM site is ~99% of the catalogue — so the revenue
            # weighting ranked a $0.15 page identically to a $3.92 one. See
            # revenue_signals.weight_from_rpm() for the measured numbers.
            # RANK_V2/B: a page with NO measurement must not be priced above what the
            # best-measured pages actually earn. The benchmark table is built from CONTENT
            # sites and overrates tool pages 2-5x (see calibrated_niche_rpm's docstring);
            # unclamped it handed /us/ pages $35.00 RPM against a measured $0.75. Cap at 2x
            # this site's own median so an unmeasured page can still lead a measured one,
            # but only within touching distance of reality. Left as-is when the median is
            # unknown — a guess about a guess is not an improvement.
            if rank_v2 and rpm_src == "niche-benchmark" and _median_rpm:
                capped = min(rpm, _median_rpm * 2.0)
                if capped < rpm:
                    c['rpm_benchmark_raw'] = rpm
                    rpm = capped
                    c['rpm_mid'] = rpm
                    c['rpm_source'] = "niche-benchmark-capped"
            rw = _rs.weight_from_rpm(rpm, anchor=_median_rpm)
            # Position-proximity boost: a page in the 11-15 "one nudge from page 1" zone
            # converts to clicks THIS month; an equal-RPM page at pos 25+ needs a quarter.
            # Lead the striking sweet-spot over deeper pages. Pos parsed from the candidate's
            # citation ("pos X.X" / "rank X.X"); no pos found = no change (graceful).
            pos = _pos_from_citation(c.get('citation', ''))
            if pos is not None:
                if 11 <= pos <= 15:   rw *= 1.4    # striking sweet spot — lead the queue
                elif 8 <= pos < 11:   rw *= 1.15   # already page 1 — small nudge toward top-5
                elif pos > 22:        rw *= 0.8    # too deep to convert soon — de-prioritize
            c['pos'] = pos
            c['rev_weight'] = round(rw, 2)
        print("[enhance-queue] revenue weighting by source: "
              + ", ".join(f"{k}={v}" for k, v in sorted(_src_counts.items())))
    except Exception as e:
        print(f"[enhance-queue] revenue weighting skipped ({type(e).__name__}) — raw signal sort")
        for c in by_slug.values():
            c['rev_weight'] = 1.0

    # RANK_V2/A: put every pool on ONE scale before sorting. Each pool keeps its own
    # internal order (best of that pool = 100, worst = 10, linear on rank), so what
    # crosses pools is "how good is this FOR ITS POOL" times what the page is worth —
    # never the arbitrary ceiling its scorer happened to use. Raw signal_score is kept
    # untouched: the source quotas below and every consumer of the JSON still read it.
    # Two pools are SPECULATIVE by construction: cold-start pages have no traffic yet and
    # dead-revival pages have no demand. Their own scorers deliberately hand out 0.5 and 0.4
    # so they "can only ever use LEFTOVER capacity, never displaces a proven target" (their
    # comments, above). Normalising them would hand each pool's best member a 100 and break
    # exactly that guarantee — measured on the first run of this patch, cold-start jumped
    # from 0 slots to 5 of 26. They keep their raw floor scores and stay at the bottom.
    _SPECULATIVE = ('cold-start', 'dead-revival')
    if rank_v2:
        from collections import defaultdict as _dd
        _by_src = _dd(list)
        for c in by_slug.values():
            _by_src[c.get('source', '')].append(c)
        for _src, _members in _by_src.items():
            if _src in _SPECULATIVE:
                for c in _members:
                    c['pool_score'] = c['signal_score']
                continue
            _members.sort(key=lambda x: -x['signal_score'])
            n = len(_members)
            for i, c in enumerate(_members):
                # single-member pool -> 100.0; it IS the best of its pool, and rev_weight
                # then decides whether it deserves a slot at all.
                c['pool_score'] = 100.0 if n == 1 else round(100.0 - (i / (n - 1)) * 90.0, 2)
        print("[enhance-queue] RANK_V2 normalised "
              + ", ".join(f"{k or '(none)'}={len(v)}" for k, v in sorted(_by_src.items())))
    else:
        for c in by_slug.values():
            c['pool_score'] = c['signal_score']

    ranked = sorted(by_slug.values(),
                    key=lambda x: x['pool_score'] * x.get('rev_weight', 1.0), reverse=True)

    # Cap with mode mix: target 4 Mode A google + 2 Mode B google + 1 bing
    final = []
    a_quota = max(1, args.cap // 2)
    b_quota = max(1, args.cap // 4)
    bing_quota = max(1, args.cap // 7)
    cold_quota = max(1, args.cap // 4)   # cold-start share raised (user: don't skip low) — 5 at cap 20
    revival_quota = max(1, args.cap // 4)  # dead-revival share raised (user: don't skip dead) — 5 at cap 20
    striking_quota = max(2, args.cap // 2)  # GSC near-page-1 money pages LEAD — up to half the run
    faq_quota = max(2, args.cap // 4)       # thin-FAQ + demand: content-thicken share — 5 at cap 20
    counts = {'A_google': 0, 'B_google': 0, 'bing': 0, 'other': 0, 'cold': 0, 'revival': 0,
              'striking': 0, 'thin_faq': 0}

    # Guaranteed FLOOR for dead-revival: revived pages carry low signal scores (they are, by
    # definition, dead), so a purely greedy score-sorted fill never reaches them once striking +
    # thin-faq fill the cap — they got 0 slots. The user's rule is "don't skip dead", so reserve a
    # floor for revival FIRST (highest-scored revival candidates), then greedy-fill the remainder.
    revival_floor = max(2, args.cap // 6)    # ~3 at cap 20 — never skip dead entirely
    # RANK_V2/C: dead-revival still gets revival_quota in the greedy loop below, so dead
    # pages are never skipped entirely — the user's rule holds. What stops is the floor
    # PRE-PASS, which seated candidates scoring 0.40 ahead of everything measured.
    if rank_v2:
        revival_floor = 0
    for c in ranked:
        if counts['revival'] >= revival_floor:
            break
        if c['source'] == 'dead-revival':
            final.append(c); counts['revival'] += 1
    picked = {c['slug'] for c in final}

    # RANK_V2/C part 2: with the pre-pass gone, dead-revival scored 0.4 and the greedy fill
    # never reached it — 3 slots became 0, which breaks the user's "don't skip dead" rule in
    # the other direction. So reserve the TAIL, not the head: greedy-fill stops short and the
    # speculative pools take the last seats. Proven earners are never displaced, and the dead
    # pool is never zeroed.
    spec_tail = (max(1, args.cap // 13) if rank_v2 else 0)     # 2 at cap 26, 1 at cap 7
    greedy_cap = args.cap - spec_tail
    for c in ranked:
        if len(final) >= greedy_cap:
            break
        if c['slug'] in picked:                  # already taken by the revival floor pass
            continue
        if c['source'] == 'striking-distance':   # highest priority: pages already on page 2,
            if counts['striking'] >= striking_quota:   # one push from page 1 — but capped so
                continue                          # other pools still get worked each run
            final.append(c); counts['striking'] += 1
            continue
        if c['source'] == 'thin-faq':            # demand pages with empty FAQ — write content,
            if counts['thin_faq'] >= faq_quota:   # don't prune; quota'd so it shares the run
                continue
            final.append(c); counts['thin_faq'] += 1
            continue
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

    if spec_tail:
        picked = {c['slug'] for c in final}
        for _src, _key in (('dead-revival', 'revival'), ('cold-start', 'cold')):
            for c in ranked:
                if len(final) >= args.cap:
                    break
                if c['slug'] in picked or c['source'] != _src:
                    continue
                final.append(c); counts[_key] += 1; picked.add(c['slug'])
        # Anything the speculative pools could not fill goes back to proven candidates —
        # an unfilled reservation must not shrink the night's work.
        for c in ranked:
            if len(final) >= args.cap:
                break
            if c['slug'] in picked:
                continue
            final.append(c); counts['other'] += 1; picked.add(c['slug'])

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
            'GA4 sessionDefaultChannelGroup, 90d (Pool 12 AI-invisible demand gap)',
        ],
        'pool_counts': {
            'striking_distance': len(p10),
            'thin_faq': len(p11),
            'ai_invisible': len(p12),
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

    # OUTSIDE the dry-run branch on purpose: a warning that only fires on a real write is
    # invisible exactly when someone is inspecting the queue by hand to find out why it looks
    # short. Loud in both modes.
    if SUBMODULE_SKIPS:
        # These are real, high-signal pages this flow structurally cannot enhance — they need
        # a session that commits inside the submodule and bumps the pointer. Saying nothing
        # would let a shrunk queue read as a quiet night.
        print(f"[enhance-queue] SKIPPED {len(SUBMODULE_SKIPS)} submodule page(s) the nightly "
              f"cannot commit: {', '.join(SUBMODULE_SKIPS)} "
              f"— enhance these from a session that commits inside the submodule.")
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
