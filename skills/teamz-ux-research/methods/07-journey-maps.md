# Journey Maps

Walks a persona through a specific goal, surfacing where the experience
breaks. A good journey map is a diagnostic tool, not a wall poster.

## Format

| # | Step | Action | Thought | Emotion | Touchpoint | Gap / Opportunity |
|---|---|---|---|---|---|---|
| 1 | Install + open | Taps the app icon | "What's this do?" | 😐 curious | Home screen | No headline answer |
| 2 | First impression | Sees 3 competing cards | "Where do I start?" | 😕 overwhelmed | Home | Hick's law violation |
| 3 | **Moment of truth** | Taps broken feature | "Oh, I have no data" | 😖 frustrated | Feature X | Fix or hide |
| … | | | | | | |

## Required columns

- **Step** — what phase of the journey (discovery, onboarding, task, return, etc.)
- **Action** — observable behavior
- **Thought** — internal mental state (from think-aloud or inference)
- **Emotion** — tag with simple emoji or word
- **Touchpoint** — which surface (screen, email, notification, external)
- **Gap / Opportunity** — what's broken, what's possible

## Moments of truth

Label 1–3 steps as "Moments of Truth" — the points where the user
decides "this is/isn't for me." Usually the first real task, the first
sign of value, or the first friction point.

Design attention must concentrate at these moments.

## Scope one journey per map

Don't try to map "the whole product." Map one journey:

- "First-time user: install → first note saved"
- "Returning user: reopens app → reviews notes from last week"
- "Churned user: hits paywall → decides whether to upgrade"

## Before vs. after maps

When redesigning, produce TWO maps:

- **Current-state journey** — what happens today, with friction labeled
- **Future-state journey** — what should happen, with each change tied
  to a rec ID

Place them side-by-side. Differences are your redesign scope.

## Data sources per column

| Column | Best data source |
|---|---|
| Action | Usability test observation, analytics event |
| Thought | Think-aloud quote, interview |
| Emotion | Facial/voice cues from sessions, survey sentiment |
| Gap | Severity-rated issue log |

If any column is pure speculation, mark the whole row `[hypothesized]`.

## Service blueprint (optional, for systems work)

When the journey crosses team boundaries (support, billing, ops), add a
below-the-line swimlane showing the **backstage** processes that make
the front-stage experience possible. Exposes handoff failures and
dependencies.

## Journey map sins

- Mapping an aspirational future as if it were the current state
- Skipping the emotion column ("we don't have data") — use proxies
- Using generic "frustration" everywhere — specificity matters
- Making it beautiful before it's useful
