import React from "react";
import { AbsoluteFill, Audio, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Sequence } from "remotion";
import { GradientBg, FloatingOrbs, AccentRing, ScanLine, GlowLine } from "../components/backgrounds";
import { InstantHook, AnimText } from "../components/typography";
import { Badge } from "../components/badges";
import { MetricCard, StepCard } from "../components/cards";
import { getTheme } from "../variety/themes";

/**
 * BeforeAfter Template — Result first → Before → Steps → After → CTA
 * Best for: file conversion, design, optimization, compression demos
 */
export const BeforeAfter = ({
  hook = "This turned 2 hours into 2 minutes",
  title = "PDF Compressor",
  description = "Compress PDFs without losing quality. Free, private, browser-based.",
  url = "tool.teamzlab.com/pdf/pdf-compressor/",
  audioFile = "",
  ctaText = "Try it now",
  ctaBadge = "LINK IN BIO",
  brandName = "tool.teamzlab.com",
  themeIndex = 0,
  beforeState = "Manual work, paid tools, privacy concerns",
  afterState = "One click, free, 100% private",
  steps = null,
  metrics = null, // [{ label, before, after }]
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const T = getTheme(themeIndex);
  const SLIDE = Math.round(durationInFrames / 6);

  const defaultSteps = steps || [
    { text: "Open the tool in your browser" },
    { text: "Upload or paste your content" },
    { text: "Get instant results — done" },
  ];

  const defaultMetrics = metrics || [
    { label: "Time", before: "2 hours", after: "2 seconds" },
    { label: "Cost", before: "$15/mo", after: "FREE" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: T.bg }}>
      {audioFile && (
        <Audio src={staticFile(audioFile)}
          volume={(f) => interpolate(f, [0, 15, durationInFrames - 30, durationInFrames], [0, 0.7, 0.7, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      )}

      {/* Slide 1: OUTCOME HOOK — show the result first */}
      <Sequence from={0} durationInFrames={SLIDE} name="Hook">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={0} />
          <FloatingOrbs theme={T} />
          <ScanLine theme={T} delay={2} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 44, zIndex: 1, padding: 50 }}>
            <InstantHook fontSize={68} color={T.text} delay={0}>{hook}</InstantHook>
            <Badge theme={T} delay={14} size="normal">REAL RESULT</Badge>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 2: BEFORE — show the pain */}
      <Sequence from={SLIDE} durationInFrames={SLIDE} name="Before">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={1} />
          <FloatingOrbs theme={T} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 30, zIndex: 1, padding: 50 }}>
            <AnimText delay={0} fontSize={36} color="#EF4444" fontWeight={700}>BEFORE</AnimText>
            <AnimText delay={5} fontSize={52} fontWeight={800} color={T.text}>{beforeState}</AnimText>
            <div style={{ marginTop: 20 }}>
              <AnimText delay={15} fontSize={80}>😤</AnimText>
            </div>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 3: THE STEPS — how it works */}
      <Sequence from={SLIDE * 2} durationInFrames={SLIDE} name="Steps">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={2} />
          <FloatingOrbs theme={T} />
          <div style={{ display: "flex", flexDirection: "column", gap: 24, zIndex: 1, width: "82%", padding: 50 }}>
            <AnimText fontSize={40} delay={0} fontWeight={800} color={T.text}>How {title} works</AnimText>
            {defaultSteps.map((s, i) => (
              <StepCard key={i} number={i + 1} text={s.text} theme={T} delay={6 + i * 8} />
            ))}
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 4: AFTER — show the transformation */}
      <Sequence from={SLIDE * 3} durationInFrames={SLIDE} name="After">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={0} />
          <FloatingOrbs theme={T} />
          <AccentRing theme={T} delay={0} size={400} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 30, zIndex: 1, padding: 50 }}>
            <AnimText delay={0} fontSize={36} color="#22C55E" fontWeight={700}>AFTER</AnimText>
            <AnimText delay={5} fontSize={52} fontWeight={800} color={T.text}>{afterState}</AnimText>
            <div style={{ marginTop: 20 }}>
              <AnimText delay={15} fontSize={80}>🎉</AnimText>
            </div>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 5: METRICS — before vs after numbers */}
      <Sequence from={SLIDE * 4} durationInFrames={SLIDE} name="Metrics">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={1} />
          <FloatingOrbs theme={T} />
          <div style={{ display: "flex", flexDirection: "column", gap: 28, zIndex: 1, width: "82%", padding: 50 }}>
            <AnimText fontSize={40} delay={0} fontWeight={800} color={T.text}>The difference</AnimText>
            {defaultMetrics.map((m, i) => (
              <MetricCard key={i} label={m.label} before={m.before} after={m.after} theme={T} delay={8 + i * 10} />
            ))}
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 6: CTA */}
      <Sequence from={SLIDE * 5} durationInFrames={SLIDE} name="CTA">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={0} />
          <FloatingOrbs theme={T} />
          <AccentRing theme={T} delay={0} size={550} />
          <AccentRing theme={T} delay={4} size={380} />
          <CTAContent theme={T} ctaText={ctaText} ctaBadge={ctaBadge} url={url} brandName={brandName} />
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};

const CTAContent = ({ theme, ctaText, ctaBadge, url, brandName }) => {
  const frame = useCurrentFrame();
  const arrowY = interpolate(frame % 40, [0, 20, 40], [0, -16, 0], { extrapolateRight: "clamp" });

  return (
    <>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 36, zIndex: 1 }}>
        <InstantHook delay={0} fontSize={72} color={theme.text}>{ctaText}</InstantHook>
        <div style={{ transform: `translateY(${arrowY}px)`, fontSize: 72 }}>👇</div>
        <Badge theme={theme} delay={10} size="large">{ctaBadge}</Badge>
        <AnimText fontSize={26} delay={18} fontWeight={400} color={theme.muted}>{url}</AnimText>
      </div>
      <div style={{ position: "absolute", bottom: 70, fontSize: 22, color: `${theme.muted}66`, fontFamily: "sans-serif", fontWeight: 500, letterSpacing: 1 }}>{brandName}</div>
    </>
  );
};
