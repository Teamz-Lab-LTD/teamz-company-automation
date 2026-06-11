#!/usr/bin/env python3
"""
ASO Name-Collision Checker — does a proposed app name clash with existing apps?
====================================================================================
Closes the gap the keyword-competitor scripts miss: they find competitors for
KEYWORDS, but never check whether your exact app NAME is already taken / confusingly
similar (the "Arrow Escape 3D" problem — a dozen apps share that name).

FREE sources (no paid APIs):
  • iTunes Search API (App Store) — reliable JSON
  • Google Play search page — best-effort title scrape

Usage:
  python3 aso-name-collision.py "Arrow Jam 3D"
  python3 aso-name-collision.py "Arrow Jam 3D: Logic Puzzle" --country us
  python3 aso-name-collision.py "Arrow Jam 3D" --json   # machine-readable for /aso-refresh

Exit code: 0 = clear, 1 = similar names exist, 2 = COLLISION (differentiate).
So it can gate a release: `aso-name-collision.py "$NAME" || echo "fix the name"`.
"""
import sys, json, re, urllib.request, urllib.parse


def _http(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) Safari/605.1.15"})
    return urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")


def itunes_search(term, country="us", limit=30):
    url = (f"https://itunes.apple.com/search?term={urllib.parse.quote(term)}"
           f"&country={country}&entity=software&limit={limit}")
    try:
        d = json.loads(_http(url))
        return [{"name": r.get("trackName", ""), "dev": r.get("artistName", ""),
                 "ratings": r.get("userRatingCount", 0) or 0,
                 "bundle": r.get("bundleId", "")} for r in d.get("results", [])]
    except Exception as e:
        return []


def play_search(term, limit=25):
    url = f"https://play.google.com/store/search?q={urllib.parse.quote(term)}&c=apps&hl=en"
    try:
        html = _http(url)
        titles = re.findall(r'aria-label="([^"]{3,70})"', html) + re.findall(r'<span[^>]*>([^<]{3,60})</span>', html)
        seen, out = set(), []
        for t in titles:
            k = t.strip().lower()
            if k and k not in seen and not k.startswith("http"):
                seen.add(k); out.append(t.strip())
        return out[:limit]
    except Exception:
        return []


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def overlap(a, b):
    ta, tb = set(norm(a).split()), set(norm(b).split())
    return len(ta & tb) / max(1, len(ta | tb))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if not args:
        print('usage: aso-name-collision.py "<app name>" [--country us] [--json]'); sys.exit(3)
    full = args[0]
    country = "us"
    if "--country" in sys.argv:
        country = sys.argv[sys.argv.index("--country") + 1]
    full_core = norm(full).split(":")[0].strip()      # full pre-subtitle name (for EXACT-match detection)
    base = re.sub(r"\b(3d|hd|free|game|puzzle)\b", "", full_core).strip() or full_core  # brand core (for overlap)

    ios = itunes_search(full.split(":")[0].strip(), country)
    ios_hits = sorted([{**a, "ov": overlap(base, a["name"])} for a in ios if overlap(base, a["name"]) >= 0.5],
                      key=lambda x: -x["ratings"])
    play = play_search(full.split(":")[0].strip())
    play_hits = [{"name": t, "ov": overlap(base, t)} for t in play if overlap(base, t) >= 0.5]

    # COLLISION (hard, exit 2) = an existing app with the SAME core name. A merely shared
    # prefix ("Arrow Jam 3D" vs "Arrow Jam Escape") is SIMILAR (soft, exit 1), not a blocker.
    exact_ios = [h for h in ios_hits if full_core in (norm(h["name"]), norm(h["name"]).split(":")[0].strip())]
    exact_play = [h for h in play_hits if full_core in (norm(h["name"]), norm(h["name"]).split(":")[0].strip())]
    if exact_ios or exact_play:
        verdict, code = "COLLISION", 2
    elif ios_hits or play_hits:
        verdict, code = "SIMILAR", 1
    else:
        verdict, code = "CLEAR", 0

    if "--json" in flags:
        print(json.dumps({"name": full, "verdict": verdict,
                          "app_store": ios_hits, "play": play_hits}, indent=1))
        sys.exit(code)

    icon = {"COLLISION": "🔴", "SIMILAR": "🟡", "CLEAR": "🟢"}[verdict]
    print(f"=== Name-collision check: {full!r} (core: {base!r}) ===\n")
    print(f"App Store — {len(ios_hits)} close match(es):")
    for h in ios_hits[:8]:
        print(f"  {'🔴' if norm(h['name']).startswith(base) else '⚠️ '} {h['name']!r} by {h['dev']} "
              f"({h['ratings']:,} ratings, overlap {h['ov']:.0%})")
    print(f"\nGoogle Play — {len(play_hits)} close title(s):")
    for h in play_hits[:8]:
        print(f"  {'🔴' if norm(h['name']).startswith(base) else '⚠️ '} {h['name']!r} (overlap {h['ov']:.0%})")
    print(f"\n=== VERDICT: {icon} {verdict} ===")
    if verdict == "COLLISION":
        print("  Your name is already used / closely matched. Differentiate before submit.")
    elif verdict == "SIMILAR":
        print("  Similar names exist (above). Usually OK if your lead word is distinct.")
    else:
        print("  No close name match found. Safe to ship.")
    sys.exit(code)


if __name__ == "__main__":
    main()
