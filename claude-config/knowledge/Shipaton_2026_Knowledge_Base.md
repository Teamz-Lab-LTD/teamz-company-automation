<!--
  CANONICAL COPY. Authored by the team lead; the body below is VERBATIM and unedited.

  A second copy exists at team_mvp_kit/prompts/shipaton-2026-knowledge-base.md. That one is
  the mirror — it is reached by apps through the kit submodule and carries this same header.
  If you edit one, edit both, or a "locked" plan quietly forks. See GENERIC-ASSET-INDEX.md.

  Two things learned the hard way executing this on ai_resume_checker (2026-07-12), kept here
  so the next app does not repeat them:

  1. VERIFY A CLAIM BEFORE YOU SHIP IT. "Your resume never leaves your device" was about to
     go into a Play listing. The FILE never leaves the phone — but the extracted TEXT is
     sent to a third-party LLM and stored in Firestore. The claim was false in the way a
     user would read it, and it is exactly what the anti-dark-pattern judge screens for.
     Every store claim must be checked against the code path, not the pitch.

  2. "CONFIGURED" IS NOT "WORKING." The resume app's ads were configured, preloaded, and
     displayed to nobody for its entire life — `autoShowOnLoad: false`, zero
     `AdPlacementView` in the tree. Grep for the CALL SITE, not the config.

  Worked example of both: ai_resume_checker/automation_data/deep-research-keywords.json
  (`_privacy_reality`, `_app_constraints.forbidden_claims`).
-->

---

# RevenueCat Shipaton 2026 — Master Knowledge Base & Strategy

> **What this document is.** A self-contained strategic knowledge base for competing in RevenueCat Shipaton 2026. It reconciles three independent research passes (Gemini, ChatGPT Deep Research, and live page fetches) plus audits of three candidate apps. It is designed to be **portable**: paste it into any fresh AI conversation to rebuild full context.
>
> **How to reuse it.** Open a new chat, paste this whole file, and say: *"This is my Shipaton 2026 knowledge base — continue from the Open Decisions section."*
>
> **Last compiled:** July 4, 2026. **Re-verify the "Unconfirmed" section after the official rules drop (before Aug 1, 2026).**
> **Owner context:** Small team, Dhaka (Bangladesh), Flutter builders, one part-time junior designer, at least one student on the team, AI-assisted workflow, 100% flexible on features/design.

---

## Table of Contents
1. Competition — Confirmed Facts
2. Still Unconfirmed (re-verify before Aug 1)
3. The Prize Structure (why it drives strategy)
4. The Categories (full list + what each rewards)
5. Judges & Judging Process
6. Judge Profiles & Psychology
7. Historical Winning Patterns (2024–2025)
8. The Three Candidate Apps — Audit Summaries
9. THE DECISION — Recommendation & Rationale
10. Winning Strategy & Execution Roadmap
11. Ethical "Unfair Advantages"
12. Open Decisions & Next Actions
13. Sources

---

## 1. Competition — Confirmed Facts

| Item | Confirmed detail |
|---|---|
| **Event window** | Ship a **brand-new** app; first public release must land **Aug 1 – Sep 30, 2026**. |
| **Winners announced** | **October 21, 2026**. |
| **Core requirement** | Integrate the **RevenueCat SDK** to power **≥1 in-app purchase** OR serve ads through **RevenueCat Ads** (see caveat in §2). |
| **Eligible platforms** | iOS, iPadOS, macOS, Android → **App Store, Google Play, or Samsung Galaxy Store** (Samsung is new for 2026). |
| **"Brand-new" rule** | Updates to existing apps don't qualify. If an app was live on one platform before Aug 1, shipping later on another platform does **not** count as a first-time release. |
| **Team size** | **No limit.** But if you win a travel-eligible prize, they fly **only one** teammate to NYC. |
| **Submission requires** | Text description; demo video (**≤2 min**, essential footage, on the target device, public on YouTube/Vimeo); URL to the **fully published** app; 1024×1024 icon; ≥1 screenshot at **1179×2556** (no device frame); a **free trial or working promo code** so judges can unlock premium features. |
| **Prize pool** | Official pages: **$700,000+ cash / $1M+ total value** (still growing). Publicly itemized payouts currently sum to **~$425k** because categories are still being finalized. |
| **Extras for 1st place** | NYC trip + App Growth Annual conference + custom Shippy trophy + **Times Square billboard** + press on **9to5Mac / 9to5Google**. |
| **NEW for 2026** | Samsung Galaxy Store eligibility; **RevenueCat Ads** monetization path; **Catvertising** award; **Next Gen** student award; **Shipaton Growth Fund** (investor exposure — mechanics not yet public). |
| **ShipKit** | Bundle of sponsor tools/credits/deals for all registrants (some "while supplies last"; still rolling out). |

---

## 2. Still Unconfirmed (re-verify before Aug 1)

These were **not** finalized in official sources as of July 4, 2026. The official rules page explicitly said full rules would be posted before the event.

- **Exact final cash total** — reconcile the $700k+ claim vs the ~$425k itemized schedule once categories finalize.
- **Full judge roster** — only Charlie Chapman & David Barnard are named; the 5 influencer judges are unnamed.
- **Per-category point weightings** — only known rubric is "score 1–5 per category"; no legal weight table published.
- **The 5 Influencer Award category names + target demographics** — only placeholders "Category 1–5" exist.
- **Sponsor-dedicated award categories + criteria** — "coming soon."
- **Exact ShipKit contents** — not itemized.
- **⚠️ Ads-only eligibility** — marketing says "IAP **or** RevenueCat Ads," but one Devpost snippet still says "at least one in-app or web purchase." **Treat as unconfirmed → build a real IAP regardless.**
- **Growth Fund mechanics** — structure/eligibility/check size unknown.

---

## 3. The Prize Structure (why it drives strategy)

The structure — not the headline number — is the whole strategic story.

- **~15+ award tracks**, each paying **1st $15k / 2nd $10k / 3rd $5k** (Grand Prize 1st is **$50k**). Conflict of Interest = recognition only, no cash.
- That's **45+ discrete cash prizes**.
- **Registration ≠ competition.** 2025: ~54,000 registrants but only **~812 finished submissions**. **Completion is the real filter.** Reliably shipping one polished app already beats ~98% of registrants who never finish.
- **Strategic implication:** target the **least-crowded categories** and design **one app to qualify for 3–4 tracks at once**.

---

## 4. The Categories (full list + what each rewards)

| Category | What it rewards | Crowdedness (est.) |
|---|---|---|
| **Grand Prize (Build & Grow)** | Most **user traction & growth momentum** during the event; what you did post-release | High (everyone wants it) |
| **HAMM** (Help Apps Make Money) | Smartest, most creative use of RevenueCat to drive **real revenue** | **High** (every well-monetized app targets it) |
| **Catvertising** ⭐ | Creative + effective use of **RevenueCat Ads**; clever placements users don't hate | **Low — NEW, small field** |
| **Design** | Product craft, beautiful UI, animation (apart from business viability) | Medium (native SwiftUI dominates) |
| **Peace Prize** | Greatest social good / community benefit | Medium |
| **Best Game** | Best mobile game; gameplay, art, monetization fit | Medium |
| **Next Gen** ⭐ | Best **student** submission; judged on **video + open-source code**; no store release or paid dev account needed | **Low — students only** |
| **#BuildInPublic** | Most compelling build-in-public journey; lessons + community feedback incorporated | Medium (requires daily posting) |
| **Influencer Awards ×5** | Build an app for a specific influencer's audience; the influencer judges personally | Unknown (names TBD) |
| **Conflict of Interest** | Best submission from RevenueCat/sponsor employees (no cash) | N/A |

⭐ = strategically under-exploited openings for this team.

---

## 5. Judges & Judging Process

- **Named judges (only 2 public):** **Charlie Chapman** (Senior Developer Advocate, RevenueCat) and **David Barnard** (Growth Advocate, RevenueCat).
- **Category assignments are deliberately hidden** — RevenueCat does not disclose which judge covers which category, specifically to stop participants contacting judges. *Do not try to game a specific judge.*
- **Scoring:** Prescreeners and judges score each targeted app **1–5 in each category**.
- **Minimum judge effort per app:** read the description, watch **≥2 minutes** of the video, review **all** screenshots, then score. Downloading the app is *encouraged but not required*.
- **Strategic implication:** The **first 2 minutes of video, the description, and the screenshots must carry the entire pitch.** Many judges will never open your app. Front-load everything.

---

## 6. Judge Profiles & Psychology

Both named judges are **indie practitioners** who have personally shipped and monetized apps. They reward authenticity, honest monetization, design craft, real traction, and *fluent* RevenueCat usage.

**David Barnard — Growth Advocate**
- Building apps since 2008 (founded Contrast); launched 20+ apps, sold 3 (e.g., Weather Up, Launch Center Pro). Ex-recording engineer, self-taught. Hosts the *Sub Club* podcast.
- **Values:** matching the value you deliver to what you charge. **Openly hostile to dark patterns** — has said the part of the market that "tricks people into subscribing" is the part he hopes suffers.
- **Implication:** Build an **honest paywall** a savvy operator would respect. No trap subscriptions.

**Charlie Chapman — Senior Developer Advocate**
- Indie iOS dev behind **Dark Noise** (famous for animation/UI polish, custom icons); hosts the *Launched* podcast; self-taught from .NET.
- *The* internal expert on RevenueCat's paywall tooling — publicly migrated Dark Noise to **RevenueCat Paywalls** and used **RevenueCat Experiments** for an A/B-tested rollout. Embeds RevenueCat verified public metrics on his own site.
- **Values:** design craft, satisfying animation, and **sophisticated, correct** use of Paywalls UI + Experiments.
- **Implication:** Using **Paywalls UI + a live A/B Experiment** speaks directly to him and almost no one else will do it.

---

## 7. Historical Winning Patterns (2024–2025)

**Scale trajectory:** 2024 was year one — ~1,700 participants, $25k across 3 categories, SF billboards. 2025 exploded to ~54,000 registrants (~812 finished projects), $350k+ prizes, AI/vibecoding dominant.

**What wins, consistently across every category:**
- **Small teams.** Solo builders and duos dominate the winners' list, Grand Prize down.
- **A sharp personal pain-point + origin story.** Nearly every winner has one (education inequality, a child's mental health, a hard-of-hearing partner). Judges reward the *why*.
- **AI-assisted builds are celebrated, not hidden.** 2025 Grand Prize = **Payout** (class-action settlement finder), built **entirely** with Claude Code + Cursor, no hand-written code; reached **17k+ users, $30k revenue, 1,750 paying subs**. Winners openly documented Claude Code / Cursor / CodeRabbit / Xcode Cloud pipelines.
- **Stacks:** Native SwiftUI for design/craft wins; **React Native + Expo** and **Flutter** for speed/cross-platform; **Kotlin Multiplatform** has its own sponsor lane; on-device AI (Vision/CoreML/ARKit) for technically impressive entries.
- **Monetization that's a *story* beats plain subscriptions.** Hybrid credits + subscription; goal-personalized paywall copy; mission-linked models (e.g., "every subscription funds 50 free accounts").
- **Traction is heavily weighted at the top** (Grand Prize = release early, iterate, grow). **Ship early, show the curve.**
- **Recurring app archetypes:** sharply-niched AI utilities (decode texts, find money, study tools, stylist), "satisfying ritual" utilities, health/accessibility, niche-passion apps, polished games.

---

## 8. The Three Candidate Apps — Audit Summaries

All three are Flutter, built on a shared `team_mvp_kit` that already ships the full RevenueCat stack (`purchases_flutter` + `purchases_ui_flutter` 9.9.1, RevenueManager, Paywalls UI, credits BLoC, ads infra).

### 8.1 Sleep Switch — **6/10 as-is → up to 8/10 with a real founder story** (revised up)
- **Pitch:** One-tap, eyes-closed, voice-guided sleep drills (Cognitive Shuffle / 4-7-8 / military method) for overthinkers.
- **Status:** Core engine ~70% (genuinely works — phased TTS, voice commands, session player). Monetization ~5%. Store-ready ~30%. **Dormant ~4 months.**
- **RevenueCat:** Basic — SDK + Paywalls UI in the kit but **not activated** (config null → paywall no-ops to a snackbar).
- **Monetization 2/5 · Virality 3/5.**
- **Best fit:** **Peace Prize** (wellbeing) + **Design** (theming/animation) + **HAMM** (if wired) — three clean lanes.
- **Genuine differentiator (do not under-rate):** **voice-first, eyes-closed control.** Calm/Headspace/mySleepButton don't do this because "you can't scroll a phone while falling asleep" is a real insight they missed. This is a wedge, not a me-too — and it's demoable in 15 seconds.
- **Real risk:** the incumbent moat (Calm/Headspace) — the voice-first angle is the wedge through it. The 6/10 was dragged down by three **fixable** things: dormant, monetarily hollow, no written story. With time + flexibility + a genuine personal sleep story, founder-passion + authentic "why" + demoable hook is exactly the profile that wins Shipaton. **If the team has a real insomnia story, this becomes a top contender.**

### 8.2 NoteTube AI — **7/10** (highest floor, highest structural risk)
- **Pitch:** Turn YouTube watch-time into knowledge you remember (notes, transcripts, AI summaries, flashcards, quizzes).
- **Status:** **~75–80% done** — the most shippable. Real player, tier-aware AI (Claude 3.5 Sonnet premium / Gemini free), spaced repetition, server-side quota. Work left is *verification + pruning*, not building.
- **RevenueCat:** **FLUENT** — real platform keys, **Paywalls v2** live via PaywallView, webhook→Firestore, **server-side quota enforcement** (correct architecture), source-keyed paywalls, forces real sign-in before purchase. A/B Experiment not yet wired (kit has the harness — cheap to add).
- **Monetization 4/5** (sophisticated 7-tier persona pricing — but no single narratable story) **· Virality 3/5.**
- **Best fit:** **HAMM** (textbook entry).
- **⚠️ Killer risk (POLICY, not technical):** The risk is **not** "can you fetch the captions" — you can auto-fetch them. The problem is **YouTube's ToS + store policy.** Apple Guideline **5.2.3** and Google's rules prohibit apps that repackage/facilitate access to third-party content (YouTube specifically) in ways that break YouTube's ToS — which restricts using its content *independently of the video* (exactly what summaries/flashcards-from-any-video do) and prohibits scraping the transcript endpoint. **So auto-fetching captions doesn't remove the exposure — it *is* the exposure.** Not certain death (YouTube-summarizer apps exist), but elevated, reviewer-dependent risk in a competition where a live, non-removed app is mandatory.
- **What actually lowers it (the real re-architecture):** shift value to **user-provided** content (they paste/upload their *own* transcript), **or** use only YouTube's official **IFrame Player + Data API** and keep users watching *on* YouTube rather than replacing it. Do that and NoteTube's near-done build + fluent RC = strongest of the three. Keep browse-and-scrape and you're betting two months on a reviewer's coin flip.
- **Secondary risk:** 8-month-old / 181-commit codebase reads as "not built for Shipaton" (hurts authenticity + #BuildInPublic).

### 8.3 ai_resume_checker (Resume Coach) — **7/10** (best risk-adjusted)
- **Pitch:** Upload your resume → AI grades, fixes, ATS-scans it, and preps interviews.
- **Status:** ~70% as an app / **~35% as a Shipaton entry** (because RC monetization is absent). Real backend (`aibackend.teamzlab.com`), real AI (9 smart actions), **LIVE AdMob** (real production units, interstitial + native, analytics-tracked), ~19 locales.
- **RevenueCat:** **NONE wired in this app** (kit is fluent but unwired — a config + gating job, ~1 week).
- **Monetization 3/5 design · 1/5 shipped · Virality 3/5.**
- **Best fit:** **HAMM** + **Catvertising** (uniquely — it already has a live ad stack).
- **Killer risk:** Category saturation ("most cloned AI app concept") — **but this is a *positioning* problem, fixable with a sharp niche.** RC gap is a cheap week.

### 8.4 Comparison
| Field | Sleep Switch | NoteTube AI | Resume Checker |
|---|---|---|---|
| % done (as Shipaton entry) | ~30% | **~75–80%** | ~35% |
| Build-days to v1 | 5–7 | 5–8 (verify/prune) | 6–9 |
| RevenueCat readiness | Basic | **Fluent** | None (kit fluent) |
| Monetization | 2/5 | **4/5** | 3/5 design / 1/5 shipped |
| Virality | 3/5 | 3/5 | 3/5 |
| Best category | **Peace + Design + HAMM** | HAMM | HAMM + **Catvertising** |
| Differentiator | **Voice-first eyes-closed (real wedge)** | Fluent RC / near-done | Live ad stack → Catvertising |
| Key weakness type | Founder story + monetization (**fixable**) | **Store/ToS policy risk (needs re-architecture)** | Positioning (**fixable**) |
| Score | 6→**8** w/ real story | 7 (capped by policy risk) | 7 (best pure odds) |

---

## 9. THE DECISION — Recommendation & Rationale

### 9.1 Submit ONE app, not three (even with 3 months)
The calendar is ~3 months but the **scored window is only 2**: publishing before **Aug 1 disqualifies** the app, so July is prep-only, and Grand Prize + every traction category is judged on growth *during* Aug 1–Sep 30. **Build time isn't the bottleneck — attention is.** A small team can't grow three user bases, run three build-in-public streams, and iterate three paywalls in two months. Judges score 1–5; **three 3/5 apps lose to one 5/5.** Three half-apps is the most common way strong teams lose.

**The clean hedge that is NOT dilution:** run one app all-in, and have the **student submit that *same app's* open-source code + video to Next Gen.** Different rubric, near-zero extra marketing cost, one extra shot. (A store build submitted to Next Gen is *not* judged for Next Gen — it judges code + video.) → **one app, up to three category entries** (e.g., Catvertising/HAMM/Peace + Next Gen).

### 9.2 ✅ FINAL LOCKED PLAN (decided in session, July 2026) — Two tracks, three owners

> **Before touching pricing, trials, paywall structure or the launch funnel on ANY app here, read [`RevenueCat_Benchmarks_2026.md`](./RevenueCat_Benchmarks_2026.md) — start at its TRIPWIRES table.** It is product-neutral and its tripwires are meant to stop an agent mid-task. [`RevenueCat_Growth_Playbook.md`](./RevenueCat_Growth_Playbook.md) is a worked example for ONE product (a $79.99/90-day exam-prep app) — do not copy its offer structure into another app.

The contingency is resolved. **Structure: two apps, cleanly divided by owner, zero overlap on any one person's attention.** Resume Checker is SHELVED (adding it would put a second app on the lead's plate — the one forbidden move).

| Track | Owner | App | Target categories |
|---|---|---|---|
| **Track 1 (primary)** | **Gk (team lead)** | **NoteTube AI** | **HAMM** (sole build target) + #BuildInPublic (bonus lane) + Grand Prize (passive — only if growth happens; spend $0 chasing it) |
| **Track 2 (delegated)** | **Intern** (via the interactive HTML guide) | **Sleep Switch** | **Peace Prize + Design** (+ HAMM secondary) |
| **Track 3 (near-free)** | **Student teammate** | Sleep Switch's **code + video** | **Next Gen** (no store account needed; store release not judged; same app can also be published for other categories — confirmed allowed) |
| **Track 4 (conditional)** | Game teammate ONLY | A small game | **Best Game** — allowed only under 3 conditions: (1) game teammate owns it 100%, lead never touches it; (2) small scope, one mechanic; (3) **Sep 1 kill-switch** — not near store-ready by then → dropped, no guilt |

**NoteTube locked decisions (all four made):**
1. **Architecture:** official **YouTube embedded player** — users keep watching *on* YouTube; notes/flashcards/quizzes layer around it. No WebView browse, no transcript scraping. (Kills the Apple 5.2.3 / ToS rejection risk.)
2. **Persona:** **exam-cramming students.** One sentence: *"Pass your exam from the YouTube lectures you already watch."* Everything not serving that sentence gets HIDDEN (not deleted) for launch: creator tools, Notion/Readwise sync, etc.
3. **Pricing:** **one hero product — Exam Cycle, ~$79.99 / 90 days**, expires when the exam does ("we help you pass, then we're done" — honest, narratable, exactly what HAMM rewards). One cheap monthly as fallback. Other tiers hidden.
4. **Category:** **HAMM only** as the shaping target.

**MAXIMUM-COVERAGE MATRIX (owner's directive: HR is managed by Gk; each app targets its true ceiling).** Every app works down its tiers as far as its team's real capacity reaches: **SHAPED-FOR** = polish budget lives here; **UNLOCK** = available with the specific listed work; **PASSIVE** = free box-tick, expect nothing extra.

| App | SHAPED-FOR | UNLOCKS (with the work listed) | PASSIVE | Physically closed |
|---|---|---|---|---|
| **NoteTube** | HAMM | **Catvertising** → add RevenueCat Ads to free tier (tasteful, between study sessions; premium removes ads — also strengthens the HAMM story) · **Next Gen** → student contributes code + submits (confirm multi-submission rules in Discord) · **#BuildInPublic** → Gk's X/LinkedIn engine (§12.5) | Grand Prize (growth) · Influencer (check when names drop) | Best Game, Design (kit UI can't beat native craft) |
| **Sleep Switch** | Peace Prize, Design | **#BuildInPublic** → intern runs their own "my first app" journey account (beginner story = highly compelling to these judges) · HAMM → wire the honest paywall per the intern guide | Grand Prize · Next Gen (student, already planned) · Influencer | Best Game · Catvertising NOT recommended even though possible (ads would damage the Peace + Design entries — the one unlock deliberately left unpulled) |
| **Resume app** (if activated) | Catvertising, HAMM | **Peace Prize** → lean the niche into "helping international grads beat ATS discrimination" (credible social-good entry, not a box-tick) · **#BuildInPublic** → its team lead posts · Next Gen → if a student is on that team | Grand Prize · Influencer | Best Game, Design |
| **Game** (if committed) | Best Game | **Design** → the award explicitly rewards art direction/craft; games can win it — invest in art style · **HAMM** → honest game monetization (cosmetics/pass, no dark patterns) · **#BuildInPublic** → game teammate posts · Next Gen → if a student builds on it | Grand Prize · Influencer | Peace, Catvertising (unless ads genuinely fit the game) |

**Theoretical ceiling: 20+ category entries across four apps.** Rules that keep the matrix honest: (1) polish budget always goes to SHAPED-FOR first — unlocks only after the core entry is strong; (2) no fake targeting of physically closed lanes; (3) each live app still needs one accountable owner for its weekly ship-and-grow rhythm (Gk manages the allocation); (4) every #BuildInPublic journey must be run by the person actually building that app — authenticity is the judged criterion.

**Budget (locked): ~$125–145 total.** Google Play $25 (one-time) + Apple $99/yr (one account covers both apps) + Cursor $20/mo (already paying). RevenueCat free at this scale. Samsung free. **Marketing $0 — no paid ads; free channels only** (Reddit, TikTok/Shorts, X). ⚠️ Watch NoteTube's AI API costs: keep free-tier quotas tight (free users already route to cheap models) so a free-user spike can't burn money.

**Cheapest-path-to-a-prize ranking:** (1) **Next Gen** — smallest field, ~$0; (2) a **2nd–3rd place in Peace Prize or HAMM** — finished + honest + story-driven is genuinely competitive there; (3) Grand Prize — lottery ticket, spend nothing on it.

### 9.3 NoteTube weekly calendar (Gk holds only the current week)
- **Wk Jul 6 — Verify, don't build:** RC dashboard check; offering loads in-app; **ONE sandbox purchase end-to-end** (webhook was "previously broken" — trust the foundation first).
- **Wk Jul 13 — The player switch:** WebView/scrape → official YouTube embedded player. The only deep technical week.
- **Wk Jul 20 — Hide & sharpen:** hide non-core features; create Exam Cycle product (stores + RC); rewrite store copy around the one sentence.
- **Wk Jul 27 — Launch prep:** screenshots, icon, listing ready. **Do NOT publish.**
- **Aug 1 (±days) — SHIP.** Week-one store link = real advantage.
- **Aug → Sep 20 — weekly rhythm:** fix top complaint → ship small update → post in **one** student community (one subreddit/Discord, not five) → BuildInPublic posts. Somewhere in here: **one paywall A/B Experiment** (trial vs no-trial — kit has the harness; the judge-impressing move).
- **Sep 21–30 — Submission:** ≤2-min video (hook: lecture → flashcards in 30 seconds), story-driven description, promo code tested, BuildInPublic story assembled from the journey log.

### 9.4 Standing risk flag — ✅ LARGELY RESOLVED (Jul 12, 2026)
The official 2026 launch post explicitly states the app "can be something you've been working on for a longer time but just haven't shipped yet," and that building/posting before Aug 1 is encouraged. **NoteTube's 8-month codebase is eligible — first public release in-window is what counts.** Residual action: skim the legal rules page when it posts (final wording), but intent is now unambiguous.

### 9.5 Entry format (decided)
Register as a **team of individuals** on Devpost, not as the company — simpler, no entity paperwork, prize goes to a designated representative anyway. Company entry only matters if prize money must be paid to the business for tax reasons. Devpost standardly accepts individuals, teams, AND organizations (2025 Shipaton rules referenced all three). **Student registers with their academic email** (unlocks Next Gen).

### 9.6 Resume Checker — official Plan B (parachute status)
**Shelved, not dead.** It does NOT enter the competition alongside the two tracks (that would put a second app on the lead's plate — forbidden). Its role:

- **Activation trigger:** if RevenueCat's eligibility ruling goes AGAINST NoteTube → Resume Checker takes the lead's slot. Track becomes: **Resume Checker → Catvertising (primary) + HAMM (secondary)**, same weekly-rhythm plan.
- **Why it's the right parachute:** never published → 100% eligibility-clean, zero 2025 history; ~70% built with a real backend + working AI actions; the ONLY app of the three that fits **Catvertising** (live, analytics-tracked AdMob → migrate to RevenueCat Ads); its one weakness (saturated category) is a positioning fix — locked niche: **South Asian / international graduates applying to jobs abroad** (silently filtered by ATS bots built for markets they don't know — authentic Dhaka-team story).
- **If never activated:** it simply waits for after the competition.

**Future feature roadmap (owner's wish, recorded):** the long-term vision is bigger than resume checking — expand into a broader career tool ("a lot of things"), with new features chosen **based on real usage data** after launch, not guesses. **Scope guard (binding):** during any Shipaton window, the app launches NARROW (resume check + ATS + the credit loop); data-driven expansion is a **post-competition** activity. The winning pattern is one sharp wedge first, platform later — expansion before traction is the classic way to lose both.

### 9.7 Resume Coach — REACTIVATED by owner override (2026-08-01)

**This section reverses §9.6 and the Resume-app row of the §9.2 matrix. Both are left above
exactly as written — they are the record of what was decided in July, and this is the record
of what changed. Read them together, not instead of each other.**

| | |
|---|---|
| **Decision** | Resume Coach **enters Shipaton 2026** as a second entry alongside NoteTube. |
| **Who** | Owner (Gk), explicit instruction, 2026-08-01. |
| **Targets** | **Design Award** (primary), **HAMM**, **Catvertising**. |
| **What it reverses** | §9.6 "shelved / parachute, activate only if the ruling goes AGAINST NoteTube" — the trigger never fired (§9.4) and the app is being activated anyway. §9.2's matrix row listing **Design as "physically closed"** for this app. |

**The risk this accepts, stated plainly because §9.1 called it the one forbidden move.**
§9.1 argues a small team cannot grow two user bases, run two build-in-public streams and
iterate two paywalls inside a two-month scored window, and §9.2 shelved this app precisely
so a second app would not land on the lead's plate. That argument has not been refuted — it
has been **overruled**. Anyone planning against this section should treat attention, not
build time, as the binding constraint, and should expect the §9.3 NoteTube calendar to be
the first thing that suffers if something has to give.

**What is being built on the strength of this decision:** a resume **format system** —
several ATS-safe templates, an on-device recommendation engine, a live preview and a
template-aware export. Research dossier lives in the app repo at
`docs/shipaton/research-resume-format-system.md`.

The Design case rests on one claim, and it is worth re-testing before submission rather
than repeating: of eleven competitors surveyed, **none combines a situational quiz, a stated
rationale, a live preview and a per-template ATS signal in a single flow.**

**Unchanged by this override:** pricing and the credit unit stay **parked** (owner,
2026-07-28); the launch stays narrow per the §9.6 scope guard; NoteTube remains the primary
track.

---

## 10. Winning Strategy & Execution Roadmap

### 10.1 Positioning principles (apply to whichever app)
- Lead the description with a **story** (pain → build → numbers), not a feature list.
- Pick **one persona** and one clear value sentence a stranger understands (shareability → downloads → Grand Prize).
- Make monetization a **narratable story**, not a pricing matrix.
- **Front-load the video + screenshots** — many judges never open the app.

### 10.2 Timeline
**Now → Jul 31 (runway — where most teams fail by not starting):**
- Lock the niche + origin story. Set up Apple ($99/yr) / Google ($25) / Samsung dev accounts **now** (approval + first review are the schedule killers).
- Verify the student's academic email is on the **JetBrains/swot** list for Next Gen.
- Stand up RevenueCat project, Offerings, entitlement, and a Paywall in the dashboard.
- Start the **#BuildInPublic** account (X + TikTok/YouTube) and post *before* Aug 1. Grab ShipKit credits.
- Do **not** publish any app before Aug 1 (disqualifies it).

**Aug 1–14 (ship absurdly early):** Publish a lean-but-usable v1 with a working paywall to the store(s). A week-one store link is a major Grand Prize advantage over teams that submit Sep 30.

**Aug 15 → Sep 20 (iterate + grow + document):** This is where prizes are won, not in code. Run a **RevenueCat Experiment** on the paywall. Ship weekly. Do real marketing (niche communities, one subreddit/Discord, influencer outreach, a shareable "score card"). Post daily. Collect real metrics.

**Sep 21–30 (submission as a production):** Nail the **≤2-min video** (hook in first 10s). Story-driven description. Test the **free trial / promo code**. Embed **RevenueCat verified public metrics** to prove traction.

### 10.3 Criteria to nail (ranked)

> ⚠️ **Submission blocker on #1:** Apple is now **rejecting free-trial toggle paywalls** as confusing/misleading. If your paywall is RevenueCat-hosted, the toggle is configured in the **RevenueCat dashboard**, not in app code — grepping the repo finds nothing. Verify before submitting. See [`RevenueCat_Benchmarks_2026.md`](./RevenueCat_Benchmarks_2026.md) §3 (including the caveat that this rests on a single unverified citation and should be checked against Apple's current guidelines).

1. Working, **honest** RevenueCat paywall with ≥1 live IAP (and/or RevenueCat Ads for Catvertising).
2. Real published store link, **early**.
3. Tight ≤2-min demo video with an immediate hook.
4. Demonstrable **traction/growth** (for Grand Prize).
5. A documented **build-in-public** trail.
6. Polished, animated UX (use the intern designer here).
7. A narrative-driven description tied to one persona.

---

## 11. Ethical "Unfair Advantages"

1. **Go deep on the RevenueCat stack the way a judge would.** Use **Paywalls UI + a live A/B Experiment** and report the lift (speaks straight to Chapman). Layer **Targeting**, **Virtual Currency** (hybrid credits), **Web Billing / web-to-app Funnels**, **Customer Center**. Almost no one shows this fluency.
2. **Attack the under-contested categories.** **Catvertising** (new → smallest field) + **Next Gen** (student-only, low friction) + **Peace Prize** (mission niche). Avoid fighting the whole field in HAMM alone.
3. **Weaponize a documented AI build pipeline as content.** e.g., tag Claude Code on a GitHub issue → PR → CodeRabbit review → GitHub Action → TestFlight. Speeds the build *and* becomes your #BuildInPublic story. One activity, two categories.
4. **Turn monetization into a mission story.** Outcome-based credits ("free credits back when you land an interview") reframes a "resume subscription" into a "job-outcome engine" — HAMM hook *and* the authentic mission angle at once.

---

## 12. Current State & Next Actions

**All strategic decisions are LOCKED (see §9.2–9.4). Nothing is pending except execution.**

**Gk's ONE current task (Wk Jul 6):** one NoteTube sandbox purchase, end-to-end, verifying the RC offering + webhook. Nothing else exists until it's done.

**Per-owner task lists:**
- **Gk:** weekly calendar in §9.3, one week at a time. Plus: register team on Devpost/Shipaton + grab ShipKit; set up X account and first BuildInPublic posts before Aug 1; start a journey log.
- **Intern:** follows `sleep-switch-intern-guide.html` (interactive checklist with Cursor prompts, progress auto-saves). Needs from Gk: the repo link + a 5-minute kickoff pointing at task 0.0.
- **Student:** confirm academic email domain is on the **JetBrains/swot** list (10 min). At submission time: make Sleep Switch repo public + submit code + video to Next Gen.
- **Game teammate (only if Track 4 activates):** small one-mechanic game, fully self-owned, Sep 1 kill-switch.

**Date-triggered checks:**
- [ ] **Day official rules drop (before Aug 1):** verify the "brand-new app" wording (§9.4) + the §2 Unconfirmed list.
- [ ] **When the 5 influencers are announced:** 10-minute match check (students/study → NoteTube; sleep/wellness → Sleep Switch). Never build for it.

**Next things to ask the AI when resuming:**
- "Write the ≤2-min NoteTube demo video script + the story-driven Devpost description."
- "Help me design the paywall A/B experiment (trial vs no-trial) and how to read results."
- "Help me assemble the #BuildInPublic submission story from my journey log."
- "The official rules just published — here's the text: [paste] — verify NoteTube's eligibility."

---

## 12.5 #BuildInPublic Content Engine + AI Prompt Library

> **INSTRUCTION TO ANY AI READING THIS KNOWLEDGE BASE:** When Gk asks for build-in-public content, follow this section exactly. Generate posts for **X (primary — this is what the #BuildInPublic award judges)** and a **LinkedIn cross-post version** of the same content (secondary, adapted tone). Never invent fake progress, fake numbers, or fake struggles — only write from what Gk actually reports. Authenticity is the judged criterion; fabrication would destroy the entry.

### Posting rules (the AI must apply these)
- **Voice:** plain, honest, specific. Short sentences. No corporate tone, no buzzwords, no "thrilled to announce." The 2025-confirmed judging criteria: *sharing your story creatively, engagement/ideas incorporated from community feedback, and lessons learned* — audience size explicitly does NOT matter.
- **Format per X post:** 1–3 sentences + 1 screenshot suggestion + hashtags **#BuildInPublic #Shipaton** (tagging these is how posts count).
- **LinkedIn version:** same content, slightly expanded (3–6 sentences), first line must hook (LinkedIn truncates), same honesty rules.
- **Cadence:** ~4–5×/week during Aug–Sep; start before Aug 1. One work session = one post; the post is a byproduct, never a task.
- **Best post types (in value order):** (1) shipped-a-community-suggestion (screenshot the suggestion + the shipped feature — the literal judged criterion), (2) honest struggle/bug story with the lesson, (3) small win with a visual, (4) metric milestone, (5) decision + why.
- **Journey log:** after generating any post, remind Gk to add one line (date + link + topic) to the journey log — it becomes the Devpost #BuildInPublic story at submission.
- Post launch content in the Shipaton Discord **#post-engagement-boost** and **#launch-day** channels for amplification.

### Visuals for posts (image rules + generation prompts)

**Rule 1 — REAL beats generated.** For #BuildInPublic, authenticity is the judged criterion: a real screenshot (code in Cursor, app on your phone, RevenueCat dashboard, a bug on screen, a hand-drawn sketch) creates more attachment and trust than any polished AI graphic. Default every post to a real screenshot. AI-generated images that look like ads can make a build-in-public post feel corporate — the opposite of what wins.

**Rule 2 — Generated images are for MOMENTS.** Use them only when there's nothing real to show or the moment deserves ceremony: origin post, launch day, milestones (first user, first sale, 100 users), submission day. Style must stay consistent across the campaign (pick one style, reuse it — it becomes your visual identity).

**Rule 3 — Never generate fake evidence.** No AI-generated "dashboard screenshots," fake metrics, or fake app UI presented as real. Generated images must be clearly illustrative/celebratory, not documentary.

**Image-generation prompt templates** (paste into any image AI; keep [brackets] filled from post context):

- **Campaign style anchor (decide once, prepend to every image prompt):** "Flat illustration style, dark indigo night palette with one warm amber accent, minimal, hand-crafted indie feel, no text in image, 16:9."
- **Origin post:** "[STYLE]. A solo developer at a desk at night, laptop glowing, YouTube-style video window and floating flashcards around them, mood of quiet determination, second-attempt comeback energy."
- **Launch day:** "[STYLE]. A small paper rocket launching from a smartphone screen into a night sky, confetti of tiny flashcards and play buttons, celebratory but humble."
- **Milestone (users/revenue):** "[STYLE]. A tiny sprout growing from a phone into a small plant with [N] leaves, night sky background, sense of early honest growth."
- **Struggle/bug post:** "[STYLE]. A developer facing a tangled ball of yarn shaped like a code bracket, one loose thread leading toward light — mood: stuck but finding the way." (Use sparingly — a real screenshot of the actual error is usually stronger.)
- **Submission day:** "[STYLE]. A wrapped parcel with a wax seal being placed into a mail slot shaped like a trophy, night-to-dawn gradient sky."
- **Concept/feature tease:** "[STYLE]. [Describe the feature as a simple physical metaphor, e.g. 'a video screen folding itself into a stack of flashcards']."

**AI instruction:** when generating a post via the §12.5 prompts, also state which visual to use — "real screenshot of X" (default) or one of the templates above (moments only) — matched to the post's content.

### Prompt library (copy-paste into any AI session with this knowledge base loaded)

**Daily post:** "Read the knowledge base §12.5 and follow its rules. Here's what I did today on [app]: [2–3 lines of what actually happened, incl. any bug/struggle/win]. Write 1 X post + 1 LinkedIn cross-post in my voice, with a screenshot suggestion and hashtags."

**Feedback-shipped post (highest value):** "Per KB §12.5: someone suggested [X] (link/screenshot), and I shipped it today. Write the X + LinkedIn posts showing the suggestion→shipped loop explicitly."

**Origin post (pinned, pre-Aug 1):** "Per KB §12.5, write my origin post: last year I entered Shipaton 2025 with [app]; this year I'm back with [what changed]. Honest comeback framing, no hype. X + LinkedIn versions."

**Weekly task check:** "Read KB §9.3. Today is [date]. What is my ONE task this week, and what's the first 30-minute step?"

**Launch-day post:** "Per KB §12.5 + §9.3: the app is live [store link]. Write the launch post (X + LinkedIn) + a short version for Discord #launch-day."

**Demo video script:** "Read KB §9.3 + §10. Write the ≤2-min demo video script for [app]: hook in first 10 seconds, real-device shot list + narration."

**Devpost description:** "Read KB §9 + §10.1. Write the story-driven Devpost description for [app]: pain → build → what's different → honest monetization → traction [numbers I'll fill in]."

**#BuildInPublic submission story (Sep 21–30):** "Here is my journey log: [paste]. Per KB §12.5, assemble the #BuildInPublic Devpost narrative: arc, lessons learned, and the feedback→shipped evidence, with post links."

**Rules-ruling update:** "RevenueCat replied to my eligibility question: [paste reply]. Read KB §9 and tell me the final app decision per the decision tree, then update the knowledge base."

**Intern/student briefs:** "From this KB, extract a half-page brief containing ONLY what the [intern / student] needs — nothing about other tracks."

---

## 12.6 NoteTube PROJECT_BRIEF.md (embedded master copy — for Cursor)

> **How to use:** Copy everything between the START/END markers into a file named `PROJECT_BRIEF.md` in the **NoteTube repo root**. Cursor reads it automatically as project context in every session. **This knowledge base holds the master copy** — if a decision changes here, re-copy the section into the repo. You manage ONE file (this one); the repo copy is a mirror.

```
===== START PROJECT_BRIEF.md =====
# NoteTube — Project Brief for AI coding assistants
Read this before generating or changing any code in this repo.

## What we are building
A Flutter app for EXAM-CRAMMING STUDENTS: "Pass your exam from the
YouTube lectures you already watch." Watch a lecture → get notes,
flashcards (spaced repetition), and quizzes. Entry for RevenueCat
Shipaton 2026 (target category: HAMM — smartest honest monetization).

## Locked architecture decisions (do NOT contradict these)
1. YOUTUBE: Use ONLY YouTube's official embedded player (IFrame /
   official player SDK). Users must keep watching ON YouTube.
   NEVER scrape transcripts, NEVER browse YouTube in a WebView,
   NEVER call unofficial endpoints (e.g. timedtext). If existing
   code does this, it must be replaced, not extended.
2. SCOPE: Core loop only = watch → notes → flashcards → quiz.
   HIDE (do not delete) everything else for launch: creator tools,
   Notion/Readwise sync, concept maps, chat-with-video extras.
   Prefer feature flags / route removal over code deletion.
3. MONETIZATION: One hero product — "Exam Cycle", ~$79.99 / 90 days,
   expiring by design ("expires when your exam does").
   One cheap monthly as fallback. Other legacy tiers stay hidden.
   RevenueCat is the source of truth: Paywalls v2 via PaywallView
   (purchases_ui_flutter), entitlement `notetube_pro`, server-side
   quota enforcement stays in Cloud Functions (never client-writable).
4. HONEST PAYWALL RULE: Never interrupt an active study session
   with an upsell. Paywalls appear only at natural entry points.
   No dark patterns, no fake urgency, no hidden renewals.

## Hard constraints
- Do NOT publish to any store before August 1, 2026 (disqualifies
  the app from Shipaton). First public release must be Aug 1–Sep 30.
- New app identity: new app name + NEW package name / bundle ID
  (this is a new product, not an update to the 2025 Android app).
- Keep free-tier AI quotas tight (free users route to cheap models);
  premium routes to the premium model. Quotas enforced server-side.
- Flutter + shared team_mvp_kit; RevenueCat purchases_flutter /
  purchases_ui_flutter (9.9.x). BLoC + Clean Architecture patterns
  already in the repo — follow them.

## Where to get technical truth
- RevenueCat: ALWAYS use current official docs (Flutter SDK,
  Paywalls v2, Experiments, webhooks). Do not trust memorized
  snippets if they conflict with current docs.
- YouTube: official IFrame Player API / official player solutions
  and YouTube Data API v3 only. Anything else is off-limits.

## Definition of done for any change
Builds clean → respects the 4 locked decisions → no scraping paths
introduced → paywall/entitlement logic still passes a sandbox
purchase → hidden features stay hidden.
===== END PROJECT_BRIEF.md =====
```

---

## 12.7 Resume App Reboot — Research & Feature Prompt Pack

> Run these in order. Prompts 1 goes in **Cursor** (needs the code); 2–4 go in a **Claude chat with web search** (or any research AI); 5 comes back to the strategist chat.

**1. Codebase rediscovery (Cursor, in the resume app repo):**
"Map this Flutter codebase for me in plain English. List: (1) every screen and what it does, (2) every feature that works end-to-end, (3) everything stubbed/fake/hardcoded (e.g. credits UI with no purchases, RevenueCat unwired), (4) the backend endpoints it calls, (5) what looks abandoned. End with a table: feature | status (works/stub/missing) | file location. I built this months ago and need to re-learn what exists."

**2. Demand research (Claude + web search):**
"Research what job-seekers actually pay for in resume/career apps in 2026. Read recent App Store & Google Play reviews of Rezi, Teal, Kickresume, and similar apps: extract (a) the top 5 praised features, (b) the top 5 complaints and 'I wish it did X' requests, (c) what's behind their paywalls and typical prices. Then list 5 feature opportunities that are demanded but underserved. Cite sources."

**3. Competition-gap research (Claude + web search):**
"I have an AI resume/career app and want the LEAST competitive positioning. Research: which job-seeker segments are underserved by the big resume apps (built mainly for US/EU applicants)? Specifically evaluate: international students & South Asian graduates applying to jobs abroad (visa-mention handling, foreign degree formatting, country-specific ATS/CV norms, IELTS/GRE context). Compare vs 2–3 other niche options (career switchers, fresh grads, non-native English speakers). For each: competition level, willingness to pay, reachable communities. Recommend one niche with reasoning."

**4. Feature-fit decision (Claude, paste outputs of 1–3):**
"Here's what my app already has [paste 1], what the market demands [paste 2], and my chosen niche [paste 3]. Design the LAUNCH SLICE: the 3–5 features (existing or small additions) that best serve this niche for an Aug 1 launch, a monetization suggestion (RevenueCat Ads free tier + credits/subscription hybrid), and a post-launch roadmap of everything else, ordered by expected demand. Bias heavily toward reusing what already works."

**5. Activation (strategist chat, this project):**
"Read the knowledge base. Here is the resume app's new scope: [3–5 lines from step 4]. Update §8.3 and the matrix, write the resume app's embedded PROJECT_BRIEF (same pattern as §12.6), and cut its weekly calendar from today to submission."

---



## 13. Sources

Primary (highest trust):
- RevenueCat Shipaton 2026 — Devpost overview & rules: https://revenuecat-shipaton-2026.devpost.com/
- Shipaton 2026 official site / prizes / Next Gen / host: https://www.shipaton.com/
- RevenueCat Shipaton 2026 launch post (Jul 2, 2026) & "How we judge Shipaton" (Jun 26, 2026): https://www.revenuecat.com/blog/
- Shipaton 2025 winners breakdown: https://www.revenuecat.com/blog/company/shipaton-2025-winners/
- Shipaton 2025 Devpost: https://revenuecat-shipaton-2025.devpost.com/
- 2024 (year one) recap: https://www.revenuecat.com/blog/engineering/revenuecat-ship-a-ton/

Judge backgrounds:
- David Barnard: https://www.revenuecat.com/blog/author/david-barnard/ ; https://www.businessofapps.com/app-leaders/david-barnard/
- Charlie Chapman: https://charliemchapman.com/ ; https://www.revenuecat.com/blog/engineering/how-i-successfully-migrated-my-indie-app-to-revenuecat-paywalls/

Context:
- "Vibecoding goes mainstream" (54k participants; Payout built with Claude Code + Cursor): https://www.einnews.com/pr_news/866676286/
- Rudrank Riyam #BuildInPublic 2024 interview: https://www.revenuecat.com/blog/company/shipaton-interview-with-rudrank-riyam/

Research passes reconciled into this doc: Gemini Deep Research (Jul 4, 2026), ChatGPT Deep Research (Jul 4, 2026), and live page fetches. Where sources conflicted, official RevenueCat/Devpost/Shipaton pages were treated as source of truth; unresolved conflicts are flagged in §2.

*Note: aggregator listings (e.g., Internshala) lagged the official pages on prize totals. Disregard the "IIT Madras / 'Bloom' / $20,000 winner" press item — the 2026 event had not started at compile time, so no winners exist.*
