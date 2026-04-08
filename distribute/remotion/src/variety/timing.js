// 3 animation timing presets for variety

export const TIMINGS = {
  snappy: { damping: 10, mass: 0.25, stiffness: 300 },
  smooth: { damping: 22, mass: 0.5, stiffness: 150 },
  bouncy: { damping: 8, mass: 0.3, stiffness: 200 },
};

export const TIMING_NAMES = Object.keys(TIMINGS);

export function getTiming(name) {
  return TIMINGS[name] || TIMINGS.snappy;
}

export function randomTiming() {
  return TIMING_NAMES[Math.floor(Math.random() * TIMING_NAMES.length)];
}
