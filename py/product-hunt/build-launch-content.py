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

  STOP-RULE-001 compliance:
  ----------------------------
  Before any tagline/description/first-comment is emitted, this script:
    1. Detects product type (app | web | unknown)
    2. Audits data sources (master_keywords.csv, apple-store-keywords-en-US.json,
       aso-competitors-latest.json for apps; landing yaml + keyword-volume cache for web)
    3. If sources are MISSING or STALE (>14d), calls the underlying kit scripts to
       refresh: aso-keyword-pipeline.py, aso-competitors.py, build-keyword-volume.py
    4. Builds a winnability table per RULE-001 — emitted as section 0 of the
       paste-ready Markdown AND as `data-audit.json` for machine consumption
    5. Tagline + description are derived FROM that audit, not from assumption

  Outputs (under <app-repo>/automation_data/product_hunt/):
    - data-audit.json            — structured audit (kws + winnability + sources)
    - launch-content.auto.md     — kit-generated copy (rewritten each run)
    - launch-content.md          — ONLY created if missing (canonical, hand-curated)
    - thumbnail-240.png          — 240x240 (PH thumbnail spec)
    - gallery/01-og-card.png     — 1270x760 OG/social preview
    - gallery/02..05*.png        — 1270x760 landscape cards composed from
                                    portrait screenshots on brand bg

Usage:
    python build-launch-content.py --app-slug top3picks
    python build-launch-content.py --app-slug top3picks --landing-repo /path/to/landing
    python build-launch-content.py --app-slug top3picks --dry-run
    python build-launch-content.py --app-slug top3picks --force-canonical
    python build-launch-content.py --app-slug top3picks --no-refresh   # use existing data, skip fresh scripts
    python build-launch-content.py --app-slug top3picks --strict        # abort if winnability table can't be built

Default behavior NEVER clobbers a hand-edited launch-content.md — kit only
writes launch-content.auto.md and (if no canonical exists) seeds launch-content.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import textwrap
import time
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

    # Product type + data audit (set by detect_product_type + audit_data_sources)
    product_type: str = "unknown"  # "app" | "web" | "unknown"
    secondary_keywords: list[str] = field(default_factory=list)

    # Data audit results
    top_keywords: list[dict] = field(default_factory=list)  # [{keyword, score, source}]
    winnability_rows: list[dict] = field(default_factory=list)  # [{keyword, competitor, reviews, installs, verdict}]
    data_sources_used: list[str] = field(default_factory=list)
    data_sources_stale: list[str] = field(default_factory=list)
    data_sources_missing: list[str] = field(default_factory=list)
    fresh_calls_made: list[str] = field(default_factory=list)

    @property
    def out_dir(self) -> Path:
        return self.app_repo / "automation_data" / "product_hunt"

    @property
    def gallery_dir(self) -> Path:
        return self.out_dir / "gallery"

    @property
    def aso_data_dir(self) -> Path:
        return self.app_repo / "automation_data"

    @property
    def automation_kit_root(self) -> Path:
        return self.app_repo / "packages" / "team_mvp_kit" / "teamz-company-automation"


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


# ---------- product-type detection ----------

def detect_product_type(app_repo: Path) -> str:
    """app: native mobile (Flutter/RN/iOS/Android). web: SaaS / web product. unknown otherwise.

    Detection signals (checked in order):
      app   : pubspec.yaml | android/ | ios/ | fastlane/ at repo root
      web   : package.json + (next.config* | astro.config* | vite.config*) | index.html only
    """
    app_signals = [
        app_repo / "pubspec.yaml",
        app_repo / "android" / "app",
        app_repo / "ios" / "Runner",
        app_repo / "fastlane",
    ]
    if any(s.exists() for s in app_signals):
        return "app"

    web_signals = [
        app_repo / "package.json",
        app_repo / "next.config.js",
        app_repo / "next.config.mjs",
        app_repo / "next.config.ts",
        app_repo / "astro.config.mjs",
        app_repo / "vite.config.js",
        app_repo / "vite.config.ts",
    ]
    if any(s.exists() for s in web_signals):
        return "web"

    return "unknown"


# ---------- data audit + fresh calls ----------

STALE_DAYS = 14  # ASO cadence locked at 14d (see memory: aso_cadence.md)


def _mtime_days(p: Path) -> Optional[float]:
    if not p.exists():
        return None
    return (time.time() - p.stat().st_mtime) / 86400.0


def _load_master_keywords_csv(path: Path) -> list[dict]:
    """Returns rows sorted by score desc. master_keywords.csv schema:
       keyword,platform,category,avg_score,max_score,trending_days,score"""
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                row["_score"] = float(row.get("score", 0) or 0)
            except ValueError:
                row["_score"] = 0.0
            out.append(row)
    out.sort(key=lambda r: -r["_score"])
    return out


def _load_apple_kws_json(path: Path) -> dict:
    """apple-store-keywords-en-US.json — has 'en' subdoc with 'keywords' (csv string of stems)."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_competitors_json(path: Path) -> list[dict]:
    """aso-competitors-latest.json — schema varies by --mode of the last run.

    Expected for winnability: output of `aso-competitors.py --matrix "<seed>"`
    which produces {"apps": [...]} or {"matches": [...]} — list of competitor
    apps with userRatingCount/trackName fields.

    If the file contains a single-app output (--keywords or --analyze mode), it
    has top-level "app_id" / "trackId" and no apps list. We return [] so the
    caller can fall back gracefully.
    """
    if not path.exists():
        return []
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        # Preferred shapes — matrix output
        for k in ("apps", "results", "competitors", "matches", "ranked"):
            if k in d and isinstance(d[k], list):
                return d[k]
        # Single-app output (--keywords / --analyze mode) — not usable for matrix
        if "app_id" in d or "trackId" in d:
            return []
        # Generic fallback: first list-of-dicts found
        for v in d.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return []


def _call_kit_script(ctx: AppContext, script_relpath: str, args: list[str]) -> tuple[bool, str]:
    """Run a kit script as subprocess. Returns (ok, tail_of_output)."""
    script_path = ctx.automation_kit_root / "py" / script_relpath
    if not script_path.exists():
        return False, f"script not found: {script_path}"
    cmd = ["python3", str(script_path)] + args
    try:
        # Long timeout because keyword pipelines can take 5-10 min
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=900,
            cwd=str(ctx.app_repo),
        )
        tail = (result.stdout or "")[-400:] + (result.stderr or "")[-400:]
        return (result.returncode == 0), tail
    except subprocess.TimeoutExpired:
        return False, f"timeout after 900s running {script_relpath}"
    except Exception as e:
        return False, f"exception running {script_relpath}: {e}"


def audit_data_sources(ctx: AppContext, refresh_stale: bool = True) -> None:
    """Populate ctx.top_keywords + ctx.data_sources_* by reading ASO/SEO artifacts.

    For apps: master_keywords.csv + apple-store-keywords + aso-competitors.
    For web:  landing-page secondaryKeywords + (optional) build-keyword-volume output.

    If files are missing OR stale beyond STALE_DAYS, attempts refresh by calling
    the underlying kit scripts. Records every attempt in ctx.fresh_calls_made.
    """
    if ctx.product_type == "app":
        _audit_app(ctx, refresh_stale=refresh_stale)
    elif ctx.product_type == "web":
        _audit_web(ctx, refresh_stale=refresh_stale)
    else:
        # Unknown product type: fall back to landing-yaml kws only
        _audit_landing_only(ctx)


def _audit_app(ctx: AppContext, *, refresh_stale: bool) -> None:
    master = ctx.aso_data_dir / "master_keywords.csv"
    apple_kws = ctx.aso_data_dir / "apple-store-keywords-en-US.json"
    competitors = ctx.aso_data_dir / "aso-competitors-latest.json"

    for label, path in [("master_keywords.csv", master),
                        ("apple-store-keywords-en-US.json", apple_kws),
                        ("aso-competitors-latest.json", competitors)]:
        age = _mtime_days(path)
        if age is None:
            ctx.data_sources_missing.append(label)
        elif age > STALE_DAYS:
            ctx.data_sources_stale.append(f"{label} ({age:.0f}d old, >{STALE_DAYS}d)")
        else:
            ctx.data_sources_used.append(f"{label} ({age:.0f}d old)")

    # Refresh if needed
    if refresh_stale and (ctx.data_sources_missing or ctx.data_sources_stale):
        seeds = ctx.primaryKeyword or "shopping assistant"
        if master in (
            *(ctx.aso_data_dir / m for m in ctx.data_sources_missing if "master" in m),
        ) or any("master" in s for s in (*ctx.data_sources_missing, *ctx.data_sources_stale)):
            print(f"  → refreshing master_keywords.csv (seeds: {seeds[:60]})...")
            ok, tail = _call_kit_script(ctx, "aso/aso-keyword-pipeline.py",
                                        ["--seeds", seeds])
            ctx.fresh_calls_made.append(
                f"aso-keyword-pipeline.py {'OK' if ok else 'FAIL: ' + tail[-160:]}"
            )

        if any("competitor" in s for s in (*ctx.data_sources_missing, *ctx.data_sources_stale)):
            print(f"  → refreshing aso-competitors-latest.json (matrix: {seeds[:60]})...")
            ok, tail = _call_kit_script(ctx, "aso/aso-competitors.py",
                                        ["--matrix", seeds])
            ctx.fresh_calls_made.append(
                f"aso-competitors.py {'OK' if ok else 'FAIL: ' + tail[-160:]}"
            )

    # Priority 1 — primaryKeyword from landing (always the anchor)
    if ctx.primaryKeyword:
        ctx.top_keywords.append({
            "keyword": ctx.primaryKeyword,
            "score": None,
            "source": "landing.md primaryKeyword",
        })

    # Priority 2 — Apple keywords field (already top-scored by aso-metadata pipeline)
    # These are single-word stems ranked by Apple search ads volume + difficulty.
    apple = _load_apple_kws_json(apple_kws)
    en = apple.get("en", {}) if isinstance(apple, dict) else {}
    apple_csv = en.get("keywords", "")
    if apple_csv:
        for kw in [k.strip() for k in apple_csv.split(",") if k.strip()][:12]:
            if not any(t["keyword"].lower() == kw.lower() for t in ctx.top_keywords):
                ctx.top_keywords.append({
                    "keyword": kw,
                    "score": None,
                    "source": "apple-store-keywords (top-ordered)",
                })

    # Priority 3 — landing.md secondaryKeywords (curated compound phrases)
    # These pair well with the Apple single-stems above to form ranking-friendly text.
    for kw in ctx.secondary_keywords[:8]:
        if not any(t["keyword"].lower() == kw.lower() for t in ctx.top_keywords):
            ctx.top_keywords.append({
                "keyword": kw,
                "score": None,
                "source": "landing.md secondaryKeywords",
            })

    # Priority 4 — master_keywords.csv (ONLY use if its scores are differentiated;
    # the pipeline often emits uniform scores which makes alphabetic sort = noise)
    rows = _load_master_keywords_csv(master)
    if rows:
        # Check score variance — if all top scores are identical, the CSV is
        # un-ranked and we skip it to avoid alphabetic noise pollution
        top_scores = {r["_score"] for r in rows[:20]}
        if len(top_scores) > 1:
            for r in rows[:6]:
                kw = r.get("keyword", "")
                if kw and not any(t["keyword"].lower() == kw.lower() for t in ctx.top_keywords):
                    ctx.top_keywords.append({
                        "keyword": kw,
                        "score": r["_score"],
                        "source": "master_keywords.csv",
                    })
        else:
            ctx.data_sources_stale.append(
                f"master_keywords.csv (uniform score {next(iter(top_scores)):.3f} — needs re-run)"
            )

    # Build winnability rows from competitor data — pair each top kw against
    # competitors that mention any stem from it (short-stem matching catches more)
    comps = _load_competitors_json(competitors)
    ctx.winnability_rows = _build_winnability_rows(ctx, comps)


def _audit_web(ctx: AppContext, *, refresh_stale: bool) -> None:
    """For web products: secondaryKeywords from landing yaml + optional volume data."""
    # Landing yaml secondaryKeywords already populated by discover()
    for kw in ctx.secondary_keywords[:12]:
        ctx.top_keywords.append({
            "keyword": kw,
            "score": None,
            "source": "landing.md secondaryKeywords",
        })

    if ctx.primaryKeyword:
        ctx.top_keywords.insert(0, {
            "keyword": ctx.primaryKeyword,
            "score": None,
            "source": "landing.md primaryKeyword",
        })

    # Try keyword-volume cache for web
    vol_cache = ctx.app_repo / "automation_data" / f"keyword-volume-{ctx.slug}.json"
    age = _mtime_days(vol_cache)
    if age is None:
        ctx.data_sources_missing.append(f"keyword-volume-{ctx.slug}.json")
        if refresh_stale and ctx.top_keywords:
            print(f"  → estimating keyword volume for top {min(6, len(ctx.top_keywords))} kws...")
            kws_to_check = [t["keyword"] for t in ctx.top_keywords[:6]]
            ok, tail = _call_kit_script(ctx, "build-keyword-volume.py", kws_to_check)
            ctx.fresh_calls_made.append(
                f"build-keyword-volume.py {'OK' if ok else 'FAIL: ' + tail[-160:]}"
            )
    else:
        ctx.data_sources_used.append(f"keyword-volume-{ctx.slug}.json ({age:.0f}d old)")

    # Web doesn't have ASO competitors — winnability skipped, leave empty rows.
    # User MUST hand-fill or run dedicated SERP tracker separately.
    ctx.winnability_rows = []


def _audit_landing_only(ctx: AppContext) -> None:
    """Fallback path: only landing yaml available."""
    if ctx.primaryKeyword:
        ctx.top_keywords.append({
            "keyword": ctx.primaryKeyword,
            "score": None,
            "source": "landing.md primaryKeyword",
        })
    for kw in ctx.secondary_keywords[:11]:
        ctx.top_keywords.append({
            "keyword": kw,
            "score": None,
            "source": "landing.md secondaryKeywords",
        })


def _build_winnability_rows(ctx: AppContext, comps: list[dict]) -> list[dict]:
    """For top 6 keywords, find the toughest competitor across loaded comp data
    and emit a winnability verdict using review/install proxies.

    Verdict thresholds (apps < 10k installs target):
      Winnable     : top competitor < 5_000 reviews
      Contested    : 5_000 ≤ reviews < 50_000
      Hard         : 50_000 ≤ reviews < 500_000
      Locked       : ≥ 500_000 reviews (don't pick as title kw)
    """
    # Stopwords to drop when extracting matchable stems from compound kws
    STOPS = {"a", "an", "the", "for", "of", "to", "in", "on", "and", "or",
             "with", "app", "best", "free", "online", "your"}

    rows = []
    for tk in ctx.top_keywords[:6]:
        kw = tk["keyword"].lower()
        # Build matchable stems: full phrase + each significant word
        stems = [kw] + [w for w in re.findall(r"[a-z0-9]+", kw) if w not in STOPS and len(w) > 2]
        # Find toughest competitor whose haystack mentions ANY stem
        best = None
        for c in comps:
            haystack = " ".join([
                str(c.get("trackName", "") or c.get("name", "") or ""),
                str(c.get("description", "") or "")[:500],
                str(c.get("keywords", "") or ""),
            ]).lower()
            if any(s in haystack for s in stems):
                reviews = int(c.get("userRatingCount", c.get("reviews", 0)) or 0)
                if best is None or reviews > int(best.get("userRatingCount", best.get("reviews", 0)) or 0):
                    best = c

        if best is None:
            verdict = "Unknown — run `aso-competitors.py --matrix`"
            if not comps:
                verdict = "Unknown — no matrix data; run `aso-competitors.py --matrix \"<seed>\"`"
            rows.append({
                "keyword": tk["keyword"],
                "competitor": "—",
                "reviews": "—",
                "installs": "—",
                "verdict": verdict,
            })
            continue

        reviews = int(best.get("userRatingCount", best.get("reviews", 0)) or 0)
        installs = best.get("installs", "—")
        comp_name = best.get("trackName") or best.get("name") or "?"

        if reviews < 5_000:
            verdict = "Winnable ✓"
        elif reviews < 50_000:
            verdict = "Contested"
        elif reviews < 500_000:
            verdict = "Hard"
        else:
            verdict = "Locked ✗"

        rows.append({
            "keyword": tk["keyword"],
            "competitor": comp_name,
            "reviews": f"{reviews:,}",
            "installs": str(installs) if installs != "—" else "—",
            "verdict": verdict,
        })
    return rows


def render_winnability_table(ctx: AppContext) -> str:
    """Markdown table per STOP-RULE-001. ALWAYS emitted; if data missing → row says so."""
    lines = ["| Keyword | Top competitor | Reviews | Installs | Winnable? |",
             "|---|---|---|---|---|"]
    if not ctx.winnability_rows:
        if ctx.product_type == "web":
            lines.append("| *(web product — SERP competitor check skipped; run build-serp-tracker.py for full audit)* | — | — | — | — |")
        else:
            lines.append("| *(no competitor data — run `py/aso/aso-competitors.py --matrix \"<seed>\"` to populate)* | — | — | — | — |")
        return "\n".join(lines)
    for r in ctx.winnability_rows:
        lines.append(f"| {r['keyword']} | {r['competitor']} | {r['reviews']} | {r['installs']} | {r['verdict']} |")
    return "\n".join(lines)


def write_data_audit_json(ctx: AppContext) -> Path:
    """Persist the audit so the user can verify exactly what kws drove the copy."""
    out = ctx.out_dir / "data-audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "slug": ctx.slug,
        "product_type": ctx.product_type,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "primary_keyword": ctx.primaryKeyword,
        "top_keywords": ctx.top_keywords,
        "winnability_rows": ctx.winnability_rows,
        "data_sources": {
            "used": ctx.data_sources_used,
            "stale": ctx.data_sources_stale,
            "missing": ctx.data_sources_missing,
        },
        "fresh_calls_made": ctx.fresh_calls_made,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def discover(slug: str, app_repo: Path, landing_repo: Path,
             brand_bg: Optional[str], brand_fg: Optional[str]) -> AppContext:
    ctx = AppContext(slug=slug, app_repo=app_repo, landing_repo=landing_repo)

    if brand_bg:
        ctx.brand_bg = brand_bg
    if brand_fg:
        ctx.brand_fg = brand_fg

    # Landing yaml — try apps/<slug>.md first, fall back to web/<slug>.md
    landing_md = landing_repo / "src" / "content" / "apps" / f"{slug}.md"
    if not landing_md.exists():
        landing_md_web = landing_repo / "src" / "content" / "web" / f"{slug}.md"
        if landing_md_web.exists():
            landing_md = landing_md_web

    fm = parse_yaml_frontmatter(landing_md)
    ctx.app_name = fm.get("appName") or fm.get("siteName") or slug
    ctx.metaTitle = fm.get("metaTitle", "")
    ctx.tagline = fm.get("tagline", "")
    ctx.shortDescription = fm.get("shortDescription", "")
    ctx.primaryKeyword = fm.get("primaryKeyword", "")
    sec = fm.get("secondaryKeywords") or []
    if isinstance(sec, list):
        ctx.secondary_keywords = [s for s in sec if isinstance(s, str)]
    ctx.play_url = fm.get("playStoreUrl", "")
    ctx.apple_url = fm.get("appStoreUrl", "")
    ctx.category = fm.get("category", "Shopping")
    ctx.landing_url = f"https://apps.teamzlab.com/{slug}/"

    # Product type detection
    ctx.product_type = detect_product_type(app_repo)

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
    slug = re.sub(r"[^a-z0-9]+", "-", headline.lower()).strip("-")[:50]
    out = ctx.gallery_dir / f"{idx:02d}-{slug}.png"
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

    # Pick up to 4 screenshots for slots 2-5.
    # Headlines drive both on-card text AND output filename slug — pre-bake the app's
    # top kws into the headline so the gallery filename ranks in Google Image Search.
    pkw = (ctx.primaryKeyword or ctx.app_name).lower()
    captions = [
        (f"{ctx.app_name} {pkw}", "AI compares prices across stores — hands back 3 picks."),
        ("Price comparison side by side", "Tap two picks. See the winner with explained reasoning."),
        ("AI shopping assistant pros cons", "No more scrolling 200 reviews. AI summarizes what matters."),
        ("Deal finder + budget shopping", "Type the budget. AI respects it. 160+ currencies, auto-detected."),
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


def _top_winnable_kws(ctx: AppContext, n: int = 4) -> list[str]:
    """Return up to n top kws that pass the winnability gate.

    For apps with winnability data: returns kws labelled Winnable/Contested.
    For web or missing data: returns top kws unfiltered (best-effort).
    """
    out = []
    if ctx.winnability_rows:
        for row in ctx.winnability_rows:
            v = row.get("verdict", "")
            if v.startswith("Winnable") or v.startswith("Contested") or v.startswith("Unknown"):
                out.append(row["keyword"])
                if len(out) >= n:
                    return out
    # Fallback to top_keywords order
    for tk in ctx.top_keywords:
        kw = tk["keyword"]
        if kw and kw not in out:
            out.append(kw)
            if len(out) >= n:
                break
    return out


def tagline_candidates(ctx: AppContext) -> list[str]:
    """Generate kw-anchored tagline candidates from audit data, NOT assumption."""
    pkw = ctx.primaryKeyword
    winnable = _top_winnable_kws(ctx, n=4)

    # Try to build candidates that combine 2 high-value kws under 60 chars
    cands: list[str] = []
    if pkw and len(winnable) >= 2:
        # Pattern A: "<primary> + <2nd kw> — 3 picks, your budget"
        for second in winnable:
            if second.lower() == pkw.lower():
                continue
            c = f"{pkw.title()} + {second.title()} — 3 picks, your budget"
            if len(c) <= 60:
                cands.append(c)
                break

    if pkw:
        cands.append(f"{pkw.title()} — type budget, AI picks 3")

    # Subtitle as natural fallback
    if ctx.apple_subtitle:
        cands.append(ctx.apple_subtitle[:60])

    if ctx.tagline:
        cands.append(ctx.tagline[:60])

    # Dedupe + length filter
    seen: set = set()
    out: list[str] = []
    for c in cands:
        if not c or len(c) > 60:
            continue
        key = c.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out[:4]


def description_500(ctx: AppContext) -> str:
    """Returns ≤500-char paragraph anchored on top winnable kws from audit.

    Prefers landing.shortDescription if it ALREADY uses top kws (data-driven).
    Otherwise composes new copy that injects them.
    """
    winnable = _top_winnable_kws(ctx, n=6)
    short = ctx.shortDescription or ""

    # If landing copy already covers ≥60% of top kws, trust it
    if short:
        hits = sum(1 for kw in winnable if kw.lower() in short.lower())
        if winnable and (hits / len(winnable)) >= 0.6 and len(short) <= 500:
            return short
        if winnable and (hits / len(winnable)) >= 0.6:
            return truncate(short, 500)

    # Compose from top kws
    if winnable:
        kw_phrase = ", ".join(winnable[:3])
        s = (
            f"{ctx.app_name} is built for {kw_phrase}. "
            f"{ctx.tagline} "
            f"No affiliate links, no tracking, no signup. "
            f"Free."
        )
        return truncate(s, 500)

    # Final fallback
    s = (
        f"{ctx.app_name} — {ctx.tagline}. "
        f"Free. No affiliate links, no tracking, no signup."
    )
    return truncate(s, 500)


def render_data_audit_block(ctx: AppContext) -> list[str]:
    """STOP-RULE-001 compliance: winnability table FIRST, every run, no exceptions."""
    lines: list[str] = []
    a = lines.append
    a("## 0. Data audit (RULE-001: winnability before recommendation)")
    a("")
    a(f"**Product type:** `{ctx.product_type}`  |  **Primary keyword:** `{ctx.primaryKeyword or '(none in landing yaml)'}`")
    a("")
    a("### Winnability check — top keyword candidates")
    a("")
    a(render_winnability_table(ctx))
    a("")
    if ctx.top_keywords:
        a(f"**Top {min(8, len(ctx.top_keywords))} keywords** (anchored into tagline + description below):")
        for tk in ctx.top_keywords[:8]:
            src = tk.get("source", "?")
            score = tk.get("score")
            score_str = f" · score={score:.2f}" if isinstance(score, (int, float)) else ""
            a(f"- `{tk['keyword']}`  *(source: {src}{score_str})*")
        a("")
    a("### Data sources")
    if ctx.data_sources_used:
        a("- ✓ Used: " + ", ".join(ctx.data_sources_used))
    if ctx.data_sources_stale:
        a("- ⚠ Stale: " + ", ".join(ctx.data_sources_stale))
    if ctx.data_sources_missing:
        a("- ✗ Missing: " + ", ".join(ctx.data_sources_missing))
    if ctx.fresh_calls_made:
        a("- 🔄 Fresh calls: " + "; ".join(ctx.fresh_calls_made))
    if not (ctx.data_sources_used or ctx.data_sources_stale or ctx.data_sources_missing):
        a("- *(no ASO/SEO artifacts available — copy below uses landing yaml only)*")
    a("")
    a(f"_Full structured audit: `automation_data/product_hunt/data-audit.json`._")
    a("")
    a("---\n")
    return lines


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
    # STOP-RULE-001: winnability table BEFORE any tagline/description
    lines.extend(render_data_audit_block(ctx))
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
    ap.add_argument("--no-refresh", action="store_true",
                    help="Skip auto-calling ASO/SEO refresh scripts even if data is stale/missing. "
                         "Use existing artifacts as-is. Default: refresh stale data automatically.")
    ap.add_argument("--strict", action="store_true",
                    help="STOP-RULE-001 strict mode — abort if winnability table cannot be built "
                         "(missing competitor data for apps). Default: emit table with 'no data' rows.")
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
    print(f"  slug         : {ctx.slug}")
    print(f"  app_repo     : {ctx.app_repo}")
    print(f"  landing      : {ctx.landing_repo}")
    print(f"  product_type : {ctx.product_type}")
    print(f"  app_name     : {ctx.app_name}")
    print(f"  apple_name   : {ctx.apple_name}")
    print(f"  primary kw   : {ctx.primaryKeyword}")
    print(f"  logo         : {ctx.logo_path}")
    print(f"  og.png       : {ctx.og_path}")
    print(f"  screenshots  : {len(ctx.screenshot_paths)} found")
    print(f"  out_dir      : {ctx.out_dir}")
    print()

    # Step 1 — data audit (STOP-RULE-001: must come before any copy)
    print(f"--- Data audit ({ctx.product_type}) ---")
    audit_data_sources(ctx, refresh_stale=not args.no_refresh)
    print(f"  top_keywords    : {len(ctx.top_keywords)} loaded")
    print(f"  winnability rows: {len(ctx.winnability_rows)}")
    if ctx.data_sources_used:
        print(f"  used    : {ctx.data_sources_used}")
    if ctx.data_sources_stale:
        print(f"  stale   : {ctx.data_sources_stale}")
    if ctx.data_sources_missing:
        print(f"  missing : {ctx.data_sources_missing}")
    if ctx.fresh_calls_made:
        print(f"  fresh   : {ctx.fresh_calls_made}")

    if args.strict and ctx.product_type == "app" and not ctx.winnability_rows:
        print("ERROR: --strict and no winnability data. Run aso-competitors.py first.", file=sys.stderr)
        sys.exit(2)
    print()

    if args.dry_run:
        print("[dry-run] no files written")
        return

    ctx.out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Data audit JSON (machine-readable companion)
    audit_path = write_data_audit_json(ctx)
    print(f"✓ wrote {audit_path} (structured audit — what kws drove the copy)")

    # 2. Copy
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

    # 3. Thumbnail
    thumb = make_thumbnail(ctx)
    print(f"✓ wrote {thumb} (240×240)")

    # 4. Gallery
    if not ctx.screenshot_paths and not ctx.og_path:
        print("WARN: no og.png or screenshots found — skipping gallery")
        return
    gallery = generate_gallery(ctx)
    for g in gallery:
        print(f"✓ wrote {g} (1270×760)")

    print()
    print(f"Done. Paste content from {canonical_path} into Product Hunt launch form.")
    print(f"Upload thumbnail + gallery files from {ctx.out_dir}/")


if __name__ == "__main__":
    main()
