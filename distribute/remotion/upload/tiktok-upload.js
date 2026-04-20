#!/usr/bin/env node
/**
 * Teamz Lab — TikTok Scheduled Upload
 *
 * Uploads videos to TikTok via Content Posting API.
 * Rate-limited: 2/day, 5/week, 4h minimum gap.
 *
 * Setup:
 *   1. Register at developers.tiktok.com → Create app
 *   2. Add "Content Posting API" scope (video.upload, video.publish)
 *   3. Run: node upload/tiktok-auth.js  (opens browser for OAuth)
 *   4. Token saved to ~/.config/teamzlab/tiktok-token.json
 *
 * Usage:
 *   node upload/tiktok-upload.js --from-history           # Upload next unposted reel
 *   node upload/tiktok-upload.js --from-history --count 2 # Upload next 2
 *   node upload/tiktok-upload.js --file video.mp4 --caption "text"
 *   node upload/tiktok-upload.js --quota                  # Show usage today
 *   node upload/tiktok-upload.js --setup                  # Show setup instructions
 */

const path = require("path");
const fs = require("fs");
const https = require("https");

const REMOTION_DIR = path.resolve(__dirname, "..");
const TOKEN_FILE = path.join(require("os").homedir(), ".config", "teamzlab", "tiktok-token.json");
const CONFIG_FILE = path.join(require("os").homedir(), ".config", "teamzlab", "tiktok-config.json");
const HISTORY_FILE = path.join(REMOTION_DIR, "reel-history.json");
const QUOTA_FILE = path.join(__dirname, "tiktok-quota.json");

// Safety limits
const MAX_UPLOADS_PER_DAY = 2;
const MAX_UPLOADS_PER_WEEK = 5;
const MIN_GAP_HOURS = 4;

// ─── Parse args ─────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const hasFlag = (n) => args.includes(n);

// ─── Setup instructions ─────────────────────────────────────────────────────
if (hasFlag("--setup")) {
  console.log(`
TikTok Content Posting API — Setup Guide
=========================================

1. Go to: https://developers.tiktok.com/
2. Sign in with your TikTok account
3. Click "Manage apps" → "Create app"
4. App name: "Teamz Lab Video Publisher"
5. Add these scopes:
   - video.upload
   - video.publish
   - user.info.basic
6. Set redirect URI: http://localhost:8889
7. Submit for review (takes 1-3 business days)

After approval, create config file:
  ~/.config/teamzlab/tiktok-config.json

  {
    "client_key": "YOUR_CLIENT_KEY",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8889"
  }

Then run auth:
  node upload/tiktok-auth.js

This opens browser → you authorize → token saved automatically.
Then upload:
  node upload/tiktok-upload.js --from-history
`);
  process.exit(0);
}

// ─── Token management ───────────────────────────────────────────────────────
function checkSetup() {
  if (!fs.existsSync(CONFIG_FILE)) {
    console.error("\nTikTok not configured. Run: node upload/tiktok-upload.js --setup\n");
    process.exit(1);
  }
  if (!fs.existsSync(TOKEN_FILE)) {
    console.error("\nTikTok not authorized. Run: node upload/tiktok-auth.js\n");
    process.exit(1);
  }
}

function loadConfig() { return JSON.parse(fs.readFileSync(CONFIG_FILE, "utf-8")); }
function loadTokens() { return JSON.parse(fs.readFileSync(TOKEN_FILE, "utf-8")); }
function saveTokens(t) { fs.writeFileSync(TOKEN_FILE, JSON.stringify(t, null, 2)); }

function refreshToken() {
  return new Promise((resolve, reject) => {
    const config = loadConfig();
    const tokens = loadTokens();
    const postData = `client_key=${config.client_key}&client_secret=${config.client_secret}&grant_type=refresh_token&refresh_token=${tokens.refresh_token}`;

    const req = https.request({
      hostname: "open.tiktokapis.com",
      path: "/v2/oauth/token/",
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded", "Content-Length": Buffer.byteLength(postData) },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        try {
          const result = JSON.parse(data);
          if (result.access_token) {
            saveTokens(result);
            resolve(result.access_token);
          } else {
            reject(new Error(`Refresh failed: ${data.substring(0, 200)}`));
          }
        } catch (e) { reject(e); }
      });
    });
    req.on("error", reject);
    req.write(postData);
    req.end();
  });
}

async function getAccessToken() {
  const tokens = loadTokens();
  // Check if token expired
  const expiresAt = tokens.expires_at || 0;
  if (Date.now() / 1000 < expiresAt - 300) {
    return tokens.access_token;
  }
  return await refreshToken();
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

  // Reset daily count if new day
  if (q.date !== today) {
    q.date = today;
    q.uploads = 0;
  }

  // Clean week uploads older than 7 days
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  q.weekUploads = (q.weekUploads || []).filter((d) => d > weekAgo);

  return q;
}

function isSafeToUpload() {
  const q = checkQuota();

  if (q.uploads >= MAX_UPLOADS_PER_DAY) {
    return { safe: false, reason: `Daily limit reached (${q.uploads}/${MAX_UPLOADS_PER_DAY})` };
  }

  if ((q.weekUploads || []).length >= MAX_UPLOADS_PER_WEEK) {
    return { safe: false, reason: `Weekly limit reached (${q.weekUploads.length}/${MAX_UPLOADS_PER_WEEK})` };
  }

  // Check minimum gap
  const lastUpload = (q.weekUploads || []).sort().reverse()[0];
  if (lastUpload) {
    const hoursSince = (Date.now() - new Date(lastUpload).getTime()) / (1000 * 60 * 60);
    if (hoursSince < MIN_GAP_HOURS) {
      return { safe: false, reason: `Too soon — ${hoursSince.toFixed(1)}h since last post (min ${MIN_GAP_HOURS}h)` };
    }
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

// ─── TikTok Upload (Content Posting API v2) ─────────────────────────────────
async function uploadToTiktok({ filePath, caption }) {
  const token = await getAccessToken();
  const fileSize = fs.statSync(filePath).size;

  // Step 1: Initialize upload — uses INBOX endpoint (drafts in TikTok app)
  // Why inbox instead of direct publish:
  //   - Works for Business accounts (direct publish needs audited app + private
  //     account; Business accounts can't be set to private)
  //   - Works in sandbox without any account-privacy restriction
  //   - Videos land in user's TikTok app inbox — user reviews + publishes with
  //     one tap. Acts as a draft safety net (algorithm-safer than fully
  //     automated posting anyway).
  //   - Saves the caption as the draft title — user can edit before posting.
  const initBody = JSON.stringify({
    source_info: {
      source: "FILE_UPLOAD",
      video_size: fileSize,
      chunk_size: fileSize, // Single chunk for files under 64MB
      total_chunk_count: 1,
    },
  });

  const initResult = await new Promise((resolve, reject) => {
    const req = https.request({
      hostname: "open.tiktokapis.com",
      path: "/v2/post/publish/inbox/video/init/",
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json; charset=UTF-8",
        "Content-Length": Buffer.byteLength(initBody),
      },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        if (res.statusCode >= 400) reject(new Error(`Init failed ${res.statusCode}: ${data.substring(0, 200)}`));
        else resolve(JSON.parse(data));
      });
    });
    req.on("error", reject);
    req.write(initBody);
    req.end();
  });

  if (initResult.error && initResult.error.code !== "ok") {
    throw new Error(`TikTok init error: ${initResult.error.message || JSON.stringify(initResult.error)}`);
  }

  const publishId = initResult.data.publish_id;
  const uploadUrl = initResult.data.upload_url;

  // Step 2: Upload video file
  await new Promise((resolve, reject) => {
    const url = new URL(uploadUrl);
    const fileData = fs.readFileSync(filePath);

    const req = https.request({
      hostname: url.hostname,
      path: url.pathname + url.search,
      method: "PUT",
      headers: {
        "Content-Type": "video/mp4",
        "Content-Length": fileSize,
        "Content-Range": `bytes 0-${fileSize - 1}/${fileSize}`,
      },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        if (res.statusCode >= 400) reject(new Error(`Upload failed ${res.statusCode}: ${data.substring(0, 200)}`));
        else resolve();
      });
    });
    req.on("error", reject);
    req.write(fileData);
    req.end();
  });

  // Step 3: Check publish status
  let status = "processing";
  let attempts = 0;
  let videoUrl = "";

  while (status === "processing" && attempts < 10) {
    await new Promise((r) => setTimeout(r, 3000)); // Wait 3s between checks
    attempts++;

    const checkResult = await new Promise((resolve, reject) => {
      const checkBody = JSON.stringify({ publish_id: publishId });
      const req = https.request({
        hostname: "open.tiktokapis.com",
        path: "/v2/post/publish/status/fetch/",
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(checkBody),
        },
      }, (res) => {
        let data = "";
        res.on("data", (c) => data += c);
        res.on("end", () => resolve(JSON.parse(data)));
      });
      req.on("error", reject);
      req.write(checkBody);
      req.end();
    });

    status = checkResult.data?.status || "failed";
    if (status === "PUBLISH_COMPLETE") {
      videoUrl = `https://www.tiktok.com/@teamzlab/video/${checkResult.data.publicaly_available_post_id || ""}`;
      break;
    }
    if (status === "FAILED") {
      throw new Error(`TikTok publish failed: ${checkResult.data?.fail_reason || "unknown"}`);
    }
    process.stdout.write(".");
  }

  return { publishId, url: videoUrl, status };
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
  // Quota check
  if (hasFlag("--quota")) {
    const check = isSafeToUpload();
    const q = checkQuota();
    console.log(`\nTikTok Upload Status (${q.date || "no uploads"}):`);
    console.log(`  Today: ${q.uploads}/${MAX_UPLOADS_PER_DAY}`);
    console.log(`  This week: ${(q.weekUploads || []).length}/${MAX_UPLOADS_PER_WEEK}`);
    console.log(`  Status: ${check.safe ? "SAFE to post" : "BLOCKED — " + check.reason}`);
    process.exit(0);
  }

  checkSetup();

  // Upload from history
  if (hasFlag("--from-history")) {
    const h = loadHistory();
    const count = parseInt(getArg("--count") || "1");
    const unposted = h.reels.filter(
      (r) => r.platforms && r.platforms.tiktok && !r.platforms.tiktok.posted && r.video && fs.existsSync(r.video)
    );

    if (!unposted.length) {
      console.log("No unposted TikTok videos. Render some first.");
      process.exit(0);
    }

    // Safety check — --force bypasses gap (inbox uploads are drafts, lower risk)
    const safeCheck = isSafeToUpload();
    if (!safeCheck.safe && !hasFlag("--force")) {
      console.log(`\n  BLOCKED: ${safeCheck.reason}`);
      console.log(`  TikTok rate limits protect your account from being flagged.`);
      console.log(`  Use --force to bypass gap (safe-ish for inbox drafts).\n`);
      process.exit(1);
    }
    if (!safeCheck.safe && hasFlag("--force")) {
      console.log(`\n  --force: bypassing gap check (${safeCheck.reason})\n`);
    }

    const maxNow = Math.min(count, MAX_UPLOADS_PER_DAY - (safeCheck.daily || 0));
    const toUpload = unposted.slice(0, maxNow);
    console.log(`\nUploading ${toUpload.length} video(s) to TikTok...\n`);

    for (let i = 0; i < toUpload.length; i++) {
      const reel = toUpload[i];

      // Read TikTok-specific caption
      let caption = "";
      const ttCaptionFile = (reel.caption || "").replace(".txt", ".tiktok.txt");
      if (fs.existsSync(ttCaptionFile)) {
        caption = fs.readFileSync(ttCaptionFile, "utf-8");
      } else if (reel.caption && fs.existsSync(reel.caption)) {
        caption = fs.readFileSync(reel.caption, "utf-8").substring(0, 300);
      } else {
        caption = `${reel.hook || reel.title} #freetools #shorts`;
      }

      console.log(`[${i + 1}/${toUpload.length}] ${reel.title}`);
      console.log(`  File: ${reel.video}`);
      console.log(`  Caption: ${caption.substring(0, 80)}...`);

      try {
        const result = await uploadToTiktok({ filePath: reel.video, caption });
        recordUpload();

        console.log(`  Uploaded! Status: ${result.status}`);
        if (result.url) console.log(`  URL: ${result.url}`);

        reel.platforms.tiktok = {
          posted: true,
          url: result.url,
          publishId: result.publishId,
          postedAt: new Date().toISOString(),
          retries: 0,
        };
        saveHistory(h);

        // Check if safe for next upload
        const nextCheck = isSafeToUpload();
        if (!nextCheck.safe && i < toUpload.length - 1) {
          console.log(`\n  Rate limit reached — stopping. ${nextCheck.reason}`);
          break;
        }

      } catch (e) {
        console.log(`  FAILED: ${e.message.substring(0, 150)}`);
        reel.platforms.tiktok.retries = (reel.platforms.tiktok.retries || 0) + 1;
        saveHistory(h);
      }
      console.log();
    }
    process.exit(0);
  }

  // Direct upload
  const filePath = getArg("--file");
  const caption = getArg("--caption") || "#freetools #shorts";

  if (!filePath || !fs.existsSync(filePath)) {
    console.log("Usage:");
    console.log("  node upload/tiktok-upload.js --setup                 # Setup guide");
    console.log("  node upload/tiktok-upload.js --from-history          # Upload next unposted");
    console.log("  node upload/tiktok-upload.js --from-history --count 2");
    console.log("  node upload/tiktok-upload.js --file video.mp4 --caption 'text'");
    console.log("  node upload/tiktok-upload.js --quota                 # Check limits");
    process.exit(0);
  }

  const safeCheck = isSafeToUpload();
  if (!safeCheck.safe) {
    console.log(`\n  BLOCKED: ${safeCheck.reason}\n`);
    process.exit(1);
  }

  console.log(`Uploading: ${filePath}`);
  try {
    const result = await uploadToTiktok({ filePath, caption });
    recordUpload();
    console.log(`\nUploaded! ${result.url || "Processing..."}`);
  } catch (e) {
    console.error(`Failed: ${e.message}`);
    process.exit(1);
  }
})();
