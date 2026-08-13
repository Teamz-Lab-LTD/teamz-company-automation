#!/usr/bin/env python3
"""
build-marooned-pages.py — pages that are linked, indexed, and still unreachable.

WHY THE EXISTING ORPHAN CHECK MISSES THESE
------------------------------------------
scripts/build-fix-orphans.py defines an orphan as "a tool page that no other tool links to",
and fixes it by adding a link from a sibling. Good, and not enough. Measured on
tool.teamzlab.com 2026-08-14:

    nfl/nfl-playoff-predictor           2 inbound links   0 impressions / 90d
    nfl/nfl-passer-rating-calculator    2 inbound links   0 impressions / 90d
    us/fantasy-football-trade-analyzer  2 inbound links   0 impressions / 90d

Not orphans. They have links. Every one of those links comes from nfl/index.html — which itself
drew FOUR impressions in ninety days — or from each other. Three pages, all indexed (URL
Inspection: "Submitted and indexed"), pointing at each other on an island nobody visits.

A link from a page with no traffic is not a link. Counting inbound links without asking whether
the SOURCE has any authority is how a page passes an orphan check and still gets zero. That is
the whole defect, and it took the owner asking six questions to surface one instance of it.

WHAT COUNTS AS MAROONED
-----------------------
    the page gets almost no impressions itself                (it is not working)
    AND it is not noindex/excluded                            (it is meant to work)
    AND no page linking to it has meaningful traffic          (nothing can send it any)

The third clause is the one that is new. It is also the only one that suggests a fix: name the
best DONOR — the highest-traffic page that is topically adjacent — so the link goes somewhere
that can actually pass authority, rather than to another quiet sibling.

WHAT IT DOES NOT DO
-------------------
It does not edit pages. Inserting a link means writing a sentence that earns it, in the donor
page's voice, and a link dropped into a footer block is worth roughly what it costs to add. The
nightly content agent writes that sentence; this reports the pair and stops. Same split as
build-keyword-target-audit.py, and for the same reason: a confident wrong edit to a page that
earns money is worse than a report nobody reads.

Usage:
  python3 build-marooned-pages.py --site tools
  python3 build-marooned-pages.py --site apps --max-impr 5
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

CFG = Path.home() / ".config" / "teamzlab"
PROJECTS = Path(__file__).resolve().parent.parent.parent

SITES = {
    "tools":   ("teamzlab-tools", "https://tool.teamzlab.com/"),
    "apps":    ("teamz-lab-generic-landing-pages", "https://apps.teamzlab.com/"),
    "learn":   ("teamz-lab-learning", "https://learn.teamzlab.com/"),
    "goalkit": ("goalkit-bd", "sc-domain:goalkit.teamzlab.com"),
}

# A page under this many impressions in the window is "not working".
MAX_IMPR = int(os.getenv("TEAMZ_MAROON_MAX_IMPR", "10"))
# A linking page needs at least this many impressions before it counts as a real road in.
# nfl/index.html had 4 — which is why three pages passed the orphan check and got nothing.
DONOR_MIN_IMPR = int(os.getenv("TEAMZ_MAROON_DONOR_MIN_IMPR", "100"))


def token():
    t = json.loads((CFG / "search-console-token.json").read_text())
    data = urllib.parse.urlencode({
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data),
        timeout=30))["access_token"]


def impressions_by_path(prop, tok, days=90):
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=days - 1)
    body = json.dumps({"startDate": start.isoformat(), "endDate": end.isoformat(),
                       "dimensions": ["page"], "rowLimit": 25000}).encode()
    url = ("https://www.googleapis.com/webmasters/v3/sites/"
           f"{urllib.parse.quote(prop, safe='')}/searchAnalytics/query")
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    out = {}
    for r in json.load(urllib.request.urlopen(req, timeout=180)).get("rows", []):
        p = r["keys"][0].split("teamzlab.com", 1)[-1] or "/"
        out[p] = out.get(p, 0.0) + r["impressions"]
    return out


def link_graph(root):
    """{target_path: set(source_path)} from the built HTML.

    Reads shipped markup rather than a link registry: what the crawler sees is what counts, and
    a registry that has drifted from the pages is exactly the kind of thing that reports health
    while the site is broken."""
    pages, graph = [], {}
    for f in root.rglob("index.html"):
        rel = "/" + str(f.parent.relative_to(root)).replace("\\", "/").strip("./") + "/"
        if rel == "//":
            rel = "/"
        if any(seg in rel for seg in ("/node_modules/", "/dist/", "/.git/")):
            continue
        pages.append((rel, f))
    for rel, f in pages:
        try:
            html = f.read_text(errors="ignore")
        except OSError:
            continue
        for m in re.finditer(r'href="(/[^"#?]*/)"', html):
            tgt = m.group(1)
            if tgt == rel:
                continue
            graph.setdefault(tgt, set()).add(rel)
    return {p for p, _ in pages}, graph


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="tools", choices=sorted(SITES))
    ap.add_argument("--max-impr", type=int, default=MAX_IMPR)
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    repo, prop = SITES[args.site]
    root = PROJECTS / repo
    if not root.exists():
        print(f"ERROR: {root} not found", file=sys.stderr)
        return 1

    try:
        impr = impressions_by_path(prop, token(), days=90)
    except Exception as e:  # noqa: BLE001
        # Never fall back to "0 impressions everywhere" — that would mark the entire site
        # marooned and bury the real cases in noise.
        print(f"marooned: UNREACHABLE — Search Console failed ({type(e).__name__}). "
              "No verdict this run.", file=sys.stderr)
        return 1

    pages, graph = link_graph(root)
    marooned = []
    for p in sorted(pages):
        if impr.get(p, 0.0) > args.max_impr:
            continue
        sources = graph.get(p, set())
        best_donor = max(sources, key=lambda s: impr.get(s, 0.0), default=None)
        best_impr = impr.get(best_donor, 0.0) if best_donor else 0.0
        if best_impr >= DONOR_MIN_IMPR:
            continue                      # already has a real road in; low traffic is a different problem
        # Suggest a donor: the highest-traffic page sharing this page's first path segment,
        # i.e. topically adjacent rather than merely popular. A link from an unrelated page is
        # a link Google discounts and a reader never clicks.
        # DONOR CHOICE IS TOPIC FIRST, TRAFFIC SECOND.
        # Picking the highest-traffic page in the hub proposed the same donor for every page in
        # /finance/ — a business-loan comparison tool as the suggested source for a Roth IRA
        # calculator, a debt consolidator and a home-equity calculator alike. A link like that is
        # one no reader clicks and Google discounts, and the sentence carrying it would have to be
        # invented. Rank by shared slug words first, so the suggestion is a page whose readers
        # plausibly want the target, and use traffic only to break ties.
        hub = ("/" + p.strip("/").split("/")[0] + "/") if p.strip("/") else "/"
        def _toks(path):
            return set(re.split(r"[-/]+", path.strip("/").lower())) - {
                "calculator", "comparison", "vs", "tool", "free", "online", "2026", "2027", ""}
        tgt_toks = _toks(p)
        cands = []
        for q, v in impr.items():
            if v < DONOR_MIN_IMPR or q == p:
                continue
            overlap = len(tgt_toks & _toks(q))
            same_hub = q.startswith(hub)
            if not overlap and not same_hub:
                continue
            cands.append((overlap, same_hub, v, q))
        cands.sort(reverse=True)
        cands = [(v, q) for _, _, v, q in cands]
        marooned.append({
            "path": p,
            "impressions_90d": round(impr.get(p, 0.0)),
            "inbound_links": len(sources),
            "best_existing_source": best_donor,
            "best_existing_source_impr": round(best_impr),
            "suggested_donor": cands[0][1] if cands else None,
            "suggested_donor_impr": round(cands[0][0]) if cands else 0,
        })

    # Worst first = most inbound links with least effect. A page with 5 links and no traffic is a
    # louder finding than one with 0: it means the link-building already ran and achieved nothing.
    marooned.sort(key=lambda r: (-r["inbound_links"], r["path"]))
    out = root / "data" / "marooned-pages.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at": date.today().isoformat(),
        "site": args.site,
        "thresholds": {"max_impr": args.max_impr, "donor_min_impr": DONOR_MIN_IMPR},
        "pages_scanned": len(pages),
        "marooned_count": len(marooned),
        "marooned": marooned[:500],
    }, indent=2))

    print(f"marooned pages [{args.site}]: {len(marooned)} of {len(pages)} scanned — indexed, "
          f"linked, and no inbound link from any page above {DONOR_MIN_IMPR} impressions")
    for r in marooned[:args.top]:
        src = (f"{r['best_existing_source']} ({r['best_existing_source_impr']} impr)"
               if r["best_existing_source"] else "nothing links here")
        print(f"    {r['impressions_90d']:>4} impr  {r['inbound_links']} link(s) from {src}")
        print(f"          {r['path']}")
        if r["suggested_donor"]:
            print(f"          -> link it from {r['suggested_donor']} "
                  f"({r['suggested_donor_impr']} impr)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
