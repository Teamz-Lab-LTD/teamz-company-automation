# /design-gap [app-slug] [--fix] [--assets]

**Find the ONE thing blocking this app's design, mechanically, before forming any opinion.**

Works in any project — it needs no Shipaton context, no tracker, and no prior audit. Run it
in a repo that has never heard of the competition and it still answers the only question
that matters: *would a stranger who never installs this know it was made with care, and if
not, what exactly is stopping them?*

## Why this command exists

On 2026-09-03 an audit of Resume Coach scored its design **1/2** and wrote *"the system is
real, a judge just cannot see it."* That was wrong, and lazily wrong. The app genuinely was
not a 2 — for a reason with nothing to do with screenshots, that no amount of looking would
ever have surfaced, and that **one grep found in four seconds**: it was drawing from three
Material icon families at once.

Everything found that day was the same kind of defect — systematic, mechanical, invisible to
the eye AND to 886 passing tests:

| Found | How | What it cost |
|---|---|---|
| 3 icon families in one app | one grep | the rubric's named amateur tell |
| Interface typeface downloaded at runtime | a golden test failing in a sandbox | cold start on bad wifi rendered the whole app in Roboto, silently |
| A font weight requested everywhere, bundled nowhere | reading that failure properly | the app's bold ALWAYS came off the network |
| A `Row` overflowing 59px at 360dp | the first golden ever written | striped overflow banner on every card, every narrow phone |

**An eye that has already decided the app looks fine will not find any of them.** So the
scan runs first, before any judgement. That ordering is the whole command.

## Pre-flight reads

1. `claude-config/design-award-audit.md` — the rubric, the six axes, the mechanical scan,
   and the conditional rule on new assets. **Mandatory.** Do not score from memory.
2. `claude-config/prompts/design-gap-super-prompt.md` — the same discipline in pasteable
   form, plus the worked reasoning on when new art is right and when it is a regression.
3. `<app>/docs/shipaton/DESIGN-AWARD-STATUS.md` if it exists — the previous score. **Read
   it to diff against, never to inherit.** A score written before a feature shipped is
   stale; Sleep Switch's Animation axis sat at 1 in its own file for a day after the fix
   that made it a 2.

## Flow

### Step 1 — Resolve the app

Same auto-discovery as `/aso-refresh` and `/shipaton-check`. With no argument, use the
current working directory's project.

```bash
APP_SLUG="${1:-}"
if [ -n "$APP_SLUG" ]; then
  PROJECT_DIR=""
  while IFS= read -r envf; do
    if grep -qE "^TEAMZ_APP_SLUG=$APP_SLUG\b" "$envf" 2>/dev/null; then
      PROJECT_DIR="$(dirname "$envf")"; break
    fi
  done < <(find "$HOME/Projects/Teamz Lab Projects/teamz-projects" -maxdepth 5 -name ".teamz-automation.env" 2>/dev/null)
  [ -z "$PROJECT_DIR" ] && { echo "Unknown slug '$APP_SLUG'"; exit 1; }
else
  PROJECT_DIR="$(pwd)"
fi
```

### Step 2 — Run the mechanical scan, paste the real output

Every command from `design-award-audit.md`'s scan section. **Paste what it printed.** No
claim in the report may exist without a command behind it.

Do not skip a check because it "obviously passes" — the icon-family check obviously passed
too, right up until it printed three numbers.

### Step 3 — The narrow-phone test

Overflow does not appear on a 6.7" simulator, and it did not appear across two device
passes on a real Pixel.

Write one golden at **320–360dp** for every component holding a `Row` of two or more
labelled controls, and run it. Check the **longest locale the app ships**, not English — a
row that fits in English may not fit in German or Bengali, and these labels are usually
translated into twenty-odd languages.

Report every overflow with its pixel count. If the repo has no golden suite at all, say so:
that is itself a finding on the craft axis, and the suite is the fix.

### Step 4 — Name the signature moment in five words

One motion unmistakably this app's, that a stranger could describe afterwards. Not a fade.
Not a page transition.

If naming it takes a paragraph, **the app does not have one** — say that outright rather
than nominating the nearest animation. That honest "no" is what tells the owner to build
one, and it is the finding that moved Sleep Switch from 6/12 to 7/12.

### Step 5 — Score six axes, 0/1/2

`innovative idea · beautiful design · animation · craft made visible · screenshots · video`

**2** = would be remembered · **1** = competent · **0** = absent or generic.
Any axis at 0 caps the entry.

Score the **deliverables**, not the app — but do not double-count: a missing video is
Axis 6's problem, not Animation's. Docking Animation for having no video is the error that
put Resume Coach at 5/12 when it was an 8.

### Step 6 — The gap sentence, verbatim shape

> **Lowest axis is `<axis>` at `<n>`/2. Blocking it: `<the specific finding>`.
> Cost to fix: `<estimate>`. Moves the total to `<n>`/12.**

Then say which situation the app is in, because the advice is opposite:

- **Lowest axis is craft** (idea / design / animation / craft-made-visible) → there is
  buildable work. Name it, smallest first.
- **Lowest axis is Screenshots or Video** → **no code change moves it.** Say so and stop
  recommending app work. This is the common case and the one sessions get wrong.

### Step 7 — Write it back

Create or update `<app>/docs/shipaton/DESIGN-AWARD-STATUS.md`: the six-axis table with
evidence per row, what moved since the last run and why, and the gap sentence. Never delete
a previous score — date it and leave it, same discipline as the category tracker.

## `--fix`

Apply only the mechanical findings, one commit each, tests green between them:
icon-family unification · runtime font fetching disabled and every requested weight bundled
· overflow fixes · emoji-as-icons replaced · stock framework colours removed.

Never bundled with a redesign, and never a taste change — if a fix requires choosing
between two defensible looks (which icon family, which weight), state the choice and its
reasoning in the commit body so it can be reversed on one line.

## `--assets`

Decide whether new art or a new signature animation is warranted, using the conditional
table in `design-award-audit.md`. **Both blanket answers are wrong** and each has burned a
session: "never generate art" would have blocked Sleep Switch's `SwitchOnDawn`, and
"generate art" put ~8MB into Resume Coach that nothing in `lib/` ever rendered and that
broke every fresh clone.

Write asset prompts as reviewable files first — the pattern is
`ai_resume_checker/docs/shipaton/design/codex-asset-prompts.md` — so what will be generated
can be read before it is committed.

**Never generate a product screenshot.** Brand and marketing surfaces only.

## Refusal conditions

- **Scoring before the scan has run and its output pasted.** This is the entire point.
- **Recommending app or design work when the lowest axis is Screenshots or Video.** No
  commit moves those; the recommendation sends the owner to polish an axis already at 2.
- Inheriting a score from another app, from this app's own stale status file, or from the
  README. Re-run the tests against this code, today.
- Declaring an axis a 2 without naming the evidence that earns it.
- Proposing new art without stating which row of the conditional table fired.
- Generating anything that will be presented as a screenshot of the app.

## Citation requirement

State: this command's path, the rubric read and its `Written:` date, the status file
written, which scan commands were actually run, and anything not verified. So the owner can
audit which signals fired rather than trusting a number.
