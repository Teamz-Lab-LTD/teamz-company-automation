# Accessibility Audit

Not a finishing touch — a research method. Done with the same rigor as
usability testing, ideally with AT users (screen reader, keyboard-only,
low-vision). Integrates with the Teamz design system.

## Minimum pre-launch audit (every surface)

### Perceivable

- [ ] Text contrast ≥ 4.5:1 for body; ≥ 3:1 for large (≥ 18pt /
      14pt-bold) (WCAG AA)
- [ ] Non-text contrast (icons, borders, focus indicators) ≥ 3:1
- [ ] Images have `Semantics(label: …)` (Flutter) or `alt` (web)
- [ ] Color is never the sole information channel (add icon, label, pattern)
- [ ] Dynamic type scales up without clipping (test at 200% accessibility size)

### Operable

- [ ] Touch targets ≥ 44×44 pt (iOS) / 48×48 dp (Android) / 24×24 px (WCAG 2.2 minimum)
- [ ] All interactive elements reachable via keyboard / switch / AT focus
- [ ] Focus order follows reading order (top→bottom, left→right)
- [ ] Focus indicator visible (≥ 3:1 contrast against adjacent)
- [ ] No motion-only interactions without an alternative
- [ ] Animations respect `MediaQuery.disableAnimations` / `prefers-reduced-motion`

### Understandable

- [ ] Form fields have visible labels (not placeholder-only)
- [ ] Error messages name the field and the fix ("Email must include @")
- [ ] Instructions precede the input they describe
- [ ] Language attribute set (Flutter: `Locale`; web: `<html lang>`)

### Robust

- [ ] Semantic widgets used (not `GestureDetector` where `Button` fits)
- [ ] Screen reader announces state changes (loading, error, success)
- [ ] Platform conventions honored (iOS VoiceOver, Android TalkBack)

## Teamz-specific bindings

The kit provides:

- **`ds.*` tokens** — paired `on*` colors enforce contrast when used correctly
- **`OnColor(background: ..., child: ...)`** — wraps a subtree and
  propagates the correct foreground. Use this rather than setting text
  colors manually on any non-default background.
- **`ds.contrastOn(bg)`** — computes black/white by luminance for
  dynamic backgrounds (gradients, user-picked colors, images)

Rules that follow from the global CLAUDE.md:

- Never pick a text or icon color in isolation. Every background
  pairs with its `on*` foreground.
- Banned: white text on neon (`primary`, `success`, `warning`); black
  text on dark (`background`, `surface`).
- Never re-implement contrast logic at app level.

## Testing matrix

| Test | Tool | Pass criteria |
|---|---|---|
| Color contrast | Stark, Colour Contrast Analyser | WCAG AA |
| Screen reader | VoiceOver (iOS), TalkBack (Android), NVDA (web) | Every element reachable, state changes announced |
| Keyboard-only (web) | Physical keyboard, Tab/Shift-Tab | Every control focusable, visible focus |
| Dynamic type | iOS Settings → Accessibility → Text Size (max) | No clipping, no cutoff |
| Dark mode | Toggle | Contrast holds in both modes |
| Reduced motion | OS setting | Animations are instant or cross-fade |

## AT-user testing

When shipping a major surface (onboarding, paywall, core flow), recruit
1–3 AT users:

- Blind / low-vision screen reader users
- Motor-impaired users (switch, voice control, keyboard-only)
- Cognitive-disability users (dyslexia, ADHD)

Session protocol mirrors usability testing
([`03-usability-testing.md`](./03-usability-testing.md)) with extra
warm-up and more time per task.

## Accessibility severity (adds to the rubric)

Within the severity rubric, accessibility issues score:

- Blocking AT users from primary task → **4** (catastrophic — legal risk)
- Degrading AT user experience without blocking → **3**
- Minor AT friction → **2**
- Cosmetic AT issue → **1**

Under-scoring accessibility is the most common scoring mistake.

## Deliverables

- Per-surface checklist (above) filled
- Specific issues with severity + rec
- Before/after contrast ratios for changes
- AT-user session notes (if applicable)
- Re-audit after implementation — accessibility is verified on the
  shipped build, not the design spec.
