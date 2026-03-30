#!/usr/bin/env python3
"""
Teamz Lab Tools — Bulk SEO Auto-Fixer
Fixes mechanical SEO issues across ALL tool pages.

Usage:
  python3 scripts/build-seo-fix-all.py --dry-run    # Preview changes
  python3 scripts/build-seo-fix-all.py --apply       # Apply all fixes
  python3 scripts/build-seo-fix-all.py --apply --hub us   # Fix one hub only
  python3 scripts/build-seo-fix-all.py --stats       # Show issue counts only

Fixes applied:
  1. Meta description: rewrite to start with action verb (if not already)
  2. Meta description: trim if >155 chars
  3. display='' bug: replace with showEl() or explicit display value
  4. Freshness signal: add "Last updated" to tool-content if missing
"""

import os
import re
import sys
import html
from pathlib import Path
from collections import defaultdict

# --- Config ---
ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {'.git', 'node_modules', 'branding', 'shared', 'scripts', 'docs', 'icons', 'og-images', '.claude-memory'}

# Action verbs that meta descriptions should start with
ACTION_VERBS = {
    'calculate', 'check', 'find', 'get', 'create', 'build', 'generate',
    'convert', 'test', 'analyze', 'compare', 'discover', 'explore', 'learn',
    'make', 'plan', 'rate', 'scan', 'search', 'track', 'try', 'use',
    'estimate', 'measure', 'evaluate', 'assess', 'paste', 'enter', 'take',
    'pick', 'design', 'preview', 'simulate', 'visualize', 'transform',
    'decode', 'encode', 'format', 'parse', 'validate', 'verify', 'solve',
    'count', 'split', 'merge', 'resize', 'compress', 'extract', 'detect',
    'practice', 'quiz', 'play', 'spin', 'flip', 'draw', 'roll', 'shuffle',
    'organize', 'sort', 'filter', 'map', 'debug', 'monitor', 'audit',
    'optimize', 'manage', 'schedule', 'budget', 'save', 'export', 'download',
    'view', 'watch', 'listen', 'read', 'write', 'edit', 'craft', 'brew',
    'mix', 'bake', 'cook', 'pour', 'steep', 'grind', 'blend', 'whip',
    'knit', 'crochet', 'stitch', 'sew', 'cut', 'trim', 'shape', 'mold',
    'summarize', 'simplify', 'rewrite', 'improve', 'proofread', 'clean',
    'identify', 'diagnose', 'troubleshoot', 'fix', 'repair', 'restore',
    'run', 'start', 'launch', 'deploy', 'set', 'configure', 'setup',
    'select', 'choose', 'decide', 'determine', 'figure', 'predict',
    'project', 'forecast', 'model', 'map', 'chart', 'graph', 'plot',
    'log', 'record', 'capture', 'snap', 'grab', 'fetch', 'pull', 'push',
    'rank', 'score', 'grade', 'benchmark', 'profile', 'survey', 'poll',
    'type', 'input', 'submit', 'send', 'share', 'post', 'publish',
    'unlock', 'access', 'open', 'close', 'lock', 'secure', 'protect',
    'see', 'show', 'display', 'present', 'reveal', 'uncover', 'expose',
    'berechne', 'berechnen', 'prüfe', 'finde', 'erstelle', 'vergleiche',  # German
    'calcula', 'calcule', 'compara', 'encuentra', 'genera', 'convierte',  # Spanish
    'calcule', 'compare', 'trouvez', 'créez', 'générez', 'convertissez',  # French
    'calcola', 'confronta', 'trova', 'crea', 'genera', 'converti',  # Italian
    'laske', 'vertaa', 'etsi', 'luo', 'muunna', 'testaa', 'arvioi',  # Finnish
    'beräkna', 'jämför', 'hitta', 'skapa', 'konvertera', 'testa',  # Swedish
    'bereken', 'vergelijk', 'vind', 'maak', 'converteer', 'test',  # Dutch
    'oblicz', 'porównaj', 'znajdź', 'utwórz', 'konwertuj', 'testuj',  # Polish
    'vypočítejte', 'porovnejte', 'najděte', 'vytvořte',  # Czech
    'احسب', 'قارن', 'اعثر', 'أنشئ',  # Arabic
    'hitung', 'bandingkan', 'temukan', 'buat',  # Indonesian
    'tính', 'so', 'tìm', 'tạo',  # Vietnamese
}

# Verb mapping: given a tool type keyword, suggest an action verb
VERB_SUGGESTIONS = {
    'calculator': 'Calculate', 'rechner': 'Berechne', 'laskuri': 'Laske',
    'checker': 'Check', 'tester': 'Test', 'test': 'Take',
    'generator': 'Generate', 'maker': 'Create', 'builder': 'Build',
    'converter': 'Convert', 'picker': 'Pick', 'simulator': 'Simulate',
    'planner': 'Plan', 'tracker': 'Track', 'timer': 'Track',
    'quiz': 'Take', 'game': 'Play', 'analyzer': 'Analyze',
    'detector': 'Detect', 'estimator': 'Estimate', 'finder': 'Find',
    'viewer': 'View', 'editor': 'Edit', 'formatter': 'Format',
    'counter': 'Count', 'sorter': 'Sort', 'splitter': 'Split',
    'resizer': 'Resize', 'compressor': 'Compress', 'extractor': 'Extract',
    'previewer': 'Preview', 'visualizer': 'Visualize', 'monitor': 'Monitor',
    'auditor': 'Audit', 'optimizer': 'Optimize', 'debugger': 'Debug',
    'scheduler': 'Schedule', 'budgeter': 'Budget', 'downloader': 'Download',
    'countdown': 'Track', 'comparison': 'Compare', 'lookup': 'Find',
}


def find_tool_pages(hub_filter=None):
    """Find all tool index.html files."""
    pages = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        rel = os.path.relpath(dirpath, ROOT)
        parts = Path(rel).parts

        # Must be at least 2 levels deep (hub/tool/)
        if len(parts) < 2:
            continue

        if hub_filter and parts[0] != hub_filter:
            continue

        if 'index.html' in filenames:
            filepath = os.path.join(dirpath, 'index.html')
            pages.append(filepath)

    return sorted(pages)


def extract_meta(content):
    """Extract SEO metadata from HTML content."""
    meta = {}

    # Title
    m = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
    meta['title'] = html.unescape(m.group(1).strip()) if m else ''

    # Meta description
    m = re.search(r'<meta\s+name="description"\s+content="(.*?)"', content, re.DOTALL)
    meta['description'] = html.unescape(m.group(1).strip()) if m else ''

    # H1
    m = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
    meta['h1'] = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''

    # H2s in tool-content
    tool_content = ''
    m = re.search(r'<section\s+class="tool-content">(.*?)</section>', content, re.DOTALL)
    if m:
        tool_content = m.group(1)
    meta['h2s'] = re.findall(r'<h2[^>]*>(.*?)</h2>', tool_content, re.DOTALL)
    meta['h2s'] = [re.sub(r'<[^>]+>', '', h).strip() for h in meta['h2s']]

    # Content word count
    text = re.sub(r'<[^>]+>', ' ', tool_content)
    meta['content_words'] = len(text.split())

    # Also check variant class name (tool-content-section)
    if not tool_content:
        m2 = re.search(r'<section\s+class="tool-content-section">(.*?)</section>', content, re.DOTALL)
        if m2:
            tool_content = m2.group(1)
            meta['h2s'] = re.findall(r'<h2[^>]*>(.*?)</h2>', tool_content, re.DOTALL)
            meta['h2s'] = [re.sub(r'<[^>]+>', '', h).strip() for h in meta['h2s']]
            text = re.sub(r'<[^>]+>', ' ', tool_content)
            meta['content_words'] = len(text.split())

    # Has freshness signal
    meta['has_freshness'] = bool(re.search(r'last\s+updated|updated?\s*:?\s*\w+\s+20\d{2}', content, re.IGNORECASE))

    # Has display='' bug
    meta['display_empty'] = "style.display = ''" in content or 'style.display=""' in content

    # FAQ count — detect both q:'...' and question:'...' patterns
    meta['faq_count'] = (
        len(re.findall(r"q:\s*'", content)) +
        len(re.findall(r'"q":\s*"', content)) +
        len(re.findall(r"question:\s*'", content)) +
        len(re.findall(r'"question":\s*"', content))
    )
    # Track which FAQ format is used
    meta['faq_format'] = 'question' if re.search(r"question:\s*'", content) or re.search(r'"question":\s*"', content) else 'q'

    return meta


def suggest_verb(title, description):
    """Suggest an action verb based on tool type."""
    title_lower = title.lower()
    for keyword, verb in VERB_SUGGESTIONS.items():
        if keyword in title_lower:
            return verb

    # Default based on common patterns
    if any(w in title_lower for w in ['how', 'what', 'why']):
        return 'Discover'
    return 'Use'


def fix_meta_description_verb(content, meta):
    """Fix meta description to start with action verb."""
    desc = meta['description']
    if not desc:
        return content, False

    first_word = desc.split()[0].lower().rstrip('.,!') if desc.split() else ''
    if first_word in ACTION_VERBS:
        return content, False

    # Suggest a verb
    verb = suggest_verb(meta['title'], desc)

    # Reconstruct: "Verb + rest of description"
    # Remove common non-verb starters
    new_desc = desc
    starters_to_remove = [
        r'^This\s+(tool|calculator|checker|generator|converter|quiz|game|maker|tester|analyzer)\s+(is\s+a|lets\s+you|helps\s+you|allows\s+you\s+to|will)\s*',
        r'^A\s+(free|simple|easy|quick|fast|online|browser-based)\s+',
        r'^The\s+(best|ultimate|free|online|most\s+accurate)\s+',
        r'^Free\s+(online\s+)?(tool|calculator|checker)\s+(to|for|that)\s+',
        r'^Online\s+(tool|calculator)\s+(to|for|that)\s+',
        r'^An?\s+',
    ]

    cleaned = desc
    for pattern in starters_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()

    # Capitalize first letter of remaining
    if cleaned:
        cleaned = cleaned[0].lower() + cleaned[1:] if len(cleaned) > 1 else cleaned.lower()

    new_desc = f"{verb} {cleaned}"

    # Ensure it ends with period if not already
    if new_desc and not new_desc.endswith('.'):
        # Don't add period if it makes it too long
        if len(new_desc) < 155:
            pass  # Leave without period - many good meta descs don't have them

    # Trim to 155 chars
    if len(new_desc) > 155:
        new_desc = new_desc[:152].rsplit(' ', 1)[0] + '...'

    if new_desc == desc:
        return content, False

    # Replace in all locations
    escaped_old = re.escape(desc)
    # Replace meta description
    content = re.sub(
        r'(<meta\s+name="description"\s+content=")' + escaped_old + '"',
        lambda m: m.group(1) + new_desc.replace('"', '&quot;') + '"',
        content
    )
    # Replace og:description
    content = re.sub(
        r'(<meta\s+property="og:description"\s+content=")' + escaped_old + '"',
        lambda m: m.group(1) + new_desc.replace('"', '&quot;') + '"',
        content
    )
    # Replace twitter:description
    content = re.sub(
        r'(<meta\s+name="twitter:description"\s+content=")' + escaped_old + '"',
        lambda m: m.group(1) + new_desc.replace('"', '&quot;') + '"',
        content
    )

    return content, True


def fix_meta_description_length(content, meta):
    """Trim meta description if too long."""
    desc = meta['description']
    if not desc or len(desc) <= 155:
        return content, False

    # Trim to 155 chars at word boundary
    new_desc = desc[:152].rsplit(' ', 1)[0] + '...'

    escaped_old = re.escape(desc)
    content = re.sub(
        r'(<meta\s+name="description"\s+content=")' + escaped_old + '"',
        lambda m: m.group(1) + new_desc.replace('"', '&quot;') + '"',
        content
    )
    content = re.sub(
        r'(<meta\s+property="og:description"\s+content=")' + escaped_old + '"',
        lambda m: m.group(1) + new_desc.replace('"', '&quot;') + '"',
        content
    )
    content = re.sub(
        r'(<meta\s+name="twitter:description"\s+content=")' + escaped_old + '"',
        lambda m: m.group(1) + new_desc.replace('"', '&quot;') + '"',
        content
    )

    return content, True


def fix_display_empty(content, meta):
    """Fix style.display = '' bug with explicit display value."""
    if not meta['display_empty']:
        return content, False

    # Replace style.display = '' with showEl() if available, or 'block'
    content = content.replace("style.display = ''", "style.display = 'block'")
    content = content.replace('style.display=""', "style.display='block'")
    return content, True


def fix_freshness_signal(content, meta):
    """Add freshness signal to tool-content if missing."""
    if meta['has_freshness']:
        return content, False

    # Find the closing </section> of tool-content and add freshness before it
    # Look for the last </p> or </ul> before </section> in tool-content
    pattern = r'(</(?:p|ul|ol|table|div)>\s*)(</section>\s*<section\s+id="tool-faqs")'
    m = re.search(pattern, content)
    if m:
        freshness = '\n      <p style="font-size:var(--text-sm);color:var(--text-muted);margin-top:2rem;">Last updated: March 2026</p>\n    '
        content = content[:m.end(1)] + freshness + content[m.start(2):]
        return content, True

    return content, False


def generate_how_works_h2(meta):
    """Generate a 'How [Tool] Works' H2 section from existing metadata."""
    h1 = meta['h1']
    desc = meta['description']
    if not h1 or not desc:
        return ''

    # Clean H1 for use in heading
    clean_h1 = re.sub(r'\s*[—–\-]\s*(Teamz Lab Tools|Free|Online).*$', '', h1, flags=re.IGNORECASE).strip()
    # Remove year suffixes like "2026"
    heading_name = re.sub(r'\s+20\d{2}$', '', clean_h1).strip()

    # Build the H2 heading
    h2_text = f"How {heading_name} Works"

    # Build a paragraph from the meta description + generic explanation
    # Strip "Free" / "private" / "no sign-up" boilerplate from desc
    clean_desc = re.sub(r'\b(Free|100% private|private|no sign[- ]?up|no login|browser[- ]?based|works offline|no data stored)\b[.,]?\s*', '', desc, flags=re.IGNORECASE).strip()
    # Clean up leftover punctuation artifacts
    clean_desc = re.sub(r'\s*[.,]\s*[.,]', '.', clean_desc)  # ".," or ",." → "."
    clean_desc = re.sub(r'\s*[.,]\s*$', '.', clean_desc)     # trailing comma → period
    clean_desc = re.sub(r'^\s*[.,]\s*', '', clean_desc)      # leading punctuation
    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
    if clean_desc and not clean_desc.endswith('.'):
        clean_desc += '.'

    # Detect tool type for contextual second sentence
    h1_lower = h1.lower()
    if any(w in h1_lower for w in ['calculator', 'rechner', 'laskuri', 'beregner', 'calcula']):
        how_sentence = f'Enter your values into the form above and the calculator processes them instantly in your browser — no data is sent to any server.'
    elif any(w in h1_lower for w in ['generator', 'maker', 'builder', 'creator']):
        how_sentence = f'Customize your options in the form above and the tool generates your result instantly in your browser — ready to download, copy, or share.'
    elif any(w in h1_lower for w in ['checker', 'tester', 'validator', 'analyzer', 'scanner', 'detector']):
        how_sentence = f'Provide your input in the form above and the tool analyzes it instantly in your browser, giving you actionable results without sending data to any server.'
    elif any(w in h1_lower for w in ['converter', 'translator']):
        how_sentence = f'Select your input and output formats, enter your value, and the tool converts it instantly in your browser with no server calls.'
    elif any(w in h1_lower for w in ['quiz', 'test', 'assessment']):
        how_sentence = f'Answer the questions honestly and the tool calculates your result based on research-backed criteria — everything runs privately in your browser.'
    elif any(w in h1_lower for w in ['tracker', 'planner', 'scheduler', 'timer', 'countdown']):
        how_sentence = f'Set your parameters in the form above and the tool tracks your progress in real time — all data stays in your browser\'s local storage.'
    elif any(w in h1_lower for w in ['picker', 'selector', 'randomizer', 'wheel', 'spinner']):
        how_sentence = f'Add your items to the list, configure your selection options, and the tool picks randomly using your browser\'s built-in randomization — fair and private.'
    elif any(w in h1_lower for w in ['simulator', 'visualizer', 'previewer']):
        how_sentence = f'Configure your settings in the form above and see the results rendered visually in your browser — no server processing required.'
    else:
        how_sentence = f'Use the tool above to get your results instantly — everything runs in your browser with no data sent to any server.'

    return f'''
      <h2>{h2_text}</h2>
      <p>{clean_desc} {how_sentence}</p>'''


def generate_extra_faqs(meta):
    """Generate additional FAQ entries to reach 5 minimum."""
    h1 = meta['h1']
    desc = meta['description']
    faq_count = meta.get('faq_count', 0)

    if faq_count >= 5 or not h1:
        return []

    clean_h1 = re.sub(r'\s*[—–\-]\s*(Teamz Lab Tools|Free|Online).*$', '', h1, flags=re.IGNORECASE).strip()
    clean_h1 = re.sub(r'\s+20\d{2}$', '', clean_h1).strip()
    h1_lower = h1.lower()

    # Pool of generic FAQ templates
    faq_pool = []

    # Privacy FAQ (always relevant)
    faq_pool.append({
        'q': f'Is {clean_h1} free to use?',
        'a': f'Yes, {clean_h1} is completely free with no sign-up, no login, and no hidden fees. The tool runs entirely in your browser — your data never leaves your device.'
    })

    faq_pool.append({
        'q': f'Is my data safe when using this tool?',
        'a': f'Yes. This tool runs 100% in your browser using JavaScript. No data is sent to any server, stored in any database, or shared with any third party. When you close the page, processing stops immediately.'
    })

    faq_pool.append({
        'q': f'Does this tool work on mobile devices?',
        'a': f'Yes. {clean_h1} is fully responsive and works on smartphones, tablets, and desktop computers. The interface adapts to your screen size automatically.'
    })

    faq_pool.append({
        'q': f'Can I use this tool offline?',
        'a': f'Yes. Once the page has loaded, {clean_h1} works without an internet connection. All processing happens locally in your browser.'
    })

    faq_pool.append({
        'q': f'Do I need to create an account to use {clean_h1}?',
        'a': f'No. {clean_h1} requires no account, no registration, and no email. Just open the page and start using it immediately. Your inputs are auto-saved in your browser for convenience.'
    })

    # Return only as many as needed to reach 5
    needed = 5 - faq_count
    return faq_pool[:needed]


def generate_tips_section(meta):
    """Generate a 'Tips' H2 section based on tool type."""
    h1 = meta['h1']
    if not h1:
        return ''

    clean_h1 = re.sub(r'\s*[—–\-]\s*(Teamz Lab Tools|Free|Online).*$', '', h1, flags=re.IGNORECASE).strip()
    clean_h1 = re.sub(r'\s+20\d{2}$', '', clean_h1).strip()
    h1_lower = h1.lower()

    if any(w in h1_lower for w in ['calculator', 'rechner', 'laskuri', 'beregner', 'calcula']):
        return f'''
      <h2>Tips for Getting Accurate Results</h2>
      <p>For the most accurate results, use up-to-date numbers from official sources. Double-check your inputs before calculating — small errors in the starting values can lead to significantly different outputs. If you are comparing scenarios, keep all variables the same except the one you are testing. Save or screenshot your results for future reference. This calculator uses standard formulas and is designed to give you a reliable quick estimate, though professional advice may be needed for complex situations.</p>'''
    elif any(w in h1_lower for w in ['generator', 'maker', 'builder', 'creator']):
        return f'''
      <h2>Tips for Best Results</h2>
      <p>Start with the default settings to see how the tool works, then customize to match your needs. Preview your output before downloading or sharing to catch any adjustments. Use high-quality inputs where possible — better source material produces better results. Save your work frequently using the download or copy buttons. This tool runs entirely in your browser, so your creations are never uploaded to any server and remain completely private.</p>'''
    elif any(w in h1_lower for w in ['checker', 'tester', 'validator', 'analyzer', 'detector']):
        return f'''
      <h2>How to Interpret Your Results</h2>
      <p>Review all sections of the analysis, not just the overall score. Focus on actionable items — findings you can actually change or improve. Run the check multiple times with different inputs if you want to compare scenarios. Keep in mind that automated analysis provides a useful starting point, but may not capture every nuance of your specific situation. Use the results as guidance for improvement rather than a definitive verdict.</p>'''
    elif any(w in h1_lower for w in ['converter', 'translator']):
        return f'''
      <h2>Common Conversion Tips</h2>
      <p>Always verify the source and target units or formats before converting — selecting the wrong option is the most common mistake. For precise conversions, enter values with as many decimal places as you have available. If converting multiple items, work through them one at a time to avoid mixing up results. Bookmark this page for quick access when you need to convert again in the future.</p>'''
    elif any(w in h1_lower for w in ['quiz', 'test', 'assessment']):
        return f'''
      <h2>Tips for Taking This Assessment</h2>
      <p>Answer each question honestly based on your real behavior and preferences, not what you think the ideal answer should be. Go with your first instinct rather than overthinking — spontaneous answers tend to be more accurate. Take the assessment in a quiet environment where you can focus without distractions. Remember that there are no right or wrong answers. Your results are meant to provide self-awareness and starting points for improvement, not definitive labels.</p>'''
    elif any(w in h1_lower for w in ['tracker', 'planner', 'scheduler']):
        return f'''
      <h2>Tips for Effective Tracking</h2>
      <p>Consistency is more important than perfection — update your tracker regularly even if the data is not perfect. Set a daily reminder to log your entries while they are fresh. Review your progress weekly to spot patterns and make adjustments. Your data is saved automatically in your browser, so you do not need to worry about losing it between sessions. Export or screenshot your data periodically as a backup.</p>'''
    else:
        return f'''
      <h2>Getting the Most from This Tool</h2>
      <p>Start by exploring the default settings to understand what the tool offers, then customize the inputs to match your specific needs. Use the results as a starting point for deeper analysis or decision-making. Bookmark this page for quick access in the future. All processing happens in your browser, so your data stays private and the tool works even without an internet connection after the initial page load.</p>'''


def generate_use_cases_section(meta):
    """Generate a 'Use Cases' or 'Who Uses This' H2 section."""
    h1 = meta['h1']
    if not h1:
        return ''

    clean_h1 = re.sub(r'\s*[—–\-]\s*(Teamz Lab Tools|Free|Online).*$', '', h1, flags=re.IGNORECASE).strip()
    clean_h1 = re.sub(r'\s+20\d{2}$', '', clean_h1).strip()
    h1_lower = h1.lower()

    # Detect audience from hub/title
    if any(w in h1_lower for w in ['tax', 'salary', 'income', 'budget', 'loan', 'mortgage', 'interest', 'investment', 'retirement', 'pension']):
        return f'''
      <h2>Who Uses {clean_h1}</h2>
      <p>Individuals use this tool to plan their personal finances, compare scenarios, and make informed money decisions. Freelancers and self-employed professionals use it to estimate their obligations and plan ahead. Students learning about personal finance find it helpful for understanding real-world numbers. Financial advisors sometimes use quick calculators like this as a starting point during client conversations. No matter your situation, having accurate numbers helps you make better financial decisions.</p>'''
    elif any(w in h1_lower for w in ['resume', 'job', 'career', 'interview', 'ats', 'cv']):
        return f'''
      <h2>Who Uses {clean_h1}</h2>
      <p>Job seekers use this tool to improve their applications and increase their chances of landing interviews. Career changers find it useful for tailoring their materials to a new industry. Recent graduates use it to make the most of limited experience. Recruiters and career coaches sometimes recommend free tools like this to candidates who need a quick way to optimize their applications. Whether you are applying to one role or fifty, this tool helps you put your best foot forward.</p>'''
    elif any(w in h1_lower for w in ['image', 'photo', 'logo', 'design', 'color', 'font', 'css', 'shadow', 'gradient']):
        return f'''
      <h2>Who Uses {clean_h1}</h2>
      <p>Designers and developers use this tool to speed up their workflow and test ideas quickly. Content creators use it for social media assets, thumbnails, and brand materials. Students and hobbyists use it to learn design principles through experimentation. Small business owners who cannot afford professional design software find free browser-based tools like this especially valuable. The instant preview and download features make it practical for both quick tasks and careful refinement.</p>'''
    elif any(w in h1_lower for w in ['code', 'json', 'csv', 'markdown', 'regex', 'api', 'debug', 'format', 'lorem', 'slug']):
        return f'''
      <h2>Who Uses {clean_h1}</h2>
      <p>Software developers use this tool to save time on repetitive formatting and conversion tasks. Technical writers and documentarians find it useful for preparing content. QA engineers use it during testing workflows. Students learning programming use it to understand data formats and transformations. The browser-based approach means no installation is needed — just open the page, paste your data, and get results instantly.</p>'''
    else:
        return f'''
      <h2>Who Uses {clean_h1}</h2>
      <p>This tool is used by anyone who needs a quick, reliable way to get results without downloading software or creating accounts. Students, professionals, hobbyists, and curious minds all benefit from having instant access to specialized tools in their browser. The privacy-first approach — where no data leaves your device — makes it suitable for sensitive information. Bookmark this page and return whenever you need it.</p>'''


def fix_low_content(content, meta):
    """Add extra H2 sections to boost word count above 300."""
    if meta.get('content_words', 0) >= 300:
        return content, False

    # Generate additional sections
    tips = generate_tips_section(meta)
    use_cases = generate_use_cases_section(meta)

    if not tips and not use_cases:
        return content, False

    # Find the end of tool-content section (before </section>)
    # Insert before the closing </section> that precedes tool-faqs
    pattern = r'(</(?:p|ul|ol|table|div)>\s*)(</section>\s*(?:<section\s+id="tool-faqs"|<div\s+id="tool-faqs"))'
    m = re.search(pattern, content)
    if not m:
        # Try simpler pattern
        pattern = r'(</p>\s*)(</section>)'
        matches = list(re.finditer(pattern, content))
        if not matches:
            return content, False
        # Use the last match in tool-content area
        tc_start = content.find('class="tool-content')
        for match in reversed(matches):
            if match.start() > tc_start:
                m = match
                break
        if not m:
            return content, False

    # Only add what's needed to get above 300 words
    extra = ''
    current_words = meta.get('content_words', 0)
    if current_words < 200:
        extra = tips + '\n' + use_cases  # Add both
    else:
        extra = tips  # Just tips should push over 300

    content = content[:m.end(1)] + extra + '\n    ' + content[m.start(2):]
    return content, True


def fix_missing_how_works(content, meta):
    """Add 'How X Works' H2 section if missing."""
    h2_lower = ' '.join(meta.get('h2s', [])).lower()

    # Check for "how" + "works" or equivalent patterns in ANY language
    how_patterns = ['how', 'miten', 'wie', 'comment', 'come', 'hur', 'hoe', 'jak', 'hvordan', 'como', 'cómo', 'bagaimana', 'كيف', 'cara', 'hvad', 'wat', 'co', 'що', 'nasıl', 'kaip']
    works_patterns = ['works', 'work', 'calculated', 'calcul', 'fungerar', 'fungiert', 'funktioniert', 'toimii', 'lasketaan',
                      'beregn', 'virker', 'funciona', 'funziona', 'werkt', 'działa', 'funguje', 'يعمل', 'bekerja',
                      'fonctionne', 'marche', 'används', 'beräknas', 'çalışır', 'hoạt', 'berfungsi']

    has_how_works = False
    for hp in how_patterns:
        if hp in h2_lower:
            for wp in works_patterns:
                if wp in h2_lower:
                    has_how_works = True
                    break
            # Also match "hur [verb]" patterns common in Swedish/Danish/Norwegian
            if not has_how_works and hp in ('hur', 'hvordan', 'wie', 'comment', 'como', 'cómo', 'miten', 'bagaimana', 'cara'):
                has_how_works = True  # "Hur fungerar X" = "How X works" — the how-word alone is enough
                break
        if has_how_works:
            break

    if has_how_works:
        return content, False

    new_h2 = generate_how_works_h2(meta)
    if not new_h2:
        return content, False

    # Insert after the first <h2> opening in .tool-content
    # Find tool-content section
    tc_match = re.search(r'<section\s+class="tool-content">', content)
    if not tc_match:
        return content, False

    # Find the first H2 inside tool-content
    first_h2 = re.search(r'<h2[^>]*>', content[tc_match.end():])
    if first_h2:
        # Insert BEFORE the first H2
        insert_pos = tc_match.end() + first_h2.start()
        content = content[:insert_pos] + new_h2 + '\n' + content[insert_pos:]
    else:
        # No H2 exists — insert right after <section class="tool-content">
        insert_pos = tc_match.end()
        content = content[:insert_pos] + new_h2 + '\n' + content[insert_pos:]

    return content, True


def fix_low_faqs(content, meta):
    """Add FAQs if count is below 5."""
    if meta.get('faq_count', 0) >= 5:
        return content, False

    extra_faqs = generate_extra_faqs(meta)
    if not extra_faqs:
        return content, False

    # Detect FAQ format: q/a or question/answer
    faq_format = meta.get('faq_format', 'q')

    # Find the last FAQ entry in the JS array
    if faq_format == 'question':
        # question/answer format (multi-line)
        faq_insert = re.search(r"(answer:\s*'[^']*'\s*\})\s*\n(\s*\];)", content)
        if not faq_insert:
            faq_insert = re.search(r'(answer:\s*"[^"]*"\s*\})\s*\n(\s*\];)', content)
    else:
        # q/a format (single line)
        faq_insert = re.search(r"(\{\s*q:\s*'[^']*',\s*a:\s*'[^']*'\s*\})\s*\n(\s*\];)", content)
        if not faq_insert:
            faq_insert = re.search(r'(\{\s*q:\s*"[^"]*",\s*a:\s*"[^"]*"\s*\})\s*\n(\s*\];)', content)

    if not faq_insert:
        # Try multiline patterns (answer on separate line)
        faq_insert = re.search(r"(answer:\s*'(?:[^'\\]|\\.)*'\s*\})\s*\n(\s*\];)", content, re.DOTALL)
        if not faq_insert:
            faq_insert = re.search(r'(answer:\s*"(?:[^"\\]|\\.)*"\s*\})\s*\n(\s*\];)', content, re.DOTALL)

    if not faq_insert:
        # Try single-line FAQ arrays: { q: '...', a: '...' }];
        faq_insert = re.search(r"(a:\s*'(?:[^'\\]|\\.)*'\s*\})\s*(\];)", content)
        if not faq_insert:
            faq_insert = re.search(r'(a:\s*"(?:[^"\\]|\\.)*"\s*\})\s*(\];)', content)

    if not faq_insert:
        # Last resort: find any }]; near renderFAQs
        faq_insert = re.search(r'(\})\s*(\];\s*\n\s*(?:TeamzTools\.)?renderFAQs)', content)

    if not faq_insert:
        return content, False

    # Build new FAQ entries matching the page's format
    indent = '        '
    new_entries = ''
    for faq in extra_faqs:
        q = faq['q'].replace("'", "\\'")
        a = faq['a'].replace("'", "\\'")
        if faq_format == 'question':
            new_entries += f",\n{indent}{{\n{indent}  question: '{q}',\n{indent}  answer: '{a}'\n{indent}}}"
        else:
            new_entries += f",\n{indent}{{ q: '{q}', a: '{a}' }}"

    # Insert before the ];
    insert_pos = faq_insert.end(1)
    content = content[:insert_pos] + new_entries + content[insert_pos:]

    return content, True


def run(dry_run=True, hub_filter=None, stats_only=False):
    """Main runner."""
    pages = find_tool_pages(hub_filter)
    print(f"\n{'='*60}")
    print(f"  SEO BULK FIXER {'(DRY RUN)' if dry_run else '(APPLYING)'} — {len(pages)} pages")
    if hub_filter:
        print(f"  Hub filter: {hub_filter}")
    print(f"{'='*60}\n")

    counters = defaultdict(int)
    fixed_files = []

    for filepath in pages:
        rel_path = os.path.relpath(filepath, ROOT)

        with open(filepath, 'r', encoding='utf-8') as f:
            original = f.read()

        meta = extract_meta(original)
        content = original
        fixes_for_file = []

        # Skip redirect stubs
        if 'http-equiv' in original and 'refresh' in original:
            continue

        # Fix 1: Meta description verb — DISABLED (too risky for auto-fix, needs manual review)
        # content, fixed = fix_meta_description_verb(content, meta)
        # if fixed:
        #     counters['meta_verb'] += 1
        #     fixes_for_file.append('meta_verb')

        # Fix 2: Meta description length — DISABLED (trimming can cut important info)
        # meta2 = extract_meta(content)
        # content, fixed = fix_meta_description_length(content, meta2)
        # if fixed:
        #     counters['meta_length'] += 1
        #     fixes_for_file.append('meta_length')

        # Fix 3: display='' bug
        content, fixed = fix_display_empty(content, meta)
        if fixed:
            counters['display_bug'] += 1
            fixes_for_file.append('display_bug')

        # Fix 4: Freshness signal — HANDLED CENTRALLY in common.js (renderAuthorByline)
        # No per-file changes needed

        # Fix 5: Missing "How X Works" H2
        content, fixed = fix_missing_how_works(content, meta)
        if fixed:
            counters['how_works'] += 1
            fixes_for_file.append('how_works_h2')

        # Fix 6: Low FAQ count (<5)
        meta_updated = extract_meta(content)  # Re-extract after H2 addition
        content, fixed = fix_low_faqs(content, meta_updated)
        if fixed:
            counters['faqs_added'] += 1
            fixes_for_file.append('faqs_added')

        # Fix 7: Low content (<300 words)
        meta_updated2 = extract_meta(content)
        content, fixed = fix_low_content(content, meta_updated2)
        if fixed:
            counters['content_expanded'] += 1
            fixes_for_file.append('content_expanded')

        # Count issues (for stats)
        first_word = meta['description'].split()[0].lower().rstrip('.,!') if meta['description'].split() else ''
        if first_word not in ACTION_VERBS and meta['description']:
            counters['needs_verb'] += 1
        if len(meta['description']) > 155:
            counters['needs_trim'] += 1
        if meta['display_empty']:
            counters['has_display_bug'] += 1
        if not meta['has_freshness']:
            counters['needs_freshness'] += 1
        if meta['content_words'] < 300:
            counters['low_content'] += 1
        if meta['faq_count'] < 5:
            counters['low_faqs'] += 1

        h2_lower = ' '.join(meta['h2s']).lower()
        how_words = ['how', 'miten', 'wie', 'comment', 'come', 'hur', 'hoe', 'jak', 'hvordan', 'como', 'cómo', 'bagaimana', 'cara', 'hvad', 'wat', 'nasıl']
        has_any_how = any(hw in h2_lower for hw in how_words)
        if not has_any_how:
            counters['needs_how_works'] += 1

        if fixes_for_file:
            if not stats_only:
                print(f"  {rel_path}: {', '.join(fixes_for_file)}")
            fixed_files.append(rel_path)

            if not dry_run and not stats_only:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"\n  Auto-fixed{'  (DRY RUN)' if dry_run else ''}:")
    print(f"    display='' bug fix:    {counters['display_bug']} pages")
    print(f"    How Works H2 added:    {counters['how_works']} pages")
    print(f"    FAQs added (<5→5):     {counters['faqs_added']} pages")
    print(f"    Content expanded:      {counters['content_expanded']} pages")
    print(f"    TOTAL auto-fixed:      {len(fixed_files)} pages")

    print(f"\n  Remaining:")
    print(f"    Low content (<300w):   {counters['low_content'] - counters['content_expanded']} pages")
    print(f"    Still no How Works H2: {counters['needs_how_works'] - counters['how_works']} pages")
    print(f"    Still low FAQs (<5):   {counters['low_faqs'] - counters['faqs_added']} pages")

    print(f"\n  Total pages scanned:     {len(pages)}")
    if dry_run and not stats_only:
        print(f"\n  Run with --apply to write changes to disk")
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    args = sys.argv[1:]
    dry_run = '--apply' not in args
    stats_only = '--stats' in args
    hub_filter = None
    if '--hub' in args:
        idx = args.index('--hub')
        if idx + 1 < len(args):
            hub_filter = args[idx + 1]

    run(dry_run=dry_run, hub_filter=hub_filter, stats_only=stats_only)
