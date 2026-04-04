---
slug: is-whatsapp-telegram-blocked-network-reachability-test-android
title: "Is WhatsApp or Telegram Blocked? How to Test Network Reachability & Internet Censorship on Android (Free)"
tags: android, internet-censorship, whatsapp-blocked, telegram-blocked, network-reachability, vpn, isp-blocking, internet-freedom, network-test, free
canonical_url: https://apps.teamzlab.com/devicegpt/
language: en
og_image: https://apps.teamzlab.com/devicegpt/og-image.png
pin_image: https://apps.teamzlab.com/devicegpt/og-image.png
status: draft
series: devicegpt-deep-dives
---

You open WhatsApp and it won't connect. Telegram times out. Your VPN isn't working. Is the app down? Is your ISP blocking it? Is it your WiFi network? Is it a government block?

Most people can't tell the difference — and most tools don't help them figure it out. A standard speed test tells you your bandwidth is fine. But bandwidth being "fine" doesn't mean your apps aren't being blocked at a deeper level.

[DeviceGPT](https://play.google.com/store/apps/details?id=com.teamz.lab.debugger) runs a **network reachability test** that checks 10+ major services individually and tells you exactly which ones are blocked on your current network — and at what level.

## Why Apps Get Blocked (And How ISPs Do It)

Internet blocking operates at several levels, each requiring different detection methods:

**DNS Blocking:** The ISP's DNS server returns no result (or a wrong result) for a blocked domain. Your phone can't even find the IP address. Solution: use Private DNS (DNS-over-TLS) or a VPN.

**IP Blocking:** The ISP blocks traffic to specific IP addresses used by the service. Even if DNS resolves correctly, packets to those IPs are dropped. A VPN routes around this.

**Deep Packet Inspection (DPI) Blocking:** The ISP examines packet contents and drops traffic that matches certain patterns (e.g., Telegram's protocol signature). Requires a VPN with obfuscation to bypass.

**Port Blocking:** Specific network ports used by services are blocked. Less common but used against VoIP services.

**SNI-based Blocking:** The ISP reads the Server Name Indication in TLS handshakes (which is unencrypted) to identify and block specific HTTPS destinations even without breaking encryption.

## What DeviceGPT's Network Reachability Test Checks

DeviceGPT probes 10+ major services using multiple methods — not just a simple ping:

### Services Tested

| Service | Why It Matters |
|---------|----------------|
| **WhatsApp** | Most-blocked messaging app globally |
| **Telegram** | Blocked in multiple countries, frequent target |
| **Instagram** | Blocked during political unrest in many regions |
| **Google** | DNS/search blocking is the first sign of heavy censorship |
| **YouTube** | Bandwidth throttling and full blocks both detected |
| **Google Drive** | Cloud storage blocking affects work productivity |
| **GitHub** | Blocked for developers in several countries |
| **Cloudflare DNS (1.1.1.1)** | Tests if alternative DNS resolvers are reachable |
| **Cloudflare CDN** | Tests general internet infrastructure access |

### How It Tests (Beyond Simple Ping)

**TCP Connection Test:** Attempts to establish a real TCP connection to the service's servers — not just a ping. Tells you if the IP is reachable at all.

**HTTPS Handshake Test:** Goes a step further and completes a TLS handshake. Detects SNI-based blocking and SSL interception.

**QUIC/UDP Probing:** Tests whether the service is reachable over QUIC (HTTP/3), which some ISPs block specifically to force traffic through more-monitorable protocols.

**DNS Resolution Comparison:** Resolves the service domain through your ISP's DNS, then through 1.1.1.1, and compares results. Mismatch = DNS manipulation.

### The Network Openness Score

After running all tests, DeviceGPT calculates a **Network Openness Score** — how freely your current network allows access to the open internet. This score changes when you:
- Switch from WiFi to mobile data
- Connect to a different WiFi network
- Enable or disable a VPN
- Change your Private DNS settings

Run the test on each network you use — your home WiFi, mobile carrier, work network, and coffee shop WiFi may all have different scores.

## Countries Where This Is Most Useful

DeviceGPT's network tests are especially valuable in countries with significant internet restrictions:

**Turkey:** WhatsApp, Twitter/X, Instagram, and Discord have all been blocked during periods of civil unrest. ISPs are legally required to implement blocks when ordered by the government.

**Iran:** Telegram is permanently restricted. WhatsApp calling is blocked. Instagram is intermittently blocked. VPN usage is common but many VPN IPs are blocked too.

**Russia:** LinkedIn has been blocked since 2016. Instagram was blocked in 2022. Twitter/X was slowed to near-unusable speeds. Deep packet inspection is widely deployed.

**Pakistan:** TikTok has been blocked multiple times. YouTube was blocked for several years. WhatsApp restrictions occur during protests.

**Indonesia:** Multiple apps and websites have been blocked by the government at various points. The Kominfo ministry regularly adds domains to blocklists.

**Corporate/School Networks:** Even outside censoring governments, corporate firewalls and school networks often block social media, gaming services, and messaging apps.

## Understanding Your Results

| Result | What It Means | Solution |
|--------|---------------|---------|
| Reachable | No blocking detected | No action needed |
| DNS blocked | ISP's DNS returns wrong result | Enable Private DNS or VPN |
| IP blocked | Traffic to service IPs is dropped | Use a VPN |
| DPI blocked | Protocol-level blocking | Use a VPN with obfuscation |
| Timeout | Service is slow or partially blocked | Try a different network or VPN |
| SSL mismatch | Someone is intercepting your connection | Stop using this network |

## Using DeviceGPT to Test Your VPN

Many VPNs claim to bypass censorship — but don't actually work on the specific blocks in your country. DeviceGPT lets you:

1. Run the reachability test without VPN → see what's blocked
2. Enable your VPN
3. Run the test again → see what's now accessible

If certain services are still blocked with your VPN on, your VPN isn't routing those properly. Try a different server location or VPN protocol.

DeviceGPT also detects whether your VPN's DNS is leaking — a common issue where your VPN routes traffic but uses your ISP's DNS, still revealing what you're accessing.

## FAQ

**Q: Does this work to test school or work WiFi blocks?**
A: Yes. Connect to the network, run the test, and see exactly which services your institution blocks.

**Q: Can this help me bypass blocks?**
A: DeviceGPT detects blocks — it doesn't bypass them. To bypass, use a VPN (we recommend checking ProtonVPN or Mullvad for countries with heavy censorship).

**Q: Does this use a lot of data?**
A: The full reachability test uses approximately 15-20MB of data (including the speed test). The connectivity-only tests use less than 1MB.

**Q: Is this legal to run in my country?**
A: Testing what you can access on your own connection is legal everywhere we're aware of. Using VPNs to bypass government blocks varies by jurisdiction.

## Download

**Free. No root required. Works anywhere in the world.**

- [Google Play Store](https://play.google.com/store/apps/details?id=com.teamz.lab.debugger)
- [Source Code on GitHub](https://github.com/Teamz-Lab-LTD/device-gpt)

---

*Part of the [DeviceGPT Deep Dive series](https://apps.teamzlab.com/devicegpt/). Built by [Teamz Lab](https://apps.teamzlab.com).*
