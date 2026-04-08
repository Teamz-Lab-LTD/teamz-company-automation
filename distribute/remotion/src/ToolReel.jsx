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
} from "remotion";

// ─── Brand ───────────────────────────────────────────────────────────────────
const B = {
  bg: "#0A0D12",
  surface: "#151920",
  card: "#1A1F28",
  accent: "#D9FE06",
  accent2: "#A5F700",
  text: "#FFFFFF",
  muted: "#6B7280",
  accentText: "#0A0D12",
  gradient1: "#0A0D12",
  gradient2: "#111827",
};

// ─── Animated Gradient Background ───────────────────────────────────────────
const GradientBg = ({ variant = 0 }) => {
  const frame = useCurrentFrame();
  const angle = 135 + Math.sin(frame * 0.02) * 15;
  const shift = Math.sin(frame * 0.015) * 5;

  const gradients = [
    `radial-gradient(ellipse at 50% ${30 + shift}%, ${B.accent}08 0%, transparent 50%)`,
    `radial-gradient(ellipse at ${70 + shift}% 70%, ${B.accent}06 0%, transparent 45%)`,
    `radial-gradient(ellipse at ${30 - shift}% 80%, #6366F108 0%, transparent 40%)`,
  ];

  return (
    <AbsoluteFill
      style={{
        background: `${gradients[variant % 3]}, linear-gradient(${angle}deg, ${B.gradient1}, ${B.gradient2})`,
      }}
    />
  );
};

// ─── Floating Orbs (subtle, organic motion) ─────────────────────────────────
const FloatingOrbs = () => {
  const frame = useCurrentFrame();
  const orbs = [
    { x: 15, y: 20, r: 180, color: B.accent, opacity: 0.04, speed: 0.008 },
    { x: 80, y: 60, r: 220, color: B.accent, opacity: 0.03, speed: 0.012 },
    { x: 50, y: 85, r: 150, color: "#818CF8", opacity: 0.03, speed: 0.01 },
    { x: 30, y: 50, r: 100, color: B.accent2, opacity: 0.05, speed: 0.015 },
  ];

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {orbs.map((o, i) => {
        const dx = Math.sin(frame * o.speed + i * 1.5) * 8;
        const dy = Math.cos(frame * o.speed + i * 2) * 6;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${o.x + dx}%`,
              top: `${o.y + dy}%`,
              width: o.r,
              height: o.r,
              borderRadius: "50%",
              background: `radial-gradient(circle, ${o.color}${Math.round(o.opacity * 255).toString(16).padStart(2, "0")}, transparent 70%)`,
              filter: "blur(40px)",
              transform: "translate(-50%, -50%)",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

// ─── Accent Ring (rotating, pulsing) ────────────────────────────────────────
const AccentRing = ({ delay = 0, size = 400 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 20, mass: 0.5 } });
  const rotation = frame * 0.5;
  const scale = interpolate(s, [0, 1], [0.5, 1]);
  const pulse = 1 + Math.sin(frame * 0.1) * 0.02;

  return (
    <div
      style={{
        position: "absolute",
        width: size,
        height: size,
        border: `2px solid ${B.accent}15`,
        borderRadius: "50%",
        transform: `rotate(${rotation}deg) scale(${scale * pulse})`,
        opacity: interpolate(s, [0, 1], [0, 0.3]),
      }}
    />
  );
};

// ─── Scan Line (horizontal sweep) ───────────────────────────────────────────
const ScanLine = ({ delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 40, mass: 0.8 } });
  const y = interpolate(s, [0, 1], [-10, 110]);

  return (
    <div
      style={{
        position: "absolute",
        top: `${y}%`,
        left: 0,
        right: 0,
        height: 1,
        background: `linear-gradient(90deg, transparent 5%, ${B.accent}22 30%, ${B.accent}44 50%, ${B.accent}22 70%, transparent 95%)`,
        boxShadow: `0 0 30px ${B.accent}22`,
        opacity: interpolate(s, [0, 0.8, 1], [0, 0.6, 0]),
      }}
    />
  );
};

// ─── Grid Pattern ───────────────────────────────────────────────────────────
const GridPattern = () => {
  const frame = useCurrentFrame();
  const opacity = 0.03 + Math.sin(frame * 0.03) * 0.01;

  return (
    <AbsoluteFill
      style={{
        backgroundImage: `
          linear-gradient(${B.accent}${Math.round(opacity * 255).toString(16).padStart(2, "0")} 1px, transparent 1px),
          linear-gradient(90deg, ${B.accent}${Math.round(opacity * 255).toString(16).padStart(2, "0")} 1px, transparent 1px)
        `,
        backgroundSize: "60px 60px",
        transform: `perspective(800px) rotateX(60deg) translateY(${-frame * 0.5}px)`,
        transformOrigin: "center top",
        opacity: 0.4,
      }}
    />
  );
};

// ─── Animated Text ──────────────────────────────────────────────────────────
const AnimText = ({ children, delay = 0, fontSize = 64, color = B.text, fontWeight = 800, lineHeight = 1.15, maxWidth = "88%" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const s = spring({ frame: frame - delay, fps, config: { damping: 14, mass: 0.35, stiffness: 220 } });
  const scale = interpolate(s, [0, 1], [0.6, 1]);
  const opacity = interpolate(s, [0, 1], [0, 1]);
  const y = interpolate(s, [0, 1], [40, 0]);

  return (
    <div
      style={{
        fontSize, fontWeight, color, lineHeight, maxWidth,
        textAlign: "center",
        transform: `scale(${scale}) translateY(${y}px)`,
        opacity,
        fontFamily: "'SF Pro Display', 'Inter', -apple-system, sans-serif",
        letterSpacing: fontSize > 50 ? -1 : 0,
      }}
    >
      {children}
    </div>
  );
};

// ─── Word-by-Word Reveal ────────────────────────────────────────────────────
const WordReveal = ({ text, delay = 0, fontSize = 68, color = B.text, fontWeight = 800 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(" ");

  return (
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 16px", maxWidth: "88%" }}>
      {words.map((word, i) => {
        const wordDelay = delay + i * 3;
        const s = spring({ frame: frame - wordDelay, fps, config: { damping: 12, mass: 0.3, stiffness: 250 } });
        const y = interpolate(s, [0, 1], [30, 0]);
        const opacity = interpolate(s, [0, 1], [0, 1]);
        const blur = interpolate(s, [0, 1], [8, 0]);

        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              fontSize, fontWeight, color,
              lineHeight: 1.2,
              transform: `translateY(${y}px)`,
              opacity,
              filter: `blur(${blur}px)`,
              fontFamily: "'SF Pro Display', 'Inter', -apple-system, sans-serif",
              letterSpacing: -1,
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};

// ─── Accent Badge ───────────────────────────────────────────────────────────
const Badge = ({ children, delay = 0, size = "normal" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 10, mass: 0.25, stiffness: 300 } });
  const scale = interpolate(s, [0, 1], [0, 1]);
  const pulse = 1 + Math.sin(frame * 0.12) * 0.025;
  const glow = 40 + Math.sin(frame * 0.15) * 15;

  const isLarge = size === "large";

  return (
    <div
      style={{
        display: "inline-block",
        padding: isLarge ? "20px 56px" : "14px 40px",
        background: `linear-gradient(135deg, ${B.accent}, ${B.accent2})`,
        color: B.accentText,
        fontSize: isLarge ? 44 : 36,
        fontWeight: 900,
        borderRadius: 60,
        transform: `scale(${scale * pulse})`,
        boxShadow: `0 0 ${glow}px ${B.accent}66, 0 0 ${glow * 2}px ${B.accent}22, 0 4px 20px rgba(0,0,0,0.4)`,
        fontFamily: "'SF Pro Display', 'Inter', -apple-system, sans-serif",
        letterSpacing: 3,
        textTransform: "uppercase",
      }}
    >
      {children}
    </div>
  );
};

// ─── Counter / Number Pop ───────────────────────────────────────────────────
const NumberPop = ({ value, label, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 10, mass: 0.3, stiffness: 280 } });
  const count = Math.round(interpolate(s, [0, 1], [0, parseInt(value) || 0]));

  return (
    <div style={{ textAlign: "center" }}>
      <div
        style={{
          fontSize: 72, fontWeight: 900, color: B.accent,
          fontFamily: "'SF Pro Display', monospace",
          transform: `scale(${interpolate(s, [0, 1], [0.5, 1])})`,
          opacity: interpolate(s, [0, 1], [0, 1]),
          textShadow: `0 0 30px ${B.accent}44`,
        }}
      >
        {typeof value === "string" && value.includes("+") ? `${count}+` : count}
      </div>
      <div style={{ fontSize: 24, color: B.muted, fontWeight: 500, marginTop: 8, fontFamily: "sans-serif" }}>
        {label}
      </div>
    </div>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// SLIDES
// ═════════════════════════════════════════════════════════════════════════════

// ─── Slide 1: Hook (word-by-word reveal + badge) ────────────────────────────
const SlideHook = ({ hook }) => {
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <GradientBg variant={0} />
      <FloatingOrbs />
      <GridPattern />
      <ScanLine delay={5} />
      <AccentRing delay={3} size={500} />
      <AccentRing delay={8} size={350} />

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 50, zIndex: 1, padding: 50 }}>
        <WordReveal text={hook} delay={2} fontSize={72} fontWeight={900} />
        <Badge delay={18} size="large">FREE FOREVER</Badge>
      </div>
    </AbsoluteFill>
  );
};

// ─── Slide 2: Tool Name + Stats ─────────────────────────────────────────────
const SlideTool = ({ title, description }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lineS = spring({ frame: frame - 15, fps, config: { damping: 25 } });
  const lineW = interpolate(lineS, [0, 1], [0, 70]);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <GradientBg variant={1} />
      <FloatingOrbs />
      <ScanLine delay={3} />

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 32, zIndex: 1, padding: 50 }}>
        {/* Tool icon placeholder */}
        <AnimText delay={0} fontSize={48} color={B.muted} fontWeight={500}>
          Introducing
        </AnimText>

        <AnimText delay={5} fontSize={64} fontWeight={900} color={B.text}>
          {title}
        </AnimText>

        {/* Glow underline */}
        <div style={{
          width: `${lineW}%`, height: 3,
          background: `linear-gradient(90deg, transparent, ${B.accent}, ${B.accent2}, transparent)`,
          boxShadow: `0 0 20px ${B.accent}55`,
          borderRadius: 2,
        }} />

        <AnimText delay={14} fontSize={30} fontWeight={400} color={B.muted} lineHeight={1.6}>
          {description}
        </AnimText>

        {/* Stats row */}
        <div style={{
          display: "flex", gap: 60, marginTop: 30,
          opacity: interpolate(spring({ frame: frame - 25, fps }), [0, 1], [0, 1]),
        }}>
          <NumberPop value="1800" label="Free Tools" delay={28} />
          <NumberPop value="100" label="% Private" delay={32} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─── Slide 3: Features ──────────────────────────────────────────────────────
const SlideFeatures = ({ customFeatures }) => {
  const features = customFeatures || [
    { icon: "🌐", text: "Works in your browser" },
    { icon: "🔒", text: "100% private" },
    { icon: "⚡", text: "No signup needed" },
    { icon: "💰", text: "Completely free" },
  ];

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <GradientBg variant={2} />
      <FloatingOrbs />

      <div style={{ display: "flex", flexDirection: "column", gap: 28, zIndex: 1, width: "82%", padding: 50 }}>
        <AnimText fontSize={42} delay={0} fontWeight={800}>
          Why you'll love it
        </AnimText>

        {features.map((f, i) => (
          <FeatureCard key={i} icon={f.icon} text={f.text} delay={6 + i * 6} index={i} />
        ))}
      </div>
    </AbsoluteFill>
  );
};

const FeatureCard = ({ icon, text, delay, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 14, mass: 0.3 } });

  // Alternate slide direction
  const dir = index % 2 === 0 ? -1 : 1;
  const x = interpolate(s, [0, 1], [120 * dir, 0]);
  const opacity = interpolate(s, [0, 1], [0, 1]);
  const scale = interpolate(s, [0, 1], [0.9, 1]);

  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 20,
        transform: `translateX(${x}px) scale(${scale})`,
        opacity,
        padding: "20px 24px",
        background: `linear-gradient(135deg, ${B.card}EE, ${B.surface}DD)`,
        borderRadius: 20,
        border: `1px solid ${B.accent}15`,
        backdropFilter: "blur(10px)",
        boxShadow: `0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 ${B.accent}08`,
      }}
    >
      <div style={{
        width: 56, height: 56, display: "flex", alignItems: "center", justifyContent: "center",
        background: `${B.accent}12`, borderRadius: 14, fontSize: 32, flexShrink: 0,
      }}>
        {icon}
      </div>
      <span style={{
        fontSize: 28, color: B.text, fontWeight: 600,
        fontFamily: "'SF Pro Display', 'Inter', sans-serif",
      }}>
        {text}
      </span>
    </div>
  );
};

// ─── Slide 4: CTA ───────────────────────────────────────────────────────────
const SlideCTA = ({ url, ctaText = "Try it now", ctaBadge = "LINK IN BIO", brandName = "tool.teamzlab.com" }) => {
  const frame = useCurrentFrame();
  const arrowY = interpolate(frame % 40, [0, 20, 40], [0, -16, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <GradientBg variant={0} />
      <FloatingOrbs />
      <GridPattern />
      <AccentRing delay={0} size={600} />
      <AccentRing delay={3} size={420} />
      <AccentRing delay={6} size={280} />
      <ScanLine delay={8} />

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 36, zIndex: 1 }}>
        <WordReveal text={ctaText} delay={0} fontSize={76} fontWeight={900} />

        <div style={{ transform: `translateY(${arrowY}px)`, fontSize: 72, marginTop: 10 }}>👇</div>

        <Badge delay={10} size="large">{ctaBadge}</Badge>

        <AnimText fontSize={26} delay={18} fontWeight={400} color={B.muted}>
          {url}
        </AnimText>
      </div>

      {/* Brand watermark */}
      <div style={{
        position: "absolute", bottom: 70, fontSize: 22,
        color: `${B.muted}66`, fontFamily: "sans-serif", fontWeight: 500,
        letterSpacing: 1,
      }}>
        {brandName}
      </div>
    </AbsoluteFill>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// MAIN COMPOSITION
// ═════════════════════════════════════════════════════════════════════════════
export const ToolReel = ({
  hook = "Stop paying for this",
  title = "Grammar Checker",
  description = "Check grammar, spelling, and punctuation with AI. Free, private, runs in your browser.",
  url = "tool.teamzlab.com/ai/grammar-checker/",
  audioFile = "",
  ctaText = "Try it now",
  ctaBadge = "LINK IN BIO",
  features = null,
  brandName = "tool.teamzlab.com",
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const slideDuration = Math.round(fps * 3.5);

  return (
    <AbsoluteFill style={{ backgroundColor: B.bg }}>
      {audioFile && (
        <Audio
          src={staticFile(audioFile)}
          volume={(f) =>
            interpolate(f, [0, 15, durationInFrames - 30, durationInFrames], [0, 0.7, 0.7, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
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
