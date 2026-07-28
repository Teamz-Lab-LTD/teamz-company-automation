# Design prompt template — for generating a screen as a claude.ai Artifact

**What this is.** A fill-in-the-blanks prompt that produces a *working motion prototype* of a
screen, which then ports to Flutter one-to-one. Generalized from the prompts that produced
Resume Coach's payoff screen, brand marks and career hub — the screens that came out well.

**Paste the filled prompt into claude.ai, not into Claude Code.** The model on the other end
has no access to the repo, so every constraint it needs must be inside the prompt. That is why
this template pins values instead of referring to files.

## Why an HTML artifact and not an image

The RevenueCat Design Award criterion is *"beautiful app design **and animations**"* and
*"smooth gestures, satisfying animations, and clear feedback loops."* A PNG cannot show any of
that. An artifact runs — so it can be judged on motion, and the motion can be ported.

This holds outside the competition too: a static mockup lets you approve a layout you have not
actually seen behave. Most screens that feel cheap feel cheap in motion, not in a screenshot.

## The one idea worth copying

> **Render the invisible process, in motion.** Polish alone never wins.

Every screen has some work the app does that the user cannot see — a match being computed, a
file being parsed, a plan being assembled. Ordinary apps report the *result* and ask to be
trusted. The screens worth building show the *process*, and become both the proof and the
product's best argument. Resume Coach's ATS X-ray is this: it scans the user's real page in
front of them instead of claiming a score.

Before filling in the template, answer one question: **what does this screen do that the user
currently has to take on faith?** That is what to choreograph.

---

## Fill these in

| Placeholder | What goes here |
|---|---|
| `{{APP}}` | One sentence a stranger understands. Not a feature list. |
| `{{SCREEN}}` | The screen's job in one line. |
| `{{PROBLEM}}` | What competitors do badly here, and why users don't believe them. |
| `{{INVISIBLE_PROCESS}}` | The work the user currently takes on faith. |
| `{{ELEMENTS}}` | The 3–5 things the screen holds. Numbered. |
| `{{THE_MOMENT}}` | The single instant the design has to earn. |
| `{{REFUSALS}}` | What the app honestly cannot do, shown as a feature. Delete only if truly none. |
| `{{LANGUAGE}}` | The design language in 3 words + one sentence on how the user feels arriving. |
| `{{TOKENS}}` | The real CSS custom properties. Light AND dark. Copy actual values from the app's design system — never let the model invent a palette. |
| `{{TYPE}}` | At most two families, each with its job. |
| `{{MOTION}}` | The app's real duration and curve table. |

---

## The prompt

> You are designing {{SCREEN}} of a mobile app. I need a **working HTML/CSS/JS artifact** — a
> motion prototype, not a static mockup. It must actually animate when I open it.
>
> ### The app
> {{APP}}
>
> ### The problem I am trying to solve
> {{PROBLEM}}
>
> ### What I want you to design
> Make {{INVISIBLE_PROCESS}} visible, **in motion**. Without a paragraph of explanation, the
> screen should let the user see it happen rather than be told it happened.
>
> The screen holds these things. Your job is to choreograph how they arrive and how they
> connect:
> {{ELEMENTS}}
>
> **The moment I care about:** {{THE_MOMENT}}
>
> **The refusal is a feature, not a limitation.** {{REFUSALS}} Competitors paper over this.
> Design it as something the user is glad to see, not an error state.
>
> ### Hard constraints — do not deviate
>
> **Design language: {{LANGUAGE}}**
>
> **Colours — use exactly these. Do not invent any.**
> ```css
> {{TOKENS}}
> ```
> Ship BOTH themes, switched on `prefers-color-scheme`. Every foreground comes from the paired
> `on*` token of its background — never a generic text colour on a coloured surface.
>
> **Type — {{TYPE}}**
> Put `font-variant-numeric: tabular-nums` on any number that animates or sits in a column, so
> digits do not jitter.
>
> **Spacing:** 4pt grid — 4, 8, 12, 16, 20, 24, 32, 40, 48.
> **Radius:** tight, and consistent. Pill-shaped everything reads as a consumer toy.
> **Shadows:** surfaces lift, they do not glow.
>
> **Motion — match these exactly, because this ports to Flutter:**
> ```
> {{MOTION}}
> ```
> Animate **only `transform` and `opacity`**. Never width, height, top, left or padding —
> those re-run layout every frame and cannot be ported cheaply.
> Honour `@media (prefers-reduced-motion: reduce)`: every duration collapses to 0 and the
> screen still reaches its final state on the first frame, still making its whole argument.
>
> ### Things that will make me reject the output
> - Purple/violet gradients. Glassmorphism. Frosted blur. Neon. Glows.
> - Emoji as icons. Use inline SVG, 1.5px stroke.
> - A generic SaaS dashboard look.
> - Any colour not in the list above.
> - Decorative animation that means nothing. **If I delete an animation and lose no
>   information, it should not exist.**
> - Text below 12px, or a touch target under 44×44.
>
> ### Deliverable
> One self-contained HTML artifact. A 390×844 phone frame, centred on a neutral backdrop.
> Light and dark. It should **play the whole sequence on load**, with a replay button, because
> I will watch it twenty times.
>
> Give me **three genuinely different choreographies** of the same content — not three colour
> variants. Different *ideas* about how these elements relate. Then tell me in two sentences
> which one you would ship, and why.

---

## After the artifact comes back

1. **Watch it with reduced motion on.** If the screen stops making its argument, the motion was
   carrying meaning that the static state does not. Fix the static state, not the motion.
2. **Save the HTML into the app repo** under `docs/design/` — it is the reference the Flutter
   port is checked against, and the only record of what was actually approved.
3. **Port it, then run the ship gate** — `DESIGN-SHIP-GATE.md` in this folder. The gate is what
   stops a screen from being 80% ported and quietly left there.
4. **Record which prompts produced which screens.** On Resume Coach, prompt 3 specified three
   screens and only one was ever ported; nobody noticed for two weeks because nothing tracked
   it.
