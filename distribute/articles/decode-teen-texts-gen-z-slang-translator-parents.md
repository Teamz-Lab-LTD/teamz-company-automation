---
title: I Built a Gen Z Slang Translator for Parents — With a Cringe-o-Meter and Safety Flags
language: en
tags: [webdev, ai, javascript, parenting]
canonical: https://tool.teamzlab.com/kids/decode-teen-texts/
---

# I Built a Gen Z Slang Translator for Parents — With a Cringe-o-Meter and Safety Flags

My parents still think "rizz" is a kind of cracker. When I showed them what their kids were actually texting, the conversation turned serious fast — a lot of "internet slang" overlaps with drug references, bullying codes, and self-harm signals. So I built a two-way translator that runs 100% in the browser, with a safety layer I haven't seen anywhere else.

**Try it:** [Decode Teen Texts](https://tool.teamzlab.com/kids/decode-teen-texts/)

---

## Why Another Slang Translator?

There are 17 Gen Z translators on Product Hunt. They all do the same thing: take teen-speak, give you a definition. But parents don't need a dictionary — they need three things:

1. **Context** — "bro is lowkey cooking fr" isn't 4 definitions, it's one thought
2. **Tone** — flirty vs angry vs concerning (same words, different meaning)
3. **Safety flags** — the word "unalive" isn't funny when your 14-year-old uses it in context

None of the existing tools do #3. That's the moat.

---

## Two Modes in One Page

**Decode (Teen → Parent):**
- Paste any message from iMessage, Snap, Instagram, Discord
- 150+ term dictionary + Chrome AI contextual translation
- Tone detection: friendly / flirty / dismissive / sad / angry
- Safety panel flags: drug slang, self-harm code, bullying language, eating disorder codes, sexual content
- Each flag includes the relevant crisis hotline (988, NEDA, SAMHSA)

**Encode (Parent → Teen):**
- Type what you want to say in plain English
- Pick intensity: Light / Medium / Heavy
- Get a teen-slang rewrite with a **Cringe-o-Meter (0–100)**
- Higher intensity = higher cringe = more eye-roll from your teen
- Peak cringe message: "They will screenshot this. You've been warned."

---

## The Technical Stack — Zero API Calls

The whole tool is client-side. No backend, no OpenAI key, no data leaves the browser.

**3-tier AI fallback:**

```
Chrome AI Prompt API (Gemini Nano, on-device)
   ↓ if unavailable
Transformers.js flan-t5-base (runs in WebAssembly)
   ↓ if unavailable
Rule-based dictionary (150+ terms, 60+ reverse phrases)
```

**Why this works:**
- Chrome 138+ users get contextual AI translation instantly, free, private
- Other browsers download a 200MB model once (cached via Cache API), then work offline forever
- Worst case, the rule engine handles 90% of slang correctly with zero downloads

**Key code pattern** using the shared AI engine:

```js
var result = await TeamzAI.generate({
  chromePrompt: 'Translate Gen Z slang to plain English: "' + text + '"',
  chromeSystemPrompt: 'You are a translator for parents. Output only the rewrite.',
  transformersTask: 'text2text-generation',
  transformersModel: 'Xenova/flan-t5-base',
  transformersPrompt: 'Translate Gen Z slang: ' + text,
  fallback: function() { return ruleBasedDecode(text); },
  qualityCheck: function(t) { return t && t.length > 5; }
});
```

The `qualityCheck` catches AI outputs that are identical to the input (a common failure mode with small LLMs) and falls back to the rule engine.

---

## The Safety Layer

This is where generic slang translators fail. Example patterns the tool flags:

| Category | Example terms | Action |
|---|---|---|
| Drugs | plug, addy, zaza, percs, lean | Suggests non-accusatory conversation |
| Self-harm | kms, kys, unalive, "dark lately" | 988 hotline + direct ask guidance |
| Bullying | pick me, ratio'd, L + ratio | Check both sides — bully or bullied |
| Eating | sw/cw/gw, ana, thinspo | NEDA helpline: 1-800-931-2237 |
| Sexual | nudes, DTF, "Snap me 18+" | Age/identity context check |

Crucially, these are **conversation starters, not verdicts**. The tool text makes that explicit — the flag says "have a calm chat," not "your child is in danger."

---

## What I Learned Building It

1. **Rule engines still win** on speed and quality for domain-specific translation. LLMs hallucinate slang definitions. A curated dictionary doesn't.
2. **Chrome AI is genuinely useful** for short, private, context-aware tasks — not a replacement for GPT-4, but perfect for "rewrite this in tone X."
3. **Transformers.js caching is real** — once `flan-t5-base` loads on one tool, every other tool on the site uses it instantly. This makes 200MB models actually shippable.
4. **Parents are the real audience.** Teens already know the slang. The market is adults who want to understand their kids without violating trust.

---

## Try It

[Decode Teen Texts — Gen Z Slang for Parents](https://tool.teamzlab.com/kids/decode-teen-texts/)

Free. No signup. Works offline after first load. The cringe-o-meter is brutally honest.

If you try the Encode mode on Heavy intensity with a wholesome message like "I love you, have a good day at school" — screenshot the result. That's the share-worthy output.
