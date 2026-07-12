#!/usr/bin/env python3
import os
from pathlib import Path


def _optional_path(raw: str):
    if not raw:
        return None
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def _load_env_file(path: Path, *, override: bool = False) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        # Strip an INLINE comment. Bash `source` does this; this loader did not, so
        #     TEAMZ_CONTENT_MIN_IMPR=100    # keeps the queue out of the noise
        # became the literal string "100    # keeps the queue out of the noise" and every
        # int() of it blew up (or, worse, a string compare silently did the wrong thing).
        # Only strip when the '#' is unquoted and preceded by whitespace, so a value that
        # legitimately contains '#' (a colour, a URL fragment) survives.
        if not (v.startswith('"') or v.startswith("'")):
            hash_at = v.find(" #")
            if hash_at != -1:
                v = v[:hash_at].rstrip()
        v = v.strip('"').strip("'")
        # Match shell `source`: expand $HOME and other env refs in .env values.
        v = os.path.expandvars(os.path.expanduser(v))
        if not k:
            continue
        if override or k not in os.environ:
            os.environ[k] = v


def _find_host_root(script_file: str) -> Path:
    """Which repo is CALLING us?

    NOT derivable from the script path. Every host repo exposes these scripts as
    SYMLINKS in its scripts/ dir, so Path(script_file).resolve() collapses them all to
    <automation>/py — whose parent is the shared projects dir, never the caller. The old
    code did exactly that, so EVERY repo silently fell back to the default site
    (tool.teamzlab.com): apps/learn/goalkit pulled GSC for, and requested indexing of,
    the WRONG property. Same bug that was fixed in sh/lib/config.sh on 2026-07-12 — this
    is its Python twin, found 2026-07-12 while building the content queue.

    Order: explicit env > walk up from CWD for .teamz-automation.env > legacy fallback.
    """
    explicit = os.getenv("TEAMZ_HOST_SITE_ROOT")
    if explicit:
        return Path(os.path.expandvars(os.path.expanduser(explicit))).resolve()
    d = Path.cwd().resolve()
    for cand in (d, *d.parents):
        if (cand / ".teamz-automation.env").is_file():
            return cand
    return Path(script_file).resolve().parent.parent.parent


def load_runtime(script_file: str) -> dict:
    py_dir = Path(script_file).resolve().parent
    automation_root = py_dir.parent
    host_site_root = _find_host_root(script_file)

    # Base machine-level config (shared across projects), then per-project override.
    base_env = os.getenv("TEAMZ_BASE_ENV", str(Path.home() / ".config" / "teamzlab" / "automation.base.env"))
    _load_env_file(Path(base_env))

    explicit_env = os.getenv("TEAMZ_AUTOMATION_ENV")
    if explicit_env:
        _load_env_file(Path(explicit_env), override=True)
    else:
        # Same as bash `source`: project .env wins over inherited process env.
        _load_env_file(host_site_root / ".teamz-automation.env", override=True)
        _load_env_file(automation_root / ".teamz-automation.env", override=True)

    host_site_root = Path(
        os.path.expandvars(os.path.expanduser(os.getenv("TEAMZ_HOST_SITE_ROOT", str(host_site_root))))
    ).resolve()
    site_url = os.getenv("TEAMZ_SITE_URL", "https://tool.teamzlab.com/").rstrip("/") + "/"

    # A GSC property is one of TWO kinds and they normalise DIFFERENTLY:
    #   URL-prefix   https://tool.teamzlab.com/     -> MUST end in "/"
    #   domain       sc-domain:goalkit.teamzlab.com -> MUST NOT end in "/"
    # Blindly appending "/" produced "sc-domain:goalkit.teamzlab.com/", which the Search
    # Console API rejects with HTTP 400 — so goalkit's anomaly/keyword pulls silently
    # returned nothing while the site really had 938 clicks at a 16.7% CTR. Same fix as
    # sh/lib/config.sh; this is the Python twin.
    site_property = os.getenv("TEAMZ_SITE_PROPERTY", site_url)
    if site_property.startswith("sc-domain:"):
        site_property = site_property.rstrip("/")
    else:
        site_property = site_property.rstrip("/") + "/"
    config_dir = Path(
        os.path.expandvars(
            os.path.expanduser(os.getenv("TEAMZ_CONFIG_DIR", str(Path.home() / ".config" / "teamzlab")))
        )
    )
    data_dir = Path(
        os.path.expandvars(os.path.expanduser(os.getenv("TEAMZ_DATA_DIR", str(automation_root / "data"))))
    )
    report_dir = Path(
        os.path.expandvars(os.path.expanduser(os.getenv("TEAMZ_REPORT_DIR", str(host_site_root / "docs"))))
    )

    return {
        "automation_root": automation_root,
        "host_site_root": host_site_root,
        "site_url": site_url,
        "site_property": site_property,
        "google_project": os.getenv("TEAMZ_GOOGLE_CLOUD_PROJECT", "teamzlab-tools"),
        "config_dir": config_dir,
        "data_dir": data_dir,
        "report_dir": report_dir,
        "project_type": os.getenv("TEAMZ_PROJECT_TYPE", "website").strip().lower(),
        "sc_token_file": Path(
            os.path.expandvars(
                os.path.expanduser(
                    os.getenv("TEAMZ_SC_TOKEN_FILE", str(config_dir / "search-console-token.json"))
                )
            )
        ),
        "ga4_token_file": Path(
            os.path.expandvars(
                os.path.expanduser(os.getenv("TEAMZ_GA4_TOKEN_FILE", str(config_dir / "analytics-token.json")))
            )
        ),
        "adsense_token_file": Path(
            os.path.expandvars(
                os.path.expanduser(os.getenv("TEAMZ_ADSENSE_TOKEN_FILE", str(config_dir / "adsense-token.json")))
            )
        ),
        "pagespeed_key_file": Path(
            os.path.expandvars(
                os.path.expanduser(os.getenv("TEAMZ_PAGESPEED_KEY_FILE", str(config_dir / "pagespeed-api-key.txt")))
            )
        ),
        "clarity_token_file": Path(
            os.path.expandvars(
                os.path.expanduser(os.getenv("TEAMZ_CLARITY_TOKEN_FILE", str(config_dir / "clarity-token.txt")))
            )
        ),
        "ga4_property_id": os.getenv("TEAMZ_GA4_PROPERTY_ID", "528521795"),
        "play_service_account_json": _optional_path(
            os.getenv("TEAMZ_PLAY_SERVICE_ACCOUNT_JSON", "").strip()
        ),
        "play_package_name": os.getenv("TEAMZ_PLAY_PACKAGE_NAME", "").strip(),
    }

