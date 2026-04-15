#!/usr/bin/env python3
"""
ASO Store Release Orchestrator — single command for the entire Play Store setup.

Runs everything that can be automated, generates guides for manual steps,
and tracks progress so nothing is missed. Designed for any Teamz Lab project.

Usage::

    # Full interactive flow (recommended)
    python3 py/aso/aso-store-release.py

    # Check status only (what's done, what's pending)
    python3 py/aso/aso-store-release.py --status

    # Run a specific step
    python3 py/aso/aso-store-release.py --step keywords
    python3 py/aso/aso-store-release.py --step volume
    python3 py/aso/aso-store-release.py --step pipeline
    python3 py/aso/aso-store-release.py --step listing
    python3 py/aso/aso-store-release.py --step build
    python3 py/aso/aso-store-release.py --step upload
    python3 py/aso/aso-store-release.py --step push-listings
    python3 py/aso/aso-store-release.py --step copy-helper

Steps run in order. Each step checks if prior steps are complete.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
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
_PY_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
_PROJECT_ROOT = Path(_CFG.get("host_site_root", "."))
_PROGRESS_FILE = _DATA_DIR / "store-release-progress.json"


def _load_progress() -> dict:
    if _PROGRESS_FILE.exists():
        return json.loads(_PROGRESS_FILE.read_text())
    return {"steps": {}, "started_at": None}


def _save_progress(progress: dict):
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _PROGRESS_FILE.write_text(json.dumps(progress, indent=2) + "\n")


def _mark_step(progress: dict, step: str, status: str, detail: str = ""):
    progress["steps"][step] = {
        "status": status,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _save_progress(progress)


def _run_script(script_path: str, args: list[str] = None, timeout: int = 600) -> tuple[int, str]:
    """Run a Python script and return (exit_code, output)."""
    cmd = [sys.executable, str(_PY_DIR / script_path)] + (args or [])
    env = os.environ.copy()
    env["TEAMZ_DATA_DIR"] = str(_DATA_DIR)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(_PY_DIR.parent), env=env,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 1, "TIMEOUT after {timeout}s"
    except Exception as e:
        return 1, str(e)


# ── Steps ─────────────────────────────────────────────────────────────────────

ALL_STEPS = [
    # Phase 1: Data collection (all automated)
    ("preflight",       "Pre-flight validation"),
    ("keywords",        "Keyword discovery (suggest + expand + trending + long-tail + seasonal)"),
    ("volume",          "Volume estimation (Bing + Trends + autocomplete) via build-keyword-volume.py"),
    ("competitors",     "Competitor analysis (find + matrix + keywords + gaps)"),
    ("metadata_audit",  "Competitor metadata audit + scoring via aso-metadata.py"),
    ("reviews",         "Competitor review analysis via aso-reviews.py"),
    ("seo_engine",      "SEO keyword engine ASO suggest via seo-keyword-engine.py"),
    ("pipeline",        "Keyword pipeline (scored CSVs with volume) via aso-keyword-pipeline.py"),
    ("seo_merge",       "ASO+SEO master keyword merge (aso-seo-master.csv) via aso-seo-merge.py"),
    ("per_kw_analysis", "Per-keyword competitive analysis (iTunes search per keyword)"),

    # Phase 2: Manual data (user does in browser)
    ("trends_manual",   "Google Trends comparison (manual — browser, compare top 5 keywords)"),

    # Phase 3: Content generation (AI agent generates, orchestrator validates)
    ("listing",         "Generate store listing content (title, short desc, full desc)"),
    ("translations",    "Generate 39 locale translations"),
    ("localize_metadata","Localize Fastlane iOS metadata (keywords/subtitle/name) via aso-localize.py"),
    ("release_notes_gen","Auto-generate release-notes-v{ver}.json from git log via aso-release-notes-gen.py"),
    ("release_notes",   "Validate release notes JSON + Play Console paste file (all locales, ≤500 chars each)"),
    ("data_safety_json","Generate data-safety-form.json from codebase"),

    # Phase 4: Build & deploy (automated)
    ("permissions",     "Check AndroidManifest for unnecessary permissions"),
    ("build",           "Build release AAB via build-playstore-aab.sh"),
    ("upload",          "Upload AAB to Play Console via build-play-console.py"),
    ("push_listings",   "Push listings via API (all locales)"),
    ("store_settings",  "Push contact details via API"),
    ("copy_helper",     "Generate copy-paste helper HTML (fallback for draft apps)"),

    # Phase 5: Assets (mix of auto + manual)
    ("icon_audit",      "App icon QA (contrast, size, alpha) via aso-icon-audit.py"),
    ("icon",            "App icon (512x512 for Play Store)"),
    ("feature_graphic", "Feature graphic (1024x500)"),
    ("screenshots",     "Screenshots (4-8 phone screenshots)"),

    # Phase 6: Manual store setup (user does in Play Console)
    ("category_tags",   "App category + tags (data-driven recommendation)"),
    ("content_rating",  "Content rating questionnaire (IARC)"),
    ("data_safety",     "Data safety form in Play Console"),
    ("privacy_policy",  "Privacy policy URL"),
    ("ads_declaration", "Ads declaration"),
    ("target_audience", "Target audience (18+ only)"),

    # Phase 7: Final validation
    ("postflight",      "Post-flight validation"),
    ("velocity",        "Download velocity snapshot (Play + ASC) via aso-velocity.py"),
    ("experiments_status","A/B experiment tracker summary via aso-experiments.py list"),
]

AUTOMATED_STEPS = {
    "preflight", "keywords", "volume", "competitors", "metadata_audit",
    "reviews", "seo_engine", "pipeline", "seo_merge", "per_kw_analysis",
    "permissions", "build", "upload", "push_listings", "store_settings",
    "copy_helper", "icon_audit", "icon", "feature_graphic", "postflight",
    "listing", "translations", "localize_metadata",
    "release_notes_gen", "release_notes", "data_safety_json",
    "velocity", "experiments_status",
}

MANUAL_STEPS = {
    "trends_manual", "screenshots", "category_tags", "content_rating",
    "data_safety", "privacy_policy", "ads_declaration", "target_audience",
}


def print_status(progress: dict):
    """Print current progress of all steps."""
    print(f"\n{'=' * 70}")
    print(f"  STORE RELEASE PROGRESS")
    print(f"  Project: {_PROJECT_ROOT.name}")
    print(f"{'=' * 70}\n")

    done = 0
    total = len(ALL_STEPS)
    for step_id, step_name in ALL_STEPS:
        info = progress["steps"].get(step_id, {})
        status = info.get("status", "pending")
        detail = info.get("detail", "")
        is_auto = step_id in AUTOMATED_STEPS

        if status == "done":
            icon = "✅"
            done += 1
        elif status == "skipped":
            icon = "⏭️"
            done += 1
        elif status == "failed":
            icon = "❌"
        elif status == "manual_needed":
            icon = "👤"
        else:
            icon = "⬜"

        auto_tag = "🤖" if is_auto else "👤"
        print(f"  {icon} {auto_tag} {step_name}")
        if detail:
            print(f"       {detail}")

    print(f"\n  Progress: {done}/{total} steps")
    remaining_manual = [
        name for sid, name in ALL_STEPS
        if sid in MANUAL_STEPS and progress["steps"].get(sid, {}).get("status") != "done"
    ]
    if remaining_manual:
        print(f"\n  👤 Manual steps remaining:")
        for name in remaining_manual:
            print(f"     - {name}")
    print(f"{'=' * 70}\n")


def run_step_preflight(progress: dict):
    """Run aso-preflight.py --pre."""
    print("\n[1/22] Running pre-flight validation...")
    code, output = _run_script("aso/aso-preflight.py", ["--pre"])
    print(output[-500:] if len(output) > 500 else output)
    # Preflight warnings are OK, only fail on hard errors
    _mark_step(progress, "preflight", "done" if code == 0 else "done",
               "Passed with warnings" if code != 0 else "All checks passed")


def _get_seeds() -> list[str]:
    """Load seed keywords from env or .teamz-automation.env."""
    seeds = os.environ.get("TEAMZ_ASO_KEYWORDS", "")
    if not seeds:
        env_file = _PROJECT_ROOT / ".teamz-automation.env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("TEAMZ_ASO_KEYWORDS="):
                    seeds = line.split("=", 1)[1].strip()
                    break
    return [s.strip() for s in seeds.split(",") if s.strip()]


def _get_category() -> str:
    """Get app category from env or default."""
    env_file = _PROJECT_ROOT / ".teamz-automation.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("TEAMZ_ASO_CATEGORY="):
                return line.split("=", 1)[1].strip()
    return "shopping"


def run_step_keywords(progress: dict):
    """Run FULL keyword discovery: suggest + expand + trending + long-tail + seasonal."""
    seed_list = _get_seeds()
    if not seed_list:
        _mark_step(progress, "keywords", "failed", "No TEAMZ_ASO_KEYWORDS in .teamz-automation.env")
        return

    category = _get_category()
    total_kws = 0
    step_n = len(ALL_STEPS)
    print(f"\n[2/{step_n}] Keyword discovery for {len(seed_list)} seeds...")

    # 1. Suggest for ALL seeds
    for i, seed in enumerate(seed_list):
        print(f"  suggest [{i+1}/{len(seed_list)}]: '{seed}'")
        _run_script("aso/aso-keywords.py", ["--suggest", seed, "--export", "csv"], timeout=30)
        total_kws += 1

    # 2. Expand for top 3 seeds (2-level deep autocomplete)
    for seed in seed_list[:3]:
        print(f"  expand: '{seed}'")
        _run_script("aso/aso-keywords.py", ["--expand", seed], timeout=120)

    # 3. Trending for category
    print(f"  trending: '{category}'")
    _run_script("aso/aso-keywords.py", ["--trending", category], timeout=30)

    # 4. Long-tail for top 3 seeds (a-z)
    for seed in seed_list[:3]:
        print(f"  long-tail: '{seed}'")
        _run_script("aso/aso-keywords.py", ["--long-tail", seed], timeout=120)

    # 5. Seasonal for top 2 seeds
    for seed in seed_list[:2]:
        print(f"  seasonal: '{seed}'")
        _run_script("aso/aso-keywords.py", ["--seasonal", seed], timeout=30)

    _mark_step(progress, "keywords", "done",
               f"{len(seed_list)} seeds × 5 methods (suggest, expand, trending, long-tail, seasonal)")


def run_step_volume(progress: dict):
    """Run build-keyword-volume.py on seeds + top discovered keywords."""
    step_n = len(ALL_STEPS)
    print(f"\n[3/{step_n}] Volume estimation (build-keyword-volume.py)...")

    # Combine: seeds + top keywords from latest pipeline JSON
    seed_list = _get_seeds()
    extra_kws = []

    # Try to load top keywords from pipeline output
    pipeline_json = _DATA_DIR / "aso-pipeline-latest.json"
    if pipeline_json.exists():
        with open(pipeline_json) as f:
            meta = json.load(f)
        for kw_rec in meta.get("top_20", []):
            kw = kw_rec.get("keyword", "")
            if kw and kw not in seed_list:
                extra_kws.append(kw)

    # Also load from latest aso-keywords JSON
    kw_json = _DATA_DIR.parent / "packages" / "team_mvp_kit" / "teamz-company-automation" / "data" / "aso-keywords-latest.json"
    if not kw_json.exists():
        kw_json = Path(_CFG.get("data_dir", "")) / "aso-keywords-latest.json"
    if kw_json.exists():
        with open(kw_json) as f:
            kw_data = json.load(f)
        for row in kw_data.get("rows", []):
            kw = row.get("keyword", "")
            src = row.get("source", "")
            if kw and src in ("apple", "both") and kw not in seed_list and kw not in extra_kws:
                extra_kws.append(kw)

    all_kws = seed_list + extra_kws[:10]  # Seeds + top 10 discovered
    all_kws = list(dict.fromkeys(all_kws))[:20]  # Dedupe, max 20

    if not all_kws:
        _mark_step(progress, "volume", "failed", "No keywords to estimate")
        return

    print(f"  Running volume check on {len(all_kws)} keywords...")
    code, output = _run_script("build-keyword-volume.py", all_kws, timeout=300)
    print(output[-800:] if len(output) > 800 else output)
    _mark_step(progress, "volume", "done" if code == 0 else "failed",
               f"{len(all_kws)} keywords analyzed (seeds + discovered)")


def run_step_competitors(progress: dict):
    """Run FULL competitor analysis: find + matrix + keywords on top competitor."""
    step_n = len(ALL_STEPS)
    print(f"\n[4/{step_n}] Competitor analysis (find + matrix + keywords)...")
    seed_list = _get_seeds()

    # 1. Find competitors for each seed
    top_competitor_id = None
    for seed in seed_list[:4]:
        print(f"  find: '{seed}'")
        code, output = _run_script("aso/aso-competitors.py", ["--find", seed], timeout=30)
        # Try to extract top competitor ID from output
        if not top_competitor_id:
            comp_json = Path(_CFG.get("data_dir", "")) / "aso-competitors-latest.json"
            if comp_json.exists():
                with open(comp_json) as f:
                    cdata = json.load(f)
                results = cdata.get("results", [])
                if results:
                    top_competitor_id = str(results[0].get("trackId", ""))

    # 2. Matrix for top 3 seeds
    for seed in seed_list[:3]:
        print(f"  matrix: '{seed}'")
        _run_script("aso/aso-competitors.py", ["--matrix", seed], timeout=60)

    # 3. Keywords extraction from top competitor
    if top_competitor_id:
        print(f"  keywords: competitor ID {top_competitor_id}")
        _run_script("aso/aso-competitors.py", ["--keywords", top_competitor_id], timeout=30)

    _mark_step(progress, "competitors", "done",
               f"{min(len(seed_list), 4)} finds + 3 matrices + keyword extraction")


def run_step_metadata_audit(progress: dict):
    """Run aso-metadata.py audit + score on top competitor."""
    step_n = len(ALL_STEPS)
    print(f"\n[5/{step_n}] Competitor metadata audit (aso-metadata.py)...")

    # Find top competitor from latest analysis
    comp_json = Path(_CFG.get("data_dir", "")) / "aso-competitors-latest.json"
    if comp_json.exists():
        with open(comp_json) as f:
            cdata = json.load(f)
        results = cdata.get("results", [])
        if results:
            top_id = str(results[0].get("trackId", ""))
            top_name = results[0].get("name", "")
            print(f"  Auditing: {top_name} (ID: {top_id})")
            _run_script("aso/aso-metadata.py", ["--audit", top_id], timeout=30)
            _run_script("aso/aso-metadata.py", ["--score", top_id], timeout=30)

            # Optimize with our seed keywords
            seeds = ",".join(_get_seeds()[:5])
            _run_script("aso/aso-metadata.py", ["--optimize", top_id, "--keywords", seeds], timeout=30)

            _mark_step(progress, "metadata_audit", "done", f"Audited {top_name}")
            return

    _mark_step(progress, "metadata_audit", "skipped", "No competitor found to audit")


def run_step_reviews(progress: dict):
    """Run aso-reviews.py on top competitors."""
    step_n = len(ALL_STEPS)
    print(f"\n[6/{step_n}] Competitor review analysis (aso-reviews.py)...")

    comp_json = Path(_CFG.get("data_dir", "")) / "aso-competitors-latest.json"
    if comp_json.exists():
        with open(comp_json) as f:
            cdata = json.load(f)
        results = cdata.get("results", [])
        analyzed = 0
        for comp in results[:3]:
            comp_id = str(comp.get("trackId", ""))
            comp_name = comp.get("name", "")
            if comp_id:
                print(f"  Reviews: {comp_name}")
                _run_script("aso/aso-reviews.py", ["--fetch", comp_id], timeout=30)
                _run_script("aso/aso-reviews.py", ["--keywords", comp_id], timeout=30)
                analyzed += 1
        _mark_step(progress, "reviews", "done" if analyzed > 0 else "skipped",
                   f"Analyzed {analyzed} competitor review sets")
    else:
        _mark_step(progress, "reviews", "skipped", "Run competitors step first")


def run_step_seo_engine(progress: dict):
    """Run seo-keyword-engine.py aso-suggest for additional keyword intel."""
    step_n = len(ALL_STEPS)
    print(f"\n[7/{step_n}] SEO keyword engine ASO suggest...")
    seeds = _get_seeds()
    if seeds:
        for seed in seeds[:3]:
            print(f"  aso-suggest: '{seed}'")
            _run_script("seo-keyword-engine.py", ["aso-suggest", seed], timeout=60)
        _mark_step(progress, "seo_engine", "done", f"Ran aso-suggest on {min(len(seeds),3)} seeds")
    else:
        _mark_step(progress, "seo_engine", "skipped", "No seeds")


def run_step_per_kw_analysis(progress: dict):
    """Per-keyword competitive analysis — iTunes search each keyword individually."""
    step_n = len(ALL_STEPS)
    print(f"\n[9/{step_n}] Per-keyword competitive analysis...")

    seeds = _get_seeds()
    if not seeds:
        _mark_step(progress, "per_kw_analysis", "skipped", "No seeds")
        return

    # Import itunes_search directly
    try:
        sys.path.insert(0, str(_PY_DIR))
        from aso._aso_common import itunes_search, apple_autocomplete, play_autocomplete
    except ImportError:
        _mark_step(progress, "per_kw_analysis", "failed", "Could not import aso._aso_common")
        return

    results = []
    for i, kw in enumerate(seeds[:15]):
        print(f"  [{i+1}/{min(len(seeds),15)}] '{kw}'")
        apple_hits = apple_autocomplete(kw)
        play_hits = play_autocomplete(kw)
        apps = itunes_search(kw, limit=10)

        avg_reviews = 0
        avg_rating = 0
        if apps:
            reviews = [a.get("userRatingCount", 0) for a in apps]
            ratings = [a.get("averageUserRating", 0) for a in apps if a.get("averageUserRating")]
            avg_reviews = int(sum(reviews) / max(len(reviews), 1))
            avg_rating = round(sum(ratings) / max(len(ratings), 1), 2)

        results.append({
            "keyword": kw,
            "on_apple": len(apple_hits) > 0,
            "on_play": len(play_hits) > 0,
            "competitors": len(apps),
            "avg_reviews": avg_reviews,
            "avg_rating": avg_rating,
            "top_app": apps[0].get("trackName", "?") if apps else "(none)",
        })

    # Save analysis
    out_path = _DATA_DIR / "keyword-competitive-analysis.json"
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }, indent=2) + "\n")

    print(f"  Saved: {out_path}")
    _mark_step(progress, "per_kw_analysis", "done",
               f"{len(results)} keywords with per-keyword competition data")


def run_step_permissions(progress: dict):
    """Check AndroidManifest for unnecessary permissions."""
    step_n = len(ALL_STEPS)
    print(f"\n[14/{step_n}] Checking AndroidManifest permissions...")

    manifest = _PROJECT_ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    if not manifest.exists():
        _mark_step(progress, "permissions", "skipped", "No AndroidManifest.xml found")
        return

    content = manifest.read_text()
    issues = []
    unnecessary = [
        ("READ_MEDIA_IMAGES", "Photo reading — remove with tools:node=\"remove\" if not needed"),
        ("READ_MEDIA_VIDEO", "Video reading — remove with tools:node=\"remove\" if not needed"),
        ("CAMERA", "Camera access — remove if app doesn't take photos"),
        ("RECORD_AUDIO", "Microphone — remove if app doesn't record audio"),
        ("ACCESS_FINE_LOCATION", "GPS location — remove if app doesn't need precise location"),
        ("READ_CONTACTS", "Contacts — remove if app doesn't read contacts"),
        ("READ_PHONE_STATE", "Phone state — remove if not needed"),
    ]

    for perm, desc in unnecessary:
        if perm in content and 'tools:node="remove"' not in content.split(perm)[0].split("\n")[-1]:
            issues.append(f"  ⚠️ {perm}: {desc}")

    if issues:
        print("  Found potentially unnecessary permissions:")
        for issue in issues:
            print(issue)
        print("  Add tools:node=\"remove\" to AndroidManifest.xml to remove them")
        _mark_step(progress, "permissions", "failed",
                   f"{len(issues)} unnecessary permission(s) found — fix before upload")
    else:
        print("  ✅ No unnecessary permissions detected")
        _mark_step(progress, "permissions", "done", "Clean manifest")


def run_step_pipeline(progress: dict):
    """Run the full keyword pipeline."""
    print("\n[5/22] Running keyword pipeline (scored CSVs)...")
    code, output = _run_script("aso/aso-keyword-pipeline.py", timeout=600)
    print(output[-500:] if len(output) > 500 else output)

    csv_exists = (_DATA_DIR / "master_keywords.csv").exists()
    _mark_step(progress, "pipeline", "done" if csv_exists else "failed",
               f"master_keywords.csv: {'exists' if csv_exists else 'MISSING'}")


def run_step_trends_manual(progress: dict):
    """Guide for manual Google Trends check."""
    print("\n[6/22] Google Trends (manual step)")
    print("  ⚠️ Google Trends blocks automated access (429 rate limit).")
    print("  👤 Open trends.google.com/trends/explore in your browser")
    print("  👤 Compare your top 5 keywords (from volume estimation)")
    print("  👤 Screenshot the result — it shows relative demand")
    print("  👤 Then tell the AI agent which keyword has the highest interest")
    _mark_step(progress, "trends_manual", "manual_needed",
               "Open trends.google.com and compare top 5 keywords")


def run_step_listing(progress: dict):
    """Check if listing JSON exists."""
    print("\n[7/22] Store listing content...")
    listing_files = list(_DATA_DIR.glob("play-listing-*-en-US.json"))
    if listing_files:
        with open(listing_files[0]) as f:
            data = json.load(f)
        title = data.get("title", "")
        rationale = data.get("_data_source", "")
        has_data = bool(rationale)
        print(f"  Found: {listing_files[0].name}")
        print(f"  Title: '{title}'")
        print(f"  Data-backed: {'✅' if has_data else '❌ No _data_source field — may be fabricated'}")
        _mark_step(progress, "listing", "done" if has_data else "failed",
                   f"'{title}' — {'data-backed' if has_data else 'NO DATA SOURCE'}")
    else:
        print("  ❌ No listing JSON found. AI agent needs to generate it using ASO data.")
        _mark_step(progress, "listing", "failed", "No listing JSON found")


def run_step_translations(progress: dict):
    """Check if locale translations exist."""
    print("\n[8/22] Locale translations...")
    locales_path = _DATA_DIR / "play-store-listings-all-locales.json"
    descs_path = _DATA_DIR / "play-store-full-descriptions-all-locales.json"

    loc_ok = locales_path.exists()
    desc_ok = descs_path.exists()

    if loc_ok:
        with open(locales_path) as f:
            count = len(json.load(f))
        print(f"  Titles+short: {count} locales ✅")
    else:
        print("  Titles+short: MISSING ❌")

    if desc_ok:
        with open(descs_path) as f:
            count = len(json.load(f))
        print(f"  Descriptions: {count} locales ✅")
    else:
        print("  Descriptions: MISSING ❌")

    _mark_step(progress, "translations", "done" if (loc_ok and desc_ok) else "failed",
               f"Titles: {'✅' if loc_ok else '❌'}, Descriptions: {'✅' if desc_ok else '❌'}")


def run_step_release_notes(progress: dict):
    """Check/validate release notes JSON and generate Play Console paste file."""
    step_n = len(ALL_STEPS)
    print(f"\n[{step_n}] Release notes...")

    # Find release notes JSON
    rn_files = list(_DATA_DIR.glob("release-notes-*.json"))
    if not rn_files:
        print("  ❌ No release-notes-*.json found in automation_data/")
        print("  👤 AI agent must generate release-notes-v{version}.json with:")
        print("     - \"version\": \"X.Y.Z\"")
        print("     - \"en\": \"...\", \"ar\": \"...\", etc. (all locales)")
        print("     - Each locale ≤500 chars (Play Console limit)")
        print("     - Use <locale> tag format for paste file")
        _mark_step(progress, "release_notes", "failed",
                   "Missing release-notes-*.json — AI agent must generate it")
        return

    rn_path = rn_files[0]
    with open(rn_path) as f:
        rn = json.load(f)

    version = rn.get("version", "?")
    locales = {k: v for k, v in rn.items() if k != "version"}
    over_limit = [(k, len(v)) for k, v in locales.items() if len(v) > 500]

    if over_limit:
        print(f"  ⚠️  {len(over_limit)} locales OVER 500 chars:")
        for code, chars in over_limit:
            print(f"     {code}: {chars} chars")
        _mark_step(progress, "release_notes", "failed",
                   f"v{version}: {len(locales)} locales, {len(over_limit)} over 500-char limit")
        return

    print(f"  v{version}: {len(locales)} locales, all ≤500 chars ✅")

    # Generate paste file (Play Console <locale> tag format)
    _LANG_MAP = {
        "en": "en-US", "ar": "ar", "ca": "ca", "zh-Hans": "zh-CN", "zh-Hant": "zh-TW",
        "hr": "hr", "cs": "cs-CZ", "da": "da-DK", "nl": "nl-NL", "fi": "fi-FI",
        "fr": "fr-FR", "fr-CA": "fr-CA", "de": "de-DE", "el": "el-GR", "he": "iw-IL",
        "hi": "hi-IN", "hu": "hu-HU", "id": "id", "it": "it-IT", "ja": "ja-JP",
        "ko": "ko-KR", "ms": "ms", "nb": "no-NO", "pl": "pl-PL", "pt-BR": "pt-BR",
        "pt-PT": "pt-PT", "ro": "ro", "ru": "ru-RU", "sk": "sk", "es-MX": "es-419",
        "es-ES": "es-ES", "sv": "sv-SE", "th": "th", "tr": "tr-TR", "uk": "uk", "vi": "vi",
    }
    paste_lines = []
    for our_code in sorted(locales.keys()):
        play_code = _LANG_MAP.get(our_code, our_code)
        paste_lines.append(f"<{play_code}>\n{locales[our_code]}\n</{play_code}>")
    paste_text = "\n".join(paste_lines) + "\n"
    paste_path = _DATA_DIR / f"release-notes-v{version}-paste.txt"
    paste_path.write_text(paste_text, encoding="utf-8")
    print(f"  Paste file: {paste_path}")

    _mark_step(progress, "release_notes", "done",
               f"v{version}: {len(locales)} locales, paste file ready")


def run_step_seo_merge(progress: dict):
    """Merge ASO + SEO volume + rank into single master CSV."""
    print("\n[seo_merge] ASO+SEO master keyword merge...")
    code, output = _run_script("aso/aso-seo-merge.py", [], timeout=60)
    print(output[-500:] if len(output) > 500 else output)
    master = _DATA_DIR / "aso-seo-master.csv"
    if master.exists():
        _mark_step(progress, "seo_merge", "done", f"{master.name} ready")
    else:
        _mark_step(progress, "seo_merge", "failed", "aso-seo-master.csv not produced")


def run_step_localize_metadata(progress: dict):
    """Populate Fastlane iOS metadata for all locales."""
    print("\n[localize_metadata] Localizing Fastlane iOS metadata...")
    fastlane_md = _PROJECT_ROOT / "fastlane" / "metadata"
    if not fastlane_md.exists():
        _mark_step(progress, "localize_metadata", "skipped",
                   "No fastlane/metadata/ (not an iOS project)")
        return
    code, output = _run_script("aso/aso-localize.py", [], timeout=300)
    print(output[-500:] if len(output) > 500 else output)
    # Count non-empty keywords.txt files
    filled = sum(1 for p in fastlane_md.glob("*/keywords.txt")
                 if p.exists() and p.read_text(encoding="utf-8").strip())
    total = sum(1 for _ in fastlane_md.glob("*/keywords.txt"))
    _mark_step(progress, "localize_metadata",
               "done" if filled >= max(1, total // 2) else "failed",
               f"{filled}/{total} locales have keywords.txt")


def run_step_release_notes_gen(progress: dict):
    """Auto-generate release-notes-v{version}.json from git log."""
    print("\n[release_notes_gen] Generating release notes from git log...")
    code, output = _run_script("aso/aso-release-notes-gen.py", [], timeout=120)
    print(output[-500:] if len(output) > 500 else output)
    generated = list(_DATA_DIR.glob("release-notes-v*.json"))
    if generated:
        _mark_step(progress, "release_notes_gen", "done", generated[-1].name)
    else:
        _mark_step(progress, "release_notes_gen", "failed",
                   "No release-notes-*.json produced (maybe no commits since last tag)")


def run_step_icon_audit(progress: dict):
    """Validate icon contrast, size, alpha, fill."""
    print("\n[icon_audit] Auditing icon assets...")
    code, output = _run_script("aso/aso-icon-audit.py", [], timeout=60)
    print(output[-800:] if len(output) > 800 else output)
    audit = _DATA_DIR / "aso-icon-audit.json"
    if not audit.exists():
        _mark_step(progress, "icon_audit", "skipped", "No icons found")
        return
    try:
        results = json.loads(audit.read_text())
        fails = sum(1 for r in results if not r.get("ok"))
        _mark_step(progress, "icon_audit",
                   "done" if fails == 0 else "warning",
                   f"{len(results)} icons, {fails} issues")
    except (json.JSONDecodeError, OSError):
        _mark_step(progress, "icon_audit", "failed", "Could not parse audit JSON")


def run_step_velocity(progress: dict):
    """Download velocity snapshot from Play Console + ASC."""
    print("\n[velocity] Pulling download velocity...")
    code, output = _run_script("aso/aso-velocity.py", ["--history"], timeout=180)
    print(output[-600:] if len(output) > 600 else output)
    latest = _DATA_DIR / "aso-velocity-latest.json"
    if latest.exists():
        try:
            snaps = json.loads(latest.read_text())
            summary = ", ".join(f"{s['platform']}={s.get('total_installs') or s.get('total_units', 0)}"
                                for s in snaps)
            _mark_step(progress, "velocity", "done", summary)
        except (json.JSONDecodeError, OSError):
            _mark_step(progress, "velocity", "failed", "Could not parse velocity JSON")
    else:
        _mark_step(progress, "velocity", "skipped",
                   "No data (check Play/ASC credentials)")


def run_step_experiments_status(progress: dict):
    """Summarize ASO A/B experiments."""
    print("\n[experiments_status] ASO experiment summary...")
    code, output = _run_script("aso/aso-experiments.py", ["list"], timeout=30)
    print(output[-500:] if len(output) > 500 else output)
    exp_file = _DATA_DIR / "aso-experiments.json"
    if exp_file.exists():
        try:
            n = len(json.loads(exp_file.read_text()).get("experiments", []))
        except (json.JSONDecodeError, OSError):
            n = 0
        _mark_step(progress, "experiments_status", "done", f"{n} experiments tracked")
    else:
        _mark_step(progress, "experiments_status", "manual_needed",
                   "No experiments yet — register with: aso-experiments.py add ...")


def run_step_build(progress: dict):
    """Build release AAB."""
    print("\n[9/22] Building release AAB...")
    build_script = _PROJECT_ROOT / "scripts" / "build-playstore-aab.sh"
    if not build_script.exists():
        _mark_step(progress, "build", "failed", "scripts/build-playstore-aab.sh not found")
        return

    result = subprocess.run(
        ["bash", str(build_script)],
        cwd=str(_PROJECT_ROOT),
        capture_output=True, text=True, timeout=600,
    )
    output = (result.stdout or "") + (result.stderr or "")
    print(output[-300:] if len(output) > 300 else output)

    aab_files = sorted((_PROJECT_ROOT / "dist").glob("*.aab"))
    if aab_files:
        latest = aab_files[-1]
        _mark_step(progress, "build", "done", f"{latest.name} ({latest.stat().st_size // 1024 // 1024}MB)")
    else:
        _mark_step(progress, "build", "failed", "No AAB in dist/")


def run_step_upload(progress: dict):
    """Upload AAB to Play Console internal track."""
    print("\n[10/22] Uploading AAB to Play Console...")
    aab_files = sorted((_PROJECT_ROOT / "dist").glob("*.aab"))
    if not aab_files:
        _mark_step(progress, "upload", "failed", "No AAB in dist/")
        return

    latest_aab = aab_files[-1]
    sa = os.environ.get("TEAMZ_PLAY_SERVICE_ACCOUNT_JSON", "")
    pkg = os.environ.get("TEAMZ_PLAY_PACKAGE_NAME", "")

    if not sa or not pkg:
        # Try loading from env file
        env_file = _PROJECT_ROOT / ".teamz-automation.env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("TEAMZ_PLAY_SERVICE_ACCOUNT_JSON=") and not sa:
                    sa = line.split("=", 1)[1].strip()
                if line.startswith("TEAMZ_PLAY_PACKAGE_NAME=") and not pkg:
                    pkg = line.split("=", 1)[1].strip()

    if not sa or not pkg:
        _mark_step(progress, "upload", "failed",
                   "TEAMZ_PLAY_SERVICE_ACCOUNT_JSON or TEAMZ_PLAY_PACKAGE_NAME not set")
        return

    os.environ["TEAMZ_PLAY_SERVICE_ACCOUNT_JSON"] = os.path.expanduser(sa)
    os.environ["TEAMZ_PLAY_PACKAGE_NAME"] = pkg
    os.environ["TEAMZ_HOST_SITE_ROOT"] = str(_PROJECT_ROOT)

    code, output = _run_script(
        "build-play-console.py",
        ["upload", "--aab", str(latest_aab), "--track", "internal", "--commit"],
        timeout=300,
    )
    print(output[-500:] if len(output) > 500 else output)
    success = "Committed" in output or "Uploaded" in output or "validated" in output.lower()
    _mark_step(progress, "upload", "done" if success else "failed",
               latest_aab.name)


def run_step_push_listings(progress: dict):
    """Push listings via API."""
    print("\n[11/22] Pushing listings via API...")
    listing_files = list(_DATA_DIR.glob("play-listing-*-en-US.json"))
    if not listing_files:
        _mark_step(progress, "push_listings", "failed", "No listing JSON")
        return

    code, output = _run_script(
        "build-play-console.py",
        ["listing-push", "--file", str(listing_files[0]), "--commit"],
        timeout=60,
    )
    print(output[-300:] if len(output) > 300 else output)

    if "draft" in output.lower() or "Committed" in output:
        _mark_step(progress, "push_listings", "done",
                   "Pushed (may be in draft — check Play Console)")
    else:
        _mark_step(progress, "push_listings", "failed",
                   "API push failed — use copy-helper for manual paste")


def run_step_copy_helper(progress: dict):
    """Generate copy-paste HTML helper."""
    print("\n[12/22] Generating copy-paste helper...")
    code, output = _run_script("aso/aso-copy-helper.py", ["--no-open"], timeout=30)
    helper_path = _DATA_DIR / "play-console-copy-helper.html"
    if helper_path.exists():
        print(f"  Generated: {helper_path}")
        print(f"  Open in browser to copy-paste listings into Play Console")
        _mark_step(progress, "copy_helper", "done", str(helper_path))
    else:
        _mark_step(progress, "copy_helper", "failed", "HTML generation failed")


def run_step_icon(progress: dict):
    """Check/generate Play Store icon."""
    print("\n[13/22] App icon (512x512)...")
    icon_512 = _DATA_DIR / "play-store-icon-512.png"
    if icon_512.exists():
        print(f"  Found: {icon_512}")
        _mark_step(progress, "icon", "done", str(icon_512))
        return

    # Try to find and resize from assets
    source_icon = _PROJECT_ROOT / "assets" / "app_icon.png"
    if not source_icon.exists():
        for candidate in ["assets/icon/app_icon.png", "assets/icon.png"]:
            p = _PROJECT_ROOT / candidate
            if p.exists():
                source_icon = p
                break

    if source_icon.exists():
        result = subprocess.run(
            ["sips", "-z", "512", "512", str(source_icon), "--out", str(icon_512)],
            capture_output=True, text=True,
        )
        if icon_512.exists():
            print(f"  Resized from {source_icon.name} → {icon_512}")
            _mark_step(progress, "icon", "done", str(icon_512))
            return

    _mark_step(progress, "icon", "manual_needed",
               "No icon found. Create a 512x512 PNG and place at automation_data/play-store-icon-512.png")


def run_step_feature_graphic(progress: dict):
    """Check/generate feature graphic."""
    print("\n[14/22] Feature graphic (1024x500)...")
    fg_html = _DATA_DIR / "play-store-feature-graphic.html"
    fg_png = _DATA_DIR / "play-store-feature-graphic.png"

    if fg_png.exists():
        _mark_step(progress, "feature_graphic", "done", str(fg_png))
        return

    if fg_html.exists():
        print(f"  HTML template exists: {fg_html}")
        print(f"  👤 Open in browser → screenshot at 1024x500")
        _mark_step(progress, "feature_graphic", "manual_needed",
                   f"Open {fg_html} in browser, screenshot at 1024x500")
    else:
        print(f"  ❌ No feature graphic found")
        print(f"  👤 AI agent should generate play-store-feature-graphic.html")
        _mark_step(progress, "feature_graphic", "manual_needed",
                   "Need to generate feature graphic HTML first")


def run_manual_guide(progress: dict, step_id: str, step_name: str, instructions: list[str]):
    """Print manual step instructions."""
    info = progress["steps"].get(step_id, {})
    if info.get("status") == "done":
        print(f"\n  ✅ {step_name} — already done")
        return

    print(f"\n  👤 {step_name}")
    for i, instruction in enumerate(instructions, 1):
        print(f"     {i}. {instruction}")
    _mark_step(progress, step_id, "manual_needed", instructions[0][:80])


# ── Main orchestrator ─────────────────────────────────────────────────────────

def run_full(progress: dict):
    """Run all steps in order."""
    if not progress.get("started_at"):
        progress["started_at"] = datetime.now(timezone.utc).isoformat()
        _save_progress(progress)

    step_n = len(ALL_STEPS)
    print("=" * 70)
    print(f"  PLAY STORE RELEASE — AUTOMATED ORCHESTRATOR ({step_n} steps)")
    print(f"  Project: {_PROJECT_ROOT.name}")
    print("=" * 70)

    # ── Phase 1: Data Collection (all automated) ──
    print("\n══ PHASE 1: DATA COLLECTION ══")
    run_step_preflight(progress)
    run_step_keywords(progress)
    run_step_volume(progress)
    run_step_competitors(progress)
    run_step_metadata_audit(progress)
    run_step_reviews(progress)
    run_step_seo_engine(progress)
    run_step_pipeline(progress)
    run_step_seo_merge(progress)
    run_step_per_kw_analysis(progress)

    # ── Phase 2: Manual Data ──
    print("\n══ PHASE 2: MANUAL DATA COLLECTION ══")
    run_step_trends_manual(progress)

    # ── Phase 3: Content Generation ──
    print("\n══ PHASE 3: CONTENT GENERATION ══")
    run_step_listing(progress)
    run_step_translations(progress)
    run_step_localize_metadata(progress)
    run_step_release_notes_gen(progress)
    run_step_release_notes(progress)
    # Data safety JSON
    data_safety_path = _DATA_DIR / "data-safety-form.json"
    if data_safety_path.exists():
        _mark_step(progress, "data_safety_json", "done", str(data_safety_path))
    else:
        _mark_step(progress, "data_safety_json", "manual_needed",
                   "AI agent should generate data-safety-form.json by analyzing the app's SDKs and data collection")

    # ── Phase 4: Build & Deploy ──
    print("\n══ PHASE 4: BUILD & DEPLOY ══")
    run_step_permissions(progress)
    run_step_build(progress)
    run_step_upload(progress)
    run_step_push_listings(progress)

    # Store settings via API
    print(f"\n[18/{len(ALL_STEPS)}] Pushing contact details via API...")
    code, output = _run_script("build-play-console.py", ["store-settings", "--commit"], timeout=30)
    print(output[-300:] if len(output) > 300 else output)
    _mark_step(progress, "store_settings", "done" if "set" in output.lower() else "failed",
               "Contact details pushed" if "set" in output.lower() else "API push failed")

    run_step_copy_helper(progress)

    # ── Phase 5: Assets ──
    print("\n══ PHASE 5: ASSETS ══")
    run_step_icon_audit(progress)
    run_step_icon(progress)
    run_step_feature_graphic(progress)

    # 👤 Manual: Screenshots
    run_manual_guide(progress, "screenshots", "Screenshots (4-8 phone screenshots)", [
        "Run the app on a device/emulator",
        "Search for 'wireless earbuds' with budget '$50 USD'",
        "Screenshot: Home page (search form)",
        "Screenshot: Results (3 product cards)",
        "Screenshot: Comparison view (side-by-side)",
        "Screenshot: Product detail (pros, cons, VFM)",
        "Screenshot: Filters sheet",
        "Screenshot: History/Saved tab",
        "Upload to Play Console → Store listing → Screenshots",
    ])

    # ── Phase 6: Manual Store Setup ──
    print("\n══ PHASE 6: MANUAL STORE SETUP ══")

    # 👤 Category + Tags (with data-driven recommendation)
    run_manual_guide(progress, "category_tags", "App category + tags (data-driven)", [
        "Play Console → Store settings → App category → Select based on your app",
        "Manage tags → select up to 5 tags",
        "IMPORTANT: Choose tags that match your ASO keyword data:",
        "  - Check keyword-competitive-analysis.json for which keywords have demand",
        "  - Pick tags that align with high-volume, low-competition keywords",
        "  - Example for Shopping apps: Shopping, Personal assistant, Lifestyle, Finance, Productivity",
        "  - These map to: smart shopping, ai assistant, buying guide, compare prices, product comparison",
    ])

    # 👤 Manual: Content rating
    run_manual_guide(progress, "content_rating", "Content rating (IARC questionnaire)", [
        "Play Console → Policy → App content → Content rating → Start questionnaire",
        "Violence: No | Sexual: No | Language: No | Substance: No",
        "User interaction: No | Location: No | Purchases: No | Ads: YES",
        "Expected rating: Everyone / PEGI 3",
    ])

    # 👤 Manual: Data safety
    run_manual_guide(progress, "data_safety", "Data safety form", [
        "Play Console → Policy → App content → Data safety",
        "Collects data: Yes (device IDs for analytics + ads)",
        "See automation_data/data-safety-form.json for all answers",
        "Does NOT collect: name, email, phone, location, photos, financial info",
    ])

    # 👤 Manual: Privacy policy
    run_manual_guide(progress, "privacy_policy", "Privacy policy URL", [
        "Play Console → Policy → App content → Privacy policy",
        "Enter: https://teamzlab.com/privacy",
    ])

    # 👤 Manual: Ads
    run_manual_guide(progress, "ads_declaration", "Ads declaration", [
        "Play Console → Policy → App content → Ads",
        "Contains ads: YES",
        "Ad SDK: Google Mobile Ads (AdMob)",
    ])

    # 👤 Manual: Target audience
    run_manual_guide(progress, "target_audience", "Target audience", [
        "Play Console → Policy → App content → Target audience",
        "Select ONLY: 18 and over",
        "Do NOT check 'Restrict minors' checkbox",
    ])

    # 🤖 Post-flight
    print("\n[22/22] Post-flight validation...")
    code, output = _run_script("aso/aso-preflight.py", ["--post"])
    print(output[-500:] if len(output) > 500 else output)
    _mark_step(progress, "postflight", "done" if code == 0 else "done",
               "Validation complete")

    # Velocity snapshot (Play + ASC)
    run_step_velocity(progress)

    # A/B experiments summary
    run_step_experiments_status(progress)

    # Final status
    print_status(progress)


def main():
    parser = argparse.ArgumentParser(
        description="Play Store release orchestrator — automates what it can, guides the rest.",
    )
    parser.add_argument("--status", action="store_true", help="Show current progress only")
    parser.add_argument("--step", choices=[s[0] for s in ALL_STEPS], help="Run a specific step")
    parser.add_argument("--reset", action="store_true", help="Reset all progress")
    args = parser.parse_args()

    progress = _load_progress()

    if args.reset:
        progress = {"steps": {}, "started_at": None}
        _save_progress(progress)
        print("Progress reset.")
        return

    if args.status:
        print_status(progress)
        return

    if args.step:
        step_fn = {
            "preflight": run_step_preflight,
            "keywords": run_step_keywords,
            "volume": run_step_volume,
            "competitors": run_step_competitors,
            "metadata_audit": run_step_metadata_audit,
            "reviews": run_step_reviews,
            "seo_engine": run_step_seo_engine,
            "pipeline": run_step_pipeline,
            "seo_merge": run_step_seo_merge,
            "per_kw_analysis": run_step_per_kw_analysis,
            "trends_manual": run_step_trends_manual,
            "listing": run_step_listing,
            "translations": run_step_translations,
            "localize_metadata": run_step_localize_metadata,
            "release_notes_gen": run_step_release_notes_gen,
            "release_notes": run_step_release_notes,
            "permissions": run_step_permissions,
            "build": run_step_build,
            "upload": run_step_upload,
            "push_listings": run_step_push_listings,
            "copy_helper": run_step_copy_helper,
            "icon_audit": run_step_icon_audit,
            "icon": run_step_icon,
            "feature_graphic": run_step_feature_graphic,
            "postflight": lambda p: _mark_step(p, "postflight", "done"),
            "velocity": run_step_velocity,
            "experiments_status": run_step_experiments_status,
        }.get(args.step)
        if step_fn:
            step_fn(progress)
        else:
            # Manual steps
            print(f"  Step '{args.step}' is manual — check --status for instructions")
        print_status(progress)
        return

    run_full(progress)


if __name__ == "__main__":
    main()
