# Next.js + Tailwind mapping

## How tokens live in a Teamz web project

Tokens are declared once as CSS custom properties, then surfaced to
Tailwind via `tailwind.config.js` using `hsl(var(--primary) / <alpha>)`
triplets. Every Teamz web repo should have this shape — if a project
doesn't, flag that `teamz-web-kit` (or equivalent) is missing.

```css
/* app/globals.css (or src/styles/globals.css) */
:root {
  --background: 0 0% 100%;
  --on-background: 222 47% 11%;
  --surface: 0 0% 98%;
  --on-surface: 222 47% 11%;
  --primary: 220 85% 55%;
  --on-primary: 0 0% 100%;
  --secondary: 160 60% 45%;
  --on-secondary: 222 47% 11%;
  --success: 140 60% 42%;
  --warning: 38 92% 50%;
  --error: 0 72% 52%;
  --on-status: 0 0% 100%;
  --outline: 220 10% 88%;
}

.dark {
  --background: 222 47% 8%;
  --on-background: 0 0% 98%;
  /* … */
}
```

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        background:       'hsl(var(--background) / <alpha-value>)',
        'on-background':  'hsl(var(--on-background) / <alpha-value>)',
        surface:          'hsl(var(--surface) / <alpha-value>)',
        'on-surface':     'hsl(var(--on-surface) / <alpha-value>)',
        primary:          'hsl(var(--primary) / <alpha-value>)',
        'on-primary':     'hsl(var(--on-primary) / <alpha-value>)',
        secondary:        'hsl(var(--secondary) / <alpha-value>)',
        'on-secondary':   'hsl(var(--on-secondary) / <alpha-value>)',
        success:          'hsl(var(--success) / <alpha-value>)',
        warning:          'hsl(var(--warning) / <alpha-value>)',
        error:            'hsl(var(--error) / <alpha-value>)',
        'on-status':      'hsl(var(--on-status) / <alpha-value>)',
        outline:          'hsl(var(--outline) / <alpha-value>)',
      },
    },
  },
};
```

## Abstract → Tailwind class map

| Abstract          | Tailwind class example                       |
|-------------------|----------------------------------------------|
| `background`      | `bg-background`                              |
| `onBackground`    | `text-on-background`                         |
| `surface`         | `bg-surface` (often with `rounded-lg`, `shadow-sm`) |
| `onSurface`       | `text-on-surface`                            |
| `primary`         | `bg-primary` — MUST pair with `text-on-primary` |
| `onPrimary`       | `text-on-primary`                            |
| `secondary`       | `bg-secondary` — pair with `text-on-secondary`  |
| spacing `md`      | `p-4` / `gap-4`                              |
| spacing `lg`      | `p-6` / `gap-6`                              |
| radius `md`       | `rounded-md`                                 |
| typography `displayLarge` | a dedicated utility class, e.g. `text-display-lg` (declared in tailwind `fontSize`) |

## Forbidden in generated web code

- Raw hex (`#1d4ed8`) or `rgb(...)` in JSX/TSX className, inline style, or component prop
- `color: red` / `bg-blue-500` / `text-gray-400` — these are Tailwind defaults that skip the token layer
- Custom style on a block without matching `text-on-*` for its background
- `dangerouslySetInnerHTML` of untrusted HTML
- Hardcoded px sizes larger than 4px that aren't on the spacing scale

## Pattern-mode variant strategy (web)

Ship a per-app CSS file under `theme/variants/<app>.css` that re-declares
the CSS custom properties inside a scoped selector (e.g.
`[data-theme="serenity"] { --primary: 350 50% 84%; ... }`) and toggle it
via a `<body data-theme="serenity">` attribute. Tailwind classes never
change — the values resolve differently per app.

For multi-site Teamz landing setups, each site reads its own variant.
Base tokens remain the cross-brand default.
