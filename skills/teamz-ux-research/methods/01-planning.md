# Research Planning

A plan exists before any observation. Skipping it is the #1 source of
wasted research effort.

## Output of this step

A filled [`templates/research-plan.md`](../templates/research-plan.md)
with:

1. Research questions (1–3, one sentence each)
2. Hypotheses (what you expect, so disconfirming evidence is visible)
3. Method(s) chosen with justification
4. Sample and recruitment
5. Success criteria (what "we know enough" looks like)
6. Declared biases (reflexivity)
7. Timeline + deliverables

## Method selection matrix

Pick by what you need to learn, not by what's familiar.

| Goal | Method | n | When to use |
|---|---|---|---|
| Are users finding the primary action? | Moderated usability | 5–8 | Before major layout changes |
| Does label X make sense? | Unmoderated tree test or 5-second test | 20–30 | Nav / IA decisions |
| Why is retention flat? | Analytics + diary study | all + 5 | Engagement problems |
| Which variant converts? | A/B test | power-calc | Reversible design choices |
| Who are our users? | Interviews (Jobs-to-Be-Done style) | 8–12 | Pre-persona |
| Is copy clear? | Cloze test or first-click test | 15–25 | Landing / empty-state copy |
| Is X accessible? | Heuristic + AT testing (VoiceOver, TalkBack) | n/a + 3 AT users | Pre-launch audit |
| Are we matching the market? | Competitive heuristic audit | 3–5 apps | Pre-redesign |

## Sample sizing rules of thumb

- **Formative usability (find problems):** 5 users per segment catches
  ~85% of issues (Nielsen). Diminishing returns after 8.
- **Card sort / tree test:** 15–30 for reasonable stability.
- **Survey:** n ≥ 100 for directional; n ≥ 384 for population-level
  95% CI ± 5%.
- **A/B test:** compute with baseline conversion, minimum detectable
  effect, α=0.05, power=0.80. Never run "until it feels significant."
- **Diary studies:** 5–8 participants, 5–7 days.

## Recruitment screener basics

- Match your target segment (behavior, not just demographics).
- Screen OUT professionals (designers, researchers) unless that's the
  target.
- Balance first-time vs experienced users intentionally.
- Incentive: ~$20–40 for 30 min, local fair-rate.

## Writing research questions

Bad: "What do users think of our app?"
Good: "What prevents first-time users from creating their first note
within their first session?"

Good research questions are:
- **Specific** — bounded to a surface, user, or behavior
- **Answerable** — the method you pick can actually answer them
- **Falsifiable** — you could be wrong, and that would show

## Before you move to implementation

- [ ] Questions written and reviewed
- [ ] Biases declared (see `../rules/reflexivity.md`)
- [ ] Sample sized with rationale
- [ ] Method chosen matches question
- [ ] Success criteria defined ("we'll know we have enough when…")
- [ ] Stakeholders aligned on the question (not just the method)
