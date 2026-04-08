import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

// ─── Feature Card (glassmorphic with slide-in) ──────────────────────────────
export const FeatureCard = ({ icon, text, theme, delay, index = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 14, mass: 0.3 } });
  const dir = index % 2 === 0 ? -1 : 1;
  const x = interpolate(s, [0, 1], [120 * dir, 0]);
  const opacity = interpolate(s, [0, 1], [0, 1]);
  const scale = interpolate(s, [0, 1], [0.9, 1]);

  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 20,
        transform: `translateX(${x}px) scale(${scale})`, opacity,
        padding: "20px 24px",
        background: `linear-gradient(135deg, ${theme.card}EE, ${theme.surface}DD)`,
        borderRadius: 20,
        border: `1px solid ${theme.accent}15`,
        boxShadow: `0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 ${theme.accent}08`,
      }}
    >
      <div style={{
        width: 56, height: 56, display: "flex", alignItems: "center", justifyContent: "center",
        background: `${theme.accent}12`, borderRadius: 14, fontSize: 32, flexShrink: 0,
      }}>
        {icon}
      </div>
      <span style={{
        fontSize: 28, color: theme.text, fontWeight: 600,
        fontFamily: "'SF Pro Display', 'Inter', sans-serif",
      }}>
        {text}
      </span>
    </div>
  );
};

// ─── Comparison Column Card ─────────────────────────────────────────────────
export const ComparisonCard = ({ name, price, features, theme, delay = 0, isWinner = false, eliminated = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 12, mass: 0.3 } });
  const scale = interpolate(s, [0, 1], [0.7, 1]);
  const opacity = interpolate(s, [0, 1], [0, eliminated ? 0.4 : 1]);

  const winGlow = isWinner ? 40 + Math.sin(frame * 0.15) * 15 : 0;

  return (
    <div
      style={{
        flex: 1,
        padding: "24px 16px",
        background: isWinner
          ? `linear-gradient(180deg, ${theme.accent}15, ${theme.card})`
          : theme.card,
        borderRadius: 20,
        border: isWinner ? `2px solid ${theme.accent}` : `1px solid ${theme.accent}15`,
        boxShadow: isWinner ? `0 0 ${winGlow}px ${theme.accent}33` : "0 4px 16px rgba(0,0,0,0.2)",
        transform: `scale(${scale})`, opacity,
        display: "flex", flexDirection: "column", alignItems: "center", gap: 12,
        textDecoration: eliminated ? "line-through" : "none",
      }}
    >
      <div style={{ fontSize: 24, fontWeight: 700, color: isWinner ? theme.accent : theme.text, fontFamily: "sans-serif" }}>
        {name}
      </div>
      <div style={{ fontSize: 20, color: theme.muted, fontFamily: "sans-serif" }}>
        {price}
      </div>
      {(features || []).map((f, i) => (
        <div key={i} style={{ fontSize: 16, color: eliminated ? theme.muted : theme.text, fontFamily: "sans-serif" }}>
          {f}
        </div>
      ))}
      {isWinner && (
        <div style={{
          marginTop: 8, padding: "6px 20px",
          background: `linear-gradient(135deg, ${theme.accent}, ${theme.accent2})`,
          color: theme.accentText, fontSize: 18, fontWeight: 800,
          borderRadius: 20, letterSpacing: 1,
        }}>
          WINNER
        </div>
      )}
    </div>
  );
};

// ─── Metric Card (before/after comparison) ──────────────────────────────────
export const MetricCard = ({ label, before, after, theme, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 14, mass: 0.3 } });
  const opacity = interpolate(s, [0, 1], [0, 1]);
  const y = interpolate(s, [0, 1], [30, 0]);

  return (
    <div style={{
      transform: `translateY(${y}px)`, opacity,
      padding: "20px 28px",
      background: theme.card, borderRadius: 20,
      border: `1px solid ${theme.accent}20`,
      display: "flex", flexDirection: "column", gap: 12,
    }}>
      <div style={{ fontSize: 22, color: theme.muted, fontFamily: "sans-serif", fontWeight: 500 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <span style={{ fontSize: 28, color: "#EF4444", fontWeight: 700, textDecoration: "line-through", fontFamily: "sans-serif" }}>{before}</span>
        <span style={{ fontSize: 24, color: theme.muted }}>→</span>
        <span style={{ fontSize: 32, color: "#22C55E", fontWeight: 800, fontFamily: "sans-serif" }}>{after}</span>
      </div>
    </div>
  );
};

// ─── Step Card (numbered step) ──────────────────────────────────────────────
export const StepCard = ({ number, text, theme, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 12, mass: 0.3 } });
  const x = interpolate(s, [0, 1], [100, 0]);
  const opacity = interpolate(s, [0, 1], [0, 1]);

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 20,
      transform: `translateX(${x}px)`, opacity,
      padding: "18px 24px",
      background: `${theme.card}EE`, borderRadius: 18,
      border: `1px solid ${theme.accent}12`,
    }}>
      <div style={{
        width: 48, height: 48, borderRadius: 14, display: "flex", alignItems: "center", justifyContent: "center",
        background: `linear-gradient(135deg, ${theme.accent}, ${theme.accent2})`,
        color: theme.accentText, fontSize: 22, fontWeight: 900, fontFamily: "sans-serif", flexShrink: 0,
      }}>
        {number}
      </div>
      <span style={{ fontSize: 26, color: theme.text, fontWeight: 600, fontFamily: "sans-serif" }}>{text}</span>
    </div>
  );
};
