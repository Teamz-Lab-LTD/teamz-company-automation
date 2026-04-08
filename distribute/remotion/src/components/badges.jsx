import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

const FONT = "'SF Pro Display', 'Inter', -apple-system, sans-serif";

// ─── Accent Badge (pill with glow + pulse) ──────────────────────────────────
export const Badge = ({ children, theme, delay = 0, size = "normal" }) => {
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
        background: `linear-gradient(135deg, ${theme.accent}, ${theme.accent2})`,
        color: theme.accentText,
        fontSize: isLarge ? 44 : 36,
        fontWeight: 900, borderRadius: 60,
        transform: `scale(${scale * pulse})`,
        boxShadow: `0 0 ${glow}px ${theme.accent}66, 0 0 ${glow * 2}px ${theme.accent}22, 0 4px 20px rgba(0,0,0,0.4)`,
        fontFamily: FONT, letterSpacing: 3, textTransform: "uppercase",
      }}
    >
      {children}
    </div>
  );
};

// ─── NumberPop — Animated counter ───────────────────────────────────────────
export const NumberPop = ({ value, label, theme, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 10, mass: 0.3, stiffness: 280 } });
  const num = parseInt(String(value).replace(/[^0-9]/g, "")) || 0;
  const count = Math.round(interpolate(s, [0, 1], [0, num]));
  const suffix = String(value).includes("+") ? "+" : String(value).includes("%") ? "%" : "";

  return (
    <div style={{ textAlign: "center" }}>
      <div
        style={{
          fontSize: 72, fontWeight: 900, color: theme.accent,
          fontFamily: "'SF Pro Display', monospace",
          transform: `scale(${interpolate(s, [0, 1], [0.5, 1])})`,
          opacity: interpolate(s, [0, 1], [0, 1]),
          textShadow: `0 0 30px ${theme.accent}44`,
        }}
      >
        {count}{suffix}
      </div>
      <div style={{ fontSize: 24, color: theme.muted, fontWeight: 500, marginTop: 8, fontFamily: "sans-serif" }}>
        {label}
      </div>
    </div>
  );
};

// ─── Strikethrough Badge (for CompareThree eliminations) ────────────────────
export const StrikeBadge = ({ children, theme, delay = 0, eliminated = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 12, mass: 0.3 } });

  const strikeW = eliminated
    ? interpolate(spring({ frame: frame - delay - 10, fps, config: { damping: 15 } }), [0, 1], [0, 100])
    : 0;

  return (
    <div style={{
      position: "relative", display: "inline-block",
      padding: "12px 32px",
      backgroundColor: eliminated ? `${theme.card}88` : theme.card,
      borderRadius: 16,
      border: `1px solid ${eliminated ? theme.muted + "33" : theme.accent + "33"}`,
      transform: `scale(${interpolate(s, [0, 1], [0.8, 1])})`,
      opacity: interpolate(s, [0, 1], [0, eliminated ? 0.5 : 1]),
    }}>
      <span style={{
        fontSize: 28, fontWeight: 600,
        color: eliminated ? theme.muted : theme.text,
        fontFamily: "'SF Pro Display', sans-serif",
      }}>
        {children}
      </span>
      {eliminated && (
        <div style={{
          position: "absolute", top: "50%", left: "5%",
          width: `${strikeW}%`, height: 3,
          backgroundColor: "#EF4444", borderRadius: 2,
          transform: "translateY(-50%)",
        }} />
      )}
    </div>
  );
};
