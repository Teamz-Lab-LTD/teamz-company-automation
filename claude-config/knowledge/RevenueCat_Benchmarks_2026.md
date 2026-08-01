# RevenueCat Benchmarks 2026 — Product-Neutral Reference

> **What this file is:** RevenueCat's published 2026 numbers, mechanisms and case studies, with **no product framing attached**. Every figure here is a category or global median from RevenueCat's own research — not a recommendation for any one app.
>
> **Why it exists separately:** [`RevenueCat_Growth_Playbook.md`](./RevenueCat_Growth_Playbook.md) applies these numbers to **one specific product** — a $79.99 / 90-day exam-prep app (NoteTube's Exam Cycle). That application is sound for that product and misleading for every other. This file holds the evidence; the Playbook holds one worked example of using it.
>
> **How to use it:** Read the TRIPWIRES section first — it is the part that should stop you. Then read only the section you need. Never read cover-to-cover.
>
> **Related:** [`Shipaton_2026_Knowledge_Base.md`](./Shipaton_2026_Knowledge_Base.md) §9.2 (locked monetization decisions) · [`GENERIC-ASSET-INDEX.md`](./GENERIC-ASSET-INDEX.md) (what transfers between apps)

**Last updated:** 2026-08-01 · **Refresh trigger:** next annual *State of Subscription Apps* publication.

---

## TRIPWIRES — stop and cite before proceeding

These exist because an agent working on a feature will not spontaneously remember a benchmark. If a session moves toward any row below, say so **before** writing the code, quote the number, and let the owner decide. The owner overrules any of these; an agent silently sailing past one does not.

| If the plan is… | The evidence says | Required action |
|---|---|---|
| **A free-trial toggle on an iOS paywall** | Apple is now **rejecting** these as confusing/misleading | **Hard stop.** Submission blocker, not an optimization. Replace with an explicit multi-package selector or a timeline paywall. |
| **Annual as the flagship on a goal-window product** | Yearly first renewal **25.2%** overall, **24%** Education, vs **53.2%** monthly | Challenge it. Match plan length to the goal window. |
| **A 3-day trial** | **25.5%** trial-to-paid (worst band) and **55.4%** of its cancellations land on Day 0 | Challenge it. 7 days is the practical floor. |
| **A broad freemium tier at launch** | Hard paywall **10.7%** D35 download-to-paid vs freemium **2.1%** | Challenge it. Soften later, from evidence, not on day one. |
| **A countdown timer, fake scarcity, or a progress bar on a paywall** | Virtually **absent** from high-performing paywalls | Challenge it. Also collides with the honest-paywall rule in the KB. |
| **Login/registration before the user has seen value** | Coconote removed a **10%** drop-off by moving login after the paywall | Challenge it. |
| **"Let users explore, paywall them later"** | **>80%** of trials start immediately after install; nearly all trial starts are Day 0 | Challenge it. The onboarding paywall is where the volume is. |
| **Steering by downloads, signups, session length, or onboarding completion** | RevenueCat names these as the wrong stars | Redirect to first value, core value, download-to-trial, trial-to-paid, D35 download-to-paid, RPI. |
| **Discounting to save a canceller** | Coconote: a **trial extension** retained ~**25%** and beat a discount | Try time before price. |
| **A premium price with no trust proof** | Refund rate rises **2.7% → 3.9% → 4.5%** from low to high price tier | Require the proof, or price lower. |
| **Calling a launch successful on downloads** | Median **58 days** to $1K MRR, **109 days** to $10K; only **17.3%** of apps ever reach $1K | Reframe against paid conversion + repeat usage. |
| **Shipping Android without payment recovery** | **~32%** of Google Play cancellations are failed payments (vs ~15% Apple) | Configure grace period + recovery messaging first. |
| **Copying $79.99 / 90-day / "exam pass" from the Playbook** | That is one product's positioning, not a benchmark | Stop. Derive pricing from this file's category medians and the app's own goal window. |
| **Applying Education prices ($44.99 yr / $9.99 mo) to a non-Education app** | Education is a **premium outlier** by category | Get the correct category's medians first. |

---

## 1. Universal benchmarks (any category)

### Access model
| Metric | Hard paywall | Freemium |
|---|---:|---:|
| D35 download-to-paid (median) | **10.7%** (UQ >20%) | **2.1%** |
| D60 revenue per install | **$3.09** | **$0.38** |
| 1-year subscriber retention | ~**27%** | ~**28%** |

The retention row is the one people miss: hard paywalls are a **conversion and cash-flow** choice, not a retention improvement. Both models keep roughly the same share of the subscribers they get.

### Trials
| Trial length | Trial-to-paid (median) |
|---|---:|
| ≤ 4 days | **25.5%** |
| 5–9 days | **37.4%** (UQ **52.8%**) |
| 17–32 days | **42.5%** |

Longer converts better **in aggregate**. RevenueCat's tactical guidance overrides the aggregate: match trial length to **time-to-value and usage cadence**, not to this table.

- **3–7 days** — quick-value utilities and games
- **7–14 days** — daily-use habit products
- **14–30 days** — low-frequency or complex tools

Documented counter-case: a **14-day trial lost to a 7-day trial** because the longer window raised trial starts without improving activation. Users postponed rather than engaged.

**Cancellation timing** (share of that trial's cancellations occurring on Day 0):

| Trial | Day 0 | Days 0–1 |
|---|---:|---:|
| 3-day | **55.4%** | **84%** |
| 7-day | **39.8%** | **64%** |
| 14-day | **35.7%** | — |
| 30-day | **31.1%** | — |

These describe **when cancellations happen**, not what share of trialists cancel. Most Day-0 cancellers are not bad-intent — they are people afraid of forgetting the charge. That is a communication problem, and it is solvable.

### Funnel medians
| Metric | iOS | Google Play |
|---|---:|---:|
| Trial-to-paid | **32.0%** | **32.5%** |
| D35 download-to-paid | **2.6%** | **0.9%** |

### Revenue per install
| Metric | Median |
|---|---:|
| D14 RPI | **$0.23** |
| D60 RPI | **$0.34** |
| D60 RPI — North America | **$0.55** |
| D60 RPI — India / SEA | **$0.11** |

RPI at D14/D60 is the fastest honest economic signal in a launch window. Long-horizon LTV cannot be known in two months; do not pretend otherwise.

### Renewals
- First **monthly** renewal: **53.2%** median
- First **yearly** renewal: **25.2%** median
- The **first** renewal is always the weakest; rates improve among those who survive it.

### Refunds
| Price tier | Refund rate (median) |
|---|---:|
| Low | **2.7%** |
| Mid | **3.9%** |
| High | **4.5%** |

Above ~**5%** is a trust, value, or accidental-purchase problem. Premium pricing works, but it buys refund pressure along with the revenue. Separately: high-priced apps show **~2.8%** D35 download-to-paid vs **~1.4%** for low-priced — which more likely reflects that strong differentiated products sustain both, rather than proving a price rise causes a conversion rise.

### Involuntary churn
- **~32%** of Google Play cancellations are **failed payments**
- **~15%** on Apple

On Android, a third of your churn is a billing configuration problem, not a product problem. Grace periods and payment recovery outrank win-back campaigns.

### Timing reality
- **>80%** of trials start immediately after install; nearly all trial starts happen on **Day 0**
- Median **58 days** to reach $1K monthly revenue; **109 days** to $10K
- Only **17.3%** of apps ever reach $1K/mo; **4.6%** reach $10K/mo

### Paywall structure (what high performers actually do)
- **Two-plan** paywalls: **41–60%** of category distributions
- **74.5%** highlight pricing
- **54%** include free-trial messaging
- **"Continue"** dominates CTA copy across categories
- Countdown timers and progress bars: **virtually absent**

### Regional price medians
| Region | Monthly | Annual |
|---|---:|---:|
| North America | ~$9.99 | ~$39.99 |
| Asia-Pacific | ~$6.72 | — |
| India / SEA | ~$3.75 | ~$18.32 |

A single currency conversion will not maximize both conversion and revenue globally.

**Dataset:** 2026 *State of Subscription Apps* covers 115,000+ apps and $16B in revenue. Everything above is a **category-level median**, not a law.

---

## 2. Category-specific — Education

**Do not apply these to a non-Education app.** Listed because the Playbook's product sits here and because Education's *shape* (see §4) generalizes even where its *numbers* do not.

| Metric | Education |
|---|---:|
| Monthly price median | **$9.99** (category-leading) |
| Yearly price median | **$44.99** (highest of any category) |
| First **monthly** renewal | **56%** (UQ **66%**) |
| First **weekly** renewal | **58%** |
| First **annual** renewal | **24%** |
| D30 download-to-trial | **6.5%** |
| D35 download-to-paid (iOS) | **3.1%** |
| Same-day trial start share | **78.5%** (lowest category) |
| Trials in the 5–9 day band | **50.3%** |
| Paywalls that scroll | **72%** |
| D14 RPI | **$0.30** |

RevenueCat has **no published quarterly (90-day) Education benchmark.** Any quarterly recommendation anywhere in this knowledge base is inference, not measurement.

---

## 3. Compliance — things that get a build rejected

**Free-trial toggle paywalls are being rejected by Apple** as confusing and misleading. This is current App Review behaviour, not a style preference.

Approved replacements:
- An explicit **multi-package selector** where each plan states plainly whether a trial is included
- A **timeline-style paywall** showing what happens on each day of the trial and when the charge lands

Supporting evidence that transparency is also a conversion lever, not just a compliance tax:
- **Blinkist** honest-timeline paywall: **+23% conversion**, **−55% complaints**
- **Duolingo**: removing uncertainty around the purchase converts better than selling harder

> **Where this risk actually lives:** if your paywalls are RevenueCat-hosted, the toggle is configured in the **RevenueCat dashboard**, not in your app code. Grepping the repo will find nothing. Check the dashboard.

---

## 4. Mechanisms that transfer between products

These are the parts of the research that are **not** category-bound. They are the reusable half.

### Goal-window matching
Education renews at **24% annually** but **56% monthly** because people buy against a finite goal — a semester, an exam, a language sprint. The transferable rule is not "education is different." It is:

> **Match plan duration to the user's goal window.** Where the need has a natural endpoint within 3–6 months, monthly or a fixed-term pass serves both sides better than forcing an annual commitment.

This also applies where the brand is **new and trust is still being built**, independent of category.

### First value vs core value
- **First value** — the first moment the product proves it understood the problem. Prevents early abandonment.
- **Core value** — repeat behaviour across sessions/days. This is the one that predicts retention.

Define both **app-specifically**. There is no benchmark for either, and that is the point: signups and session length are proxies that look healthy while meaning nothing.

### Micro-commitment before the paywall
A screen asking the user to affirm intent immediately before the purchase screen (Flo, Headway, Duolingo). One documented case **doubled D30 retention**. The mechanism is identity formation — after "I'm doing this," the paywall reads as the continuation of a decision rather than an interruption.

Note the distinction: this is **not** a settings step ("pick your reminder time"). It is an affirmation.

### Defer the account
Do not force login before value is clear. Coconote moved login to **after the paywall** and removed a **10% drop-off**.

### The trial reminder triad
1. **Same-day activation nudge**
2. **Two-days-before-expiry reminder**
3. **Clear "ends today" message on the final day**

Framed by RevenueCat as trust-building and involuntary-churn-reducing — a conversion tool, not support hygiene.

### Onboarding length is not the variable
Coconote **doubled** onboarding to 15 screens and trial starts rose **16%**, because the longer flow was more personalized. The lesson is not "add screens." It is: remove **administrative** friction, keep **personalizing** friction.

### Test order
1. Price
2. Subscription duration and duration mix
3. Trial presence and length
4. Offer type
5. Layout, copy, visual details

Commercial proposition before cosmetics. Evaluate price tests on revenue, cancellation and projected revenue — never conversion alone.

### Price framing
Express large commitments in smaller units and anchor against a higher or longer option. One documented regional case: framing a yearly plan as "just $X per month" produced **+30% trial starts** and **+10% yearly take rate** with **no** trial-to-paid penalty.

### Paywall as a system, not a screen
- **Onboarding paywall** — where the majority of trial starts happen (Mojo: ~**50%**)
- **Always-available upgrade route** — for users who convince themselves later (Avast: **+10–20%** revenue, net of cannibalization)
- **Contextual paywalls** — at real feature limits
- **Campaign/event-triggered paywalls** — Mojo: **15%** of new iOS revenue

### Early growth order
User research → product differentiation → onboarding/activation → **only then** performance marketing. Paid acquisition is not the early bottleneck.

Organic playbook that is documented to work without ad budget: niche Reddit communities, Discords and specialized forums; **micro-creators (5K–10K followers)** chosen for content skill over audience size; founder-level responsiveness to early users. Coconote reached **$1M ARR in 4 months with no paid ads** using ~25 part-time creators on this thesis.

### ASO is conversion optimization
- App name/title carries the strongest keyword weight
- Icon is critical — newer apps cannot win on awareness, so they must win on conversion
- Screenshots lead with **benefits over features** and tell a story
- Test store assets with **Apple Product Page Optimization** and **Google Play Store Experiments**
- Ratings below **4.0** measurably hurt conversion

---

## 5. Case studies — hypotheses, not laws

Every item here is a single company's result under its own conditions. Use them to generate experiments, never as expected uplift.

| Case | Result | The catch |
|---|---|---|
| **Natal** — removed the free trial from monthly | Monthly **+2,000%**, quarterly **+46%**, annual **+21%** | Mature brand with years of audience trust. Do not expect this on a new app. It does prove "every plan needs a trial" is testable. |
| **Coconote** — 25 part-time micro-creators | **$1M ARR in 4 months**, no paid ads | Substantially larger operation than most indie launches. |
| **Coconote** — trial extension offered at cancellation | Retained ~**25%**, beat a discount | Offer selectively by cancellation reason, not to everyone. |
| **Coconote** — onboarding 15 screens, login after paywall | Trial starts **+16%**, drop-off **−10%** | The personalization did the work, not the screen count. |
| **Blinkist** — honest timeline paywall | **+23%** conversion, **−55%** complaints | — |
| **Mojo** — hid monthly behind "View all plans" | More flagship take-up, **small** overall conversion loss | A real trade-off, not a free win. Hiding plans early conceals objections you need to hear. |
| **Mojo** — annual expressed as monthly equivalent | Higher revenue per paywall impression | — |
| **Avast** — direct upgrade button | **+10–20%** revenue after cannibalization | — |
| **Sub Club case** — free product + 7-day trial of the best tier | **+75%** LTV per user | Paired with pricing *and* packaging changes. Presented as a case study, explicitly not a benchmark. The honest counterweight to the hard-paywall row in §1. |
| **Duolingo** — clear trial timeline | Converts better than pushing harder | — |

---

## 6. Provenance and known gaps

**Read this before citing anything above as fact.**

- These numbers come from **two separate deep-research runs** of the *same* prompt: "RevenueCat growth playbook for a 90-day exam-prep subscription app." Run 1 (2026-07-28) produced `RevenueCat_Growth_Playbook.md`. Run 2 (2026-08-01) produced a second report with substantially overlapping content plus ~12 figures the first run missed. This file is the union, stripped of the exam framing.
- **Raw source, archived verbatim:** [`sources/2026-08-01-chatgpt-deep-research-revenuecat-60day-launch.md`](./sources/2026-08-01-chatgpt-deep-research-revenuecat-60day-launch.md). Go there to check what a figure actually said before it was distilled. That file is never edited to reflect new findings — corrections belong here.
- **Run 1's raw output was never archived.** `RevenueCat_Growth_Playbook.md` is a distillation of a research run whose source document does not exist in this repo, so its run-1-only figures cannot be re-checked either. If that original is recoverable, it belongs in `sources/` as `2026-07-28-*`.
- **Run 2's inline citations are corrupted** in the delivered file (mangled `turnNviewN` markers). The figures are internally consistent with run 1 and with RevenueCat's published source index, but **run-2-only numbers are unverified against source.** Those are: D14/D60 RPI medians, time-to-$1K/$10K, Education D30 download-to-trial, Education D35, Education same-day-trial share, the 50.3% trial-band figure, the 72% scrollable figure, the paywall distribution percentages, refund-by-tier, and the toggle-paywall rejection.
- **Verify the toggle-paywall claim directly** against Apple's current App Review guidelines before treating it as a submission blocker. It is the highest-stakes item here and it rests on a single unverified citation.
- Both runs were prompted for an exam-prep product. Nothing here was researched for a **non-Education** app. The category tables in §2 do not transfer; §1 and §4 do.
- **No quarterly (90-day) renewal benchmark exists** in any category. Every quarterly claim in this knowledge base is inference.
- RevenueCat's source index lives at the bottom of `RevenueCat_Growth_Playbook.md` (20 URLs) and covers both runs.

### Deliberately not covered
Web-to-app funnels and web checkout · video paywalls · lifetime subscriptions · AI/hybrid monetization economics · paid-acquisition optimization · advanced win-back and reactivation · seasonal/Black Friday discounting · large-scale freemium case studies that depend on mature brands · organizational advice on growth hiring.

Each was excluded because it requires either an ad budget, a web funnel, or an audience none of these apps has yet. Revisit when one of those becomes true.
