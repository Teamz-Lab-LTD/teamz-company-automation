# WordPress (team_wp_mvp_kit) mapping

## Tokens live in `theme.json`

WordPress Full-Site-Editing themes declare tokens in `theme.json` at the
theme root. The bridge's abstract tokens map to WP's palette + typography
slugs with the same names.

```json
{
  "$schema": "https://schemas.wp.org/trunk/theme.json",
  "version": 3,
  "settings": {
    "color": {
      "palette": [
        { "slug": "background",      "name": "Background",      "color": "#ffffff" },
        { "slug": "on-background",   "name": "On Background",   "color": "#0f172a" },
        { "slug": "surface",         "name": "Surface",         "color": "#f8fafc" },
        { "slug": "on-surface",      "name": "On Surface",      "color": "#0f172a" },
        { "slug": "primary",         "name": "Primary",         "color": "#1d4ed8" },
        { "slug": "on-primary",      "name": "On Primary",      "color": "#ffffff" },
        { "slug": "secondary",       "name": "Secondary",       "color": "#10b981" },
        { "slug": "on-secondary",    "name": "On Secondary",    "color": "#0f172a" },
        { "slug": "success",         "name": "Success",         "color": "#16a34a" },
        { "slug": "warning",         "name": "Warning",         "color": "#f59e0b" },
        { "slug": "error",           "name": "Error",           "color": "#dc2626" },
        { "slug": "on-status",       "name": "On Status",       "color": "#ffffff" },
        { "slug": "outline",         "name": "Outline",         "color": "#e2e8f0" }
      ]
    },
    "typography": {
      "fontFamilies": [
        { "slug": "display", "name": "Display", "fontFamily": "Inter, system-ui, sans-serif" },
        { "slug": "body",    "name": "Body",    "fontFamily": "Inter, system-ui, sans-serif" }
      ],
      "fontSizes": [
        { "slug": "display-lg", "name": "Display L", "size": "3rem" },
        { "slug": "body-lg",    "name": "Body L",    "size": "1.125rem" }
      ]
    }
  }
}
```

## Consuming tokens in blocks, patterns, templates

**Block supports** — reference palette slug:
```php
<!-- wp:group {"backgroundColor":"surface","textColor":"on-surface"} -->
```

**In CSS** — use the generated CSS vars:
```css
.my-card {
  background: var(--wp--preset--color--surface);
  color:      var(--wp--preset--color--on-surface);
  border:     1px solid var(--wp--preset--color--outline);
}
```

## Abstract → WP map

| Abstract       | WP palette slug  | CSS var                                    |
|----------------|------------------|--------------------------------------------|
| `background`   | `background`     | `var(--wp--preset--color--background)`     |
| `onBackground` | `on-background`  | `var(--wp--preset--color--on-background)`  |
| `primary`      | `primary`        | `var(--wp--preset--color--primary)`        |
| `onPrimary`    | `on-primary`     | `var(--wp--preset--color--on-primary)`     |
| (others follow same pattern) | | |

## Forbidden in generated WP code

- Inline hex inside blocks (`"style":{"color":{"background":"#1d4ed8"}}`)
- Custom CSS properties with raw color values
- Using "black"/"white" color keywords where `on-*` tokens exist
- Creating a new palette slug for a one-off color — if it's not in
  `theme.json` it does not ship

## Pattern-mode variant strategy (WP)

Ship a child-theme-style variant: a second `theme.json` diff file that
re-declares the `color.palette` entries (same slugs, different hex). Load
it conditionally via `add_theme_support('custom-theme-json', …)`
or a sibling child theme per client. Base `theme.json` stays as the
brand default for every other WP site.
