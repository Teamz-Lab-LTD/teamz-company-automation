#!/usr/bin/env python3
"""
ASO Metadata Localizer — auto-populate Fastlane iOS metadata for all 40 locales.

Reads master_keywords.csv (from aso-keyword-pipeline.py) + base English listing,
then for each Fastlane locale folder writes:
- keywords.txt (≤100 chars, comma-separated, locale-aware via iTunes autocomplete)
- subtitle.txt (≤30 chars)
- name.txt (≤30 chars)
- promotional_text.txt (≤170 chars)

Strategy per locale:
1. If `--translate` + `claude` CLI available → LLM-translate English base.
2. Else for keywords: run iTunes autocomplete with locale hl to re-rank the master
   keyword list in the local market and pack under 100 chars.
3. Else fallback: copy English (never leave slots empty — empty slots are worse
   than English for review).

Usage::

    python3 py/aso/aso-localize.py                 # locale-aware keywords only
    python3 py/aso/aso-localize.py --translate     # full LLM translation via claude CLI
    python3 py/aso/aso-localize.py --locales ja,ko # subset
    python3 py/aso/aso-localize.py --force         # overwrite non-empty files

Writes: fastlane/metadata/{locale}/{keywords,subtitle,name,promotional_text}.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _teamz_config import load_runtime  # noqa: E402

_ASO_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ASO_DIR)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_aso_common", os.path.join(_ASO_DIR, "_aso_common.py"))
_aso = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_aso)  # type: ignore

_CFG = load_runtime(os.path.join(os.path.dirname(_ASO_DIR), "_teamz_config.py"))
_DATA_DIR = Path(
    os.environ.get("TEAMZ_DATA_DIR", "")
    or _CFG.get("data_dir", "")
    or str(Path(_CFG["host_site_root"]) / "automation_data")
)
_PROJECT_ROOT = Path(_CFG.get("host_site_root", "."))
_FASTLANE_METADATA = _PROJECT_ROOT / "fastlane" / "metadata"

# Fastlane locale code → iTunes autocomplete hl code
FASTLANE_TO_HL = {
    "en-US": "en", "en-AU": "en", "en-GB": "en", "en-CA": "en",
    "ar-SA": "ar", "ca": "ca", "zh-Hans": "zh", "zh-Hant": "zh",
    "hr": "hr", "cs": "cs", "da": "da", "nl-NL": "nl", "fi": "fi",
    "fr-FR": "fr", "fr-CA": "fr", "de-DE": "de", "el": "el",
    "he": "he", "hi": "hi", "hu": "hu", "id": "id", "it": "it",
    "ja": "ja", "ko": "ko", "ms": "ms", "no": "no", "pl": "pl",
    "pt-BR": "pt", "pt-PT": "pt", "ro": "ro", "ru": "ru", "sk": "sk",
    "es-MX": "es", "es-ES": "es", "sv": "sv", "th": "th", "tr": "tr",
    "uk": "uk", "vi": "vi",
}

LIMITS = {"keywords.txt": 100, "subtitle.txt": 30, "name.txt": 30, "promotional_text.txt": 170}


def _load_master_keywords() -> list[str]:
    for name in ("master_keywords.csv", "ios_keywords.csv"):
        p = _DATA_DIR / name
        if not p.exists():
            continue
        rows = list(csv.DictReader(p.open(encoding="utf-8")))
        rows.sort(key=lambda r: float(r.get("score", 0) or 0), reverse=True)
        return [r.get("keyword", "").strip() for r in rows if r.get("keyword")]
    return []


def _pack_keywords(kws: list[str], limit: int = 100) -> str:
    """Pack keywords comma-separated under limit, greedy by order."""
    out: list[str] = []
    used = 0
    for k in kws:
        k = k.strip().lower()
        if not k or k in out:
            continue
        add = len(k) + (1 if out else 0)
        if used + add > limit:
            continue
        out.append(k)
        used += add
    return ",".join(out)


def _localized_keywords(master: list[str], hl: str) -> str:
    """Re-rank master keywords using per-locale autocomplete signal, pack to 100."""
    if hl == "en" or not master:
        return _pack_keywords(master)
    # Take top-10 English seeds, query localized autocomplete for each
    local_terms: list[str] = []
    seen = set()
    for seed in master[:8]:
        try:
            hints = _aso.apple_autocomplete(seed) or []
        except Exception:
            hints = []
        for h in hints[:5]:
            low = h.strip().lower()
            if low and low not in seen and len(low) <= 40:
                seen.add(low)
                local_terms.append(low)
    # Mix: localized discoveries first, then original master tail
    combined = local_terms + [m for m in master if m.lower() not in seen]
    return _pack_keywords(combined)


def _read_english(name: str) -> str:
    p = _FASTLANE_METADATA / "en-US" / name
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def _translate_claude(text: str, locale: str, field: str, limit: int) -> str | None:
    if not text:
        return None
    which = subprocess.run(["which", "claude"], capture_output=True, text=True)
    if which.returncode != 0 or not which.stdout.strip():
        return None
    prompt = (
        f"Translate this App Store {field} to locale '{locale}'. "
        f"Max {limit} characters. Natural, not literal. "
        f"Output ONLY the translation, no quotes, no preamble.\n\n{text}"
    )
    try:
        r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=45)
        out = (r.stdout or "").strip().strip('"').strip("'")
        if out and len(out) <= limit:
            return out
    except Exception:
        pass
    return None


def _write(path: Path, content: str, force: bool) -> str:
    """Returns status: written/skipped/unchanged."""
    existing = path.read_text(encoding="utf-8").strip() if path.exists() else ""
    if existing and not force:
        return "skipped"
    if existing == content.strip():
        return "unchanged"
    path.write_text(content + "\n", encoding="utf-8")
    return "written"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--translate", action="store_true",
                    help="Use `claude` CLI for full translation (else keyword-only localization)")
    ap.add_argument("--locales", default=None,
                    help="Comma-separated Fastlane locales (default: all non-empty metadata dirs)")
    ap.add_argument("--force", action="store_true", help="Overwrite non-empty files")
    args = ap.parse_args()

    if not _FASTLANE_METADATA.exists():
        print(f"[ERROR] {_FASTLANE_METADATA} does not exist — is this an iOS project with Fastlane?",
              file=sys.stderr)
        return 1

    master = _load_master_keywords()
    if not master:
        print("[WARN] master_keywords.csv/ios_keywords.csv not found in data_dir — "
              "run `aso-keyword-pipeline.py` first. Will still translate other fields.",
              file=sys.stderr)

    en_subtitle = _read_english("subtitle.txt")
    en_name = _read_english("name.txt")
    en_promo = _read_english("promotional_text.txt")

    if args.locales:
        locales = [l.strip() for l in args.locales.split(",") if l.strip()]
    else:
        locales = sorted([d.name for d in _FASTLANE_METADATA.iterdir() if d.is_dir()])

    stats = {"written": 0, "skipped": 0, "unchanged": 0}
    for loc in locales:
        d = _FASTLANE_METADATA / loc
        if not d.is_dir():
            continue
        hl = FASTLANE_TO_HL.get(loc, "en")
        is_english = loc.startswith("en-")

        # keywords.txt
        if master:
            kw_content = _pack_keywords(master) if is_english else _localized_keywords(master, hl)
            if kw_content:
                s = _write(d / "keywords.txt", kw_content, args.force)
                stats[s] += 1

        # subtitle/name/promotional_text — translate from English or copy
        for field, english, limit in (
            ("subtitle.txt", en_subtitle, LIMITS["subtitle.txt"]),
            ("name.txt", en_name, LIMITS["name.txt"]),
            ("promotional_text.txt", en_promo, LIMITS["promotional_text.txt"]),
        ):
            if not english:
                continue
            if is_english:
                content = english[:limit]
            else:
                content = None
                if args.translate:
                    content = _translate_claude(english, hl, field.replace(".txt", ""), limit)
                content = content or english[:limit]
            s = _write(d / field, content, args.force)
            stats[s] += 1

        print(f"  [{loc}] hl={hl} done", file=sys.stderr)

    print(f"\n  [ok] {stats['written']} written, {stats['skipped']} skipped "
          f"(existing, use --force), {stats['unchanged']} unchanged", file=sys.stderr)
    print(f"  [next] Review fastlane/metadata/*/keywords.txt, then "
          f"`cd ios && bundle exec fastlane deliver --skip_screenshots --skip_binary_upload`",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
