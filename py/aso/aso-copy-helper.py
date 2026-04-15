#!/usr/bin/env python3
"""
ASO Copy Helper — generates an HTML page with copy buttons for Play Console paste.

Reads listing JSON files from TEAMZ_DATA_DIR and creates a single-page HTML
with one-click copy buttons for title, short description, full description,
and all locale translations. Opens automatically in browser.

Usage::

    python3 py/aso/aso-copy-helper.py
    python3 py/aso/aso-copy-helper.py --open    # auto-open in browser (default)
    python3 py/aso/aso-copy-helper.py --no-open # just generate the file
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import webbrowser
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

# Play Console language code mapping
LANG_MAP = {
    "en": "en-US", "en-AU": "en-AU", "en-CA": "en-CA", "en-GB": "en-GB",
    "ar": "ar", "ca": "ca", "zh-Hans": "zh-CN", "zh-Hant": "zh-TW",
    "hr": "hr", "cs": "cs-CZ", "da": "da-DK", "nl": "nl-NL",
    "fi": "fi-FI", "fr": "fr-FR", "fr-CA": "fr-CA", "de": "de-DE",
    "el": "el-GR", "he": "iw-IL", "hi": "hi-IN", "hu": "hu-HU",
    "id": "id", "it": "it-IT", "ja": "ja-JP", "ko": "ko-KR",
    "ms": "ms", "nb": "no-NO", "pl": "pl-PL", "pt-BR": "pt-BR",
    "pt-PT": "pt-PT", "ro": "ro", "ru": "ru-RU", "sk": "sk",
    "es-MX": "es-419", "es-ES": "es-ES", "sv": "sv-SE",
    "th": "th", "tr": "tr-TR", "uk": "uk", "vi": "vi",
}

LANG_NAMES = {
    "en": "English (US)", "en-AU": "English (AU)", "en-CA": "English (CA)", "en-GB": "English (UK)",
    "ar": "Arabic", "ca": "Catalan", "zh-Hans": "Chinese (Simplified)", "zh-Hant": "Chinese (Traditional)",
    "hr": "Croatian", "cs": "Czech", "da": "Danish", "nl": "Dutch",
    "fi": "Finnish", "fr": "French", "fr-CA": "French (Canada)", "de": "German",
    "el": "Greek", "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian",
    "id": "Indonesian", "it": "Italian", "ja": "Japanese", "ko": "Korean",
    "ms": "Malay", "nb": "Norwegian", "pl": "Polish", "pt-BR": "Portuguese (Brazil)",
    "pt-PT": "Portuguese (Portugal)", "ro": "Romanian", "ru": "Russian", "sk": "Slovak",
    "es-MX": "Spanish (Latin America)", "es-ES": "Spanish (Spain)", "sv": "Swedish",
    "th": "Thai", "tr": "Turkish", "uk": "Ukrainian", "vi": "Vietnamese",
}


def _escape(text: str) -> str:
    return html.escape(text).replace("\n", "\\n")


def _escape_display(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def generate_html() -> str:
    # Load data
    en_path = None
    for f in _DATA_DIR.glob("play-listing-*-en-US.json"):
        en_path = f
        break

    if not en_path:
        print(f"ERROR: No play-listing-*-en-US.json found in {_DATA_DIR}", file=sys.stderr)
        sys.exit(1)

    with open(en_path) as f:
        en = json.load(f)

    locales = {}
    locales_path = _DATA_DIR / "play-store-listings-all-locales.json"
    if locales_path.exists():
        with open(locales_path) as f:
            locales = json.load(f)

    descs = {}
    descs_path = _DATA_DIR / "play-store-full-descriptions-all-locales.json"
    if descs_path.exists():
        with open(descs_path) as f:
            descs = json.load(f)

    release_notes = {}
    for rn_path in _DATA_DIR.glob("release-notes-*.json"):
        with open(rn_path) as f:
            release_notes = json.load(f)
        break

    app_name = en.get("title", "App")

    # Build HTML
    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(app_name)} — Play Console Copy Helper</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 20px; max-width: 900px; margin: 0 auto; }}
h1 {{ color: #fff; margin-bottom: 8px; font-size: 24px; }}
.subtitle {{ color: #888; margin-bottom: 30px; font-size: 14px; }}
.section {{ background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 20px; margin-bottom: 16px; }}
.section-title {{ color: #aaa; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }}
.field-label {{ color: #4fc3f7; font-weight: 600; font-size: 14px; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; }}
.char-count {{ color: #666; font-size: 12px; font-weight: 400; }}
.field-value {{ background: #111; border: 1px solid #2a2a2a; border-radius: 8px; padding: 12px; margin-bottom: 12px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; max-height: 300px; overflow-y: auto; position: relative; }}
.copy-btn {{ background: #4fc3f7; color: #000; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
.copy-btn:hover {{ background: #81d4fa; }}
.copy-btn.copied {{ background: #66bb6a; }}
.locale-grid {{ display: grid; grid-template-columns: 1fr; gap: 8px; }}
.locale-item {{ background: #111; border: 1px solid #2a2a2a; border-radius: 8px; padding: 12px; }}
.locale-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
.locale-name {{ color: #4fc3f7; font-weight: 600; font-size: 13px; }}
.locale-code {{ color: #666; font-size: 11px; }}
.locale-fields {{ font-size: 13px; }}
.locale-fields .label {{ color: #888; font-size: 11px; }}
.locale-fields .value {{ margin-bottom: 6px; }}
details {{ margin-top: 8px; }}
summary {{ cursor: pointer; color: #4fc3f7; font-size: 13px; padding: 8px 0; }}
.search-box {{ width: 100%; padding: 10px 16px; background: #111; border: 1px solid #333; border-radius: 8px; color: #e0e0e0; font-size: 14px; margin-bottom: 16px; }}
.search-box:focus {{ outline: none; border-color: #4fc3f7; }}
.hidden {{ display: none !important; }}
.stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
.stat {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 12px 16px; flex: 1; text-align: center; }}
.stat-num {{ font-size: 24px; font-weight: 700; color: #4fc3f7; }}
.stat-label {{ font-size: 11px; color: #888; text-transform: uppercase; }}
.copy-all-btn {{ background: #66bb6a; color: #000; border: none; border-radius: 8px; padding: 10px 24px; font-size: 14px; font-weight: 600; cursor: pointer; width: 100%; margin-top: 12px; }}
.copy-all-btn:hover {{ background: #81c784; }}
</style>
</head>
<body>
<h1>{html.escape(app_name)} — Play Console Copy Helper</h1>
<p class="subtitle">Click any "Copy" button → paste directly into Play Console. Generated from ASO data.</p>
""")

    # Stats
    locale_count = len(locales)
    desc_count = len(descs)
    parts.append(f"""
<div class="stats">
  <div class="stat"><div class="stat-num">1</div><div class="stat-label">Default Listing</div></div>
  <div class="stat"><div class="stat-num">{locale_count}</div><div class="stat-label">Locale Titles</div></div>
  <div class="stat"><div class="stat-num">{desc_count}</div><div class="stat-label">Full Descriptions</div></div>
</div>
""")

    # English (default) listing
    title = en.get("title", "")
    short = en.get("shortDescription", "")
    full = en.get("fullDescription", "")

    parts.append(f"""
<div class="section">
  <div class="section-title">Default Store Listing (en-US)</div>

  <div class="field-label">App name <span class="char-count">{len(title)}/30 chars</span></div>
  <div class="field-value" id="title">{_escape_display(title)}</div>
  <button class="copy-btn" onclick="copyField('title', this)">Copy Title</button>

  <br><br>
  <div class="field-label">Short description <span class="char-count">{len(short)}/80 chars</span></div>
  <div class="field-value" id="short">{_escape_display(short)}</div>
  <button class="copy-btn" onclick="copyField('short', this)">Copy Short Description</button>

  <br><br>
  <div class="field-label">Full description <span class="char-count">{len(full)}/4000 chars</span></div>
  <div class="field-value" id="full">{_escape_display(full)}</div>
  <button class="copy-btn" onclick="copyField('full', this)">Copy Full Description</button>
</div>
""")

    # Release notes
    if release_notes:
        rn_version = release_notes.get("version", "")
        rn_locales = {k: v for k, v in release_notes.items() if k != "version"}
        if rn_locales:
            # Build Play Console paste-ready text (<locale>...</locale> tags)
            paste_lines = []
            over_limit = []
            for our_code in sorted(rn_locales.keys()):
                play_code = LANG_MAP.get(our_code, our_code)
                text = rn_locales[our_code]
                if len(text) > 500:
                    over_limit.append(f"{play_code} ({len(text)} chars)")
                paste_lines.append(f"<{play_code}>\n{text}\n</{play_code}>")
            paste_text = "\n".join(paste_lines)

            # Write the paste file to data_dir — companion to Apple's
            # release-notes-v{version}-paste.txt. Open + Cmd+A Cmd+C and paste
            # into Play Console → Release → Release notes bulk-locale input.
            play_paste_path = _DATA_DIR / f"play-release-notes-v{rn_version}-paste.txt"
            play_paste_path.write_text(paste_text + "\n", encoding="utf-8")
            print(f"  [ok] Wrote {play_paste_path.name} ({len(rn_locales)} locales)",
                  file=sys.stderr)

            warn_html = ""
            if over_limit:
                warn_html = f'<div style="color:#ef5350;margin-bottom:8px">⚠️ Over 500 chars: {html.escape(", ".join(over_limit))}</div>'

            parts.append(f"""
<div class="section">
  <div class="section-title">Release Notes (v{html.escape(rn_version)}) — {len(rn_locales)} locales</div>
  {warn_html}
  <p style="color:#888;font-size:13px;margin-bottom:12px">Copy the block below and paste directly into Play Console → Release → Release notes. All locales in one paste.</p>
  <div class="field-value" id="release-notes-paste" style="max-height:400px">{_escape_display(paste_text)}</div>
  <button class="copy-btn" onclick="copyField('release-notes-paste', this)">Copy All Release Notes (paste into Play Console)</button>
  <button class="copy-all-btn" onclick="downloadReleaseNotes()" style="margin-top:8px;background:#4fc3f7">Download as .txt</button>
</div>
""")

            # Also show per-locale cards for individual copy
            parts.append(f"""
<div class="section">
  <div class="section-title">Release Notes — Per Locale ({len(rn_locales)} locales)</div>
  <div class="locale-grid" id="rn-grid">
""")
            for our_code in sorted(rn_locales.keys()):
                play_code = LANG_MAP.get(our_code, our_code)
                lang_name = LANG_NAMES.get(our_code, our_code)
                text = rn_locales[our_code]
                char_warn = ' style="color:#ef5350"' if len(text) > 500 else ""
                item_id = f"rn_{our_code.replace('-', '_')}"
                parts.append(f"""
    <div class="locale-item" data-locale="{our_code}" data-name="{lang_name.lower()}" data-play="{play_code}">
      <div class="locale-header">
        <span class="locale-name">{html.escape(lang_name)}</span>
        <span class="locale-code">{html.escape(play_code)} — <span{char_warn}>{len(text)}/500 chars</span></span>
      </div>
      <div class="field-value" id="{item_id}" style="max-height:200px">{_escape_display(text)}</div>
      <button class="copy-btn" onclick="copyField('{item_id}', this)">Copy</button>
    </div>
""")
            parts.append("  </div>\n</div>\n")

    # All locale translations
    if locales:
        parts.append(f"""
<div class="section">
  <div class="section-title">All Locale Translations ({locale_count} locales)</div>
  <input type="text" class="search-box" placeholder="Search locales (e.g. German, ja-JP, French...)" oninput="filterLocales(this.value)">
  <div class="locale-grid" id="locale-grid">
""")

        for our_code in sorted(locales.keys()):
            if our_code == "en":
                continue
            play_code = LANG_MAP.get(our_code, our_code)
            lang_name = LANG_NAMES.get(our_code, our_code)
            loc = locales[our_code]
            loc_title = loc.get("title", "")
            loc_short = loc.get("shortDescription", "")
            loc_full = descs.get(our_code, "")

            item_id = our_code.replace("-", "_")
            parts.append(f"""
    <div class="locale-item" data-locale="{our_code}" data-name="{lang_name.lower()}" data-play="{play_code}">
      <div class="locale-header">
        <span class="locale-name">{html.escape(lang_name)}</span>
        <span class="locale-code">{html.escape(play_code)}</span>
      </div>
      <div class="locale-fields">
        <div class="label">Title ({len(loc_title)} chars)</div>
        <div class="value" id="t_{item_id}">{_escape_display(loc_title)}</div>
        <button class="copy-btn" onclick="copyField('t_{item_id}', this)" style="margin-bottom:6px">Copy Title</button>

        <div class="label">Short ({len(loc_short)} chars)</div>
        <div class="value" id="s_{item_id}">{_escape_display(loc_short)}</div>
        <button class="copy-btn" onclick="copyField('s_{item_id}', this)" style="margin-bottom:6px">Copy Short</button>
""")
            if loc_full:
                parts.append(f"""
        <details>
          <summary>Full description ({len(loc_full)} chars)</summary>
          <div class="value field-value" id="d_{item_id}" style="margin-top:8px">{_escape_display(loc_full)}</div>
          <button class="copy-btn" onclick="copyField('d_{item_id}', this)">Copy Description</button>
        </details>
""")
            parts.append("      </div>\n    </div>\n")

        parts.append("  </div>\n</div>\n")

    # JavaScript
    parts.append("""
<script>
function copyField(id, btn) {
  const el = document.getElementById(id);
  if (!el) return;
  // Get text content (replace <br> with newlines)
  let text = el.innerHTML.replace(/<br\\s*\\/?>/gi, '\\n').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&nbsp;/g, ' ');
  // Remove any remaining HTML tags
  const tmp = document.createElement('div');
  tmp.innerHTML = text;
  text = tmp.textContent || tmp.innerText || '';

  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('copied'); }, 1500);
  });
}

function downloadReleaseNotes() {
  const el = document.getElementById('release-notes-paste');
  if (!el) return;
  let text = el.innerHTML.replace(/<br\\s*\\/?>/gi, '\\n').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&nbsp;/g, ' ');
  const tmp = document.createElement('div');
  tmp.innerHTML = text;
  text = tmp.textContent || tmp.innerText || '';
  const blob = new Blob([text], {type: 'text/plain'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'release-notes-paste.txt';
  a.click();
}

function filterLocales(query) {
  const q = query.toLowerCase().trim();
  document.querySelectorAll('.locale-item').forEach(item => {
    const locale = item.dataset.locale || '';
    const name = item.dataset.name || '';
    const play = item.dataset.play || '';
    const match = !q || locale.includes(q) || name.includes(q) || play.includes(q);
    item.classList.toggle('hidden', !match);
  });
}
</script>
</body>
</html>
""")

    return "".join(parts)


def generate_release_notes_paste() -> str | None:
    """Generate a Play Console paste-ready .txt with <locale> tags for release notes.

    Returns the output path, or None if no release notes found.
    Play Console format:  <en-US>\\ntext\\n</en-US>\\n<ar>\\ntext\\n</ar>...
    Validates each locale is ≤500 chars and warns on violations.
    """
    release_notes = {}
    for rn_path in _DATA_DIR.glob("release-notes-*.json"):
        with open(rn_path) as f:
            release_notes = json.load(f)
        break

    if not release_notes:
        return None

    version = release_notes.get("version", "")
    rn_locales = {k: v for k, v in release_notes.items() if k != "version"}
    if not rn_locales:
        return None

    lines = []
    over_limit = []
    for our_code in sorted(rn_locales.keys()):
        play_code = LANG_MAP.get(our_code, our_code)
        text = rn_locales[our_code]
        if len(text) > 500:
            over_limit.append((play_code, len(text)))
        lines.append(f"<{play_code}>\n{text}\n</{play_code}>")

    paste_text = "\n".join(lines) + "\n"

    suffix = f"-v{version}" if version else ""
    out_path = _DATA_DIR / f"release-notes{suffix}-paste.txt"
    out_path.write_text(paste_text, encoding="utf-8")

    if over_limit:
        print(f"  ⚠️  OVER 500 CHARS (Play Console will reject):")
        for code, chars in over_limit:
            print(f"     {code}: {chars} chars")
    print(f"  Release notes paste file: {out_path} ({len(rn_locales)} locales)")
    return str(out_path)


def main():
    parser = argparse.ArgumentParser(description="Generate HTML copy helper for Play Console store listing paste")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open in browser")
    args = parser.parse_args()

    html_content = generate_html()

    out_path = _DATA_DIR / "play-console-copy-helper.html"
    out_path.write_text(html_content, encoding="utf-8")
    print(f"Generated: {out_path}")

    # Also generate release notes paste .txt
    rn_path = generate_release_notes_paste()

    if not args.no_open:
        webbrowser.open(f"file://{out_path}")
        print("Opened in browser.")


if __name__ == "__main__":
    main()
