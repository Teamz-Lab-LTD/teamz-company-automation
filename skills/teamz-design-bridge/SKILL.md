---
name: teamz-design-bridge
description: >
  Rewrites any generic UI/UX recommendation (including ui-ux-pro-max output)
  into Teamz Lab brand-consistent code. Enforces TeamzLab design-system tokens,
  kit widgets, contrast rules, and accessibility. Auto-activates whenever the
  user asks to build or refactor a UI surface (screen, widget, component,
  paywall, onboarding, landing page).
activation:
  keywords:
    [
      "design",
      "ui",
      "ux",
      "screen",
      "page",
      "widget",
      "component",
      "paywall",
      "onboarding",
      "theme",
      "landing",
      "color",
      "typography",
      "wireframe",
      "hero",
      "style guide",
      "design system",
    ]
---

# Teamz Design Bridge

**Purpose** — you (Claude) are producing UI for a Teamz Lab project. This
skill makes sure every output matches the brand, whatever stack you're in.

## Two operating modes

### 1. Strict mode (default — use this unless user says otherwise)

Every color, font, spacing, and widget primitive you emit must come from the
host project's Teamz design system. Never invent a hex, never reach for a
raw Flutter `Text()` when a kit primitive exists.

See [`platforms/`](./platforms) for the per-stack mapping and
[`tokens.json`](./tokens.json) for the abstract token names.

### 2. Pattern mode (opt-in — only when user explicitly says so)

When the user says something like "this app should feel like a wellness spa
— soft pinks, Cormorant Garamond" or otherwise requests a style deviation,
DO NOT scatter hex codes across widgets. Instead:

1. Propose a **`DesignSystemVariant` file** at
   `lib/src/shared/design_system/variants/<app>_variant.dart` (Flutter)
   or `theme/variants/<app>.css` (web) that declares the overridden tokens.
2. Base `TeamzLabDesignSystem` **stays untouched** — every other Teamz
   project keeps its brand.
3. All widgets still reference tokens (`ds.primary`, `bg-primary`) — the
   variant swaps what those tokens resolve to.

Always show the diff before writing the variant.

## Hard rules (never broken, in either mode)

See [`rules/`](./rules) for the full catalog. Top-level:

- **Always pair background with its `on*` foreground.** If you set a
  background color, you MUST set the paired foreground token from the
  design system. No guessing. See `rules/contrast.md`.
- **Never use banned patterns.** See `rules/banned.md` — list includes
  white-on-neon, black-on-dark-surface, `SnackBar` with `backgroundColor:
  primary` and default body text.
- **Accessibility is non-negotiable.** See `rules/a11y.md` — WCAG AA
  contrast, 44×44 touch targets, dynamic type, semantic labels.
- **Use kit widget primitives over raw Flutter/HTML.** Flutter: prefer
  `CommonButton`, `TeamzAppBar`, `TeamzSection`, `TeamzScreenScaffold`,
  `OnColor`, `CustomEditText`. See `platforms/flutter.md`.

## How to use when generating UI

1. **Read the abstract design intent** from the user / any upstream skill
   (ui-ux-pro-max, figma, etc.) — record it as: pattern, mood, color
   direction, typography direction, motion direction.
2. **Decide mode:** if the user accepted a specific brand style (pink
   wellness palette, fintech dark, etc.) → Pattern mode. Otherwise →
   Strict mode.
3. **Map every concrete color/font/space** recommendation to an abstract
   token in `tokens.json`. If no token fits, flag it to the user — don't
   silently invent one.
4. **Emit code using the active stack's bridge** in `platforms/`. Never
   emit raw hex, `Color(0xFF...)`, `FontFamily('...')`, or CSS hex literals
   directly. If you would, STOP and call yourself out.
5. **Validate against `rules/`** before claiming done. If any rule is
   broken, fix before emitting.

## Compatible with / overrides

- **ui-ux-pro-max** — if that skill proposes raw palettes/fonts, this
  bridge re-maps them to Teamz tokens first. Never emit ui-ux-pro-max
  output verbatim.
- **figma MCP** — same policy. Figma tokens get routed through
  `tokens.json` mapping.

## How the skill reaches your project

This skill lives inside the `teamz-company-automation` submodule.
`setup-symlinks.sh` creates a symlink at `.claude/skills/teamz-design-bridge`
in every host project so Claude Code discovers it automatically.
