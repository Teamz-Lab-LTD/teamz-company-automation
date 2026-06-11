#!/usr/bin/env python3
"""
ASO Claims Lint — block forbidden marketing claims BEFORE submit.
====================================================================================
Scans the generated listing (title/subtitle/keywords/description) + screenshot OCR for
claims the app legally cannot make — e.g. "offline" when it's a remote WebView, "ad-free"
when it ships ads. This is the guard that would have caught the "Play offline" rejection.

Per-app forbidden list comes from automation_data/deep-research-keywords.json
(_app_constraints.forbidden_claims); falls back to a safe default.

Usage:
  python3 aso-claims-lint.py                          # uses TEAMZ_DATA_DIR or ./automation_data
  python3 aso-claims-lint.py --data-dir <dir> --screenshots <dir> --text "extra text"
Exit: 0 = clean, 2 = forbidden claim found (block the submit), 3 = bad args.
"""
import sys, os, json, re, glob, subprocess

DEFAULT_FORBIDDEN = [
    "no ads", "ad-free", "ad free", "without ads", "remove ads",
    "offline", "works offline", "play offline", "no internet",
    "no wifi", "no wi-fi", "no connection needed",
]


def load_forbidden(data_dir):
    try:
        d = json.load(open(os.path.join(data_dir, "deep-research-keywords.json")))
        fc = d.get("_app_constraints", {}).get("forbidden_claims")
        if fc:
            return [c.lower() for c in fc]
    except Exception:
        pass
    return DEFAULT_FORBIDDEN


def gather_listing_text(data_dir, extra):
    texts = [extra] if extra else []
    for p in glob.glob(os.path.join(data_dir, "aso-*latest.json")):
        try:
            d = json.load(open(p))
            for k in ("title", "subtitle", "keywords", "description", "name",
                      "short_description", "full_description"):
                v = d.get(k)
                if isinstance(v, str):
                    texts.append(v)
        except Exception:
            pass
    return texts


def _has_tesseract():
    try:
        subprocess.run(["tesseract", "--version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def ocr_screenshots(shot_dir):
    out = []
    if not shot_dir or not os.path.isdir(shot_dir):
        return out
    if not _has_tesseract():
        print("  [claims-lint] tesseract not installed — skipping screenshot OCR (brew install tesseract)")
        return out
    for s in glob.glob(os.path.join(shot_dir, "**", "*.png"), recursive=True):
        try:
            t = subprocess.run(["tesseract", s, "-"], capture_output=True, text=True, timeout=30).stdout
            out.append((os.path.basename(s), t))
        except Exception:
            pass
    return out


def main():
    args = sys.argv[1:]
    data_dir = os.environ.get("TEAMZ_DATA_DIR") or "automation_data"
    extra = shot_dir = None
    if "--data-dir" in args:
        data_dir = args[args.index("--data-dir") + 1]
    if "--text" in args:
        extra = args[args.index("--text") + 1]
    if "--screenshots" in args:
        shot_dir = args[args.index("--screenshots") + 1]

    forbidden = load_forbidden(data_dir)
    hits = []
    for t in gather_listing_text(data_dir, extra):
        low = t.lower()
        for c in forbidden:
            if re.search(r"\b" + re.escape(c) + r"\b", low):
                hits.append(("listing", c, t.strip()[:60]))
    for name, t in ocr_screenshots(shot_dir):
        low = t.lower()
        for c in forbidden:
            if re.search(r"\b" + re.escape(c) + r"\b", low):
                hits.append((name, c, "(screenshot text)"))

    print("=== ASO claims-lint ===")
    print(f"  forbidden ({len(forbidden)}): {', '.join(forbidden[:6])} …")
    if hits:
        print("  🔴 FORBIDDEN CLAIMS FOUND:")
        for where, claim, ctx in hits:
            print(f"     - '{claim}'  in {where}   {ctx}")
        print("  Remove before submit — Apple 2.3.1 / Google deceptive-behavior rejection risk.")
        sys.exit(2)
    print("  🟢 clean — no forbidden claims.")
    sys.exit(0)


if __name__ == "__main__":
    main()
