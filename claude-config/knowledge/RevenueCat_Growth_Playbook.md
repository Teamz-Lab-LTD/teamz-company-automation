# RevenueCat Growth Playbook — Evidence Companion

> **What this file is:** The full research report distilling RevenueCat's growth content (2026 State of Subscription Apps, growth blog, Sub Club case studies) for a 90-day exam-prep subscription app. Compiled Jul 28, 2026 via research run; sources linked throughout.
>
> **How to use it:** This is the STATIC EVIDENCE APPENDIX to the Shipaton 2026 Knowledge Base. The book's §9.2.1 holds the locked decisions; come here only when you need the "why," a benchmark's context, or a case study. Read task-attached (15 min per decision), never cover-to-cover. Principles are evergreen; refresh benchmark numbers when the next annual State of Subscription Apps report publishes.

---

## Executive decision

Your strongest launch configuration is:

* **Primary offer:** 90-day exam-preparation plan, positioned around completing a defined outcome rather than accessing generic educational content.
* **Fallback:** monthly plan with a lower upfront price, but a meaningfully higher three-month total.
* **Trial:** initially seven days on the 90-day plan only.
* **Access model:** one useful personalized result before an onboarding paywall, followed by a hard gate on the complete study programme.
* **Paywall:** two plans, one clearly recommended, with no weekly or annual option during the first 60 days.
* **Growth:** exam-specific organic content, small creators and direct student support—not broad paid acquisition.
* **First experiment:** the price and packaging of the 90-day offer, not cosmetic paywall changes.

RevenueCat's data supports plans that match Education users' finite goals: Education has only **24% median first renewal on annual plans**, compared with **56% monthly and 58% weekly**. RevenueCat explicitly attributes this pattern to education goals such as a semester, exam or language-learning period. However, RevenueCat does not publish a specific conversion benchmark for 90-day plans, so quarterly recommendations below are an evidence-based inference rather than a direct benchmark.

RevenueCat's 2026 report covers more than 115,000 apps and $16 billion in revenue, but its figures are category-level benchmarks. Coconote, Natal, Mojo and other Sub Club examples are individual-company experiments: use them as hypotheses to test, not universal laws.

---

## 1. Pricing

### Your price is premium—even for Education

RevenueCat reports a **$44.99 median annual price for Education apps**. Your proposed **$79.99 for only 90 days** therefore sits far above the category's normal time-adjusted pricing. That does not automatically make it wrong: exam preparation can carry much higher willingness to pay than general learning, especially where passing produces a clear academic or career payoff. But the app must sell a credible outcome—"be ready for the exam"—rather than a collection of videos, questions or AI features.

RevenueCat's cross-category data also suggests that higher prices can outperform timid pricing. High-priced apps recorded approximately **2.8% median Day-35 download-to-paid conversion**, compared with 1.4% for low-priced apps, and higher trial-to-paid conversion and realized lifetime value. This does not prove that raising a specific app's price will improve conversion; it more likely indicates that strong, differentiated products can sustain both premium prices and stronger monetization.

### The monthly plan must be lower upfront—not cheaper overall

A monthly option should remove commitment friction without destroying the logic of the 90-day plan. For example:

* **90 days: $79.99**, equivalent to about $26.66 per month.
* **Monthly: $34.99–$39.99**, or $104.97–$119.97 over three months.

At $39.99 monthly, the flagship saves approximately 33% across the expected exam-preparation period. At $9.99 or $14.99 monthly, the "premium" 90-day option would cost considerably more than buying three months separately, making the anchor self-defeating.

RevenueCat advises testing the duration mix—not just the nominal price—because the alternatives shown beside a plan change its perceived value. Its guidance recommends making the preferred plan visibly better while retaining a lower-commitment choice for users who are not ready for the larger upfront payment.

### Period pass versus auto-renewing subscription

The best evidence supporting your 90-day concept is Education's goal-bound retention pattern. RevenueCat says short-term education plans work because they match how long users expect to need the product. Its newer monthly-plan guidance similarly recommends monthly or quarterly billing when the use case has a natural endpoint within three to six months or when the product is still pre-product-market-fit.

RevenueCat does **not** provide a direct comparison between:

1. a non-renewing 90-day access pass; and
2. an automatically renewing three-month subscription.

Commercially, a non-renewing pass better matches "prepare for this exam," reduces subscription anxiety and makes the $79.99 payment easier to explain. An auto-renewing three-month product produces recurring revenue but may be mismatched once the student has completed the exam. Google Play prepaid plans, for example, require the user to extend access manually and do not have the grace-period, account-hold or pause lifecycle of auto-renewing subscriptions.

For the first launch, present the product as **"90-Day Exam Access"** regardless of the underlying store configuration. If it auto-renews, the renewal must be unmistakably disclosed. Once enough users reach the end of the programme, test whether they actually want another exam cycle, continuing practice or a different course before relying on renewals.

### Regional pricing

RevenueCat's general medians vary dramatically by region. Its reported monthly medians include approximately $9.99 in North America, $6.72 in Asia-Pacific and $3.75 in India/Southeast Asia; annual medians range from about $39.99 in North America to $18.32 in India/Southeast Asia. A single direct currency conversion is therefore unlikely to maximize both conversion and revenue globally.

### DO THIS

* Launch with **two visible plans only**: $79.99/90 days as "Best for exam readiness," and approximately $34.99–$39.99 monthly as the lower-upfront fallback.
* Run the first pricing experiment on the flagship—such as **$59.99 versus $79.99**—while keeping the monthly anchor unchanged.
* Describe the purchase as a defined transformation: **"Complete your personalized 90-day preparation plan,"** not "unlock premium features."

---

## 2. Free trials

### Use a trial—but not a three-day one

RevenueCat's 2026 benchmarks show:

* Trials of four days or less: **25.5% median trial-to-paid conversion**.
* Five-to-nine-day trials: approximately **37.4%**.
* Seventeen-to-32-day trials: approximately **42.5%**.

Longer trials therefore convert better in aggregate, but RevenueCat warns that conversion alone is not the objective. A longer trial can encourage procrastination and produce worse activation, retention or revenue even when it generates more starts. In one cited experiment, a 14-day trial underperformed seven days because users postponed the behaviours that actually created value.

Three-day trials create particularly severe buyer anxiety. More than 55% of cancellations from three-day trials happen on Day 0, and 84% happen during Days 0–1. For seven-day trials, 64% of cancellations happen in that same initial window. These percentages describe the timing of cancellations, not the percentage of all trial users who cancel.

Education apps generally cluster around five-to-nine-day trials because users need repeated engagement to see progress. RevenueCat's practical framework recommends **seven to 14 days for daily-use products that need time for habit formation**.

### Trial only the 90-day plan initially

A useful structure is:

* **90-day plan:** seven-day trial.
* **Monthly plan:** immediate payment, no free trial.

This makes the flagship feel safer without giving away a large proportion of the already-short monthly period. It also creates a meaningful packaging difference rather than offering identical terms at two prices.

The approach has some support from Natal's Sub Club case study. Natal removed the free trial specifically from its monthly offer; monthly subscriptions increased 2,000%, quarterly subscriptions 46% and annual subscriptions 21%. That result came from a highly trusted brand with years of audience development, so it should not be treated as an expected uplift for a new exam-prep app. It does, however, demonstrate that "every plan requires a trial" is an assumption worth testing.

### Hard paywall or soft paywall?

Across RevenueCat's dataset, hard-paywall apps reach **10.7% median Day-35 download-to-paid conversion**, compared with **2.1% for freemium apps**. Their median Day-60 revenue per install is approximately **$3.09 versus $0.38**. One-year subscriber retention is nearly equal, at approximately 27% for hard paywalls and 28% for freemium. RevenueCat therefore frames the hard-paywall decision primarily as a conversion and cash-flow choice, not a retention improvement.

A completely cold hard paywall is risky at $79.99. Your better version is a **value-first hard gate**:

1. Ask the student's exam, date, target score and weak subjects.
2. Run a short diagnostic.
3. Reveal a personalized readiness score and high-level study roadmap.
4. Paywall the full 90-day schedule, explanations, mock exams and progress tracking.

This gives users evidence that the app understands their problem without turning the product into an open-ended freemium service.

### DO THIS

* Start with a **seven-day trial on the 90-day plan only**; do not launch with a three-day trial.
* Let the student see one personalized diagnostic result, then place a hard gate before the complete study programme.
* After obtaining sufficient volume, test **seven versus 14 days** using paid conversion, D30 revenue and core-value activation—not trial starts alone.

---

## 3. Paywall design

### Recommended structure

RevenueCat's paywall research shows that high-performing paywalls commonly:

* highlight one preferred price;
* show multiple—but usually few—options;
* include a short benefit list;
* clearly state trial terms;
* show discounts or equivalent monthly pricing;
* use a straightforward CTA such as "Continue."

Countdown timers and progress bars appear very rarely and are not foundational paywall elements. RevenueCat also notes that two-plan paywalls are the most common configuration across categories, while adding more options can create choice overload.

A strong first version:

> **Be ready for [Exam] in 90 days**
> Get a daily plan based on your exam date, target score and weak topics.
>
> ✓ Personalized daily study plan
> ✓ Full mock exams with explanations
> ✓ Weak-topic tracking and revision reminders
>
> **90-Day Exam Plan — $79.99**
> *Recommended · 7 days free · then $79.99*
>
> Monthly Flex — $39.99/month
> *No free trial*
>
> **Start My 7-Day Trial**
>
> Cancel anytime. You will be charged on [localized date]. Subscription terms apply.

Use localized store-price variables rather than placing fixed prices inside graphics or remote text.

### Where to place it

RevenueCat recommends an onboarding paywall because users are at their highest intent immediately after installation. At Mojo, approximately half of trial starts came from onboarding. Contextual paywalls remain useful when users later attempt mock exams, advanced explanations or additional subject modules. A permanently visible "Upgrade" or "Get full access" route also captures users who become ready without encountering a gated feature; an Avast example attributed a 10–20% revenue increase to adding a direct upgrade route.

For this app, the primary paywall should appear after the personalized diagnostic—not before the student has supplied any information and not after several unrestricted study sessions.

### What RevenueCat's experiments imply

RevenueCat recommends testing in roughly this order:

1. Price.
2. Subscription duration and duration mix.
3. Trial presence and length.
4. Offer type.
5. Paywall layout, copy and visual details.

RevenueCat's Mojo contributor reports that even apparently strong changes frequently lose in controlled tests. Price tests should be evaluated using immediate revenue, cancellation and longer-term projected revenue—not conversion alone.

Mojo also found that hiding the monthly option behind "View all plans" increased selection of the longer plan, although it caused a small decline in overall conversion. This illustrates the trade-off between maximizing flagship-plan share and allowing transparent choice. At launch, keep both options visible; hiding plans before you understand user objections can conceal valuable learning.

### DO THIS

* Use **one screen, two options and one highlighted flagship**; avoid weekly, annual, lifetime and multiple feature tiers.
* Put the paywall immediately after the personalized readiness result, with additional contextual paywalls at mock-exam or explanation limits.
* Test the **commercial proposition first**—price, trial and plan mix—before experimenting with button colours, illustrations or long copy.

---

## 4. Onboarding and retention

### Onboarding must produce evidence, not explain features

RevenueCat reports that more than 80% of trial starts happen immediately after installation, making the first minutes disproportionately important. Its onboarding guidance says the flow should communicate the future transformation, personalize the experience and produce one clear "aha" moment before asking for payment—not provide a tour of every feature.

For exam preparation, the first-value moment should be:

> "The app has identified what I need to study and has given me a credible route to my target score."

The deeper core-value moment should require repeat behaviour, such as completing three study sessions, correcting weak-topic mistakes and seeing the readiness score improve. RevenueCat distinguishes these carefully: first value prevents immediate abandonment, while core value is the behaviour more likely to predict retention. It recommends measuring D7 retention and whether users return for sessions two and three rather than optimizing onboarding completion as an isolated metric.

### Suggested onboarding flow

1. Select exam and exam date.
2. Enter target score or result.
3. Select weak topics or confidence level.
4. Complete five-to-ten diagnostic questions.
5. Show readiness score and the three biggest gaps.
6. Preview the first seven days of the study plan.
7. Ask for a commitment: preferred study days and reminder time.
8. Show the paywall.
9. Request account creation after purchase or trial selection where technically feasible.
10. Begin the first short study session immediately.

Coconote provides a useful counterexample to "shorter onboarding is always better." Expanding its onboarding to 15 screens increased trial starts by 16%, while moving login until after the paywall removed a 10% drop-off. The lesson is not to copy 15 screens; it is to remove administrative friction while retaining questions that make the result feel genuinely personalized.

### The first week determines whether the trial works

During the seven-day trial, guide users toward a defined activation sequence:

* Day 0: diagnostic plus first study session.
* Day 1: return and complete the first weak-topic practice.
* Day 3: finish the first mini mock.
* Day 5: show measurable improvement or an updated readiness score.
* Day 6: remind the student what remains in the 90-day roadmap.
* Day 7: conversion, with clear payment timing.

A long passive trial will not create retention. RevenueCat says longer trials work only when the product actively drives repeated usage, investment and progress.

### Retention and cancellation

RevenueCat reports that the first renewal is the weakest: cross-category medians are approximately 53.2% for monthly subscriptions, while later renewal rates improve among the users who remain. For Education specifically, the first monthly renewal median is 56%.

Coconote found that adding seven extra trial days during cancellation saved 25% of would-be cancellations and outperformed a discount. This is especially relevant when a student says they were busy or had not completed enough of the diagnostic plan. A trial extension should be offered selectively by cancellation reason, not automatically to everyone.

RevenueCat's 2026 data also attributes roughly 32% of Google Play cancellations to billing failure, compared with about 15% on Apple. Configure grace periods, payment-recovery messaging and RevenueCat customer-management flows before spending time on sophisticated win-back campaigns.

### DO THIS

* Define **first value** as receiving a credible personalized roadmap and **core value** as completing at least three study sessions with measurable progress.
* Drive a seven-day activation sequence instead of merely granting seven days of unrestricted access.
* Offer a **seven-day extension**, rather than an immediate discount, to trial users who cancel because they lacked time to evaluate the app.

---

## 5. Launch and growth tactics: first 60 days

### Days 1–14: establish the learning system

Ship the smallest version that fully delivers the promised outcome: diagnostic, 90-day plan, practice, explanations, mock assessment, progress and billing. RevenueCat's launch guidance recommends releasing an MVP around the central value proposition and learning from real behaviour instead of completing every peripheral feature first.

Before launch, instrument: install source; onboarding steps; diagnostic completion; paywall views; plan selected; trial start; first and core value; cancellation; payment and refund events.

RevenueCat's pre-product-market-fit guidance says early teams should prioritize repeat core-feature usage, willingness to pay and unsolicited return behaviour—not downloads, registrations or social followers. Look for consistent patterns across at least two or three cohorts before declaring a result.

### Days 15–30: win one organic distribution channel

RevenueCat's ASO guidance emphasizes matching store metadata to user intent: the title and subtitle should name the exam and outcome; screenshots should tell a benefit-driven story; the icon and screenshot order should be tested; and reviews should be requested after users experience core value rather than immediately after opening the app.

For each major exam, build a focused listing and content cluster around searches such as:

* "[Exam] practice test"
* "[Exam] study plan"
* "[Exam] mock exam"
* "How to pass [Exam]"
* "[Exam] preparation in 90 days"

Do not target "AI education app" unless students already search that phrase. Students buy exam confidence, feedback and preparation—not the implementation technology.

For organic social growth, Coconote's case is the most relevant Sub Club example. It reached $1 million ARR in four months without paid ads by assembling approximately 25 part-time creators. It preferred skilled creators with roughly 5,000–10,000 followers over established influencers, prioritizing content quality and authenticity over audience size. This was a substantially larger operation than most indie launches, but the underlying model can be started with two or three creators producing exam-specific short-form content.

### Days 31–45: run one meaningful experiment

Choose one:

* $59.99 versus $79.99 for 90 days.
* Seven-day versus 14-day trial.
* Trial versus no trial on monthly.
* Paywall after the readiness score versus after the first practice set.

Do not run all of them simultaneously unless traffic is large enough for a factorial experiment. RevenueCat repeatedly warns that poorly powered tests and multiple changing variables can produce persuasive but unreliable results.

At the same time, speak directly with users who: purchased immediately; started but cancelled the trial; reached the paywall but did not purchase; paid but did not complete three sessions; requested a refund. The objective is to identify whether the problem is trust, affordability, unsuitable content, unclear differentiation or failure to reach value.

### Days 46–60: double down, do not broaden

Scale the exam topics, creators and store messages that produce activated students—not just installations. Release visible improvements weekly or biweekly, especially those answering recurring support questions. RevenueCat's launch and pre-PMF guidance favours rapid iteration and close customer contact over premature channel expansion.

Avoid broad freemium, additional exams, complex referral systems and paid advertising until the initial cohort shows: repeat study behaviour; acceptable trial-to-paid conversion; low refund levels; positive student feedback; evidence that users perceive the programme as worth the price.

Natal's case reinforces that conversion can be the downstream result of trust built through content and human support. Natal attributed its unusually high conversion to years of answering audience questions and keeping specialists close to customers, not merely to paywall optimization.

### DO THIS

* Spend the first month proving one exam, one audience and one organic content format—not launching multiple courses.
* Recruit **two or three small exam-content creators** and pay for repeatable output rather than one-off influencer posts.
* During Days 31–60, run one high-impact monetization test and conduct weekly interviews with converters, cancellers and non-buyers.

---

## 6. Metrics that matter

RevenueCat argues that an early app should separate leading indicators—activation, early retention and qualitative value—from lagging indicators such as mature lifetime value. Long-term LTV cannot be known reliably during a two-month launch.

| Metric | RevenueCat reference point | How to use it |
| --- | ---: | --- |
| Day-35 download-to-paid, hard paywall | 10.7% median; >20% upper quartile | Primary paid-conversion benchmark |
| Day-35 download-to-paid, freemium | 2.1% median | Comparison if access is later softened |
| Trial-to-paid, 5–9-day trial | 37.4% median; 52.8% upper quartile | Target for the seven-day flagship trial |
| Education monthly first renewal | 56% median; 66% upper quartile | Relevant to monthly fallback |
| Education annual first renewal | 24% median | Why a year-long commitment is poorly matched |
| Education weekly first renewal | 58% median | Evidence that short, goal-matched plans can retain |
| Refund rate | ~3–4% median; >5% concerning | Trust/value/accidental-purchase indicator |
| Day-60 revenue per install | $3.09 hard paywall; $0.38 freemium | Broad monetization context |
| Failed-payment share of cancellations | ~32% Google Play; ~15% Apple | Justifies payment recovery + grace periods |

These figures come from broad app populations rather than exam-prep apps, and RevenueCat does not publish an equivalent first-renewal benchmark for quarterly Education subscriptions.

### First-60-day dashboard (review weekly)

**Acquisition:** store-page view-to-install; installs by exam keyword, creator, content format; cost per activated user (even at zero cash cost).
**Activation:** diagnostic completion; % reaching readiness result; % completing first session; % completing three sessions within seven days; time to first value and core value.
**Monetization:** paywall-view-to-trial/purchase; trial-to-paid; download-to-paid at D7/D14/D35; plan mix (90-day vs monthly); revenue per install at D7/D30/D60; trial cancellation timing; refund rate; payment failure.
**Retention:** D1/D7/D30 active-study retention; monthly first renewal; % of 90-day customers disabling renewal in week one; progress toward plan completion; cancellation and refund reasons.

Do not optimize onboarding completion or study time without checking whether those behaviours predict payment and return usage. RevenueCat warns these can become volume metrics that look healthy while failing to represent meaningful activation.

### DO THIS

* Make **three sessions completed within seven days** the initial core-value metric, then validate whether it predicts payment and D30 retention.
* Judge the first funnel against approximately **10.7% hard-paywall download-to-paid** and **37.4% seven-day-range trial-to-paid**, while allowing for the premium price.
* Do not call the launch successful based on downloads or trial starts; require paid conversion, repeated study behaviour and low refunds.

---

# Recommended launch configuration

**Offer:** 90-Day Exam Plan $79.99 (test cell: $59.99) · Monthly Flex $34.99–$39.99 · 7-day trial on 90-day plan only · two plans visible · no weekly/annual/lifetime.

**Experience:** diagnostic before the paywall · personalized result before payment · full plan behind a hard gate · first study session immediately after trial start · login and avoidable setup deferred until after value or purchase.

**First test order:** (1) 90-day price → (2) trial presence on monthly → (3) 7 vs 14 days → (4) paywall timing → (5) copy and layout.

---

# What I left out (gap register)

* **Lifetime subscription strategy** — concerns permanent access, not a finite 90-day programme.
* **AI and hybrid monetization** — excluded because AI inference wasn't established as a major cost/core paid unit.
* **Web-to-app funnels and web checkout** — powerful later; adds attribution/checkout/compliance scope not essential to validating the native product within 60 days.
* **Large-scale freemium case studies (Duolingo, Opal, network-effect apps)** — depend on enormous audiences/mature brands; not transferable to a new premium exam-prep app.
* **Paid user-acquisition optimization** — plan assumes no meaningful ad budget.
* **Advanced win-back and reactivation programmes** — relevant only after enough subscriptions expire.
* **Seasonal discounts and Black Friday paywalls** — premature discounting could undermine premium positioning; RevenueCat's Mojo example found no-offer sometimes performed best.
* **Detailed store billing engineering** — grace periods and payment recovery retained (revenue-affecting); wider subscription-state/platform-API material excluded as implementation, not growth strategy.

---

## Source index (RevenueCat)

1. Average Subscription Renewal Rates by App Category (2026 Benchmarks) — revenuecat.com/blog/growth/average-subscription-renewal-rates-by-app-category
2. The State of Subscription Apps in 10 minutes (2026) — revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026
3. Price for Value and Localize — revenuecat.github.io/codelabs/monetization-success-formula/price-for-value/
4. 10 price test ideas for your subscription app — revenuecat.com/blog/growth/10-price-test-ideas-for-your-mobile-app
5. Understanding Google Play's subscription lifecycle — revenuecat.com/blog/engineering/google-play-lifecycle
6. The right trial length isn't 7 days — revenuecat.com/blog/growth/7-day-trial-subscription-app
7. Natal Sub Club case study (trial CVR 68%) — revenuecat.com/blog/growth/nancy-anderson-natal-sub-club-podcast-2026
8. Design a Paywall That Converts — revenuecat.github.io/codelabs/monetization-success-formula/paywall-design/
9. The essential guide to mobile paywalls — revenuecat.com/blog/growth/guide-to-mobile-paywalls-subscription-apps
10. Fix Your Onboarding Funnel First — revenuecat.com/blog/growth/fix-onboarding-funnels
11. Activation metrics that actually predict retention — revenuecat.com/blog/growth/activation-metrics
12. How Coconote hit $1M ARR in 4 months with no paid ads — revenuecat.com/blog/growth/brett-zack-coconote-sub-club-podcast-2026
13. Win the First Renewal — revenuecat.github.io/codelabs/monetization-success-formula/retention/
14. Recover Involuntary Churn — revenuecat.github.io/codelabs/monetization-success-formula/involuntary-churn/
15. How to launch your app — revenuecat.com/blog/growth/how-to-launch-your-app
16. Pre-PMF metrics — revenuecat.com/blog/growth/pre-product-market-fit-metrics
17. App Store Optimization Guide — revenuecat.com/blog/growth/app-store-optimization-guide
18. Your Monetization Scorecard — revenuecat.github.io/codelabs/monetization-success-formula/scorecard/
19. A guide to lifetime subscriptions — revenuecat.com/blog/growth/lifetime-subscriptions
20. Why hybrid monetization is the default model — revenuecat.com/blog/growth/ai-hybrid-monetization
