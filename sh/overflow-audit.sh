#!/usr/bin/env bash
#
# overflow-audit.sh — catch small-device layout overflow before it ships.
#
# Modals built and reviewed on a Pixel-class phone silently break on an
# iPhone SE (320 dp wide) or under large accessibility font scaling — the
# "RenderFlex overflowed by N pixels" stripe, or content clipped by the
# bottom-sheet height cap.
#
# Run it from the APP ROOT (same as aso-discovery.sh):
#   bash team_mvp_kit/teamz-company-automation/sh/overflow-audit.sh
#
# This is a thin convenience wrapper. The actual checks live in
# test/overflow/ as ordinary Dart tests, so they ALSO run under plain
# `flutter test`, under `run_all_tests.sh` (category: overflow), and in
# CI — this script is just the LLM/human-facing entry point that adds
# fix guidance on failure.
#
# test/overflow/ contains two halves:
#   - modal_wiring_test.dart  — static: every showModalBottomSheet must
#     set `isScrollControlled: true` (kit ModalAudit scans lib/).
#   - sheet_overflow_test.dart — runtime: each sheet/dialog is pumped at
#     iPhone SE / small-phone sizes × large font scale; fails on real
#     overflow (kit ResponsiveAudit).
#
# Exit code is non-zero on any failure, so it works as a release gate.

set -uo pipefail

# ---- resolve flutter command (prefer FVM) ----------------------------------
if command -v fvm >/dev/null 2>&1 && [ -f ".fvmrc" ]; then
  FLUTTER="fvm flutter"
else
  FLUTTER="flutter"
fi

BOLD=$'\033[1m'; RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'

echo "${BOLD}=== overflow-audit ===${RESET}"
echo "app root: $(pwd)"
echo

if [ ! -d test/overflow ]; then
  echo "${YELLOW}skip${RESET}  no test/overflow/ directory."
  echo "      create test/overflow/ with:"
  echo "        - modal_wiring_test.dart   (kit ModalAudit static scan)"
  echo "        - sheet_overflow_test.dart (kit ResponsiveAudit runtime pump)"
  exit 0
fi

echo "${BOLD}running test/overflow/ — static modal-wiring + runtime overflow${RESET}"
echo

if $FLUTTER test test/overflow/; then
  echo
  echo "${GREEN}${BOLD}PASS${RESET} — no overflow risks found."
  exit 0
fi

# ---- failure guidance (LLM- and human-readable) ----------------------------
echo
echo "${RED}${BOLD}FAIL${RESET} — overflow issue(s) found above."
echo
echo "${BOLD}How to fix:${RESET}"
echo "  'showModalBottomSheet missing isScrollControlled' (modal_wiring_test):"
echo "   1. Set isScrollControlled: true in the showModalBottomSheet(...) call."
echo "   2. Wrap the builder's content in kit SafeBottomSheet:"
echo "        import 'package:team_mvp_kit/team_mvp_kit.dart' as kit;"
echo "        builder: (_) => kit.SafeBottomSheet(child: <your content>),"
echo
echo "  'Overflow on surface ... at textScale ...' (sheet_overflow_test):"
echo "   - Bottom sheet: wrap its content widget in kit SafeBottomSheet."
echo "   - Custom Dialog: wrap the child in MediaQuery(textScaler clamped"
echo "     to 1.3) > ConstrainedBox(maxHeight) > SingleChildScrollView."
echo "   - AlertDialog: add 'scrollable: true'."
echo "   - Button rows: wrap labels in Expanded/Flexible + FittedBox(scaleDown),"
echo "     or stack vertically when MediaQuery width < 360."
echo
echo "  After fixing, add the new surface to test/overflow/sheet_overflow_test.dart,"
echo "  then re-run this script."
exit 1
