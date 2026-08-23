---
title: "7 Real Signs an Android Phone Has Spyware (and the Ones That Mean Nothing)"
description: "Battery drain alone does not mean you are hacked. Here are the signals that actually indicate Android spyware, the ones that are just normal wear, and how to check each one."
tags: android, privacy, security, spyware, mobile
canonical_url: https://apps.teamzlab.com/books/is-your-android-phone-hacked/
slug: signs-android-phone-hacked-spyware-check
pin_image: https://apps.teamzlab.com/og/books-is-your-android-phone-hacked.png
og_image: https://apps.teamzlab.com/og/books-is-your-android-phone-hacked.png
---

Search "is my phone hacked" and you get a wall of articles listing battery drain as sign number one. Battery drain is the least useful signal there is — every Android battery degrades, and every OS update makes the phone work harder. If that is your only symptom, you almost certainly have an old battery, not spyware.

Here is a more honest split.

## Signals that mean nothing on their own

- **Battery draining faster than last year.** Lithium cells lose measurable capacity every year. Normal.
- **Phone feels warm while charging or navigating.** Normal.
- **Occasional ads in a free app.** That is the business model, not an infection.
- **A random unknown app you do not recognise.** Most are carrier or OEM preinstalls with unhelpful names.

Chasing these produces anxiety and no answers.

## Signals that actually matter

**1. Mobile data used by an app that should not need it.**
Settings → Network & Internet → Data usage. Sort by usage. A calculator, wallpaper or flashlight app sitting near the top is a real red flag — spyware has to send what it collects somewhere, and that costs data.

**2. The camera or microphone indicator dot appearing when you are not using them.**
Android 12+ shows a green dot top-right when the camera or mic is active. If it appears while your screen is idle, something is recording. This is one of the few signals that is close to conclusive.

**3. An app holding Accessibility Service permission that has no reason to.**
Settings → Accessibility → Downloaded apps. Accessibility is the single most abused permission on Android — it lets an app read everything on screen and simulate taps. Legitimate users: screen readers, password managers, automation tools. Nothing else.

**4. A Device Admin app you did not add.**
Settings → Security → Device admin apps. Stalkerware commonly registers here because it makes uninstalling much harder.

**5. Screen activity when the phone is idle.**
Screen waking, brief flashes, the phone getting warm in your pocket while doing nothing.

**6. Google account shows a login from a device or place you do not recognise.**
myaccount.google.com → Security → Your devices. Most "phone hacked" cases are actually a compromised Google account, not a compromised phone. This is the check people skip, and it is often the real answer.

**7. Someone knows things they should not.**
Unglamorous, but in practice this is how most stalkerware is discovered — not by a scanner, by a person noticing that a partner or family member knows about a message or a location they had no way to know.

## What to do, in order

1. Check the Google account first (#6). Change the password, sign out all devices, turn on 2-step verification.
2. Audit Accessibility and Device Admin lists. Remove anything you did not deliberately install.
3. Review data usage by app.
4. Reboot into Safe Mode — third-party apps are disabled. If the symptom disappears, it is an app, not the system.
5. Factory reset only after the Google account is secured. Resetting first and restoring the same compromised account just reinstalls the problem.

## The uncomfortable part

Consumer "antivirus" apps on Android detect very little real stalkerware. Commercial monitoring apps are often signed, distributed legitimately and installed by someone with physical access to the phone. Permission audits find them; scanners frequently do not.

If you want a structured walkthrough rather than a checklist — including what to do when the person who installed it has physical access to your device — **Is Your Android Phone Hacked?** covers the full process:

- [Read more about the book](https://apps.teamzlab.com/books/is-your-android-phone-hacked/)

And if you would rather have the phone check itself, [DeviceGPT](https://apps.teamzlab.com/devicegpt/) runs the sensor, permission and privacy checks on-device.
