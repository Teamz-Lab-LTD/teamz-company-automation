# Severity Rubric (Nielsen 0–4)

Scores usability issues so you can prioritize. Unscored issues get
worked on by whoever shouts loudest — not necessarily the right thing.

## Severity scale

| Score | Label | Definition |
|---|---|---|
| **0** | Cosmetic | Unattractive but doesn't affect use. Fix if time. |
| **1** | Minor | Low-priority. Users notice, work around easily. |
| **2** | Serious | Important. Causes frustration, wasted time, support tickets. |
| **3** | Critical | Blocks the primary task or damages trust for many users. |
| **4** | Catastrophic | Data loss, security, accessibility-blocker, legal risk. |

## Frequency scale

| Score | Label | Definition |
|---|---|---|
| **1** | Rare | <10% of users encounter |
| **2** | Occasional | 10–40% |
| **3** | Common | 40–80% |
| **4** | Universal | >80% |

## Priority = severity × frequency

Issues with score ≥ 9 (e.g., severity 3 × frequency 3) must be fixed
before launch or reclassified with evidence.

## Issue log format

| # | Issue | Theme | Sev | Freq | Score | Evidence |
|---|---|---|---|---|---|---|
| I1 | Primary CTA not visible above fold | Hierarchy | 3 | 4 | 12 | P1, P3, P5 dropped at step 2 |
| I2 | Error state shows raw exception | Error-handling | 2 | 2 | 4 | P4 confused; analytics error_event_raw=17% |

## How to score severity

Ask, in order:

1. Does it cause data loss, security breach, or regulatory risk? → **4**
2. Does it block the primary task? Or permanently reduce trust? → **3**
3. Does it cause visible frustration or force a workaround? → **2**
4. Is it noticeable but ignorable? → **1**
5. Is it purely aesthetic? → **0**

## How to score frequency

Prefer data over estimates:

- Usability test hit-rate (N / total tested)
- Analytics event rate (users who hit the bug / MAU)
- Support ticket volume (tickets about X / total tickets × 100)

If you must estimate, say so and tag `[estimated]`. Update when data
arrives.

## Common scoring mistakes

- **Scoring the fix difficulty instead of the user impact.** Severity
  is about users, not about engineering.
- **Scoring once and never updating.** Re-score after analytics lands
  or after the next round.
- **Letting HIPPO adjust scores.** Highest-paid person's opinion
  doesn't change severity — data does.
- **Skipping frequency because "we only tested 5 users."** Estimate
  it, tag it, and move on. Don't skip.

## Output

Feed into
[`templates/recommendation-matrix.md`](../templates/recommendation-matrix.md).
Each rec cites the issue ID(s) it addresses.
