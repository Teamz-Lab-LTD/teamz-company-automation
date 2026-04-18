# Flutter mapping — team_mvp_kit consumers

## How to reach tokens in code

Always access the design system through `context`:

```dart
final ds = context.designSystem;         // TeamzLabDesignSystem
final ty = context.teamzLabTypography;   // typography scale

Container(
  color: ds.primary,
  child: OnColor(
    background: ds.primary,
    child: Text('Hi', style: ty.bodyLarge),
  ),
);
```

## Abstract → Flutter token map

| Abstract           | Flutter code                     | Widget helper to prefer                 |
|--------------------|----------------------------------|-----------------------------------------|
| `background`       | `ds.background`                  | wrap with `OnColor(background: ds.background)` |
| `onBackground`     | auto from `OnColor` OR `ds.onBackground` | — |
| `surface`          | `ds.surface`                     | `OnColor`, `TeamzSection` |
| `onSurface`        | auto OR `ds.onSurface`           | — |
| `primary`          | `ds.primary`                     | `CommonButton(type: ButtonType.primary)` |
| `onPrimary`        | auto via `OnColor(background: ds.primary)` | — |
| `secondary`        | `ds.secondary`                   | `CommonButton(type: ButtonType.secondary)` |
| `success/warning/error` | `ds.success` etc.           | `WarningMessageCard`, `SnackBarHelpers.success(...)` |
| `outline`          | `ds.outline`                     | dividers via `TeamzSection.divider` |
| typography `displayLarge` | `ty.displayLarge`          | — |
| typography `bodyLarge`    | `ty.bodyLarge`             | — |
| spacing `md`       | `16` (literal is fine here, spacing is consistent) | `const SizedBox(height: 16)` |

## Widget primitives you should default to

| Instead of            | Prefer                                      |
|-----------------------|---------------------------------------------|
| `MaterialApp.router`  | `ThemedMaterialAppRouter` (kit) when the kit provides one; otherwise keep `MaterialApp.router` with `TeamzLabDesignSystem.defaultLightTheme` / `defaultDarkTheme` |
| `Scaffold(...)` | `TeamzScreenScaffold(...)` |
| `AppBar(...)`         | `TeamzAppBar(...)`                          |
| `ElevatedButton`      | `CommonButton`                              |
| `TextField`           | `CustomEditText` (or one of the typed variants — `OtpInputField`, `PhoneNumberField`, etc., imported explicitly) |
| `FloatingActionButton`| `TeamzFab`                                  |
| bottom sheet          | `TeamzModal.bottomSheet(...)`, `TeamzSelectionSheet` |
| `SnackBar(...)`       | `SnackBarHelpers.success/error/info(context, …)` |
| `AlertDialog`         | `TeamzModal.alert(...)`                     |
| `Container` with decoration | `TeamzSection(...)` for grouping content cards |

## Forbidden in generated code

- `Color(0xFF...)` literals
- `Colors.red`, `Colors.grey[300]`, etc.
- `TextStyle(fontFamily: '…', color: …)` — use `ty.*` from `context.teamzLabTypography`
- Raw `Text('…')` of user-visible strings — go through `context.appText.<key>` (app-level l10n)
- Raw `Text("…")` — same
- Setting a background color without pairing it with `OnColor` or the matching `on*` foreground

## Pattern-mode variant file template

When the user asks for an app-specific style, don't inline overrides.
Emit a variant file at `lib/src/shared/design_system/variants/`:

```dart
// lib/src/shared/design_system/variants/serenity_spa_variant.dart
import 'package:team_mvp_kit/team_mvp_kit.dart';

/// Wellness/spa-oriented variant.
///
/// Overrides: primary (soft pink), secondary (sage green), display font
/// (Cormorant Garamond). Every on-* pair and every other token stays
/// inherited from [TeamzLabDesignSystem].
class SerenitySpaVariant extends TeamzLabDesignSystem {
  const SerenitySpaVariant();

  @override
  Color get primary   => const Color(0xFFE8B4B8); // soft pink
  @override
  Color get secondary => const Color(0xFFA8D5BA); // sage green
  // onPrimary / onSecondary stay inherited — contrast is auto-tuned.
}
```

Wire it at `AppInitializer.createApp(customDesignSystem: const SerenitySpaVariant())`.
Base `TeamzLabDesignSystem` is untouched; every other Teamz app unaffected.
