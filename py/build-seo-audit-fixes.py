#!/usr/bin/env python3
"""
Teamz Lab Tools — SEO Audit Mechanical Fixes

Fixes the specific crawl-audit issues currently affecting the site:
1. Title tag too short
2. URL/title keyword mismatch on clean URLs
3. Low visible word count on thin hub/static pages

Usage:
  python3 scripts/build-seo-audit-fixes.py --dry-run
  python3 scripts/build-seo-audit-fixes.py --apply
"""

from __future__ import annotations

import html
import os
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "shared",
    "branding",
    "scripts",
    "docs",
    "icons",
    "og-images",
    ".claude-memory",
}

TITLE_SUFFIX = " — Teamz Lab Tools"
MIN_TITLE_LEN = 30
MIN_MAIN_WORDS = 220

SPECIAL_SLUG_LABELS = {
    "uidesign": "UI Design",
    "eldercare": "Elder Care",
    "evergreen": "Evergreen",
    "auto": "Auto",
    "dev": "Dev",
    "seo": "SEO",
    "ai": "AI",
    "gadgets": "Gadgets",
}

ACRONYM_WORDS = {
    "ai": "AI",
    "seo": "SEO",
    "faq": "FAQ",
    "ats": "ATS",
    "ocr": "OCR",
    "jwt": "JWT",
    "api": "API",
    "css": "CSS",
    "json": "JSON",
    "yaml": "YAML",
    "url": "URL",
    "dns": "DNS",
    "vpn": "VPN",
    "sql": "SQL",
    "svg": "SVG",
    "png": "PNG",
    "jpg": "JPG",
    "jpeg": "JPEG",
    "gif": "GIF",
    "webp": "WebP",
    "heic": "HEIC",
    "pdf": "PDF",
    "csv": "CSV",
    "apr": "APR",
    "cgt": "CGT",
    "eos": "EOS",
    "iloe": "ILOE",
    "sss": "SSS",
    "pagibig": "Pag-IBIG",
    "philhealth": "PhilHealth",
    "zatca": "ZATCA",
    "ejar": "Ejar",
    "bhxh": "BHXH",
    "vat": "VAT",
    "hdb": "HDB",
    "cpf": "CPF",
    "absd": "ABSD",
    "tdsr": "TDSR",
    "wfh": "WFH",
    "nhr": "NHR",
}


def iter_pages():
    for path in ROOT.rglob("index.html"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        yield path


def get_match(pattern: str, content: str, flags: int = re.IGNORECASE | re.DOTALL):
    return re.search(pattern, content, flags)


def get_html_lang(content: str) -> str:
    match = get_match(r"<html[^>]*\blang=\"([^\"]+)\"", content)
    return (match.group(1) if match else "en").strip().lower()


def get_title(content: str) -> str:
    match = get_match(r"<title>(.*?)</title>", content)
    return html.unescape(match.group(1).strip()) if match else ""


def get_description(content: str) -> str:
    match = get_match(r'<meta\s+name="description"\s+content="(.*?)"', content)
    return html.unescape(match.group(1).strip()) if match else ""


def get_h1(content: str) -> str:
    match = get_match(r"<h1[^>]*>(.*?)</h1>", content)
    if not match:
        return ""
    return re.sub(r"<[^>]+>", "", html.unescape(match.group(1))).strip()


def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_main_words(content: str) -> int:
    main = get_match(r"<main[^>]*>(.*?)</main>", content)
    if not main:
        body = get_match(r"<body[^>]*>(.*?)</body>", content)
        if not body:
            return 0
        return len(strip_tags(body.group(1)).split())
    return len(strip_tags(main.group(1)).split())


def is_redirect_stub(content: str) -> bool:
    if re.search(r"http-equiv=\"refresh\"", content, re.IGNORECASE):
        return True
    if re.search(r'<meta[^>]+name="robots"[^>]+content="[^"]*noindex', content, re.IGNORECASE):
        return True
    return False


def normalize_tokens(text: str) -> list[str]:
    tokens = []
    current = []
    for char in text.lower():
        category = unicodedata.category(char)
        if category.startswith(("L", "N")):
            current.append(char)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return tokens


def ascii_only(text: str) -> bool:
    return all(ord(char) < 128 for char in text)


def has_non_latin_letters(text: str) -> bool:
    for char in text:
        if not unicodedata.category(char).startswith("L"):
            continue
        if ord(char) < 128:
            continue
        try:
            name = unicodedata.name(char)
        except ValueError:
            return True
        if "LATIN" not in name:
            return True
    return False


def strip_suffix(title: str) -> tuple[str, str]:
    suffix_patterns = [
        " — Teamz Lab Tools",
        " | Teamz Lab Tools",
        " — Teamz Lab",
        " | Teamz Lab",
    ]
    for suffix in suffix_patterns:
        if title.endswith(suffix):
            return title[: -len(suffix)].strip(), suffix
    return title.strip(), TITLE_SUFFIX


def humanize_slug(slug: str) -> str:
    if slug in SPECIAL_SLUG_LABELS:
        return SPECIAL_SLUG_LABELS[slug]
    if len(slug) == 2 and slug.isalpha():
        return slug.upper()

    words = []
    for part in slug.split("-"):
        if not part:
            continue
        if part in ACRONYM_WORDS:
            words.append(ACRONYM_WORDS[part])
        elif part.isdigit():
            words.append(part)
        else:
            words.append(part.replace("_", " ").title())
    return " ".join(words).strip()


def title_overlap_ratio(base_title: str, slug: str) -> float:
    slug_tokens = [token for token in normalize_tokens(slug.replace("-", " ")) if len(token) > 1]
    if not slug_tokens:
        return 1.0
    title_tokens = set(normalize_tokens(base_title))
    overlap = sum(1 for token in slug_tokens if token in title_tokens)
    return overlap / len(slug_tokens)


def fold_for_compare(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    return "".join(char.lower() for char in folded if char.isalnum())


def preserved_title_bits(base_title: str, alias: str) -> list[str]:
    alias_tokens = set(normalize_tokens(alias))
    preserved = []
    for token in re.findall(r"\b[A-Za-z0-9&+\-]+\b", base_title):
        normalized = token.lower().strip("()")
        if normalized in alias_tokens:
            continue
        if re.fullmatch(r"20\d{2}", token):
            preserved.append(token)
        elif token.isupper() and len(token) <= 5:
            preserved.append(token)
        elif token in {"Australia", "Canada", "Singapore", "Nigeria", "Ghana", "Ireland", "Dubai", "UAE", "UK"}:
            preserved.append(token)
    deduped = []
    seen = set()
    for token in preserved:
        if token not in seen:
            deduped.append(token)
            seen.add(token)
    return deduped


def replace_title_family(content: str, new_title: str) -> str:
    escaped = html.escape(new_title, quote=True)
    content = re.sub(r"<title>.*?</title>", f"<title>{escaped}</title>", content, count=1, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(
        r'(<meta\s+property="og:title"\s+content=")(.*?)(")',
        lambda match: match.group(1) + escaped + match.group(3),
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    content = re.sub(
        r'(<meta\s+name="twitter:title"\s+content=")(.*?)(")',
        lambda match: match.group(1) + escaped + match.group(3),
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return content


def build_new_title(rel_path: Path, content: str) -> tuple[str | None, list[str]]:
    current_title = get_title(content)
    if not current_title:
        return None, []

    base_title, current_suffix = strip_suffix(current_title)
    suffix = TITLE_SUFFIX if "Teamz Lab Tools" in current_suffix or current_suffix else current_suffix
    if not suffix:
        suffix = TITLE_SUFFIX

    parts = rel_path.parts
    is_root = rel_path.as_posix() == "index.html"
    is_hub = is_root or (len(parts) == 2 and parts[-1] == "index.html")
    slug = ""
    if len(parts) >= 3:
        slug = parts[-2]
    elif is_hub and not is_root:
        slug = parts[0]
    elif is_root:
        slug = "home"

    alias = humanize_slug(slug) if slug else ""
    overlap = title_overlap_ratio(base_title, slug) if slug else 1.0
    non_ascii_title = has_non_latin_letters(base_title)
    alias_present = bool(alias) and fold_for_compare(alias) in fold_for_compare(base_title)
    title_needs_length = len(current_title) < MIN_TITLE_LEN
    title_needs_code = is_hub and len(slug) == 2 and slug.upper() not in base_title
    title_needs_alignment = False

    if slug:
        if title_needs_code:
            title_needs_alignment = True
        elif non_ascii_title and ascii_only(slug) and not alias_present:
            title_needs_alignment = True
        elif not is_hub and not alias_present and overlap == 0:
            if re.match(r"(?i)^(what|how|why)\b", base_title):
                title_needs_alignment = True
            elif re.search(r"\b[A-Z]{2,5}\b", base_title):
                title_needs_alignment = True
            elif len(base_title) < 22:
                title_needs_alignment = True
            elif slug in {"ambient-sound-mixer", "clothing-suggester"}:
                title_needs_alignment = True
        elif not is_hub and not alias_present and overlap < 0.2 and slug in {"capital-gains-tax-calculator"}:
            title_needs_alignment = True

    if not title_needs_length and not title_needs_alignment and suffix == current_suffix:
        return None, []

    new_base = base_title
    reasons = []

    if title_needs_alignment and slug:
        reasons.append("title_alignment")
        if title_needs_code:
            new_base = f"{base_title} ({slug.upper()})"
        elif is_hub:
            new_base = f"{base_title} ({alias})"
        elif non_ascii_title:
            if alias and alias.lower() not in base_title.lower():
                new_base = f"{base_title} ({alias})"
        else:
            new_base = f"{base_title} ({alias})"

    if len(f"{new_base}{suffix}") < MIN_TITLE_LEN:
        reasons.append("title_length")
        if is_hub:
            if len(slug) == 2 or non_ascii_title:
                new_base = f"{new_base} Hub"
            elif "tool" in new_base.lower() or "tools" in new_base.lower() or "calculators" in new_base.lower():
                new_base = f"{new_base} Hub"
            else:
                new_base = f"{new_base} Tools Hub"
        else:
            if re.search(r"(?i)\b(calculator|checker|generator|converter|planner|tracker|quiz|timer|tool|viewer|decoder|parser|maker|estimator|formatter)\b", new_base):
                new_base = f"{new_base} Online"
            else:
                new_base = f"{new_base} Online Tool"

    new_title = f"{new_base}{suffix}"
    if new_title == current_title:
        return None, []
    return new_title, reasons


def get_card_titles(content: str) -> list[str]:
    titles = []
    for match in re.finditer(r"<h3[^>]*>(.*?)</h3>", content, re.IGNORECASE | re.DOTALL):
        title = strip_tags(match.group(1))
        if title:
            titles.append(title)
    return titles


def join_titles_for_copy(titles: list[str], limit: int = 5) -> str:
    if not titles:
        return "specialized Teamz Lab tools"
    picked = titles[:limit]
    if len(picked) == 1:
        return picked[0]
    if len(picked) == 2:
        return f"{picked[0]} and {picked[1]}"
    return ", ".join(picked[:-1]) + f", and {picked[-1]}"


def build_low_word_section(rel_path: Path, content: str) -> str | None:
    if 'data-seo-audit="expanded"' in content:
        return None

    h1 = get_h1(content) or strip_suffix(get_title(content))[0] or "these tools"
    description = get_description(content)
    titles = get_card_titles(content)
    lead_tools = join_titles_for_copy(titles)
    description_sentence = description.strip()
    if description_sentence and description_sentence[-1] not in ".!?。！？":
        description_sentence += "."

    if rel_path.as_posix() == "contact/index.html":
        return f"""
    <section class="tool-content" data-seo-audit="expanded">
      <h2>What You Can Contact Teamz Lab About</h2>
      <p>This page is the main contact point for Teamz Lab Tools. Use it to report bugs, request improvements, suggest new calculators, or ask about custom development work. If a page feels confusing, outdated, or incomplete, sending a clear note here helps us fix the issue faster and improve the overall quality of the tool library.</p>
      <h2>Support, Feedback, and Custom Tool Requests</h2>
      <p>Many visitors use the contact form to request business-specific calculators, internal workflow tools, lead magnets, embedded widgets, or lightweight SaaS prototypes. It is also the right place to share SEO issues, incorrect formulas, broken layouts, translation problems, or outdated rate tables. Specific examples, URLs, screenshots, and expected behavior make support requests much easier to action.</p>
      <h2>Why This Contact Page Matters</h2>
      <p>Teamz Lab Tools covers a large library of practical calculators and generators, which means direct feedback is important for keeping the site accurate and useful. This contact page gives users a straightforward way to reach the team without an account, raise issues quickly, and start conversations about custom product or automation work.</p>
    </section>"""

    return f"""
    <section class="tool-content" data-seo-audit="expanded">
      <h2>What You Can Do with {h1}</h2>
      <p>{description_sentence} This collection brings together tools such as {lead_tools}, so visitors can move from browsing to solving a specific problem quickly. Instead of hunting through separate pages or spreadsheets, the hub gives you one place to compare options, open the right calculator, and get an answer with minimal setup.</p>
      <h2>Popular Tools in This Collection</h2>
      <p>Start with the most relevant page for your task, then use nearby tools for follow-up checks and comparisons. The pages in this section are designed to be focused, readable, and fast to use, which makes them practical for everyday planning, quick calculations, work decisions, and repeat tasks. That is especially useful when you want a direct answer rather than a long article or a complicated app flow.</p>
      <h2>Fast, Practical, and Browser-Based</h2>
      <p>Teamz Lab Tools is built around direct utility. Most pages work right in the browser, avoid unnecessary sign-up friction, and keep the experience lightweight enough to use on desktop or mobile. Bookmark this hub if you come back to these topics often, because it gives you a stable starting point for the most useful tools in this category.</p>
    </section>"""


def insert_low_word_section(content: str, section_html: str) -> str:
    if not section_html:
        return content

    ad_slot = re.search(r'\n\s*<div class="ad-slot">', content)
    if ad_slot:
        return content[: ad_slot.start()] + section_html + "\n" + content[ad_slot.start() :]

    main_close = re.search(r"\n\s*</main>", content)
    if main_close:
        return content[: main_close.start()] + section_html + "\n" + content[main_close.start() :]

    return content


def process_page(path: Path, apply: bool) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    if is_redirect_stub(content):
        return []

    rel_path = path.relative_to(ROOT)
    fixes = []
    new_content = content

    new_title, title_reasons = build_new_title(rel_path, new_content)
    if new_title:
        new_content = replace_title_family(new_content, new_title)
        fixes.extend(title_reasons)

    if get_main_words(new_content) < MIN_MAIN_WORDS:
        section = build_low_word_section(rel_path, new_content)
        if section:
            updated = insert_low_word_section(new_content, section)
            if updated != new_content:
                new_content = updated
                fixes.append("low_word_content")

    if apply and new_content != content:
        path.write_text(new_content, encoding="utf-8")

    return fixes


def main():
    apply = "--apply" in sys.argv
    pages = sorted(iter_pages())
    changed = []
    counters = {
        "title_length": 0,
        "title_alignment": 0,
        "low_word_content": 0,
    }

    for path in pages:
        fixes = process_page(path, apply=apply)
        if not fixes:
            continue
        rel = path.relative_to(ROOT).as_posix()
        changed.append((rel, fixes))
        for fix in fixes:
            if fix in counters:
                counters[fix] += 1

    mode = "APPLY" if apply else "DRY RUN"
    print(f"\nSEO audit fixes ({mode})")
    print(f"Scanned pages: {len(pages)}")
    print(f"Changed pages: {len(changed)}")
    print(f"  title length fixes: {counters['title_length']}")
    print(f"  title alignment fixes: {counters['title_alignment']}")
    print(f"  low word content fixes: {counters['low_word_content']}")
    if changed:
        print("\nExamples:")
        for rel, fixes in changed[:80]:
            print(f"  {rel}: {', '.join(fixes)}")


if __name__ == "__main__":
    main()
