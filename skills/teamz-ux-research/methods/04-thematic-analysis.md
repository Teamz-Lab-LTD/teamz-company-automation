# Thematic Analysis + Affinity Mapping

Turn raw observations into themes, themes into root causes, root causes
into recommendations. Skip this step and you produce opinions instead
of findings.

## Process (Braun & Clarke, condensed)

1. **Familiarize** — read all notes/transcripts once without coding
2. **Generate initial codes** — tag every observation with a short code
3. **Search for themes** — group codes that fit together
4. **Review themes** — do they hold against the raw data?
5. **Define + name themes** — one sentence per theme
6. **Produce the report** — themes + exemplar quotes + implication

## Coding rubric

Every observation gets:

| Field | Example |
|---|---|
| ID | `O-03` |
| Source | `P2 interview 14:20` or `analytics funnel step 3` |
| Raw observation | "I tapped the big yellow card, expecting search" |
| Code | `affordance-mismatch` |
| Theme | `Hierarchy` |

Codes should be short, active, and descriptive. `affordance-mismatch`
not `user-confused`.

## Affinity map template

```
┌────────────────────────── Root cause A ──────────────────────────┐
│                                                                   │
│   Theme 1            Theme 2           Theme 3                   │
│   ───────            ───────           ───────                   │
│   Code a1            Code b1           Code c1                   │
│   Code a2            Code b2           Code c2                   │
│   Obs O-03, O-07     Obs O-12          Obs O-04, O-19            │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

Aim for 2–5 root causes. More means you haven't abstracted enough;
fewer means you're overgeneralizing.

## Saturation test

You have enough data when the last 2 sessions/observations produce no
new codes. If they do, add more participants.

## Inter-coder reliability (for published research / high-stakes work)

Have a second person code 20% of the data blind. Calculate Cohen's
kappa. κ ≥ 0.7 is acceptable; below that, refine the codebook and re-code.

For internal product decisions, solo coding with a sanity-check
review is usually sufficient.

## Common mistakes

- **Coding your hypothesis** — you see what you want to see. Have a
  second person spot-check.
- **Over-generalizing from one participant** — a single vivid quote
  feels like truth. It's not. N ≥ 2 before it becomes a theme.
- **Letting severity drive themes** — severity is scored in the next
  step, not here. A low-severity issue can still be a real theme.
- **Collapsing themes too early** — start with more codes, fewer
  themes, not the reverse.

## Output

Hand off to [`05-severity-rubric.md`](./05-severity-rubric.md):

- Theme list with one-line definitions
- Observation count per theme (frequency signal)
- Exemplar quotes/observations per theme
- Root cause map (2–5 clusters)
