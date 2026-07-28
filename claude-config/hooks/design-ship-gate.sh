#!/bin/bash
# PostToolUse hook on Write|Edit — scans a Flutter UI file that was just written and
# reports design-system violations back into the conversation.
#
# This is a LINTER, not a reminder. Every rule below corresponds to a defect that
# actually shipped or nearly shipped in a Teamz Lab app; the rationale for each lives
# in claude-config/design/DESIGN-SHIP-GATE.md.
#
# It never blocks. Blocking every UI edit would be unusable, and the point is that the
# rules are IN FRONT OF the model while it writes screens rather than in a document
# nobody opens. Findings are advisory context; the model decides.
#
# Wired by setup-symlinks.sh into ~/.claude/hooks/. Register in settings.json as a
# PostToolUse hook matching Write and Edit.

set -e

input="$(cat)"

path="$(python3 -c "
import json, sys
try:
    d = json.loads(sys.argv[1])
    tn = d.get('tool_name', d.get('toolName', ''))
    if tn not in ('Write', 'Edit', 'MultiEdit'):
        sys.exit(0)
    ti = d.get('tool_input', d.get('toolInput', {}))
    print(ti.get('file_path', ''))
except Exception:
    pass
" "$input" 2>/dev/null)"

[ -z "$path" ] && exit 0
[ -f "$path" ] || exit 0

# Dart only, and only UI code. Design systems and theme files legitimately hold raw
# colour literals — they are where the tokens are DEFINED.
case "$path" in
  *.dart) ;;
  *) exit 0 ;;
esac
case "$path" in
  */theme/*|*design_system*|*_test.dart|*.g.dart|*.freezed.dart|*/l10n/*) exit 0 ;;
esac
case "$path" in
  */features/*|*/common_ui/*|*/widgets/*|*/presentation/*|*/ui/*) ;;
  *) exit 0 ;;
esac

# The scanner writes to a temp file rather than into $(...). A quoted heredoc nested
# inside a command substitution is parsed inconsistently by bash — it choked on an
# ordinary double quote inside the Python source.
_gate_out="$(mktemp -t design-gate)"
trap 'rm -f "$_gate_out"' EXIT

python3 - "$path" > "$_gate_out" <<'PY'
import re, sys

path = sys.argv[1]
try:
    src = open(path, encoding='utf-8').read()
except Exception:
    sys.exit(0)

lines = src.split('\n')
out = []

def add(i, rule, msg):
    out.append(f"  L{i+1}  [{rule}] {msg}")

# 1) borderRadius together with a non-uniform Border(...) — throws during PAINT.
#    Flutter: "a borderRadius can only be given on borders with uniform colors".
for m in re.finditer(r'BoxDecoration\s*\(', src):
    start = m.end()
    depth, i = 1, start
    while i < len(src) and depth:
        if src[i] == '(': depth += 1
        elif src[i] == ')': depth -= 1
        i += 1
    block = src[start:i]
    if 'borderRadius' in block and re.search(r'\bBorder\s*\(', block):
        add(src[:m.start()].count('\n'), 'border-radius-uniform',
            'borderRadius with a non-uniform Border(...) throws during paint. '
            'Draw the accent as a child widget, not as a thick BorderSide.')

for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('//') or stripped.startswith('///'):
        continue

    # 2) Raw colour literals outside the theme layer.
    if re.search(r'\bColor\(0x[0-9a-fA-F]{6,8}\)', line):
        add(i, 'raw-color',
            'a raw Color(0x..) cannot follow the theme — right in one mode, wrong in the '
            'other. Use a design-system token.')

    # 3) The classic contrast failure.
    if re.search(r'color:\s*Colors\.(white|black)\b', line):
        add(i, 'contrast-pair',
            'Colors.white/black as a foreground. Take the paired on* token of the '
            'background instead, and check light AND dark.')

    # 4) Motion tokens bypassed — ignores the OS reduce-motion flag.
    if re.search(r'Duration\(\s*milliseconds:\s*\d+', line) and 'Motion' not in line:
        add(i, 'motion-token',
            'hardcoded Duration bypasses the motion tokens, so it ignores reduce-motion. '
            'Use Motion.of(context).')

    # 5) Animating layout properties.
    if 'AnimatedContainer' in line:
        add(i, 'animate-transform',
            'AnimatedContainer usually animates width/height — that re-runs layout every '
            'frame. Prefer transform/opacity (AnimatedSlide, AnimatedScale, AnimatedOpacity).')

    # 6) Emoji standing in for an icon.
    if re.search(r"Text\(\s*'[^']*[\U0001F300-\U0001FAFF☀-➿]", line):
        add(i, 'no-emoji-icons', 'emoji used as an icon. Use an SVG/Icon widget.')

if out:
    print('\n'.join(out[:12]))
    if len(out) > 12:
        print(f"  … and {len(out) - 12} more")
PY

[ -s "$_gate_out" ] || exit 0

GATE_FINDINGS="$(cat "$_gate_out")" python3 <<'PY'
import json, os

msg = (
    'DESIGN SHIP GATE - automatic checks on the file just written:\n\n'
    + os.environ.get('GATE_FINDINGS', '')
    + '\n\nEach rule maps to a defect that already shipped once; see '
      'claude-config/design/DESIGN-SHIP-GATE.md for the story behind each. '
      'Fix them now, or say explicitly why the rule does not apply here - do not '
      'leave them silently. The manual half of the gate (contrast measured in BOTH '
      'themes, touch targets, reduce-motion tested, every on-screen claim true of '
      'the code path) is section B of that file and still needs eyes.'
)

print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PostToolUse',
        'additionalContext': msg,
    }
}))
PY

exit 0
