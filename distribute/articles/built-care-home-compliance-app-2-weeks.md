---
slug: built-care-home-compliance-app-2-weeks
tags: javascript, firebase, pwa, healthcare, startup, webdev, showdev
canonical_url: https://tool.teamzlab.com/apps/always-ready-care/
og_image: https://tool.teamzlab.com/og-images/compliance.png
language: en
---

I built a full compliance evidence app for UK care homes in 2 weeks. Here's the tech stack, architecture decisions, and what I learned about building for healthcare.

## The Problem

UK care homes must maintain continuous compliance evidence for CQC (Care Quality Commission) inspections. There are 29,700+ registered care locations in England. 37% still use paper. The rest use expensive all-in-one platforms (£179-£4,500/month) that require ripping out existing systems.

Nobody offers a lightweight evidence-only layer that works alongside existing software.

## What I Built

**AlwaysReady Care** — a PWA that does one thing: compliance evidence capture, review, and export.

**Live:** [tool.teamzlab.com/apps/always-ready-care/](https://tool.teamzlab.com/apps/always-ready-care/)

### Features
- 12 evidence templates (medication, personal care, safeguarding, incidents, etc.)
- AI-assisted evidence structuring (rule-based, no API keys in frontend)
- 21 compliance categories mapped to CQC 5 key questions
- Role-based access (Carer → Senior → Manager → Director → Admin)
- Real-time evidence review (approve/reject workflow)
- Compliance readiness dashboard with SVG score circle
- Follow-up action tracking with overdue alerts
- One-click inspection pack generation
- Offline-first (Service Worker + IndexedDB + Firestore persistence)
- Team management (admin panel)
- PWA installable with app icons and status bar theming

## Tech Stack

- **Frontend:** Pure HTML/CSS/JS (no framework, no build step)
- **Backend:** Firebase (Auth, Firestore, Storage, Hosting)
- **Auth:** Google Sign-In + Email/Password + Anonymous
- **Offline:** Service Worker + IndexedDB queue + Background Sync API
- **AI:** Client-side rule-based analysis (12 risk keyword categories, tag extraction)
- **Design:** Custom CSS with dark/light theme via CSS custom properties
- **PWA:** manifest.json, 10 icon sizes, apple-mobile-web-app-capable

Total JS: ~2,500 lines. Total CSS: ~2,000 lines. No dependencies except Firebase SDK.

## Why No Framework?

Healthcare software needs to be:
1. **Fast** — carers have 60 seconds between tasks
2. **Offline-ready** — rural care homes have spotty internet
3. **Simple to deploy** — one folder to Firebase Hosting
4. **Easy to audit** — no node_modules black box for compliance review

Vanilla JS + Firebase compat SDK gave me all of this with zero build complexity.

## Firestore Structure

```
orgs/{orgId}/
  users/{uid}        → role, siteIds
  sites/{siteId}     → name, address
  evidence/{id}      → type, status, rawText, manualTags, attachments
  actions/{id}       → title, priority, status, dueDate
  packs/{id}         → dateRange, evidenceCount
  config/categories  → required compliance categories
  auditLogs/{id}     → immutable action log
```

Security rules enforce org-level isolation. Evidence documents can never be deleted (audit trail requirement). Audit logs are create-only (immutable).

## The AI Part (No API Keys Exposed)

Instead of calling Gemini/OpenAI from the frontend, I built a rule-based analysis engine:

- **22 tag categories** with keyword matching (medication, safeguarding, falls, etc.)
- **12 risk detection keywords** (fall, injury, bruise, bleeding, choking, etc.)
- **Risk level scoring** (low/medium/high based on keyword count)
- **Follow-up action suggestions** based on detected risks

It's not as smart as an LLM, but it's:
- Free (no API costs)
- Private (nothing leaves the browser)
- Instant (no network latency)
- Deterministic (same input = same output, important for healthcare)

A real Gemini backend is planned for the Pro tier.

## Organic Growth Strategy

Instead of paid marketing, I built:
- **40 location-specific SEO pages** targeting "care home compliance software [city]" for every major UK city
- **3 free CQC tools** (checklist, score calculator, readiness quiz) that funnel to the app
- **FAQ schema** targeting "how to prepare for CQC inspection" and similar questions

All leveraging an existing tool site with 2,100+ indexed pages and established domain authority.

## What I'd Do Differently

1. **Start with the PDF export** — care managers care most about the inspection pack
2. **Build the admin panel first** — the buyer (manager) needs to add their team before carers can use it
3. **Talk to a care home manager before building** — I built features based on research, but real user feedback would have saved time

## Try It

- **App:** [tool.teamzlab.com/apps/always-ready-care/](https://tool.teamzlab.com/apps/always-ready-care/)
- **Free tools:** [CQC Checklist](https://tool.teamzlab.com/compliance/cqc-inspection-checklist/) | [Compliance Score](https://tool.teamzlab.com/compliance/care-home-compliance-score/) | [Readiness Quiz](https://tool.teamzlab.com/compliance/cqc-readiness-quiz/)

If you work in UK social care or know someone who does, I'd love feedback.
