# app-stats

Reusable automation module that pulls lifetime app stats from four sources
and produces a single markdown report:

- App Store Connect (iOS sales, installs, proceeds)
- Google Play Console reports bucket (Android installs, IAP earnings)
- AdMob Network Report API (ad revenue, impressions, clicks)
- GA4 Data API (DAU, sessions, new users, engagement)

Project-agnostic: symlink into any app, configure via `.stats.env`.

## Prerequisites

1. **gcloud SDK** (for `gsutil`) — required by the Play Console puller.
   `brew install --cask google-cloud-sdk` then `gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS`.
2. **Ruby gems** — `jwt` and `dotenv`. Already in the kit Gemfile; run `bundle install` in your project.
3. **Python deps** — `pip install -r app-stats/requirements.txt` (or in a venv).
4. Shared credentials dir: `~/.config/teamzlab/` containing
   `AuthKey_559DD92MBH.p8`, `play-console-service-account.json`,
   `admob-token.json`, `analytics-token.json`.

## One-time setup

1. Copy the env template into your project root:
   ```
   cp app-stats/.stats.env.example ../.stats.env
   ```
2. Fill in `ASC_VENDOR_NUMBER`, `ANDROID_PACKAGE`, `PLAY_REPORTS_BUCKET`,
   AdMob publisher/app IDs, and `GA4_PROPERTY_ID`. The ASC API-key vars are
   inherited from `.appstore-fastlane.env` if you already use Fastlane.
3. Grant the Play service account the **"View financial data"** permission
   on the app: Play Console → Users and permissions → select SA → app
   permissions → tick "View financial data" for the target app.
4. Add `.stats.env` to `.gitignore`.

## Usage

```
./app-stats/pull_all.sh                # lifetime (default)
./app-stats/pull_all.sh last-30d
./app-stats/pull_all.sh last-90d
./app-stats/pull_all.sh ytd
```

Output lands in `$REPORT_OUT_DIR/YYYY-MM-DD-<range>.md`
(default: `app-stats-reports/` in the project root).

Partial failures are tolerated — any puller that errors is shown as
`N/A — <reason>` in the report, and warnings are collected at the bottom.

## Troubleshooting

- **iOS 401 `NOT_AUTHORIZED`** — `.p8` key revoked or `ASC_ISSUER_ID` wrong.
  Regenerate in App Store Connect → Users and Access → Integrations.
- **iOS 403 on salesReports** — the API key role must be Admin, Finance, or
  Sales. App Manager is not enough.
- **Play `AccessDeniedException: 403`** — the service account lacks "View
  financial data". The bucket auth is per-app, not per-project.
- **Play `BucketNotFoundException`** — `PLAY_REPORTS_BUCKET` is wrong; copy
  it fresh from Play Console → Download reports → Statistics → Copy URI.
- **AdMob 401** — `admob-token.json` refresh token expired. Re-run the
  OAuth flow against scope `https://www.googleapis.com/auth/admob.readonly`.
- **AdMob 400 on multi-year lifetime** — handled automatically (request is
  retried in yearly chunks).
- **GA4 `PERMISSION_DENIED`** — the token principal needs at least "Viewer"
  on the GA4 property, and the property ID must be the numeric one (not the
  measurement ID `G-XXXX`).
