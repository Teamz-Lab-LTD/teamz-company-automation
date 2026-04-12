import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig, Sequence,
} from "remotion";
import { GradientBg, FloatingOrbs, GlowLine } from "../components/backgrounds";
import { InstantHook, AnimText, Subtitle } from "../components/typography";
import { Badge } from "../components/badges";
import { getTheme } from "../variety/themes";

/**
 * Tutorial Template — "How To" long-form videos (3-7 minutes)
 *
 * Structure:
 *   1. Intro slide (title + hook)
 *   2. Problem slide (why you need this)
 *   3-N. Step slides (screenshot + text overlay + zoom animation + step counter)
 *   N+1. Result showcase
 *   N+2. CTA + outro
 *
 * Props:
 *   - title: tool name
 *   - hook: opening hook text
 *   - problem: pain point text
 *   - steps: [{ label, description, screenshot }] — 3-5 steps
 *   - resultText: what the user gets
 *   - screenshotDir: path to screenshots from capture-tool.js
 *   - url, ctaText, ctaBadge, brandName, audioFile, themeIndex
 */
export const Tutorial = ({
  hook = "How to create free invoices online",
  title = "Invoice Generator",
  problem = "Most invoice tools charge $10-20/month",
  steps = [
    { label: "Open the tool", description: "Visit the free invoice generator in your browser", screenshot: "" },
    { label: "Enter your details", description: "Fill in your business name, client info, and line items", screenshot: "" },
    { label: "Customize the look", description: "Pick a professional template and add your logo", screenshot: "" },
    { label: "Download your invoice", description: "Click generate — your invoice is ready in seconds", screenshot: "" },
  ],
  resultText = "Professional invoice — completely free, no signup",
  url = "tool.teamzlab.com/finance/invoice-generator/",
  audioFile = "",
  ctaText = "Try it free",
  ctaBadge = "LINK IN DESCRIPTION",
  brandName = "tool.teamzlab.com",
  themeIndex = 0,
  durationInFrames: propDuration,
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const frame = useCurrentFrame();
  const T = getTheme(themeIndex);

  // Dynamic slide timing based on total duration and step count
  const totalSlides = steps.length + 4; // intro + problem + steps + result + cta
  const SLIDE = Math.round(durationInFrames / totalSlides);

  const totalSteps = steps.length;

  return (
    <AbsoluteFill style={{ backgroundColor: T.bg }}>
      {/* Background music */}
      {audioFile && (
        <Audio
          src={staticFile(audioFile)}
          volume={(f) => interpolate(f, [0, 30, durationInFrames - 60, durationInFrames], [0, 0.4, 0.4, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
        />
      )}

      {/* Persistent progress bar at top */}
      <AbsoluteFill style={{ zIndex: 100 }}>
        <ProgressBar durationInFrames={durationInFrames} theme={T} />
      </AbsoluteFill>

      {/* ── Slide 1: INTRO ── */}
      <Sequence from={0} durationInFrames={SLIDE} name="Intro">
        <SlideIntro hook={hook} title={title} theme={T} />
      </Sequence>

      {/* ── Slide 2: PROBLEM ── */}
      <Sequence from={SLIDE} durationInFrames={SLIDE} name="Problem">
        <SlideProblem problem={problem} theme={T} />
      </Sequence>

      {/* ── Step slides ── */}
      {steps.map((step, i) => (
        <Sequence
          key={i}
          from={SLIDE * (i + 2)}
          durationInFrames={SLIDE}
          name={`Step${i + 1}`}
        >
          <SlideStep
            step={step}
            stepNumber={i + 1}
            totalSteps={totalSteps}
            theme={T}
            slideFrames={SLIDE}
          />
        </Sequence>
      ))}

      {/* ── Result slide ── */}
      <Sequence from={SLIDE * (steps.length + 2)} durationInFrames={SLIDE} name="Result">
        <SlideResult
          resultText={resultText}
          title={title}
          theme={T}
          lastScreenshot={steps[steps.length - 1]?.screenshot}
        />
      </Sequence>

      {/* ── CTA slide ── */}
      <Sequence from={SLIDE * (steps.length + 3)} durationInFrames={SLIDE} name="CTA">
        <SlideCTA theme={T} ctaText={ctaText} ctaBadge={ctaBadge} url={url} brandName={brandName} />
      </Sequence>
    </AbsoluteFill>
  );
};

// ─── Progress Bar ───────────────────────────────────────────────────────────
const ProgressBar = ({ durationInFrames, theme }) => {
  const frame = useCurrentFrame();
  const progress = (frame / durationInFrames) * 100;

  return (
    <div style={{
      position: "absolute", top: 0, left: 0, right: 0, height: 6, zIndex: 100,
      backgroundColor: `${theme.muted}22`,
    }}>
      <div style={{
        width: `${progress}%`, height: "100%",
        backgroundColor: theme.accent,
        transition: "width 0.1s linear",
      }} />
    </div>
  );
};

// ─── Intro Slide ────────────────────────────────────────────────────────────
const SlideIntro = ({ hook, title, theme }) => {
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <GradientBg theme={theme} variant={0} />
      <FloatingOrbs theme={theme} />

      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        gap: 40, zIndex: 1, padding: 60,
      }}>
        {/* "HOW TO" badge */}
        <Badge theme={theme} delay={0} size="large">HOW TO</Badge>

        {/* Main title */}
        <InstantHook fontSize={58} color={theme.text} delay={4}>
          {hook}
        </InstantHook>

        <GlowLine theme={theme} delay={15} />

        {/* Tool name */}
        <AnimText fontSize={34} delay={18} fontWeight={500} color={theme.muted}>
          Using {title} — Free, No Signup
        </AnimText>

        {/* Step count preview */}
        <AnimText fontSize={28} delay={25} fontWeight={400} color={`${theme.muted}88`}>
          Quick step-by-step guide
        </AnimText>
      </div>
    </AbsoluteFill>
  );
};

// ─── Problem Slide ──────────────────────────────────────────────────────────
const SlideProblem = ({ problem, theme }) => {
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <GradientBg theme={theme} variant={1} />
      <FloatingOrbs theme={theme} />

      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        gap: 44, zIndex: 1, padding: 60,
      }}>
        {/* Problem icon */}
        <AnimText fontSize={80} delay={0} fontWeight={400} color={theme.text}>
          😤
        </AnimText>

        <AnimText fontSize={38} delay={4} fontWeight={600} color={theme.muted}>
          The problem
        </AnimText>

        <InstantHook fontSize={48} color={theme.text} delay={10}>
          {problem}
        </InstantHook>

        <GlowLine theme={theme} delay={22} />

        <AnimText fontSize={32} delay={26} fontWeight={500} color={theme.accent}>
          Here's the free solution ↓
        </AnimText>
      </div>
    </AbsoluteFill>
  );
};

// ─── Step Slide (screenshot + text + zoom + step counter) ───────────────────
const SlideStep = ({ step, stepNumber, totalSteps, theme, slideFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Zoom animation on the screenshot: starts zoomed in, settles to normal
  const zoomSpring = spring({ frame: frame - 10, fps, config: { damping: 20, mass: 0.6 } });
  const scale = interpolate(zoomSpring, [0, 1], [1.15, 1]);

  // Ken Burns: slight pan during the slide
  const panX = interpolate(frame, [0, slideFrames], [-15, 15], { extrapolateRight: "clamp" });
  const panY = interpolate(frame, [0, slideFrames], [-8, 8], { extrapolateRight: "clamp" });

  const hasScreenshot = step.screenshot && step.screenshot.length > 0;

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bg }}>
      {/* Screenshot area (top 60%) */}
      <div style={{
        position: "absolute", top: 80, left: 40, right: 40, height: 1050,
        borderRadius: 24, overflow: "hidden",
        border: `2px solid ${theme.accent}33`,
        backgroundColor: theme.surface,
      }}>
        {hasScreenshot ? (
          <div style={{
            width: "100%", height: "100%", overflow: "hidden",
            transform: `scale(${scale}) translate(${panX}px, ${panY}px)`,
          }}>
            <Img
              src={staticFile(step.screenshot)}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </div>
        ) : (
          /* Placeholder when no screenshot — show step text large */
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
            <GradientBg theme={theme} variant={stepNumber % 3} />
            <FloatingOrbs theme={theme} />
            <div style={{ zIndex: 1, padding: 60, textAlign: "center" }}>
              <AnimText fontSize={52} delay={8} fontWeight={700} color={theme.text}>
                {step.label}
              </AnimText>
            </div>
          </AbsoluteFill>
        )}

        {/* Step highlight pointer (animated arrow) */}
        <StepPointer frame={frame} theme={theme} />
      </div>

      {/* Step counter bar */}
      <div style={{
        position: "absolute", top: 30, left: 40, right: 40,
        display: "flex", alignItems: "center", gap: 12, zIndex: 10,
      }}>
        {Array.from({ length: totalSteps }, (_, i) => (
          <div key={i} style={{
            flex: 1, height: 5, borderRadius: 3,
            backgroundColor: i < stepNumber ? theme.accent : `${theme.muted}33`,
            transition: "background-color 0.3s",
          }} />
        ))}
      </div>

      {/* Bottom text area (40%) */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        height: 700, padding: "50px 60px",
        display: "flex", flexDirection: "column", gap: 24,
        background: `linear-gradient(transparent, ${theme.bg} 15%)`,
      }}>
        {/* Step badge */}
        <div style={{
          display: "flex", alignItems: "center", gap: 16,
        }}>
          <div style={{
            width: 52, height: 52, borderRadius: 14,
            backgroundColor: theme.accent, color: theme.accentText,
            display: "flex", justifyContent: "center", alignItems: "center",
            fontSize: 26, fontWeight: 900, fontFamily: "sans-serif",
          }}>
            {stepNumber}
          </div>
          <AnimText fontSize={22} delay={0} fontWeight={500} color={theme.muted}>
            Step {stepNumber} of {totalSteps}
          </AnimText>
        </div>

        {/* Step title */}
        <InstantHook fontSize={46} color={theme.text} delay={4}>
          {step.label}
        </InstantHook>

        {/* Step description */}
        <AnimText fontSize={30} delay={12} fontWeight={400} color={theme.muted} lineHeight={1.5}>
          {step.description}
        </AnimText>
      </div>
    </AbsoluteFill>
  );
};

// ─── Animated pointer/highlight on screenshot ───────────────────────────────
const StepPointer = ({ frame, theme }) => {
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - 20, fps, config: { damping: 10, mass: 0.3, stiffness: 200 } });
  const opacity = interpolate(s, [0, 1], [0, 0.8]);
  const scale = interpolate(s, [0, 1], [0.5, 1]);

  // Pulsing ring effect
  const pulse = interpolate(frame % 60, [0, 30, 60], [1, 1.3, 1]);

  return (
    <div style={{
      position: "absolute", top: "45%", left: "50%",
      width: 80, height: 80, borderRadius: "50%",
      border: `3px solid ${theme.accent}`,
      transform: `translate(-50%, -50%) scale(${scale * pulse})`,
      opacity,
      boxShadow: `0 0 30px ${theme.accent}44`,
      pointerEvents: "none",
    }} />
  );
};

// ─── Result Slide ───────────────────────────────────────────────────────────
const SlideResult = ({ resultText, title, theme, lastScreenshot }) => {
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <GradientBg theme={theme} variant={2} />
      <FloatingOrbs theme={theme} />

      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        gap: 40, zIndex: 1, padding: 60,
      }}>
        {/* Success icon */}
        <AnimText fontSize={90} delay={0} fontWeight={400} color={theme.text}>
          ✅
        </AnimText>

        <InstantHook fontSize={52} color={theme.text} delay={4}>
          Done!
        </InstantHook>

        <GlowLine theme={theme} delay={12} />

        <AnimText fontSize={36} delay={16} fontWeight={500} color={theme.muted} lineHeight={1.5}>
          {resultText}
        </AnimText>

        <div style={{ display: "flex", gap: 30, marginTop: 20 }}>
          <Badge theme={theme} delay={24} size="normal">FREE</Badge>
          <Badge theme={theme} delay={28} size="normal">NO SIGNUP</Badge>
          <Badge theme={theme} delay={32} size="normal">PRIVATE</Badge>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─── CTA Slide ──────────────────────────────────────────────────────────────
const SlideCTA = ({ theme, ctaText, ctaBadge, url, brandName }) => {
  const frame = useCurrentFrame();
  const arrowY = interpolate(frame % 40, [0, 20, 40], [0, -16, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <GradientBg theme={theme} variant={0} />
      <FloatingOrbs theme={theme} />

      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        gap: 36, zIndex: 1,
      }}>
        <InstantHook delay={0} fontSize={64} color={theme.text}>{ctaText}</InstantHook>
        <div style={{ transform: `translateY(${arrowY}px)`, fontSize: 72, marginTop: 10 }}>👇</div>
        <Badge theme={theme} delay={10} size="large">{ctaBadge}</Badge>
        <AnimText fontSize={28} delay={18} fontWeight={400} color={theme.muted}>{url}</AnimText>

        {/* Subscribe reminder */}
        <div style={{ marginTop: 40, display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
          <AnimText fontSize={26} delay={24} fontWeight={500} color={theme.accent}>
            Like & Subscribe for more free tools
          </AnimText>
          <AnimText fontSize={22} delay={28} fontWeight={400} color={`${theme.muted}88`}>
            New tutorials every week
          </AnimText>
        </div>
      </div>

      <div style={{
        position: "absolute", bottom: 70, fontSize: 22,
        color: `${theme.muted}66`, fontFamily: "sans-serif", fontWeight: 500, letterSpacing: 1,
      }}>
        {brandName}
      </div>
    </AbsoluteFill>
  );
};
