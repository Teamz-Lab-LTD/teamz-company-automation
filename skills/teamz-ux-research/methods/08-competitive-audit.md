# Competitive / Heuristic Audit

Structured comparison against 3–5 peers plus Nielsen's 10 heuristics.
Surfaces patterns without running a single user session.

## When to use

- Pre-redesign — learn the category conventions
- Before a new feature — is anyone else solving this, how?
- Post-launch sanity check — are we drifting from best practice?

## Pick competitors

3–5 apps. Mix of:

- **Direct competitors** — same users, same JTBD
- **Adjacent competitors** — same users, different job
- **Best-in-class outside category** — great pattern to steal

Example for NoteTube AI:
- Direct: Glasp, Snipd
- Adjacent: Readwise, Mem
- Outside: Anki (for spaced repetition pattern)

## Heuristic matrix

Score each app on each heuristic: ✅ strong, ⚠️ mixed, ❌ weak.

|  | Us | A | B | C | D |
|---|---|---|---|---|---|
| Visibility of system status | ⚠️ | ✅ | ✅ | ⚠️ | ❌ |
| Match system ↔ real world | ✅ | ✅ | ⚠️ | ✅ | ⚠️ |
| User control & freedom | ⚠️ | ✅ | ⚠️ | ⚠️ | ❌ |
| Consistency & standards | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| Error prevention | ❌ | ⚠️ | ✅ | ⚠️ | ❌ |
| Recognition > recall | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ |
| Flexibility & efficiency | ❌ | ⚠️ | ⚠️ | ✅ | ❌ |
| Aesthetic & minimalist | ✅ | ✅ | ⚠️ | ⚠️ | ❌ |
| Help with errors | ❌ | ✅ | ⚠️ | ⚠️ | ❌ |
| Help & docs | ❌ | ⚠️ | ✅ | ❌ | ❌ |

## Pattern extraction

After the matrix, list **3–5 patterns** that appear in ≥3 competitors.
These are the category conventions — deviating from them requires
explicit justification.

Example:
> Pattern 1 — Search lives in the top-right app bar (Glasp, Snipd,
> Readwise, Mem). Our hero-card placement deviates without evidence.

## Gap analysis

For each heuristic where YOU scored ⚠️ or ❌ and ≥3 competitors scored
✅: that's a gap to close.

For each heuristic where YOU scored ✅ and competitors didn't: that's
a potential differentiator to amplify.

## What to capture per competitor

- Cold-start screen (screenshot + annotation)
- Populated home state (≥ seeded library)
- Empty state messaging
- Onboarding flow (first 60 seconds)
- Paywall trigger + copy
- Settings IA
- Dark mode support
- Accessibility spot check (dynamic type, contrast)

## Before you finish

- [ ] 3–5 competitors analyzed
- [ ] All 10 heuristics scored for each
- [ ] Patterns extracted (≥3)
- [ ] Gaps listed (with severity)
- [ ] Differentiators listed
- [ ] Screenshots captured + annotated

Pass to synthesis ([`04-thematic-analysis.md`](./04-thematic-analysis.md))
as a data source alongside interviews and analytics.
