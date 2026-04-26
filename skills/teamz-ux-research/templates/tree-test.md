# Tree Test Plan — [IA / nav study]

> Validate labels and hierarchy before engineering builds them.
> Unmoderated, n=15–30, runs in 1–3 days via Maze / Optimal Workshop.

## Objective

Confirm users can find [what] in [where] without getting lost.

## Tree under test

Provide the labeled hierarchy (indent for nesting):

```
- Home
- Library
  - All videos
  - Has notes
  - Summarized
  - Archived
- [AppBar right] Search
- [AppBar right] Profile
  - Account
  - Subscription
  - Ad preferences
  - Data
  - About
```

## Tasks

| # | Task prompt | Correct path | Alternatives accepted | Measure |
|---|---|---|---|---|
| T1 | "Find the notes you took last week." | Home → Resurface · or · Library → Has notes | either | success rate |
| T2 | "Search for something you wrote down before." | AppBar → Search | — | success rate + time |
| T3 | "Turn off email notifications." | AppBar → Profile → Account | — | success rate |
| T4 | "Manage your subscription." | AppBar → Profile → Subscription | — | success rate |
| T5 | "Change what tracking data you share." | AppBar → Profile → Ad preferences | — | success rate |

Task wording rules:

- Goal-framed (what the user wants)
- Does NOT contain label words from the tree (no "manage your subscription" → path labeled "Subscription")
- Has exactly one correct answer (or explicitly allows alternatives)

## Pass criteria

| Metric | Threshold |
|---|---|
| **Success rate** (found correct) | ≥ 80% |
| **Directness** (no back-tracks) | ≥ 70% |
| **Time to find** (median) | ≤ 20 sec per task |

Any task failing thresholds → relabel or restructure before engineering.

## Sample

- **n:** 15–30
- **Recruitment:** user panel or existing user email list
- **Incentive:** $5–15 for 5–10 min (short study)

## Analysis

For each task:

- **Success rate** — % of users who found the correct destination
- **First-click accuracy** — % who picked the right parent first
- **Common wrong paths** — where did failers go instead?
- **Time** — median + p90

Heat-map the tree: frequency of clicks per node. Dead labels (never
clicked) are suspects for cutting or merging.

## Decisions flowing from results

- **Task fails threshold** → try new labels, re-test
- **Task passes with lots of wrong-first-clicks** → sibling label is
  cannibalizing; consider demoting
- **One node gets 0 traffic** → cut or merge
- **All tasks pass** → ship the IA

## Pre-registration

Record tasks + thresholds BEFORE running. Moving the goalposts after
seeing results invalidates the test.

---

**Tool:** [Maze / Optimal Workshop / Treejack]
**Study URL:** [link]
**Start:** [Y-M-D]
**End:** [Y-M-D]
**Owner:** [name]
