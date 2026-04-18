# A/B Test Plan — [experiment name]

> Every recommendation with severity ≥ 2 gets an A/B plan before dev
> starts. Running unscoped experiments wastes data and trust.

## Hypothesis

**H:** [Change X will move metric Y by Z% because [mechanism].]

**Example:** "Reordering the home screen (resurface → hero) will
increase D1 retention in cold-start users by ≥ 8% relative because it
replaces broken-promise cards with a single usable action."

## Null safety

**H0 (null):** [what would be unacceptable]

**Example:** "Ask search usage among ≥ 5-note users does NOT drop by
more than 10%."

## Design

**Type:** [A/B · A/B/n · multivariate · holdback · switchback]

**Arms:**
- **Control:** [current behavior]
- **Treatment:** [new behavior]
- [Treatment 2 if A/B/n…]

**Randomization unit:** [user · session · device · tenant]

**Assignment:** [server-side flag / RemoteConfig / build variant]

## Metrics

### Primary (one, overpowered)

- **Metric:** [e.g., "D1 return rate for cold-start cohort"]
- **Baseline:** [current rate]
- **MDE (minimum detectable effect):** [relative %]
- **Direction:** [increase / decrease]

### Secondary (2–4, descriptive)

- [Metric 2 — e.g., "Time to first note"]
- [Metric 3]
- [Metric 4]

### Guardrails (must not degrade)

- [Guardrail 1 — e.g., "Ask search usage among eligible users"]
- [Guardrail 2]
- [Guardrail 3 — always include: crash-free sessions, app-start time]

## Sample size

```
Baseline conversion:  X%
MDE (relative):       Y%
α (two-sided):        0.05
Power (1-β):          0.80
Arms:                 2
Required n per arm:   [calculated]
```

Tool: [G*Power · Evan Miller · statsig · in-house calculator]

## Duration

- **Estimated daily traffic per arm:** [n/day]
- **Days to sample size:** [calculated]
- **Minimum run:** 7 days (captures weekly cycle)
- **Maximum run:** [cap — beyond this, stop whether or not significant]

## Segmentation

Analyze primary by:

- Cohort (cold, seeded, active, engaged)
- Platform (iOS, Android, web)
- Region (if ≥ 5% non-primary)
- Network quality (if relevant)

Segmentation is for understanding, not for stopping the test early.

## Pre-registration

Before flipping the flag, record in `automation_data/experiments/`:

- Hypothesis (fixed)
- Primary metric + MDE (fixed)
- Sample size (fixed)
- Stop rule (fixed — no HARKing)

Changes after flip = invalidate the test.

## Analysis

- Report primary + secondaries + guardrails
- Cite confidence interval, not just p-value
- Interpret practical significance (is the effect size worth it?)
- Call out interactions with other live experiments

## Decision rule

- **Ship treatment** if: primary significant + positive + no guardrail breach
- **Kill treatment** if: primary flat/negative OR guardrail breached
- **Extend** if: underpowered, close-to-significant, and within max-run

## Rollout plan (if shipping)

1. Ship to [10%] for [3 days] — watch crashes, support
2. Ramp to [50%] — re-check guardrails
3. 100% — archive experiment, delete dead flag in next release

## Post-mortem

After the test concludes (regardless of outcome):

- What we learned
- What we'd design differently next time
- Follow-up experiments triggered

---

**Owner:** [name]
**Flag name:** [code-referenceable key]
**Start date:** [Y-M-D]
**End date:** [Y-M-D]
**Decision:** [Ship / Kill / Extend / Inconclusive]
