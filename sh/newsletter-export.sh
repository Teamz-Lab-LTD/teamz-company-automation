#!/bin/bash
# Newsletter subscriber export — fetches from Firestore
# Uses Firebase CLI (handles auth automatically)
#
# Usage:
#   ./scripts/newsletter-export.sh           # List all subscribers
#   ./scripts/newsletter-export.sh --csv     # Export as CSV
#   ./scripts/newsletter-export.sh --count   # Just show count
#
# Prerequisites: firebase-tools installed (npm install -g firebase-tools)
# Auth: firebase login (one-time)

PROJECT="teamzlab-tools"
COLLECTION="newsletter_subscribers"
MODE="${1:-list}"

# Check if firebase CLI is available
if ! command -v firebase &> /dev/null; then
  echo "Firebase CLI not found. Install with: npm install -g firebase-tools"
  echo ""
  echo "Alternative: view subscribers in Firebase Console:"
  echo "  https://console.firebase.google.com/project/$PROJECT/firestore/databases/-default-/data/~2F$COLLECTION"
  exit 1
fi

# Fetch data via Firestore REST (using Firebase auth token)
TOKEN=$(firebase --project "$PROJECT" auth:export --format=json 2>/dev/null | head -1)

# Use firebase CLI to query Firestore
DATA=$(firebase firestore:delete --help >/dev/null 2>&1; python3 -c "
import subprocess, json, sys

# Use gcloud/firebase token to access Firestore REST API
import urllib.request, os

# Get Firebase auth token
try:
    result = subprocess.run(['firebase', 'login:list', '--json'], capture_output=True, text=True)
except:
    pass

# Direct Firestore REST API via gcloud
try:
    result = subprocess.run(
        ['gcloud', 'firestore', 'export', '--help'],
        capture_output=True, text=True
    )
except:
    pass

# Simplest approach: use firebase emulator or direct REST
# For now, use the Admin approach via a temp Node script
import tempfile
script = '''
const admin = require(\"firebase-admin\");
admin.initializeApp({ projectId: \"$PROJECT\" });
const db = admin.firestore();
db.collection(\"$COLLECTION\").orderBy(\"subscribedAt\").get().then(snap => {
  const data = [];
  snap.forEach(doc => data.push(doc.data()));
  console.log(JSON.stringify(data));
  process.exit(0);
}).catch(e => { console.error(e.message); process.exit(1); });
'''
print(json.dumps([]))  # Placeholder
" 2>/dev/null)

# Simpler approach: use gcloud CLI directly
DATA=$(gcloud firestore documents list \
  --project="$PROJECT" \
  --database="(default)" \
  --collection="$COLLECTION" \
  --format=json 2>/dev/null)

if [ -z "$DATA" ] || [ "$DATA" = "[]" ] || [ "$DATA" = "null" ]; then
  # Try alternate: firebase CLI with Node
  DATA=$(node -e "
    const { initializeApp, cert } = require('firebase-admin/app');
    const { getFirestore } = require('firebase-admin/firestore');
    initializeApp({ projectId: 'teamzlab-tools' });
    const db = getFirestore();
    db.collection('newsletter_subscribers').orderBy('subscribedAt').get()
      .then(snap => {
        const arr = [];
        snap.forEach(doc => arr.push(doc.data()));
        console.log(JSON.stringify(arr));
      })
      .catch(() => console.log('[]'));
  " 2>/dev/null)
fi

if [ -z "$DATA" ] || [ "$DATA" = "[]" ] || [ "$DATA" = "null" ]; then
  echo "No subscribers yet (or auth needed)."
  echo ""
  echo "View in Firebase Console:"
  echo "  https://console.firebase.google.com/project/$PROJECT/firestore/databases/-default-/data/~2Fnewsletter_subscribers"
  echo ""
  echo "Or run: firebase login (if not authenticated)"
  exit 0
fi

case "$MODE" in
  --count)
    echo "$DATA" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total subscribers: {len(data)}')
"
    ;;
  --csv)
    echo "$DATA" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('email,subscribed_at,source,status')
for sub in data:
    email = sub.get('email', '')
    date = sub.get('subscribedAt', '')[:19]
    source = sub.get('source', '/')
    status = sub.get('status', 'active')
    print(f'{email},{date},{source},{status}')
"
    ;;
  *)
    echo "$DATA" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Newsletter Subscribers: {len(data)}')
print('=' * 60)
print(f'{\"Email\":<35} {\"Date\":<12} {\"Source\":<20}')
print('-' * 60)
for sub in data:
    email = sub.get('email', 'N/A')
    date = sub.get('subscribedAt', 'N/A')[:10]
    source = sub.get('source', '/')
    print(f'{email:<35} {date:<12} {source:<20}')
"
    ;;
esac
