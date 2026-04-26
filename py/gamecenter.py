#!/usr/bin/env python3
"""Cross-app Apple Game Center achievement automation.

Mirror of gpgs.py for the App Store Connect API v1 Game Center
endpoints. One YAML source of truth (`automation_data/achievements.yaml`)
drives:

  * PATCH existing gameCenterAchievements (points, showBeforeEarned,
    repeatable, archived flags)
  * POST gameCenterAchievementLocalizations (en-US name +
    beforeEarnedDescription + afterEarnedDescription) — upserts the
    en-US locale, leaves other locales alone.
  * POST gameCenterAchievements for missing entries — by vendorIdentifier
    (the reverse-DNS string in `_kGameCenterAchievementIds`).

Apple has no programmatic publish step. Achievements go live in the
App Store with the next app version review.

Why this exists:
    Game Center has 23 existing achievements with generic name-cased
    auto-titles ("Star First Bronze") that don't match the in-game
    SpaceX voice. The Console UI is per-locale form-by-form; doing
    26 × 1 locale by hand drifts copy across worlds. YAML pushes one
    canonical en-US set in seconds.

Canonical credentials (shared across every Teamz Lab project):
    ASC P8 key:  ~/.config/teamzlab/AuthKey_559DD92MBH.p8
    Key ID:      559DD92MBH
    Issuer ID:   100d6ef8-7452-4aff-85a4-990158b60b3d

Per-app config (host project's `.teamz-automation.env`):
    TEAMZ_APPLE_APP_ID            numeric ASC app id (e.g. 6739433404)
    TEAMZ_ACHIEVEMENTS_YAML       override; defaults to
                                  automation_data/achievements.yaml

YAML schema — see gpgs.py + the YAML file's header. Required per
achievement: id, name, description, points.

Usage:
    # Show what's live (with localization summary)
    python3 gamecenter.py list

    # Diff vs YAML, dry-run
    python3 gamecenter.py sync --dry-run

    # Apply (PATCH attrs + upsert en-US localization + INSERT missing)
    python3 gamecenter.py sync --apply

Gotchas baked in:
    * Apple's POST /v1/gameCenterAchievements requires the
      `gameCenterDetail` relationship to be set. Fetched dynamically
      from /v1/apps/{appId}/gameCenterDetail at script start.
    * `referenceName` must be unique inside the gameCenterDetail —
      we use the YAML `name` for the human display, but reuse the
      same string for referenceName (Apple allows it).
    * Localization: en-US localized `name` ≤30 chars, before/after
      earned descriptions ≤45 chars (per Apple's CMS, undocumented in
      the API docs but enforced by the backend).
    * `points` valid range is 1-100, sum across game ≤1000.
    * Apple uses `en-US` (hyphen). Sending `en_US` returns 409
      ENTITY_ERROR.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    yaml = None

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None


def _require_yaml() -> None:
    if yaml is None:
        raise SystemExit("Missing PyYAML — pip install --user pyyaml")


def _require_pyjwt() -> None:
    if pyjwt is None:
        raise SystemExit(
            "Missing PyJWT + cryptography — "
            "pip install --user pyjwt cryptography"
        )


# ─────────────────────────────────────────────────────────────────────
# Config + auth
# ─────────────────────────────────────────────────────────────────────

_DEFAULT_ASC_KEY = Path.home() / ".config" / "teamzlab" / "AuthKey_559DD92MBH.p8"
_DEFAULT_ASC_KEY_ID = "559DD92MBH"
_DEFAULT_ASC_ISSUER_ID = "100d6ef8-7452-4aff-85a4-990158b60b3d"
ASC_BASE = "https://api.appstoreconnect.apple.com"
LOCALE = "en-US"


def _load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _resolve_config() -> dict[str, str]:
    file_env = _load_env_file(Path.cwd() / ".teamz-automation.env")
    return {
        "TEAMZ_APPLE_APP_ID": os.environ.get(
            "TEAMZ_APPLE_APP_ID", file_env.get("TEAMZ_APPLE_APP_ID", "")
        ),
        "TEAMZ_ACHIEVEMENTS_YAML": os.environ.get(
            "TEAMZ_ACHIEVEMENTS_YAML",
            file_env.get(
                "TEAMZ_ACHIEVEMENTS_YAML", "automation_data/achievements.yaml"
            ),
        ),
        "TEAMZ_ASC_KEY_FILEPATH": os.environ.get(
            "TEAMZ_ASC_KEY_FILEPATH",
            file_env.get("TEAMZ_ASC_KEY_FILEPATH", str(_DEFAULT_ASC_KEY)),
        ),
        "TEAMZ_ASC_KEY_ID": os.environ.get(
            "TEAMZ_ASC_KEY_ID",
            file_env.get("TEAMZ_ASC_KEY_ID", _DEFAULT_ASC_KEY_ID),
        ),
        "TEAMZ_ASC_ISSUER_ID": os.environ.get(
            "TEAMZ_ASC_ISSUER_ID",
            file_env.get("TEAMZ_ASC_ISSUER_ID", _DEFAULT_ASC_ISSUER_ID),
        ),
    }


def _asc_jwt(cfg: dict[str, str]) -> str:
    _require_pyjwt()
    key_path = Path(cfg["TEAMZ_ASC_KEY_FILEPATH"]).expanduser()
    if not key_path.exists():
        raise SystemExit(f"ASC P8 key not found: {key_path}")
    payload = {
        "iss": cfg["TEAMZ_ASC_ISSUER_ID"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 1200,
        "aud": "appstoreconnect-v1",
    }
    return pyjwt.encode(
        payload,
        key_path.read_text(),
        algorithm="ES256",
        headers={"alg": "ES256", "kid": cfg["TEAMZ_ASC_KEY_ID"], "typ": "JWT"},
    )


def _request(
    method: str,
    url: str,
    jwt: str,
    body: Optional[dict] = None,
    retries: int = 2,
) -> tuple[int, dict | None, str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    last: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {jwt}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode("utf-8")
                try:
                    return r.status, json.loads(raw) if raw else None, raw
                except json.JSONDecodeError:
                    return r.status, None, raw
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") if e.fp else ""
            try:
                return e.code, json.loads(raw), raw
            except json.JSONDecodeError:
                return e.code, None, raw
        except (TimeoutError, urllib.error.URLError) as e:
            last = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise last  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────
# Apple ASC helpers
# ─────────────────────────────────────────────────────────────────────

def _get_game_center_detail_id(app_id: str, jwt: str) -> str:
    url = f"{ASC_BASE}/v1/apps/{app_id}/gameCenterDetail"
    s, j, raw = _request("GET", url, jwt)
    if s != 200 or not j:
        raise SystemExit(
            f"could not fetch gameCenterDetail for app {app_id}: {s} {raw[:300]}"
        )
    return j["data"]["id"]


def _list_achievements(detail_id: str, jwt: str) -> list[dict]:
    items: list[dict] = []
    next_url: str | None = (
        f"{ASC_BASE}/v1/gameCenterDetails/{detail_id}/gameCenterAchievements"
        f"?limit=200&include=localizations"
    )
    while next_url:
        s, j, raw = _request("GET", next_url, jwt)
        if s != 200 or not j:
            raise SystemExit(f"list achievements failed: {s} {raw[:300]}")
        items.extend(j.get("data", []))
        # paginate via included data + links.next
        next_url = j.get("links", {}).get("next")
    return items


def _list_localizations(achievement_id: str, jwt: str) -> list[dict]:
    url = (
        f"{ASC_BASE}/v1/gameCenterAchievements/{achievement_id}"
        f"/localizations?limit=200"
    )
    s, j, raw = _request("GET", url, jwt)
    if s != 200 or not j:
        raise SystemExit(
            f"list localizations({achievement_id}): {s} {raw[:300]}"
        )
    return j.get("data", [])


def _create_achievement(
    detail_id: str,
    *,
    reference_name: str,
    vendor_id: str,
    points: int,
    show_before_earned: bool,
    repeatable: bool,
    jwt: str,
) -> dict:
    url = f"{ASC_BASE}/v1/gameCenterAchievements"
    body = {
        "data": {
            "type": "gameCenterAchievements",
            "attributes": {
                "referenceName": reference_name,
                "vendorIdentifier": vendor_id,
                "points": points,
                "showBeforeEarned": show_before_earned,
                "repeatable": repeatable,
            },
            "relationships": {
                "gameCenterDetail": {
                    "data": {"type": "gameCenterDetails", "id": detail_id}
                }
            },
        }
    }
    s, j, raw = _request("POST", url, jwt, body)
    if s >= 300:
        raise RuntimeError(f"create achievement failed: {s} {raw[:600]}")
    return j["data"]


def _patch_achievement(
    achievement_id: str,
    *,
    points: int | None = None,
    show_before_earned: bool | None = None,
    repeatable: bool | None = None,
    jwt: str,
) -> None:
    attrs: dict[str, Any] = {}
    if points is not None:
        attrs["points"] = points
    if show_before_earned is not None:
        attrs["showBeforeEarned"] = show_before_earned
    if repeatable is not None:
        attrs["repeatable"] = repeatable
    if not attrs:
        return
    body = {
        "data": {
            "type": "gameCenterAchievements",
            "id": achievement_id,
            "attributes": attrs,
        }
    }
    url = f"{ASC_BASE}/v1/gameCenterAchievements/{achievement_id}"
    s, j, raw = _request("PATCH", url, jwt, body)
    if s >= 300:
        raise RuntimeError(f"patch attributes failed: {s} {raw[:600]}")


def _create_localization(
    achievement_id: str,
    *,
    name: str,
    before_earned_desc: str,
    after_earned_desc: str,
    jwt: str,
) -> dict:
    url = f"{ASC_BASE}/v1/gameCenterAchievementLocalizations"
    body = {
        "data": {
            "type": "gameCenterAchievementLocalizations",
            "attributes": {
                "locale": LOCALE,
                "name": name,
                "beforeEarnedDescription": before_earned_desc,
                "afterEarnedDescription": after_earned_desc,
            },
            "relationships": {
                "gameCenterAchievement": {
                    "data": {
                        "type": "gameCenterAchievements",
                        "id": achievement_id,
                    }
                }
            },
        }
    }
    s, j, raw = _request("POST", url, jwt, body)
    if s >= 300:
        raise RuntimeError(f"create localization failed: {s} {raw[:600]}")
    return j["data"]


def _patch_localization(
    loc_id: str,
    *,
    name: str,
    before_earned_desc: str,
    after_earned_desc: str,
    jwt: str,
) -> None:
    body = {
        "data": {
            "type": "gameCenterAchievementLocalizations",
            "id": loc_id,
            "attributes": {
                "name": name,
                "beforeEarnedDescription": before_earned_desc,
                "afterEarnedDescription": after_earned_desc,
            },
        }
    }
    url = f"{ASC_BASE}/v1/gameCenterAchievementLocalizations/{loc_id}"
    s, j, raw = _request("PATCH", url, jwt, body)
    if s >= 300:
        raise RuntimeError(f"patch localization failed: {s} {raw[:600]}")


# ─────────────────────────────────────────────────────────────────────
# Local helpers
# ─────────────────────────────────────────────────────────────────────

def _read_local_id_map(yaml_data: dict, host_root: Path) -> dict[str, str]:
    ac = host_root / "lib" / "app_config.dart"
    if not ac.exists():
        return {}
    text = ac.read_text()
    map_var = yaml_data.get("apple_id_map_var", "_kGameCenterAchievementIds")
    idx = text.find(f"{map_var} = {{")
    if idx == -1:
        return {}
    end = text.find("};", idx)
    block = text[idx:end]
    out: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("'") and not line.startswith('"'):
            continue
        if ":" not in line:
            continue
        k, _, rest = line.partition(":")
        v = rest.strip().rstrip(",").strip()
        out[k.strip().strip("'").strip('"')] = v.strip().strip("'").strip('"')
    return out


def _load_yaml(path: Path) -> dict:
    _require_yaml()
    if not path.exists():
        raise SystemExit(f"Missing achievements yaml at {path}")
    return yaml.safe_load(path.read_text())


# ─────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────

def cmd_list(args: argparse.Namespace) -> int:
    cfg = _resolve_config()
    app_id = args.apple_app_id or cfg["TEAMZ_APPLE_APP_ID"]
    if not app_id:
        raise SystemExit("Missing TEAMZ_APPLE_APP_ID")
    jwt = _asc_jwt(cfg)
    detail_id = _get_game_center_detail_id(app_id, jwt)
    items = _list_achievements(detail_id, jwt)
    print(f"{len(items)} Game Center achievements (detail={detail_id}):")
    for it in items:
        attrs = it.get("attributes", {}) or {}
        ref = attrs.get("referenceName", "?")
        vid = attrs.get("vendorIdentifier", "?")
        pts = attrs.get("points", "?")
        sbe = "show" if attrs.get("showBeforeEarned") else "hide"
        print(f"  {it['id']:36s} {pts:3} pts {sbe:4} {ref!r} ({vid})")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    cfg = _resolve_config()
    app_id = args.apple_app_id or cfg["TEAMZ_APPLE_APP_ID"]
    if not app_id:
        raise SystemExit("Missing TEAMZ_APPLE_APP_ID")

    yaml_path = Path(args.yaml or cfg["TEAMZ_ACHIEVEMENTS_YAML"])
    yaml_data = _load_yaml(yaml_path)
    entries = yaml_data.get("achievements") or []

    id_map = _read_local_id_map(yaml_data, Path.cwd())
    if not id_map:
        raise SystemExit(
            "Couldn't parse _kGameCenterAchievementIds map. "
            "Need vendor IDs to sync — fix lib/app_config.dart parsing."
        )

    jwt = _asc_jwt(cfg)
    detail_id = _get_game_center_detail_id(app_id, jwt)
    live = _list_achievements(detail_id, jwt)
    by_vendor = {
        (it.get("attributes") or {}).get("vendorIdentifier", ""): it
        for it in live
    }

    plan: list[tuple[str, str, dict]] = []
    for entry in entries:
        local = entry["id"]
        vendor = id_map.get(local, "")
        if not vendor:
            print(f"  (skip) {local}: no vendor id mapped in app_config")
            continue
        action = "patch" if vendor in by_vendor else "create"
        plan.append((action, vendor, entry))

    creates = sum(1 for a, _, _ in plan if a == "create")
    patches = sum(1 for a, _, _ in plan if a == "patch")
    print(f"Plan: PATCH {patches} existing, CREATE {creates} missing.")

    for action, vendor, entry in plan:
        name = entry["name"][:30]
        desc = entry["description"][:45]
        if action == "create":
            if args.dry_run:
                print(f"  CREATE  {vendor} → '{name}' / '{desc}' / {entry['points']}pts")
                continue
            new = _create_achievement(
                detail_id,
                reference_name=name,
                vendor_id=vendor,
                points=int(entry.get("points", 5)),
                show_before_earned=not bool(entry.get("hidden", False)),
                repeatable=False,
                jwt=jwt,
            )
            ach_id = new["id"]
            _create_localization(
                ach_id,
                name=name,
                before_earned_desc=desc,
                after_earned_desc=desc,
                jwt=jwt,
            )
            print(f"  CREATE  {vendor} → id={ach_id} '{name}' ✓")
        else:
            existing = by_vendor[vendor]
            ach_id = existing["id"]
            if args.dry_run:
                print(
                    f"  PATCH   {vendor} (id={ach_id}) "
                    f"→ '{name}' / '{desc}' / {entry['points']}pts"
                )
                continue
            _patch_achievement(
                ach_id,
                points=int(entry.get("points", 5)),
                show_before_earned=not bool(entry.get("hidden", False)),
                repeatable=False,
                jwt=jwt,
            )
            # upsert en-US localization
            locs = _list_localizations(ach_id, jwt)
            existing_loc = next(
                (
                    l
                    for l in locs
                    if (l.get("attributes") or {}).get("locale") == LOCALE
                ),
                None,
            )
            if existing_loc:
                _patch_localization(
                    existing_loc["id"],
                    name=name,
                    before_earned_desc=desc,
                    after_earned_desc=desc,
                    jwt=jwt,
                )
            else:
                _create_localization(
                    ach_id,
                    name=name,
                    before_earned_desc=desc,
                    after_earned_desc=desc,
                    jwt=jwt,
                )
            print(f"  PATCH   {vendor} (id={ach_id}) '{name}' ✓")

    if args.dry_run:
        print()
        print("Dry-run complete. Re-run with --apply to write.")
    else:
        print()
        print(
            "Sync complete. Apple Game Center achievements go live with "
            "the next app review submission — no separate publish step."
        )
    return 0


# ─────────────────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s_list = sub.add_parser("list", help="List live Game Center achievements")
    s_list.add_argument("--apple-app-id", help="Apple ASC numeric app id")
    s_list.set_defaults(func=cmd_list)

    s_sync = sub.add_parser("sync", help="PATCH + INSERT from yaml")
    s_sync.add_argument("--apple-app-id", help="Apple ASC numeric app id")
    s_sync.add_argument("--yaml", help="Path to achievements yaml")
    g = s_sync.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    s_sync.set_defaults(func=cmd_sync)
    return p


def main() -> int:
    args = _build_parser().parse_args()
    if hasattr(args, "dry_run") and not args.dry_run and not args.apply:
        args.dry_run = True
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
