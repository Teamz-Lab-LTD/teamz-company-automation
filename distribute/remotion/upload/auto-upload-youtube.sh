#!/bin/bash
# Auto-upload YouTube Shorts — runs via cron daily
# Uploads up to 6 unposted videos, auto-schedules publish times
# Stops gracefully when nothing left to upload
#
# FIXED 2026-08-08 — two silent bugs that made this a 98-day no-op:
#   1. bare `node` resolves under an interactive shell's PATH but cron runs
#      with PATH=/usr/bin:/bin — node lives at /opt/homebrew/bin/node and was
#      never found, so $UNPOSTED came back "" (empty), which the guard below
#      treated identically to "genuinely zero" and exited 0 silently.
#   2. the schema check read `r.youtube`, which has never existed on a reel
#      object — the real field is `r.platforms.youtube.posted` (verified via
#      reel-history.json). Bare `r.youtube` is always undefined, so if node
#      COULD run, every reel — including the 45 already-posted ones — read as
#      unposted, which would have re-uploaded the entire history.
# Both bugs happened to cancel out into "nothing happens," which is why 22
# straight days of /tmp/yt-auto-upload.log looked identical and nobody caught it.

NODE_BIN="$(command -v node || echo /opt/homebrew/bin/node)"
REMOTION_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REMOTION_DIR" || exit 1

# Check if there are unposted videos
UNPOSTED=$("$NODE_BIN" -e "
const h = JSON.parse(require('fs').readFileSync('reel-history.json','utf8'));
const n = h.reels.filter(r => !(r.platforms && r.platforms.youtube && r.platforms.youtube.posted)).length;
console.log(n);
" 2>/dev/null)

if [ "$UNPOSTED" = "0" ] || [ -z "$UNPOSTED" ]; then
  echo "[$(date)] No unposted videos. Nothing to do."
  exit 0
fi

echo "[$(date)] $UNPOSTED unposted videos. Uploading up to 6..."
"$NODE_BIN" upload/youtube-upload.js --from-history --count 6 2>&1

echo "[$(date)] Done."
