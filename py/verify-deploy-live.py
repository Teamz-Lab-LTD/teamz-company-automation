#!/usr/bin/env python3
"""verify-deploy-live.py — did what we just built actually reach the public site?

THE GAP THIS CLOSES
-------------------
Every deploy signal in this repo is an exit code, and an exit code is a claim about
a command, not about the internet.

  nightly-build.sh (tools)   `deploy` is derived from PUSH_EXIT — the exit status of
                             `git push`. tool.teamzlab.com publishes from that push,
                             so a green push is treated as a green deploy. If the
                             publish step downstream of GitHub ever breaks, the push
                             still returns 0 and the monitor still says "deploy: ok".
  nightly-site.sh (others)   `deploy` is the exit status of TEAMZ_NIGHTLY_DEPLOY_CMD.
                             goalkit's is an rsync followed by a Cloudflare purge; the
                             purge script is already known to print ERROR and exit 0
                             (see memory reference_cloudflare_purge), so a stale-CDN
                             night can look clean.

Measured 2026-08-14 on tools: nightly-status.json said `deploy: unknown` and there was
no way to resolve it from inside the repo. One HTTP request settled it — the live
tools.json carried the date-only `generated` field pushed an hour earlier, so the
deploy had in fact landed. That request is what this file automates.

WHAT IT CHECKS
--------------
The sitemap is the one artifact every property regenerates on every build, so it is
the closest thing to a build stamp that all four share. This fetches the LIVE sitemap
(following a sitemap index if that is what is served), reads the LOCAL one, and
compares the URL sets:

    urls_local - urls_live   built here, NOT on the server  -> DEPLOY DID NOT LAND
    urls_live - urls_local   on the server, not built here  -> stale files server-side

A missing-from-live set is the failure that matters: it is exactly what "I shipped 6
new pages and none of them are public" looks like.

FAIL LOUD, NEVER QUIET
----------------------
An unreachable site, an unparseable sitemap, or a local sitemap that cannot be found
all exit 2 with a distinct message. None of them may read as "deploy ok" — the entire
reliability layer exists because "couldn't check" once rendered the same as "all
clear".

Usage:
  python3 verify-deploy-live.py                       # uses TEAMZ_SITE_URL
  python3 verify-deploy-live.py --site https://x/ --local path/to/sitemap.xml
  python3 verify-deploy-live.py --json                # machine-readable, for the digest

Exit codes: 0 = live matches local · 1 = pages built but not live · 2 = could not check
"""
import argparse
import gzip
import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
UA = "teamzlab-deploy-verify/1.0"
# Where a property's freshly built sitemap tends to sit, most specific first. Tried in
# order and the first that exists wins; if none do, that is an exit-2, never a pass.
LOCAL_CANDIDATES = [
    "sitemap.xml", "dist/sitemap-index.xml", "dist/sitemap.xml",
    "public/sitemap.xml", "sitemap-index.xml", "dist/sitemap-0.xml",
]


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def urls_from_xml(raw, base=None, depth=0):
    """URL set from a sitemap or sitemap index. Follows one level of index."""
    root = ET.fromstring(raw)
    tag = root.tag.split("}")[-1]
    if tag == "sitemapindex":
        if depth > 1:
            return set()
        out = set()
        for sm in root.findall("s:sitemap", NS):
            loc = sm.find("s:loc", NS)
            if loc is None or not loc.text:
                continue
            try:
                out |= urls_from_xml(fetch(loc.text.strip()), base, depth + 1)
            except Exception as e:  # noqa: BLE001
                # A child sitemap that will not load means the answer is incomplete.
                # Say so rather than returning a short set that reads as "fewer pages".
                raise RuntimeError(f"child sitemap {loc.text.strip()} failed: "
                                   f"{type(e).__name__}") from e
        return out
    return {u.find("s:loc", NS).text.strip()
            for u in root.findall("s:url", NS)
            if u.find("s:loc", NS) is not None and u.find("s:loc", NS).text}


def find_local(root, explicit):
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = root / p
        return p if p.exists() else None
    for c in LOCAL_CANDIDATES:
        p = root / c
        if p.exists():
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=os.getenv("TEAMZ_SITE_URL", "").strip())
    ap.add_argument("--root", default=os.getenv("TEAMZ_HOST_SITE_ROOT", "").strip() or ".")
    ap.add_argument("--local", default="", help="path to the locally built sitemap")
    ap.add_argument("--remote-path", default=os.getenv("TEAMZ_SITEMAP_PATH", "").strip(),
                    help="sitemap path on the live site (auto-probed when unset)")
    ap.add_argument("--max-list", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    def bail(msg, payload=None):
        if args.json:
            print(json.dumps({"state": "could-not-check", "reason": msg,
                              **(payload or {})}))
        else:
            print(f"verify-deploy-live: COULD NOT CHECK — {msg}", file=sys.stderr)
        return 2

    if not args.site:
        return bail("no --site and TEAMZ_SITE_URL is unset")
    site = args.site.rstrip("/") + "/"
    root = Path(args.root).resolve()

    local_path = find_local(root, args.local)
    if local_path is None:
        return bail(f"no local sitemap found under {root} "
                    f"(tried: {', '.join(LOCAL_CANDIDATES)})")

    try:
        local_urls = urls_from_xml(local_path.read_bytes())
    except Exception as e:  # noqa: BLE001
        return bail(f"local sitemap {local_path.name} unparseable: {type(e).__name__}: {e}")
    if not local_urls:
        return bail(f"local sitemap {local_path.name} lists 0 URLs")

    candidates = [args.remote_path] if args.remote_path else ["sitemap.xml", "sitemap-index.xml"]
    live_urls, used, last_err = None, None, None
    for cand in candidates:
        try:
            live_urls = urls_from_xml(fetch(site + cand.lstrip("/")))
            used = cand
            break
        except Exception as e:  # noqa: BLE001
            last_err = f"{cand}: {type(e).__name__}: {e}"
    if live_urls is None:
        return bail(f"no live sitemap readable at {site} ({last_err})")

    missing = sorted(local_urls - live_urls)
    extra = sorted(live_urls - local_urls)
    state = "not-live" if missing else "live"

    if args.json:
        print(json.dumps({
            "state": state, "site": site, "remote_sitemap": used,
            "local_sitemap": str(local_path.relative_to(root)),
            "local_urls": len(local_urls), "live_urls": len(live_urls),
            "missing_from_live": len(missing), "stale_on_live": len(extra),
            "missing_sample": missing[:args.max_list],
        }))
    else:
        print(f"verify-deploy-live [{site}] via {used}: "
              f"local {len(local_urls)} URLs, live {len(live_urls)}")
        if missing:
            print(f"  ✗ {len(missing)} page(s) built here are NOT on the live site — "
                  f"the deploy did not land:")
            for u in missing[:args.max_list]:
                print(f"      {u}")
            if len(missing) > args.max_list:
                print(f"      … and {len(missing) - args.max_list} more")
        else:
            print("  ✓ every locally built URL is present on the live site")
        if extra:
            # Not a failure: a page deleted locally lingers server-side until the next
            # --delete rsync, and some properties serve extra URLs by design.
            print(f"  note: {len(extra)} URL(s) live but not in the local sitemap "
                  f"(e.g. {extra[0]})")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
