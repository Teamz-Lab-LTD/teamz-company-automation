#!/usr/bin/env python3
"""
Multi-Language Tool Builder — Teamz Lab Tools

Identifies high-RPM tools that should have Spanish/Portuguese versions,
and tracks which tools have been translated.

Usage:
  python3 scripts/build-multilang.py status          # Show translation status
  python3 scripts/build-multilang.py suggest          # Suggest tools to translate next
  python3 scripts/build-multilang.py --help           # Show help

Note: Actual translation is done by Claude (natively written, not machine-translated).
This script tracks what exists and what's missing.
"""

import os
import sys
import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# High-RPM categories that should get ES/PT versions
HIGH_RPM_HUBS = ["evergreen", "career", "freelance", "crypto", "housing"]

# Language hubs and their codes
LANG_HUBS = {
    "es": {"name": "Spanish", "lang": "es", "speakers": "500M+", "countries": "20+"},
    "pt": {"name": "Portuguese", "lang": "pt", "speakers": "180M+", "countries": "Portugal + Brazil"},
    "de": {"name": "German", "lang": "de", "speakers": "100M+", "countries": "DE + AT + CH"},
    "fr": {"name": "French", "lang": "fr", "speakers": "280M+", "countries": "FR + BE + CA + Africa"},
    "jp": {"name": "Japanese", "lang": "ja", "speakers": "125M", "countries": "Japan"},
    "tr": {"name": "Turkish", "lang": "tr", "speakers": "80M+", "countries": "Turkey"},
    "pl": {"name": "Polish", "lang": "pl", "speakers": "40M+", "countries": "Poland + diaspora"},
}

# Top tools to translate (highest RPM potential)
TOP_TOOLS_FOR_TRANSLATION = [
    "evergreen/compound-interest-calculator",
    "evergreen/mortgage-affordability-calculator",
    "evergreen/loan-amortization-calculator",
    "evergreen/50-30-20-budget-calculator",
    "evergreen/salary-comparison-by-city",
    "evergreen/hourly-to-salary-calculator",
    "evergreen/retirement-withdrawal-calculator",
    "evergreen/apr-calculator",
    "evergreen/car-affordability-calculator",
    "evergreen/bmi-calculator",
    "career/take-home-pay-estimator",
    "career/salary-hike-calculator",
    "career/offer-comparison-calculator",
    "freelance/invoice-due-date-calculator",
    "freelance/freelance-rate-calculator",
    "freelance/profit-margin-calculator",
    "housing/rent-burden-calculator",
    "housing/rent-vs-buy-breakeven-calculator",
    "crypto/profit-loss-calculator",
    "crypto/staking-rewards-calculator",
]


def get_existing_tools(hub):
    """Get all tools in a hub."""
    hub_path = os.path.join(PROJECT_ROOT, hub)
    if not os.path.isdir(hub_path):
        return []
    tools = []
    for item in sorted(os.listdir(hub_path)):
        tool_path = os.path.join(hub_path, item, "index.html")
        if os.path.isfile(tool_path) and item != "index.html":
            tools.append(f"{hub}/{item}")
    return tools


def get_tool_title(tool_path):
    """Extract title from a tool page."""
    full_path = os.path.join(PROJECT_ROOT, tool_path, "index.html")
    if not os.path.isfile(full_path):
        return "?"
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    import re
    match = re.search(r"<title>([^<]+)</title>", content)
    if match:
        title = match.group(1).replace(" — Teamz Lab Tools", "").replace(" \u2014 Teamz Lab Tools", "")
        return title
    return "?"


def show_status():
    """Show translation status for all language hubs."""
    print("=" * 60)
    print("  MULTI-LANGUAGE STATUS")
    print("=" * 60)
    print()

    for code, info in sorted(LANG_HUBS.items()):
        tools = get_existing_tools(code)
        status = f"  /{code}/ — {info['name']} ({info['speakers']} speakers, {info['countries']})"
        print(status)
        print(f"  Tools: {len(tools)}")
        if tools:
            for t in tools[:5]:
                print(f"    - {t}: {get_tool_title(t)}")
            if len(tools) > 5:
                print(f"    ... and {len(tools) - 5} more")
        print()

    # Show which top tools have been translated
    print("=" * 60)
    print("  TOP 20 TOOLS — TRANSLATION STATUS")
    print("=" * 60)
    print()
    print(f"  {'Tool':<45} {'EN':>3} {'ES':>3} {'PT':>3} {'DE':>3} {'FR':>3}")
    print(f"  {'-' * 45} {'---':>3} {'---':>3} {'---':>3} {'---':>3} {'---':>3}")

    for tool in TOP_TOOLS_FOR_TRANSLATION:
        # Check if this tool concept exists in each language hub
        tool_slug = tool.split("/")[-1]
        en = "✓" if os.path.isfile(os.path.join(PROJECT_ROOT, tool, "index.html")) else "✗"

        # For other languages, search by concept (slug might differ)
        es = "✓" if any(tool_slug in t for t in get_existing_tools("es")) else "✗"
        pt = "✓" if any(tool_slug in t for t in get_existing_tools("pt")) else "✗"
        de = "✓" if len(get_existing_tools("de")) > 0 and any(tool_slug.replace("-", "") in t.replace("-", "") for t in get_existing_tools("de")) else "✗"
        fr = "✓" if any(tool_slug in t for t in get_existing_tools("fr")) else "✗"

        title = get_tool_title(tool)
        if len(title) > 43:
            title = title[:40] + "..."
        print(f"  {title:<45} {en:>3} {es:>3} {pt:>3} {de:>3} {fr:>3}")

    print()


def show_suggest():
    """Suggest which tools to translate next."""
    print("=" * 60)
    print("  SUGGESTED TRANSLATIONS (Priority Order)")
    print("=" * 60)
    print()

    es_tools = get_existing_tools("es")
    pt_tools = get_existing_tools("pt")

    missing_es = []
    missing_pt = []

    for tool in TOP_TOOLS_FOR_TRANSLATION:
        tool_slug = tool.split("/")[-1]
        title = get_tool_title(tool)

        if not any(tool_slug in t for t in es_tools):
            missing_es.append((tool, title))
        if not any(tool_slug in t for t in pt_tools):
            missing_pt.append((tool, title))

    print(f"  SPANISH (/es/) — {len(missing_es)} tools to translate:")
    for tool, title in missing_es[:10]:
        print(f"    → {title}")
    print()

    print(f"  PORTUGUESE (/pt/) — {len(missing_pt)} tools to translate:")
    for tool, title in missing_pt[:10]:
        print(f"    → {title}")
    print()

    print("  To translate, ask Claude:")
    print("    'Build Spanish version of [tool name] in /es/'")
    print("    'Build Portuguese version of [tool name] in /pt/'")
    print()
    print("  Claude will write natively in the target language (not machine translate).")
    print()


def main():
    args = sys.argv[1:]

    if not args or "--help" in args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "status":
        show_status()
    elif cmd == "suggest":
        show_suggest()
    else:
        print(f"Unknown command: {cmd}")
        print("Use: status, suggest, or --help")


if __name__ == "__main__":
    main()
