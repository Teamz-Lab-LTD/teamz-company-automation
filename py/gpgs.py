#!/usr/bin/env python3
"""Cross-app Play Games Services achievement automation.

Mirror of iap.py for the Play Games Configuration v1 API. One YAML
source of truth (`automation_data/achievements.yaml`) drives:

  * PATCH existing achievements (set name + description + XP +
    incremental stepsToUnlock + initial state)
  * INSERT missing achievements (returns new tokens for app_config)
  * Optional reorder via sortRank

The Games Configuration API does NOT expose a programmatic publish step
— after sync, the developer clicks "Review and publish" in the Play
Console UI once. That UI gate is the only manual step; everything
else is REST.

Why this exists:
    Play Console's Achievements UI is form-by-form, slow, and easy to
    desync from the local achievement IDs map in app_config.dart. A
    YAML-driven push pattern keeps both sides in lockstep across every
    Teamz Lab game and removes per-app re-learning of the API's
    quirks.

Canonical credentials (shared across every Teamz Lab project):
    Play Service Account JSON
        ~/.config/teamzlab/play-console-service-account.json
        SA email: play-console-automation@...
        Per-game: SA must be granted Game services management on the
                  Game project (Play Console -> Game services ->
                  Setup -> Project members -> Add).

Per-app config (host project's `.teamz-automation.env`):
    TEAMZ_PLAY_PACKAGE_NAME      e.g. com.teamz.lab.chopstick_landing_games
    TEAMZ_PG_APPLICATION_ID      numeric Play Games application id (1004286776719)
    TEAMZ_ACHIEVEMENTS_YAML      override path; defaults to
                                 automation_data/achievements.yaml in CWD

YAML schema — see the example file's header for full key list. Required
per achievement: id, name, description, points, xp.

Usage:
    # List live state (drafts vs published vs missing)
    python3 gpgs.py list

    # Diff YAML vs live, show planned PATCH/INSERT bodies, no writes
    python3 gpgs.py sync --dry-run

    # Apply: PATCH 24 + INSERT 2 missing. Prints new IDs to paste into
    # app_config.dart's _kPlayGamesAchievementIds map.
    python3 gpgs.py sync --apply

    # Publish reminder (Console UI is the only path)
    python3 gpgs.py publish

Gotchas baked in:
    * games#localizedStringBundle is double-nested: each name/description
      goes inside translations[].value. Sending a flat string returns
      a vague 400. Use `_localized_bundle()`.
    * `stepsToUnlock` only valid on INCREMENTAL — sending it on STANDARD
      returns 400. _build_resource() omits the key when not incremental.
    * `initialState` cannot change after first publish. Patches that
      try to flip REVEALED ↔ HIDDEN return 200 but silently no-op.
    * `pointValue` is XP, not Apple points. Cap is 1000 per achievement,
      7500 per game.
    * Each PATCH payload must include the full `draft` object — partial
      drafts truncate. Always read-modify-write.
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
    yaml = None  # surfaced via _require_yaml()

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GAuthRequest
except ImportError:
    service_account = None
    GAuthRequest = None


# ─────────────────────────────────────────────────────────────────────
# Dependency guards
# ─────────────────────────────────────────────────────────────────────

def _require_yaml() -> None:
    if yaml is None:
        raise SystemExit(
            "Missing PyYAML. Install:\n"
            "  pip install --user pyyaml"
        )


def _require_google_auth() -> None:
    if service_account is None:
        raise SystemExit(
            "Missing google-auth. Install:\n"
            "  pip install --user google-auth google-auth-httplib2"
        )


# ─────────────────────────────────────────────────────────────────────
# Config + auth
# ─────────────────────────────────────────────────────────────────────

PLAY_SA_DEFAULT = Path.home() / ".config" / "teamzlab" / "play-console-service-account.json"
# Canonical host per discovery doc — `www.googleapis.com` legacy proxy
# only handles GET, write methods 400 there. Always use the dedicated
# host for PUT / POST / DELETE.
GAMES_BASE = "https://gamesconfiguration.googleapis.com/games/v1configuration"
SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]


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
    """Load .teamz-automation.env (cwd) + env overrides."""
    file_env = _load_env_file(Path.cwd() / ".teamz-automation.env")
    cfg = {
        "TEAMZ_PG_APPLICATION_ID": os.environ.get(
            "TEAMZ_PG_APPLICATION_ID",
            file_env.get("TEAMZ_PG_APPLICATION_ID", ""),
        ),
        "TEAMZ_ACHIEVEMENTS_YAML": os.environ.get(
            "TEAMZ_ACHIEVEMENTS_YAML",
            file_env.get(
                "TEAMZ_ACHIEVEMENTS_YAML",
                "automation_data/achievements.yaml",
            ),
        ),
        "TEAMZ_PLAY_SERVICE_ACCOUNT_JSON": os.environ.get(
            "TEAMZ_PLAY_SERVICE_ACCOUNT_JSON",
            file_env.get(
                "TEAMZ_PLAY_SERVICE_ACCOUNT_JSON",
                str(PLAY_SA_DEFAULT),
            ),
        ),
    }
    return cfg


def _oauth_token(sa_path: str) -> str:
    """Mint an access token from the Play service account JSON."""
    _require_google_auth()
    p = Path(sa_path).expanduser()
    if not p.exists():
        raise SystemExit(
            f"Play service account JSON missing at {p}. "
            "Download from GCP -> IAM -> Service Accounts and place "
            "at ~/.config/teamzlab/play-console-service-account.json"
        )
    creds = service_account.Credentials.from_service_account_file(
        str(p), scopes=SCOPES
    )
    creds.refresh(GAuthRequest())
    return creds.token


def _request(
    method: str,
    url: str,
    token: str,
    body: Optional[dict] = None,
    retries: int = 2,
) -> tuple[int, dict | None, str]:
    """Wraps urllib so we get (status, json, raw_body) consistently.

    Retries TimeoutError up to `retries` times. Games Configuration
    write endpoints are slow (1-3s) and occasionally drop mid-flight.
    """
    data = None if body is None else json.dumps(body).encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode("utf-8")
                try:
                    return r.status, json.loads(raw), raw
                except json.JSONDecodeError:
                    return r.status, None, raw
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") if e.fp else ""
            try:
                return e.code, json.loads(raw), raw
            except json.JSONDecodeError:
                return e.code, None, raw
        except (TimeoutError, urllib.error.URLError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise last_err  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────
# YAML schema + resource builder
# ─────────────────────────────────────────────────────────────────────

LOCALE = "en-US"  # Google Play Games uses hyphen-locale (matches Apple ASC)


def _localized_bundle(value: str, kind: str) -> dict:
    """Build a games#localizedStringBundle for a single en_US value.

    kind is one of:
      games#localizedStringBundle  (top wrapper)
    Inner translations use:
      games#localizedString
    """
    return {
        "kind": "gamesConfiguration#localizedStringBundle",
        "translations": [
            {
                "kind": "gamesConfiguration#localizedString",
                "locale": LOCALE,
                "value": value,
            }
        ],
    }


def _build_resource(entry: dict, application_id: str) -> dict:
    """Translate a YAML entry into a games#achievementResource body."""
    incremental = bool(entry.get("incremental", False))
    hidden = bool(entry.get("hidden", False))
    body: dict[str, Any] = {
        "kind": "gamesConfiguration#achievementConfiguration",
        "achievementType": "INCREMENTAL" if incremental else "STANDARD",
        "initialState": "HIDDEN" if hidden else "REVEALED",
        "draft": {
            "kind": "gamesConfiguration#achievementConfigurationDetail",
            "name": _localized_bundle(entry["name"], "name"),
            "description": _localized_bundle(entry["description"], "description"),
            "pointValue": int(entry.get("xp", entry.get("points", 5))),
            "sortRank": int(entry.get("sort_rank", 0)),
        },
    }
    if incremental:
        body["stepsToUnlock"] = int(entry["steps"])
    return body


def _load_yaml(path: Path) -> dict:
    _require_yaml()
    if not path.exists():
        raise SystemExit(
            f"Missing achievements yaml at {path}. "
            "Place at automation_data/achievements.yaml or set "
            "TEAMZ_ACHIEVEMENTS_YAML."
        )
    return yaml.safe_load(path.read_text())


# ─────────────────────────────────────────────────────────────────────
# Live API — list / patch / insert
# ─────────────────────────────────────────────────────────────────────

def list_live(application_id: str, token: str) -> list[dict]:
    """Return the raw achievementResource list for the application."""
    url = f"{GAMES_BASE}/applications/{application_id}/achievements?maxResults=200"
    status, data, raw = _request("GET", url, token)
    if status != 200 or data is None:
        raise SystemExit(f"list achievements failed: {status} {raw[:400]}")
    return data.get("items", [])


def get_live(achievement_id: str, token: str) -> dict:
    """Fetch a single achievement (needed for the optimistic-lock token
    that PUT requires)."""
    url = f"{GAMES_BASE}/achievements/{achievement_id}"
    status, data, raw = _request("GET", url, token)
    if status != 200 or data is None:
        raise SystemExit(f"GET {achievement_id} failed: {status} {raw[:400]}")
    return data


def patch_live(achievement_id: str, body: dict, token: str) -> dict:
    """Update an achievement in place. The Games Configuration API
    does not support PATCH — only PUT (full replace). We always send
    the full resource so partial-write surprises don't bite."""
    url = f"{GAMES_BASE}/achievements/{achievement_id}"
    status, data, raw = _request("PUT", url, token, body)
    if status >= 300:
        raise RuntimeError(f"PUT {achievement_id} failed: {status} {raw[:400]}")
    return data or {}


def insert_live(application_id: str, body: dict, token: str) -> dict:
    url = f"{GAMES_BASE}/applications/{application_id}/achievements"
    status, data, raw = _request("POST", url, token, body)
    if status >= 300:
        raise RuntimeError(f"INSERT failed: {status} {raw[:400]}")
    return data or {}


# ─────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────

def _read_local_id_map(yaml_data: dict, host_root: Path) -> dict[str, str]:
    """Read the host app's _kPlayGamesAchievementIds map (lib/app_config.dart)."""
    ac = host_root / "lib" / "app_config.dart"
    if not ac.exists():
        return {}
    text = ac.read_text()
    map_var = yaml_data.get("google_id_map_var", "_kPlayGamesAchievementIds")
    # naive parse — find "$map_var = {" then read lines until "};"
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
        # 'key': 'val',
        if ":" not in line:
            continue
        k, _, rest = line.partition(":")
        v = rest.strip().rstrip(",").strip()
        k = k.strip().strip("'").strip('"')
        v = v.strip().strip("'").strip('"')
        out[k] = v
    return out


def cmd_list(args: argparse.Namespace) -> int:
    cfg = _resolve_config()
    app_id = args.application_id or cfg["TEAMZ_PG_APPLICATION_ID"]
    if not app_id:
        raise SystemExit("Missing TEAMZ_PG_APPLICATION_ID — set in .teamz-automation.env")
    token = _oauth_token(cfg["TEAMZ_PLAY_SERVICE_ACCOUNT_JSON"])
    items = list_live(app_id, token)
    print(f"{len(items)} achievements live for application {app_id}:")
    for it in items:
        draft = it.get("draft") or {}
        pub = it.get("published") or {}
        name = (
            (draft.get("name") or {}).get("translations", [{}])[0].get("value")
            or (pub.get("name") or {}).get("translations", [{}])[0].get("value")
            or ""
        )
        steps = it.get("stepsToUnlock") or "-"
        state = it.get("initialState") or "?"
        kind = it.get("achievementType") or "?"
        published = "published" if pub else "draft"
        print(
            f"  {it['id']:30s} {kind:11s} {state:8s} steps={steps:3} "
            f"[{published}] {name!r}"
        )
    return 0


def _diff_plan(
    yaml_entries: list[dict],
    live: list[dict],
    id_map: dict[str, str],
) -> tuple[list[tuple[dict, str]], list[dict]]:
    """Split YAML entries into (existing-to-PATCH, missing-to-INSERT)."""
    live_by_id = {it["id"]: it for it in live}
    patches: list[tuple[dict, str]] = []
    inserts: list[dict] = []
    for entry in yaml_entries:
        local = entry["id"]
        platform = id_map.get(local, "")
        if platform.startswith("CgkI") and platform in live_by_id:
            patches.append((entry, platform))
        elif platform.startswith("TODO_") or platform == "":
            inserts.append(entry)
        else:
            # Mapped to something but not live — also insert (shouldn't happen)
            inserts.append(entry)
    return patches, inserts


def cmd_sync(args: argparse.Namespace) -> int:
    cfg = _resolve_config()
    app_id = args.application_id or cfg["TEAMZ_PG_APPLICATION_ID"]
    if not app_id:
        raise SystemExit("Missing TEAMZ_PG_APPLICATION_ID")

    yaml_path = Path(args.yaml or cfg["TEAMZ_ACHIEVEMENTS_YAML"])
    yaml_data = _load_yaml(yaml_path)
    entries = yaml_data.get("achievements") or []
    if not entries:
        raise SystemExit(f"No achievements in {yaml_path}")

    id_map = _read_local_id_map(yaml_data, Path.cwd())
    if not id_map:
        print("(warn) couldn't parse _kPlayGamesAchievementIds — treating all as INSERT")

    token = _oauth_token(cfg["TEAMZ_PLAY_SERVICE_ACCOUNT_JSON"])
    live = list_live(app_id, token)
    patches, inserts = _diff_plan(entries, live, id_map)

    print(f"Plan: PATCH {len(patches)} existing, INSERT {len(inserts)} missing.")
    for entry, pid in patches:
        body = _build_resource(entry, app_id)
        body["id"] = pid  # PUT requires id in body to match URL path
        n = entry["name"]
        if args.dry_run:
            print(f"  PUT {pid}  ({entry['id']}) name='{n}'")
            print(f"    body: {json.dumps(body)[:200]}")
        else:
            # Fetch existing for the optimistic-lock token + preserved
            # iconUrl + sortRank that we don't want to clobber.
            current = get_live(pid, token)
            body["token"] = current.get("token", "")
            existing_draft = current.get("draft") or {}
            # Preserve iconUrl ONLY when non-empty — empty string fails 400.
            existing_icon = existing_draft.get("iconUrl") or ""
            if existing_icon:
                body["draft"]["iconUrl"] = existing_icon
            if "sortRank" in existing_draft and not body["draft"].get("sortRank"):
                body["draft"]["sortRank"] = existing_draft["sortRank"]
            patch_live(pid, body, token)
            print(f"  PUT {pid}  ({entry['id']}) name='{n}' ✓")

    new_ids: dict[str, str] = {}
    for entry in inserts:
        body = _build_resource(entry, app_id)
        n = entry["name"]
        if args.dry_run:
            print(f"  INSERT (planned) ({entry['id']}) name='{n}'")
            print(f"    body: {json.dumps(body)[:200]}")
        else:
            result = insert_live(app_id, body, token)
            new_ids[entry["id"]] = result.get("id", "?")
            print(f"  INSERT {result.get('id')} ({entry['id']}) name='{n}' ✓")

    if not args.dry_run and new_ids:
        print()
        print("ACTION REQUIRED — paste these into lib/app_config.dart:")
        for k, v in new_ids.items():
            print(f"    '{k}': '{v}',")

    if args.dry_run:
        print()
        print("Dry-run complete. Re-run with --apply to write.")
    else:
        print()
        print("Sync complete. Now click 'Review and publish' in Play Console.")
        print(f"  https://play.google.com/console/u/0/developers/.../app/{app_id}/game-services")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    print(
        "Play Games Configuration API has no programmatic publish step.\n"
        "Open Play Console -> Game services -> {your game} -> Configuration\n"
        "and click 'Review and publish' to push drafts global.\n\n"
        "Achievements remain `Available to testers` until that button is pushed."
    )
    return 0


# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s_list = sub.add_parser("list", help="List live achievements (drafts + published)")
    s_list.add_argument("--application-id", help="Play Games numeric app id")
    s_list.set_defaults(func=cmd_list)

    s_sync = sub.add_parser("sync", help="PATCH existing + INSERT missing from yaml")
    s_sync.add_argument("--application-id", help="Play Games numeric app id")
    s_sync.add_argument("--yaml", help="Path to achievements yaml")
    g = s_sync.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="Show planned writes only")
    g.add_argument("--apply", action="store_true", help="Apply writes")
    s_sync.set_defaults(func=cmd_sync)

    s_pub = sub.add_parser("publish", help="Publish reminder (Console UI is the only path)")
    s_pub.set_defaults(func=cmd_publish)

    return p


def main() -> int:
    args = _build_parser().parse_args()
    if hasattr(args, "dry_run") and not args.dry_run and not args.apply:
        # Default to dry-run if neither flag given
        args.dry_run = True
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
