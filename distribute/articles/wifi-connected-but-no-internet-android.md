---
title: "Wi-Fi Connected but No Internet on Android: The Fix Order That Works"
description: "Connected only means your phone reached the router. Captive portals, Private DNS and WebView break the internet while every indicator still says healthy. Here is the order that eliminates causes fastest."
tags: android, networking, wifi, dns, troubleshooting
canonical_url: https://apps.teamzlab.com/blog/wifi-connected-but-no-internet-android/
slug: wifi-connected-but-no-internet-android
pin_image: https://apps.teamzlab.com/devicegpt/og.png
og_image: https://apps.teamzlab.com/devicegpt/og.png
---

Your phone says it is connected. The Wi-Fi icon is full. And nothing loads. **Wi-Fi connected but no internet** is one of the most confusing states Android can be in, because every indicator says the connection is healthy while every app disagrees.

The reason it is confusing is worth understanding: "connected to Wi-Fi" only means your phone successfully joined **the router**. It says nothing about whether traffic can travel past that router, whether names can be looked up, or whether the network is waiting for you to sign in first. Those are separate steps, and any one of them can fail silently.

This guide walks the failure points in the order that eliminates the most possibilities fastest.

## Step 1: Decide whether it is the network or the phone (20 seconds)

Turn Wi-Fi **off** and load any page on mobile data.

- **Works on mobile data, fails on Wi-Fi** → the fault is that specific network. Jump to Step 3 and Step 4.
- **Fails on both** → the fault is on the phone, or the site itself is genuinely down. Go to Step 2.
- **Works on both now** → you had an intermittent fault, which is the hardest kind. See Step 5.

This single test eliminates half the possible causes, and it is the step most guides skip in favour of "restart your router."

## Step 2: Is the site down, or is it you?

Before changing settings, confirm the destination is alive. Try a second, unrelated site. If one specific site fails everywhere while others load fine, nothing on your phone will fix it — the site is down and waiting is the only option.

If **every** site fails but the phone reports a working connection, keep going.

## Step 3: The network wants you to sign in (captive portal)

This is the most common cause of "connected but no internet" outside your own home, and almost nobody names it.

Cafe, hotel, airport, office and campus Wi-Fi frequently use a **captive portal** — a sign-in or terms-acceptance page that must be completed before any traffic is allowed through. Until you finish it, the phone is genuinely connected to the router and genuinely unable to reach anything. Android sometimes shows a notification, and sometimes does not.

To trigger it manually, open a plain `http://` address rather than an `https://` one. Secure connections cannot be intercepted by the portal, so an https address will simply hang while an http address gets redirected to the login page.

## Step 4: Private DNS is pointing at something unreachable

DNS translates names like `example.com` into IP addresses. If DNS fails, everything fails, while Wi-Fi still reports connected.

Android has a system-wide **Private DNS** setting, and this is the trap: if it is set to a specific hostname and that provider is blocked or unreachable on your current network, every lookup in every app fails at once. Many networks — offices, schools, some mobile carriers, some countries — block third-party DNS providers, so a setting that works perfectly at home breaks completely elsewhere.

Check it at **Settings → Network & internet → Private DNS**. If it is set to a hostname, switch to **Automatic** and retest. If pages load immediately, you have found your cause.

### The VPN version of the same problem

A VPN replaces both your route and your DNS. A VPN profile that is technically active but cannot reach its server produces this exact symptom. Turn it **fully off** — not just disconnect — and retest.

## Step 5: Test more than once, because intermittent faults look healthy

Here is the mistake that costs the most time. You try a site, it fails, you change a setting, you try again, it works, and you conclude the change fixed it.

Often it did not. A connection that fails one request in five looks completely healthy if you only check once — and looks "fixed" by whatever you happened to do just before a successful attempt. This is why people end up convinced that some unrelated toggle solved their problem, then find it back the next day.

The fix is to test the same address several times in a row and count the successes. **"3 of 4 attempts worked, averaging 240 ms"** is a diagnosis you can act on. A single green tick is a coin flip.

## Step 6: The browser works but apps do not

If Chrome loads pages fine while your apps insist there is no internet, you have narrowed the problem considerably — and to somewhere most troubleshooting never looks.

Apps that display web content use **Android System WebView**, which is a separate component from Chrome with its own version and its own networking stack. Chrome ships its own copy of that engine, so Chrome can keep working while every WebView-based app fails. When those two disagree, the fault is in the WebView layer, not in your connection.

Two things to try:

1. Open the Play Store and check **Android System WebView** for a pending update.
2. Check the same for **Google Chrome**, since on many devices it provides the WebView implementation.

This also explains the "this site can't be reached" error appearing inside one app while the identical address opens normally in the browser on the same phone, in the same second.

## What to check, in order

1. Load a page on mobile data with Wi-Fi off — network fault or phone fault?
2. Try a second site — is the destination actually down?
3. Open a plain `http://` address — is a sign-in page waiting?
4. **Settings → Network & internet → Private DNS** → set to Automatic and retest.
5. Turn any VPN fully off and retest.
6. Test the same address four times and count successes — constant or intermittent?
7. Compare the browser against an app — if they disagree, update System WebView.
8. Only now: forget the network and rejoin, or restart the router.

[DeviceGPT](https://play.google.com/store/apps/details?id=com.teamz.lab.debugger) collapses several of these into one screen on Android. You type an address; it probes it four times and reports the pass count and average latency instead of a single tick, runs the same check again through the in-app browser so you can see whether the two stacks disagree, and shows which DNS servers are in use, whether Private DNS or a VPN is active, whether the network is holding you at a sign-in wall, and which System WebView build your phone is running.

## What no Android app can do for you

- **See another app's traffic or its DNS.** DNS settings are device-wide. Any app claiming to show which addresses a specific other app contacted is describing something Android does not permit.
- **Clear another app's cache or data.** Not possible without root since Android 6. A tool can only open that app's storage settings for you; you tap the final button.
- **Fix your router.** A phone can tell you the fault is upstream. It cannot repair it.

## Frequently asked questions

### Why does my phone say connected to Wi-Fi but no internet?

Joining the router and reaching the internet are separate steps. The usual causes are a captive portal waiting for sign-in, a Private DNS host that is unreachable on this network, an active VPN, or a genuine outage upstream of the router.

### Should I turn Private DNS off on Android?

Set it to Automatic while testing. If pages load immediately afterwards, that setting was the cause — a Private DNS hostname that is blocked on your current network breaks every app at once. You can re-enable it on networks where it works.

### Why does Wi-Fi work on my laptop but not my phone?

The phone has its own DNS settings, its own VPN state, and its own captive-portal status. Private DNS in particular is per-device and is a frequent reason one device fails on a network where everything else is fine.

### How do I know if the problem is my phone or the Wi-Fi?

Turn Wi-Fi off and load a page on mobile data. Working on data but not Wi-Fi points at the network; failing on both points at the phone or the site.

### Does restarting the router fix "connected but no internet"?

Sometimes, but it is the wrong first step because it fixes nothing when the cause is a captive portal, Private DNS or a VPN — and those are more common on a phone. Work through the list above first; a restart takes minutes and rules out very little.

## Related checks

If the network turns out to be fine, the next questions people usually have are whether something on the network is interfering — see [is my ISP spying on me](https://apps.teamzlab.com/blog/is-my-isp-spying-on-me-dns-dpi-ssl-check-android/) — or whether a specific service is blocked rather than broken: [is WhatsApp or Telegram blocked](https://apps.teamzlab.com/blog/is-whatsapp-telegram-blocked-network-reachability-test-android/).

## The short version

"Connected" only means your phone reached the router. Test on mobile data to split network faults from phone faults, open a plain http address to expose a sign-in wall, set Private DNS to Automatic, turn off any VPN, and test several times rather than once. Those five checks account for the large majority of Wi-Fi-connected-but-no-internet cases on Android — and none of them require restarting anything.
