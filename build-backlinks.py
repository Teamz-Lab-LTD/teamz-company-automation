#!/usr/bin/env python3
"""
Teamz Lab Tools — Automated Backlink & Directory Submission Script
Submits site to 40+ free tool directories and backlink sources.

Usage:
    python3 scripts/build-backlinks.py                  # Show status + next actions
    python3 scripts/build-backlinks.py submit            # Open directories in browser to submit
    python3 scripts/build-backlinks.py submit --auto     # Auto-submit where API available
    python3 scripts/build-backlinks.py ping              # Ping blog/indexing services (automated)
    python3 scripts/build-backlinks.py status            # Show submission status
    python3 scripts/build-backlinks.py next              # Show next pending directories to work
    python3 scripts/build-backlinks.py clipboard [id|n]  # Copy targeted submission details by directory id or queue number

Directories are categorized by link type:
    - DoFollow: Pass SEO authority (most valuable)
    - NoFollow: Don't pass authority but drive traffic
    - UGC/Mixed: May vary per page
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
import ssl
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
HISTORY_FILE = SCRIPT_DIR / "backlinks-history.json"
INDEXING_SCRIPT = SCRIPT_DIR / "build-request-indexing.py"

# ──────────────────────────────────────────────────────────────
# Site Details (used for submissions)
# ──────────────────────────────────────────────────────────────
SITE = {
    "name": "Teamz Lab Tools",
    "url": "https://tool.teamzlab.com",
    "tagline": "1900+ free browser-based tools — no signup, no data collection, 100% private",
    "description": "Teamz Lab Tools is a collection of 1900+ free online tools that run entirely in your browser. Calculators, converters, generators, SEO tools, developer tools, health calculators, finance tools, and more. No signup required, no data uploaded — everything stays private on your device.",
    "short_description": "1900+ free browser tools. No signup. 100% private.",
    "categories": ["Tools", "Productivity", "Developer Tools", "Calculators", "Free"],
    "tags": ["free-tools", "online-calculator", "developer-tools", "privacy", "browser-based", "no-signup"],
    "logo": "https://tool.teamzlab.com/icons/icon-512.png",
    "screenshot": "https://tool.teamzlab.com/og-images/home.png",
    "owner": "Teamz Lab LTD",
    "email": "teamz.lab.contact@gmail.com",
    "twitter": "@teamzlab",
    "github": "https://github.com/Teamz-Lab-LTD",
}

SUBMISSION_PROFILES = {
    "hackernews": {
        "listing_title": "Show HN: I built 1900+ free browser-based tools that run locally",
        "destination_url": "https://tool.teamzlab.com/",
        "primary_angle": "Privacy-first browser-based tool library with no signup and client-side execution.",
        "short_pitch": "A large collection of free browser-based tools across calculators, developer utilities, SEO helpers, converters, and workflow tools. No signup and no server-side data collection.",
        "support_asset": "docs/research/backlink-priority-batch-2026-03-29.md",
    },
    "trustpilot": {
        "listing_title": "Teamz Lab Tools",
        "destination_url": "https://tool.teamzlab.com/",
        "primary_angle": "Business profile for the tool collection and brand entity.",
        "short_pitch": "A privacy-first library of 1900+ browser-based tools for finance, health, design, SEO, developer workflows, and everyday calculations.",
        "support_asset": "docs/research/backlink-priority-batch-2026-03-29.md",
    },
    "behance": {
        "listing_title": "Teamz Lab Tools — Browser-Based Creative Utilities",
        "destination_url": "https://tool.teamzlab.com/design/logo-text-maker/",
        "primary_angle": "Portfolio-style showcase starting from a visually demonstrable design tool.",
        "short_pitch": "Showcase the design side of Teamz Lab Tools through a browser-based text logo maker and related creative utilities.",
        "support_asset": "scripts/distribute/articles/free-logo-design-tools.md",
    },
    "sourceforge": {
        "listing_title": "Text Logo Maker by Teamz Lab Tools",
        "destination_url": "https://tool.teamzlab.com/design/logo-text-maker/",
        "primary_angle": "Free, browser-based logo text maker with transparent PNG export and no watermark.",
        "short_pitch": "A fast text logo maker for founders, side projects, and internal tools. Runs in the browser, exports clean PNG logos, and avoids heavyweight design suites.",
        "support_asset": "scripts/distribute/articles/free-logo-design-tools.md",
    },
    "g2": {
        "listing_title": "Teamz Lab Tools",
        "destination_url": "https://tool.teamzlab.com/",
        "primary_angle": "Broad browser-based utility suite for everyday workflows.",
        "short_pitch": "A browser-based collection of calculators, generators, and workflow helpers with no signup requirement and privacy-first execution.",
        "support_asset": "docs/research/backlink-priority-batch-2026-03-29.md",
    },
    "producthunt": {
        "listing_title": "Amazon Seller Calculator Pack",
        "destination_url": "https://tool.teamzlab.com/amazon/acos-calculator/",
        "primary_angle": "Focused launch around a narrow commercial use case instead of a generic all-tools listing.",
        "short_pitch": "A free browser-based pack of Amazon seller calculators covering ACOS, BSR, fees, and profit estimation without login friction.",
        "support_asset": "scripts/distribute/articles/amazon-seller-tools-2026.md",
    },
    "capterra": {
        "listing_title": "Teamz Lab Tools",
        "destination_url": "https://tool.teamzlab.com/",
        "primary_angle": "Software directory profile for the main tool suite.",
        "short_pitch": "A browser-based suite of free calculators, generators, converters, and operations tools for teams, individuals, and small businesses.",
        "support_asset": "docs/research/backlink-priority-batch-2026-03-29.md",
    },
    "crunchbase": {
        "listing_title": "Teamz Lab LTD",
        "destination_url": "https://tool.teamzlab.com/",
        "primary_angle": "Company profile and brand-level listing.",
        "short_pitch": "Teamz Lab LTD builds privacy-first browser-based software tools and utility products with strong organic search coverage across many niches.",
        "support_asset": "docs/research/backlink-priority-batch-2026-03-29.md",
    },
    "wellfound": {
        "listing_title": "Teamz Lab LTD",
        "destination_url": "https://tool.teamzlab.com/",
        "primary_angle": "Company profile for startup and brand visibility.",
        "short_pitch": "A startup building a large free browser-based tool platform with SEO-led growth and privacy-first product positioning.",
        "support_asset": "docs/research/backlink-priority-batch-2026-03-29.md",
    },
    "getapp": {
        "listing_title": "Teamz Lab Tools",
        "destination_url": "https://tool.teamzlab.com/",
        "primary_angle": "Software directory profile for the broader tool suite.",
        "short_pitch": "A free browser-based software utility suite covering calculators, generators, SEO tools, health tools, and developer utilities.",
        "support_asset": "docs/research/backlink-priority-batch-2026-03-29.md",
    },
    "alternativeto": {
        "listing_title": "Text Logo Maker by Teamz Lab Tools",
        "destination_url": "https://tool.teamzlab.com/design/logo-text-maker/",
        "primary_angle": "Alternative to Canva text-logo workflows and other quick logo makers.",
        "short_pitch": "A free text logo maker with transparent export, no watermark, and no signup. Good fit for lightweight founder and side-project workflows.",
        "support_asset": "scripts/distribute/articles/free-logo-design-tools.md",
    },
    "futurepedia": {
        "listing_title": "Text Logo Maker by Teamz Lab Tools",
        "destination_url": "https://tool.teamzlab.com/design/logo-text-maker/",
        "primary_angle": "Light automation angle for fast browser-based logo generation.",
        "short_pitch": "A quick browser-based tool for generating text-led logos and exporting them fast for prototypes, launches, and lightweight brand kits.",
        "support_asset": "scripts/distribute/articles/free-logo-design-tools.md",
    },
    "saashub": {
        "listing_title": "Signature Background Remover by Teamz Lab Tools",
        "destination_url": "https://tool.teamzlab.com/tools/signature-background-remover/",
        "primary_angle": "Narrow browser-based workflow tool with immediate business utility.",
        "short_pitch": "Remove the background from a handwritten signature and export a transparent PNG for forms, PDFs, and documents without uploading to a server.",
        "support_asset": "scripts/distribute/articles/signature-tools-collection.md",
    },
    "stackshare": {
        "listing_title": "Number Typing Practice by Teamz Lab Tools",
        "destination_url": "https://tool.teamzlab.com/tools/number-typing-practice/",
        "primary_angle": "Operator and workflow utility for 10-key and data-entry training.",
        "short_pitch": "A browser-based 10-key and number typing practice tool for data-entry, cashier, and operations workflows.",
        "support_asset": "scripts/distribute/articles/career-resume-tools.md",
    },
}

# ──────────────────────────────────────────────────────────────
# Directory Database
# ──────────────────────────────────────────────────────────────
DIRECTORIES = [
    # ── DoFollow Directories (Most Valuable) ──
    {
        "id": "producthunt",
        "name": "Product Hunt",
        "url": "https://www.producthunt.com/posts/new",
        "link_type": "DoFollow",
        "da": 91,
        "category": "Startup/Product",
        "notes": "Launch as a product. Best on Tuesday-Thursday. Need an account.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "alternativeto",
        "name": "AlternativeTo",
        "url": "https://alternativeto.net/manage/new-app/",
        "link_type": "DoFollow",
        "da": 73,
        "category": "Software Directory",
        "notes": "List as alternative to Calculator.net, TinyWow, SmallSEOTools. Add multiple alternatives.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "saashub",
        "name": "SaaSHub",
        "url": "https://www.saashub.com/submit",
        "link_type": "DoFollow",
        "da": 56,
        "category": "SaaS Directory",
        "notes": "Free listing. Add as alternative to popular tools.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "sourceforge",
        "name": "SourceForge",
        "url": "https://sourceforge.net/software/product/new",
        "link_type": "DoFollow",
        "da": 92,
        "category": "Software Directory",
        "notes": "DA 92! Free listing, high authority. List under Productivity > Calculators.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "slant",
        "name": "Slant",
        "url": "https://www.slant.co/improve",
        "link_type": "DoFollow",
        "da": 58,
        "category": "Recommendation",
        "notes": "Add to 'What are the best free online tools?' type questions.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "stackshare",
        "name": "StackShare",
        "url": "https://stackshare.io/submit",
        "link_type": "DoFollow",
        "da": 72,
        "category": "Developer",
        "notes": "For developer tools section. List JSON formatter, CSS tools, etc.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "toolpilot",
        "name": "ToolPilot.ai",
        "url": "https://www.toolpilot.ai/submit-tool",
        "link_type": "DoFollow",
        "da": 42,
        "category": "AI Tool Directory",
        "notes": "Submit AI-powered tools (summarizer, quote generator, etc.)",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "betalist",
        "name": "BetaList",
        "url": "https://betalist.com/submit",
        "link_type": "DoFollow",
        "da": 64,
        "category": "Startup",
        "notes": "Free submission (paid for faster review). Good for new products.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "sideprojectors",
        "name": "SideProjectors",
        "url": "https://www.sideprojectors.com/",
        "link_type": "DoFollow",
        "da": 45,
        "category": "Side Project",
        "notes": "List as a free side project / open tool collection.",
        "auto": False,
        "priority": 3,
    },
    {
        "id": "launchingnext",
        "name": "Launching Next",
        "url": "https://www.launchingnext.com/submit/",
        "link_type": "DoFollow",
        "da": 43,
        "category": "Startup",
        "notes": "Free startup directory. Quick approval.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "startupbase",
        "name": "StartupBase",
        "url": "https://startupbase.io/startups/new",
        "link_type": "DoFollow",
        "da": 38,
        "category": "Startup",
        "notes": "Free startup listing directory.",
        "auto": False,
        "priority": 3,
    },
    {
        "id": "webtools_directory",
        "name": "WebToolHub",
        "url": "https://www.webtoolhub.com/submit.aspx",
        "link_type": "DoFollow",
        "da": 35,
        "category": "Web Tools",
        "notes": "Niche-relevant directory for web tools.",
        "auto": False,
        "priority": 3,
    },
    {
        "id": "1000tools",
        "name": "1000.tools",
        "url": "https://1000.tools/submit",
        "link_type": "DoFollow",
        "da": 30,
        "category": "Tool Directory",
        "notes": "Curated tool directory. Free submission.",
        "auto": False,
        "priority": 3,
    },
    {
        "id": "toolify",
        "name": "Toolify.ai",
        "url": "https://www.toolify.ai/submit",
        "link_type": "DoFollow",
        "da": 52,
        "category": "AI Tool Directory",
        "notes": "Growing AI tool directory. Submit AI-powered tools.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "futurepedia",
        "name": "Futurepedia",
        "url": "https://www.futurepedia.io/submit-tool",
        "link_type": "DoFollow",
        "da": 60,
        "category": "AI Tool Directory",
        "notes": "Major AI tool directory. High DA.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "topai",
        "name": "TopAI.tools",
        "url": "https://topai.tools/submit",
        "link_type": "DoFollow",
        "da": 45,
        "category": "AI Tool Directory",
        "notes": "AI tool directory with free listings.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "aitoptools",
        "name": "AITopTools",
        "url": "https://aitoptools.com/submit-tool/",
        "link_type": "DoFollow",
        "da": 40,
        "category": "AI Tool Directory",
        "notes": "Free AI tool directory listing.",
        "auto": False,
        "priority": 3,
    },
    {
        "id": "startupstash",
        "name": "Startup Stash",
        "url": "https://startupstash.com/add-listing/",
        "link_type": "DoFollow",
        "da": 56,
        "category": "Startup Resource",
        "notes": "Curated directory of startup resources and tools.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "getapp",
        "name": "GetApp",
        "url": "https://www.getapp.com/submit/",
        "link_type": "DoFollow",
        "da": 78,
        "category": "Software Review",
        "notes": "DA 78! Free listing on Gartner-owned directory.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "g2",
        "name": "G2",
        "url": "https://www.g2.com/products/new",
        "link_type": "DoFollow",
        "da": 92,
        "category": "Software Review",
        "notes": "DA 92! Premier software review site. Free listing available.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "capterra",
        "name": "Capterra",
        "url": "https://www.capterra.com/vendors/sign-up",
        "link_type": "DoFollow",
        "da": 91,
        "category": "Software Review",
        "notes": "DA 91! Gartner-owned. Free basic listing.",
        "auto": False,
        "priority": 1,
    },

    # ── NoFollow but High Traffic ──
    {
        "id": "reddit_iib",
        "name": "Reddit r/InternetIsBeautiful",
        "url": "https://www.reddit.com/r/InternetIsBeautiful/submit",
        "link_type": "NoFollow",
        "da": 99,
        "category": "Social/Community",
        "notes": "DA 99! Post your best single tool. Can go viral. NoFollow but massive traffic.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "reddit_webdev",
        "name": "Reddit r/webdev",
        "url": "https://www.reddit.com/r/webdev/submit",
        "link_type": "NoFollow",
        "da": 99,
        "category": "Social/Community",
        "notes": "For developer tools. Share dev tools with explanation of how you built them.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "reddit_sideproject",
        "name": "Reddit r/SideProject",
        "url": "https://www.reddit.com/r/SideProject/submit",
        "link_type": "NoFollow",
        "da": 99,
        "category": "Social/Community",
        "notes": "Great for 'I built 1900 free tools' type posts.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "hackernews",
        "name": "Hacker News (Show HN)",
        "url": "https://news.ycombinator.com/submit",
        "link_type": "DoFollow",
        "da": 93,
        "category": "Tech Community",
        "notes": "DA 93, DoFollow! Use 'Show HN: I built 1900+ free browser tools'. Can drive massive traffic.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "indiehackers",
        "name": "Indie Hackers",
        "url": "https://www.indiehackers.com/products/new",
        "link_type": "DoFollow",
        "da": 65,
        "category": "Indie/Startup",
        "notes": "List as a product, share revenue journey. DoFollow profile link.",
        "auto": False,
        "priority": 2,
    },

    # ── Automated Ping Services ──
    {
        "id": "ping_google",
        "name": "Google Ping",
        "url": "https://www.google.com/ping?sitemap=https://tool.teamzlab.com/sitemap.xml",
        "link_type": "Indexing",
        "da": 100,
        "category": "Ping/Index",
        "notes": "Notify Google of sitemap update.",
        "auto": True,
        "priority": 1,
    },
    {
        "id": "ping_bing",
        "name": "Bing Ping",
        "url": "https://www.bing.com/ping?sitemap=https://tool.teamzlab.com/sitemap.xml",
        "link_type": "Indexing",
        "da": 100,
        "category": "Ping/Index",
        "notes": "Notify Bing of sitemap update.",
        "auto": True,
        "priority": 1,
    },
    {
        "id": "ping_indexnow",
        "name": "IndexNow (Bing/Yandex)",
        "url": "https://api.indexnow.org/indexnow",
        "link_type": "Indexing",
        "da": 0,
        "category": "Ping/Index",
        "notes": "Batch submit URLs to Bing, Yandex, Seznam, Naver.",
        "auto": True,
        "priority": 1,
    },

    # ── Web Directories ──
    {
        "id": "crunchbase",
        "name": "Crunchbase",
        "url": "https://www.crunchbase.com/add-new",
        "link_type": "DoFollow",
        "da": 91,
        "category": "Business Directory",
        "notes": "DA 91! Add Teamz Lab LTD as a company. Free basic profile.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "trustpilot",
        "name": "Trustpilot",
        "url": "https://business.trustpilot.com/signup",
        "link_type": "DoFollow",
        "da": 93,
        "category": "Review Site",
        "notes": "DA 93! Already have a page. Claim and optimize your business profile.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "f6s",
        "name": "F6S",
        "url": "https://www.f6s.com/company/new",
        "link_type": "DoFollow",
        "da": 62,
        "category": "Startup",
        "notes": "Free startup profile with DoFollow link.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "angellist",
        "name": "Wellfound (AngelList)",
        "url": "https://wellfound.com/company/new",
        "link_type": "DoFollow",
        "da": 90,
        "category": "Startup",
        "notes": "DA 90! Create company profile with link to site.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "devpost",
        "name": "Devpost",
        "url": "https://devpost.com/software/new",
        "link_type": "DoFollow",
        "da": 70,
        "category": "Developer",
        "notes": "Post as a software project. Good for developer tools.",
        "auto": False,
        "priority": 2,
    },

    # ── Profile Backlinks (Create once) ──
    {
        "id": "about_me",
        "name": "About.me",
        "url": "https://about.me/signup",
        "link_type": "DoFollow",
        "da": 82,
        "category": "Profile",
        "notes": "DA 82! Create profile with link. Quick 2-min setup.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "gravatar",
        "name": "Gravatar",
        "url": "https://gravatar.com/profiles/new",
        "link_type": "DoFollow",
        "da": 88,
        "category": "Profile",
        "notes": "DA 88! Add website link to Gravatar profile.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "linktree",
        "name": "Linktree",
        "url": "https://linktr.ee/register",
        "link_type": "DoFollow",
        "da": 82,
        "category": "Profile",
        "notes": "DA 82! Link-in-bio with DoFollow. Free tier.",
        "auto": False,
        "priority": 2,
    },
    {
        "id": "behance",
        "name": "Behance",
        "url": "https://www.behance.net/",
        "link_type": "DoFollow",
        "da": 93,
        "category": "Portfolio",
        "notes": "DA 93! Create project showcasing your tools. Adobe-owned.",
        "auto": False,
        "priority": 1,
    },
    {
        "id": "dribbble",
        "name": "Dribbble",
        "url": "https://dribbble.com/signup/new",
        "link_type": "DoFollow",
        "da": 92,
        "category": "Portfolio",
        "notes": "DA 92! Showcase tool screenshots. Free account.",
        "auto": False,
        "priority": 2,
    },
]


def load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return {}


def save_history(history):
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def mark_submitted(dir_id, url="", notes=""):
    history = load_history()
    history[dir_id] = {
        "submitted_at": datetime.now().isoformat(),
        "url": url,
        "notes": notes,
        "status": "submitted"
    }
    save_history(history)


def mark_status(dir_id, status):
    history = load_history()
    if dir_id in history:
        history[dir_id]["status"] = status
        history[dir_id]["updated_at"] = datetime.now().isoformat()
        save_history(history)


def show_status():
    history = load_history()

    submitted = [d for d in DIRECTORIES if d["id"] in history]
    pending = [d for d in DIRECTORIES if d["id"] not in history and not d.get("auto")]
    auto = [d for d in DIRECTORIES if d.get("auto")]

    total_da = sum(d["da"] for d in submitted if d["link_type"] == "DoFollow")
    dofollow_count = len([d for d in submitted if d["link_type"] == "DoFollow"])

    print("=" * 64)
    print("  BACKLINK & DIRECTORY SUBMISSION STATUS")
    print("  Site: tool.teamzlab.com")
    print("=" * 64)
    print()
    print(f"  Submitted:     {len(submitted)}/{len(DIRECTORIES)}")
    print(f"  Pending:       {len(pending)}")
    print(f"  DoFollow links: {dofollow_count}")
    print(f"  Avg DA of DoFollow: {total_da // max(dofollow_count, 1)}")
    print()

    if submitted:
        print("  SUBMITTED:")
        print("  " + "-" * 60)
        for d in sorted(submitted, key=lambda x: x["da"], reverse=True):
            h = history[d["id"]]
            status = h.get("status", "submitted")
            icon = {"submitted": "~", "approved": "+", "rejected": "x"}.get(status, "?")
            print(f"  [{icon}] {d['name']:25s} DA:{d['da']:3d}  {d['link_type']:10s}  {status}")
        print()

    if pending:
        print("  PENDING (not yet submitted):")
        print("  " + "-" * 60)

        # Sort by priority then DA
        for d in sorted(pending, key=lambda x: (x["priority"], -x["da"])):
            pri = {1: "!!!", 2: "!! ", 3: "!  "}.get(d["priority"], "   ")
            print(f"  {pri} {d['name']:25s} DA:{d['da']:3d}  {d['link_type']:10s}  {d['category']}")
        print()

    # Summary by priority
    p1 = [d for d in pending if d["priority"] == 1]
    if p1:
        p1_da = [d for d in p1 if d["link_type"] == "DoFollow"]
        print(f"  PRIORITY 1: {len(p1)} directories pending ({len(p1_da)} DoFollow)")
        print(f"  Potential DA boost from P1 DoFollow: avg DA {sum(d['da'] for d in p1_da) // max(len(p1_da), 1)}")
        print()

    print("  Commands:")
    print("    python3 scripts/build-backlinks.py submit          # Open directories to submit")
    print("    python3 scripts/build-backlinks.py submit --auto   # Auto-ping indexing services")
    print("    python3 scripts/build-backlinks.py ping            # Alias for --auto ping")
    print("    python3 scripts/build-backlinks.py next 5 1        # Show next 5 pending Priority 1 directories")
    print("    python3 scripts/build-backlinks.py clipboard 1     # Copy details for queue item #1")
    print("    python3 scripts/build-backlinks.py clipboard sourceforge")
    print("    python3 scripts/build-backlinks.py done <id>       # Mark as submitted")
    print("    python3 scripts/build-backlinks.py approved <id>   # Mark as approved")
    print()


def link_sort_weight(link_type):
    weights = {
        "DoFollow": 0,
        "UGC/Mixed": 1,
        "NoFollow": 2,
        "Indexing": 3,
    }
    return weights.get(link_type, 9)


def get_pending(priority=None):
    history = load_history()
    pending = [d for d in DIRECTORIES if d["id"] not in history and not d.get("auto")]
    if priority is not None:
        pending = [d for d in pending if d["priority"] == priority]
    pending.sort(key=lambda x: (x["priority"], link_sort_weight(x["link_type"]), -x["da"]))
    return pending


def resolve_directory(selector):
    if selector is None:
        return None

    if selector.isdigit():
        queue = get_pending()
        idx = int(selector) - 1
        if 0 <= idx < len(queue):
            return queue[idx]
        return None

    return next((d for d in DIRECTORIES if d["id"] == selector), None)


def get_submission_profile(directory):
    base = {
        "listing_title": SITE["name"],
        "destination_url": SITE["url"],
        "primary_angle": SITE["tagline"],
        "short_pitch": SITE["short_description"],
        "support_asset": "docs/research/backlink-priority-batch-2026-03-29.md",
    }
    if not directory:
        return base
    profile = SUBMISSION_PROFILES.get(directory["id"], {})
    merged = dict(base)
    merged.update(profile)
    return merged


def generate_clipboard_text(selector=None):
    """Generate copy-paste text for directory submissions."""
    directory = resolve_directory(selector) if selector else None
    profile = get_submission_profile(directory)
    text = f"""
Site Name: {SITE['name']}
URL: {SITE['url']}
Tagline: {SITE['tagline']}

Description:
{SITE['description']}

Short Description: {SITE['short_description']}

Categories: {', '.join(SITE['categories'])}
Tags: {', '.join(SITE['tags'])}

Logo URL: {SITE['logo']}
Screenshot: {SITE['screenshot']}

Company: {SITE['owner']}
Email: {SITE['email']}
Twitter: {SITE['twitter']}
GitHub: {SITE['github']}

Key Features:
- 1900+ free browser-based tools
- No signup or account required
- 100% client-side — data never leaves your browser
- Covers: Finance, Health, Developer, SEO, Math, Career, Design, and 30+ categories
- Works offline after first load (PWA)
- Dark/Light mode
- Mobile responsive
"""
    text = text.strip()

    if directory:
        text += f"""

Directory Submission Target:
- Directory: {directory['name']} ({directory['id']})
- Listing Title: {profile['listing_title']}
- Destination URL: {profile['destination_url']}
- Primary Angle: {profile['primary_angle']}
- Short Pitch: {profile['short_pitch']}
- Support Asset: {profile['support_asset']}
- Directory Notes: {directory['notes']}
""".rstrip()

    return text.strip()


def do_submit(auto_only=False):
    if auto_only:
        # Auto-ping indexing services
        print("\n  AUTO-PINGING indexing services...\n")
        ctx = ssl.create_default_context()

        for d in DIRECTORIES:
            if not d.get("auto"):
                continue
            if d["id"] == "ping_indexnow":
                if not INDEXING_SCRIPT.exists():
                    print(f"  [skip] {d['name']} — {INDEXING_SCRIPT.name} not found")
                    continue
                try:
                    result = subprocess.run(
                        [sys.executable, str(INDEXING_SCRIPT), "--indexnow-only"],
                        capture_output=True,
                        text=True,
                        timeout=120,
                        check=False,
                    )
                    if result.stdout.strip():
                        for line in result.stdout.strip().splitlines():
                            print(f"         {line}")
                    if result.returncode == 0:
                        print(f"  [ok]   {d['name']} — submitted via {INDEXING_SCRIPT.name}")
                        mark_submitted(d["id"], d["url"], "Submitted via build-request-indexing.py --indexnow-only")
                    else:
                        print(f"  [fail] {d['name']} — {INDEXING_SCRIPT.name} exited {result.returncode}")
                    if result.stderr.strip():
                        print(f"         stderr: {result.stderr.strip()[:200]}")
                except Exception as e:
                    print(f"  [fail] {d['name']} — {e}")
                continue

            try:
                req = urllib.request.Request(d["url"], method="GET")
                req.add_header("User-Agent", "TeamzLabTools/1.0")
                resp = urllib.request.urlopen(req, timeout=10, context=ctx)
                status = resp.getcode()
                print(f"  [ok]   {d['name']} — HTTP {status}")
                mark_submitted(d["id"], d["url"], f"Auto-pinged, HTTP {status}")
            except urllib.error.HTTPError as e:
                if d["id"] == "ping_bing" and e.code == 410:
                    print(f"  [skip] {d['name']} — endpoint retired (HTTP 410), use IndexNow instead")
                elif d["id"] == "ping_google" and e.code == 429:
                    print(f"  [skip] {d['name']} — rate limited (HTTP 429), retry later or rely on sitemap fetch")
                else:
                    print(f"  [fail] {d['name']} — HTTP {e.code}: {e.reason}")
            except Exception as e:
                print(f"  [fail] {d['name']} — {e}")
        print()
        return

    # Interactive: open pending directories in browser
    pending = get_pending()

    if not pending:
        print("\n  All directories have been submitted!\n")
        return

    # Copy submission details to clipboard
    clip_text = generate_clipboard_text()
    try:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(clip_text.encode())
        print("\n  Submission details copied to clipboard!\n")
    except Exception:
        print("\n  (Could not copy to clipboard — print details below)")
        print(clip_text)
        print()

    print(f"  Opening {min(5, len(pending))} highest-priority directories...\n")
    print(f"  Paste the clipboard content into each submission form.\n")

    for i, d in enumerate(pending[:5]):
        pri = {1: "P1", 2: "P2", 3: "P3"}.get(d["priority"], "P?")
        print(f"  [{pri}] {d['name']:25s} DA:{d['da']:3d}  {d['link_type']}")
        print(f"        {d['url']}")
        print(f"        Note: {d['notes']}")
        print()

    answer = input("  Open these 5 in browser? [Y/n]: ").strip().lower()
    if answer != "n":
        for d in pending[:5]:
            webbrowser.open(d["url"])
            print(f"  Opened: {d['name']}")

    print()
    print(f"  After submitting, mark each as done:")
    for d in pending[:5]:
        print(f"    python3 scripts/build-backlinks.py done {d['id']}")
    print()

    remaining = len(pending) - 5
    if remaining > 0:
        print(f"  {remaining} more directories remaining. Run again after finishing these.\n")


def show_next(limit=5, priority=None):
    pending = get_pending(priority)

    if not pending:
        print("\n  No pending directories match that filter.\n")
        return

    print("=" * 64)
    print("  NEXT BACKLINK SUBMISSION QUEUE")
    print("=" * 64)
    print()

    for idx, d in enumerate(pending[:limit], start=1):
        pri = {1: "P1", 2: "P2", 3: "P3"}.get(d["priority"], "P?")
        profile = get_submission_profile(d)
        print(f"  {idx}. [{pri}] {d['name']} ({d['id']})")
        print(f"     DA: {d['da']} | Link: {d['link_type']} | Category: {d['category']}")
        print(f"     URL: {d['url']}")
        print(f"     Target: {profile['destination_url']}")
        print(f"     Listing: {profile['listing_title']}")
        print(f"     Notes: {d['notes']}")
        print()

    remaining = len(pending) - min(limit, len(pending))
    if remaining > 0:
        print(f"  Remaining after this batch: {remaining}")
        print()


def do_clipboard(selector=None):
    clip_text = generate_clipboard_text(selector)
    directory = resolve_directory(selector) if selector else None

    try:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(clip_text.encode())
        print(f"\n  Submission details copied to clipboard!\n")
    except Exception:
        print(clip_text)

    if directory:
        profile = get_submission_profile(directory)
        print(f"  Ready for: {directory['name']} ({directory['id']})")
        print(f"  Suggested target: {profile['destination_url']}")
        print(f"  Suggested listing: {profile['listing_title']}\n")


def do_mark(dir_id, status="submitted"):
    d = next((d for d in DIRECTORIES if d["id"] == dir_id), None)
    if not d:
        print(f"\n  Unknown directory: {dir_id}")
        print(f"  Available IDs: {', '.join(d['id'] for d in DIRECTORIES)}\n")
        return

    if status == "submitted":
        mark_submitted(dir_id)
        print(f"\n  Marked {d['name']} as submitted\n")
    else:
        mark_status(dir_id, status)
        print(f"\n  Marked {d['name']} as {status}\n")


def main():
    args = sys.argv[1:]

    if not args or args[0] == "status":
        show_status()
    elif args[0] == "submit":
        auto_only = "--auto" in args
        do_submit(auto_only)
    elif args[0] == "ping":
        do_submit(auto_only=True)
    elif args[0] == "next":
        limit = 5
        priority = None
        if len(args) > 1:
            try:
                limit = max(1, int(args[1]))
            except ValueError:
                pass
        if len(args) > 2:
            try:
                priority = int(args[2])
            except ValueError:
                pass
        show_next(limit, priority)
    elif args[0] == "clipboard":
        dir_id = args[1] if len(args) > 1 else None
        do_clipboard(dir_id)
    elif args[0] == "done":
        if len(args) < 2:
            print("\n  Usage: python3 scripts/build-backlinks.py done <directory_id>\n")
            return
        do_mark(args[1], "submitted")
    elif args[0] == "approved":
        if len(args) < 2:
            print("\n  Usage: python3 scripts/build-backlinks.py approved <directory_id>\n")
            return
        do_mark(args[1], "approved")
    elif args[0] == "rejected":
        if len(args) < 2:
            print("\n  Usage: python3 scripts/build-backlinks.py rejected <directory_id>\n")
            return
        do_mark(args[1], "rejected")
    elif args[0] == "list":
        for d in sorted(DIRECTORIES, key=lambda x: -x["da"]):
            if d.get("auto"):
                continue
            print(f"  {d['id']:25s} DA:{d['da']:3d}  {d['link_type']:10s}  {d['name']}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
