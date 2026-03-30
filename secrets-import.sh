#!/usr/bin/env bash
# ─── Teamz Lab Tools — Secrets Import ─────────────────────────────
# Restores ALL API keys, tokens, and configs from an encrypted backup.
# Created by secrets-export.sh on another machine.
#
# Usage:
#   ./scripts/secrets-import.sh teamzlab-secrets.gpg
#   ./scripts/secrets-import.sh /path/to/backup.gpg
#
# What it restores:
#   ~/.config/teamzlab/*          — Google APIs, Product Hunt, PageSpeed
#   scripts/distribute/config.json — Dev.to, Hashnode, Blogger, etc.
# ──────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$HOME/.config/teamzlab"
INPUT="${1:-$PROJECT_DIR/teamzlab-secrets.gpg}"

if [ ! -f "$INPUT" ]; then
    echo ""
    echo "  ERROR: Backup file not found: $INPUT"
    echo ""
    echo "  Usage: ./scripts/secrets-import.sh teamzlab-secrets.gpg"
    echo ""
    echo "  To create a backup on your current machine first:"
    echo "    ./scripts/secrets-export.sh"
    exit 1
fi

echo ""
echo "============================================================"
echo "  TEAMZ LAB — SECRETS IMPORT"
echo "============================================================"
echo ""
echo "  Restoring from: $INPUT"
echo ""

TMP_DIR=$(mktemp -d)

# Support --password flag for non-interactive use
PASSWORD=""
for i in "$@"; do
    case "$i" in
        --password=*) PASSWORD="${i#*=}" ;;
    esac
done

# Decrypt
if [ -n "$PASSWORD" ]; then
    gpg --decrypt --batch --passphrase "$PASSWORD" --pinentry-mode loopback -o - "$INPUT" | tar -xzf - -C "$TMP_DIR"
else
    export GPG_TTY=$(tty)
    gpg --decrypt -o - "$INPUT" | tar -xzf - -C "$TMP_DIR"
fi

# Show manifest
if [ -f "$TMP_DIR/MANIFEST.txt" ]; then
    echo "  Backup info:"
    sed 's/^/    /' "$TMP_DIR/MANIFEST.txt"
    echo ""
fi

COUNT=0

# 1. Restore ~/.config/teamzlab/
if [ -d "$TMP_DIR/config-teamzlab" ]; then
    mkdir -p "$CONFIG_DIR"
    for f in "$TMP_DIR/config-teamzlab"/*; do
        if [ -f "$f" ]; then
            BASENAME=$(basename "$f")
            if [ -f "$CONFIG_DIR/$BASENAME" ]; then
                echo "  ~ config/teamzlab/$BASENAME (overwriting existing)"
            else
                echo "  + config/teamzlab/$BASENAME"
            fi
            cp "$f" "$CONFIG_DIR/$BASENAME"
            COUNT=$((COUNT + 1))
        fi
    done
fi

# 2. Restore distribute config
if [ -f "$TMP_DIR/distribute/config.json" ]; then
    DEST="$SCRIPT_DIR/distribute/config.json"
    if [ -f "$DEST" ]; then
        echo "  ~ distribute/config.json (overwriting existing)"
    else
        echo "  + distribute/config.json"
    fi
    cp "$TMP_DIR/distribute/config.json" "$DEST"
    COUNT=$((COUNT + 1))
fi

# 3. Restore gcloud credentials
if [ -d "$TMP_DIR/gcloud" ]; then
    for f in "$TMP_DIR/gcloud"/*; do
        if [ -f "$f" ]; then
            BASENAME=$(basename "$f")
            # Try to put it where it came from
            if [ "$BASENAME" = "application_default_credentials.json" ]; then
                mkdir -p "$HOME/.config/gcloud"
                cp "$f" "$HOME/.config/gcloud/$BASENAME"
                echo "  + gcloud/$BASENAME"
            else
                cp "$f" "$PROJECT_DIR/$BASENAME"
                echo "  + $BASENAME (project root)"
            fi
            COUNT=$((COUNT + 1))
        fi
    done
fi

# Cleanup
rm -rf "$TMP_DIR"

echo ""
echo "  Restored $COUNT file(s)"
echo ""

# Verify
echo "  Verification:"
[ -d "$CONFIG_DIR" ] && echo "    ~/.config/teamzlab/ — $(ls "$CONFIG_DIR" | wc -l | tr -d ' ') files" || echo "    ~/.config/teamzlab/ — MISSING"
[ -f "$SCRIPT_DIR/distribute/config.json" ] && echo "    distribute/config.json — OK" || echo "    distribute/config.json — MISSING"

echo ""
echo "  Quick test commands:"
echo "    ./build-search-console.sh --status     # Google Search Console"
echo "    ./build-seo-audit.sh --ph-trending     # Product Hunt"
echo "    python3 scripts/distribute/distribute.py test  # Distribution APIs"
echo ""
echo "============================================================"
