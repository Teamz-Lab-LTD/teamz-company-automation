#!/usr/bin/env node
/**
 * Teamz Lab — Batch Reel Renderer V2 (Remotion)
 *
 * Renders reels from SEO-optimized video plans (content-engine.py output)
 * or auto-generates from search-index.js with full template variety.
 *
 * Usage:
 *   node render-batch.js                              # 5 reels from top tools (auto mode)
 *   node render-batch.js --from-plans                 # Render from video-plans.json
 *   node render-batch.js --from-plans --count 10      # First 10 from plans
 *   node render-batch.js --count 20                   # 20 reels (auto mode)
 *   node render-batch.js --tool /ai/grammar-checker/  # Specific tool
 *   node render-batch.js --template BeforeAfter       # Force specific template
 *   node render-batch.js --list                       # List available tools
 *   node render-batch.js --status                     # Show posting status
 *   node render-batch.js --mark SLUG --platform youtube --url URL
 *   node render-batch.js --retry --platform youtube
 *   node render-batch.js --dry-run                    # Show what would render
 */

const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");

const REMOTION_DIR = __dirname;
const CFG = require(path.join(REMOTION_DIR, "project-config.js"));
const PROJECT_ROOT = path.resolve(REMOTION_DIR, "..", "..", "..");
const OUTPUT_DIR = path.join(require("os").homedir(), "Videos", "teamzlab-reels");
const SCREENSHOT_DIR = path.join(OUTPUT_DIR, "screenshots");
const AUDIO_DIR = path.join(REMOTION_DIR, "public", "audio");
const DATA_DIR = path.join(REMOTION_DIR, "data");
const HISTORY_FILE = path.join(REMOTION_DIR, "reel-history.json");
const PLANS_FILE = path.join(DATA_DIR, "video-plans.json");

// ─── Available templates ────────────────────────────────────────────────────
const SHORT_TEMPLATES = ["InstantFix", "BeforeAfter", "CompareThree", "ProofCase"];
const TEMPLATES = [...SHORT_TEMPLATES, "Tutorial"];

// ─── SAFETY LIMITS (prevents platform bans) ─────────────────────────────────
// Based on research: YouTube 5/week, TikTok 4-5/week, Instagram 3-4/week
// YouTube API: 10,000 units/day, videos.insert = 1600 units = max 6 uploads/day
const PLATFORM_LIMITS = {
  youtube:   { daily: 2, weekly: 5, minGapHours: 6 },   // Conservative — avoid spam detection
  tiktok:    { daily: 2, weekly: 5, minGapHours: 4 },
  instagram: { daily: 1, weekly: 4, minGapHours: 6 },
};
const MAX_RENDER_PER_DAY = 20;  // Don't render more than 20 in one session (stockpile limit)

// ─── Parse args ─────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const hasFlag = (n) => args.includes(n);

const COUNT = parseInt(getArg("--count") || "5");
const TOOL_PATH = getArg("--tool");
const FROM_PLANS = hasFlag("--from-plans");
const FORCE_TEMPLATE = getArg("--template");
const FORMAT = getArg("--format") || "short"; // "short" or "tutorial"
const LIST = hasFlag("--list");
const DRY_RUN = hasFlag("--dry-run");

// ─── Status/Mark/Retry commands (handle first, before rendering) ────────────
if (hasFlag("--status")) { showStatus(); process.exit(0); }
if (hasFlag("--mark")) { markPosted(); process.exit(0); }
if (hasFlag("--retry")) { showRetry(); process.exit(0); }

// ─── Hook templates (fallback for auto mode) ────────────────────────────────
const HOOKS = CFG.shortHooks;

const TUTORIAL_HOOKS = CFG.tutorialHooks;

// Auto-generate tutorial steps from tool description
function generateTutorialSteps(tool) {
  const desc = (tool.desc || "").toLowerCase();
  const title = tool.title || "";

  const steps = [
    { label: `Open ${title}`, description: "Visit the tool in your browser — no download or signup needed" },
  ];

  // Smart step generation based on tool type
  if (desc.includes("calculat") || desc.includes("convert")) {
    steps.push({ label: "Enter your values", description: "Type in the numbers or data you want to process" });
    steps.push({ label: "Click Calculate", description: "Hit the button and get instant results" });
    steps.push({ label: "Copy or download", description: "Save your results — share them or use them anywhere" });
  } else if (desc.includes("generat") || desc.includes("creat") || desc.includes("make")) {
    steps.push({ label: "Choose your options", description: "Pick a style, template, or format that fits your needs" });
    steps.push({ label: "Customize your content", description: "Add your own text, colors, or details" });
    steps.push({ label: "Generate your result", description: "Click generate — your result is ready in seconds" });
    steps.push({ label: "Download or share", description: "Save as image or PDF — or share with a link" });
  } else if (desc.includes("check") || desc.includes("analyz") || desc.includes("detect") || desc.includes("test")) {
    steps.push({ label: "Paste or upload your content", description: "Enter the text, URL, or file you want to analyze" });
    steps.push({ label: "Run the analysis", description: "The tool scans your content automatically" });
    steps.push({ label: "Review your results", description: "See scores, issues, and recommendations instantly" });
  } else {
    // Generic steps
    steps.push({ label: "Enter your information", description: "Fill in the form with your details" });
    steps.push({ label: "Click the action button", description: "Hit the main button to process your request" });
    steps.push({ label: "Get your results", description: "View, copy, or download your output instantly" });
  }

  return steps;
}

function getTutorialHook(tool) {
  const action = (tool.desc || "").split(".")[0].toLowerCase().replace(/^(free |online )*/g, "").trim();
  return CFG.getTutorialHook(tool.title, action || "do this");
}

function getTutorialProblem(tool) {
  const problems = [
    `Most ${tool.hub || "online"} tools charge $10-30/month`,
    `You shouldn't need to pay for basic ${tool.hub || "online"} tools`,
    `Paid tools want your email, credit card, and data`,
    `Why is something this simple locked behind a paywall?`,
  ];
  return pick(problems);
}

// Tutorial duration: 30 seconds per step slide + 15s intro + 15s problem + 15s result + 15s CTA
function tutorialDuration(stepCount) {
  const baseFrames = (stepCount * 30 + 60) * 30; // seconds × 30fps
  // Add random jitter of ±5 seconds
  const jitter = (Math.random() * 10 - 5) * 30;
  return Math.round((baseFrames + jitter) / 30) * 30;
}

// ─── Helpers ────────────────────────────────────────────────────────────────
function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

// ─── Duration randomization (anti-spam: avoid identical-length Shorts) ──────
// Each template has a base + random jitter so no two reels are the same length.
// YouTube flags channels where all Shorts are identical duration as automated.
const TEMPLATE_DURATION_RANGE = {
  InstantFix:   { min: 330, max: 420 },   // 11-14 seconds (tightened for retention)
  BeforeAfter:  { min: 390, max: 480 },   // 13-16 seconds
  CompareThree: { min: 480, max: 570 },   // 16-19 seconds
  ProofCase:    { min: 390, max: 480 },   // 13-16 seconds
  Tutorial:     { min: 5400, max: 12600 }, // 3-7 minutes (long-form, unchanged)
};

function randomDuration(template) {
  const range = TEMPLATE_DURATION_RANGE[template] || { min: 450, max: 720 };
  // Round to nearest 30 frames (1 second) for clean cuts
  const raw = range.min + Math.random() * (range.max - range.min);
  return Math.round(raw / 30) * 30;
}

function loadTools() {
  const idxPath = path.join(PROJECT_ROOT, "shared", "js", "search-index.js");
  if (!fs.existsSync(idxPath)) { console.error("search-index.js not found"); return []; }
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

function pickTemplate(tool) {
  if (FORCE_TEMPLATE && TEMPLATES.includes(FORCE_TEMPLATE)) return FORCE_TEMPLATE;
  const hub = tool.hub || "";
  const desc = (tool.desc || "").toLowerCase();
  // Smart template selection based on content
  if (desc.includes("compare") || desc.includes("vs") || desc.includes("alternative")) return "CompareThree";
  if (desc.includes("convert") || desc.includes("compress") || desc.includes("resize") || desc.includes("optimize")) return "BeforeAfter";
  if (hub === "career" || hub === "legal" || desc.includes("review") || desc.includes("client")) return "ProofCase";
  // Random between InstantFix (60%) and others (40%) for variety
  // Only pick from SHORT_TEMPLATES — Tutorial is a separate format
  return Math.random() < 0.6 ? "InstantFix" : pick(SHORT_TEMPLATES);
}

// ─── History management ─────────────────────────────────────────────────────
function loadHistory() {
  if (fs.existsSync(HISTORY_FILE)) return JSON.parse(fs.readFileSync(HISTORY_FILE, "utf-8"));
  return { reels: [] };
}

function saveHistory(h) { fs.writeFileSync(HISTORY_FILE, JSON.stringify(h, null, 2)); }

function getUsedCombos(history) {
  return new Set(history.reels.map((r) => `${r.slug}|${r.template}|${r.themeIndex}`));
}

// Cross-run deduplication: skip tools that already have a reel (any template)
function getRenderedSlugs(history) {
  return new Set(history.reels.map((r) => r.slug));
}

function pickUniqueTheme(slug, template, usedCombos) {
  for (let attempt = 0; attempt < 20; attempt++) {
    const theme = Math.floor(Math.random() * 8);
    const key = `${slug}|${template}|${theme}`;
    if (!usedCombos.has(key)) return theme;
  }
  return Math.floor(Math.random() * 8); // fallback
}

// ─── Status commands ────────────────────────────────────────────────────────
function showStatus() {
  const h = loadHistory();
  const total = h.reels.length;
  if (!total) { console.log("No reels rendered yet."); return; }
  const yt = h.reels.filter((r) => r.platforms && r.platforms.youtube && r.platforms.youtube.posted).length;
  const ig = h.reels.filter((r) => r.platforms && r.platforms.instagram && r.platforms.instagram.posted).length;
  const tt = h.reels.filter((r) => r.platforms && r.platforms.tiktok && r.platforms.tiktok.posted).length;

  // Count by template
  const byTemplate = {};
  h.reels.forEach((r) => { byTemplate[r.template || "ToolReel"] = (byTemplate[r.template || "ToolReel"] || 0) + 1; });

  console.log(`\n${"=".repeat(50)}`);
  console.log(`  Reel History: ${total} videos`);
  console.log(`${"=".repeat(50)}`);
  console.log(`  YouTube:   ${yt}/${total} posted`);
  console.log(`  Instagram: ${ig}/${total} posted`);
  console.log(`  TikTok:    ${tt}/${total} posted`);
  console.log(`\n  Templates used:`);
  Object.entries(byTemplate).sort((a, b) => b[1] - a[1]).forEach(([t, c]) => console.log(`    ${t}: ${c}`));

  const unposted = h.reels.filter(
    (r) => r.platforms && (!r.platforms.youtube.posted || !r.platforms.instagram.posted || !r.platforms.tiktok.posted)
  );
  if (unposted.length) {
    console.log(`\n  Pending (${unposted.length}):`);
    for (const r of unposted.slice(0, 10)) {
      const missing = [];
      if (!r.platforms.youtube.posted) missing.push("YT");
      if (!r.platforms.instagram.posted) missing.push("IG");
      if (!r.platforms.tiktok.posted) missing.push("TT");
      console.log(`    ${r.title} [${r.template || "?"}] — ${missing.join(", ")}`);
    }
    if (unposted.length > 10) console.log(`    ... +${unposted.length - 10} more`);
  }
}

function markPosted() {
  const slug = getArg("--mark");
  const platform = getArg("--platform");
  const postUrl = getArg("--url") || "";
  const force = hasFlag("--force");
  const h = loadHistory();
  const reel = h.reels.find((r) => r.slug === slug || (r.title || "").toLowerCase().includes((slug || "").toLowerCase()));
  if (!reel || !platform || !reel.platforms || !reel.platforms[platform]) {
    console.log(`Not found: ${slug} / ${platform}`);
    return;
  }

  // Safety check — warn if posting too fast
  const check = isSafeToPost(platform, h);
  if (!check.safe && !force) {
    console.log(`\n  WARNING: ${platform.toUpperCase()} rate limit hit!`);
    console.log(`  ${check.reason}`);
    console.log(`\n  This will likely get your account flagged or shadowbanned.`);
    console.log(`  If you already posted anyway, use --force to override.\n`);
    return;
  }

  reel.platforms[platform] = { posted: true, url: postUrl, postedAt: new Date().toISOString(), retries: 0 };
  saveHistory(h);
  console.log(`Marked "${reel.title}" as posted on ${platform}`);

  // Show remaining safe capacity
  const newCheck = isSafeToPost(platform, h);
  if (newCheck.safe) {
    console.log(`  ${platform}: ${newCheck.todayCount || 0}/${PLATFORM_LIMITS[platform].daily} today, ${newCheck.weekCount || 0}/${PLATFORM_LIMITS[platform].weekly} this week`);
  } else {
    console.log(`  ${platform}: LIMIT REACHED — wait before posting more`);
  }
}

function showRetry() {
  const h = loadHistory();
  const platform = getArg("--platform") || "youtube";
  const unposted = h.reels.filter(
    (r) => r.platforms && r.platforms[platform] && !r.platforms[platform].posted && r.video && fs.existsSync(r.video)
  );
  console.log(`\n${unposted.length} reels not posted on ${platform}:`);
  for (const r of unposted.slice(0, 15)) {
    console.log(`  [${r.template || "?"}] ${r.title}`);
    console.log(`    Video: ${r.video}`);
    if (r.youtubeTitle) console.log(`    YT Title: ${r.youtubeTitle}`);
  }
  if (!unposted.length) console.log("  All posted!");
}

// ─── Safety: platform rate limit checker ────────────────────────────────────
function isSafeToPost(platform, history) {
  const limits = PLATFORM_LIMITS[platform];
  if (!limits) return { safe: true };

  const now = new Date();
  const todayStr = now.toISOString().slice(0, 10);
  const weekAgo = new Date(now - 7 * 24 * 60 * 60 * 1000);

  const posted = history.reels.filter(
    (r) => r.platforms && r.platforms[platform] && r.platforms[platform].posted
  );

  // Daily limit
  const todayCount = posted.filter((r) => (r.platforms[platform].postedAt || "").startsWith(todayStr)).length;
  if (todayCount >= limits.daily) {
    return { safe: false, reason: `Daily limit reached (${todayCount}/${limits.daily}). Try tomorrow.` };
  }

  // Weekly limit
  const weekCount = posted.filter((r) => new Date(r.platforms[platform].postedAt || 0) > weekAgo).length;
  if (weekCount >= limits.weekly) {
    return { safe: false, reason: `Weekly limit reached (${weekCount}/${limits.weekly}). Wait a few days.` };
  }

  // Minimum gap
  const lastPost = posted
    .map((r) => new Date(r.platforms[platform].postedAt || 0))
    .sort((a, b) => b - a)[0];
  if (lastPost) {
    const hoursSince = (now - lastPost) / (1000 * 60 * 60);
    if (hoursSince < limits.minGapHours) {
      return { safe: false, reason: `Too soon — last post ${hoursSince.toFixed(1)}h ago (min ${limits.minGapHours}h gap).` };
    }
  }

  return { safe: true, todayCount, weekCount };
}

// ─── Distribute command: show what's safe to post now ───────────────────────
function showDistribute() {
  const h = loadHistory();
  console.log(`\n${"=".repeat(50)}`);
  console.log(`  Distribution Safety Dashboard`);
  console.log(`${"=".repeat(50)}\n`);

  for (const platform of ["youtube", "tiktok", "instagram"]) {
    const check = isSafeToPost(platform, h);
    const limits = PLATFORM_LIMITS[platform];
    const unposted = h.reels.filter(
      (r) => r.platforms && r.platforms[platform] && !r.platforms[platform].posted && r.video && fs.existsSync(r.video)
    );

    const status = check.safe ? "SAFE" : "BLOCKED";
    const icon = check.safe ? "+" : "x";
    console.log(`  [${icon}] ${platform.toUpperCase()} — ${status}`);
    if (!check.safe) console.log(`      Reason: ${check.reason}`);
    console.log(`      Limits: ${limits.daily}/day, ${limits.weekly}/week, ${limits.minGapHours}h gap`);
    console.log(`      Ready to post: ${unposted.length} videos`);

    if (check.safe && unposted.length > 0) {
      const next = unposted[0];
      console.log(`      Next: "${next.youtubeTitle || next.title}"`);
      console.log(`      Video: ${next.video}`);
      console.log(`      Caption: ${next.caption}`);
      if (platform === "tiktok" && fs.existsSync((next.caption || "").replace(".txt", ".tiktok.txt"))) {
        console.log(`      TikTok caption: ${next.caption.replace(".txt", ".tiktok.txt")}`);
      }
      if (platform === "instagram" && fs.existsSync((next.caption || "").replace(".txt", ".instagram.txt"))) {
        console.log(`      IG caption: ${next.caption.replace(".txt", ".instagram.txt")}`);
      }
    }
    console.log();
  }

  console.log(`  After posting, mark done:`);
  console.log(`    node render-batch.js --mark SLUG --platform youtube --url URL\n`);
}

if (hasFlag("--distribute") || hasFlag("--safety")) { showDistribute(); process.exit(0); }

// ═════════════════════════════════════════════════════════════════════════════
// MAIN — Build render queue
// ═════════════════════════════════════════════════════════════════════════════

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
const history = loadHistory();
const usedCombos = getUsedCombos(history);
const renderedSlugs = getRenderedSlugs(history);

// ─── Build render queue ─────────────────────────────────────────────────────
let renderQueue = [];

if (FROM_PLANS) {
  // ── Mode 1: Render from video-plans.json (content-engine.py output) ──
  if (!fs.existsSync(PLANS_FILE)) {
    console.error(`\nNo video plans found. Generate them first:\n  python3 content-engine.py --count 20 --export\n`);
    process.exit(1);
  }

  const plans = JSON.parse(fs.readFileSync(PLANS_FILE, "utf-8"));
  console.log(`Loaded ${plans.count} video plans from content-engine`);
  console.log(`Audio tracks: ${audioFiles.length}\n`);

  const toRender = plans.plans.slice(0, COUNT);

  for (const plan of toRender) {
    const r = plan.render;
    const template = FORCE_TEMPLATE || r.template || "InstantFix";
    const slug = plan.id;
    const themeIndex = r.props.themeIndex != null ? r.props.themeIndex : pickUniqueTheme(slug, template, usedCombos);
    const durationInFrames = randomDuration(template);

    renderQueue.push({
      slug,
      template,
      themeIndex,
      durationInFrames,
      outFile: path.join(OUTPUT_DIR, `${slug}.mp4`),
      captionFile: path.join(OUTPUT_DIR, `${slug}.txt`),
      props: { ...r.props, themeIndex, durationInFrames },
      // YouTube metadata from content-engine
      youtubeTitle: plan.youtube ? plan.youtube.title : "",
      youtubeDesc: plan.youtube ? plan.youtube.description : "",
      youtubeTags: plan.youtube ? plan.youtube.tags : [],
      youtubeCategoryId: plan.youtube ? plan.youtube.categoryId : 28,
      youtubeLanguage: plan.youtube ? plan.youtube.defaultLanguage : "",
      // Platform captions
      tiktokCaption: plan.tiktok ? plan.tiktok.caption : "",
      instagramCaption: plan.instagram ? plan.instagram.caption : "",
      language: plan.language || "en",
      hub: plan.hub || "",
      title: r.props.title,
      hook: r.props.hook,
      audio: r.props.audioFile,
      // App-landing backlinks — threaded into caption + upload-time description
      backlinks: plan.backlinks || null,
    });
  }

} else if (TOOL_PATH) {
  // ── Mode 2: Specific tool ──
  const clean = TOOL_PATH.replace(/^\/|\/$/g, "");
  const found = tools.filter((t) => t.href.replace(/^\/|\/$/g, "") === clean);
  if (!found.length) { console.error(`Tool not found: ${TOOL_PATH}`); process.exit(1); }

  for (const tool of found) {
    const template = pickTemplate(tool);
    const themeIndex = pickUniqueTheme(tool.slug, template, usedCombos);
    const hook = pick(HOOKS);
    const audio = audioFiles.length ? pick(audioFiles) : "";
    const durationInFrames = randomDuration(template);

    renderQueue.push({
      slug: tool.slug,
      template,
      themeIndex,
      durationInFrames,
      outFile: path.join(OUTPUT_DIR, `${tool.slug}.mp4`),
      captionFile: path.join(OUTPUT_DIR, `${tool.slug}.txt`),
      props: {
        hook, title: tool.title, description: tool.desc.substring(0, 150),
        url: CFG.buildUrl(tool),
        audioFile: audio, themeIndex, durationInFrames,
        ctaText: CFG.ctaText, ctaBadge: CFG.ctaBadgeShort, brandName: CFG.brandName,
      },
      youtubeTitle: `${tool.title} — Free, No Signup`,
      title: tool.title, hook, audio, hub: tool.hub, language: "en",
    });
  }

} else {
  // ── Mode 3: Auto-pick top tools ──
  // Filter out tools that already have a reel (cross-run dedup)
  const freshTools = tools.filter((t) => !renderedSlugs.has(t.slug));
  const skipped = tools.length - freshTools.length;
  if (skipped > 0) console.log(`Skipping ${skipped} tools already rendered in previous runs`);
  const selected = pickTopTools(freshTools.length ? freshTools : tools, COUNT);
  console.log(`Format: ${FORMAT} | Audio tracks: ${audioFiles.length}\n`);

  for (const tool of selected) {
    const audio = audioFiles.length ? pick(audioFiles) : "";

    if (FORMAT === "tutorial") {
      // ── Tutorial mode: "How To" long-form videos ──
      const template = "Tutorial";
      const themeIndex = pickUniqueTheme(tool.slug, template, usedCombos);
      const steps = generateTutorialSteps(tool);
      const durationInFrames = tutorialDuration(steps.length);
      const hook = getTutorialHook(tool);
      const problem = getTutorialProblem(tool);

      // Check if screenshots exist for this tool
      const screenshotDir = path.join(SCREENSHOT_DIR, "screenshots", tool.slug);
      const hasScreenshots = fs.existsSync(screenshotDir);
      const stepScreenshots = steps.map((s, i) => {
        const file = path.join(screenshotDir, `step-${i + 1}.png`);
        return fs.existsSync(file) ? `screenshots/${tool.slug}/step-${i + 1}.png` : "";
      });

      // Attach screenshots to steps
      steps.forEach((s, i) => { s.screenshot = stepScreenshots[i] || ""; });

      renderQueue.push({
        slug: tool.slug,
        template,
        themeIndex,
        durationInFrames,
        format: "tutorial",
        outFile: path.join(OUTPUT_DIR, `tutorial-${tool.slug}.mp4`),
        captionFile: path.join(OUTPUT_DIR, `tutorial-${tool.slug}.txt`),
        props: {
          hook, title: tool.title, problem, steps,
          resultText: `${tool.title} — ${CFG.priceLine}`,
          url: CFG.buildUrl(tool),
          audioFile: audio, themeIndex, durationInFrames,
          ctaText: CFG.ctaText, ctaBadge: CFG.ctaBadgeTutorial, brandName: CFG.brandName,
        },
        youtubeTitle: `How to ${tool.title} for Free — Step by Step Tutorial`,
        title: tool.title, hook, audio, hub: tool.hub, language: "en",
      });

      if (!hasScreenshots) {
        console.log(`  NOTE: No screenshots for ${tool.slug}. Run: node capture-tool.js --url ${tool.href}`);
      }
    } else {
      // ── Short mode (default) ──
      const template = pickTemplate(tool);
      const themeIndex = pickUniqueTheme(tool.slug, template, usedCombos);
      const hook = pick(HOOKS);
      const durationInFrames = randomDuration(template);

      renderQueue.push({
        slug: tool.slug,
        template,
        themeIndex,
        durationInFrames,
        format: "short",
        outFile: path.join(OUTPUT_DIR, `${tool.slug}.mp4`),
        captionFile: path.join(OUTPUT_DIR, `${tool.slug}.txt`),
        props: {
          hook, title: tool.title, description: tool.desc.substring(0, 150),
          url: CFG.buildUrl(tool),
          audioFile: audio, themeIndex, durationInFrames,
          ctaText: CFG.ctaText, ctaBadge: CFG.ctaBadgeShort, brandName: CFG.brandName,
        },
        youtubeTitle: `${tool.title} — Free, No Signup`,
        title: tool.title, hook, audio, hub: tool.hub, language: "en",
      });
    }
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// RENDER
// ═════════════════════════════════════════════════════════════════════════════

// Stockpile warning — count only YouTube-unposted reels.
// IG isn't auto-posted (manual), TikTok has weekly quota — counting them
// here causes a permanent BLOCKED state once IG backlog grows past 30.
// YouTube is the only fully-automated platform, so it's the right signal.
const unpostedCount = history.reels.filter(
  (r) => r.platforms && !r.platforms.youtube.posted && r.video && fs.existsSync(r.video)
).length;

if (unpostedCount >= 15 && !DRY_RUN) {
  console.log(`\n  WARNING: You have ${unpostedCount} unposted videos already!`);
  console.log(`  Rendering more without posting = stockpiling = looks spammy when bulk-uploaded.`);
  console.log(`  Post your existing videos first, then render more.`);
  console.log(`\n  Run: node render-batch.js --distribute`);
  console.log(`  to see what's safe to post now.\n`);
  if (unpostedCount >= 30) {
    if (hasFlag("--force")) {
      console.log(`  --force: overriding stockpile block. Queue will grow to ${unpostedCount + renderQueue.length}.\n`);
    } else {
      console.log(`  BLOCKED: ${unpostedCount} unposted videos. Post at least 10 before rendering more.`);
      console.log(`  To override (grows queue): add --force\n`);
      process.exit(1);
    }
  }
}

// Safety cap on renders per session
if (renderQueue.length > MAX_RENDER_PER_DAY) {
  console.log(`\nSafety: capping at ${MAX_RENDER_PER_DAY} renders (requested ${renderQueue.length}).`);
  console.log(`  Reason: stockpiling too many unposted videos looks spammy if uploaded in bulk.`);
  console.log(`  Tip: render in smaller batches, post first, then render more.\n`);
  renderQueue = renderQueue.slice(0, MAX_RENDER_PER_DAY);
}

console.log(`Rendering ${renderQueue.length} reels...\n`);

if (DRY_RUN) {
  for (let i = 0; i < renderQueue.length; i++) {
    const q = renderQueue[i];
    const durSec = (q.durationInFrames || 720) / 30;
    console.log(`[${i + 1}/${renderQueue.length}] ${q.title}`);
    console.log(`  Template: ${q.template} | Theme: ${q.themeIndex} | Duration: ${durSec}s | Lang: ${q.language || "en"}`);
    console.log(`  Hook: "${q.hook || q.props.hook}"`);
    console.log(`  Audio: ${q.audio || q.props.audioFile || "none"}`);
    if (q.youtubeTitle) console.log(`  YT Title: ${q.youtubeTitle}`);
    console.log(`  Output: ${q.outFile}`);
    console.log();
  }
  console.log(`(dry run — nothing rendered)`);
  process.exit(0);
}

const rendered = [];

for (let i = 0; i < renderQueue.length; i++) {
  const q = renderQueue[i];

  const durSec = (q.durationInFrames || 720) / 30;
  console.log(`[${i + 1}/${renderQueue.length}] ${q.title}`);
  console.log(`  Template: ${q.template} | Theme: ${q.themeIndex} | Duration: ${durSec}s | Lang: ${q.language || "en"}`);
  console.log(`  Hook: "${q.hook || q.props.hook}"`);
  console.log(`  Audio: ${q.audio || q.props.audioFile || "none"}`);

  const propsJson = JSON.stringify(q.props);

  try {
    // Tutorials (3-7min) need much longer render time than shorts (15-25s)
    const renderTimeout = q.format === "tutorial" ? 600000 : 180000;
    execSync(
      `npx remotion render src/index.js ${q.template} "${q.outFile}" --props='${propsJson.replace(/'/g, "'\\''")}'`,
      { cwd: REMOTION_DIR, stdio: "pipe", timeout: renderTimeout }
    );

    const size = (fs.statSync(q.outFile).size / (1024 * 1024)).toFixed(1);
    console.log(`  Rendered: ${size} MB`);

    // ── HACK 4 & 5: SEO-optimized descriptions with engagement bait ──
    // YouTube reads descriptions for search ranking. 3 key tricks:
    //   - First 2 lines show in search results (front-load keywords)
    //   - Timestamps = YouTube auto-creates chapters (more click targets)
    //   - End with a question (triggers comments = algorithm boost)
    const ENGAGEMENT_QUESTIONS = [
      "What tool should I cover next? Drop it in the comments! 👇",
      "Did you know this existed? Let me know below! 👇",
      "Would you use this? Tell me in the comments! 💬",
      "What's your favorite free tool? Share below! 👇",
      "Save this for later — you'll need it! ❤️ What else do you need?",
    ];
    const engagementQ = ENGAGEMENT_QUESTIONS[Math.floor(Math.random() * ENGAGEMENT_QUESTIONS.length)];

    let caption;
    if (q.format === "tutorial" && q.props.steps) {
      // Tutorial: full SEO description with timestamps + cross-links
      const stepDur = Math.round((q.durationInFrames || 5400) / 30 / (q.props.steps.length + 4));
      const timestamps = q.props.steps.map((s, i) => {
        const sec = stepDur * (i + 2);
        const m = Math.floor(sec / 60);
        const ss = String(sec % 60).padStart(2, "0");
        return `${m}:${ss} Step ${i + 1}: ${s.label}`;
      });
      caption = [
        // First 2 lines = search preview (front-load keywords)
        CFG.resolveTemplate(CFG.tutorialDescIntro, { hook: q.props.hook, title: q.title }),
        `${CFG.ctaText}: https://${q.props.url}`,
        "",
        CFG.resolveTemplate(CFG.tutorialDescBody, { title: q.title }),
        "",
        "⏱️ Timestamps:",
        "0:00 Intro",
        `0:${String(stepDur).padStart(2, "0")} The Problem`,
        ...timestamps,
        "",
        "━━━━━━━━━━━━━━━━━━━",
        CFG.resolveTemplate(CFG.descFooterLine, {}),
        `📂 More: ${CFG.siteUrl}/${q.hub || ""}/`,
        "",
        `${engagementQ}`,
        "",
        "━━━━━━━━━━━━━━━━━━━",
        `#${(q.hub || "freetools").replace(/[^a-z0-9]/g, "")} #tutorial #howto #free #${(q.title || "").replace(/\s+/g, "").toLowerCase().slice(0, 20)}`,
      ].join("\n");
    } else {
      // Short: compact but SEO-optimized
      const backlinkBlock = [];
      if (q.backlinks && (q.backlinks.play_store || q.backlinks.app_store || q.backlinks.landing)) {
        backlinkBlock.push("📲 Install:");
        if (q.backlinks.play_store) backlinkBlock.push(`Android: ${q.backlinks.play_store}`);
        if (q.backlinks.app_store) backlinkBlock.push(`iOS: ${q.backlinks.app_store}`);
        if (q.backlinks.landing) backlinkBlock.push(`More: ${q.backlinks.landing}`);
        backlinkBlock.push("");
      }
      caption = [
        `${q.props.hook}`,
        "",
        `Try ${q.title} FREE: https://${q.props.url}`,
        "",
        ...backlinkBlock,
        ...CFG.sellingPoints.map((s) => `✅ ${s}`),
        "",
        `${engagementQ}`,
        "",
        CFG.resolveTemplate(CFG.descFooterLine, {}),
        "",
        `#${CFG.shortHashtags.join(" #")} #${(q.hub || "tools").replace(/[^a-z0-9]/g, "")} #${(q.title || "").replace(/\s+/g, "").toLowerCase().slice(0, 20)}`,
      ].join("\n");
    }
    fs.writeFileSync(q.captionFile, caption);

    // Save platform-specific captions if available
    if (q.tiktokCaption) fs.writeFileSync(q.captionFile.replace(".txt", ".tiktok.txt"), q.tiktokCaption);
    if (q.instagramCaption) fs.writeFileSync(q.captionFile.replace(".txt", ".instagram.txt"), q.instagramCaption);

    rendered.push(q);
  } catch (e) {
    console.log(`  FAILED: ${e.message.substring(0, 120)}`);
  }
  console.log();
}

// ═════════════════════════════════════════════════════════════════════════════
// SAVE HISTORY
// ═════════════════════════════════════════════════════════════════════════════

for (const q of rendered) {
  const existing = history.reels.find((h) => h.slug === q.slug && h.template === q.template);
  if (existing) {
    existing.lastRendered = new Date().toISOString();
    existing.video = q.outFile;
    existing.caption = q.captionFile;
    existing.hook = q.hook || q.props.hook;
    existing.themeIndex = q.themeIndex;
    if (q.backlinks) existing.backlinks = q.backlinks;
    if (q.hub) existing.hub = q.hub;
  } else {
    history.reels.push({
      slug: q.slug,
      title: q.title,
      hub: q.hub,
      language: q.language || "en",
      template: q.template,
      themeIndex: q.themeIndex,
      durationInFrames: q.durationInFrames || 720,
      format: q.format || "short",
      hook: q.hook || q.props.hook,
      audio: q.audio || q.props.audioFile,
      video: q.outFile,
      caption: q.captionFile,
      youtubeTitle: q.youtubeTitle || "",
      // Central tracking of app backlinks so upload scripts can inject them
      // into per-platform descriptions (YouTube / TikTok / Instagram).
      backlinks: q.backlinks || null,
      rendered: new Date().toISOString(),
      lastRendered: new Date().toISOString(),
      platforms: {
        youtube: { posted: false, url: "", postedAt: "", retries: 0 },
        instagram: { posted: false, url: "", postedAt: "", retries: 0 },
        tiktok: { posted: false, url: "", postedAt: "", retries: 0 },
      },
    });
  }
}
saveHistory(history);

// ═════════════════════════════════════════════════════════════════════════════
// SUMMARY
// ═════════════════════════════════════════════════════════════════════════════

console.log("=".repeat(50));
console.log(`Rendered: ${rendered.length}/${renderQueue.length}`);
console.log(`Output: ${OUTPUT_DIR}`);
console.log(`History: ${history.reels.length} total reels tracked`);
if (audioFiles.length) console.log(`Audio: ${audioFiles.length} tracks`);

// Format breakdown
const shorts = rendered.filter((r) => r.format !== "tutorial").length;
const tutorials = rendered.filter((r) => r.format === "tutorial").length;
if (tutorials > 0) console.log(`Formats: ${shorts} shorts, ${tutorials} tutorials`);

// Show template distribution
const tDist = {};
rendered.forEach((r) => { tDist[r.template] = (tDist[r.template] || 0) + 1; });
if (Object.keys(tDist).length > 1) {
  console.log(`Templates: ${Object.entries(tDist).map(([t, c]) => `${t}(${c})`).join(", ")}`);
}

console.log(`\nShorts pipeline:`);
console.log(`  1. python3 content-engine.py --count 20 --trending --export`);
console.log(`  2. node render-batch.js --from-plans --count 20`);
console.log(`  3. node upload/youtube-upload.js --from-history --count 2`);
console.log(`\nTutorial pipeline:`);
console.log(`  1. node render-batch.js --format tutorial --count 5`);
console.log(`  2. node capture-tool.js --url /hub/tool/     # Optional: real screenshots`);
console.log(`  3. node render-batch.js --format tutorial --count 5  # Re-render with screenshots`);
console.log(`  4. node upload/youtube-upload.js --from-history --count 1`);
console.log(`\nShared commands:`);
console.log(`  node render-batch.js --distribute          # What's safe to post now`);
console.log(`  node render-batch.js --status              # Overall status`);
console.log(`  node render-batch.js --dry-run             # Preview without rendering`);
