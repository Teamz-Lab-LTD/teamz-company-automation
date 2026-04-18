# Contrast rules (apply on every generated UI)

**Single rule that covers 90% of mistakes:** every time you paint a
background, pair it with the matching foreground token of that background.
Never pick a text or icon color in isolation.

## The paired tokens

| Background            | Foreground                |
| --------------------- | ------------------------- |
| `background`          | `onBackground`            |
| `surface`             | `onSurface`               |
| `surfaceVariant`      | `onSurfaceVariant`        |
| `primary`             | `onPrimary`               |
| `secondary`           | `onSecondary`             |
| `success/warning/error` | `onStatus`              |

## Dynamic / computed backgrounds

For backgrounds where the color is computed at runtime (gradient, user-picked,
tinted image overlay):

- **Flutter:** use `ds.contrastOn(bg)` to auto-pick black vs white.
- **Web:** compute WCAG relative luminance once in a theme utility; pick
  `--on-background` when luminance > 0.35, `#000` otherwise. Cache the
  choice — don't recompute per paint.

## Scope propagation (Flutter)

For any subtree placed on a non-default background, wrap in `OnColor`:

```dart
OnColor(
  background: ds.primary,
  child: Row(children: [Icon(Icons.star), Text('Readable')]),
);
```

Every `Text` and `Icon` descendant inherits `ds.onPrimary` automatically.
If you can use `OnColor`, DO — it eliminates the whole class of "someone
forgot the foreground color on this child" bugs.

## Web equivalent

Wrap an element in a class that sets both:

```tsx
<section className="bg-primary text-on-primary">
  <Icon /> <span>Readable</span>
</section>
```

Single class pair. Both sides declared together. Never just `className="bg-primary"`.

## Verification before claiming done

Grep the diff before presenting it:

- `grep -nE "bg-(primary|secondary|success|warning|error)" changed.*.tsx` — every
  match must have a matching `text-on-*` on the SAME element or an ancestor.
- `grep -nE "color: ds\.(primary|secondary)" changed.*.dart` — every
  match must have `OnColor(background: …)` at or above, or an explicit
  `foregroundColor: ds.on…` next to it.

If any fails, fix before shipping.
