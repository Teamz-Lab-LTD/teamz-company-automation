#!/usr/bin/env python3
"""
Programmatic SEO Generator — Teamz Lab Tools

Generates location-specific variants of existing tools.
Each variant targets a long-tail keyword for easier ranking.

Usage:
  python3 scripts/build-programmatic-seo.py us-income-tax    # Generate US state income tax pages
  python3 scripts/build-programmatic-seo.py --list            # List available templates
  python3 scripts/build-programmatic-seo.py --dry-run us-income-tax  # Preview without writing
"""

import os
import sys
import json

SITE_URL = "https://tool.teamzlab.com"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# US STATE INCOME TAX DATA (2026)
# ============================================================
US_STATES = {
    "alabama": {"name": "Alabama", "abbr": "AL", "type": "graduated", "rates": [{"min": 0, "max": 500, "rate": 2.0}, {"min": 500, "max": 3000, "rate": 4.0}, {"min": 3000, "max": float("inf"), "rate": 5.0}], "note": "Alabama allows a deduction for federal income tax paid.", "std_deduction": {"single": 2500, "mfj": 7500}},
    "alaska": {"name": "Alaska", "abbr": "AK", "type": "none", "note": "Alaska has no state income tax. Residents also receive an annual Permanent Fund Dividend from oil revenues."},
    "arizona": {"name": "Arizona", "abbr": "AZ", "type": "flat", "rate": 2.5, "note": "Arizona has a flat 2.5% income tax rate, one of the lowest in the nation.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "arkansas": {"name": "Arkansas", "abbr": "AR", "type": "graduated", "rates": [{"min": 0, "max": 4400, "rate": 2.0}, {"min": 4400, "max": 8800, "rate": 4.0}, {"min": 8800, "max": float("inf"), "rate": 4.4}], "note": "Arkansas recently reduced its top rate as part of ongoing tax reform.", "std_deduction": {"single": 2340, "mfj": 4680}},
    "california": {"name": "California", "abbr": "CA", "type": "graduated", "rates": [{"min": 0, "max": 10412, "rate": 1.0}, {"min": 10412, "max": 24684, "rate": 2.0}, {"min": 24684, "max": 38959, "rate": 4.0}, {"min": 38959, "max": 54081, "rate": 6.0}, {"min": 54081, "max": 68350, "rate": 8.0}, {"min": 68350, "max": 349137, "rate": 9.3}, {"min": 349137, "max": 418961, "rate": 10.3}, {"min": 418961, "max": 698271, "rate": 11.3}, {"min": 698271, "max": 1000000, "rate": 12.3}, {"min": 1000000, "max": float("inf"), "rate": 13.3}], "note": "California has the highest state income tax rate in the US at 13.3% on income over $1 million.", "std_deduction": {"single": 5540, "mfj": 11080}},
    "colorado": {"name": "Colorado", "abbr": "CO", "type": "flat", "rate": 4.4, "note": "Colorado uses a flat tax rate applied to federal taxable income.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "connecticut": {"name": "Connecticut", "abbr": "CT", "type": "graduated", "rates": [{"min": 0, "max": 10000, "rate": 3.0}, {"min": 10000, "max": 50000, "rate": 5.0}, {"min": 50000, "max": 100000, "rate": 5.5}, {"min": 100000, "max": 200000, "rate": 6.0}, {"min": 200000, "max": 250000, "rate": 6.5}, {"min": 250000, "max": 500000, "rate": 6.9}, {"min": 500000, "max": float("inf"), "rate": 6.99}], "note": "Connecticut also applies a tax on capital gains and has a personal tax credit for lower-income filers."},
    "delaware": {"name": "Delaware", "abbr": "DE", "type": "graduated", "rates": [{"min": 0, "max": 2000, "rate": 0}, {"min": 2000, "max": 5000, "rate": 2.2}, {"min": 5000, "max": 10000, "rate": 3.9}, {"min": 10000, "max": 20000, "rate": 4.8}, {"min": 20000, "max": 25000, "rate": 5.2}, {"min": 25000, "max": 60000, "rate": 5.55}, {"min": 60000, "max": float("inf"), "rate": 6.6}], "note": "Delaware has no sales tax, making income tax the primary state revenue source.", "std_deduction": {"single": 3250, "mfj": 6500}},
    "florida": {"name": "Florida", "abbr": "FL", "type": "none", "note": "Florida has no state income tax, making it one of the most tax-friendly states. This is a major draw for retirees and remote workers."},
    "georgia": {"name": "Georgia", "abbr": "GA", "type": "flat", "rate": 5.39, "note": "Georgia transitioned to a flat tax rate starting in 2025, replacing its previous graduated structure.", "std_deduction": {"single": 12000, "mfj": 24000}},
    "hawaii": {"name": "Hawaii", "abbr": "HI", "type": "graduated", "rates": [{"min": 0, "max": 2400, "rate": 1.4}, {"min": 2400, "max": 4800, "rate": 3.2}, {"min": 4800, "max": 9600, "rate": 5.5}, {"min": 9600, "max": 14400, "rate": 6.4}, {"min": 14400, "max": 19200, "rate": 6.8}, {"min": 19200, "max": 24000, "rate": 7.2}, {"min": 24000, "max": 36000, "rate": 7.6}, {"min": 36000, "max": 48000, "rate": 7.9}, {"min": 48000, "max": 150000, "rate": 8.25}, {"min": 150000, "max": 175000, "rate": 9.0}, {"min": 175000, "max": 200000, "rate": 10.0}, {"min": 200000, "max": float("inf"), "rate": 11.0}], "note": "Hawaii has 12 tax brackets — the most of any state — with a top rate of 11%."},
    "idaho": {"name": "Idaho", "abbr": "ID", "type": "flat", "rate": 5.695, "note": "Idaho switched to a flat tax in 2023, simplifying its previous graduated system.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "illinois": {"name": "Illinois", "abbr": "IL", "type": "flat", "rate": 4.95, "note": "Illinois has a constitutionally mandated flat tax. A 2020 ballot measure to allow graduated rates was defeated by voters.", "std_deduction": {"single": 0, "mfj": 0}},
    "indiana": {"name": "Indiana", "abbr": "IN", "type": "flat", "rate": 3.05, "note": "Indiana has one of the lower flat tax rates in the nation. Counties also levy their own income taxes (0.5%–2.9%).", "std_deduction": {"single": 0, "mfj": 0}},
    "iowa": {"name": "Iowa", "abbr": "IA", "type": "flat", "rate": 3.8, "note": "Iowa transitioned to a flat tax rate as part of 2022 tax reform, down from a previous top rate of 8.53%.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "kansas": {"name": "Kansas", "abbr": "KS", "type": "graduated", "rates": [{"min": 0, "max": 15000, "rate": 3.1}, {"min": 15000, "max": 30000, "rate": 5.25}, {"min": 30000, "max": float("inf"), "rate": 5.7}], "note": "Kansas has three tax brackets with a top rate of 5.7%.", "std_deduction": {"single": 3500, "mfj": 8000}},
    "kentucky": {"name": "Kentucky", "abbr": "KY", "type": "flat", "rate": 4.0, "note": "Kentucky uses a flat income tax rate applied to all taxable income.", "std_deduction": {"single": 3160, "mfj": 6320}},
    "louisiana": {"name": "Louisiana", "abbr": "LA", "type": "flat", "rate": 3.0, "note": "Louisiana adopted a flat tax rate in 2025, replacing its previous three-bracket system.", "std_deduction": {"single": 12500, "mfj": 25000}},
    "maine": {"name": "Maine", "abbr": "ME", "type": "graduated", "rates": [{"min": 0, "max": 26050, "rate": 5.8}, {"min": 26050, "max": 61600, "rate": 6.75}, {"min": 61600, "max": float("inf"), "rate": 7.15}], "note": "Maine offers an earned income tax credit equal to 12% of the federal credit.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "maryland": {"name": "Maryland", "abbr": "MD", "type": "graduated", "rates": [{"min": 0, "max": 1000, "rate": 2.0}, {"min": 1000, "max": 2000, "rate": 3.0}, {"min": 2000, "max": 3000, "rate": 4.0}, {"min": 3000, "max": 100000, "rate": 4.75}, {"min": 100000, "max": 125000, "rate": 5.0}, {"min": 125000, "max": 150000, "rate": 5.25}, {"min": 150000, "max": 250000, "rate": 5.5}, {"min": 250000, "max": float("inf"), "rate": 5.75}], "note": "Maryland counties also levy a local income tax (1.75%–3.2%) on top of the state tax.", "std_deduction": {"single": 2550, "mfj": 5100}},
    "massachusetts": {"name": "Massachusetts", "abbr": "MA", "type": "flat", "rate": 5.0, "note": "Massachusetts added a 4% surtax on income over $1 million in 2023, making the effective top rate 9%.", "std_deduction": {"single": 0, "mfj": 0}},
    "michigan": {"name": "Michigan", "abbr": "MI", "type": "flat", "rate": 4.25, "note": "Michigan uses a flat tax rate. Some cities (including Detroit at 2.4%) levy additional local income taxes.", "std_deduction": {"single": 0, "mfj": 0}},
    "minnesota": {"name": "Minnesota", "abbr": "MN", "type": "graduated", "rates": [{"min": 0, "max": 31690, "rate": 5.35}, {"min": 31690, "max": 104090, "rate": 6.8}, {"min": 104090, "max": 183340, "rate": 7.85}, {"min": 183340, "max": float("inf"), "rate": 9.85}], "note": "Minnesota has the fifth-highest state income tax rate in the US at 9.85%.", "std_deduction": {"single": 14575, "mfj": 29150}},
    "mississippi": {"name": "Mississippi", "abbr": "MS", "type": "flat", "rate": 4.7, "note": "Mississippi moved to a flat tax in 2026, eliminating its previous graduated brackets.", "std_deduction": {"single": 2300, "mfj": 4600}},
    "missouri": {"name": "Missouri", "abbr": "MO", "type": "graduated", "rates": [{"min": 0, "max": 1207, "rate": 0}, {"min": 1207, "max": 2414, "rate": 2.0}, {"min": 2414, "max": 3621, "rate": 2.5}, {"min": 3621, "max": 4828, "rate": 3.0}, {"min": 4828, "max": 6035, "rate": 3.5}, {"min": 6035, "max": 7242, "rate": 4.0}, {"min": 7242, "max": 8449, "rate": 4.5}, {"min": 8449, "max": float("inf"), "rate": 4.8}], "note": "Missouri has been gradually reducing its top rate and plans further cuts.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "montana": {"name": "Montana", "abbr": "MT", "type": "flat", "rate": 5.9, "note": "Montana switched to a flat tax in 2024 from a previous seven-bracket graduated system.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "nebraska": {"name": "Nebraska", "abbr": "NE", "type": "graduated", "rates": [{"min": 0, "max": 3700, "rate": 2.46}, {"min": 3700, "max": 22170, "rate": 3.51}, {"min": 22170, "max": 35730, "rate": 5.01}, {"min": 35730, "max": float("inf"), "rate": 5.84}], "note": "Nebraska has been phasing in rate reductions as part of tax reform.", "std_deduction": {"single": 8000, "mfj": 16000}},
    "nevada": {"name": "Nevada", "abbr": "NV", "type": "none", "note": "Nevada has no state income tax. The state relies primarily on gaming and sales tax revenue."},
    "new-hampshire": {"name": "New Hampshire", "abbr": "NH", "type": "none", "note": "New Hampshire eliminated its interest and dividends tax in 2025, making it fully income-tax-free."},
    "new-jersey": {"name": "New Jersey", "abbr": "NJ", "type": "graduated", "rates": [{"min": 0, "max": 20000, "rate": 1.4}, {"min": 20000, "max": 35000, "rate": 1.75}, {"min": 35000, "max": 40000, "rate": 3.5}, {"min": 40000, "max": 75000, "rate": 5.525}, {"min": 75000, "max": 500000, "rate": 6.37}, {"min": 500000, "max": 1000000, "rate": 8.97}, {"min": 1000000, "max": float("inf"), "rate": 10.75}], "note": "New Jersey has the third-highest top state income tax rate in the nation at 10.75%.", "std_deduction": {"single": 0, "mfj": 0}},
    "new-mexico": {"name": "New Mexico", "abbr": "NM", "type": "graduated", "rates": [{"min": 0, "max": 5500, "rate": 1.7}, {"min": 5500, "max": 11000, "rate": 3.2}, {"min": 11000, "max": 16000, "rate": 4.7}, {"min": 16000, "max": 210000, "rate": 4.9}, {"min": 210000, "max": float("inf"), "rate": 5.9}], "note": "New Mexico exempts most Social Security income from state taxation.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "new-york": {"name": "New York", "abbr": "NY", "type": "graduated", "rates": [{"min": 0, "max": 8500, "rate": 4.0}, {"min": 8500, "max": 11700, "rate": 4.5}, {"min": 11700, "max": 13900, "rate": 5.25}, {"min": 13900, "max": 80650, "rate": 5.5}, {"min": 80650, "max": 215400, "rate": 6.0}, {"min": 215400, "max": 1077550, "rate": 6.85}, {"min": 1077550, "max": 5000000, "rate": 9.65}, {"min": 5000000, "max": 25000000, "rate": 10.3}, {"min": 25000000, "max": float("inf"), "rate": 10.9}], "note": "New York City residents pay an additional 3.078%–3.876% city income tax on top of the state tax.", "std_deduction": {"single": 8000, "mfj": 16050}},
    "north-carolina": {"name": "North Carolina", "abbr": "NC", "type": "flat", "rate": 4.5, "note": "North Carolina has been steadily reducing its flat rate, down from 5.25% in 2022.", "std_deduction": {"single": 12750, "mfj": 25500}},
    "north-dakota": {"name": "North Dakota", "abbr": "ND", "type": "flat", "rate": 1.95, "note": "North Dakota has the lowest flat income tax rate of any state that levies an income tax.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "ohio": {"name": "Ohio", "abbr": "OH", "type": "graduated", "rates": [{"min": 0, "max": 26050, "rate": 0}, {"min": 26050, "max": 100000, "rate": 2.75}, {"min": 100000, "max": float("inf"), "rate": 3.5}], "note": "Ohio exempts the first $26,050 of income from tax. Many cities levy additional municipal income taxes.", "std_deduction": {"single": 0, "mfj": 0}},
    "oklahoma": {"name": "Oklahoma", "abbr": "OK", "type": "graduated", "rates": [{"min": 0, "max": 1000, "rate": 0.25}, {"min": 1000, "max": 2500, "rate": 0.75}, {"min": 2500, "max": 3750, "rate": 1.75}, {"min": 3750, "max": 4900, "rate": 2.75}, {"min": 4900, "max": 7200, "rate": 3.75}, {"min": 7200, "max": float("inf"), "rate": 4.75}], "note": "Oklahoma also levies a use tax on purchases made from out-of-state retailers.", "std_deduction": {"single": 6350, "mfj": 12700}},
    "oregon": {"name": "Oregon", "abbr": "OR", "type": "graduated", "rates": [{"min": 0, "max": 4050, "rate": 4.75}, {"min": 4050, "max": 10200, "rate": 6.75}, {"min": 10200, "max": 125000, "rate": 8.75}, {"min": 125000, "max": float("inf"), "rate": 9.9}], "note": "Oregon has no sales tax, so income tax is the primary revenue source. The top rate of 9.9% is among the highest in the US.", "std_deduction": {"single": 2745, "mfj": 5495}},
    "pennsylvania": {"name": "Pennsylvania", "abbr": "PA", "type": "flat", "rate": 3.07, "note": "Pennsylvania has one of the lowest flat income tax rates. Local earned income taxes (up to 3.88% in Philadelphia) apply separately.", "std_deduction": {"single": 0, "mfj": 0}},
    "rhode-island": {"name": "Rhode Island", "abbr": "RI", "type": "graduated", "rates": [{"min": 0, "max": 77450, "rate": 3.75}, {"min": 77450, "max": 176050, "rate": 4.75}, {"min": 176050, "max": float("inf"), "rate": 5.99}], "note": "Rhode Island offers a flat alternative tax for small business owners.", "std_deduction": {"single": 10550, "mfj": 21150}},
    "south-carolina": {"name": "South Carolina", "abbr": "SC", "type": "graduated", "rates": [{"min": 0, "max": 3460, "rate": 0}, {"min": 3460, "max": 17330, "rate": 3.0}, {"min": 17330, "max": float("inf"), "rate": 6.2}], "note": "South Carolina exempts the first $3,460 of income from tax.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "south-dakota": {"name": "South Dakota", "abbr": "SD", "type": "none", "note": "South Dakota has no state income tax. The state relies on sales tax and tourism-related revenue."},
    "tennessee": {"name": "Tennessee", "abbr": "TN", "type": "none", "note": "Tennessee eliminated its Hall Tax on investment income in 2021 and now has no state income tax."},
    "texas": {"name": "Texas", "abbr": "TX", "type": "none", "note": "Texas has no state income tax, enshrined in the state constitution. The state funds services primarily through property and sales taxes."},
    "utah": {"name": "Utah", "abbr": "UT", "type": "flat", "rate": 4.55, "note": "Utah applies its flat rate to all income but offers a taxpayer credit that effectively exempts lower earners.", "std_deduction": {"single": 14600, "mfj": 29200}},
    "vermont": {"name": "Vermont", "abbr": "VT", "type": "graduated", "rates": [{"min": 0, "max": 45400, "rate": 3.35}, {"min": 45400, "max": 110050, "rate": 6.6}, {"min": 110050, "max": 229550, "rate": 7.6}, {"min": 229550, "max": float("inf"), "rate": 8.75}], "note": "Vermont bases its income tax on federal adjusted gross income with Vermont-specific adjustments.", "std_deduction": {"single": 7000, "mfj": 14000}},
    "virginia": {"name": "Virginia", "abbr": "VA", "type": "graduated", "rates": [{"min": 0, "max": 3000, "rate": 2.0}, {"min": 3000, "max": 5000, "rate": 3.0}, {"min": 5000, "max": 17000, "rate": 5.0}, {"min": 17000, "max": float("inf"), "rate": 5.75}], "note": "Virginia has not significantly changed its tax brackets in decades, making bracket creep a factor for many residents.", "std_deduction": {"single": 4500, "mfj": 9000}},
    "washington": {"name": "Washington", "abbr": "WA", "type": "none", "note": "Washington has no state income tax but levies a 7% tax on capital gains over $250,000 (upheld by the state supreme court in 2023)."},
    "west-virginia": {"name": "West Virginia", "abbr": "WV", "type": "graduated", "rates": [{"min": 0, "max": 10000, "rate": 2.36}, {"min": 10000, "max": 25000, "rate": 3.15}, {"min": 25000, "max": 40000, "rate": 3.54}, {"min": 40000, "max": 60000, "rate": 4.72}, {"min": 60000, "max": float("inf"), "rate": 5.12}], "note": "West Virginia has been gradually reducing rates with a goal of eventually eliminating the income tax.", "std_deduction": {"single": 0, "mfj": 0}},
    "wisconsin": {"name": "Wisconsin", "abbr": "WI", "type": "graduated", "rates": [{"min": 0, "max": 14320, "rate": 3.5}, {"min": 14320, "max": 28640, "rate": 4.4}, {"min": 28640, "max": 315310, "rate": 5.3}, {"min": 315310, "max": float("inf"), "rate": 7.65}], "note": "Wisconsin allows a deduction for up to $12,760 of retirement income.", "std_deduction": {"single": 13230, "mfj": 24500}},
    "wyoming": {"name": "Wyoming", "abbr": "WY", "type": "none", "note": "Wyoming has no state income tax. Like Alaska, it benefits from energy sector revenue."},
    "dc": {"name": "Washington D.C.", "abbr": "DC", "type": "graduated", "rates": [{"min": 0, "max": 10000, "rate": 4.0}, {"min": 10000, "max": 40000, "rate": 6.0}, {"min": 40000, "max": 60000, "rate": 6.5}, {"min": 60000, "max": 250000, "rate": 8.5}, {"min": 250000, "max": 500000, "rate": 9.25}, {"min": 500000, "max": 1000000, "rate": 9.75}, {"min": 1000000, "max": float("inf"), "rate": 10.75}], "note": "D.C. is not a state but has its own tax system. Its top rate of 10.75% rivals the highest state rates.", "std_deduction": {"single": 14600, "mfj": 29200}},
}


def build_state_tax_js(state_data):
    """Build JS for state tax calculation."""
    slug = state_data["slug"]
    name = state_data["name"]
    abbr = state_data["abbr"]
    tax_type = state_data["type"]

    if tax_type == "none":
        return f"""
    // {name} has no state income tax
    var STATE_TAX_TYPE = 'none';
    var STATE_NAME = '{name}';
    var STATE_ABBR = '{abbr}';

    function calcStateTax(income, filing) {{
      return 0;
    }}

    function getStateMarginalRate(income) {{
      return 0;
    }}

    function buildStateBracketBreakdown(income) {{
      return '<tr><td colspan="4" style="padding:8px;text-align:center;color:var(--text-muted);">{name} has no state income tax</td></tr>';
    }}
"""
    elif tax_type == "flat":
        rate = state_data["rate"]
        return f"""
    var STATE_TAX_TYPE = 'flat';
    var STATE_NAME = '{name}';
    var STATE_ABBR = '{abbr}';
    var STATE_FLAT_RATE = {rate / 100};

    function calcStateTax(income, filing) {{
      return income * STATE_FLAT_RATE;
    }}

    function getStateMarginalRate(income) {{
      return STATE_FLAT_RATE;
    }}

    function buildStateBracketBreakdown(income) {{
      if (income <= 0) return '';
      var tax = income * STATE_FLAT_RATE;
      return '<tr><td>{rate}%</td><td>All income</td><td>' + fmt(income) + '</td><td>' + fmt(tax) + '</td></tr>';
    }}
"""
    else:  # graduated
        rates_js = json.dumps([
            {"min": r["min"], "max": "Infinity" if r["max"] == float("inf") else r["max"], "rate": r["rate"] / 100}
            for r in state_data["rates"]
        ])
        # Fix Infinity in JSON
        rates_js = rates_js.replace('"Infinity"', 'Infinity')
        return f"""
    var STATE_TAX_TYPE = 'graduated';
    var STATE_NAME = '{name}';
    var STATE_ABBR = '{abbr}';
    var STATE_BRACKETS = {rates_js};

    function calcStateTax(income, filing) {{
      var tax = 0;
      for (var i = 0; i < STATE_BRACKETS.length; i++) {{
        var b = STATE_BRACKETS[i];
        if (income <= b.min) break;
        tax += (Math.min(income, b.max) - b.min) * b.rate;
      }}
      return tax;
    }}

    function getStateMarginalRate(income) {{
      for (var i = STATE_BRACKETS.length - 1; i >= 0; i--) {{
        if (income > STATE_BRACKETS[i].min) return STATE_BRACKETS[i].rate;
      }}
      return STATE_BRACKETS[0].rate;
    }}

    function buildStateBracketBreakdown(income) {{
      var rows = '';
      for (var i = 0; i < STATE_BRACKETS.length; i++) {{
        var b = STATE_BRACKETS[i];
        if (income <= b.min) break;
        var taxable = Math.min(income, b.max) - b.min;
        var tax = taxable * b.rate;
        var range = fmt(b.min) + ' \\u2013 ' + (b.max === Infinity ? '\\u221e' : fmt(b.max));
        rows += '<tr><td>' + (b.rate * 100).toFixed(2) + '%</td><td>' + range + '</td><td>' + fmt(taxable) + '</td><td>' + fmt(tax) + '</td></tr>';
      }}
      return rows;
    }}
"""


def get_state_description(state_data):
    """Generate meta description for a state."""
    name = state_data["name"]
    tax_type = state_data["type"]
    if tax_type == "none":
        return f"Calculate your total tax in {name} \u2014 federal only, since {name} has no state income tax. See brackets, effective rate, and take-home pay. Free and private."
    elif tax_type == "flat":
        rate = state_data["rate"]
        return f"Calculate your {name} income tax ({rate}% flat rate) plus federal tax. See combined brackets, effective rate, and take-home pay. Free and private."
    else:
        top_rate = state_data["rates"][-1]["rate"]
        return f"Calculate your {name} income tax (up to {top_rate}%) plus federal tax. See combined brackets, effective rate, and take-home pay. Free and private."


def get_content_section(state_data):
    """Generate SEO content for a state page."""
    name = state_data["name"]
    abbr = state_data["abbr"]
    tax_type = state_data["type"]
    note = state_data.get("note", "")

    if tax_type == "none":
        content = f"""      <h2>{name} Income Tax: No State Tax</h2>
      <p>{name} is one of the few states with no state income tax. Residents of {name} only pay federal income tax on their earnings. {note}</p>
      <p>While {name} does not tax income, residents still owe federal income tax using the standard IRS brackets. The 2026 federal rates range from 10% to 37% depending on your taxable income and filing status. This calculator shows your complete federal tax breakdown for {name} residents.</p>

      <h2>Tax Advantages of Living in {name}</h2>
      <p>Without state income tax, {name} residents keep more of their earnings compared to states like California (13.3% top rate) or New York (10.9%). For someone earning $100,000, the difference can be $5,000 to $10,000 per year in savings. This makes {name} especially attractive for high earners, retirees, and remote workers choosing where to live.</p>
      <p>However, {name} may offset the lack of income tax through higher property taxes, sales taxes, or other fees. It is important to consider your total tax burden, not just income tax, when comparing states.</p>

      <h2>Filing Tips for {name} Residents</h2>
      <p>Since there is no state return to file, {name} residents only need to submit their federal tax return. Focus your tax planning on maximizing federal deductions: contribute to a 401(k) or IRA, use your HSA, and take the higher of the standard or itemized deduction. The 2026 standard deduction is $15,700 for single filers and $31,400 for married filing jointly.</p>"""
    elif tax_type == "flat":
        rate = state_data["rate"]
        content = f"""      <h2>{name} Income Tax: {rate}% Flat Rate</h2>
      <p>{name} uses a flat income tax rate of {rate}%, meaning all taxable income is taxed at the same rate regardless of how much you earn. {note}</p>
      <p>On top of the {rate}% state tax, {name} residents also pay federal income tax ranging from 10% to 37%. This calculator combines both federal and {name} state tax to show your total liability, effective rate, and take-home pay.</p>

      <h2>How {name}'s Flat Tax Compares</h2>
      <p>A flat tax simplifies filing \u2014 you pay {rate}% on all taxable income without navigating multiple brackets. Compared to the national median top state rate of around 5.5%, {name}'s {rate}% rate is {'below' if rate < 5.5 else 'above'} average. For a single filer earning $100,000, the {name} state tax would be approximately ${int(100000 * rate / 100):,}.</p>
      <p>States with flat taxes tend to have simpler returns and more predictable tax bills. The trade-off is that lower-income residents pay the same percentage as higher earners, unlike graduated systems where rates increase with income.</p>

      <h2>Reducing Your {name} Tax Bill</h2>
      <p>While you cannot change the flat rate, you can reduce your taxable income. Contributions to traditional 401(k) and IRA accounts reduce both your federal and {name} state taxable income. The 2026 401(k) limit is $24,500 ($32,500 with catch-up for age 50+). HSA contributions are also pre-tax for both federal and state purposes in most states.</p>"""
    else:
        rates = state_data["rates"]
        top_rate = rates[-1]["rate"]
        num_brackets = len(rates)
        content = f"""      <h2>{name} Income Tax: Graduated Brackets Up to {top_rate}%</h2>
      <p>{name} uses a progressive income tax system with {num_brackets} brackets. Rates range from {rates[0]['rate']}% to {top_rate}%, with higher income taxed at higher rates. {note}</p>
      <p>Like federal taxes, {name}'s system is marginal \u2014 only the income within each bracket is taxed at that bracket's rate. Combined with federal taxes (10%\u201337%), {name} residents can face a total marginal rate of up to {top_rate + 37}% on their highest dollars of income.</p>

      <h2>{name} Tax Brackets for 2026 (Single Filer)</h2>
      <p>The {name} income tax brackets for single filers are:</p>
      <ul>"""
        for r in rates:
            max_str = f"${r['max']:,.0f}" if r["max"] != float("inf") else "and above"
            if r["max"] == float("inf"):
                content += f"\n        <li><strong>{r['rate']}%</strong> on income over ${r['min']:,.0f}</li>"
            else:
                content += f"\n        <li><strong>{r['rate']}%</strong> on income from ${r['min']:,.0f} to ${r['max']:,.0f}</li>"
        content += f"""
      </ul>
      <p>Your marginal rate is the rate on your last dollar of income. Your effective rate (total tax divided by total income) is always lower because of the progressive structure.</p>

      <h2>Tips to Lower Your {name} Tax</h2>
      <p>Maximize pre-tax retirement contributions to reduce both federal and {name} taxable income. The 2026 401(k) limit is $24,500 ($32,500 with catch-up for age 50+). If {name} conforms to federal deductions, your standard deduction and itemized expenses also reduce your state tax liability.</p>"""

    return content


def get_faqs(state_data):
    """Generate FAQs for a state."""
    name = state_data["name"]
    tax_type = state_data["type"]

    faqs = []
    if tax_type == "none":
        faqs = [
            {"q": f"Does {name} have a state income tax?", "a": f"No. {name} has no state income tax. Residents only pay federal income tax."},
            {"q": f"What taxes do {name} residents pay?", "a": f"{name} residents pay federal income tax (10%-37%), Social Security (6.2%), and Medicare (1.45%). The state may also levy property taxes, sales taxes, and other fees."},
            {"q": f"Is {name} a good state for taxes?", "a": f"For income tax purposes, yes \u2014 {name} is one of the most tax-friendly states. However, the overall tax burden depends on property taxes, sales taxes, and cost of living."},
            {"q": f"Do I still need to file a state return in {name}?", "a": f"No. Since {name} has no state income tax, you only need to file a federal return with the IRS."},
            {"q": f"How does {name} fund state services without income tax?", "a": f"{name} relies on other revenue sources such as sales tax, property tax, energy revenues, or tourism taxes to fund state services."},
        ]
    elif tax_type == "flat":
        rate = state_data["rate"]
        faqs = [
            {"q": f"What is {name}'s income tax rate?", "a": f"{name} has a flat income tax rate of {rate}%. All taxable income is taxed at this rate regardless of how much you earn."},
            {"q": f"How much state tax will I pay in {name} on $100,000?", "a": f"On $100,000 of taxable income, you would pay approximately ${int(100000 * rate / 100):,} in {name} state income tax ({rate}% flat rate), plus federal tax."},
            {"q": f"Does {name} allow standard deductions?", "a": f"{'Yes' if state_data.get('std_deduction', {}).get('single', 0) > 0 else 'No, ' + name + ' does not offer a state standard deduction. Tax is calculated on all taxable income'}."},
            {"q": f"Is {name}'s tax rate competitive?", "a": f"At {rate}%, {name}'s flat rate is {'below' if rate < 5.0 else 'above'} the national average top state rate of about 5.5%. {'This makes it relatively tax-friendly.' if rate < 5.0 else 'Some states have lower rates or no income tax.'}"},
            {"q": f"Can I reduce my {name} state tax?", "a": f"Yes. Contributions to traditional 401(k), IRA, and HSA accounts reduce your taxable income for both federal and {name} state purposes."},
        ]
    else:
        top_rate = state_data["rates"][-1]["rate"]
        num_brackets = len(state_data["rates"])
        faqs = [
            {"q": f"What is {name}'s top income tax rate?", "a": f"{name}'s top marginal income tax rate is {top_rate}%. The state has {num_brackets} tax brackets with rates ranging from {state_data['rates'][0]['rate']}% to {top_rate}%."},
            {"q": f"How does {name}'s income tax work?", "a": f"{name} uses a progressive system where income is taxed at increasing rates through {num_brackets} brackets. Only income within each bracket is taxed at that bracket's rate."},
            {"q": f"How much total tax will I pay in {name}?", "a": f"Your total tax includes both federal (10%-37%) and {name} state tax (up to {top_rate}%). Use this calculator to see the combined amount, effective rate, and take-home pay."},
            {"q": f"Does {name} conform to federal deductions?", "a": f"Many states base their tax on federal adjusted gross income with state-specific modifications. Check {name}'s specific rules for how deductions and exemptions apply."},
            {"q": f"How can I lower my {name} state income tax?", "a": f"Maximize pre-tax retirement contributions (401k, IRA), use your HSA, and ensure you take all available deductions. These reduce both federal and state taxable income."},
        ]

    return faqs


def get_related_tools(state_slug):
    """Get related tools for a state page."""
    return [
        {"slug": "us/income-tax-calculator", "name": "US Federal Income Tax Calculator", "description": "Calculate federal income tax only."},
        {"slug": "us/paycheck-calculator", "name": "US Paycheck Calculator", "description": "Estimate your net paycheck after all deductions."},
        {"slug": "us/capital-gains-tax-calculator", "name": "Capital Gains Tax Calculator", "description": "Calculate federal and state capital gains tax."},
        {"slug": "career/take-home-pay-estimator", "name": "Take-Home Pay Estimator", "description": "Calculate your net pay after all deductions."},
        {"slug": "us/401k-paycheck-calculator", "name": "401(k) Paycheck Calculator", "description": "See how 401(k) contributions affect your paycheck."},
        {"slug": "evergreen/bonus-tax-estimator", "name": "Bonus Tax Estimator", "description": "Estimate federal tax on bonus income."},
    ]


def generate_state_page(state_slug, state_data, dry_run=False):
    """Generate a single state income tax calculator page."""
    name = state_data["name"]
    abbr = state_data["abbr"]
    slug = f"us/income-tax-calculator-{state_slug}"
    title = f"{name} Income Tax Calculator 2026"
    desc = get_state_description(state_data)
    # Trim description to 155 chars
    if len(desc) > 155:
        desc = desc[:152] + "..."

    title_tag = f"{title} \u2014 Teamz Lab Tools"
    if len(title_tag) > 60:
        title_tag = f"{abbr} Income Tax Calculator 2026 \u2014 Teamz Lab Tools"

    faqs = get_faqs(state_data)
    faqs_js = json.dumps(faqs, indent=6)
    related = get_related_tools(state_slug)
    related_js = json.dumps(related, indent=6)
    content_html = get_content_section(state_data)
    state_tax_js = build_state_tax_js({"slug": state_slug, **state_data})

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_tag}</title>
  <meta name="description" content="{desc}">
  <meta property="og:title" content="{title_tag}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{SITE_URL}/{slug}/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Teamz Lab Tools">
  <meta property="og:image" content="{SITE_URL}/og-images/us.png">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{title_tag}">
  <meta name="twitter:description" content="{desc}">
  <link rel="canonical" href="{SITE_URL}/{slug}/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/branding/css/teamz-branding.css">
  <link rel="stylesheet" href="/shared/css/tools.css">
</head>
<body>
  <header id="site-header" class="site-header"></header>
  <main class="site-main">
    <div id="breadcrumbs"></div>
    <section class="tool-hero">
      <h1>{title}</h1>
      <p class="tool-description">Calculate your combined federal and {name} state income tax for 2026. See your federal brackets, {name} tax, effective rate, and take-home pay \u2014 all calculated privately in your browser.</p>
    </section>
    <section id="tool-calculator" class="tool-calculator"></section>
    <div class="ad-slot">Ad Space</div>
    <section class="tool-content">
{content_html}
    </section>
    <section id="tool-faqs"></section>
    <section id="related-tools"></section>
  </main>
  <footer id="site-footer" class="site-footer"></footer>
  <script src="/branding/js/theme.js"></script>
  <script src="/shared/js/common.js"></script>
  <script src="/shared/js/tool-engine.js"></script>
  <script>
    var BRACKETS_SINGLE = [
      {{ min: 0, max: 11925, rate: 0.10 }},
      {{ min: 11925, max: 48475, rate: 0.12 }},
      {{ min: 48475, max: 103350, rate: 0.22 }},
      {{ min: 103350, max: 197300, rate: 0.24 }},
      {{ min: 197300, max: 250525, rate: 0.32 }},
      {{ min: 250525, max: 626350, rate: 0.35 }},
      {{ min: 626350, max: Infinity, rate: 0.37 }}
    ];
    var BRACKETS_MFJ = [
      {{ min: 0, max: 23850, rate: 0.10 }},
      {{ min: 23850, max: 96950, rate: 0.12 }},
      {{ min: 96950, max: 206700, rate: 0.22 }},
      {{ min: 206700, max: 394600, rate: 0.24 }},
      {{ min: 394600, max: 501050, rate: 0.32 }},
      {{ min: 501050, max: 751600, rate: 0.35 }},
      {{ min: 751600, max: Infinity, rate: 0.37 }}
    ];
    var BRACKETS_MFS = [
      {{ min: 0, max: 11925, rate: 0.10 }},
      {{ min: 11925, max: 48475, rate: 0.12 }},
      {{ min: 48475, max: 103350, rate: 0.22 }},
      {{ min: 103350, max: 197300, rate: 0.24 }},
      {{ min: 197300, max: 250525, rate: 0.32 }},
      {{ min: 250525, max: 375800, rate: 0.35 }},
      {{ min: 375800, max: Infinity, rate: 0.37 }}
    ];
    var BRACKETS_HOH = [
      {{ min: 0, max: 17000, rate: 0.10 }},
      {{ min: 17000, max: 64850, rate: 0.12 }},
      {{ min: 64850, max: 103350, rate: 0.22 }},
      {{ min: 103350, max: 197300, rate: 0.24 }},
      {{ min: 197300, max: 250500, rate: 0.32 }},
      {{ min: 250500, max: 626350, rate: 0.35 }},
      {{ min: 626350, max: Infinity, rate: 0.37 }}
    ];

    var STD_DEDUCTIONS = {{
      single: 15700,
      mfj: 31400,
      mfs: 15700,
      hoh: 23500
    }};

    function getBrackets(filing) {{
      if (filing === 'mfj') return BRACKETS_MFJ;
      if (filing === 'mfs') return BRACKETS_MFS;
      if (filing === 'hoh') return BRACKETS_HOH;
      return BRACKETS_SINGLE;
    }}

    function calcTax(income, brackets) {{
      var tax = 0;
      for (var i = 0; i < brackets.length; i++) {{
        var b = brackets[i];
        if (income <= b.min) break;
        tax += (Math.min(income, b.max) - b.min) * b.rate;
      }}
      return tax;
    }}

    function getMarginalRate(income, brackets) {{
      for (var i = brackets.length - 1; i >= 0; i--) {{
        if (income > brackets[i].min) return brackets[i].rate;
      }}
      return brackets[0].rate;
    }}

    function buildBracketBreakdown(income, brackets) {{
      var rows = [];
      for (var i = 0; i < brackets.length; i++) {{
        var b = brackets[i];
        if (income <= b.min) break;
        var taxableInBracket = Math.min(income, b.max) - b.min;
        var taxInBracket = taxableInBracket * b.rate;
        var rangeLabel = fmt(b.min) + ' \\u2013 ' + (b.max === Infinity ? '\\u221e' : fmt(b.max));
        rows.push('<tr><td>' + (b.rate * 100) + '%</td><td>' + rangeLabel + '</td><td>' + fmt(taxableInBracket) + '</td><td>' + fmt(taxInBracket) + '</td></tr>');
      }}
      return rows.join('');
    }}

    function fmt(n) {{ return '$' + Math.round(n).toLocaleString(); }}
    function pct(n) {{ return (n * 100).toFixed(1) + '%'; }}

    // --- {name} State Tax ---
    {state_tax_js}

    var TOOL_CONFIG = {{
      slug: '{slug}',
      title: '{title}',
      description: 'Calculate combined federal and {name} state income tax for 2026.',
      inputs: [
        {{ id: 'income', type: 'number', label: 'Annual Income ($)', placeholder: 'e.g. 85000', min: 1, step: 1000, error: 'Enter your annual income.' }},
        {{ id: 'filing', type: 'select', label: 'Filing Status', options: [
          {{ value: 'single', label: 'Single' }},
          {{ value: 'mfj', label: 'Married Filing Jointly' }},
          {{ value: 'mfs', label: 'Married Filing Separately' }},
          {{ value: 'hoh', label: 'Head of Household' }}
        ], default: 'single' }},
        {{ id: 'deductionType', type: 'select', label: 'Deduction Type', options: [
          {{ value: 'standard', label: 'Standard Deduction' }},
          {{ value: 'itemized', label: 'Itemized Deduction' }}
        ], default: 'standard' }},
        {{ id: 'itemizedAmount', type: 'number', label: 'Itemized Deduction Amount ($)', placeholder: 'e.g. 25000', min: 0, step: 500, default: 0 }},
        {{ id: 'dependents', type: 'number', label: 'Number of Dependents', placeholder: '0', min: 0, max: 20, step: 1, default: 0 }}
      ],
      calculate: function(v) {{
        if (!v.income) return null;
        var income = v.income;
        var filing = v.filing || 'single';
        var deductionType = v.deductionType || 'standard';
        var dependents = v.dependents || 0;
        var brackets = getBrackets(filing);

        var deduction;
        if (deductionType === 'itemized' && v.itemizedAmount > 0) {{
          deduction = v.itemizedAmount;
        }} else {{
          deduction = STD_DEDUCTIONS[filing] || STD_DEDUCTIONS.single;
        }}

        var taxableIncome = Math.max(income - deduction, 0);
        var federalTax = calcTax(taxableIncome, brackets);

        var childCredit = dependents * 2000;
        federalTax = Math.max(federalTax - childCredit, 0);

        var stateTax = calcStateTax(taxableIncome, filing);
        var totalTax = federalTax + stateTax;

        var effectiveRate = income > 0 ? totalTax / income : 0;
        var federalEffective = income > 0 ? federalTax / income : 0;
        var stateEffective = income > 0 ? stateTax / income : 0;
        var marginalRate = getMarginalRate(taxableIncome, brackets);
        var stateMarginal = getStateMarginalRate(taxableIncome);
        var takeHomeAnnual = income - totalTax;
        var takeHomeMonthly = takeHomeAnnual / 12;

        var fedBracketRows = buildBracketBreakdown(taxableIncome, brackets);
        var stateBracketRows = buildStateBracketBreakdown(taxableIncome);

        var tableStyle = 'width:100%;border-collapse:collapse;margin-top:12px;';
        var thStyle = 'border-bottom:2px solid var(--border);text-align:left;padding:8px;';
        var tableHead = '<thead><tr><th style="' + thStyle + '">Rate</th><th style="' + thStyle + '">Bracket Range</th><th style="' + thStyle + '">Taxable</th><th style="' + thStyle + '">Tax</th></tr></thead>';

        var html = '<h3 style="margin-top:20px;color:var(--heading);">Federal Tax Breakdown</h3>' +
          '<table style="' + tableStyle + '">' + tableHead + '<tbody>' + fedBracketRows + '</tbody></table>' +
          '<h3 style="margin-top:20px;color:var(--heading);">' + STATE_NAME + ' State Tax Breakdown</h3>' +
          '<table style="' + tableStyle + '">' + tableHead + '<tbody>' + stateBracketRows + '</tbody></table>';

        var items = [
          {{ label: 'Gross Income', value: fmt(income) }},
          {{ label: 'Deduction (' + (deductionType === 'itemized' ? 'Itemized' : 'Standard') + ')', value: fmt(deduction) }},
          {{ label: 'Taxable Income', value: fmt(taxableIncome) }}
        ];

        if (dependents > 0) {{
          items.push({{ label: 'Child Tax Credit (' + dependents + ' dep.)', value: '\\u2212' + fmt(childCredit) }});
        }}

        items.push(
          {{ label: 'Federal Tax', value: fmt(federalTax) + ' (' + pct(federalEffective) + ')' }},
          {{ label: STATE_NAME + ' State Tax', value: fmt(stateTax) + ' (' + pct(stateEffective) + ')' }},
          {{ label: 'Total Tax (Federal + State)', value: fmt(totalTax) }},
          {{ label: 'Combined Effective Rate', value: pct(effectiveRate) }},
          {{ label: 'Federal Marginal Bracket', value: pct(marginalRate) }},
          {{ label: STATE_NAME + ' Marginal Rate', value: pct(stateMarginal) }},
          {{ label: 'Take-Home Pay (Annual)', value: fmt(takeHomeAnnual) }},
          {{ label: 'Take-Home Pay (Monthly)', value: fmt(takeHomeMonthly) }}
        );

        var filingLabels = {{ single: 'Single', mfj: 'Married Filing Jointly', mfs: 'Married Filing Separately', hoh: 'Head of Household' }};

        return {{
          items: items,
          summary: 'On ' + fmt(income) + ' income (' + filingLabels[filing] + ') in ' + STATE_NAME + ', you owe ' + fmt(federalTax) + ' federal + ' + fmt(stateTax) + ' state = ' + fmt(totalTax) + ' total tax (effective ' + pct(effectiveRate) + '). Take-home: ' + fmt(takeHomeMonthly) + '/month.',
          html: html
        }};
      }}
    }};

    var BREADCRUMBS = [
      {{ name: 'Home', url: '/' }},
      {{ name: 'US Tools', url: '/us/' }},
      {{ name: '{name} Income Tax Calculator' }}
    ];

    var FAQS = {faqs_js};

    var RELATED_TOOLS = {related_js};

    document.addEventListener('DOMContentLoaded', function() {{
      TeamzTools.renderBreadcrumbs(BREADCRUMBS);
      TeamzTools.injectBreadcrumbSchema(BREADCRUMBS);
      TeamzTools.injectFAQSchema(FAQS);
      TeamzTools.injectWebAppSchema(TOOL_CONFIG);
      TeamzTools.renderFAQs(FAQS);
      TeamzTools.renderRelatedTools(RELATED_TOOLS);
      ToolEngine.init(TOOL_CONFIG);
    }});
  </script>
</body>
</html>
"""
    return page


def main():
    args = sys.argv[1:]

    if not args or "--help" in args:
        print(__doc__)
        return

    if "--list" in args:
        print("Available templates:")
        print("  us-income-tax  — US state income tax calculators (50 states + DC)")
        return

    dry_run = "--dry-run" in args
    template = [a for a in args if not a.startswith("--")]

    if not template:
        print("Error: specify a template name. Use --list to see options.")
        return

    template = template[0]

    if template == "us-income-tax":
        print(f"{'[DRY RUN] ' if dry_run else ''}Generating US state income tax calculator pages...")
        count = 0
        for state_slug, state_data in sorted(US_STATES.items()):
            page_dir = os.path.join(PROJECT_ROOT, "us", f"income-tax-calculator-{state_slug}")
            page_path = os.path.join(page_dir, "index.html")

            if dry_run:
                print(f"  Would create: /us/income-tax-calculator-{state_slug}/")
            else:
                os.makedirs(page_dir, exist_ok=True)
                page_content = generate_state_page(state_slug, state_data)
                with open(page_path, "w", encoding="utf-8") as f:
                    f.write(page_content)
                print(f"  Created: /us/income-tax-calculator-{state_slug}/")
            count += 1

        print(f"\n{'Would create' if dry_run else 'Created'} {count} state income tax calculator pages.")
        if not dry_run:
            print("\nNext steps:")
            print("  1. Add new tools to /us/index.html hub page")
            print("  2. Run: python3 build-static-schema.py")
            print("  3. Run: ./build-search-index.sh")
            print("  4. Run: ./build.sh")
    else:
        print(f"Unknown template: {template}")
        print("Use --list to see available templates.")


if __name__ == "__main__":
    main()
