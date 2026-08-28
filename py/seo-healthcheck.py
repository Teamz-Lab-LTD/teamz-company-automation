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
# host repo = the property that invoked us (tools, apps, goalkit, learn...), NOT a directory
# guess. Every script in a host repo's scripts/ dir is a SYMLINK into this automation repo, so
# __file__/readlink -f always resolves to the SAME canonical teamz-company-automation/py path
# regardless of which property triggered it — os.path.dirname(AUTO) does not recover the real
# host, it always lands on teamz-projects/ (the grandparent CONTAINING every property). Same
# bug class already found and fixed in sh/lib/config.sh on 2026-07-12 (apps.teamzlab.com); that
# fix was never carried over to this script, so "[FAIL] output freshness" fired every night on
# tools for ~45 days (since 2026-06-11) even when the checked files were minutes-old fresh.
# nightly-build.sh's config.sh always exports TEAMZ_HOST_SITE_ROOT before calling this script —
# trust it. The __file__-based guess survives only as a last-resort fallback for a manual,
# standalone run outside the nightly pipeline where that env var was never set.
HOST = os.environ.get("TEAMZ_HOST_SITE_ROOT") or os.path.dirname(AUTO)
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
#
# History of THIS check, so nobody re-breaks it:
#   Written to catch the failure where Google Trends returned blank for months while every
#   exit code stayed 0. It did that job. But it was written BEFORE Google Ads Keyword Planner
#   access arrived (2026-08-08), and it was never updated afterwards. Result, verified
#   2026-08-18: it fired RED on a night when Planner was ACTIVE with exact volumes, Bing
#   returned 121,917/171,189 and Autocomplete returned 75 — because one free weight-4 signal
#   was rate-limited for that minute. Re-probed by hand the next morning: Trends returned 77.
#   Transient. That RED had fired 5x in one log and 32x historically, which is how a monitor
#   trains its owner to ignore it — the exact failure this whole file exists to prevent.
#
# So the severity rules below are deliberate, and each clause is load-bearing:
#   - Planner (weight 9) is now the PRIMARY volume source and was not checked AT ALL. It is
#     checked first now: Planner dead is a real RED, blank or not.
#   - A weight-4 signal blanking while the weight-9 source works is degraded, not broken.
#   - Transient != chronic. One blank retries once, then counts. A signal that stays blank
#     for CHRONIC_NIGHTS consecutive runs escalates back to RED — that is the original
#     months-of-silence bug, and it must never hide behind WARN.
CHRONIC_NIGHTS = 7
STREAK_FILE = os.path.join(AUTO, "data", "seo-healthcheck-streaks.json")


def _streaks_load():
    try:
        with open(STREAK_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _streaks_save(d):
    try:
        os.makedirs(os.path.dirname(STREAK_FILE), exist_ok=True)
        with open(STREAK_FILE, "w") as f:
            json.dump(d, f, indent=2, sort_keys=True)
    except Exception:
        pass          # a monitor must never fail the run it is monitoring


def _parse_probe(out, probe):
    """Pull the signal row + Planner state out of build-keyword-volume.py output."""
    row = next((l for l in out.splitlines() if probe in l and "/100" in l), "")
    nums, blanks = [], []
    labels = ["Autocomplete", "Trends", "Bing-exact", "Bing-broad", "GSC-impr"]
    if row:
        nums = row.replace(",", "").split()[-5:]
        blanks = [lab for lab, val in zip(labels, nums) if val == "---"]
    # Planner is a separate section, not a column in that row.
    planner_active = bool(re.search(r"Google Ads Keyword Planner:\s*ACTIVE", out))
    exact_rows = 0
    m = re.search(r"EXACT VOLUMES \(Google Ads Keyword Planner\):", out)
    if m:
        exact_rows = len(re.findall(r"^\s+\S.*?\s+[\d,]+\s+(?:LOW|MEDIUM|HIGH)\s",
                                    out[m.end():], re.M))
    return row, nums, blanks, planner_active, exact_rows


def check_keyword_signals():
    """Probe a known-popular term and assert the volume stack still returns data.

    Severity is weight-aware: Planner (w9) dead is RED on its own; a free signal
    (Trends w4 / Autocomplete w3) blanking while Planner works is WARN until it has
    blanked CHRONIC_NIGHTS nights running, at which point it is RED again."""
    if FAST:
        add("keyword-volume signals", WARN, "skipped (--fast)")
        return
    probe = "mortgage calculator"   # always-popular; every signal should fire
    cmd = f'python3 scripts/build-keyword-volume.py "{probe}"'
    rc, out = run(cmd, timeout=120)
    row, nums, blanks, planner_active, exact_rows = _parse_probe(out, probe)

    if not row:
        add("keyword-volume signals", RED, "no data row produced — script failed to output")
        return

    critical_dead = [b for b in blanks if b in ("Trends", "Autocomplete")]

    # Retry ONCE before believing a free-signal blank. Google Trends rate-limits per-minute
    # and returns an empty series rather than an error; one retry separates "rate-limited
    # this minute" from "dead". Only pay the second 120s on an actual failure.
    retried = False
    if critical_dead:
        retried = True
        rc2, out2 = run(cmd, timeout=120)
        row2, nums2, blanks2, pa2, er2 = _parse_probe(out2, probe)
        if row2:
            row, nums, blanks, planner_active, exact_rows = row2, nums2, blanks2, pa2, er2
            critical_dead = [b for b in blanks if b in ("Trends", "Autocomplete")]

    # Track how many consecutive nights each free signal has come back blank.
    streaks = _streaks_load()
    for lab in ("Trends", "Autocomplete"):
        key = f"kwsignal_{lab.lower()}_blank_nights"
        streaks[key] = (streaks.get(key, 0) + 1) if lab in critical_dead else 0
    _streaks_save(streaks)
    chronic = [lab for lab in critical_dead
               if streaks.get(f"kwsignal_{lab.lower()}_blank_nights", 0) >= CHRONIC_NIGHTS]

    rowfmt = f"row=[{' '.join(nums)}]" + (" (after 1 retry)" if retried else "")
    planner = (f"Planner ACTIVE ({exact_rows} exact volumes)" if planner_active and exact_rows
               else "Planner ACTIVE but returned NO exact volumes" if planner_active
               else "Planner NOT ACTIVE")

    # 1. The weight-9 source itself. Nothing below matters if this is gone.
    if not (planner_active and exact_rows):
        add("keyword-volume signals", RED,
            f"PRIMARY volume source down: {planner}. "
            f"Scoring falls back to free signals only. {rowfmt}")
        return

    # 2. A free signal blank for a week+ is the original silent-death bug, not a blip.
    if chronic:
        n = max(streaks.get(f"kwsignal_{c.lower()}_blank_nights", 0) for c in chronic)
        add("keyword-volume signals", RED,
            f"CHRONIC: {', '.join(chronic)} blank {n} nights running for '{probe}' — "
            f"not a rate-limit any more. {planner}. {rowfmt}")
        return

    # 3. Transient free-signal blank while the primary source works. Degraded, not broken.
    if critical_dead:
        n = max(streaks.get(f"kwsignal_{c.lower()}_blank_nights", 0) for c in critical_dead)
        add("keyword-volume signals", WARN,
            f"{', '.join(critical_dead)} blank (night {n}/{CHRONIC_NIGHTS} before this goes RED) "
            f"— free signal rate-limited; {planner} is carrying the score. {rowfmt}")
        return

    if blanks:
        add("keyword-volume signals", WARN,
            f"optional blank: {', '.join(blanks)} (Bing/GSC can be legitimately empty). "
            f"{planner}. {rowfmt}")
        return

    add("keyword-volume signals", GREEN, f"all 5 signals + {planner}. {rowfmt}")


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
    # Paid APIs are OFF by the owner's explicit instruction (2026-08-28): the creds
    # live in CFG/disabled-paid/ and nothing may call them. Report that as a settled
    # decision, not as a missing dependency — a WARN that reads like breakage is how
    # a deliberate choice gets "helpfully" undone months later.
    off = os.path.join(CFG, "disabled-paid", "dataforseo-credentials.json")
    fc_off = os.path.join(CFG, "disabled-paid", "firecrawl-api-key.txt")
    if not os.path.exists(f) and os.path.exists(off):
        add("Paid SEO APIs", GREEN,
            "DataForSEO + Firecrawl OFF by owner — creds parked in disabled-paid/. "
            "GSC, Keyword Planner, Bing, GA4 and AdSense all still run. "
            "See disabled-paid/README.txt to re-enable.")
        return
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
                # Deliberately not urgent, and NOT a nudge to spend. This line used to
                # read "top up for exact Google volume", which was true when written and
                # is now advice to pay for something we already get free: Google Ads
                # Keyword Planner Basic Access was approved 2026-08-08 and its exact
                # volumes feed the composite score directly as of 2026-08-14.
                add("DataForSEO balance", WARN,
                    f"balance ${bal} — empty, and that is fine. Exact Google volume now "
                    f"comes free from Keyword Planner; only top up if a check needs "
                    f"DataForSEO SERP data specifically")
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


def check_revenue_serp():
    """Verify the money layer: RPM steering (revenue_priority) + SERP difficulty
    (serp_difficulty) import + their data is reachable. These rank the nightly by expected
    $/mo, not just traffic — silent breakage = back to traffic-blind enhancement."""
    sys.path.insert(0, HERE)
    try:
        import revenue_priority as rp
        r = rp.expected_dollars("finance/test", "finance", "", 1000, 6)
        if not r or r.get("rpm_mid", 0) <= 0:
            add("revenue steering", WARN, "revenue_priority returned no RPM — check rpm-benchmarks.json");
        else:
            add("revenue steering", GREEN, f"RPM steering live (finance=${r['rpm_mid']})")
    except Exception as e:
        add("revenue steering", WARN, f"revenue_priority failed: {type(e).__name__} — run build-public-rpm-benchmarks.py")
    try:
        import serp_difficulty as sd
        best = None
        for d in DATA_DIRS:
            st = sd.stats(d)
            if st["cached_keywords"]:
                best = st; break
        if best:
            add("SERP difficulty", GREEN, f"{best['cached_keywords']} cached ({best['winnable']} winnable, {best['walled']} walled)")
        else:
            add("SERP difficulty", GREEN, "module OK, cache empty (fills as revival runs)")
    except Exception as e:
        add("SERP difficulty", WARN, f"serp_difficulty failed: {type(e).__name__}")


# ------------------------------------------------- 9. AI crawler reachability
#
# Found 2026-08-03 on hazirakhata.xyz: every OpenAI, Anthropic and Perplexity agent got a hard
# 403 from Cloudflare — including /llms.txt, the file whose entire audience is those agents —
# while Googlebot and browsers got 200. Nobody turned that on. Cloudflare's MANAGED AI-crawler
# block enabled itself on the zone and injected its own "User-agent: GPTBot / Disallow: /" block
# ON TOP of the site's own robots.txt, which allows all of them.
#
# This is the same failure class the whole script exists for: the site is up, uptime is green,
# Googlebot is fine, rankings look normal — and the AI answer engines cannot read a single page.
# No existing check could see it, because every existing check fetches as a browser.
#
# It can also come BACK on: it is a vendor-managed default, flipped on Cloudflare's schedule and
# not ours. So this probes reachability every night rather than trusting a one-time dashboard fix.
AI_CRAWLER_SITES = [s.strip().rstrip("/") for s in (
    os.environ.get("TEAMZ_AI_CRAWLER_SITES")
    or "https://hazirakhata.xyz,https://apps.teamzlab.com,https://teamzlab.com"
).split(",") if s.strip()]

# Agents that SEND READERS: they fetch a page to answer a live question, and the answer can carry
# a link back. Blocking these costs traffic, so blocked = RED.
AI_FETCH_AGENTS = {
    "OAI-SearchBot": "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
    "ChatGPT-User": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot",
    "PerplexityBot": "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    "Claude-User": "Mozilla/5.0 (compatible; Claude-User/1.0; +Claude-User@anthropic.com)",
}
# Training-corpus crawlers. Blocking these is a legitimate business choice, so blocked = WARN, not
# RED — the check reports the state without deciding it for you.
AI_TRAIN_AGENTS = {
    "GPTBot": "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)",
    "ClaudeBot": "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
}
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _http_probe(url, ua, timeout=15, read_bytes=0):
    """(status_code, body) for one URL under one User-Agent. status 0 = transport failure.

    HTTPError is caught rather than raised because a 403 IS the answer here — an edge block is
    reported as an HTTP error by urllib, and treating it as an exception would lose the code."""
    import urllib.request, urllib.error
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, (r.read(read_bytes).decode("utf-8", "replace") if read_bytes else "")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, type(e).__name__


def check_ai_crawlers():
    """Every AI answer engine must be able to fetch the site, and robots.txt must be ours."""
    if FAST:
        add("AI crawler reach", GREEN, "skipped (--fast)")
        return
    for site in AI_CRAWLER_SITES:
        host = site.split("//", 1)[-1]
        # Baseline first. Without it a plain outage reads as a bot-block and fires a RED that
        # sends you hunting through Cloudflare bot settings for a problem that is not there.
        base, _ = _http_probe(site + "/", BROWSER_UA)
        if base != 200:
            add(f"AI crawler reach {host}", WARN, f"site itself returned {base} as a browser — not a bot-block signal")
            continue

        blocked_fetch = [n for n, ua in AI_FETCH_AGENTS.items() if _http_probe(site + "/", ua)[0] != 200]
        blocked_train = [n for n, ua in AI_TRAIN_AGENTS.items() if _http_probe(site + "/", ua)[0] != 200]

        # A 403 on llms.txt is the loudest possible signal: that file exists for nothing but these
        # agents. 404 is not a block — plenty of properties simply do not publish one.
        llms_code, _ = _http_probe(site + "/llms.txt", AI_FETCH_AGENTS["OAI-SearchBot"])
        llms_blocked = llms_code not in (200, 404)

        # Cloudflare stamps its own directives over the origin's file. Ours ships from public/ and
        # allows these agents, so this marker means the live policy is not the one in the repo.
        _, robots = _http_probe(site + "/robots.txt", BROWSER_UA, read_bytes=20000)
        managed_robots = "Cloudflare Managed" in robots

        if blocked_fetch:
            add(f"AI crawler reach {host}", RED,
                f"BLOCKED: {', '.join(blocked_fetch)}"
                + (f" + /llms.txt {llms_code}" if llms_blocked else "")
                + " — Cloudflare AI-crawler block; turn it off on the zone")
        elif managed_robots:
            add(f"AI crawler reach {host}", RED,
                "pages reachable but robots.txt is Cloudflare-managed and disallows AI agents — "
                "well-behaved crawlers will obey it and stay out; turn off managed robots.txt")
        elif llms_blocked:
            add(f"AI crawler reach {host}", RED, f"/llms.txt returned {llms_code} to OAI-SearchBot")
        elif blocked_train:
            add(f"AI crawler reach {host}", WARN,
                f"fetch agents OK; training crawlers blocked: {', '.join(blocked_train)} (fine if deliberate)")
        else:
            add(f"AI crawler reach {host}", GREEN,
                f"all {len(AI_FETCH_AGENTS) + len(AI_TRAIN_AGENTS)} AI agents get 200, robots.txt is ours")


CHECKS = [check_compile_all, check_keyword_signals, check_gsc_auth,
          check_bing_key, check_dataforseo, check_output_freshness,
          check_manual_google_volume, check_revenue_serp, check_ai_crawlers]


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
