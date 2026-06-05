---
name: feedback-aso-screenshot-compliance
description: Apple §2.3.7 (and Play equivalent) rejects ANY pricing/subscription/discount text in screenshots — including in-app paywall UI captured by sim. Block at compose-script level before render.
metadata:
  type: feedback
---

When composing App Store screenshots (`aso-compose-screenshot.py`,
`aso-generate-batch.py`, frameit, any PIL overlay tool), REFUSE to
render any shot that contains banned pricing language ANYWHERE —
both in the overlay marketing text AND in the raw simulator
capture inside the phone frame.

**Why this rule exists (2026-06-05):** No Trace Chat shipped a
paywall screenshot for build 12 + 13 (iPhone 6.7 + iPad 12.9) with
the overlay text `$4.99` / `LIFETIME ACCESS` / `ONE PAYMENT.
NEVER EXPIRES.` AND the underlying sim capture showed the in-app
paywall page with `$4.99`, `Get Premium - $4.99`, and the `Get
Lifetime Access` CTA. Apple rejected v1.0.2 under §2.3.7 — "The app
screenshots include references to the price of the app or the
service it provides." That cost a full submission cycle even
though the binary was clean (the crash fix worked on build 13).
Apple does NOT distinguish between overlay marketing text and
genuine in-app UI — pricing visible anywhere in the screenshot
frame triggers the rejection.

**How to apply:**

Two checks fire BEFORE any image is rendered.

**Check 1 — overlay text ban list (`hero` + `subtitle` fields):**

- Any currency amount: `$\d`, `€\d`, `£\d`, `¥\d`, `₹\d` etc. — including `"$4.99"`, `"USD 4.99"`, `"4.99 USD"`
- Lifetime / permanence claim implying purchase: `LIFETIME`, `FOREVER`, `NEVER EXPIRES`, `ONE PAYMENT`, `ONE-TIME`, `PAY ONCE`
- Subscription / trial: `SUBSCRIPTION`, `SUBSCRIBE`, `MONTHLY`, `WEEKLY`, `YEARLY`, `FREE TRIAL`, `TRIAL`, `RENEW`, `7 DAYS FREE`
- Direct purchase CTA: `BUY`, `BUY NOW`, `GET FOR`, `PURCHASE`, `PAY`
- Discount language: `OFF`, `SAVE`, `% OFF`, `DISCOUNT`, `LIMITED TIME`, `SALE`

**Check 2 — raw screenshot subject ban (the `raw` field):**

- If the raw sim capture filename or path contains `paywall`,
  `pricing`, `subscription`, `iap`, `upgrade-modal`, `premium-cta`,
  refuse the slot. The user can either pick a different raw
  screenshot OR re-capture the paywall page with the price
  portion blacked out / replaced with `PREMIUM` placeholder
  before re-attempting.
- For ANY raw screenshot, if the underlying app surface contains
  visible pricing (best signaled by the filename heuristic above
  OR explicit user note in the preset), surface a warning and
  list the surface — never silently render.

**Compliant alternatives** (use these for the marketing overlay):

- `UNLIMITED MESSAGES.` / `NO LIMITS.` / `FULL CHAT.`
- `UNLOCK FULL CHAT.` / `PREMIUM.` / `UPGRADE.`
- `NO ADS. NO TRACE.`
- Feature names: `END-TO-END ENCRYPTED.` / `DISAPPEARING.` / `QR CODE.`
- Sentiment without price: `SUPPORT THE TEAM.`

**Compliant alternative for the paywall slot itself:**

Replace it with a FEATURE slot instead. Apple does not require a
paywall screenshot — the IAP product page in ASC already shows the
price. Showing the paywall in the marketing carousel adds zero new
info and triggers §2.3.7. Common safe replacements: privacy
settings, code-share UI, chat-in-action, QR scan, onboarding card.

**When refusing, emit:**

- The banned phrase verbatim AND the rule key that caught it
- The slot name + filename
- A short list of compliant rewrites the user can approve
- Do NOT silently re-word and proceed — the user picks the
  replacement

**Scope:** Apple §2.3.7 explicitly. Play Store rejections for
in-app pricing in screenshots are MUCH rarer — most NTC-class apps
ship the same paywall screenshot on Play without issue. Still safe
to apply the same hygiene to Play presets, but the primary
trigger and risk live on the Apple side. (User confirmed 2026-06-05
that Play did not reject NTC for this.)

Related rules: [[feedback-aso-winnability-first]] (RULE-001) — keyword
competitiveness; [[aso_cadence]] — when to ship a fresh metadata pass.
This rule is RULE-002 in the ASO ruleset.
