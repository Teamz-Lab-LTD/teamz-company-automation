#!/usr/bin/env node
/**
 * TikTok OAuth — opens browser, catches redirect, saves token.
 * Same pattern as youtube-auth.py but for TikTok Content Posting API.
 *
 * Prerequisites:
 *   ~/.config/teamzlab/tiktok-config.json with client_key, client_secret, redirect_uri
 *
 * Usage:
 *   node upload/tiktok-auth.js          # Authorize (opens browser)
 *   node upload/tiktok-auth.js --test   # Test connection
 */

const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execSync } = require("child_process");
const url = require("url");

// PKCE — TikTok v2 OAuth requires this. Note: TikTok uses HEX, not base64url.
const codeVerifier = crypto.randomBytes(32).toString("hex");
const codeChallenge = crypto.createHash("sha256").update(codeVerifier).digest("hex");

const CONFIG_DIR = path.join(require("os").homedir(), ".config", "teamzlab");
const CONFIG_FILE = path.join(CONFIG_DIR, "tiktok-config.json");
const TOKEN_FILE = path.join(CONFIG_DIR, "tiktok-token.json");
const PORT = 8889;

const args = process.argv.slice(2);

if (!fs.existsSync(CONFIG_FILE)) {
  console.log(`\nCreate config first: ${CONFIG_FILE}\n`);
  console.log(`{`);
  console.log(`  "client_key": "YOUR_CLIENT_KEY",`);
  console.log(`  "client_secret": "YOUR_CLIENT_SECRET",`);
  console.log(`  "redirect_uri": "http://localhost:${PORT}"`);
  console.log(`}\n`);
  console.log(`Get keys from: https://developers.tiktok.com/\n`);
  process.exit(1);
}

const config = JSON.parse(fs.readFileSync(CONFIG_FILE, "utf-8"));

if (args.includes("--test")) {
  if (!fs.existsSync(TOKEN_FILE)) {
    console.log("No token. Run: node upload/tiktok-auth.js");
    process.exit(1);
  }
  const tokens = JSON.parse(fs.readFileSync(TOKEN_FILE, "utf-8"));
  console.log("TikTok token found:");
  console.log(`  Open ID: ${tokens.open_id || "?"}`);
  console.log(`  Expires: ${new Date((tokens.expires_at || 0) * 1000).toISOString()}`);
  console.log(`  Scopes: ${tokens.scope || "?"}`);
  process.exit(0);
}

// Build auth URL
const scopes = "user.info.basic,video.upload,video.publish";
const authUrl = `https://www.tiktok.com/v2/auth/authorize/?client_key=${config.client_key}&scope=${scopes}&response_type=code&redirect_uri=${encodeURIComponent(config.redirect_uri)}&state=teamzlab&code_challenge=${codeChallenge}&code_challenge_method=S256`;

console.log("Opening browser for TikTok authorization...\n");

// Start local server to catch redirect
const server = http.createServer(async (req, res) => {
  const parsed = url.parse(req.url, true);
  const code = parsed.query.code;

  if (!code) {
    res.writeHead(400);
    res.end("No authorization code received");
    return;
  }

  // Exchange code for token
  const postData = `client_key=${config.client_key}&client_secret=${config.client_secret}&code=${code}&grant_type=authorization_code&redirect_uri=${encodeURIComponent(config.redirect_uri)}&code_verifier=${codeVerifier}`;

  try {
    const tokenData = await new Promise((resolve, reject) => {
      const tokenReq = https.request({
        hostname: "open.tiktokapis.com",
        path: "/v2/oauth/token/",
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded", "Content-Length": Buffer.byteLength(postData) },
      }, (tokenRes) => {
        let data = "";
        tokenRes.on("data", (c) => data += c);
        tokenRes.on("end", () => resolve(JSON.parse(data)));
      });
      tokenReq.on("error", reject);
      tokenReq.write(postData);
      tokenReq.end();
    });

    if (tokenData.access_token) {
      // Add expires_at for easy checking
      tokenData.expires_at = Math.floor(Date.now() / 1000) + (tokenData.expires_in || 86400);
      fs.writeFileSync(TOKEN_FILE, JSON.stringify(tokenData, null, 2));
      console.log("TikTok connected!");
      console.log(`  Open ID: ${tokenData.open_id}`);
      console.log(`  Token saved to ${TOKEN_FILE}`);

      res.writeHead(200, { "Content-Type": "text/html" });
      res.end("<html><body><h1>TikTok Connected!</h1><p>You can close this tab.</p></body></html>");
    } else {
      console.error("Token exchange failed:", JSON.stringify(tokenData));
      res.writeHead(400);
      res.end("Token exchange failed");
    }
  } catch (e) {
    console.error("Error:", e.message);
    res.writeHead(500);
    res.end("Error exchanging token");
  }

  server.close();
});

server.listen(PORT, () => {
  // Open browser
  try { execSync(`open "${authUrl}"`); } catch (e) {
    console.log(`Open this URL manually:\n${authUrl}\n`);
  }
});

// Timeout after 2 minutes
setTimeout(() => { console.log("\nTimeout — no authorization received."); server.close(); process.exit(1); }, 120000);
