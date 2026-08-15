# Shipaton #BuildInPublic — Core Posting Engine (generic, all apps)

> **What this file is.** The canonical, app-agnostic mechanism for running a #BuildInPublic
> journey under this owner's real constraints: no video, no face on camera, personal account,
> ~45 min/week, multiple apps shipping in the same window.
>
> **Precedence:** where this file and `Shipaton_2026_Knowledge_Base.md` §12.5 conflict, **this
> file wins** (corrections dated below). §12.5's voice rules, visual rules, and prompt library
> are **inherited by reference** — do not duplicate them, do not skip them.
>
> **How to use it:** any app entering #BuildInPublic derives its own
> `docs/shipaton/BUILDINPUBLIC-PLAN.md` from §11 of this file. Worked example:
> `interview-boss-plus/docs/shipaton/BUILDINPUBLIC-PLAN.md`.
>
> **Built:** 2026-08-15. Sources: live fetch of https://revenuecat-shipaton-2026.devpost.com/rules
> (2026-08-15) · 2024/2025 winner interviews (RevenueCat blog) ·
> `Shipaton_2026_Category_Registry.md` (built 2026-08-03).
>
> **INSTRUCTION TO ANY AI READING THIS FILE:** you do not need any other briefing. When the
> owner asks for build-in-public work on any app: (1) follow the model/effort routing in §10a —
> do not run post generation on a frontier-tier model; (2) derive the app plan via §11 including
> the ready-to-paste post pack and the single-prompt Codex image set; (3) never fabricate — the
> `[FILL]` system in §11a exists so pre-written posts stay honest. Voice/visual rules: KB §12.5.

---

## 1. Verbatim judging criteria (live-fetched 2026-08-15 — do not paraphrase)

Three criteria, **no published weights**:

1. **Sharing your story** — how creatively and consistently the journey was shared publicly
2. **Engagement** — ideas and feedback from the community incorporated into the app
3. **Lessons learned** — what the builder learned and shared along the way

Facts that shape everything below:

- **Audience size explicitly does NOT matter** (stated in the rules).
- Tie-break convention on Devpost: criteria are applied **in listed order** — story first.
- Prizes: **1st $30,000 + Times Square billboard · 2nd $20,000 · 3rd $10,000.**
- Engagement Period = Submission Period: **Jul 31 – Sep 30, 2026**. Posts made **before**
  submitting count — the form collects links at the end. Posting early is free evidence.
- Posts count when tagged **`#BuildInPublic #Shipaton`** and linked on the submission form.

**Structural insight (why this lane cannot be backfilled):** criteria 2 and 3 score **events in
the world** — did strangers suggest things, did the app change because of it. No writing model,
no polish, no last-week sprint can manufacture that. The loop in §4 needs weeks of lead time.
Start the moment the app has anything to show.

## 2. What past winners actually did (corrections to KB §12.5, dated 2026-08-15)

| Winner | Year/Place | What they did |
|---|---|---|
| Gurwi | 2025 · 1st | One video hit ~200k views; video-led throughout |
| Echo Reminder | 2025 · 2nd | Ran 4 video platforms simultaneously |
| **Tomo Japan** | 2025 · **3rd** | Daily posts incl. **long-form written posts judges explicitly praised** |
| Rudrank Riyam | 2024 · 1st | Rebuilt a YouTube channel; arc = audible improvement in his own skill |

Two dated corrections to §12.5:

- **(a)** §12.5 implies screenshot-first is the winning default. **Wrong vs evidence** — all four
  were video-led. Video is the meta.
- **(b)** But video is **not required by the rules**, and Tomo proves **text + images can place**.
  Honest ceiling for a no-video run: **2nd–3rd ($10–20k)**. Worth 45 min/week; not worth
  pretending 1st is likely.

## 3. The constraint set this engine is built for

- No video. No face. No voice recordings of the owner.
- Personal account (a company page cannot say "I learned" — criterion 3 dies in corporate voice).
- ~45 minutes/week total.
- Several apps publishing inside the same window (see §8).
- LinkedIn excluded (owner cannot expose presence there — overrides §12.5's LinkedIn cross-post
  instruction for this owner).

## 4. THE CORE MECHANISM — the feedback loop

Criteria 2 and 3 are events, not prose. Only one machine produces them:

```
post → someone replies with a suggestion → ship it → post before/after with both screenshots
```

Every completed loop is one unit of hard evidence. Everything else in this file exists to feed
this loop.

**An empty timeline generates zero replies.** Seed every post where people already answer:

| Venue | Cadence | Rule |
|---|---|---|
| **Shipaton Discord** `#post-engagement-boost`, `#launch-day` | every post | fellow builders reply; Rudrank's stated advice: help competitors, they help back |
| `r/FlutterDev`, `r/SideProject` | ≤1×/week | promo-hostile — lead with the technique/lesson, app second |
| IndieHackers | ≤1×/week | long-form tolerated; Tomo-style written posts live here |
| **X** | 3×/week | the surface judges read; submission-form links point here |

**Hard rules:**

- Every reply containing a suggestion goes into the journey log **immediately, with link** (§9).
  Those links are the criterion-2 evidence on the form.
- Ship **≥3 community suggestions** per entered app before Sep 30, each with a linked
  before/after post. Below 3 → the criterion-2 story is thin; say so at submission, never pad.
- Ask for input explicitly in posts ("which of these two?", "what would you cut?") — questions
  convert lurkers to repliers far better than announcements.

## 5. The data-spine pattern (generic)

One repeating post format carries the whole journey: **a number the app itself produces about
its own user, posted weekly as an image, week 1 vs week N.**

Derivation question — always step 1 for any app: **"what measurable thing does this app generate
about its user's life?"**

| App type | Spine candidate |
|---|---|
| Skill trainer (e.g. InterviewBoss Plus) | the app's own score of the owner: fillers/min · pace · fluency, week 1 vs now |
| Habit/health app | streak + tracked-metric trend of the owner using it |
| Productivity tool | owner's real usage delta (time saved, items processed) |
| Game | owner's own progression/difficulty curve |

Why it wins under the no-video constraint:

- It is Rudrank's winning arc (audible self-improvement) **rendered as a chart instead of a face**.
- Every post demos the product while telling a story.
- Criterion 3 answers itself: *building in public improved the app, and the app improved me.*
- Uncopyable — competitors don't have your scorer/data.
- ~60 seconds/week. No camera. No editing.

**Post the week-1 baseline even though the number is bad. The bad number IS the asset — without
it there is no arc.** Never improve the baseline retroactively; never smooth the curve.

## 6. No-video playbook

- Real screenshots default; generated images only for ceremony moments; never fake evidence —
  §12.5 rules 1–3 inherited verbatim.
- Formats that replace video: spine image (§5) · before/after screenshot pairs (§4) ·
  annotated bug screenshots · hand-drawn sketch photos · short text threads (Tomo pattern).
- 1–3 sentences per X post + one real image + `#BuildInPublic #Shipaton`. Long-form goes to
  IndieHackers/Reddit, linked from X.
- No face, no voice, ever — this is a constraint, not an apology. Do not reference its absence
  in posts.

## 7. Cadence under time constraint (supersedes §12.5's "4–5×/week")

- **Floor: 3 posts/week on X** — 1 spine post + 2 others. Frequency is not a judged criterion;
  consistency of the arc is.
- Budget: **~45 min/week** (batch-generate weekly via §10, post from phone).
- **Drop rule:** below 2 posts/week for 2 consecutive weeks → withdraw the lane honestly rather
  than limp. A visibly dead journey scores worse than no entry.

### 7a. Prepare in parallel, publish sequentially (BINDING)

The pack is written weeks ahead; it is **not** posted weeks ahead.

**Publishing is sequential. Minimum ~24h between posts; target every 2–3 days.** Reasons:

1. Criterion 1 judges consistency *over time*. A burst then silence reads as a campaign, not a
   journey — and judges see timestamps.
2. Your own posts cannibalize each other's reach on a small account.
3. **The loop needs the gaps.** `post → reply → ship → before/after` requires time for a reply
   to actually arrive. Posting everything at once removes the window feedback lives in, which
   is criteria 2 and 3 — the two that decide placement.
4. Clustered timestamps read as backfilled; spread timestamps are free proof the journey was real.

**Parallel is correct for everything except the publish button:**

- generate the whole Codex ceremony image set in ONE run, up front (§11 step 6)
- capture screenshots when the moment happens, never when the post is due — a week-1 baseline
  number cannot be recreated in week 3
- one post → multiple venues the same day (X → Discord → weekly Reddit/IndieHackers) is
  amplification of one post, not two posts
- replying to your own post the same day is depth on one post, not a second post — and it is the
  cheapest way to invite the replies the loop needs
- other apps' ceremony posts (§8) run on their own timeline

Rule of thumb: **build ahead, release on a drip.**

## 8. Multi-app allocation rule

When several apps ship in the same window:

- **ONE personal account carries everything.** Multiple accounts = divided identity, zero
  compounding, and the owner's time doesn't exist for it.
- **Exactly ONE app gets the full engine** (spine + loop + calendar) — that app is the
  #BuildInPublic entry. Choose the app where the spine metric is strongest (§5).
- Every **other** app gets ceremony posts only: launch day + one milestone + submission day.
  Those posts still tag `#BuildInPublic #Shipaton` (they cost nothing and feed the account),
  but no spine, no weekly commitment.
- Rationale: the criteria reward **depth of one journey**, not breadth. Five half-journeys score
  worse than one real one plus four launches.
- Cross-pollinate honestly: "app 4 of 5 this Shipaton" is itself a compelling story line for the
  main journey.

### 8a. How multiple apps share ONE timeline

**Interleave on a single timeline — never run parallel tracks.**

| Pattern | Verdict |
|---|---|
| App A on days 1,3,5 **and** App B on days 1,3,5 (two tracks, 6 posts/wk) | **WRONG.** Two posts per day breaks §7a spacing, the posts cannibalize each other's reach, time cost doubles, and the profile reads as two products with no single story |
| One timeline, apps interleaved, ~3 posts/wk total | **CORRECT** — but the split must be lopsided, see below |

**The ratio is what matters, not the interleaving.** Alternating evenly still dilutes the
journey. Across the whole window:

- **Entry app:** every spine post, every feedback loop, every story post — roughly **80%** of all
  posts.
- **Every other app combined:** ceremony posts only (launch · one real milestone · submission) —
  roughly **3–5 posts TOTAL across all of them**, not per app, not per week.

Shape of a real timeline: `A A A A B-launch A A A C-launch A A A A B-milestone A A A A submission`.

Why: criteria 2 and 3 measure the **depth of one journey**. Five shallow journeys score worse
than one real journey plus four launch announcements — and five feedback loops cannot be run
inside a 45-min/week budget.

**Hard rules:**

- Never two posts on the same day. If another app's launch collides with a queued entry-app
  post, push the entry-app post back a day — launches are date-locked, story posts are not.
- **Do not enter #BuildInPublic twice with two apps.** Multiple submissions are legal (rules:
  each must be "unique and substantially different"), but splitting post evidence across two
  entries makes both weaker. Other categories can and should be claimed per app.
- Frame the other apps' posts as part of the same story ("app 2 of 5 I'm shipping this
  Shipaton") — turns dilution into a credibility line at zero cost.

## 9. Capture protocol (feeds all generation)

Fabrication kills the entry (§12.5 hard rule: never invent progress, numbers, or struggles).
Generation without input becomes fabrication. So:

- Per app: `docs/shipaton/JOURNEY-LOG.md`, one line per working day:

```
2026-08-15 | wired real STT, found my own docs had overclaimed it | -
2026-08-18 | @someone suggested a countdown to interview date | https://x.com/...
```

- **The 70/30 rule:** ~70% of material (what was built, bugs, commits) is derivable from git and
  session history unattended. **Decisions, feelings, and other people's reactions are the 30%
  only the human can log** — that 30% is where criteria 2 and 3 live. 30 seconds/day.
- Suggestions get logged with their link **the moment they arrive** (see §4).
- At submission, the log + post links assemble into the Devpost narrative (§12.5 prompt library).

## 10. Generation prompts (updated — reference this file, not only §12.5)

**Weekly batch (the default, replaces daily prompting):**
> Read `Shipaton_BuildInPublic_Core_Engine.md` + KB §12.5 + this app's
> `docs/shipaton/BUILDINPUBLIC-PLAN.md`. Here is this week's journey log: [paste].
> Write my 3 X posts for the week: 1 spine post + 2 others. Real screenshot suggestion for
> each. No invented facts. Also state which venue each gets seeded to (§4 table).

**Before/after (highest value — one per completed loop):**
> Per Core Engine §4: [person] suggested [X] (link), I shipped it. Write the X post showing the
> suggestion→shipped loop explicitly, with both screenshots named.

**Baseline post (week 1, once per journey):**
> Per Core Engine §5: here is my real week-1 number: [paste]. Write the baseline post — honest
> about it being bad, framing the arc that starts here.

All other prompts (origin, launch-day, submission story, demo script): use §12.5's library
unchanged, adding "read Core Engine first" to each.

### 10a. Model + effort routing (BINDING for any AI running this engine)

Token-efficiency rule: the criteria score events, not prose quality. Never spend frontier-model
tokens on tasks whose shape already exists in this file.

| Task | Claude model | Effort | Why |
|---|---|---|---|
| Weekly post generation from an existing plan + journey log | **Sonnet** | **medium** | Pure pattern-fill; the spec exists; a bigger model adds polish that HURTS criterion 1 |
| Per-app plan derivation (§11) from this file + git log | **Sonnet** | **medium** | Template exists; worked examples exist |
| Adapting the Codex image mega-prompt to a new app (§11 step 6) | **Sonnet** | **low** | Motif/palette substitution only |
| New strategy decision (lane change, ceiling reassessment, criteria re-fetch) | **Opus** | **high** | Judged-criterion direction; wrong answer ships silently |
| Final Devpost #BuildInPublic narrative (submission week) | **Opus** | **xhigh** | One-shot, highest-stakes text of the campaign |
| NEVER | Fable / frontier tier | — | 2× cost, zero movement on criteria 2–3, over-polish risk on criterion 1; its docs warn prescriptive specs (this file is one) degrade its output |

Codex side (image generation only): agent model `gpt-5.1-codex-max` or newest Codex model
available, reasoning effort **high** (multi-image consistency task), image model `gpt-image-1`
or the exposed image tool. Codex generates CEREMONY images only — never evidence (§6, §12).

## 11. Per-app derivation template (produces `docs/shipaton/BUILDINPUBLIC-PLAN.md`)

Checklist — an agent with this file + the app's git log can complete it:

1. **Spine metric** (§5 question). If the app produces no number about its user → this app is a
   ceremony-posts app (§8), not the main journey. Stop here.
2. **Post bank:** mine git history + docs for 5–7 REAL story items (bugs found, overclaims
   corrected, design pivots, ethical decisions, localization choices). Each must be verifiable
   in a commit. Lead with the most self-critical one — publicly catching your own mistake is
   rare and hits criterion 3 hardest.
3. **Calendar:** weeks remaining until Sep 30 → one row per week: spine post + 2 others, with
   launch day, first-loop target (§4), and closing week-1-vs-week-N post placed.
4. **Open items:** account handle, store-listing blockers, anything owner-only.
5. **Ready-to-paste post pack** (`docs/shipaton/POSTS-READY.md`): every calendar post fully
   written, copy-paste ready with hashtags, one image assignment per post
   (`REAL: <exact screenshot>` default, `IMG-xx` ceremony only). See §11a for the honesty
   mechanism. Include a Swap Bank of 3–5 evergreen real-story posts for when conditional
   events don't happen.
6. **Single-prompt Codex image set:** ONE paste-able mega-prompt generating all ceremony images
   in one run — global style block (app's own palette + 3–4 visual motifs), one scene per
   ceremony moment (origin · launch · milestone · submission · thank-you · concept tease),
   filenames, 16:9, no-text rule, self-check pass. Scenes must be metaphors from the app's own
   world, not stock clichés (no generic rockets/sprouts). Include the Codex model/effort header
   from §10a.
7. Header of the produced file points back to this Core Engine — app file adds only what is
   app-specific, never re-states the mechanism.

Worked examples (structure reference): `interview-boss-plus/docs/shipaton/BUILDINPUBLIC-PLAN.md`
(plan) and `interview-boss-plus/docs/shipaton/POSTS-READY.md` (post pack + Codex mega-prompt).

### 11a. The `[FILL]` system (how pre-written posts stay honest)

Posts for future weeks are pre-written in full, with `[FILL: …]` slots for anything that must
come from reality (numbers, links, names, events). Binding rules:

- A post containing an unfilled `[FILL]` is NEVER posted.
- If the event behind a conditional post doesn't happen, swap in a Swap Bank post — never
  invent the event.
- Fills come only from: the app's real output, real replies (with links), real store/console
  screenshots, real git history.

This is the token-efficiency core: the expensive thinking happens once at derivation time
(Sonnet, medium); weekly effort collapses to filling slots — no model call needed at all in a
normal week.

## 12. Non-negotiables

- Personal account, never the company page.
- **Never** fabricate a metric, dashboard, user, reply, or struggle. Never backdate.
- Say "I", not "we". No "thrilled to announce". No corporate voice.
- Every post: `#BuildInPublic #Shipaton`.
- Real screenshots by default; generated images = ceremony only, clearly illustrative.
- Posting before the app is submitted/published is allowed and counts — start early.
- If the journey dies, withdraw the lane honestly (§7 drop rule).
