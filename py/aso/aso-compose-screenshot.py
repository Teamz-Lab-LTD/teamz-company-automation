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
# Latin Poppins has zero Bengali glyphs — text shows as tofu boxes. When the
# hero/subtitle contains any character in the Bengali Unicode block
# (U+0980 to U+09FF), swap to a Bengali-capable font automatically. macOS
# ships Kohinoor Bangla; user fonts may have Kalpurush. First hit wins.
FONT_BN_CANDIDATES = [
    "/System/Library/Fonts/KohinoorBangla.ttc",
    os.path.expanduser("~/Library/Fonts/Kalpurush.ttf"),
    os.path.expanduser("~/Library/Fonts/kalpurush.ttf"),
    os.path.expanduser("~/Library/Fonts/Siyamrupali.ttf"),
]


def _has_bengali(text: str) -> bool:
    return any("ঀ" <= ch <= "৿" for ch in text)


def _pick_bn_font():
    for p in FONT_BN_CANDIDATES:
        if os.path.exists(p):
            return p
    return None

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
):
    spec = DEVICES[device]
    W, H = spec["width"], spec["height"]
    BG = hex_to_rgb(bg_color)
    TEXT_CLR = hex_to_rgb(text_color)

    # Auto-pick Bengali font when text contains Bengali script — Poppins has
    # no Bengali glyphs and would render tofu boxes. Explicit JSON overrides
    # take precedence.
    auto_hero = font_hero_path or FONT_HERO_PATH
    auto_sub = font_sub_path or FONT_SUB_PATH
    if _has_bengali(hero_text) and not font_hero_path:
        bn = _pick_bn_font()
        if bn:
            auto_hero = bn
    if any(_has_bengali(l) for l in subtitle_lines) and not font_sub_path:
        bn = _pick_bn_font()
        if bn:
            auto_sub = bn

    canvas = Image.new("RGBA", (W, H), BG + (255,))
    draw = ImageDraw.Draw(canvas)

    # === HERO TEXT (auto-fit to 88% canvas width) ===
    max_text_w = int(W * 0.88)
    hero_size = HERO_FONT_SIZE
    font_h = _load_font(auto_hero, hero_size)
    while hero_size > 100:
        font_h = _load_font(auto_hero, hero_size)
        bb = draw.textbbox((0, 0), hero_text, font=font_h)
        if (bb[2] - bb[0]) <= max_text_w:
            break
        hero_size -= 10
    bb = draw.textbbox((0, 0), hero_text, font=font_h)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(((W - tw) // 2, HERO_Y), hero_text, fill=TEXT_CLR, font=font_h)

    # === SUBTITLE (auto-fit per line) ===
    y = HERO_Y + th + HERO_TO_SUB_GAP
    for line in subtitle_lines:
        sub_size = SUB_FONT_SIZE
        font_s = _load_font(auto_sub, sub_size)
        while sub_size > 50:
            font_s = _load_font(auto_sub, sub_size)
            bb = draw.textbbox((0, 0), line, font=font_s)
            if (bb[2] - bb[0]) <= max_text_w:
                break
            sub_size -= 5
        bb = draw.textbbox((0, 0), line, font=font_s)
        tw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        draw.text(((W - tw) // 2, y), line, fill=TEXT_CLR, font=font_s)
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
    )


if __name__ == "__main__":
    main()
