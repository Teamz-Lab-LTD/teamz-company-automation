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


def _snapshot_row(url: str, data: dict, strategy: str) -> dict | None:
    """Extract a compact scoreboard row for JSON logging."""
    if data.get("error"):
        return {"url": url, "strategy": strategy, "error": data["error"]}
    lr = data.get("lighthouseResult", {})
    cats = lr.get("categories", {})
    audits = lr.get("audits", {})
    exp = data.get("loadingExperience", {}).get("metrics", {})

    def pct(key: str) -> int | None:
        v = cats.get(key, {}).get("score")
        return int(round(v * 100)) if v is not None else None

    def field(key: str) -> dict | None:
        m = exp.get(key)
        if not m:
            return None
        return {"p75": m.get("percentile"), "category": m.get("category")}

    def lab_raw(audit_id: str, key: str = "numericValue") -> float | None:
        return audits.get(audit_id, {}).get(key)

    return {
        "url": url,
        "strategy": strategy,
        "scores": {
            "performance": pct("performance"),
            "seo": pct("seo"),
            "accessibility": pct("accessibility"),
            "best_practices": pct("best-practices"),
        },
        "field": {
            "LCP": field("LARGEST_CONTENTFUL_PAINT_MS"),
            "INP": field("INTERACTION_TO_NEXT_PAINT"),
            "CLS": field("CUMULATIVE_LAYOUT_SHIFT_SCORE"),
            "FCP": field("FIRST_CONTENTFUL_PAINT_MS"),
            "TTFB": field("EXPERIMENTAL_TIME_TO_FIRST_BYTE"),
        },
        "lab": {
            "lcp_ms": lab_raw("largest-contentful-paint"),
            "cls": lab_raw("cumulative-layout-shift"),
            "tbt_ms": lab_raw("total-blocking-time"),
            "fcp_ms": lab_raw("first-contentful-paint"),
            "tti_ms": lab_raw("interactive"),
            "speed_index_ms": lab_raw("speed-index"),
        },
    }


def _log_snapshot(rows: list[dict], strategy: str, data_dir: str | None) -> str | None:
    """Append today's snapshot to data/cwv-history.json (grouped by date+strategy)."""
    import datetime
    if not data_dir:
        data_dir = os.environ.get("TEAMZ_DATA_DIR", "")
    if not data_dir:
        return None
    path = os.path.join(data_dir, "cwv-history.json")
    history = {"records": []}
    if os.path.exists(path):
        try:
            history = json.loads(open(path).read())
        except Exception:
            pass
    today = datetime.date.today().isoformat()
    # Replace any existing same-day+strategy record so re-running today overwrites
    history["records"] = [
        r for r in history.get("records", []) if not (r.get("date") == today and r.get("strategy") == strategy)
    ]
    history["records"].append({"date": today, "strategy": strategy, "rows": rows})
    history["records"] = history["records"][-120:]  # keep ~4 months of mobile+desktop snapshots
    with open(path, "w") as f:
        json.dump(history, f, indent=2)
    # Also write a flat today-only file for quick grepping
    day_path = os.path.join(data_dir, f"cwv-{today}-{strategy}.json")
    with open(day_path, "w") as f:
        json.dump({"date": today, "strategy": strategy, "rows": rows}, f, indent=2)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", nargs="+")
    ap.add_argument("--file")
    ap.add_argument("--strategy", choices=["mobile", "desktop"], default="mobile")
    ap.add_argument("--sleep", type=float, default=0.4, help="Seconds between calls.")
    ap.add_argument("--log", action="store_true", help="Append snapshot to $TEAMZ_DATA_DIR/cwv-history.json.")
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
    rows: list[dict] = []
    for u in urls:
        data = _query(u, args.strategy, api_key)
        if _emit_row(u, data, args.strategy):
            ok += 1
        else:
            bad += 1
        snap = _snapshot_row(u, data, args.strategy)
        if snap is not None:
            rows.append(snap)
        if args.sleep > 0:
            time.sleep(args.sleep)

    print()
    print(f"Summary: {ok} OK, {bad} poor/slow  (of {len(urls)})")

    if args.log:
        path = _log_snapshot(rows, args.strategy, data_dir=os.environ.get("TEAMZ_DATA_DIR"))
        if path:
            print(f"Logged snapshot → {path}")
        else:
            print("WARN: --log set but TEAMZ_DATA_DIR not resolved; skipped.")

    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
