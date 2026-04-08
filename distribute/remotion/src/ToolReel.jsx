import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
  Easing,
} from "remotion";

// ─── Brand ───────────────────────────────────────────────────────────────────
const BRAND = {
  bg: "#12151A",
  surface: "#1E2128",
  accent: "#D9FE06",
  text: "#FFFFFF",
  muted: "#8B8B8B",
  accentText: "#12151A",
};

// ─── Animated Background Particles ──────────────────────────────────────────
const Particles = () => {
  const frame = useCurrentFrame();
  const particles = Array.from({ length: 12 }, (_, i) => ({
    x: (i * 137.5) % 100,
    y: (i * 73.7) % 100,
    size: 3 + (i % 4) * 2,
    speed: 0.3 + (i % 3) * 0.2,
    opacity: 0.05 + (i % 5) * 0.03,
  }));

  return (
    <AbsoluteFill>
      {particles.map((p, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${p.x}%`,
            top: `${(p.y + frame * p.speed * 0.3) % 110 - 5}%`,
            width: p.size,
            height: p.size,
            borderRadius: "50%",
            backgroundColor: BRAND.accent,
            opacity: p.opacity,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

// ─── Neon Glow Line ─────────────────────────────────────────────────────────
const GlowLine = ({ delay = 0, y = "50%" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({ frame: frame - delay, fps, config: { damping: 30, mass: 0.5 } });
  const width = interpolate(progress, [0, 1], [0, 100]);

  return (
    <div
      style={{
        position: "absolute",
        top: y,
        left: `${50 - width / 2}%`,
        width: `${width}%`,
        height: 3,
        background: `linear-gradient(90deg, transparent, ${BRAND.accent}, transparent)`,
        boxShadow: `0 0 20px ${BRAND.accent}66, 0 0 40px ${BRAND.accent}33`,
        opacity: interpolate(progress, [0, 1], [0, 0.8]),
      }}
    />
  );
};

// ─── Animated Text (spring in + scale) ──────────────────────────────────────
const AnimatedText = ({
  children,
  delay = 0,
  fontSize = 64,
  color = BRAND.text,
  fontWeight = 800,
  lineHeight = 1.2,
  maxWidth = "90%",
  textAlign = "center",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scaleSpring = spring({
    frame: frame - delay,
    fps,
    config: { damping: 12, mass: 0.4, stiffness: 200 },
  });

  const scale = interpolate(scaleSpring, [0, 1], [0.3, 1]);
  const opacity = interpolate(scaleSpring, [0, 1], [0, 1]);
  const y = interpolate(scaleSpring, [0, 1], [60, 0]);

  return (
    <div
      style={{
        fontSize,
        fontWeight,
        color,
        lineHeight,
        textAlign,
        maxWidth,
        transform: `scale(${scale}) translateY(${y}px)`,
        opacity,
        textShadow: `0 4px 30px rgba(0,0,0,0.5)`,
        fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
      }}
    >
      {children}
    </div>
  );
};

// ─── Accent Badge (pill shape with glow) ────────────────────────────────────
const AccentBadge = ({ children, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const s = spring({
    frame: frame - delay,
    fps,
    config: { damping: 10, mass: 0.3, stiffness: 300 },
  });

  const scale = interpolate(s, [0, 1], [0, 1]);
  const pulse = Math.sin(frame * 0.15) * 0.03 + 1;

  return (
    <div
      style={{
        display: "inline-block",
        padding: "16px 48px",
        backgroundColor: BRAND.accent,
        color: BRAND.accentText,
        fontSize: 40,
        fontWeight: 900,
        borderRadius: 50,
        transform: `scale(${scale * pulse})`,
        boxShadow: `0 0 40px ${BRAND.accent}88, 0 0 80px ${BRAND.accent}44`,
        fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
        letterSpacing: 2,
      }}
    >
      {children}
    </div>
  );
};

// ─── Slide 1: Hook ──────────────────────────────────────────────────────────
const SlideHook = ({ hook }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BRAND.bg,
        justifyContent: "center",
        alignItems: "center",
        padding: 60,
      }}
    >
      <Particles />
      <GlowLine delay={5} y="25%" />
      <GlowLine delay={15} y="75%" />

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 40, zIndex: 1 }}>
        <AnimatedText fontSize={72} delay={3} fontWeight={900}>
          {hook}
        </AnimatedText>
        <AccentBadge delay={15}>FREE FOREVER</AccentBadge>
      </div>
    </AbsoluteFill>
  );
};

// ─── Slide 2: Tool Name + Description ───────────────────────────────────────
const SlideTool = ({ title, description }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animated underline
  const lineProgress = spring({ frame: frame - 20, fps, config: { damping: 20 } });
  const lineWidth = interpolate(lineProgress, [0, 1], [0, 80]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BRAND.bg,
        justifyContent: "center",
        alignItems: "center",
        padding: 60,
      }}
    >
      <Particles />

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 30, zIndex: 1 }}>
        <AnimatedText fontSize={60} delay={3} fontWeight={900} color={BRAND.accent}>
          {title}
        </AnimatedText>

        {/* Animated underline */}
        <div
          style={{
            width: `${lineWidth}%`,
            height: 4,
            background: `linear-gradient(90deg, transparent, ${BRAND.accent}, transparent)`,
            boxShadow: `0 0 15px ${BRAND.accent}66`,
          }}
        />

        <AnimatedText fontSize={32} delay={12} fontWeight={400} color={BRAND.muted} lineHeight={1.5}>
          {description}
        </AnimatedText>
      </div>
    </AbsoluteFill>
  );
};

// ─── Slide 3: Features (animated list) ──────────────────────────────────────
const SlideFeatures = ({ customFeatures }) => {
  const features = customFeatures || [
    { icon: "🌐", text: "Works in your browser" },
    { icon: "🔒", text: "100% private — data stays on device" },
    { icon: "⚡", text: "No signup, no download" },
    { icon: "💰", text: "Completely free" },
  ];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BRAND.bg,
        justifyContent: "center",
        alignItems: "center",
        padding: 60,
      }}
    >
      <Particles />

      <div style={{ display: "flex", flexDirection: "column", gap: 36, zIndex: 1, width: "85%" }}>
        <AnimatedText fontSize={44} delay={0} fontWeight={800}>
          Why people love it
        </AnimatedText>

        {features.map((f, i) => (
          <FeatureRow key={i} icon={f.icon} text={f.text} delay={8 + i * 8} />
        ))}
      </div>
    </AbsoluteFill>
  );
};

const FeatureRow = ({ icon, text, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const s = spring({ frame: frame - delay, fps, config: { damping: 12, mass: 0.3 } });
  const x = interpolate(s, [0, 1], [-200, 0]);
  const opacity = interpolate(s, [0, 1], [0, 1]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 24,
        transform: `translateX(${x}px)`,
        opacity,
        padding: "18px 28px",
        backgroundColor: `${BRAND.surface}CC`,
        borderRadius: 16,
        borderLeft: `4px solid ${BRAND.accent}`,
      }}
    >
      <span style={{ fontSize: 40 }}>{icon}</span>
      <span
        style={{
          fontSize: 30,
          color: BRAND.text,
          fontWeight: 600,
          fontFamily: "'Inter', 'Helvetica Neue', Arial, sans-serif",
        }}
      >
        {text}
      </span>
    </div>
  );
};

// ─── Slide 4: CTA ───────────────────────────────────────────────────────────
const SlideCTA = ({ url, ctaText = "Try it now", ctaBadge = "LINK IN BIO", brandName = "tool.teamzlab.com" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pulse = Math.sin(frame * 0.2) * 6;

  const arrowY = interpolate(
    frame % 30,
    [0, 15, 30],
    [0, -12, 0],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BRAND.bg,
        justifyContent: "center",
        alignItems: "center",
        padding: 60,
      }}
    >
      <Particles />
      <GlowLine delay={0} y="30%" />
      <GlowLine delay={5} y="70%" />

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 40, zIndex: 1 }}>
        <AnimatedText fontSize={72} delay={0} fontWeight={900}>
          {ctaText}
        </AnimatedText>

        <div style={{ transform: `translateY(${arrowY}px)`, fontSize: 64 }}>👇</div>

        <AccentBadge delay={8}>{ctaBadge}</AccentBadge>

        <AnimatedText fontSize={28} delay={15} fontWeight={400} color={BRAND.muted}>
          {url}
        </AnimatedText>
      </div>

      {/* Brand watermark */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          fontSize: 24,
          color: `${BRAND.muted}99`,
          fontFamily: "'Inter', Arial, sans-serif",
          fontWeight: 500,
        }}
      >
        {brandName}
      </div>
    </AbsoluteFill>
  );
};

// ─── Main Composition ───────────────────────────────────────────────────────
export const ToolReel = ({
  hook = "Stop paying for this",
  title = "Grammar Checker",
  description = "Check grammar, spelling, and punctuation with AI. Free, private, runs in your browser.",
  url = "tool.teamzlab.com/ai/grammar-checker/",
  audioFile = "",
  ctaText = "Try it now",
  ctaBadge = "LINK IN BIO",
  features = null, // custom features array: [{icon, text}] — null = default
  brandName = "tool.teamzlab.com",
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const slideDuration = Math.round(fps * 3.5); // 3.5 seconds per slide

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.bg }}>
      {/* Background music with fade in/out */}
      {audioFile && (
        <Audio
          src={staticFile(audioFile)}
          volume={(f) =>
            interpolate(
              f,
              [0, 15, durationInFrames - 30, durationInFrames],
              [0, 0.7, 0.7, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            )
          }
        />
      )}

      <Sequence from={0} durationInFrames={slideDuration} name="Hook">
        <SlideHook hook={hook} />
      </Sequence>

      <Sequence from={slideDuration} durationInFrames={slideDuration} name="Tool">
        <SlideTool title={title} description={description} />
      </Sequence>

      <Sequence from={slideDuration * 2} durationInFrames={slideDuration} name="Features">
        <SlideFeatures customFeatures={features} />
      </Sequence>

      <Sequence from={slideDuration * 3} durationInFrames={slideDuration} name="CTA">
        <SlideCTA url={url} ctaText={ctaText} ctaBadge={ctaBadge} brandName={brandName} />
      </Sequence>
    </AbsoluteFill>
  );
};
