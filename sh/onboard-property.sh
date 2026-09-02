#!/bin/bash
# ============================================================
# Onboard a new Teamz Lab property into the nightly engine.
#
#   bash teamz-company-automation/sh/onboard-property.sh \
#        <repo-dir> <gsc-property> <launchd-label> [hour]
#
# Example:
#   bash .../onboard-property.sh shop-bd https://shop.teamzlab.com/ \
#        com.teamzlab.shop-nightly 22
#
# DRY RUN BY DEFAULT. Nothing is written until you add --apply.
#
# Why this exists: tekko-bd was the sixth property, and every step below was
# done by hand — including the plist, which was copied from a sibling and edited
# in a text editor. Six hand steps is six chances to typo a path that then fails
# silently at 22:00. The registry itself is small (one row in one file), so the
# work is not complex, only fiddly and easy to get subtly wrong.
# ============================================================
set -e

SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
AUTOMATION="$(cd "$(dirname "$SCRIPT")/.." && pwd)"
PROJECTS="$(cd "$AUTOMATION/.." && pwd)"
DIGEST="$AUTOMATION/py/build-growth-digest.py"

APPLY=false
ARGS=()
for a in "$@"; do
  case "$a" in
    --apply) APPLY=true ;;
    *) ARGS+=("$a") ;;
  esac
done
set -- "${ARGS[@]}"

REPO="$1"; SITE="$2"; LABEL="$3"; HOUR="${4:-22}"
if [ -z "$REPO" ] || [ -z "$SITE" ] || [ -z "$LABEL" ]; then
  echo "usage: onboard-property.sh <repo-dir> <gsc-property> <launchd-label> [hour] [--apply]"
  echo "   eg: onboard-property.sh shop-bd https://shop.teamzlab.com/ com.teamzlab.shop-nightly 22"
  exit 1
fi

ROOT="$PROJECTS/$REPO"
say() { if $APPLY; then echo "  $1"; else echo "  [dry-run] $1"; fi; }

# ---- 0. refuse anything that is not a real project ----------------------
[ -d "$ROOT" ]      || { echo "ERROR: $ROOT does not exist. Clone or create the repo first."; exit 1; }
[ -e "$ROOT/.git" ] || { echo "ERROR: $ROOT is not a git repo."; exit 1; }
case "$LABEL" in com.teamzlab.*) ;; *) echo "ERROR: label must start with com.teamzlab."; exit 1 ;; esac

echo ""
echo "============================================================"
echo "  ONBOARD  $REPO  ->  $SITE"
echo "  label $LABEL, nightly at ${HOUR}:00"
$APPLY || echo "  DRY RUN — nothing will be written. Re-run with --apply."
echo "============================================================"

# ---- 1. shared toolkit + the git-exclude block --------------------------
# setup-symlinks.sh also writes .git/info/exclude, so the links it creates
# cannot make the dirty guard skip this property's very first night.
if $APPLY; then
  ( cd "$ROOT" && bash "$AUTOMATION/setup-symlinks.sh" >/dev/null 2>&1 ) \
    && echo "  linked shared scripts + wrote .git/info/exclude"
else
  say "would run setup-symlinks.sh in $REPO"
fi

# ---- 2. .teamz-automation.env ------------------------------------------
ENVF="$ROOT/.teamz-automation.env"
if [ -f "$ENVF" ]; then
  echo "  .teamz-automation.env already exists — left alone"
else
  say "would create .teamz-automation.env"
  if $APPLY; then
    cat > "$ENVF" <<ENVEOF
# Teamz Lab automation config for $REPO. Created by onboard-property.sh.
TEAMZ_SITE_URL=$SITE
TEAMZ_HOST_SITE_ROOT=$ROOT
# Fill these in — they cannot be derived:
TEAMZ_GSC_PROPERTY=$SITE
TEAMZ_GA4_PROPERTY_ID=
ENVEOF
  fi
fi

# ---- 3. launchd plist, generated not hand-copied ------------------------
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
RUNNER="$ROOT/scripts/nightly-site.sh"
if [ -f "$PLIST" ]; then
  echo "  plist already exists — left alone ($PLIST)"
else
  say "would write $PLIST"
  if $APPLY; then
    mkdir -p "$ROOT/logs"
    cat > "$PLIST" <<PEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$RUNNER</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>TEAMZ_HOST_SITE_ROOT</key><string>$ROOT</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>$HOUR</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>$ROOT/logs/$LABEL.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/$LABEL.log</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
PEOF
    echo "  NOT loaded. Start it yourself when ready:"
    echo "     launchctl load $PLIST"
  fi
fi

# ---- 4. register in the digest so /growth can see it -------------------
# A property missing from SITES is invisible to /growth forever — it will run
# every night and never appear in a single health report.
if grep -q "\"$REPO\"" "$DIGEST" 2>/dev/null || grep -q "(\"$REPO\"" "$DIGEST" 2>/dev/null; then
  echo "  already registered in build-growth-digest.py"
else
  say "would add \"$REPO\" to SITES in build-growth-digest.py"
  if $APPLY; then
    python3 - "$DIGEST" "$REPO" "$SITE" "$LABEL" <<'PYEOF'
import sys, re, pathlib
digest, repo, site, label = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
p = pathlib.Path(digest); t = p.read_text()
row = f'    ("{repo}",{" " * max(1, 34 - len(repo))}"{site}",{" " * max(1, 33 - len(site))}"{label}"),\n'
m = re.search(r"(SITES = \[\n)((?:.*\n)*?)(\]\n)", t)
if not m:
    sys.exit("could not find the SITES list")
t = t[:m.end(2)] + row + t[m.end(2):]
p.write_text(t)
print("  registered in SITES")
PYEOF
  fi
fi

# ---- 5. the parts no script can do ------------------------------------
cat <<MANUAL

  ---- still yours to do, these cannot be automated ----
  1. Search Console: add and verify $SITE, then grant the
     automation service account read access.
  2. GA4: create the property and put its numeric id in
     $ENVF  (TEAMZ_GA4_PROPERTY_ID=)
     and in the GA4 map in build-growth-digest.py.
  3. DNS, if the domain is new:
       bash scripts/cf-dns.sh doctor
       bash scripts/cf-dns.sh set teamzlab.com CNAME <sub> <target>
  4. Start the schedule when you are ready:
       launchctl load $PLIST

  Then confirm it is actually visible:
       python3 $AUTOMATION/py/build-growth-digest.py | head -12
  The new row must appear. If it does not, step 4 above did not take.

MANUAL
$APPLY || echo "  DRY RUN finished — nothing was written. Add --apply to do it."
echo ""
