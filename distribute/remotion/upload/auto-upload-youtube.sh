#!/bin/bash
# Auto-upload YouTube Shorts — runs via cron daily
# Uploads up to 6 unposted videos, auto-schedules publish times
# Stops gracefully when nothing left to upload

REMOTION_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REMOTION_DIR" || exit 1

# Check if there are unposted videos
UNPOSTED=$(node -e "
const h = JSON.parse(require('fs').readFileSync('reel-history.json','utf8'));
const n = h.reels.filter(r => !r.youtube).length;
console.log(n);
" 2>/dev/null)

if [ "$UNPOSTED" = "0" ] || [ -z "$UNPOSTED" ]; then
  echo "[$(date)] No unposted videos. Nothing to do."
  exit 0
fi

echo "[$(date)] $UNPOSTED unposted videos. Uploading up to 6..."
node upload/youtube-upload.js --from-history --count 6 2>&1

echo "[$(date)] Done."
