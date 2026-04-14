---
title: "Free CSRD & Carbon Reporting Tools for EU SMEs (2026)"
slug: free-csrd-tools-eu-sme-2026
tags: csrd, sustainability, esg, carbon, eu, sme, reporting, free
canonical_url: https://tool.teamzlab.com/eu/csrd/
og_image: https://tool.teamzlab.com/og-images/eu.png
---

# Free CSRD & Carbon Reporting Tools for EU SMEs (2026)

If you run a small or mid-sized business in the EU, the sustainability reporting wall is no longer something that happens to other people. The Corporate Sustainability Reporting Directive (CSRD) wave 2 covers large companies for FY2025, with reports due between March and June 2026 — and those companies are pushing data requests down their supply chain. Your customers, your lenders, and increasingly your insurers want numbers: Scope 1 emissions, Scope 2 emissions, an energy mix, a headcount-weighted workforce figure.

For most SMEs, the tooling market is broken. Persefoni, Sweep, Plan A, Normative, Coolset and Greenly sit in the €8,000 to €30,000 per year bracket before consultancy fees. That makes sense for a 2,000-person manufacturer. It does not make sense for a 14-person bakery in Munich whose biggest customer just sent them a 40-field data sheet.

I spent the last two weekends building three free browser-based tools to cover the 80% case — what EFRAG actually standardised in the **Voluntary SME (vSME) Standard** published December 2024, and the inputs you need to fill it in. Everything runs client-side. No signup, no upload, no consultant dashboard to log into. Below is what each one does and how to use it.

## 1. The vSME Report Generator

**The problem.** EFRAG's vSME standard is 47 pages of module-by-module disclosures: Basic Module (B1–B12) plus the optional Comprehensive Module (C1–C9). It is genuinely a good standard — proportionate, reasonable, designed for companies without a sustainability team — but reading it, mapping your data to it, and producing a clean PDF is a week of work if you have never done ESG reporting before. The paid platforms charge €5k–€15k a year for a template that does essentially this.

**The tool.** [vSME Report Generator](https://tool.teamzlab.com/eu/csrd/vsme-report-generator/) walks you through the Basic Module in the order EFRAG specifies. You enter company basics (B1), sustainability practices (B2), energy and GHG (B3), pollution (B4), biodiversity (B5), water (B6), resource use (B7), workforce (B8–B10), workers in the value chain (B11), and governance (B12). The tool builds a formatted report you can download, hand to your auditor, or attach to a customer questionnaire.

**How to use it.** Start with B1 and B3. Those two modules satisfy maybe 70% of the data requests you'll actually receive from larger customers who are in CSRD scope. Come back for the rest when you have another two hours.

## 2. Scope 1 + 2 Emissions Calculator (EU SME)

**The problem.** Scope 1 is fuel you burn directly (gas boiler, company van diesel, refrigerants that leak). Scope 2 is electricity you purchase. The formulas are not hard — it is kWh × emission factor — but the emission factors are scattered across DEFRA, the EEA, national grid operators, and the GHG Protocol. Paid calculators bundle the factors but lock them behind a subscription.

**The tool.** [Scope 1+2 Emissions Calculator for EU SMEs](https://tool.teamzlab.com/eu/csrd/scope-1-2-calculator-sme/) ships with current EU factors built in. You enter annual natural gas (kWh or m³), diesel and petrol (litres), LPG, heating oil, refrigerant top-ups (kg of R-410A, R-134a, etc.), and purchased electricity by country. It returns tCO₂e for Scope 1, Scope 2 (location-based), and a combined total — the exact fields vSME B3 asks for.

**A concrete example.** A bakery in Germany with 20 employees, one delivery van, and a gas-fired oven might log: 180,000 kWh natural gas, 4,200 litres diesel, 95,000 kWh purchased electricity. The calculator returns roughly 32.7 tCO₂e Scope 1 and 35.4 tCO₂e Scope 2 — a total of ~68 tCO₂e. That one number is what their supermarket customer's CSRD team needs to fill in their own supply chain disclosure.

## 3. EU Grid Carbon Factor Lookup by Country

**The problem.** For Scope 2 you need a country-specific electricity emission factor, and those numbers move every year as national grids decarbonise. France sits around 55 gCO₂/kWh (nuclear heavy). Poland is still north of 650 gCO₂/kWh. Sweden is under 40. Pick the wrong one and your disclosure is off by an order of magnitude.

**The tool.** [EU Grid Carbon Factor Lookup by Country](https://tool.teamzlab.com/eu/csrd/carbon-factor-by-country/) gives you the latest published factor for each EU-27 country plus UK, Norway, and Switzerland, with the source year shown. Useful if you operate across borders — a SaaS company with a Dublin HQ, a Warsaw dev office, and AWS workloads in eu-central-1 (Frankfurt) will find three very different factors apply.

**How to use it alongside the calculator.** Pull the factor for each country you operate in, plug the kWh figure into the Scope 1+2 calculator for each site separately, then sum. That is the location-based method EFRAG expects in vSME B3.

## Why browser-based, and what's next

None of your energy bills, payroll data, or site lists leave your browser with any of these tools. That matters because this data is commercially sensitive — you do not want your diesel volumes cached on a SaaS vendor's server whose privacy policy is a moving target, and you certainly do not want a supplier data leak to be the reason your largest customer finds out you're behind on a decarbonisation commitment.

Three tools are not a full CSRD suite. Still to come on the [EU CSRD hub](https://tool.teamzlab.com/eu/csrd/): a Scope 3 screening estimator for the common categories (purchased goods, business travel, commuting), a double materiality assessment worksheet, and a CBAM quarterly report builder for importers of steel, cement, aluminium, fertiliser, hydrogen and electricity.

If there is a specific vSME module or a CSRD data point you keep getting asked for and can't find a free calculator for, that's useful feedback — the priority for the next batch comes from what SMEs actually get hit with in their customer questionnaires.

---

*Originally published at [https://tool.teamzlab.com](https://tool.teamzlab.com)*
