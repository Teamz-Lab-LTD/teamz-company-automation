#!/usr/bin/env python3
"""
SEO toolchain health-check — deterministic, no LLM.

Catches the failure class that broke Google Trends silently for months: a script
that RUNS, EXITS 0, and WRITES a file, but where one data SOURCE inside returns
blank. Exit codes can't see that — so this probes DATA QUALITY, not just "did it run".

Run:  python3 py/seo-healthcheck.py            # full check
      python3 py/seo-healthcheck.py --fast      # skip live network probes
      python3 py/seo-healthcheck.py --json       # machine-readable

Exit code: 0 if all GREEN/WARN, 1 if any RED (so the nightly can gate on it).

Add a new probe by appending to CHECKS. Each check returns (status, detail) where
status is "GREEN" (works), "WARN" (degraded/optional), or "RED" (broken).
"""
import os, sys, json, glob, time, subprocess, re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))          # .../teamz-company-automation/py
AUTO = os.path.dirname(HERE)                                # .../teamz-company-automation
# host repo = parent of the submodule (the consumer); data/ + config live there
HOST = os.path.dirname(AUTO)
# Outputs are split: _teamz_config-based scripts write to TEAMZ_DATA_DIR or
# <submodule>/data; others write to <host>/data. Check BOTH or we false-alarm.
DATA_DIRS = [os.path.join(HOST, "data"),
             os.environ.get("TEAMZ_DATA_DIR") or os.path.join(AUTO, "data")]
CFG = os.path.expanduser("~/.config/teamzlab")
FAST = "--fast" in sys.argv
AS_JSON = "--json" in sys.argv

GREEN, WARN, RED = "GREEN", "WARN", "RED"
results = []   # (name, status, detail)


def add(name, status, detail):
    results.append((name, status, detail))


def run(cmd, timeout=60):
    """Run a shell command, return (rc, stdout+stderr)."""
    try:
        p = subprocess.run(cmd, shell=True, cwd=HOST, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:
        return 1, f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------- 1. compile-all
def check_compile_all():
    """Every .py must parse; every .sh must pass bash -n. Catches breakage."""
    bad = []
    for f in glob.glob(os.path.join(HERE, "*.py")):
        rc, out = run(f'python3 -m py_compile "{f}"', timeout=30)
        if rc != 0:
            bad.append(os.path.basename(f) + ": " + out.strip().splitlines()[-1][:80])
    for f in glob.glob(os.path.join(HERE, "..", "sh", "*.sh")) + glob.glob(os.path.join(HOST, "scripts", "*.sh")):
        rc, out = run(f'bash -n "{f}"', timeout=15)
        if rc != 0:
            bad.append(os.path.basename(f) + ": syntax")
    if bad:
        add("compile-all (py+sh parse)", RED, f"{len(bad)} broken: " + "; ".join(bad[:4]))
    else:
        add("compile-all (py+sh parse)", GREEN, "all scripts parse")


# ---------------------------------------------------------------- 2. keyword signals (the Trends-class catcher)
def check_keyword_signals():
    """Run build-keyword-volume on a known-popular term; assert EACH signal
    returns data. A blank column = that source is silently dead (the Trends bug)."""
    if FAST:
        add("keyword-volume signals", WARN, "skipped (--fast)")
        return
    probe = "mortgage calculator"   # always-popular; every signal should fire
    rc, out = run(f'python3 scripts/build-keyword-volume.py "{probe}"', timeout=90)
    # find the data row
    row = next((l for l in out.splitlines() if probe in l and "/100" in l), "")
    if not row:
        add("keyword-volume signals", RED, "no data row produced — script failed to output")
        return
    # columns: Keyword .. Score Tier AC Trends Bing/mo BingBrd Impr
    cols = row.split()
    blanks = []
    # detect each signal by scanning for the known markers
    ac = re.search(r"\b(\d{1,3})\b(?=\s+(?:\d{1,3}|---))", row)
    # simpler: split tail tokens
    tail = row.replace(",", "").split()
    # Find 'HIGH/MEDIUM/LOW/VERY' tier index, signals follow it
    nums = tail[-5:]   # AC Trends Bing BingBrd Impr (--- where blank)
    labels = ["Autocomplete", "Trends", "Bing-exact", "Bing-broad", "GSC-impr"]
    for lab, val in zip(labels, nums):
        if val == "---":
            blanks.append(lab)
    # Trends + Autocomplete are the free Google signals we most rely on
    critical_dead = [b for b in blanks if b in ("Trends", "Autocomplete")]
    if critical_dead:
        add("keyword-volume signals", RED,
            f"DEAD signal(s): {', '.join(critical_dead)} returned '---' for '{probe}'. row=[{' '.join(nums)}]")
    elif blanks:
        add("keyword-volume signals", WARN,
            f"optional blank: {', '.join(blanks)} (Bing/GSC can be legitimately empty). row=[{' '.join(nums)}]")
    else:
        add("keyword-volume signals", GREEN, f"all 5 signals returned data. row=[{' '.join(nums)}]")


# ---------------------------------------------------------------- 3. GSC auth
def check_gsc_auth():
    tok = os.path.join(CFG, "search-console-token.json")
    if not os.path.exists(tok):
        add("GSC auth (search console)", RED, "token file missing")
        return
    if FAST:
        add("GSC auth (search console)", WARN, "token present; live refresh skipped (--fast)")
        return
    try:
        import requests
        td = json.load(open(tok))
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": td["client_id"], "client_secret": td["client_secret"],
            "refresh_token": td["refresh_token"], "grant_type": "refresh_token"}, timeout=20)
        if r.status_code == 200 and r.json().get("access_token"):
            add("GSC auth (search console)", GREEN, "token refresh OK")
        else:
            add("GSC auth (search console)", RED, f"refresh failed HTTP {r.status_code} — re-run build-search-console-auth.py")
    except Exception as e:
        add("GSC auth (search console)", RED, f"{type(e).__name__}: {str(e)[:60]}")


# ---------------------------------------------------------------- 4. Bing key
def check_bing_key():
    f = os.path.join(CFG, "bing-webmaster-api-key.txt")
    if os.path.exists(f) and os.path.getsize(f) > 10:
        add("Bing Webmaster key", GREEN, "key present")
    else:
        add("Bing Webmaster key", WARN, "missing/empty — Bing volume + submit will be blank")


# ---------------------------------------------------------------- 5. DataForSEO balance
def check_dataforseo():
    f = os.path.join(CFG, "dataforseo-credentials.json")
    if not os.path.exists(f):
        add("DataForSEO balance", WARN, "no creds — exact Google volume unavailable (free sources still work)")
        return
    if FAST:
        add("DataForSEO balance", WARN, "creds present; balance check skipped (--fast)")
        return
    try:
        import requests, base64
        c = json.load(open(f))
        login = c.get("login") or c.get("username") or ""
        pw = c.get("password") or ""
        auth = base64.b64encode(f"{login}:{pw}".encode()).decode()
        r = requests.get("https://api.dataforseo.com/v3/appendix/user_data",
                         headers={"Authorization": f"Basic {auth}"}, timeout=20)
        if r.status_code == 200:
            bal = r.json().get("tasks", [{}])[0].get("result", [{}])[0].get("money", {}).get("balance")
            if bal and bal > 0:
                add("DataForSEO balance", GREEN, f"${bal:.2f} available")
            else:
                add("DataForSEO balance", WARN, f"balance ${bal} — top up for exact Google volume (free sources cover meanwhile)")
        else:
            add("DataForSEO balance", WARN, f"HTTP {r.status_code} (was 402=out of credits)")
    except Exception as e:
        add("DataForSEO balance", WARN, f"{type(e).__name__}: {str(e)[:50]}")


# ---------------------------------------------------------------- 6. output freshness
def check_output_freshness():
    """Data outputs that should refresh on a cadence. Stale/empty = the producing
    script likely stopped working silently."""
    checks = [
        ("bing-data-latest.json", 14),
        ("rising-tools-latest.json", 7),
        ("gsc-anomalies-latest.json", 7),
        ("enhance-queue.json", 3),
    ]
    def find(fn):
        best = None
        for d in DATA_DIRS:
            p = os.path.join(d, fn)
            if os.path.exists(p) and os.path.getsize(p) >= 5:
                if best is None or os.path.getmtime(p) > os.path.getmtime(best):
                    best = p
        return best
    stale, missing = [], []
    for fn, max_age in checks:
        p = find(fn)
        if not p:
            missing.append(fn); continue
        age_days = (time.time() - os.path.getmtime(p)) / 86400
        if age_days > max_age:
            stale.append(f"{fn} {age_days:.0f}d>{max_age}d")
    if missing:
        add("output freshness", RED, f"missing/empty: {', '.join(missing)}" + (f"; stale: {', '.join(stale)}" if stale else ""))
    elif stale:
        add("output freshness", WARN, f"stale (producer may be idle): {', '.join(stale)}")
    else:
        add("output freshness", GREEN, "key data outputs present + fresh")


def check_manual_google_volume():
    """Recommend a free Keyword Planner pull when this project has SEO pages but no real
    Google volume data (or it's gone stale). Exact volume is the authoritative demand
    source — without it every enhance/revive/prune decision is a guess. This is the
    cross-consumer nudge: any project running SEO orchestration gets told to pull batches."""
    # does this consumer even have a public SEO surface worth pulling for?
    has_surface = (os.path.exists(os.path.join(HOST, "sitemap.xml"))
                   or os.path.exists(os.path.join(HOST, "tools.json")))
    if not has_surface:
        add("google volume", GREEN, "no public SEO surface here — pull not needed"); return
    try:
        sys.path.insert(0, HERE)
        import keyword_volume_manual as kvm
    except Exception as e:
        add("google volume", WARN, f"loader import failed: {e}"); return
    cov = None
    for d in DATA_DIRS:
        mv = kvm.load_manual_volume(d)
        if mv:
            cov = kvm.coverage(mv); base = os.path.join(d, "manual-pull", "2-DROP-RESULTS-HERE"); break
    if not cov:
        add("google volume", WARN,
            "MISSING — no Keyword Planner data. STRONGLY RECOMMENDED: run "
            "`python3 teamz-company-automation/py/build-keyword-batches.py` then pull each "
            "batch from Keyword Planner (US, free, no API token). Decisions are guesses until then.")
        return
    # present — is it stale? (volume is a 12-mo average; refresh ~1-2x/yr)
    newest = 0
    import glob as _g
    for f in _g.glob(os.path.join(base, "*.csv")):
        newest = max(newest, os.path.getmtime(f))
    age_days = (time.time() - newest) / 86400 if newest else 9999
    msg = f"{cov['with_volume']}/{cov['total']} keywords with real volume"
    if age_days > 270:
        add("google volume", WARN, f"STALE ({age_days:.0f}d > 270d) — re-pull recommended. {msg}")
    else:
        add("google volume", GREEN, f"{msg} ({age_days:.0f}d old)")


CHECKS = [check_compile_all, check_keyword_signals, check_gsc_auth,
          check_bing_key, check_dataforseo, check_output_freshness,
          check_manual_google_volume]


def main():
    for c in CHECKS:
        try:
            c()
        except Exception as e:
            add(c.__name__, RED, f"check crashed: {type(e).__name__}: {str(e)[:60]}")

    if AS_JSON:
        print(json.dumps([{"name": n, "status": s, "detail": d} for n, s, d in results], indent=2))
    else:
        icon = {GREEN: "OK  ", WARN: "WARN", RED: "FAIL"}
        print("\n" + "=" * 72)
        print(f"  SEO TOOLCHAIN HEALTH-CHECK  ({datetime.now():%Y-%m-%d %H:%M})")
        print("=" * 72)
        for n, s, d in results:
            print(f"  [{icon[s]}] {n:<32} {d}")
        reds = sum(1 for _, s, _ in results if s == RED)
        warns = sum(1 for _, s, _ in results if s == WARN)
        print("-" * 72)
        print(f"  {len(results)} checks — {reds} FAIL, {warns} WARN, {len(results)-reds-warns} OK")
        if reds:
            print("  >> RED means a data source is silently broken. Fix before trusting SEO output.")
        print("=" * 72)
    sys.exit(1 if any(s == RED for _, s, _ in results) else 0)


if __name__ == "__main__":
    main()
