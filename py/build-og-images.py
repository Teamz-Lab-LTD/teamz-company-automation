#!/usr/bin/env python3
"""
Generate hub-level OG images for social sharing.
Creates 1200x630 branded PNG images per hub category.
Uses Pillow (PIL) — install with: pip3 install Pillow

Usage:
    python3 build-og-images.py          # Generate all hub OG images
    python3 build-og-images.py health   # Generate for one hub
"""

import os
import sys
import glob
import re
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OG_DIR = os.path.join(BASE_DIR, 'og-images')

# Design tokens (matching the site's design system)
BG_DARK = (18, 21, 26)         # #12151A
ACCENT = (217, 254, 6)         # #D9FE06 (neon)
TEXT_WHITE = (245, 245, 245)
TEXT_MUTED = (160, 165, 175)

# Hub display names and emoji/icon indicators
HUB_META = {
    '3d': ('3D Tools', '3D model viewers, STL tools'),
    'ae': ('UAE Tools', 'Calculators for the United Arab Emirates'),
    'ai': ('AI Tools', 'AI-powered utilities and analyzers'),
    'amazon': ('Amazon Seller Tools', 'FBA calculators, listing tools, and more'),
    'apple': ('Apple Tools', 'iPhone, iPad, Mac utilities'),
    'au': ('Australia Tools', 'Tax, super, and HECS calculators'),
    'auto': ('Auto & Vehicle', 'Fuel, EV, and vehicle calculators'),
    'ca': ('Canada Tools', 'RRSP, TFSA, and CRA calculators'),
    'career': ('Career Tools', 'Salary, resume, and job calculators'),
    'compliance': ('Compliance Tools', 'Regulatory checkers and auditors'),
    'creator': ('Creator Economy', 'Sponsorship, CPM, and income tools'),
    'cricket': ('Cricket Tools', 'DLS, stats, and match calculators'),
    'crypto': ('Crypto Tools', 'Mining, staking, and fee calculators'),
    'de': ('Germany Tools', 'Steuerrechner und Finanztools'),
    'design': ('Design Tools', 'Color, layout, and image utilities'),
    'dev': ('Developer Tools', 'JSON, regex, git, and coding utilities'),
    'diagnostic': ('Diagnostic Tools', 'Speed tests, device info, privacy checks'),
    'eg': ('Egypt Tools', 'Egyptian tax and finance calculators'),
    'eldercare': ('Eldercare Tools', 'Health tracking for seniors'),
    'eu': ('EU Tools', 'CBAM, energy, and EU regulation tools'),
    'evergreen': ('Finance Tools', 'Timeless calculators for personal finance'),
    'fi': ('Finland Tools', 'Finnish tax and utility calculators'),
    'fitness': ('Fitness Tools', 'Workout, macro, and body calculators'),
    'football': ('Football Tools', 'UCL stats, predictions, and quizzes'),
    'fr': ('France Tools', 'Simulateurs et calculateurs français'),
    'freelance': ('Freelance Tools', 'Invoice, rate, and pricing calculators'),
    'gh': ('Ghana Tools', 'GhanaPostGPS and local calculators'),
    'grooming': ('Grooming Tools', 'Skincare, haircare, and style guides'),
    'health': ('Health Tools', 'BMI, sleep, stress, and wellness tools'),
    'housing': ('Housing Tools', 'Rent, mortgage, and appliance calculators'),
    'id': ('Indonesia Tools', 'Coretax and Indonesian calculators'),
    'in': ('India Tools', 'Income tax, HRA, and gratuity calculators'),
    'jp': ('Japan Tools', 'Japanese tax and finance calculators'),
    'ke': ('Kenya Tools', 'PAYE, NHIF, and Kenyan payroll tools'),
    'kids': ('Kids & Parenting', 'Reading, screen time, and learning tools'),
    'ma': ('Morocco Tools', 'Moroccan finance calculators'),
    'math': ('Math Tools', 'Calculators, plotters, and converters'),
    'physics': ('Physics Calculators', 'Velocity, force, energy, and motion tools'),
    'mobile': ('Mobile Tools', 'Screen sizes, data, and device tools'),
    'music': ('Music Tools', 'BPM, tuning, and music theory tools'),
    'my': ('Malaysia Tools', 'EPF, PCB, and Malaysian tools'),
    'ng': ('Nigeria Tools', 'PAYE, pension, and Nigerian tax tools'),
    'nl': ('Netherlands Tools', 'Dutch tax and benefit calculators'),
    'no': ('Norway Tools', 'Norwegian tax and housing tools'),
    'outdoor': ('Outdoor Tools', 'Hiking, knots, and adventure utilities'),
    'ペット': ('Pet Tools', 'Pet age, health, and care calculators'),
    'pets': ('Pet Tools', 'Dog age, cat age, and pet health'),
    'ph': ('Philippines Tools', 'SSS, PhilHealth, and Pag-IBIG tools'),
    'productivity': ('Productivity', 'Time management and focus tools'),
    'ramadan': ('Ramadan Tools', 'Iftar, suhoor, and fasting utilities'),
    'restaurant': ('Food & Cooking', 'Recipe, baking, and kitchen tools'),
    'sa': ('Saudi Arabia Tools', 'SaaS and Saudi finance calculators'),
    'se': ('Sweden Tools', 'Swedish tax and benefit calculators'),
    'sg': ('Singapore Tools', 'CPF and Singaporean finance tools'),
    'shopping': ('Shopping Tools', 'Discount, price, and deal calculators'),
    'software': ('Software Tools', 'App cost, API, and dev estimators'),
    'student': ('Student Tools', 'Attendance, GPA, and exam tools'),
    'text': ('Text Tools', 'Word count, case convert, and formatters'),
    'tools': ('Utility Tools', 'QR codes, converters, and generators'),
    'travel': ('Travel Tools', 'Currency, packing, and trip planners'),
    'uidesign': ('UI Design Tools', 'CSS generators and design utilities'),
    'uk': ('UK Tools', 'Tax, NI, and British finance calculators'),
    'us': ('US Tools', 'American tax and savings calculators'),
    'video': ('Video Tools', 'Thumbnail, subtitle, and video utilities'),
    'vn': ('Vietnam Tools', 'Vietnamese social insurance tools'),
    'weather': ('Weather Tools', 'Clothing, UV, and weather utilities'),
    'work': ('Work & Payroll', 'Salary, overtime, and payroll tools'),
    'za': ('South Africa Tools', 'Two-pot, SARS, and SA finance tools'),
}


def get_font(size):
    """Try to load a good system font, fall back to default."""
    font_paths = [
        '/System/Library/Fonts/SFNSMono.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
        '/System/Library/Fonts/SFNSDisplay.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_og_image(hub, title, subtitle, output_path):
    """Generate a single branded OG image (1200x630)."""
    img = Image.new('RGB', (1200, 630), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Accent stripe at top
    draw.rectangle([(0, 0), (1200, 6)], fill=ACCENT)

    # Brand name
    font_brand = get_font(22)
    draw.text((60, 40), 'TEAMZ LAB TOOLS', fill=ACCENT, font=font_brand)

    # Hub indicator (small pill)
    font_hub = get_font(18)
    hub_text = '/' + hub + '/'
    draw.text((60, 75), hub_text, fill=TEXT_MUTED, font=font_hub)

    # Main title
    font_title = get_font(52)
    # Word wrap title
    words = title.split()
    lines = []
    current = ''
    for w in words:
        test = (current + ' ' + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font_title)
        if bbox[2] > 1080:  # max width
            lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)

    y = 160
    for line in lines[:3]:  # max 3 lines
        draw.text((60, y), line, fill=TEXT_WHITE, font=font_title)
        y += 68

    # Subtitle
    font_sub = get_font(24)
    draw.text((60, y + 30), subtitle, fill=TEXT_MUTED, font=font_sub)

    # Bottom bar
    draw.rectangle([(0, 590), (1200, 630)], fill=(25, 28, 35))
    font_url = get_font(18)
    draw.text((60, 598), 'tool.teamzlab.com', fill=ACCENT, font=font_url)
    draw.text((900, 598), 'Free & Private', fill=TEXT_MUTED, font=font_url)

    # Grid dots (decorative)
    for x in range(900, 1160, 30):
        for yy in range(160, 400, 30):
            opacity = 40 if (x + yy) % 60 == 0 else 20
            draw.ellipse([(x, yy), (x+4, yy+4)], fill=(217, 254, 6, opacity))

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'PNG', optimize=True)
    return output_path


def count_tools_in_hub(hub):
    """Count tool pages in a hub directory."""
    pattern = os.path.join(BASE_DIR, hub, '*', 'index.html')
    return len(glob.glob(pattern))


def main():
    os.makedirs(OG_DIR, exist_ok=True)

    # Determine which hubs to generate for
    target_hubs = sys.argv[1:] if len(sys.argv) > 1 else None

    # Find all hubs
    hubs = set()
    for filepath in glob.glob(os.path.join(BASE_DIR, '*', '*', 'index.html')):
        rel = os.path.relpath(filepath, BASE_DIR)
        hub = rel.split(os.sep)[0]
        if hub in {'shared', 'branding', 'docs', '.git', 'icons', 'og-images', 'about', 'contact', 'privacy', 'terms'}:
            continue
        hubs.add(hub)

    if target_hubs:
        hubs = {h for h in hubs if h in target_hubs}

    print(f"Generating OG images for {len(hubs)} hubs...")

    generated = 0
    for hub in sorted(hubs):
        meta = HUB_META.get(hub, (hub.title() + ' Tools', 'Free browser-based tools'))
        title, subtitle = meta
        tool_count = count_tools_in_hub(hub)
        subtitle = f"{tool_count} free tools — {subtitle}"

        output = os.path.join(OG_DIR, f'{hub}.png')
        generate_og_image(hub, title, subtitle, output)
        generated += 1

    print(f"Generated {generated} OG images in /og-images/")

    # Now update all tool pages to reference their hub's OG image
    if not target_hubs:
        print("Updating og:image tags in all tool pages...")
        updated = 0
        for filepath in glob.glob(os.path.join(BASE_DIR, '*', '*', 'index.html')):
            rel = os.path.relpath(filepath, BASE_DIR)
            hub = rel.split(os.sep)[0]
            if hub in {'shared', 'branding', 'docs', '.git', 'icons', 'og-images', 'about', 'contact', 'privacy', 'terms'}:
                continue

            og_image_url = f'https://tool.teamzlab.com/og-images/{hub}.png'
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Check if it already has a custom (non-default) OG image
                og_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]*)"', content)
                if og_match:
                    current = og_match.group(1)
                    if 'og-default' in current or not current.strip():
                        # Replace default with hub-specific
                        content = content.replace(
                            f'content="{current}"',
                            f'content="{og_image_url}"',
                            1
                        )
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        updated += 1
                else:
                    # No og:image at all — inject after og:description or og:title
                    og_tag = f'  <meta property="og:image" content="{og_image_url}">\n'
                    insertion_points = [
                        (r'(<meta\s+property="og:description"[^>]*>)', r'\1\n' + og_tag.strip()),
                        (r'(<meta\s+property="og:title"[^>]*>)', r'\1\n' + og_tag.strip()),
                    ]
                    for pattern, replacement in insertion_points:
                        new_content = re.sub(pattern, replacement, content, count=1)
                        if new_content != content:
                            content = new_content
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(content)
                            updated += 1
                            break

            except Exception as e:
                print(f"  Error updating {rel}: {e}")

        print(f"Updated {updated} tool pages with hub-specific OG images")


if __name__ == '__main__':
    main()
