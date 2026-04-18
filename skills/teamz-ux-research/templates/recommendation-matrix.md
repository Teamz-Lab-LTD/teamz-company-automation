# Recommendation Matrix — [surface / project]

> Each recommendation is an atomic change. One row per rec. Sort by
> priority descending before handing off to engineering.

## Legend

- **Severity:** 0 cosmetic · 1 minor · 2 serious · 3 critical · 4 catastrophic
- **Effort:** S ≤ 1 dev-day · M 1–3 days · L 3–7 days · XL > 1 week
- **Priority:** P0 ship now · P1 this sprint · P2 next sprint · P3 backlog
- **State:** all · cold · seeded · active · engaged

## Matrix

| # | Recommendation | Evidence (issue ID / obs / data) | Severity | Frequency | Score (S×F) | Effort | Priority | State | Files | Owner |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | [one-sentence change] | I1, O-03, P2 | 3 | 4 | 12 | S | P0 | all | `path/to/file.dart` | [name] |
| R2 | … | … | 2 | 3 | 6 | M | P1 | cold | … | … |

## Per-recommendation detail

### R1 — [title]

**Change:** [what exactly changes, at a code-referenceable level]

**Evidence:**
- [Issue ID / Observation / Quote / Analytics event]
- […]

**Implementation:**
- File: `[path]:[line]` — [what to change]
- Token(s): `[ds.primary]`, `[OnColor]`, etc. — never raw hex
- Depends on: [other rec IDs or nothing]

**Accessibility:**
- Contrast pair: [bg → fg]
- Focus order: [if changed]
- Semantics label: [if new interactive element]

**Validation:**
- A/B test plan ID: [link] (required if severity ≥ 2)
- Success metric: [leading indicator]
- Guardrail metric: [what must NOT drop]

**Rollback:** [how to revert if validation fails]

---

### R2 — [title]

[…same structure…]

---

## Prioritization summary

- **P0 (ship in PR1):** R1, R4 (score ≥ 9 or blocking a launch)
- **P1 (next sprint):** R2, R5
- **P2 (when the data lands):** R3
- **P3 (backlog):** R6

## Handoff checklist

- [ ] Every rec has severity AND frequency
- [ ] Every rec cites evidence (no unsourced opinions)
- [ ] Every sev ≥ 2 rec has an A/B plan
- [ ] Every UI rec uses kit tokens / `OnColor` / kit widgets
- [ ] Every rec has a file path and owner
- [ ] Accessibility impact checked per rec

---

**Created:** [Y-M-D]
**Last updated:** [Y-M-D]
**Source research:** [link to plan]
