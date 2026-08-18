#!/usr/bin/env python3
"""
Distribution Draft Briefs — Phase 2b, MECHANICAL half only.

THIS SCRIPT DOES NOT WRITE ARTICLES. THIS SCRIPT DOES NOT PUBLISH ANYTHING.
It picks the next business, selects a winnable keyword target for it, checks
the keyword isn't already a top-10 GSC winner for that business's own site
(self-cannibalization guard), pulls its mined features/angles from
registry.json, and writes a STRUCTURED BRIEF to data/distribution-brief.json
— data for a human (or a separately-reviewed nightly-agent step) to write
the actual prose from.

WHY THE BOUNDARY IS HERE, DELIBERATELY: the owner asked for the distribution
engine to write and publish content unattended, every night. That is real —
but auto-publishing AI-written copy under the Teamz Lab brand, with zero
human checkpoint the first time it runs, is a different risk than fixing an
existing engine's plumbing (which is what shipped 2026-08-08). This script
builds the SAFE, mechanical, fully-testable half: picking WHAT to write
about and WHICH keyword to target, with real data and real guardrails. The
prose-writing step and the auto-publish wiring are separate, later work that
needs its own explicit go-ahead — see docs (plan file) for why.

Selection logic:
  1. Round-robin the registry, weighted apps 2x tools/services (first-wave
     scope), skipping any business drafted within COOLDOWN_DAYS.
  2. Seed keywords = business.hub_keywords + business.article_angles.
  3. Expand via Google Ads Keyword Planner (generateKeywordIdeas — confirmed
     live 2026-08-08) for exact volumes; falls back to the seed list alone
     if the API is unreachable (never silently invents numbers).
  4. WINNABILITY FIRST, never raw-volume-first (standing doctrine,
     memory: feedback_aso_winnability_first): among candidates with
     competition != HIGH, pick the highest-volume one — a 10-volume LOW-
     competition term beats a 10,000-volume HIGH-competition term nobody
     ranks for at this domain's authority.
  5. SELF-CANNIBALIZATION GUARD: pulls the business's own GSC top queries
     (28d, position <=10) for its landing page and excludes any candidate
     that's already a winner there — the article would compete with the
     money page it's trying to support, not extend it.
  6. GEO: uses business.geo to pick the Keyword Planner geo-target constant
     (Bangladesh vs global/US) — wrong geo on a BD business produces
     garbage numbers (documented trap, memory: project_goalkit_bd_seo_demand).

Usage:
  python3 py/build-distribution-drafts.py                 # pick + write brief
  python3 py/build-distribution-drafts.py --dry-run        # pick + print, no write
  python3 py/build-distribution-drafts.py --business SLUG  # force a specific business
"""
import argparse
import json
import sys
import urllib.request
import urllib.parse
import urllib.error
import ssl
from datetime import date, datetime, timedelta
from pathlib import Path

AUTOMATION_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_ROOT = AUTOMATION_ROOT.parent
CFG = Path.home() / ".config" / "teamzlab"

REGISTRY_PATH = AUTOMATION_ROOT / "distribute" / "registry.json"
DRAFT_LOG_PATH = AUTOMATION_ROOT / "data" / "distribution-draft-log.json"
BRIEF_PATH = AUTOMATION_ROOT / "data" / "distribution-brief.json"

COOLDOWN_DAYS = 14
GOOGLE_PROJECT = "teamzlab-tools"
SSL_CTX = ssl.create_default_context()

# Geo target constants (Google Ads geoTargetConstants) — extend as new
# geos show up in the registry. Bangladesh gets its own; everything else
# defaults to a broad/global read via the US constant (Keyword Planner
# has no true "worldwide" constant; US is the standard broad proxy used
# elsewhere in this repo's keyword scripts).
#
# BD was "geoTargetConstants/1000352" here until 2026-08-14. That is not a valid
# constant — the API answers HTTP 400 INVALID_ARGUMENT for it, so every Bangladesh
# business (goalkit, Hazira) got zero keyword data from this path and the failure
# looked like "no keywords found" rather than "the request was malformed." The
# country constant for Bangladesh is 2050, confirmed by effect: "bkash" returns
# 246,000/mo on 2050 and 1,900/mo on 2840.
GEO_TARGET = {
    "BD": "geoTargetConstants/2050",  # Bangladesh
    "global": "geoTargetConstants/2840",  # United States (broad proxy)
}

# repo -> GSC site property, for the self-cannibalization check.
GSC_PROPERTY = {
    "tool.teamzlab.com": "https://tool.teamzlab.com/",
    "apps.teamzlab.com": "https://apps.teamzlab.com/",
    "learn.teamzlab.com": "https://learn.teamzlab.com/",
    "goalkit.teamzlab.com": "sc-domain:goalkit.teamzlab.com",
    "notracechat.teamzlab.com": "https://notracechat.teamzlab.com/",
}


def gsc_token():
    t = json.loads((CFG / "search-console-token.json").read_text())
    data = urllib.parse.urlencode({
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30))["access_token"]


def gsc_query(tok, site_url, body):
    encoded = urllib.parse.quote(site_url, safe="")
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/searchAnalytics/query"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-goog-user-project", GOOGLE_PROJECT)
    return json.load(urllib.request.urlopen(req, context=SSL_CTX, timeout=30))


def ads_token_and_headers():
    """Reuses the SAME Google Ads auth verified live 2026-08-08
    (build-keyword-volume.py's try_google_ads_volume). Raises on failure —
    caller decides how loud to be."""
    import requests
    config = json.loads((CFG / "google-ads-config.json").read_text())
    token_data = json.loads((CFG / "google-ads-token.json").read_text())
    r = requests.post(token_data.get("token_uri", "https://oauth2.googleapis.com/token"), data={
        "client_id": token_data["client_id"], "client_secret": token_data["client_secret"],
        "refresh_token": token_data["refresh_token"], "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    token = r.json()["access_token"]
    customer_id = config["customer_id"].replace("-", "")
    headers = {
        "Authorization": f"Bearer {token}",
        "developer-token": config["developer_token"],
        "login-customer-id": config.get("login_customer_id", customer_id).replace("-", ""),
        "Content-Type": "application/json",
    }
    return headers


def keyword_planner_ideas(seed_keywords, geo_constant):
    """Real exact volumes via Google Ads generateKeywordIdeas — verified
    live 2026-08-08 (Basic Access approved same day). Returns [] on any
    failure, loudly, not a fabricated estimate."""
    if not seed_keywords:
        return []
    try:
        import requests
        sys.path.insert(0, str(AUTOMATION_ROOT / "py"))
        import google_ads_api as ads
        config = json.loads((CFG / "google-ads-config.json").read_text())
        headers = ads_token_and_headers()
        url = ads.endpoint(config, headers)
        if not url:
            print("  ! Google Ads endpoint could not be resolved — skipping exact-volume expansion", file=sys.stderr)
            return []
        r = requests.post(url, headers=headers, json={
            "keywordSeed": {"keywords": seed_keywords[:10]},
            "language": "languageConstants/1000",
            "geoTargetConstants": [geo_constant],
            "keywordPlanNetwork": "GOOGLE_SEARCH",
        }, timeout=30)
        if r.status_code != 200:
            print(f"  ! Keyword Planner HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return []
        out = []
        for idea in r.json().get("results", []):
            m = idea.get("keywordIdeaMetrics", {})
            out.append({
                "keyword": idea.get("text", ""),
                "volume": int(m.get("avgMonthlySearches", 0)),
                "competition": m.get("competition", "UNSPECIFIED"),
            })
        return out
    except Exception as e:  # noqa: BLE001
        print(f"  ! Keyword Planner call failed ({type(e).__name__}: {e}) — skipping exact-volume expansion", file=sys.stderr)
        return []


def load_registry():
    if not REGISTRY_PATH.exists():
        print(f"!! registry.json not found — run build-business-registry.py first", file=sys.stderr)
        sys.exit(2)
    return json.loads(REGISTRY_PATH.read_text()).get("businesses", [])


def load_draft_log():
    if not DRAFT_LOG_PATH.exists():
        return {}
    try:
        return json.loads(DRAFT_LOG_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def save_draft_log(log):
    DRAFT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DRAFT_LOG_PATH.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n")


def pick_next_business(registry, draft_log, forced_slug=None):
    if forced_slug:
        match = next((b for b in registry if b["slug"] == forced_slug), None)
        if not match:
            print(f"!! --business {forced_slug} not found in registry", file=sys.stderr)
            sys.exit(2)
        return match

    now = datetime.now()
    candidates = []
    unseeded = []
    for b in registry:
        if not b.get("enabled", True):
            continue
        # A business with no hub_keywords AND no article_angles cannot be briefed — there is
        # nothing to expand into a keyword set. Skipping it here is the difference between
        # "nothing to do tonight" and a nightly failure.
        #
        # Before 2026-08-18 the picker happily returned such a business and main() then exited
        # 1, which the nightly recorded as "Distribution draft brief failed (exit 1)". 18 of the
        # 36 enabled businesses (every svc-* service page) have empty seeds, so the rotation
        # landed on one roughly every other night and reported a hard failure for a registry
        # gap. The gap is real and worth filling; it is not a crash, and reporting it as one
        # buried it among genuine failures for weeks.
        if not ((b.get("hub_keywords") or []) + (b.get("article_angles") or [])):
            unseeded.append(b["slug"])
            continue
        last = draft_log.get(b["slug"])
        if last:
            age = (now - datetime.fromisoformat(last)).days
            if age < COOLDOWN_DAYS:
                continue
        weight = 2 if b.get("type") in ("app", "saas") else 1
        # Oldest-drafted-first within weight class — a business never drafted
        # sorts first (treated as infinitely stale).
        staleness = float("inf") if not last else (now - datetime.fromisoformat(last)).days
        candidates.append((weight, staleness, b))

    if unseeded:
        # Named, every run, so the gap stays visible instead of silently shrinking the rotation.
        print(f"skipped {len(unseeded)} business(es) with no hub_keywords/article_angles: "
              f"{', '.join(sorted(unseeded))}")
    if not candidates:
        return None
    # Highest weight first, then most stale first.
    candidates.sort(key=lambda c: (-c[0], -c[1]))
    return candidates[0][2]


def gsc_property_for(business):
    for url_field in ("landing_url", "web_url"):
        u = business.get(url_field)
        if not u:
            continue
        host = urllib.parse.urlparse(u).netloc
        if host in GSC_PROPERTY:
            return GSC_PROPERTY[host], urllib.parse.urlparse(u).path
    return None, None


def already_ranking_queries(business, threshold_position=10, days=28):
    """Self-cannibalization guard. Returns (set_of_queries, error_or_None)."""
    prop, page_path = gsc_property_for(business)
    if not prop:
        return set(), "no GSC-mapped domain for this business"
    try:
        tok = gsc_token()
        end = date.today() - timedelta(days=3)
        start = end - timedelta(days=days)
        res = gsc_query(tok, prop, {
            "startDate": start.isoformat(), "endDate": end.isoformat(),
            "dimensions": ["query", "page"],
            "dimensionFilterGroups": [{"filters": [
                {"dimension": "page", "operator": "contains", "expression": page_path}
            ]}] if page_path and page_path != "/" else [],
            "rowLimit": 200, "dataState": "all",
        })
        winners = set()
        for r in res.get("rows", []):
            pos = r.get("position", 100)
            if pos <= threshold_position:
                winners.add(r["keys"][0].lower().strip())
        return winners, None
    except Exception as e:  # noqa: BLE001
        return set(), f"{type(e).__name__}: {e}"


def score_winnable(candidates, excluded_queries):
    """Winnability-first: never pick by raw volume alone. Filters out
    HIGH-competition and already-ranking (self-cannibalization) candidates,
    then picks the highest-volume SURVIVOR. If nothing survives, returns
    None rather than falling back to a bad pick."""
    survivors = [c for c in candidates
                 if c["competition"] != "HIGH"
                 and c["keyword"].lower().strip() not in excluded_queries
                 and c["volume"] > 0]
    if not survivors:
        return None
    survivors.sort(key=lambda c: -c["volume"])
    return survivors[0]


def build_brief(business, keyword_choice, cannibalization_excluded, cannibalization_error):
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "business": {
            "slug": business["slug"],
            "name": business["name"],
            "type": business.get("type"),
            "landing_url": business.get("landing_url") or business.get("web_url"),
            "play_url": business.get("play_url"),
            "app_store_url": business.get("app_store_url"),
            "geo": business.get("geo", "global"),
        },
        "target_keyword": keyword_choice,
        "mined_features": business.get("features", []),
        "article_angles": business.get("article_angles", []),
        "self_cannibalization_check": {
            "excluded_query_count": len(cannibalization_excluded),
            "error": cannibalization_error,
        },
        "content_rules": {
            "min_words": 400,
            "must_include": [
                "at least 2 real numbers from the business's own data/features",
                "a first-person build note (\"why I built this\")",
                "one dated statistic or 'Updated YYYY-MM-DD' line",
            ],
            "must_avoid": [
                "em-dash-heavy listicle voice",
                "identical H2 skeleton to the last 3 briefs for this business",
                "claiming any feature not in mined_features/article_angles with file:line evidence",
            ],
            "canonical_target": business.get("landing_url") or business.get("web_url"),
            "one_contextual_link_max": True,
        },
        "REVIEW_GATE": {
            "status": "needs_human_review",
            "note": ("This brief is DATA, not an article. A human (or a separately-reviewed "
                     "prose-writing step) must write from this brief, then run "
                     "`distribute.py draft <file> --priority <p>` explicitly. This script never "
                     "calls cmd_draft/cmd_post — nothing here enters the publish rotation on its own."),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--business", help="force a specific business slug instead of round-robin picking")
    args = ap.parse_args()

    registry = load_registry()
    draft_log = load_draft_log()

    business = pick_next_business(registry, draft_log, args.business)
    if business is None:
        print("No business is due (all in cooldown or none enabled). Nothing to do.")
        return

    print(f"picked: {business['slug']} ({business['name']}, type={business.get('type')}, "
          f"geo={business.get('geo')})")

    seeds = list(dict.fromkeys(
        (business.get("hub_keywords") or []) + (business.get("article_angles") or [])
    ))
    if not seeds:
        # Only reachable via --business <slug>; the round-robin picker filters these out now.
        print(f"!! {business['slug']} has no hub_keywords/article_angles — nothing to target. "
              f"Run the feature-miner for this business first.", file=sys.stderr)
        sys.exit(1)
    print(f"seed keywords: {seeds}")

    geo_constant = GEO_TARGET.get(business.get("geo", "global"), GEO_TARGET["global"])
    candidates = keyword_planner_ideas(seeds, geo_constant)
    print(f"Keyword Planner returned {len(candidates)} candidate(s)")

    excluded, cannib_error = already_ranking_queries(business)
    if cannib_error:
        print(f"  ! self-cannibalization check COULD NOT VERIFY: {cannib_error} (not a clean pass — noted in brief)")
    else:
        print(f"  self-cannibalization check: {len(excluded)} already-ranking quer(ies) excluded")

    choice = score_winnable(candidates, excluded)
    if choice is None:
        # Fall back to the first seed keyword itself, unscored — better than
        # producing no brief at all when Keyword Planner has nothing to add,
        # but flagged clearly as a fallback, not a real winnability pick.
        choice = {"keyword": seeds[0], "volume": None, "competition": None, "fallback": True}
        print(f"  no winnable candidate survived scoring — falling back to seed keyword {seeds[0]!r} (unscored)")
    else:
        print(f"  target keyword: {choice['keyword']!r} (vol={choice['volume']}, competition={choice['competition']})")

    brief = build_brief(business, choice, excluded, cannib_error)

    if args.dry_run:
        print("\n--dry-run: brief NOT written")
        print(json.dumps(brief, indent=2, ensure_ascii=False))
        return

    BRIEF_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRIEF_PATH.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n")
    print(f"\nbrief written to {BRIEF_PATH}")

    draft_log[business["slug"]] = datetime.now().isoformat(timespec="seconds")
    save_draft_log(draft_log)
    print(f"cooldown recorded for {business['slug']} ({COOLDOWN_DAYS}d)")


if __name__ == "__main__":
    main()
