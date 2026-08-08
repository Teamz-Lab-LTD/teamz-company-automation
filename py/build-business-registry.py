#!/usr/bin/env python3
"""
Business Registry — Phase 0 of the distribution-engine-v2 plan.

WHY THIS EXISTS. v1's distribution engine was hardcoded to one site
(tool.teamzlab.com) — config.json has exactly one `defaults.site_url`, and two
posters (gitlab, substack) even hardcode that domain into their footer string
regardless of what the article is actually about. Adding a new business meant
editing distribute.py's Python by hand. Nobody did, so v1 stayed 96%
tools-listicles and never touched the owner's 18 app products.

This script regenerates `distribute/registry.json` — one entry per business —
by reading the SAME frontmatter the landing-pages site already builds pages
from (teamz-lab-generic-landing-pages/src/content/apps/*.md). That means the
onboarding flow for a NEW business is just "add a landing page" (which the
owner already does for every product) — the registry sync makes it join the
distribution cycle automatically. No landing page = not in the registry; this
script prints that gap explicitly rather than silently ignoring those repos.

MERGE, NEVER REPLACE. Same discipline as the enhance-queue picker (memory:
feedback_picker_gated_on_guesses — a picker swap once hid 98.9% of revenue by
replacing instead of unioning). Fields marked EDITABLE below survive a
re-run even when the source frontmatter changes; only the DERIVED fields are
overwritten every time. This lets a human (or the ban tripwire) flip
`enabled: false` on one business without that edit being silently reverted
the next time this script runs.

Usage:
  python3 py/build-business-registry.py            # regenerate registry.json
  python3 py/build-business-registry.py --dry-run   # print, don't write
  python3 py/build-business-registry.py --list-gaps # only print no-landing-page repos
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

AUTOMATION_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_ROOT = AUTOMATION_ROOT.parent
LANDING_REPO = PROJECTS_ROOT / "teamz-lab-generic-landing-pages"
APPS_DIR = LANDING_REPO / "src" / "content" / "apps"
SERVICES_FILE = LANDING_REPO / "src" / "data" / "services.ts"
REGISTRY_PATH = AUTOMATION_ROOT / "distribute" / "registry.json"

# Tools-hub seed — tool.teamzlab.com isn't in the apps collection (it's the
# SaaS itself, already present as slug teamz-lab-tools), but its high-value
# CONTENT HUBS need registry entries too so Phase 2b can pick "which business"
# for a tools article the same way it picks an app. Kept small and static
# deliberately — hub list is reviewed by the owner's existing event-formula /
# GSC-winner data (project_event_formula_playbook, project_pl_season_prep),
# not guessed here. Extend by hand when a new hub proves itself, same as the
# owner already tracks in memory.
TOOLS_HUBS = [
    {
        "slug": "tools-football",
        "name": "Teamz Lab Tools — Football hub",
        "type": "tool",
        "landing_url": "https://tool.teamzlab.com/football/",
        "hub_keywords": ["premier league table predictor", "penalty shootout simulator",
                          "champions league bracket predictor"],
        "geo": "global",
    },
    {
        "slug": "tools-bd",
        "name": "Teamz Lab Tools — Bangladesh calculators",
        "type": "tool",
        "landing_url": "https://tool.teamzlab.com/bd/",
        "hub_keywords": ["govt salary calculator bd", "electricity bill calculator bd"],
        "geo": "BD",
    },
]

# EDITABLE fields: once set in an existing registry.json, these survive a
# re-run untouched even if this script would derive something different.
EDITABLE_FIELDS = {"enabled", "hub_keywords", "geo", "features", "article_angles",
                    "_disabled_at", "_disabled_reason", "notes"}


def strip_frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        print(f"  ! YAML parse failed: {e}", file=sys.stderr)
        return None


def infer_geo(fm):
    """Best-effort geo hint from primaryKeyword/slug — EDITABLE once set, so a
    wrong guess here costs one manual correction, not a repeated one."""
    text = f"{fm.get('primaryKeyword', '')} {fm.get('appName', '')}".lower()
    if any(t in text for t in ("bd", "bangla", "হাজিরা", "মার্কশিট", "hazira")):
        return "BD"
    return "global"


def load_apps():
    if not APPS_DIR.exists():
        print(f"!! APPS_DIR not found: {APPS_DIR} — ABORT, not a real result", file=sys.stderr)
        sys.exit(2)
    entries = []
    for f in sorted(APPS_DIR.glob("*.md")):
        raw = f.read_text(encoding="utf-8", errors="replace")
        fm = strip_frontmatter(raw)
        if fm is None:
            print(f"  ! skipped {f.name}: no/broken frontmatter")
            continue
        slug = f.stem
        store_links = {k: fm.get(k) for k in ("playStoreUrl", "appStoreUrl", "webUrl") if fm.get(k)}
        entries.append({
            "slug": slug,
            "name": fm.get("appName", slug),
            "type": fm.get("productType", "app"),
            "landing_url": f"https://apps.teamzlab.com/{slug}/",
            "play_url": fm.get("playStoreUrl"),
            "app_store_url": fm.get("appStoreUrl"),
            "web_url": fm.get("webUrl"),
            "primary_keyword": fm.get("primaryKeyword"),
            "hub_keywords": [fm["primaryKeyword"]] if fm.get("primaryKeyword") else [],
            "geo": infer_geo(fm),
            "has_store_link": bool(store_links),
            "source_file": str(f.relative_to(PROJECTS_ROOT)),
        })
    return entries


def load_services():
    """Teamz Lab's OWN service offerings (vibe coding, AI agent dev, RAG,
    ecommerce dev, etc.) — added 2026-08-08 per owner request to extend
    distribution beyond apps/tools. Source: src/data/services.ts, the SAME
    structured data the service landing pages themselves render from
    (imported via `servicePages.find(s => s.slug === '...')` in each page's
    .astro file) — not invented copy.

    This file is TypeScript, not YAML frontmatter, so it's regex-extracted
    rather than parsed as a content collection like load_apps(). Verified
    safe for this file's specific shape (18/18 entries parse clean as of
    2026-08-08) — if a future edit to services.ts breaks the pattern, this
    prints a per-entry parse failure rather than silently returning fewer
    entries than exist.
    """
    if not SERVICES_FILE.exists():
        print(f"  ! SERVICES_FILE not found: {SERVICES_FILE} — skipping services (not fatal)")
        return []
    src = SERVICES_FILE.read_text(encoding="utf-8")
    chunks = re.split(r"(?=\n\s*slug: ')", src)
    entries = []
    for chunk in chunks[1:]:
        m_slug = re.search(r"slug:\s*'([^']+)'", chunk)
        if not m_slug:
            continue
        slug = m_slug.group(1)
        end = chunk.find("\n  },")
        body = chunk[:end] if end != -1 else chunk
        m_title = re.search(r"title:\s*\n?\s*'([^']+)'", body)
        m_desc = re.search(r"description:\s*\n?\s*'([^']+)'", body)
        if not (m_title and m_desc):
            print(f"  ! services.ts: could not parse title/description for '{slug}' — skipped, not guessed")
            continue
        entries.append({
            "slug": f"svc-{slug}",
            "name": m_title.group(1).split(" | ")[0].split(" — ")[0].strip(),
            "type": "service",
            "landing_url": f"https://apps.teamzlab.com/{slug}/",
            "seo_description": m_desc.group(1),
            "hub_keywords": [],
            "geo": "global",
            "has_store_link": False,
            "source_file": str(SERVICES_FILE.relative_to(PROJECTS_ROOT)),
        })
    return entries


def find_gaps():
    """Repos under teamz-projects/ that look like products but have no landing
    page entry — surfaced, never silently dropped (per the plan's Phase 0
    scoping note)."""
    known_slugs = {f.stem for f in APPS_DIR.glob("*.md")} if APPS_DIR.exists() else set()
    gaps = []
    for d in sorted(PROJECTS_ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        looks_like_app = (d / "pubspec.yaml").exists() or (d / "android").is_dir()
        already_registered = d.name in known_slugs or any(
            d.name.replace("_", "-") == s or d.name == s.replace("-", "_") for s in known_slugs
        )
        if looks_like_app and not already_registered:
            gaps.append(d.name)
    return gaps


def merge(existing_by_slug, fresh_entries):
    out = []
    for fresh in fresh_entries:
        slug = fresh["slug"]
        prior = existing_by_slug.get(slug, {})
        merged = dict(fresh)
        for field in EDITABLE_FIELDS:
            if field in prior:
                merged[field] = prior[field]
        merged.setdefault("enabled", True)
        merged.setdefault("features", [])
        merged.setdefault("article_angles", [])
        out.append(merged)
    # Static tools-hub seed — same merge rule.
    for hub in TOOLS_HUBS:
        prior = existing_by_slug.get(hub["slug"], {})
        merged = dict(hub)
        for field in EDITABLE_FIELDS:
            if field in prior:
                merged[field] = prior[field]
        merged.setdefault("enabled", True)
        merged.setdefault("features", [])
        merged.setdefault("article_angles", [])
        out.append(merged)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list-gaps", action="store_true")
    args = ap.parse_args()

    gaps = find_gaps()
    if args.list_gaps:
        print(f"App-shaped repos with NO landing page ({len(gaps)}) — not in the registry:")
        for g in gaps:
            print(f"  - {g}")
        return

    fresh = load_apps()
    if not fresh:
        print("!! zero app entries parsed — ABORT rather than write an empty registry", file=sys.stderr)
        sys.exit(2)
    services = load_services()
    fresh = fresh + services
    print(f"  + {len(services)} service entries from services.ts")

    existing = {}
    if REGISTRY_PATH.exists():
        try:
            prior_doc = json.loads(REGISTRY_PATH.read_text())
            existing = {e["slug"]: e for e in prior_doc.get("businesses", [])}
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  ! existing registry.json unreadable ({e}) — treating as empty, nothing to merge from")

    merged = merge(existing, fresh)
    doc = {
        "_comment": "Generated by py/build-business-registry.py. EDITABLE fields "
                    f"({', '.join(sorted(EDITABLE_FIELDS))}) survive re-runs; "
                    "everything else is re-derived from source landing pages every run.",
        "businesses": merged,
        "no_landing_page_gap": gaps,
    }

    print(f"parsed {len(fresh) - len(services)} app entries + {len(services)} service entries "
          f"+ {len(TOOLS_HUBS)} tools hubs = {len(merged)} total")
    print(f"gap (no landing page, not in registry): {len(gaps)} repos")
    for e in merged:
        stores = []
        if e.get("play_url"):
            stores.append("Play")
        if e.get("app_store_url"):
            stores.append("iOS")
        if e.get("web_url"):
            stores.append("web")
        print(f"  {'✓' if e.get('enabled') else '✗':1} {e['slug']:<28} [{e['type']:<5}] "
              f"{','.join(stores) or '(no store link)':<14} geo={e.get('geo')}")

    if args.dry_run:
        print("\n--dry-run: not written")
        return

    REGISTRY_PATH.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"\nwrote {REGISTRY_PATH}")


if __name__ == "__main__":
    main()
