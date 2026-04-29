# Teamz Lab Tools — Money Machine 2026-2027

> **Compiled:** 2026-04-13 · **Author:** deep-research synthesis (4 parallel research agents + SEO skills)
> **Inputs used:** Search Console, GA4, AdSense, Microsoft Clarity, PageSpeed, Rank Tracker, Backlinks Overview, Topic Cluster Report, Keyword Intel, Bing Volume, Product Hunt API, Google Trends, Google Autocomplete, build-keyword-volume, build-multilang, build-programmatic-seo, seo-geo + seo-programmatic skills, plus 30+ targeted WebSearches (real sources cited).
> **Status:** Replaces the earlier "GLP-1 + Perimenopause + Longevity" synthesis. Several earlier picks were **wrong** — corrected here based on SERP evidence.

> **2026-04-29 update:** Rising-tools auto-detection live. Phase 0 nightly auto-enhance locked. RPM-tier hub coverage data folded into TL;DR + PICK 6 (mortgage) added below.

---

## TL;DR — what to do this week

1. **Fix AdSense FIRST.** £0 on 4,592 weekly views is the bleeding wound. Likely "Ads Limited" status driven by 26% bot traffic. No new tool earns until this is fixed.
2. **Then build in this order** (90-day plan): TCJA-2027 cluster (US, time-locked spike Dec 2026–Apr 2027) → Mortgage hub fill (highest RPM $30-80 × empty hub, see PICK 6) → Singapore expansion (16→50 tools, validated by clone competitor) → Japan English expansion (8→30 tools, top organic + retention winner) → CSRD/SME carbon (EU, regulation-forced, B2B RPM) → Longevity / PhenoAge (evergreen, blue ocean).
3. **Stop building one-shot calculators.** Default to retention (biological/seasonal trigger) tools when possible. Programmatic SEO + multilang is the scale lever — already 5 templates exist, only 2% of tools use TeamzAI.

**Hub-coverage-gap context (2026-04-29 audit):** Site has 2,511 tools but Tier 1 RPM hubs are nearly empty. mortgage:1 ($30-80 RPM), finance:2 ($18-45), insurance:0 ($25-60), tax:0 ($20-50), real-estate:0 ($12-28). Total gap −577 tools = **$6-20K/mo potential**. PICKs 1, 4 already fill /tax/ and /eu/csrd/ hubs. PICK 6 (mortgage) added below to fill highest-RPM × biggest-gap hub. Country-RPM modifier: Tier S (CH/NO/AU/DK/SE/NZ/IE/SG) +30-80% over US. Banned: BD/IN/PK/NG/PH/ID (2-10% of US RPM, wasted cycle).

**Honest revenue projection (after AdSense fix + this plan):**
- Now: £0/mo (broken)
- Month 3 (AdSense fixed + 30 new tools): £400–1,200/mo
- Month 6 (200+ programmatic variants live + ES/PT translations): £1,500–4,500/mo
- Month 12 (full plan + earned backlinks + AI-search compounding): £4,000–12,000/mo

This is not a get-rich number. It's a real number, achievable, and it stacks year-on-year.

---

## 1. The £0 AdSense crisis (fix before anything else)

**Reality from `build-adsense.sh`:**
```
Earnings £0.00  Page Views 2,125  Ad Impressions 1,554  Clicks 16
Page RPM £0.00  CPC £0.00
```
Ads ARE rendering (1,554 impressions). Users ARE clicking (16 = 1% CTR, normal). Yet CPC = £0 every single day for 8 days. **This is not a code bug.** Code is correct: ads.txt OK, publisher ID matches in `shared/js/adsense.js`, headless/localhost guards in place.

**Most likely root cause: "Ads Limited" or invalid traffic filter.**
- Microsoft Clarity confirms **26% bot traffic** (32 of 123 sessions in 3 days)
- US traffic is 65% bots (28 of 43)
- `(direct)/Other device` = 100% bots, `(direct)/PC` = 44% bots
- AdSense filters revenue aggressively when bot rates exceed ~10%, especially in US

### Fix steps (do today, in this order)
1. AdSense console → **Policy center** + **Account status**. Screenshot any "Ads Limited" banner.
2. AdSense → **Payments** → verify address + tax info submitted.
3. Confirm `https://tool.teamzlab.com/ads.txt` is publicly accessible.
4. Extend `shared/js/adsense.js` skip rules to filter suspicious sessions: empty referrer + `(direct)` + Other device. Block bot UAs. Re-deploy.
5. If "Ads Limited" is on → wait 30 days, file reconsideration after bot traffic rate drops below 10%.

### Adjacent issues that are also burning money
- **Mobile PageSpeed:** Homepage mobile Perf 55, LCP 8.5s. `/jp/tedori-keisan/` (our #2 traffic page!) has **CLS 0.972** — catastrophic, capped ad viewability. Fix top 10 traffic pages = +25-40% RPM once AdSense pays.
- **Search Console token expired** — re-auth: `python3 build-search-console-auth.py`. We're flying blind on ranking drops without it.
- **Backlinks reality: 601 of 602 are self-distribution, 1 real directory link.** 36 of 39 high-DA directories (HN DA93, Trustpilot 93, Behance 93, Product Hunt 91, G2 92, SourceForge 92, Crunchbase 91, Capterra 91, Wellfound 90) **never submitted**.

**Revenue impact ranking of fixes:**
1. AdSense Policy Center check (30 min) → +£300-800/mo at current traffic
2. Bot-traffic filtering in adsense.js (2 hrs) → reduces invalid traffic flag
3. Mobile LCP fixes on top 10 pages (1 day) → +25-40% RPM
4. Re-auth GSC + populate `rank-watchlist.json` (1 hr) → restores anomaly alerts
5. Submit to top 5 DA directories (3 hrs) → real backlinks, domain trust

---

## 2. What the data actually shows (correcting first synthesis)

### Top 10 organic pages by traffic (last 7 days, GA4)
| Page | Views | Users | Avg Engaged Time |
|---|---|---|---|
| `/jp/tedori-keisan/` | 150 | 51 | **173s** |
| `/` (homepage) | 119 | 50 | 75s |
| `/3d/fluid-simulation/` | 74 | 13 | **253s** |
| `/tools/ai-audio-classifier/` | 73 | 15 | **473s** |
| `/diagnostic/` | 51 | 9 | 27s |
| `/diagnostic/encrypted-dns-checker/` | 50 | 21 | 16s |
| `/3d/text-generator/` | 46 | 12 | 121s |
| `/games/color-cards/` | 46 | 5 | 185s |
| `/diagnostic/dns-leak-test/` | 36 | 15 | 49s |
| `/3d/audio-visualizer/` | 29 | 5 | 409s |

### Three findings that change the strategy
1. **ChatGPT/Perplexity send MORE traffic than Google.** 155 sessions from `chatgpt.com + openai + perplexity + qwen` vs 84 from Google organic + 20 Bing. **AI search is already our #1 channel.** Double down on `seo-geo` skill (GEO optimization) and `llms.txt` curation.
2. **⚠️ CORRECTION (2026-04-13):** Earlier claim "Singapore = 57% of users" was based on raw GA4 country counts. Investigation revealed: ZERO `/sg/*` pages in top 20, 88% of all sessions are `(direct)/(none)`, 90% desktop. **The Singapore traffic is almost certainly bot/scraper traffic from Singapore datacenters (AWS/GCP APAC region), NOT real Singaporean users.** Real human traffic baseline: Google organic 73 + AI search 89 + social/refer ~20 ≈ **~180 real sessions/week** (not 1,988). Singapore hub is still a valid Build Soon based on validated keyword research (SmartCalculator.sg ranking proves real SG search market), but it's NOT a quick win from existing traffic — it's a 3-6 month organic ranking play.
3. **Localized EU finance ranks top-10 with zero effort.** Italian `codice-fiscale` pos 3, Dutch `box-3-belasting` pos 4-5, Danish `su-beregner` pos 13, Finnish `asuntolainlaskuri` pos 26, Belgian `erfbelasting` pos 28. English-only competitors ignore these markets — tier-1 RPM, near-zero competition.

### Hub size reality
| Hub | Tool count | Status |
|---|---|---|
| evergreen | 235 | bloated, diminishing returns |
| tools | 116 | bloated |
| health | 115 | fat — has GLP-1 family already |
| us | 105 | fat |
| dev | 75 | fat |
| de | 47 | mature |
| pt | 37 | solid |
| es | 35 | solid |
| **sg** | **16** | **THIN — gold mine** |
| fr | 9 | thin gap |
| **jp** | **9** | **THIN — top organic + 173s retention** |
| it | 9 | thin |
| ae | 10 | thin |
| nz | 17 | thin (we just added 3) |
| ie | 20 | thin (we just added 3) |

### Retention-style tool inventory
- Trackers: 33 · Streak: 2 · Habit: 3 · **Journals: 0** · Logs: 1 (`blood-pressure-log`)
- **Journals = the single biggest retention category gap.** Zero competition internally, daily-return UX pattern.

### AI engine adoption
- **44 of 2,233 tools use TeamzAI = 2%.** Massive untapped competitive moat. Every generator/analyzer/recommender in `/career/`, `/work/`, `/freelance/` is a natural TeamzAI candidate.

### Programmatic SEO templates already built
- 5 templates: `us-income-tax` (51), `uk-care-compliance` (40), `au-aged-care` (20), `ie-nursing-home` (15), `nz-aged-care` (12). Total: 138 variant pages already live.
- **Headroom:** building 5 more templates = +250-500 long-tail pages with zero per-page authoring effort.

---

## 3. The 5 GO picks (full playbooks)

These are the 2026-2027 money machines, ranked by execution priority:

---

### 🥇 PICK 1 — TCJA 2027 Sunset Cluster (`/us/tcja-2027/`) — TIME-LOCKED, BUILD NOW

**Why now:** TCJA provisions sunset Dec 31, 2026. OBBBA (July 2025) made some permanent but not all — standard deduction reverts, estate exemption halves from $13.9M → ~$7M, brackets shift. **Search spike inevitable Dec 2026 → Apr 2027.** US RPM is highest in our portfolio.

**Validation evidence:** Tax Foundation, JCT, Grant Thornton, Empower all publishing 2027 planning guides Mar-Apr 2026. SERP for "2027 tax bracket calculator" is currently thin blog posts.

**5 launch tools:**

| Slug | Title (≤60) | Meta description (120-155) |
|---|---|---|
| `/us/tcja-2027-bracket-compare/` | 2027 Tax Bracket Compare (TCJA Sunset) — Teamz Lab | Compare 2026 vs 2027 US tax brackets after TCJA sunset. Official IRS rates. Free, private, no sign-up. |
| `/us/salt-40k-cap-calculator/` | SALT $40K Cap Calculator 2027 — Teamz Lab | Calculate your SALT deduction after the $40K cap reverts in 2027. All 50 states. Free, instant. |
| `/us/bonus-depreciation-phaseout-2026/` | Bonus Depreciation 40% Phaseout 2026 — Teamz Lab | Calculate Section 168(k) bonus depreciation at 40% for 2026 assets. IRS-compliant. Free tool. |
| `/us/401k-catch-up-8000-calculator/` | $8,000 401(k) Catch-Up Calculator 2026 — Teamz Lab | Calculate your new $8,000 SECURE 2.0 catch-up 401(k) contribution (age 60-63). IRS 2026 limits. |
| `/us/estate-exemption-2027-halving/` | Estate Tax Exemption 2027 Halving Calculator — Teamz Lab | Calculate estate tax impact when exemption halves from $13.9M to ~$7M in 2027. Free, private. |

**Programmatic SEO templates:**
- `us-tcja-by-state` (51 variants) — each state shows actual 2026→2027 delta in $ using state tax stack
- `us-tcja-by-income-bracket` (8 variants: <50K, 50-100K, 100-200K, 200-400K, 400-600K, 600K-1M, 1M-5M, 5M+)
- `us-estate-exemption-by-net-worth` (5 tiers)
- **Total: 64 variants** auto-generated after base tools ship.

**GEO intro template** (use for every TCJA tool):
> "On [Last updated: 2026-MM-DD], the Tax Cuts and Jobs Act provisions sunset December 31, 2026. This calculator compares your 2026 vs 2027 [bracket/SALT/estate] tax under current law reversion. Based on IRS 2026 inflation-adjusted brackets and Joint Committee on Taxation scoring."

**Schema stack:** WebApplication + FAQPage + BreadcrumbList + GovernmentService + Dataset (bracket table) + Article (per state).

**AI integration (TeamzAI):** "Explain how TCJA sunset affects you" — input → 3-sentence plain-English impact summary. Chrome AI first, Transformers fallback.

**Backlinks:** taxfoundation.org (data citation pitch), bogleheads.org forum, reddit.com/r/tax + r/personalfinance, thefinancebuff.com (guest article), Kitces.com newsletter.

**Hub:** create `/us/tcja-2027/index.html` H2s: Individual Tax Reversion · Business Provisions · Estate & Gift · State-Level Impact. Cross-link from `/evergreen/tax-calculator/`, `/finance/retirement-calculator/`, `/career/salary-calculator/`.

---

### 🥈 PICK 2 — Singapore Finance Hub (`/sg/` 16 → 50) [DOWNGRADED 2026-04-13]

**⚠️ Updated rationale:** Original ranking was based on GA4 "57% SG traffic" which turned out to be ~88% bot/datacenter traffic (see Section 1 correction). The TRUE rationale for Singapore stands on **independent keyword evidence**, not our existing traffic:
- SmartCalculator.sg has **69 calculators ranking** in SG SERPs — proves real SG search demand
- Singapore tier-1 AdSense RPM ($8-15)
- SG-specific keywords (CPF, BTO ABSD, GST Voucher) are validated low-competition

But it's a 3-6 month organic ranking play, NOT a quick win. Recommend deferring full hub expansion until after TCJA + Japan. Started with 3 tools (cpf-self-employed-medisave, bto-absd-2026, gst-voucher-2026-eligibility) on 2026-04-13 to test ranking velocity before further investment.

**5 launch tools:**

| Slug | Title | Meta |
|---|---|---|
| `/sg/cpf-self-employed-medisave-calculator/` | CPF Self-Employed MediSave Calculator 2026 — Teamz Lab | Free Singapore CPF MediSave calculator for self-employed. Uses IRAS 2026 rates. Private, no sign-up. |
| `/sg/bto-absd-2026-calculator/` | BTO ABSD 2026 Calculator Singapore — Teamz Lab | Calculate Additional Buyer Stamp Duty for HDB BTO 2026. SC/PR/Foreigner rates. Free, instant. |
| `/sg/iras-tax-clearance-ir21-calculator/` | IRAS Tax Clearance IR21 Calculator — Teamz Lab | Estimate Singapore IR21 tax clearance for departing employees. 2026 IRAS rates. Free, private. |
| `/sg/gst-voucher-2026-eligibility/` | GST Voucher 2026 Eligibility Checker — Teamz Lab | Check your Singapore GST Voucher 2026 payout (Cash, MediSave, U-Save). Official 2026 tiers. Free. |
| `/sg/srs-tax-relief-optimizer/` | SRS Tax Relief Optimizer Singapore — Teamz Lab | Optimize your SRS contribution for max Singapore tax relief. $15,300 SC / $35,700 foreigner cap. |

**Programmatic templates:**
- `sg-cpf-by-age-bracket` (7 ages × 4 income tiers = 28 pages)
- `sg-bto-absd-by-property-type` (5 HDB types × 3 buyer status = 15)
- `sg-income-tax-by-residency` (5 residency types)
- **Total: 48 variants.**

**GEO intro:** Cite CPF Board, IRAS e-Tax Guide, MOM Employment Act, MAS SRS cap. Visible "Last updated: YYYY-MM-DD · Rates source: IRAS" line under H1 on every page.

**AI integration:** "Explain my CPF result" with SG-contextual TeamzAI prompt — competitors show only numbers.

**Backlinks:** seedly.sg (community posts), dollarsandsense.sg (guest article), moneysmart.sg/forum, hardwarezone.com.sg Money Mind, reddit.com/r/singaporefi.

**Halal note:** Avoid heavy interest-product upsells; favour takaful-aware framing where possible.

---

### 🥉 PICK 3 — Japan Finance English Hub (`/jp/` 8 → 30)

**Why:** `/jp/tedori-keisan/` is our top organic page with **173s engagement**. Hub has only 8 tools. English-language Japan SERP is **extremely thin** — RetireJapan forum, esplo.net personal blog, takayamacpa.com (consultant lead-gen, ugly UX), japantaxcalculator.com. ~2.5M foreigners in Japan + millions of expat-curious are massively underserved.

**5 launch tools:**

| Slug | Title | Meta |
|---|---|---|
| `/jp/furusato-nozei-limit-calculator-english/` | Furusato Nozei Limit Calculator (English) — Teamz Lab | Calculate your Japan furusato nozei donation limit in English. 2026 NTA rates. Free for expats. |
| `/jp/nisa-tsumitate-simulator-english/` | NISA Tsumitate Simulator English 2026 — Teamz Lab | Simulate Japan NISA Tsumitate growth in English. ¥1.2M cap, 20-year projection. Free, private. |
| `/jp/nenshu-tedori-take-home-calculator/` | Nenshu to Tedori Take-Home Calculator Japan — Teamz Lab | Convert Japan annual salary (nenshu) to monthly take-home (tedori). 2026 rates, English. Free. |
| `/jp/juuminzei-resident-tax-calculator/` | Juuminzei Resident Tax Calculator Japan — Teamz Lab | Calculate Japan resident tax (juuminzei) in English. 10% + prefecture rate. Free, no sign-up. |
| `/jp/ideco-contribution-english/` | iDeCo Contribution Calculator English Japan — Teamz Lab | Calculate your Japan iDeCo monthly contribution by employment type. 2026 MHLW limits. Free. |

**Programmatic:**
- `jp-furusato-by-prefecture` (47 prefectures, each with top henreihin gifts + prefecture tax %)
- `jp-juuminzei-by-city` (top 20 cities — Tokyo wards + Osaka/Yokohama/Nagoya/Fukuoka)
- **Total: 67 variants.**

**Seasonal spike:** Furusato Nozei deadline = Dec 31 each year. Build by November 2026 to capture Q4 spike.

**AI integration:** "Explain my furusato nozei limit in plain English" + "Translate this MHLW form field" — Chrome AI Prompt + Transformers fallback. Japanese-only competitors can't match.

**Backlinks:** retirejapan.com (forum + wiki), reddit.com/r/JapanFinance, r/japanlife, tokyocheapo.com (guest), gaijinpot.com.

**Schema:** WebApplication + FAQPage + BreadcrumbList + FinancialProduct + GovernmentService + Place (per prefecture).

---

### 🏅 PICK 4 — SME CSRD Carbon Tracker (`/eu/csrd/` new hub)

**Why:** 2026 = first reporting year for many EU SMEs under CSRD. Existing tools (Sweep, Coolset, Persefoni, Seedling) charge €10K-30K/year. Free public tools = massive demand gap. CarbonTrack just launched Jan 2026 — niche not yet dominated. **B2B RPM >> consumer.** Affiliate to Sweep/Coolset/Plan A; lead-gen to sustainability consultants is $50-300/lead.

**5 launch tools:**

| Slug | Title | Meta |
|---|---|---|
| `/eu/csrd/scope-1-2-calculator-sme/` | Scope 1+2 Emissions Calculator EU SME (CSRD) — Teamz Lab | Calculate Scope 1 & 2 CO2e for CSRD/vSME reporting. DEFRA 2026 + IEA factors. Free, private. |
| `/eu/csrd/esrs-e1-datapoint-lookup/` | ESRS E1 Data Point Lookup Tool — Teamz Lab | Look up ESRS E1 climate disclosure data points with paragraph references. EFRAG 2024. Free. |
| `/eu/csrd/taxonomy-alignment-check/` | EU Taxonomy Alignment Quick-Check — Teamz Lab | Check your activity's EU Taxonomy alignment (substantial contribution + DNSH). Free, instant. |
| `/eu/csrd/vsme-report-generator/` | vSME Voluntary Sustainability Report Generator — Teamz Lab | Generate EFRAG vSME voluntary SME sustainability report. PDF export. Free, private. |
| `/eu/csrd/carbon-factor-by-country/` | EU Grid Carbon Factor Lookup by Country — Teamz Lab | Look up Scope 2 electricity emissions factor by EU country. IEA 2026 data. Free tool. |

**Programmatic:**
- `eu-csrd-by-country` (27 EU members × Scope 2 factor page)
- `eu-taxonomy-by-nace-sector` (top 20 NACE codes)
- **Total: 47 variants.**

**Multilang:** Build EN first, then DE/FR/NL via `build-multilang.py`.

**AI integration (highest moat):** TeamzAI "AI-summarize my CSRD scope" produces ESRS-E1-structured narrative draft (double-materiality hint, transition plan stub). Replaces what consultancies charge €5K to produce.

**Schema:** WebApplication + FAQPage + BreadcrumbList + GovernmentService + Dataset + Report.

**Backlinks:** efrag.org (submit as vSME community resource), greenly.earth blog (guest), normative.io resource list, sustainability-mag.com, reddit.com/r/sustainability + r/ESG.

---

### 🏅 PICK 5 — Biological Age / PhenoAge / Longevity (`/longevity/` new hub)

**Why:** SERP #1-3 for "PhenoAge calculator" = Thrivous, AgelessRx, Andrew Steele's personal site, LaunchMyHealth, BioAgeAudit. **All thin single-purpose calculators or supplement-brand lead magnets** — the exact "blog post ranks, we replace with a real tool" pattern. Hone Health's "26 Longevity Trends 2026" report confirms mainstream momentum. Bing exact volume on `biological age calculator` = 76/mo (only validated candidate with hard volume).

**Validate-new score:** `phenoage calculator` 75/100 GO · `biological age calculator` 70/100 GO.

**5 launch tools:**

| Slug | Title | Meta |
|---|---|---|
| `/longevity/phenoage-calculator/` | PhenoAge Biological Age Calculator (Levine) — Teamz Lab | Calculate biological age using Levine PhenoAge formula + 9 biomarkers. Free, private, science-based. |
| `/longevity/dunedinpace-estimator/` | DunedinPACE Pace of Aging Estimator — Teamz Lab | Estimate your pace of aging (DunedinPACE proxy) from lifestyle inputs. Free, private, no sign-up. |
| `/longevity/zone-2-heart-rate-calculator/` | Zone 2 Heart Rate Calculator (Attia Method) — Teamz Lab | Calculate your Zone 2 training heart rate for mitochondrial health. Free, instant, private. |
| `/longevity/bio-vs-chrono-age-gap/` | Biological vs Chronological Age Gap Visualizer — Teamz Lab | Visualize your bio-chrono age gap + 10-year mortality delta. Based on Levine 2018 PhenoAge. |
| `/longevity/longevity-stack-tracker/` | Longevity Supplement Stack Tracker — Teamz Lab | Track your longevity stack (NMN, rapamycin, metformin, omega-3). Private, no sign-up. Free. |

**Programmatic:** `bio-age-by-decade-sex` (12 baseline profile pages — 20s-70s × M/F). Modest scale, focus on depth.

**AI integration:** TeamzAI "AI-coach: 3 interventions to close your bio-age gap" — takes biomarkers, returns ranked intervention list (sleep, Zone 2, protein, fasting). Curated DB fallback.

**Monetization:** AgelessRx (Rx longevity meds), Thorne supplements affiliate, Function Health lab testing ($499 referrals), InsideTracker. Each result card upsells a lab test. **High-RPM health, not gossip health.**

**Schema:** WebApplication + FAQPage + BreadcrumbList + MedicalWebPage + MedicalCondition + ScholarlyArticle (cite Levine 2018 PMID 29676998). Avoid `MedicalRiskCalculator` — stay under YMYL risk with disclaimer.

**Backlinks:** peterattiamd.com newsletter (pitch free tool), reddit.com/r/longevity + r/PeterAttia, bryanjohnson.com Blueprint forum, foundmyfitness.com community, levels.com blog (guest).

---

### 🏅 PICK 6 — Mortgage Hub Fill (`/mortgage/` 1 → 100+) — added 2026-04-29

**Why now:** Highest RPM in entire portfolio ($30-80 US) × biggest empty hub (1 tool currently). Existing tool `/mortgage/cash-out-refinance-calculator/` is the only entry. Hub index already built (Phase 1 done 2026-04-28 per `project_high_rpm_hubs_2026_04`) but content not populated.

**Validation evidence:** rpm-benchmarks.json shows mortgage US RPM $30-80 (Ezoic 2025 + Mediavine data). Bankrate, NerdWallet, MortgageProfessor dominate but 4-7-word long-tail variants are blue ocean. DataForSEO mega-batch shows "mortgage refinance break-even calculator 2026" 12K vol $14.20 CPC LOW comp.

**10 launch tools** (build at 2-3/night = 5 weeks to ship all 10):

| Slug | Title (≤60) | Meta (120-155) |
|---|---|---|
| `/mortgage/refinance-savings-calculator-2026/` | Mortgage Refinance Savings Calculator 2026 — Teamz Lab | Calculate your mortgage refinance savings with current 2026 rates. Includes break-even, total interest savings, and closing-cost recovery. |
| `/mortgage/mortgage-points-buy-down-calculator/` | Mortgage Points Buy-Down Calculator — Teamz Lab | Calculate true cost of buying mortgage points vs higher rate. Compares break-even and lifetime savings. |
| `/mortgage/biweekly-vs-monthly-payment-calculator/` | Biweekly vs Monthly Mortgage Payment Calculator — Teamz Lab | Compare biweekly vs monthly mortgage payments. See how much interest and time you save with biweekly payoff. |
| `/mortgage/early-payoff-calculator/` | Mortgage Early Payoff Calculator — Teamz Lab | Calculate impact of extra payments on your mortgage. See payoff date and total interest savings instantly. |
| `/mortgage/heloc-vs-cash-out-refinance/` | HELOC vs Cash-Out Refinance Comparison — Teamz Lab | Compare HELOC vs cash-out refinance for tapping home equity. Includes 2026 rate scenarios and tax implications. |
| `/mortgage/jumbo-loan-qualifier-2026/` | Jumbo Loan Qualifier Calculator 2026 — Teamz Lab | Check if you qualify for a jumbo mortgage in 2026. Income, DTI, reserves requirements by lender tier. |
| `/mortgage/fha-vs-conventional-comparison/` | FHA vs Conventional Mortgage Comparison — Teamz Lab | Compare FHA and conventional mortgages. Down payment, MIP, PMI, credit score requirements 2026. |
| `/mortgage/usda-loan-eligibility-calculator/` | USDA Rural Loan Eligibility Calculator — Teamz Lab | Check USDA rural development loan eligibility. Income limits, property location, 0% down qualification. |
| `/mortgage/mortgage-recast-calculator/` | Mortgage Recast Calculator — Teamz Lab | Calculate impact of mortgage recast vs refinance. See payment reduction without rate reset. |
| `/mortgage/down-payment-by-state-calculator/` | Down Payment by State Calculator 2026 — Teamz Lab | Compare typical down payment percentages and amounts across all 50 US states. 2026 home price data. |

**Programmatic SEO templates:**
- `mortgage-rates-by-state` (51 variants — each US state with current 2026 rates + state-specific lender list)
- `mortgage-by-credit-score` (8 variants — 580/620/640/680/700/720/740/780+)
- `mortgage-by-loan-amount` (10 variants — $100K, $200K, $300K... $1M jumbo)
- `mortgage-affordability-by-city` (top 100 US metros)
- **Total: 169 variants** auto-generated after base 10 ship.

**GEO intro template** (use for every mortgage tool):
> "On [Last updated: 2026-MM-DD], current US mortgage rates: 30-yr fixed 6.85-7.20%, 15-yr 6.10-6.45%, jumbo 7.05-7.40% (per Freddie Mac PMMS, week ending [date]). This calculator uses [feature] for [scenario]."

**Schema stack:** WebApplication + FAQPage + BreadcrumbList + GovernmentService (for FHA/USDA/VA tools) + Dataset (rate tables).

**AI integration (TeamzAI):** "Should I refinance?" — takes current rate, balance, term remaining, new rate quote → 3-sentence recommendation citing break-even months.

**Backlinks:** cfpb.gov data citations, hud.gov press kit, freddiemac.com PMMS reference, fanniemae.com homepath partner, reddit.com/r/personalfinance + r/realestate, mortgagenewsdaily.com guest article.

**Hub:** `/mortgage/index.html` already exists (Phase 1). Update with H2s: 2026 Rates Snapshot · Refinance Tools · Buy-Down + Points · Equity & HELOC · By State · By Credit Score. Cross-link from `/finance/`, `/us/income-tax-calculator/`, `/real-estate/`.

**Y1 revenue projection:** 100 mortgage tools at 1K-5K monthly views/tool average × $30-80 RPM = $3K-40K/mo at maturity. Conservative 25% conversion to actual traffic in Y1 = **$750-10K/mo**.

**Sources:** cfpb.gov, hud.gov/program_offices/housing, freddiemac.com/research/datasets, fanniemae.com/research-insights, fhfa.gov.

---

## 4. The 3 SKIP picks (correcting the earlier synthesis)

### ❌ GLP-1 Tracker Hub
**Earlier verdict:** GO. **Corrected:** SKIP.
Top 10 SERP for "best GLP-1 tracker 2026" = Shotsy, Glapp, Pep, GlucoPal, Weightly, MeAgain, GLPeak, Jabby, SlimShot, MyNetDiary. **All free-tier polished native mobile apps, all VC-funded.** GLP-1 users want injection-site rotation diagrams, Apple Health sync, push reminders — native mobile features. Web tool loses.
**Salvage:** Build ONE simple `/health/tirzepatide-titration-schedule/` as traffic bait, affiliate-link to Hims/Ro. Don't build a hub.

### ❌ Perimenopause Symptom Journal
**Earlier verdict:** GO. **Corrected:** SKIP the journal.
Balance (Dr. Louise Newson, Apple Editors' Choice + ORCHA certified), Health & Her (ORCHA certified), MenoLife, Clue Perimenopause own this niche. Trust is the moat — a free web tool cannot beat "built by Dr. Newson."
**Salvage:** Build 3-5 one-shot menopause calculators (Greene Climacteric Scale quiz, HRT dose converter, FSH interpretation) under `/health/`. Affiliate to Winona/The Better Menopause (25-30% commissions, lifetime residual on some).

### ❌ Burnout Risk Daily Check-in
Maslach Burnout Inventory is **proprietary** (Mind Garden licenses it — cannot legally republish). Mental-health advertising is AdSense-restricted, affiliates weak (BetterHelp lawsuit reduced payouts). Validate-new score: 45/100, 0 autocomplete. Triple-skip.

### Other validated SKIPs
- **Creator posting streak tracker** — feature, not product. Metricool/Buffer/Hootsuite already track this.
- **CPF contribution calculator** — 9 similar tools already in our codebase (cannibalization).
- **CSRD acronym keyword** — Trends FALLING. Use "carbon calculator business" framing instead (RISING avg 37/100).
- **`longevity stack tracker` exact phrase** — 0 autocomplete, ambiguous keyword. Rename "supplement stack tracker."

---

## 5. Three sleeper bets (uncolonized blue oceans found in research)

### 🌊 Sleeper 1 — Oral health → biological age connector
Hone Health 2026 trend report flags oral health / inflammation / aging as the "actionable longevity metric." **Zero calculator exists.** Build `/longevity/gum-health-longevity-score/` — first mover, ride the longevity wave, dental affiliate angle.

### 🌊 Sleeper 2 — Neko Health / Function Health prep tools
Neko Health (full-body scan) is exploding (London, Stockholm, US launch). Function Health $499/yr. People search "what to ask at a Neko scan", "Neko vs Function Health comparison", "biomarker glossary." **Zero competitors.** Build `/longevity/neko-health-prep-checklist/` and `/longevity/biomarker-glossary/`.

### 🌊 Sleeper 3 — vSME (Voluntary SME) ESRS data-point lookup
EU micro-SMEs *below* CSRD threshold still need voluntary reporting for supply-chain requests. Totally uncontested. Build `/eu/csrd/vsme-datapoint-lookup/` as part of pick 4's hub — but worth flagging separately, audience is different.

---

## 6. Infrastructure to leverage (already built, underused)

### Programmatic SEO (5 templates exist, room for 5+ more)
**Existing:** us-income-tax (51), uk-care-compliance (40), au-aged-care (20), ie-nursing-home (15), nz-aged-care (12) = 138 variant pages.
**To build (per the 5 picks):** us-tcja-by-state (51) · sg-cpf-by-age-bracket (28) · jp-furusato-by-prefecture (47) · eu-csrd-by-country (27) · plus secondary templates = **+200 pages with zero per-page authoring**.

### Multilang (DE/PT/ES mature; FR/IT/JP starved)
- DE 47, PT 37, ES 35 — solid hubs to pour translations into
- FR 9, IT 9, JP 9, PL 3 — thin gaps
- **20 top-traffic finance tools have ZERO translations.** ES + PT translations of 20 tools = +40 tools to mature hubs (zero authoring, 100% language work via `build-multilang.py`).

### AI engine (TeamzAI) — only 2% adoption
44 of 2,233 tools use TeamzAI. Every `/career/`, `/work/`, `/freelance/`, `/health/` generator/analyzer/recommender is a candidate. **Lift adoption to 20% over 12 months = differentiated moat.** Chrome AI privacy story is unique selling point.

### Retention category (largely empty)
- Trackers: 33 · Streak: 2 · **Journals: 0** · Logs: 1
- Build 10 journal tools (mood, gratitude, food, dream, symptom, period, pregnancy, expense, workout, sleep) — all localStorage, all daily return, calendar heatmap pattern.

---

## 7. 90-day execution plan

### Week 1 — Stop the bleeding
- [ ] AdSense Policy Center check + Payments verification
- [ ] Re-auth Search Console: `python3 build-search-console-auth.py`
- [ ] Populate `rank-watchlist.json` with top 20 keywords; cron `build-rank-tracker.py record` daily
- [ ] Add bot-traffic filter to `shared/js/adsense.js`
- [ ] Submit to top 5 high-DA directories (Hacker News, Product Hunt, Trustpilot, G2, Behance)
- [ ] Run `python3 scripts/build-fix-orphans.py fix` — 9 orphans, 27 hub-unlinked, 51 thin-related
- [ ] Investigate Singapore traffic source (organic vs referrer flood)

### Week 2 — Mobile CWV blitz
- [ ] Fix LCP < 2.5s on top 10 traffic pages: `/`, `/jp/tedori-keisan/`, `/bd/family-card-generator/`, `/3d/fluid-simulation/`, `/tools/ai-audio-classifier/`, top 5 Ramadan pages
- [ ] Fix CLS on `/jp/tedori-keisan/` (currently 0.972 — catastrophic)
- [ ] Re-run `build-pagespeed.sh --url` to verify

### Weeks 3-5 — TCJA 2027 cluster (Pick 1)
- [ ] Build 5 launch tools listed in Pick 1
- [ ] Add `us-tcja-by-state` template to `build-programmatic-seo.py`, generate 51 state pages
- [ ] Add `us-tcja-by-income-bracket` template (8 variants)
- [ ] Add `us-estate-exemption-by-net-worth` template (5 variants)
- [ ] Hub `/us/tcja-2027/index.html` with 4 H2 sections
- [ ] Cross-link from `/evergreen/tax-calculator/`, `/finance/retirement-calculator/`, `/career/salary-calculator/`
- [ ] Backlink outreach: pitch taxfoundation.org + Kitces.com newsletter
- [ ] Run `python3 scripts/build-request-indexing.py` after each batch

### Weeks 6-8 — Singapore expansion (Pick 2)
- [ ] Build 5 launch tools listed in Pick 2
- [ ] Add `sg-cpf-by-age-bracket` template (28 variants)
- [ ] Add `sg-bto-absd-by-property-type` template (15 variants)
- [ ] Add `sg-income-tax-by-residency` template (5 variants)
- [ ] Update `/sg/index.html` with 4 H2 sections (CPF Tools / Property & Stamp Duty / Tax & Relief / Government Payouts)
- [ ] Outreach: post helpful tools on r/singaporefi, seedly.sg community, hardwarezone.com.sg

### Weeks 9-11 — Japan English expansion (Pick 3)
- [ ] Build 5 launch tools listed in Pick 3 (start with furusato-nozei — seasonal spike Q4)
- [ ] Add `jp-furusato-by-prefecture` template (47 variants)
- [ ] Add `jp-juuminzei-by-city` template (20 variants)
- [ ] Update `/jp/index.html` H2 structure
- [ ] Outreach: RetireJapan forum, r/JapanFinance, r/japanlife, tokyocheapo.com guest pitch

### Weeks 12-13 — Pick 4 (CSRD) base + Pick 5 (Longevity) base
- [ ] Build 5 launch tools each
- [ ] CSRD: build EN base, queue DE/FR/NL via `build-multilang.py suggest`
- [ ] Longevity: ship PhenoAge calculator first (highest validated demand)
- [ ] Cross-link new clusters to existing health/business hubs

### Throughout — cron jobs
```
0 9 * * *  ./build-daily-seo.sh           # rank tracker + GSC anomalies daily
0 10 * * 1 ./build-seo-dashboard.sh        # weekly SEO dashboard
0 11 * * * python3 scripts/build-rank-tracker.py record
0 12 * * 0 python3 scripts/build-backlinks.py    # weekly directory check
```

---

## 8. Tracking + KPIs

### Weekly check (every Monday)
- AdSense earnings + RPM (target: rising trend after fix)
- GA4 returning users % (retention proxy — target: rising)
- Top 10 organic pages (look for new entries from new tools)
- Search Console new queries with impressions (track keyword surface)

### Monthly check (first of month)
- Microsoft Clarity bot rate (target: <10%)
- Backlinks Overview new DoFollow (target: 5+/mo)
- Internal link health score (target: 90+/100, currently 81)
- Programmatic variant pages indexed % via Google URL Inspection
- Rank tracker movers report

### Quarterly check
- Hub-by-hub revenue decomposition (which clusters paying most?)
- Multilang translation progress (`build-multilang.py status`)
- AI engine adoption % (`grep -l "TeamzAI" -r . --include="*.html" | wc -l`)

---

## 9. Things to STOP doing

- **Stop building one-shot calculators** unless they fit a hub cluster + have programmatic variants + name a specific affiliate program.
- **Stop English-only generic calculators** (BMI, tip, compound interest). CPC has collapsed.
- **Stop posting to low-yield distribution channels** (Mastodon, Bluesky get near-zero referral). Focus distribution on Reddit niche subs + Pinterest pin images for finance/health tools.
- **Stop adding to bloated hubs** (`/evergreen/` 235 tools, `/tools/` 116, `/health/` 115). Diminishing returns. Pour energy into `/sg/`, `/jp/`, `/longevity/`, `/eu/csrd/`, `/us/tcja-2027/`.
- **Stop building without programmatic + multilang flag check** — every new finance/tax/health tool should be evaluated: "can this become 50 pages with one template?" + "should this exist in ES/PT/DE?"
- **Stop trusting AdSense alone.** 24% ad-blocker rate + £0 RPM means revenue must diversify: named affiliate programs (Hims/Thorne/Wise/Rakuten Securities/MoneySmart SG), B2B lead-gen (CSRD consultants), email lead capture for retention.

---

## 10. Critical scripts & where data lives

| What | Script | Run cadence |
|---|---|---|
| AdSense earnings | `./scripts/build-adsense.sh` | Daily |
| Bot detection | `./scripts/build-clarity.sh` | Weekly |
| PageSpeed | `./scripts/build-pagespeed.sh --url <path>` | After mobile fixes |
| Search Console | `./scripts/build-search-console.sh` | Daily (after re-auth) |
| Rank tracker | `python3 scripts/build-rank-tracker.py record/movers/report` | Daily / Weekly |
| GSC anomalies | `python3 scripts/build-gsc-anomalies.py` | Daily (after re-auth) |
| Backlinks | `python3 scripts/build-backlinks-overview.py scan/report/dofollow` | Weekly |
| Directories | `python3 scripts/build-backlinks.py submit / done` | Weekly |
| Programmatic SEO | `python3 scripts/build-programmatic-seo.py [template]` | Per cluster build |
| Multilang | `python3 scripts/build-multilang.py status / suggest` | Monthly |
| Orphan fix | `python3 scripts/build-fix-orphans.py fix` | After every batch build |
| Indexing requests | `python3 scripts/build-request-indexing.py` | After every batch build |
| Topic clusters | `python3 scripts/build-topic-cluster-report.py` | Monthly |
| Full SEO dashboard | `./scripts/build-seo-dashboard.sh --quick` | Weekly |

---

## 11. Honest expectations

**This is not a 6-month plan to financial freedom.** SEO compounds slowly. Realistic milestones:

- **Day 30:** AdSense paying again (fix dependent). 5-10 new tools live.
- **Day 90:** First TCJA cluster ranking page-2/3 in Google. 30+ new tools, 100+ programmatic variants.
- **Day 180:** TCJA seasonal spike captured. SG hub ranks for 20+ keywords. Backlink count from real domains (not self-distribution) at 20+.
- **Day 365:** Longevity hub hits page-1 for 5+ Levine/PhenoAge keywords. Multilang DE/FR for finance tools live. Revenue diversified beyond AdSense (3+ named affiliate programs producing).

**The biggest risk to this plan:**
1. AdSense never recovers (account banned) — diversify to Ezoic/Mediavine, accelerate affiliate revenue.
2. AI search ChatGPT/Perplexity changes citation policy — diversify channel mix back to Google.
3. Burning out on building before fixing infrastructure — stop building, fix bottlenecks first.

**The biggest opportunity in this plan:**
- We're already getting more traffic from ChatGPT than Google. If we double down on `seo-geo` and `llms.txt` excellence while everyone else still optimizes for Google, we're 12 months ahead of the market.

---

## 12. Sources cited in research

- [LearnMuscles — 6 Best GLP-1 Apps 2026](https://learnmuscles.com/blog/2025/11/27/6-best-glp-1-tracking-apps-compared-which-app-actually-works-in-2026/)
- [Hone Health — 26 Longevity Trends 2026](https://honehealth.com/edge/longevity-trends/)
- [Andrew Steele PhenoAge Calculator](https://andrewsteele.co.uk/biological-age/)
- [Thrivous PhenoAge Calculator](https://thrivous.com/pages/biological-age-calculator)
- [Balance Menopause App](https://apps.apple.com/us/app/balance-menopause-hormones/id1503345959)
- [Health & Her App](https://healthandher.com/en-us/pages/menopause-perimenopause-app)
- [SmartCalculator Singapore (69 calculators ranking)](https://www.smartcalculator.sg/)
- [IRAS Calculators](https://www.iras.gov.sg/quick-links/calculators)
- [RetireJapan Forum](https://www.retirejapan.com/forum/)
- [Takayama CPA Furusato Calculator](https://www.takayamacpa.com/furusato/en)
- [IRS One Big Beautiful Bill provisions](https://www.irs.gov/newsroom/one-big-beautiful-bill-provisions)
- [Grant Thornton 2026 Individual Tax Planning Guide](https://www.grantthornton.com/insights/alerts/tax/2025/legislative-updates/2026-individual-tax-planning-guide)
- [Empower — 8 IRS changes 2026](https://www.empower.com/the-currency/money/8-irs-changes-could-impact-your-taxes-2026-news)
- [CarbonTrack CSRD](https://carbontracksystem.com/)
- [EFRAG vSME standard (Dec 2024)](https://www.efrag.org/)
- [Persefoni — Free Carbon Calculators](https://www.persefoni.com/blog/best-free-carbon-footprint-software)
- [Authority Hacker — Women's Health Affiliate Programs](https://www.authorityhacker.com/womens-health-affiliate-programs/)
- [Katalys — Hims/Ro affiliate](https://katalys.com/industries/weight-loss-affiliate-programs/)
- [Levine 2018 PhenoAge — PMID 29676998](https://pubmed.ncbi.nlm.nih.gov/29676998/)

---

**END OF DOCUMENT.** Update this file at the end of each 90-day cycle with what worked, what didn't, and the next 90 days. Treat it as a living planning document, not a one-shot strategy.
