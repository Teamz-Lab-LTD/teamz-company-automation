# The design-gap prompt

Paste the block below into any Teamz Lab app project. It works in a repo that has never
heard of the Shipaton — it asks for evidence, not for a verdict.

**Why it is shaped like this.** The obvious version of this request — *"make my app look
more impressive"* — reliably produces the wrong work: a new animation, a colour tweak, a
screen nobody asked for. Design scores are not lost on missing beauty. They are lost on
**systematic, mechanical defects that are invisible to the eye and to a passing test
suite**, and on **craft that exists but was never shown to anybody**.

On 2026-09-03 this exact scan, run against an app whose owner and whose agent both
believed it looked finished, found in under an hour:

- three Material icon families in one app,
- the entire interface typeface being downloaded from `fonts.gstatic.com` at runtime,
- a font weight requested everywhere and bundled nowhere,
- a `Row` overflowing 59px on any 360dp phone, on every card, through 886 passing tests.

Four real defects. None of them findable by looking harder.

---

## The prompt — copy from here

```
Audit this app's design the way a competition judge would, then tell me the ONE thing
blocking it. Not a list of nice-to-haves.

Ground rules, in order of importance:

1. RUN THE MECHANICAL SCAN BEFORE FORMING ANY OPINION. If you look at the app first you
   will decide it looks fine and then rationalise a score. Run every command, paste the
   real output, and quote it in your findings. No claim without a command behind it.

2. Score what a stranger sees in 60 seconds, not what the code deserves. Assume they
   never install it. Screenshots, a video, and whatever is written on the form.

3. Separate "the craft is missing" from "the craft is invisible". These need opposite
   fixes and conflating them wastes the week. Craft that exists but was never captured is
   a camera problem, not a code problem — say so and refuse to recommend polish.

4. Tell me what you did NOT verify. An unverified pass is a guess.

THE SCAN — run all of it, paste the output:

  # one icon family, or several? more than one is the loudest amateur tell
  grep -rhoE "Icons\.[a-z0-9_]+" lib/ | sed -E 's/.*_(rounded|outlined|sharp)$/\1/' | sort | uniq -c

  # is the typeface a network dependency?
  grep -rn "allowRuntimeFetching" lib/ || echo "NEVER DISABLED"

  # is every requested weight actually bundled?
  grep -rhoE "FontWeight\.w[0-9]+" lib/ | sort -u
  sed -n '/^  fonts:/,/^[a-z]/p' pubspec.yaml

  # emoji standing in for icons
  grep -rnP "Text\('[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]" lib/

  # stock framework identity left in place
  grep -rn "Colors.deepPurple\|0xFF6200EE\|Colors.purple\|#D9FE06" lib/

  # one visual voice: painted, or raster? mixing them is a second voice
  echo "images: $(grep -rn 'Image.asset\|SvgPicture' lib/ | wc -l)"
  echo "painters: $(grep -rl 'extends CustomPainter' lib/ | wc -l)"

  # reduced motion in one place, or forgotten at forty call sites?
  grep -rn "disableAnimations\|reducedMotion" lib/ | head

  # the two things nobody can fake
  ls fastlane/screenshots/**/*.png store/*.png 2>/dev/null | wc -l
  find . -name '*.mp4' -o -name '*.mov' | grep -v build | head

THEN, and only then:

5. Write ONE golden test at 320-360dp for every component holding a Row of two or more
   labelled controls, and run it. Overflow does not appear on a big simulator. Check the
   longest locale this app ships, not English — a row that fits in English may not fit in
   German or Bengali. Report every overflow with its pixel count.

6. Name the signature moment in five words or fewer. One motion that is unmistakably this
   app's, that a stranger could describe afterwards. Not a fade, not a page transition.
   If naming it takes a paragraph, the app does not have one — say that outright rather
   than nominating the nearest animation.

7. Score six axes 0/1/2 (2 = would be remembered, 1 = competent, 0 = absent or generic):
   innovative idea · beautiful design · animation · craft made visible · screenshots ·
   video. Any axis at 0 caps the entry.

8. Finish with exactly this sentence and nothing softer:

   Lowest axis is <axis> at <n>/2. Blocking it: <the specific finding>.
   Cost to fix: <estimate>. Moves the total to <n>/12.

9. NEW ASSETS AND NEW ANIMATION: propose them only when the scan earns it, and say
   which condition fired. Do not propose them by default, and do not refuse them by
   default either.

   PROPOSE new work when:
   - Animation scored 0 or 1 AND step 6 could not name a signature moment. Then the
     app needs one built. Do not sprinkle motion everywhere — find the ONE surface
     where movement is already legitimate for this product (an onboarding step, the
     completion of something, a morning or "after" screen, the gesture the product is
     named for) and make that single moment exceptional.
   - An empty state, a first-run screen or a paywall is bare, and bare is reading as
     unfinished rather than as chosen.
   - The app ALREADY ships raster or vector art, so new art joins an existing voice
     instead of introducing a second one.

   DO NOT propose new art when:
   - The UI is drawn in code (many CustomPainters, ~zero Image.asset call sites).
     Dropping raster illustrations beside code-drawn line art is the "One voice"
     failure in step 1, and it also loses theming, animation and scale: a painter
     recolours itself in dark mode and interpolates between states; a PNG cannot.
   - The axis is already at 2. There is no score above 2, so the work earns nothing.
   - Screenshots or video is the lowest axis. New art does not move either.

   Whatever you propose, say how it will be produced and what it costs in bundle
   size, and check `pubspec.yaml` for assets that are declared and never loaded
   before adding more. One app in this org shipped ~8MB of generated art that
   nothing in `lib/` ever rendered, and it broke fresh clones for months.

10. NEVER generate a product screenshot. Store screenshots must show the real app on
    a real device — Play requires it, the rubric requires real content in the real
    typeface, and a rendered mock-up of a UI that does not exist is a fabricated
    product shot. Generated imagery is for brand and marketing surfaces (feature
    graphic, illustration, empty-state art), never for "here is the app working".

Do not recommend a redesign, and do not recommend features that are not design.
If the lowest axis is screenshots or video, tell me to pick up my phone and stop
touching the code.
```

## Reading the answer you get back

**If the lowest axis is craft** — idea, design, animation, craft-made-visible — there is
buildable work and it is usually small and mechanical. Unifying an icon family is an
afternoon.

**If the lowest axis is screenshots or video** — which is the common case, and was the
case for both apps audited on 2026-09-03 — **no commit moves it.** Every hour spent
polishing is spent on an axis already at 2. The honest instruction is: stop, and go
capture.

**Ceiling check before you start.** If four axes already read 2, the maximum remaining
gain is 4 points and all of it is capture. Know that before committing a week.

## When new assets and animation ARE the answer

The first version of this prompt banned proposing them outright. That was over-fitted to
one app — Resume Coach draws its entire UI in code, ships zero image assets, and had
already reversed an ~8MB generated-art experiment that nothing in `lib/` ever rendered.
True there; not a rule.

**Sleep Switch is the counter-example, in this same portfolio, the same week.** Its
Animation axis scored 1 with no signature moment, and the correct fix was to build one:
`SwitchOnDawn` — the crescent's handle travelling back to *on* while the sky comes up
behind it, once, only on a morning after a night that ran. That moved the axis 1 → 2. A
prompt that forbids new work would have blocked the single highest-value thing that app
did.

So the rule is conditional, and the condition is what the scan found:

| Scan says | New art / motion |
|---|---|
| Animation 0–1, no nameable signature moment | **Build one.** One surface, not everywhere |
| Empty states bare, reading as unfinished | **Yes** |
| App already ships raster/vector art | **Yes** — it joins an existing voice |
| UI is code-drawn, ~0 `Image.asset` | **No** — a second voice, and it loses theming and animation |
| Axis already at 2 | **No** — no score exists above 2 |
| Screenshots or video is the lowest axis | **No** — art moves neither |

**The restraint trap, and the way out.** A calm product — sleep, journaling, meditation,
a serious document tool — is *right* to move slowly, and that correctness is exactly what
makes it invisible to a criterion naming animation explicitly. The way out is never to
violate the product. It is to find the one surface where motion is already legitimate and
make that moment exceptional. One exceptional moment beats twenty tasteful ones.

**Existing pattern to follow:** `ai_resume_checker/docs/shipaton/design/codex-asset-prompts.md`
and `design/format-picker/illustration-prompts.md` — asset prompts written and reviewed as
files, not improvised, so what gets generated is reviewable before it is committed.

## Related

- `claude-config/design-award-audit.md` — the full rubric, with the scan appended
- `claude-config/commands/shipaton-check.md` — Step 3b runs this per app and requires the
  gap sentence in every report
