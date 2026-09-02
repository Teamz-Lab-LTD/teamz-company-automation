#!/usr/bin/env python3
"""
build-static-schema.py
Extracts schema data from each page's inline JS and injects
static <script type="application/ld+json"> into <head>.
Called directly by pre-commit hook and nightly/continuous build scripts.
"""

import os, re, json, html, glob, sys, subprocess
from pathlib import Path
from _teamz_config import load_runtime

RUNTIME = load_runtime(__file__)
BASE_DIR = Path(RUNTIME["host_site_root"])
SITE_URL = RUNTIME["site_url"].rstrip("/")
TEAMZ_URL = "https://teamzlab.com"
PROJECT_TYPE = RUNTIME.get("project_type", "website")
MARKER = "<!-- STATIC-SCHEMA -->"

SKIP_DIRS = {"about", "contact", "privacy", "terms"}
count = 0
skip = 0
errors = []


def extract_breadcrumbs(content):
    """Extract breadcrumb schema from injectBreadcrumbSchema([...]) or variable."""
    # Pattern 1: inline array — injectBreadcrumbSchema([{...},{...}])
    m = re.search(r'injectBreadcrumbSchema\(\[(.+?)\]\)', content, re.DOTALL)
    if not m:
        # Pattern 2: variable — var breadcrumbs = [...] or var BREADCRUMBS = [...]
        for varname in ('breadcrumbs', 'BREADCRUMBS'):
            if f'injectBreadcrumbSchema({varname})' in content:
                m2 = re.search(rf'var {varname}\s*=\s*\[(.+?)\]', content, re.DOTALL)
                if m2:
                    m = m2
                    break
    if not m:
        return None

    arr_str = m.group(1)
    # Normalize JS objects to JSON: {name:'X',url:'/'} -> {"name":"X","url":"/"}
    arr_str = re.sub(r"(\w+)\s*:\s*'", r'"\1":"', arr_str)
    arr_str = re.sub(r"'\s*([,}])", r'"\1', arr_str)
    # Handle double-quoted JS too
    arr_str = re.sub(r'(\w+)\s*:\s*"', r'"\1":"', arr_str)

    try:
        items = json.loads("[" + arr_str + "]")
    except json.JSONDecodeError:
        return None

    elements = []
    for i, item in enumerate(items):
        entry = {"@type": "ListItem", "position": i + 1, "name": html.unescape(item["name"])}
        if "url" in item:
            entry["item"] = SITE_URL + item["url"]
        elements.append(entry)

    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": elements,
    }


def extract_faqs(content):
    """Extract FAQ schema from var faqs = [...] block."""
    if "injectFAQSchema" not in content:
        return None

    # Try all variable name patterns (var + const + let, lower + upper)
    start = -1
    for varname in (
        "var faqs = [", "var faqs=[",
        "var FAQS = [", "var FAQS=[",
        "const faqs = [", "const faqs=[",
        "const FAQS = [", "const FAQS=[",
        "let faqs = [", "let faqs=[",
        "let FAQS = [", "let FAQS=[",
    ):
        start = content.find(varname)
        if start != -1:
            break
    if start == -1:
        return None

    bracket_start = content.index("[", start)
    depth = 0
    end = bracket_start
    for i in range(bracket_start, len(content)):
        if content[i] == "[":
            depth += 1
        elif content[i] == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    arr_str = content[bracket_start:end]

    # Extract q/a pairs with regex
    pairs = re.findall(
        r"q\s*:\s*['\"](.+?)['\"],\s*\n?\s*a\s*:\s*['\"](.+?)['\"]\s*\n?\s*}",
        arr_str,
        re.DOTALL,
    )

    if not pairs:
        return None

    faqs = []
    for q, a in pairs:
        q = q.replace("\\'", "'").replace('\\"', '"').strip()
        a = a.replace("\\'", "'").replace('\\"', '"').strip()
        faqs.append(
            {
                "@type": "Question",
                "name": html.unescape(q),
                "acceptedAnswer": {"@type": "Answer", "text": html.unescape(a)},
            }
        )

    if not faqs:
        return None

    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faqs}


def extract_webapp(content, filepath=""):
    """Extract WebApplication schema from injectWebAppSchema({...}) or variable."""
    m = re.search(r"injectWebAppSchema\(\{(.*?)\}\)", content, re.DOTALL)
    if not m:
        # Try variable pattern: var TOOL_CONFIG = {...}; injectWebAppSchema(TOOL_CONFIG)
        for varname in ("TOOL_CONFIG", "toolConfig"):
            if f"injectWebAppSchema({varname})" in content:
                m2 = re.search(rf"var {varname}\s*=\s*\{{(.*?)\}}", content, re.DOTALL)
                if m2:
                    m = m2
                    break
    if not m:
        return None

    block = m.group(1)

    # Try inline quoted strings first
    title_m = re.search(r"title\s*:\s*['\"](.+?)['\"]", block)
    desc_m = re.search(r"description\s*:\s*['\"](.+?)['\"]", block)
    slug_m = re.search(r"slug\s*:\s*['\"](.+?)['\"]", block)

    # If block uses variables (title: TITLE), resolve from var declarations
    if not title_m:
        var_m = re.search(r"title\s*:\s*(\w+)", block)
        if var_m:
            varname = var_m.group(1)
            val_m = re.search(rf"var {varname}\s*=\s*['\"](.+?)['\"]", content)
            if val_m:
                title_m = val_m

    if not desc_m:
        var_m = re.search(r"description\s*:\s*(\w+)", block)
        if var_m:
            varname = var_m.group(1)
            val_m = re.search(rf"var {varname}\s*=\s*['\"](.+?)['\"]", content)
            if val_m:
                desc_m = val_m

    if not slug_m:
        var_m = re.search(r"slug\s*:\s*(\w+)", block)
        if var_m:
            varname = var_m.group(1)
            val_m = re.search(rf"var {varname}\s*=\s*['\"](.+?)['\"]", content)
            if val_m:
                slug_m = val_m

    if not title_m:
        return None

    title = title_m.group(1).replace("\\'", "'")
    desc = desc_m.group(1).replace("\\'", "'") if desc_m else title

    # Resolve slug: use extracted slug or derive from filepath
    if slug_m:
        slug = slug_m.group(1)
        # If slug doesn't include directory, derive from filepath
        if "/" not in slug and filepath:
            dir_path = os.path.dirname(filepath).replace("\\", "/")
            slug = dir_path
    elif filepath:
        slug = os.path.dirname(filepath).replace("\\", "/")
    else:
        return None

    # Get lang from <html lang="xx">
    lang_m = re.search(r'<html[^>]*lang="([^"]+)"', content)
    lang = lang_m.group(1) if lang_m else "en"

    return {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": html.unescape(title),
        "description": html.unescape(desc),
        "url": f"{SITE_URL}/{slug}/",
        "applicationCategory": "UtilityApplication",
        "operatingSystem": "All",
        "browserRequirements": "Requires JavaScript",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "author": {"@type": "Organization", "name": "Teamz Lab", "url": TEAMZ_URL, "foundingDate": "2023"},
        "publisher": {"@type": "Organization", "name": "Teamz Lab", "url": TEAMZ_URL},
        "inLanguage": lang,
    }


twitter_fixed = 0
ahrefs_fixed = 0

AHREFS_SNIPPET = '  <script src="https://analytics.ahrefs.com/analytics.js" data-key="ZQ0gF0rxGwTEy//NGtIzxQ" async></script>\n'

def fix_ahrefs_analytics(content):
    """Ensure every page has the Ahrefs Web Analytics script before </head>."""
    global ahrefs_fixed
    if 'analytics.ahrefs.com/analytics.js' in content:
        return content
    if '</head>' not in content:
        return content
    ahrefs_fixed += 1
    return content.replace('</head>', AHREFS_SNIPPET + '</head>', 1)


def fix_twitter_tags(content):
    """Auto-inject missing twitter:card/title/description from OG tags."""
    global twitter_fixed
    changed = False

    # If twitter:card missing entirely, inject a full block after og:description
    # (or after og:title if og:description missing, else before </head>).
    if 'twitter:card' not in content:
        og_title = re.search(r'property="og:title"\s+content="([^"]*)"', content)
        og_desc = re.search(r'property="og:description"\s+content="([^"]*)"', content)
        og_image = re.search(r'property="og:image"\s+content="([^"]*)"', content)
        if not og_title:
            return content  # No OG tags — probably not a real tool page, skip

        lines = ['  <meta name="twitter:card" content="summary">']
        lines.append(f'  <meta name="twitter:title" content="{og_title.group(1)}">')
        if og_desc:
            lines.append(f'  <meta name="twitter:description" content="{og_desc.group(1)[:200]}">')
        if og_image:
            lines.append(f'  <meta name="twitter:image" content="{og_image.group(1)}">')
        block = "\n".join(lines) + "\n"

        # Insert after og:image if present, else after og:description, else og:title, else before </head>
        anchor_match = None
        for pat in (r'<meta property="og:image"[^>]*>', r'<meta property="og:description"[^>]*>', r'<meta property="og:title"[^>]*>'):
            m = re.search(pat, content)
            if m:
                anchor_match = m
                break
        if anchor_match:
            i = anchor_match.end()
            content = content[:i] + "\n" + block.rstrip() + content[i:]
        elif '</head>' in content:
            content = content.replace('</head>', block + '</head>', 1)
        else:
            return content
        twitter_fixed += 1
        return content

    # Fix missing twitter:title
    if 'twitter:title' not in content:
        og_title = re.search(r'property="og:title"\s+content="([^"]*)"', content)
        if og_title:
            insert = f'  <meta name="twitter:title" content="{og_title.group(1)}">\n'
            content = content.replace(
                '<meta name="twitter:card" content="summary">',
                '<meta name="twitter:card" content="summary">\n' + insert.rstrip(),
            )
            changed = True

    # Fix missing twitter:description
    if 'twitter:description' not in content:
        og_desc = re.search(r'property="og:description"\s+content="([^"]*)"', content)
        if og_desc:
            desc = og_desc.group(1)[:200]  # Twitter allows 200 chars
            insert = f'  <meta name="twitter:description" content="{desc}">'
            # Insert after twitter:title if it exists, otherwise after twitter:card
            if 'twitter:title' in content:
                content = re.sub(
                    r'(<meta name="twitter:title"[^>]*>)',
                    r'\1\n' + insert,
                    content,
                    count=1,
                )
            else:
                content = content.replace(
                    '<meta name="twitter:card" content="summary">',
                    '<meta name="twitter:card" content="summary">\n' + insert,
                )
            changed = True

    if changed:
        twitter_fixed += 1
    return content


def carry_forward_unregenerated(content, regenerated_types):
    """Rescue schema blocks the rebuild below would otherwise destroy.

    process_file() deletes the whole marker block and rebuilds it from ONLY
    what it could extract from JS this run. That is silent data loss for any
    @type whose source is not a JS inject call — nightly tool builders write
    some ld+json tags directly into the marker block, and those have no JS to
    re-extract from.

    Verified live 2026-08-04 on 3d/ai-3d-prompt-generator: the page carried
    BreadcrumbList + FAQPage + WebApplication and ZERO inject calls. One run
    reduced it to FAQPage alone — the only type still reachable, via the
    renderFAQs() gate added earlier the same day.

    That earlier gate is what turned this from dormant to active: before it,
    extract_faqs() also returned None here, schema_blocks came back empty, and
    the early-return above protected the page by never deleting anything. This
    is the same data-loss class as the injector-stripping bug fixed the same
    day, reached from the opposite direction.

    Returns raw JSON strings to append verbatim to the rebuilt block.
    """
    marker_match = re.search(
        rf"{re.escape(MARKER)}(.*?){re.escape(MARKER)}", content, re.DOTALL
    )
    if not marker_match:
        return []

    carried = []
    for tag in re.finditer(
        r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        marker_match.group(1),
        flags=re.DOTALL | re.IGNORECASE,
    ):
        try:
            parsed = json.loads(tag.group(1).strip())
        except json.JSONDecodeError:
            continue  # never carry forward a block we cannot even parse
        if not isinstance(parsed, dict):
            continue
        stype = parsed.get("@type")
        if stype and stype not in regenerated_types:
            carried.append(json.dumps(parsed, ensure_ascii=False))
    return carried

def process_file(filepath):
    """Process a single HTML file: extract schemas, inject static JSON-LD, fix twitter tags."""
    global count, skip

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        original = content

    # Skip redirect pages
    if 'http-equiv="refresh"' in content:
        return

    # Auto-fix missing twitter tags
    content = fix_twitter_tags(content)
    content = fix_ahrefs_analytics(content)

    # Extract all schemas from JS calls
    schema_blocks = []

    bc = extract_breadcrumbs(content)
    if bc:
        schema_blocks.append(json.dumps(bc, ensure_ascii=False))

    faq = extract_faqs(content)
    if faq:
        schema_blocks.append(json.dumps(faq, ensure_ascii=False))

    webapp = extract_webapp(content, filepath)
    if webapp:
        schema_blocks.append(json.dumps(webapp, ensure_ascii=False))

    if not schema_blocks:
        # No JS schema calls found — but twitter fix may have mutated content.
        # Persist twitter fix even when no schemas were extracted.
        if content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        if MARKER in content:
            marker_match = re.search(rf"{re.escape(MARKER)}(.*?){re.escape(MARKER)}", content, re.DOTALL)
            if marker_match and 'application/ld+json' in marker_match.group(1):
                count += 1  # Already has valid static schemas, no changes needed
                return
        skip += 1
        return

    # Rescue types the rebuild cannot regenerate BEFORE the marker block that
    # holds them is deleted a few lines down. Order matters: read, then delete.
    regenerated_types = set()
    if bc:
        regenerated_types.add("BreadcrumbList")
    if faq:
        regenerated_types.add("FAQPage")
    if webapp:
        regenerated_types.add("WebApplication")
    schema_blocks.extend(carry_forward_unregenerated(content, regenerated_types))

    # Remove old static schema blocks before injecting new ones
    if MARKER in content:
        content = re.sub(
            rf"{re.escape(MARKER)}.*?{re.escape(MARKER)}\n?",
            "",
            content,
            flags=re.DOTALL,
        )

    # Remove redundant runtime JS inject calls that duplicate the static schemas
    # (Google flags "Duplicate field FAQPage" etc. when both static + runtime exist)
    if faq:
        content = re.sub(r'\s*TeamzTools\.injectFAQSchema\([^)]*\);?', '', content)
        content = re.sub(r'\s*if\s*\([^)]*injectFAQSchema[^;]*;', '', content)
    if bc:
        content = re.sub(r'\s*TeamzTools\.injectBreadcrumbSchema\([^)]*\);?', '', content)
    if webapp:
        content = re.sub(r'\n?\s*TeamzTools\.injectWebAppSchema\([^;]*;', '', content)

    # After stripping calls, also strip any dangling `if (TeamzTools.injectXxx)`
    # guard whose body was just removed. Without this, the next statement gets
    # silently absorbed as the body, which at best is a semantic bug and at worst
    # is a JS syntax error when followed by `}`.
    content = re.sub(
        r'^[ \t]*if\s*\(\s*TeamzTools\.(?:injectBreadcrumbSchema|injectFAQSchema|injectWebAppSchema)\s*\)\s*;?\s*$\n',
        '',
        content,
        flags=re.MULTILINE,
    )

    # Build the injection block
    lines = [MARKER]
    for schema_json in schema_blocks:
        lines.append(f'  <script type="application/ld+json">{schema_json}</script>')
    lines.append(MARKER)
    injection = "\n".join(lines) + "\n"

    # Insert before </head>
    if "</head>" in content:
        content = content.replace("</head>", injection + "</head>", 1)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        count += 1
    else:
        errors.append(filepath)


def main():
    if PROJECT_TYPE == "app":
        print("INFO: build-static-schema.py is website-focused and disabled for TEAMZ_PROJECT_TYPE=app.")
        sys.exit(2)

    os.chdir(BASE_DIR)
    print("=== Building static schema ===")

    # Support targeted runs:
    #   python3 build-static-schema.py                → all tools
    #   python3 build-static-schema.py --staged        → only git-staged files (used by pre-commit)
    #   python3 build-static-schema.py ai/grammar-checker  → specific tool path
    #   python3 build-static-schema.py ai/ health/     → specific hubs

    args = sys.argv[1:]
    staged_only = "--staged" in args
    targets = [a for a in args if a != "--staged"]

    if staged_only:
        # Only process staged index.html files
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                capture_output=True, text=True, timeout=10,
            )
            files = [f for f in result.stdout.strip().split("\n") if f.endswith("index.html")]
        except Exception:
            files = []
        if not files:
            print("  No staged index.html files — skipping")
            print("=== Done ===")
            return
        print(f"  Targeted: {len(files)} staged file(s)")
        for filepath in sorted(files):
            parts = filepath.split("/")
            if len(parts) < 2 or parts[0] in SKIP_DIRS:
                continue
            process_file(filepath)
    elif targets:
        # Process specific paths (tool or hub)
        files = []
        for t in targets:
            t = t.rstrip("/")
            idx = os.path.join(t, "index.html")
            if os.path.isfile(idx):
                files.append(idx)
            elif os.path.isdir(t):
                for f in sorted(glob.glob(os.path.join(t, "**/index.html"), recursive=True)):
                    files.append(f)
        print(f"  Targeted: {len(files)} file(s)")
        for filepath in sorted(files):
            parts = filepath.split("/")
            if len(parts) < 2 or parts[0] in SKIP_DIRS:
                continue
            process_file(filepath)
    else:
        # Process all tools
        for filepath in sorted(glob.glob("**/index.html", recursive=True)):
            parts = filepath.split("/")
            if len(parts) < 2:
                continue
            if parts[0] in SKIP_DIRS:
                continue
            if filepath == "404.html":
                continue
            process_file(filepath)

    print(f"  Static schema: {count} pages updated, {skip} skipped")
    if twitter_fixed:
        print(f"  Twitter tags: {twitter_fixed} pages auto-fixed")
    if errors:
        print(f"  Errors: {len(errors)} files")
        for e in errors:
            print(f"    {e}")
    print("=== Done ===")


if __name__ == "__main__":
    main()
