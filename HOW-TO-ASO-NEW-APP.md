# How to do ASO for a new app (the only doc you need)

One canonical automation, symlinked into every project. **Code is shared; generated data
stays per-project.** Follow this and you never hand-hold the agent again.

## Architecture (why it works)
- **`teamz-projects/teamz-company-automation`** = the ONE real clone (the `main` branch). All
  scripts live here.
- Every project has `teamz-company-automation` as a **symlink** → that canonical (NOT a
  submodule — submodules pin per-project and drift, which is what broke everything before).
- Each project keeps its OWN **`./automation_data/`** — generated CSVs/JSON go there
  (per-project, never into the shared canonical). Scripts read/write it via
  `TEAMZ_DATA_DIR` / `.teamz-automation.env`.

## Register a NEW app (one-time, ~2 min)
```bash
cd <your-new-app-project>
# 1. declare the slug (this is ALL the /aso-refresh skill needs to find the app)
cat > .teamz-automation.env <<EOF
TEAMZ_APP_SLUG=<your-slug>
TEAMZ_PLAY_PACKAGE_NAME=<com.you.app>
TEAMZ_PROJECT_TYPE=mobile_game
EOF
# 2. symlink the shared automation (relative to canonical)
ln -s "$(python3 -c "import os;print(os.path.relpath('$HOME/Projects/Teamz Lab Projects/teamz-projects/teamz-company-automation', '.'))")" teamz-company-automation
# 3. seed data dir + keywords
mkdir -p automation_data && echo "your, seed, keywords" > automation_data/seed_keywords.txt
```
No editing the `/aso-refresh` switch — it **auto-discovers** any project with a
`.teamz-automation.env` that declares `TEAMZ_APP_SLUG`.

## Run ASO (every time)
```bash
git -C teamz-company-automation pull        # never run a stale canonical
/aso-refresh <your-slug>                     # ONE command — resolves the app, runs the pipeline
```
That runs `aso-store-blitz.py` which chains, in order:
`preflight → keyword-volume → seo-signals → competitors → ai-edit → name-collision →
compose → claims-lint → … → apple-metadata → apple-submit`.

Built-in gates (a release STOPS if these fail):
- **name-collision** — your title vs App Store + Play (exit 2 = clashing name → differentiate).
- **claims-lint** — forbidden claims in listing/screenshots: `offline`, `ad-free`, `no ads`…
  (per-app list from `automation_data/deep-research-keywords.json` →
  `_app_constraints.forbidden_claims`). This is what catches "Play offline" on a WebView app.

## The rule for the agent (me)
1. **Always `/aso-refresh <slug>` first.** Never invent a title/keyword from memory.
2. **Read `automation_data/`** (ranked CSV, deep-research) before touching any listing field.
3. **Copy the pipeline's output — never re-derive it.**
4. If a gate fails, FIX it — don't bypass.

## Gotchas (learned the hard way)
- **Stale canonical** → looks like scripts are missing. `git pull` it first.
- **Forbidden claims** = instant rejection. The app ships AdMob + is a remote WebView →
  never say `ad-free` or `offline`.
- **Generated data never goes in the canonical** — it belongs in each app's `./automation_data/`.
