#!/usr/bin/env python3
"""
build-revenue-velocity-score.py — Composite "expected $/mo by month 3" scorer.

Replaces vague "high RPM" / "low competition" rankings with ONE actionable
number: estimated dollars in pocket by month 3 of launching this tool.

Formula:
  monthly_$ = visitors_mo3
              × (rpm_dollars / 1000)
              × bot_resistance_factor
              × programmatic_multiplier
              × multilang_multiplier
              × retention_multiplier
              × adsense_maturity_factor

Then ranks ideas. Used by /ideas as the primary sort key.

Inputs: a JSON list of candidate ideas, each with:
  {
    "slug": "/sg/cpf-self-employed/",
    "niche": "tax",                    # matches data/rpm-benchmarks.json
    "country": "SG",
    "est_visitors_mo3": 600,
    "time_to_rank_months": 2,           # 1=fast, 6=slow
    "serp_winnability": 8,              # 1-10 (10=blog post #1, 1=NerdWallet)
    "programmatic_variants": 0,         # 0 = none; e.g. 50 = ×50 states
    "multilang_variants": 0,            # 0=EN only, 2=+ES+PT, 4=+ES+PT+DE+FR
    "retention_score": 4,               # 1-10 (10=daily-trigger, 2=one-shot)
    "lead_gen": false,                  # if true, switch to per-lead pricing
    "named_affiliate_cpa": 0            # USD per conversion if affiliate
  }

Usage:
  python3 scripts/build-revenue-velocity-score.py --input ideas.json
  python3 scripts/build-revenue-velocity-score.py --demo   # show on sample ideas
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RPM_DB = ROOT / 'data' / 'rpm-benchmarks.json'
REDDIT_RPM_DB = ROOT / 'data' / 'reddit-rpm-crowd.json'

# Tuning constants — adjust as you learn from real data
ADSENSE_MATURITY_FACTOR = 0.55   # account is 25 days old; 0.5 at <60d, 1.0 at >90d
BOT_RESISTANCE_BASE = 0.74        # current 26% bot rate; 1 - bot_rate
DEFAULT_RETENTION_MULT = 1.0      # 1x for visitor-only; up to 1.6x for daily-return
DEFAULT_PROG_MULT_PER_VARIANT = 0.4  # each programmatic variant adds 40% of a base tool's traffic
DEFAULT_MULTILANG_MULT_PER_LANG = 0.5  # each new language adds 50% of base traffic


def load_rpm():
    if not RPM_DB.exists():
        print(f'ERROR: {RPM_DB} missing. Run build-public-rpm-benchmarks.py first.')
        sys.exit(1)
    return json.loads(RPM_DB.read_text())


def load_reddit_rpm():
    if not REDDIT_RPM_DB.exists():
        return None
    return json.loads(REDDIT_RPM_DB.read_text())


def get_rpm(rpm_db, reddit_db, niche, country):
    """Return (rpm_low, rpm_high, confidence, source). Prefers Reddit crowd if recent + count>=5."""
    static = None
    for n, entries in rpm_db['benchmarks'].items():
        if n.lower() == niche.lower():
            for e in entries:
                if e['country'].upper() == country.upper():
                    static = (e['low'], e['high'], 'medium', e['source'])
                    break
            if static:
                break
    # Try emerging-market multiplier
    if not static:
        for n, entries in rpm_db['benchmarks'].items():
            if n.lower() == niche.lower():
                # Use US as anchor + apply country tier multiplier
                us = next((e for e in entries if e['country'] == 'US'), None)
                if us:
                    mult = country_tier_multiplier(country)
                    static = (us['low'] * mult, us['high'] * mult,
                              'low', f'{us["source"]} × tier multiplier')
                    break
    if not static:
        static = (3.0, 8.0, 'guess', 'no benchmark — defaulting tier-C')

    # Override with Reddit crowd if it has >=5 mentions for this niche
    if reddit_db:
        agg = reddit_db.get('aggregated', {}).get(niche)
        if agg and agg.get('count', 0) >= 5:
            return (agg['p25'], agg['p75'], 'high',
                    f'Reddit crowd n={agg["count"]} (p25-p75)')

    return static


def country_tier_multiplier(country):
    tier_s = {'CH', 'NO', 'AU', 'DK', 'SE', 'NZ', 'IE', 'SG'}
    tier_a = {'CA', 'DE', 'AT', 'IL', 'BE', 'AE', 'NL', 'FI', 'JP'}
    tier_b = {'IT', 'ES', 'FR', 'PT', 'CZ', 'PL', 'KR', 'TW'}
    emerging = {'BD', 'IN', 'PK', 'NG', 'PH', 'ID', 'KE', 'GH', 'EG', 'MA'}
    c = country.upper()
    if c in tier_s: return 1.5
    if c in tier_a: return 1.1
    if c == 'US': return 1.0
    if c in tier_b: return 0.8
    if c in emerging: return 0.05
    return 0.6


def time_to_rank_factor(months):
    """Penalize slow-ranking ideas; we want money in 90 days."""
    if months <= 1: return 1.0
    if months <= 2: return 0.85
    if months <= 3: return 0.6
    if months <= 6: return 0.3
    return 0.1


def winnability_factor(serp_winnability):
    """1-10 scale; 10 = easy win, 1 = NerdWallet/Calculator.net entrenched."""
    return max(0.1, min(1.0, serp_winnability / 10))


def retention_multiplier(retention_score):
    """1-10 scale; 10 = daily biological trigger, 2 = one-shot calculator."""
    # 1.0 baseline; 1.6x at 10/10
    return 1.0 + (retention_score - 1) * (0.6 / 9)


def programmatic_multiplier(variants):
    if variants <= 0: return 1.0
    return 1.0 + (variants * DEFAULT_PROG_MULT_PER_VARIANT)


def multilang_multiplier(variants):
    if variants <= 0: return 1.0
    return 1.0 + (variants * DEFAULT_MULTILANG_MULT_PER_LANG)


def score_idea(idea, rpm_db, reddit_db):
    rpm_low, rpm_high, conf, source = get_rpm(
        rpm_db, reddit_db, idea['niche'], idea['country']
    )
    rpm_mid = (rpm_low + rpm_high) / 2

    visitors = idea.get('est_visitors_mo3', 0)
    bot_resistance = BOT_RESISTANCE_BASE  # could vary per-idea later
    ttr = time_to_rank_factor(idea.get('time_to_rank_months', 3))
    win = winnability_factor(idea.get('serp_winnability', 5))
    prog = programmatic_multiplier(idea.get('programmatic_variants', 0))
    ml = multilang_multiplier(idea.get('multilang_variants', 0))
    ret = retention_multiplier(idea.get('retention_score', 5))
    maturity = ADSENSE_MATURITY_FACTOR

    # Lead-gen overrides ad RPM math
    if idea.get('lead_gen'):
        cpa = idea.get('named_affiliate_cpa', 0)
        # assume 0.5% of visitors convert as lead
        leads = visitors * 0.005 * win * ret
        ad_revenue = leads * cpa
    else:
        ad_revenue = visitors * (rpm_mid / 1000) * bot_resistance * win * prog * ml * ret * maturity

    # Add affiliate revenue if both AdSense + named affiliate (display + click)
    if not idea.get('lead_gen') and idea.get('named_affiliate_cpa', 0) > 0:
        affiliate_rev = visitors * 0.003 * idea['named_affiliate_cpa']  # 0.3% conversion
        ad_revenue += affiliate_rev

    return {
        'slug': idea['slug'],
        'niche': idea['niche'],
        'country': idea['country'],
        'expected_dollars_mo3': round(ad_revenue, 2),
        'rpm_used_mid': round(rpm_mid, 2),
        'rpm_range': f'${rpm_low}-${rpm_high}',
        'rpm_confidence': conf,
        'rpm_source': source,
        'breakdown': {
            'visitors_mo3': visitors,
            'bot_resistance': bot_resistance,
            'time_to_rank_factor': ttr,
            'winnability_factor': win,
            'programmatic_mult': prog,
            'multilang_mult': ml,
            'retention_mult': ret,
            'adsense_maturity': maturity,
        }
    }


def demo():
    samples = [
        {'slug': '/us/tcja-bracket-2027/', 'niche': 'tax', 'country': 'US',
         'est_visitors_mo3': 200, 'time_to_rank_months': 5, 'serp_winnability': 4,
         'programmatic_variants': 51, 'multilang_variants': 0, 'retention_score': 3},
        {'slug': '/sg/cpf-self-employed/', 'niche': 'tax', 'country': 'SG',
         'est_visitors_mo3': 600, 'time_to_rank_months': 2, 'serp_winnability': 7,
         'programmatic_variants': 0, 'multilang_variants': 0, 'retention_score': 3},
        {'slug': '/jp/furusato-en/', 'niche': 'tax', 'country': 'JP',
         'est_visitors_mo3': 800, 'time_to_rank_months': 1, 'serp_winnability': 9,
         'programmatic_variants': 0, 'multilang_variants': 0, 'retention_score': 4},
        {'slug': '/longevity/phenoage/', 'niche': 'longevity', 'country': 'US',
         'est_visitors_mo3': 400, 'time_to_rank_months': 3, 'serp_winnability': 7,
         'programmatic_variants': 12, 'multilang_variants': 2, 'retention_score': 8},
        {'slug': '/eu/csrd/scope-1-2/', 'niche': 'b2b-leadgen', 'country': 'EU',
         'est_visitors_mo3': 100, 'time_to_rank_months': 4, 'serp_winnability': 8,
         'programmatic_variants': 27, 'multilang_variants': 3, 'retention_score': 5,
         'lead_gen': True, 'named_affiliate_cpa': 150},
    ]
    rpm_db = load_rpm()
    reddit_db = load_reddit_rpm()

    results = [score_idea(i, rpm_db, reddit_db) for i in samples]
    results.sort(key=lambda r: -r['expected_dollars_mo3'])

    print(f'{"SLUG":<35} {"COUNTRY":<8} ${"$/MO":>6} {"RPM":>14} {"CONF":>6}  SOURCE')
    print('-' * 100)
    for r in results:
        print(f'{r["slug"]:<35} {r["country"]:<8} ${r["expected_dollars_mo3"]:>6.2f} '
              f'{r["rpm_range"]:>14} {r["rpm_confidence"]:>6}  {r["rpm_source"][:40]}')


def main():
    args = sys.argv[1:]
    if '--demo' in args or not args:
        demo()
        return
    if '--input' in args:
        path = Path(args[args.index('--input') + 1])
        ideas = json.loads(path.read_text())
        rpm_db = load_rpm()
        reddit_db = load_reddit_rpm()
        results = [score_idea(i, rpm_db, reddit_db) for i in ideas]
        results.sort(key=lambda r: -r['expected_dollars_mo3'])
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
