#!/usr/bin/env python3
"""
aso-admob-rpm-benchmarks.py — Public AdMob/IAP eCPM benchmarks for mobile apps.

Mobile counterpart to build-public-rpm-benchmarks.py (web AdSense).

Maintains a local JSON database of mobile-ad eCPM (effective CPM) by:
  - App category (15 categories matching ASO taxonomy)
  - Ad format (banner / interstitial / rewarded / native / app-open)
  - Country (with tier multipliers off US baseline)

Numbers compiled from public sources — INTENTIONALLY hardcoded:
  - AdMob official benchmarks (Google publisher help)
  - AppLovin 2024 mobile ad benchmarks report
  - ironSource State of Mobile Gaming 2024
  - Statista mobile ad CPM by country 2024
  - AppsFlyer Performance Index 2024
  - Sensor Tower / data.ai free preview reports
  - Reddit r/AdMob + r/iOSProgramming community averages

Refresh manually each quarter:
  1. Pull latest AdMob/AppLovin/ironSource public reports
  2. Update BENCHMARKS dict + TIER_MULTIPLIERS below
  3. Bump LAST_UPDATED
  4. Cross-validate vs reddit-aso-rpm-crowd.json (run with --validate)

Use cases (ranked by $ impact):
  1. App idea generation — gate ideation by eCPM × volume × difficulty
  2. Country localization priority — pick markets by US-relative tier
  3. Monetization model decision — ads-only vs IAP vs hybrid
  4. IAP price ladder per country
  5. Investor / positioning deck

Usage:
  python3 aso-admob-rpm-benchmarks.py                             # write JSON
  python3 aso-admob-rpm-benchmarks.py --query finance --country US
  python3 aso-admob-rpm-benchmarks.py --top 10                    # highest eCPM combos
  python3 aso-admob-rpm-benchmarks.py --top 10 --format rewarded  # filter by ad format
  python3 aso-admob-rpm-benchmarks.py --revenue-projection \\
            --category finance-apps --country US --daus 1000      # rough rev calc
  python3 aso-admob-rpm-benchmarks.py --validate                  # crowd cross-check
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data' / 'admob-rpm-benchmarks.json'
CROWD = ROOT / 'data' / 'reddit-aso-rpm-crowd.json'

LAST_UPDATED = '2026-04-30'

# Per-category eCPM in USD by ad format. US baseline. Apply TIER_MULTIPLIERS for other countries.
# Format: {category: {format: {low, high, notes}}}
# Categories match aso-niche taxonomy in build-reddit-rpm-tracker.py --niche aso.
BENCHMARKS = {
    # ===== HIGH-eCPM (FINANCE / SHOPPING / WEB3) =====
    'finance-apps': {
        'banner':       {'low': 1.50, 'high': 5.00, 'source': 'AdMob/AppsFlyer 2024'},
        'interstitial': {'low': 8.00, 'high': 25.00, 'source': 'AdMob 2024'},
        'rewarded':     {'low': 12.00, 'high': 40.00, 'source': 'AdMob 2024 (highest non-gaming)'},
        'native':       {'low': 3.00, 'high': 12.00, 'source': 'AppsFlyer 2024'},
        'app-open':     {'low': 2.00, 'high': 8.00, 'source': 'AdMob 2024'},
        'iap_arpdau':   {'low': 0.05, 'high': 0.40, 'source': 'GameAnalytics non-gaming median'},
    },
    'shopping-apps': {
        'banner':       {'low': 1.00, 'high': 3.50, 'source': 'AdMob 2024'},
        'interstitial': {'low': 6.00, 'high': 18.00, 'source': 'AdMob 2024'},
        'rewarded':     {'low': 10.00, 'high': 25.00, 'source': 'AppsFlyer 2024'},
        'native':       {'low': 2.50, 'high': 9.00, 'source': 'AppsFlyer 2024'},
        'app-open':     {'low': 1.50, 'high': 6.00, 'source': 'AdMob 2024'},
        'iap_arpdau':   {'low': 0.02, 'high': 0.15, 'source': 'GameAnalytics 2024'},
    },
    'web3-crypto-apps': {
        'banner':       {'low': 0.80, 'high': 3.00, 'source': 'Reddit/AdMob 2024 (volatile)'},
        'interstitial': {'low': 4.00, 'high': 15.00, 'source': 'Reddit r/AdMob'},
        'rewarded':     {'low': 8.00, 'high': 25.00, 'source': 'Reddit r/AdMob'},
        'native':       {'low': 2.00, 'high': 8.00, 'source': 'Reddit'},
        'app-open':     {'low': 1.00, 'high': 5.00, 'source': 'Reddit'},
        'iap_arpdau':   {'low': 0.10, 'high': 1.50, 'source': 'High-LTV but small audience'},
        'notes': 'Many regions restrict crypto ads. Eligibility check required per country.',
    },

    # ===== MID-eCPM (PHOTO/VIDEO / SOCIAL / HEALTH) =====
    'photo-video-apps': {
        'banner':       {'low': 0.80, 'high': 2.50, 'source': 'AppLovin 2024'},
        'interstitial': {'low': 5.00, 'high': 12.00, 'source': 'AppLovin 2024'},
        'rewarded':     {'low': 8.00, 'high': 22.00, 'source': 'AppsFlyer 2024 (filter unlocks)'},
        'native':       {'low': 2.00, 'high': 7.00, 'source': 'AppLovin 2024'},
        'app-open':     {'low': 1.00, 'high': 4.00, 'source': 'AppLovin 2024'},
        'iap_arpdau':   {'low': 0.03, 'high': 0.25, 'source': 'GameAnalytics 2024'},
    },
    'social-dating-apps': {
        'banner':       {'low': 0.80, 'high': 3.00, 'source': 'AdMob 2024'},
        'interstitial': {'low': 5.00, 'high': 15.00, 'source': 'AdMob 2024'},
        'rewarded':     {'low': 10.00, 'high': 30.00, 'source': 'Sensor Tower preview 2024'},
        'native':       {'low': 2.00, 'high': 8.00, 'source': 'AdMob 2024'},
        'app-open':     {'low': 1.50, 'high': 5.00, 'source': 'AdMob 2024'},
        'iap_arpdau':   {'low': 0.10, 'high': 1.20, 'source': 'Dating sub LTV high'},
    },
    'health-fitness-apps': {
        'banner':       {'low': 0.70, 'high': 2.20, 'source': 'AppLovin 2024'},
        'interstitial': {'low': 4.00, 'high': 10.00, 'source': 'AppLovin 2024'},
        'rewarded':     {'low': 7.00, 'high': 18.00, 'source': 'AppsFlyer 2024'},
        'native':       {'low': 1.80, 'high': 6.00, 'source': 'AppLovin 2024'},
        'app-open':     {'low': 1.00, 'high': 3.50, 'source': 'AppLovin 2024'},
        'iap_arpdau':   {'low': 0.05, 'high': 0.50, 'source': 'GameAnalytics 2024'},
    },
    'productivity-apps': {
        'banner':       {'low': 0.50, 'high': 2.00, 'source': 'AdMob 2024'},
        'interstitial': {'low': 3.00, 'high': 10.00, 'source': 'AdMob 2024'},
        'rewarded':     {'low': 5.00, 'high': 18.00, 'source': 'AdMob 2024'},
        'native':       {'low': 1.50, 'high': 5.00, 'source': 'AdMob 2024'},
        'app-open':     {'low': 0.80, 'high': 3.00, 'source': 'AdMob 2024'},
        'iap_arpdau':   {'low': 0.02, 'high': 0.30, 'source': 'GameAnalytics 2024'},
    },
    'utility-apps': {
        'banner':       {'low': 0.50, 'high': 2.00, 'source': 'AdMob 2024'},
        'interstitial': {'low': 3.00, 'high': 10.00, 'source': 'AdMob 2024'},
        'rewarded':     {'low': 5.00, 'high': 18.00, 'source': 'AppsFlyer 2024'},
        'native':       {'low': 1.50, 'high': 5.00, 'source': 'AdMob 2024'},
        'app-open':     {'low': 0.80, 'high': 3.00, 'source': 'AdMob 2024'},
        'iap_arpdau':   {'low': 0.01, 'high': 0.15, 'source': 'GameAnalytics 2024'},
    },

    # ===== GAMING (high rewarded eCPM, lower banner) =====
    'rpg-strategy-games': {
        'banner':       {'low': 0.50, 'high': 2.00, 'source': 'ironSource 2024'},
        'interstitial': {'low': 5.00, 'high': 12.00, 'source': 'ironSource 2024'},
        'rewarded':     {'low': 10.00, 'high': 30.00, 'source': 'ironSource 2024 (top game eCPM)'},
        'native':       {'low': 1.50, 'high': 5.00, 'source': 'ironSource 2024'},
        'app-open':     {'low': 1.50, 'high': 5.00, 'source': 'ironSource 2024'},
        'iap_arpdau':   {'low': 0.20, 'high': 3.00, 'source': 'GameAnalytics 2024 RPG/strategy median'},
    },
    'casual-games': {
        'banner':       {'low': 0.40, 'high': 1.50, 'source': 'AppLovin 2024'},
        'interstitial': {'low': 4.00, 'high': 8.00, 'source': 'AppLovin 2024'},
        'rewarded':     {'low': 8.00, 'high': 20.00, 'source': 'AppLovin 2024'},
        'native':       {'low': 1.00, 'high': 4.00, 'source': 'AppLovin 2024'},
        'app-open':     {'low': 1.00, 'high': 3.50, 'source': 'AppLovin 2024'},
        'iap_arpdau':   {'low': 0.05, 'high': 0.50, 'source': 'GameAnalytics 2024 casual median'},
    },
    'word-trivia-games': {
        'banner':       {'low': 0.40, 'high': 1.50, 'source': 'ironSource 2024'},
        'interstitial': {'low': 4.00, 'high': 10.00, 'source': 'ironSource 2024'},
        'rewarded':     {'low': 8.00, 'high': 18.00, 'source': 'ironSource 2024'},
        'native':       {'low': 1.00, 'high': 4.00, 'source': 'ironSource 2024'},
        'app-open':     {'low': 1.00, 'high': 3.50, 'source': 'ironSource 2024'},
        'iap_arpdau':   {'low': 0.10, 'high': 1.00, 'source': 'GameAnalytics 2024'},
    },
    'simulation-games': {
        'banner':       {'low': 0.40, 'high': 1.80, 'source': 'AppLovin 2024'},
        'interstitial': {'low': 4.00, 'high': 9.00, 'source': 'AppLovin 2024'},
        'rewarded':     {'low': 8.00, 'high': 22.00, 'source': 'AppLovin 2024'},
        'native':       {'low': 1.00, 'high': 4.00, 'source': 'AppLovin 2024'},
        'app-open':     {'low': 1.00, 'high': 3.50, 'source': 'AppLovin 2024'},
        'iap_arpdau':   {'low': 0.10, 'high': 1.50, 'source': 'GameAnalytics 2024 sim/idle'},
    },

    # ===== LOWER-eCPM (KIDS/EDUCATION constrained by COPPA, ENTERTAINMENT/NEWS) =====
    'lifestyle-apps': {
        'banner':       {'low': 0.50, 'high': 1.80, 'source': 'AppLovin 2024'},
        'interstitial': {'low': 3.00, 'high': 8.00, 'source': 'AppLovin 2024'},
        'rewarded':     {'low': 5.00, 'high': 15.00, 'source': 'AppLovin 2024'},
        'native':       {'low': 1.20, 'high': 4.00, 'source': 'AppLovin 2024'},
        'app-open':     {'low': 0.80, 'high': 3.00, 'source': 'AppLovin 2024'},
        'iap_arpdau':   {'low': 0.02, 'high': 0.40, 'source': 'GameAnalytics 2024'},
    },
    'news-magazines': {
        'banner':       {'low': 0.40, 'high': 1.50, 'source': 'AdMob 2024'},
        'interstitial': {'low': 3.00, 'high': 8.00, 'source': 'AdMob 2024'},
        'rewarded':     {'low': 5.00, 'high': 15.00, 'source': 'AdMob 2024'},
        'native':       {'low': 1.50, 'high': 5.00, 'source': 'AdMob 2024 (native fits content)'},
        'app-open':     {'low': 0.60, 'high': 2.50, 'source': 'AdMob 2024'},
        'iap_arpdau':   {'low': 0.01, 'high': 0.20, 'source': 'Subscription model dominates'},
    },
    'kids-education-apps': {
        'banner':       {'low': 0.40, 'high': 1.50, 'source': 'AdMob 2024 (COPPA-limited)'},
        'interstitial': {'low': 2.00, 'high': 6.00, 'source': 'AdMob 2024'},
        'rewarded':     {'low': 5.00, 'high': 12.00, 'source': 'AdMob 2024'},
        'native':       {'low': 0.80, 'high': 3.00, 'source': 'AdMob 2024'},
        'app-open':     {'low': 0.50, 'high': 2.00, 'source': 'AdMob 2024'},
        'iap_arpdau':   {'low': 0.05, 'high': 0.80, 'source': 'GameAnalytics 2024 (subscription parents)'},
        'notes': 'COPPA/Apple Kids Category bans behavioral targeting — eCPM ~50% of equivalent adult app.',
    },
}

# Country tier multipliers vs US baseline (US = 1.0).
# Apply to eCPM lows/highs to estimate eCPM in target country.
TIER_MULTIPLIERS = {
    # US baseline
    'US': 1.00,

    # Tier S+ (RPM peers or above US)
    'CH': 1.10, 'NO': 1.00, 'AU': 1.00, 'NZ': 0.90, 'CA': 0.95, 'SG': 0.80,

    # Tier S (high but below US)
    'UK': 0.85, 'GB': 0.85, 'DK': 0.90, 'SE': 0.85, 'LU': 0.85, 'IL': 0.70,
    'JP': 0.70, 'KR': 0.65, 'HK': 0.60, 'IE': 0.70,

    # Tier 1 (Western Europe)
    'DE': 0.70, 'FR': 0.60, 'NL': 0.70, 'FI': 0.70, 'AT': 0.70, 'BE': 0.60,
    'CH-DE': 1.10,  # Swiss German alias

    # Tier 2 (Southern + Eastern Europe + Latin America premium)
    'ES': 0.40, 'IT': 0.40, 'PT': 0.35, 'PL': 0.25, 'CZ': 0.30, 'GR': 0.25,
    'MX': 0.20, 'BR': 0.18, 'AR': 0.12, 'CL': 0.18, 'CO': 0.15,

    # Tier 3 (emerging Asia + Eastern Europe + MENA premium)
    'TR': 0.15, 'RU': 0.15, 'MY': 0.20, 'TH': 0.15, 'PH': 0.10, 'ID': 0.08,
    'VN': 0.08, 'AE': 0.50, 'SA': 0.40, 'QA': 0.50, 'KW': 0.45,

    # Tier 4 (low-RPM — banned for revenue-optimization per Teamz strategy)
    'IN': 0.08, 'BD': 0.05, 'PK': 0.06, 'NG': 0.05, 'EG': 0.07, 'KE': 0.06,
    'LK': 0.06, 'MA': 0.10, 'DZ': 0.08,

    # Default catch-all
    'OTHER': 0.30,
}

# Country group names for reporting
TIER_LABELS = {
    'S+': ['US', 'CH', 'NO', 'AU', 'NZ', 'CA', 'SG'],
    'S':  ['UK', 'GB', 'DK', 'SE', 'LU', 'IL', 'JP', 'KR', 'HK', 'IE'],
    '1':  ['DE', 'FR', 'NL', 'FI', 'AT', 'BE'],
    '2':  ['ES', 'IT', 'PT', 'PL', 'CZ', 'GR', 'MX', 'BR', 'AR', 'CL', 'CO'],
    '3':  ['TR', 'RU', 'MY', 'TH', 'PH', 'ID', 'VN', 'AE', 'SA', 'QA', 'KW'],
    '4':  ['IN', 'BD', 'PK', 'NG', 'EG', 'KE', 'LK', 'MA', 'DZ'],
}

CAVEATS = [
    'eCPM is what publisher actually receives per 1000 impressions, AFTER mediation losses.',
    'Real eCPM varies ±50% from these benchmarks depending on app age, fill rate, mediation stack.',
    'Rewarded video has highest eCPM but limited slots/user — total revenue depends on placements × engagement.',
    'IAP ARPDAU figures are MEDIAN — top quartile apps earn 5-10x median.',
    'Tier-4 countries (BD/IN/PK) are revenue-banned per Teamz strategy — listed for context only.',
    'Crypto/web3 ads are restricted in EU/UK/many APAC markets — verify eligibility per country before assuming.',
    'Kids/Education apps are COPPA-limited (no behavioral targeting) → eCPM ~50% of equivalent adult-targeted app.',
    'New AdMob accounts (<30 days, <10K impressions) earn 30-60% below mature account benchmarks.',
]

SOURCES = [
    'AdMob official benchmarks (Google publisher help, 2024)',
    'AppLovin Mobile Ad Benchmarks Report 2024',
    'ironSource State of Mobile Gaming 2024',
    'AppsFlyer Performance Index 2024',
    'GameAnalytics Mobile Game Industry Report 2024',
    'Sensor Tower / data.ai free preview tier reports 2024',
    'Reddit r/AdMob + r/iOSProgramming + r/androiddev community averages',
    'Statista Mobile Ad CPM by Country 2024',
]


def country_tier(cc):
    cc = cc.upper()
    for tier, codes in TIER_LABELS.items():
        if cc in codes:
            return tier
    return 'OTHER'


def estimate_country_ecpm(category, country, ad_format='rewarded'):
    """Return (low, high) eCPM for category × country × format."""
    if category not in BENCHMARKS:
        return None
    cat = BENCHMARKS[category]
    if ad_format not in cat:
        return None
    multiplier = TIER_MULTIPLIERS.get(country.upper(), TIER_MULTIPLIERS['OTHER'])
    base = cat[ad_format]
    return {
        'category': category,
        'country': country.upper(),
        'tier': country_tier(country),
        'format': ad_format,
        'multiplier': multiplier,
        'low': round(base['low'] * multiplier, 2),
        'high': round(base['high'] * multiplier, 2),
        'us_baseline': {'low': base['low'], 'high': base['high']},
        'source': base['source'],
    }


def write():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'last_updated': LAST_UPDATED,
        'sources': SOURCES,
        'units': 'USD eCPM (per 1000 impressions). iap_arpdau is per Daily Active User per day.',
        'caveats': CAVEATS,
        'benchmarks': BENCHMARKS,
        'tier_multipliers': TIER_MULTIPLIERS,
        'tier_labels': TIER_LABELS,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'Wrote {OUT.relative_to(ROOT)}')
    print(f'  {len(BENCHMARKS)} app categories')
    print(f'  {len(TIER_MULTIPLIERS)} country multipliers')
    print(f'  Last updated: {LAST_UPDATED}')


def query(category=None, country=None, top_n=None, ad_format=None):
    rows = []
    for cat, formats in BENCHMARKS.items():
        if category and category.lower() not in cat.lower():
            continue
        for fmt, vals in formats.items():
            if fmt in ('notes',):
                continue
            if ad_format and fmt != ad_format.lower():
                continue
            countries = [country.upper()] if country else ['US']
            for cc in countries:
                est = estimate_country_ecpm(cat, cc, fmt)
                if est is None:
                    continue
                rows.append(est)

    rows.sort(key=lambda r: -((r['low'] + r['high']) / 2))
    if top_n:
        rows = rows[:top_n]

    print(f'{"CATEGORY":<22} {"CTRY":<6} {"FORMAT":<13} {"LOW":>7} {"HIGH":>7}  TIER  SOURCE')
    print('-' * 100)
    for r in rows:
        src = r['source'][:30]
        print(f'{r["category"]:<22} {r["country"]:<6} {r["format"]:<13} ${r["low"]:>6.2f} ${r["high"]:>6.2f}  {r["tier"]:<5} {src}')


def revenue_projection(category, country, daus, format_mix=None):
    """Rough monthly revenue projection.
    format_mix: {'banner': impressions_per_dau, 'interstitial': N, 'rewarded': N}
    Default mix: 30 banner + 5 interstitial + 2 rewarded per DAU per day.
    """
    if format_mix is None:
        format_mix = {'banner': 30, 'interstitial': 5, 'rewarded': 2}
    if category not in BENCHMARKS:
        print(f'ERROR: category "{category}" not found. Options: {", ".join(BENCHMARKS.keys())}')
        return

    print(f'\n=== Revenue Projection: {category} / {country.upper()} / {daus} DAUs ===')
    print(f'(30 days, format mix per DAU per day: {format_mix})')
    total_low_month = 0.0
    total_high_month = 0.0
    for fmt, imp_per_dau in format_mix.items():
        est = estimate_country_ecpm(category, country, fmt)
        if est is None:
            continue
        # impressions per month = DAUs × imp_per_dau × 30 days
        impressions = daus * imp_per_dau * 30
        rev_low = (impressions / 1000) * est['low']
        rev_high = (impressions / 1000) * est['high']
        total_low_month += rev_low
        total_high_month += rev_high
        print(f'  {fmt:<13} {impressions:>10,} impr/mo × ${est["low"]:.2f}-${est["high"]:.2f} eCPM  =  ${rev_low:>8.0f}-${rev_high:>8.0f}/mo')

    # IAP rough
    iap_arpdau = BENCHMARKS[category].get('iap_arpdau')
    if iap_arpdau:
        mult = TIER_MULTIPLIERS.get(country.upper(), TIER_MULTIPLIERS['OTHER'])
        iap_low = daus * 30 * iap_arpdau['low'] * mult
        iap_high = daus * 30 * iap_arpdau['high'] * mult
        total_low_month += iap_low
        total_high_month += iap_high
        print(f'  iap_arpdau    {daus} DAUs × 30 days × ${iap_arpdau["low"]:.2f}-${iap_arpdau["high"]:.2f}   =  ${iap_low:>8.0f}-${iap_high:>8.0f}/mo')

    print('-' * 80)
    print(f'  TOTAL est monthly revenue: ${total_low_month:>10,.0f} - ${total_high_month:>10,.0f}')
    print(f'  Per DAU per month: ${total_low_month/daus:.2f} - ${total_high_month/daus:.2f}')
    print(f'\n  Caveats: median app earns near LOW. Top 25% earn near HIGH. Top 1% earn 3-5× HIGH.')


def validate_against_crowd():
    """Cross-check static benchmarks vs reddit-aso-rpm-crowd.json (if exists)."""
    if not CROWD.exists():
        print(f'No crowd data found. Run: python3 build-reddit-rpm-tracker.py --niche aso')
        return
    crowd = json.loads(CROWD.read_text())
    agg = crowd.get('aggregated', {})
    if not agg:
        print('Crowd data has no aggregated entries (n<3 per niche). Run with full --niche aso.')
        return

    # Map crowd niches → our category names
    NICHE_MAP = {
        'casual-games': 'casual-games',
        'word-trivia-games': 'word-trivia-games',
        'rpg-strategy-games': 'rpg-strategy-games',
        'simulation-games': 'simulation-games',
        'productivity-apps': 'productivity-apps',
        'finance-apps': 'finance-apps',
        'health-fitness-apps': 'health-fitness-apps',
        'photo-video-apps': 'photo-video-apps',
        'social-dating-apps': 'social-dating-apps',
        'utility-apps': 'utility-apps',
        'kids-education-apps': 'kids-education-apps',
        'shopping-apps': 'shopping-apps',
        'news-magazines': 'news-magazines',
        'lifestyle-apps': 'lifestyle-apps',
        'web3-crypto-apps': 'web3-crypto-apps',
    }

    print(f'=== Crowd validation (last refresh: {crowd.get("last_refreshed", "?")}) ===\n')
    print(f'{"CATEGORY":<22} {"OUR_RANGE":>16} {"CROWD_MED":>11} {"VERDICT":<25}')
    print('-' * 80)

    for crowd_niche, our_cat in NICHE_MAP.items():
        if crowd_niche not in agg or our_cat not in BENCHMARKS:
            continue
        crowd_med = agg[crowd_niche]['median']
        # Use rewarded as the comparable signal — most often what devs cite as "my eCPM"
        rewarded = BENCHMARKS[our_cat].get('rewarded')
        if not rewarded:
            continue
        our_low, our_high = rewarded['low'], rewarded['high']
        our_range = f'${our_low:.0f}-${our_high:.0f}'

        verdict = 'OK (in range)'
        if crowd_med < our_low * 0.5:
            verdict = 'WARN: crowd <50% our LOW (banner/interstitial-heavy?)'
        elif crowd_med > our_high * 1.5:
            verdict = 'WARN: crowd >150% our HIGH (top-percentile?)'

        print(f'{our_cat:<22} {our_range:>16} ${crowd_med:>9.2f}  {verdict:<25}')


def main():
    args = sys.argv[1:]

    if '--validate' in args:
        validate_against_crowd()
        return

    if '--revenue-projection' in args:
        category = args[args.index('--category') + 1] if '--category' in args else None
        country = args[args.index('--country') + 1] if '--country' in args else 'US'
        daus = int(args[args.index('--daus') + 1]) if '--daus' in args else 1000
        if not category:
            print('ERROR: --revenue-projection requires --category <name>')
            print(f'Options: {", ".join(BENCHMARKS.keys())}')
            return
        revenue_projection(category, country, daus)
        return

    if '--query' in args or '--country' in args or '--top' in args or '--format' in args:
        category = args[args.index('--query') + 1] if '--query' in args else None
        country = args[args.index('--country') + 1] if '--country' in args else None
        top_n = int(args[args.index('--top') + 1]) if '--top' in args else None
        ad_format = args[args.index('--format') + 1] if '--format' in args else None
        query(category=category, country=country, top_n=top_n, ad_format=ad_format)
    else:
        write()


if __name__ == '__main__':
    main()
