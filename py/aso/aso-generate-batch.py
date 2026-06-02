#!/usr/bin/env python3
"""aso-generate-batch.py — generate a set of App Store / Play Store screenshots
from a project-specific presets JSON file.

Per project, you ship a JSON like:

{
  "device": "iphone-6.7",
  "bg": "#D9FE06",
  "text_color": "#000000",
  "frame": "~/.fastlane/frameit/latest/Apple iPhone 16 Pro Max Black Titanium.png",
  "output_dir": "screenshots/store-ready",
  "shots": [
    {
      "name": "01-battery-health",
      "raw": "screenshots/by-feature/02-battery/01-power-consumption-7p9w-overview.png",
      "hero": "BATTERY HEALTH",
      "subtitle": ["IN WATTS", "NOT JUST %"],
      "keywords": "battery health (RISING 10.6k/mo), ai battery"
    },
    ...
  ]
}

Paths are resolved relative to the JSON file's directory (or absolute).

Usage:
  python3 aso-generate-batch.py --presets path/to/aso_screenshot_presets.json
  python3 aso-generate-batch.py --presets path/to/presets.json --output-dir custom/out
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _load_compose():
    """Import the sibling aso-compose-screenshot.py module (the dash makes a plain
    import keyword-illegal so we go via importlib)."""
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "aso_compose_screenshot",
        here / "aso-compose-screenshot.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--presets", required=True, type=Path,
                   help="Project-specific presets JSON")
    p.add_argument("--output-dir", default=None,
                   help="Override output_dir in the JSON")
    p.add_argument("--filter", default=None,
                   help="Only generate shots whose name contains this substring")
    args = p.parse_args()

    if not args.presets.exists():
        print(f"[err] presets file not found: {args.presets}", file=sys.stderr)
        sys.exit(1)

    cfg = json.loads(args.presets.read_text())
    base = args.presets.parent

    device = cfg.get("device", "iphone-6.7")
    bg = cfg.get("bg", "#D9FE06")
    text_color = cfg.get("text_color", "#000000")
    frame = cfg.get("frame", None)
    # Optional global font overrides (per-locale Bengali / Arabic / Japanese
    # presets ship a font_hero + font_sub here). compose() also auto-picks a
    # Bengali font if hero/subtitle contains BN script, so this is mostly for
    # explicit control or scripts other than Bengali.
    font_hero = cfg.get("font_hero", None)
    font_sub = cfg.get("font_sub", None)
    # Optional phone-shape width / canvas width override. Tablets auto-pick a
    # smaller default via the compose script's DEVICE_PHONE_RATIO map; this
    # JSON key only matters when the auto default needs tweaking per project.
    phone_ratio = cfg.get("phone_ratio", None)
    out_dir_str = args.output_dir or cfg.get("output_dir", "screenshots/store-ready")
    out_dir = (base / out_dir_str).resolve() if not Path(out_dir_str).is_absolute() else Path(out_dir_str)
    out_dir.mkdir(parents=True, exist_ok=True)

    compose_mod = _load_compose()

    shots = cfg.get("shots", [])
    if args.filter:
        shots = [s for s in shots if args.filter in s.get("name", "")]
    if not shots:
        print("[warn] no shots matched", file=sys.stderr)
        sys.exit(0)

    print(f"Generating {len(shots)} screenshot(s) -> {out_dir}")
    failed = 0
    for s in shots:
        name = s["name"]
        raw_path = s["raw"]
        raw = Path(raw_path) if Path(raw_path).is_absolute() else (base / raw_path).resolve()
        if not raw.exists():
            print(f"  [skip] {name} — raw missing: {raw}")
            failed += 1
            continue
        out_file = out_dir / f"{name}.jpg"
        try:
            kwargs = {
                "raw_path": str(raw),
                "hero_text": s["hero"],
                "subtitle_lines": s["subtitle"],
                "output_path": str(out_file),
                "device": device,
                "bg_color": bg,
                "text_color": text_color,
            }
            if frame:
                kwargs["frame_path"] = str(Path(frame).expanduser())
            # Per-shot font overrides win; otherwise fall back to global
            # font_hero/font_sub from the JSON top level.
            shot_hero_font = s.get("font_hero", font_hero)
            shot_sub_font = s.get("font_sub", font_sub)
            if shot_hero_font:
                kwargs["font_hero_path"] = str(Path(shot_hero_font).expanduser())
            if shot_sub_font:
                kwargs["font_sub_path"] = str(Path(shot_sub_font).expanduser())
            shot_phone_ratio = s.get("phone_ratio", phone_ratio)
            if shot_phone_ratio is not None:
                kwargs["phone_ratio"] = float(shot_phone_ratio)
            compose_mod.compose(**kwargs)
        except Exception as e:
            print(f"  [err] {name}: {e}", file=sys.stderr)
            failed += 1

    print(f"\nDone. {len(shots) - failed}/{len(shots)} succeeded.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
