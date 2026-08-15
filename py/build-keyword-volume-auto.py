#!/usr/bin/env python3
"""
build-keyword-volume-auto — resolve pending Keyword Planner batches via the Google Ads API.

WHAT THIS REPLACES. Keyword demand for the content engine comes from
keyword_volume_manual.load_manual_volume(), which reads Planner exports the owner produced BY
HAND: open data/manual-pull/1-UPLOAD-THESE/batch-NN.csv, paste it into Keyword Planner, export
the results, drop the file into 2-DROP-RESULTS-HERE/. Every batch is a manual chore, so batches
pile up unrun and the engine goes blind on the properties nobody got around to:

    tools    11,838 keywords known   24 batches pending
    learn    80,387 keywords known   12 batches pending
    apps        131 keywords known    3 batches pending   <- effectively blind
    goalkit      90 keywords known    2 batches pending   <- effectively blind

A queue that cannot see demand picks targets by rank alone, which is how apps ended up
spending nights on a position-51 term. The Google Ads API answers the same question the
Planner UI does, so this script is simply the robot that runs the errand.

WHY IT WRITES A CSV INSTEAD OF A NEW DATA PATH. Output goes to 2-DROP-RESULTS-HERE/ in the
exact tab-delimited shape _parse_planner_csv() already accepts. Nothing downstream changes,
nothing downstream can tell the difference, and if this script never runs the engine behaves
exactly as it does today. Adding a parallel "API volume" source that every consumer had to
learn about is how two disagreeing versions of the same number get born.

Files are written as result-<batch>-auto.csv, so a hand-made export is never overwritten. The
loader merges everything under the folder and the higher KNOWN volume wins, which is the same
rule two manual pulls of the same batch already follow.

Usage:
  python3 scripts/build-keyword-volume-auto.py                 # all pending batches, capped
  python3 scripts/build-keyword-volume-auto.py --max-calls 40  # widen the quota for one run
  python3 scripts/build-keyword-volume-auto.py --dry-run       # show what it would ask for
"""
import argparse
import csv
import glob
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

CONFIG_DIR = Path.home() / ".config" / "teamzlab"
ADS_CONFIG = CONFIG_DIR / "google-ads-config.json"
ADS_TOKEN = CONFIG_DIR / "google-ads-token.json"

# Google Ads accepts at most 10 seed keywords per generateKeywordIdeas call but answers with
# the seeds PLUS related ideas, so a single call routinely resolves far more than 10 of ours.
SEEDS_PER_CALL = 10

# Default ceiling on API calls per run. Basic Access allows far more, but a runaway loop over
# 500-row batches is the kind of thing that gets a developer token rate-limited, and the
# batches are not urgent — whatever is left is simply picked up tomorrow night.
DEFAULT_MAX_CALLS = 25

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _teamz_geo  # noqa: E402  — resolves TEAMZ_KW_GEO whether it's a numeric
                   # geoTargetConstant or a country name. See that file's docstring
                   # for why this replaced a local name->id dict: TEAMZ_KW_GEO=2050
                   # (set for goalkit 2026-08-14) silently killed this script's
                   # keyword-batch resolution every night until it was shared.

HEADER = ["Keyword", "Currency", "Segmentation", "Avg. monthly searches",
          "Three month change", "YoY change", "Competition",
          "Competition (indexed value)", "Top of page bid (low range)",
          "Top of page bid (high range)"]


def _token():
    import requests
    cfg = json.loads(ADS_CONFIG.read_text())
    tok = json.loads(ADS_TOKEN.read_text())
    r = requests.post(tok.get("token_uri", "https://oauth2.googleapis.com/token"),
                      data={"client_id": tok["client_id"],
                            "client_secret": tok["client_secret"],
                            "refresh_token": tok["refresh_token"],
                            "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return cfg, r.json()["access_token"]


def read_batch(path):
    """Batch files are a one-column CSV with a 'Keyword' header."""
    out, seen = [], set()
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for i, row in enumerate(csv.reader(fh)):
                if not row:
                    continue
                kw = row[0].strip()
                if i == 0 and kw.lower().startswith("keyword"):
                    continue
                k = kw.lower()
                if kw and k not in seen:
                    seen.add(k)
                    out.append(kw)
    except OSError:
        return []
    return out


def fetch(keywords, geo_id, max_calls, dry_run=False):
    """{keyword: metrics} from the API. Returns ({}, reason) rather than raising."""
    if dry_run:
        return {}, f"dry-run: would issue {min(max_calls, -(-len(keywords)//SEEDS_PER_CALL))} call(s)"
    if not ADS_CONFIG.exists() or not ADS_TOKEN.exists():
        return {}, "no Google Ads credentials in ~/.config/teamzlab"
    try:
        import requests
        cfg, access = _token()
    except Exception as e:  # noqa: BLE001
        return {}, f"auth failed ({type(e).__name__})"

    # Version is negotiated, never hardcoded — see google_ads_api for why (v18 sat dead for
    # months; v21 began being blocked mid-rollout hours after it was pinned).
    import google_ads_api as _ads
    headers = _ads.headers(cfg, access)
    url = _ads.endpoint(cfg, headers)
    if not url:
        return {}, "no Google Ads API version answered — check credentials/approval"

    got, calls = {}, 0
    for i in range(0, len(keywords), SEEDS_PER_CALL):
        if calls >= max_calls:
            break
        seeds = keywords[i:i + SEEDS_PER_CALL]
        calls += 1
        try:
            r = requests.post(url, headers=headers, json={
                "keywordSeed": {"keywords": seeds},
                "language": "languageConstants/1000",
                "geoTargetConstants": [f"geoTargetConstants/{geo_id}"],
                "keywordPlanNetwork": "GOOGLE_SEARCH",
            }, timeout=60)
            if r.status_code != 200:
                print(f"    HTTP {r.status_code}: {r.text[:140]}")
                continue
            for idea in r.json().get("results", []):
                m = idea.get("keywordIdeaMetrics") or {}
                got[idea.get("text", "").strip().lower()] = {
                    "vol": int(m.get("avgMonthlySearches", 0) or 0),
                    "comp": (m.get("competition") or "").title().replace("Unspecified", ""),
                    "comp_idx": m.get("competitionIndex", ""),
                    "bid_lo": round(int(m.get("lowTopOfPageBidMicros", 0) or 0) / 1e6, 2),
                    "bid_hi": round(int(m.get("highTopOfPageBidMicros", 0) or 0) / 1e6, 2),
                }
        except Exception as e:  # noqa: BLE001
            print(f"    call failed ({type(e).__name__}) — continuing")
    return got, f"{calls} call(s)"


def write_planner_csv(path, rows, geo_name):
    """Write the exact tab-delimited shape _parse_planner_csv() reads."""
    today = time.strftime("%Y-%m-%d")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow([f"Keyword Stats {today} (Google Ads API, automated)"])
        w.writerow([f"Generated {today} — geo {geo_name}"])
        w.writerow(HEADER)
        for kw, m in sorted(rows.items()):
            w.writerow([kw, "USD", "", m["vol"], "", "",
                        m["comp"], m["comp_idx"], m["bid_lo"], m["bid_hi"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base = Path(args.data_dir) / "manual-pull"
    pend_dir, out_dir = base / "1-UPLOAD-THESE", base / "2-DROP-RESULTS-HERE"
    if not pend_dir.is_dir():
        print(f"  no {pend_dir} — nothing to resolve.")
        return 0

    geo_id, geo_name = _teamz_geo.resolve(os.getenv("TEAMZ_KW_GEO"))
    if not geo_id:
        # Guessing a geo would silently price Bangladeshi demand at US volumes.
        print(f"  TEAMZ_KW_GEO='{geo_name}' is not recognised — refusing to guess. "
              f"Add it to ID_TO_NAME/NAME_TO_ID/CODE_TO_ID in _teamz_geo.py.")
        return 0

    batches = sorted(glob.glob(str(pend_dir / "batch-*.csv")))
    if not batches:
        print("  no pending batch-*.csv — nothing to resolve.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    calls_left = args.max_calls
    done = 0
    for b in batches:
        stem = Path(b).stem
        target = out_dir / f"result-{stem}-auto.csv"
        if target.exists():
            continue  # already resolved by a previous run
        kws = read_batch(b)
        if not kws:
            continue
        if calls_left <= 0:
            print(f"  call budget spent — {stem} and the rest deferred to the next run.")
            break
        print(f"  {stem}: {len(kws)} keyword(s), geo {geo_name}")
        got, note = fetch(kws, geo_id, calls_left, dry_run=args.dry_run)
        calls_left -= min(calls_left, -(-len(kws) // SEEDS_PER_CALL))
        if args.dry_run:
            print(f"    {note}")
            continue
        # Keep only keywords we asked about; Google's extra ideas are interesting but they are
        # not what this batch was built to price, and mixing them in would quietly inflate the
        # "keywords known" count with terms no page targets.
        want = {k.lower() for k in kws}
        rows = {k: v for k, v in got.items() if k in want and v["vol"] > 0}
        if not rows:
            print(f"    {note} — no volume returned; leaving {stem} pending for a retry.")
            continue
        write_planner_csv(target, rows, geo_name)
        done += 1
        print(f"    {note} -> {len(rows)}/{len(kws)} priced -> {target.name}")

    print(f"  keyword-volume-auto: {done} batch file(s) written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
