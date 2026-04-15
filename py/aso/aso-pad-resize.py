#!/usr/bin/env python3
"""Pad + resize a source screenshot to target device dimensions.

Zero API cost — preserves headline + app content, pads with BG color to fit
target aspect ratio, then resizes.

Usage:
    python3 pad_resize.py --src source.jpg --dst out.jpg \\
        --width 1080 --height 1920 --bg "#CDFF1A"
"""
import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("[ERROR] Pillow required: pip3 install Pillow", file=sys.stderr)
    sys.exit(1)


def pad_resize(src: Path, dst: Path, target_w: int, target_h: int, bg_hex: str):
    bg = tuple(int(bg_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    img = Image.open(src).convert("RGB")
    w, h = img.size
    target_ratio = target_w / target_h
    current_ratio = w / h

    if current_ratio < target_ratio:
        # Too tall — pad left+right
        new_w = int(h * target_ratio)
        canvas = Image.new("RGB", (new_w, h), bg)
        canvas.paste(img, ((new_w - w) // 2, 0))
        img = canvas
    elif current_ratio > target_ratio:
        # Too wide — pad top+bottom
        new_h = int(w / target_ratio)
        canvas = Image.new("RGB", (w, new_h), bg)
        canvas.paste(img, (0, (new_h - h) // 2))
        img = canvas

    img = img.resize((target_w, target_h), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "JPEG", quality=92)
    print(f"✓ {dst} ({target_w}×{target_h})")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True)
    p.add_argument("--dst", required=True)
    p.add_argument("--width", type=int, required=True)
    p.add_argument("--height", type=int, required=True)
    p.add_argument("--bg", required=True, help="Background hex color e.g. #CDFF1A")
    args = p.parse_args()
    pad_resize(Path(args.src), Path(args.dst), args.width, args.height, args.bg)


if __name__ == "__main__":
    main()
