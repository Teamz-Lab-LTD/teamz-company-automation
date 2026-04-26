# Interviews (generative + JTBD)

Use when you need to understand *why* users do what they do, not just
*what* they do. Analytics tells you what; interviews tell you why.

## Structure of a 30-minute interview

| Min | Phase | Purpose |
|---|---|---|
| 0–3 | Warm-up + consent | Relax participant; get recording consent |
| 3–6 | Context | Their life, their day, where your product might fit |
| 6–20 | Core questions | Task recall, behavior mapping, JTBD probes |
| 20–27 | Scenario | Optional: walk through a task or recent event |
| 27–30 | Wrap | "One thing you wish…", thank, incentive |

## JTBD interview protocol (condensed)

Anchor every question on a specific past event, not hypothetical
preference.

1. "Tell me about the last time you [did the job]."
2. "When did you first realize you needed to do this?"
3. "What were you using before?" / "What did you try first?"
4. "What made you pick [current solution]?"
5. "What almost made you give up?"
6. "If [current solution] disappeared tomorrow, what would you do?"

The last question reveals the real JTBD — the function, not the feature.

## Banned questions

- "Would you use a feature that…?" (users can't predict own behavior)
- "What do you think about…?" (yields opinions, not evidence)
- "Do you like X or Y better?" (leading, binary, shallow)
- "How often do you…?" (recall bias — ask about the last time instead)

## Prompts that work

- "Walk me through that."
- "What did you do next?"
- "What were you thinking?"
- "Was that easy or hard? What made it so?"
- "Take me back to the moment you decided…"

## Observation vs. inference

Keep observation and inference in separate columns in your notes.
You will over-infer when tired.

```
TIME   OBSERVATION (what they said/did)         INFERENCE (your read)
02:14  "I just gave up and closed it."          Frustration with load time?
```

## Deliverables from interviews

- Verbatim quotes (exact, attributed by participant ID)
- Observation log (timestamped)
- Inference log (separate column)
- Feed → `04-thematic-analysis.md` for coding

## Do not

- Share your own opinion mid-interview ("yeah that's a bug")
- Fix their problems live ("oh, you can actually do that by…")
- Lead ("don't you think…", "wouldn't it be better if…")
- Summarize back incorrectly (paraphrase to check; don't twist)

## Consent boilerplate

> "I'm recording this so I don't have to take notes. It's only used
> inside our team. You can stop the recording or leave at any time,
> and you'll still receive the incentive. Is that OK?"

Get explicit verbal yes before proceeding.
