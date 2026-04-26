---
name: teamz-ux-research
description: >
  Conducts rigorous UX research for any Teamz product — planning,
  discovery, usability testing, synthesis, and evidence-based
  recommendations. Merges the ux-researcher agent workflow (planning →
  implementation → impact) with the qualitative-research rigor layer
  (thematic coding, severity rubric, triangulation, reflexivity).
  Auto-activates on research, redesign, audit, journey, persona, and
  usability requests. Hands off implementation-ready specs to the
  teamz-design-bridge skill.
activation:
  keywords:
    [
      "ux research",
      "user research",
      "ui research",
      "research",
      "discovery",
      "interview",
      "usability test",
      "heuristic audit",
      "persona",
      "journey map",
      "jtbd",
      "job to be done",
      "funnel",
      "drop-off",
      "a/b test",
      "ab test",
      "tree test",
      "card sort",
      "thematic analysis",
      "severity",
      "affinity map",
      "synthesize insights",
      "research synthesis",
      "redesign",
      "audit",
      "e-e-a-t",
    ]
---

# Teamz UX Research

**Purpose** — you (Claude) are conducting user-experience research on a
Teamz Lab product and must deliver rigorous, actionable, unbiased
findings. This skill enforces method selection, synthesis discipline,
and evidence-based recommendations.

It does NOT replace `teamz-design-bridge` — it produces the *spec* that
feeds the bridge. Research here → design there → code.

## Three operating phases

Follow them in order. Never skip synthesis; never ship recommendations
without evidence.

### Phase 1 — Plan

1. State the research question(s) — one sentence each.
2. State your **biases and assumptions** (see `rules/reflexivity.md`).
3. Pick methods using [`methods/01-planning.md`](./methods/01-planning.md).
4. Size the sample (n=5 for formative usability, power calc for A/B).
5. Write the research plan using
   [`templates/research-plan.md`](./templates/research-plan.md).

### Phase 2 — Implement

Execute the chosen methods. One method per task:

- Moderated interview / usability test →
  [`methods/02-interviews.md`](./methods/02-interviews.md) +
  [`methods/03-usability-testing.md`](./methods/03-usability-testing.md)
- Heuristic audit →
  [`methods/08-competitive-audit.md`](./methods/08-competitive-audit.md)
- Analytics review → funnel, cohort, retention
- Accessibility audit →
  [`methods/09-accessibility.md`](./methods/09-accessibility.md)

Stay objective. Triangulate across ≥2 sources before concluding (see
[`rules/triangulation.md`](./rules/triangulation.md)).

### Phase 3 — Synthesize + recommend

1. Code observations into themes →
   [`methods/04-thematic-analysis.md`](./methods/04-thematic-analysis.md).
2. Affinity-map themes into root causes.
3. Score issues with Nielsen severity × frequency →
   [`methods/05-severity-rubric.md`](./methods/05-severity-rubric.md).
4. Produce the recommendation matrix →
   [`templates/recommendation-matrix.md`](./templates/recommendation-matrix.md).
5. Label every hypothesized finding `[hypothesized]` until validated
   (see [`rules/no-fabrication.md`](./rules/no-fabrication.md)).

## Hand-off to implementation

When recommendations are ready, hand off to `teamz-design-bridge`:

- Reference kit tokens (`ds.primary`, `OnColor`, `TeamzSection`), not hex.
- Map each recommendation to a file path and a PR scope.
- Every destructive/high-severity rec must name the evidence ID.

## Deliverables checklist

A research pass is complete only when ALL of these exist:

- [ ] Research plan (objectives, methods, sample, success criteria)
- [ ] Reflexivity note (declared biases)
- [ ] Observations log (raw, timestamped where possible)
- [ ] Thematic analysis + affinity map
- [ ] Severity-rated issue log (Nielsen 0–4 × frequency)
- [ ] Persona card(s) — hypothesized or validated (labelled)
- [ ] Journey map with moments of truth
- [ ] Competitive / heuristic audit (≥3 comparators)
- [ ] Recommendation matrix (evidence → rec → severity → effort → owner)
- [ ] Accessibility checklist (per
      [`methods/09-accessibility.md`](./methods/09-accessibility.md))
- [ ] A/B test plan for each rec with severity ≥ 2
- [ ] Success metrics (D1, D7, W2, W4 as applicable)

## Integration with other Teamz skills

- `teamz-design-bridge` — implementation partner. Hand off recs with
  file paths + kit-token references.
- `teamz-company-automation` scripts — use analytics, velocity, and ASO
  data (`aso-velocity.py`, GA4, Crashlytics) to triangulate qualitative
  findings quantitatively.

## Hard rules (never broken)

- **Never fabricate quotes, metrics, or persona details.** Hypothesize
  with the `[hypothesized]` label, then validate.
- **Never skip reflexivity.** Declared biases in every plan.
- **Never conclude from one source.** Triangulate (2 of: interview,
  analytics, competitive, heuristic, A/B).
- **Never propose recs without severity + effort.** Unscored recs get
  deprioritized silently and the right work doesn't happen.
- **Every rec cites the evidence it rests on** (obs ID, analytics event,
  citation). If you can't cite, you can't recommend.
- **Accessibility is part of the rec matrix, not a later pass.**

## Quick-start prompts the skill handles

- "Audit the home screen" → phases 1–3 on that surface
- "Plan a usability study for X" → phase 1 only, full plan output
- "Synthesize these 5 interview transcripts" → phase 3 only
- "Compare us to 5 competitors" → competitive audit method
- "Why is D7 retention flat?" → analytics + journey map, thematic
  synthesis, recommendation matrix

Default output format: Markdown with scannable headers, tables, and a
decision-ask at the end. Long-form reports get a TL;DR in the first
three lines.
