# Rule — Reflexivity

Every research plan declares the researcher's biases before data is
collected. Biases don't disappear when unacknowledged — they just
disappear from your awareness.

## What to declare

At minimum, write 3–5 sentences covering:

1. **Prior beliefs** — what do you already expect to find?
2. **Product relationship** — are you on the team that built this?
   Incentivized by a particular outcome?
3. **Competitor familiarity** — which patterns shape your expectations?
4. **Data gaps** — what don't you know, and what are you guessing
   about?
5. **Persona proximity** — are you a target user or far from one?
   Familiarity can blind you to obvious friction.

## Where it lives

Section 3 of
[`templates/research-plan.md`](../templates/research-plan.md). Visible
in every synthesis doc you produce from the plan.

## Revisit during synthesis

After coding and before recommending, re-read your biases. Ask:

- Did I code data that contradicted my expectations, or skip past it?
- Did I recruit participants who resemble me?
- Did I score severity based on my own friction threshold, not the
  users'?

If any answer is "yes", triangulate that finding with an independent
source before it ships as a recommendation.

## Why this matters

The most common research failure mode is **confirmation dressed up as
evidence** — a designer "tests" their own design, watches 5 users
who mostly succeed (because the designer explained the task), and
concludes the design is good.

Declaring bias upfront doesn't prevent this, but it makes the failure
visible in the final report. A reviewer can say "your bias note said X,
and your conclusion is X — where's the disconfirming data?"

## Example

> **Reflexivity note for home screen audit:**
>
> 1. I believe the home has too many competing CTAs. Evidence that
>    would disprove me: high tap-rate and low bounce on all three cards.
> 2. I'm on the team that built this — motivation to find fixable
>    problems, not "it's fine."
> 3. Readwise's home shapes my expectations. Their user base is
>    different and the pattern may not transfer.
> 4. No usability sessions run yet — all severity scores are estimated
>    from heuristic review alone.
> 5. I watch 8 hr/week educational YouTube — closer to the power user
>    than the typical user. May underweight onboarding friction.
