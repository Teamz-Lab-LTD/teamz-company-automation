# /shipaton-check <app-slug> [--refresh-rules] [--claim <category>]

**MANDATORY ENTRY POINT for any Shipaton category, prize, eligibility or submission question.**
Never answer "which categories can this app enter?" from memory. Never re-derive the category list
in conversation. The owner has re-derived it across multiple sessions and it cost weeks — that is
the exact mistake this command exists to end.

## What this command is

The category rulebook lives in
[`claude-config/knowledge/Shipaton_2026_Category_Registry.md`](../knowledge/Shipaton_2026_Category_Registry.md).
The per-app state lives in that app's `docs/shipaton/CATEGORY-TRACKER.md`.

This command joins them: run every `OPEN IF` test against the app, diff the result against the
tracker, and report **every reachable category that is not yet claimed**, ranked by
prize-per-hour-of-work.

It does not decide pricing. It does not push anything.

## Pre-flight reads (do these BEFORE saying anything)

1. `claude-config/knowledge/Shipaton_2026_Category_Registry.md` — §1 verdict table + **§1b
   judging criteria** + §4 traps. **§1b is not optional.** §1 says only whether the app may
   ENTER a category; §1b says how it is SCORED, and the two lead to different advice. Most
   categories are judged on craft, not traction — so "wait until we have users" is usually
   the wrong call and must never be given without checking §1b first.
   **§4 is mandatory.** Nine documented traps, every one of which a previous session got wrong.
2. `<app>/docs/shipaton/CATEGORY-TRACKER.md` — current state. If absent, this run creates it.
3. `claude-config/knowledge/Shipaton_2026_Knowledge_Base.md` — app allocation, #BuildInPublic engine.
4. `claude-config/knowledge/RevenueCat_Benchmarks_2026.md` — **TRIPWIRES table only**, and only if
   the session is heading toward price / trial / paywall structure.
5. `claude-config/memory/shipaton_category_coverage.md` — the locked coverage rule.

## Flow

### Step 1 — Resolve the app

Same auto-discovery as `/aso-refresh`: scan every project's `.teamz-automation.env` for
`TEAMZ_APP_SLUG=<slug>`. No hardcoded switch.

```bash
APP_SLUG="$1"
PROJECT_DIR=""
while IFS= read -r envf; do
  if grep -qE "^TEAMZ_APP_SLUG=$APP_SLUG\b" "$envf" 2>/dev/null; then
    PROJECT_DIR="$(dirname "$envf")"; break
  fi
done < <(find "$HOME/Projects/Teamz Lab Projects/teamz-projects" -maxdepth 5 -name ".teamz-automation.env" 2>/dev/null)
[ -z "$PROJECT_DIR" ] && { echo "Unknown slug '$APP_SLUG'"; exit 1; }
```

### Step 2 — The eligibility gate (run FIRST, it can end the conversation)

Two questions that are unfixable if answered wrong:

1. **Was this app ever publicly released on any eligible store before Jul 31, 2026?**
   If yes → **permanently ineligible**. Stop. Say so. Do not plan anything.
2. **Is it published on at least one eligible store today?**
   If no → every category except Next Gen is blocked. That is the top of the report, above all
   category talk. Find the specific blocker (release signing, store account, review status) and
   name it.

### Step 3 — Run every `OPEN IF` test

For each of the 20 rows in registry §1, evaluate the test **against this app** — never inherit a
verdict from another app. Evidence, not assertion:

| Test | How to actually check |
|---|---|
| Has ≥1 real IAP | RevenueCat project exists + product + entitlement + SDK keys wired in the build |
| Serves RevenueCat Ads | `purchases_flutter` **10.x** AND RevenueCat Ads configured — grep for `google_mobile_ads` alone is a FAIL (registry §4 trap 3) |
| Is Kotlin Multiplatform | inspect the build system, not the README |
| Student on team | ask; needs a qualifying academic email |
| Stripe operable | which country's entity, and can it take **live** charges (not test mode) |
| Social-good angle | must be credible and already true of the product — never invent one |
| Influencer fit | read that influencer's stated audience in the rules; near-miss = closed |

### Step 4 — Diff against the tracker, write it back

Update `<app>/docs/shipaton/CATEGORY-TRACKER.md`. Columns:
`Category | Reachable | Prize | Requirement | Status | Owner | Evidence`

`Status` ∈ `claimed` · `in-progress` · `NOT STARTED` · `closed (reason)`.
`Owner` ∈ `owner` · `agent`. Be honest about which — account creation, money, decisions and
#BuildInPublic posting can never be delegated to an agent.

### Step 5 — Report

1. **Eligibility verdict** (Step 2) — first, always.
2. **Gap list:** every category where `Reachable = yes` AND `Status = NOT STARTED`, sorted by
   prize ÷ estimated hours. This is the point of the command.
3. **Free-after-ship reminder:** registry §2's four description-only categories, if unclaimed.
4. **Owner-only actions**, separated out — the things no agent can do.
5. **Ship Kit milestones** not yet unlocked (registry §3).
6. **Citations:** registry version/date + the tracker path + anything re-fetched.

## Refusal conditions

- Answering any "which categories / what prize / am I eligible" question **without reading the
  registry first**.
- Advising on how to WIN or improve standing in a category **without quoting that category's
  §1b judging criteria**. Entry requirements are not scoring criteria. Guessing at how a
  category is judged — or assuming it rewards downloads/revenue when its criteria never
  mention them — is the same class of error as re-deriving the category list.
- Declaring a category closed **without quoting its `OPEN IF` test and the evidence that failed**.
  "Probably not a fit" is not a verdict.
- Recommending a category that requires spending money **without stating the cost up front**.
  Assume the owner's budget is **$0** unless told otherwise this session.
- Planning category work while the app is unpublished, **without leading with that blocker**.
  Publishing gates every category except Next Gen. Category strategy under an unpublished app is
  motion, not progress.
- Fake-targeting a closed category to inflate the count (registry §4 trap 8).
- Touching price, trial length, or paywall structure without checking the
  `RevenueCat_Benchmarks_2026.md` TRIPWIRES table.

## `--refresh-rules`

Sponsor categories are added **during** the event. Re-fetch
https://revenuecat-shipaton-2026.devpost.com/rules, diff against registry §1, and append new rows.
**Never overwrite a row** — append and date it, same discipline as the decisions log.
Run this at least once before any submission.

## Citation requirement

The report must state: this command's path, the registry's `Built:` date, the tracker path, and
whether rules were re-fetched this run. So the owner can audit which signals actually fired.
