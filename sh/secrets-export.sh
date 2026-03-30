#!/usr/bin/env bash
# ─── Teamz Lab Tools — Secrets Export ─────────────────────────────
# Packs ALL API keys, tokens, and configs into one encrypted file.
# Use secrets-import.sh on a new machine to restore everything.
#
# Usage:
#   ./scripts/secrets-export.sh                    # Creates teamzlab-secrets.gpg
#   ./scripts/secrets-export.sh my-backup.gpg      # Custom output name
# ──────────────────────────────────────────────────────────────────

set -e

_RES="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$_RES")" && pwd)"
# sh/ → teamz-company-automation/ → parent = teamzlab-tools (submodule)
AUTOMATION_ROOT="$(dirname "$SCRIPT_DIR")"
HOST_SITE_ROOT="$(dirname "$AUTOMATION_ROOT")"
CONFIG_DIR="$HOME/.config/teamzlab"
DIST_CONFIG="$AUTOMATION_ROOT/distribute/config.json"
OUTPUT="${1:-$HOST_SITE_ROOT/teamzlab-secrets.gpg}"
TMP_DIR=$(mktemp -d)

echo ""
echo "============================================================"
echo "  TEAMZ LAB — SECRETS EXPORT"
echo "============================================================"
echo ""

# Collect all secret files
COUNT=0

# 1. ~/.config/teamzlab/ (all files)
if [ -d "$CONFIG_DIR" ]; then
    mkdir -p "$TMP_DIR/config-teamzlab"
    for f in "$CONFIG_DIR"/*; do
        if [ -f "$f" ]; then
            cp "$f" "$TMP_DIR/config-teamzlab/"
            echo "  + config/teamzlab/$(basename "$f")"
            COUNT=$((COUNT + 1))
        fi
    done
fi

# 2. Distribution config (API keys for 7 platforms)
if [ -f "$DIST_CONFIG" ]; then
    mkdir -p "$TMP_DIR/distribute"
    cp "$DIST_CONFIG" "$TMP_DIR/distribute/config.json"
    echo "  + distribute/config.json (7 platform API keys)"
    COUNT=$((COUNT + 1))
fi

# 3. Google Cloud service account (if exists)
for sa in "$HOME/.config/gcloud/application_default_credentials.json" \
          "$HOST_SITE_ROOT/service-account.json" \
          "$HOST_SITE_ROOT/scripts/service-account.json" \
          "$AUTOMATION_ROOT/service-account.json"; do
    if [ -f "$sa" ]; then
        mkdir -p "$TMP_DIR/gcloud"
        cp "$sa" "$TMP_DIR/gcloud/$(basename "$sa")"
        echo "  + gcloud/$(basename "$sa")"
        COUNT=$((COUNT + 1))
    fi
done

if [ "$COUNT" -eq 0 ]; then
    echo "  No secrets found to export."
    rm -rf "$TMP_DIR"
    exit 1
fi

echo ""
echo "  Found $COUNT secret file(s)"
echo ""

# Create manifest
cat > "$TMP_DIR/MANIFEST.txt" << EOF
Teamz Lab Tools — Secrets Backup
Created: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
Machine: $(hostname)
Files: $COUNT

To restore: ./scripts/secrets-import.sh teamzlab-secrets.gpg
EOF

# Encrypt with GPG (symmetric, password-only)
# Support --password flag for non-interactive use, otherwise prompt
PASSWORD=""
for i in "$@"; do
    case "$i" in
        --password=*) PASSWORD="${i#*=}" ;;
    esac
done

if [ -n "$PASSWORD" ]; then
    tar -czf - -C "$TMP_DIR" . | gpg --symmetric --cipher-algo AES256 --batch --yes --passphrase "$PASSWORD" --pinentry-mode loopback -o "$OUTPUT"
else
    echo "  Enter a password to encrypt your secrets:"
    echo "  (You'll need this password on the new machine)"
    echo ""
    export GPG_TTY=$(tty)
    tar -czf - -C "$TMP_DIR" . | gpg --symmetric --cipher-algo AES256 -o "$OUTPUT"
fi

# Cleanup
rm -rf "$TMP_DIR"

echo ""
echo "  Encrypted backup saved to: $OUTPUT"
echo "  Size: $(du -h "$OUTPUT" | cut -f1)"
echo ""
echo "  To restore on a new machine:"
echo "    1. Copy $OUTPUT to the new machine"
echo "    2. Run: ./scripts/secrets-import.sh $(basename "$OUTPUT")"
echo ""
echo "  IMPORTANT: Do NOT commit this file to git!"
echo "  It's already in .gitignore."
echo ""
echo "============================================================"
