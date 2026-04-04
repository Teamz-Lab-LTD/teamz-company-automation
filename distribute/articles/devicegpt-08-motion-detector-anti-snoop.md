---
slug: phone-motion-detector-alert-if-someone-touches-locked-phone-android
title: "Phone Motion Detector: Get an Alert If Someone Touches Your Locked Phone (Android, Free)"
tags: android, motion-detector, phone-security, anti-snoop, phone-theft, privacy, lock-screen, phone-alert, phone-guard, free
canonical_url: https://apps.teamzlab.com/devicegpt/
language: en
og_image: https://apps.teamzlab.com/devicegpt/og-image.png
pin_image: https://apps.teamzlab.com/devicegpt/og-image.png
status: draft
series: devicegpt-deep-dives
---

You leave your phone on your desk during a meeting. On a restaurant table while you order. On your bedside table while you sleep. And you wonder — did anyone look at it?

Most lock screens protect against casual snooping. But they don't tell you if someone picked up your phone, tried your PIN, or held it in front of your face hoping facial recognition would unlock it.

DeviceGPT's **motion detector** does exactly that — it alerts you the moment your locked phone is moved or touched, turning your phone into its own security guard.

## How the Motion Detector Works

[DeviceGPT](https://play.google.com/store/apps/details?id=com.teamz.lab.debugger) uses your phone's built-in **accelerometer and gyroscope** — the same sensors that detect rotation and movement — to monitor for physical disturbance while your phone is locked.

When the phone is set down and the screen is off, DeviceGPT establishes a baseline (completely still). Any movement beyond that baseline triggers an immediate alert:

- **Screen lights up** with an alert
- **Notification fires** even if the phone is on silent (optional loud alert mode)
- **Timestamps the disturbance** so you can see exactly when it happened
- **Logs repeated events** — if someone checks your phone 3 times while you're away, you'll see all three timestamps

No internet required. No server connection. Everything runs on-device.

## 5 Real-World Scenarios This Protects You From

### 1. Workplace Snooping
You step away from your desk for 10 minutes. A coworker picks up your phone to "check the time" — or to look at your messages, copy your number, or read your notifications. The motion detector alerts you as soon as they lift it.

### 2. Partner Monitoring
In relationships where trust is frayed, partners sometimes check each other's phones without permission. The motion detector creates an audit trail — you'll know if your phone was touched while you were in the shower.

### 3. Hotel Room Security
Housekeeping staff, hotel employees, or anyone with a room key can enter while you're out. If your phone is in the room, the motion detector logs whether it was disturbed.

### 4. Theft Prevention
A phone being pocketed without your knowledge triggers the accelerometer immediately. The alert fires on the phone itself — which may deter a casual thief who didn't expect the phone to react.

### 5. PIN Shoulder-Surfing Prevention
Some attackers don't steal your phone — they watch you type your PIN, then wait for an opportunity. The motion detector reveals that your phone was picked up and examined after you locked it, prompting you to change your PIN.

## Setting Up the Motion Detector

1. Open [DeviceGPT](https://play.google.com/store/apps/details?id=com.teamz.lab.debugger)
2. Navigate to the **Security** tab
3. Tap **Motion Detector**
4. Set sensitivity (Low / Medium / High)
5. Choose alert type (screen alert / notification / sound)
6. Lock your screen and set your phone down
7. DeviceGPT monitors in the background

**Sensitivity guide:**
- **Low:** Only triggers on significant movement (picking up the phone, walking with it)
- **Medium:** Triggers on moderate movement (someone nudging it on a table)
- **High:** Triggers on any touch or vibration (recommended for maximum security)

## Motion Detector + Device Sleep Tracking

DeviceGPT also runs **device sleep tracking** in the background — automatically mapping when your phone is picked up vs. put down throughout the day.

This data serves two purposes:

1. **Security:** Corroborates motion detector alerts — if your phone shows a usage gap in your timeline that you don't remember, something happened
2. **Battery optimization:** Sleep/wake patterns reveal which habits drain your battery fastest. Many users discover their phone is being woken hundreds of times per day by notifications, costing significant battery life

## How This Combines With the Full Security Dashboard

The motion detector is one piece of DeviceGPT's larger security picture:

| Layer | What It Catches |
|-------|----------------|
| Motion detector | Physical access while locked |
| Keylogger scanner | Monitoring software installed on your device |
| Mic/camera history | Background access by installed apps |
| ISP privacy tests | Network-level surveillance |
| Zero Trust Score | Overall security grade (A-F) |

Running all layers together gives you a complete picture of both physical and digital security threats.

## What No Other Free App Offers

Most "anti-theft" apps focus on locking the phone after theft or taking photos of would-be thieves. DeviceGPT's motion detector is different:

- **Real-time alert** while the phone is still in range
- **No account required** — works offline
- **No photos taken** — privacy-respecting (we don't photograph people without consent)
- **Timestamped log** — you can review history
- **Paired with full device health** — it's one feature among many, not a one-trick app

## FAQ

**Q: Will it trigger from vibration or a table being bumped?**
A: At Medium sensitivity, small vibrations won't trigger it. At High sensitivity, any movement will. Choose based on your environment.

**Q: Does it work while my phone is charging?**
A: Yes. The detector runs as a foreground service regardless of charging state.

**Q: Does it drain battery?**
A: The accelerometer is extremely power-efficient — it uses milliwatts. In testing, 8 hours of motion detection uses less than 3% battery.

**Q: Will it trigger if I get a phone call or notification?**
A: Notifications don't trigger it. A phone call causes enough vibration to trigger at High sensitivity — you can pause monitoring when expecting calls.

**Q: Can I use this at night to know if someone enters my room?**
A: The motion detector responds to the phone being moved, not general room movement. For room entry detection, the phone needs to be on a surface that would move when someone walks near it — or you'd need a dedicated security camera.

**Q: Does DeviceGPT store the motion logs in the cloud?**
A: No. All logs stay on your device. Nothing is uploaded. The app is open source — verify this on [GitHub](https://github.com/Teamz-Lab-LTD/device-gpt).

## Download

**Free. No root. No account. Open source.**

- [Google Play Store](https://play.google.com/store/apps/details?id=com.teamz.lab.debugger)
- [Source Code on GitHub](https://github.com/Teamz-Lab-LTD/device-gpt)

---

*Part of the [DeviceGPT Deep Dive series](https://apps.teamzlab.com/devicegpt/). Built by [Teamz Lab](https://apps.teamzlab.com).*
