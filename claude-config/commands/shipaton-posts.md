# /shipaton-posts [setup | today | log <url> | suggestion <who> <what> [link] | shipped <#> | health]

**The #BuildInPublic engine for every Teamz Lab Shipaton app.** One X account (@gkemonapp), many
apps, one queue. Claude does everything except two physically-owner things: tapping "publish" on
X, and speaking into an app that scores speech.

## §0. What wins — read before doing anything

Verbatim judging criteria (fetched 2026-08-15, quoted in
`interview-boss-plus/docs/shipaton/CATEGORY-TRACKER.md`):

1. **Sharing your story** — how creatively the journey is shared
2. **Engagement** — *"What new ideas were brought into the app based on feedback from your
   social posts?"*
3. **Lessons Learned** — *"How did sharing publicly improve the app?"*

**Post COUNT is not a criterion.** Criteria 2–3 are scored on **loops**: post → someone replies
with an idea → it ships → before/after posted. Target **≥3 loops per app** before Sep 30. Every
mode below serves loops first, cadence second, polish third.

**Flagship rule:** each app is a separate Devpost submission judged only on its own posts — they
do not pool. InterviewBoss Plus is the flagship (the uncopyable weekly self-scoring arc) and keeps
3 posts/week. Every other app is a supporting entry: 5–8 honest posts, credible, cheap, not
expected to place. Never let a supporting app's slot displace a flagship arc post.

## §1. The fixed structure (never deviate)

- **Per app** (`docs/shipaton/` in that app's repo): `POSTS-READY.md` (finished texts + evidence
  footers + image paths), `JOURNEY-LOG.md` (published URLs, suggestions, loops, decisions),
  `images/` (real captures + rendered cards + `cards/INDEX.md` mapping each card to its source).
- **One hub, dates only:**
  `~/Projects/Teamz Lab Projects/teamz-projects/interview-boss-plus/docs/shipaton/X-QUEUE.md`.
  Content never lives in the hub.
- **Cross-project write rule:** a session in app A may touch only app A's rows in the hub. (The
  one authorized cross-project write — owner decision, 2026-08-28.)

## §2. What a good post looks like (learned from the two proven campaigns)

Run every draft through this before it enters POSTS-READY.md:

1. **First line is the hook** — the surprising fact, not the setup. "My own docs claimed the
   microphone worked. It was replaying four canned sentences." Never open with "Today I worked on…".
2. **One concrete number or detail per post.** "dropped 5 of 6 pasted digits" beats "had a paste
   bug". Specificity is what makes honesty legible.
3. **Self-critical beats self-congratulating.** The proven posts are confessions with fixes:
   wrong copy shipped, price I got wrong, promise I chose not to make. Wins > lessons is the
   wrong ratio; judges score lessons.
4. **End with a question when a reply is wanted** — direct, answerable in one line, about the
   reader's experience, not "what do you think?". This is the loop-harvest mechanism; put one on
   every 2nd–3rd post, always on technique posts.
5. **2–5 short sentences.** If it needs more, it is two posts or a thread — prefer two posts.
6. **Voice: "I", never "we".** Plain words. No emoji walls, no 🚀, no "excited to announce".
7. **`#BuildInPublic #Shipaton` on every post** — the tagging is how posts count at all.
8. **Evidence footer in the file** (not in the tweet): the commit/file/dashboard that proves each
   claim, checked against git BEFORE the draft is saved. No invented metrics, no users that don't
   exist, no relabeling a weak number as a strong one.
9. **BLOCKED means blocked.** An event that hasn't happened gets a BLOCKED stub, never a draft
   written as if it happened.
10. **Images are real:** device screenshots (`adb exec-out screencap`) or cards rendered from
    verbatim repo content. AI ceremony art only for non-evidence moments (launch, thank-you).
    Anything that looks like a result must be a real capture — a generated "result" is fabricated
    evidence and kills the entry.

## §3. Modes

### `setup` — once per new app

1. Confirm cwd is the app's repo. Read `git log --oneline -40`, existing `docs/shipaton/`, and
   the app's real features (grep before claiming anything).
2. Read both exemplars: `interview-boss-plus/docs/shipaton/POSTS-READY.md` and
   `ai_resume_checker/docs/shipaton/POSTS-READY.md`.
3. Write `POSTS-READY.md`: 5–8 posts from REAL git events (a bug with a story, an honest mistake,
   a decision with a reason, a pricing choice), each passing §2, at least two ending in
   loop-harvest questions. Mark event posts BLOCKED.
4. Write `JOURNEY-LOG.md` (interview-boss-plus structure: posts / suggestions / loops /
   decisions tables).
5. **Create the images now, not a plan:** rendered cards built immediately from repo content;
   device screenshots captured immediately if a device is connected (ask for one if not — no
   "ready" post without its image on disk); `images/cards/INDEX.md` maps every card to its
   source. Only owner-voice/face shots and the one-batch Codex ceremony art may wait.
6. Register in the hub: this app's rows into free gap days (flagship rule §0), and a row in the
   hub's "Registered apps" table.
7. Report: posts drafted, evidence behind each, images created, dates taken.

### `today` — default, run from any project

1. Read the hub. Name today's row — or the nearest overdue one, and say it's overdue.
2. Print the post text in one copy-paste block + the image's absolute path (verify it exists;
   render it now if it's a not-yet-built card).
3. Print the seeding line: which venue today per that app's SEEDING.md / the §2 cadence
   (Shipaton Discord every post; r/FlutterDev / IndieHackers max 1×week, technique posts only).
4. Remind: `/shipaton-posts log <url>` after publishing.
5. If anything is >2 days overdue, slide that app's queue right in the hub (own rows only) and
   say so. Never advise posting two in one day to catch up.

### `log <url>`

File URL + date + post # into THIS app's JOURNEY-LOG posts table (create the row if missing). If
the URL belongs to another registered app, say so and file it there instead. Then check: does
this app's journey log still have any `[FILL` URL slots? If yes, nag — unlogged links do not
exist to judges.

### `suggestion <who> <what> [link]` — the prize-critical one

1. Append to this app's JOURNEY-LOG suggestions table immediately, with date and link.
2. Assess shippability. If shippable: propose the smallest real implementation and offer to build
   it now. Small and real beats big and pending — the loop needs a before/after, not a feature.
3. When it ships, run `shipped`.

### `shipped <suggestion-row>` — close the loop

1. Draft the before/after post: name the person (handle), what they suggested, both screenshots.
   It **jumps the queue** — post it the next free day; the bumped post slides.
2. Fill the loops table row linking suggestion → commit → post.
3. Say the count: "loop N of 3 for this app."

### `health` — run weekly, audits ALL registered apps

For every app in the hub's registry:
- days since last published post (>4 = red, cadence is dying — the kill rule is two consecutive
  weeks below 2/week);
- `[FILL` URL slots in its journey log (any = red);
- loop count vs the ≥3 target;
- overdue queue rows;
- flagship only: days since last recorded voice session (>8 = red, the arc is shrinking).
Output one table, reds first, each red with its one-line fix. This mode exists because the
flagship once went silent for 7 days with a finished post sitting ready.

## §4. Refusals

- Never draft a post about an event that has not happened.
- Never invent, round up, or relabel a metric; never claim users that don't exist.
- Never write post content into the hub; never touch another app's hub rows.
- Never claim a feature without grepping the app's code for it first.
- Never generate an image that could be read as an app result or metric.
- Never advise two posts in one day, even to catch up a broken cadence.
