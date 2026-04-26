# Rule — No Fabrication

Never invent quotes, metrics, participants, or findings. Every claim
cites evidence or is labeled a hypothesis.

## What this rule prohibits

- Inventing user quotes to "illustrate" a point
- Rounding or inflating metrics ("about 40%" when you mean "2 of 5 users")
- Composite personas presented as individuals ("Sara is…" when Sara is
  a combination of 3 people)
- Claiming competitive parity or inferiority without capturing the
  evidence (screenshot, annotation, date)
- Assigning a severity rating based on feel rather than the rubric
- Citing "research shows" without a source link

## Labels you must use when you don't have evidence

| Label | Meaning |
|---|---|
| `[hypothesized]` | Inferred from logic, competitive analogs, or partial data. Not yet validated. |
| `[estimated]` | A number without a direct measurement. Show the method. |
| `[single-source]` | Finding from one source type. Pending triangulation. |
| `[anecdotal]` | Based on an individual case. Not generalizable yet. |
| `[composite]` | Persona or scenario built from multiple individuals. Never present as one person. |

Labels appear inline in every document that uses the labeled item,
not just the source doc.

## Persona fabrication

A persona named "Sara" is a commitment: there is a real cluster of
users whose behavior, pains, and JTBD match this card. If you made her
up from two competitor interviews and your own assumptions, she is
`[hypothesized]` until you run 5 interviews that confirm the pattern.

## Quote fabrication

If a quote isn't verbatim with a participant ID attached, it's not a
quote. Options:

- `[hypothesized]` bracket the quote: `[hyp] "I gave up at the second card."`
- Rewrite as a finding: "Multiple hypothesized users would abandon at the second card."
- Cut it.

## Metric fabrication

Never write a number without the method that produced it.

Bad: "Most users struggle with the home screen."
Bad: "About 40% of users drop off at step 3."

Good: "3 of 5 participants (P1, P2, P4) gave up at step 3."
Good: "40% of cold-start users abandon at home-view (analytics, 2026-04 cohort, n=2,140)."

## Competitive claims

"Competitor X does Y better" requires:

- Screenshot or live link captured on [date]
- Specific criterion (heuristic, metric, feature)
- Acknowledgment that their context differs from ours

## The cost of fabrication

Once fabricated data enters a deck or doc, it propagates:

- A competitor's execs quote your invented 40%
- Your team builds for a persona that doesn't exist
- A designer anchors on a quote that was never said
- Future research "confirms" patterns you invented

The cost of a single made-up number is years of misdirection.

## Self-check before publishing

For every number, quote, persona, competitor claim, severity score,
and recommendation in your document, ask:

- Can I link to the evidence?
- If I can't link, is it labeled?
- Am I presenting a cluster as an individual?
- Am I rounding in a direction that flatters my hypothesis?

If any answer is no / yes (respectively), fix it before publishing.
