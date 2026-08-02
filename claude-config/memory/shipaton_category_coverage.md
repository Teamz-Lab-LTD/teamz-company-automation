---
name: shipaton-category-coverage
description: "Locked rule for Shipaton 2026 — every app claims EVERY reachable category, verdicts come from /shipaton-check not from memory, and publishing gates all of it. Stops the per-session re-derivation that lost weeks."
metadata:
  node_type: memory
  type: feedback
---

**Rule (locked 2026-08-03, owner instruction):**

Every teamzlab app entered in Shipaton 2026 must claim **every category it can reach**. Coverage is
not optional and is not re-decided per session.

| Question | Answer |
|---|---|
| Which categories can this app enter? | Run `/shipaton-check <app-slug>`. Never answer from memory. |
| Where is the rulebook? | `claude-config/knowledge/Shipaton_2026_Category_Registry.md` |
| Where is per-app state? | `<app>/docs/shipaton/CATEGORY-TRACKER.md` |
| How many categories exist? | 20. Reachability is per-app — re-run the `OPEN IF` tests, never inherit another app's verdict. |
| Assumed budget | **$0** unless the owner says otherwise in that session. |

**Three things that are true of every app and get forgotten anyway:**

1. **Publishing gates everything.** Every category except Next Gen requires a *fully published* store
   listing. Category strategy while the app is unpublished is motion, not progress — lead the report
   with the publishing blocker, always.
2. **Four categories cost one paragraph each** after the app ships (HAMM, Design, Peace, Grand
   Prize). Never ship without claiming all four. That is the cheapest money on the board.
3. **The sponsor categories get forgotten** because they were announced after the main list.
   OneSignal pays **$25k** for first — second largest prize in the whole event — for about one day
   of SDK work plus one campaign. Layers pays $15k for installing an SDK and describing one
   experiment.

**"Force to win" is not encodable — this is what is enforced instead:** `/shipaton-check` fails loudly
when a reachable category sits at `NOT STARTED`, and refuses to declare a category closed without
quoting the failed `OPEN IF` test and its evidence. A guess is not a verdict.

**Why this rule exists:** the owner re-derived the category list, the eligibility rules and the
prize amounts in several separate sessions. Each pass reached different conclusions, under-counted
the sponsor categories, mis-priced OneSignal by $10k, and twice declared a reachable category
impossible. Nine documented traps live in registry §4 — read them before answering anything.

Related: [[aso-cadence]] (same pattern: locked rule + registry + command, so the question is
answered once instead of re-derived every session).
