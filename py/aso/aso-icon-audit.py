#!/usr/bin/env python3
"""
ASO App Icon Audit — stdlib-only icon QA for Android + iOS.

Checks each icon PNG for:
- File exists + correct dimension
- Min size for the platform slot (e.g. Play Store 512×512, App Store 1024×1024)
- Average luminance (detects "too dark" or "too bright" icons that lose contrast
  against Apple's white and Google's light/dark store surfaces)
- Corner-vs-center contrast ratio (detects flat low-info icons)
- Transparency check (iOS App Store icons must have NO alpha channel)
- Edge-legibility signal: approximates whether the icon fills enough of the frame

Usage::

    python3 py/aso/aso-icon-audit.py
    python3 py/aso/aso-icon-audit.py --json            # machine-readable
    python3 py/aso/aso-icon-audit.py --strict          # exit 1 on any failure

Writes: {data}/aso-icon-audit.json
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _teamz_config import load_runtime  # noqa: E402

_CFG = load_runtime(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_teamz_config.py")
)
_DATA_DIR = Path(
    os.environ.get("TEAMZ_DATA_DIR", "")
    or _CFG.get("data_dir", "")
    or str(Path(_CFG["host_site_root"]) / "automation_data")
)
_ROOT = Path(_CFG.get("host_site_root", "."))


def _read_png(path: Path) -> dict | None:
    """Minimal PNG reader (stdlib only). Returns width, height, has_alpha,
    and a downsampled pixel grid for luminance sampling."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    i = 8
    width = height = bit_depth = color_type = 0
    idat = b""
    while i < len(raw):
        ln = struct.unpack(">I", raw[i:i+4])[0]
        ctype = raw[i+4:i+8]
        data = raw[i+8:i+8+ln]
        i += 8 + ln + 4
        if ctype == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", data[:10])
        elif ctype == b"IDAT":
            idat += data
        elif ctype == b"IEND":
            break
    if not idat or bit_depth != 8 or color_type not in (2, 6):
        # Only RGB (2) and RGBA (6), 8-bit: skip paletted/grayscale (rare for icons).
        return {"width": width, "height": height, "has_alpha": color_type == 6, "pixels": None}

    try:
        decomp = zlib.decompress(idat)
    except zlib.error:
        return {"width": width, "height": height, "has_alpha": color_type == 6, "pixels": None}

    bpp = 4 if color_type == 6 else 3
    stride = width * bpp
    rows = []
    prev = bytes(stride)
    pos = 0
    for _ in range(height):
        if pos >= len(decomp):
            break
        ftype = decomp[pos]; pos += 1
        line = bytearray(decomp[pos:pos + stride]); pos += stride
        # PNG defilter
        if ftype == 0:
            pass
        elif ftype == 1:  # Sub
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 0xFF
        elif ftype == 2:  # Up
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif ftype == 3:  # Average
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                line[x] = (line[x] + (a + b) // 2) & 0xFF
        elif ftype == 4:  # Paeth
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                if pa <= pb and pa <= pc:
                    pr = a
                elif pb <= pc:
                    pr = b
                else:
                    pr = c
                line[x] = (line[x] + pr) & 0xFF
        else:
            return {"width": width, "height": height, "has_alpha": color_type == 6, "pixels": None}
        rows.append(bytes(line))
        prev = line

    # Downsample to 16×16 grid of (r,g,b,a) averages for fast analysis
    GRID = 16
    grid = [[None]*GRID for _ in range(GRID)]
    for gy in range(GRID):
        for gx in range(GRID):
            y0 = gy * height // GRID
            y1 = max(y0 + 1, (gy + 1) * height // GRID)
            x0 = gx * width // GRID
            x1 = max(x0 + 1, (gx + 1) * width // GRID)
            r = g = b = a = count = 0
            for y in range(y0, min(y1, len(rows))):
                row = rows[y]
                for x in range(x0, x1):
                    off = x * bpp
                    if off + bpp > len(row):
                        continue
                    r += row[off]; g += row[off+1]; b += row[off+2]
                    a += row[off+3] if bpp == 4 else 255
                    count += 1
            if count:
                grid[gy][gx] = (r//count, g//count, b//count, a//count)
            else:
                grid[gy][gx] = (0, 0, 0, 0)
    return {"width": width, "height": height, "has_alpha": color_type == 6, "pixels": grid}


def _luminance(r, g, b) -> float:
    return (0.2126*r + 0.7152*g + 0.0722*b) / 255.0


def _analyze(meta: dict, slot: dict) -> dict:
    findings = []
    ok = True

    if meta["width"] != meta["height"]:
        findings.append(f"Non-square: {meta['width']}x{meta['height']}")
        ok = False

    min_size = slot.get("min_size", 0)
    if meta["width"] < min_size:
        findings.append(f"Too small: {meta['width']}px (min {min_size}px)")
        ok = False

    if slot.get("no_alpha") and meta["has_alpha"]:
        findings.append("Has alpha channel — iOS App Store rejects transparent icons")
        ok = False

    pixels = meta.get("pixels")
    avg_lum = corner_center_contrast = fill_ratio = None
    if pixels:
        lums = []
        for row in pixels:
            for px in row:
                lums.append(_luminance(px[0], px[1], px[2]))
        avg_lum = sum(lums) / len(lums)
        if avg_lum < 0.08:
            findings.append(f"Very dark (avg luminance {avg_lum:.2f}) — poor visibility on dark UI")
            ok = False
        elif avg_lum > 0.95:
            findings.append(f"Very bright (avg luminance {avg_lum:.2f}) — poor visibility on white UI")
            ok = False

        # Corner vs center contrast
        corner_lum = sum(_luminance(*pixels[y][x][:3]) for (y, x) in
                         [(0, 0), (0, 15), (15, 0), (15, 15)]) / 4
        center_lum = sum(_luminance(*pixels[y][x][:3]) for y in range(6, 10)
                         for x in range(6, 10)) / 16
        corner_center_contrast = abs(center_lum - corner_lum)
        if corner_center_contrast < 0.08:
            findings.append(
                f"Low center↔corner contrast ({corner_center_contrast:.2f}) — "
                f"icon may look flat at small sizes")
            ok = False

        # Fill ratio: how much of frame is non-background (vs corner color)
        bg = pixels[0][0][:3]
        diff_pixels = 0
        for row in pixels:
            for px in row:
                if abs(px[0] - bg[0]) + abs(px[1] - bg[1]) + abs(px[2] - bg[2]) > 30:
                    diff_pixels += 1
        fill_ratio = diff_pixels / 256
        if fill_ratio < 0.25:
            findings.append(
                f"Low fill ratio ({fill_ratio:.0%}) — content too small within frame")
            ok = False

    return {
        "ok": ok,
        "findings": findings,
        "avg_luminance": round(avg_lum, 3) if avg_lum is not None else None,
        "corner_center_contrast": round(corner_center_contrast, 3) if corner_center_contrast is not None else None,
        "fill_ratio": round(fill_ratio, 3) if fill_ratio is not None else None,
    }


def _discover_icons() -> list[dict]:
    slots = []
    # iOS App Store marketing icon (1024×1024, no alpha)
    ios_appicon = list(_ROOT.glob("ios/Runner/Assets.xcassets/AppIcon.appiconset/*1024*.png"))
    for p in ios_appicon:
        slots.append({"path": p, "platform": "ios", "slot": "appstore_1024",
                      "min_size": 1024, "no_alpha": True})
    # iOS other sizes
    ios_other = [p for p in _ROOT.glob("ios/Runner/Assets.xcassets/AppIcon.appiconset/*.png")
                 if "1024" not in p.name]
    for p in ios_other:
        slots.append({"path": p, "platform": "ios", "slot": "ios_runtime",
                      "min_size": 20, "no_alpha": False})
    # Android Play Store 512×512
    play_icons = list(_ROOT.glob("android/app/src/main/play/listings/*/graphics/icon/*.png"))
    play_icons += list(_ROOT.glob("fastlane/metadata/android/*/images/icon/*.png"))
    for p in play_icons:
        slots.append({"path": p, "platform": "android", "slot": "play_512",
                      "min_size": 512, "no_alpha": False})
    # Android launcher icons (mipmap)
    for p in _ROOT.glob("android/app/src/main/res/mipmap-xxxhdpi/*.png"):
        if "ic_launcher" in p.name and "foreground" not in p.name:
            slots.append({"path": p, "platform": "android", "slot": "launcher_xxxhdpi",
                          "min_size": 192, "no_alpha": False})
    return slots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    slots = _discover_icons()
    if not slots:
        print("[WARN] No icon files found under ios/ or android/", file=sys.stderr)
        return 0

    results = []
    fails = 0
    for slot in slots:
        meta = _read_png(slot["path"])
        if not meta:
            results.append({"path": str(slot["path"]), "slot": slot["slot"],
                            "ok": False, "findings": ["Unreadable PNG"]})
            fails += 1
            continue
        a = _analyze(meta, slot)
        results.append({
            "path": str(slot["path"].relative_to(_ROOT)),
            "platform": slot["platform"],
            "slot": slot["slot"],
            "size": f"{meta['width']}x{meta['height']}",
            "has_alpha": meta["has_alpha"],
            **a,
        })
        if not a["ok"]:
            fails += 1

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = _DATA_DIR / "aso-icon-audit.json"
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\nIcon audit: {len(results)} icons, {fails} with issues\n")
        for r in results:
            status = "✅" if r.get("ok") else "❌"
            print(f"{status} [{r.get('slot', '?')}] {r['path']} ({r.get('size', '?')})")
            for f in r.get("findings", []):
                print(f"     - {f}")
        print(f"\n  [ok] Wrote {out}", file=sys.stderr)

    return 1 if (args.strict and fails) else 0


if __name__ == "__main__":
    sys.exit(main())
