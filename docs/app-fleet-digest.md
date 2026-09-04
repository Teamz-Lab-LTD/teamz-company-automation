# App Fleet Digest — 2026-09-05

One verdict per app from Play bulk reports (installs / uninstalls / ratings — Google publishes these MONTHLY, the `data through` column is the truth of how fresh each row is), Play vitals, App Store reviews, the Crashlytics monitor and the /aso-refresh sentinels.

| RETENTION-BLOCKED 2 | CRASH-BLOCKED 0 | RATINGS-STARVED 11 | ASO-DUE 2 | GROW 0 | UNMEASURED 4 |

| app | verdict | installs 28d | uninstalls | ratio | active (Δ28d) | ratings | crash % | ASO signal | data through | do this |
|---|---|---|---|---|---|---|---|---|---|---|
| zoyiai | **RETENTION-BLOCKED** | 63 | 57 | 90% | 47 (-4) | 0 | — | never | 2026-08-21 | Stop buying traffic for it. Fix the first session + the D1 return hook (push: unknown). Measure D1 in GA4 (NON |
| devicegpt | **RETENTION-BLOCKED** | 50 | 81 | 162% | 395 (-35) | 11 | — | 7d | 2026-08-21 | Stop buying traffic for it. Fix the first session + the D1 return hook (push: OneSignal + WorkManager). Measur |
| no-trace-chat | **RATINGS-STARVED** | 112 | 103 | 92% | 75 (+10) | 2 | — | 72d | 2026-08-21 | Earn ratings before chasing installs. Review prompt: present (in_app_review via kit). Fire it at the peak mome |
| scorpion-solitaire | **RATINGS-STARVED** | 68 | 58 | 85% | 20 (+14) | 0 | — | 76d | 2026-08-21 | Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge. |
| notetube-ai | **RATINGS-STARVED** | 58 | 59 | 102% | 91 (+7) | 0 | — | 9d | 2026-08-21 | Earn ratings before chasing installs. Review prompt: present (single call site in main.dart). Fire it at the p |
| hyper-toad | **RATINGS-STARVED** | 25 | 10 | 40% | 18 (+15) | 0 | — | 77d | 2026-08-21 | Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge. |
| forty-thieves-solitaire | **RATINGS-STARVED** | 21 | 20 | 95% | 5 (+1) | 0 | — | 54d | 2026-08-21 | Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge. |
| arrow-jam-3d | **RATINGS-STARVED** | 18 | 15 | 83% | 12 (+3) | 2 | — | 54d | 2026-08-21 | Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge. |
| golf-solitaire | **RATINGS-STARVED** | 12 | 10 | 83% | 3 (+0) | 0 | — | 77d | 2026-08-21 | Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge. |
| toss | **RATINGS-STARVED** | 9 | 4 | 44% | 16 (+4) | 3 | — | never | 2026-08-21 | Earn ratings before chasing installs. Review prompt: present (kit, main + 4 tool screens). Fire it at the peak |
| voltline | **RATINGS-STARVED** | 3 | 4 | 133% | 10 (+1) | 6 | — | 84d | 2026-08-21 | Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge. |
| top3picks | **RATINGS-STARVED** | 0 | 0 | — | 11 (-1) | 3 | — | 27d | 2026-08-21 | Earn ratings before chasing installs. Review prompt: present (kit, 3 call sites). Fire it at the peak moment ( |
| brimful | **RATINGS-STARVED** | — | — | — | — | 0 | — | 54d | — | Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge. |
| hazira-khata | **ASO-DUE** | 1053 | 973 | 92% | 1309 (+311) | 111 | 0.0 | never | 2026-08-21 | `/aso-refresh hazira-khata` — the skill picks SIGNAL_ONLY vs FULL_REWRITE from the sentinels. |
| chopstick-landing-games | **ASO-DUE** | 680 | 699 | 103% | 802 (+2) | 13 | — | 83d | 2026-08-21 | `/aso-refresh chopstick-landing-games` — the skill picks SIGNAL_ONLY vs FULL_REWRITE from the sentinels. |
| goldmend | **UNMEASURED** | — | — | — | — | — | — | 6d | — | Run `bash sh/app-fleet-nightly.sh --only=goldmend` and read logs/app-fleet/goldmend/steps/. |
| sleep-switch | **UNMEASURED** | — | — | — | — | — | — | 3d | — | Run `bash sh/app-fleet-nightly.sh --only=sleep-switch` and read logs/app-fleet/sleep-switch/steps/. |
| resume-coach | **UNMEASURED** | — | — | — | — | — | — | 0d | — | Run `bash sh/app-fleet-nightly.sh --only=resume-coach` and read logs/app-fleet/resume-coach/steps/. |
| interview-boss-plus | **UNMEASURED** | — | — | — | — | — | — | never | — | Run `bash sh/app-fleet-nightly.sh --only=interview-boss-plus` and read logs/app-fleet/interview-boss-plus/step |

## ⚠️ UNMEASURED — unknown, not zero

- **goldmend** — Play's bulk bucket has no install CSVs for com.teamzlab.goldmend (27 files absent) — the app is unpublished, under ~2 weeks old, or the package id is wrong; failed steps: velocity
- **sleep-switch** — Play's bulk bucket has no install CSVs for com.teamzlab.sleep_switch (27 files absent) — the app is unpublished, under ~2 weeks old, or the package id is wrong; failed steps: velocity, vitals
- **resume-coach** — Play's bulk bucket has no install CSVs for com.teamzlab.airesumechecker (27 files absent) — the app is unpublished, under ~2 weeks old, or the package id is wrong; failed steps: velocity
- **interview-boss-plus** — Play's bulk bucket has no install CSVs for com.teamzlab.interviewbossplus (27 files absent) — the app is unpublished, under ~2 weeks old, or the package id is wrong; failed steps: velocity

## ASO due (paste one line; the skill decides signal vs rewrite)

- `/aso-refresh hazira-khata` — never signal-pulled; Android rewrite floor open (never)
- `/aso-refresh chopstick-landing-games` — signal 83d old; Android rewrite floor open (never); iOS rewrite floor open (never)

## Needs a human (briefs in docs/app-fleet/)

- **zoyiai** (RETENTION-BLOCKED): Stop buying traffic for it. Fix the first session + the D1 return hook (push: unknown). Measure D1 in GA4 (NONE — add a property).
- **devicegpt** (RETENTION-BLOCKED): Stop buying traffic for it. Fix the first session + the D1 return hook (push: OneSignal + WorkManager). Measure D1 in GA4 (property 481224245).
- **no-trace-chat** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present (in_app_review via kit). Fire it at the peak moment (a win, a completed task), never on launch.
- **scorpion-solitaire** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge.dart) — fires only if the GAME calls it. Fire it at the peak moment (a win, a completed task), never on launch.
- **notetube-ai** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present (single call site in main.dart). Fire it at the peak moment (a win, a completed task), never on launch.
- **hyper-toad** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge.dart) — fires only if the GAME calls it. Fire it at the peak moment (a win, a completed task), never on launch.
- **forty-thieves-solitaire** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge.dart) — fires only if the GAME calls it. Fire it at the peak moment (a win, a completed task), never on launch.
- **arrow-jam-3d** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge.dart) — fires only if the GAME calls it. Fire it at the peak moment (a win, a completed task), never on launch.
- **golf-solitaire** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge.dart) — fires only if the GAME calls it. Fire it at the peak moment (a win, a completed task), never on launch.
- **toss** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present (kit, main + 4 tool screens). Fire it at the peak moment (a win, a completed task), never on launch.
- **voltline** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge.dart) — fires only if the GAME calls it. Fire it at the peak moment (a win, a completed task), never on launch.
- **top3picks** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present (kit, 3 call sites). Fire it at the peak moment (a win, a completed task), never on launch.
- **brimful** (RATINGS-STARVED): Earn ratings before chasing installs. Review prompt: present in kit via JS bridge (game_webview_review_bridge.dart) — fires only if the GAME calls it. Fire it at the peak moment (a win, a completed task), never on launch.
