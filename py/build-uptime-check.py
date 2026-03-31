#!/usr/bin/env python3
"""
Site health monitor — checks TEAMZ_SITE_URL + sample pages from sitemap.

Reads sitemap.xml, picks up to 20 random URLs, runs HTTP HEAD against each,
and checks SSL certificate expiry for the domain.

Usage:
    python3 py/build-uptime-check.py              # check + print report
    python3 py/build-uptime-check.py --alert       # exit 1 if any page non-200 or SSL <14d

Data: TEAMZ_DATA_DIR/uptime-latest.json
"""

import json
import os
import random
import re
import socket
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from _teamz_config import load_runtime

_CFG = load_runtime(__file__)


def _read_sitemap_urls(sitemap_path: Path, limit: int = 20) -> list:
    """Extract <loc> URLs from a local sitemap.xml, return up to *limit* random ones."""
    if not sitemap_path.exists():
        return []
    text = sitemap_path.read_text(encoding="utf-8", errors="replace")
    urls = re.findall(r"<loc>\s*(https?://[^<]+?)\s*</loc>", text, re.I)
    if len(urls) > limit:
        urls = random.sample(urls, limit)
    return urls


def _head_check(url: str, timeout: int = 15) -> dict:
    """HTTP HEAD request; returns status_code + response_time_ms."""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", "TeamzUptimeCheck/1.0")
    start = time.monotonic()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        elapsed = (time.monotonic() - start) * 1000
        return {"url": url, "status": resp.status, "ms": round(elapsed, 1), "error": None}
    except urllib.error.HTTPError as e:
        elapsed = (time.monotonic() - start) * 1000
        return {"url": url, "status": e.code, "ms": round(elapsed, 1), "error": str(e.reason)}
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return {"url": url, "status": 0, "ms": round(elapsed, 1), "error": str(e)}


def _check_ssl_expiry(hostname: str, port: int = 443) -> dict:
    """Check SSL certificate expiry date for *hostname*."""
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        not_after = cert.get("notAfter", "")
        expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_left = (expiry - datetime.now(timezone.utc)).days
        return {
            "hostname": hostname,
            "expiry_date": expiry.strftime("%Y-%m-%d"),
            "days_left": days_left,
            "error": None,
        }
    except Exception as e:
        return {"hostname": hostname, "expiry_date": None, "days_left": -1, "error": str(e)}


def main() -> int:
    alert_mode = "--alert" in sys.argv

    site_url = _CFG["site_url"].rstrip("/")
    host_root: Path = _CFG["host_site_root"]
    data_dir: Path = _CFG["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)

    parsed = urllib.parse.urlparse(site_url)
    hostname = parsed.hostname or ""

    print()
    print("=" * 72)
    print(f"  UPTIME CHECK — {site_url}")
    print("=" * 72)

    # 1. Gather URLs: homepage + sitemap sample
    urls = [site_url + "/"]
    sitemap_path = host_root / "sitemap.xml"
    sitemap_urls = _read_sitemap_urls(sitemap_path, limit=20)
    for u in sitemap_urls:
        if u not in urls:
            urls.append(u)
    if not sitemap_urls:
        print(f"\n  Warning: no sitemap.xml at {sitemap_path}")

    # 2. HEAD checks
    print(f"\n  Checking {len(urls)} pages...\n")
    results = []
    failures = []
    for url in urls:
        r = _head_check(url)
        results.append(r)
        status_icon = "OK" if r["status"] == 200 else "FAIL"
        print(f"    [{status_icon:>4s}] {r['status']:>3d}  {r['ms']:>7.0f}ms  {r['url']}")
        if r["status"] != 200:
            failures.append(r)

    avg_ms = sum(r["ms"] for r in results) / len(results) if results else 0
    print(f"\n  Pages checked: {len(results)}")
    print(f"  Avg response:  {avg_ms:.0f}ms")
    print(f"  Failures:      {len(failures)}")

    # 3. SSL check
    ssl_result = {"hostname": hostname, "expiry_date": None, "days_left": -1, "error": "no hostname"}
    ssl_warning = False
    if hostname:
        print(f"\n  Checking SSL for {hostname}...")
        ssl_result = _check_ssl_expiry(hostname)
        if ssl_result["error"]:
            print(f"    SSL ERROR: {ssl_result['error']}")
            ssl_warning = True
        else:
            label = "OK" if ssl_result["days_left"] >= 14 else "WARN"
            print(f"    [{label}] Expires {ssl_result['expiry_date']} ({ssl_result['days_left']} days)")
            if ssl_result["days_left"] < 14:
                ssl_warning = True

    # 4. Write report
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "site_url": site_url,
        "pages_checked": len(results),
        "pages_ok": len(results) - len(failures),
        "pages_failed": len(failures),
        "avg_response_ms": round(avg_ms, 1),
        "ssl": ssl_result,
        "results": results,
    }
    out_path = data_dir / "uptime-latest.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report saved → {out_path.name}")

    # 5. Alert exit code
    if alert_mode and (failures or ssl_warning):
        if failures:
            print(f"\n  ALERT: {len(failures)} page(s) returned non-200")
        if ssl_warning:
            print(f"  ALERT: SSL certificate issue for {hostname}")
        print()
        return 1

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
