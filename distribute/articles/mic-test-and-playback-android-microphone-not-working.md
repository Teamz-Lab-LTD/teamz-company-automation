---
title: "Mic Test and Playback on Android: Why People Can't Hear You"
description: "You cannot judge your own microphone by listening — you hear your voice through your skull, not the phone. Record, play back, and read the one number that separates a broken mic from a loud room."
tags: android, microphone, audio, troubleshooting, mobile
canonical_url: https://apps.teamzlab.com/blog/mic-test-and-playback-android-microphone-not-working/
slug: mic-test-and-playback-android-microphone-not-working
pin_image: https://apps.teamzlab.com/devicegpt/og.png
og_image: https://apps.teamzlab.com/devicegpt/og.png
---

If people keep saying "I can't hear you" and you are wondering why your microphone is not working on Android, the frustrating part is that you cannot check it yourself by listening. You hear your own voice through your skull, not through the phone. The only way to know what callers actually receive is a **microphone test with playback** — record a few seconds, then listen back to the recording.

This guide shows you how to run a proper mic test and playback on Android, what the numbers mean, and how to tell the difference between a genuinely broken microphone and a phone that is simply muted, blocked by a permission, or sitting in a noisy room.

## Why "does my mic work?" is harder than it sounds

Most people test a microphone by opening a voice recorder and shouting into it. That tells you very little, for three reasons:

- **A loud room hides a dead microphone.** If the recording shows a strong signal, that signal may be the room, not you. Air conditioning, traffic and a ceiling fan all register.
- **A quiet room hides a weak microphone.** If you record in silence and the level looks low, that may be a perfectly healthy mic in a very quiet room.
- **Phones have more than one microphone.** Modern Android devices carry two or three — bottom, top, and often one beside the rear camera for video. One can fail while the others work, which is why some apps sound fine and others do not.

The number that actually matters is not how loud the recording is. It is **how far your voice rises above the room**.

## The one measurement that tells you the truth: headroom

A useful microphone test measures two things and subtracts one from the other:

1. **The noise floor** — how loud the room is while you stay silent.
2. **Your voice peak** — the loudest point while you speak normally.

The gap between them is the **headroom**. Levels are measured in dBFS (decibels relative to full scale), where 0 dBFS is the loudest a digital recording can go and everything below is negative. A typical healthy result on a phone looks roughly like this:

> Room noise: −55 dBFS · Voice peak: −17 dBFS · **Rise above the room: 38 dB**

Here is how to read the result:

| Headroom | What it means |
|---|---|
| **25 dB or more** | Your voice is clearly separated from the room. This is what you want. |
| **10–25 dB** | Audible but thin. Callers may say you sound distant. Usually too far from the phone, or a case blocking the mic port. |
| **Under 10 dB** | Your voice is barely rising above the room. Either the room is very loud, or the microphone is not picking you up. |
| **Under 3 dB** | Effectively nothing is getting through — the signature of a muted, blocked, or failed microphone. |

Notice that a phone recording at a healthy-looking −12 dBFS can still be broken, if the room is also at −12 dBFS. **Absolute loudness on its own is not a diagnosis.** This is exactly why a simple "level meter" app can tell you your mic is fine when it is not.

## How to run a microphone test and playback on Android

You can do this with any recorder app, but the sequence matters. Follow it in this order:

1. **Measure the room first.** Stay completely silent for one to two seconds and note the level. This is your baseline.
2. **Speak normally.** Not loudly, not into the mic port — normal speaking distance, the way you would hold the phone on a call. Say a full sentence rather than "test test," because real speech contains the range of sounds a call has to carry.
3. **Play it back and listen.** This is the step people skip, and it is the only step that proves the whole chain works.
4. **Answer honestly: did you hear yourself?** If you heard nothing, do not assume the mic is dead — the speaker or the volume may be the problem instead. See the next section.

If you would rather not do this by hand, [DeviceGPT](https://play.google.com/store/apps/details?id=com.teamz.lab.debugger) runs this exact sequence on Android in about five seconds: it measures the room, measures your voice, plays the recording straight back, and shows you the room level, the voice peak, and the headroom between them. The recording stays on the phone and is never saved or uploaded.

## You heard nothing on playback. Now what?

Silence on playback has more than one cause, and the microphone is only one of them. Work through these in order, because they get progressively less likely:

### 1. Media volume, not ringer volume

Android has separate volume channels. Playback uses the **media** channel. Press volume up while audio is actually playing, or open Settings and raise Media volume specifically. A phone on full ring volume can still play recordings silently.

### 2. Microphone permission

If the app never received the microphone permission, the recording is silence. Go to **Settings → Apps → (the app) → Permissions → Microphone**. If you denied it twice, Android stops showing the prompt and only Settings can turn it back on.

### 3. Another app is holding the microphone

Only one app can use the mic at a time on most Android versions. An active or backgrounded call, a voice assistant, or a recording app left running will lock it. Close other apps and try again.

### 4. A case, film, or debris over the mic port

The primary microphone is usually a pinhole on the bottom edge beside the charging port. Thick cases cover it, and lint packs into it over months. Look at it in good light. Do not push anything sharp into the hole.

### 5. Speaker fault rather than microphone fault

If the level meter moved while you spoke but playback was silent, the microphone captured audio correctly and **the speaker is the problem**. That is a different repair, and the test just saved you from replacing the wrong part.

## "Why can't people hear me on my phone?" — the five real causes

When your Android mic is not working on calls but the phone seems fine otherwise, it is almost always one of these, in rough order of how often they turn out to be the culprit:

1. **The mic port is physically blocked.** A case edge, a screen-protector lip, or compacted lint in the pinhole beside the charging port. Costs nothing to check and is the most common cause by a distance.
2. **An app lost its microphone permission.** Very common after a system update. The phone works on ordinary calls, but WhatsApp or your dialler records silence.
3. **Another app is holding the mic.** A voice assistant, a recorder left running, or a call still active in the background. Only one app gets the microphone at a time.
4. **Noise suppression is cutting you off.** Some phones aggressively gate background noise. In a very quiet room a soft speaker can be treated as noise and suppressed.
5. **A genuine hardware fault.** Real, but far less common than the four above — which is why it is worth ruling those out before paying for a repair.

A test with playback separates these quickly. If the recording captures your voice clearly, the microphone hardware is fine and the fault is a permission or an app. If the recording is silent while the room reading looks normal, the mic itself is not receiving.

## What a microphone test cannot tell you

Being straightforward about the limits matters more than sounding impressive:

- **No app can grade your microphone's quality.** Sound quality is only measurable against a calibrated reference signal in a known acoustic environment. Any app that shows you a "microphone health: 87%" score has invented that number.
- **No app can tell which physical mic a given call used.** Android does not expose that.
- **Your ear is the detector.** The measurements tell you whether a signal arrived. Only listening to the playback tells you whether it sounds right.

A test that reports what it measured, and then asks you what you heard, is being honest. A test that hands you a score is guessing.

## Frequently asked questions

### How do I test my mic on Android without installing anything?

Open the built-in voice recorder, record five seconds of speech, then play it back with media volume raised. This tells you whether audio is captured, but not the noise floor or the headroom, so it will not distinguish a weak mic from a loud room.

### What is a good dBFS level for a phone microphone?

There is no single correct number, because it depends on the room. Aim for a voice peak roughly 25 dB or more above the room's noise floor, and a peak that stays below about −3 dBFS so it is not clipped.

### What does clipping mean in a mic test?

Clipping means the input went past the loudest value the recording can store, so the tops of the waveform were cut off. It sounds like harsh distortion. Move the phone further from your mouth and test again.

### Why do I sound fine in one app and muffled in another?

Apps can request different microphones and apply different noise suppression. A blocked or failed secondary mic can affect video recording while voice calls still sound normal.

### Can a microphone test fix my mic?

No. A test tells you where the fault is. If the mic port is blocked or a permission is off, you can fix it yourself; a hardware failure needs a repair.

## Checking the rest of the hardware

A microphone rarely fails alone on a phone that has been dropped or water-damaged. If you are already testing, it is worth checking the parts that fail quietly — battery health, speakers, [the screen](https://apps.teamzlab.com/blog/dead-pixel-test-android-screen-check/), sensors, and charging behaviour — because those degrade without any visible symptom at all.

[DeviceGPT](https://play.google.com/store/apps/details?id=com.teamz.lab.debugger) is a free Android app that runs those hardware and battery checks and explains the results in plain language, without root. It reports what Android actually exposes and tells you when a value is not available.

## The short version

Record the room, record your voice, subtract one from the other, then listen to the playback. Headroom above roughly 25 dB with clear playback means your microphone is doing its job. Near-zero headroom means something is stopping it — and the checklist above will usually tell you what, before you pay anyone to open your phone.

---

*The mic test described here is built by the Teamz Lab team into DeviceGPT 3.1.22 on Android. The technique itself works with any recorder that can play back, and nothing above requires our app.*
