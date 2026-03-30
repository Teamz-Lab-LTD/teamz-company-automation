#!/bin/bash
# Quick runner — triggers the full nightly build pipeline NOW with Sonnet
# Usage: bash scripts/run-build-now.sh

_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
_SCRIPT_DIR="$(cd "$(dirname "$_SCRIPT")" && pwd)"
# shellcheck disable=SC1091
source "$_SCRIPT_DIR/lib/config.sh"
teamz_load_config "$_SCRIPT"
cd "$TEAMZ_HOST_SITE_ROOT"

export MODEL="sonnet"
echo "Starting build with Sonnet model..."
echo "This will: research keywords → build 5-8 tools → QA → commit → push"
echo "Check logs/nightly-build.log for progress"
echo ""

bash "$_SCRIPT_DIR/nightly-build.sh" 2>&1 | tee logs/nightly-build-manual.log

echo ""
echo "Done! Check logs/nightly-build-manual.log for full output"
