#!/usr/bin/env python3
"""
ASO education and LLM prompt generator.

Teaches App Store Optimization basics and produces contextual prompts/checklists
using iTunes data (lookup, search, reviews, autocomplete). Standard library only.

Output is written to ``<data_dir>/aso-guide-latest.md`` (``TEAMZ_DATA_DIR``).

Examples::

    python3 py/aso/aso-guide.py --learn
    python3 py/aso/aso-guide.py --checklist 123456789
    python3 py/aso/aso-guide.py --content-plan 123456789
    python3 py/aso/aso-guide.py --landing-page 123456789
    python3 py/aso/aso-guide.py --blog-ideas 123456789
    python3 py/aso/aso-guide.py --prompt "write title"
    python3 py/aso/aso-guide.py --prompt "write description" --app 123456789
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _teamz_config import load_runtime  # noqa: E402

from aso._aso_common import (  # noqa: E402
    apple_autocomplete,
    ensure_data_dir,
    itunes_lookup,
    itunes_reviews,
    itunes_search,
    load_seo_context,
    mentions_for_content,
    serp_app_pack_keywords,
    tokenize,
    top_keywords,
    web_gaps_as_aso_opportunities,
    web_keywords_for_seed,
)

_CFG = load_runtime(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py")
)

_APP_TITLE_MAX = 30
_DESC_MIN_WORDS = 120
_REVIEWS_STRONG = 100
_SCREENSHOT_MIN = 3
_SCREENSHOT_STRONG = 5
_UPDATE_DAYS_OK = 120
_CTA_RE = re.compile(
    r"\b(download|install|try|get started|start free|free trial|today|now|join|sign up)\b",
    re.I,
)


def _out_path():
    return ensure_data_dir(_CFG) / "aso-guide-latest.md"


def _write_md(body: str, title: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    md = f"# {title}\n\n_Generated: {ts} (UTC)_\n\n{body.strip()}\n"
    p = _out_path()
    p.write_text(md, encoding="utf-8")
    print(f"Wrote {p}", file=sys.stderr)


def _rating(rec):
    if not rec:
        return None
    v = rec.get("averageUserRatingForCurrentVersion")
    if v is None:
        v = rec.get("averageUserRating")
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _reviews_count(rec):
    if not rec:
        return None
    n = rec.get("userRatingCountForCurrentVersion")
    if n is None:
        n = rec.get("userRatingCount")
    try:
        return int(n)
    except (TypeError, ValueError):
        return None


def _screenshot_count(rec):
    if not rec:
        return 0
    urls = rec.get("screenshotUrls") or []
    return len(urls) if isinstance(urls, list) else 0


def _parse_release_date(rec):
    raw = (rec or {}).get("currentVersionReleaseDate") or (rec or {}).get("releaseDate") or ""
    if not raw:
        return None
    s = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _days_since_release(rec):
    dt = _parse_release_date(rec)
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return (now - dt).days


def _desc_words(rec):
    d = (rec.get("description") or "").strip()
    return len(d.split()) if d else 0


def _keyword_overlap_title(rec):
    """How many of the top description keywords appear in the title."""
    title = (rec.get("trackName") or "").lower()
    desc = (rec.get("description") or "")
    top = [w for w, _ in top_keywords(desc, n=12)]
    if not top:
        return 0, []
    hits = [w for w in top if w in title]
    return len(hits), hits


def _max_keyword_density(rec):
    """Share of non-stopword tokens taken by the most frequent meaningful token."""
    desc = (rec.get("description") or "").strip()
    if not desc:
        return 0.0, ""
    c = tokenize(desc)
    total = sum(c.values())
    if not total:
        return 0.0, ""
    w, n = c.most_common(1)[0]
    return 100.0 * n / total, w


def _fetch_app_or_exit(app_id):
    rec = itunes_lookup(app_id)
    if not rec:
        print(f"Lookup failed for app id: {app_id}", file=sys.stderr)
        sys.exit(1)
    return rec


def _competitors(rec, limit=5):
    """Top search results excluding the app itself."""
    genre = (rec.get("primaryGenreName") or "").strip()
    name = (rec.get("trackName") or "").strip()
    seed_text = f"{genre} {name}"
    seeds = [w for w, _ in top_keywords(seed_text, n=4)]
    query = " ".join(seeds[:2]) if seeds else (genre or name or "app")
    results = itunes_search(query, limit=30)
    my_id = rec.get("trackId")
    out = []
    for r in results:
        if r.get("trackId") == my_id:
            continue
        out.append(r)
        if len(out) >= limit:
            break
    return out, query


def _review_text_blob(app_rec):
    tid = app_rec.get("trackId")
    if not tid:
        return ""
    revs = itunes_reviews(int(tid), page=1)
    parts = []
    for r in revs:
        parts.append((r.get("title") or "") + " " + (r.get("content") or ""))
    return " ".join(parts)


def crash_course_text() -> str:
    return """
## What is ASO?

**App Store Optimization (ASO)** is the practice of improving an app’s visibility and conversion rate inside mobile marketplaces—primarily the Apple App Store and Google Play. It combines **discoverability** (ranking for relevant searches and categories) with **conversion rate optimization** (turning impressions into installs). Unlike paid user acquisition, ASO focuses on **organic** growth: search results, browse placements, similar-app recommendations, and listing quality. Think of it as **SEO for app stores**, but with stricter character limits, heavier emphasis on creative assets, and star ratings visible on every impression.

## Why ASO matters

Most installs still start with **search and browse**. A strong listing captures high-intent users at the moment they look for a solution. Poor metadata wastes ad spend too: users who arrive from ads still read the title, screenshots, and reviews before installing. ASO compounds over time—better ratings, fresher creative, and clearer keywords reinforce each other. For indie teams, ASO is often the **highest-ROI** lever because it improves every channel that points at the store page. Even a small lift in **impression-to-install rate** multiplies across all traffic sources.

## Five ranking and conversion signals (simplified)

1. **Title & subtitle (iOS) / title & short description (Android)** — The strongest indexed fields for relevance. Put your **brand plus 1–2 core keywords** naturally; avoid stuffing or misleading terms. On iOS, the subtitle appears under the name and should reinforce the **primary use case** without repeating the title verbatim.
2. **Keyword field (iOS only, hidden)** — 100 characters that influence search matching. No duplicates of the title; use comma-separated terms and research-backed phrases. On Google Play, the **long description** matters more for indexing, so weave terms into readable paragraphs instead of comma lists.
3. **Ratings & reviews** — Average rating and volume affect **ranking and conversion**. Below ~4.0 stars, install rates typically drop sharply; volume signals legitimacy. Stores also surface **recent review sentiment** to users—patterns of bugs or support issues hurt even if the average stays high.
4. **Downloads & velocity** — Stores infer popularity from **install volume and momentum**. Spikes from campaigns can help, but sustained organic demand matters more long term. Sudden uninstall spikes or crash reports can counteract raw download numbers.
5. **Engagement & quality** — Retention, crashes, and uninstall patterns feed **quality signals**. A polished onboarding and stable builds support both store algorithms and user trust. This is where product quality and ASO meet: **promises in the listing must match the first-session experience**.

## Optimization workflow

1. **Research** — Mine autocomplete, competitor titles, reviews, and your analytics for **language users actually use**. Build a **keyword map**: primary term, synonyms, problem-based phrases (“how to…”, “best… for…”), and competitor brand terms you are allowed to target.
2. **Optimize** — Iterate title, keywords, description (first lines matter most), screenshots, preview video, and icon for **clarity and proof**. Lead screenshots with **benefits**, not splash screens or login walls.
3. **Monitor** — Track keyword ranks, conversion rate (impression → install), ratings, and competitor moves. Watch **seasonality** (back-to-school, holidays) and platform OS releases that shift search behavior.
4. **Iterate** — Localize, A/B test creative where available, and ship **regular updates** with meaningful release notes. Each cycle should change one major hypothesis (e.g., new title, new first screenshot) so you know what moved the needle.

## iOS vs Android (key differences)

| Area | Apple App Store | Google Play |
|------|-----------------|-------------|
| Keywords | Dedicated **100-char keyword field** | No separate field; indexing from **title, short description, long description** |
| Creative | Strict screenshot sizes; **App Preview** video | Flexible; **feature graphic** + video optional |
| Reviews | Often stricter moderation; **prompt for ratings** via system API | Similar rating prompts; metadata policies differ slightly |
| Algorithms | Less public detail; strong weight on **relevance + quality** | Also opaque; **description text** carries more keyword weight |

Treat the two stores as **siblings, not twins**: reuse messaging, but **tailor keywords and first-screen copy** to each platform’s rules. If you only optimize one store, you leave **half the addressable market** under-served.

## Common mistakes

- **Keyword stuffing** in titles or descriptions (hurts conversion; may violate guidelines).
- **Ignoring the first 2–3 screenshot frames** — most users never scroll the gallery.
- **Stale listings** — old “What’s New” text or outdated screenshots erode trust.
- **Chasing irrelevant high-volume terms** that do not match the app’s core value.
- **Neglecting reviews** — unanswered complaints signal neglect; thoughtful replies improve perception.
- **Translating English metadata word-for-word** without local keyword research for each locale.
- **Overpromising in screenshots** that the app cannot deliver in the first minute of use.

Use the checklists and prompts in this toolkit to turn these ideas into **repeatable, data-informed** actions for your app.
""".strip()


def cmd_learn():
    body = crash_course_text()
    _write_md(body, "ASO crash course")
    print(body)


def cmd_checklist(app_id: str):
    rec = _fetch_app_or_exit(app_id)
    title = rec.get("trackName") or ""
    title_len = len(title)
    title_ok = title_len <= _APP_TITLE_MAX
    overlap_n, overlap_words = _keyword_overlap_title(rec)
    kw_in_title_ok = overlap_n >= 1 or len(top_keywords(rec.get("description") or "", n=5)) == 0

    desc_wc = _desc_words(rec)
    desc_len_ok = desc_wc >= _DESC_MIN_WORDS
    dens, dens_word = _max_keyword_density(rec)
    density_ok = dens <= 4.0  # avoid spammy repetition
    desc = rec.get("description") or ""
    cta_ok = bool(_CTA_RE.search(desc))

    rating = _rating(rec)
    rating_ok = rating is not None and rating >= 4.0

    rev_n = _reviews_count(rec)
    reviews_ok = rev_n is not None and rev_n >= _REVIEWS_STRONG

    shots = _screenshot_count(rec)
    screenshots_ok = shots >= _SCREENSHOT_MIN
    screenshots_strong = shots >= _SCREENSHOT_STRONG

    days = _days_since_release(rec)
    update_ok = days is not None and days <= _UPDATE_DAYS_OK

    lines = [
        f"**App:** {title} (id `{rec.get('trackId')}`)",
        f"**Bundle:** `{rec.get('bundleId')}`",
        "",
        "## Checklist (pass / fail)",
        "",
    ]

    def item(n, name, passed, detail):
        pf = "PASS" if passed else "FAIL"
        lines.append(f"{n}. **{name}** — [{pf}] {detail}")

    item(
        1,
        "Title length",
        title_ok,
        f"{title_len} chars (target ≤ {_APP_TITLE_MAX}).",
    )
    item(
        2,
        "Title keyword coverage",
        kw_in_title_ok,
        f"{overlap_n} top description keywords appear in title"
        + (f" ({', '.join(overlap_words[:5])})" if overlap_words else "")
        + ".",
    )
    item(
        3,
        "Description depth",
        desc_len_ok,
        f"~{desc_wc} words (target ≥ {_DESC_MIN_WORDS}).",
    )
    item(
        4,
        "Description keyword density",
        density_ok,
        f"Highest token share {dens:.1f}% for “{dens_word}” (keep primary terms under ~4%).",
    )
    item(
        5,
        "Call-to-action in description",
        cta_ok,
        "Includes install/try/start-style language."
        if cta_ok
        else "Add a clear CTA (e.g. Download, Try free, Get started).",
    )
    item(
        6,
        "Rating health",
        rating_ok,
        f"Average {rating:.2f}★" if rating is not None else "No rating data.",
    )
    item(
        7,
        "Review volume (social proof)",
        reviews_ok,
        (f"{rev_n} ratings/reviews" if rev_n is not None else "Unknown count.")
        + f" (target ≥ {_REVIEWS_STRONG} for stronger proof).",
    )
    item(
        8,
        "Screenshot coverage",
        screenshots_ok,
        f"{shots} screenshots"
        + (
            f" (strong: ≥ {_SCREENSHOT_STRONG})"
            if screenshots_strong
            else f" (aim for ≥ {_SCREENSHOT_MIN})."
        ),
    )
    item(
        9,
        "Update recency",
        update_ok,
        (f"Last release ~{days} days ago." if days is not None else "Release date unknown.")
        + (f" Target refresh within {_UPDATE_DAYS_OK} days." if days is not None else ""),
    )
    lines.append("")
    lines.append(
        "10. **Keyword field (iOS)** — [INFO] Public APIs do not expose your 100-character keyword list; verify in App Store Connect for duplicates and relevance."
    )

    # 11 — Localization (languageCodesISO2A)
    langs = rec.get("languageCodesISO2A") or []
    if not isinstance(langs, list):
        langs = [langs] if langs else []
    n_locales = len(langs)
    if n_locales == 0:
        lines.append(
            "11. **Localization** — [FAIL] languageCodesISO2A missing or empty in lookup — verify locales in App Store Connect. "
            "Use --localize in aso-keywords.py to find keywords in other markets."
        )
    elif n_locales == 1:
        lines.append(
            "11. **Localization** — [FAIL] Only 1 locale — you're missing ~70% of global revenue. "
            "Use --localize in aso-keywords.py to find keywords in other markets."
        )
    elif n_locales >= 3:
        lines.append(f"11. **Localization** — [PASS] Supports {n_locales} locales.")
    else:
        lines.append(
            "11. **Localization** — [!] Only 2 locales — consider adding more markets; "
            "use --localize in aso-keywords.py to find keywords in other markets."
        )

    # 12 — Release notes freshness
    rn = (rec.get("releaseNotes") or "").strip()
    if not rn:
        lines.append(
            "12. **Release notes freshness** — [FAIL] No release notes — App Store editorial and users both check these."
        )
    else:
        rn_wc = len(rn.split())
        lines.append(f"12. **Release notes freshness** — [PASS] Release notes present ({rn_wc} words).")

    lines.append(
        "13. **Video preview** — [INFO] Video preview availability cannot be detected via API — verify manually in App Store Connect."
    )

    # 14 — App size (fileSizeBytes)
    fs_b = rec.get("fileSizeBytes")
    try:
        fs_int = int(fs_b) if fs_b is not None else None
    except (TypeError, ValueError):
        fs_int = None
    if fs_int is not None and fs_int > 0:
        size_mb = fs_int / (1024 * 1024)
        if size_mb > 200:
            lines.append(
                f"14. **App size** — [!] App is {size_mb:.1f}MB — large downloads reduce conversion on cellular. Target <150MB."
            )
        else:
            lines.append(f"14. **App size** — [PASS] App size {size_mb:.1f}MB")
    else:
        lines.append(
            "14. **App size** — [INFO] fileSizeBytes not available in lookup — verify download size in App Store Connect."
        )

    lines.append(
        "15. **Conversion optimization** — [INFO] Impression-to-install rate is only available in "
        "App Store Connect > Analytics > Metrics. Check weekly and target >30% for search traffic."
    )

    lines.append("")
    lines.append("### TODO next")
    lines.append("")
    lines.append("Work through any **FAIL** items first, then tighten copy and creative using the `--prompt` and `--landing-page` commands in this script.")

    body = "\n".join(lines)
    _write_md(body, f"ASO checklist — {title[:50]}")
    print(body)


def _blog_title_ideas(seed_keywords, genre, n=10):
    g = genre or "your niche"
    k1 = seed_keywords[0] if seed_keywords else "app"
    k2 = seed_keywords[1] if len(seed_keywords) > 1 else "mobile"
    templates = [
        f"Best {k1} apps in 2026: what to look for before you install",
        f"How to pick a {g.lower()} app without wasting storage",
        f"{k1.title()} vs {k2}: which fits your daily workflow?",
        f"ASO breakdown: why {k1} apps win (or lose) in search",
        f"User guide: getting started with {k1} on iPhone and Android",
        f"Privacy checklist for {g.lower()} apps in 2026",
        f"Common mistakes people make when choosing a {k1} tool",
        f"From download to power user: a week with a top {k1} app",
        f"How ratings and reviews shape {g.lower()} app rankings",
        f"Landing page ideas that convert browsers into {k1} installs",
    ]
    return templates[:n]


def cmd_content_plan(app_id: str):
    rec = _fetch_app_or_exit(app_id)
    title = rec.get("trackName") or ""
    desc = rec.get("description") or ""
    genre = rec.get("primaryGenreName") or ""
    combined = f"{title}\n{desc}"
    kws = top_keywords(combined, n=15)
    seed_terms = [w for w, _ in kws[:3]]
    auto = []
    for s in seed_terms[:2]:
        auto.extend(apple_autocomplete(s)[:6])
    auto = list(dict.fromkeys(auto))[:12]

    blog = _blog_title_ideas([w for w, _ in kws], genre, n=10)
    sections = [
        "Hero: outcome + primary keyword + single CTA",
        "Social proof: rating summary + short testimonial strip",
        "Feature grid: 3–5 benefits mapped to screenshots",
        "How it works: 3 steps with plain language",
        "FAQ: objections (pricing, privacy, offline, support)",
    ]

    lines = [
        f"## Content plan for **{title}**",
        "",
        "### Top keywords (title + description)",
        "",
        ", ".join(f"`{w}` ({c})" for w, c in kws[:12]) or "—",
        "",
        "### Autocomplete hints (Apple)",
        "",
        ", ".join(f"`{a}`" for a in auto) or "—",
        "",
        "### Ten blog topic titles",
        "",
    ]
    for i, b in enumerate(blog, 1):
        lines.append(f"{i}. {b}")
    lines.extend(["", "### Suggested landing page sections", ""])
    for i, s in enumerate(sections, 1):
        lines.append(f"{i}. {s}")

    seo = load_seo_context(_CFG["data_dir"])
    web_seeds = web_keywords_for_seed(seo)
    web_gaps = web_gaps_as_aso_opportunities(seo)
    app_pack = serp_app_pack_keywords(seo)
    unlinked = mentions_for_content(seo)
    if web_seeds or web_gaps or app_pack or unlinked:
        lines.extend(["", "### SEO cross-insights (from web data)", ""])
        if web_seeds:
            lines.append(f"**Web keywords usable as ASO seeds:** {', '.join(f'`{k}`' for k in web_seeds[:10])}")
        if web_gaps:
            lines.append(f"**Competitor web gaps (potential ASO targets):** {', '.join(f'`{g}`' for g in web_gaps[:10])}")
        if app_pack:
            lines.append(f"**SERP keywords with app/video results:** {', '.join(f'`{k}`' for k in app_pack[:10])}")
        if unlinked:
            lines.append(f"**Unlinked brand mentions (outreach):** {len(unlinked)} recent mentions")

    comps, _q = _competitors(rec, limit=5)
    if comps:
        lines.extend(["", "### Competitor cadence", ""])
        update_gaps = []
        now = datetime.now(timezone.utc)
        for c in comps:
            c_name = (c.get("trackName") or "Unknown")[:40]
            raw = c.get("currentVersionReleaseDate") or c.get("releaseDate") or ""
            if not raw:
                lines.append(f"- **{c_name}** — release date unknown")
                continue
            dt = _parse_release_date(c)
            if dt is None:
                lines.append(f"- **{c_name}** — release date unparseable")
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            days_ago = (now - dt).days
            update_gaps.append(days_ago)
            lines.append(f"- **{c_name}** — last updated ~{days_ago} days ago")
        if update_gaps:
            avg_gap = sum(update_gaps) // len(update_gaps)
            lines.append(
                f"\nTop {len(update_gaps)} competitors update every ~{avg_gap} days. "
                "Match or exceed this cadence."
            )

    body = "\n".join(lines)
    _write_md(body, f"ASO content plan — {title[:40]}")
    print(body)


def cmd_landing_page(app_id: str):
    rec = _fetch_app_or_exit(app_id)
    title = rec.get("trackName") or ""
    desc = rec.get("description") or ""
    rating = _rating(rec)
    rev_n = _reviews_count(rec)
    kws = top_keywords(f"{title}\n{desc}", n=20)
    kw_line = ", ".join(w for w, _ in kws[:15])

    blob = _review_text_blob(rec)
    review_kws = top_keywords(blob, n=12) if blob.strip() else []
    review_line = ", ".join(f"{w} ({c})" for w, c in review_kws[:10]) if review_kws else "— (no recent reviews fetched)"

    features = []
    for line in desc.splitlines():
        t = line.strip()
        if t.startswith("•") or t.startswith("-") or re.match(r"^\d+[\).\s]", t):
            features.append(t.lstrip("•- ").strip())
    if not features:
        features = [ln.strip() for ln in desc.split(". ")[:5] if len(ln.strip()) > 20]

    seo = load_seo_context(_CFG["data_dir"])
    web_seeds = web_keywords_for_seed(seo)
    web_gaps = web_gaps_as_aso_opportunities(seo)
    seo_section = ""
    if web_seeds or web_gaps:
        parts = []
        if web_seeds:
            parts.append(f"- **High-traffic web keywords (from SEO rank data):** {', '.join(web_seeds[:10])}")
        if web_gaps:
            parts.append(f"- **Competitor keyword gaps (from web SEO):** {', '.join(web_gaps[:8])}")
        seo_section = "\n".join(parts) + "\n"

    prompt = f"""You are a senior conversion copywriter and mobile growth marketer.

## Context (real app data — use faithfully, do not invent stores or awards)

- **App name:** {title}
- **Platform listing summary:** {desc[:1200].strip()}{"…" if len(desc) > 1200 else ""}
- **Primary keywords (from listing text):** {kw_line}
- **Average rating:** {f"{rating:.2f}★" if rating is not None else "unknown"}
- **Rating/review count (if known):** {rev_n if rev_n is not None else "unknown"}
- **Themes in recent user reviews (token frequency):** {review_line}
{seo_section}

## Task

Write a **complete marketing landing page** (single long page) for this app that complements the store listing. Audience: high-intent visitors from search or ads.

### Deliverables (use clear headings)

1. **Hero section** — Headline, subhead, primary CTA, 2–3 trust bullets (privacy, free tier, offline, etc. only if supported by the description).
2. **Features** — 4–6 bullets; each ties to a user outcome; weave 2–3 keywords naturally.
3. **Testimonials placeholder** — 2 short realistic quotes labeled “Example — replace with real quotes” that match review themes above.
4. **FAQ** — 5 questions addressing objections (compatibility, pricing model if inferable, data use, account requirement, support).
5. **CTA block** — Repeat primary action + secondary link text for “See screenshots” style link.

### Style rules

- Plain, scannable English; short paragraphs; no keyword stuffing.
- Do not claim #1 ranking or fake awards.
- If information is missing, say what should be verified instead of guessing.

Output **Markdown** suitable for publishing.
"""

    body = "## LLM prompt: app landing page\n\n```\n" + prompt.strip() + "\n```"
    _write_md(body, f"ASO landing page prompt — {title[:40]}")
    print(body)


def cmd_blog_ideas(app_id: str):
    rec = _fetch_app_or_exit(app_id)
    title = rec.get("trackName") or ""
    desc = rec.get("description") or ""
    genre = rec.get("primaryGenreName") or ""
    app_kws = [w for w, _ in top_keywords(f"{title}\n{desc}", n=12)]

    comps, q_used = _competitors(rec, limit=5)
    comp_blob = " ".join(
        (c.get("trackName") or "") + " " + (c.get("description") or "")[:400] for c in comps
    )
    comp_kws = [w for w, _ in top_keywords(comp_blob, n=20)]

    blob = _review_text_blob(rec)
    theme_kws = [w for w, _ in top_keywords(blob, n=15)] if blob.strip() else []

    ideas = []
    base = app_kws + comp_kws + theme_kws
    seen = set()

    def add(t):
        if t.lower() in seen or len(ideas) >= 15:
            return
        seen.add(t.lower())
        ideas.append(t)

    k1 = app_kws[0] if app_kws else "app"
    kc = comp_kws[0] if comp_kws else "competitors"
    th = theme_kws[0] if theme_kws else "users"

    templates = [
        f"Why {k1} searchers pick one {genre.lower() or 'category'} app over another",
        f"{k1.title()} apps compared: features that actually matter in 2026",
        f"What {kc} keywords reveal about {genre.lower() or 'this'} market positioning",
        f"How to read App Store reviews for {k1} (spotting real {th} pain points)",
        f"ASO for {k1}: title, screenshots, and first lines that convert",
        f"Building trust for a {genre.lower() or 'niche'} app without a big brand",
        f"Onboarding patterns that reduce churn for {k1}-style products",
        f"Content marketing ideas for apps competing on “{kc}”",
        f"Translating in-app value into landing page copy for {k1}",
        f"Seasonal angles for promoting a {genre.lower() or 'utility'} app",
        f"Using competitor gaps ({kc}) to shape your feature roadmap",
        f"FAQ content that captures long-tail {k1} searches",
        f"Case study outline: improving ratings for apps with “{th}” feedback",
        f"Privacy-first messaging for {genre.lower() or 'data-sensitive'} apps",
        f"From store page to blog: repurposing your {k1} story",
    ]
    for t in templates:
        add(t)
    while len(ideas) < 15:
        add(f"Deep dive #{len(ideas)+1}: {k1}, {kc}, and user intent")

    lines = [
        f"## Blog ideas for **{title}**",
        "",
        f"_Competitor search query used:_ `{q_used}`",
        "",
        "### Signals used",
        "",
        f"- **App keywords:** {', '.join(app_kws[:8]) or '—'}",
        f"- **Competitor keywords (top 5 titles/descriptions):** {', '.join(comp_kws[:10]) or '—'}",
        f"- **Review themes:** {', '.join(theme_kws[:8]) or '—'}",
        "",
        "### Fifteen blog post titles",
        "",
    ]
    for i, idea in enumerate(ideas[:15], 1):
        lines.append(f"{i}. {idea}")

    seo = load_seo_context(_CFG["data_dir"])
    web_gaps = web_gaps_as_aso_opportunities(seo)
    app_pack = serp_app_pack_keywords(seo)
    if web_gaps or app_pack:
        lines.extend(["", "### SEO cross-insights", ""])
        if web_gaps:
            lines.append(f"**Web competitor gaps to target:** {', '.join(f'`{g}`' for g in web_gaps[:8])}")
        if app_pack:
            lines.append(f"**Keywords with app SERP features:** {', '.join(f'`{k}`' for k in app_pack[:8])}")
            lines.append("_(These keywords show video/app results in Google — high app-intent.)_")

    body = "\n".join(lines)
    _write_md(body, f"ASO blog ideas — {title[:40]}")
    print(body)


def _app_context_block(rec):
    if not rec:
        return ""
    title = rec.get("trackName") or ""
    desc = (rec.get("description") or "")[:2000]
    rating = _rating(rec)
    rev_n = _reviews_count(rec)
    kws = ", ".join(w for w, _ in top_keywords(f"{title}\n{desc}", n=15))
    return f"""
## App context (insert faithfully)

- **Name:** {title}
- **Bundle ID:** {rec.get('bundleId')}
- **Genre:** {rec.get('primaryGenreName')}
- **Rating:** {f"{rating:.2f}★" if rating is not None else "n/a"} ({rev_n if rev_n is not None else "n/a"} reviews)
- **Top keywords from listing:** {kws}
- **Description excerpt:**
```
{desc.strip()}{"…" if len(rec.get("description") or "") > 2000 else ""}
```
""".strip()


def cmd_prompt(task: str, app_id: str | None):
    rec = itunes_lookup(app_id) if app_id else None
    if app_id and not rec:
        print(f"Lookup failed for --app {app_id}; continuing without app context.", file=sys.stderr)
    ctx = _app_context_block(rec) if rec else ""

    bodies = {
        "write title": f"""You are an ASO specialist for the Apple App Store.

{ctx if ctx else "## Context\n\nNo specific app provided — use generic best practices."}

## Task
Draft **3 alternative app titles** (each ≤ 30 characters including spaces). Rules:
- Lead with **brand**; add **one or two high-value keywords** that match actual functionality.
- No competitor names, no misleading claims, no excessive punctuation.
- Avoid duplicating terms you will place in the iOS **keyword field**.

For each option, add a **one-line rationale** (search intent + differentiation).

Output as a Markdown bullet list.
""",
        "write description": f"""You are an ASO copywriter.

{ctx if ctx else "## Context\n\nNo specific app provided — write guidance for a generic utility app."}

## Task
Write a **full App Store description** with:
1. **Hook** (first 2–3 lines): primary benefit + keyword naturally included.
2. **Feature sections** with short headings (Markdown `###`).
3. **Social proof** line if ratings/reviews are provided above; otherwise omit numbers.
4. **Bulleted benefits** (5–7 bullets) scannable on mobile.
5. **Closing CTA** with a clear install phrase.

Formatting tips: short paragraphs; avoid keyword stuffing; no ALL CAPS blocks; include a **What’s New** placeholder heading the developer can fill.

Output **Markdown**.
""",
        "screenshot text": f"""You are a mobile UX copywriter.

{ctx if ctx else "## Context\n\nNo specific app — assume a productivity app."}

## Task
Produce **caption text for 5–8 App Store screenshots** in order:
- For each, give: **Headline** (≤6 words), **Subline** (≤14 words), optional **fine print** for disclaimers.
- Map captions to a plausible screenshot sequence (onboarding, core action, results, settings/privacy, social proof).
- Style: benefit-first, plain English, no fake awards.

Output a numbered Markdown list.
""",
        "update notes": f"""You are a product marketer.

{ctx if ctx else "## Context\n\nNo specific app — write a template."}

## Task
Write **“What’s New”** release notes for the next App Store submission:
- **Tone:** friendly, specific, honest.
- Structure: **Highlights** (2–4 bullets) + **Fixes** (if any generic) + **Thanks** line.
- Avoid internal jargon; no placeholder version numbers unless provided.

If app context is present, infer plausible improvements from the feature list; label speculative items as optional.

Output **Markdown** (short, mobile-friendly).
""",
        "reply reviews": f"""You are a customer support lead for a mobile app team.

{ctx if ctx else "## Context\n\nGeneric app — no live listing data."}

## Task
Create a **review response playbook** in Markdown:
1. Principles (empathy, brevity, no arguments, invite offline support).
2. **5 templates** for: 5★ praise, 4★ feature request, 3★ mixed, 1–2★ bug report, 1★ rant.
3. **Do / Don’t** table for refunds, competitors, and policy disputes.

If app context is included, add **2 filled-in example replies** tailored to likely themes from the app’s niche (still anonymized).

Output **Markdown** only.
""",
    }

    body_text = bodies[task]
    body = f"## LLM prompt: `{task}`\n\n```\n{body_text.strip()}\n```"
    _write_md(body, f"ASO LLM prompt — {task}")
    print(body)


def main():
    parser = argparse.ArgumentParser(description="ASO education + LLM prompt generator.")
    parser.add_argument("--learn", action="store_true", help="Print ASO crash course (~800 words).")
    parser.add_argument("--checklist", metavar="APP_ID", help="Personalized ASO checklist for an iTunes app id.")
    parser.add_argument("--content-plan", metavar="APP_ID", dest="content_plan", help="Blog + landing section ideas.")
    parser.add_argument("--landing-page", metavar="APP_ID", dest="landing_page", help="LLM prompt for a landing page.")
    parser.add_argument("--blog-ideas", metavar="APP_ID", dest="blog_ideas", help="15 blog titles from signals.")
    parser.add_argument(
        "--prompt",
        choices=["write title", "write description", "screenshot text", "update notes", "reply reviews"],
        metavar="TASK",
        help="Task-specific LLM prompt template.",
    )
    parser.add_argument("--app", metavar="APP_ID", help="Optional iTunes app id to inject into --prompt.")

    args = parser.parse_args()

    modes = [
        args.learn,
        args.checklist,
        args.content_plan,
        args.landing_page,
        args.blog_ideas,
        args.prompt is not None,
    ]
    if sum(bool(m) for m in modes) != 1:
        parser.error("Specify exactly one of: --learn, --checklist, --content-plan, --landing-page, --blog-ideas, --prompt")

    if args.learn:
        cmd_learn()
    elif args.checklist:
        cmd_checklist(args.checklist)
    elif args.content_plan:
        cmd_content_plan(args.content_plan)
    elif args.landing_page:
        cmd_landing_page(args.landing_page)
    elif args.blog_ideas:
        cmd_blog_ideas(args.blog_ideas)
    else:
        cmd_prompt(args.prompt, args.app)


if __name__ == "__main__":
    main()
