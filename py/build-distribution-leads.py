#!/usr/bin/env python3
"""
Distribution Leads Tracker — is distribution actually earning anything, per
business, and is that changing over time?

WHAT THIS IS HONEST ABOUT: "leads" here means the best signal actually
available in this stack — GA4 sessions + engagement + outbound-click/CTA
events from sessions that landed via a known distribution platform, matched
to a business via its registered landing URL. It is NOT a CRM lead count and
NOT a confirmed app install — Play/App Store installs are not attributable
without a mobile measurement partner (AppsFlyer/Adjust/etc.), which is not
wired up anywhere in this stack. Reporting a store-click as an "install"
would be exactly the kind of false-precision this repo's own memory
(feedback_revenue_ground_truth, feedback_asc_sales_report_is_per_vendor) has
been burned by before. Call it what it is: interest signal, not conversion
proof.

WHY IT EXISTS: the owner asked, explicitly, for a way to judge — after 2-3
months — whether distribution is adding real value per business, not just
whether it's technically running. distribute.py outcome (activity) and
build-growth-digest.py's Distribution section (site-wide outcome) both
already exist; this is the business-level breakdown neither of those does,
and it's the one that answers "which businesses is this actually helping."

METHOD: pull GA4 landing pages + sessionSource for the tools and apps
properties, keep only rows whose source matches a known distribution
platform host, match each landing page's PATH against every registered
business's landing_url/web_url (registry.json), and aggregate. Appends one
dated snapshot per run to data/distribution-leads-history.jsonl (append-only
— never rewrites past snapshots) so a trend is readable months from now
without having re-queried GA4's finite lookback window in time.

Usage:
  python3 py/build-distribution-leads.py                 # pull + append + print
  python3 py/build-distribution-leads.py --report-only    # print latest + trend, no new GA4 pull
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import importlib.util

AUTOMATION_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_ROOT = AUTOMATION_ROOT.parent
REGISTRY_PATH = AUTOMATION_ROOT / "distribute" / "registry.json"
HISTORY_PATH = AUTOMATION_ROOT / "data" / "distribution-leads-history.jsonl"

DIST_HOSTS = ("dev.to", "hashnode", "blogspot", "blogger", "bsky", "bluesky", "mastodon",
              "pinterest", "telegraph", "substack", "github", "tumblr", "medium",
              "gitlab", "sites.google", "tiktok", "youtube", "wordpress")

# Interest-signal events already firing in GA4 (verified live 2026-08-08) that
# indicate someone did more than just land — clicked toward a store, a CTA,
# or an app card. This is the closest thing to a "lead" this stack can prove.
LEAD_EVENTS = ("outbound_click", "cta_click", "app_card_click", "tutorial_llm_optin")


def _load_digest_module():
    spec = importlib.util.spec_from_file_location(
        "digest", str(AUTOMATION_ROOT / "py" / "build-growth-digest.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_registry():
    if not REGISTRY_PATH.exists():
        print(f"!! registry.json not found at {REGISTRY_PATH} — run build-business-registry.py first", file=sys.stderr)
        sys.exit(2)
    doc = json.loads(REGISTRY_PATH.read_text())
    # path -> business, built from every URL field a business carries
    by_path = {}
    for biz in doc.get("businesses", []):
        for url_field in ("landing_url", "web_url"):
            u = biz.get(url_field)
            if not u:
                continue
            path = urlparse(u).path.rstrip("/") or "/"
            by_path[path] = biz["slug"]
    return doc.get("businesses", []), by_path


def match_business(landing_page_path, by_path):
    """Longest-prefix match — a business's landing_url is usually a prefix
    of the actual pages under it (e.g. /football/ hub vs individual tools)."""
    path = (landing_page_path or "/").split("?")[0].rstrip("/") or "/"
    if path in by_path:
        return by_path[path]
    best, best_len = None, 0
    for p, slug in by_path.items():
        if p != "/" and path.startswith(p) and len(p) > best_len:
            best, best_len = slug, len(p)
    return best


def pull_property(d, prop_key, tok, start, end, by_path):
    prop = d.GA4_PROPERTY.get(prop_key)
    if not prop:
        return None, f"no GA4 property configured for {prop_key}"
    try:
        sess_res = d._ga4_report(prop, tok, {
            "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
            "dimensions": [{"name": "landingPagePlusQueryString"}, {"name": "sessionSource"}],
            "metrics": [{"name": "sessions"}, {"name": "totalAdRevenue"},
                        {"name": "engagedSessions"}],
            "limit": 100000,
        })
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"

    rows = sess_res.get("rows", [])
    if not rows:
        return None, "GA4 returned zero rows — treat as unreachable, not zero traffic"

    per_business = {}
    for r in rows:
        page = r["dimensionValues"][0]["value"]
        src = r["dimensionValues"][1]["value"].lower()
        if not any(h in src for h in DIST_HOSTS):
            continue
        sess = int(r["metricValues"][0]["value"])
        rev = float(r["metricValues"][1]["value"])
        eng = int(r["metricValues"][2]["value"])
        biz = match_business(page, by_path) or "(unmatched)"
        row = per_business.setdefault(biz, {"sessions": 0, "revenue": 0.0, "engaged": 0, "lead_events": 0})
        row["sessions"] += sess
        row["revenue"] += rev
        row["engaged"] += eng

    # Second pass: lead-signal event counts, same source filter, joined by path.
    # Separate query because GA4's Data API can't mix a dimension-level source
    # filter cleanly with per-event breakdowns in one call without a segment.
    try:
        evt_res = d._ga4_report(prop, tok, {
            "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
            "dimensions": [{"name": "landingPagePlusQueryString"}, {"name": "sessionSource"}, {"name": "eventName"}],
            "metrics": [{"name": "eventCount"}],
            "dimensionFilter": {"filter": {"fieldName": "eventName",
                                           "inListFilter": {"values": list(LEAD_EVENTS)}}},
            "limit": 100000,
        })
        for r in evt_res.get("rows", []):
            page = r["dimensionValues"][0]["value"]
            src = r["dimensionValues"][1]["value"].lower()
            if not any(h in src for h in DIST_HOSTS):
                continue
            cnt = int(r["metricValues"][0]["value"])
            biz = match_business(page, by_path) or "(unmatched)"
            if biz in per_business:
                per_business[biz]["lead_events"] += cnt
    except Exception:  # noqa: BLE001 — lead-event breakdown is a bonus, not the core metric
        pass

    return per_business, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    businesses, by_path = load_registry()
    slug_to_name = {b["slug"]: b["name"] for b in businesses}

    if not args.report_only:
        d = _load_digest_module()
        tok = d.ga4_token()
        end = date.today() - timedelta(days=3)
        start = end - timedelta(days=args.days)

        combined = {}
        errors = []
        for prop_key in ("teamzlab-tools", "teamz-lab-generic-landing-pages"):
            per_business, err = pull_property(d, prop_key, tok, start, end, by_path)
            if err:
                errors.append(f"{prop_key}: {err}")
                continue
            for biz, row in per_business.items():
                c = combined.setdefault(biz, {"sessions": 0, "revenue": 0.0, "engaged": 0, "lead_events": 0})
                for k in row:
                    c[k] += row[k]

        snapshot = {
            "pulled_at": datetime.now().isoformat(timespec="seconds"),
            "window_days": args.days,
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "errors": errors,
            "businesses": combined,
        }
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_PATH, "a") as f:
            f.write(json.dumps(snapshot) + "\n")
        print(f"snapshot appended to {HISTORY_PATH}")
        if errors:
            print("COULD NOT CHECK (not zero, genuinely unknown):")
            for e in errors:
                print(f"  - {e}")

    # ── Report: latest snapshot + trend vs the OLDEST snapshot on file ──
    if not HISTORY_PATH.exists():
        print("\nNo history yet — this was the first pull, nothing to trend against.")
        return

    lines = [json.loads(l) for l in HISTORY_PATH.read_text().splitlines() if l.strip()]
    if not lines:
        print("\nHistory file empty.")
        return
    latest = lines[-1]
    first = lines[0]
    span_days = (datetime.fromisoformat(latest["pulled_at"]) - datetime.fromisoformat(first["pulled_at"])).days

    print(f"\n{'='*70}")
    print(f"  Distribution Leads — {latest['window_days']}d window, as of {latest['pulled_at'][:10]}")
    if len(lines) > 1:
        print(f"  ({len(lines)} snapshots on file, spanning {span_days}d — this IS your 2-3 month trend)")
    print(f"{'='*70}\n")

    rows = sorted(latest["businesses"].items(), key=lambda kv: -kv[1]["sessions"])
    if not rows:
        print("  No distribution-attributed sessions matched any business this window.")
    else:
        print(f"  {'business':<40}{'sessions':>9}{'engaged':>9}{'lead-evt':>9}{'revenue':>10}")
        for slug, row in rows:
            name = slug_to_name.get(slug, slug)[:38]
            print(f"  {name:<40}{row['sessions']:>9}{row['engaged']:>9}{row['lead_events']:>9}"
                  f"{'$' + format(row['revenue'], '.2f'):>10}")

    if len(lines) > 1:
        print(f"\n  Trend vs first snapshot ({first['pulled_at'][:10]}):")
        first_biz = first["businesses"]
        for slug, row in rows[:10]:
            prev = first_biz.get(slug, {}).get("sessions", 0)
            delta = row["sessions"] - prev
            arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "─")
            name = slug_to_name.get(slug, slug)[:38]
            print(f"    {arrow} {name:<38} {prev} → {row['sessions']} sessions")

    print("\n  NOTE: 'lead-evt' = outbound/CTA/app-card clicks from distribution-sourced "
          "sessions. This is an interest signal, not a confirmed install or CRM lead — "
          "this stack has no mobile attribution partner wired up. Treat it as directional.")


if __name__ == "__main__":
    main()
