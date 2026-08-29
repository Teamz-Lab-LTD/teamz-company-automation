---
description: One-screen health + growth rollup across ALL Teamz Lab nightly properties (apps, goalkit, learn, tools, tekko). Reads the digest + the loud preflight/nightly status files.
---

# /growth — full business growth, one conversation

The owner drives Uber and cannot open four projects. This command answers **"is my whole business
healthy, and is it growing?"** in one screen, from ANY Claude session. It reads the SAME status
files the nightly self-check writes — so if a silent killer fired, it shows here.

## Do this, in order

1. **Run the cross-property digest** (covers every property, writes + prints the rollup):
   ```
   cd "/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects/teamz-company-automation" && python3 py/build-growth-digest.py
   ```

2. **Read each property's LOUD health signals** — the preflight verdict and the nightly exit status.
   A missing/stale `preflight-status.json` is itself a flag (the guard did not run). For each repo
   below, read `data/preflight-status.json` and `data/nightly-status.json`:
   - apps   → `teamz-projects/teamz-lab-generic-landing-pages`
   - goalkit→ `teamz-projects/goalkit-bd`
   - learn  → `teamz-projects/teamz-lab-learning`
   - tools  → `teamz-projects/teamzlab-tools`
   - tekko  → `teamz-projects/tekko-bd`  (new 2026-08-22 — IoT/Arduino components, BD)
   ```
   for r in teamz-lab-generic-landing-pages goalkit-bd teamz-lab-learning teamzlab-tools tekko-bd; do
     echo "== $r =="
     cat "/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects/$r/data/preflight-status.json" 2>/dev/null || echo "  (no preflight-status — guard did not run here)"
     cat "/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects/$r/data/nightly-status.json" 2>/dev/null || echo "  (no nightly-status)"
   done
   ```

3. **If any `$ARGUMENTS` is given**, treat it as a property name (apps/goalkit/learn/tools) or a
   question and drill into THAT one: read its `data/content-queue.json`, `docs/last-night-content.md`,
   and recent git log, and explain what it did last night and what it will do next.

4. **Check WHAT the nightly CHOSE, not just that it ran.** This step exists because it was
   missing for ~12 weeks. On 2026-08-30 the owner asked "why is my nightly not doing this?" and
   the answer was: the enhance queue had ranked `/pest/bug-bite-identifier/` — the site's
   highest-earning page, $9.38 measured RPM against a $1.15 site average — **24th of 26**, while
   seating pages scoring 0.40 in the top three. Every `/growth` run before that reported
   "healthy, N commits" and was technically correct. **"It ran" is not "it chose well."**

   ```
   python3 - <<'EOF'
   import json, os, statistics
   ROOT = "/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects"
   for r in ("teamzlab-tools", "teamz-lab-generic-landing-pages", "goalkit-bd",
             "teamz-lab-learning", "tekko-bd"):
       f = os.path.join(ROOT, r, "data", "enhance-queue.json")
       if not os.path.exists(f):
           print(f"== {r}: no enhance-queue.json — COULDN'T CHECK (not 'fine')")
           continue
       d = json.load(open(f)); t = d.get("targets", [])
       when = (d.get("generated_at") or "?")[:10]
       print(f"== {r}  generated {when}  {len(t)} targets")
       meas = [(i + 1, c) for i, c in enumerate(t)
               if c.get("rpm_source") == "measured" and (c.get("rpm_mid") or 0) > 0]
       if meas:
           med = statistics.median([c["rpm_mid"] for _, c in meas])
           rank, best = max(meas, key=lambda x: x[1]["rpm_mid"])
           flag = "  <-- BURIED" if rank > len(t) / 2 and best["rpm_mid"] > med else ""
           print(f"   best MEASURED page: rank {rank}/{len(t)}  "
                 f"${best['rpm_mid']}  {best['slug']}{flag}")
       else:
           print("   no page in this queue has measured earnings — every rank is a guess")
       bench = sum(1 for c in t[:10] if "benchmark" in (c.get("rpm_source") or ""))
       print(f"   top-10 priced by GUESSED benchmark RPM: {bench} of {min(10, len(t))}"
             + ("   <-- ranking on invented money" if bench > 5 else ""))
   EOF
   ```

   Report a finding, in the owner's words, whenever ANY of these is true:
   - a page with `rpm_source: measured` and an RPM **above the property's median** sits in the
     **bottom half** of the queue — name the page, its RPM, and its rank;
   - **more than half** the top 10 are priced `niche-benchmark` (a guessed number, not this
     site's own earnings) — the queue is ranking on invented money;
   - the same slug has been in the queue **3+ runs** without its GSC clicks moving — it is being
     re-picked and not fixed;
   - `enhance-queue.json` is **missing or older than 3 days** — say "couldn't check", never ✅.

   If nothing trips, say so in one line: "queue choices look sane — best measured page is at
   rank N." One line is enough; do not pad it.

## Report format (keep it to one screen)

Lead with the single most important fact — a silent-killer alert, a deploy failure, or "all four
healthy." Then a compact table, most-broken first:

| property | ran last night? | grew? | health |
|---|---|---|---|
| apps | ✅/⚠️/❌ + hrs ago | clicks/impr Δ from digest | preflight ok / **ALERT: \<name\>** |
| goalkit | … | … | … |
| learn | … | … | … |
| tools | … | … | … |
| tekko | … | … | … |

**Health column MUST also check `nightly-status.json`'s `build` field and `health_alerts` count,
not just preflight.** On 2026-07-23, tools' `nightly-status.json` had sat at `"build":
"ok:4-health-alerts"` for months — a real, growing internal-link problem (3499 pages not linked
from their own hub) — while every /growth run before that date reported "preflight ok" and the
owner never found out. Preflight and health_alerts are DIFFERENT signals: preflight only proves
the guard ran; `build` containing anything other than plain `"ok"` (e.g. `ok:N-health-alerts`,
`ok:link-health-alert`) means a check inside the run found something wrong and it belongs in this
table, in the health column, every time — never silently folded into "ran fine."

Then **"what it did for you"** — one line per property, from the digest's "What the engine actually
did" commit list (already generated by build-growth-digest.py — read it, don't re-derive it) plus
each property's `nightly-status.json` `content`/`courses` fields. Classify each property honestly,
don't just say "it ran":
- **real content shipped** — commit subjects are `content(...)` describing an actual new
  section/page (e.g. "add CQC compliance section", "cold-start Liverpool jersey page"). Say what
  kind, in plain words, not the raw commit hash.
- **enhanced existing pages** (tools' model) — no new pages; picks existing ones and improves them.
  Cite the enhance-outcome verdict if present in the log (ENHANCED vs CONTROL clicks) — that's the
  proof it worked, not just that it ran.
- **research/prep only, nothing published** — commits are `content(radar)`/keyword-seed/batch-prep
  work, or `nightly-status.json` shows `content: "ok:empty-queue"` / `courses: "ok:no-task"`. This
  is NOT the same as "did nothing wrong" — say plainly that no content shipped, so "preflight ok"
  is never read by the owner as "it grew my content."
- **maintenance only** — commits are all `chore(nightly): refresh generated output` / dirty-tree
  unblocks with no `content(...)` subject at all.

Then 2–3 lines: the overall business trend (are total clicks/AI-sessions rising or flat?), and the
ONE thing worth the owner's attention this week (a stale keyword pull, a page to watch, a decision
owed). Do NOT dump raw JSON — interpret it.

## Rules
- **A monitor must never lie.** If a signal could not be read (missing file, unreachable property,
  stale status), say "couldn't check" — never render it as ✅. "All clear" and "couldn't check" must
  look different (this is the exact bug this whole system exists to prevent).
- **Revenue = store/AdSense earnings, never analytics events.** If asked about money, say the digest
  shows traffic/health, not revenue, and point to the store reports.
- Be honest about flat or shrinking numbers. The owner wants the uncomfortable truth first, not a
  cheerful summary.
- **"It ran" is not "it chose well."** The nightly's exit code, commit count and health alerts
  describe whether the machine WORKED, never whether it worked on the RIGHT PAGES. A queue can
  pick 26 worthless pages every night for a year and every other signal in this report stays
  green. Step 4 is the only part of `/growth` that can catch that — never skip it, and never
  summarise it as "healthy" without having actually read the queue.
- **"preflight ok" is not "content grew."** Preflight only proves the guard ran and found no
  broken path/token/parse — it says nothing about whether anything was written. Never let a green
  preflight read as proof of growth; the "what it did for you" section is the only thing that
  answers that.
