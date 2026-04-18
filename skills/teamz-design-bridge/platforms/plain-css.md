# Plain CSS (vanilla HTML/JS, pre-framework projects) mapping

Use the same CSS-custom-property pattern as Next.js, without Tailwind.

```css
:root {
  --background: #ffffff;
  --on-background: #0f172a;
  --surface: #f8fafc;
  --on-surface: #0f172a;
  --primary: #1d4ed8;
  --on-primary: #ffffff;
  --secondary: #10b981;
  --on-secondary: #0f172a;
  --success: #16a34a;
  --warning: #f59e0b;
  --error: #dc2626;
  --on-status: #ffffff;
  --outline: #e2e8f0;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-pill: 999px;

  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #0b1220;
    --on-background: #f8fafc;
    /* … */
  }
}
```

## Usage

```css
.button-primary {
  background: var(--primary);
  color:      var(--on-primary);      /* pairing — non-negotiable */
  padding:    var(--space-sm) var(--space-md);
  border-radius: var(--radius-pill);
}
.card {
  background: var(--surface);
  color:      var(--on-surface);
  border:     1px solid var(--outline);
  border-radius: var(--radius-md);
  padding:    var(--space-lg);
}
```

## Forbidden

- Any raw `color: #hex`, `background: rgb(...)`, or named color (`color: red`)
  outside the token declaration above
- Using `color: white` on a variable background without first computing the
  right on-* token
- Inline `style="..."` attributes with color or typography — put them in
  CSS classes that reference variables

## Pattern-mode variant strategy

Per-site overrides via a scoped selector:

```css
[data-theme="serenity"] {
  --primary:   #e8b4b8;
  --secondary: #a8d5ba;
}
```

Toggle with `<body data-theme="serenity">`.
