---
slug: i-built-1700-free-tools-in-2-weeks
tags: webdev, opensource, showdev, javascript, productivity
canonical_url: https://tool.teamzlab.com/tools/
---

Two weeks ago, I launched [tool.teamzlab.com](https://tool.teamzlab.com) with 1,700+ browser-based tools. No backend. No signups. No data collection. Everything runs client-side.

Here's what happened, what I learned, and the tools people actually use.

## The stack

- **Pure HTML/CSS/JS** — no React, no Next.js, no build step
- **GitHub Pages** — free hosting, zero server costs
- **CSS custom properties** — one design system, dark/light mode across 1,700 pages
- **Chrome AI + Transformers.js** — AI features that run in the browser, no API keys
- **Pre-commit hooks** — auto-rebuild search index, sitemap, SEO validation on every commit

Total monthly cost: **$0**

## What surprised me

**Bing sends more traffic than Google.** After 2 weeks, Bing organic is my #2 traffic source (530 sessions/week). Google is still warming up. If you're building tools, don't ignore Bing Webmaster Tools and IndexNow.

**People spend 3+ minutes on tools that generate something.** My [QR Card Generator](https://tool.teamzlab.com/ramadan/eid-salami-qr-card-generator/) averages 112 seconds per session. The [Cheque Book Maker](https://tool.teamzlab.com/ramadan/eid-salami-cheque-book/) hits 151 seconds. Calculators get 6 seconds. Lesson: **build generators, not just calculators.**

**Facebook referral traffic converts.** People share their generated cards/images back to Facebook, which drives more users. Viral loop without trying.

## 10 tools developers will actually use

1. **[AI Background Remover](https://tool.teamzlab.com/tools/ai-background-remover/)** — ML-powered, runs locally via Transformers.js. No upload to any server.

2. **[DNS Leak Test](https://tool.teamzlab.com/diagnostic/dns-leak-test/)** — check if your VPN is actually protecting your DNS queries.

3. **[JSON Formatter](https://tool.teamzlab.com/dev/json-formatter/)** — paste messy JSON, get formatted output. Syntax highlighting included.

4. **[Regex Tester](https://tool.teamzlab.com/dev/regex-tester/)** — test regex patterns with real-time match highlighting.

5. **[Base64 Encoder/Decoder](https://tool.teamzlab.com/dev/base64-encoder-decoder/)** — encode/decode text and files instantly.

6. **[JWT Decoder](https://tool.teamzlab.com/dev/jwt-decoder/)** — paste a JWT, see the decoded header and payload. No server involved.

7. **[Cron Expression Generator](https://tool.teamzlab.com/dev/cron-expression-generator/)** — build cron expressions visually with plain English descriptions.

8. **[Git Command Generator](https://tool.teamzlab.com/dev/git-command-generator/)** — describe what you want to do, get the git command.

9. **[Photo to Pencil Sketch](https://tool.teamzlab.com/image/photo-to-pencil-sketch/)** — convert any photo to a pencil sketch drawing using canvas filters.

10. **[Signature Font Preview](https://tool.teamzlab.com/tools/signature-font-preview/)** — type your name, see it in 20+ signature-style fonts. Download as PNG.

## The automation behind it

Every commit triggers:
- Search index rebuild (1,700+ tools searchable)
- Sitemap regeneration (pinged to Google + Bing)
- JSON-LD schema injection (BreadcrumbList, FAQPage, WebApplication)
- SEO validation (title length, meta description, keyword density)
- IndexNow submission (instant Bing indexing)
- Runtime QA in headless Chromium

22 automated checks prevent broken deploys. Zero manual SEO work.

## What I'd do differently

1. **Start with 10 high-quality tools, not 1,700.** Depth beats breadth for SEO. Google hasn't fully crawled everything yet.
2. **Build generators first.** They get 20x more engagement than calculators.
3. **Add share buttons from day one.** Social sharing creates backlinks naturally.

## Try it

The whole site is at [tool.teamzlab.com](https://tool.teamzlab.com). Search works across all 1,700+ tools. Everything is free, private, and runs in your browser.

If you're a developer building something similar, happy to share the pre-commit hook setup and automation approach — just drop a comment.

---

*Built by [Teamz Lab](https://teamzlab.com). If you find a tool useful, sharing it is the best way to support the project.*
