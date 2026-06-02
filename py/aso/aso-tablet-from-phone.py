#!/usr/bin/env python3
"""aso-tablet-from-phone.py — derive tablet/iPad presets from a phone preset.

Why this exists:
  Apple BLOCKS submission of Universal apps (TARGETED_DEVICE_FAMILY = "1,2")
  that don't ship iPad 12.9" screenshots. Google Play strongly recommends
  10" tablet screenshots when the app declares tablet support.

  Without this script every project would manually clone the phone preset
  JSON, edit device + output_dir + raw paths, and ship a half-done set.
  We did exactly that on InterviewBoss the first time around — caught only
  at submission. This script makes the mistake impossible.

What it does:
  Reads a phone preset JSON (iphone-* or play-phone device) and writes
  derived tablet preset JSON(s) next to it:

    aso_screenshot_presets_ios.json      ──►  aso_screenshot_presets_ipad.json
    aso_screenshot_presets_ios_bn.json   ──►  aso_screenshot_presets_ipad_bn.json
    aso_screenshot_presets_play.json     ──►  aso_screenshot_presets_play_tablet.json

  The derived JSON:
    - Uses the same shots + hero/subtitle copy (no re-translation)
    - Switches "device" to ipad-12.9 (Apple) or play-tablet-10 (Google)
    - Drops the iPhone "frame" (Apple has no canonical iPad 12.9 frame in
      our fastlane bundle yet — the no-frame rounded-rect fallback ships)
    - Switches output_dir to a tablet-suffixed folder

  After writing the derived JSON, the existing aso-generate-batch.py runs
  unchanged — phone_ratio auto-shrinks the device silhouette so it fits
  the tablet canvas.

Usage:
  python3 aso-tablet-from-phone.py --phone path/to/aso_screenshot_presets_ios.json
  # writes aso_screenshot_presets_ipad.json in the same directory.

  # batch over every phone preset in a directory:
  python3 aso-tablet-from-phone.py --scan path/to/automation_data
"""

import argparse
import json
import sys
from pathlib import Path


# Phone-device → tablet-device mapping. Apple iPad 12.9" Pro is the canonical
# largest-iPad class App Store reviewers expect; play-tablet-10 is the 1600x2560
# 10" portrait Google publishes as the modern default.
PHONE_TO_TABLET = {
    "iphone-6.7": "ipad-12.9",
    "iphone-6.5": "ipad-12.9",
    "iphone-5.5": "ipad-12.9",
    "play-phone": "play-tablet-10",
}


def _derived_name(phone_path: Path) -> Path:
    """Map a phone preset filename to its tablet counterpart in the same dir.

    aso_screenshot_presets_ios.json     -> aso_screenshot_presets_ipad.json
    aso_screenshot_presets_ios_bn.json  -> aso_screenshot_presets_ipad_bn.json
    aso_screenshot_presets_play.json    -> aso_screenshot_presets_play_tablet.json
    foo.json (no convention)            -> foo_tablet.json
    """
    stem = phone_path.stem
    if "_ios" in stem:
        new_stem = stem.replace("_ios", "_ipad", 1)
    elif "_play" in stem and "_tablet" not in stem:
        new_stem = stem.replace("_play", "_play_tablet", 1)
    else:
        new_stem = f"{stem}_tablet"
    return phone_path.with_name(f"{new_stem}{phone_path.suffix}")


def _derived_output_dir(phone_output: str, new_device: str) -> str:
    """Rewrite the phone output_dir to a tablet-suffixed folder.

    "../screenshots/store-ready/ios-6.7-en"     -> "../screenshots/store-ready/ipad-12.9-en"
    "../screenshots/store-ready/ios-6.7-bn"     -> "../screenshots/store-ready/ipad-12.9-bn"
    "../screenshots/store-ready/play-phone-en"  -> "../screenshots/store-ready/play-tablet-10-en"
    """
    if "ios-6.7" in phone_output:
        return phone_output.replace("ios-6.7", "ipad-12.9", 1)
    if "iphone-6.7" in phone_output:
        return phone_output.replace("iphone-6.7", "ipad-12.9", 1)
    if "play-phone" in phone_output:
        return phone_output.replace("play-phone", "play-tablet-10", 1)
    return f"{phone_output}-tablet"


def derive_one(phone_path: Path, overwrite: bool = False) -> Path:
    phone_cfg = json.loads(phone_path.read_text())
    phone_device = phone_cfg.get("device", "iphone-6.7")
    if phone_device not in PHONE_TO_TABLET:
        print(f"[skip] {phone_path.name} — device '{phone_device}' is not a phone class", file=sys.stderr)
        return None

    tablet_device = PHONE_TO_TABLET[phone_device]
    tablet_path = _derived_name(phone_path)
    if tablet_path.exists() and not overwrite:
        print(f"[exists] {tablet_path.name} — pass --overwrite to regenerate")
        return tablet_path

    tablet_cfg = dict(phone_cfg)
    tablet_cfg["_doc"] = (
        f"DERIVED FROM {phone_path.name} by aso-tablet-from-phone.py. "
        f"Re-derive with: python3 aso-tablet-from-phone.py --phone "
        f"{phone_path.name} --overwrite. "
        f"Apple Universal apps (TARGETED_DEVICE_FAMILY = 1,2) need iPad screenshots "
        f"or App Store Connect blocks submission. Google Play wants 10\" tablet "
        f"screenshots when the app declares tablet support."
    )
    tablet_cfg["device"] = tablet_device
    # Drop iPhone frame — no iPad frame in fastlane bundle; the no-frame
    # rounded-rect fallback in compose() handles tablet rendering.
    tablet_cfg.pop("frame", None)
    if "output_dir" in tablet_cfg:
        tablet_cfg["output_dir"] = _derived_output_dir(tablet_cfg["output_dir"], tablet_device)

    tablet_path.write_text(json.dumps(tablet_cfg, indent=2, ensure_ascii=False) + "\n")
    print(f"  -> wrote {tablet_path.name} (device={tablet_device}, {len(tablet_cfg.get('shots', []))} shots)")
    return tablet_path


def main():
    p = argparse.ArgumentParser(
        description="Derive tablet/iPad presets from a phone preset so Universal apps don't get caught at submission.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--phone", type=Path, help="Single phone preset JSON to derive from")
    g.add_argument("--scan", type=Path, help="Directory to scan for aso_screenshot_presets_*.json files")
    p.add_argument("--overwrite", action="store_true",
                   help="Regenerate tablet preset even if it already exists")
    args = p.parse_args()

    derived = []
    if args.phone:
        if not args.phone.exists():
            print(f"[err] phone preset not found: {args.phone}", file=sys.stderr)
            sys.exit(1)
        out = derive_one(args.phone, overwrite=args.overwrite)
        if out:
            derived.append(out)
    else:
        scan_dir = args.scan
        if not scan_dir.exists() or not scan_dir.is_dir():
            print(f"[err] scan dir not found: {scan_dir}", file=sys.stderr)
            sys.exit(1)
        for f in sorted(scan_dir.glob("aso_screenshot_presets_*.json")):
            # Skip already-tablet ones (avoid loops)
            if any(t in f.stem for t in ("ipad", "tablet")):
                continue
            out = derive_one(f, overwrite=args.overwrite)
            if out:
                derived.append(out)

    if not derived:
        print("[warn] no tablet presets derived (already exist? pass --overwrite to force)")
    else:
        print(f"\nDone. {len(derived)} tablet preset(s) derived.")
        print("Now run for each:")
        for p in derived:
            print(f"  python3 aso-generate-batch.py --presets {p}")


if __name__ == "__main__":
    main()
