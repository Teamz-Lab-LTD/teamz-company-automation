#!/usr/bin/env node
/**
 * Comment Catch-Up — post pinned first comments to all previously-uploaded
 * Shorts that are missing one.
 *
 * Fixes the 403-error-silently-skipped comments that accumulated while the
 * OAuth token was missing the youtube.force-ssl scope.
 *
 * Prerequisites (one-time):
 *   1. rm ~/.config/teamzlab/youtube-token.json
 *   2. python3 scripts/distribute/youtube-auth.py   (re-auth with new scope)
 *
 * Usage:
 *   node scripts/distribute/remotion/upload/comment-catchup.js          # Dry-run first
 *   node scripts/distribute/remotion/upload/comment-catchup.js --go     # Actually post
 *   node scripts/distribute/remotion/upload/comment-catchup.js --go --count 5
 *
 * Safety:
 *   - Defaults to dry-run (prints what WOULD post; makes no API calls)
 *   - 30–60s random gap between comments (anti-spam)
 *   - Stops cleanly on first 403/401 and tells you to re-auth
 *   - Marks each reel with platforms.youtube.commented=true so re-runs skip
 */

const path = require("path");
const fs = require("fs");
const https = require("https");
const { URL } = require("url");

const REMOTION_DIR = path.resolve(__dirname, "..");
const CFG = require(path.join(REMOTION_DIR, "project-config.js"));
const HISTORY_FILE = path.join(REMOTION_DIR, "reel-history.json");
const TOKEN_FILE = path.join(require("os").homedir(), ".config", "teamzlab", "youtube-token.json");
const OAUTH_CFG_FILE = path.join(require("os").homedir(), ".config", "teamzlab", "oauth-client-config.json");

const args = process.argv.slice(2);
const DRY_RUN = !args.includes("--go");
const COUNT = (() => {
  const i = args.indexOf("--count");
  return i >= 0 ? parseInt(args[i + 1]) || 999 : 999;
})();

function loadHistory() {
  if (!fs.existsSync(HISTORY_FILE)) {
    console.error(`History not found: ${HISTORY_FILE}`);
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(HISTORY_FILE, "utf-8"));
}
function saveHistory(h) {
  fs.writeFileSync(HISTORY_FILE, JSON.stringify(h, null, 2));
}

async function refreshToken() {
  if (!fs.existsSync(TOKEN_FILE)) {
    console.error(`\n  ERROR: no token at ${TOKEN_FILE}`);
    console.error(`  Run: python3 scripts/distribute/youtube-auth.py\n`);
    process.exit(1);
  }
  const tok = JSON.parse(fs.readFileSync(TOKEN_FILE, "utf-8"));
  const cfg = JSON.parse(fs.readFileSync(OAUTH_CFG_FILE, "utf-8"));
  const body = new URLSearchParams({
    client_id: cfg.client_id,
    client_secret: cfg.client_secret,
    refresh_token: tok.refresh_token,
    grant_type: "refresh_token",
  }).toString();
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: "oauth2.googleapis.com",
      path: "/token",
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded", "Content-Length": Buffer.byteLength(body) },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        try {
          const j = JSON.parse(data);
          if (j.access_token) { tok.access_token = j.access_token; fs.writeFileSync(TOKEN_FILE, JSON.stringify(tok, null, 2)); resolve(j.access_token); }
          else reject(new Error("token refresh failed: " + data));
        } catch (e) { reject(e); }
      });
    });
    req.on("error", reject);
    req.write(body); req.end();
  });
}

async function postComment(token, videoId, text) {
  const body = JSON.stringify({ snippet: { videoId, topLevelComment: { snippet: { textOriginal: text } } } });
  return new Promise((resolve) => {
    const req = https.request({
      hostname: "www.googleapis.com",
      path: "/youtube/v3/commentThreads?part=snippet",
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        if (res.statusCode >= 400) {
          resolve({ ok: false, status: res.statusCode, body: data });
        } else {
          try { resolve({ ok: true, id: JSON.parse(data).id }); } catch { resolve({ ok: false, status: 0, body: "parse error" }); }
        }
      });
    });
    req.on("error", (e) => resolve({ ok: false, status: 0, body: e.message }));
    req.write(body); req.end();
  });
}

async function postReply(token, parentId, text) {
  const body = JSON.stringify({ snippet: { parentId, textOriginal: text } });
  return new Promise((resolve) => {
    const req = https.request({
      hostname: "www.googleapis.com",
      path: "/youtube/v3/comments?part=snippet",
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
    }, (res) => { let d = ""; res.on("data", (c) => d += c); res.on("end", () => resolve(res.statusCode < 400)); });
    req.on("error", () => resolve(false));
    req.write(body); req.end();
  });
}

function deriveToolUrl(reel) {
  if (reel.toolUrl) return reel.toolUrl;
  if (reel.caption && fs.existsSync(reel.caption)) {
    const txt = fs.readFileSync(reel.caption, "utf-8");
    const m = txt.match(/https?:\/\/[^\s]+/);
    if (m) return m[0].replace("https://", "");
  }
  return CFG.domain;
}

const SELF_REPLY_TEMPLATES = [
  "Drop a ❤️ if you found this useful!",
  "More on the channel — subscribe to never miss one!",
  "Bookmark this — you'll thank yourself later 🔖",
  "Let me know if you want a tutorial on this 👇",
];

(async () => {
  const h = loadHistory();
  const targets = (h.reels || []).filter((r) => {
    const yt = r.platforms && r.platforms.youtube;
    return yt && yt.posted && yt.videoId && !yt.commented;
  }).slice(0, COUNT);

  console.log(`\n${"=".repeat(60)}`);
  console.log(`  Comment Catch-Up — ${targets.length} video(s) need a first comment`);
  console.log(`  Mode: ${DRY_RUN ? "DRY RUN (no API calls)" : "LIVE (posting comments)"}`);
  console.log(`${"=".repeat(60)}\n`);

  if (!targets.length) {
    console.log("  Nothing to do. Either all posted videos already have comments, or the history is empty.\n");
    process.exit(0);
  }

  let token = null;
  if (!DRY_RUN) {
    try { token = await refreshToken(); }
    catch (e) { console.error(`  Token refresh failed: ${e.message}\n  Try: python3 scripts/distribute/youtube-auth.py\n`); process.exit(1); }
  }

  let posted = 0, failed = 0;
  for (let i = 0; i < targets.length; i++) {
    const reel = targets[i];
    const vid = reel.platforms.youtube.videoId;
    const vurl = `https://youtube.com/shorts/${vid}`;
    const toolUrl = deriveToolUrl(reel);
    const hub = reel.hub || "tools";
    const text = CFG.buildComment(reel.title || reel.youtubeTitle || "our free tool", toolUrl, hub);

    console.log(`[${i + 1}/${targets.length}] ${reel.title || vid}`);
    console.log(`  Short: ${vurl}`);
    console.log(`  Tool : https://${toolUrl}`);
    console.log(`  Comment:\n    ${text.replace(/\n/g, "\n    ")}`);

    if (DRY_RUN) {
      console.log(`  [DRY] would post this comment.\n`);
      continue;
    }

    if (i > 0) {
      const waitSec = 30 + Math.floor(Math.random() * 30); // 30-60s
      console.log(`  Waiting ${waitSec}s (anti-spam)...`);
      await new Promise((r) => setTimeout(r, waitSec * 1000));
    }

    const res = await postComment(token, vid, text);
    if (!res.ok) {
      failed++;
      console.log(`  FAILED: HTTP ${res.status} — ${String(res.body).slice(0, 180)}`);
      if (res.status === 401 || res.status === 403) {
        console.log(`\n  STOPPING. Likely token-scope issue. Re-auth: python3 scripts/distribute/youtube-auth.py\n`);
        break;
      }
      console.log();
      continue;
    }

    // Self-reply (doubles comment count, looks active)
    await postReply(token, res.id, SELF_REPLY_TEMPLATES[Math.floor(Math.random() * SELF_REPLY_TEMPLATES.length)]);

    // Mark in history so re-runs skip
    reel.platforms.youtube.commented = true;
    reel.platforms.youtube.commentId = res.id;
    reel.platforms.youtube.commentedAt = new Date().toISOString();
    saveHistory(h);

    console.log(`  OK — commented + self-replied.\n`);
    posted++;
  }

  console.log(`\n${"=".repeat(60)}`);
  console.log(`  Complete.  posted: ${posted}  failed: ${failed}  skipped: ${targets.length - posted - failed}`);
  console.log(`${"=".repeat(60)}\n`);
})();
