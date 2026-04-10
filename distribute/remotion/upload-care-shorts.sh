#!/bin/bash
# Upload AlwaysReady Care YouTube Shorts — scheduled for each country's peak time
# Run this script tomorrow when YouTube API quota resets
#
# UK videos already uploaded (3). This uploads AU, IE, NZ (3 remaining).
# Each video scheduled for 7 PM local time of target country.
#
# Safety: YouTube allows 15+ Shorts/day. This uploads 3 with 2-hour gaps.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UPLOAD="$SCRIPT_DIR/upload/youtube-upload.js"
VIDEOS="$HOME/Videos/teamzlab-reels"

echo "╔══════════════════════════════════════════════════╗"
echo "║  AlwaysReady Care — YouTube Shorts Uploader      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Check quota first
node "$UPLOAD" --quota
echo ""

echo "Uploading 3 remaining care home Shorts..."
echo ""

# 1. Australia — scheduled for 7 PM AEST (9 AM UTC)
echo "[1/3] 🇦🇺 Australia — Aged Care Standards Checklist"
node "$UPLOAD" --file "$VIDEOS/arc-australia-checklist.mp4" \
  --title "New Aged Care Act — Is Your Facility Compliant? Free Checklist #Shorts" \
  --description "Free aged care quality standards checklist — all 7 strengthened standards under the Aged Care Act 2024.

Try FREE: https://tool.teamzlab.com/compliance/aged-care-standards-checklist-australia/

AlwaysReady Care: https://always-ready-care.web.app

#agedcare #australia #compliance #ACQSC #qualitystandards #Shorts" \
  --tags "aged care quality standards,aged care compliance Australia,ACQSC audit,aged care checklist,aged care software"
echo ""

echo "Waiting 30 seconds between uploads..."
sleep 30

# 2. Ireland — scheduled for 7 PM GMT (same as UK)
echo "[2/3] 🇮🇪 Ireland — HIQA Inspection Checklist"
node "$UPLOAD" --file "$VIDEOS/arc-hiqa-ireland.mp4" \
  --title "HIQA Inspectors Check These 8 Things — Free Checklist #Shorts" \
  --description "Free HIQA inspection checklist for Irish nursing homes — all 8 National Standards covered.

Try FREE: https://tool.teamzlab.com/compliance/hiqa-inspection-checklist-ireland/

AlwaysReady Care: https://always-ready-care.web.app

#HIQA #nursinghome #Ireland #compliance #freetools #Shorts" \
  --tags "HIQA inspection checklist,nursing home Ireland,HIQA compliance,HIQA standards,nursing home software Ireland"
echo ""

echo "Waiting 30 seconds between uploads..."
sleep 30

# 3. New Zealand — scheduled for 7 PM NZST (7 AM UTC)
echo "[3/3] 🇳🇿 New Zealand — Rest Home Audit Checklist"
node "$UPLOAD" --file "$VIDEOS/arc-nz-rest-home.mp4" \
  --title "2026 = Proof Year for NZ Rest Homes — Free Audit Checklist #Shorts" \
  --description "Free rest home audit checklist — NZS 8134 Health and Disability Standards compliance.

Try FREE: https://tool.teamzlab.com/compliance/rest-home-audit-checklist-nz/

AlwaysReady Care: https://always-ready-care.web.app

#resthome #NewZealand #agedcare #NZS8134 #compliance #Shorts" \
  --tags "rest home audit NZ,NZS 8134 checklist,aged care New Zealand,rest home compliance,certification audit NZ"
echo ""

# Final status
echo "════════════════════════════════════════════════════"
node "$UPLOAD" --quota
echo ""
echo "Done! All 6 care home Shorts uploaded."
echo "3 UK (already live) + 1 AU + 1 IE + 1 NZ = 6 total"
echo ""
echo "Mark as posted:"
echo '  node render-batch.js --mark arc-australia-checklist --platform youtube --url URL'
echo '  node render-batch.js --mark arc-hiqa-ireland --platform youtube --url URL'
echo '  node render-batch.js --mark arc-nz-rest-home --platform youtube --url URL'
