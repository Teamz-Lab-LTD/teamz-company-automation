---
slug: is-my-isp-spying-on-me-dns-dpi-ssl-check-android
title: "Is My ISP Spying on Me? How to Check DNS Manipulation, DPI & SSL Hijacking on Android (Free)"
tags: android, isp-privacy, dns-manipulation, deep-packet-inspection, ssl-hijacking, network-privacy, vpn, internet-privacy, isp-tracking, free
canonical_url: https://apps.teamzlab.com/devicegpt/
language: en
og_image: https://apps.teamzlab.com/devicegpt/og-image.png
pin_image: https://apps.teamzlab.com/devicegpt/og-image.png
status: draft
series: devicegpt-deep-dives
---

Your Internet Service Provider (ISP) can see every website you visit, every app you use, and every connection your phone makes. Most people know this in theory — but few ever check whether their ISP is actively manipulating their traffic.

Some ISPs go further than passive logging. They redirect your DNS queries to inject ads. They use Deep Packet Inspection to read your data. They perform SSL certificate hijacking to intercept encrypted traffic. And almost nobody has a tool to detect it.

Until now.

## What Your ISP Can Actually See (And Do)

Before we get to detection, here's what ISPs are technically capable of:

**DNS Manipulation:** Every time you type a website address, your phone sends a DNS query — essentially asking "what's the IP address for google.com?" Your ISP controls the default DNS server. A manipulating ISP can redirect these queries to inject ads, block websites, or track every domain you visit.

**Deep Packet Inspection (DPI):** Even for encrypted traffic, your ISP can see the size, timing, and destination of every packet. DPI goes further — on unencrypted connections, ISPs can read the full content. Some ISPs use DPI to throttle streaming services, block competitors, or sell your browsing data.

**SSL Certificate Hijacking (MITM):** The most dangerous attack. A rogue ISP or network operator installs a fake certificate authority, allowing them to decrypt your "secure" HTTPS connections, read the plaintext, then re-encrypt it. Your browser shows a padlock — but the ISP is reading everything in between.

**Transparent Proxy:** Your traffic gets routed through an ISP-controlled proxy without your knowledge. The proxy can cache, modify, or log all traffic passing through it.

## How DeviceGPT Detects ISP Surveillance (The Only Free App That Does This)

No other phone health app runs ISP privacy tests. [DeviceGPT](https://play.google.com/store/apps/details?id=com.teamz.lab.debugger) built this as a core feature because network privacy is just as important as device privacy.

Open DeviceGPT → Network tab → Privacy Tests.

### Test 1: DNS Integrity Check

DeviceGPT queries multiple DNS resolvers and compares the results. If your ISP is manipulating DNS:
- The IP address returned for a known domain won't match the legitimate address
- DNS responses arrive from unexpected IP addresses
- Certain domains return ISP-controlled redirect addresses instead of real ones

**What it means if it fails:** Your ISP is intercepting and modifying your DNS queries. Solution: enable Private DNS (DNS-over-TLS) in Settings > Network > Private DNS, or use a VPN.

### Test 2: SSL Certificate Validation

DeviceGPT connects to known servers and validates the entire SSL certificate chain. It checks:
- Is the certificate issued by a trusted root authority?
- Does the certificate match the expected domain?
- Are there unexpected intermediate certificates in the chain?

**What it means if it fails:** Someone is performing a man-in-the-middle attack on your HTTPS connections. This is extremely serious — stop using this network for anything sensitive.

### Test 3: Deep Packet Inspection Detection

DeviceGPT sends specially crafted packets to probe whether DPI is active on your network:
- Tests whether HTTP headers are being modified in transit
- Checks if packet timing patterns match known DPI signatures
- Probes whether specific protocols are being throttled or blocked

**What it means if it fails:** Your ISP is reading and potentially modifying your internet traffic.

### Test 4: Transparent Proxy Detection

DeviceGPT checks whether HTTP requests are being silently intercepted by a proxy:
- Sends requests with unique identifiers to known test servers
- Checks if the originating IP in server logs matches your real IP
- Detects proxy-injected headers in responses

**What it means if it fails:** Your traffic is being routed through an ISP-controlled proxy.

### Test 5: Private DNS Status

Are you already protected? DeviceGPT checks whether Private DNS (DNS-over-TLS) is active on your device — the simplest protection against DNS manipulation.

### Test 6: QUIC Protocol Probing

The QUIC protocol (used by HTTP/3) encrypts more connection metadata than traditional HTTPS, making it harder for ISPs to surveil. DeviceGPT tests whether your ISP blocks QUIC — a sign they prefer easier-to-monitor protocols.

### Test 7: ISP Tracking Score

DeviceGPT combines all test results into a **Network Trust Score** — a single grade (A through F) representing how much you can trust your current network.

## Real Speed Test (Not the Fake Kind)

Most speed test apps use nearby sponsored servers that make your ISP look faster than it is. DeviceGPT downloads a real 10MB file from Cloudflare's global network — the same infrastructure most websites use.

You also get:
- Latency and jitter measurements (important for video calls and gaming)
- WiFi signal strength (RSSI) in real dBm values
- IPv4 and IPv6 connectivity status
- VPN/proxy detection (is your VPN actually working?)

## Service Reachability Testing

DeviceGPT tests whether 10+ major services are reachable from your network:

- Google, YouTube, Google Drive
- WhatsApp, Telegram, Instagram
- GitHub, Cloudflare DNS (1.1.1.1)
- And more

If any are blocked, you'll see exactly which ones and why it matters.

## What To Do If Tests Fail

| Problem | Solution |
|---------|----------|
| DNS manipulation | Enable Private DNS: Settings > Network > Private DNS > "dns.google" or "1.1.1.1" |
| SSL hijacking | Stop using this network immediately. Use mobile data or a trusted VPN |
| DPI detected | Use a VPN with obfuscation (Mullvad, ProtonVPN) |
| Transparent proxy | Enable Private DNS or VPN |
| QUIC blocked | Use a VPN — your ISP is surveillance-optimising your connection |

## FAQ

**Q: Is this legal to run?**
A: Yes. You're testing your own connection to check what's being done to your traffic. You're not intercepting anyone else's data.

**Q: Does this work on mobile data (not just WiFi)?**
A: Yes. Run it on both WiFi and mobile data — your mobile carrier and WiFi ISP may behave differently.

**Q: Does DeviceGPT send my network data anywhere?**
A: No. All tests are run locally. No data is sent to Teamz Lab servers. The app is open source — verify this yourself on [GitHub](https://github.com/Teamz-Lab-LTD/device-gpt).

**Q: My ISP says they don't do any of this. Should I trust them?**
A: Run the tests and check yourself. Several major ISPs have been caught manipulating DNS and performing DPI despite denying it.

## Download

**Free. No root required. Open source.**

- [Google Play Store](https://play.google.com/store/apps/details?id=com.teamz.lab.debugger)
- [Source Code on GitHub](https://github.com/Teamz-Lab-LTD/device-gpt)

---

*Part of the [DeviceGPT Deep Dive series](https://apps.teamzlab.com/devicegpt/). Built by [Teamz Lab](https://apps.teamzlab.com).*
