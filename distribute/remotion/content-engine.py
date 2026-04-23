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

# Project root for loading tool data.
# Override with env TEAMZ_HOST_SITE_ROOT when running from a host repo other
# than the one the submodule is nested under (useful for multi-project setups).
_ENV_ROOT = os.getenv("TEAMZ_HOST_SITE_ROOT", "").strip()
PROJECT_ROOT = Path(_ENV_ROOT) if _ENV_ROOT else SCRIPT_DIR.parent.parent.parent

# Per-project site + brand config — read from env (loaded from .teamz-automation.env
# by distribute.py before this module imports, or set explicitly). Falls back to
# sensible defaults so single-project repos still work with zero config.
SITE_URL = os.getenv("TEAMZ_SITE_URL", "https://apps.teamzlab.com/").rstrip("/")
BRAND_NAME = os.getenv("TEAMZ_VIDEO_BRAND", SITE_URL.replace("https://", "").replace("http://", ""))
CTA_BADGE = os.getenv("TEAMZ_VIDEO_CTA", "DOWNLOAD FREE")

# ═════════════════════════════════════════════════════════════════════════════
# FREE DATA SOURCES
# ═════════════════════════════════════════════════════════════════════════════

def youtube_autocomplete(query, lang="en"):
    """Get YouTube search suggestions (free, no API key)"""
    try:
        hl = lang if lang != "en" else ""
        lang_param = f"&hl={hl}&gl={hl.upper()}" if hl else ""
        url = f"https://suggestqueries-clients6.youtube.com/complete/search?client=youtube&ds=yt&q={urllib.parse.quote(query)}{lang_param}"
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
    """Load tools from search-index.js (tool.teamzlab.com-style catalog)"""
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


def _parse_simple_frontmatter(raw: str) -> dict:
    """Minimal YAML-ish frontmatter parser for key: value pairs + nested keys we care about.
    Avoids a pyyaml dep. Returns top-level scalar keys only — good enough for appName,
    shortDescription, primaryKeyword, playStoreUrl, appStoreUrl, platforms, secondaryKeywords."""
    if not raw.startswith("---"):
        return {}
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}
    body = parts[1]
    meta = {}
    current_list_key = None
    for line in body.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            current_list_key = None
            continue
        # continuation of a list (- item under "key:")
        if current_list_key and line.startswith(("  - ", "- ")):
            meta.setdefault(current_list_key, []).append(
                line.strip()[2:].strip().strip('"').strip("'")
            )
            continue
        if ":" not in line or line.startswith(" "):
            current_list_key = None
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if not val:
            current_list_key = key  # next lines may be list items
            continue
        current_list_key = None
        meta[key] = val.strip('"').strip("'")
    return meta


def load_tools_from_landing_pages():
    """Load app landing pages (src/content/apps/*.md) as 'app' tools for video generation.

    Makes content-engine usable from ANY host repo that ships app landing pages —
    not just the tool.teamzlab.com tools catalog. Override the scan path with env
    TEAMZ_APPS_DIR (default: <PROJECT_ROOT>/src/content/apps).
    """
    apps_dir_env = os.getenv("TEAMZ_APPS_DIR", "").strip()
    apps_dir = Path(apps_dir_env) if apps_dir_env else (PROJECT_ROOT / "src" / "content" / "apps")
    if not apps_dir.exists() or not apps_dir.is_dir():
        return []
    tools = []
    for md in sorted(apps_dir.glob("*.md")):
        if md.name.lower() == "readme.md":
            continue
        try:
            meta = _parse_simple_frontmatter(md.read_text(errors="replace"))
        except Exception:
            continue
        slug = md.stem
        name = meta.get("appName") or slug
        desc = meta.get("shortDescription") or meta.get("tagline") or ""
        landing = f"{SITE_URL}/{slug}/"
        play = meta.get("playStoreUrl", "")
        app_store = meta.get("appStoreUrl", "")
        tools.append({
            "title": name,
            "desc": desc,
            "href": landing,
            "hub": "app",
            "type": "app",
            "slug": slug,
            "landing_url": landing,
            "play_store_url": play,
            "app_store_url": app_store,
            "primary_keyword": meta.get("primaryKeyword", ""),
            "secondary_keywords": meta.get("secondaryKeywords", []),
            "platforms": meta.get("platforms", ""),
        })
    return tools


def load_tools_from_sources():
    """Combine tools from all configured sources. Dedupes by href."""
    combined = []
    seen = set()
    for t in (*load_tools_from_index(), *load_tools_from_landing_pages()):
        key = t.get("href") or t.get("title")
        if key in seen:
            continue
        seen.add(key)
        combined.append(t)
    return combined


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

# ─── Hub → Language mapping (ISO 639-1 — supported by YouTube, Android, iOS) ──
HUB_LANGUAGE = {
    "no": "no",   # Norwegian
    "de": "de",   # German
    "fr": "fr",   # French
    "se": "sv",   # Swedish
    "fi": "fi",   # Finnish
    "nl": "nl",   # Dutch
    "ae": "ar",   # Arabic (UAE)
    "sa": "ar",   # Arabic (Saudi Arabia)
    "eg": "ar",   # Arabic (Egypt)
    "ma": "ar",   # Arabic (Morocco)
    "id": "id",   # Indonesian
    "vn": "vi",   # Vietnamese
    "jp": "ja",   # Japanese
    # Future hubs
    "es": "es",   # Spanish
    "pt": "pt",   # Portuguese
    "it": "it",   # Italian
    "pl": "pl",   # Polish
    "tr": "tr",   # Turkish
    "kr": "ko",   # Korean
    "cn": "zh",   # Chinese
    "ru": "ru",   # Russian
    "th": "th",   # Thai
    "in": "hi",   # Hindi (India)
}

# Localized hook templates (most impactful hooks in each language)
LOCALIZED_HOOKS = {
    "no": {
        "pain": [
            "Slutt å betale for {keyword}",
            "Hvorfor betaler du fortsatt for {keyword}?",
            "Gratis {keyword} — ingen registrering",
            "Du trenger ikke dyre apper for {keyword}",
        ],
        "curiosity": [
            "Dette gratis {keyword}-verktøyet er helt fantastisk",
            "Kan ikke tro at dette {keyword}-verktøyet er gratis",
            "Vent til du ser hva dette verktøyet gjør",
        ],
        "outcome": [
            "Gratis {keyword} som faktisk fungerer",
            "Beste gratis {keyword} — ingen installasjon",
            "{keyword} på sekunder — helt gratis",
        ],
    },
    "de": {
        "pain": [
            "Hör auf für {keyword} zu bezahlen",
            "Warum bezahlst du noch für {keyword}?",
            "Kostenloses {keyword} — keine Anmeldung",
            "{keyword} sollte nicht Geld kosten",
        ],
        "curiosity": [
            "Dieses kostenlose {keyword}-Tool ist der Wahnsinn",
            "Ich kann nicht glauben, dass dieses {keyword}-Tool kostenlos ist",
            "Warte bis du siehst was dieses Tool kann",
        ],
        "outcome": [
            "Kostenloses {keyword} das wirklich funktioniert",
            "Bestes kostenloses {keyword} — ohne Installation",
            "{keyword} in Sekunden — komplett kostenlos",
        ],
    },
    "fr": {
        "pain": [
            "Arrêtez de payer pour {keyword}",
            "Pourquoi payez-vous encore pour {keyword} ?",
            "{keyword} gratuit — sans inscription",
        ],
        "curiosity": [
            "Cet outil {keyword} gratuit est incroyable",
            "Comment cet outil {keyword} peut être gratuit ?",
        ],
        "outcome": [
            "{keyword} gratuit qui fonctionne vraiment",
            "Meilleur {keyword} gratuit — sans installation",
        ],
    },
    "sv": {
        "pain": [
            "Sluta betala för {keyword}",
            "Varför betalar du fortfarande för {keyword}?",
            "Gratis {keyword} — ingen registrering",
        ],
        "curiosity": [
            "Det här gratis {keyword}-verktyget är helt galet",
            "Kan inte tro att det här {keyword}-verktyget är gratis",
        ],
        "outcome": [
            "Gratis {keyword} som faktiskt fungerar",
            "Bästa gratis {keyword} — ingen installation",
        ],
    },
    "fi": {
        "pain": [
            "Lopeta maksaminen {keyword}-työkaluista",
            "Miksi maksat vielä {keyword}-työkalusta?",
            "Ilmainen {keyword} — ei rekisteröitymistä",
        ],
        "curiosity": [
            "Tämä ilmainen {keyword}-työkalu on uskomaton",
        ],
        "outcome": [
            "Ilmainen {keyword} joka todella toimii",
            "Paras ilmainen {keyword} — ei asennusta",
        ],
    },
    "nl": {
        "pain": [
            "Stop met betalen voor {keyword}",
            "Waarom betaal je nog voor {keyword}?",
            "Gratis {keyword} — geen registratie",
        ],
        "curiosity": [
            "Deze gratis {keyword}-tool is echt geweldig",
            "Kan niet geloven dat deze {keyword}-tool gratis is",
        ],
        "outcome": [
            "Gratis {keyword} die echt werkt",
            "Beste gratis {keyword} — geen installatie",
        ],
    },
    "ar": {
        "pain": [
            "توقف عن الدفع مقابل {keyword}",
            "{keyword} مجاني — بدون تسجيل",
        ],
        "curiosity": [
            "أداة {keyword} المجانية هذه مذهلة",
        ],
        "outcome": [
            "{keyword} مجاني يعمل فعلاً",
        ],
    },
}

# Localized title templates
LOCALIZED_TITLES = {
    "no": [
        "{title} — Gratis, Ingen Registrering",
        "Gratis {title} på Nett",
        "Beste Gratis {keyword} — Norsk",
        "{title} — 100% Privat og Gratis",
    ],
    "de": [
        "{title} — Kostenlos, Keine Anmeldung",
        "Kostenloses {title} Online",
        "Bestes Kostenloses {keyword}",
        "{title} — 100% Privat & Kostenlos",
    ],
    "fr": [
        "{title} — Gratuit, Sans Inscription",
        "{title} Gratuit en Ligne",
        "Meilleur {keyword} Gratuit",
    ],
    "sv": [
        "{title} — Gratis, Ingen Registrering",
        "Gratis {title} Online",
        "Bästa Gratis {keyword}",
    ],
    "fi": [
        "{title} — Ilmainen, Ei Rekisteröitymistä",
        "Ilmainen {title} Verkossa",
        "Paras Ilmainen {keyword}",
    ],
    "nl": [
        "{title} — Gratis, Geen Registratie",
        "Gratis {title} Online",
        "Beste Gratis {keyword}",
    ],
    "ar": [
        "{title} — مجاني بدون تسجيل",
        "{title} مجاني عبر الإنترنت",
    ],
}

# Localized CTA text
LOCALIZED_CTA = {
    "no": {"ctaText": "Prøv nå", "ctaBadge": "LENKE I BIO", "privacy": "100% privat. Ingen registrering. Helt gratis."},
    "de": {"ctaText": "Jetzt testen", "ctaBadge": "LINK IN BIO", "privacy": "100% privat. Keine Anmeldung. Komplett kostenlos."},
    "fr": {"ctaText": "Essayez maintenant", "ctaBadge": "LIEN EN BIO", "privacy": "100% privé. Sans inscription. Entièrement gratuit."},
    "sv": {"ctaText": "Prova nu", "ctaBadge": "LÄNK I BIO", "privacy": "100% privat. Ingen registrering. Helt gratis."},
    "fi": {"ctaText": "Kokeile nyt", "ctaBadge": "LINKKI BIOSSA", "privacy": "100% yksityinen. Ei rekisteröitymistä. Täysin ilmainen."},
    "nl": {"ctaText": "Probeer nu", "ctaBadge": "LINK IN BIO", "privacy": "100% privé. Geen registratie. Helemaal gratis."},
    "ar": {"ctaText": "جرب الآن", "ctaBadge": "الرابط في البايو", "privacy": "خاص 100%. بدون تسجيل. مجاني تماماً."},
}

# Localized description template
LOCALIZED_DESC = {
    "no": "{title} — {desc}\n\nPrøv GRATIS: https://{url}\n\nIngen registrering. Ingen nedlasting.\nDataene dine forlater aldri nettleseren.\n\n100% gratis, 100% privat.\n\n---\n{title} er ett av 1800+ gratis nettleserverktøy på tool.teamzlab.com",
    "de": "{title} — {desc}\n\nJetzt KOSTENLOS testen: https://{url}\n\nKeine Anmeldung. Kein Download.\nIhre Daten verlassen nie den Browser.\n\n100% kostenlos, 100% privat.\n\n---\n{title} ist eines von 1800+ kostenlosen Browser-Tools auf tool.teamzlab.com",
    "fr": "{title} — {desc}\n\nEssayez GRATUITEMENT: https://{url}\n\nSans inscription. Sans téléchargement.\nVos données ne quittent jamais le navigateur.\n\n100% gratuit, 100% privé.\n\n---\n{title} fait partie de 1800+ outils gratuits sur tool.teamzlab.com",
    "sv": "{title} — {desc}\n\nProva GRATIS: https://{url}\n\nIngen registrering. Ingen nedladdning.\nDin data lämnar aldrig webbläsaren.\n\n100% gratis, 100% privat.",
    "fi": "{title} — {desc}\n\nKokeile ILMAISEKSI: https://{url}\n\nEi rekisteröitymistä. Ei latausta.\nTietosi eivät koskaan poistu selaimesta.\n\n100% ilmainen, 100% yksityinen.",
    "nl": "{title} — {desc}\n\nProbeer GRATIS: https://{url}\n\nGeen registratie. Geen download.\nUw data verlaat nooit de browser.\n\n100% gratis, 100% privé.",
    "ar": "{title} — {desc}\n\nجرب مجاناً: https://{url}\n\nبدون تسجيل. بدون تحميل.\nبياناتك لا تغادر المتصفح أبداً.\n\nمجاني 100%، خاص 100%.",
}


def get_language(hub):
    """Get language code for a hub"""
    return HUB_LANGUAGE.get(hub, "en")


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
    """Generate YouTube-optimized description.

    App-type tools (tool['type'] == 'app') get app-store-first copy (landing +
    Play + App Store links, no 'browser tool' framing). Catalog tools (default)
    keep the tool.teamzlab.com-style 'browser tool' copy.
    """
    if tool.get("type") == "app":
        landing = tool.get("landing_url") or (f"https://{url}" if url else "")
        play = tool.get("play_store_url", "")
        app_store = tool.get("app_store_url", "")
        store_lines = []
        if landing:
            store_lines.append(f"Learn more: {landing}")
        if play:
            store_lines.append(f"Google Play: {play}")
        if app_store:
            store_lines.append(f"App Store: {app_store}")
        stores = "\n".join(store_lines) or f"Learn more: https://{url}"
        brand = BRAND_NAME
        tool_desc = (tool.get("desc") or "")[:200]
        kw_tag = keyword.replace(" ", "").lower()
        return (
            f"{tool['title']} — {tool_desc}\n\n"
            f"{stores}\n\n"
            f"Free to install. No paywall, no subscription, no signup.\n\n"
            f"---\n"
            f"More from {brand}: https://{brand}\n\n"
            f"#app #{kw_tag} #free #nosignup"
        )

    # Default: tool catalog / browser-tool framing
    desc = f"""{tool['title']} — {tool['desc'][:120]}

Try it FREE: https://{url}

No signup. No download. No tracking.
Your data never leaves your browser.

100% free, 100% private, works instantly.

---
{tool['title']} is one of many free browser tools at {BRAND_NAME}

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
    lang = get_language(hub)

    # Pick template
    template = pick_template(kw, tool)

    # Pick hook — use localized hooks for non-English tools
    hook_style = pick_hook_style(template)
    if lang != "en" and lang in LOCALIZED_HOOKS:
        local_hooks = LOCALIZED_HOOKS[lang].get(hook_style, LOCALIZED_HOOKS[lang].get("pain", []))
        if local_hooks:
            hook = random.choice(local_hooks).format(keyword=kw, audience=audience)
        else:
            hook = random.choice(HOOKS_BY_STYLE["pain"]).format(keyword=kw, audience=audience)
    else:
        hook_templates = HOOKS_BY_STYLE.get(hook_style, HOOKS_BY_STYLE["pain"])
        hook = random.choice(hook_templates).format(keyword=kw, audience=audience)

    # Generate YouTube-optimized metadata — localized for non-English
    if lang != "en" and lang in LOCALIZED_TITLES:
        title_templates = LOCALIZED_TITLES[lang]
        title = random.choice(title_templates).format(title=tool["title"], keyword=kw.title())
        title = title[:60]
    else:
        title = generate_title(tool["title"], kw)

    # URL resolution: prefer full URLs on tool (app landings) over prepending
    # brand host. Falls back to BRAND_NAME + href for relative hrefs (tools catalog).
    href = tool.get("href") or ""
    if href.startswith(("http://", "https://")):
        url = href.replace("https://", "").replace("http://", "").rstrip("/")
    elif href:
        url = f"{BRAND_NAME}{href}"
    else:
        url = tool.get("url", BRAND_NAME)

    if lang != "en" and lang in LOCALIZED_DESC:
        description = LOCALIZED_DESC[lang].format(
            title=tool["title"], desc=tool.get("desc", "")[:120], url=url
        )
    else:
        description = generate_description(tool, kw, url)

    tags = generate_tags(tool, kw, hub)
    category_id = CATEGORIES.get(hub, 28)

    # Pick theme (random for variety)
    theme_index = random.randint(0, 7)

    # Pick audio
    audio_files = [f"audio/beat{i}.mp3" for i in range(1, 11)]
    audio = random.choice(audio_files)

    # Localized CTA
    local_cta = LOCALIZED_CTA.get(lang, {"ctaText": "Try it free", "ctaBadge": "LINK IN BIO", "privacy": "100% free. No signup. 100% private."})

    # ─── TikTok-optimized captions (viral hashtag strategy per hub) ─────────
    # Hub-specific hashtag pools: 2 niche + 1 broad topic + 1 platform + 1 tool
    # TikTok feed algorithm favors 3-5 focused hashtags over 10+ generic ones
    HUB_HASHTAGS = {
        "longevity":  ["#biohacking",    "#longevity",    "#healthtok",    "#peterattia"],
        "health":     ["#healthtok",     "#wellness",     "#healthhacks",  "#biohacking"],
        "finance":    ["#moneytok",      "#personalfinance", "#financehack", "#taxtips"],
        "tax":        ["#taxtips",       "#moneytok",     "#taxes",        "#irs"],
        "career":     ["#careeradvice",  "#resumetips",   "#jobtok",       "#careertok"],
        "resume":     ["#resumetips",    "#careeradvice", "#jobsearch",    "#jobtok"],
        "ai":         ["#aitools",       "#chatgpt",      "#techtok",      "#aitok"],
        "dev":        ["#codetok",       "#webdev",       "#programmer",   "#techtok"],
        "devicegpt":  ["#androidtips",   "#phonetips",    "#techtok",      "#smartphone"],
        "pdf":        ["#productivity",  "#officehacks",  "#lifehack",     "#techtok"],
        "image":      ["#designtok",     "#graphicdesign","#contentcreator","#techtok"],
        "video":      ["#videoediting",  "#contentcreator","#editingtips", "#techtok"],
        "design":     ["#designtok",     "#graphicdesign","#branding",     "#canva"],
        "compliance": ["#carehome",      "#nursinghome",  "#ukcare",       "#socialcare"],
        "care":       ["#carehome",      "#nursinghome",  "#caregiver",    "#healthcare"],
        "education":  ["#studytok",      "#studytips",    "#learning",     "#education"],
        "marketing":  ["#marketingtips", "#smallbusiness","#digitalmarketing","#entrepreneur"],
        "business":   ["#smallbusiness", "#entrepreneur", "#businesstips", "#startup"],
        "restaurant": ["#foodtok",       "#restaurant",   "#smallbusiness","#hospitality"],
        "eu":         ["#sustainability","#esg",          "#greenbusiness","#climate"],
        "fitness":    ["#fittok",        "#workout",      "#fitness",      "#gymtok"],
        "parenting":  ["#parentingtips", "#momsoftiktok", "#parentok",     "#momlife"],
        "travel":     ["#travelhacks",   "#traveltips",   "#budgettravel", "#traveltok"],
    }
    # Default fallback for any hub not above
    hub_tags = HUB_HASHTAGS.get(hub, ["#lifehack", "#productivity", "#techtok", "#freetools"])

    # Niche-specific engagement prompt (algorithm boosts comments/saves)
    ENGAGE_PROMPTS = {
        "longevity":  "Save this for your next bloodwork 🔖",
        "health":     "Tag someone who needs this 👇",
        "finance":    "Save this before tax season 🔖",
        "tax":        "Save this before tax season 🔖",
        "career":     "Save this for your next job hunt 🔖",
        "resume":     "Save this for your next job hunt 🔖",
        "ai":         "Which one are you trying first? 👇",
        "dev":        "Bookmark this — you'll need it 🔖",
        "devicegpt":  "Try it on your phone right now 📱",
        "compliance": "Tag your compliance lead 👇",
        "care":       "Tag your compliance lead 👇",
    }
    engage = ENGAGE_PROMPTS.get(hub, "Try it free — link in bio 🔗")

    # Shorten URL for readability (remove protocol)
    short_url = url.replace("https://", "").replace("http://", "")

    # TikTok caption — viral format:
    # [Hook] \n\n [engagement prompt] \n\n [link] \n\n [5 hashtags]
    # Total target: 120-250 chars (optimal for TikTok feed completion)
    viral_hashtags = " ".join(hub_tags[:4] + ["#fyp"])
    tt_caption = f"{hook}\n\n{engage}\n\n🔗 {short_url}\n\n{viral_hashtags}"

    # Instagram caption — longer is fine, IG rewards detail + 10-15 hashtags
    ig_hashtags = " ".join(hub_tags + ["#reels", "#explorepage", "#smallbusiness", "#freetools", f"#{kw.replace(' ', '').replace('-', '')}"])
    ig_caption = f"{hook}\n\n{tool['title']} — {tool.get('desc', '')[:100]}\n\nFree. No signup. 100% private.\n\n{engage}\n\nLink in bio: {short_url}\n\n{ig_hashtags}"

    # Non-English override (keep local hashtag style)
    kw_tag = kw.replace(" ", "").replace("-", "")
    if lang != "en":
        tt_caption = f"{hook}\n\n{local_cta['privacy']}\n\n🔗 {short_url}\n\n#freetools #{kw_tag} #{hub} #fyp"
        ig_caption = f"{hook}\n\n{tool['title']} — {tool.get('desc', '')[:100]}\n\n{local_cta['privacy']}\n\nLink in bio: {short_url}\n\n#freetools #{kw_tag} #{hub}tools #reels"

    plan = {
        "id": tool.get("href", "").strip("/").replace("/", "_") or tool["title"].lower().replace(" ", "-"),
        "type": tool.get("type", "tool"),
        "language": lang,

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
                "ctaText": local_cta["ctaText"],
                "ctaBadge": local_cta["ctaBadge"],
                "brandName": url.split("/")[0] if "/" in url else url,
            },
        },

        # YouTube upload metadata (in tool's language)
        "youtube": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "privacy": "public",
            "madeForKids": False,
            "defaultLanguage": lang if lang != "en" else "",
            "hashtags": [f"#freetools", f"#{kw_tag}", "#shorts"],
        },

        # TikTok caption (in tool's language)
        "tiktok": {
            "caption": tt_caption,
        },

        # Instagram caption (in tool's language)
        "instagram": {
            "caption": ig_caption,
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
# TUTORIAL PLAN GENERATOR
# ═════════════════════════════════════════════════════════════════════════════

TUTORIAL_STEP_TEMPLATES = {
    "calculator": [
        {"label": "Open the tool", "description": "Visit {title} in your browser — completely free, no signup"},
        {"label": "Enter your values", "description": "Type in the numbers you want to calculate"},
        {"label": "Adjust the settings", "description": "Choose the options that fit your situation"},
        {"label": "Get your results", "description": "Click calculate — instant results with full breakdown"},
        {"label": "Save or share", "description": "Copy your results or share with a link"},
    ],
    "generator": [
        {"label": "Open the tool", "description": "Visit {title} in your browser — no download needed"},
        {"label": "Choose your style", "description": "Pick a template, format, or style that works for you"},
        {"label": "Add your content", "description": "Enter your text, images, or data"},
        {"label": "Generate your result", "description": "Click generate — your {output} is ready in seconds"},
        {"label": "Download or copy", "description": "Save as an image, PDF, or copy to clipboard"},
    ],
    "checker": [
        {"label": "Open the tool", "description": "Visit {title} in your browser — 100% private"},
        {"label": "Paste your content", "description": "Enter the text, URL, or file you want to check"},
        {"label": "Run the analysis", "description": "The tool scans everything automatically"},
        {"label": "Review the results", "description": "See scores, issues, and what needs fixing"},
        {"label": "Apply the fixes", "description": "Follow the suggestions to improve your {subject}"},
    ],
    "converter": [
        {"label": "Open the tool", "description": "Visit {title} — works right in your browser"},
        {"label": "Upload your file", "description": "Drag and drop or select the file to convert"},
        {"label": "Choose output format", "description": "Select the format you need"},
        {"label": "Convert instantly", "description": "Your file is processed locally — nothing uploaded to any server"},
        {"label": "Download the result", "description": "Save the converted file to your device"},
    ],
    "generic": [
        {"label": "Open the tool", "description": "Visit {title} in your browser — free, no signup"},
        {"label": "Enter your information", "description": "Fill in the form with your details"},
        {"label": "Process your request", "description": "Click the main button — results appear instantly"},
        {"label": "Use your results", "description": "Copy, download, or share what you created"},
    ],
}


def detect_tool_type(tool):
    """Detect tool type from title/description for tutorial step selection"""
    text = f"{tool.get('title', '')} {tool.get('desc', '')}".lower()
    if any(w in text for w in ["calculat", "compute", "estimate"]):
        return "calculator"
    if any(w in text for w in ["generat", "creat", "make", "build"]):
        return "generator"
    if any(w in text for w in ["check", "analyz", "detect", "test", "audit", "scan", "valid"]):
        return "checker"
    if any(w in text for w in ["convert", "compress", "resize", "transform"]):
        return "converter"
    return "generic"


def generate_tutorial_plan(tool, keyword=None):
    """Generate a tutorial video plan with steps, problem, and SEO title"""
    hub = tool.get("hub", "tools")
    kw = clean_keyword(keyword or tool["title"].lower())
    tool_type = detect_tool_type(tool)
    lang = get_language(hub)

    # Get step template
    steps_template = TUTORIAL_STEP_TEMPLATES.get(tool_type, TUTORIAL_STEP_TEMPLATES["generic"])
    steps = []
    for st in steps_template:
        label = st["label"].format(title=tool["title"])
        desc = st["description"].format(
            title=tool["title"],
            output=kw.split()[-1] if kw else "result",
            subject=kw or "content",
        )
        steps.append({"label": label, "description": desc, "screenshot": ""})

    # Tutorial-specific YouTube title (search-optimized, "How to" format)
    title_options = [
        f"How to {tool['title']} for Free — Step by Step",
        f"Free {tool['title']} — No Signup Tutorial",
        f"{tool['title']} Tutorial — Free Online Tool ({datetime.now().year})",
        f"How to {kw.title()} Online for Free",
        f"Best Free {tool['title']} — Full Tutorial",
    ]
    yt_title = random.choice(title_options)[:60]

    # Problem text
    problems = [
        f"Most {hub} tools charge $10-30/month for basic features",
        f"You shouldn't need to pay for a simple {kw}",
        f"Paid {kw} tools want your email, credit card, and data",
        f"Why is something this simple locked behind a paywall?",
    ]
    problem = random.choice(problems)

    # Hook
    hooks = [
        f"How to {kw} for free — step by step",
        f"Free {tool['title']} — no signup, no download",
        f"The easiest way to {kw} online",
        f"Stop paying for {kw} tools",
    ]
    hook = random.choice(hooks)

    href = tool.get("href") or ""
    if href.startswith(("http://", "https://")):
        url = href.replace("https://", "").replace("http://", "").rstrip("/")
    elif href:
        url = f"{BRAND_NAME}{href}"
    else:
        url = BRAND_NAME
    theme_index = random.randint(0, 7)
    audio_files = [f"audio/beat{i}.mp3" for i in range(1, 11)]
    audio = random.choice(audio_files)

    # Duration: ~30s per step + 60s for intro/problem/result/CTA
    step_seconds = len(steps) * 30 + 60
    # Add jitter
    jitter = random.randint(-5, 5)
    duration_frames = (step_seconds + jitter) * 30

    # YouTube description with timestamps
    timestamps = []
    sec_offset = 0
    timestamps.append("0:00 Intro")
    sec_offset += 15
    timestamps.append(f"0:{sec_offset:02d} The Problem")
    sec_offset += 15
    for i, step in enumerate(steps):
        m = sec_offset // 60
        s = sec_offset % 60
        timestamps.append(f"{m}:{s:02d} Step {i+1}: {step['label']}")
        sec_offset += 30
    m = sec_offset // 60
    s = sec_offset % 60
    timestamps.append(f"{m}:{s:02d} Results")

    yt_desc = (
        f"{hook}\n\n"
        f"Try {tool['title']} FREE: https://{url}\n\n"
        f"In this tutorial, I'll show you how to {kw} completely free, "
        f"right in your browser. No signup, no download, 100% private.\n\n"
        f"Timestamps:\n" + "\n".join(timestamps) + "\n\n"
        f"No signup. No download. 100% private — your data never leaves your browser.\n\n"
        f"#freetools #tutorial #howto #{kw.replace(' ', '')} #{hub}"
    )

    tags = [kw, tool["title"].lower(), f"free {kw}", f"how to {kw}", f"{kw} tutorial",
            f"free {kw} online", hub, "free tools", "no signup", "browser tools", "tutorial"]

    category_id = CATEGORIES.get(hub, 28)

    plan = {
        "id": tool.get("href", "").strip("/").replace("/", "_") or tool["title"].lower().replace(" ", "-"),
        "type": "tutorial",
        "format": "tutorial",
        "language": lang,
        "hub": hub,
        "slug": tool.get("href", "").strip("/").split("/")[-1] if tool.get("href") else tool["title"].lower().replace(" ", "-"),
        "toolPath": tool.get("href", ""),
        "title": tool["title"],

        "render": {
            "template": "Tutorial",
            "props": {
                "hook": hook,
                "title": tool["title"],
                "problem": problem,
                "steps": steps,
                "resultText": f"{tool['title']} — completely free, no signup required",
                "url": url,
                "audioFile": audio,
                "themeIndex": theme_index,
                "ctaText": "Try it free",
                "ctaBadge": "LINK IN DESCRIPTION",
                "brandName": BRAND_NAME,
                "durationInFrames": duration_frames,
            },
        },

        "youtube": {
            "title": yt_title,
            "description": yt_desc,
            "tags": tags,
            "categoryId": category_id,
            "privacy": "public",
            "madeForKids": False,
            "defaultLanguage": lang if lang != "en" else "",
        },

        "tiktok": {"caption": ""},
        "instagram": {"caption": ""},

        "keyword": kw,
        "steps": steps,
        "hookStyle": "tutorial",
        "template": "Tutorial",
        "generatedAt": datetime.now().isoformat(),
    }

    return plan


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
    parser.add_argument("--format", type=str, default="short", choices=["short", "tutorial"], help="Video format: short (15-25s) or tutorial (3-7min)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Content Intelligence Engine — Teamz Lab")
    print("=" * 60)

    # Load tools from all sources (search-index.js + app landing pages)
    tools = load_tools_from_sources()
    app_tool_count = sum(1 for t in tools if t.get("type") == "app")
    catalog_tool_count = len(tools) - app_tool_count
    print(f"\nLoaded {len(tools)} tools total — {catalog_tool_count} from search-index, {app_tool_count} from app landings")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Site URL:     {SITE_URL}")

    # Collect keyword ideas from all free sources
    all_keywords = []

    # 1. Google Trends (if --trending) — only use tech-relevant trends
    if args.trending:
        print("\nPulling Google Trends...")
        trends = google_trends_daily()
        print(f"  Daily trends: {len(trends)}")
        # Broad filter — covers ALL product categories (tools, apps, health, finance, career, design, etc.)
        relevant_keywords = [
            # Tech
            "ai", "app", "tool", "software", "code", "design", "tech", "api", "web", "data",
            "cloud", "security", "crypto", "generator", "converter", "calculator", "browser",
            # Finance
            "finance", "tax", "salary", "budget", "invest", "loan", "mortgage", "interest", "saving",
            "income", "payment", "invoice", "price", "cost", "money", "bank", "insurance",
            # Health
            "health", "fitness", "diet", "calorie", "bmi", "weight", "sleep", "water", "nutrition",
            "exercise", "workout", "medical", "mental", "wellness",
            # Career
            "resume", "job", "career", "interview", "hiring", "salary", "remote", "freelance",
            "linkedin", "cover letter", "work",
            # Design
            "color", "font", "image", "photo", "logo", "icon", "ui", "ux", "css", "gradient",
            "mockup", "template", "canvas", "figma",
            # Legal
            "legal", "contract", "privacy", "gdpr", "compliance", "document",
            # Education
            "learn", "study", "student", "course", "education", "tutorial", "exam",
            # Productivity
            "productivity", "timer", "planner", "schedule", "todo", "note", "organize",
            # General utility
            "qr", "pdf", "text", "email", "password", "download", "upload", "scan",
        ]
        relevant_trends = [t for t in trends if any(kw in t.lower() for kw in relevant_keywords)]
        print(f"  Relevant trends: {len(relevant_trends)} (from {len(trends)} total)")
        for t in relevant_trends[:5]:
            print(f"    - {t}")
        for trend in relevant_trends:
            related = youtube_autocomplete(f"{trend} free tool")[:2]
            all_keywords.extend(related)

    # 2. Niche research
    if args.niche:
        keywords = research_keywords_for_niche(args.niche, tools)
        all_keywords.extend(keywords)
    else:
        # Auto-research across ALL product categories
        top_niches = [
            # High-RPM
            "salary calculator", "tax calculator", "loan calculator", "resume builder",
            "cover letter generator", "ats resume checker",
            # AI tools
            "ai text generator", "ai image generator", "grammar checker", "ai summarizer",
            # Utility
            "pdf compressor", "image converter", "qr code generator", "password generator",
            "json formatter", "color picker",
            # Health
            "bmi calculator", "calorie calculator", "sleep calculator",
            # Design
            "font generator", "logo maker", "color palette generator",
            # Productivity
            "pomodoro timer", "invoice generator", "text counter",
        ]
        print("\nAuto-researching niches...")
        for niche in random.sample(top_niches, min(5, len(top_niches))):
            keywords = research_keywords_for_niche(niche, tools)
            all_keywords.extend(keywords)

    # 3. Search Console keywords (if available)
    sc_keywords = load_search_console_keywords()
    if sc_keywords:
        print(f"\nSearch Console keywords: {len(sc_keywords)}")
        all_keywords.extend(sc_keywords[:20])

    # 4. Keyword Intel opportunities (build-keyword-intel.py output)
    intel_file = SCRIPT_DIR.parent.parent / "data" / "keyword-intel-latest.json"
    if intel_file.exists():
        try:
            intel = json.loads(intel_file.read_text(errors="replace"))
            opportunities = [kw.get("query", "") for kw in intel.get("opportunities", [])[:20]]
            if opportunities:
                print(f"\nKeyword Intel opportunities: {len(opportunities)}")
                all_keywords.extend(opportunities)
        except Exception:
            pass

    # 5. Rank tracker movers (keywords gaining position)
    rank_file = SCRIPT_DIR.parent.parent / "data" / "rank-history.json"
    if rank_file.exists():
        try:
            ranks = json.loads(rank_file.read_text(errors="replace"))
            # Get keywords that improved recently (make videos for winners)
            improving = []
            for kw, history in ranks.items():
                if isinstance(history, list) and len(history) >= 2:
                    latest = history[-1] if isinstance(history[-1], (int, float)) else 0
                    prev = history[-2] if isinstance(history[-2], (int, float)) else 0
                    if 0 < latest < prev:  # Position improved (lower = better)
                        improving.append(kw)
            if improving:
                print(f"\nRank tracker — improving keywords: {len(improving)}")
                all_keywords.extend(improving[:15])
        except Exception:
            pass

    # 6. Content ideas (build-content-ideas.py output)
    ideas_file = SCRIPT_DIR.parent.parent / "data" / "content-ideas-latest.json"
    if ideas_file.exists():
        try:
            ideas_data = json.loads(ideas_file.read_text(errors="replace"))
            for idea in ideas_data.get("ideas", [])[:15]:
                if idea.get("keyword"):
                    all_keywords.append(idea["keyword"])
            if ideas_data.get("ideas"):
                print(f"\nContent ideas engine: {min(15, len(ideas_data['ideas']))}")
        except Exception:
            pass

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

    # Select plan generator based on format
    plan_generator = generate_tutorial_plan if args.format == "tutorial" else generate_video_plan

    # Match keywords to tools
    for kw in unique_keywords:
        if len(plans) >= args.count:
            break
        tool = match_keyword_to_tool(kw, tools)
        if tool and tool["href"] not in used_tools:
            used_tools.add(tool["href"])
            plan = plan_generator(tool, keyword=kw)
            plans.append(plan)

    # If not enough, pick top tools by category
    if len(plans) < args.count:
        high_rpm_hubs = ["finance", "career", "ai", "health", "tax", "legal"]
        remaining = [t for t in tools if t["hub"] in high_rpm_hubs and t["href"] not in used_tools]
        random.shuffle(remaining)
        for tool in remaining:
            if len(plans) >= args.count:
                break
            plan = plan_generator(tool)
            plans.append(plan)
            used_tools.add(tool["href"])

    # App-specific plans
    # Mode A (explicit): --app "AppName" → ASO-style plans for that one app.
    # Mode B (auto): no --app flag → iterate every app landing page found and
    #                generate plans seeded from primaryKeyword + secondaryKeywords
    #                in their frontmatter. Works for any host repo with apps.
    app_tools = [t for t in tools if t.get("type") == "app"]

    if args.app:
        print(f"\nASO mode for app: {args.app}")
        aso_keywords = youtube_autocomplete(args.app)
        aso_keywords.extend(google_autocomplete(f"{args.app} app"))
        print(f"  ASO keywords: {len(aso_keywords)}")
        match = next((t for t in app_tools if t["title"].lower() == args.app.lower()), None)
        base_tool = match or {
            "title": args.app,
            "desc": f"Download {args.app} on App Store & Play Store",
            "href": "",
            "hub": "app",
            "type": "app",
        }
        for kw in aso_keywords[:5]:
            app_plan = generate_video_plan(base_tool, keyword=kw)
            app_plan["render"]["props"]["ctaBadge"] = CTA_BADGE
            app_plan["render"]["props"]["brandName"] = BRAND_NAME
            if base_tool.get("landing_url"):
                app_plan.setdefault("backlinks", {})["landing"] = base_tool["landing_url"]
            if base_tool.get("play_store_url"):
                app_plan.setdefault("backlinks", {})["play_store"] = base_tool["play_store_url"]
            if base_tool.get("app_store_url"):
                app_plan.setdefault("backlinks", {})["app_store"] = base_tool["app_store_url"]
            plans.append(app_plan)
    elif app_tools:
        print(f"\nApp landings mode: found {len(app_tools)} app landing page(s)")
        # Per app, generate 1-3 ASO plans using its primary + first two secondary keywords.
        for t in app_tools:
            seeds = []
            if t.get("primary_keyword"):
                seeds.append(t["primary_keyword"])
            for k in (t.get("secondary_keywords") or [])[:2]:
                if k and k not in seeds:
                    seeds.append(k)
            if not seeds:
                seeds = [t["title"]]
            for kw in seeds:
                app_plan = generate_video_plan(t, keyword=kw)
                app_plan["render"]["props"]["ctaBadge"] = CTA_BADGE
                app_plan["render"]["props"]["brandName"] = BRAND_NAME
                if t.get("landing_url"):
                    app_plan.setdefault("backlinks", {})["landing"] = t["landing_url"]
                if t.get("play_store_url"):
                    app_plan.setdefault("backlinks", {})["play_store"] = t["play_store_url"]
                if t.get("app_store_url"):
                    app_plan.setdefault("backlinks", {})["app_store"] = t["app_store_url"]
                plans.append(app_plan)
                if len(plans) >= args.count:
                    break
            if len(plans) >= args.count:
                break

    print(f"\n{'=' * 60}")
    print(f"Generated {len(plans)} video plans")
    print(f"{'=' * 60}\n")

    # Display plans
    for i, plan in enumerate(plans, 1):
        yt = plan["youtube"]
        r = plan["render"]
        fmt = plan.get("format", "short")
        dur_sec = r["props"].get("durationInFrames", 720) / 30
        print(f"#{i} [{r['template']}] Theme {r['props']['themeIndex']} | {fmt} | {dur_sec:.0f}s")
        print(f"  YT Title: {yt['title']}")
        print(f"  Hook: {r['props']['hook']}")
        print(f"  Keyword: {plan['keyword']}")
        if fmt == "tutorial" and plan.get("steps"):
            print(f"  Steps: {len(plan['steps'])} ({', '.join(s['label'] for s in plan['steps'][:3])}...)")
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
        if args.format == "tutorial":
            print(f"\nNext steps:")
            print(f"  1. node capture-tool.js --from-plans          # Take screenshots")
            print(f"  2. node render-batch.js --from-plans           # Render tutorials")
            print(f"  3. node upload/youtube-upload.js --from-history # Upload to YouTube")
        else:
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
