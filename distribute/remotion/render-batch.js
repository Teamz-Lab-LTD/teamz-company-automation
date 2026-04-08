#!/usr/bin/env node
/**
 * Teamz Lab — Batch Reel Renderer (Remotion)
 *
 * Renders multiple reels with randomized audio, hooks, and tool selection.
 * Reads tool data from search-index.js, picks top tools, renders MP4s.
 *
 * Usage:
 *   node render-batch.js                    # 5 reels from top tools
 *   node render-batch.js --count 20         # 20 reels
 *   node render-batch.js --tool /ai/grammar-checker/  # Specific tool
 *   node render-batch.js --upload           # Render + upload to YouTube
 *   node render-batch.js --list             # List available tools
 */

const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");

const REMOTION_DIR = __dirname;
const PROJECT_ROOT = path.resolve(REMOTION_DIR, "..", "..", "..");
const OUTPUT_DIR = path.join(require("os").homedir(), "Videos", "teamzlab-reels");
const AUDIO_DIR = path.join(REMOTION_DIR, "public", "audio");

// ─── Parse args ──────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const hasFlag = (n) => args.includes(n);
const COUNT = parseInt(getArg("--count") || "5");
const TOOL_PATH = getArg("--tool");
const UPLOAD = hasFlag("--upload");
const LIST = hasFlag("--list");

// ─── Hook templates ──────────────────────────────────────────────────────────
const HOOKS = [
  "Stop paying for this",
  "This free tool is actually insane",
  "I can't believe this is free",
  "Delete your paid subscription",
  "Why are people still paying for this?",
  "Wait till you see what this does",
  "POV: You found a free tool that works",
  "This just changed everything",
  "Nobody talks about this free tool",
  "I built 1800+ free tools — here's the best",
  "How is this free??",
  "Free tools that replaced $500/mo",
];

// ─── Helpers ─────────────────────────────────────────────────────────────────
function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

function loadTools() {
  const idxPath = path.join(PROJECT_ROOT, "shared", "js", "search-index.js");
  const raw = fs.readFileSync(idxPath, "utf-8").replace(/[^\x00-\x7F]/g, "");
  const tools = [];
  const re = /\{t:'([^']*)',d:'([^']*)',h:'([^']*)'\}/g;
  let m;
  while ((m = re.exec(raw)) !== null) {
    const [, title, desc, href] = m;
    const parts = href.replace(/^\/|\/$/g, "").split("/");
    if (parts.length < 2) continue;
    tools.push({ title: decode(title), desc: decode(desc), href, hub: parts[0], slug: parts.join("_") });
  }
  return tools;
}

function decode(s) {
  return s.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(n)).replace(/&quot;/g, '"');
}

function getAudioFiles() {
  if (!fs.existsSync(AUDIO_DIR)) return [];
  return fs.readdirSync(AUDIO_DIR).filter((f) => f.endsWith(".mp3")).map((f) => `audio/${f}`);
}

function pickTopTools(tools, count) {
  const highRpm = ["finance", "career", "ai", "health", "tax", "legal", "insurance", "salary"];
  const viral = ["design", "image", "video", "games", "text", "productivity"];
  const scored = tools.map((t) => {
    let s = 0;
    if (highRpm.includes(t.hub)) s += 3;
    else if (viral.includes(t.hub)) s += 2;
    else s += 1;
    const d = t.desc.toLowerCase();
    if (d.includes("calculator") || d.includes("generator")) s += 1;
    if (d.includes("ai") || d.includes("detect")) s += 1;
    return { score: s + Math.random(), tool: t };
  });
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, count).map((s) => s.tool);
}

function generateCaption(tool, hook) {
  const tags = ["#freetools", "#productivity", "#tech", "#lifehack", "#webapp", "#freetool", "#nosubscription", "#browsertools"];
  const shuffled = tags.sort(() => Math.random() - 0.5).slice(0, 6);
  return `${hook}\n\n${tool.title} — ${tool.desc.substring(0, 120)}\n\n100% free. No signup. Runs in your browser.\nYour data never leaves your device.\n\nTry it: tool.teamzlab.com${tool.href}\n\n${shuffled.join(" ")}`;
}

// ─── Main ────────────────────────────────────────────────────────────────────
const tools = loadTools();
console.log(`Loaded ${tools.length} tools`);

if (LIST) {
  const hubs = {};
  tools.forEach((t) => (hubs[t.hub] = hubs[t.hub] || []).push(t.title));
  Object.keys(hubs).sort().forEach((h) => {
    console.log(`${h}/ (${hubs[h].length})`);
    hubs[h].slice(0, 3).forEach((t) => console.log(`  - ${t}`));
    if (hubs[h].length > 3) console.log(`  +${hubs[h].length - 3} more`);
  });
  process.exit(0);
}

fs.mkdirSync(OUTPUT_DIR, { recursive: true });
const audioFiles = getAudioFiles();
console.log(`Audio tracks: ${audioFiles.length}`);

// Select tools
let selected;
if (TOOL_PATH) {
  const clean = TOOL_PATH.replace(/^\/|\/$/g, "");
  selected = tools.filter((t) => t.href.replace(/^\/|\/$/g, "") === clean);
  if (!selected.length) { console.error(`Tool not found: ${TOOL_PATH}`); process.exit(1); }
} else {
  selected = pickTopTools(tools, COUNT);
}

console.log(`\nRendering ${selected.length} reels...\n`);

const rendered = [];

for (let i = 0; i < selected.length; i++) {
  const tool = selected[i];
  const hook = pick(HOOKS);
  const audio = audioFiles.length ? pick(audioFiles) : "";
  const outFile = path.join(OUTPUT_DIR, `${tool.slug}.mp4`);
  const captionFile = path.join(OUTPUT_DIR, `${tool.slug}.txt`);

  console.log(`[${i + 1}/${selected.length}] ${tool.title}`);
  console.log(`  Hook: "${hook}"`);
  console.log(`  Audio: ${audio || "none"}`);

  const props = JSON.stringify({
    hook,
    title: tool.title,
    description: tool.desc.substring(0, 150),
    url: `tool.teamzlab.com${tool.href}`,
    audioFile: audio,
  });

  try {
    execSync(
      `npx remotion render src/index.js ToolReel "${outFile}" --props='${props.replace(/'/g, "'\\''")}'`,
      { cwd: REMOTION_DIR, stdio: "pipe", timeout: 120000 }
    );

    const size = (fs.statSync(outFile).size / (1024 * 1024)).toFixed(1);
    console.log(`  Rendered: ${size} MB`);

    // Save caption
    const caption = generateCaption(tool, hook);
    fs.writeFileSync(captionFile, caption);

    rendered.push({ tool, video: outFile, caption: captionFile, hook, audio });
  } catch (e) {
    console.log(`  FAILED: ${e.message.substring(0, 100)}`);
  }
  console.log("");
}

// Upload to YouTube if --upload
if (UPLOAD && rendered.length > 0) {
  console.log("\nUploading to YouTube...\n");
  const ytAuth = path.join(REMOTION_DIR, "..", "youtube-auth.py");

  for (const r of rendered) {
    const title = `${r.hook} | ${r.tool.title} — Free Tool`;
    const desc = fs.readFileSync(r.caption, "utf-8");
    const tags = `free tools,${r.tool.hub},${r.tool.title},browser tools,no signup,privacy`;

    try {
      execSync(
        `python3 "${ytAuth}" --upload "${r.video}" --title "${title.replace(/"/g, '\\"')}" --description "${desc.replace(/"/g, '\\"').replace(/\n/g, '\\n')}" --tags "${tags}"`,
        { stdio: "pipe", timeout: 120000 }
      );
      console.log(`  Uploaded: ${r.tool.title}`);
    } catch (e) {
      console.log(`  Upload failed: ${r.tool.title}`);
    }
  }
}

// ─── Tracking: load/save reel history ────────────────────────────────────────
const HISTORY_FILE = path.join(REMOTION_DIR, "reel-history.json");

function loadHistory() {
  if (fs.existsSync(HISTORY_FILE)) return JSON.parse(fs.readFileSync(HISTORY_FILE, "utf-8"));
  return { reels: [] };
}

function saveHistory(history) {
  fs.writeFileSync(HISTORY_FILE, JSON.stringify(history, null, 2));
}

const history = loadHistory();

// Save each rendered reel to history with platform tracking
for (const r of rendered) {
  const existing = history.reels.find((h) => h.slug === r.tool.slug);
  if (existing) {
    existing.lastRendered = new Date().toISOString();
    existing.video = r.video;
    existing.caption = r.caption;
    existing.hook = r.hook;
  } else {
    history.reels.push({
      slug: r.tool.slug,
      title: r.tool.title,
      href: r.tool.href,
      hub: r.tool.hub,
      hook: r.hook,
      audio: r.audio,
      video: r.video,
      caption: r.caption,
      rendered: new Date().toISOString(),
      lastRendered: new Date().toISOString(),
      platforms: {
        youtube: { posted: false, url: "", postedAt: "" },
        instagram: { posted: false, url: "", postedAt: "" },
        tiktok: { posted: false, url: "", postedAt: "" },
      },
    });
  }
}
saveHistory(history);

// ─── Status commands ─────────────────────────────────────────────────────────
if (hasFlag("--status")) {
  const h = loadHistory();
  const total = h.reels.length;
  const yt = h.reels.filter((r) => r.platforms.youtube.posted).length;
  const ig = h.reels.filter((r) => r.platforms.instagram.posted).length;
  const tt = h.reels.filter((r) => r.platforms.tiktok.posted).length;
  console.log(`\nReel History: ${total} videos`);
  console.log(`  YouTube:   ${yt}/${total} posted`);
  console.log(`  Instagram: ${ig}/${total} posted`);
  console.log(`  TikTok:    ${tt}/${total} posted`);

  const unposted = h.reels.filter(
    (r) => !r.platforms.youtube.posted || !r.platforms.instagram.posted || !r.platforms.tiktok.posted
  );
  if (unposted.length) {
    console.log(`\nPending (${unposted.length}):`);
    for (const r of unposted.slice(0, 10)) {
      const missing = [];
      if (!r.platforms.youtube.posted) missing.push("YT");
      if (!r.platforms.instagram.posted) missing.push("IG");
      if (!r.platforms.tiktok.posted) missing.push("TT");
      console.log(`  ${r.title} — missing: ${missing.join(", ")}`);
    }
    if (unposted.length > 10) console.log(`  ... +${unposted.length - 10} more`);
  }
  process.exit(0);
}

// Mark a reel as posted: --mark slug --platform youtube --url https://...
if (hasFlag("--mark")) {
  const slug = getArg("--mark");
  const platform = getArg("--platform");
  const postUrl = getArg("--url") || "";
  const h = loadHistory();
  const reel = h.reels.find((r) => r.slug === slug || r.title.toLowerCase().includes(slug.toLowerCase()));
  if (reel && platform && reel.platforms[platform]) {
    reel.platforms[platform] = { posted: true, url: postUrl, postedAt: new Date().toISOString() };
    saveHistory(h);
    console.log(`Marked ${reel.title} as posted on ${platform}`);
  } else {
    console.log(`Not found: ${slug} / ${platform}`);
  }
  process.exit(0);
}

// Retry failed/missing platforms: --retry
if (hasFlag("--retry")) {
  const h = loadHistory();
  const platform = getArg("--platform") || "youtube";
  const unposted = h.reels.filter((r) => r.platforms[platform] && !r.platforms[platform].posted && r.video && fs.existsSync(r.video));
  console.log(`\n${unposted.length} reels not posted on ${platform}:`);
  for (const r of unposted.slice(0, 10)) {
    console.log(`  ${r.video}`);
    console.log(`    Caption: ${r.caption}`);
  }
  if (!unposted.length) console.log("  All posted!");
  process.exit(0);
}

// Summary
console.log("=".repeat(50));
console.log(`Rendered: ${rendered.length}/${selected.length}`);
console.log(`Output: ${OUTPUT_DIR}`);
console.log(`History: ${history.reels.length} total reels tracked`);
if (audioFiles.length) console.log(`Audio: ${audioFiles.length} tracks (randomized)`);
console.log(`\nCommands:`);
console.log(`  --status              Show posting status across all platforms`);
console.log(`  --mark SLUG --platform youtube --url URL   Mark as posted`);
console.log(`  --retry --platform youtube    Show unposted reels for retry`);
