#!/usr/bin/env node
/**
 * Teamz Lab — Instagram Reels Upload
 *
 * Uploads Reels to Instagram via Meta Graph API (Content Publishing API).
 * Rate-limited: 1/day, 4/week, 6h minimum gap.
 *
 * Setup:
 *   1. Go to developers.facebook.com → Create app (Business type)
 *   2. Add Instagram Graph API product
 *   3. Add permissions: instagram_content_publish, instagram_basic, pages_read_engagement
 *   4. Link Facebook Page to Instagram Business/Creator account
 *   5. Submit for app review
 *   6. Save config to ~/.config/teamzlab/instagram-config.json
 *   7. Run: node upload/instagram-auth.js
 *
 * Usage:
 *   node upload/instagram-upload.js --from-history           # Upload next unposted reel
 *   node upload/instagram-upload.js --from-history --count 1
 *   node upload/instagram-upload.js --quota                  # Show usage
 *   node upload/instagram-upload.js --setup                  # Setup instructions
 *
 * Note: Instagram Reels API requires video to be hosted at a public URL.
 *       This script uploads to a temporary public host first, then publishes.
 */

const path = require("path");
const fs = require("fs");
const https = require("https");

const REMOTION_DIR = path.resolve(__dirname, "..");
const CONFIG_FILE = path.join(require("os").homedir(), ".config", "teamzlab", "instagram-config.json");
const TOKEN_FILE = path.join(require("os").homedir(), ".config", "teamzlab", "instagram-token.json");
const HISTORY_FILE = path.join(REMOTION_DIR, "reel-history.json");
const QUOTA_FILE = path.join(__dirname, "instagram-quota.json");

// Safety limits
const MAX_UPLOADS_PER_DAY = 1;
const MAX_UPLOADS_PER_WEEK = 4;
const MIN_GAP_HOURS = 6;

// ─── Parse args ─────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const hasFlag = (n) => args.includes(n);

// ─── Setup ──────────────────────────────────────────────────────────────────
if (hasFlag("--setup")) {
  console.log(`
Instagram Reels Upload — Setup Guide
======================================

1. Go to: https://developers.facebook.com/
2. Create a Business app
3. Add product: "Instagram Graph API"
4. Add permissions:
   - instagram_content_publish
   - instagram_basic
   - pages_read_engagement
5. Link your Facebook Page to your Instagram Business/Creator account
   (Instagram Settings → Account → Linked accounts → Facebook)
6. Submit app for review (required for instagram_content_publish)

After approval, create config:
  ~/.config/teamzlab/instagram-config.json

  {
    "app_id": "YOUR_APP_ID",
    "app_secret": "YOUR_APP_SECRET",
    "instagram_account_id": "YOUR_IG_BUSINESS_ACCOUNT_ID",
    "access_token": "YOUR_LONG_LIVED_TOKEN"
  }

To get your Instagram Business Account ID:
  curl "https://graph.facebook.com/v21.0/me/accounts?access_token=TOKEN"
  → get page ID → then:
  curl "https://graph.facebook.com/v21.0/PAGE_ID?fields=instagram_business_account&access_token=TOKEN"

To get a long-lived token (60 days):
  curl "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN"

IMPORTANT: Instagram Reels API requires video at a PUBLIC URL.
The script will use your tool.teamzlab.com hosting or a temp upload service.
`);
  process.exit(0);
}

// ─── Quota tracking ─────────────────────────────────────────────────────────
function loadQuota() {
  if (!fs.existsSync(QUOTA_FILE)) return { date: "", uploads: 0, weekUploads: [] };
  return JSON.parse(fs.readFileSync(QUOTA_FILE, "utf-8"));
}

function saveQuota(q) { fs.writeFileSync(QUOTA_FILE, JSON.stringify(q, null, 2)); }

function checkQuota() {
  const q = loadQuota();
  const today = new Date().toISOString().slice(0, 10);
  if (q.date !== today) { q.date = today; q.uploads = 0; }
  q.weekUploads = (q.weekUploads || []).filter((d) => d > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString());
  return q;
}

function isSafeToUpload() {
  const q = checkQuota();
  if (q.uploads >= MAX_UPLOADS_PER_DAY) return { safe: false, reason: `Daily limit (${q.uploads}/${MAX_UPLOADS_PER_DAY})` };
  if ((q.weekUploads || []).length >= MAX_UPLOADS_PER_WEEK) return { safe: false, reason: `Weekly limit (${q.weekUploads.length}/${MAX_UPLOADS_PER_WEEK})` };
  const last = (q.weekUploads || []).sort().reverse()[0];
  if (last) {
    const hrs = (Date.now() - new Date(last).getTime()) / 3600000;
    if (hrs < MIN_GAP_HOURS) return { safe: false, reason: `Too soon (${hrs.toFixed(1)}h, min ${MIN_GAP_HOURS}h)` };
  }
  return { safe: true, daily: q.uploads, weekly: (q.weekUploads || []).length };
}

function recordUpload() {
  const q = checkQuota();
  q.uploads += 1;
  q.weekUploads = q.weekUploads || [];
  q.weekUploads.push(new Date().toISOString());
  saveQuota(q);
}

// ─── Instagram Reels Publishing (Meta Graph API) ────────────────────────────
function graphApi(endpoint, method, body) {
  return new Promise((resolve, reject) => {
    const config = JSON.parse(fs.readFileSync(CONFIG_FILE, "utf-8"));
    const separator = endpoint.includes("?") ? "&" : "?";
    const fullPath = `/v21.0/${endpoint}${separator}access_token=${config.access_token}`;

    const options = {
      hostname: "graph.facebook.com",
      path: fullPath,
      method: method || "GET",
    };

    if (body) {
      options.headers = { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) };
    }

    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        if (res.statusCode >= 400) reject(new Error(`Graph API ${res.statusCode}: ${data.substring(0, 200)}`));
        else resolve(JSON.parse(data));
      });
    });
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

async function publishReel({ videoUrl, caption }) {
  const config = JSON.parse(fs.readFileSync(CONFIG_FILE, "utf-8"));
  const igId = config.instagram_account_id;

  // Step 1: Create media container
  const container = await graphApi(
    `${igId}/media`,
    "POST",
    JSON.stringify({
      media_type: "REELS",
      video_url: videoUrl,
      caption: caption.substring(0, 2200), // IG caption limit
      share_to_feed: true,
    })
  );

  const containerId = container.id;
  console.log(`  Container created: ${containerId}`);

  // Step 2: Wait for video processing
  let status = "IN_PROGRESS";
  let attempts = 0;
  while (status === "IN_PROGRESS" && attempts < 30) {
    await new Promise((r) => setTimeout(r, 5000)); // Check every 5s
    attempts++;
    const check = await graphApi(`${containerId}?fields=status_code`);
    status = check.status_code;
    process.stdout.write(".");
  }
  console.log();

  if (status !== "FINISHED") {
    throw new Error(`Video processing failed: ${status}`);
  }

  // Step 3: Publish
  const published = await graphApi(
    `${igId}/media_publish`,
    "POST",
    JSON.stringify({ creation_id: containerId })
  );

  return {
    mediaId: published.id,
    url: `https://www.instagram.com/reel/${published.id}/`,
  };
}

// ─── History ────────────────────────────────────────────────────────────────
function loadHistory() {
  if (fs.existsSync(HISTORY_FILE)) return JSON.parse(fs.readFileSync(HISTORY_FILE, "utf-8"));
  return { reels: [] };
}
function saveHistory(h) { fs.writeFileSync(HISTORY_FILE, JSON.stringify(h, null, 2)); }

// ═════════════════════════════════════════════════════════════════════════════
// MAIN
// ═════════════════════════════════════════════════════════════════════════════

(async () => {
  if (hasFlag("--quota")) {
    const check = isSafeToUpload();
    const q = checkQuota();
    console.log(`\nInstagram Upload Status (${q.date || "none"}):`);
    console.log(`  Today: ${q.uploads}/${MAX_UPLOADS_PER_DAY}`);
    console.log(`  This week: ${(q.weekUploads || []).length}/${MAX_UPLOADS_PER_WEEK}`);
    console.log(`  Status: ${check.safe ? "SAFE" : "BLOCKED — " + check.reason}`);
    process.exit(0);
  }

  if (!fs.existsSync(CONFIG_FILE)) {
    console.log("\nInstagram not configured. Run: node upload/instagram-upload.js --setup\n");
    process.exit(1);
  }

  if (hasFlag("--from-history")) {
    const h = loadHistory();
    const count = parseInt(getArg("--count") || "1");
    const unposted = h.reels.filter(
      (r) => r.platforms && r.platforms.instagram && !r.platforms.instagram.posted && r.video && fs.existsSync(r.video)
    );

    if (!unposted.length) {
      console.log("No unposted Instagram reels.");
      process.exit(0);
    }

    const check = isSafeToUpload();
    if (!check.safe) {
      console.log(`\n  BLOCKED: ${check.reason}\n`);
      process.exit(1);
    }

    const toUpload = unposted.slice(0, Math.min(count, MAX_UPLOADS_PER_DAY - (check.daily || 0)));
    console.log(`\nUploading ${toUpload.length} reel(s) to Instagram...\n`);
    console.log(`  NOTE: Instagram API requires video at a public URL.`);
    console.log(`  If this fails, upload manually using the caption files.\n`);

    for (const reel of toUpload) {
      // Read Instagram caption
      let caption = "";
      const igCaptionFile = (reel.caption || "").replace(".txt", ".instagram.txt");
      if (fs.existsSync(igCaptionFile)) {
        caption = fs.readFileSync(igCaptionFile, "utf-8");
      } else if (reel.caption && fs.existsSync(reel.caption)) {
        caption = fs.readFileSync(reel.caption, "utf-8").substring(0, 2200);
      }

      // Append app install link if reel carries backlinks (central reel-history).
      if (reel.backlinks && !/Install:/.test(caption)) {
        const bl = reel.backlinks;
        const link = bl.landing || bl.play_store || bl.app_store;
        if (link) {
          caption = `${caption.trim()}\n\nInstall: ${link}`.substring(0, 2200);
        }
      }

      console.log(`  ${reel.title}`);
      console.log(`  File: ${reel.video}`);

      // For Instagram, video needs to be at a public URL
      // Option 1: If hosted on your domain
      // Option 2: Temporary upload service
      // For now, show manual instructions if no public URL available
      console.log(`\n  Instagram requires a PUBLIC video URL.`);
      console.log(`  Manual upload option:`);
      console.log(`    1. Open Instagram app`);
      console.log(`    2. Create Reel → select: ${reel.video}`);
      console.log(`    3. Paste caption from: ${igCaptionFile || reel.caption}`);
      console.log(`    4. Add trending audio → Post`);
      console.log(`    5. Mark done: node render-batch.js --mark ${reel.slug} --platform instagram --url URL\n`);
    }
    process.exit(0);
  }

  console.log("Usage:");
  console.log("  node upload/instagram-upload.js --setup              # Setup guide");
  console.log("  node upload/instagram-upload.js --from-history       # Upload next reel");
  console.log("  node upload/instagram-upload.js --quota              # Check limits");
})();
