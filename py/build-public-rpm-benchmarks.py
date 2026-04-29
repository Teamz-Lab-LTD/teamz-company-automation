#!/usr/bin/env python3
"""
build-public-rpm-benchmarks.py — Public AdSense/Ezoic/Mediavine RPM benchmarks.

Maintains a local JSON database of niche RPMs collated from public sources:
  - Ezoic Big Data Analytics (publicly published niche EPMV)
  - Mediavine annual reports (per-niche EPMV)
  - NicheSiteProject case studies
  - AdSense help docs CPC ranges
  - Publisher community averages

These are SEED values from public reports as of 2026-04. They are
INTENTIONALLY hardcoded (not scraped) because:
  1. Public reports update annually, not daily
  2. HTML scraping breaks; data here is human-verified
  3. /ideas needs a stable lookup, not best-effort scraping

Refresh manually each quarter by:
  1. Reading the latest Ezoic / Mediavine / NSP reports
  2. Updating BENCHMARKS dict below
  3. Bumping LAST_UPDATED

Usage:
  python3 scripts/build-public-rpm-benchmarks.py            # write data/rpm-benchmarks.json
  python3 scripts/build-public-rpm-benchmarks.py --query finance --country US
  python3 scripts/build-public-rpm-benchmarks.py --top 10
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'rpm-benchmarks.json'

LAST_UPDATED = '2026-04-13'

# Niche → list of {country, RPM_low, RPM_high, source, notes}
# Numbers are USD CPM (i.e., per 1000 ad impressions on that niche, in that country).
# For multi-country niches, US is anchor; tier-S countries (CH/NO/AU/DK/SE/NZ/IE/SG)
# typically get +30-80% over US; tier-A (CA/DE/AT/IL/BE/UAE/NL/FI/JP) +0-30%;
# emerging (BD/IN/PK/NG) get -90% (≈$0.20-1.50).
#
# Sources cited in `source` field — prefer these when possible:
#   - "Ezoic 2025": Ezoic Big Data Analytics niche report
#   - "Mediavine 2025": Mediavine annual EPMV report
#   - "NSP 2024": NicheSiteProject case studies
#   - "Reddit/Adsense 2025": community-validated averages
BENCHMARKS = {
    # ===== TIER-S RPM (>= $20 US) =====
    'finance': [
        {'country': 'US', 'low': 18, 'high': 45, 'source': 'Ezoic 2025 + Mediavine'},
        {'country': 'UK', 'low': 12, 'high': 30, 'source': 'Ezoic 2025'},
        {'country': 'CA', 'low': 14, 'high': 32, 'source': 'Ezoic 2025'},
        {'country': 'AU', 'low': 16, 'high': 35, 'source': 'Ezoic 2025'},
        {'country': 'SG', 'low': 12, 'high': 28, 'source': 'NSP 2024'},
        {'country': 'JP', 'low': 6, 'high': 14, 'source': 'NSP 2024'},
        {'country': 'CH', 'low': 25, 'high': 60, 'source': 'Ezoic 2025'},
        {'country': 'NO', 'low': 22, 'high': 50, 'source': 'Ezoic 2025'},
    ],
    'tax': [
        {'country': 'US', 'low': 20, 'high': 50, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 15, 'high': 35, 'source': 'Ezoic 2025'},
        {'country': 'CA', 'low': 16, 'high': 38, 'source': 'Ezoic 2025'},
        {'country': 'AU', 'low': 18, 'high': 40, 'source': 'Ezoic 2025'},
        {'country': 'SG', 'low': 14, 'high': 32, 'source': 'NSP 2024'},
        {'country': 'JP', 'low': 5, 'high': 12, 'source': 'NSP 2024'},
        {'country': 'DE', 'low': 14, 'high': 30, 'source': 'Ezoic 2025'},
    ],
    'insurance': [
        {'country': 'US', 'low': 25, 'high': 60, 'source': 'Mediavine 2025'},
        {'country': 'UK', 'low': 18, 'high': 40, 'source': 'Mediavine 2025'},
        {'country': 'CA', 'low': 20, 'high': 45, 'source': 'Mediavine 2025'},
        {'country': 'AU', 'low': 22, 'high': 48, 'source': 'Mediavine 2025'},
    ],
    'mortgage': [
        {'country': 'US', 'low': 30, 'high': 80, 'source': 'NSP 2024'},
        {'country': 'UK', 'low': 22, 'high': 55, 'source': 'NSP 2024'},
        {'country': 'CA', 'low': 25, 'high': 60, 'source': 'NSP 2024'},
        {'country': 'AU', 'low': 28, 'high': 65, 'source': 'NSP 2024'},
    ],
    'legal': [
        {'country': 'US', 'low': 22, 'high': 55, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 16, 'high': 38, 'source': 'Ezoic 2025'},
        {'country': 'CA', 'low': 18, 'high': 42, 'source': 'Ezoic 2025'},
    ],

    # ===== TIER-A RPM ($10-20 US) =====
    'business-saas': [
        {'country': 'US', 'low': 14, 'high': 30, 'source': 'Mediavine 2025'},
        {'country': 'UK', 'low': 10, 'high': 22, 'source': 'Mediavine 2025'},
        {'country': 'CA', 'low': 11, 'high': 24, 'source': 'Mediavine 2025'},
    ],
    'b2b-leadgen': [
        {'country': 'US', 'low': 50, 'high': 300, 'source': 'NSP 2024 (per-lead, not CPM)',
         'notes': 'B2B is lead-gen not impression-based. Per qualified email lead.'},
        {'country': 'EU', 'low': 40, 'high': 250, 'source': 'NSP 2024 (per-lead)'},
    ],
    'health-supplements': [
        {'country': 'US', 'low': 12, 'high': 28, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 9, 'high': 20, 'source': 'Ezoic 2025'},
        {'country': 'CA', 'low': 10, 'high': 22, 'source': 'Ezoic 2025'},
        {'country': 'AU', 'low': 11, 'high': 24, 'source': 'Ezoic 2025'},
    ],
    'longevity': [
        {'country': 'US', 'low': 15, 'high': 35, 'source': 'NSP 2024 (high-CPC niche)'},
        {'country': 'UK', 'low': 11, 'high': 25, 'source': 'NSP 2024'},
        {'country': 'AU', 'low': 13, 'high': 28, 'source': 'NSP 2024'},
    ],
    'real-estate': [
        {'country': 'US', 'low': 12, 'high': 28, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 9, 'high': 20, 'source': 'Ezoic 2025'},
        {'country': 'CA', 'low': 10, 'high': 22, 'source': 'Ezoic 2025'},
        {'country': 'AU', 'low': 11, 'high': 25, 'source': 'Ezoic 2025'},
        {'country': 'SG', 'low': 13, 'high': 30, 'source': 'NSP 2024 (HDB/BTO)'},
    ],
    'career-jobs': [
        {'country': 'US', 'low': 10, 'high': 22, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 7, 'high': 16, 'source': 'Ezoic 2025'},
        {'country': 'AU', 'low': 9, 'high': 20, 'source': 'Ezoic 2025'},
    ],

    # ===== TIER-B RPM ($5-10 US) =====
    'health-general': [
        {'country': 'US', 'low': 8, 'high': 18, 'source': 'Mediavine 2025'},
        {'country': 'UK', 'low': 6, 'high': 14, 'source': 'Mediavine 2025'},
        {'country': 'CA', 'low': 7, 'high': 15, 'source': 'Mediavine 2025'},
        {'country': 'AU', 'low': 7, 'high': 16, 'source': 'Mediavine 2025'},
    ],
    'parenting-family': [
        {'country': 'US', 'low': 7, 'high': 16, 'source': 'Mediavine 2025'},
        {'country': 'UK', 'low': 5, 'high': 12, 'source': 'Mediavine 2025'},
    ],
    'education': [
        {'country': 'US', 'low': 6, 'high': 15, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 4, 'high': 11, 'source': 'Ezoic 2025'},
    ],
    'travel': [
        {'country': 'US', 'low': 6, 'high': 14, 'source': 'Mediavine 2025'},
        {'country': 'UK', 'low': 5, 'high': 11, 'source': 'Mediavine 2025'},
    ],
    'home-improvement': [
        {'country': 'US', 'low': 7, 'high': 16, 'source': 'Mediavine 2025'},
        {'country': 'UK', 'low': 5, 'high': 12, 'source': 'Mediavine 2025'},
    ],
    'auto': [
        {'country': 'US', 'low': 6, 'high': 14, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 4, 'high': 10, 'source': 'Ezoic 2025'},
    ],

    # ===== TIER-C RPM ($2-5 US) =====
    'technology': [
        {'country': 'US', 'low': 4, 'high': 10, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 3, 'high': 8, 'source': 'Ezoic 2025'},
    ],
    'productivity': [
        {'country': 'US', 'low': 4, 'high': 9, 'source': 'NSP 2024'},
        {'country': 'UK', 'low': 3, 'high': 7, 'source': 'NSP 2024'},
    ],
    'lifestyle': [
        {'country': 'US', 'low': 3, 'high': 8, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 2, 'high': 6, 'source': 'Ezoic 2025'},
    ],
    'fitness-workout': [
        {'country': 'US', 'low': 4, 'high': 10, 'source': 'Mediavine 2025'},
        {'country': 'UK', 'low': 3, 'high': 8, 'source': 'Mediavine 2025'},
    ],
    'food-recipes': [
        {'country': 'US', 'low': 5, 'high': 13, 'source': 'Mediavine 2025'},
        {'country': 'UK', 'low': 4, 'high': 10, 'source': 'Mediavine 2025'},
    ],

    # ===== TIER-D RPM (<= $3 US) =====
    'entertainment': [
        {'country': 'US', 'low': 1, 'high': 4, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 1, 'high': 3, 'source': 'Ezoic 2025'},
    ],
    'gaming': [
        {'country': 'US', 'low': 2, 'high': 5, 'source': 'Ezoic 2025'},
        {'country': 'UK', 'low': 1, 'high': 4, 'source': 'Ezoic 2025'},
    ],
    'memes-jokes': [
        {'country': 'US', 'low': 0.5, 'high': 2, 'source': 'NSP 2024 (saturated)'},
    ],
    'creative-art': [
        {'country': 'US', 'low': 2, 'high': 6, 'source': 'Ezoic 2025'},
    ],

    # ===== EMERGING MARKETS (regardless of niche) =====
    '_emerging_markets_multiplier': [
        {'country': 'BD', 'low': 0.05, 'high': 0.30, 'source': 'AdSense data',
         'notes': 'Multiply ANY niche RPM by 0.02-0.06 for BD audience'},
        {'country': 'IN', 'low': 0.10, 'high': 0.50, 'source': 'AdSense data'},
        {'country': 'PK', 'low': 0.05, 'high': 0.25, 'source': 'AdSense data'},
        {'country': 'NG', 'low': 0.05, 'high': 0.20, 'source': 'AdSense data'},
        {'country': 'PH', 'low': 0.20, 'high': 0.80, 'source': 'AdSense data'},
        {'country': 'ID', 'low': 0.15, 'high': 0.60, 'source': 'AdSense data'},
    ],
}


def write():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'last_updated': LAST_UPDATED,
        'sources': [
            'Ezoic Big Data Analytics 2025',
            'Mediavine 2025 EPMV report',
            'NicheSiteProject case studies 2024',
            'Reddit r/Adsense + r/juststart community averages',
            'AdSense Help Center CPC ranges',
        ],
        'units': 'USD CPM (per 1000 impressions). Exception: b2b-leadgen is per-lead.',
        'caveats': [
            'Numbers are public benchmarks. Your actual RPM depends on account age, '
            'CWV, traffic quality, and content relevance.',
            'Tier-S countries (CH/NO/AU/DK/SE/NZ/IE/SG) get +30-80% over US in same niche.',
            'Emerging markets (BD/IN/PK/NG/PH/ID) RPM is 2-10% of US for the same niche.',
            'New AdSense accounts (<60 days) earn 30-80% below mature account RPM.',
        ],
        'benchmarks': BENCHMARKS,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'Wrote {OUT.relative_to(ROOT)}')
    print(f'  {len(BENCHMARKS)} niches')
    print(f'  {sum(len(v) for v in BENCHMARKS.values())} country/niche pairs')
    print(f'  Last updated: {LAST_UPDATED}')


def query(niche=None, country=None, top_n=None):
    rows = []
    for nk, entries in BENCHMARKS.items():
        for e in entries:
            row = {'niche': nk, **e}
            if niche and niche.lower() not in nk.lower():
                continue
            if country and country.upper() != e['country'].upper():
                continue
            rows.append(row)

    rows.sort(key=lambda r: -((r['low'] + r['high']) / 2))
    if top_n:
        rows = rows[:top_n]

    print(f'{"NICHE":<24} {"CTRY":<6} {"LOW":>7} {"HIGH":>7}  SOURCE')
    print('-' * 80)
    for r in rows:
        print(f'{r["niche"]:<24} {r["country"]:<6} ${r["low"]:>6.2f} ${r["high"]:>6.2f}  {r["source"]}')


def main():
    args = sys.argv[1:]

    if '--query' in args or '--country' in args or '--top' in args:
        niche = None
        country = None
        top_n = None
        if '--query' in args:
            niche = args[args.index('--query') + 1]
        if '--country' in args:
            country = args[args.index('--country') + 1]
        if '--top' in args:
            top_n = int(args[args.index('--top') + 1])
        query(niche=niche, country=country, top_n=top_n)
    else:
        write()


if __name__ == '__main__':
    main()
