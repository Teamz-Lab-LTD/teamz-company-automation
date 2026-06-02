#!/usr/bin/env python3
"""
build-launch-content.py — Product Hunt launch kit for any Teamz Lab app.

Reads the app's existing artifacts and produces paste-ready PH launch content:

  Inputs (auto-discovered, all optional except --app-slug):
    - teamz-lab-generic-landing-pages/src/content/apps/<slug>.md       (canonical copy)
    - teamz-lab-generic-landing-pages/public/<slug>/logo.png           (thumbnail source)
    - teamz-lab-generic-landing-pages/public/<slug>/og.png             (first gallery card)
    - teamz-lab-generic-landing-pages/public/<slug>/screenshots/*.jpg  (gallery sources)
    - <app-repo>/fastlane/metadata/en-US/{name,subtitle,promotional_text}.txt

  Outputs (under <app-repo>/automation_data/product_hunt/):
    - launch-content.auto.md     — kit-generated minimal copy (rewritten each run)
    - launch-content.md          — ONLY created if missing (canonical, hand-curated)
    - thumbnail-240.png          — 240x240 (PH thumbnail spec)
    - gallery/01-og-card.png     — 1270x760 OG/social preview
    - gallery/02..05*.png        — 1270x760 landscape cards composed from
                                    portrait screenshots on brand bg

Usage:
    python build-launch-content.py --app-slug top3picks
    python build-launch-content.py --app-slug top3picks --landing-repo /path/to/landing
    python build-launch-content.py --app-slug top3picks --dry-run
    python build-launch-content.py --app-slug top3picks --force-canonical  # overwrite launch-content.md too

Default behavior NEVER clobbers a hand-edited launch-content.md — kit only
writes launch-content.auto.md and (if no canonical exists) seeds launch-content.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("ERROR: Pillow required. pip install Pillow", file=sys.stderr)
    sys.exit(1)


DEFAULT_LANDING_REPO = Path(
    "/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects/teamz-lab-generic-landing-pages"
)

# Brand defaults (override per-app via .teamz-automation.env or CLI)
BRAND_BG_DEFAULT = "#D9FE06"   # Teamz neon yellow (Top3Picks brand)
BRAND_FG_DEFAULT = "#0A0A0A"   # high-contrast on neon
BRAND_ACCENT_DEFAULT = "#FF3D5A"

PH_THUMB_SIZE = (240, 240)
PH_GALLERY_SIZE = (1270, 760)


@dataclass
class AppContext:
    slug: str
    app_repo: Path
    landing_repo: Path

    # Resolved from landing page yaml
    app_name: str = ""
    metaTitle: str = ""
    tagline: str = ""
    shortDescription: str = ""
    longDescription: str = ""
    primaryKeyword: str = ""
    play_url: str = ""
    apple_url: str = ""
    category: str = "Shopping"
    landing_url: str = ""

    # Resolved from fastlane (Apple en-US)
    apple_name: str = ""
    apple_subtitle: str = ""
    apple_promo: str = ""

    # Brand
    brand_bg: str = BRAND_BG_DEFAULT
    brand_fg: str = BRAND_FG_DEFAULT
    brand_accent: str = BRAND_ACCENT_DEFAULT

    # Files
    logo_path: Optional[Path] = None
    og_path: Optional[Path] = None
    screenshot_paths: list[Path] = field(default_factory=list)

    @property
    def out_dir(self) -> Path:
        return self.app_repo / "automation_data" / "product_hunt"

    @property
    def gallery_dir(self) -> Path:
        return self.out_dir / "gallery"


# ---------- discovery ----------

def parse_yaml_frontmatter(md_path: Path) -> dict:
    """Tiny YAML-frontmatter parser — only handles the subset our content uses."""
    if not md_path.exists():
        return {}
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    block = m.group(1)
    out: dict = {}
    cur_key = None
    cur_list: Optional[list] = None
    for raw in block.split("\n"):
        if not raw.strip():
            continue
        if raw.startswith("  - ") and cur_list is not None:
            cur_list.append(raw[4:].strip().strip("'\""))
            continue
        if raw.startswith("  ") and cur_key:
            # nested object field — flatten as "parent.child"
            sub = raw.strip()
            if ":" in sub:
                sk, sv = sub.split(":", 1)
                out[f"{cur_key}.{sk.strip()}"] = sv.strip().strip("'\"")
            continue
        if ":" in raw and not raw.startswith(" "):
            cur_list = None
            k, v = raw.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v == "":
                # could be list or nested object
                cur_key = k
                cur_list = []
                out[k] = cur_list
            elif v == "|":
                cur_key = k
                # gather indented block
                continue
            else:
                cur_key = k
                out[k] = v.strip("'\"")
    return out


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def discover(slug: str, app_repo: Path, landing_repo: Path,
             brand_bg: Optional[str], brand_fg: Optional[str]) -> AppContext:
    ctx = AppContext(slug=slug, app_repo=app_repo, landing_repo=landing_repo)

    if brand_bg:
        ctx.brand_bg = brand_bg
    if brand_fg:
        ctx.brand_fg = brand_fg

    landing_md = landing_repo / "src" / "content" / "apps" / f"{slug}.md"
    fm = parse_yaml_frontmatter(landing_md)
    ctx.app_name = fm.get("appName", slug)
    ctx.metaTitle = fm.get("metaTitle", "")
    ctx.tagline = fm.get("tagline", "")
    ctx.shortDescription = fm.get("shortDescription", "")
    ctx.primaryKeyword = fm.get("primaryKeyword", "")
    ctx.play_url = fm.get("playStoreUrl", "")
    ctx.apple_url = fm.get("appStoreUrl", "")
    ctx.category = fm.get("category", "Shopping")
    ctx.landing_url = f"https://apps.teamzlab.com/{slug}/"

    # Fastlane Apple metadata
    fl_en = app_repo / "fastlane" / "metadata" / "en-US"
    ctx.apple_name = read_text(fl_en / "name.txt")
    ctx.apple_subtitle = read_text(fl_en / "subtitle.txt")
    ctx.apple_promo = read_text(fl_en / "promotional_text.txt")

    # Image assets
    pub = landing_repo / "public" / slug
    if (pub / "logo.png").exists():
        ctx.logo_path = pub / "logo.png"
    if (pub / "og.png").exists():
        ctx.og_path = pub / "og.png"
    ss_dir = pub / "screenshots"
    if ss_dir.exists():
        ctx.screenshot_paths = sorted(
            list(ss_dir.glob("*.jpg")) + list(ss_dir.glob("*.png"))
        )[:8]

    return ctx


# ---------- image generation ----------

def load_font(size: int) -> ImageFont.FreeTypeFont:
    """Try common system fonts; fall back to default bitmap."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFCompact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make_thumbnail(ctx: AppContext) -> Path:
    """240x240 — paste app logo on brand bg if logo has transparency, else center-crop logo."""
    out = ctx.out_dir / "thumbnail-240.png"
    bg = Image.new("RGB", PH_THUMB_SIZE, ctx.brand_bg)
    if ctx.logo_path and ctx.logo_path.exists():
        logo = Image.open(ctx.logo_path).convert("RGBA")
        # Fit logo inside ~70% of thumbnail
        target = int(min(PH_THUMB_SIZE) * 0.78)
        logo.thumbnail((target, target), Image.LANCZOS)
        x = (PH_THUMB_SIZE[0] - logo.width) // 2
        y = (PH_THUMB_SIZE[1] - logo.height) // 2
        bg.paste(logo, (x, y), logo)
    else:
        # Text fallback
        draw = ImageDraw.Draw(bg)
        font = load_font(64)
        initials = "".join([w[0] for w in ctx.app_name.split()[:2]]).upper() or "T3P"
        bbox = draw.textbbox((0, 0), initials, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((PH_THUMB_SIZE[0] - w) / 2, (PH_THUMB_SIZE[1] - h) / 2 - 8),
                  initials, fill=ctx.brand_fg, font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    bg.save(out, "PNG", optimize=True)
    return out


def make_og_card(ctx: AppContext) -> Path:
    """First gallery card — re-use og.png if available (upscale to 1270x760), else compose."""
    out = ctx.gallery_dir / "01-og-card.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    if ctx.og_path and ctx.og_path.exists():
        og = Image.open(ctx.og_path).convert("RGB")
        # Letterbox into 1270x760 (preserve aspect, brand bg around)
        canvas = Image.new("RGB", PH_GALLERY_SIZE, ctx.brand_bg)
        ratio = min(PH_GALLERY_SIZE[0] / og.width, PH_GALLERY_SIZE[1] / og.height)
        new_w, new_h = int(og.width * ratio), int(og.height * ratio)
        og_resized = og.resize((new_w, new_h), Image.LANCZOS)
        x = (PH_GALLERY_SIZE[0] - new_w) // 2
        y = (PH_GALLERY_SIZE[1] - new_h) // 2
        canvas.paste(og_resized, (x, y))
        canvas.save(out, "PNG", optimize=True)
        return out
    # Fallback — render text card
    canvas = Image.new("RGB", PH_GALLERY_SIZE, ctx.brand_bg)
    draw = ImageDraw.Draw(canvas)
    font_big = load_font(96)
    font_sm = load_font(42)
    headline = (ctx.primaryKeyword or ctx.app_name).upper()
    draw.text((80, 280), headline, fill=ctx.brand_fg, font=font_big)
    sub = ctx.apple_subtitle or ctx.tagline[:120]
    draw.text((80, 420), sub, fill=ctx.brand_fg, font=font_sm)
    canvas.save(out, "PNG", optimize=True)
    return out


def make_gallery_card(ctx: AppContext, idx: int, ss_path: Path,
                      headline: str, sub: str) -> Path:
    """Compose portrait screenshot onto 1270x760 brand bg with headline + subline."""
    out = ctx.gallery_dir / f"{idx:02d}-{headline.lower().replace(' ', '-')[:40]}.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    canvas = Image.new("RGB", PH_GALLERY_SIZE, ctx.brand_bg)
    draw = ImageDraw.Draw(canvas)

    # Screenshot on right side, scaled to fit height with padding
    ss = Image.open(ss_path).convert("RGB")
    target_h = PH_GALLERY_SIZE[1] - 80  # 40px top/bottom padding
    ratio = target_h / ss.height
    new_w, new_h = int(ss.width * ratio), target_h
    ss_resized = ss.resize((new_w, new_h), Image.LANCZOS)
    ss_x = PH_GALLERY_SIZE[0] - new_w - 60
    ss_y = (PH_GALLERY_SIZE[1] - new_h) // 2
    canvas.paste(ss_resized, (ss_x, ss_y))

    # Headline + sub on left
    text_x = 70
    text_max_w = ss_x - text_x - 40
    font_big = load_font(64)
    font_sm = load_font(30)

    # word-wrap headline
    def wrap(text: str, font, max_w: int) -> list[str]:
        words = text.split()
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            bbox = draw.textbbox((0, 0), trial, font=font)
            if bbox[2] - bbox[0] <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    hl_lines = wrap(headline, font_big, text_max_w)
    y_cur = PH_GALLERY_SIZE[1] // 2 - (len(hl_lines) * 70) // 2 - 80
    for line in hl_lines:
        draw.text((text_x, y_cur), line, fill=ctx.brand_fg, font=font_big)
        y_cur += 72

    y_cur += 20
    sub_lines = wrap(sub, font_sm, text_max_w)
    for line in sub_lines[:3]:
        draw.text((text_x, y_cur), line, fill=ctx.brand_fg, font=font_sm)
        y_cur += 38

    canvas.save(out, "PNG", optimize=True)
    return out


def generate_gallery(ctx: AppContext) -> list[Path]:
    """Generate up to 5 gallery cards. Slot 1 = OG. Slots 2-5 = screenshots + text."""
    outputs = [make_og_card(ctx)]

    # Pick up to 4 screenshots for slots 2-5
    captions = [
        ("3 picks, not 30 tabs", "AI compares Amazon, Best Buy, Walmart, Flipkart, Daraz — hands back 3."),
        ("Side-by-side winner", "Tap two picks. See the winner with explained reasoning."),
        ("AI pros + cons per pick", "No more scrolling 200 reviews. AI summarizes what matters."),
        ("Gift finder + budget mode", "Type the budget. AI respects it. 160+ currencies, auto-detected."),
    ]
    for i, ss in enumerate(ctx.screenshot_paths[:4]):
        if i >= len(captions):
            break
        headline, sub = captions[i]
        outputs.append(make_gallery_card(ctx, i + 2, ss, headline, sub))

    return outputs


# ---------- copy generation ----------

def truncate(s: str, n: int) -> str:
    s = s.strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def tagline_candidates(ctx: AppContext) -> list[str]:
    base = ctx.apple_subtitle or ctx.primaryKeyword or "AI shopping assistant"
    cands = [
        f"AI picks 3 best products for your budget — skip 300 tabs",
        f"{ctx.primaryKeyword.title()} — type budget, AI picks 3" if ctx.primaryKeyword else None,
        f"Stuck shopping? Type budget. AI compares + picks your 3.",
        f"{base[:50]}",
    ]
    return [c for c in cands if c and len(c) <= 60][:4]


def description_500(ctx: AppContext) -> str:
    """Returns a 500-char-max paragraph anchored on the app's primary positioning."""
    if ctx.shortDescription and len(ctx.shortDescription) <= 500:
        return ctx.shortDescription
    if ctx.shortDescription:
        return truncate(ctx.shortDescription, 500)
    # Fallback assembly
    s = (
        f"{ctx.app_name} — {ctx.tagline}. "
        f"Free on iOS + Android. No affiliate links, no tracking, no signup."
    )
    return truncate(s, 500)


def render_launch_md(ctx: AppContext) -> str:
    taglines = tagline_candidates(ctx)
    desc = description_500(ctx)
    lines: list[str] = []
    a = lines.append

    a(f"# {ctx.app_name} — Product Hunt Launch (paste-ready)")
    a("")
    a(f"App: **{ctx.apple_name or ctx.app_name}**")
    if ctx.apple_url:
        a(f"App Store: {ctx.apple_url}")
    if ctx.play_url:
        a(f"Google Play: {ctx.play_url}")
    if ctx.landing_url:
        a(f"Landing: {ctx.landing_url}")
    a("Maker: Teamz Lab LTD")
    a("")
    a("---\n")
    a("## 1. Main info\n")
    a(f"### Name (≤40 chars)")
    a(f"Recommended: `{(ctx.apple_name or ctx.app_name)[:40]}`")
    a("")
    a(f"### Tagline (≤60 chars) — pick one")
    for i, t in enumerate(taglines):
        marker = " *(recommended)*" if i == 0 else ""
        a(f"- ({len(t)} chars){marker}: `{t}`")
    a("")
    a("### Description (≤500 chars)")
    a("```")
    a(desc)
    a("```")
    a(f"({len(desc)} chars)\n")
    a("### Launch tags (3 max)")
    a(f"1. **{ctx.category}**")
    a("2. **Artificial Intelligence**")
    a("3. **iOS** *(or Android — pick the platform you want to anchor)*")
    a("")
    a("### Links field")
    if ctx.apple_url:
        a(f"- {ctx.apple_url}")
    if ctx.play_url:
        a(f"- {ctx.play_url}")
    if ctx.landing_url:
        a(f"- {ctx.landing_url}")
    a("")
    a("---\n")
    a("## 2. Images & media\n")
    a("### Thumbnail (240×240)")
    a(f"File: `automation_data/product_hunt/thumbnail-240.png` (generated)\n")
    a("### Gallery (1270×760+, first = social preview)")
    a("Files in `automation_data/product_hunt/gallery/` in numeric order.\n")
    a("---\n")
    a("## 3. Makers")
    a("- Hunter & Maker: `@teamzlab_ltd` (both checkboxes ✓)")
    a("")
    a("---\n")
    a("## 4. Shoutouts (≥3)")
    a("- **Claude / Claude Code** — Anthropic. Used for ASO automation, copy iteration, screenshot composition pipeline.")
    a("- **Firebase** — Auth, Remote Config, Crashlytics, App Check.")
    a("- **RevenueCat** — monetization layer across iOS + Android.")
    a("- *(optional)* **Gemini API** — image edits inside store screenshots.")
    a("")
    a("---\n")
    a("## 5. Extras")
    a("- Pricing: **Free**")
    a("- Funding: **Bootstrapped**")
    a("- Promo code: *leave blank — app is free*")
    a("")
    a("---\n")
    a("## 6. First comment (paste into form)")
    a("```")
    a(f"Hi Product Hunt — Emon from Teamz Lab here 👋")
    a("")
    a(f"{ctx.app_name} started as a personal itch — I kept opening 20 tabs to gift-shop")
    a("and ended up overpaying or buying the wrong thing. Every \"best of\" article I read")
    a("turned out to be ranked by affiliate commission instead of by recipient fit.")
    a("")
    a(f"So we built the tool I wanted: type what you (or someone else) needs, set a budget,")
    a("let AI do the comparison — pull current prices across major stores, read the reviews,")
    a("score value-for-money, hand back exactly 3 picks with trade-offs explained.")
    a("")
    a("A few choices on purpose:")
    a("- **3 picks, never a list.** A list shifts the decision back to you.")
    a("- **No affiliate links.** The ranking is the recommendation, not the auction.")
    a("- **160+ currencies, auto-detected.** Respects local stores.")
    a("- **No account, no tracking.** Open and search.")
    a("")
    a("Free on iOS + Android. Would love feedback on whether \"3 picks\" feels like the right")
    a("ceiling or if you want 5. Drop your worst shopping query below — I'll run it and reply.")
    a("Thanks 🙏")
    a("```\n")
    a("---\n")
    a("## 7. Pre-launch checklist")
    a("- [ ] Tagline ≤ 60 chars")
    a("- [ ] Description ≤ 500 chars")
    a("- [ ] Thumbnail uploaded")
    a("- [ ] Gallery ≥ 3 images")
    a("- [ ] At least 3 shoutouts attached")
    a("- [ ] First comment drafted")
    a("- [ ] Launch day: **Tuesday or Wednesday** (highest PH traffic)")
    a("- [ ] Notify supporter network 30 min before 00:00 PT")
    a("")
    a("---\n")
    a(f"*Generated by `py/product-hunt/build-launch-content.py` for `{ctx.slug}`.*")
    return "\n".join(lines) + "\n"


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-slug", required=True,
                    help="App slug as used in landing-pages content (e.g. top3picks)")
    ap.add_argument("--app-repo", default=None,
                    help="App repo root (default: cwd)")
    ap.add_argument("--landing-repo", default=str(DEFAULT_LANDING_REPO),
                    help="teamz-lab-generic-landing-pages root")
    ap.add_argument("--brand-bg", default=None,
                    help=f"Hex bg color (default {BRAND_BG_DEFAULT})")
    ap.add_argument("--brand-fg", default=None,
                    help=f"Hex fg color (default {BRAND_FG_DEFAULT})")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would be generated; write nothing")
    ap.add_argument("--skip-images", action="store_true",
                    help="Only generate launch-content.md, skip Pillow image work")
    ap.add_argument("--force-canonical", action="store_true",
                    help="Overwrite launch-content.md even if it already exists "
                         "(default: never touch canonical file once created)")
    args = ap.parse_args()

    app_repo = Path(args.app_repo) if args.app_repo else Path.cwd()
    landing_repo = Path(args.landing_repo)

    if not landing_repo.exists():
        print(f"ERROR: landing repo not found: {landing_repo}", file=sys.stderr)
        sys.exit(1)

    ctx = discover(
        slug=args.app_slug,
        app_repo=app_repo,
        landing_repo=landing_repo,
        brand_bg=args.brand_bg,
        brand_fg=args.brand_fg,
    )

    print(f"=== Product Hunt launch builder ===")
    print(f"  slug       : {ctx.slug}")
    print(f"  app_repo   : {ctx.app_repo}")
    print(f"  landing    : {ctx.landing_repo}")
    print(f"  app_name   : {ctx.app_name}")
    print(f"  apple_name : {ctx.apple_name}")
    print(f"  primary kw : {ctx.primaryKeyword}")
    print(f"  logo       : {ctx.logo_path}")
    print(f"  og.png     : {ctx.og_path}")
    print(f"  screenshots: {len(ctx.screenshot_paths)} found")
    print(f"  out_dir    : {ctx.out_dir}")
    print()

    if args.dry_run:
        print("[dry-run] no files written")
        return

    ctx.out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy
    rendered = render_launch_md(ctx)
    auto_path = ctx.out_dir / "launch-content.auto.md"
    auto_path.write_text(rendered, encoding="utf-8")
    print(f"✓ wrote {auto_path} (kit-generated; rewritten each run)")

    canonical_path = ctx.out_dir / "launch-content.md"
    if canonical_path.exists() and not args.force_canonical:
        print(f"↷ kept {canonical_path} (hand-curated — pass --force-canonical to overwrite)")
    else:
        canonical_path.write_text(rendered, encoding="utf-8")
        print(f"✓ wrote {canonical_path} (seeded canonical; safe to hand-edit, future runs won't touch it)")

    if args.skip_images:
        print("[--skip-images] image generation skipped")
        return

    # 2. Thumbnail
    thumb = make_thumbnail(ctx)
    print(f"✓ wrote {thumb} (240×240)")

    # 3. Gallery
    if not ctx.screenshot_paths and not ctx.og_path:
        print("WARN: no og.png or screenshots found — skipping gallery")
        return
    gallery = generate_gallery(ctx)
    for g in gallery:
        print(f"✓ wrote {g} (1270×760)")

    print()
    print(f"Done. Paste content from {md_path} into Product Hunt launch form.")
    print(f"Upload thumbnail + gallery files from {ctx.out_dir}/")


if __name__ == "__main__":
    main()
