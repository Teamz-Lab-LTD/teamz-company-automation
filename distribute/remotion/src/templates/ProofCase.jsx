import React from "react";
import { AbsoluteFill, Audio, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Sequence } from "remotion";
import { GradientBg, FloatingOrbs, AccentRing, ScanLine, GlowLine } from "../components/backgrounds";
import { InstantHook, AnimText } from "../components/typography";
import { Badge, NumberPop } from "../components/badges";
import { MetricCard } from "../components/cards";
import { getTheme } from "../variety/themes";

/**
 * ProofCase Template — Problem → Pain → Transform → Review → CTA
 * Best for: client work, service proof, app reviews, case studies
 */
export const ProofCase = ({
  hook = "We saved this client $500/month",
  title = "Web Design Service",
  description = "Full-stack web design and development for startups and SMBs.",
  url = "teamzlab.com",
  audioFile = "",
  ctaText = "Get started",
  ctaBadge = "HIRE US",
  brandName = "teamzlab.com",
  themeIndex = 0,
  problemText = "Paying $500/month for tools they didn't need",
  transformText = "We replaced 8 paid tools with free alternatives",
  review = { text: "Teamz Lab saved us thousands. Best decision we made.", author: "Happy Client" },
  metrics = null,
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const T = getTheme(themeIndex);
  const SLIDE = Math.round(durationInFrames / 6);

  const defaultMetrics = metrics || [
    { label: "Monthly savings", before: "$500", after: "$0" },
    { label: "Tools replaced", before: "8 paid", after: "8 free" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: T.bg }}>
      {audioFile && (
        <Audio src={staticFile(audioFile)}
          volume={(f) => interpolate(f, [0, 15, durationInFrames - 30, durationInFrames], [0, 0.7, 0.7, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      )}

      {/* Slide 1: PROBLEM HOOK */}
      <Sequence from={0} durationInFrames={SLIDE} name="Hook">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={0} />
          <FloatingOrbs theme={T} />
          <ScanLine theme={T} delay={2} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 44, zIndex: 1, padding: 50 }}>
            <InstantHook fontSize={68} color={T.text} delay={0}>{hook}</InstantHook>
            <Badge theme={T} delay={14} size="normal">REAL STORY</Badge>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 2: THE PAIN */}
      <Sequence from={SLIDE} durationInFrames={SLIDE} name="Pain">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={1} />
          <FloatingOrbs theme={T} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 30, zIndex: 1, padding: 60 }}>
            <AnimText delay={0} fontSize={36} color="#EF4444" fontWeight={700}>The Problem</AnimText>
            <InstantHook delay={5} fontSize={52} color={T.text}>{problemText}</InstantHook>
            <AnimText delay={20} fontSize={70}>😰</AnimText>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 3: TRANSFORMATION */}
      <Sequence from={SLIDE * 2} durationInFrames={SLIDE} name="Transform">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={2} />
          <FloatingOrbs theme={T} />
          <AccentRing theme={T} delay={0} size={450} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 30, zIndex: 1, padding: 60 }}>
            <AnimText delay={0} fontSize={36} color="#22C55E" fontWeight={700}>The Solution</AnimText>
            <InstantHook delay={5} fontSize={48} color={T.text}>{transformText}</InstantHook>
            <AnimText delay={20} fontSize={70}>🚀</AnimText>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 4: METRICS */}
      <Sequence from={SLIDE * 3} durationInFrames={SLIDE} name="Metrics">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={0} />
          <FloatingOrbs theme={T} />
          <div style={{ display: "flex", flexDirection: "column", gap: 28, zIndex: 1, width: "82%", padding: 50 }}>
            <AnimText fontSize={40} delay={0} fontWeight={800} color={T.text}>The results</AnimText>
            {defaultMetrics.map((m, i) => (
              <MetricCard key={i} label={m.label} before={m.before} after={m.after} theme={T} delay={8 + i * 10} />
            ))}
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 5: REVIEW / TESTIMONIAL */}
      <Sequence from={SLIDE * 4} durationInFrames={SLIDE} name="Review">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={1} />
          <FloatingOrbs theme={T} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 30, zIndex: 1, padding: 60 }}>
            <AnimText delay={0} fontSize={80} color={T.accent}>❝</AnimText>
            <AnimText delay={5} fontSize={36} fontWeight={500} color={T.text} lineHeight={1.6}>
              {review.text}
            </AnimText>
            <GlowLine theme={T} delay={20} widthPct={40} />
            <AnimText delay={25} fontSize={26} fontWeight={600} color={T.accent}>
              — {review.author}
            </AnimText>
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
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 36, zIndex: 1 }}>
            <InstantHook delay={0} fontSize={72} color={T.text}>{ctaText}</InstantHook>
            <div style={{ transform: `translateY(${interpolate(useCurrentFrame() % 40, [0, 20, 40], [0, -16, 0], { extrapolateRight: "clamp" })}px)`, fontSize: 72 }}>👇</div>
            <Badge theme={T} delay={10} size="large">{ctaBadge}</Badge>
            <AnimText fontSize={26} delay={18} fontWeight={400} color={T.muted}>{url}</AnimText>
          </div>
          <div style={{ position: "absolute", bottom: 70, fontSize: 22, color: `${T.muted}66`, fontFamily: "sans-serif", fontWeight: 500, letterSpacing: 1 }}>{brandName}</div>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
