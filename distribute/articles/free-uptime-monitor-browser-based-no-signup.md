# I Built a Free UptimeRobot Alternative That Runs Entirely in Your Browser (No Sign-Up)

I wanted to check if a website was down without handing my email to yet another SaaS dashboard. So I built two free tools that run entirely in the browser — zero sign-up, zero server polling, zero telemetry. Both are under a minute to try, and one of them has a status-badge generator that gives you free README backlinks for your repo.

No account. No cloud. Nothing stored on a server. Your URL never leaves your machine.

---

## 1. Is My Website Down Right Now? — Instant Checker

**The problem:** When a site stops loading, you need to know in 5 seconds: is it actually down, or is it just me? The popular options all have catches — IsItDownRightNow routes your query through their server (they see everything you check), UptimeRobot needs an account and a monitor setup, DownDetector only works for the 100 biggest sites.

**The tool:** Type any URL and the tool fires four probes from inside your browser in parallel: a Cloudflare DNS-over-HTTPS lookup (does the domain resolve?), an HTTP reachability test, a favicon image probe, and a Resource Timing API measurement. The combined verdict is UP, UP (degraded), or DOWN, with response time, server IP, and DNS TTL displayed.

Pre-filled chips for the sites that go down often — Facebook, Instagram, X, ChatGPT, GitHub, Gmail, YouTube, WhatsApp — so you can click-and-check during the next big outage instead of typing.

**Bonus:** there's a status badge generator. Paste the generated markdown into any README and you get a live green/red pill that updates automatically via img.shields.io — free branded backlink, no account needed.

**Try it:** [Is My Website Down Right Now?](https://tool.teamzlab.com/diagnostic/website-up-checker/)

---

## 2. Website Monitor Dashboard — Unlimited Free Monitors (Browser-Based)

**The problem:** UptimeRobot Free caps at 50 monitors, Better Uptime Free caps at 10, Pingdom starts at $15/month. For quick deploy-time checks or watching a handful of SaaS vendors during an incident, you do not need 24/7 server polling — you just need a grid of live statuses.

**The tool:** Add unlimited websites to monitor. Every 60 seconds the dashboard runs three probes per site (Cloudflare DNS, no-cors HTTP, favicon) while the tab is open. Each monitor card shows live UP/DOWN status, uptime percentage over the last 30 cycles, average response time, and an SVG sparkline of the response-time trend. Pause/resume per monitor, check-all button, auto-throttle when the tab is hidden.

All settings and history live in your browser's localStorage — close the tab and polling stops, open the tab and it resumes. No server involved, no data leaves your machine.

**When to use this vs UptimeRobot:** this dashboard is for live tab-open monitoring (during deploys, while tracking a vendor incident, NOC-style watch mode). UptimeRobot and similar services are for 24/7 background alerts — the two complement each other.

**Try it:** [Free Website Uptime Monitor](https://tool.teamzlab.com/diagnostic/website-monitor-dashboard/)

---

## Why Browser-Side Monitoring Actually Matters

Every server-based uptime service tells you if the site is up from their datacenter. That is the answer to a different question than "is it up from my network right now?" When you are on hotel WiFi, behind a corporate proxy, or on a residential ISP having a bad routing day, a browser-side probe is the only honest answer.

It also means the tool can never sell your data, because the tool never sees your data. Your URL, your DNS lookup, your HTTP request — all of it leaves your browser directly for the target site. There is no Teamz Lab server in the middle.

---

## Tech Stack (for anyone curious)

- **DNS:** Cloudflare DNS-over-HTTPS (`cloudflare-dns.com/dns-query`)
- **HTTP probe:** `fetch(url, { mode: 'no-cors' })` with a 6-second timeout
- **Favicon probe:** `new Image()` with `onload`/`onerror` — bypasses CORS entirely
- **Response time:** `performance.now()` around each probe
- **Storage:** `localStorage` for monitors + history (30 cycles per monitor)
- **Sparkline:** inline SVG, zero dependencies
- **Status badge:** img.shields.io `/website` endpoint (free, rate-limited per IP)

No framework, no build step, no bundler. Two static HTML files with one inline script each.

---

## What's Next

If the positive response is there, I am planning:
- **Webhook alerting** — POST to a Discord/Slack webhook when status changes
- **Multi-region probes** — let you check from other regions via public CORS proxies
- **Export/import** — drop-in JSON for backing up or sharing your monitor list
- **PWA offline mode** — pin the dashboard as a standalone app

If you use it, try it during the next big outage (statistically, sometime in the next 48 hours there will be one) and let me know what breaks. All feedback welcome — the contact is on the Teamz Lab site footer.
