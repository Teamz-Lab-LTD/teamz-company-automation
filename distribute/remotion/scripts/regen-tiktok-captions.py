#!/usr/bin/env python3
"""
Regenerate .tiktok.txt files for all reels in reel-history.json using the
viral caption template defined in content-engine.py. No re-render — only
the caption text files are rewritten.

Usage: python3 scripts/regen-tiktok-captions.py
"""
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
HISTORY = HERE / "reel-history.json"

HUB_HASHTAGS = {
    "longevity":  ["#biohacking", "#longevity", "#healthtok", "#peterattia"],
    "health":     ["#healthtok", "#wellness", "#healthhacks", "#biohacking"],
    "finance":    ["#moneytok", "#personalfinance", "#financehack", "#taxtips"],
    "tax":        ["#taxtips", "#moneytok", "#taxes", "#irs"],
    "career":     ["#careeradvice", "#resumetips", "#jobtok", "#careertok"],
    "resume":     ["#resumetips", "#careeradvice", "#jobsearch", "#jobtok"],
    "ai":         ["#aitools", "#chatgpt", "#techtok", "#aitok"],
    "dev":        ["#codetok", "#webdev", "#programmer", "#techtok"],
    "devicegpt":  ["#androidtips", "#phonetips", "#techtok", "#smartphone"],
    "pdf":        ["#productivity", "#officehacks", "#lifehack", "#techtok"],
    "image":      ["#designtok", "#graphicdesign", "#contentcreator", "#techtok"],
    "video":      ["#videoediting", "#contentcreator", "#editingtips", "#techtok"],
    "design":     ["#designtok", "#graphicdesign", "#branding", "#canva"],
    "compliance": ["#carehome", "#nursinghome", "#ukcare", "#socialcare"],
    "care":       ["#carehome", "#nursinghome", "#caregiver", "#healthcare"],
    "education":  ["#studytok", "#studytips", "#learning", "#education"],
    "marketing":  ["#marketingtips", "#smallbusiness", "#digitalmarketing", "#entrepreneur"],
    "business":   ["#smallbusiness", "#entrepreneur", "#businesstips", "#startup"],
    "restaurant": ["#foodtok", "#restaurant", "#smallbusiness", "#hospitality"],
    "eu":         ["#sustainability", "#esg", "#greenbusiness", "#climate"],
    "fitness":    ["#fittok", "#workout", "#fitness", "#gymtok"],
    "parenting":  ["#parentingtips", "#momsoftiktok", "#parentok", "#momlife"],
    "travel":     ["#travelhacks", "#traveltips", "#budgettravel", "#traveltok"],
    "productivity": ["#productivity", "#lifehack", "#worklife", "#officehacks"],
    "generator":  ["#aitools", "#contentcreator", "#creativetools", "#techtok"],
    "converter":  ["#productivity", "#techtok", "#officehacks", "#lifehack"],
    "tools":      ["#freetools", "#productivity", "#techtok", "#lifehack"],
}

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
    "education":  "Save this for exam prep 🔖",
    "fitness":    "Save this for leg day 🔖",
    "marketing":  "Save for your next campaign 🔖",
    "business":   "Tag your co-founder 👇",
}

URL_RE = re.compile(r"https?://[^\s]+")


def hub_from_url(url: str) -> str:
    """Extract first path segment after domain as the hub."""
    m = re.search(r"teamzlab\.com/([^/]+)/", url)
    if m:
        return m.group(1).lower()
    m = re.search(r"always-ready-care\.web\.app/?([^/]*)", url)
    if m:
        return "care"
    return "tools"


def extract_url(caption_text: str) -> str | None:
    for line in caption_text.split("\n"):
        urls = URL_RE.findall(line)
        if urls:
            # Prefer teamzlab over always-ready-care
            tz = [u for u in urls if "teamzlab.com" in u]
            return tz[0] if tz else urls[0]
    return None


def build_viral_caption(hook: str, url: str, hub: str, lang: str = "en") -> str:
    hub_tags = HUB_HASHTAGS.get(hub, HUB_HASHTAGS["tools"])
    engage = ENGAGE_PROMPTS.get(hub, "Try it free — link in bio 🔗")
    short_url = url.replace("https://", "").replace("http://", "").rstrip("/") + "/"
    short_url = short_url.rstrip("/")
    hashtags = " ".join(hub_tags[:4] + ["#fyp"])
    return f"{hook}\n\n{engage}\n\n🔗 {short_url}\n\n{hashtags}"


def main():
    data = json.loads(HISTORY.read_text())
    reels = data.get("reels", [])
    updated = 0
    skipped = 0

    for r in reels:
        caption_path = r.get("caption")
        if not caption_path or not os.path.exists(caption_path):
            skipped += 1
            continue

        # Extract URL from the main .txt caption (already written by render-batch)
        main_caption = open(caption_path).read()
        url = extract_url(main_caption)
        if not url:
            print(f"  [skip] {r['slug']} — no URL found in caption")
            skipped += 1
            continue

        hook = r.get("hook") or r.get("title", "")
        hub = (r.get("hub") or "").strip() or hub_from_url(url)
        lang = r.get("language", "en")

        tt_caption = build_viral_caption(hook, url, hub, lang)
        tt_path = caption_path.replace(".txt", ".tiktok.txt")
        open(tt_path, "w").write(tt_caption)
        updated += 1
        print(f"  [ok]   {r['slug'][:50]:50s}  hub={hub}")

    print()
    print(f"Updated: {updated}  Skipped: {skipped}  Total: {len(reels)}")


if __name__ == "__main__":
    main()
