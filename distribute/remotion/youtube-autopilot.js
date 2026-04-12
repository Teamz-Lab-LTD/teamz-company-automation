#!/usr/bin/env node
/**
 * Teamz Lab — YouTube Autopilot
 *
 * ONE command. Auto-decides Short vs Tutorial. Handles everything.
 *
 * Usage:
 *   node youtube-autopilot.js                    # Smart auto-post (default: 1 tutorial + 2 shorts)
 *   node youtube-autopilot.js --shorts 3         # Override: 3 shorts
 *   node youtube-autopilot.js --tutorials 2      # Override: 2 tutorials
 *   node youtube-autopilot.js --upload-only      # Just upload already-rendered videos
 *   node youtube-autopilot.js --status            # What's rendered, what's uploaded, what's next
 *   node youtube-autopilot.js --dry-run           # Preview without doing anything
 *
 * What it does automatically:
 *   1. Checks what's already rendered & unposted
 *   2. Picks the best tools (high-RPM, not yet covered)
 *   3. Decides: calculator/generator/checker → Tutorial, everything else → Short
 *   4. Captures screenshots for tutorials (if local server running)
 *   5. Renders videos via Remotion
 *   6. Uploads to YouTube with anti-spam spacing
 *   7. Shows you what it did
 */

const path = require("path");
const fs = require("fs");
const { execSync, spawn } = require("child_process");

const REMOTION_DIR = __dirname;
const CFG = require(path.join(REMOTION_DIR, "project-config.js"));
const HISTORY_FILE = path.join(REMOTION_DIR, "reel-history.json");
const UPLOAD_SCRIPT = path.join(REMOTION_DIR, "upload", "youtube-upload.js");
const RENDER_SCRIPT = path.join(REMOTION_DIR, "render-batch.js");
const CAPTURE_SCRIPT = path.join(REMOTION_DIR, "capture-tool.js");
const CONTENT_ENGINE = path.join(REMOTION_DIR, "content-engine.py");
const QUOTA_FILE = path.join(REMOTION_DIR, "upload", "quota-tracker.json");
const PROJECT_ROOT = path.resolve(REMOTION_DIR, "..", "..", "..");

// ─── Parse args ─────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const hasFlag = (n) => args.includes(n);

const OVERRIDE_SHORTS = getArg("--shorts");
const OVERRIDE_TUTORIALS = getArg("--tutorials");
const UPLOAD_ONLY = hasFlag("--upload-only");
const DRY_RUN = hasFlag("--dry-run");
const STATUS = hasFlag("--status");

// ─── Helpers ────────────────────────────────────────────────────────────────
function loadHistory() {
  if (fs.existsSync(HISTORY_FILE)) return JSON.parse(fs.readFileSync(HISTORY_FILE, "utf-8"));
  return { reels: [] };
}

function loadQuota() {
  if (!fs.existsSync(QUOTA_FILE)) return { date: "", used: 0, uploads: 0 };
  const q = JSON.parse(fs.readFileSync(QUOTA_FILE, "utf-8"));
  const today = new Date().toISOString().slice(0, 10);
  if (q.date !== today) return { date: today, used: 0, uploads: 0 };
  return q;
}

function run(cmd, opts = {}) {
  try {
    return execSync(cmd, { cwd: REMOTION_DIR, stdio: "pipe", timeout: opts.timeout || 60000, ...opts }).toString();
  } catch (e) {
    return e.stdout ? e.stdout.toString() : e.message;
  }
}

function runVisible(cmd, opts = {}) {
  try {
    execSync(cmd, { cwd: REMOTION_DIR, stdio: "inherit", timeout: opts.timeout || 600000, ...opts });
    return true;
  } catch (e) {
    return false;
  }
}

function isLocalServerRunning() {
  try {
    const http = require("http");
    return new Promise((resolve) => {
      const req = http.get("http://localhost:9090", (res) => {
        resolve(res.statusCode < 500);
      });
      req.on("error", () => resolve(false));
      req.setTimeout(2000, () => { req.destroy(); resolve(false); });
    });
  } catch {
    return Promise.resolve(false);
  }
}

// ─── Smart format decision ──────────────────────────────────────────────────
// This is the brain — decides whether a tool should be a Short or Tutorial.
// Rules:
//   Tutorial = tools where users search "how to X" (calculators, generators, checkers)
//   Short    = tools that are visual/fun/quick (timers, games, color pickers)

function decideFormat(tool) {
  const text = `${tool.title || ""} ${tool.desc || ""}`.toLowerCase();
  const hub = (tool.hub || "").toLowerCase();

  // HIGH-VALUE TUTORIALS — users search "how to" for these
  const tutorialSignals = [
    "calculator", "generator", "builder", "checker", "analyzer",
    "converter", "creator", "planner", "estimator", "compressor",
    "formatter", "validator", "scanner", "detector", "maker",
    "resume", "invoice", "tax", "salary", "mortgage", "loan",
    "budget", "bmi", "calorie", "contract", "letter",
  ];

  const tutorialHubs = [
    "finance", "career", "tax", "legal", "health", "insurance",
    "ai", "pdf", "dev",
  ];

  // SHORT-FRIENDLY — visual, fun, instant wow
  const shortSignals = [
    "timer", "clock", "sound", "noise", "game", "quiz",
    "color", "palette", "gradient", "font", "emoji",
    "random", "dice", "coin", "spinner",
    "countdown", "stopwatch", "aesthetic",
  ];

  const shortHubs = [
    "games", "design", "productivity", "text", "image",
    "video", "grooming", "fun",
  ];

  // Score each format
  let tutorialScore = 0;
  let shortScore = 0;

  for (const signal of tutorialSignals) {
    if (text.includes(signal)) tutorialScore += 3;
  }
  for (const h of tutorialHubs) {
    if (hub === h) tutorialScore += 5;
  }

  for (const signal of shortSignals) {
    if (text.includes(signal)) shortScore += 3;
  }
  for (const h of shortHubs) {
    if (hub === h) shortScore += 5;
  }

  // Tiebreaker: longer descriptions suggest more complex tools → tutorial
  if (tutorialScore === shortScore) {
    return (tool.desc || "").length > 80 ? "tutorial" : "short";
  }

  return tutorialScore > shortScore ? "tutorial" : "short";
}

// ═════════════════════════════════════════════════════════════════════════════
// STATUS
// ═════════════════════════════════════════════════════════════════════════════

if (STATUS) {
  const h = loadHistory();
  const quota = loadQuota();

  const ytPosted = h.reels.filter((r) => r.platforms?.youtube?.posted).length;
  const ytPending = h.reels.filter((r) => r.platforms?.youtube && !r.platforms.youtube.posted && r.video && fs.existsSync(r.video)).length;
  const shorts = h.reels.filter((r) => r.format !== "tutorial").length;
  const tutorials = h.reels.filter((r) => r.format === "tutorial").length;

  console.log(`
${"=".repeat(50)}
  YouTube Autopilot — ${CFG.name}
${"=".repeat(50)}

  Total rendered:     ${h.reels.length} videos
    Shorts:           ${shorts}
    Tutorials:        ${tutorials}

  YouTube:
    Posted:           ${ytPosted}
    Ready to upload:  ${ytPending}

  Quota today:
    Used:             ${quota.used}/10000 units
    Uploads today:    ${quota.uploads}/10
    Remaining:        ${Math.max(0, Math.floor((10000 - quota.used) / 1600))} uploads possible

  Next action:        ${ytPending > 0 ? `Upload ${Math.min(ytPending, 2)} pending videos` : "Render new videos first"}
  `);

  if (ytPending > 0) {
    console.log("  Ready to upload:");
    const pending = h.reels.filter((r) => r.platforms?.youtube && !r.platforms.youtube.posted && r.video && fs.existsSync(r.video));
    for (const r of pending.slice(0, 5)) {
      const fmt = r.format === "tutorial" ? "[TUTORIAL]" : "[SHORT]";
      const dur = r.durationInFrames ? `${Math.round(r.durationInFrames / 30)}s` : "?s";
      console.log(`    ${fmt} ${r.youtubeTitle || r.title} (${dur})`);
    }
    if (pending.length > 5) console.log(`    ... +${pending.length - 5} more`);
  }

  process.exit(0);
}

// ═════════════════════════════════════════════════════════════════════════════
// MAIN — Autopilot
// ═════════════════════════════════════════════════════════════════════════════

(async () => {
  console.log(`
${"=".repeat(50)}
  YouTube Autopilot — ${CFG.name}
  Project: ${require(path.join(REMOTION_DIR, "project-config.js")).PROJECT}
  Domain:  ${CFG.domain}
${"=".repeat(50)}
  `);

  const history = loadHistory();
  const quota = loadQuota();

  // How many uploads can we do today?
  const remainingUploads = Math.max(0, Math.min(10, Math.floor((10000 - quota.used) / 1600)));

  if (remainingUploads === 0 && !DRY_RUN) {
    console.log("  YouTube API quota exhausted for today. Try tomorrow.");
    console.log(`  Quota: ${quota.used}/10000 used, ${quota.uploads} uploads today.\n`);
    process.exit(0);
  }

  // Check what's already rendered and ready to upload
  const readyToUpload = history.reels.filter(
    (r) => r.platforms?.youtube && !r.platforms.youtube.posted && r.video && fs.existsSync(r.video)
  );

  console.log(`  Ready to upload: ${readyToUpload.length} videos`);
  console.log(`  Remaining uploads today: ${remainingUploads}`);

  // ── STEP 1: Upload existing rendered videos first ──
  if (readyToUpload.length > 0) {
    const uploadCount = Math.min(readyToUpload.length, remainingUploads, 3); // Max 3 per run
    console.log(`\n  Step 1: Uploading ${uploadCount} existing video(s)...\n`);

    if (!DRY_RUN) {
      runVisible(`node "${UPLOAD_SCRIPT}" --from-history --count ${uploadCount}`, { timeout: 300000 });
    } else {
      for (let i = 0; i < uploadCount; i++) {
        const r = readyToUpload[i];
        const fmt = r.format === "tutorial" ? "[TUTORIAL]" : "[SHORT]";
        console.log(`  [DRY] Would upload: ${fmt} ${r.youtubeTitle || r.title}`);
      }
    }
  }

  // If upload-only mode, stop here
  if (UPLOAD_ONLY) {
    if (readyToUpload.length === 0) console.log("\n  Nothing to upload. Run without --upload-only to render new videos.");
    process.exit(0);
  }

  // ── STEP 2: Decide what to render next ──
  // Default daily mix: 1 tutorial + 2 shorts (best of both worlds)
  let shortCount = OVERRIDE_SHORTS ? parseInt(OVERRIDE_SHORTS) : 2;
  let tutorialCount = OVERRIDE_TUTORIALS ? parseInt(OVERRIDE_TUTORIALS) : 1;

  // Don't render if too many unposted already
  if (readyToUpload.length >= 10 && !DRY_RUN) {
    console.log(`\n  Skipping render — ${readyToUpload.length} videos already waiting.`);
    console.log("  Upload existing videos first before rendering more.\n");
    process.exit(0);
  }

  console.log(`\n  Step 2: Rendering ${shortCount} short(s) + ${tutorialCount} tutorial(s)...\n`);

  // ── STEP 3: Render Shorts ──
  if (shortCount > 0) {
    console.log(`  --- Rendering ${shortCount} Shorts ---\n`);
    const dryFlag = DRY_RUN ? " --dry-run" : "";
    runVisible(`node "${RENDER_SCRIPT}" --count ${shortCount}${dryFlag}`, { timeout: 600000 });
  }

  // ── STEP 4: Render Tutorials ──
  if (tutorialCount > 0) {
    console.log(`\n  --- Rendering ${tutorialCount} Tutorials ---\n`);

    // Check if local server is running (needed for screenshots)
    const serverRunning = await isLocalServerRunning();
    if (serverRunning && !DRY_RUN) {
      console.log("  Local server detected on :9090 — will capture screenshots.\n");
    } else if (!serverRunning) {
      console.log("  Local server not running — tutorials will use text-only slides.");
      console.log("  For screenshots: python3 -m http.server 9090\n");
    }

    const dryFlag = DRY_RUN ? " --dry-run" : "";
    runVisible(`node "${RENDER_SCRIPT}" --format tutorial --count ${tutorialCount}${dryFlag}`, { timeout: 600000 });
  }

  // ── STEP 5: Upload newly rendered videos ──
  if (!DRY_RUN) {
    // Reload history after rendering
    const freshHistory = loadHistory();
    const freshQuota = loadQuota();
    const newReady = freshHistory.reels.filter(
      (r) => r.platforms?.youtube && !r.platforms.youtube.posted && r.video && fs.existsSync(r.video)
    );
    const freshRemaining = Math.max(0, Math.min(10, Math.floor((10000 - freshQuota.used) / 1600)));

    if (newReady.length > 0 && freshRemaining > 0) {
      const uploadCount = Math.min(newReady.length, freshRemaining, 3);
      console.log(`\n  Step 3: Uploading ${uploadCount} newly rendered video(s)...\n`);
      runVisible(`node "${UPLOAD_SCRIPT}" --from-history --count ${uploadCount}`, { timeout: 300000 });
    }
  }

  // ── Summary ──
  console.log(`
${"=".repeat(50)}
  Autopilot Complete
${"=".repeat(50)}

  Run 'node youtube-autopilot.js --status' to see current state.
  Run 'node youtube-autopilot.js' again tomorrow for the next batch.

  Daily rhythm:
    • 1 tutorial + 2 shorts per day (auto-mixed)
    • Uploads spaced 3+ hours apart (anti-spam)
    • Each Short: unique duration (15-28s)
    • Each publish time: randomized (no exact :00 pattern)
  `);
})();
