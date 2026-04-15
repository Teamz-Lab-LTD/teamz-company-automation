# app-stats — Quickstart for any Teamz project

Pulls lifetime stats from App Store Connect, Play Console, AdMob, and GA4 into a single markdown report. Reusable across every Teamz app and web project.

## One-time per machine

```bash
mkdir -p ~/.config/teamzlab
# Copy these credential files from your primary Mac:
#   AuthKey_559DD92MBH.p8
#   play-console-service-account.json
#   admob-token.json
#   analytics-token.json
#   oauth-client-config.json

pip3 install --break-system-packages google-cloud-storage
# For full report (AdMob + GA4):
#   pip3 install --break-system-packages -r app-stats/requirements.txt
# For Android via gsutil (optional — Python path works without it):
#   brew install --cask google-cloud-sdk
```

## Per-project setup (~5 min)

```bash
cd my-app/
ln -s packages/team_mvp_kit/teamz-company-automation/app-stats app-stats
cp app-stats/.stats.env.example .stats.env
# fill in 7 per-app values (see table below)
echo -e ".stats.env\napp-stats-reports/" >> .gitignore
./app-stats/pull_all.sh lifetime
```

## Account-level values (baked into the kit — DO NOT re-enter)

| Field | Value |
|---|---|
| ASC Vendor # | `93213066` |
| ASC Key ID | `559DD92MBH` |
| ASC Issuer ID | `100d6ef8-7452-4aff-85a4-990158b60b3d` |
| Play reports bucket | `pubsite_prod_7194763656319643086` |
| AdMob Publisher ID | `pub-7088022825081956` |
| Apple Team ID | `NDV83KC5LC` |

Full list: `../CLAUDE.md` (Teamz Lab Company Info section).

## Per-app values (fill these in `.stats.env`)

| Var | Where to find it |
|---|---|
| `APP_NAME` | Anything — display name in the report header |
| `APP_BUNDLE_ID` | `ios/Runner.xcodeproj` → General tab, or `ios/Runner/Info.plist` `CFBundleIdentifier` |
| `APPLE_APP_ID` | App Store Connect → the app → App Information → "Apple ID" (numeric) |
| `ANDROID_PACKAGE` | `android/app/build.gradle` → `applicationId` |
| `ADMOB_IOS_APP_ID` | `ios/Runner/Info.plist` → `GADApplicationIdentifier` (`ca-app-pub-...~...`) |
| `ADMOB_ANDROID_APP_ID` | `android/app/src/main/AndroidManifest.xml` → `com.google.android.gms.ads.APPLICATION_ID` |
| `GA4_PROPERTY_ID` | GA4 → Admin → Property Settings → 9-digit Property ID |

## Run variants

```bash
./app-stats/pull_all.sh lifetime     # all-time (default)
./app-stats/pull_all.sh last-30d     # monthly review
./app-stats/pull_all.sh last-90d     # quarterly review
./app-stats/pull_all.sh ytd          # year-to-date
```

Output: `app-stats-reports/YYYY-MM-DD-<range>.md`

## With Claude

In any project with this symlinked, say:

> "Pull lifetime stats for this app"

Claude reads `.stats.env`, fills missing values from the table above (or asks), runs `pull_all.sh`, and delivers a decision-grade summary (installs, revenue, ARPU, monetization verdict).

## Common errors

| Error | Fix |
|---|---|
| `ASC 410 GONE_ERROR` | Old report version deprecated — remove `filter[version]` (already fixed in `pullers/ios_sales.rb`) |
| `403 on Play earnings/` | Grant service account "View financial data" in Play Console → Users and permissions |
| `ModuleNotFoundError: google.analytics` | `pip3 install --break-system-packages -r app-stats/requirements.txt` |
| `gsutil not found` | Use the Python GCS path (already default) or `brew install --cask google-cloud-sdk` |

## Adding new projects (even web)

For a web project, same symlink pattern works. You'll need additional pullers for Search Console / AdSense — add them under `pullers/` and wire into `pull_all.sh`. Keep the `.stats.env`-driven config pattern.
