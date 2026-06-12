# appstore-fastlane/ — shared iOS Fastlane config

One shared Fastfile reused by every Teamz iOS app via symlink — auth, metadata push, screenshot push, submit lanes. Per-app setup: run [`setup-appstore-fastlane.sh`](./setup-appstore-fastlane.sh) once from the app project, fill the env from [`appstore-fastlane.env.example`](./appstore-fastlane.env.example). Lane recipes: [`../CLAUDE.md`](../CLAUDE.md) § Fastlane.

| File | What it does | Typical command |
|---|---|---|
| [`Fastfile`](./Fastfile) | Shared Fastlane lanes (auth, metadata, screenshots, submit) reused by every Teamz iOS app via symlink. | `fastlane <lane_name>` |
| [`Gemfile`](./Gemfile) | Ruby deps: fastlane >= 2.220 and dotenv. | `bundle install` |
| [`appstore-fastlane.env.example`](./appstore-fastlane.env.example) | Per-app env template: ASC API key (pre-filled for Teamz), bundle ID, app name, URLs. | — |
| [`setup-appstore-fastlane.sh`](./setup-appstore-fastlane.sh) | One-time project setup: symlinks shared Fastfile, copies env template, creates 40-locale metadata dirs. | `bash appstore-fastlane/setup-appstore-fastlane.sh` |
| [`sync_game_achievements.rb`](./sync_game_achievements.rb) | Creates/updates Game Center and Play Games achievements from a JSON spec; dry-run by default. | `ruby appstore-fastlane/sync_game_achievements.rb --spec=achievements.json --platform=both` |

---
**Lost?** The repo-wide index lives in [`../README.md`](../README.md) (root README, section 5) and the agent rulebook in [`../CLAUDE.md`](../CLAUDE.md). This folder's table above is the complete list — every file here is in it.
