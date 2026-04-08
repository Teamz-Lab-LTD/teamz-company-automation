// 8 color themes for anti-duplicate variety
// Each render picks a random theme so no two videos look identical

export const THEMES = [
  {
    name: "neon",
    bg: "#0A0D12", surface: "#151920", card: "#1A1F28",
    accent: "#D9FE06", accent2: "#A5F700",
    text: "#FFFFFF", muted: "#6B7280", accentText: "#0A0D12",
    gradient1: "#0A0D12", gradient2: "#111827",
  },
  {
    name: "electric-blue",
    bg: "#0B0F1A", surface: "#131A2E", card: "#1A2340",
    accent: "#3B82F6", accent2: "#60A5FA",
    text: "#FFFFFF", muted: "#6B7280", accentText: "#FFFFFF",
    gradient1: "#0B0F1A", gradient2: "#0F172A",
  },
  {
    name: "hot-pink",
    bg: "#120A10", surface: "#1E1520", card: "#281A28",
    accent: "#EC4899", accent2: "#F472B6",
    text: "#FFFFFF", muted: "#7B7280", accentText: "#FFFFFF",
    gradient1: "#120A10", gradient2: "#1A0A18",
  },
  {
    name: "amber",
    bg: "#12100A", surface: "#1E1A15", card: "#28221A",
    accent: "#F59E0B", accent2: "#FBBF24",
    text: "#FFFFFF", muted: "#7B7268", accentText: "#12100A",
    gradient1: "#12100A", gradient2: "#1A1508",
  },
  {
    name: "purple",
    bg: "#0E0A14", surface: "#18152A", card: "#201A38",
    accent: "#8B5CF6", accent2: "#A78BFA",
    text: "#FFFFFF", muted: "#7B7290", accentText: "#FFFFFF",
    gradient1: "#0E0A14", gradient2: "#150E22",
  },
  {
    name: "cyan",
    bg: "#0A1214", surface: "#121E22", card: "#18282E",
    accent: "#06B6D4", accent2: "#22D3EE",
    text: "#FFFFFF", muted: "#6B8088", accentText: "#0A1214",
    gradient1: "#0A1214", gradient2: "#0A181C",
  },
  {
    name: "coral",
    bg: "#140A0A", surface: "#221515", card: "#2E1A1A",
    accent: "#F97316", accent2: "#FB923C",
    text: "#FFFFFF", muted: "#887068", accentText: "#140A0A",
    gradient1: "#140A0A", gradient2: "#1C0E08",
  },
  {
    name: "mono",
    bg: "#0A0A0A", surface: "#161616", card: "#1E1E1E",
    accent: "#FFFFFF", accent2: "#E5E5E5",
    text: "#FFFFFF", muted: "#737373", accentText: "#0A0A0A",
    gradient1: "#0A0A0A", gradient2: "#111111",
  },
];

export function getTheme(index) {
  return THEMES[index % THEMES.length];
}

export function randomTheme() {
  return Math.floor(Math.random() * THEMES.length);
}
