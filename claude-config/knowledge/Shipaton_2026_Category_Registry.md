# Shipaton 2026 — Category Registry

> **Canonical.** Mirror in `team_mvp_kit/prompts/` must stay byte-identical in body.
>
> **What this file is for:** the owner should never again have to ask "am I touching all the
> categories?" or re-derive which are reachable. This answers it once, per app, mechanically.
>
> **How to use it:** run `/shipaton-check <app-slug>`. That command reads this file, reads the
> app's `docs/shipaton/CATEGORY-TRACKER.md`, and reports every reachable category that is not
> yet claimed. Do not read this file cover-to-cover — read §1 (the verdict table) and the
> §4 traps, then the rows you need.
>
> **Related:** [`Shipaton_2026_Knowledge_Base.md`](./Shipaton_2026_Knowledge_Base.md) (strategy, app
> allocation, #BuildInPublic engine) · [`RevenueCat_Benchmarks_2026.md`](./RevenueCat_Benchmarks_2026.md)
> (pricing tripwires — read before touching price/trial/paywall)

**Built:** 2026-08-03, from the official Devpost rules text + live fetches.
**Source of truth:** https://revenuecat-shipaton-2026.devpost.com/rules
**Refresh trigger:** sponsors are added mid-event. Re-fetch the rules page before any submission.

---

## 0. The two dates and the one gate

| | |
|---|---|
| Submission Period | **Jul 31, 2026 8:00am PDT → Sep 30, 2026 11:45pm PDT** |
| #BuildInPublic Engagement Period | same window |
| Judging | Oct 1 – Oct 13, 2026 |
| Winners announced | Oct 21, 2026 |

**The gate that kills entries:** the app must be **fully published** on the App Store, Google Play,
**or** the Samsung Galaxy Store by the deadline. Not TestFlight. Not internal testing. Published.
Store review takes days and can bounce. **Every category below except Next Gen requires this.**

**"or" is load-bearing** — ONE store qualifies you for everything. An Android-only release is a
complete, valid entry. Do not buy an Apple Developer account ($99/yr) unless a category
specifically demands iOS (only JetBrains does, and it demands Kotlin anyway).

**Newly-published rule:** the app may be old, but its **first public store release must fall inside
the Submission Period**. An app already live on any eligible store before Jul 31, 2026 is
permanently ineligible. Check this FIRST for any candidate app — it is unfixable.

---

## 1. Verdict table — every category, and the test that decides it

> **§1 is entry requirements only. For how a category is SCORED, read §1b** — added 2026-08-22
> after it emerged that no judging criteria had ever been recorded here, and that most categories
> are judged on craft rather than traction.
>
> **Read §1a before quoting any prize amount.** A `--refresh-rules` run on 2026-08-21 found the
> landing page and the rules page disagreeing by +$5k on seven RevenueCat-funded rows.

`OPEN IF` is a **test to run per app**, not a verdict copied from a previous app. A Kotlin app opens
JetBrains; a game opens Best Game. Re-run the test, do not inherit the answer.

| # | Category | 1st / 2nd / 3rd | Cost to enter | OPEN IF |
|---|---|---|---|---|
| 1 | **Grand Prize** | **$100k** / — / — | $0 | always — every submission is auto-eligible. Shortlisted by **total RevenueCat revenue** in the window, then judged on growth story. |
| 2 | **#BuildInPublic** | **$30k / $20k / $10k** | $0 | always. Needs public posts tagged `#Shipaton` + links on the form. **Audience size explicitly does not matter.** |
| 3 | **Keep Them Coming Back** (OneSignal) | **$25k / $15k / $5k** | $0 (free tier) | always. Needs OneSignal SDK + **≥1 deployed campaign** + App ID on the form. |
| 4 | **HAMM** | $15k / $10k / $5k | $0 | app has ≥1 real IAP. Needs a monetization-strategy description. |
| 5 | **RevenueCat Design Award** | $15k / $10k / $5k | $0 | always. Needs a description of design elements + where judges should look. |
| 6 | **RevenueCat Peace Prize** | $15k / $10k / $5k | $0 | app has a credible social-good angle. Needs a description. Do not fake it. |
| 7 | **Catvertising** | $15k / $10k / $5k | $0 (ads earn) | app serves **RevenueCat Ads** — NOT AdMob. See §4 trap 3. |
| 8 | **Growth Loop** (Layers) | $15k / $10k / $5k | $0 | always. Install Layers SDK **before judging** + describe one growth experiment. Explicitly says the winner "will not necessarily have the most downloads, revenue, or traction." |
| 9 | **Funnel Vision** (Stripe) | $15k / $10k / $5k | $0 upfront | you can operate **Stripe** (country-gated) + build a web funnel via **RevenueCat Funnels**. Judged primarily on **web payment volume**. |
| 10 | **Most Viral App** (Noise) | $15k / $10k / $5k | **COSTS CASH** | you have UA budget. Pay-per-view UGC marketplace at `platform.getnoise.com`. See §4 trap 5. |
| 11 | **Best App for Galaxy** (Samsung) | **non-monetary** (featured placement) | $0 | you publish to the Galaxy Store. 20% of score is Galaxy optimization (foldables, multi-window). |
| 12 | **Best Game** | $15k / $10k / $5k | $0 | the app is a game. |
| 13 | **Next Gen** | $15k / $10k / $5k | $0 | a **student** with a qualifying academic email is on the team. **No store release needed** — video + public open-source repo (with a license file) instead. |
| 14 | **Ship Kotlin Everywhere** (JetBrains) | $15k / $10k / $5k | $99/yr (needs iOS too) | app is **Kotlin Multiplatform / Compose Multiplatform** AND published on **both** App Store and Google Play. Flutter/Dart apps score zero — this is structural, not effort. |
| 15 | **Idea to Income** (Replit) | $15k / $10k / $5k | $0 | the app was **actually built with Replit** + RevenueCat integrated via Replit Agent. Claiming this falsely risks disqualification. |
| 16–20 | **Influencer Awards** ×5 | $15k / $10k / $5k each | $0 | the app genuinely serves that influencer's audience. **Only ONE influencer category per project.** Categories: Productivity (Christopher Lawley) · Nutrition (Abbey's Kitchen) · Yoga/Fitness (Simone Sharice) · Career Coaching (Leadership Heather) · Gaming (Mr Lewis Blogs). |
| — | Conflict of Interest | no cash | — | you work for RevenueCat or a sponsor. |

**A single project may enter every category it qualifies for** (except: one influencer category max).
Entering more costs a form field, not a build.

---

## 1a. Amendments — appended by `--refresh-rules` runs (never overwrite a §1 row)

### 2026-08-21 — re-fetched by `/shipaton-check interview-boss-plus --refresh-rules`

Sources fetched live this run: the landing page `https://revenuecat-shipaton-2026.devpost.com/`
and the official rules `…/rules`. (`curl` is 403-blocked by Devpost; both reads went through the
agent fetch tool, and every figure below was confirmed by a **second, independently-worded fetch**
of the same page.)

**Category set: UNCHANGED.** All 21 rows in §1 are still present under the same names and
sponsors. **No new sponsor category has been added** since the 2026-08-03 build. The `[NEW]`
badges the landing page now shows on **Catvertising** and **Next Gen** sit on rows that already
existed in §1 — they flag the prize bump below, not a new category.

**AMENDMENT 1 — prize amounts conflict between the two official pages. Unresolved by Devpost.**

| Award | §1 / rules page says | Landing page says |
|---|---|---|
| HAMM | $15k / $10k / $5k | **$20,000** 1st |
| RevenueCat Design Award | $15k / $10k / $5k | **$20,000** 1st |
| RevenueCat Peace Prize | $15k / $10k / $5k | **$20,000** 1st |
| Catvertising | $15k / $10k / $5k | **$20,000** 1st `[NEW]` |
| Best Game | $15k / $10k / $5k | **$20,000** 1st |
| Next Gen | $15k / $10k / $5k | **$20,000** 1st `[NEW]` |
| Influencer awards ×5 | $15k / $10k / $5k | **$20,000** 1st |

**The split is systematic, not noise, and that is the tell:** every award RevenueCat itself funds
is $5k higher on the landing page, while every **sponsor**-funded award (OneSignal 25/15/5,
Layers, Stripe, Noise, Replit, JetBrains, all 15/10/5) and **#BuildInPublic** (30/20/10) reads
**identically on both pages**. Sponsors set their own purse; RevenueCat raised its own and the
rules text was not re-issued. That makes the landing page the likely current truth and the rules
text stale — but the rules page is the *legal* document, so **treat this as unresolved**.

Landing page also now states the pool as **"$740,000+ in cash"** and **"over $1 million worth of
prizes in total"**, which is only consistent with the higher figures.

**What this changes in practice:** nothing about which categories to chase, and nothing about
ordering — it is a uniform +$5k across seven rows. It only *widens* the gap that already made §2
the best trade on the board: **Design and Peace are now plausibly $20k each for one paragraph.**
Do not restate §1's amounts as fact in a report; cite the range and the conflict.
**Owner action if a number ever needs to be quoted publicly:** ask in the Shipaton Discord which
page governs.

**AMENDMENT 2 — submission-material specs, quoted from the rules this run.** These are checklist
items that fail silently at review time, not judging criteria:

- app icon **1024×1024**
- screenshot **1179px × 2556px**
- demo video **under 2 minutes**, public YouTube/Vimeo
- free trial **or** promo code for judges (every category except Next Gen)
- *"Apps must be accessible from United States"* — a US-market store listing is mandatory even for
  an app whose real audience is elsewhere
- *"Entrants may submit multiple unique submissions"* — confirms one project may hold several
  distinct submissions, separate from §1's "one influencer category per project" limit

**AMENDMENT 3 — §1 row 15 (Replit / Idea to Income) carries an extra requirement** not recorded on
2026-08-03: the submission must *"include three publicly visible social-media posts"* on top of
being built with Replit. Does not reopen the row for any non-Replit app.

**Unchanged and re-confirmed this run:** the publish gate (App Store **or** Google Play **or**
Samsung Galaxy Store, fully published, first public release inside the window); Next Gen as the
only store-exempt category; the ads-or-purchase eligibility clause (*"…at least one in-app or web
purchase, **or that serves ads through RevenueCat Ads**"*, §4 trap 2); and every influencer
audience definition, including Career Coaching = *"Help new managers practice difficult workplace
conversations"*.

### 2026-08-24 — re-fetched by `/shipaton-check interview-boss-plus` (Samsung challenge)

Triggered by the owner asking whether the Samsung award had been missed and whether other prizes
were being left on the board. Landing page and `/rules` both re-read (`curl` still 403; agent fetch
tool used), and the Samsung and prize-amount answers were each confirmed from the *other* page.

**Category set: UNCHANGED, third refresh running.** Still exactly 21 rows, same names, same
sponsors. Asked `/rules` directly to name any category outside the known 21 — answer: *"No other
award categories appear on this page beyond the 21 you listed."* **No sponsor category has been
added at any point since the 2026-08-03 build.**

**AMENDMENT 4 — §1 row 11 and §4 trap 7 UNDERSTATE the Samsung prize. Correct the framing, not
the verdict.** Both currently read as "featured placement only", which led a session to describe
Samsung as an afterthought. The prize text, verbatim from `/rules`:

> *"3 weeks of featured placement on the Galaxy Store (Apps Tab and Discover Tab editorial
> feature) • Invitation to RevenueCat's App Growth Annual conference in New York City (travel and
> accommodation not included) • Your app featured on a giant billboard in Times Square • Shippy
> trophy • Blog post featuring winning submissions • Media Spotlight on 9to5Mac & 9to5Google"*

So trap 7's core claim survives — **there is still no cash** — but "featured placement only" is
wrong. It also carries a Times Square billboard and a 9to5Mac/9to5Google media spotlight, which
for an unknown app is real distribution, not a consolation prize.

**Note the landing/rules divergence here too:** the landing page lists Samsung's prize alongside
the cash awards' "trip to NYC", which reads as travel included. The rules text says
**"travel and accommodation not included"** — an *invitation* only. The rules page is the legal
document; do not repeat the landing page's framing.

**The strategic point both §1 and trap 7 miss entirely:** Galaxy Store is one of the three stores
that satisfy §0's publish gate. That makes publishing there **$0 insurance on the whole
submission** — if Play review bounces or drags past the deadline, Galaxy alone still unlocks every
category except Next Gen. That value has nothing to do with winning Samsung's row and should not
be weighed against its (absent) cash.

**AMENDMENT 5 — the §1a amendment-1 prize conflict is STILL UNRESOLVED, now across two refreshes
three days apart.** Re-read on 2026-08-24: `/rules` still says **"$15,000 in USD"** first place for
HAMM, Design, Peace, Catvertising, Best Game, Next Gen and every influencer award, while the
landing page still says **$20,000** for the same rows. Sponsor-funded rows still agree on both
pages (OneSignal $25k, Layers $15k — both re-confirmed this run). The split still falls exactly
along who funds the award.

That it has persisted unchanged for three days makes a transient publishing error less likely and
strengthens amendment 1's owner action: **ask in the Shipaton Discord which page governs** before
quoting a figure publicly. Continue to cite the range, never a single number.

### 2026-08-29 — Layers looked up for the first time, by `/shipaton-check goldmend`

Triggered by the owner asking, plainly, "layer sdk? what is this?" — a question this registry
could not answer. Every Layers row here records the CATEGORY (sponsor, prize, "install the SDK",
judging criteria) and **nothing about the product**: no website, no package name, no platform
list, no pricing. A session had already ranked Layers as the best unclaimed prize-per-hour on a
board without knowing whether a mobile SDK existed. Fetched live this run from the Devpost
resources page, layers.com, layers.com/pricing and github.com/layers.

**AMENDMENT 6 — what Layers actually is.** Not an analytics SDK. From the Devpost resources
page, verbatim: Layers *"provides full-stack marketing automation for apps - it generates
content, runs paid ads, manages social, and optimizes your App Store listing so you can focus
on shipping."* The SDK's job is **attribution**: layers.com says *"One SDK drop ties every post
to the installs, trials, and revenue it actually produced."*

**Mobile SDKs DO exist** — `github.com/layers` is the real org (profile links to layers.com,
"Marketing for Developers") and publishes **Layers SDK for iOS/macOS, for Android, and for
Flutter**, plus a Unity analytics SDK, a CLI and an MCP server. So the category is genuinely
open to a Flutter app. The layers.com homepage only shows `npm i @layers/sdk`, which is what
made this look npm-only at first glance.

**AMENDMENT 7 — §3's "Layers SDK | $0 (sponsor)" is WRONG. Correct the cost, not the verdict.**
layers.com/pricing, read this run: a **3-day trial with 100 credits, "$0 today, card required"**,
which **auto-converts to a paid plan unless cancelled**. After that, **Pro $39/month** (5,000
credits) or **Ultra $159/month**. No plan forces ad spend — paid media is opt-in — but the
platform itself is not free, and §3 lists it under the $0-budget path. Under the standing $0
budget assumption, Layers now costs either a cancelled trial or $39.

**What this changes in practice:** it demotes Layers, it does not close it. Growth Loop's §1b
criteria are still craft-worded and still say the winner *"will not necessarily have the most
downloads, revenue, or traction."* But the work is no longer "install an SDK and write a
paragraph": an attribution SDK measures installs that came from posts, so it needs a PUBLISHED
app and real social content before it can observe anything. **OneSignal is the better
prize-per-hour claim** — $25k, free tier, and the SDK is usually already in the build.

**Not a conflict, recorded so nobody re-opens it:** the Devpost resources page calls Growth Loop
"a $30,000 prize category" while §1 says $15k/$10k/$5k. That is the same thing — 15 + 10 + 5 =
30 — the total pool, not a per-place figure. This is NOT another instance of the amendment-1
landing/rules split.

---

## 1b. Judging criteria — verbatim, per category (added 2026-08-22)

**Why this section exists, and what it says about §1.** Until this date the registry recorded only
each category's ENTRY requirement — the `OPEN IF` test — and never how a submission is actually
SCORED. Sessions across multiple apps advised on strategy from entry requirements alone. That is a
hole in the middle of the thing this file exists to be. Fetched live from
https://revenuecat-shipaton-2026.devpost.com/rules on **2026-08-22**. Quote from here; do not
paraphrase, and do not infer a criterion that is not written below.

**The single most consequential finding: MOST CATEGORIES ARE NOT TRACTION-GATED.** Only four score
on numbers at all. Every other category is judged on craft, articulation, and design quality —
meaning the work is doable BEFORE launch, and a session that defers category work until after a
store listing has misread the board.

| Traction/metrics-gated (numbers decide) | Craft-gated (quality decides) |
|---|---|
| Grand Prize · Funnel Vision (Stripe) · Idea to Income (Replit) · Most Viral App (Noise) | HAMM · Design · Peace · Catvertising · Keep Them Coming Back · Growth Loop · Best Game · Next Gen · Galaxy · JetBrains · all 5 Influencer awards |

---

**Grand Prize** — *Early and Effective Release:* "Explain when you first put a live, usable version
in front of real users, why you shipped at that moment, and how the initial build allowed you to
test or achieve early traction." · *Growth by numbers:* "Share the product improvements,
user-acquisition and retention efforts, marketing experiments, and iterations you ran after launch
and link them to concrete results, such as installs, active users, paying customers, conversion,
retention, waitlist growth, MRR/ARR, social reach, or community engagement."

**HAMM** — (1) "Are the proposed revenue streams clearly articulated and integrated into the app's
design? Is the monetization strategy realistic and achievable within the context of the target
market and the app's functionality?" (2) "Does the app demonstrate an innovative or unique approach
to monetization that goes beyond standard models?" (3) "Can the app articulate how their chosen
monetization methods could generate revenue? How does their monetization strategy differentiate
them from potential competitors?"
> **Corrects a common misreading:** HAMM is scored on the *articulation and inventiveness of the
> strategy*, NOT on revenue earned. Entry still needs ≥1 real IAP, but a pre-revenue app with a
> genuinely unusual monetization model can score well. A goal-window/one-off pass instead of a
> plain subscription is exactly what criterion 2 rewards.

**RevenueCat Design Award** — *Innovative ideas:* "Does the app introduce any innovative technology
or designs?" · *Aesthetics:* "Is the app simply delightful to look at and use? Does the design spark
joy?"

**RevenueCat Peace Prize** — *Impact:* "How impactful is the solution? Does the project clearly
demonstrate how it will benefit individuals, specific communities, or society as a whole?" ·
*Feasibility:* "Is the technology solution realistic and achievable for solving the problem?"

**Catvertising** — (1) "How well are ads integrated into the app experience? Do they feel natural,
useful, or additive rather than interruptive?" (2) "How well does the ad strategy fit the app's
audience, use case, and broader revenue model?"
> Note this is about ad *integration quality*, not ad revenue. §4 trap 3 still applies for
> eligibility: it must be RevenueCat Ads, not AdMob.

**Keep Them Coming Back (OneSignal)** — *Implementation:* "Did the Project successfully implement
fundamental OneSignal features? Is the integration clean, stable, and well executed?" · *User
value:* "Does the OneSignal integration improve the user experience or add significant value to the
app?" · *Resourcefulness and creativity:* "How resourcefully did the Entrant use OneSignal to
achieve the intended experience and outcome? Did the Entrant use OneSignal in a creative,
unexpected, or clever way, or attempt to use less-common or advanced mobile-messaging features?"
> Criterion 3 is where a basic init/consent/identify port scores ZERO. It rewards advanced features
> — behaviour-based tags/segmentation, per-user local-time delivery, journeys, in-app messages.

**Growth Loop (Layers)** — (1) "Did the Entrant identify a specific audience and a clear reason that
audience might care about the Project?" (2) "Did the Entrant use Layers to define a focused growth
loop, including the message, channel or product surface, experiment, and intended outcome?" (3) "Was
the Layers SDK properly installed so the loop could be observed and measured?" (4) "Did the Entrant
use the observed signal or response to explain what was learned and what the Entrant would try
next?"

**Best Game** — "Is the game fun and engaging to play?" · "Does it provide a unique gameplay
experience, progression, or replayability?" · "How is the game monetized?"

**Next Gen** — "Is the app idea clear, useful, interesting, or original? Does it solve a real problem
or create a compelling experience for its intended users?" · "Does the submitted project demonstrate
meaningful progress toward a working app? Is the core functionality clear from the video and code
repository?" · "Does the project thoughtfully use RevenueCat to support subscriptions, in-app
purchases, web purchases, ads, or another monetization flow?" · "Does the submission show thoughtful
technical choices, product thinking, and care in how the app was built and presented?"

**Best App for Galaxy (Samsung)** — *Galaxy optimization (**20%** — the only published weight on the
board):* "Does the Project take advantage of Samsung-specific features such as foldable-device
support, multi-window, or device-specific hardware?" · *Store quality:* "Is the Galaxy Store listing
polished, with optimized metadata and assets?"

**Funnel Vision (Stripe)** — *Web payment volume (**primary**):* "What total payment volume did the
Project process through its web funnel via Stripe?" · *Funnel design and conversion:* "How well
designed is the web-to-app experience, and how effectively does the funnel convert users from an ad
click to web checkout and app download?"

**Ship Kotlin Everywhere (JetBrains)** — *Cross-platform quality:* "How effectively does the Project
use Kotlin Multiplatform and/or Compose Multiplatform across iOS and Android?" · *Community
interaction (optional):* "Did the Entrant share the work in a useful, engaging way through a blog
post, devlog, video, or social-media updates?" · *Contribution to the community (optional):* "Did
the Entrant publish a library, contribute a pull request to a Kotlin Multiplatform library,
open-source a reusable component, or improve relevant documentation?"

**Most Viral App (Noise)** — *Virality:* "Did the Project's creative content and user-generated-content
playbooks on Noise produce one or more viral or semi-viral posts about the app or brand?" ·
*Scalability:* "Are the creative formats repeatable and suitable for distribution at significant
scale?" · *Conversion relevance:* "Do the Project's creatives clearly convey the Project's value or
novelty, address prospective users' needs or pain points, and present the product as a compelling
solution?"

**Idea to Income (Replit)** — *Growth momentum (**primary**):* "How fast and consistently did revenue
and transaction volume grow week over week?" · *Traction:* "What supporting traction did the Project
demonstrate, including gross revenue and number of paying users?" · *Craft:* "Is the user experience
and visual design high quality? Does the app feel like a complete, real product?" · *Social pull:*
"Did the Project generate meaningful community engagement or buzz?"

### Influencer awards — the criteria are content specifications, not vibes

Each names the exact experience being scored. Read the wording as a build spec: it says what the app
must contain to score, which is far more actionable than §1's one-line audience description.

**Productivity (Christopher Lawley)** — *Product focus and speed:* "Does the Project give Apple power
users a fast, focused way to save and retrieve reusable content?" · *Organization and intelligent
features:* "How effectively does the Project organize text, documents, files, and images, and do
intelligent features make retrieval easier?" · *Design and polish:* "Is the overall experience
polished, clear, and thoughtfully designed?"

**Nutrition (Abbey's Kitchen)** — *Practical nutrition support:* "Does the Project help users make
meals more satisfying in real-life situations?" · *Compassionate flexibility:* "Does the experience
support healthy eating without calorie counting, macro tracking, or restrictive meal plans?" ·
*Usefulness:* "Is the experience practical and helpful for the people it is designed to serve?"

**Yoga & Fitness (Simone Sharice)** — *Personalization:* "How effectively does the Project respond to
each user's movement, Pilates, recovery, and other wellness needs?" · *Daily clarity:* "Does it turn
those needs into a clear and achievable plan for today?" · *Information restraint:* "Does the
experience avoid overload and make the next action easy to understand?"

**Career Coaching (Leadership Heather)** — *Realistic scenarios:* "Are the workplace conversations
realistic and relevant to new managers?" · *Practice and feedback:* "Does the Project provide active
practice and useful feedback for situations involving **feedback, boundaries, and saying no**?" ·
*Confidence building:* "Does the experience help users feel better prepared before handling the real
situation?"
> The three named situation types are a content checklist. An app covering only "giving feedback"
> addresses one of three. Boundaries and saying-no are separately named and separately scored.

**Gaming (Mr Lewis Blogs)** — *Discovery and organization:* "Can users quickly save games when they
discover them and organize their backlog?" · *Completion and sharing:* "How effectively can users
complete, rate, and share games?" · *Enjoyment:* "Does managing the backlog feel enjoyable rather
than like another chore?"

---

## 2. The four "free after ship" categories

Once the app is live with an IAP, these cost **one paragraph each** on the submission form:

- **HAMM** — describe how it makes money, the paywall, pricing approach, any conversion numbers.
- **Design Award** — describe unique design elements and which screens judges should look at.
- **Peace Prize** — describe how it benefits individuals, a community, or society.
- **Grand Prize** — describe what you did post-launch to grow, with numbers.

**Never skip these.** Zero marginal work for $15k–$100k of exposure. An agent that ships an app and
does not claim all four has left the cheapest money on the board.

## 3. The $0-budget path

Everything except Noise and the Apple account is free:

| Item | Cost |
|---|---|
| Release keystore (`keytool`) | $0 |
| RevenueCat | $0 under $2.5k monthly revenue |
| OneSignal | $0 free tier |
| Layers SDK | $0 (sponsor) |
| Stripe | $0 upfront, % of sales |
| Samsung Galaxy Store seller | $0 |
| Google Play Developer | **$25 one-time** — the only unavoidable cost, and only if not already owned |
| Apple Developer | $99/yr — **skip unless chasing JetBrains** |
| Noise | pay-per-view UGC — **the only category requiring spend** |

**Ship Kit — free perks the owner keeps forgetting to claim.** Up to **25 sponsor perks** across
five milestones: registration complete · **RevenueCat project created** · first test purchase ·
first Store API call · first real purchase. Delivered by email, redeemed via the Shipaton Discord.
Creating the RC project is both a submission requirement AND a perk trigger. Claim them.

## 4. Traps — every one of these was gotten wrong in a real session

1. **"Public repo is required."** **False.** Only **Next Gen** needs a public open-source repo.
   A leaked-credential problem blocking a repo from going public does **not** block #BuildInPublic
   or any other category.
2. **"Ads-only eligibility is unconfirmed."** **Resolved.** Official rules: *"uses the RevenueCat SDK
   to power at least one in-app or web purchase, **or that serves ads through RevenueCat Ads**."*
   The ads-only path is real. (Superseding the KB's earlier "treat as unconfirmed" note.)
3. **AdMob ≠ RevenueCat Ads.** Catvertising judges name **RevenueCat Ads** explicitly. An app with
   `google_mobile_ads` and no RevenueCat Ads scores zero. RevenueCat Ads needs `purchases_flutter`
   **10.x**.
4. **"The shared kit pins an old SDK, so we need the teammate's agreement to upgrade."** **False.**
   `dependency_overrides` in the *app's own* pubspec applies only to that app's resolution. The
   other app that shares the kit resolves independently and is untouched. No kit edit, no
   negotiation. (Whether the kit's code compiles against the new major is a separate, testable
   question — ~30 min to find out.)
5. **"Noise is impossible."** **False — it is open but costs money.** It is a pay-per-view UGC
   marketplace (brand side: `platform.getnoise.com/auth/sign-up`; the App Store app named
   "Noise — Make Money Posting" is the *creator* app, not yours). No minimum, no contract, you set
   CPM and budget. But judging is *"did the content produce viral or semi-viral posts"* — bought
   distribution is not virality. **Worst money-per-dollar on the board.** Skip at $0 budget.
6. **Under-counting the sponsor categories.** OneSignal pays **$25k** for first place — the second
   largest category prize — for roughly one day of SDK work. Layers pays $15k for installing an SDK
   and writing a description. These are routinely forgotten because they were announced after the
   main category list.
7. **Samsung pays nothing.** Featured placement only. Do it for distribution, not prize money.
8. **Don't fake-target an influencer category.** Criterion #1 in each is audience relevance. A
   job-search app entered under "Career Coaching (new managers practising difficult conversations)"
   scores near zero and burns the one influencer slot.
9. **Grand Prize is revenue-gated.** Shortlist is built from total RevenueCat revenue in the window.
   Zero revenue = never shortlisted, no matter how good the growth story.

## 5. Submission checklist — required for EVERY entry

- [ ] App **fully published** on Play / App Store / Galaxy Store (Next Gen exempt)
- [ ] First public release falls **inside** the Submission Period
- [ ] RevenueCat SDK powering ≥1 real purchase, **or** RevenueCat Ads
- [ ] **Free trial OR a working promo code** so judges can unlock premium
- [ ] Demo video **≤2 min**, public on YouTube/Vimeo, real device footage
- [ ] Text description of features and functionality
- [ ] **1024×1024** app icon
- [ ] ≥1 screenshot at **1179×2556**, **no device frame**
- [ ] App installable **from the United States**
- [ ] All materials in English (or with English translation)
- [ ] Per-category description paragraphs (§2)

## 6. Per-app tracker

Every app repo carries `docs/shipaton/CATEGORY-TRACKER.md`, seeded from §1 by running
`/shipaton-check <app-slug>`. The tracker is the state; this registry is the rulebook. When they
disagree, re-fetch the official rules — sponsors get added mid-event.

---

## AMENDMENT 3 — rules re-fetched 2026-09-03 (`/shipaton-check --refresh-rules`)

Fetched live from https://revenuecat-shipaton-2026.devpost.com/rules. **§1 rows above are NOT
overwritten** — the amounts below supersede them where they differ, same discipline as the
decisions log.

**Seven categories raised their 1st prize from $15k to $20k** since the 2026-08-03 build:

| Category | §1 said | Live 2026-09-03 |
|---|---|---|
| HAMM | $15k / $10k / $5k | **$20k** / $10k / $5k |
| Catvertising | $15k / $10k / $5k | **$20k** / $10k / $5k |
| RevenueCat Design Award | $15k / $10k / $5k | **$20k** / $10k / $5k |
| RevenueCat Peace Prize | $15k / $10k / $5k | **$20k** / $10k / $5k |
| Next Gen | $15k / $10k / $5k | **$20k** / $10k / $5k |
| Best Game | $15k / $10k / $5k | **$20k** / $10k / $5k |
| Influencer Awards (each of 5) | $15k / $10k / $5k | **$20k** / $10k / $5k |

**Unchanged:** Grand Prize $100k · #BuildInPublic $30k/$20k/$10k · Keep Them Coming Back
(OneSignal) $25k/$15k/$5k · JetBrains, Replit, Noise, Layers, Stripe all $15k/$10k/$5k ·
Best App for Galaxy = featured placement, 1st only.

**Changed in kind:** Conflict of Interest Award is listed as a **billboard feature** (1st only),
not merely "no cash".

**No new sponsor categories** appeared between 2026-08-03 and 2026-09-03.

### Demo video — quoted, because §1 never recorded these

- Length: *"should be less than two (2) minutes. Judges are not required to watch beyond two minutes"*
- Hosting: *"must be uploaded to and made publicly visible on YouTube or Vimeo"*
- Device footage: *"should include footage that shows the Project functioning on the device for
  which it was built"* — note **"should"**, not "must", and the test is the device the project was
  built FOR. An Android game therefore wants Android device footage.
- Content: *"must not include third party trademarks, or copyrighted music or other material unless
  the Entrant has permission"* — an app whose audio is synthesised in-app is clean here.

**Deadline confirmed:** *"Wednesday, September 30, 2026 at 11:45pm PDT"*.
