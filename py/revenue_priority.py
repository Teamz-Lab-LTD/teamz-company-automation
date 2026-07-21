"""
Shared: turn a page (slug + hub + traffic) into an expected-$/mo number, so the nightly
enhances the highest-EARNING winnable page first — not just the highest-traffic one.

NON-REDUNDANT: this does NOT re-implement RPM math. It reuses the existing
`build-revenue-velocity-score.py` scorer (get_rpm + score_idea, niche x country -> RPM x
winnability x ...). The only thing missing there was a map from our 137 hubs/slugs to its
RPM niches + country — that's all this file adds, plus a thin `expected_dollars()` wrapper.

  from revenue_priority import expected_dollars, niche_for
  usd = expected_dollars(slug="us/paycheck-calculator", hub="us", title="...",
                         visitors_mo=4000, serp_winnability=7)
"""
import os, re, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_scorer():
    p = os.path.join(HERE, "build-revenue-velocity-score.py")
    spec = importlib.util.spec_from_file_location("rvs", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_RVS = None
def _scorer():
    global _RVS
    if _RVS is None:
        _RVS = _load_scorer()
    return _RVS


# ---- hub -> RPM niche (topic hubs map directly to the rpm-benchmarks.json niches) ----
HUB_NICHE = {
    'finance': 'finance', 'crypto': 'finance',
    'tax': 'tax',
    'insurance': 'insurance',
    'mortgage': 'mortgage', 'housing': 'real-estate', 'real-estate': 'real-estate',
    'legal': 'legal',
    'b2b-leadgen': 'b2b-leadgen', 'compliance': 'b2b-leadgen', 'seo': 'business-saas',
    'freelance': 'business-saas', 'amazon': 'business-saas', 'creator': 'business-saas',
    'work': 'career-jobs', 'career': 'career-jobs', 'military': 'career-jobs',
    'software': 'technology', 'dev': 'technology', 'ai': 'technology', 'apple': 'technology',
    'mobile': 'technology', 'gadgets': 'technology', 'accessibility': 'technology', 'tools': 'productivity',
    'text': 'productivity',
    'design': 'creative-art', 'uidesign': 'creative-art', 'image': 'creative-art',
    'video': 'creative-art', 'music': 'creative-art', '3d': 'creative-art',
    'candle-making': 'creative-art', 'knitting': 'creative-art',
    'health': 'health-general', 'eldercare': 'health-general', 'diagnostic': 'health-general',
    'au-care': 'health-general', 'uk-care': 'health-general', 'ie-care': 'health-general',
    'nz-care': 'health-general', 'skincare': 'health-supplements', 'longevity': 'longevity',
    'grooming': 'lifestyle', 'pets': 'lifestyle', 'weather': 'lifestyle', 'shopping': 'lifestyle',
    'auto': 'auto',
    'kids': 'parenting-family', 'student': 'education', 'math': 'education', 'physics': 'education',
    'research': 'education', 'prep': 'education',
    'games': 'gaming', 'gaming': 'gaming', 'football': 'entertainment', 'cricket': 'entertainment',
    'sports': 'fitness-workout', 'cycling': 'fitness-workout', 'outdoor': 'travel',
    'food': 'food-recipes', 'restaurant': 'food-recipes', 'coffee': 'food-recipes',
    'tea': 'food-recipes', 'baking': 'food-recipes',
    'travel': 'travel', 'garden': 'home-improvement', 'safety': 'home-improvement',
    'pest': 'home-improvement',
}

# keyword inference for country/generic hubs (us=931 mixed tools), checked in order
NICHE_KEYWORDS = [
    ('mortgage', ['mortgage', 'refinance', 'home loan', 'heloc']),
    ('tax', ['tax', 'irs', 'vat', 'gst', 'hmrc', 'deduction', 'w-4', 'w4', 'tariff']),
    ('insurance', ['insurance', 'premium', 'deductible', 'medicare', 'medigap', 'life cover']),
    ('legal', ['alimony', 'child support', 'custody', 'settlement', 'lawsuit', 'probate',
               'court', 'divorce', 'attorney', 'compensation']),
    ('finance', ['loan', 'apr', 'interest', 'debt', 'retirement', '401k', 'ira', 'pension',
                 'salary', 'paycheck', 'wage', 'income', 'savings', 'invest', 'annuity',
                 'dividend', 'roi', 'cagr', 'compound', 'budget', 'gratuity', 'superannuation',
                 'cpf', 'provident', 'credit']),
    ('real-estate', ['rent', 'property', 'stamp duty', 'rental yield', 'tenant', 'landlord',
                     'hdb', 'bto', 'land', 'lease']),
    ('auto', ['car', 'vehicle', 'auto', 'ev ', 'mileage', 'fuel']),
    ('health-general', ['bmi', 'calorie', 'pregnancy', 'hearing', 'health', 'dose', 'bmr',
                        'body fat', 'ovulation', 'due date', 'blood']),
    ('education', ['gpa', 'grade', 'exam', 'study', 'quiz', 'school', 'student', 'acft']),
    ('entertainment', ['dice', 'coin flip', 'random', 'wheel', 'meme', 'birthday', 'wish',
                       'name generator', 'spinner']),
    ('food-recipes', ['recipe', 'calorie', 'baking', 'cook', 'oven']),
]

# hub -> RPM-table country code (the table uses US/UK/CA/AU/SG/JP/DE/EU)
HUB_COUNTRY = {
    'us': 'US', 'uk': 'UK', 'gb': 'UK', 'ca': 'CA', 'au': 'AU', 'sg': 'SG', 'jp': 'JP',
    'de': 'DE', 'at': 'DE', 'ch': 'CH', 'no': 'NO', 'nz': 'AU', 'ie': 'UK', 'in': 'IN',
    'bd': 'BD', 'pk': 'PK', 'ng': 'NG', 'ph': 'PH', 'id': 'ID', 'eu': 'EU',
    'au-care': 'AU', 'uk-care': 'UK', 'ie-care': 'UK', 'nz-care': 'AU',
}


def niche_for(hub, slug="", title=""):
    h = (hub or "").lower()
    if h in HUB_NICHE:
        return HUB_NICHE[h]
    text = f"{slug} {title}".lower().replace("-", " ")
    for niche, kws in NICHE_KEYWORDS:
        if any(k in text for k in kws):
            return niche
    return "productivity"   # safe mid-low default


def country_for(hub, slug=""):
    h = (hub or "").lower()
    if h in HUB_COUNTRY:
        return HUB_COUNTRY[h]
    first = (slug or "").strip("/").split("/")[0].lower()
    return HUB_COUNTRY.get(first, "US")


def expected_dollars(slug, hub="", title="", visitors_mo=0, serp_winnability=5,
                     time_to_rank_months=2, niche=None):
    """Expected $/mo from this page, via the existing revenue-velocity scorer.
    serp_winnability: 1-10 (10=easy win, 1=walled by NerdWallet/Wikipedia). Default 5
    until a real SERP-difficulty signal is supplied (see serp_difficulty.py)."""
    rvs = _scorer()
    rpm_db = rvs.load_rpm()
    reddit_db = rvs.load_reddit_rpm()
    idea = {
        "slug": slug,
        # `niche` lets a caller that already knows the subject state it outright. Added because
        # hub does double duty: country_for() needs 'us'/'bd' there, which means niche_for() falls
        # through to keyword-matching the title — and a caller passing a country was silently
        # getting the 'productivity' default ($6.5) for EVERY item, flattening the whole RPM
        # weighting to a constant. Default None preserves existing behaviour exactly.
        "niche": niche or niche_for(hub, slug, title),
        "country": country_for(hub, slug),
        "est_visitors_mo3": visitors_mo,
        "time_to_rank_months": time_to_rank_months,
        "serp_winnability": serp_winnability,
        "retention_score": 4,
    }
    r = rvs.score_idea(idea, rpm_db, reddit_db)
    return {
        "expected_dollars_mo": r["expected_dollars_mo3"],
        "niche": r["niche"], "country": r["country"],
        "rpm_mid": r["rpm_used_mid"], "rpm_source": r["rpm_source"],
    }
