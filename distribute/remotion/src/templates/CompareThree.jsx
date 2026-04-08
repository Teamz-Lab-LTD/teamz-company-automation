import React from "react";
import { AbsoluteFill, Audio, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Sequence } from "remotion";
import { GradientBg, FloatingOrbs, AccentRing, ScanLine } from "../components/backgrounds";
import { InstantHook, AnimText } from "../components/typography";
import { Badge } from "../components/badges";
import { ComparisonCard, FeatureCard } from "../components/cards";
import { getTheme } from "../variety/themes";

/**
 * CompareThree Template — "Which is best?" → 3 options → Eliminate → Winner
 * Best for: paid vs free, format comparison, tool alternatives
 */
export const CompareThree = ({
  hook = "Which is actually the best?",
  title = "Grammar Checker",
  url = "tool.teamzlab.com/ai/grammar-checker/",
  audioFile = "",
  ctaText = "Try the winner",
  ctaBadge = "LINK IN BIO",
  brandName = "tool.teamzlab.com",
  themeIndex = 0,
  // Three options to compare
  option1 = { name: "Grammarly", price: "$12/mo", features: ["Cloud-based", "Tracks your data"] },
  option2 = { name: "ProWritingAid", price: "$20/mo", features: ["Desktop app", "Subscription only"] },
  optionWinner = { name: "Teamz Lab", price: "FREE", features: ["Browser-based", "100% private"] },
  winnerFeatures = null,
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const T = getTheme(themeIndex);
  const SLIDE = Math.round(durationInFrames / 6);

  const defaultWinnerFeatures = winnerFeatures || [
    { icon: "💰", text: "Completely free — no hidden costs" },
    { icon: "🔒", text: "Your data never leaves your device" },
    { icon: "⚡", text: "Works instantly, no signup" },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: T.bg }}>
      {audioFile && (
        <Audio src={staticFile(audioFile)}
          volume={(f) => interpolate(f, [0, 15, durationInFrames - 30, durationInFrames], [0, 0.7, 0.7, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      )}

      {/* Slide 1: QUESTION HOOK */}
      <Sequence from={0} durationInFrames={SLIDE} name="Hook">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={0} />
          <FloatingOrbs theme={T} />
          <ScanLine theme={T} delay={3} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 40, zIndex: 1, padding: 50 }}>
            <AnimText delay={0} fontSize={40} color={T.muted} fontWeight={500}>🤔 Comparison</AnimText>
            <InstantHook fontSize={68} color={T.text} delay={0}>{hook}</InstantHook>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 2: THREE OPTIONS SIDE BY SIDE */}
      <Sequence from={SLIDE} durationInFrames={SLIDE * 2} name="Compare">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={1} />
          <FloatingOrbs theme={T} />
          <div style={{ display: "flex", flexDirection: "column", gap: 24, zIndex: 1, width: "90%", padding: 40 }}>
            <AnimText fontSize={36} delay={0} fontWeight={700} color={T.text}>The contenders</AnimText>
            <div style={{ display: "flex", gap: 16, marginTop: 10 }}>
              <ComparisonCard name={option1.name} price={option1.price} features={option1.features} theme={T} delay={6} />
              <ComparisonCard name={option2.name} price={option2.price} features={option2.features} theme={T} delay={12} />
              <ComparisonCard name={optionWinner.name} price={optionWinner.price} features={optionWinner.features} theme={T} delay={18} />
            </div>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 3: ELIMINATION — cross out losers */}
      <Sequence from={SLIDE * 3} durationInFrames={SLIDE} name="Eliminate">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={2} />
          <FloatingOrbs theme={T} />
          <div style={{ display: "flex", flexDirection: "column", gap: 24, zIndex: 1, width: "90%", padding: 40 }}>
            <AnimText fontSize={36} delay={0} fontWeight={700} color={T.text}>The verdict</AnimText>
            <div style={{ display: "flex", gap: 16, marginTop: 10 }}>
              <ComparisonCard name={option1.name} price={option1.price} features={option1.features} theme={T} delay={0} eliminated />
              <ComparisonCard name={option2.name} price={option2.price} features={option2.features} theme={T} delay={8} eliminated />
              <ComparisonCard name={optionWinner.name} price={optionWinner.price} features={optionWinner.features} theme={T} delay={0} isWinner />
            </div>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 4: WHY IT WINS */}
      <Sequence from={SLIDE * 4} durationInFrames={SLIDE} name="Winner">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={0} />
          <FloatingOrbs theme={T} />
          <AccentRing theme={T} delay={0} size={450} />
          <div style={{ display: "flex", flexDirection: "column", gap: 24, zIndex: 1, width: "82%", padding: 50 }}>
            <AnimText fontSize={42} delay={0} fontWeight={800} color={T.accent}>{optionWinner.name} wins</AnimText>
            {defaultWinnerFeatures.map((f, i) => (
              <FeatureCard key={i} icon={f.icon} text={f.text} theme={T} delay={8 + i * 6} index={i} />
            ))}
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Slide 5: CTA */}
      <Sequence from={SLIDE * 5} durationInFrames={SLIDE} name="CTA">
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <GradientBg theme={T} variant={0} />
          <FloatingOrbs theme={T} />
          <AccentRing theme={T} delay={0} size={550} />
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
