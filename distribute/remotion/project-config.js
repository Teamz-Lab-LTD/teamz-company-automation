/**
 * Project Config — YouTube Video Pipeline
 *
 * This is the ONLY file that changes between projects.
 * Everything else (render, upload, capture, autopilot) reads from here.
 *
 * To use for a different project:
 *   1. Copy this file
 *   2. Change the values
 *   3. Done — entire pipeline adapts automatically
 */

const path = require("path");

// ─── Which project is this? ─────────────────────────────────────────────────
// Auto-detection order (you never need to remember anything):
//   1. --project flag:    node youtube-autopilot.js --project devicegpt
//   2. .youtube-project file in parent project directory
//   3. TEAMZ_VIDEO_PROJECT env var
//   4. Auto-detect from parent folder name
//   5. Default: "web-tools"

function detectProject() {
  const path = require("path");
  const fs = require("fs");
  const args = process.argv.slice(2);

  // 1. --project flag (highest priority)
  const flagIdx = args.indexOf("--project");
  if (flagIdx >= 0 && args[flagIdx + 1]) return args[flagIdx + 1];

  // 2. .youtube-project file in parent project (walk up from cwd)
  let dir = process.cwd();
  for (let i = 0; i < 5; i++) {
    const configFile = path.join(dir, ".youtube-project");
    if (fs.existsSync(configFile)) {
      return fs.readFileSync(configFile, "utf-8").trim();
    }
    dir = path.dirname(dir);
  }

  // 3. Env var
  if (process.env.TEAMZ_VIDEO_PROJECT) return process.env.TEAMZ_VIDEO_PROJECT;

  // 4. Auto-detect from parent folder name
  const scriptDir = __dirname;
  const projectRoot = path.resolve(scriptDir, "..", "..", "..");
  const folderName = path.basename(projectRoot).toLowerCase();
  if (folderName.includes("devicegpt")) return "devicegpt";
  if (folderName.includes("teamzlab-tools") || folderName.includes("tool")) return "web-tools";
  // Add more auto-detections here as you add projects

  // 5. Default
  return "web-tools";
}

const PROJECT = detectProject();

const PROJECTS = {

  // ═══════════════════════════════════════════════════════════════════════════
  // Teamz Lab — 1800+ Free Browser Tools
  // ═══════════════════════════════════════════════════════════════════════════
  "web-tools": {
    name: "Teamz Lab Tools",
    domain: "tool.teamzlab.com",
    brandName: "tool.teamzlab.com",
    tagline: "1800+ free browser tools",
    channelHandle: "@teamzlab",

    // What makes this product special (used in descriptions, comments, CTAs)
    sellingPoints: [
      "No signup",
      "No download",
      "100% private — runs in your browser",
    ],
    privacyLine: "Your data never leaves your browser.",
    priceLine: "Free forever",

    // URL builder: how to construct links to products/tools
    buildUrl: (tool) => `tool.teamzlab.com${tool.href || ""}`,
    buildFullUrl: (tool) => `https://tool.teamzlab.com${tool.href || ""}`,
    siteUrl: "https://tool.teamzlab.com",

    // Where to load product data from
    dataSource: "search-index", // "search-index" | "json-file" | "api"
    // EXPLICIT, not derived. This used to be `null` with a comment claiming
    // "auto-detected from PROJECT_ROOT/shared/js/search-index.js" — but
    // PROJECT_ROOT was computed as 3 levels up from this file, which lands on
    // teamz-projects/ (the sibling-repos folder), not teamzlab-tools/. That
    // depth assumption broke silently on 2026-06-11 when this automation repo
    // was moved out of teamzlab-tools and symlinked back in
    // (teamzlab-tools/scripts/distribute -> ../teamz-company-automation/distribute).
    // render-batch.js's loadTools() has returned [] ever since — every video
    // render after that date silently had zero tools to choose from. Fixed
    // 2026-08-08 by pointing at the real path directly instead of guessing a
    // directory depth that depends on where this repo happens to be checked out.
    dataPath: path.join(path.resolve(__dirname, "..", "..", ".."), "teamzlab-tools",
                         "shared", "js", "search-index.js"),

    // CTA buttons
    ctaText: "Try it free",
    ctaBadgeShort: "LINK IN BIO",
    ctaBadgeTutorial: "LINK IN DESCRIPTION",
    subscribeLine: "Like & Subscribe for more free tools",

    // Hashtags
    defaultHashtags: ["freetools", "free", "nodownload"],
    shortHashtags: ["Shorts", "freetools", "free", "nodownload"],

    // Comment templates
    commentTemplates: [
      "What {category} tool do you wish existed for free? 👇\n\nMeanwhile, try {title}: https://{url}\n{sellingPoints}",
      "Would you switch from a paid tool if a free one did the same thing? 🤔\n\nTry {title} FREE: https://{url}\n{privacyLine}",
      "What's your biggest frustration with {category} tools? Tell me below 👇\n\n{title} is 100% free: https://{url}",
      "Save this for later ❤️ You'll need it!\n\nTry {title}: https://{url}\n{priceLine}. {sellingPoints}",
      "Who else didn't know this existed? 😮\n\n{title}: https://{url}\n{sellingPoints}",
      "Tag someone who needs this! 🔖\n\n{title}: https://{url}\n{priceLine}.",
    ],

    // Hooks
    shortHooks: [
      "Stop paying for this",
      "This free tool is actually insane",
      "I can't believe this is free",
      "Delete your paid subscription",
      "Why are people still paying for this?",
      "Wait till you see what this does",
      "POV: You found a free tool that works",
      "This just changed everything",
      "Nobody talks about this free tool",
      "How is this free??",
      "Free tools that replaced $500/mo",
    ],
    tutorialHooks: [
      "How to {title} for free — step by step",
      "Free {title} — no signup, no download",
      "How to use {title} in your browser",
      "{title} tutorial — completely free",
      "The easiest way to {action} online for free",
    ],

    // Playlist naming
    playlistTemplate: "Free {hub} Tools — Tutorials & Demos",
    playlistDescription: "Free {hub} tools you can use right in your browser. No signup, no download, 100% private.\n\nNew tools added regularly — subscribe!",

    // Tags
    defaultTags: ["free tools", "browser tools", "no signup", "privacy"],

    // Tutorial step templates — how first step reads
    firstStepTemplate: "Visit {title} in your browser — no download or signup needed",

    // Description templates
    tutorialDescIntro: "{hook} — completely free, no signup required.",
    tutorialDescBody: "In this tutorial, you'll learn how to use this tool step by step.\nIt works 100% in your browser — your data never leaves your device.",
    shortDescBody: "{sellingPoints}",
    descFooterLine: "🔗 {tagline}: {siteUrl}",

    // Category for YouTube
    defaultCategoryId: 28, // Science & Technology
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // Template: Mobile App
  // Duplicate and customize for any app project
  // ═══════════════════════════════════════════════════════════════════════════
  "mobile-app-template": {
    name: "My App Name",
    domain: "myapp.com",
    brandName: "My App",
    tagline: "The best app for X",
    channelHandle: "@myapp",

    sellingPoints: [
      "Download free on iOS & Android",
      "Works offline",
      "No account required",
    ],
    privacyLine: "Your data stays on your device.",
    priceLine: "Free to download",

    buildUrl: (tool) => tool.url || "myapp.com",
    buildFullUrl: (tool) => `https://${tool.url || "myapp.com"}`,
    siteUrl: "https://myapp.com",

    dataSource: "json-file",
    dataPath: null, // path to features.json or screens.json

    ctaText: "Download free",
    ctaBadgeShort: "LINK IN BIO",
    ctaBadgeTutorial: "DOWNLOAD LINK IN DESCRIPTION",
    subscribeLine: "Like & Subscribe for more tips",

    defaultHashtags: ["app", "mobileapp", "free"],
    shortHashtags: ["Shorts", "app", "free", "mobileapp"],

    commentTemplates: [
      "Would you try this app? Let me know 👇\n\nDownload {title} free: https://{url}",
      "What feature would you add? Tell me below! 💬\n\n{title}: https://{url}",
      "Save this for later ❤️\n\nGet {title}: https://{url}\n{priceLine}.",
    ],

    shortHooks: [
      "This app is actually insane",
      "Why didn't I know about this sooner?",
      "Delete your old app — this one is free",
      "POV: You found an app that actually works",
      "This app just changed everything",
    ],
    tutorialHooks: [
      "How to use {title} — step by step",
      "{title} tutorial — free app walkthrough",
      "How to {action} with {title}",
    ],

    playlistTemplate: "{hub} — App Tutorials",
    playlistDescription: "Learn how to use {hub} features.\n\nNew tutorials every week — subscribe!",

    defaultTags: ["app", "mobile app", "free app", "tutorial"],
    firstStepTemplate: "Download {title} free from App Store or Google Play",

    tutorialDescIntro: "{hook}",
    tutorialDescBody: "In this tutorial, I'll show you how to use {title} step by step.",
    shortDescBody: "{sellingPoints}",
    descFooterLine: "📱 Download: {siteUrl}",

    defaultCategoryId: 28,
  },
};

// ─── Export active config ───────────────────────────────────────────────────

const config = PROJECTS[PROJECT];
if (!config) {
  console.error(`Unknown project: "${PROJECT}". Available: ${Object.keys(PROJECTS).join(", ")}`);
  console.error(`Set via: TEAMZ_VIDEO_PROJECT=web-tools node youtube-autopilot.js`);
  process.exit(1);
}

// Helper: resolve template strings in config
config.resolveTemplate = function(template, vars) {
  let result = template;
  for (const [key, val] of Object.entries(vars)) {
    result = result.replace(new RegExp(`\\{${key}\\}`, "g"), val);
  }
  // Resolve config-level vars
  result = result.replace(/\{sellingPoints\}/g, this.sellingPoints.map((s) => `✅ ${s}`).join("\n"));
  result = result.replace(/\{privacyLine\}/g, this.privacyLine);
  result = result.replace(/\{priceLine\}/g, this.priceLine);
  result = result.replace(/\{tagline\}/g, this.tagline);
  result = result.replace(/\{siteUrl\}/g, this.siteUrl);
  result = result.replace(/\{brandName\}/g, this.brandName);
  return result;
};

// Helper: pick random from array
config.pick = function(arr) { return arr[Math.floor(Math.random() * arr.length)]; };

// Helper: build comment for a video
config.buildComment = function(title, url, hub) {
  const template = this.pick(this.commentTemplates);
  return this.resolveTemplate(template, { title, url, category: hub || "online" });
};

// Helper: get short hook
config.getShortHook = function() { return this.pick(this.shortHooks); };

// Helper: get tutorial hook
config.getTutorialHook = function(title, action) {
  const template = this.pick(this.tutorialHooks);
  return this.resolveTemplate(template, { title, action: action || "do this" });
};

module.exports = config;
module.exports.PROJECTS = PROJECTS;
module.exports.PROJECT = PROJECT;
