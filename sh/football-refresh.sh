#!/bin/bash
# Football feed refresh — standings + fixtures only, on a FIXTURE-shaped schedule.
#
# WHY THIS EXISTS. The tools nightly already runs both fetchers, but it runs at 15:00 and 21:00
# Asia/Dhaka (09:00 and 15:00 UTC) — a schedule built around content publishing, not football.
# Measured against Premier League matchweek 1 (2026-08-21..24):
#
#   Fri 19:00 UTC kickoff  -> next feed run Sat 09:00 UTC   12.0h stale
#   Sat 14:00 UTC (x3)     -> next feed run Sun 09:00 UTC   17.0h stale
#   Sat 16:30 UTC          -> next feed run Sun 09:00 UTC   14.5h stale
#   Sun 13:00 UTC (x2)     -> next feed run Mon 09:00 UTC   18.0h stale
#   Sun 15:30 UTC          -> next feed run Mon 09:00 UTC   15.5h stale
#
# 7 of 10 matches sat more than 12 hours behind. The #1 result for the money query
# (worldfootball.net) advertises minute-level freshness, and the "vs actual" panel on our
# earner is only worth returning to if the table it scores against is current.
#
# One extra run at 22:00 UTC / 04:00 Asia/Dhaka takes the worst case from 18h to ~7h. That slot
# is the only one clear of all nine existing scheduled jobs (08:30 catch-up, 15:00 + 21:00 tools
# nightly which ran until 22:49 last night, 22:00 tekko, 22:30 landing, 23:00 learn, 23:20
# goalkit, 23:40 brand, 23:55 growth-watchdog).
#
# DELIBERATELY NARROW. It fetches two feeds and commits data/football/ ONLY. No content, no
# sitemap, no enhance agent. If it ever does more than that, it is the wrong script.
set -uo pipefail

ROOT="/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects/teamzlab-tools"
LOG="$ROOT/logs/football-refresh.log"
mkdir -p "$(dirname "$LOG")"
exec >> "$LOG" 2>&1
echo ""
echo "=== football-refresh $(date '+%Y-%m-%d %H:%M:%S %z') ==="

cd "$ROOT" || { echo "  ABORT: repo not found at $ROOT"; exit 1; }

# Never run alongside a nightly. `git add -A` in nightly-build.sh has already swept another
# session's staged work into its own commit once (2026-08-21); racing it also risks
# 'cannot lock ref HEAD'. pgrep -fl, never `ps | grep -c` — the bracket trick still matches
# the grep's own command line.
if pgrep -fl 'nightly-build.sh' >/dev/null 2>&1; then
    echo "  SKIP: a nightly build is running — not touching this repo."
    exit 0
fi

# Do not hijack a commit someone is in the middle of preparing.
if ! git diff --cached --quiet 2>/dev/null; then
    echo "  SKIP: the index already has staged changes — leaving them alone."
    exit 0
fi

CHANGED=0
for s in build-football-standings.py build-football-fixtures.py; do
    if [ ! -f "scripts/$s" ]; then
        echo "  ERROR: scripts/$s missing — cannot refresh."
        exit 1
    fi
    OUT=$(python3 "scripts/$s" 2>&1); RC=$?
    echo "$OUT" | sed 's/^/    /'
    if [ "$RC" -ne 0 ]; then
        echo "  ERROR: $s exited $RC — leaving every feed file untouched."
        git checkout -- data/football/ 2>/dev/null
        exit 1
    fi
done

if git diff --quiet -- data/football/ 2>/dev/null; then
    echo "  no feed changes — nothing to commit."
    exit 0
fi

# Explicit pathspec. NEVER `git add -A` here: a previous `-A` in this codebase swept
# credential-bearing backup files into a commit.
git add data/football/
git diff --cached --name-only | sed 's/^/    staged: /'
git commit -q -m "chore(football): refresh standings + fixtures" --no-verify || {
    echo "  ERROR: commit failed"; exit 1; }

if git push -q origin HEAD 2>&1 | sed 's/^/    /'; then
    echo "  pushed."
else
    echo "  ERROR: push failed — commit is local only, next run will carry it."
    exit 1
fi

python3 -c "
import json
for c in ['pl','pd','sa','bl1','elc']:
    try:
        d=json.load(open('data/football/%s.json'%c)); s=d['standings']
        print('    %-4s started=%-5s zero-played=%d/%d' % (c,d['started'],sum(1 for r in s if r['played']==0),len(s)))
    except Exception as e:
        print('    %-4s UNREADABLE: %s' % (c,e))
"
echo "=== done $(date '+%H:%M:%S') ==="
