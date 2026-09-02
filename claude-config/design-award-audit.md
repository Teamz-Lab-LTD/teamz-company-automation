# Design Award readiness — the audit every Teamz app runs

The criterion, verbatim:

> **RevenueCat Design Award:** For the app that best represents the craft of app
> development — regardless of business potential. We're looking for innovative
> ideas and/or beautiful app design and animations.

Three axes, and they are not weighted equally in practice. Read what it does
*not* say: nothing about revenue, downloads, or market size. "Regardless of
business potential" is doing real work — it means a judge is comparing craft,
not traction.

---

## The thing that loses this award

**A judge sees your app for somewhere between 30 and 90 seconds, and almost
certainly never installs it.** They see store screenshots, a demo video, and
whatever you wrote on the form.

So the failure mode is not "the app is not good". It is **"the good part is not
visible in 60 seconds"**. Every audit below is really asking one question:

> Would somebody who never opens this app know it was made with care?

Apps that lose here are usually *better* than apps that win, and lose because
their craft is in places a video cannot reach: architecture, edge cases,
accessibility, restraint.

---

## Axis 1 — Innovative ideas

Not "has features". **Has an idea nobody else had, that the product needs.**

| Test | Pass |
|---|---|
| **The one-sentence idea** | Can you state what is novel in one sentence, with no adjectives? "The sky follows your real weather without ever asking for location" passes. "Beautiful, intuitive design" fails — that is a claim, not an idea. |
| **Only-here test** | Name the three closest competitors. For each, say what they do instead. If the answer is "the same but uglier", the idea is not the differentiator, the execution is — and execution is Axis 2. |
| **It earns its place** | The novel thing must be load-bearing. A gimmick that could be deleted without the product changing reads as a gimmick to a judge too. |
| **Explains in one screenshot** | If it takes a paragraph to explain why it is clever, it will not survive a scroll. |

---

## Axis 2 — Beautiful design

| Test | Pass |
|---|---|
| **First frame** | Screenshot 1 alone, no caption. Does it look like a product somebody cared about? This is the single highest-leverage asset you own. |
| **One voice** | Type, spacing, icon family, corner radius, motion — all from one system. Mixed icon sets and ad-hoc spacing are the loudest amateur tells. |
| **No stock anything** | Default Material purple, unmodified template layouts, emoji-as-icons, stock photography. Any one of these caps the score. |
| **Dark and light both deliberate** | If one mode is clearly an afterthought, say so and fix or drop it. |
| **Real content** | Screenshots must show real data in the real font. Lorem ipsum, "User Name", placeholder avatars — instant tell. |
| **Density is chosen** | Empty space that reads as unfinished is the most common failure. Every void should look decided, not left over. |

---

## Axis 3 — Animations ← the one most teams fail

The criterion names animation explicitly, which means somebody is looking for
it. **This is where restrained apps lose**, and restraint is usually correct —
so the fix is never "add motion everywhere".

| Test | Pass |
|---|---|
| **A signature moment** | One motion that is unmistakably *yours*, that a judge could describe afterwards. Not a fade. Not a page transition. Something with an idea in it. If you cannot name it in five words, you do not have one. |
| **It is in the first 10 seconds of the video** | A signature moment nobody sees is not one. |
| **Motion means something** | Every animation should encode state, causality or continuity. Decorative motion reads as filler; meaningful motion reads as craft. Be able to say what each one *tells* the user. |
| **Interruptible** | Nothing blocks input. A judge tapping through will find this instantly. |
| **Reduced-motion honoured** | Have a resting frame for every loop. This is craft, and it is worth saying on the form. |
| **60fps on a mid device** | Jank in a demo video is fatal. Profile, do not assume. |

### The restraint trap, and the way out

A calm product — sleep, meditation, focus, journaling — is *right* to move
slowly and rarely. That also makes it invisible to this criterion.

**The way out is not to violate the product. It is to find the surface where
motion is already legitimate** and make that one exceptional:

- an onboarding step, where delight is expected
- the *completion* of something, where a payoff is earned
- a morning or "after" surface, where a calm app is allowed to be bright
- the one gesture the whole product is named after

One exceptional moment beats twenty tasteful ones.

---

## Axis 4 — Craft of app development

The criterion says "craft of app development", not "craft of app design". This
is the axis most teams forget they can *show*.

| Test | Pass |
|---|---|
| **Evidence exists** | Tests, measured decisions, real device verification. If it exists, the form is where it goes — it will never be inferred. |
| **Decisions have reasons** | "We chose X because Y, measured" is the single most persuasive sentence available to you, and almost nobody writes it. |
| **Accessibility is real** | Contrast measured, not eyeballed. Touch targets ≥44pt. Screen-reader labels. Dynamic type survives. |
| **It works offline and on a bad phone** | Judges are often on hotel wifi. |
| **No crash on first run** | Obvious, and still the most common disqualifier. |

---

## The deliverables a judge actually sees

Score these, not the app.

### Screenshots (weight: highest)

- [ ] **Screenshot 1 requires no caption.** It is the whole pitch.
- [ ] Real content in the real typeface, never placeholder
- [ ] Captions state the *idea*, not the feature ("Your sky, tonight" not "Weather integration")
- [ ] Consistent device frame, or none at all — never a mix
- [ ] The novel thing appears by screenshot 3
- [ ] Legible as a thumbnail — the size they are first seen at

### Demo video (weight: high)

- [ ] **The signature moment inside 10 seconds**
- [ ] Screen recording at real speed. Sped-up motion reads as hiding jank
- [ ] No narration needed to understand what it is
- [ ] Real device, real data, real hands
- [ ] Under 60s unless the rules allow more

### The form (weight: underrated)

- [ ] Names the innovative idea in one sentence, no adjectives
- [ ] Names the signature animation and what it *means*
- [ ] Cites one measured decision with its number
- [ ] Says what was deliberately left out and why — restraint reads as
      confidence, and nobody else will write this

---

## Scoring

Per axis: **2** = would be remembered · **1** = competent · **0** = absent or generic.

| Axis | Score |
|---|---|
| Innovative idea | |
| Beautiful design | |
| Animation | |
| Craft, made visible | |
| Screenshots | |
| Video | |

**≤6 — not a contender.** Something structural is missing; find it before polishing.
**7–9 — a good app that will not be remembered.** Almost always Axis 3.
**10–12 — a contender.**

Any axis at 0 caps the whole entry. A judge cannot score what they cannot see.

---

## How to run this

1. Score honestly, alone, before showing anybody.
2. Take the lowest axis and fix only that. Polishing a 2 to a 2 is the most
   common waste of the final week.
3. Re-score against the *screenshots*, not the app. That is what is judged.

**Written 2026-09-02** from the published criterion. Re-read the criterion each
season before trusting this file — the wording moves, and the wording is the
rubric.

---

## The mechanical gap scan — run this BEFORE scoring anything

Added **2026-09-03**, after auditing Resume Coach and Sleep Switch on the same day.

**Why this section exists.** The first Resume Coach audit scored Beautiful design **1**
and wrote "the system is real, a judge just cannot see it" — which was wrong, and lazily
wrong. The design genuinely was not a 2, for a reason that had nothing to do with
screenshots and that no amount of looking would have surfaced: the app was drawing from
**three Material icon families at once**. One `grep` found it in four seconds.

Every defect found that day was like that — **systematic, mechanical, invisible to a
passing test suite, and invisible to the eye**:

| Found | How | Consequence |
|---|---|---|
| 3 icon families in one app (47 rounded / 42 outlined / 56 filled) | one grep | the rubric's named amateur tell |
| Interface typeface downloaded at runtime | a golden test failing in a sandbox | cold start on bad wifi renders the whole app in Roboto, silently |
| A weight requested that was never bundled | the same failure, read properly | the app's bold ALWAYS came off the network |
| A `Row` overflowing 59px at 360dp | the first golden ever written | striped overflow banner on every card, on every narrow phone |

None of these were taste. All of them capped a score. **Run the scan before forming an
opinion — an eye that has already decided the app looks fine will not find any of them.**

```bash
# 1 — How many icon families? More than one is the rubric's "One voice" failure.
grep -rhoE "Icons\.[a-z0-9_]+" lib/ | sed -E 's/.*_(rounded|outlined|sharp)$/\1/' \
  | sort | uniq -c
# Anything without one of those suffixes is the filled/legacy set: a third family.

# 2 — Are fonts fetched at runtime? If GoogleFonts is used and this prints nothing,
#     the typeface is a network dependency and the app renders wrong offline.
grep -rn "allowRuntimeFetching" lib/ || echo "NEVER DISABLED -> fonts come off the network"

# 3 — Is every requested weight actually bundled? A weight with no asset is fetched
#     or silently falls back.
grep -rhoE "FontWeight\.w[0-9]+" lib/ | sort -u
sed -n '/^  fonts:/,/^[a-z]/p' pubspec.yaml

# 4 — Emoji standing in for icons. Instant cap.
grep -rnP "Text\('[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]" lib/

# 5 — Stock Material identity left in place.
grep -rn "Colors.deepPurple\|0xFF6200EE\|Colors.purple\|#D9FE06" lib/

# 6 — Raster art mixed into a painted UI (or the reverse). Pick one voice.
echo "image call sites: $(grep -rn 'Image.asset\|SvgPicture' lib/ | wc -l)"
echo "CustomPainters  : $(grep -rl 'extends CustomPainter' lib/ | wc -l)"

# 7 — Does a signature moment exist, and can it be named in five words?
#     Not greppable. If the answer needs a paragraph, the answer is no.

# 8 — Is reduced motion handled in ONE place, or at forty call sites?
grep -rn "disableAnimations\|reducedMotion" lib/ | head

# 9 — The two axes nobody can fake.
ls fastlane/screenshots/**/*.png store/*.png 2>/dev/null | wc -l   # screenshots
find . -name '*.mp4' -o -name '*.mov' | grep -v build | head       # video
```

### The narrow-phone check has to be a test, not a look

Overflow does not show on a 6.7" simulator. Write one golden at **320–360dp** for every
component carrying a `Row` of two or more labelled controls. That single test found a
59px overflow that had shipped through 886 passing tests and two device passes.

Labels are translated. A row that fits in English at 360dp may not fit in German or
Bengali — check the longest locale, not the one you wrote.

### Report the GAP, not the score

A score is a number somebody nods at. **A gap is a task.** Every audit ends with one
sentence, in this shape:

> **Lowest axis is `<axis>` at `<n>`. The specific thing blocking it is `<finding>`.
> Fixing it is `<estimate>`, and it moves the total to `<n>`.**

If the lowest axis is Screenshots or Video, say so plainly and stop recommending app
work — no code change moves those, and every hour spent polishing instead is an hour
spent on an axis that is already at ceiling.
