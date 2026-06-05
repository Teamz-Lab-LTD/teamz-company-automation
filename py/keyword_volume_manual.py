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
    hdr = next((r for r in rows[:5] if "Keyword" in r and "Avg. monthly searches" in r), None)
    if not hdr:
        return {}
    ki, vi = hdr.index("Keyword"), hdr.index("Avg. monthly searches")
    ci = hdr.index("Competition") if "Competition" in hdr else -1
    out = {}
    for r in rows[rows.index(hdr) + 1:]:
        if len(r) <= vi or not r[ki].strip():
            continue
        cell = r[vi].strip()
        if not cell:
            vol = None              # blank = Planner returned no number = UNKNOWN, NOT zero demand
        else:
            try:
                vol = float(cell)
            except ValueError:
                vol = None          # unparseable = unknown; never silently assume zero
        out[_norm(r[ki])] = {"vol": vol, "comp": r[ci].strip() if ci >= 0 and len(r) > ci else ""}
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
