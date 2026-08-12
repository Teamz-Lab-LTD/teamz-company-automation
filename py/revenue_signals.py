"""
Shared: measured per-page revenue for the nightly page-picker.

WHY THIS EXISTS. build-enhance-queue.py sorts candidates by signal_score * rev_weight, so
rev_weight decides which page the nightly spends its effort on. It had exactly one input:
revenue_priority -> data/rpm-benchmarks.json, whose own `sources` field reads "Reddit
r/Adsense + r/juststart community averages" plus a few 2024/2025 blog posts — 27 niche
averages, last_updated 2026-04-13. Community hearsay was steering the money on the property
that pays the bills.

Meanwhile GA4 already knew what every page ACTUALLY earned (totalAdRevenue). It was pulled
by build-growth-digest.py for reporting and never reached the queue.

Measured against reality on tool.teamzlab.com, 2026-08-08, 105 pages with enough sessions to
compare guess vs truth:

  median |benchmark - measured|                              $3.28 RPM
  pages the benchmark put on the WRONG side of 1.0x weight   34/105 (32%)

  overrated : /amazon/sales-estimator/    guess $22.00  ->  real $4.99   (weight 2.20 -> 0.50)
  underrated: /football/...-in-germany/   guess  $2.50  ->  real $71.71  (weight 0.50 -> 3.00)

LAYERING, NOT REPLACEMENT:

    measured RPM (GA4, this file)  ->  rpm-benchmarks niche average (unchanged fallback)

Nothing is removed. measured_rpm() returns None (never {}, never 0) when GA4 cannot be
reached, and omits any page below the session floor, so every unanswered page falls through
to exactly today's behaviour. This is the UNION rule: the last time a picker input was
swapped rather than layered, it hid 98.9% of revenue behind a hardcoded niche list.

--------------------------------------------------------------------------------------
WHY THERE IS NO GOOGLE ADS CPC LAYER HERE  (negative result — do not re-add on a hunch)

The plan was to use Google Ads advertiser CPC as a second layer, on the theory that AdSense
pays a share of advertiser bids, so CPC is upstream of RPM — and unlike measured revenue it
exists for zero-traffic pages, ~81% of the site. It was built, then tested against the
measured RPMs above before being wired in. It does not work:

  Spearman rank correlation, CPC vs measured RPM   -0.250   (n=26)
  ... excluding country-hub pages (/bd/ etc.)      -0.223   (n=22)

Negative, not merely weak, and negative in every slice — so geography (US-targeted bids on
non-US audiences) is not the explanation; that was the first hypothesis and the data killed
it. Plausible mechanism: these are interactive tool pages, where a visitor arrives to USE
something, not to buy — advertiser competition for the term says little about whether that
visitor clicks an ad. Whatever the cause, a signal that points the wrong way where it CAN be
checked must not be trusted where it cannot (zero-traffic pages).

Google Ads CPC is still fetched by build-keyword-volume.py for keyword research, which is a
different question. It has no business in revenue weighting.
--------------------------------------------------------------------------------------
"""
import json
from pathlib import Path


def _strip_www(host):
    h = (host or "").strip().lower()
    return h[4:] if h.startswith("www.") else h


def _host_of(url):
    """Bare hostname from a site URL, www- and scheme-stripped. '' when unparseable.

    Returning '' on failure is deliberate: the caller treats an empty want-host as "do not
    filter", so a property whose site_url is missing or malformed keeps its old behaviour
    instead of having its whole conversion signal silently filtered to nothing.
    """
    import urllib.parse
    u = (url or "").strip()
    if not u:
        return ""
    if "//" not in u:
        u = "https://" + u
    return _strip_www(urllib.parse.urlparse(u).netloc)

# A page needs this many sessions before its measured RPM is believable. One session that
# happened to earn $0.40 computes to a $400 RPM and would rocket a dead page to the top of
# the queue. Below the floor we do not "trust it less" — the page is simply absent from the
# result and the niche-benchmark fallback answers for it.
MIN_SESSIONS_FOR_MEASURED_RPM = 30

# GA4 session-scoped dimensions are ~58% blank on D-0/D-1 while processing settles. Ending
# the window at "today" therefore under-reports revenue on the freshest pages.
GA4_LAG_DAYS = 2

# $10 RPM == weight 1.0 — the scale build-enhance-queue.py already used with the niche
# benchmarks, so swapping in measured numbers re-ranks pages against each other without
# inflating rev_weight as a whole against signal_score.
RPM_AT_WEIGHT_1 = 10.0

# Below this much total ad revenue in the window, the whole measured layer ABSTAINS.
#
# Not every property in this repo earns from ads. apps.teamzlab.com is a conversion site —
# its job is app installs, and its AdSense revenue is ~$0 by design. Reading that as "every
# page here is worthless" would clamp every candidate to the 0.5 weight floor and destroy
# the ranking the published benchmarks were at least providing. A near-zero total does not
# mean the pages are bad; it means ad RPM is the wrong yardstick for this site. So we return
# None (unknown) rather than a page full of honest, useless zeros.
MIN_SITE_REVENUE_TO_TRUST = 1.00

# Same idea per niche: a niche whose median is essentially zero teaches nothing and would
# only push its pages to the floor.
MIN_NICHE_RPM_TO_TRUST = 0.25

# Conversion rates need a lower session bar than revenue. Ad revenue on 10 sessions is noise
# (one lucky click swings RPM by hundreds of percent); a click-through rate on 10 sessions is
# coarse but honest. The non-ad properties are also far smaller — apps saw ~820 sessions in
# 28 days total — so a 30-session floor priced almost nothing there.
MIN_SESSIONS_FOR_CONVERSION = 10


def measured_rpm(cfg, days=28):
    """{landing_path: rpm_usd} for pages clearing MIN_SESSIONS_FOR_MEASURED_RPM.

    Returns None if the GA4 call could not be made. Callers MUST treat None as unknown and
    fall through to the niche benchmark — never as "these pages earned nothing"."""
    import urllib.parse as _p
    import urllib.request as _u

    tok_path = Path(cfg.get("ga4_token_file", ""))
    pid = cfg.get("ga4_property_id")
    if not pid or not tok_path.exists():
        return None

    try:
        t = json.loads(tok_path.read_text())
        data = _p.urlencode({
            "client_id": t["client_id"], "client_secret": t["client_secret"],
            "refresh_token": t["refresh_token"], "grant_type": "refresh_token",
        }).encode()
        token = json.load(_u.urlopen(_u.Request(
            t.get("token_uri", "https://oauth2.googleapis.com/token"), data=data),
            timeout=30))["access_token"]

        body = json.dumps({
            "dateRanges": [{"startDate": f"{days}daysAgo",
                            "endDate": f"{GA4_LAG_DAYS}daysAgo"}],
            "dimensions": [{"name": "landingPagePlusQueryString"}],
            "metrics": [{"name": "totalAdRevenue"}, {"name": "sessions"}],
            "limit": 2000,
        }).encode()
        req = _u.Request(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport",
            data=body, method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        rows = json.load(_u.urlopen(req, timeout=90)).get("rows", [])
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️  measured RPM UNAVAILABLE ({type(e).__name__}) — "
              f"revenue weighting falls back to niche benchmarks for every page.")
        return None

    # One landing path arrives split across query strings; sum before dividing, or a page
    # gets one RPM per ?utm_ variant and none of the slices clear the session floor.
    agg = {}
    for r in rows:
        lp = r["dimensionValues"][0]["value"]
        if not lp.startswith("/"):
            continue
        path = lp.split("?")[0]
        path = path if path.endswith("/") else path + "/"
        rev, sess = agg.get(path, (0.0, 0))
        agg[path] = (rev + float(r["metricValues"][0]["value"] or 0),
                     sess + int(r["metricValues"][1]["value"] or 0))

    total_rev = sum(rev for rev, _ in agg.values())
    if total_rev < MIN_SITE_REVENUE_TO_TRUST:
        print(f"  revenue: this property earned ${total_rev:.2f} from ads in {days}d — not an "
              f"ad-monetised site, so measured RPM ABSTAINS (niche benchmarks unchanged).")
        return None

    return {p: round(rev / sess * 1000, 2)
            for p, (rev, sess) in agg.items()
            if sess >= MIN_SESSIONS_FOR_MEASURED_RPM}


# A niche needs this many measured pages before its median is worth more than the published
# benchmark. Below it, one freak page (a viral World Cup page at $71 RPM) would define the
# whole niche.
MIN_PAGES_FOR_NICHE_CALIBRATION = 5


def calibrated_niche_rpm(measured, niche_of):
    """{niche: median measured RPM} for niches with enough of this site's own pages to speak.

    WHY THIS LAYER EXISTS. Per-page measured revenue only covers pages that already have
    traffic — and the enhance queue exists to fix pages that DON'T. On tool.teamzlab.com only
    1 of 63 candidates on a typical night has a measured RPM of its own. The niche layer
    carries the measured signal across to the other 62.

    It matters because the published benchmarks are systematically wrong for this site, in
    one direction and for one reason (measured 2026-08-08, 105 pages):

        business-saas  benchmark $22.00  ->  real $4.77   (0.22x)
        education      benchmark $10.50  ->  real $1.85   (0.18x)
        career-jobs    benchmark $16.00  ->  real $4.83   (0.30x)
        gaming         benchmark  $3.50  ->  real $1.23   (0.35x)
        lifestyle      benchmark  $5.50  ->  real $9.34   (1.70x)

    Every "high commercial intent" niche is overrated 2-5x, and the low-key ones underrated.
    Those benchmarks come from CONTENT sites, where a visitor reads and clicks an ad. These
    are TOOL pages: the visitor arrives to compute something and leaves. Same structural
    reason Google Ads CPC failed the correlation test in the module docstring above — but
    unlike CPC, this layer is built from this site's own earnings, so the discount is
    measured rather than assumed.

    `niche_of` is a callable (slug -> niche) so this module stays independent of
    revenue_priority's hub mapping."""
    if not measured:
        return {}
    import statistics
    buckets = {}
    for slug, rpm in measured.items():
        try:
            n = niche_of(slug)
        except Exception:  # noqa: BLE001
            continue
        if n:
            buckets.setdefault(n, []).append(rpm)
    # Median, not mean: one viral page must not redefine a niche.
    out = {}
    for n, v in buckets.items():
        if len(v) < MIN_PAGES_FOR_NICHE_CALIBRATION:
            continue
        med = round(statistics.median(v), 2)
        if med < MIN_NICHE_RPM_TO_TRUST:
            continue  # teaches nothing; would only pin the niche to the weight floor
        out[n] = med
    return out


def _ga4_access_token(cfg):
    import urllib.parse as _p
    import urllib.request as _u
    t = json.loads(Path(cfg["ga4_token_file"]).read_text())
    data = _p.urlencode({
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token",
    }).encode()
    return json.load(_u.urlopen(_u.Request(
        t.get("token_uri", "https://oauth2.googleapis.com/token"), data=data),
        timeout=30))["access_token"]


def conversion_value(cfg, days=28):
    """{landing_path: conversions per 1000 sessions} for properties that do not sell ads.

    WHY. tools.teamzlab.com earns from AdSense, so "what is this page worth" has a dollar
    answer. apps / goalkit / learn earn nothing from ads — their pages are worth something
    when a visitor clicks through to the App Store, views a product, or finishes a lesson.
    build-content-queue.py (which is what those three actually run) had NO value signal at
    all: it ranked purely by GSC impressions x rank proximity, so a page with 500 impressions
    and zero store clicks outranked one with 200 impressions and 12. This gives those
    properties the same "spend effort where it converts" steering that ad revenue gives tools.

    WHICH EVENT COUNTS AS VALUE IS PER-PROPERTY CONFIG, NOT A LIST IN THIS FILE.
    Set TEAMZ_VALUE_EVENTS in the property's own .teamz-automation.env, e.g.

        TEAMZ_VALUE_EVENTS="cta_click,outbound_click"     # apps: store-bound clicks
        TEAMZ_VALUE_EVENTS="lesson_complete"              # learn: finished a lesson

    Unset -> this returns None and the caller keeps today's behaviour, after printing the
    property's actual top events so the owner can choose. A hardcoded per-property event map
    living in a script shared by four sites is precisely the defect class that has already
    bitten this repo four times (MONEY_NICHES, HIGH_RPM_HUBS, TOP_PAGES, rpm-benchmarks);
    it does not get a fifth outing here."""
    import os
    import urllib.request as _u

    events = [e.strip() for e in os.getenv("TEAMZ_VALUE_EVENTS", "").split(",") if e.strip()]
    pid = cfg.get("ga4_property_id")
    if not pid or not Path(cfg.get("ga4_token_file", "")).exists():
        return None
    if not events:
        print("  value layer: TEAMZ_VALUE_EVENTS not set for this property — no conversion "
              "weighting. Set it in .teamz-automation.env to enable (e.g. \"cta_click\").")
        return None

    try:
        token = _ga4_access_token(cfg)
        body = json.dumps({
            "dateRanges": [{"startDate": f"{days}daysAgo",
                            "endDate": f"{GA4_LAG_DAYS}daysAgo"}],
            "dimensions": [{"name": "hostName"},
                           {"name": "landingPagePlusQueryString"},
                           {"name": "eventName"}],
            "metrics": [{"name": "eventCount"}, {"name": "sessions"}],
            "limit": 5000,
        }).encode()
        req = _u.Request(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport",
            data=body, method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        rows = json.load(_u.urlopen(req, timeout=90)).get("rows", [])
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️  conversion value UNAVAILABLE ({type(e).__name__}) — "
              f"queue keeps its existing impressions-only ranking.")
        return None

    # sessions is repeated per eventName row for the same landing page, so it must be taken
    # as a max per page rather than summed — summing multiplies the denominator by the number
    # of distinct events and silently divides every conversion rate by ~10.
    # ONE GA4 PROPERTY CAN COLLECT MORE THAN ONE SITE, AND THIS ONE DOES.
    # Property 524940073 is configured on apps.teamzlab.com AND hazirakhata.xyz (the Hazira
    # site is built and deployed out of the same repo, so it carries the same tag). Measured
    # 2026-08-13 over 28 days:
    #
    #     499 sessions  hazirakhata.xyz
    #     405 sessions  apps.teamzlab.com
    #       4 sessions  www.hazirakhata.xyz
    #
    # Without a host filter the majority of the "which page converts" signal steering the
    # apps content queue came from a different website. Worse than merely noisy: paths
    # collide across hosts, and section_value() then calibrated on /bn/* — a Hazira-only
    # section that no apps page can ever inherit from. The queue's own log said
    # "1 section(s) calibrated ... none=13", i.e. every candidate fell through to no signal
    # at all while the layer reported itself as working.
    want = _host_of(cfg.get("site_url") or cfg.get("site_property") or "")
    conv, sess, skipped_hosts = {}, {}, {}
    for r in rows:
        host = _strip_www(r["dimensionValues"][0]["value"])
        lp = r["dimensionValues"][1]["value"]
        if want and host != want:
            skipped_hosts[host] = skipped_hosts.get(host, 0) + 1
            continue
        if not lp.startswith("/"):
            continue
        path = lp.split("?")[0]
        path = path if path.endswith("/") else path + "/"
        ev = r["dimensionValues"][2]["value"]
        n = int(r["metricValues"][0]["value"] or 0)
        s = int(r["metricValues"][1]["value"] or 0)
        sess[path] = max(sess.get(path, 0), s)
        if ev in events:
            conv[path] = conv.get(path, 0) + n

    if skipped_hosts:
        print("  value layer: ignored " + ", ".join(
            f"{h} ({n} rows)" for h, n in sorted(skipped_hosts.items(), key=lambda kv: -kv[1]))
            + f" — not {want}")
    if want and not sess:
        # Every row belonged to some other host. Returning an empty signal quietly would look
        # identical to "this property simply has no conversions yet".
        print(f"  ⚠️  value layer: GA4 returned rows but NONE for {want} — check that "
              f"TEAMZ_SITE_URL matches the hostname this property actually collects.")
        return None

    out = {p: round(c / sess[p] * 1000, 2)
           for p, c in conv.items()
           if sess.get(p, 0) >= MIN_SESSIONS_FOR_CONVERSION}
    if not out:
        print(f"  value layer: no page has both {MIN_SESSIONS_FOR_CONVERSION}+ sessions and "
              f"a {'/'.join(events)} event yet — ranking unchanged.")
        return None
    return out


def section_value(values, min_pages=3):
    """{first_path_segment: median conversion rate} — carries the measured signal to pages
    that have no traffic of their own.

    Same problem, and same fix, as calibrated_niche_rpm() on the ad side: the queue exists to
    improve pages that are UNDERPERFORMING, and those are exactly the pages too small to have
    their own believable conversion rate. Measured directly, only 1 of 23 apps candidates and
    1 of 215 learn candidates could be priced. Grouping by section ('/blog/...' vs '/apps/...')
    lets a page inherit how well its neighbours convert, which is a far better estimate than
    the implicit "all pages are equally valuable" the queue used before."""
    if not values:
        return {}
    import statistics
    buckets = {}
    for path, v in values.items():
        buckets.setdefault(_section_key(path), []).append(v)
    return {s: round(statistics.median(v), 2)
            for s, v in buckets.items() if len(v) >= min_pages}


# Top-level pages share ONE bucket instead of each being its own section of one.
# Keying on seg[0] gave /top3picks/, /arrow-jam-3d/, /no-trace-chat/ a bucket each, and
# min_pages=3 then discarded every one of them — so apps.teamzlab.com's actual product
# pages, the whole reason the value layer exists, could never inherit a rate. Only /blog/
# survived, which meant the one section that calibrated was the section that converts
# WORST. Grouping them is also what they are: a single tier of landing pages, priced
# together the way /blog/ posts are priced together.
_ROOT_SECTION = "(root)"


def _section_key(path):
    seg = [s for s in path.strip("/").split("/") if s]
    return seg[0] if len(seg) > 1 else _ROOT_SECTION


def value_for(path, values, sections):
    """(rate, source) — the page's own rate, else its section's median, else None."""
    if values and path in values:
        return values[path], "page"
    if sections:
        key = _section_key(path)
        if key in sections:
            return sections[key], "section"
    return None, "none"


def value_weight(value, median_value):
    """Conversion rate -> the same 0.5..3.0 multiplier scale ad RPM uses.

    Normalised against the property's OWN median rather than an absolute target: a good
    store-click rate and a good lesson-completion rate are not the same number, and no
    constant in this file could be right for both."""
    if not median_value or median_value <= 0:
        return 1.0
    return max(0.5, min(3.0, value / median_value))


def rpm_for(slug, measured, fallback_rpm, niche=None, niche_rpm=None):
    """(rpm, source) using the most trustworthy layer that can answer for this page:

        1. measured      this exact page's earnings          (needs its own traffic)
        2. niche-real    this site's median for its niche    (needs 5+ measured siblings)
        3. niche-benchmark  the published average            (always answers)
    """
    if measured and slug in measured:
        return measured[slug], "measured"
    if niche and niche_rpm and niche in niche_rpm:
        return niche_rpm[niche], "niche-real"
    return fallback_rpm, "niche-benchmark"


def weight_from_rpm(rpm):
    """RPM -> rev_weight, same 0.5..3.0 clamp the queue already used."""
    return max(0.5, min(3.0, rpm / RPM_AT_WEIGHT_1))
