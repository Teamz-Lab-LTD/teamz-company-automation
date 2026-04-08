import React from "react";
import { AbsoluteFill, Audio, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Sequence } from "remotion";
import { GradientBg, FloatingOrbs, AccentRing, ScanLine, GridPattern, GlowLine } from "../components/backgrounds";
import { InstantHook, AnimText, Subtitle } from "../components/typography";
import { Badge, NumberPop } from "../components/badges";
import { FeatureCard } from "../components/cards";
import { getTheme } from "../variety/themes";

/**
 * InstantFix Template — Pain → Tool → Result → CTA
 * Best for: tool demos, app features, quick wins
 * 6 slides × 4s = 24 seconds (720 frames at 30fps)
 */
export const InstantFix = ({
  hook = "Stop paying for this",
  title = "Grammar Checker",
  description = "Check grammar, spelling, and punctuation with AI. Free, private, runs in your browser.",
  url = "tool.teamzlab.com/ai/grammar-checker/",
  audioFile = "",
  ctaText = "Try it now",
  ctaBadge = "LINK IN BIO",
  features = null,
  brandName = "tool.teamzlab.com",
  themeIndex = 0,
  metric = null, // { value: "1800+", label: "Free Tools" }
  metric2 = null, // { value: "100", label: "% Private" }
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const T = getTheme(themeIndex);
  const SLIDE = Math.round(durationInFrames / 6); // ~120 frames per slide

  const defaultFeatures = features || [
    { icon: "🌐", text: "Works in your browser" },
    { icon: "🔒", text: "100% private" },
    { icon: "⚡", text: "No signup needed" },
    { icon: "💰", text: "Completely free" },
  ];

  const m1 = metric || { value: "1800+", label: "Free Tools" };
  const m2 = metric2 || { value: "100%", label: "Private" };

  return (
    <AbsoluteFill style={{ backgroundColor: T.bg }}>
      {audioFile && (
        <Audio
          src={staticFile(audioFile)}
          volume={(f) => interpolate(f, [0, 15, durationInFrames - 30, durationInFrames], [0, 0.7, 0.7, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
        />
      )}

      {/* Slide 1: HOOK — instant text, shock value */}
      <Sequence from={0} durationInFrames={SLIDE} name="Hook">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={0} />
          <FloatingOrbs theme={T} />
          <GridPattern theme={T} />
          <ScanLine theme={T} delay={3} />
          <AccentRing theme={T} delay={2} size={500} />
          <AccentRing theme={T} delay={6} size={350} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 44, zIndex: 1, padding: 50 }}>
            <InstantHook fontSize={72} color={T.text} delay={0}>{hook}</InstantHook>
            <Badge theme={T} delay={12} size="large">FREE FOREVER</Badge>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 2: PATTERN INTERRUPT — transition flash + "But what if..." */}
      <Sequence from={SLIDE} durationInFrames={SLIDE} name="Interrupt">
        <SlideInterrupt theme={T} />
      </Sequence>

      {/* Slide 3: TOOL — name + description */}
      <Sequence from={SLIDE * 2} durationInFrames={SLIDE} name="Tool">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={1} />
          <FloatingOrbs theme={T} />
          <ScanLine theme={T} delay={5} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 28, zIndex: 1, padding: 50 }}>
            <AnimText delay={0} fontSize={44} color={T.muted} fontWeight={500}>Introducing</AnimText>
            <AnimText delay={4} fontSize={62} fontWeight={900} color={T.text}>{title}</AnimText>
            <GlowLine theme={T} delay={12} />
            <AnimText delay={14} fontSize={28} fontWeight={400} color={T.muted} lineHeight={1.6}>{description}</AnimText>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 4: FEATURES — cards sliding in */}
      <Sequence from={SLIDE * 3} durationInFrames={SLIDE} name="Features">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={2} />
          <FloatingOrbs theme={T} />
          <div style={{ display: "flex", flexDirection: "column", gap: 24, zIndex: 1, width: "82%", padding: 50 }}>
            <AnimText fontSize={40} delay={0} fontWeight={800} color={T.text}>Why you'll love it</AnimText>
            {defaultFeatures.map((f, i) => (
              <FeatureCard key={i} icon={f.icon} text={f.text} theme={T} delay={6 + i * 6} index={i} />
            ))}
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 5: RESULT — metrics/stats */}
      <Sequence from={SLIDE * 4} durationInFrames={SLIDE} name="Result">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={0} />
          <FloatingOrbs theme={T} />
          <AccentRing theme={T} delay={0} size={450} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 40, zIndex: 1 }}>
            <AnimText fontSize={44} delay={0} fontWeight={800} color={T.text}>The numbers speak</AnimText>
            <div style={{ display: "flex", gap: 60, marginTop: 20 }}>
              <NumberPop value={m1.value} label={m1.label} theme={T} delay={8} />
              <NumberPop value={m2.value} label={m2.label} theme={T} delay={14} />
            </div>
            <Badge theme={T} delay={22} size="normal">ZERO COST</Badge>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 6: CTA — try it now */}
      <Sequence from={SLIDE * 5} durationInFrames={SLIDE} name="CTA">
        <SlideCTA theme={T} ctaText={ctaText} ctaBadge={ctaBadge} url={url} brandName={brandName} />
      </Sequence>
    </AbsoluteFill>
  );
};

// ─── Pattern Interrupt Slide ────────────────────────────────────────────────
const SlideInterrupt = ({ theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Glitch flash at start
  const flash = interpolate(frame, [0, 2, 5, 8], [1, 0, 0.6, 0], { extrapolateRight: "clamp" });
  const s = spring({ frame: frame - 5, fps, config: { damping: 12, mass: 0.3 } });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <GradientBg theme={theme} variant={1} />
      <FloatingOrbs theme={theme} />

      {/* Flash overlay */}
      <AbsoluteFill style={{ backgroundColor: theme.accent, opacity: flash * 0.15 }} />

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 30, zIndex: 1 }}>
        <AnimText delay={8} fontSize={52} fontWeight={700} color={theme.muted}>But what if...</AnimText>
        <InstantHook delay={18} fontSize={64} color={theme.accent}>
          You never had to pay?
        </InstantHook>
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
      <GridPattern theme={theme} />
      <AccentRing theme={theme} delay={0} size={600} />
      <AccentRing theme={theme} delay={3} size={420} />
      <AccentRing theme={theme} delay={6} size={280} />

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 36, zIndex: 1 }}>
        <InstantHook delay={0} fontSize={76} color={theme.text}>{ctaText}</InstantHook>
        <div style={{ transform: `translateY(${arrowY}px)`, fontSize: 72, marginTop: 10 }}>👇</div>
        <Badge theme={theme} delay={10} size="large">{ctaBadge}</Badge>
        <AnimText fontSize={26} delay={18} fontWeight={400} color={theme.muted}>{url}</AnimText>
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
