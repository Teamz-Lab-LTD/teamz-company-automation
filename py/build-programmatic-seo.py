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


# ============================================================
# UK CARE HOME COMPLIANCE — LOCATION DATA
# ============================================================
# CQC-registered care homes by region/city (approximate, March 2025)
UK_CARE_LOCATIONS = {
    "london": {"name": "London", "region": "Greater London", "homes": 2150, "population": "8.8m"},
    "manchester": {"name": "Manchester", "region": "Greater Manchester", "homes": 680, "population": "2.8m"},
    "birmingham": {"name": "Birmingham", "region": "West Midlands", "homes": 520, "population": "1.1m"},
    "leeds": {"name": "Leeds", "region": "West Yorkshire", "homes": 340, "population": "793k"},
    "liverpool": {"name": "Liverpool", "region": "Merseyside", "homes": 310, "population": "486k"},
    "bristol": {"name": "Bristol", "region": "South West", "homes": 280, "population": "472k"},
    "sheffield": {"name": "Sheffield", "region": "South Yorkshire", "homes": 260, "population": "556k"},
    "newcastle": {"name": "Newcastle", "region": "North East", "homes": 240, "population": "302k"},
    "nottingham": {"name": "Nottingham", "region": "East Midlands", "homes": 220, "population": "323k"},
    "brighton": {"name": "Brighton", "region": "South East", "homes": 200, "population": "290k"},
    "leicester": {"name": "Leicester", "region": "East Midlands", "homes": 190, "population": "354k"},
    "coventry": {"name": "Coventry", "region": "West Midlands", "homes": 170, "population": "345k"},
    "bradford": {"name": "Bradford", "region": "West Yorkshire", "homes": 180, "population": "546k"},
    "cardiff": {"name": "Cardiff", "region": "Wales", "homes": 160, "population": "362k"},
    "edinburgh": {"name": "Edinburgh", "region": "Scotland", "homes": 190, "population": "527k"},
    "glasgow": {"name": "Glasgow", "region": "Scotland", "homes": 210, "population": "635k"},
    "southampton": {"name": "Southampton", "region": "South East", "homes": 150, "population": "252k"},
    "plymouth": {"name": "Plymouth", "region": "South West", "homes": 130, "population": "264k"},
    "stoke-on-trent": {"name": "Stoke-on-Trent", "region": "West Midlands", "homes": 140, "population": "256k"},
    "wolverhampton": {"name": "Wolverhampton", "region": "West Midlands", "homes": 120, "population": "254k"},
    "derby": {"name": "Derby", "region": "East Midlands", "homes": 110, "population": "257k"},
    "norwich": {"name": "Norwich", "region": "East of England", "homes": 140, "population": "144k"},
    "oxford": {"name": "Oxford", "region": "South East", "homes": 100, "population": "152k"},
    "cambridge": {"name": "Cambridge", "region": "East of England", "homes": 90, "population": "145k"},
    "york": {"name": "York", "region": "North Yorkshire", "homes": 110, "population": "211k"},
    "bath": {"name": "Bath", "region": "South West", "homes": 80, "population": "90k"},
    "exeter": {"name": "Exeter", "region": "South West", "homes": 90, "population": "131k"},
    "cheltenham": {"name": "Cheltenham", "region": "South West", "homes": 70, "population": "117k"},
    "reading": {"name": "Reading", "region": "South East", "homes": 85, "population": "174k"},
    "bournemouth": {"name": "Bournemouth", "region": "South West", "homes": 160, "population": "183k"},
    "blackpool": {"name": "Blackpool", "region": "North West", "homes": 120, "population": "140k"},
    "sunderland": {"name": "Sunderland", "region": "North East", "homes": 100, "population": "274k"},
    "hull": {"name": "Hull", "region": "East Yorkshire", "homes": 110, "population": "260k"},
    "middlesbrough": {"name": "Middlesbrough", "region": "North East", "homes": 90, "population": "140k"},
    "wigan": {"name": "Wigan", "region": "Greater Manchester", "homes": 100, "population": "326k"},
    "kent": {"name": "Kent", "region": "South East", "homes": 480, "population": "1.8m"},
    "essex": {"name": "Essex", "region": "East of England", "homes": 520, "population": "1.5m"},
    "surrey": {"name": "Surrey", "region": "South East", "homes": 380, "population": "1.2m"},
    "hampshire": {"name": "Hampshire", "region": "South East", "homes": 420, "population": "1.4m"},
    "devon": {"name": "Devon", "region": "South West", "homes": 350, "population": "795k"},
}


def generate_uk_care_page(slug, data):
    """Generate a UK care home compliance tool page for a specific location."""
    import html as html_module
    name = data["name"]
    region = data["region"]
    homes = data["homes"]
    pop = data["population"]

    title = f"Care Home Compliance Software {name} — Free CQC Tool"
    meta_desc = f"Free care home compliance software for {name}, {region}. Track CQC readiness across 21 categories for {homes}+ care homes in {name}. Record evidence in 60 seconds, generate inspection packs."
    h1 = f"Care Home Compliance Software for {name}"
    canonical = f"{SITE_URL}/uk-care/care-home-compliance-{slug}/"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Teamz Lab Tools</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Teamz Lab Tools">
<meta property="og:image" content="{SITE_URL}/og-images/uk-care.png">
<link rel="stylesheet" href="/branding/css/teamz-branding.css">
<link rel="stylesheet" href="/shared/css/tools.css">
</head>
<body>
<script src="/branding/js/theme.js"></script>

<div class="site-main">
<nav class="breadcrumbs" id="breadcrumbs"></nav>

<article class="tool-article">
<h1>{h1}</h1>
<p class="tool-intro">Free CQC compliance evidence software for the {homes}+ registered care homes in {name}, {region}. AlwaysReady Care helps care homes capture, structure, review, and export inspection-ready evidence — mapped to CQC's 5 key questions and 21 compliance categories.</p>

<div class="tool-calculator" id="tool-calculator">
  <div class="tool-calculator-section">
    <h2>Try AlwaysReady Care for {name}</h2>
    <p>Record care evidence in 60 seconds. AI structures your notes. Generate CQC inspection packs in one click. No rip-and-replace — works alongside your existing care planning system.</p>

    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:20px 0;">
      <a href="https://always-ready-care.web.app/" class="btn-primary" style="display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:12px;background:#D9FE06;color:#12151A;font-weight:600;text-decoration:none;font-size:15px;">
        Get Started Free
      </a>
      <a href="https://wa.me/447490356046?text=Hi%2C%20I%20run%20a%20care%20home%20in%20{name}%20and%20I%27d%20like%20a%20demo%20of%20AlwaysReady%20Care." class="btn-secondary" style="display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:12px;border:1px solid;text-decoration:none;font-size:15px;" target="_blank" rel="noopener">
        Book a Demo
      </a>
    </div>

    <div class="tool-result" id="tool-result">
      <h3>CQC Compliance Categories Tracked</h3>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin:16px 0;">
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Safe</strong><br>Medication, Safeguarding, Incidents, Infection Control, Risk Assessment, Falls</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Effective</strong><br>Care Planning, Nutrition, Health Monitoring, MCA/DoLS, Staff Training</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Caring</strong><br>Personal Care, Activities, Communication &amp; Engagement</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Responsive</strong><br>Complaints, End of Life, Person-Centred Care</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Well-led</strong><br>Governance, Supervision, Night Care, Duty of Candour</div>
      </div>
    </div>
  </div>
</div>

<div class="ad-slot">Ad Space</div>

<section class="tool-content">

<h2>CQC Compliance for Care Homes in {name}</h2>
<p>{name} in {region} has approximately {homes} CQC-registered care homes serving a population of {pop}. These include care homes with and without nursing, domiciliary care providers, and supported living services. Every one of these locations must maintain continuous compliance evidence across CQC's 5 key questions: Safe, Effective, Caring, Responsive, and Well-led.</p>
<p>AlwaysReady Care is a free compliance evidence layer designed specifically for UK care homes in {name} and across England. It doesn't replace your existing care planning system — it works alongside Person Centred Software, Nourish Care, Log my Care, Care Control, Birdie, and any other platform you already use.</p>

<h2>How {name} Care Homes Use AlwaysReady Care</h2>
<p>Care workers in {name} use AlwaysReady Care to record evidence during or immediately after providing care. With 12 pre-built templates covering medication administration, personal care, meals, incidents, safeguarding, night care, staff supervision, and more, recording takes under 60 seconds. AI automatically structures messy handover notes into CQC-ready format, suggests compliance tags, flags risks, and recommends follow-up actions.</p>
<p>Managers and deputy managers see a live compliance readiness dashboard showing which of the 21 CQC categories have gaps. When CQC inspects a {name} care home, the manager generates a professional inspection pack in one click — filtered by date range, evidence type, or compliance area.</p>

<h2>Why Care Homes in {name} Need Digital Compliance</h2>
<p>The most common reason CQC rates care homes in {name} as "Requires Improvement" is weak governance under Regulation 17 — specifically, poor record-keeping and scattered evidence across paper notes, WhatsApp messages, and Excel spreadsheets. AlwaysReady Care solves this by centralising all compliance evidence in one searchable, auditable, inspection-ready system.</p>
<p>For multi-site operators in {region}, the platform provides group-level visibility so nominated individuals and quality directors can spot compliance gaps before inspectors do.</p>

<h2>Get Started in {name}</h2>
<p>AlwaysReady Care is free to start. No credit card required. No installation — it works in your browser and can be installed as an app on your phone. Your team can be recording CQC-ready evidence within 5 minutes.</p>

</section>

<div id="tool-faqs"></div>
<div id="related-tools"></div>
</article>
</div>

<script src="/shared/js/common.js"></script>
<script>
TeamzTools.renderBreadcrumbs([
  {{ name: 'Home', url: '/' }},
  {{ name: 'UK Care', url: '/uk-care/' }},
  {{ name: '{name}' }}
]);

TeamzTools.renderFAQs([
  {{ q: 'How many CQC-registered care homes are in {name}?', a: 'There are approximately {homes} CQC-registered care home and care service locations in {name}, {region}. This includes residential care homes, nursing homes, domiciliary care agencies, and supported living services.' }},
  {{ q: 'What is the best compliance software for care homes in {name}?', a: 'AlwaysReady Care is a free compliance evidence layer designed for UK care homes. It tracks 21 CQC categories mapped to the 5 key questions, with AI-assisted evidence structuring, follow-up action tracking, and one-click inspection pack generation.' }},
  {{ q: 'How do I prepare my {name} care home for a CQC inspection?', a: 'Start by ensuring you have recent evidence across all compliance categories: medication, personal care, safeguarding, incidents, nutrition, activities, health monitoring, and governance. AlwaysReady Care shows your readiness score in real-time and highlights gaps before an inspector finds them.' }},
  {{ q: 'Does AlwaysReady Care work with other care home software?', a: 'Yes. AlwaysReady Care works alongside Person Centred Software, Nourish Care, Log my Care, Care Control, Birdie, CareDocs, StoriiCare, and any care planning system. It is not a replacement — it is a compliance evidence layer on top of your existing tools.' }},
  {{ q: 'Is this care home software free?', a: 'AlwaysReady Care is free to start with evidence capture, compliance tracking, and inspection pack generation for up to 3 staff. Pro plans with all 12 templates, AI structuring, and unlimited staff start from \\u00a379 per care home per month.' }}
]);
TeamzTools.injectFAQSchema();

TeamzTools.renderRelatedTools([
  {{ slug: '/uk-care/', name: 'All UK Care Home Tools', description: 'Browse all care home compliance tools by region' }},
  {{ slug: '/compliance/', name: 'Compliance Tools', description: 'Audit checklists, risk assessments, and policy generators' }},
  {{ slug: '/eldercare/', name: 'Elder Care Tools', description: 'Calculators and tools for elderly care providers' }},
  {{ slug: '/health/', name: 'Health Tools', description: 'Health calculators, BMI, medication, and wellness tools' }},
  {{ slug: '/career/', name: 'Career Tools', description: 'Resume builders, interview prep, and job search tools' }},
  {{ slug: '/tools/', name: 'All Tools', description: 'Browse 2000+ free browser-based tools' }}
]);

TeamzTools.injectWebAppSchema({{
  slug: 'uk-care/care-home-compliance-{slug}',
  title: '{title}',
  description: '{meta_desc}'
}});
</script>
</body>
</html>"""


def generate_uk_care_hub():
    """Generate the /uk-care/ hub page listing all location pages."""
    locations_html = ""
    for slug, data in sorted(UK_CARE_LOCATIONS.items(), key=lambda x: -x[1]["homes"]):
        locations_html += f'        <a href="/uk-care/care-home-compliance-{slug}/" class="hub-card"><h3>{data["name"]}</h3><p>{data["region"]} · {data["homes"]}+ care homes</p></a>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UK Care Home Compliance Software by Region — Free CQC Tools — Teamz Lab Tools</title>
<meta name="description" content="Free CQC compliance evidence software for UK care homes. Find care home compliance tools for your region — London, Manchester, Birmingham, Bristol, Leeds, and 35+ more UK locations.">
<link rel="canonical" href="{SITE_URL}/uk-care/">
<meta property="og:title" content="UK Care Home Compliance Software by Region">
<meta property="og:description" content="Free CQC compliance tools for care homes across the UK. 40 locations covered.">
<meta property="og:url" content="{SITE_URL}/uk-care/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Teamz Lab Tools">
<link rel="stylesheet" href="/branding/css/teamz-branding.css">
<link rel="stylesheet" href="/shared/css/tools.css">
</head>
<body>
<script src="/branding/js/theme.js"></script>
<div class="site-main">
<nav class="breadcrumbs" id="breadcrumbs"></nav>
<h1>UK Care Home Compliance Software</h1>
<p class="hub-intro">Free CQC compliance evidence software for care homes across the UK. Choose your region to see local care home data and get started with AlwaysReady Care.</p>
<div class="hub-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;margin:24px 0;">
{locations_html}
</div>
</div>
<script src="/shared/js/common.js"></script>
<script>
TeamzTools.renderBreadcrumbs([
  {{ name: 'Home', url: '/' }},
  {{ name: 'UK Care' }}
]);
</script>
</body>
</html>"""


# ============================================================
# AUSTRALIA — AGED CARE COMPLIANCE — LOCATION DATA
# ============================================================
AU_CARE_LOCATIONS = {
    "sydney": {"name": "Sydney", "region": "New South Wales", "homes": 420, "population": "5.3m"},
    "melbourne": {"name": "Melbourne", "region": "Victoria", "homes": 380, "population": "5.1m"},
    "brisbane": {"name": "Brisbane", "region": "Queensland", "homes": 280, "population": "2.6m"},
    "perth": {"name": "Perth", "region": "Western Australia", "homes": 180, "population": "2.1m"},
    "adelaide": {"name": "Adelaide", "region": "South Australia", "homes": 160, "population": "1.4m"},
    "gold-coast": {"name": "Gold Coast", "region": "Queensland", "homes": 120, "population": "680k"},
    "canberra": {"name": "Canberra", "region": "ACT", "homes": 40, "population": "460k"},
    "hobart": {"name": "Hobart", "region": "Tasmania", "homes": 45, "population": "240k"},
    "darwin": {"name": "Darwin", "region": "Northern Territory", "homes": 15, "population": "150k"},
    "newcastle-au": {"name": "Newcastle", "region": "New South Wales", "homes": 80, "population": "320k"},
    "wollongong": {"name": "Wollongong", "region": "New South Wales", "homes": 50, "population": "300k"},
    "geelong": {"name": "Geelong", "region": "Victoria", "homes": 45, "population": "270k"},
    "townsville": {"name": "Townsville", "region": "Queensland", "homes": 35, "population": "180k"},
    "cairns": {"name": "Cairns", "region": "Queensland", "homes": 30, "population": "160k"},
    "toowoomba": {"name": "Toowoomba", "region": "Queensland", "homes": 25, "population": "140k"},
    "ballarat": {"name": "Ballarat", "region": "Victoria", "homes": 25, "population": "110k"},
    "bendigo": {"name": "Bendigo", "region": "Victoria", "homes": 20, "population": "100k"},
    "launceston": {"name": "Launceston", "region": "Tasmania", "homes": 20, "population": "90k"},
    "new-south-wales": {"name": "New South Wales", "region": "NSW", "homes": 870, "population": "8.2m"},
    "victoria": {"name": "Victoria", "region": "VIC", "homes": 780, "population": "6.7m"},
}


def generate_au_care_page(slug, data):
    """Generate an Australian aged care compliance tool page for a specific location."""
    name = data["name"]
    region = data["region"]
    homes = data["homes"]
    pop = data["population"]

    title = f"Aged Care Compliance Software {name} — Free ACQSC Tool"
    meta_desc = f"Free aged care compliance software for {name}, {region}. Track ACQSC readiness across 7 strengthened quality standards for {homes}+ aged care homes in {name}. Record evidence in 60 seconds."
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152] + "..."
    h1 = f"Aged Care Compliance Software for {name}"
    canonical = f"{SITE_URL}/au-care/aged-care-compliance-{slug}/"

    return f"""<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Teamz Lab Tools</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en-AU" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Teamz Lab Tools">
<meta property="og:image" content="{SITE_URL}/og-images/au-care.png">
<link rel="stylesheet" href="/branding/css/teamz-branding.css">
<link rel="stylesheet" href="/shared/css/tools.css">
</head>
<body>
<script src="/branding/js/theme.js"></script>

<div class="site-main">
<nav class="breadcrumbs" id="breadcrumbs"></nav>

<article class="tool-article">
<h1>{h1}</h1>
<p class="tool-intro">Free ACQSC compliance evidence software for the {homes}+ registered aged care homes in {name}, {region}. AlwaysReady Care helps aged care providers capture, structure, review, and export audit-ready evidence — mapped to the 7 strengthened aged care quality standards introduced under the Aged Care Act 2024.</p>

<div class="tool-calculator" id="tool-calculator">
  <div class="tool-calculator-section">
    <h2>Try AlwaysReady Care for {name}</h2>
    <p>Record care evidence in 60 seconds. AI structures your notes. Generate compliance audit packs in one click. Works alongside your existing aged care software — no rip-and-replace required.</p>

    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:20px 0;">
      <a href="https://always-ready-care.web.app/" class="btn-primary" style="display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:12px;background:#D9FE06;color:#12151A;font-weight:600;text-decoration:none;font-size:15px;">
        Get Started Free
      </a>
      <a href="https://wa.me/447490356046?text=Hi%2C%20I%20run%20an%20aged%20care%20home%20in%20{name}%20and%20I%27d%20like%20a%20demo%20of%20AlwaysReady%20Care." class="btn-secondary" style="display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:12px;border:1px solid;text-decoration:none;font-size:15px;" target="_blank" rel="noopener">
        Book a Demo
      </a>
    </div>

    <div class="tool-result" id="tool-result">
      <h3>7 Strengthened Quality Standards Tracked</h3>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin:16px 0;">
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 1</strong><br>The Person — dignity, identity, culture, diversity</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 2</strong><br>The Organisation — governance, leadership, workforce</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 3</strong><br>The Care and Services — safe, effective, person-centred</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 4</strong><br>The Environment — safe, comfortable, homelike</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 5</strong><br>Clinical Care — medication, health monitoring, allied health</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 6</strong><br>Food and Nutrition — meals, hydration, dietary needs</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 7</strong><br>The Residential Community — activities, social connections, feedback</div>
      </div>
    </div>
  </div>
</div>

<div class="ad-slot">Ad Space</div>

<section class="tool-content">

<h2>Aged Care Compliance for Providers in {name}</h2>
<p>{name} in {region} has approximately {homes} registered aged care homes and services serving a population of {pop}. Under the Aged Care Act 2024, every aged care provider must demonstrate continuous compliance with the 7 strengthened quality standards enforced by the Aged Care Quality and Safety Commission (ACQSC). These standards, effective from 1 July 2025, replace the previous 8 Aged Care Quality Standards and place stronger emphasis on the rights of older Australians.</p>
<p>AlwaysReady Care is a free compliance evidence layer designed for Australian aged care providers in {name} and nationwide. It does not replace your existing aged care software — it works alongside AlayaCare, iCare, Leecare, Person Centred Software, and any other system you use.</p>

<h2>How {name} Aged Care Providers Use AlwaysReady Care</h2>
<p>Care workers in {name} use AlwaysReady Care to record evidence during or immediately after providing care. With pre-built templates covering medication administration, personal care, meals, incidents, clinical observations, and more, recording takes under 60 seconds. AI automatically structures messy handover notes into ACQSC-ready format, suggests compliance tags, flags risks, and recommends follow-up actions.</p>
<p>Managers and quality leads see a live compliance readiness dashboard showing which of the 7 strengthened standards have gaps. When the Aged Care Quality and Safety Commission conducts a quality review of your {name} service, the manager generates a professional audit pack in one click — filtered by date range, evidence type, or quality standard.</p>

<h2>Why Aged Care Providers in {name} Need Digital Compliance</h2>
<p>The most common reason the ACQSC finds non-compliance in {name} aged care homes is weak governance and poor record-keeping — scattered evidence across paper notes, WhatsApp messages, and spreadsheets. The strengthened standards under the Aged Care Act 2024 require providers to demonstrate outcomes-based compliance, not just policies. AlwaysReady Care solves this by centralising all compliance evidence in one searchable, auditable, inspection-ready system.</p>
<p>For multi-site operators in {region}, the platform provides group-level visibility so approved providers and quality directors can spot compliance gaps before the Commission does.</p>

<h2>Get Started in {name}</h2>
<p>AlwaysReady Care is free to start. No credit card required. No installation — it works in your browser and can be installed as an app on your phone. Your team can be recording ACQSC-ready evidence within 5 minutes.</p>

</section>

<div id="tool-faqs"></div>
<div id="related-tools"></div>
</article>
</div>

<script src="/shared/js/common.js"></script>
<script>
TeamzTools.renderBreadcrumbs([
  {{ name: 'Home', url: '/' }},
  {{ name: 'AU Aged Care', url: '/au-care/' }},
  {{ name: '{name}' }}
]);

TeamzTools.renderFAQs([
  {{ q: 'How many registered aged care homes are in {name}?', a: 'There are approximately {homes} registered aged care homes and services in {name}, {region}. This includes residential aged care facilities, home care providers, and flexible care services regulated by the Aged Care Quality and Safety Commission.' }},
  {{ q: 'What are the 7 strengthened aged care quality standards?', a: 'The 7 strengthened quality standards under the Aged Care Act 2024 cover: (1) The Person, (2) The Organisation, (3) The Care and Services, (4) The Environment, (5) Clinical Care, (6) Food and Nutrition, and (7) The Residential Community. They replace the previous 8 standards from 1 July 2025.' }},
  {{ q: 'What is the best compliance software for aged care in {name}?', a: 'AlwaysReady Care is a free compliance evidence layer designed for Australian aged care providers. It tracks evidence against all 7 strengthened quality standards, with AI-assisted structuring, follow-up tracking, and one-click audit pack generation.' }},
  {{ q: 'Does AlwaysReady Care work with other aged care software?', a: 'Yes. AlwaysReady Care works alongside AlayaCare, iCare, Leecare, Person Centred Software, and any other aged care platform. It is a compliance evidence layer, not a replacement for your existing care management system.' }},
  {{ q: 'Is this aged care compliance software free?', a: 'AlwaysReady Care is free to start with evidence capture, compliance tracking, and audit pack generation for up to 3 staff. Pro plans with all templates, AI structuring, and unlimited staff are available for larger services.' }}
]);
TeamzTools.injectFAQSchema();

TeamzTools.renderRelatedTools([
  {{ slug: '/au-care/', name: 'All AU Aged Care Tools', description: 'Browse all aged care compliance tools by region' }},
  {{ slug: '/uk-care/', name: 'UK Care Home Tools', description: 'CQC compliance tools for UK care homes' }},
  {{ slug: '/nz-care/', name: 'NZ Rest Home Tools', description: 'NZS 8134 compliance tools for New Zealand rest homes' }},
  {{ slug: '/ie-care/', name: 'Ireland Nursing Home Tools', description: 'HIQA compliance tools for Irish nursing homes' }},
  {{ slug: '/health/', name: 'Health Tools', description: 'Health calculators, BMI, medication, and wellness tools' }},
  {{ slug: '/tools/', name: 'All Tools', description: 'Browse 2000+ free browser-based tools' }}
]);

TeamzTools.injectWebAppSchema({{
  slug: 'au-care/aged-care-compliance-{slug}',
  title: '{title}',
  description: '{meta_desc}'
}});
</script>
</body>
</html>"""


def generate_au_care_hub():
    """Generate the /au-care/ hub page listing all location pages."""
    locations_html = ""
    for slug, data in sorted(AU_CARE_LOCATIONS.items(), key=lambda x: -x[1]["homes"]):
        locations_html += f'        <a href="/au-care/aged-care-compliance-{slug}/" class="hub-card"><h3>{data["name"]}</h3><p>{data["region"]} · {data["homes"]}+ aged care homes</p></a>\n'

    return f"""<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Australian Aged Care Compliance Software by Region — Free ACQSC Tools — Teamz Lab Tools</title>
<meta name="description" content="Free ACQSC compliance evidence software for Australian aged care providers. Find aged care compliance tools for your region — Sydney, Melbourne, Brisbane, Perth, Adelaide, and 15+ more locations.">
<link rel="canonical" href="{SITE_URL}/au-care/">
<link rel="alternate" hreflang="en-AU" href="{SITE_URL}/au-care/">
<link rel="alternate" hreflang="x-default" href="{SITE_URL}/au-care/">
<meta property="og:title" content="Australian Aged Care Compliance Software by Region">
<meta property="og:description" content="Free ACQSC compliance tools for aged care providers across Australia. 20 locations covered.">
<meta property="og:url" content="{SITE_URL}/au-care/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Teamz Lab Tools">
<link rel="stylesheet" href="/branding/css/teamz-branding.css">
<link rel="stylesheet" href="/shared/css/tools.css">
</head>
<body>
<script src="/branding/js/theme.js"></script>
<div class="site-main">
<nav class="breadcrumbs" id="breadcrumbs"></nav>
<h1>Australian Aged Care Compliance Software</h1>
<p class="hub-intro">Free ACQSC compliance evidence software for aged care providers across Australia. Choose your region to see local aged care data and get started with AlwaysReady Care.</p>
<div class="hub-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;margin:24px 0;">
{locations_html}
</div>
</div>
<script src="/shared/js/common.js"></script>
<script>
TeamzTools.renderBreadcrumbs([
  {{ name: 'Home', url: '/' }},
  {{ name: 'AU Aged Care' }}
]);
</script>
</body>
</html>"""


# ============================================================
# IRELAND — NURSING HOME COMPLIANCE — LOCATION DATA
# ============================================================
IE_CARE_LOCATIONS = {
    "dublin": {"name": "Dublin", "region": "Leinster", "homes": 120, "population": "1.4m"},
    "cork": {"name": "Cork", "region": "Munster", "homes": 60, "population": "210k"},
    "galway": {"name": "Galway", "region": "Connacht", "homes": 30, "population": "83k"},
    "limerick": {"name": "Limerick", "region": "Munster", "homes": 25, "population": "100k"},
    "waterford": {"name": "Waterford", "region": "Munster", "homes": 18, "population": "54k"},
    "kilkenny": {"name": "Kilkenny", "region": "Leinster", "homes": 12, "population": "27k"},
    "drogheda": {"name": "Drogheda", "region": "Leinster", "homes": 10, "population": "41k"},
    "dundalk": {"name": "Dundalk", "region": "Leinster", "homes": 10, "population": "40k"},
    "kerry": {"name": "Kerry", "region": "Munster", "homes": 18, "population": "155k"},
    "wexford": {"name": "Wexford", "region": "Leinster", "homes": 14, "population": "150k"},
    "mayo": {"name": "Mayo", "region": "Connacht", "homes": 12, "population": "130k"},
    "donegal": {"name": "Donegal", "region": "Ulster", "homes": 15, "population": "160k"},
    "tipperary": {"name": "Tipperary", "region": "Munster", "homes": 16, "population": "160k"},
    "clare": {"name": "Clare", "region": "Munster", "homes": 10, "population": "120k"},
    "wicklow": {"name": "Wicklow", "region": "Leinster", "homes": 12, "population": "155k"},
}


def generate_ie_care_page(slug, data):
    """Generate an Irish nursing home compliance tool page for a specific location."""
    name = data["name"]
    region = data["region"]
    homes = data["homes"]
    pop = data["population"]

    title = f"Nursing Home Compliance Software {name} — Free HIQA Tool"
    meta_desc = f"Free nursing home compliance software for {name}, {region}. Track HIQA readiness across 8 national standards for {homes}+ nursing homes in {name}. Record evidence in 60 seconds."
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152] + "..."
    h1 = f"Nursing Home Compliance Software for {name}"
    canonical = f"{SITE_URL}/ie-care/nursing-home-compliance-{slug}/"

    return f"""<!DOCTYPE html>
<html lang="en-IE">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Teamz Lab Tools</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en-IE" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Teamz Lab Tools">
<meta property="og:image" content="{SITE_URL}/og-images/ie-care.png">
<link rel="stylesheet" href="/branding/css/teamz-branding.css">
<link rel="stylesheet" href="/shared/css/tools.css">
</head>
<body>
<script src="/branding/js/theme.js"></script>

<div class="site-main">
<nav class="breadcrumbs" id="breadcrumbs"></nav>

<article class="tool-article">
<h1>{h1}</h1>
<p class="tool-intro">Free HIQA compliance evidence software for the {homes}+ registered nursing homes in {name}, {region}. AlwaysReady Care helps nursing homes capture, structure, review, and export inspection-ready evidence — mapped to the 8 National Standards for Residential Care Settings for Older People in Ireland.</p>

<div class="tool-calculator" id="tool-calculator">
  <div class="tool-calculator-section">
    <h2>Try AlwaysReady Care for {name}</h2>
    <p>Record care evidence in 60 seconds. AI structures your notes. Generate HIQA inspection packs in one click. Works alongside your existing nursing home software — no rip-and-replace required.</p>

    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:20px 0;">
      <a href="https://always-ready-care.web.app/" class="btn-primary" style="display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:12px;background:#D9FE06;color:#12151A;font-weight:600;text-decoration:none;font-size:15px;">
        Get Started Free
      </a>
      <a href="https://wa.me/447490356046?text=Hi%2C%20I%20run%20a%20nursing%20home%20in%20{name}%20and%20I%27d%20like%20a%20demo%20of%20AlwaysReady%20Care." class="btn-secondary" style="display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:12px;border:1px solid;text-decoration:none;font-size:15px;" target="_blank" rel="noopener">
        Book a Demo
      </a>
    </div>

    <div class="tool-result" id="tool-result">
      <h3>8 National Standards Tracked</h3>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin:16px 0;">
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 1</strong><br>Person-Centred Care and Support</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 2</strong><br>Effective Care and Support</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 3</strong><br>Safe Care and Support</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 4</strong><br>Health and Wellbeing</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 5</strong><br>Use of Resources</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 6</strong><br>Workforce</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 7</strong><br>Use of Information</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Standard 8</strong><br>Governance, Leadership and Management</div>
      </div>
    </div>
  </div>
</div>

<div class="ad-slot">Ad Space</div>

<section class="tool-content">

<h2>HIQA Compliance for Nursing Homes in {name}</h2>
<p>{name} in {region} has approximately {homes} HIQA-registered nursing homes and residential care centres serving a population of {pop}. The Health Information and Quality Authority (HIQA) regulates all designated centres for older people in Ireland under the Health Act 2007 and the Care and Welfare Regulations 2013. Every nursing home must demonstrate continuous compliance with the 8 National Standards for Residential Care Settings for Older People.</p>
<p>AlwaysReady Care is a free compliance evidence layer designed for Irish nursing homes in {name} and nationwide. It does not replace your existing nursing home software — it works alongside any care management platform you already use.</p>

<h2>How {name} Nursing Homes Use AlwaysReady Care</h2>
<p>Care staff in {name} use AlwaysReady Care to record evidence during or immediately after providing care. With pre-built templates covering medication administration, personal care, meals, incidents, safeguarding, health monitoring, and more, recording takes under 60 seconds. AI automatically structures handover notes into HIQA-ready format, suggests compliance tags, flags risks, and recommends follow-up actions.</p>
<p>Persons in charge and registered providers see a live compliance readiness dashboard showing which of the 8 National Standards have gaps. When HIQA inspects a {name} nursing home, the person in charge generates a professional inspection pack in one click — filtered by date range, evidence type, or regulation area.</p>

<h2>Why Nursing Homes in {name} Need Digital Compliance</h2>
<p>The most common reason HIQA finds non-compliance in {name} nursing homes is poor governance under Regulation 23 — specifically, weak oversight systems and scattered evidence across paper records. The National Standards require nursing homes to demonstrate outcomes for residents, not just policies. AlwaysReady Care solves this by centralising all compliance evidence in one searchable, auditable, inspection-ready system.</p>
<p>For nursing home groups operating across {region} and Ireland, the platform provides group-level visibility so registered providers and quality managers can identify compliance gaps before inspectors do.</p>

<h2>Get Started in {name}</h2>
<p>AlwaysReady Care is free to start. No credit card required. No installation — it works in your browser and can be installed as an app on your phone. Your team can be recording HIQA-ready evidence within 5 minutes.</p>

</section>

<div id="tool-faqs"></div>
<div id="related-tools"></div>
</article>
</div>

<script src="/shared/js/common.js"></script>
<script>
TeamzTools.renderBreadcrumbs([
  {{ name: 'Home', url: '/' }},
  {{ name: 'IE Nursing Homes', url: '/ie-care/' }},
  {{ name: '{name}' }}
]);

TeamzTools.renderFAQs([
  {{ q: 'How many HIQA-registered nursing homes are in {name}?', a: 'There are approximately {homes} HIQA-registered nursing homes and designated centres for older people in {name}, {region}. These are regulated under the Health Act 2007 and must comply with the National Standards for Residential Care Settings.' }},
  {{ q: 'What are the 8 National Standards for nursing homes in Ireland?', a: 'The 8 National Standards cover: (1) Person-Centred Care and Support, (2) Effective Care and Support, (3) Safe Care and Support, (4) Health and Wellbeing, (5) Use of Resources, (6) Workforce, (7) Use of Information, and (8) Governance, Leadership and Management.' }},
  {{ q: 'What is the best compliance software for nursing homes in {name}?', a: 'AlwaysReady Care is a free compliance evidence layer designed for Irish nursing homes. It tracks evidence against all 8 National Standards, with AI-assisted structuring, follow-up tracking, and one-click inspection pack generation.' }},
  {{ q: 'Does AlwaysReady Care work with other nursing home software?', a: 'Yes. AlwaysReady Care works alongside any care management system used in Irish nursing homes. It is a compliance evidence layer, not a replacement for your existing software.' }},
  {{ q: 'Is this nursing home compliance software free?', a: 'AlwaysReady Care is free to start with evidence capture, compliance tracking, and inspection pack generation for up to 3 staff. Pro plans with all templates, AI structuring, and unlimited staff are available for larger nursing homes.' }}
]);
TeamzTools.injectFAQSchema();

TeamzTools.renderRelatedTools([
  {{ slug: '/ie-care/', name: 'All Ireland Nursing Home Tools', description: 'Browse all nursing home compliance tools by county' }},
  {{ slug: '/uk-care/', name: 'UK Care Home Tools', description: 'CQC compliance tools for UK care homes' }},
  {{ slug: '/au-care/', name: 'AU Aged Care Tools', description: 'ACQSC compliance tools for Australian aged care' }},
  {{ slug: '/nz-care/', name: 'NZ Rest Home Tools', description: 'NZS 8134 compliance tools for New Zealand rest homes' }},
  {{ slug: '/health/', name: 'Health Tools', description: 'Health calculators, BMI, medication, and wellness tools' }},
  {{ slug: '/tools/', name: 'All Tools', description: 'Browse 2000+ free browser-based tools' }}
]);

TeamzTools.injectWebAppSchema({{
  slug: 'ie-care/nursing-home-compliance-{slug}',
  title: '{title}',
  description: '{meta_desc}'
}});
</script>
</body>
</html>"""


def generate_ie_care_hub():
    """Generate the /ie-care/ hub page listing all location pages."""
    locations_html = ""
    for slug, data in sorted(IE_CARE_LOCATIONS.items(), key=lambda x: -x[1]["homes"]):
        locations_html += f'        <a href="/ie-care/nursing-home-compliance-{slug}/" class="hub-card"><h3>{data["name"]}</h3><p>{data["region"]} · {data["homes"]}+ nursing homes</p></a>\n'

    return f"""<!DOCTYPE html>
<html lang="en-IE">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ireland Nursing Home Compliance Software by County — Free HIQA Tools — Teamz Lab Tools</title>
<meta name="description" content="Free HIQA compliance evidence software for Irish nursing homes. Find nursing home compliance tools for your county — Dublin, Cork, Galway, Limerick, and 11+ more Irish locations.">
<link rel="canonical" href="{SITE_URL}/ie-care/">
<link rel="alternate" hreflang="en-IE" href="{SITE_URL}/ie-care/">
<link rel="alternate" hreflang="x-default" href="{SITE_URL}/ie-care/">
<meta property="og:title" content="Ireland Nursing Home Compliance Software by County">
<meta property="og:description" content="Free HIQA compliance tools for nursing homes across Ireland. 15 locations covered.">
<meta property="og:url" content="{SITE_URL}/ie-care/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Teamz Lab Tools">
<link rel="stylesheet" href="/branding/css/teamz-branding.css">
<link rel="stylesheet" href="/shared/css/tools.css">
</head>
<body>
<script src="/branding/js/theme.js"></script>
<div class="site-main">
<nav class="breadcrumbs" id="breadcrumbs"></nav>
<h1>Ireland Nursing Home Compliance Software</h1>
<p class="hub-intro">Free HIQA compliance evidence software for nursing homes across Ireland. Choose your county to see local nursing home data and get started with AlwaysReady Care.</p>
<div class="hub-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;margin:24px 0;">
{locations_html}
</div>
</div>
<script src="/shared/js/common.js"></script>
<script>
TeamzTools.renderBreadcrumbs([
  {{ name: 'Home', url: '/' }},
  {{ name: 'IE Nursing Homes' }}
]);
</script>
</body>
</html>"""


# ============================================================
# NEW ZEALAND — REST HOME COMPLIANCE — LOCATION DATA
# ============================================================
NZ_CARE_LOCATIONS = {
    "auckland": {"name": "Auckland", "region": "Auckland", "homes": 180, "population": "1.7m"},
    "wellington": {"name": "Wellington", "region": "Wellington", "homes": 60, "population": "215k"},
    "christchurch": {"name": "Christchurch", "region": "Canterbury", "homes": 70, "population": "390k"},
    "hamilton": {"name": "Hamilton", "region": "Waikato", "homes": 35, "population": "180k"},
    "tauranga": {"name": "Tauranga", "region": "Bay of Plenty", "homes": 30, "population": "155k"},
    "dunedin": {"name": "Dunedin", "region": "Otago", "homes": 25, "population": "135k"},
    "palmerston-north": {"name": "Palmerston North", "region": "Manawatū", "homes": 15, "population": "90k"},
    "napier": {"name": "Napier", "region": "Hawke's Bay", "homes": 15, "population": "67k"},
    "nelson": {"name": "Nelson", "region": "Nelson", "homes": 12, "population": "54k"},
    "rotorua": {"name": "Rotorua", "region": "Bay of Plenty", "homes": 12, "population": "75k"},
    "new-plymouth": {"name": "New Plymouth", "region": "Taranaki", "homes": 10, "population": "58k"},
    "invercargill": {"name": "Invercargill", "region": "Southland", "homes": 10, "population": "55k"},
}


def generate_nz_care_page(slug, data):
    """Generate a New Zealand rest home compliance tool page for a specific location."""
    name = data["name"]
    region = data["region"]
    homes = data["homes"]
    pop = data["population"]

    title = f"Rest Home Compliance Software {name} — Free NZS 8134 Tool"
    meta_desc = f"Free rest home compliance software for {name}, {region}. Track NZS 8134 readiness for {homes}+ aged residential care facilities in {name}. Record evidence in 60 seconds."
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152] + "..."
    h1 = f"Rest Home Compliance Software for {name}"
    canonical = f"{SITE_URL}/nz-care/rest-home-compliance-{slug}/"

    return f"""<!DOCTYPE html>
<html lang="en-NZ">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Teamz Lab Tools</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en-NZ" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Teamz Lab Tools">
<meta property="og:image" content="{SITE_URL}/og-images/nz-care.png">
<link rel="stylesheet" href="/branding/css/teamz-branding.css">
<link rel="stylesheet" href="/shared/css/tools.css">
</head>
<body>
<script src="/branding/js/theme.js"></script>

<div class="site-main">
<nav class="breadcrumbs" id="breadcrumbs"></nav>

<article class="tool-article">
<h1>{h1}</h1>
<p class="tool-intro">Free NZS 8134 compliance evidence software for the {homes}+ registered aged residential care facilities in {name}, {region}. AlwaysReady Care helps rest homes capture, structure, review, and export audit-ready evidence — mapped to the Health and Disability Services Standards (NZS 8134:2021) enforced by the Ministry of Health.</p>

<div class="tool-calculator" id="tool-calculator">
  <div class="tool-calculator-section">
    <h2>Try AlwaysReady Care for {name}</h2>
    <p>Record care evidence in 60 seconds. AI structures your notes. Generate certification audit packs in one click. Works alongside your existing rest home software — no rip-and-replace required.</p>

    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:20px 0;">
      <a href="https://always-ready-care.web.app/" class="btn-primary" style="display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:12px;background:#D9FE06;color:#12151A;font-weight:600;text-decoration:none;font-size:15px;">
        Get Started Free
      </a>
      <a href="https://wa.me/447490356046?text=Hi%2C%20I%20run%20a%20rest%20home%20in%20{name}%20and%20I%27d%20like%20a%20demo%20of%20AlwaysReady%20Care." class="btn-secondary" style="display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:12px;border:1px solid;text-decoration:none;font-size:15px;" target="_blank" rel="noopener">
        Book a Demo
      </a>
    </div>

    <div class="tool-result" id="tool-result">
      <h3>NZS 8134 Standards Tracked</h3>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin:16px 0;">
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">NZS 8134.1</strong><br>Health and Disability Services (Core) Standards</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">NZS 8134.2</strong><br>Health and Disability Services (Restraint Minimisation and Safe Practice)</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">NZS 8134.3</strong><br>Health and Disability Services (Infection Prevention and Control)</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Consumer Rights</strong><br>Code of Health and Disability Services Consumers' Rights</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Governance</strong><br>Organisation management, quality improvement, risk management</div>
        <div style="padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;"><strong style="color:var(--heading);">Continuum of Service</strong><br>Entry, assessment, care planning, review, exit</div>
      </div>
    </div>
  </div>
</div>

<div class="ad-slot">Ad Space</div>

<section class="tool-content">

<h2>NZS 8134 Compliance for Rest Homes in {name}</h2>
<p>{name} in {region} has approximately {homes} registered aged residential care facilities serving a population of {pop}. Under the Health and Disability Services (Safety) Act 2001, every aged residential care provider must hold a current certification audit against the NZS 8134:2021 standards. The Ministry of Health, through designated auditing agencies, certifies rest homes, continuing care hospitals, dementia units, and psychogeriatric facilities.</p>
<p>AlwaysReady Care is a free compliance evidence layer designed for New Zealand rest homes in {name} and nationwide. It does not replace your existing rest home software — it works alongside any care management platform you already use.</p>

<h2>How {name} Rest Homes Use AlwaysReady Care</h2>
<p>Care workers in {name} use AlwaysReady Care to record evidence during or immediately after providing care. With pre-built templates covering medication administration, personal care, meals, incidents, restraint documentation, infection control, and more, recording takes under 60 seconds. AI automatically structures handover notes into NZS 8134-ready format, suggests compliance tags, flags risks, and recommends follow-up actions.</p>
<p>Facility managers see a live compliance readiness dashboard showing which NZS 8134 criteria have gaps. When a designated auditing agency conducts a certification audit of your {name} rest home, the manager generates a professional audit pack in one click — filtered by date range, evidence type, or standard area.</p>

<h2>Why Rest Homes in {name} Need Digital Compliance</h2>
<p>The most common reason rest homes in {name} receive corrective action requests during certification audits is poor documentation and scattered evidence. NZS 8134 requires rest homes to demonstrate outcomes for residents across core standards, restraint minimisation, and infection control. AlwaysReady Care solves this by centralising all compliance evidence in one searchable, auditable, certification-ready system.</p>
<p>For multi-site operators across {region} and New Zealand, the platform provides group-level visibility so managers and quality leads can spot compliance gaps before auditors do.</p>

<h2>Get Started in {name}</h2>
<p>AlwaysReady Care is free to start. No credit card required. No installation — it works in your browser and can be installed as an app on your phone. Your team can be recording NZS 8134-ready evidence within 5 minutes.</p>

</section>

<div id="tool-faqs"></div>
<div id="related-tools"></div>
</article>
</div>

<script src="/shared/js/common.js"></script>
<script>
TeamzTools.renderBreadcrumbs([
  {{ name: 'Home', url: '/' }},
  {{ name: 'NZ Rest Homes', url: '/nz-care/' }},
  {{ name: '{name}' }}
]);

TeamzTools.renderFAQs([
  {{ q: 'How many registered rest homes are in {name}?', a: 'There are approximately {homes} registered aged residential care facilities in {name}, {region}. This includes rest homes, continuing care hospitals, dementia units, and psychogeriatric facilities certified under NZS 8134.' }},
  {{ q: 'What is NZS 8134?', a: 'NZS 8134 is the New Zealand Health and Disability Services Standards. It includes core standards (8134.1), restraint minimisation (8134.2), and infection prevention and control (8134.3). All aged residential care facilities must be certified against these standards by a designated auditing agency.' }},
  {{ q: 'What is the best compliance software for rest homes in {name}?', a: 'AlwaysReady Care is a free compliance evidence layer designed for New Zealand rest homes. It tracks evidence against NZS 8134 standards, with AI-assisted structuring, follow-up tracking, and one-click audit pack generation.' }},
  {{ q: 'Does AlwaysReady Care work with other rest home software?', a: 'Yes. AlwaysReady Care works alongside any care management system used in New Zealand rest homes. It is a compliance evidence layer, not a replacement for your existing software.' }},
  {{ q: 'Is this rest home compliance software free?', a: 'AlwaysReady Care is free to start with evidence capture, compliance tracking, and audit pack generation for up to 3 staff. Pro plans with all templates, AI structuring, and unlimited staff are available for larger facilities.' }}
]);
TeamzTools.injectFAQSchema();

TeamzTools.renderRelatedTools([
  {{ slug: '/nz-care/', name: 'All NZ Rest Home Tools', description: 'Browse all rest home compliance tools by region' }},
  {{ slug: '/au-care/', name: 'AU Aged Care Tools', description: 'ACQSC compliance tools for Australian aged care' }},
  {{ slug: '/uk-care/', name: 'UK Care Home Tools', description: 'CQC compliance tools for UK care homes' }},
  {{ slug: '/ie-care/', name: 'Ireland Nursing Home Tools', description: 'HIQA compliance tools for Irish nursing homes' }},
  {{ slug: '/health/', name: 'Health Tools', description: 'Health calculators, BMI, medication, and wellness tools' }},
  {{ slug: '/tools/', name: 'All Tools', description: 'Browse 2000+ free browser-based tools' }}
]);

TeamzTools.injectWebAppSchema({{
  slug: 'nz-care/rest-home-compliance-{slug}',
  title: '{title}',
  description: '{meta_desc}'
}});
</script>
</body>
</html>"""


def generate_nz_care_hub():
    """Generate the /nz-care/ hub page listing all location pages."""
    locations_html = ""
    for slug, data in sorted(NZ_CARE_LOCATIONS.items(), key=lambda x: -x[1]["homes"]):
        locations_html += f'        <a href="/nz-care/rest-home-compliance-{slug}/" class="hub-card"><h3>{data["name"]}</h3><p>{data["region"]} · {data["homes"]}+ rest homes</p></a>\n'

    return f"""<!DOCTYPE html>
<html lang="en-NZ">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>New Zealand Rest Home Compliance Software by Region — Free NZS 8134 Tools — Teamz Lab Tools</title>
<meta name="description" content="Free NZS 8134 compliance evidence software for New Zealand rest homes. Find rest home compliance tools for your region — Auckland, Wellington, Christchurch, Hamilton, and 8+ more locations.">
<link rel="canonical" href="{SITE_URL}/nz-care/">
<link rel="alternate" hreflang="en-NZ" href="{SITE_URL}/nz-care/">
<link rel="alternate" hreflang="x-default" href="{SITE_URL}/nz-care/">
<meta property="og:title" content="New Zealand Rest Home Compliance Software by Region">
<meta property="og:description" content="Free NZS 8134 compliance tools for rest homes across New Zealand. 12 locations covered.">
<meta property="og:url" content="{SITE_URL}/nz-care/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Teamz Lab Tools">
<link rel="stylesheet" href="/branding/css/teamz-branding.css">
<link rel="stylesheet" href="/shared/css/tools.css">
</head>
<body>
<script src="/branding/js/theme.js"></script>
<div class="site-main">
<nav class="breadcrumbs" id="breadcrumbs"></nav>
<h1>New Zealand Rest Home Compliance Software</h1>
<p class="hub-intro">Free NZS 8134 compliance evidence software for rest homes across New Zealand. Choose your region to see local rest home data and get started with AlwaysReady Care.</p>
<div class="hub-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;margin:24px 0;">
{locations_html}
</div>
</div>
<script src="/shared/js/common.js"></script>
<script>
TeamzTools.renderBreadcrumbs([
  {{ name: 'Home', url: '/' }},
  {{ name: 'NZ Rest Homes' }}
]);
</script>
</body>
</html>"""


def main():
    args = sys.argv[1:]

    if not args or "--help" in args:
        print(__doc__)
        return

    if "--list" in args:
        print("Available templates:")
        print("  us-income-tax        — US state income tax calculators (50 states + DC)")
        print("  uk-care-compliance   — UK care home compliance pages (40 cities/regions)")
        print("  au-aged-care         — Australian aged care compliance pages (20 cities/states)")
        print("  ie-nursing-home      — Ireland nursing home compliance pages (15 cities/counties)")
        print("  nz-aged-care         — New Zealand rest home compliance pages (12 cities)")
        return

    dry_run = "--dry-run" in args
    template = [a for a in args if not a.startswith("--")]

    if not template:
        print("Error: specify a template name. Use --list to see options.")
        return

    template = template[0]

    if template == "uk-care-compliance":
        print(f"{'[DRY RUN] ' if dry_run else ''}Generating UK care home compliance pages...")
        count = 0
        for loc_slug, loc_data in sorted(UK_CARE_LOCATIONS.items()):
            page_dir = os.path.join(PROJECT_ROOT, "uk-care", f"care-home-compliance-{loc_slug}")
            page_path = os.path.join(page_dir, "index.html")

            if dry_run:
                print(f"  Would create: /uk-care/care-home-compliance-{loc_slug}/")
            else:
                os.makedirs(page_dir, exist_ok=True)
                page_content = generate_uk_care_page(loc_slug, loc_data)
                with open(page_path, "w", encoding="utf-8") as f:
                    f.write(page_content)
                print(f"  Created: /uk-care/care-home-compliance-{loc_slug}/")
            count += 1

        # Create hub page
        if not dry_run:
            hub_dir = os.path.join(PROJECT_ROOT, "uk-care")
            hub_path = os.path.join(hub_dir, "index.html")
            hub_content = generate_uk_care_hub()
            with open(hub_path, "w", encoding="utf-8") as f:
                f.write(hub_content)
            print(f"  Created: /uk-care/index.html (hub page)")

        print(f"\n{'Would create' if dry_run else 'Created'} {count} UK care home compliance pages + hub.")
        if not dry_run:
            print("\nNext steps:")
            print("  1. Run: python3 build-static-schema.py")
            print("  2. Run: ./build-search-index.sh")
            print("  3. Run: ./build.sh")

    elif template == "us-income-tax":
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
    elif template == "au-aged-care":
        print(f"{'[DRY RUN] ' if dry_run else ''}Generating Australian aged care compliance pages...")
        count = 0
        for loc_slug, loc_data in sorted(AU_CARE_LOCATIONS.items()):
            page_dir = os.path.join(PROJECT_ROOT, "au-care", f"aged-care-compliance-{loc_slug}")
            page_path = os.path.join(page_dir, "index.html")

            if dry_run:
                print(f"  Would create: /au-care/aged-care-compliance-{loc_slug}/")
            else:
                os.makedirs(page_dir, exist_ok=True)
                page_content = generate_au_care_page(loc_slug, loc_data)
                with open(page_path, "w", encoding="utf-8") as f:
                    f.write(page_content)
                print(f"  Created: /au-care/aged-care-compliance-{loc_slug}/")
            count += 1

        # Create hub page
        if not dry_run:
            hub_dir = os.path.join(PROJECT_ROOT, "au-care")
            os.makedirs(hub_dir, exist_ok=True)
            hub_path = os.path.join(hub_dir, "index.html")
            hub_content = generate_au_care_hub()
            with open(hub_path, "w", encoding="utf-8") as f:
                f.write(hub_content)
            print(f"  Created: /au-care/index.html (hub page)")

        print(f"\n{'Would create' if dry_run else 'Created'} {count} Australian aged care compliance pages + hub.")
        if not dry_run:
            print("\nNext steps:")
            print("  1. Run: python3 build-static-schema.py")
            print("  2. Run: ./build-search-index.sh")
            print("  3. Run: ./build.sh")

    elif template == "ie-nursing-home":
        print(f"{'[DRY RUN] ' if dry_run else ''}Generating Ireland nursing home compliance pages...")
        count = 0
        for loc_slug, loc_data in sorted(IE_CARE_LOCATIONS.items()):
            page_dir = os.path.join(PROJECT_ROOT, "ie-care", f"nursing-home-compliance-{loc_slug}")
            page_path = os.path.join(page_dir, "index.html")

            if dry_run:
                print(f"  Would create: /ie-care/nursing-home-compliance-{loc_slug}/")
            else:
                os.makedirs(page_dir, exist_ok=True)
                page_content = generate_ie_care_page(loc_slug, loc_data)
                with open(page_path, "w", encoding="utf-8") as f:
                    f.write(page_content)
                print(f"  Created: /ie-care/nursing-home-compliance-{loc_slug}/")
            count += 1

        # Create hub page
        if not dry_run:
            hub_dir = os.path.join(PROJECT_ROOT, "ie-care")
            os.makedirs(hub_dir, exist_ok=True)
            hub_path = os.path.join(hub_dir, "index.html")
            hub_content = generate_ie_care_hub()
            with open(hub_path, "w", encoding="utf-8") as f:
                f.write(hub_content)
            print(f"  Created: /ie-care/index.html (hub page)")

        print(f"\n{'Would create' if dry_run else 'Created'} {count} Ireland nursing home compliance pages + hub.")
        if not dry_run:
            print("\nNext steps:")
            print("  1. Run: python3 build-static-schema.py")
            print("  2. Run: ./build-search-index.sh")
            print("  3. Run: ./build.sh")

    elif template == "nz-aged-care":
        print(f"{'[DRY RUN] ' if dry_run else ''}Generating New Zealand rest home compliance pages...")
        count = 0
        for loc_slug, loc_data in sorted(NZ_CARE_LOCATIONS.items()):
            page_dir = os.path.join(PROJECT_ROOT, "nz-care", f"rest-home-compliance-{loc_slug}")
            page_path = os.path.join(page_dir, "index.html")

            if dry_run:
                print(f"  Would create: /nz-care/rest-home-compliance-{loc_slug}/")
            else:
                os.makedirs(page_dir, exist_ok=True)
                page_content = generate_nz_care_page(loc_slug, loc_data)
                with open(page_path, "w", encoding="utf-8") as f:
                    f.write(page_content)
                print(f"  Created: /nz-care/rest-home-compliance-{loc_slug}/")
            count += 1

        # Create hub page
        if not dry_run:
            hub_dir = os.path.join(PROJECT_ROOT, "nz-care")
            os.makedirs(hub_dir, exist_ok=True)
            hub_path = os.path.join(hub_dir, "index.html")
            hub_content = generate_nz_care_hub()
            with open(hub_path, "w", encoding="utf-8") as f:
                f.write(hub_content)
            print(f"  Created: /nz-care/index.html (hub page)")

        print(f"\n{'Would create' if dry_run else 'Created'} {count} New Zealand rest home compliance pages + hub.")
        if not dry_run:
            print("\nNext steps:")
            print("  1. Run: python3 build-static-schema.py")
            print("  2. Run: ./build-search-index.sh")
            print("  3. Run: ./build.sh")

    else:
        print(f"Unknown template: {template}")
        print("Use --list to see available templates.")


if __name__ == "__main__":
    main()
