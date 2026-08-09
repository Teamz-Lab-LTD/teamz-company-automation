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

--- 2026-08-10 fix (owner-reported, verified via money-snapshots/latest.json) ----------------
Found 702 of 2431 tools.json pages (29%) silently landing on niche="productivity" ($6.5 RPM,
the lowest-but-one benchmark) — including pages plainly under /finance/, /tax/, /legal/, and
every non-English country hub (ch/se/fr/de/...). Two independent bugs, both now fixed here:

1. BOTH call sites (build-money-tracker.py, build-enhance-queue.py) derived `hub` by
   `slug.split("/")[0]` — but tools.json's `slug` field almost never contains a "/" (it's the
   tool's own slug, e.g. "yield-to-maturity-calculator"), so that split returned the WHOLE
   slug as "hub", which obviously never matches HUB_NICHE, so every one of these pages fell
   through to keyword-matching and then the productivity default — even though tools.json
   already has a correct `"hub": "finance"` field sitting right next to the slug, unused.
   Fix: slug_to_hub() below reads tools.json once and gives callers the REAL hub. Callers
   updated to use it instead of splitting the slug.
2. Country hubs (ch/se/fr/de/...) correctly have no topic niche of their own — hub="ch" isn't
   supposed to hit HUB_NICHE. But the keyword-matching fallback (NICHE_KEYWORDS) was
   English-only, so German/French/Swedish titles ("AHV Beiträge Selbständige", "Allocations
   Familiales", "Återbäring Skatt") never matched anything and fell through to productivity
   too. Fix: MULTILINGUAL_KEYWORDS below adds the 8 languages with the most tools.json
   entries (de/fr/sv/da/nl/no/fi/pt — 184+128+76+66+56+39+32+30 = 611 pages). Smaller
   languages (ja/bn/ar/ko/it/es/...) still fall through to productivity until someone adds
   their keyword rows here — that's a known, bounded gap, not silently "solved".

If you're an LLM picking this up later: before "fixing" niche_for() again, re-run the same
verification query used to catch this (count niche=="productivity" in money-snapshots/
latest.json, spot-check whether the URL's real topic disagrees) — don't trust that this
comment is still accurate; tools.json grows nightly.
-----------------------------------------------------------------------------------------------
"""
import os, re, json, importlib.util

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

# Non-English keyword rows, same (niche, [keywords]) shape as NICHE_KEYWORDS, for country hubs
# whose tools are titled in the local language (see 2026-08-10 note above). Covers the 8
# languages with the most tools.json entries. Terms are the local calculator-site vocabulary
# for the niches that actually carry high RPM (finance/tax/insurance/legal/real-estate) —
# low-RPM niches weren't worth translating, a missed match there just stays productivity,
# same as today.
MULTILINGUAL_KEYWORDS = [
    ('tax', ['steuer', 'impot', 'impôt', 'skatt', 'skat', 'belasting', 'vero', 'imposto',
             'aterbaring', 'återbäring']),
    ('insurance', ['versicherung', 'krankenkasse', 'praemie', 'prämie', 'assurance',
                   'forsakring', 'försäkring', 'forsikring', 'verzekering', 'vakuutus',
                   'seguro']),
    ('legal', ['scheidung', 'unterhalt', 'divorce', 'pension alimentaire', 'skilsmässa',
               'skilsmisse', 'echtscheiding']),
    ('mortgage', ['hypothek', 'hypotheque', 'hypothèque', 'bolan', 'bolån', 'boliglan',
                  'boliglån', 'hypotheek', 'asuntolaina']),
    ('real-estate', ['miete', 'immobilie', 'loyer', 'immobilier', 'hyra', 'leje', 'huur',
                     'leie', 'vuokra']),
    ('finance', ['rente', 'altersvorsorge', 'gehalt', 'kredit', 'zins', 'ahv',
                 'retraite', 'salaire', 'pret', 'prêt', 'allocations familiales', 'allocations',
                 'pension', 'lon', 'lön', 'lan', 'lån',
                 'lonn', 'lønn',
                 'elake', 'eläke', 'palkka', 'laina',
                 'pensao', 'pensão', 'salario', 'salário', 'emprestimo', 'empréstimo']),
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
    for niche, kws in MULTILINGUAL_KEYWORDS:
        if any(k in text for k in kws):
            return niche
    return "productivity"   # safe mid-low default


def country_for(hub, slug=""):
    h = (hub or "").lower()
    if h in HUB_COUNTRY:
        return HUB_COUNTRY[h]
    first = (slug or "").strip("/").split("/")[0].lower()
    if first in HUB_COUNTRY:
        return HUB_COUNTRY[first]
    # 2026-08-10: was a blind "US" default here — 56 of ~70 country-hub folders (fr/se/dk/nl/
    # it/es/...) have no explicit entry above, so every one of them was priced as US traffic
    # (no tier bonus/discount at all) instead of its own market. get_rpm()'s
    # country_tier_multiplier() already knows real tiers for 30+ ISO codes (SE/CH/NO=1.5x,
    # DE/CA/JP=1.1x, FR/IT/ES=0.8x, BD/IN/PK=0.05x) — it just never saw the real code. A
    # bare 2-letter hub IS almost always the ISO country code (ch/se/fr/de/...), so use it
    # directly; only truly unrecognised hubs (topic hubs like 'finance', 'tools') still fall
    # to the US anchor, same as before. Guard: 'ai' is a 2-letter TOPIC hub (AI tools), not
    # Anguilla — exclude anything already claimed by HUB_NICHE so it isn't mis-read as a
    # country code.
    if len(h) == 2 and h.isalpha() and h not in HUB_NICHE:
        return h.upper()
    return "US"


_SLUG_HUB_CACHE = {}   # host_root (str) -> {slug: hub}, built once per process


def slug_to_hub(host_root):
    """slug -> real hub, read straight from tools.json's own `hub` field.

    2026-08-10: added because both callers (build-money-tracker.py, build-enhance-queue.py)
    were computing `hub = slug.split("/")[0]` — a guess that's wrong whenever slug has no "/"
    (the normal case; tools.json's slug is just the tool's own name, e.g.
    "yield-to-maturity-calculator", NOT "finance/yield-to-maturity-calculator"). tools.json
    already carries the correct hub next to every slug — this just reads it instead of
    re-deriving it. Falls back to the old split-guess only for a slug that isn't found (should
    not happen for anything that came out of tools.json in the first place)."""
    key = str(host_root)
    if key not in _SLUG_HUB_CACHE:
        m = {}
        try:
            path = os.path.join(str(host_root), "tools.json")
            with open(path) as f:
                d = json.load(f)
            for t in d.get("tools", []):
                s = (t.get("slug") or "").strip("/")
                h = t.get("hub")
                if s and h:
                    m[s] = h
        except (OSError, ValueError) as e:
            print(f"[revenue_priority] slug_to_hub: could not read tools.json ({e}) — "
                  f"falling back to slug-split hub guessing for this run")
        _SLUG_HUB_CACHE[key] = m
    return _SLUG_HUB_CACHE[key]


def hub_for(slug, host_root):
    """Real hub for one slug, or the old split-guess if tools.json didn't have it."""
    m = slug_to_hub(host_root)
    s = (slug or "").strip("/")
    return m.get(s) or s.split("/")[0]


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
