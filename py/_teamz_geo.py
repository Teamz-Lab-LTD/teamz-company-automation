"""_teamz_geo.py — one geo table, because there used to be three that disagreed.

THE BUG THIS FIXES
-------------------
TEAMZ_KW_GEO is read by three scripts, and each expected a different shape:

  build-keyword-volume.py        numeric geoTargetConstant, e.g. "2050"
  build-keyword-volume-auto.py   a country NAME it looks up in a name->id dict, e.g. "bangladesh"
  build-keyword-candidates.py    a country NAME (falls through unresolved if not "US")

Fixed 2026-08-14: build-keyword-volume.py was hardcoded to the US constant with no
override at all — see that file's own comment. The fix set TEAMZ_KW_GEO=2050 in
goalkit's .teamz-automation.env, which is exactly correct for that script and
silently wrong for the other two, which don't understand a bare number and (in
build-keyword-volume-auto.py's case) REFUSE to guess and return 0 rather than
resolve anything:

    TEAMZ_KW_GEO='2050' is not in the geo map — refusing to guess.

That fired every night from the fix until this file existed — goalkit's pending
Keyword Planner batches were never resolved, silently, for two nights running.

Every reader now goes through resolve() here instead of keeping its own table, so
TEAMZ_KW_GEO can be set to EITHER a numeric geoTargetConstant or a country name and
every script understands it the same way.
"""

# geoTargetConstant -> canonical country name. Extend here, nowhere else.
ID_TO_NAME = {
    "2840": "United States", "2050": "Bangladesh", "2826": "United Kingdom",
    "2124": "Canada", "2036": "Australia", "2276": "Germany", "2250": "France",
    "2356": "India", "2372": "Ireland", "2554": "New Zealand", "2702": "Singapore",
    "2392": "Japan", "2528": "Netherlands",
}
NAME_TO_ID = {name.lower(): gid for gid, name in ID_TO_NAME.items()}
# Short codes some callers already use (build-keyword-candidates.py's GEO_MAP).
CODE_TO_ID = {
    "bd": "2050", "us": "2840", "gb": "2826", "in": "2356", "jp": "2392",
    "de": "2276", "ca": "2124", "au": "2036",
}


def resolve(value, default_id="2840"):
    """Any of {geoTargetConstant, country name, short code} -> (id, name).

    Never raises and never guesses past what it's given: an unrecognised value
    returns (None, value) so the caller can refuse loudly, the way
    build-keyword-volume-auto.py already did before this file existed — that
    behavior is correct and is preserved, just no longer format-specific.
    """
    if not value:
        return default_id, ID_TO_NAME.get(default_id, default_id)
    v = value.strip()
    if v in ID_TO_NAME:
        return v, ID_TO_NAME[v]
    vl = v.lower()
    if vl in NAME_TO_ID:
        return NAME_TO_ID[vl], ID_TO_NAME[NAME_TO_ID[vl]]
    if vl in CODE_TO_ID:
        gid = CODE_TO_ID[vl]
        return gid, ID_TO_NAME.get(gid, gid)
    return None, value
