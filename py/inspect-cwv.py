#!/usr/bin/env python3
"""Batch Core Web Vitals + Lighthouse scores via PageSpeed Insights API.

Why this script exists: Google uses field CWV (real Chrome user data) as a
ranking signal. Lab scores (Lighthouse) flag likely regressions. Running this
after any significant frontend change catches LCP blow-ups from new images,
CLS from layout shifts, INP regressions from heavy JS bundles — without
opening the PSI web UI per URL.

Reads key from ~/.config/teamzlab/pagespeed-api-key.txt (or env
TEAMZ_PAGESPEED_KEY_FILE). Stdlib-only.

Usage:
    python3 inspect-cwv.py                       # audit TEAMZ_SITE_URL's sitemap
    python3 inspect-cwv.py --url URL [URL ...]   # ad-hoc URLs
    python3 inspect-cwv.py --file urls.txt       # one URL per line
    python3 inspect-cwv.py --strategy mobile|desktop   # default mobile

Exit non-zero if any URL fails CWV thresholds so CI can gate releases.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

KEY_FILE = os.path.expanduser(
    os.environ.get("TEAMZ_PAGESPEED_KEY_FILE", "~/.config/teamzlab/pagespeed-api-key.txt")
)
SITE_URL = os.environ.get("TEAMZ_SITE_URL", "").rstrip("/") + "/"
PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# CWV good thresholds (Google's official cutoffs, 2025)
GOOD = {
    "LCP_S": 2.5,   # seconds
    "INP_MS": 200,  # milliseconds
    "CLS": 0.10,
    "FCP_S": 1.8,
    "TTFB_MS": 800,
}


def _key() -> str:
    p = Path(KEY_FILE)
    if not p.exists():
        sys.exit(f"ERROR: PSI key not found at {KEY_FILE}. See TEAMZ_PAGESPEED_KEY_FILE.")
    return p.read_text().strip()


def _query(url: str, strategy: str, api_key: str, attempts: int = 3) -> dict:
    q = urllib.parse.urlencode(
        {
            "url": url,
            "strategy": strategy,
            "key": api_key,
            "category": ["PERFORMANCE", "SEO", "ACCESSIBILITY", "BEST_PRACTICES"],
        },
        doseq=True,
    )
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(f"{PSI_ENDPOINT}?{q}", timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < attempts - 1:
                time.sleep(3 + i * 3)
                continue
            return {"error": {"code": e.code, "message": e.read().decode()[:300]}}
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            last_err = e
            if i < attempts - 1:
                time.sleep(2 + i * 2)
                continue
    return {"error": {"code": "timeout", "message": str(last_err)[:200]}}


def _pct(scores: dict, key: str) -> str:
    v = scores.get(key, {}).get("score")
    if v is None:
        return "—"
    return f"{int(round(v * 100))}"


def _field(exp: dict, metric: str) -> tuple[str, str]:
    """Returns (value_display, good/ni/poor verdict)."""
    cwv = exp.get("metrics", {}).get(metric)
    if not cwv:
        return "—", ""
    category = cwv.get("category", "")
    verdict = {"FAST": "good", "AVERAGE": "ni", "SLOW": "poor"}.get(category, category.lower())
    val = cwv.get("percentile")
    if val is None:
        return "—", verdict
    if metric in ("LARGEST_CONTENTFUL_PAINT_MS", "INTERACTION_TO_NEXT_PAINT", "EXPERIMENTAL_TIME_TO_FIRST_BYTE", "FIRST_CONTENTFUL_PAINT_MS"):
        if metric == "LARGEST_CONTENTFUL_PAINT_MS" or metric == "FIRST_CONTENTFUL_PAINT_MS":
            return f"{val / 1000:.2f}s", verdict
        return f"{val}ms", verdict
    if metric == "CUMULATIVE_LAYOUT_SHIFT_SCORE":
        return f"{val / 100:.2f}", verdict
    return str(val), verdict


def _lab(audits: dict, metric_id: str) -> str:
    a = audits.get(metric_id, {})
    if "displayValue" in a:
        return a["displayValue"].replace(" ", "")
    return "—"


def _emit_row(url: str, data: dict, strategy: str) -> bool:
    err = data.get("error")
    if err:
        print(f"  FAIL {err.get('code')}  {url}  — {err.get('message', '')[:80]}")
        return False

    lr = data.get("lighthouseResult", {})
    cats = lr.get("categories", {})
    audits = lr.get("audits", {})

    perf = _pct(cats, "performance")
    seo = _pct(cats, "seo")
    a11y = _pct(cats, "accessibility")
    bp = _pct(cats, "best-practices")

    exp = data.get("loadingExperience", {})

    lcp, lcp_v = _field(exp, "LARGEST_CONTENTFUL_PAINT_MS")
    inp, inp_v = _field(exp, "INTERACTION_TO_NEXT_PAINT")
    cls, cls_v = _field(exp, "CUMULATIVE_LAYOUT_SHIFT_SCORE")
    ttfb, ttfb_v = _field(exp, "EXPERIMENTAL_TIME_TO_FIRST_BYTE")

    # lab fallback when field data missing
    lab_lcp = _lab(audits, "largest-contentful-paint")
    lab_cls = _lab(audits, "cumulative-layout-shift")
    lab_tbt = _lab(audits, "total-blocking-time")

    label = url.replace(SITE_URL, "/") or "/"
    print(
        f"  {label:46} {strategy[:3]}  perf={perf:>3}  seo={seo:>3}  a11y={a11y:>3}  "
        f"LCP(f)={lcp:>7}[{lcp_v or '-':4}]  INP(f)={inp:>6}[{inp_v or '-':4}]  "
        f"CLS(f)={cls:>4}[{cls_v or '-':4}]  TTFB={ttfb:>6}[{ttfb_v or '-':4}]  "
        f"lab(LCP={lab_lcp} CLS={lab_cls} TBT={lab_tbt})"
    )

    # Fail the row when any field CWV is clearly poor OR perf score < 50
    perf_val = int(perf) if perf.isdigit() else 100
    bad = any(v == "poor" for v in (lcp_v, inp_v, cls_v)) or perf_val < 50
    return not bad


def _sitemap_urls() -> list[str]:
    host = SITE_URL.rstrip("/")
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for path in ("sitemap-index.xml", "sitemap-0.xml", "sitemap.xml"):
        try:
            r = urllib.request.urlopen(f"{host}/{path}", timeout=20)
            root = ET.fromstring(r.read().decode())
        except Exception:
            continue
        pages: list[str] = []
        for sm in root.findall("ns:sitemap/ns:loc", ns):
            try:
                sub = ET.fromstring(urllib.request.urlopen(sm.text, timeout=20).read().decode())
                for loc in sub.findall("ns:url/ns:loc", ns):
                    if loc.text:
                        pages.append(loc.text)
            except Exception:
                pass
        for loc in root.findall("ns:url/ns:loc", ns):
            if loc.text:
                pages.append(loc.text)
        if pages:
            return [u for u in pages if not u.endswith((".txt", ".xml"))]
    return []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", nargs="+")
    ap.add_argument("--file")
    ap.add_argument("--strategy", choices=["mobile", "desktop"], default="mobile")
    ap.add_argument("--sleep", type=float, default=0.4, help="Seconds between calls.")
    args = ap.parse_args()

    urls: list[str] = []
    if args.url:
        urls += args.url
    if args.file:
        urls += [x.strip() for x in open(args.file) if x.strip() and not x.startswith("#")]
    if not urls:
        urls = _sitemap_urls()
    if not urls:
        sys.exit("ERROR: no URLs and sitemap empty.")
    print(f"Auditing {len(urls)} URL(s) — strategy={args.strategy}")
    print()

    api_key = _key()
    bad = 0
    ok = 0
    for u in urls:
        data = _query(u, args.strategy, api_key)
        if _emit_row(u, data, args.strategy):
            ok += 1
        else:
            bad += 1
        if args.sleep > 0:
            time.sleep(args.sleep)

    print()
    print(f"Summary: {ok} OK, {bad} poor/slow  (of {len(urls)})")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
