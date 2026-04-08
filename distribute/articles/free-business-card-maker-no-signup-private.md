---
slug: free-business-card-maker-no-signup-private-beats-canva
title: "I Built a Free Business Card Maker That Runs Entirely in Your Browser"
tags: webdev, javascript, free-tools, design, networking, privacy, side-project
canonical_url: https://tool.teamzlab.com/tools/business-card-maker/
language: en
og_image: https://tool.teamzlab.com/og-images/tools.png
status: draft
---

Every time I needed a quick business card, the process was the same: open Canva, create an account, scroll through hundreds of templates that don't fit standard print sizes, pick one, realize the font I want is "Pro only," export with a watermark, and then upload my full name, email, and phone number to yet another cloud service.

For something as simple as a rectangle with your name on it, that's a lot of friction.

So I built a business card maker that skips all of it. No account. No watermarks. No server uploads. Your contact info stays in your browser from start to finish.

**Try it:** [tool.teamzlab.com/tools/business-card-maker](https://tool.teamzlab.com/tools/business-card-maker/)

## What It Does

You pick a template, fill in your details, and see a live preview update as you type. When you're done, you can:

- **Download a print-ready PNG** at 3x resolution (~1350x770px, exceeding 300 DPI at standard card size)
- **Export a vCard (.vcf)** that any phone or email client can import with one tap
- **Generate a MECARD QR code** that phones can scan to save your contact instantly
- **Copy a shareable link** that reconstructs your exact card design for anyone who opens it
- **Copy the card as an image** to paste into documents, chats, or slides

Everything happens client-side. There's no backend, no database, no analytics tracking your personal info.

## 10 Templates, Each for a Different Context

I didn't want 200 generic templates. I studied what was trending on Dribbble and Behance in 2026 and built 10 focused designs:

- **Ultra Minimal** — oversized typography, 70% whitespace. For designers who want the name to do the talking
- **Dark Luxury** — near-black gradient with gold accents. Consultants, lawyers, executives
- **Glassmorphism** — frosted glass over a mesh gradient. Tech founders, product managers
- **Geometric** — bold diagonal clip-path. Architects, engineers
- **Aurora** — vibrant mesh gradient. Marketers, brand strategists
- **Framed Classic** — serif name with inset border. Academics, finance professionals
- **Terminal** — monospace, code-style layout. Developers, DevOps engineers
- **Split Panel** — color block meets white section. Corporate professionals
- **Bold Statement** — oversized name on black. Entrepreneurs, speakers
- **Accent Stripe** — single emerald bar, clean and architectural. Works for any industry

Each template has a matching back design with QR code and contact details.

## The Technical Side (for Fellow Devs)

If you're curious about the implementation, here's what's under the hood:

**Live preview rendering.** Each template is a function that returns an HTML string. The preview div gets its `innerHTML` replaced on every input change — no canvas rendering during editing, so it stays snappy.

**Print-quality export.** When you hit Download, the tool uses `html2canvas` to render the card at 3x scale. The card element is temporarily resized, rendered to canvas, then restored. This gives a crisp output that exceeds 300 DPI at standard US business card size (3.5 x 2 inches).

**QR code generation.** The QR encodes a MECARD string — a format that predates vCard QR and has broader scanner compatibility. It looks like: `MECARD:N:Smith,John;TEL:+15551234567;EMAIL:john@example.com;URL:https://example.com;ORG:Acme Corp;;` — and most modern phone cameras (iOS 11+, Android 9+) parse it natively without any app.

**Shareable links without a server.** All card data is URL-encoded into query parameters. When someone opens the link, the page reads the params, populates the form, and renders the card. The data lives in the URL itself — no database, no expiring tokens, no monthly subscription. The link works as long as the page exists.

**vCard export.** A standard `.vcf` file is generated client-side using a Blob and `URL.createObjectURL()`. It includes name, job title, company, email, phone, website, address, and social profiles.

**Photo handling.** Photos are read with the FileReader API as data URLs and rendered inline. They never leave the browser — no upload endpoint exists.

## Card Sizes

The tool supports four regional standards:

| Region | Size | Pixels at 300 DPI |
|--------|------|--------------------|
| US/Canada | 3.5 x 2 in | 1050 x 600 |
| EU/ISO | 85 x 55 mm | 1004 x 650 |
| Japan | 91 x 55 mm | 1075 x 650 |
| Square | 2.5 x 2.5 in | 750 x 750 |

The default US card exports at ~1350x770px (3x), which gives you clean prints at any standard card size.

## Customization Options

Beyond template selection, you can override:

- **Accent color** — each template has a default, but you can set any color
- **Font family** — Poppins, Georgia, Courier, Arial, Trebuchet, or Verdana
- **Layout direction** — left-aligned, centered, or right-aligned
- **Border style** — none, thin, accent, double frame, or rounded thick
- **Background** — solid color or gradient override
- **Text color** — override all text with a single color
- **Name size** — slider from 16px to 40px, or auto
- **QR on front** — optionally show the QR code on the front side instead of the back

## Why I Built This

I already had a collection of browser-based tools at [tool.teamzlab.com](https://tool.teamzlab.com/), and business cards kept coming up as a request. The existing options fell into two categories:

1. **Full design tools** (Canva, Figma) — powerful but overkill for a business card. 15-30 minutes for one card
2. **Virtual card services** (HiHello, Popl, Blinq) — require accounts, charge monthly fees, and store your data on their servers

I wanted something in between: a focused tool that does one job well, in under 30 seconds, with zero data collection.

## Try It

The tool is free, runs in any modern browser, and works on mobile.

[tool.teamzlab.com/tools/business-card-maker](https://tool.teamzlab.com/tools/business-card-maker/)

If you have feedback or template ideas, I'd genuinely like to hear them.

---

*Built with vanilla JS, html2canvas, and a QR code library. No frameworks, no build step, no backend.*
