#!/usr/bin/env python3
"""Batch URL Inspection via Google Search Console API. Stdlib + google-auth.

====================================================================
  RUN THIS AFTER ANY SCHEMA / CANONICAL / SITEMAP CHANGE
====================================================================
Future LLM: this is a no-excuses checklist. If you (or the user) just
changed JSON-LD, canonical tags, sitemap, or Open Graph / indexation
settings on a page, run this script BEFORE declaring the task done.
It replaces the manual Rich Results Test click-through and catches
mistakes like:
  * Review attached to a non-eligible parent type (Service / CreativeWork)
    → Google validates the JSON but shows "Invalid object type for field
    <parent_node>" in Rich Results. Valid parents are only: Book,
    Course, Event, HowTo, LocalBusiness, MediaObject, Movie,
    Organization, Product, Recipe, SoftwareApplication.
  * Canonical pointing to a different URL than sitemap
    ("Alternate page with proper canonical tag").
  * Pages stuck at "Discovered — currently not indexed".

Example:
  python3 teamz-company-automation/py/inspect-urls.py \\
      --url https://apps.teamzlab.com/vibe-coding-agency/

No argument: inspects every URL in the site's sitemap-0.xml.
====================================================================

Replaces manual Rich Results Test clicks. For each URL:
 - Indexation verdict + coverage state
 - Last crawl time
 - Canonical Google picked (vs your declared canonical)
 - Rich results verdict + per-item detected types

Works on any Teamz project that sources ``.teamz-automation.env``; reads the
shared GSC token at ``~/.config/teamzlab/search-console-token.json``.

Quota: ~2000 inspections/day per property, ~600/minute. Script sleeps
between calls to stay safe.

Usage:
  python3 inspect-urls.py                                   # checks TEAMZ_SITE_PROPERTY sitemap
  python3 inspect-urls.py --url https://apps.teamzlab.com/vibe-coding-agency/ ...
  python3 inspect-urls.py --file docs/urls-to-inspect.txt   # one URL per line
  python3 inspect-urls.py --rich-only                       # skip indexation details

Exit code is non-zero when any URL fails rich-results or is not indexed.
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

SC_TOKEN = os.path.expanduser(
    os.environ.get("TEAMZ_SC_TOKEN_FILE", "~/.config/teamzlab/search-console-token.json")
)
# Do NOT append "/" to an unset value. `"".rstrip("/") + "/"` yields "/", which is TRUTHY, so
# the "must be set" guard below could never fire — the script printed `Property: /`, sent that
# to the API and got HTTP 400 "Invalid input" on every URL. A missing config read as a bad
# request instead of as a missing config.
_su = os.environ.get("TEAMZ_SITE_URL", "").strip()
SITE_URL = (_su.rstrip("/") + "/") if _su else ""
SITE_PROPERTY = os.environ.get("TEAMZ_SITE_PROPERTY", SITE_URL)
GCP_PROJECT = os.environ.get("TEAMZ_GOOGLE_CLOUD_PROJECT", "")

VERDICT_ICON = {"PASS": "OK  ", "PARTIAL": "WARN", "FAIL": "FAIL", "NEUTRAL": "?   "}


def _get_access_token():
    if not os.path.exists(SC_TOKEN):
        sys.exit(f"ERROR: GSC token not found at {SC_TOKEN}. Run build-search-console-auth.py first.")
    d = json.load(open(SC_TOKEN))
    body = urllib.parse.urlencode(
        {
            "client_id": d["client_id"],
            "client_secret": d["client_secret"],
            "refresh_token": d["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode()
    r = urllib.request.urlopen(urllib.request.Request(d["token_uri"], data=body))
    return json.loads(r.read())["access_token"]


def _inspect(token, url, attempts=3):
    body = {
        "inspectionUrl": url,
        "siteUrl": SITE_PROPERTY,
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if GCP_PROJECT:
        headers["x-goog-user-project"] = GCP_PROJECT

    last_err = None
    for i in range(attempts):
        req = urllib.request.Request(
            "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST",
        )
        try:
            r = urllib.request.urlopen(req, timeout=45)
            return json.loads(r.read())
        except urllib.error.HTTPError as e:
            # 429 / 503 → backoff & retry; other HTTP errors → return
            if e.code in (429, 500, 502, 503, 504) and i < attempts - 1:
                time.sleep(2 + i * 3)
                continue
            return {"error": {"code": e.code, "message": e.read().decode()[:300]}}
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            last_err = e
            if i < attempts - 1:
                time.sleep(1.5 + i * 2)
                continue
    return {"error": {"code": "timeout", "message": str(last_err)[:200]}}


def _urls_from_sitemap():
    host = SITE_URL.rstrip("/")
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    pages: list[str] = []
    tried = []
    # Browser UA is needed — Cloudflare-fronted origins (teamzlab.com included)
    # return HTTP 403 to urllib's default "Python-urllib/X.Y" identifier.
    ua_headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/xml,text/xml,*/*",
    }
    # Start from the index, fall back to sitemap-0.xml, then sitemap.xml
    for path in ("sitemap-index.xml", "sitemap-0.xml", "sitemap.xml"):
        tried.append(f"{host}/{path}")
        try:
            r = urllib.request.urlopen(urllib.request.Request(f"{host}/{path}", headers=ua_headers), timeout=20)
            root = ET.fromstring(r.read().decode())
        except Exception:
            continue
        # sitemap index — fetch each child sitemap
        for sm in root.findall("ns:sitemap/ns:loc", ns):
            try:
                rr = urllib.request.urlopen(urllib.request.Request(sm.text, headers=ua_headers), timeout=20)
                sub = ET.fromstring(rr.read().decode())
                for loc in sub.findall("ns:url/ns:loc", ns):
                    if loc.text:
                        pages.append(loc.text)
            except Exception:
                pass
        # or direct urlset
        for loc in root.findall("ns:url/ns:loc", ns):
            if loc.text:
                pages.append(loc.text)
        if pages:
            # strip non-page extensions (llms.txt, .xml, etc.)
            return [u for u in pages if not u.endswith((".txt", ".xml"))]
    sys.stderr.write(f"  (sitemap probe tried: {', '.join(tried)})\n")
    return []


def _print_row(url, data, rich_only=False):
    err = data.get("error")
    if err:
        print(f"  FAIL http={err.get('code')}  {url}  — {err.get('message', '')[:80]}")
        return False

    result = data.get("inspectionResult", {})
    idx = result.get("indexStatusResult", {})
    rich = result.get("richResultsResult", {})

    idx_verdict = idx.get("verdict", "NEUTRAL")
    idx_cov = idx.get("coverageState", "")
    last_crawl = idx.get("lastCrawlTime", "—")
    google_canon = idx.get("googleCanonical", "")

    rich_verdict = rich.get("verdict", "—")
    rich_items = rich.get("detectedItems", []) or []

    idx_ok = idx_verdict == "PASS"
    rich_ok = rich_verdict in ("PASS", "—") and not any(
        x.get("items", [{}])[0].get("issues") for x in rich_items
    )

    line_parts = []
    if not rich_only:
        line_parts.append(f"idx={VERDICT_ICON.get(idx_verdict, idx_verdict)}")
        line_parts.append(f"cov={idx_cov or '-':<30}")
    line_parts.append(f"rich={VERDICT_ICON.get(rich_verdict, rich_verdict)}")
    print(f"  {' '.join(line_parts)}  {url}")

    # rich result details (types + issues)
    for item in rich_items:
        rtype = item.get("richResultType", "?")
        sub = item.get("items", [])
        issues_total = sum(len(s.get("issues", [])) for s in sub)
        issues_critical = sum(
            1
            for s in sub
            for i in s.get("issues", [])
            if i.get("severity") == "ERROR"
        )
        status = "OK" if issues_total == 0 else f"{issues_critical}/{issues_total} errs"
        print(f"      {rtype:<22} items={len(sub):<3} {status}")
        # dump first issue per item block for quick debug
        if issues_total:
            for s in sub[:3]:
                for i in s.get("issues", [])[:2]:
                    print(f"        - {i.get('severity', '?')} {i.get('issueMessage', '')}")

    if not rich_only:
        if google_canon and google_canon != url:
            print(f"      canonical picked by Google: {google_canon}")
        if last_crawl != "—":
            print(f"      last crawl: {last_crawl}")

    return idx_ok and rich_ok


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", nargs="+", help="Inspect these exact URL(s).")
    ap.add_argument("--file", help="File with one URL per line.")
    ap.add_argument("--rich-only", action="store_true", help="Skip index-status columns.")
    ap.add_argument("--sleep", type=float, default=0.2, help="Seconds between calls.")
    args = ap.parse_args()

    urls = []
    if args.url:
        urls += args.url
    if args.file:
        urls += [x.strip() for x in open(args.file) if x.strip() and not x.startswith("#")]
    if not urls:
        urls = _urls_from_sitemap()
        if not urls:
            sys.exit("ERROR: no URLs provided and sitemap empty.")
        print(f"Inspecting {len(urls)} URLs from sitemap...")
    else:
        print(f"Inspecting {len(urls)} URL(s)...")

    token = _get_access_token()
    if not SITE_PROPERTY:
        sys.exit("ERROR: TEAMZ_SITE_PROPERTY (or TEAMZ_SITE_URL) must be set.")
    print(f"Property: {SITE_PROPERTY}\n")

    bad = 0
    pass_ = 0
    for u in urls:
        data = _inspect(token, u)
        ok = _print_row(u, data, rich_only=args.rich_only)
        if ok:
            pass_ += 1
        else:
            bad += 1
        if args.sleep > 0:
            time.sleep(args.sleep)

    print(f"\nSummary: {pass_} OK, {bad} not OK  (of {len(urls)})")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
