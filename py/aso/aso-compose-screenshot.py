#!/usr/bin/env python3
"""aso-compose-screenshot.py — shared App Store / Play Store screenshot composer.

Wraps real Apple device frame (from fastlane frameit) + Poppins font around a
raw simulator/emulator screenshot, adds bold hero + subtitle text overlay on a
solid color background.

Zero API cost, zero AI. Requires only Pillow.

Prerequisites (one-time):
  pip3 install Pillow
  fastlane frameit download_frames                     # Apple device PNGs
  # Poppins fonts in ~/Library/Fonts/                  # Google Fonts free

Single-shot usage:
  python3 aso-compose-screenshot.py \\
    --raw screenshots/raw/01-source.png \\
    --hero "BATTERY HEALTH" \\
    --subtitle "IN WATTS" "NOT JUST %" \\
    --output screenshots/composed/01-battery-health.jpg \\
    [--bg "#D9FE06"] [--text-color "#000000"] \\
    [--device iphone-6.7]

For batch generation across many shots, use aso-generate-batch.py with a
project-specific presets JSON file.

Lessons baked in (do not strip these — each was a real bug we burned time on):
  1. Source aspect must match iPhone screen aspect exactly — center-crop before
     resize, otherwise the BG bleeds through at corners as 1-2px wedges.
  2. Frame PNG alpha has anti-aliased rounded corners — those leak BG through
     transparency. Fix: dilate the frame alpha by ~14px and fill BLACK underneath
     the frame.
  2b. The dilate+underfill in #2 hides BG leak at the OUTER bezel curve, but
      the INNER screen rounded corners stay visible as 4 white wedges if the
      app is pasted as a square rect. Fix: paste the app through a rounded-
      rect mask whose radius matches the frame's screen aperture (~7.2% of
      screen width on iPhone 16 Pro Max).
  3. Android source has status bar + nav bar that look wrong inside an iPhone
     frame. Crop top ~3.2% + bottom ~4.8% before further processing.
  4. Hero font must auto-fit to ≤88% canvas width or long words overflow.
  5. Subtitle font also auto-fits per line.
  6. Spacing: HERO_TO_SUB_GAP ≥ 110, SUB_LINE_GAP ≥ 55 reads as "premium"; tighter
     spacing looks cramped.
  7. Do NOT send the composed image through AI image-edit ("polish") — the AI
     re-renders the phone frame at slightly different proportions which exposes
     BG at the corners AGAIN. Compose is the final step.
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("Error: Pillow is required. Install with: pip3 install Pillow", file=sys.stderr)
    sys.exit(1)


# === DEVICE SPECS (App Store + Play Store canonical portrait sizes) ===
DEVICES = {
    "iphone-6.7":     {"width": 1290, "height": 2796},
    "iphone-6.5":     {"width": 1284, "height": 2778},
    "iphone-5.5":     {"width": 1242, "height": 2208},
    "ipad-12.9":      {"width": 2048, "height": 2732},
    "ipad-11":        {"width": 1668, "height": 2388},
    "play-phone":     {"width": 1080, "height": 1920},
    "play-tablet-7":  {"width": 1200, "height": 1920},
    "play-tablet-10": {"width": 1600, "height": 2560},
}

# Phone-shape width as a fraction of canvas width. Tablets get a smaller
# ratio so the phone-shape silhouette fits inside the wider tablet canvas
# without clipping the bottom (phone aspect ≈ 0.5 means a phone at 0.80 of
# 2048px-wide iPad would be 3342px tall — taller than the 2732px canvas).
# Override via "phone_ratio" key in the preset JSON when needed.
DEVICE_PHONE_RATIO = {
    "iphone-6.7":     0.80,
    "iphone-6.5":     0.80,
    "iphone-5.5":     0.80,
    "ipad-12.9":      0.52,
    "ipad-11":        0.54,
    "play-phone":     0.80,
    "play-tablet-7":  0.52,
    "play-tablet-10": 0.52,
}

DEFAULT_BG = "#D9FE06"
DEFAULT_TEXT = "#000000"

FRAME_PATH_DEFAULT = os.path.expanduser(
    "~/.fastlane/frameit/latest/Apple iPhone 16 Pro Max Black Titanium.png"
)
# Screen rect inside 1470x3000 frame PNG
FRAME_SCREEN_LEFT = 75
FRAME_SCREEN_TOP = 66
FRAME_SCREEN_RIGHT = 1394
FRAME_SCREEN_BOTTOM = 2933

FONT_HERO_PATH = os.path.expanduser("~/Library/Fonts/Poppins-Black.ttf")
FONT_SUB_PATH = os.path.expanduser("~/Library/Fonts/Poppins-ExtraBold.ttf")
FONT_FALLBACK = "/System/Library/Fonts/HelveticaNeue.ttc"

# ============================================================================
# Multi-script font + RTL pipeline.
#
# PIL/Pillow has no OpenType shaping (no HarfBuzz). For any complex script
# (Arabic, CJK, Thai, Devanagari, Hebrew, Bengali), Poppins shows tofu boxes
# OR broken glyphs (Apple's SFArabic uses on-the-fly shaping which PIL can't
# do — looks like "weird lines"). Each script needs:
#   1. A font that includes the right glyphs (not OpenType shaping — direct
#      glyph mapping for the Unicode codepoints or presentation forms).
#   2. For RTL scripts (Arabic, Hebrew), pre-shape + bidi-process the string
#      BEFORE handing to PIL, so glyphs are in correct visual order.
#
# Per-script candidate fonts (first existing wins):
# ============================================================================

# Bengali — Poppins has zero glyphs. macOS Kohinoor Bangla works.
FONT_BN_CANDIDATES = [
    "/System/Library/Fonts/KohinoorBangla.ttc",
    os.path.expanduser("~/Library/Fonts/Kalpurush.ttf"),
    os.path.expanduser("~/Library/Fonts/kalpurush.ttf"),
    os.path.expanduser("~/Library/Fonts/Siyamrupali.ttf"),
]
# Arabic — GeezaPro ships presentation forms (U+FE70-U+FEFF) which PIL needs
# after arabic-reshaper output. SFArabic uses OpenType, PIL can't render it.
FONT_AR_CANDIDATES = [
    "/System/Library/Fonts/GeezaPro.ttc",
    "/System/Library/Fonts/Supplemental/Damascus.ttc",
    os.path.expanduser("~/Library/Fonts/Cairo-Bold.ttf"),
    os.path.expanduser("~/Library/Fonts/NotoSansArabic-Bold.ttf"),
]
# Chinese Simplified + Traditional + Japanese + Korean share the CJK font.
FONT_CJK_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # Korean
    os.path.expanduser("~/Library/Fonts/NotoSansCJK-Bold.ttc"),
]
# Thai — system Thonburi has correct vowel-mark positioning.
FONT_TH_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Thonburi.ttc",
    "/System/Library/Fonts/Ayuthaya.ttf",
    os.path.expanduser("~/Library/Fonts/NotoSansThai-Bold.ttf"),
]
# Devanagari (Hindi) — Poppins has Devanagari for some chars, but macOS
# Kohinoor Devanagari is more complete.
FONT_HI_CANDIDATES = [
    "/System/Library/Fonts/Kohinoor.ttc",
    "/System/Library/Fonts/DevanagariMT.ttc",
    os.path.expanduser("~/Library/Fonts/NotoSansDevanagari-Bold.ttf"),
]
# Hebrew — ArialHB or system Hebrew font.
FONT_HE_CANDIDATES = [
    "/System/Library/Fonts/ArialHB.ttc",
    "/System/Library/Fonts/Supplemental/Corsiva Hebrew.ttc",
    os.path.expanduser("~/Library/Fonts/NotoSansHebrew-Bold.ttf"),
]
# Cyrillic — Poppins-Black download from Google Fonts SOMETIMES has Cyrillic
# subset but not always (verified 2026-06-25: user's local Poppins-Black has
# zero Cyrillic glyphs). Prefer system fonts that ship with Cyrillic.
FONT_CYRL_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Verdana Bold.ttf",
    os.path.expanduser("~/Library/Fonts/Poppins-Black.ttf"),  # only works if Cyrillic subset installed
]


def _has_bengali(text: str) -> bool:
    return any("ঀ" <= ch <= "৿" for ch in text)


def _has_arabic(text: str) -> bool:
    """Arabic block U+0600-U+06FF plus presentation forms U+FB50-FDFF, FE70-FEFF."""
    for ch in text:
        cp = ord(ch)
        if 0x0600 <= cp <= 0x06FF: return True
        if 0xFB50 <= cp <= 0xFDFF: return True
        if 0xFE70 <= cp <= 0xFEFF: return True
    return False


def _has_cjk(text: str) -> bool:
    """CJK Unified Ideographs U+4E00-U+9FFF + extensions, Hiragana, Katakana, Hangul."""
    for ch in text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF: return True   # CJK Unified
        if 0x3040 <= cp <= 0x309F: return True   # Hiragana
        if 0x30A0 <= cp <= 0x30FF: return True   # Katakana
        if 0xAC00 <= cp <= 0xD7AF: return True   # Hangul Syllables
        if 0x3400 <= cp <= 0x4DBF: return True   # CJK Extension A
    return False


def _has_thai(text: str) -> bool:
    return any(0x0E00 <= ord(ch) <= 0x0E7F for ch in text)


def _has_devanagari(text: str) -> bool:
    return any(0x0900 <= ord(ch) <= 0x097F for ch in text)


def _has_hebrew(text: str) -> bool:
    return any(0x0590 <= ord(ch) <= 0x05FF for ch in text)


def _has_cyrillic(text: str) -> bool:
    return any(0x0400 <= ord(ch) <= 0x04FF for ch in text)


def _pick_first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _pick_font_for_text(text: str, fallback: str = None):
    """Auto-pick a font that can render this text.
    Returns (font_path, needs_rtl_reshape: bool).
    fallback = Latin font path used when text has no special script."""
    if _has_arabic(text):
        f = _pick_first_existing(FONT_AR_CANDIDATES)
        return (f, True) if f else (fallback, True)
    if _has_hebrew(text):
        f = _pick_first_existing(FONT_HE_CANDIDATES)
        return (f, True) if f else (fallback, True)
    if _has_cjk(text):
        f = _pick_first_existing(FONT_CJK_CANDIDATES)
        return (f, False) if f else (fallback, False)
    if _has_thai(text):
        f = _pick_first_existing(FONT_TH_CANDIDATES)
        return (f, False) if f else (fallback, False)
    if _has_devanagari(text):
        f = _pick_first_existing(FONT_HI_CANDIDATES)
        return (f, False) if f else (fallback, False)
    if _has_bengali(text):
        f = _pick_first_existing(FONT_BN_CANDIDATES)
        return (f, False) if f else (fallback, False)
    if _has_cyrillic(text):
        f = _pick_first_existing(FONT_CYRL_CANDIDATES)
        return (f or fallback, False)
    return (fallback, False)


def _reshape_rtl(text: str) -> str:
    """RTL pre-shape Arabic/Hebrew so PIL renders the connected glyphs in
    visually-correct right-to-left order. Without this, Arabic letters appear
    as isolated forms (broken — looks like 'weird lines'). Requires
    arabic-reshaper + python-bidi (pip install --break-system-packages
    arabic-reshaper python-bidi). If unavailable, returns text unchanged with
    a warning to stderr."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        print("WARN: arabic-reshaper/python-bidi not installed — RTL text will render incorrectly. "
              "Install: pip3 install --break-system-packages arabic-reshaper python-bidi",
              file=sys.stderr)
        return text
    return get_display(arabic_reshaper.reshape(text))


def _prepare_text(text: str, override_font: str = None, fallback_font: str = None):
    """Pipeline: detect script → pick font → RTL-reshape if needed.
    Returns (text_to_render, font_path)."""
    if override_font:
        # User explicit override — assume they picked the right font.
        # Still RTL-reshape if the text needs it.
        needs_rtl = _has_arabic(text) or _has_hebrew(text)
        return (_reshape_rtl(text) if needs_rtl else text, override_font)
    font_path, needs_rtl = _pick_font_for_text(text, fallback_font)
    final = _reshape_rtl(text) if needs_rtl else text
    return (final, font_path or fallback_font)


def _font_can_render(font_path: str, text: str):
    """BLOCKER: check the font has glyphs for every codepoint in text.
    Returns list of unrenderable chars (empty = OK).

    Uses fontTools cmap table — the authoritative source of which codepoints
    a TTF/TTC actually supports. Catches the SFArabic problem (font expects
    OpenType shaping; PIL renders presentation forms with no matching glyph
    → tofu boxes / 'weird lines')."""
    try:
        from fontTools.ttLib import TTFont, TTCollection
    except ImportError:
        print("WARN: fontTools not installed — blocker disabled. Install: "
              "pip3 install --break-system-packages fonttools", file=sys.stderr)
        return []
    try:
        if font_path.lower().endswith(".ttc"):
            ttc = TTCollection(font_path)
            cmaps = []
            for f in ttc.fonts:
                cmaps.append(f.getBestCmap() or {})
            # union across faces in the collection
            combined = {}
            for c in cmaps:
                combined.update(c)
            cmap = combined
        else:
            cmap = TTFont(font_path).getBestCmap() or {}
    except Exception as e:
        print(f"WARN: cannot inspect font {font_path}: {e}", file=sys.stderr)
        return []

    # Whitelist ONLY ASCII control chars + whitespace. ASCII LETTERS and DIGITS
    # must be in cmap — otherwise a Latin "QR" inside an Arabic title renders
    # as tofu boxes (GeezaPro/Damascus/etc. lack Latin glyphs in their
    # primary face). Caught 2026-06-25 by user on No Trace ar-SA shot 2.
    missing = []
    for ch in text:
        cp = ord(ch)
        if cp < 0x20 or ch.isspace():
            # control chars + whitespace — always safe
            continue
        if cp not in cmap:
            missing.append(ch)
    return missing


# Fonts that have codepoints in cmap BUT do not render correctly in PIL
# because they rely on OpenType shaping (HarfBuzz) which PIL/Pillow has not.
# Allow override via --font-hero only when --skip-font-check is also set.
KNOWN_PIL_INCOMPATIBLE_FONTS = {
    # Apple's modern Arabic uses on-the-fly OpenType shaping. PIL renders the
    # presentation forms as null/placeholder glyphs → "weird lines".
    "SFArabic.ttf": "SFArabic uses OpenType shaping; PIL cannot render it. Use GeezaPro.ttc.",
    "SFArabicRounded.ttf": "SFArabicRounded uses OpenType shaping. Use GeezaPro.ttc.",
    # NotoNastaliq is Nastaliq Urdu script — only renders correctly with HarfBuzz.
    "NotoNastaliq.ttc": "NotoNastaliq needs Nastaliq shaping; PIL cannot. Use Damascus/Cairo for plain Arabic.",
}


def _enforce_font_blocker(text: str, font_path: str, surface: str, strict: bool = True):
    """Hard fail when the font cannot render the text. Catches:
    1. Font path missing entirely.
    2. Font lacks glyphs for some codepoints (cmap miss).
    3. Font is on the known-PIL-incompatible list (OpenType-shaping fonts).
    Prints exact missing codepoints + suggests the right font + RTL deps.

    Disabled with --skip-font-check (e.g., dev iteration on novel scripts)."""
    if not strict:
        return
    if not font_path or not os.path.exists(font_path):
        print(f"BLOCKER: font path for {surface} does not exist: {font_path}", file=sys.stderr)
        sys.exit(2)

    base = os.path.basename(font_path)
    if base in KNOWN_PIL_INCOMPATIBLE_FONTS:
        print(f"BLOCKER: {base} is on the known-PIL-incompatible list.", file=sys.stderr)
        print(f"  Reason: {KNOWN_PIL_INCOMPATIBLE_FONTS[base]}", file=sys.stderr)
        print(f"  Surface: {surface}", file=sys.stderr)
        print(f"  Text: {text!r}", file=sys.stderr)
        print("  HINT: drop the --font-hero/--font-sub override and let "
              "the composer auto-pick from the script-specific candidate list.",
              file=sys.stderr)
        sys.exit(3)

    missing = _font_can_render(font_path, text)
    if missing:
        sample = "".join(missing[:10])
        print(f"BLOCKER: font {base} cannot render "
              f"{len(missing)} codepoints in {surface!r} text "
              f"(sample: {sample!r}, U+{ord(missing[0]):04X}...). "
              f"This would produce 'weird lines' / tofu boxes in the screenshot.",
              file=sys.stderr)
        print(f"  text: {text!r}", file=sys.stderr)
        # Surface RTL dep hint if Arabic/Hebrew present
        if _has_arabic(text) or _has_hebrew(text):
            print("  HINT: install RTL deps: pip3 install --break-system-packages "
                  "arabic-reshaper python-bidi", file=sys.stderr)
        print("  HINT: override font with --font-hero/--font-sub OR add a "
              "candidate to the script's font registry in "
              "py/aso/aso-compose-screenshot.py", file=sys.stderr)
        sys.exit(3)

HERO_FONT_SIZE = 300
SUB_FONT_SIZE = 110
HERO_Y = 60
HERO_TO_SUB_GAP = 110
SUB_LINE_GAP = 55
TEXT_TO_PHONE_GAP = 90
PHONE_WIDTH_RATIO = 0.80  # Default; per-device override comes from DEVICE_PHONE_RATIO


def hex_to_rgb(hex_str: str) -> tuple:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def _load_font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype(FONT_FALLBACK, size, index=9)


def compose(
    raw_path: str,
    hero_text: str,
    subtitle_lines: list,
    output_path: str,
    device: str = "iphone-6.7",
    bg_color: str = DEFAULT_BG,
    text_color: str = DEFAULT_TEXT,
    frame_path: str = FRAME_PATH_DEFAULT,
    font_hero_path: str = None,
    font_sub_path: str = None,
    phone_ratio: float = None,
    strict_font_check: bool = True,
):
    spec = DEVICES[device]
    W, H = spec["width"], spec["height"]
    BG = hex_to_rgb(bg_color)
    TEXT_CLR = hex_to_rgb(text_color)

    # Multi-script pipeline: auto-pick font + RTL-reshape per text.
    # Explicit --font-hero / --font-sub overrides still win; the pipeline
    # only applies RTL reshape for them. Handles Arabic, Hebrew, CJK
    # (Simp/Trad/JP/KR), Thai, Devanagari, Bengali, Cyrillic.
    hero_render, auto_hero = _prepare_text(
        hero_text, override_font=font_hero_path, fallback_font=FONT_HERO_PATH
    )
    sub_prepared = [
        _prepare_text(line, override_font=font_sub_path, fallback_font=FONT_SUB_PATH)
        for line in subtitle_lines
    ]

    # BLOCKER: hard fail if the chosen font can't render the (reshaped) text.
    # Catches the SFArabic / presentation-form mismatch and any unsupported
    # script combo. Disable with --skip-font-check on the CLI.
    _enforce_font_blocker(hero_render, auto_hero, "hero", strict=strict_font_check)
    for line_render, line_font in sub_prepared:
        _enforce_font_blocker(line_render, line_font, "subtitle", strict=strict_font_check)

    canvas = Image.new("RGBA", (W, H), BG + (255,))
    draw = ImageDraw.Draw(canvas)

    # === HERO TEXT (auto-fit to 88% canvas width) ===
    max_text_w = int(W * 0.88)
    hero_size = HERO_FONT_SIZE
    font_h = _load_font(auto_hero, hero_size)
    while hero_size > 100:
        font_h = _load_font(auto_hero, hero_size)
        bb = draw.textbbox((0, 0), hero_render, font=font_h)
        if (bb[2] - bb[0]) <= max_text_w:
            break
        hero_size -= 10
    bb = draw.textbbox((0, 0), hero_render, font=font_h)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(((W - tw) // 2, HERO_Y), hero_render, fill=TEXT_CLR, font=font_h)

    # === SUBTITLE (auto-fit per line) ===
    y = HERO_Y + th + HERO_TO_SUB_GAP
    for line_render, line_font_path in sub_prepared:
        sub_size = SUB_FONT_SIZE
        font_s = _load_font(line_font_path, sub_size)
        while sub_size > 50:
            font_s = _load_font(line_font_path, sub_size)
            bb = draw.textbbox((0, 0), line_render, font=font_s)
            if (bb[2] - bb[0]) <= max_text_w:
                break
            sub_size -= 5
        bb = draw.textbbox((0, 0), line_render, font=font_s)
        tw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        draw.text(((W - tw) // 2, y), line_render, fill=TEXT_CLR, font=font_s)
        y += lh + SUB_LINE_GAP

    # === DEVICE FRAME ===
    use_real_frame = os.path.exists(frame_path)
    if use_real_frame:
        device_frame = Image.open(frame_path)
        fw, fh = device_frame.size

    # Tablets need a smaller phone silhouette so it fits in the wider canvas
    # without overflowing the bottom (phone aspect ≈ 2.04 means a phone at
    # 0.80 of an iPad would be taller than the canvas).
    effective_phone_ratio = (
        phone_ratio
        if phone_ratio is not None
        else DEVICE_PHONE_RATIO.get(device, PHONE_WIDTH_RATIO)
    )
    target_phone_w = int(W * effective_phone_ratio)
    if use_real_frame:
        scale = target_phone_w / fw
        target_phone_h = int(fh * scale)
        s_left = int(FRAME_SCREEN_LEFT * scale)
        s_top = int(FRAME_SCREEN_TOP * scale)
        s_w = int((FRAME_SCREEN_RIGHT - FRAME_SCREEN_LEFT) * scale)
        s_h = int((FRAME_SCREEN_BOTTOM - FRAME_SCREEN_TOP) * scale)
    else:
        target_phone_h = int(target_phone_w * 2.04)
        s_left, s_top = 18, 18
        s_w = target_phone_w - 36
        s_h = target_phone_h - 36

    phone_x = (W - target_phone_w) // 2
    phone_y = y + TEXT_TO_PHONE_GAP

    # === APP CONTENT (crop chrome + match aspect to iPhone screen) ===
    raw = Image.open(raw_path)
    rw, rh = raw.size
    # Android Pixel 1344x2992: status bar (top ~3.2%) + nav bar (bottom ~4.8%)
    if rw == 1344 and rh == 2992:
        crop = raw.crop((0, int(rh * 0.032), rw, int(rh * 0.952)))
    else:
        crop = raw

    # Center-crop to iPhone screen aspect — kills BG bleed at corners (LESSON #1)
    cw, ch = crop.size
    target_ratio = s_w / s_h
    current_ratio = cw / ch
    if current_ratio < target_ratio:
        new_h = int(cw / target_ratio)
        y_off = (ch - new_h) // 2
        crop = crop.crop((0, y_off, cw, y_off + new_h))
    elif current_ratio > target_ratio:
        new_w = int(ch * target_ratio)
        x_off = (cw - new_w) // 2
        crop = crop.crop((x_off, 0, x_off + new_w, ch))
    app = crop.resize((s_w, s_h), Image.LANCZOS).convert("RGBA")

    # === DROP SHADOW ===
    for i in range(5):
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle(
            [
                phone_x + 8 + i * 2, phone_y + 10 + i * 2,
                phone_x + target_phone_w + 8 + i * 2,
                phone_y + target_phone_h + 10 + i * 2,
            ],
            radius=50,
            fill=(0, 0, 0, 30 - i * 5),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15 + i * 5))
        canvas = Image.alpha_composite(canvas, shadow)

    # === COMPOSE PHONE ===
    if use_real_frame:
        frame_resized = device_frame.resize(
            (target_phone_w, target_phone_h), Image.LANCZOS
        )
        # Build silhouette mask from frame PNG alpha — dilate ~14px so anti-aliased
        # corner pixels are covered by black under-fill (LESSON #2)
        frame_alpha = frame_resized.split()[-1]
        sil = frame_alpha.point(lambda a: 255 if a > 0 else 0)
        try:
            sil = sil.filter(ImageFilter.MaxFilter(15))
            sil = sil.filter(ImageFilter.MaxFilter(15))
        except Exception:
            pass
        underfill = Image.new("RGBA", (target_phone_w, target_phone_h), (0, 0, 0, 0))
        black = Image.new("RGBA", (target_phone_w, target_phone_h), (0, 0, 0, 255))
        underfill.paste(black, (0, 0), sil)

        phone_layer = Image.new("RGBA", (target_phone_w, target_phone_h), (0, 0, 0, 0))
        phone_layer = Image.alpha_composite(phone_layer, underfill)
        # Round the app's corners to match the iPhone screen aperture. Without
        # this, the app pixels fill a SQUARE rect and the 4 square wedges show
        # through where the frame PNG's rounded screen edge is anti-aliased.
        # The fallback (no-frame) branch already does this — the bug was that
        # the real-frame branch skipped it.
        screen_radius = max(20, int(round(s_w * 0.072)))
        app_mask = Image.new("L", (s_w, s_h), 0)
        ImageDraw.Draw(app_mask).rounded_rectangle(
            [0, 0, s_w, s_h], radius=screen_radius, fill=255,
        )
        phone_layer.paste(app, (s_left, s_top), app_mask)
        phone_layer = Image.alpha_composite(phone_layer, frame_resized)
        canvas.paste(phone_layer, (phone_x, phone_y), phone_layer)
    else:
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(
            [phone_x, phone_y, phone_x + target_phone_w, phone_y + target_phone_h],
            radius=55, fill=(25, 25, 25, 255),
        )
        mask = Image.new("L", (s_w, s_h), 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle([0, 0, s_w, s_h], radius=40, fill=255)
        canvas.paste(app, (phone_x + s_left, phone_y + s_top), mask)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    canvas.convert("RGB").save(output_path, quality=95)
    print(f"  -> {output_path} ({W}x{H})")


def main():
    p = argparse.ArgumentParser(
        description="Compose App Store / Play Store screenshot with device frame + text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--raw", required=True, help="Path to raw simulator/emulator screenshot")
    p.add_argument("--hero", required=True, help="Hero text (single short phrase, all-caps)")
    p.add_argument("--subtitle", nargs="+", required=True, help="Subtitle lines (1 or more)")
    p.add_argument("--output", "-o", required=True, help="Output file path (.jpg / .png)")
    p.add_argument("--device", default="iphone-6.7", choices=DEVICES.keys())
    p.add_argument("--bg", default=DEFAULT_BG, help=f"Background hex (default {DEFAULT_BG})")
    p.add_argument("--text-color", default=DEFAULT_TEXT, help=f"Text hex (default {DEFAULT_TEXT})")
    p.add_argument("--frame", default=FRAME_PATH_DEFAULT, help="Apple device frame PNG path")
    p.add_argument("--font-hero", default=None, help="Override hero TTF path (auto-Bengali if hero has BN script)")
    p.add_argument("--font-sub", default=None, help="Override subtitle TTF path")
    p.add_argument("--phone-ratio", type=float, default=None,
                   help="Phone-shape width / canvas width. Auto-picked per device if omitted.")
    p.add_argument("--skip-font-check", action="store_true",
                   help="Skip font-glyph blocker. Use ONLY for dev iteration on novel scripts; "
                        "default behavior FAILS the composer if the chosen font cannot render "
                        "the text (prevents 'weird lines' / tofu boxes in shipped screenshots).")
    args = p.parse_args()

    compose(
        raw_path=args.raw,
        hero_text=args.hero,
        subtitle_lines=args.subtitle,
        output_path=args.output,
        device=args.device,
        bg_color=args.bg,
        text_color=args.text_color,
        frame_path=args.frame,
        font_hero_path=args.font_hero,
        font_sub_path=args.font_sub,
        phone_ratio=args.phone_ratio,
        strict_font_check=not args.skip_font_check,
    )


if __name__ == "__main__":
    main()
