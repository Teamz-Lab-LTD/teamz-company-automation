import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

// ─── Animated Gradient Background ───────────────────────────────────────────
export const GradientBg = ({ theme, variant = 0 }) => {
  const frame = useCurrentFrame();
  const angle = 135 + Math.sin(frame * 0.02) * 15;
  const shift = Math.sin(frame * 0.015) * 5;

  const gradients = [
    `radial-gradient(ellipse at 50% ${30 + shift}%, ${theme.accent}08 0%, transparent 50%)`,
    `radial-gradient(ellipse at ${70 + shift}% 70%, ${theme.accent}06 0%, transparent 45%)`,
    `radial-gradient(ellipse at ${30 - shift}% 80%, ${theme.accent2}06 0%, transparent 40%)`,
  ];

  return (
    <AbsoluteFill
      style={{
        background: `${gradients[variant % 3]}, linear-gradient(${angle}deg, ${theme.gradient1}, ${theme.gradient2})`,
      }}
    />
  );
};

// ─── Floating Orbs (subtle, organic motion) ─────────────────────────────────
export const FloatingOrbs = ({ theme }) => {
  const frame = useCurrentFrame();
  const orbs = [
    { x: 15, y: 20, r: 180, color: theme.accent, opacity: 0.04, speed: 0.008 },
    { x: 80, y: 60, r: 220, color: theme.accent, opacity: 0.03, speed: 0.012 },
    { x: 50, y: 85, r: 150, color: theme.accent2, opacity: 0.03, speed: 0.01 },
    { x: 30, y: 50, r: 100, color: theme.accent2, opacity: 0.05, speed: 0.015 },
  ];

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {orbs.map((o, i) => {
        const dx = Math.sin(frame * o.speed + i * 1.5) * 8;
        const dy = Math.cos(frame * o.speed + i * 2) * 6;
        const hex = Math.round(o.opacity * 255).toString(16).padStart(2, "0");
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${o.x + dx}%`, top: `${o.y + dy}%`,
              width: o.r, height: o.r, borderRadius: "50%",
              background: `radial-gradient(circle, ${o.color}${hex}, transparent 70%)`,
              filter: "blur(40px)", transform: "translate(-50%, -50%)",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

// ─── Accent Ring (rotating, pulsing) ────────────────────────────────────────
export const AccentRing = ({ theme, delay = 0, size = 400 }) => {
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
        width: size, height: size,
        border: `2px solid ${theme.accent}15`,
        borderRadius: "50%",
        transform: `rotate(${rotation}deg) scale(${scale * pulse})`,
        opacity: interpolate(s, [0, 1], [0, 0.3]),
      }}
    />
  );
};

// ─── Scan Line (horizontal sweep) ───────────────────────────────────────────
export const ScanLine = ({ theme, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 40, mass: 0.8 } });
  const y = interpolate(s, [0, 1], [-10, 110]);

  return (
    <div
      style={{
        position: "absolute", top: `${y}%`, left: 0, right: 0, height: 1,
        background: `linear-gradient(90deg, transparent 5%, ${theme.accent}22 30%, ${theme.accent}44 50%, ${theme.accent}22 70%, transparent 95%)`,
        boxShadow: `0 0 30px ${theme.accent}22`,
        opacity: interpolate(s, [0, 0.8, 1], [0, 0.6, 0]),
      }}
    />
  );
};

// ─── Grid Pattern (3D perspective) ──────────────────────────────────────────
export const GridPattern = ({ theme }) => {
  const frame = useCurrentFrame();
  const opacity = 0.03 + Math.sin(frame * 0.03) * 0.01;
  const hex = Math.round(opacity * 255).toString(16).padStart(2, "0");

  return (
    <AbsoluteFill
      style={{
        backgroundImage: `
          linear-gradient(${theme.accent}${hex} 1px, transparent 1px),
          linear-gradient(90deg, ${theme.accent}${hex} 1px, transparent 1px)
        `,
        backgroundSize: "60px 60px",
        transform: `perspective(800px) rotateX(60deg) translateY(${-frame * 0.5}px)`,
        transformOrigin: "center top",
        opacity: 0.4,
      }}
    />
  );
};

// ─── Glowing Underline ──────────────────────────────────────────────────────
export const GlowLine = ({ theme, delay = 0, widthPct = 70 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 25 } });
  const w = interpolate(s, [0, 1], [0, widthPct]);

  return (
    <div
      style={{
        width: `${w}%`, height: 3, borderRadius: 2,
        background: `linear-gradient(90deg, transparent, ${theme.accent}, ${theme.accent2}, transparent)`,
        boxShadow: `0 0 20px ${theme.accent}55`,
      }}
    />
  );
};
