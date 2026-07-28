# Design ship gate — run before any screen is called done

**Every item here comes from a real defect that shipped or nearly shipped.** This is not a
style opinion list; it is the accumulated set of things that were missed while someone was
paying attention to something else.

The gate has two halves. The hook (`hooks/design-ship-gate.sh`) checks what a script can check
and reports it automatically on every UI file write. The rest needs eyes, and is below.

---

## A. Automatic — the hook reports these

| Check | Why it exists |
|---|---|
| `borderRadius` on a non-uniform `Border` | Flutter asserts *"a borderRadius can only be given on borders with uniform colors"* and throws **during paint**. Shipped in Resume Coach's finding card — the flagship screen — and was found only by accident, by a test written for something else. Draw the accent as a child, not as a thick `BorderSide`. |
| Raw `Color(0x…)` / `Colors.*` in a feature file | A colour picked in place cannot follow the theme, so it is right in one mode and wrong in the other. Use the design system's tokens. |
| `Colors.white` / `Colors.black` as a foreground | The single most common contrast failure: white text on a bright surface, black text on a dark one. Take the paired `on*` token of the background instead. |
| Hardcoded `Duration(milliseconds: …)` in UI | Bypasses the motion tokens, so it ignores the OS reduce-motion flag. Use `Motion.of(context)`. |
| `AnimatedContainer` animating `width`/`height` | Re-runs layout every frame and does not port cleanly. Animate `transform`/`opacity` equivalents. |

## B. Manual — nothing can check these for you

### Contrast, both themes
- [ ] Every foreground came from its background's paired `on*` token — never a generic
      `textPrimary` on a coloured surface.
- [ ] Measured, not eyeballed: **4.5:1** body, **3:1** large text and icons.
- [ ] Checked in **light AND dark**. A token that passes in one can fail in the other.
- [ ] Includes SnackBars and dialogs — `backgroundColor: primary` with default body text is
      always unreadable, and is the classic miss.

### Touch and interaction
- [ ] Targets ≥ **44×44** (iOS) / **48×48** (Android), with ≥ **8px** between them.
- [ ] Visible pressed state. Feedback within **100ms** of the tap.
- [ ] Nothing important behind a gesture only. Every critical action has a visible control.
- [ ] Nothing critical under the notch, Dynamic Island, or gesture bar.

### Motion
- [ ] Durations come from the app's motion tokens, not from literals.
- [ ] **Reduce-motion tested.** Turn it on at OS level. The screen must still make its whole
      argument on the first frame — if it stops making sense, meaning was living in the motion
      and the static state needs fixing.
- [ ] Exit is faster than enter (~65%).
- [ ] Delete each animation in your head. If nothing is lost, it should not exist.

### Text and layout
- [ ] Body ≥ 16px on mobile. Nothing below 12px anywhere.
- [ ] Survives the largest Dynamic Type / font-scale setting without truncating meaning.
- [ ] No horizontal scroll. Wide content (tables, code, diagrams) scrolls inside its own box.
- [ ] Tested on a small phone. The illustration yields; the copy does not.

### Honesty — the one that costs the most when missed
- [ ] **Every claim on this screen is true of the code.** Not the pitch — the code path.
      Resume Coach told users *"there is nothing here to re-read"* while the text sat in
      Firestore, and *"your resume never leaves your device"* nearly went into a Play listing
      while the extracted text was going to a third-party LLM.
- [ ] No paywall, gate or ask appears **before** the screen has delivered something.
- [ ] Empty and error states say what happened and what to do — and do not blame the user for
      a gap that is ours.
- [ ] Nothing is gamified that is not actually good news.

### Ported completely
- [ ] Every screen the design prompt specified is actually ported. Prompt 3 on Resume Coach
      named three screens; one was ported and two sat untouched for two weeks because nothing
      tracked the difference.
- [ ] The reference artifact is saved in the repo under `docs/design/`.
- [ ] Tests ship with it. Widget tests are the only thing that catches a paint-time throw.

---

## Using it

At the end of any screen work, paste section B and answer it honestly. An unchecked box is a
finding, not a formality — every one of them is here because it was skipped once already.
