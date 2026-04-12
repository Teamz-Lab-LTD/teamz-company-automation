#!/usr/bin/env node
/**
 * Teamz Lab — Tool Screenshot Capture (Playwright)
 *
 * Auto-opens a tool page, takes 4-6 screenshots at different states
 * for use in Tutorial videos. Outputs screenshots to a per-tool folder.
 *
 * Usage:
 *   node capture-tool.js --url /ai/grammar-checker/
 *   node capture-tool.js --url /finance/salary-calculator/ --steps 6
 *   node capture-tool.js --from-plans                    # Capture all from video-plans.json
 *   node capture-tool.js --list                          # List captured tools
 *
 * Output: ~/Videos/teamzlab-reels/screenshots/{slug}/step-1.png ... step-N.png
 *
 * Requires: npx playwright install chromium (one-time)
 */

const path = require("path");
const fs = require("fs");

const REMOTION_DIR = __dirname;
const OUTPUT_BASE = path.join(require("os").homedir(), "Videos", "teamzlab-reels", "screenshots");
const PLANS_FILE = path.join(REMOTION_DIR, "data", "video-plans.json");
const BASE_URL = "http://localhost:9090";

// ─── Parse args ─────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const hasFlag = (n) => args.includes(n);

const TOOL_URL = getArg("--url");
const STEP_COUNT = parseInt(getArg("--steps") || "5");
const FROM_PLANS = hasFlag("--from-plans");

if (hasFlag("--list")) {
  if (fs.existsSync(OUTPUT_BASE)) {
    const dirs = fs.readdirSync(OUTPUT_BASE).filter((d) => fs.statSync(path.join(OUTPUT_BASE, d)).isDirectory());
    console.log(`\nCaptured tools (${dirs.length}):`);
    dirs.forEach((d) => {
      const files = fs.readdirSync(path.join(OUTPUT_BASE, d)).filter((f) => f.endsWith(".png"));
      console.log(`  ${d}/ — ${files.length} screenshots`);
    });
  } else {
    console.log("No screenshots captured yet.");
  }
  process.exit(0);
}

// ─── Screenshot capture strategy ────────────────────────────────────────────
// Each step simulates a real user interaction on the tool page.
// The screenshots become slides in the Tutorial video template.

async function captureToolScreenshots(toolPath, stepCount = 5) {
  // Dynamic import for Playwright (ES module)
  let chromium;
  try {
    const pw = require("playwright");
    chromium = pw.chromium;
  } catch (e) {
    console.error("Playwright not installed. Run: npm install playwright && npx playwright install chromium");
    process.exit(1);
  }

  const slug = toolPath.replace(/^\/|\/$/g, "").replace(/\//g, "_");
  const outDir = path.join(OUTPUT_BASE, slug);
  fs.mkdirSync(outDir, { recursive: true });

  const url = `${BASE_URL}${toolPath.startsWith("/") ? toolPath : "/" + toolPath}`;
  console.log(`  Opening: ${url}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1080, height: 1920 },
    deviceScaleFactor: 2,
    colorScheme: "dark",
  });
  const page = await context.newPage();

  const screenshots = [];

  try {
    // Navigate to tool page
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    // Wait for any animations to settle
    await page.waitForTimeout(1500);

    // ── Step 1: Full page view (hero/above-the-fold) ──
    console.log("  Step 1: Full page view");
    await page.screenshot({
      path: path.join(outDir, "step-1.png"),
      clip: { x: 0, y: 0, width: 1080, height: 1920 },
    });
    screenshots.push({ file: "step-1.png", label: "Tool overview", type: "full" });

    // ── Step 2: Focus on the tool calculator/form area ──
    console.log("  Step 2: Tool form area");
    const calcBox = await page.evaluate(() => {
      const calc = document.querySelector(".tool-calculator") || document.querySelector(".site-main");
      if (calc) {
        const rect = calc.getBoundingClientRect();
        return { x: rect.x, y: rect.y, width: rect.width, height: Math.min(rect.height, 1400) };
      }
      return null;
    });

    if (calcBox) {
      await page.screenshot({
        path: path.join(outDir, "step-2.png"),
        clip: { x: Math.max(0, calcBox.x), y: Math.max(0, calcBox.y), width: Math.min(1080, calcBox.width), height: Math.min(1920, calcBox.height) },
      });
    } else {
      // Fallback: scroll down slightly for form area
      await page.evaluate(() => window.scrollTo(0, 300));
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, "step-2.png"), clip: { x: 0, y: 0, width: 1080, height: 1920 } });
    }
    screenshots.push({ file: "step-2.png", label: "Enter your details", type: "form" });

    // ── Step 3: Fill in sample data (interact with inputs) ──
    console.log("  Step 3: Filling sample data");
    await page.evaluate(() => {
      const inputs = document.querySelectorAll(".tool-calculator input[type='text'], .tool-calculator input[type='number'], .tool-calculator textarea");
      const sampleData = ["John Smith", "50000", "London", "test@example.com", "Sample Company"];
      inputs.forEach((input, i) => {
        if (i < sampleData.length) {
          input.value = sampleData[i];
          input.dispatchEvent(new Event("input", { bubbles: true }));
          input.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
      // Try to select first option in select elements
      const selects = document.querySelectorAll(".tool-calculator select");
      selects.forEach((sel) => {
        if (sel.options.length > 1) {
          sel.selectedIndex = 1;
          sel.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
    });
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(outDir, "step-3.png"), clip: { x: 0, y: 0, width: 1080, height: 1920 } });
    screenshots.push({ file: "step-3.png", label: "Fill in your information", type: "filled" });

    // ── Step 4: Click the main action button (Calculate/Generate/Check) ──
    console.log("  Step 4: Clicking action button");
    const clicked = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll(".tool-calculator button, .tool-calculator .btn-primary, .tool-calculator [type='submit']"));
      const actionBtn = btns.find((b) => {
        const text = (b.textContent || "").toLowerCase();
        return text.includes("calculat") || text.includes("generat") || text.includes("check") ||
               text.includes("convert") || text.includes("analyz") || text.includes("create") ||
               text.includes("start") || text.includes("submit") || text.includes("run");
      }) || btns[0];
      if (actionBtn) { actionBtn.click(); return true; }
      return false;
    });

    if (clicked) {
      // Wait for results to render
      await page.waitForTimeout(2000);
    }

    await page.screenshot({ path: path.join(outDir, "step-4.png"), clip: { x: 0, y: 0, width: 1080, height: 1920 } });
    screenshots.push({ file: "step-4.png", label: "Click to generate results", type: "action" });

    // ── Step 5: Scroll to results area ──
    console.log("  Step 5: Results view");
    await page.evaluate(() => {
      const result = document.querySelector(".tool-result") || document.querySelector(".tool-output") ||
                     document.querySelector("[id*='result']") || document.querySelector("[class*='result']");
      if (result) {
        result.scrollIntoView({ behavior: "instant", block: "start" });
      } else {
        window.scrollTo(0, 600);
      }
    });
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(outDir, "step-5.png"), clip: { x: 0, y: 0, width: 1080, height: 1920 } });
    screenshots.push({ file: "step-5.png", label: "Your results are ready", type: "result" });

    // ── Step 6 (optional): Download/share buttons focus ──
    if (stepCount >= 6) {
      console.log("  Step 6: Share/download area");
      await page.evaluate(() => {
        const shareBar = document.querySelector(".share-bar") || document.querySelector("[class*='share']") ||
                         document.querySelector("[class*='download']");
        if (shareBar) shareBar.scrollIntoView({ behavior: "instant", block: "center" });
      });
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, "step-6.png"), clip: { x: 0, y: 0, width: 1080, height: 1920 } });
      screenshots.push({ file: "step-6.png", label: "Download or share your result", type: "share" });
    }

    // Save metadata
    const meta = {
      slug,
      toolPath,
      capturedAt: new Date().toISOString(),
      screenshots,
      stepCount: screenshots.length,
    };
    fs.writeFileSync(path.join(outDir, "meta.json"), JSON.stringify(meta, null, 2));

    console.log(`  Captured ${screenshots.length} screenshots → ${outDir}`);
  } catch (e) {
    console.error(`  Capture failed: ${e.message.substring(0, 150)}`);
  } finally {
    await browser.close();
  }

  return { slug, dir: outDir, screenshots };
}

// ═════════════════════════════════════════════════════════════════════════════
// MAIN
// ═════════════════════════════════════════════════════════════════════════════

(async () => {
  fs.mkdirSync(OUTPUT_BASE, { recursive: true });

  if (FROM_PLANS) {
    // Capture screenshots for all tutorial plans
    if (!fs.existsSync(PLANS_FILE)) {
      console.error("No video plans. Run: python3 content-engine.py --format tutorial --export");
      process.exit(1);
    }

    const plans = JSON.parse(fs.readFileSync(PLANS_FILE, "utf-8"));
    const tutorials = (plans.plans || []).filter((p) => p.format === "tutorial");

    if (!tutorials.length) {
      console.log("No tutorial plans found in video-plans.json. Generate with --format tutorial");
      process.exit(0);
    }

    console.log(`\nCapturing screenshots for ${tutorials.length} tutorials...\n`);

    for (let i = 0; i < tutorials.length; i++) {
      const plan = tutorials[i];
      const toolPath = plan.toolPath || `/${plan.hub}/${plan.slug}/`;
      console.log(`[${i + 1}/${tutorials.length}] ${plan.title || plan.id}`);
      await captureToolScreenshots(toolPath, plan.steps ? plan.steps.length : STEP_COUNT);
      console.log();
    }
  } else if (TOOL_URL) {
    // Capture single tool
    console.log(`\nCapturing: ${TOOL_URL}\n`);
    await captureToolScreenshots(TOOL_URL, STEP_COUNT);
  } else {
    console.log("Usage:");
    console.log("  node capture-tool.js --url /ai/grammar-checker/");
    console.log("  node capture-tool.js --url /finance/salary-calculator/ --steps 6");
    console.log("  node capture-tool.js --from-plans");
    console.log("  node capture-tool.js --list");
    console.log("\nNote: Local server must be running on port 9090:");
    console.log("  python3 -m http.server 9090");
  }
})();
