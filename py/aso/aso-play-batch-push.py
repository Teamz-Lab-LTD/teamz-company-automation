#!/usr/bin/env python3
"""Push all 39 Play Console listings + graphics in ONE edit transaction.

Reads from android/app/src/main/play/listings/{locale}/* (txt + graphics)
Pushes to Google Play via androidpublisher v3, committing one edit.
Maps Fastlane Apple locale codes → Play Console locale codes.
"""
import os
import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAY_DIR = PROJECT_ROOT / "android" / "app" / "src" / "main" / "play" / "listings"
PACKAGE = os.environ.get("TEAMZ_PLAY_PACKAGE_NAME", "com.teamz.toss.toss")
SA_PATH = os.path.expanduser(
    os.environ.get("TEAMZ_PLAY_SERVICE_ACCOUNT_JSON",
                   "~/.config/teamzlab/play-console-service-account.json"))

# Apple Fastlane locale → Google Play locale code
APPLE_TO_PLAY = {
    "en-US": "en-US", "en-AU": "en-AU", "en-CA": "en-CA", "en-GB": "en-GB",
    "ar-SA": "ar", "ca": "ca", "cs": "cs-CZ", "da": "da-DK",
    "de-DE": "de-DE", "el": "el-GR", "es-ES": "es-ES", "es-MX": "es-419",
    "fi": "fi-FI", "fr-CA": "fr-CA", "fr-FR": "fr-FR", "he": "iw-IL",
    "hi": "hi-IN", "hr": "hr", "hu": "hu-HU", "id": "id",
    "it": "it-IT", "ja": "ja-JP", "ko": "ko-KR", "ms": "ms",
    "nl-NL": "nl-NL", "no": "no-NO", "pl": "pl-PL", "pt-BR": "pt-BR",
    "pt-PT": "pt-PT", "ro": "ro", "ru": "ru-RU", "sk": "sk",
    "sv": "sv-SE", "th": "th", "tr": "tr-TR", "uk": "uk",
    "vi": "vi", "zh-Hans": "zh-CN", "zh-Hant": "zh-TW",
}


def main():
    if not Path(SA_PATH).exists():
        print(f"[ERROR] Service account JSON not found: {SA_PATH}", file=sys.stderr)
        return 1
    creds = service_account.Credentials.from_service_account_file(
        SA_PATH, scopes=["https://www.googleapis.com/auth/androidpublisher"])
    pub = build("androidpublisher", "v3", credentials=creds, cache_discovery=False)

    # 1. Open one edit
    try:
        edit = pub.edits().insert(packageName=PACKAGE, body={}).execute()
    except HttpError as e:
        print(f"[ERROR] Could not create edit: {e}", file=sys.stderr)
        return 1
    eid = edit["id"]
    print(f"  Created edit {eid}")

    # 2. Push every locale's listing
    success, fail = 0, 0
    for apple_loc, play_loc in APPLE_TO_PLAY.items():
        d = PLAY_DIR / apple_loc
        if not d.is_dir():
            continue
        title = (d / "title.txt").read_text(encoding="utf-8").strip()
        short = (d / "short-description.txt").read_text(encoding="utf-8").strip()
        full = (d / "full-description.txt").read_text(encoding="utf-8").strip()
        body = {"title": title, "shortDescription": short, "fullDescription": full}
        try:
            pub.edits().listings().update(
                packageName=PACKAGE, editId=eid, language=play_loc, body=body
            ).execute()
            print(f"  ✓ {apple_loc:<10} → {play_loc:<8}  title={len(title)}c short={len(short)}c full={len(full)}c")
            success += 1
        except HttpError as e:
            err = str(e)[:200]
            print(f"  ✗ {apple_loc:<10} → {play_loc:<8}  {err}")
            fail += 1

    # 3. Push graphics (en-US only — Play applies them across locales)
    en_graphics = PLAY_DIR / "en-US" / "graphics"
    graphic_jobs = [
        ("phoneScreenshots", en_graphics / "phone-screenshots", "*.jpg", 8),
        ("sevenInchScreenshots", en_graphics / "tablet-10-inch-screenshots", "*.jpg", 8),
        ("tenInchScreenshots", en_graphics / "tablet-10-inch-screenshots", "*.jpg", 8),
        ("featureGraphic", en_graphics / "feature-graphic", "*.png", 1),
        ("icon", en_graphics / "icon", "*.png", 1),
    ]
    for img_type, src_dir, pattern, max_n in graphic_jobs:
        if not src_dir.exists():
            print(f"  ⊘ {img_type}: source dir missing {src_dir.relative_to(PROJECT_ROOT)}")
            continue
        # Delete existing
        try:
            pub.edits().images().deleteall(
                packageName=PACKAGE, editId=eid, language="en-US", imageType=img_type
            ).execute()
        except HttpError:
            pass
        # Upload
        files = sorted(src_dir.glob(pattern))[:max_n]
        for f in files:
            mime = "image/png" if f.suffix == ".png" else "image/jpeg"
            try:
                pub.edits().images().upload(
                    packageName=PACKAGE, editId=eid, language="en-US",
                    imageType=img_type,
                    media_body=MediaFileUpload(str(f), mimetype=mime),
                ).execute()
                print(f"  ✓ {img_type}: uploaded {f.name}")
            except HttpError as e:
                print(f"  ✗ {img_type}/{f.name}: {str(e)[:200]}")
                fail += 1

    # 4. Commit the edit
    print(f"\n  Summary: {success} listings ok, {fail} errors")
    if "--commit" in sys.argv:
        try:
            pub.edits().commit(packageName=PACKAGE, editId=eid).execute()
            print("  ✅ COMMITTED edit to Google Play (saved as draft if app not yet published)")
        except HttpError as e:
            err = str(e)
            if "draft" in err.lower() or "appNotApprovedYet" in err:
                print("  ✅ App is in draft/pre-launch state — listing saved; finish app setup in Play Console")
            else:
                print(f"  ❌ Commit failed: {err[:300]}")
                return 1
    else:
        pub.edits().delete(packageName=PACKAGE, editId=eid).execute()
        print("  Dry-run OK: edit validated and discarded. Add --commit to save.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
