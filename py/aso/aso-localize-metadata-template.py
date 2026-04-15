#!/usr/bin/env python3
"""
App Store metadata localization template — PER-PROJECT copy, don't edit in kit.

Usage:
1. Copy this file to your project's `automation_data/localize_metadata.py`
2. Fill in the TRANSLATIONS dict with hand-crafted translations for each
   locale (Claude IS the translator — don't rely on aso-localize.py's
   English fallback)
3. Run: `cd <project_root> && python3 automation_data/localize_metadata.py`
4. All fastlane/metadata/{locale}/*.txt files get updated
5. Commit + push to ASC via fastlane upload_metadata / upload_all

Character limits per Apple App Store:
- name.txt: ≤30
- subtitle.txt: ≤30
- keywords.txt: ≤100 (comma-separated, no spaces)
- promotional_text.txt: ≤170
- description.txt: ≤4000

Locale strategy:
- English variants (en-AU/en-CA/en-GB) COPY en-US — don't re-translate
- es-MX can mirror es-ES; fr-CA can mirror fr-FR (or maintain separate if
  Canadian French / LATAM Spanish differs meaningfully)
- For non-Latin scripts (ja/ko/zh/ar/he/hi/th), keep prose tight — 80-char
  promo renders at 15-25 visible chars
- Keyword field: keep English loanwords (paycheck, freelance, BMI, loan,
  mortgage) for non-Latin locales since users search in English even when
  UI is in local language; translate to local for Latin-script European

Reference implementation: toss_app/automation_data/localize_metadata.py —
30 locales hand-translated, ~700 lines, runs in 1 second, writes 195 files.
"""
from pathlib import Path
import os

# Adjust for your project structure (relative to this script's location)
ROOT = Path(os.environ.get("TEAMZ_HOST_SITE_ROOT", Path(__file__).resolve().parent.parent))
METADATA = ROOT / "fastlane" / "metadata"


# Fill in each locale. Tuple order: (name, subtitle, keywords, promo, description)
# For locales set to None, they inherit from a parent (configured in _PARENTS below)
TRANSLATIONS: dict[str, tuple[str, str, str, str, str] | None] = {
    # English variants copy en-US (set below)
    "en-AU": None,
    "en-CA": None,
    "en-GB": None,

    # WESTERN EUROPEAN — fill in
    "de-DE": (
        "<APP NAME in German, ≤30 chars>",
        "<subtitle in German, ≤30>",
        "<comma,separated,keywords,in German,≤100>",
        "<promo text in German, ≤170>",
        "<full description in German, ≤4000>\n\nSection headers in German\n• Feature bullets"
    ),
    # "fr-FR": (...),
    # "es-ES": (...),
    # "it": (...),
    # "pt-PT": (...),
    # "pt-BR": (...),
    # "nl-NL": (...),
    # "ca": (...),

    # NORDIC — fill in
    # "da": (...), "sv": (...), "no": (...), "fi": (...),

    # OTHER EUROPEAN — fill in
    # "pl": (...), "cs": (...), "sk": (...), "hu": (...), "ro": (...),
    # "hr": (...), "el": (...), "tr": (...),

    # SLAVIC — fill in
    # "ru": (...), "uk": (...),

    # ASIAN — fill in (keep prose tight for CJK)
    # "ja": (...), "ko": (...),
    # "zh-Hans": (...), "zh-Hant": (...),
    # "th": (...), "vi": (...), "id": (...), "ms": (...), "hi": (...),

    # RTL — fill in
    # "ar-SA": (...), "he": (...),

    # fr-CA / es-MX can mirror parents (see _PARENTS)
}

# Locales that copy from a parent's translation
_PARENTS = {
    "en-AU": "en-US",
    "en-CA": "en-US",
    "en-GB": "en-US",
    "fr-CA": "fr-FR",
    "es-MX": "es-ES",
}


def write_locale(locale: str, fields: tuple):
    name, subtitle, keywords, promo, description = fields
    d = METADATA / locale
    if not d.is_dir():
        return f"  [skip] {locale}: dir missing"
    # Enforce char limits
    assert len(name) <= 30, f"{locale} name over 30: {len(name)}"
    assert len(subtitle) <= 30, f"{locale} subtitle over 30: {len(subtitle)}"
    assert len(keywords) <= 100, f"{locale} keywords over 100: {len(keywords)}"
    assert len(promo) <= 170, f"{locale} promo over 170: {len(promo)}"
    assert len(description) <= 4000, f"{locale} desc over 4000: {len(description)}"
    (d / "name.txt").write_text(name, encoding="utf-8")
    (d / "subtitle.txt").write_text(subtitle, encoding="utf-8")
    (d / "keywords.txt").write_text(keywords, encoding="utf-8")
    (d / "promotional_text.txt").write_text(promo, encoding="utf-8")
    (d / "description.txt").write_text(description, encoding="utf-8")
    return f"  [ok] {locale}: n={len(name)} s={len(subtitle)} k={len(keywords)} p={len(promo)} d={len(description)}"


def main():
    # Assumes en-US is already written (source of truth) — the translate step
    # fills everything else. If en-US is also in TRANSLATIONS, write it.
    en_us_source = TRANSLATIONS.get("en-US")
    if en_us_source:
        print(write_locale("en-US", en_us_source))

    # Copy parents
    for child, parent in _PARENTS.items():
        parent_fields = TRANSLATIONS.get(parent)
        if parent_fields is None:
            # parent might be en-US read from filesystem
            en_us_dir = METADATA / parent
            if en_us_dir.is_dir():
                for f in ("name.txt", "subtitle.txt", "keywords.txt",
                          "promotional_text.txt", "description.txt"):
                    src = en_us_dir / f
                    if src.exists() and (METADATA / child).is_dir():
                        (METADATA / child / f).write_text(
                            src.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"  [copy] {child} ← {parent}")
        else:
            print(write_locale(child, parent_fields))

    # Translated locales
    for loc, fields in TRANSLATIONS.items():
        if fields is not None and loc not in _PARENTS and loc != "en-US":
            print(write_locale(loc, fields))


if __name__ == "__main__":
    main()
