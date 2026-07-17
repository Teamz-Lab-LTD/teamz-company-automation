#!/usr/bin/env python3
"""
Keyword-candidate accumulator — the "store now, ask rarely" half of the manual-volume loop.

THE WORKFLOW ALREADY PROVEN ON TOOLS
------------------------------------
  build-keyword-batches.py  -> paste-ready CSVs from PAGE INVENTORY (sitemap/tools.json)
  keyword_volume_manual.py  -> reads the CSVs Google hands back
  ...15 batches pulled by hand, no API token, exact volume. It works.

WHAT THIS ADDS (the owner's ask, 2026-07-17)
--------------------------------------------
Two gaps in that loop, for a solo operator who drives Uber and cannot be asked to pull
volume every few days:

  1. It batched page inventory only. The richest candidates are the queries GOOGLE ALREADY
     SHOWS US FOR — real demand, measured, sitting in Search Console — that we have never
     checked a volume for. Those never entered the loop.
  2. It had no cadence. Preparing a batch every night would mean nagging the owner every
     night. He was explicit: accumulate, and only ask "when you feel we need to".

So this script:
  - HARVEST (cheap, safe to run nightly): pull GSC queries with real impressions, append any
    we have never seen to data/keyword-candidates.json with first_seen / times_seen / source.
    Dedupes against volume ALREADY pulled, so a keyword we know is never re-queued.
  - PREPARE (--prepare, gated): only when there are >= MIN_NEW unpulled candidates AND it has
    been >= MIN_DAYS since the last batch, write a paste-ready CSV into the property's
    manual-pull/1-UPLOAD-THESE/ (same folder keyword_volume_manual already reads back).
    Otherwise it prints why it is holding and writes nothing.

The owner pulls the batch by hand when told, drops results in 2-DROP-RESULTS-HERE/, and the
existing reader merges them. This file only decides WHAT to ask for and WHEN.

Usage:
  python3 build-keyword-candidates.py                 # HARVEST into the store (nightly-safe)
  python3 build-keyword-candidates.py --prepare       # emit a batch IF the gate allows
  python3 build-keyword-candidates.py --prepare --force   # emit now, ignore the cadence gate
  python3 build-keyword-candidates.py --status        # show store size + gate state, write nothing
"""
import csv
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# Reuse the proven pieces rather than reimplement them.
import importlib.util
_spec = importlib.util.spec_from_file_location("_bcq", HERE / "build-content-queue.py")
_bcq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bcq)          # only defines functions; main() is __main__-gated
from keyword_volume_manual import load_manual_volume, _norm  # noqa: E402

# Cadence + size gates. Env-overridable so the owner can loosen/tighten without a code change.
MIN_NEW = int(os.getenv("TEAMZ_KW_MIN_NEW", "150"))       # don't ask for a tiny batch
MIN_DAYS = int(os.getenv("TEAMZ_KW_MIN_DAYS", "21"))      # ...and not more than ~monthly
BATCH_MAX = int(os.getenv("TEAMZ_KW_BATCH_MAX", "700"))   # Planner upload cap
MAX_WORDS = 10                                            # Planner rejects >10-word phrases


def _today():
    # Date.now()-free: derive from a passed date or the filesystem clock via datetime.
    return date.today().isoformat()


def store_path(host):
    return host / "data" / "keyword-candidates.json"


def load_store(host):
    p = store_path(host)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"candidates": {}, "last_prepared": None, "batches_prepared": 0}


def save_store(host, store):
    p = store_path(host)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(store, indent=2, ensure_ascii=False))


def harvest(cfg, host, site_url, store):
    """Append GSC queries with real impressions that we have not seen and do not already have
    volume for. Returns the number newly added."""
    token = _bcq.gsc_token(cfg)
    prop = cfg["site_property"]
    rows = _bcq.gsc_query(prop, token, ["query"], days=90, row_limit=2000)

    have_volume = load_manual_volume(host / "data")     # {norm kw: {...}} already pulled
    cands = store["candidates"]
    today = _today()
    added = 0
    for r in rows:
        q = _norm(r["keys"][0])
        if not q or len(q.split()) > MAX_WORDS:
            continue
        if _bcq.looks_like_junk(q):
            continue
        if q in have_volume:
            continue                                    # already know its volume — never re-ask
        if q in cands:
            cands[q]["times_seen"] += 1
            cands[q]["impressions"] = int(r["impressions"])
            continue
        cands[q] = {
            "first_seen": today,
            "times_seen": 1,
            "impressions": int(r["impressions"]),
            "source": "gsc-query",
        }
        added += 1
    return added


def unpulled(host, store):
    """Candidates we still owe a volume pull for (not yet in any results file)."""
    have_volume = load_manual_volume(host / "data")
    return [q for q in store["candidates"] if q not in have_volume]


def days_since(iso):
    if not iso:
        return 10**6
    try:
        return (datetime.now() - datetime.fromisoformat(iso)).days
    except Exception:
        return 10**6


def gate_state(host, store):
    pend = unpulled(host, store)
    since = days_since(store.get("last_prepared"))
    ready = len(pend) >= MIN_NEW and since >= MIN_DAYS
    return pend, since, ready


def ensure_folders(mp):
    (mp / "1-UPLOAD-THESE").mkdir(parents=True, exist_ok=True)
    (mp / "2-DROP-RESULTS-HERE").mkdir(parents=True, exist_ok=True)
    readme = mp / "README.txt"
    if not readme.exists():
        readme.write_text(
            "KEYWORD VOLUME — manual pull (free, no API token)\n"
            "=================================================\n\n"
            "1-UPLOAD-THESE/       <- CSVs Claude gives you. Upload to Google Keyword Planner,\n"
            "                         one at a time (Get search volume -> + -> Upload a file).\n"
            "2-DROP-RESULTS-HERE/  <- the CSV Google gives back. Save it here.\n\n"
            "THE LOOP:\n"
            "  1. Keyword Planner -> Get search volume and forecasts -> + -> Upload a file\n"
            "  2. Pick a batch-NN.csv from 1-UPLOAD-THESE/ -> Submit\n"
            "  3. Saved keywords tab -> Download icon -> .csv\n"
            "  4. Move that download into 2-DROP-RESULTS-HERE/\n"
            "  5. Tell Claude \"done\" -> it merges the real volume into the engine.\n"
        )


def prepare(host, store, force=False):
    pend, since, ready = gate_state(host, store)
    if not (ready or force):
        why = []
        if len(pend) < MIN_NEW:
            why.append(f"only {len(pend)} new candidates (need {MIN_NEW})")
        if since < MIN_DAYS:
            why.append(f"last batch {since}d ago (wait {MIN_DAYS - since}d more)")
        print(f"  HOLDING — {'; '.join(why)}. Nothing written.")
        print("  (run with --force to override the cadence gate.)")
        return None

    # Richest first: most impressions = most proven demand.
    ranked = sorted(pend, key=lambda q: -store["candidates"][q].get("impressions", 0))
    batch = ranked[:BATCH_MAX]

    mp = host / "data" / "manual-pull"
    ensure_folders(mp)
    n = store.get("batches_prepared", 0) + 1
    out = mp / "1-UPLOAD-THESE" / f"batch-cand-{n:02d}.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Keyword"])
        for q in batch:
            w.writerow([q])

    store["last_prepared"] = _today()
    store["batches_prepared"] = n
    print(f"  PREPARED {out.relative_to(host)}  ({len(batch)} keywords)")
    print(f"  {len(pend) - len(batch)} candidates remain for the next batch.")
    print("  Owner: upload it in Keyword Planner, drop the result in 2-DROP-RESULTS-HERE/,")
    print("         then tell Claude \"done\".")
    return out


def main():
    argv = sys.argv[1:]
    cfg = _bcq.load_runtime(str(HERE / "build-content-queue.py"))
    host = Path(cfg["host_site_root"])
    site_url = cfg.get("site_url") or ""
    store = load_store(host)

    print(f"  keyword candidates — {cfg['site_property']}")

    if "--status" in argv:
        pend, since, ready = gate_state(host, store)
        print(f"  stored: {len(store['candidates'])}   unpulled: {len(pend)}   "
              f"last batch: {('never' if since>=10**6 else str(since)+'d ago')}   gate: {'READY' if ready else 'holding'} "
              f"(need >={MIN_NEW} new AND >={MIN_DAYS}d)")
        return

    added = harvest(cfg, host, site_url, store)
    save_store(host, store)
    pend, since, ready = gate_state(host, store)
    print(f"  harvested +{added} new   (store {len(store['candidates'])}, unpulled {len(pend)})")

    if "--prepare" in argv:
        prepare(host, store, force="--force" in argv)
        save_store(host, store)
    else:
        since_txt = "never" if since >= 10**6 else f"{since}d"
        if ready:
            print("  gate: READY — run --prepare to emit a batch")
        else:
            print(f"  gate: holding (need >={MIN_NEW} new AND >={MIN_DAYS}d; "
                  f"have {len(pend)} new, last {since_txt})")


if __name__ == "__main__":
    main()
