# Banned patterns

Things that silently produce illegible or off-brand UI. Never emit these.
If a user request seems to require one, push back and propose the
token-compliant alternative.

## Color misuse

- White/default text on neon backgrounds (`primary`, `success`, `warning`).
  Neon is bright; white text on neon fails WCAG AA in most palettes.
- Black text on dark surfaces (`background`, `surface` when the app is in
  dark mode).
- `SnackBar(backgroundColor: ds.primary)` or `AlertDialog(backgroundColor:
  ds.primary)` without pairing with `onPrimary` — Flutter's default body
  style is `ds.onSurface`, which is typically light and unreadable on
  primary. Use the kit's `SnackBarHelpers` / `TeamzModal` instead; they
  set the pair automatically.
- `Colors.grey[300]` or similar arbitrary grey — use `ds.outline` or
  `ds.onSurfaceVariant`.
- Hardcoded `#ffffff` / `#000000` — use `ds.onSurface` / `ds.surface` or
  their design-system equivalents.

## Typography misuse

- Custom `TextStyle(fontFamily: '…')` inline — always `ty.*` from
  `context.teamzLabTypography`.
- `fontSize: 18` literal inside a widget — use the typography scale.
- Setting `fontWeight: FontWeight.bold` via arbitrary number (`w800`
  etc.) when the typography scale already has a `bold` variant.

## Layout misuse

- Fixed widths for content areas (`width: 350`) — use `ConstrainedBox`
  or responsive breakpoints.
- Hardcoded `EdgeInsets.all(13)` — use the spacing scale (4, 8, 16, 24,
  32, 48, 64).
- `SizedBox(height: 17)` etc. — round to the spacing scale.

## Interaction misuse

- Tap targets smaller than 44×44 logical pixels. Minimum applies even to
  icon-only buttons.
- `TextField` with no label OR no placeholder — one of them is always
  required.
- Destructive actions (delete, sign out) without a confirmation sheet.
- Hiding primary CTA below the fold on mobile when it fits above.

## Animation misuse

- Opacity fades longer than 400ms — feels sluggish.
- `AnimatedContainer` with `Curves.bounceOut` on system UI — Teamz tone
  is calm, not bouncy. Use `Curves.easeOutCubic` or the motion token's
  easing.
- Auto-playing video/audio with sound on page load (also a web a11y win).

## Accessibility misuse

- Emoji or icons as sole labels without a `Semantics(label: …)` fallback.
- Relying on color alone to signal state (e.g., red border = error with
  no icon or message).
- Disabling the browser zoom / viewport fit.

## Copy misuse

- Raw `Text('Save')` instead of `Text(context.appText.save)` — all
  user-visible strings must be localized.
- Untranslated placeholder text inside a `Text` field.

## Web-specific

- `dangerouslySetInnerHTML` of anything user-derived.
- Inline `style={{ color: '#xxx' }}` in React/JSX outside the theme
  bootstrap file.
- `!important` in generated styles — almost always a sign you're fighting
  the token system.

## Apple/Play policy red flags

- Ads on a WebView that also serves AdSense → policy grey zone.
- Native + banner ad on the same interactive single-action screen.
- Interstitial ad firing more than once every 45 seconds.
- Missing `NSUserTrackingUsageDescription` when the app ships ads on iOS.

(The last four are enforced in the kit's main CLAUDE.md; listed here
so the design skill won't recommend layouts that violate them.)
