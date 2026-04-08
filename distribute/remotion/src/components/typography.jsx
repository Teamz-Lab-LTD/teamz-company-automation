import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const FONT = "'SF Pro Display', 'Inter', -apple-system, sans-serif";

// ─── InstantHook — Full text visible at frame 0, readable in <0.1s ─────────
export const InstantHook = ({ children, fontSize = 72, color = "#FFFFFF", delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const s = spring({ frame: frame - delay, fps, config: { damping: 14, mass: 0.2, stiffness: 350 } });
  const scale = interpolate(s, [0, 1], [0.75, 1]);
  const opacity = interpolate(s, [0, 1], [0.3, 1]);

  // Flash overlay on entry
  const flash = interpolate(frame - delay, [0, 3, 8], [0.4, 0.15, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

  return (
    <div style={{ position: "relative", maxWidth: "88%", textAlign: "center" }}>
      <div
        style={{
          fontSize, fontWeight: 900, color, lineHeight: 1.1,
          transform: `scale(${scale})`,
          opacity,
          fontFamily: FONT,
          letterSpacing: -1,
          textShadow: "0 4px 40px rgba(0,0,0,0.6)",
        }}
      >
        {children}
      </div>
      {/* White flash on entry */}
      {flash > 0 && (
        <div style={{
          position: "absolute", inset: -40,
          background: `radial-gradient(circle, rgba(255,255,255,${flash}), transparent 70%)`,
          pointerEvents: "none",
        }} />
      )}
    </div>
  );
};

// ─── AnimText — Spring-based text reveal ────────────────────────────────────
export const AnimText = ({ children, delay = 0, fontSize = 64, color = "#FFFFFF", fontWeight = 800, lineHeight = 1.15, maxWidth = "88%" }) => {
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
        fontFamily: FONT,
        letterSpacing: fontSize > 50 ? -1 : 0,
      }}
    >
      {children}
    </div>
  );
};

// ─── WordReveal — Word-by-word with blur-to-sharp ───────────────────────────
export const WordReveal = ({ text, delay = 0, fontSize = 68, color = "#FFFFFF", fontWeight = 800 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(" ");

  return (
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 16px", maxWidth: "88%" }}>
      {words.map((word, i) => {
        const d = delay + i * 3;
        const s = spring({ frame: frame - d, fps, config: { damping: 12, mass: 0.3, stiffness: 250 } });
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              fontSize, fontWeight, color, lineHeight: 1.2,
              transform: `translateY(${interpolate(s, [0, 1], [30, 0])}px)`,
              opacity: interpolate(s, [0, 1], [0, 1]),
              filter: `blur(${interpolate(s, [0, 1], [8, 0])}px)`,
              fontFamily: FONT, letterSpacing: -1,
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};

// ─── Subtitle — Muted, smaller text ─────────────────────────────────────────
export const Subtitle = ({ children, delay = 0, fontSize = 28, color }) => {
  return <AnimText delay={delay} fontSize={fontSize} fontWeight={400} color={color}>{children}</AnimText>;
};
