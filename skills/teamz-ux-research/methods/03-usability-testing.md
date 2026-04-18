# Usability Testing

Watching real people attempt real tasks on your product. The single
most cost-effective research method for catching design failures.

## When to run

- Before building a major redesign (validate the direction)
- After a prototype is clickable but before dev-complete
- When analytics show a drop-off you can't explain

## 5-user rule

5 users per segment catches ~85% of usability issues. Don't over-invest
in a single round; run iterations.

## Task design

A good task is:
- **Realistic** — something a user would actually do
- **Goal-framed** — "find X", not "click the blue button"
- **Complete** — has a clear success/failure state
- **Solo** — tests one thing, not five

Bad: "Find the settings menu."
Good: "You just realized you want email notifications off. Turn them off."

## Test protocol

1. **Warm-up (2 min)** — thank them, confirm consent, explain think-aloud
2. **First impression (5-sec test, optional)** — "What does this app do?"
3. **Tasks (15–20 min)** — 3–5 tasks, increasing in complexity
4. **Post-task questions** — "How easy was that, 1–7?", "What made it
   easy/hard?"
5. **SUS (3-item lite)** — ease, confidence, likelihood to use
6. **Wrap (3 min)** — open-ended feedback, thank, incentive

## Measures

Capture for each task:

- **Success** — did they complete it? (binary or 3-level: full / partial / fail)
- **Time on task** — seconds from start to success
- **Error count** — taps/clicks on wrong elements
- **Verbalized confusion count** — times they said "huh?" or equivalent
- **Self-rated ease** — 1–7 post-task
- **Recovery** — did they get unstuck on their own, or need help?

## Think-aloud protocol

Instruct: "Say whatever is going through your head as you do this.
Don't explain to me — just narrate your thoughts."

If they go quiet: "What are you thinking right now?" (not "what are
you doing?" — they will explain their actions).

## Severity scoring

After the session, rate each issue using
[`05-severity-rubric.md`](./05-severity-rubric.md).

## Red-team your own test

Before running:

- [ ] Can I answer the research question with the tasks I picked?
- [ ] Does any task leak the answer in its wording?
- [ ] Is the prototype/build stable enough that bugs won't derail?
- [ ] Have I pilot-tested with one internal person?
- [ ] Do I know what "success" looks like per task, in advance?

## Remote vs in-person

Default to **remote moderated**. Faster recruitment, more natural
context, mostly equivalent findings. Switch to in-person only when the
task involves physical objects, sensitive environments, or
accessibility tools we can't observe remotely.

## Unmoderated

Cheaper, faster, but loses the "why." Use for:
- Tree tests (IA validation)
- 5-second tests (first-impression)
- Click tests on specific screens
- Never for the first pass of a new flow — you need the why.

## Deliverables

- Per-session notes (timestamped observations)
- Task success matrix (users × tasks)
- Severity-ranked issue list
- Top 5 recommendations with evidence IDs
- 3–5 verbatim clips per major finding (if permitted)
