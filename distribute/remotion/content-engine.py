#!/usr/bin/env python3
"""
Teamz Lab — Content Intelligence Engine for Video

Pulls real data from free sources, auto-generates optimized video content plans.
Outputs ready-to-render JSON for render-batch.js.

Data Sources (all free, no API key needed):
  - Google Trends (trending topics via RSS)
  - YouTube Autocomplete (search suggestions)
  - Google Autocomplete (search suggestions)
  - Existing Search Console data (if available)
  - Existing ASO keyword data (if app)
  - YouTube Trending Videos API (via YouTube Data API — already connected)

Usage:
    python3 content-engine.py                      # Auto-generate 10 video plans
    python3 content-engine.py --count 30           # Generate 30 plans
    python3 content-engine.py --niche "pdf tools"  # Plans for specific niche
    python3 content-engine.py --trending           # Use Google Trends data
    python3 content-engine.py --app "DeviceGPT"    # ASO-optimized for app
    python3 content-engine.py --export             # Export as products.json for render-batch
    python3 content-engine.py --ideas              # Just show ideas, don't write files
"""

import json
import os
import re
import sys
import html
import random
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Project root for loading tool data
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

# ═════════════════════════════════════════════════════════════════════════════
# FREE DATA SOURCES
# ═════════════════════════════════════════════════════════════════════════════

def youtube_autocomplete(query):
    """Get YouTube search suggestions (free, no API key)"""
    try:
        url = f"https://suggestqueries-clients6.youtube.com/complete/search?client=youtube&ds=yt&q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=8)
        raw = resp.read().decode("utf-8", errors="replace")
        # Parse JSONP response
        match = re.search(r'\[.*\]', raw)
        if match:
            data = json.loads(match.group())
            if len(data) > 1 and isinstance(data[1], list):
                return [item[0] if isinstance(item, list) else str(item) for item in data[1]]
    except Exception as e:
        pass
    return []


def google_autocomplete(query):
    """Get Google search suggestions (free, no API key)"""
    try:
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=8)
        data = json.loads(resp.read())
        if len(data) > 1:
            return data[1][:10]
    except Exception:
        pass
    return []


def google_trends_daily():
    """Get daily trending searches from Google Trends RSS (free)"""
    try:
        url = "https://trends.google.com/trending/rss?geo=US"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read().decode("utf-8", errors="replace")
        # Simple XML parsing for <title> tags
        titles = re.findall(r'<title>([^<]+)</title>', raw)
        # Skip the feed title (first one)
        return [t.strip() for t in titles[1:20] if t.strip() and "Daily" not in t]
    except Exception:
        pass
    return []


def youtube_trending_videos(category_id=28, max_results=10):
    """Get trending YouTube videos in a category via YouTube Data API"""
    token_file = Path.home() / ".config" / "teamzlab" / "youtube-token.json"
    if not token_file.exists():
        return []
    try:
        tokens = json.loads(token_file.read_text())
        access_token = tokens.get("access_token", "")
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&chart=mostPopular&regionCode=US&videoCategoryId={category_id}&maxResults={max_results}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return [
            {"title": item["snippet"]["title"], "tags": item["snippet"].get("tags", [])[:5]}
            for item in data.get("items", [])
        ]
    except Exception:
        return []


def load_search_console_keywords():
    """Load top keywords from Search Console data (if available)"""
    sc_file = PROJECT_ROOT / "data" / "seo-latest-report.txt"
    if not sc_file.exists():
        # Try automation data
        sc_file = SCRIPT_DIR.parent.parent / "data" / "seo-latest-report.txt"
    if not sc_file.exists():
        return []
    try:
        raw = sc_file.read_text(errors="replace")
        # Extract keywords — usually "query | clicks | impressions | position" format
        keywords = []
        for line in raw.split("\n"):
            parts = line.strip().split("|")
            if len(parts) >= 3:
                kw = parts[0].strip()
                if kw and not kw.startswith("query") and len(kw) > 3:
                    keywords.append(kw)
        return keywords[:50]
    except Exception:
        return []


def load_tools_from_index():
    """Load tools from search-index.js"""
    idx_file = PROJECT_ROOT / "shared" / "js" / "search-index.js"
    if not idx_file.exists():
        return []
    raw = idx_file.read_text(errors="replace")
    tools = []
    for m in re.finditer(r"\{t:'([^']*)',d:'([^']*)',h:'([^']*)'\}", raw):
        title, desc, href = m.groups()
        parts = [p for p in href.strip("/").split("/") if p]
        if len(parts) < 2:
            continue
        tools.append({
            "title": html.unescape(title),
            "desc": html.unescape(desc),
            "href": href,
            "hub": parts[0],
        })
    return tools


# ═════════════════════════════════════════════════════════════════════════════
# YOUTUBE SEO OPTIMIZATION
# ═════════════════════════════════════════════════════════════════════════════

# YouTube categories
CATEGORIES = {
    "tools": 28,       # Science & Technology
    "ai": 28,          # Science & Technology
    "dev": 28,         # Science & Technology
    "design": 26,      # Howto & Style
    "career": 27,      # Education
    "finance": 27,     # Education
    "health": 26,      # Howto & Style
    "education": 27,   # Education
    "productivity": 28,# Science & Technology
    "app": 28,         # Science & Technology
    "service": 28,     # Science & Technology
}

# Hook templates by style
HOOKS_BY_STYLE = {
    "pain": [
        "Stop paying for {keyword}",
        "You're wasting time doing {keyword} manually",
        "Don't install software for {keyword}",
        "{keyword} shouldn't cost money",
        "Why are you still paying for {keyword}?",
    ],
    "curiosity": [
        "This free {keyword} tool is actually insane",
        "I can't believe this {keyword} tool is free",
        "Nobody talks about this free {keyword}",
        "Wait till you see this {keyword} result",
        "How is this {keyword} tool free??",
    ],
    "outcome": [
        "{keyword} in 10 seconds — for free",
        "I replaced $500/mo with this free {keyword}",
        "3 free {keyword} tools you need right now",
        "Best free {keyword} — no signup required",
        "Free {keyword} that actually works",
    ],
    "social_proof": [
        "1800+ free tools including {keyword}",
        "Every {audience} needs this free {keyword}",
        "3 websites every {audience} should bookmark",
        "The free {keyword} professionals actually use",
        "Why developers switched to this free {keyword}",
    ],
}

# Template selection logic
TEMPLATE_MAP = {
    "comparison": "CompareThree",
    "before_after": "BeforeAfter",
    "case_study": "ProofCase",
    "demo": "InstantFix",
    "tutorial": "InstantFix",
    "review": "ProofCase",
    "list": "InstantFix",
}

# Audience mapping
AUDIENCE_MAP = {
    "ai": "creator",
    "dev": "developer",
    "design": "designer",
    "career": "job seeker",
    "finance": "person",
    "health": "person",
    "pdf": "professional",
    "text": "writer",
    "image": "creator",
    "video": "creator",
    "productivity": "professional",
}


def clean_keyword(kw):
    """Strip 'free' entirely from keyword — hooks/titles add it themselves"""
    words = kw.strip().split()
    cleaned = [w for w in words if w.lower() != "free"]
    result = " ".join(cleaned).strip()
    # Also remove "online" suffix (titles add it)
    result = re.sub(r'\s+online\s*$', '', result, flags=re.IGNORECASE)
    return result if result else kw


def generate_title(tool_title, keyword, style="outcome"):
    """Generate YouTube-optimized title (<60 chars, keyword-first)"""
    kw = clean_keyword(keyword).title()
    templates = [
        f"{tool_title} — Free, No Signup",
        f"Free {tool_title} Online (No Install)",
        f"{kw} in Seconds — Free Tool",
        f"Best Free {kw} — No Signup",
        f"{tool_title} — 100% Private & Free",
        f"Free {kw} That Actually Works",
        f"Stop Paying for {kw}",
        f"{kw} — Free Browser Tool",
    ]
    # Pick one that fits <60 chars
    valid = [t for t in templates if len(t) <= 60]
    return random.choice(valid) if valid else templates[0][:60]


def generate_description(tool, keyword, url):
    """Generate YouTube-optimized description"""
    desc = f"""{tool['title']} — {tool['desc'][:120]}

Try it FREE: https://{url}

No signup. No download. No tracking.
Your data never leaves your browser.

100% free, 100% private, works instantly.

---
{tool['title']} is one of 1800+ free browser tools at tool.teamzlab.com

#freetools #{keyword.replace(' ', '').lower()} #privacy #browsertools #nosubscription"""
    return desc


def generate_tags(tool, keyword, hub):
    """Generate YouTube tags (max 500 chars total)"""
    base_tags = [
        keyword,
        f"free {keyword}",
        f"{keyword} online",
        f"{keyword} free",
        f"best {keyword}",
        f"{keyword} no signup",
        f"{keyword} browser",
        tool["title"].lower(),
        "free tools",
        "browser tools",
        "no signup",
        "privacy",
        "online tools",
        hub,
    ]
    # Add related autocomplete suggestions
    suggestions = youtube_autocomplete(f"free {keyword}")[:5]
    base_tags.extend(suggestions)

    # Deduplicate and limit to 500 chars
    seen = set()
    unique = []
    total_len = 0
    for tag in base_tags:
        tag = tag.strip().lower()
        if tag and tag not in seen and total_len + len(tag) < 480:
            seen.add(tag)
            unique.append(tag)
            total_len += len(tag) + 1
    return unique


def pick_template(keyword, tool):
    """Pick best template based on keyword intent"""
    kw = keyword.lower()
    if any(w in kw for w in ["vs", "compare", "best", "which", "alternative"]):
        return "CompareThree"
    if any(w in kw for w in ["before", "after", "convert", "compress", "optimize", "resize"]):
        return "BeforeAfter"
    if any(w in kw for w in ["review", "case", "saved", "client", "project"]):
        return "ProofCase"
    return "InstantFix"


def pick_hook_style(template):
    """Pick hook style based on template"""
    style_map = {
        "InstantFix": random.choice(["pain", "curiosity", "outcome"]),
        "BeforeAfter": "outcome",
        "CompareThree": "curiosity",
        "ProofCase": "social_proof",
    }
    return style_map.get(template, "pain")


# ═════════════════════════════════════════════════════════════════════════════
# CONTENT PLAN GENERATOR
# ═════════════════════════════════════════════════════════════════════════════

def generate_video_plan(tool, keyword=None, trending_context=None):
    """Generate a complete video plan for one tool/product"""
    hub = tool.get("hub", "tools")
    kw = clean_keyword(keyword or tool["title"].lower())
    audience = AUDIENCE_MAP.get(hub, "person")

    # Pick template
    template = pick_template(kw, tool)

    # Pick hook
    hook_style = pick_hook_style(template)
    hook_templates = HOOKS_BY_STYLE.get(hook_style, HOOKS_BY_STYLE["pain"])
    hook = random.choice(hook_templates).format(keyword=kw, audience=audience)

    # Generate YouTube-optimized metadata
    title = generate_title(tool["title"], kw)
    url = f"tool.teamzlab.com{tool['href']}" if tool.get("href") else tool.get("url", "teamzlab.com")
    description = generate_description(tool, kw, url)
    tags = generate_tags(tool, kw, hub)
    category_id = CATEGORIES.get(hub, 28)

    # Pick theme (random for variety)
    theme_index = random.randint(0, 7)

    # Pick audio
    audio_files = [f"audio/beat{i}.mp3" for i in range(1, 11)]
    audio = random.choice(audio_files)

    plan = {
        "id": tool.get("href", "").strip("/").replace("/", "_") or tool["title"].lower().replace(" ", "-"),
        "type": tool.get("type", "tool"),

        # Remotion render props
        "render": {
            "template": template,
            "props": {
                "hook": hook,
                "title": tool["title"],
                "description": tool["desc"][:150] if tool.get("desc") else "",
                "url": url,
                "audioFile": audio,
                "themeIndex": theme_index,
                "ctaText": "Try it free",
                "ctaBadge": "LINK IN BIO",
                "brandName": url.split("/")[0] if "/" in url else url,
            },
        },

        # YouTube upload metadata
        "youtube": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "privacy": "public",
            "madeForKids": False,
            "hashtags": [f"#freetools", f"#{kw.replace(' ', '')}", "#shorts"],
        },

        # TikTok caption
        "tiktok": {
            "caption": f"{hook}\n\nTry it: {url}\n\n#freetools #{kw.replace(' ', '')} #tech #lifehack #webapp",
        },

        # Instagram caption
        "instagram": {
            "caption": f"{hook}\n\n{tool['title']} — {tool.get('desc', '')[:100]}\n\nFree. No signup. 100% private.\n\nLink in bio: {url}\n\n#freetools #{kw.replace(' ', '')} #productivity #tech #browsertools #nosubscription #webapp #lifehack",
        },

        # Metadata
        "keyword": kw,
        "hub": hub,
        "hookStyle": hook_style,
        "template": template,
        "trending": trending_context or "",
        "generatedAt": datetime.now().isoformat(),
    }

    return plan


def research_keywords_for_niche(niche, tools):
    """Research keywords using free sources and match to tools"""
    print(f"\n  Researching: {niche}")
    ideas = []

    # 1. YouTube autocomplete
    yt_suggestions = youtube_autocomplete(f"free {niche}")
    print(f"    YouTube suggestions: {len(yt_suggestions)}")
    ideas.extend(yt_suggestions)

    # 2. Google autocomplete
    g_suggestions = google_autocomplete(f"free {niche} online")
    print(f"    Google suggestions: {len(g_suggestions)}")
    ideas.extend(g_suggestions)

    # 3. More specific queries
    for prefix in ["best free", "how to", "free online"]:
        more = youtube_autocomplete(f"{prefix} {niche}")[:3]
        ideas.extend(more)

    # Deduplicate
    seen = set()
    unique = []
    for idea in ideas:
        clean = idea.strip().lower()
        if clean and clean not in seen and len(clean) > 5:
            seen.add(clean)
            unique.append(clean)

    print(f"    Total unique keywords: {len(unique)}")
    return unique


def match_keyword_to_tool(keyword, tools):
    """Find the best matching tool for a keyword"""
    kw_lower = keyword.lower()
    kw_words = set(kw_lower.split())

    best = None
    best_score = 0

    for tool in tools:
        title_lower = tool["title"].lower()
        desc_lower = tool.get("desc", "").lower()

        score = 0
        # Exact match in title
        if kw_lower in title_lower:
            score += 10
        # Word overlap
        title_words = set(title_lower.split())
        overlap = len(kw_words & title_words)
        score += overlap * 3
        # Keyword in description
        if kw_lower in desc_lower:
            score += 2
        # Word overlap with description
        desc_words = set(desc_lower.split())
        score += len(kw_words & desc_words)

        if score > best_score:
            best_score = score
            best = tool

    return best if best_score >= 3 else None


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Content Intelligence Engine")
    parser.add_argument("--count", type=int, default=10, help="Number of video plans")
    parser.add_argument("--niche", type=str, help="Specific niche (e.g., 'pdf tools')")
    parser.add_argument("--trending", action="store_true", help="Use Google Trends data")
    parser.add_argument("--app", type=str, help="App name for ASO-optimized plans")
    parser.add_argument("--export", action="store_true", help="Export as products.json")
    parser.add_argument("--ideas", action="store_true", help="Just show ideas")
    args = parser.parse_args()

    print("=" * 60)
    print("  Content Intelligence Engine — Teamz Lab")
    print("=" * 60)

    # Load tools
    tools = load_tools_from_index()
    print(f"\nLoaded {len(tools)} tools from search-index")

    # Collect keyword ideas from all free sources
    all_keywords = []

    # 1. Google Trends (if --trending) — only use tech-relevant trends
    if args.trending:
        print("\nPulling Google Trends...")
        trends = google_trends_daily()
        print(f"  Daily trends: {len(trends)}")
        tech_keywords = ["ai", "app", "tool", "software", "code", "design", "tech", "api", "web",
                         "data", "cloud", "security", "crypto", "finance", "calculator", "generator"]
        tech_trends = [t for t in trends if any(kw in t.lower() for kw in tech_keywords)]
        print(f"  Tech-relevant trends: {len(tech_trends)}")
        for t in tech_trends[:5]:
            print(f"    - {t}")
        for trend in tech_trends:
            related = youtube_autocomplete(f"{trend} free tool")[:2]
            all_keywords.extend(related)

    # 2. Niche research
    if args.niche:
        keywords = research_keywords_for_niche(args.niche, tools)
        all_keywords.extend(keywords)
    else:
        # Auto-research top niches
        top_niches = ["pdf", "image converter", "calculator", "text tools",
                      "ai tools", "resume", "grammar checker", "password generator",
                      "color picker", "qr code"]
        print("\nAuto-researching top niches...")
        for niche in random.sample(top_niches, min(4, len(top_niches))):
            keywords = research_keywords_for_niche(niche, tools)
            all_keywords.extend(keywords)

    # 3. Search Console keywords (if available)
    sc_keywords = load_search_console_keywords()
    if sc_keywords:
        print(f"\nSearch Console keywords: {len(sc_keywords)}")
        all_keywords.extend(sc_keywords[:20])

    # 4. YouTube trending in Tech (via API)
    print("\nPulling YouTube trending (Tech)...")
    trending_vids = youtube_trending_videos(category_id=28, max_results=5)
    if trending_vids:
        print(f"  Trending tech videos: {len(trending_vids)}")
        for v in trending_vids[:3]:
            print(f"    - {v['title'][:60]}")
            all_keywords.extend(v.get("tags", [])[:3])

    # Deduplicate and filter keywords
    seen = set()
    unique_keywords = []
    # Skip non-English, too-long, or irrelevant keywords
    skip_words = ["bangla", "hindi", "urdu", "tamil", "telugu", "arabic", "indonesia",
                  "español", "português", "deutsch", "français", "日本", "한국"]
    for kw in all_keywords:
        clean = kw.strip().lower()
        if not clean or clean in seen or len(clean) < 4 or len(clean) > 60:
            continue
        if any(sw in clean for sw in skip_words):
            continue
        seen.add(clean)
        unique_keywords.append(clean)

    print(f"\nTotal unique keywords collected: {len(unique_keywords)}")

    # Generate video plans
    plans = []
    used_tools = set()

    # Match keywords to tools
    for kw in unique_keywords:
        if len(plans) >= args.count:
            break
        tool = match_keyword_to_tool(kw, tools)
        if tool and tool["href"] not in used_tools:
            used_tools.add(tool["href"])
            plan = generate_video_plan(tool, keyword=kw)
            plans.append(plan)

    # If not enough, pick top tools by category
    if len(plans) < args.count:
        high_rpm_hubs = ["finance", "career", "ai", "health", "tax", "legal"]
        remaining = [t for t in tools if t["hub"] in high_rpm_hubs and t["href"] not in used_tools]
        random.shuffle(remaining)
        for tool in remaining:
            if len(plans) >= args.count:
                break
            plan = generate_video_plan(tool)
            plans.append(plan)
            used_tools.add(tool["href"])

    # App-specific plans (ASO)
    if args.app:
        print(f"\nASO mode for app: {args.app}")
        aso_keywords = youtube_autocomplete(args.app)
        aso_keywords.extend(google_autocomplete(f"{args.app} app"))
        print(f"  ASO keywords: {len(aso_keywords)}")
        for kw in aso_keywords[:5]:
            app_plan = generate_video_plan(
                {"title": args.app, "desc": f"Download {args.app} on App Store & Play Store", "href": "", "hub": "app", "type": "app"},
                keyword=kw
            )
            app_plan["render"]["props"]["ctaBadge"] = "DOWNLOAD FREE"
            app_plan["render"]["props"]["brandName"] = "teamzlab.com"
            plans.append(app_plan)

    print(f"\n{'=' * 60}")
    print(f"Generated {len(plans)} video plans")
    print(f"{'=' * 60}\n")

    # Display plans
    for i, plan in enumerate(plans, 1):
        yt = plan["youtube"]
        r = plan["render"]
        print(f"#{i} [{r['template']}] Theme {r['props']['themeIndex']}")
        print(f"  YT Title: {yt['title']}")
        print(f"  Hook: {r['props']['hook']}")
        print(f"  Keyword: {plan['keyword']}")
        print(f"  Tags: {', '.join(yt['tags'][:6])}")
        print(f"  Category: {yt['categoryId']}")
        if not args.ideas:
            print(f"  Audio: {r['props']['audioFile']}")
        print()

    # Export
    if args.export or not args.ideas:
        output_file = DATA_DIR / "video-plans.json"
        output = {
            "generated": datetime.now().isoformat(),
            "count": len(plans),
            "plans": plans,
        }
        output_file.write_text(json.dumps(output, indent=2))
        print(f"Saved to {output_file}")
        print(f"\nNext step: node render-batch.js --from-plans")

    # Also export as products.json for render-batch compatibility
    if args.export:
        products = []
        for plan in plans:
            products.append({
                "id": plan["id"],
                "type": plan.get("type", "tool"),
                "category": plan["hub"],
                "title": plan["render"]["props"]["title"],
                "description": plan["render"]["props"]["description"],
                "url": plan["render"]["props"]["url"],
                "hook": plan["render"]["props"]["hook"],
                "template": plan["template"],
                "themeIndex": plan["render"]["props"]["themeIndex"],
                "audioFile": plan["render"]["props"]["audioFile"],
                "ctaText": plan["render"]["props"]["ctaText"],
                "ctaBadge": plan["render"]["props"]["ctaBadge"],
                "brandName": plan["render"]["props"]["brandName"],
                "youtube": plan["youtube"],
                "tiktok": plan["tiktok"],
                "instagram": plan["instagram"],
            })
        products_file = DATA_DIR / "products.json"
        products_file.write_text(json.dumps({"products": products}, indent=2))
        print(f"Products exported to {products_file}")


if __name__ == "__main__":
    main()
