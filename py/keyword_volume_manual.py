"""
Shared: manually-exported Google Ads Keyword Planner volume — for ANY consumer project.

Free, exact Google search volume + competition, no API developer token. The user exports
"historical metrics" CSVs from Keyword Planner (one country, US default) and drops them in
  <project>/data/manual-pull/2-DROP-RESULTS-HERE/
Every consumer (tools, landing-pages, learning, debugger blog) reads them the same way.

This is the AUTHORITATIVE demand source. The free signals (autocomplete/Trends/Bing/GSC)
only estimate; Planner gives the real number. Use it to gate enhance/revive/prune
decisions and as a LEADING INDICATOR feeding ASO keyword research (never the sole ASO
decider — ASO still needs its own competitor-winnability check).

  from keyword_volume_manual import load_manual_volume, manual_lookup, coverage
  mv = load_manual_volume(DATA_DIR)          # {normalized keyword: {'vol': float, 'comp': str}}
  hit = manual_lookup(mv, "paycheck calculator")   # exact, else core-topic fallback
"""
import os, csv, glob, re

# default tool/intent words used to fall back from a full phrase to its core topic
DEFAULT_TOOL_TYPES = {
    'rewriter', 'generator', 'calculator', 'checker', 'maker', 'tracker', 'planner',
    'converter', 'estimator', 'analyzer', 'simulator', 'tool', 'template', 'builder',
    'predictor', 'counter', 'finder', 'scanner', 'validator', 'formatter', 'editor',
    'test', 'split', 'merge',
}
DEFAULT_INTENT_SUFFIXES = {
    'generator', 'calculator', 'template', 'checker', 'tool', 'maker', 'examples',
    'free', 'online',
}


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _parse_volume(cell):
    """Planner's 'Avg. monthly searches' cell -> (value, bucketed).

    An account with no ad spend does NOT get exact numbers — Google returns log-scale BUCKETS
    like '10K - 100K' (and the dash may be an en-dash). float() on that raises, and the old code
    turned every such row into vol=None, i.e. a whole pull silently reporting "no demand data"
    while looking like it worked. Buckets are perfectly usable for RANKING, which is all the radar
    does with volume, so parse them instead of discarding them.

    The bucket's central estimate is the GEOMETRIC mean, not the arithmetic one: the buckets are
    log-scale, so the midpoint of 10K-100K is 31.6K, not 55K. Arithmetic would systematically
    inflate every bucketed keyword by ~1.7x and outrank exactly-measured ones.

    Returns (None, False) for blank/unparseable — never a guessed zero.
    """
    s = (cell or "").strip().replace(",", "")
    if not s:
        return None, False

    def one(tok):
        tok = tok.strip().upper().replace("+", "")
        m = re.match(r"^([\d.]+)\s*([KM]?)$", tok)
        if not m:
            return None
        v = float(m.group(1))
        return v * {"": 1, "K": 1_000, "M": 1_000_000}[m.group(2)]

    # en-dash, em-dash, hyphen, or the word "to"
    parts = [p for p in re.split(r"\s*[–—-]\s*|\s+to\s+", s) if p]
    if len(parts) == 2:
        lo, hi = one(parts[0]), one(parts[1])
        if lo is not None and hi is not None and lo > 0 and hi > 0:
            return round((lo * hi) ** 0.5), True      # geometric mean of a log-scale bucket
        return None, False
    v = one(s)
    return (v, False) if v is not None else (None, False)


def _parse_planner_csv(path):
    """One Planner export -> {normalized keyword: {'vol': float, 'comp': str}}.
    Tab-delimited; exports may be UTF-8 or UTF-16 (Excel). Header is the first row with
    'Keyword' + 'Avg. monthly searches' (rows above are the title + date range)."""
    raw = None
    for enc in ("utf-8", "utf-16"):
        try:
            txt = open(path, encoding=enc).read()
            if "Avg. monthly searches" in txt:
                raw = txt
                break
        except Exception:
            continue
    if raw is None:
        return {}
    rows = list(csv.reader(raw.splitlines(), delimiter="\t"))
    # "Get search volume" exports label the column exactly "Keyword"; "Discover new keywords"
    # exports label it "Keyword (by relevance)". Matching only the exact name made a discovery
    # export parse to {} — a silently wasted manual pull. Accept any Keyword* column.
    def _is_kw(c):
        return c.strip().lower().startswith("keyword")

    hdr = next((r for r in rows[:5]
                if "Avg. monthly searches" in r and any(_is_kw(c) for c in r)), None)
    if not hdr:
        return {}
    ki = next(i for i, c in enumerate(hdr) if _is_kw(c))
    vi = hdr.index("Avg. monthly searches")
    ci = hdr.index("Competition") if "Competition" in hdr else -1
    # Trend + bid columns ship in every Planner export and were being thrown away. They are the
    # durability signals: YoY change says whether demand is growing or dying (a course built on a
    # -100% keyword is dead on arrival), and top-of-page bid is Google's own per-keyword price —
    # a sharper revenue proxy than any niche-level benchmark table. All optional: absent column or
    # blank cell = None, never a guessed zero.
    yi = hdr.index("YoY change") if "YoY change" in hdr else -1
    # Prefer the high-range bid, but accept the low-range column — which is what the UI shows by
    # default, so an export made without touching Columns has only that one.
    bi = next((hdr.index(c) for c in ("Top of page bid (high range)", "Top of page bid (low range)")
               if c in hdr), -1)

    def _pct(cell):
        # "+900%" -> 9.0, "-100%" -> -1.0, "0%" -> 0.0, "∞"/blank/garbage -> None
        s = (cell or "").strip().replace("%", "").replace(",", "")
        if not s:
            return None
        try:
            return float(s) / 100.0
        except ValueError:
            return None

    def _usd(cell):
        s = (cell or "").strip().replace(",", "")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    out = {}
    for r in rows[rows.index(hdr) + 1:]:
        if len(r) <= vi or not r[ki].strip():
            continue
        vol, bucketed = _parse_volume(r[vi])
        out[_norm(r[ki])] = {
            "vol": vol,
            "bucketed": bucketed,   # True = derived from a range, precise to ~an order of magnitude
            "comp": r[ci].strip() if ci >= 0 and len(r) > ci else "",
            # A bucketed account reports change as movement BETWEEN buckets, so a one-step shift
            # reads as ±90% regardless of the real delta. Feeding that to the radar's trend
            # multiplier would swing scores on an artifact, so drop trend when volume is bucketed.
            "yoy": (_pct(r[yi]) if (yi >= 0 and len(r) > yi and not bucketed) else None),
            "bid_hi": _usd(r[bi]) if bi >= 0 and len(r) > bi else None,
        }
    return out


def manual_dir(data_dir):
    return os.path.join(data_dir, "manual-pull")


def load_manual_volume(data_dir):
    """Merge EVERY Planner export under <data_dir>/manual-pull/ into one map. Reads
    2-DROP-RESULTS-HERE/*.csv (and top-level *.csv for back-compat). Higher volume wins on
    a keyword collision (a fuller later pull supersedes an empty earlier one). Input batch
    files in 1-UPLOAD-THESE/ have no volume column and are skipped by the parser."""
    base = manual_dir(data_dir)
    paths = (glob.glob(os.path.join(base, "2-DROP-RESULTS-HERE", "*.csv"))
             + glob.glob(os.path.join(base, "*.csv")))
    merged = {}
    for p in sorted(paths):
        for k, v in _parse_planner_csv(p).items():
            if k not in merged:
                merged[k] = v
                continue
            nv, ov = v["vol"], merged[k]["vol"]
            # higher KNOWN volume wins; a known value supersedes UNKNOWN(None); None never overwrites
            if nv is not None and (ov is None or nv > ov):
                merged[k] = v
    # Loader-level silent-killer guard: CSVs present but nothing parsed = a column rename
    # ("Avg. monthly searches"), delimiter, or encoding change that turned the AUTHORITATIVE
    # demand source into {} without a peep — the exact shape that hid 11k keywords for months.
    # Warn LOUD so a direct caller (dead-revival, money-tracker) can't mistake it for "no data".
    if paths and not merged:
        import sys as _sys
        _sys.stderr.write(
            f"WARNING: {len(paths)} Planner CSV(s) under {base} but 0 keywords parsed. "
            f"Manual volume is now SILENTLY DISABLED — check the export column names/encoding "
            f"('Keyword' + 'Avg. monthly searches', tab-delimited).\n")
    return merged


def manual_lookup(mv, kw, tool_types=DEFAULT_TOOL_TYPES, intent_suffixes=DEFAULT_INTENT_SUFFIXES,
                  core_fallback=True):
    """Exact match, else (when core_fallback) strip a trailing tool/intent word and match the
    core topic. Pass core_fallback=False to FORBID the head-noun fallback — a specific tool
    phrase ('1031 exchange calculator', 500/mo) must never inherit its bare head term's
    ('1031 exchange', 50k/mo) volume and get mis-ranked into an unwinnable head queue."""
    k = _norm(kw)
    if k in mv:
        return mv[k]
    if not core_fallback:
        return None
    parts = k.split()
    if len(parts) > 1 and parts[-1] in (set(tool_types) | set(intent_suffixes)):
        core = " ".join(parts[:-1])
        if core in mv:
            return mv[core]
    return None


def coverage(mv):
    """Quick stats for health-checks: how many keywords, how many with real volume."""
    total = len(mv)
    withvol = sum(1 for v in mv.values() if (v.get("vol") or 0) > 0)
    return {"total": total, "with_volume": withvol}
