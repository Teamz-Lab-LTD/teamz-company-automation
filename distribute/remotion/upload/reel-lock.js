/**
 * Cross-process advisory lock for reel-history.json.
 *
 * WHY THIS EXISTS. youtube-upload.js, tiktok-upload.js, and comment-catchup.js
 * each load reel-history.json into memory ONCE at start, mutate that in-memory
 * copy across a loop, and call saveHistory(h) after every item — a full
 * JSON.stringify(h) overwrite of the file, not a merge. Two of these
 * processes running concurrently (verified live, 2026-08-08: a manual
 * youtube-upload.js run + comment-catchup.js --go running in parallel) means
 * whichever one saves LAST wins — the other's writes, including brand new
 * "posted": true entries for videos that had genuinely already uploaded to
 * YouTube, silently vanish from the file. Six real uploads were lost this way
 * before this lock existed; they had to be hand-reconciled against YouTube's
 * own API afterward.
 *
 * This does NOT fix the underlying overwrite-not-merge design — that would
 * mean restructuring the read/mutate/save loop in three files. It prevents
 * the race the cheap way: only one of these processes may run at a time.
 * They were never designed to run concurrently anyway (cron fires them
 * sequentially), so serializing is a correctness fix, not a feature loss.
 *
 * Usage:
 *   const { withLock } = require('./reel-lock');
 *   withLock(async () => { ...your existing main logic... });
 */
const fs = require('fs');
const path = require('path');

const LOCK_DIR = path.join(__dirname, '.reel-history.lock');
const STALE_MS = 30 * 60 * 1000; // 30 min — long enough for a real render/upload run,
                                  // short enough that a crashed process doesn't wedge things forever

function tryAcquire() {
  try {
    fs.mkdirSync(LOCK_DIR); // atomic on POSIX — fails with EEXIST if already held
    fs.writeFileSync(path.join(LOCK_DIR, 'pid'), String(process.pid));
    return true;
  } catch (e) {
    if (e.code !== 'EEXIST') throw e;
    return false;
  }
}

function lockAge() {
  try {
    return Date.now() - fs.statSync(LOCK_DIR).mtimeMs;
  } catch {
    return Infinity;
  }
}

async function withLock(fn, { label = path.basename(process.argv[1] || 'script'), maxWaitMs = 20 * 60 * 1000 } = {}) {
  const start = Date.now();
  while (!tryAcquire()) {
    if (lockAge() > STALE_MS) {
      console.log(`[reel-lock] Stale lock (>${STALE_MS / 60000}min old) — assuming a crashed process, taking over.`);
      try { fs.rmSync(LOCK_DIR, { recursive: true, force: true }); } catch {}
      continue;
    }
    if (Date.now() - start > maxWaitMs) {
      console.log(`[reel-lock] Another reel-history writer has held the lock for ${maxWaitMs / 60000}+ min. ` +
                   `Exiting rather than racing it — run again later.`);
      process.exit(0);
    }
    console.log(`[reel-lock] ${label} waiting — another reel-history writer is running...`);
    await new Promise((r) => setTimeout(r, 5000));
  }
  const release = () => { try { fs.rmSync(LOCK_DIR, { recursive: true, force: true }); } catch {} };
  process.on('exit', release);
  process.on('SIGINT', () => { release(); process.exit(1); });
  process.on('SIGTERM', () => { release(); process.exit(1); });
  try {
    return await fn();
  } finally {
    release();
  }
}

module.exports = { withLock };
