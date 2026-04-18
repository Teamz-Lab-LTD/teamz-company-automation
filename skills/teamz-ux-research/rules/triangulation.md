# Rule — Triangulation

No recommendation ships on a single source. Before recommending a
change, the finding must appear across **≥ 2 independent data sources**.

## Accepted sources

| Source | Type |
|---|---|
| Moderated interviews / usability sessions | Qualitative |
| Diary studies | Qualitative |
| Unmoderated tests (5-second, tree test, click test) | Mixed |
| Heuristic / competitive audit | Expert review |
| Analytics (funnel, cohort, retention) | Quantitative |
| A/B tests | Quantitative |
| Support tickets / reviews | Quantitative + qualitative |
| Crash / error logs | Quantitative |
| Accessibility audit | Expert + AT-user |

## Triangulation matrix

For each finding, record which sources support it:

| Finding | Interviews | Analytics | Heuristic | A/B | Support |
|---|---|---|---|---|---|
| "Home CTAs compete" | P1, P3 | bounce 40% at home | ✅ | — | — |
| "Recap unused cold" | — | 0% tap by D1 | ✅ | — | 2 tickets |

A finding with a single ✅ is a **hypothesis**, not a finding. Either
gather a second source or label the rec `[single-source, validate]`.

## When single-source is acceptable

Rare. Only when:

- Legal / compliance risk — fix immediately regardless of data density
- Catastrophic severity (4) with clear evidence
- Crashes, data loss, security

Document why triangulation was waived.

## Triangulating qualitative with quantitative

- Qualitative tells you WHY
- Quantitative tells you HOW MANY

Use together:

- Interview finds 2 users confused by label X → analytics shows click-
  through on that element is 3% (vs 30% on siblings) → **confirmed**
- Interview finds 2 users confused → analytics shows normal usage →
  **probably noise**, re-investigate
- Analytics shows drop-off at step 3 → interviews don't mention it →
  drop-off is real but cause unknown; add a targeted study

## The inverse problem

A pattern that appears across multiple sources of the SAME type (e.g.,
5 interviews) is not triangulated. It's one source with multiple
observations. You need cross-type confirmation.

## Checklist before publishing a rec

- [ ] Finding appears in ≥ 2 source types
- [ ] Sources are independent (didn't lead each other)
- [ ] Disconfirming evidence was actively searched, not just absent
- [ ] Any single-source finding is labeled `[single-source]`
