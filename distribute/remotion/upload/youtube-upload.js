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
const CFG = require(path.join(REMOTION_DIR, "project-config.js"));
const TOKEN_FILE = path.join(require("os").homedir(), ".config", "teamzlab", "youtube-token.json");
const OAUTH_CONFIG = path.join(require("os").homedir(), ".config", "teamzlab", "oauth-client-config.json");
const HISTORY_FILE = path.join(REMOTION_DIR, "reel-history.json");
const QUOTA_FILE = path.join(__dirname, "quota-tracker.json");

// YouTube API: videos.insert = 1600 quota units. Daily limit = 10,000.
// Shorts are treated differently — YouTube allows far more Shorts than long-form.
// Safe limit for Shorts: 15-20/day (YouTube creators routinely post 3-5 Shorts/day without issues).
const QUOTA_PER_UPLOAD = 1600;
const DAILY_QUOTA = 10000;
const MAX_UPLOADS_PER_DAY = 10; // Shorts: safe for algorithm (staggered 3h apart = ~5/day publish)
const MAX_PER_BATCH = 5; // Max uploads per single script run (forces you to spread across day)

// ─── Consistent posting time (trains YouTube algorithm) ─────────────────────
// YouTube algorithm learns your posting schedule and pre-loads feeds for subscribers.
// Strategy: ONE consistent time per day + tiny ±10 min jitter (looks human, not bot).
// Consistency > optimization. Posting at 7 PM daily beats random "optimal" times.
//
// Slots are ordered by priority: first slot = default daily post time.
// Second/third slots = only used when staggering multiple uploads in one day.
const OPTIMAL_SLOTS = {
  // day: [primary, secondary, tertiary] — local time of target audience
  0: [19, 12, 16],  // Sunday:   7 PM (main), noon, 4 PM
  1: [19, 12, 16],  // Monday:   7 PM (main), noon, 4 PM
  2: [19, 12, 16],  // Tuesday:  7 PM (main), noon, 4 PM
  3: [19, 12, 16],  // Wednesday: 7 PM (main), noon, 4 PM
  4: [19, 12, 16],  // Thursday: 7 PM (main), noon, 4 PM
  5: [19, 12, 16],  // Friday:   7 PM (main), noon, 4 PM
  6: [19, 12, 16],  // Saturday: 7 PM (main), noon, 4 PM
};

// Target timezone offset (hours from UTC) based on content language/hub
const AUDIENCE_TIMEZONE = {
  "en": 0,     // UK (GMT) — primary care home audience
  "en-GB": 0,  // UK explicit
  "en-AU": 10, // Australia (AEST)
  "en-IE": 0,  // Ireland (same as UK)
  "en-NZ": 12, // New Zealand (NZST)
  "en-US": -5, // US East (EST)
  "no": 1,     // Norway (CET)
  "de": 1,     // Germany (CET)
  "fr": 1,     // France (CET)
  "sv": 1,     // Sweden (CET)
  "fi": 2,     // Finland (EET)
  "nl": 1,     // Netherlands (CET)
  "ar": 4,     // UAE/Gulf (GST)
  "id": 7,     // Indonesia (WIB)
  "vi": 7,     // Vietnam (ICT)
  "ja": 9,     // Japan (JST)
  "es": -5,    // Spanish (LatAm US)
  "pt": -3,    // Portuguese (Brazil)
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

// ─── SCOPE GUARD — prevents silent "upload-but-no-comment" failures ─────────
// Checks the live token has every scope needed for upload + comment.
// If a scope is missing, aborts BEFORE uploading so you never end up with
// another batch of commentless Shorts (the bug that got shipped once).
let _scopeChecked = false;
async function assertScopes() {
  if (_scopeChecked) return;
  const tokens = loadTokens();
  // tokens.scope is a space-separated string per OAuth2 spec
  const granted = new Set((tokens.scope || "").split(/\s+/).filter(Boolean));
  const required = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",  // comments, playlists
  ];
  const missing = required.filter((s) => !granted.has(s));
  if (missing.length) {
    console.error(`\n  ERROR: OAuth token is missing required scope(s):`);
    missing.forEach((s) => console.error(`    - ${s}`));
    console.error(`\n  Without these, uploads would silently skip pinned comments, playlists, etc.`);
    console.error(`  Fix (one time):`);
    console.error(`    rm ~/.config/teamzlab/youtube-token.json`);
    console.error(`    python3 scripts/distribute/youtube-auth.py`);
    console.error(`\n  Aborting upload to prevent broken posts.\n`);
    process.exit(1);
  }
  _scopeChecked = true;
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
// STAGGER: Each call returns a slot 3 hours after the last one used.
// This prevents algorithm penalty from bulk publishing.
// YouTube Shorts best practice: max 3-5 per day, spaced 3+ hours apart.
let _lastScheduledTime = null;
const STAGGER_HOURS = 3; // Minimum gap between scheduled publishes

function getNextOptimalTime(language = "en") {
  const tzOffset = AUDIENCE_TIMEZONE[language] || 0; // default UK (GMT)
  const now = new Date();

  // If we already scheduled one, next must be at least STAGGER_HOURS later
  const earliest = _lastScheduledTime
    ? new Date(_lastScheduledTime.getTime() + STAGGER_HOURS * 60 * 60 * 1000)
    : new Date(now.getTime() + 30 * 60 * 1000);

  // Try optimal slots for next 7 days
  for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
    const targetDate = new Date(now.getTime() + dayOffset * 24 * 60 * 60 * 1000);
    const dayOfWeek = targetDate.getUTCDay();
    const slots = OPTIMAL_SLOTS[dayOfWeek] || [19, 20];

    for (const localHour of slots) {
      const utcHour = (localHour - tzOffset + 24) % 24;
      const scheduled = new Date(targetDate);
      // Add tiny jitter: ±10 minutes so it looks human, not bot.
      // Keep it small — consistency trains the algorithm, wild randomness breaks it.
      const jitterMinutes = Math.floor(Math.random() * 20) - 10; // -10 to +10
      scheduled.setUTCHours(utcHour, Math.max(0, jitterMinutes + 0), 0, 0);

      // Must be after earliest (respects stagger gap)
      if (scheduled > earliest) {
        _lastScheduledTime = scheduled;
        return scheduled;
      }
    }
  }

  // Fallback: STAGGER_HOURS after last, or tomorrow 7 PM local
  const fallback = _lastScheduledTime
    ? new Date(_lastScheduledTime.getTime() + STAGGER_HOURS * 60 * 60 * 1000)
    : new Date(now.getTime() + 24 * 60 * 60 * 1000);

  if (!_lastScheduledTime) {
    const utcHour = (19 - tzOffset + 24) % 24;
    const jitterMinutes = Math.floor(Math.random() * 20) - 10;
    fallback.setUTCHours(utcHour, Math.max(0, jitterMinutes + 0), 0, 0);
  }

  _lastScheduledTime = fallback;
  return fallback;
}

// ─── Upload video ───────────────────────────────────────────────────────────
async function uploadVideo({ filePath, title, description, tags, categoryId, language, scheduledTime }) {
  await assertScopes();  // Abort if token can't comment/manage playlists — never ship a commentless Short again.
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
      privacyStatus: getArg("--privacy") || (scheduledTime ? "private" : "public"),
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

// ─── HACK 1: Engagement-bait pinned comment ─────────────────────────────────
// Plain link comments get ignored. Engagement-bait comments get replies,
// which boosts comment count, which boosts algorithm ranking.
// Pattern: question + value + link (not link-first).

function buildComment(title, url, hub) {
  return CFG.buildComment(title, url, hub);
}

async function postComment(videoId, text) {
  const token = await getAccessToken();
  return new Promise((resolve) => {
    const body = JSON.stringify({
      snippet: {
        videoId,
        topLevelComment: { snippet: { textOriginal: text } },
      },
    });
    const req = https.request({
      hostname: "www.googleapis.com",
      path: "/youtube/v3/commentThreads?part=snippet",
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
      },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        if (res.statusCode >= 400) {
          console.log(`  Comment: failed (${res.statusCode}) — post manually later`);
          resolve(null);
        } else {
          const result = JSON.parse(data);
          console.log(`  Comment posted (engagement-bait)`);
          resolve(result.id);
        }
      });
    });
    req.on("error", () => { console.log("  Comment: network error"); resolve(null); });
    req.write(body);
    req.end();
  });
}

// ─── HACK 2: Auto-reply to own comment (doubles comment count) ──────────────
// YouTube counts replies as separate comments. Self-replying to your own pinned
// comment immediately gives you 2 comments instead of 1, which looks more active.

const SELF_REPLY_TEMPLATES = [
  "Drop a ❤️ if you found this useful!",
  `More on the channel — subscribe to never miss one!`,
  "Bookmark this — you'll thank yourself later 🔖",
  "Let me know if you want a tutorial on this 👇",
  `${CFG.subscribeLine || "Like & Subscribe for more!"}`,
];

async function postSelfReply(parentCommentId) {
  if (!parentCommentId) return;
  const token = await getAccessToken();
  const reply = SELF_REPLY_TEMPLATES[Math.floor(Math.random() * SELF_REPLY_TEMPLATES.length)];

  return new Promise((resolve) => {
    const body = JSON.stringify({
      snippet: {
        parentId: parentCommentId,
        textOriginal: reply,
      },
    });
    const req = https.request({
      hostname: "www.googleapis.com",
      path: "/youtube/v3/comments?part=snippet",
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
      },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        if (res.statusCode < 400) console.log(`  Self-reply posted (comment count hack)`);
        resolve();
      });
    });
    req.on("error", () => resolve());
    req.write(body);
    req.end();
  });
}

// ─── HACK 3: Auto-create playlist (groups videos = more watch time) ─────────
// Playlists increase session watch time — YouTube's #1 ranking signal.
// Auto-create one playlist per hub (e.g., "Free Finance Tools", "Free AI Tools").
// Adding a video to a playlist also triggers a "new content" signal to subscribers.

const _playlistCache = {};

async function getOrCreatePlaylist(hub, language) {
  const cacheKey = `${hub}-${language}`;
  if (_playlistCache[cacheKey]) return _playlistCache[cacheKey];

  const token = await getAccessToken();
  const hubName = hub.charAt(0).toUpperCase() + hub.slice(1);
  const playlistTitle = CFG.resolveTemplate(CFG.playlistTemplate, { hub: hubName });

  // Search existing playlists
  try {
    const searchResult = await apiGet(
      `/youtube/v3/playlists?part=snippet&mine=true&maxResults=50`,
      token
    );
    if (searchResult.items) {
      const existing = searchResult.items.find(
        (p) => p.snippet.title.toLowerCase().includes(hub.toLowerCase())
      );
      if (existing) {
        _playlistCache[cacheKey] = existing.id;
        return existing.id;
      }
    }
  } catch (e) {
    // Non-critical — continue without playlist
  }

  // Create new playlist
  return new Promise((resolve) => {
    const body = JSON.stringify({
      snippet: {
        title: playlistTitle,
        description: CFG.resolveTemplate(CFG.playlistDescription, { hub: hubName }),
      },
      status: { privacyStatus: "public" },
    });
    const req = https.request({
      hostname: "www.googleapis.com",
      path: "/youtube/v3/playlists?part=snippet,status",
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
      },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        if (res.statusCode < 400) {
          const result = JSON.parse(data);
          _playlistCache[cacheKey] = result.id;
          console.log(`  Playlist created: "${playlistTitle}"`);
          resolve(result.id);
        } else {
          resolve(null);
        }
      });
    });
    req.on("error", () => resolve(null));
    req.write(body);
    req.end();
  });
}

async function addToPlaylist(playlistId, videoId) {
  if (!playlistId || !videoId) return;
  const token = await getAccessToken();

  return new Promise((resolve) => {
    const body = JSON.stringify({
      snippet: {
        playlistId,
        resourceId: { kind: "youtube#video", videoId },
      },
    });
    const req = https.request({
      hostname: "www.googleapis.com",
      path: "/youtube/v3/playlistItems?part=snippet",
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
      },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        if (res.statusCode < 400) console.log(`  Added to playlist`);
        resolve();
      });
    });
    req.on("error", () => resolve());
    req.write(body);
    req.end();
  });
}

// ═════════════════════════════════════════════════════════════════════════════
// MAIN
// ═════════════════════════════════════════════════════════════════════════════

// Locked against tiktok-upload.js / comment-catchup.js — see upload/reel-lock.js.
const { withLock } = require("./reel-lock");

withLock(async () => {
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
      // Anti-spam: wait 45-90 seconds between uploads to avoid bulk-upload detection.
      // YouTube flags channels that upload 16 videos in 80 seconds as automated spam.
      if (i > 0) {
        const delaySec = 45 + Math.floor(Math.random() * 45); // 45-90s
        console.log(`  Waiting ${delaySec}s before next upload (anti-spam delay)...`);
        await new Promise((r) => setTimeout(r, delaySec * 1000));
      }

      const reel = toUpload[i];
      const lang = reel.language || "en";
      const scheduledTime = getNextOptimalTime(lang);

      // Read caption file for description
      let description = "";
      if (reel.caption && fs.existsSync(reel.caption)) {
        description = fs.readFileSync(reel.caption, "utf-8");
      }

      // Inject app-store / landing backlinks if the reel was seeded from an
      // app landing (content-engine app-mode). Idempotent — skip if caption
      // already contains the Install: block from render time.
      if (reel.backlinks && !/📲 Install:/.test(description)) {
        const bl = reel.backlinks;
        const parts = [];
        if (bl.play_store) parts.push(`Android: ${bl.play_store}`);
        if (bl.app_store) parts.push(`iOS: ${bl.app_store}`);
        if (bl.landing) parts.push(`More: ${bl.landing}`);
        if (parts.length) {
          description = `${description.trimEnd()}\n\n📲 Install:\n${parts.join("\n")}\n`;
        }
      }

      // Parse tags from caption or use defaults
      const tags = [...CFG.defaultTags, reel.hub, reel.title].filter(Boolean);

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

        // Extract tool URL from caption
        let reelUrl = "";
        if (reel.caption && fs.existsSync(reel.caption)) {
          const captionText = fs.readFileSync(reel.caption, "utf-8");
          const urlMatch = captionText.match(/https?:\/\/tool\.teamzlab\.com[^\s]*/);
          if (urlMatch) reelUrl = urlMatch[0].replace("https://", "");
        }
        if (!reelUrl) reelUrl = CFG.domain;

        // HACK 1: Engagement-bait pinned comment (not just a link)
        const commentText = buildComment(reel.title || title, reelUrl, reel.hub || "");
        const commentId = await postComment(result.videoId, commentText);

        // HACK 2: Self-reply to double comment count
        if (commentId) {
          await postSelfReply(commentId);
          // Mark commented so comment-catchup.js skips on re-run
          reel.platforms.youtube.commented = true;
          reel.platforms.youtube.commentId = commentId;
        } else {
          // Comment failed — queue for catch-up so the video doesn't end up commentless forever
          reel.platforms.youtube.commented = false;
          reel.platforms.youtube.commentPending = true;
          console.log(`  Queued for comment catch-up: node upload/comment-catchup.js --go`);
        }

        // HACK 3: Auto-add to hub playlist (increases session watch time)
        if (reel.hub) {
          const playlistId = await getOrCreatePlaylist(reel.hub, lang);
          await addToPlaylist(playlistId, result.videoId);
        }

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
  const tags = (getArg("--tags") || CFG.defaultTags.join(",")).split(",");
  const lang = getArg("--lang") || "en";

  if (!filePath || !fs.existsSync(filePath)) {
    console.log("Usage:");
    console.log("  node upload/youtube-upload.js --from-history          # Upload next unposted reel");
    console.log("  node upload/youtube-upload.js --from-history --count 2");
    console.log("  node upload/youtube-upload.js --file video.mp4 --title 'Title'");
    console.log("  node upload/youtube-upload.js --quota                 # Check quota");
    process.exit(0);
  }

  const publishNow = hasFlag("--now");
  const scheduledTime = publishNow ? null : getNextOptimalTime(lang);
  console.log(`Uploading: ${filePath}`);
  console.log(publishNow ? "Publishing: NOW (public, immediate)" : `Scheduled: ${scheduledTime.toISOString()}`);

  try {
    const result = await uploadVideo({ filePath, title, description, tags, categoryId: Number(getArg("--category")) || 28, language: lang, scheduledTime });
    useQuota(QUOTA_PER_UPLOAD);
    console.log(`\nUploaded! ${result.url}`);
    console.log(`Publishes at: ${result.publishAt}`);
  } catch (e) {
    console.error(`Failed: ${e.message}`);
    process.exit(1);
  }
});
