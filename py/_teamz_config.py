#!/usr/bin/env python3
import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def load_runtime(script_file: str) -> dict:
    py_dir = Path(script_file).resolve().parent
    automation_root = py_dir.parent
    host_site_root = automation_root.parent

    # Base machine-level config (shared across projects), then per-project override.
    base_env = os.getenv("TEAMZ_BASE_ENV", str(Path.home() / ".config" / "teamzlab" / "automation.base.env"))
    _load_env_file(Path(base_env))

    explicit_env = os.getenv("TEAMZ_AUTOMATION_ENV")
    if explicit_env:
        _load_env_file(Path(explicit_env))
    else:
        _load_env_file(host_site_root / ".teamz-automation.env")
        _load_env_file(automation_root / ".teamz-automation.env")

    host_site_root = Path(os.getenv("TEAMZ_HOST_SITE_ROOT", str(host_site_root))).expanduser().resolve()
    site_url = os.getenv("TEAMZ_SITE_URL", "https://tool.teamzlab.com/").rstrip("/") + "/"
    site_property = os.getenv("TEAMZ_SITE_PROPERTY", site_url).rstrip("/") + "/"
    config_dir = Path(os.getenv("TEAMZ_CONFIG_DIR", str(Path.home() / ".config" / "teamzlab")))
    data_dir = Path(os.getenv("TEAMZ_DATA_DIR", str(automation_root / "data")))
    report_dir = Path(os.getenv("TEAMZ_REPORT_DIR", str(host_site_root / "docs")))

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
        "sc_token_file": Path(os.getenv("TEAMZ_SC_TOKEN_FILE", str(config_dir / "search-console-token.json"))),
        "ga4_token_file": Path(os.getenv("TEAMZ_GA4_TOKEN_FILE", str(config_dir / "analytics-token.json"))),
        "adsense_token_file": Path(os.getenv("TEAMZ_ADSENSE_TOKEN_FILE", str(config_dir / "adsense-token.json"))),
        "pagespeed_key_file": Path(os.getenv("TEAMZ_PAGESPEED_KEY_FILE", str(config_dir / "pagespeed-api-key.txt"))),
        "clarity_token_file": Path(os.getenv("TEAMZ_CLARITY_TOKEN_FILE", str(config_dir / "clarity-token.txt"))),
        "ga4_property_id": os.getenv("TEAMZ_GA4_PROPERTY_ID", "528521795"),
    }

