# Personas (JTBD-flavored)

Personas turn statistical users into mental models you can design for.
Done wrong, they're demographic fluff. Done right, they anchor every
decision to a real job.

## Format (one card per persona)

```
Name:        [Memorable alliterative name]
Segment:     [behavioral, not demographic — "YouTube learners", not "millennials"]

JTBD:        "When [situation], I want [motivation], so I can [outcome]."

Behaviors:   [3–5 observable behaviors — what they do, not who they are]
Pains:       [3 specific frictions, in their own words if possible]
Gains:       [3 outcomes that would make them say "finally"]

Quote:       "[One verbatim or [hypothesized] quote that makes the JTBD concrete]"

Context:     [device, time-of-day, social context when using the product]
Frequency:   [how often this persona shows up — % of base, if known]

Evidence:    [interview IDs, analytics segments, or [hypothesized] label]
```

## The JTBD sentence

This is the heart of the card. Write it in the **form**:

> "When [situation], I want to [motivation], so I can [expected outcome]."

Not: "Sara is a student who likes to take notes." (demographic fluff)

Yes: "When I study from a YouTube lecture, I want searchable
timestamped notes, so I can find concepts during exam week without
rewatching."

## Validate vs. hypothesize

Every persona is one of:

- **Validated** — built from ≥5 interviews + analytics segment match.
  No label needed.
- **Hypothesized** — built from logical inference, competitive analysis,
  or partial data. Must be labeled `[hypothesized]` in every card and
  every document that references it.

Demoting a hypothesized persona to a validated one requires: 5+
interviews showing the JTBD pattern AND analytics segment showing the
behavioral signature.

## How many personas

2–4. Five or more means you haven't clustered hard enough. One
single persona is often fine for v1 products.

## Anti-personas

Optional but useful: who is NOT the target. Prevents feature creep.

```
Anti-persona: [Name]
Not for us because: [specific reason they don't match the JTBD]
```

## Banned persona fields

- Age (unless it's directly behavioral — "Gen Z" for a TikTok-first
  product)
- Gender (almost never product-relevant)
- Favorite foods, pets, weekend activities — fluff
- Psychographics without behavioral grounding

## Using personas in design

Every design decision should answer: "Does this help [persona] do
[JTBD] better?"

If the answer is no, cut the feature or add a second persona that
justifies it.

## Template

See [`../templates/persona-card.md`](../templates/persona-card.md).
