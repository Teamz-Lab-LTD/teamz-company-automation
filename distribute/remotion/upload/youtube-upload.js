#!/usr/bin/env node
/**
 * Teamz Lab — YouTube Scheduled Upload
 *
 * Uploads videos to YouTube via Data API with optimal scheduling.
 * Videos are uploaded as PRIVATE, then auto-publish at the best time.
 *
 * Usage:
 *   node upload/youtube-upload.js --file video.mp4 --title "Title" --description "desc" --tags "tag1,tag2"
 *   node upload/youtube-upload.js --from-history          # Upload next unposted reel from history
 *   node upload/youtube-upload.js --from-history --count 2 # Upload next 2
 *   node upload/youtube-upload.js --quota                  # Show quota usage today
 *
 * Scheduling: Videos upload as PRIVATE with publishAt set to next optimal time slot.
 * YouTube auto-publishes them — no cron needed on your machine.
 */

const path = require("path");
const fs = require("fs");
const https = require("https");

const REMOTION_DIR = path.resolve(__dirname, "..");
const TOKEN_FILE = path.join(require("os").homedir(), ".config", "teamzlab", "youtube-token.json");
const OAUTH_CONFIG = path.join(require("os").homedir(), ".config", "teamzlab", "oauth-client-config.json");
const HISTORY_FILE = path.join(REMOTION_DIR, "reel-history.json");
const QUOTA_FILE = path.join(__dirname, "quota-tracker.json");

// YouTube API: videos.insert = 1600 quota units. Daily limit = 10,000.
const QUOTA_PER_UPLOAD = 1600;
const DAILY_QUOTA = 10000;
const MAX_UPLOADS_PER_DAY = 5; // Safety cap (not just quota — also spam prevention)

// ─── Optimal posting times (Buffer research, 1.8M Shorts analyzed) ──────────
// Times are in the VIEWER'S local time. We schedule in UTC and offset per target audience.
// Peak: evenings 6-9 PM local time. Best days: Friday > Saturday > Thursday.
const OPTIMAL_SLOTS = {
  // day: [hour, hour, hour] — local time of target audience
  0: [19, 20, 17],  // Sunday
  1: [20, 17, 18],  // Monday
  2: [20, 21, 19],  // Tuesday
  3: [19, 20, 21],  // Wednesday
  4: [19, 20, 21],  // Thursday
  5: [16, 18, 19],  // Friday (BEST day)
  6: [19, 11, 18],  // Saturday
};

// Target timezone offset (hours from UTC) based on content language/hub
const AUDIENCE_TIMEZONE = {
  "en": -5,  // US East (EST) — largest English audience
  "no": 1,   // Norway (CET)
  "de": 1,   // Germany (CET)
  "fr": 1,   // France (CET)
  "sv": 1,   // Sweden (CET)
  "fi": 2,   // Finland (EET)
  "nl": 1,   // Netherlands (CET)
  "ar": 4,   // UAE/Gulf (GST)
  "id": 7,   // Indonesia (WIB)
  "vi": 7,   // Vietnam (ICT)
  "ja": 9,   // Japan (JST)
  "es": -5,  // Spanish (LatAm US)
  "pt": -3,  // Portuguese (Brazil)
};

// ─── Parse args ─────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : null; };
const hasFlag = (n) => args.includes(n);

// ─── Token management ───────────────────────────────────────────────────────
function loadTokens() {
  if (!fs.existsSync(TOKEN_FILE)) {
    console.error("No YouTube token. Run: python3 scripts/distribute/youtube-auth.py");
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(TOKEN_FILE, "utf-8"));
}

function loadOAuthConfig() {
  const data = JSON.parse(fs.readFileSync(OAUTH_CONFIG, "utf-8"));
  const key = Object.keys(data)[0];
  return data[key];
}

function refreshToken() {
  return new Promise((resolve, reject) => {
    const tokens = loadTokens();
    const config = loadOAuthConfig();
    const postData = new URLSearchParams({
      client_id: config.client_id,
      client_secret: config.client_secret,
      refresh_token: tokens.refresh_token,
      grant_type: "refresh_token",
    }).toString();

    const req = https.request({
      hostname: "oauth2.googleapis.com",
      path: "/token",
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded", "Content-Length": postData.length },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        const result = JSON.parse(data);
        result.refresh_token = tokens.refresh_token;
        fs.writeFileSync(TOKEN_FILE, JSON.stringify(result, null, 2));
        resolve(result.access_token);
      });
    });
    req.on("error", reject);
    req.write(postData);
    req.end();
  });
}

async function getAccessToken() {
  const tokens = loadTokens();
  // Try existing token first
  try {
    await apiGet("/youtube/v3/channels?part=id&mine=true", tokens.access_token);
    return tokens.access_token;
  } catch (e) {
    // Refresh
    return await refreshToken();
  }
}

function apiGet(path, token) {
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: "www.googleapis.com",
      path,
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        if (res.statusCode >= 400) reject(new Error(`API ${res.statusCode}: ${data.substring(0, 200)}`));
        else resolve(JSON.parse(data));
      });
    });
    req.on("error", reject);
    req.end();
  });
}

// ─── Quota tracking ─────────────────────────────────────────────────────────
function loadQuota() {
  if (!fs.existsSync(QUOTA_FILE)) return { date: "", used: 0, uploads: 0 };
  return JSON.parse(fs.readFileSync(QUOTA_FILE, "utf-8"));
}

function saveQuota(q) { fs.writeFileSync(QUOTA_FILE, JSON.stringify(q, null, 2)); }

function checkQuota() {
  const q = loadQuota();
  const today = new Date().toISOString().slice(0, 10);
  if (q.date !== today) {
    // New day — reset
    return { date: today, used: 0, uploads: 0 };
  }
  return q;
}

function useQuota(units) {
  const q = checkQuota();
  q.used += units;
  q.uploads += 1;
  saveQuota(q);
  return q;
}

// ─── Schedule: find next optimal publish time ───────────────────────────────
function getNextOptimalTime(language = "en") {
  const tzOffset = AUDIENCE_TIMEZONE[language] || -5; // default US East
  const now = new Date();

  // Try slots for next 7 days
  for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
    const targetDate = new Date(now.getTime() + dayOffset * 24 * 60 * 60 * 1000);
    const dayOfWeek = targetDate.getUTCDay();
    const slots = OPTIMAL_SLOTS[dayOfWeek] || [19, 20];

    for (const localHour of slots) {
      // Convert local hour to UTC
      const utcHour = (localHour - tzOffset + 24) % 24;

      const scheduled = new Date(targetDate);
      scheduled.setUTCHours(utcHour, 0, 0, 0);

      // Must be at least 30 minutes in the future
      if (scheduled > new Date(now.getTime() + 30 * 60 * 1000)) {
        return scheduled;
      }
    }
  }

  // Fallback: tomorrow at 7 PM target local time
  const fallback = new Date(now.getTime() + 24 * 60 * 60 * 1000);
  const utcHour = (19 - tzOffset + 24) % 24;
  fallback.setUTCHours(utcHour, 0, 0, 0);
  return fallback;
}

// ─── Upload video ───────────────────────────────────────────────────────────
async function uploadVideo({ filePath, title, description, tags, categoryId, language, scheduledTime }) {
  const token = await getAccessToken();
  const fileSize = fs.statSync(filePath).size;

  const metadata = {
    snippet: {
      title: title.substring(0, 100),
      description: description.substring(0, 5000),
      tags: (tags || []).slice(0, 30),
      categoryId: String(categoryId || 28),
      defaultLanguage: language && language !== "en" ? language : undefined,
    },
    status: {
      privacyStatus: scheduledTime ? "private" : "public",
      publishAt: scheduledTime ? scheduledTime.toISOString() : undefined,
      selfDeclaredMadeForKids: false,
    },
  };

  // Clean undefined fields
  if (!metadata.snippet.defaultLanguage) delete metadata.snippet.defaultLanguage;
  if (!metadata.status.publishAt) delete metadata.status.publishAt;

  const metaJson = JSON.stringify(metadata);

  return new Promise((resolve, reject) => {
    // Step 1: Initiate resumable upload
    const initReq = https.request({
      hostname: "www.googleapis.com",
      path: "/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": fileSize,
        "X-Upload-Content-Type": "video/mp4",
      },
    }, (res) => {
      const uploadUrl = res.headers.location;
      if (!uploadUrl) {
        let errData = "";
        res.on("data", (c) => errData += c);
        res.on("end", () => reject(new Error(`Init failed ${res.statusCode}: ${errData.substring(0, 200)}`)));
        return;
      }

      // Step 2: Upload the file
      const fileStream = fs.createReadStream(filePath);
      const url = new URL(uploadUrl);

      const uploadReq = https.request({
        hostname: url.hostname,
        path: url.pathname + url.search,
        method: "PUT",
        headers: {
          "Content-Length": fileSize,
          "Content-Type": "video/mp4",
        },
      }, (uploadRes) => {
        let data = "";
        uploadRes.on("data", (c) => data += c);
        uploadRes.on("end", () => {
          if (uploadRes.statusCode >= 400) {
            reject(new Error(`Upload failed ${uploadRes.statusCode}: ${data.substring(0, 200)}`));
          } else {
            const result = JSON.parse(data);
            resolve({
              videoId: result.id,
              url: `https://youtube.com/shorts/${result.id}`,
              publishAt: scheduledTime ? scheduledTime.toISOString() : "now",
            });
          }
        });
      });
      uploadReq.on("error", reject);
      fileStream.pipe(uploadReq);
    });
    initReq.on("error", reject);
    initReq.write(metaJson);
    initReq.end();
  });
}

// ─── History management ─────────────────────────────────────────────────────
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
    const q = checkQuota();
    console.log(`\nYouTube API Quota (${q.date || "no uploads today"}):`);
    console.log(`  Used: ${q.used}/${DAILY_QUOTA} units`);
    console.log(`  Uploads today: ${q.uploads}/${MAX_UPLOADS_PER_DAY}`);
    console.log(`  Remaining: ${Math.floor((DAILY_QUOTA - q.used) / QUOTA_PER_UPLOAD)} uploads possible`);
    process.exit(0);
  }

  // Upload from history
  if (hasFlag("--from-history")) {
    const h = loadHistory();
    const count = parseInt(getArg("--count") || "1");
    const unposted = h.reels.filter(
      (r) => r.platforms && r.platforms.youtube && !r.platforms.youtube.posted && r.video && fs.existsSync(r.video)
    );

    if (!unposted.length) {
      console.log("No unposted videos. Render some first: node render-batch.js --from-plans");
      process.exit(0);
    }

    // Quota safety
    const quota = checkQuota();
    if (quota.uploads >= MAX_UPLOADS_PER_DAY) {
      console.log(`\n  BLOCKED: Daily upload limit reached (${quota.uploads}/${MAX_UPLOADS_PER_DAY}).`);
      console.log(`  YouTube quota resets at midnight Pacific Time.\n`);
      process.exit(1);
    }

    const toUpload = unposted.slice(0, Math.min(count, MAX_UPLOADS_PER_DAY - quota.uploads));
    console.log(`\nUploading ${toUpload.length} video(s) to YouTube...\n`);

    for (let i = 0; i < toUpload.length; i++) {
      const reel = toUpload[i];
      const lang = reel.language || "en";
      const scheduledTime = getNextOptimalTime(lang);

      // Read caption file for description
      let description = "";
      if (reel.caption && fs.existsSync(reel.caption)) {
        description = fs.readFileSync(reel.caption, "utf-8");
      }

      // Parse tags from caption or use defaults
      const tags = ["free tools", reel.hub, reel.title, "browser tools", "no signup", "privacy"].filter(Boolean);

      const title = reel.youtubeTitle || `${reel.title} — Free, No Signup`;

      console.log(`[${i + 1}/${toUpload.length}] ${title}`);
      console.log(`  File: ${reel.video}`);
      console.log(`  Scheduled: ${scheduledTime.toISOString()} (${lang.toUpperCase()} audience)`);
      console.log(`  Local time: ~${OPTIMAL_SLOTS[scheduledTime.getDay()][0]}:00 for viewers`);

      try {
        const result = await uploadVideo({
          filePath: reel.video,
          title,
          description,
          tags,
          categoryId: 28,
          language: lang,
          scheduledTime,
        });

        useQuota(QUOTA_PER_UPLOAD);
        console.log(`  Uploaded! Video ID: ${result.videoId}`);
        console.log(`  URL: ${result.url}`);
        console.log(`  Publishes at: ${result.publishAt}`);

        // Update history
        reel.platforms.youtube = {
          posted: true,
          url: result.url,
          videoId: result.videoId,
          postedAt: new Date().toISOString(),
          scheduledAt: scheduledTime.toISOString(),
          retries: 0,
        };
        saveHistory(h);

      } catch (e) {
        console.log(`  FAILED: ${e.message.substring(0, 150)}`);
        reel.platforms.youtube.retries = (reel.platforms.youtube.retries || 0) + 1;
        saveHistory(h);
      }
      console.log();
    }

    const finalQuota = checkQuota();
    console.log(`Quota: ${finalQuota.used}/${DAILY_QUOTA} used, ${finalQuota.uploads} uploads today`);
    process.exit(0);
  }

  // Direct upload with flags
  const filePath = getArg("--file");
  const title = getArg("--title") || "Free Tool — No Signup";
  const description = getArg("--description") || "";
  const tags = (getArg("--tags") || "free tools").split(",");
  const lang = getArg("--lang") || "en";

  if (!filePath || !fs.existsSync(filePath)) {
    console.log("Usage:");
    console.log("  node upload/youtube-upload.js --from-history          # Upload next unposted reel");
    console.log("  node upload/youtube-upload.js --from-history --count 2");
    console.log("  node upload/youtube-upload.js --file video.mp4 --title 'Title'");
    console.log("  node upload/youtube-upload.js --quota                 # Check quota");
    process.exit(0);
  }

  const scheduledTime = getNextOptimalTime(lang);
  console.log(`Uploading: ${filePath}`);
  console.log(`Scheduled: ${scheduledTime.toISOString()}`);

  try {
    const result = await uploadVideo({ filePath, title, description, tags, categoryId: 28, language: lang, scheduledTime });
    useQuota(QUOTA_PER_UPLOAD);
    console.log(`\nUploaded! ${result.url}`);
    console.log(`Publishes at: ${result.publishAt}`);
  } catch (e) {
    console.error(`Failed: ${e.message}`);
    process.exit(1);
  }
})();
