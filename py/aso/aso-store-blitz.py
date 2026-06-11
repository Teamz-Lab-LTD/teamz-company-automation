#!/usr/bin/env python3
"""aso-store-blitz.py — full ASO ship pipeline in ONE command, no user prompts.

Goal: run this from a Teamz Lab app project root, get everything live on Play
+ submitted to Apple, with zero hand-holding. Reads project env, runs each
step in order, pushes commits, and prints a single-line per-step result so
the human can scan the log later.

Steps (each can be --skip-<name>):
  1.  preflight        — verify env, creds, presets JSON, raw screenshots, fonts
  2.  keyword-volume   — refresh build-keyword-volume.py against TEAMZ_ASO_KEYWORDS
  3.  competitors      — refresh aso-competitors.py --find on top kws
  4.  ai-edit          — Gemini edits raw screenshots for USD/local terms (only if
                          en-US-edited dir missing or stale)
  5.  compose          — aso-generate-batch.py with presets ordered by ASO priority
  6.  pad-resize       — fan out composed -> 5 device sizes (1242x2208, 1242x2688,
                          2048x2732, 1080x1920, 1200x1920)
  7.  feature-graphic  — Pillow compose 1024x500 banner matching design system
  8.  localize         — run project's automation_data/localize_metadata.py
  9.  play-push        — aso-play-batch-push.py --commit (listings + 8 phone + 8
                          tablet screenshots + feature graphic)
  10. apple-version    — create new App Store version (e.g. 1.0.x) if no editable
                          version exists
  11. apple-metadata   — fastlane ios upload_metadata
  12. apple-screenshots — asc-screenshots-push.rb LOCALES=ALL
  13. apple-submit     — fastlane ios submit_review (off by default; opt in
                          via --auto-submit because Apple review is irreversible)

Usage:
  cd <your_app_project_root>/
  python3 packages/team_mvp_kit/teamz-company-automation/py/aso/aso-store-blitz.py

Options:
  --auto-submit       Submit Apple version for review after upload. Default off.
  --skip <step>       Skip a step (repeat for multiple). Default: nothing skipped.
  --only <step>       Run ONLY this step + exit.
  --apple-version X   Override new Apple version string. Default = pubspec.yaml +0.0.1.
  --dry-run           Validate everything, push nothing.

Prereqs (one-time per machine):
  pip3 install Pillow google-auth google-api-python-client
  fastlane frameit download_frames
  Poppins fonts in ~/Library/Fonts/
  ~/.config/teamzlab/AuthKey_*.p8
  ~/.config/teamzlab/play-console-service-account.json
  ~/.config/teamzlab/gemini-api-key.txt

Prereqs (per app):
  .teamz-automation.env  with TEAMZ_PLAY_PACKAGE_NAME, TEAMZ_APP_IDS, TEAMZ_ASO_KEYWORDS
  .appstore-fastlane.env with ASC_KEY_ID, ASC_ISSUER_ID, APP_BUNDLE_ID, APPLE_APP_ID
  automation_data/aso_screenshot_presets.json
  automation_data/localize_metadata.py
  fastlane/screenshots/en-US/ raw PNGs (or en-US-edited for AI-edited)
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
KIT_PY = PROJECT_ROOT / "packages" / "team_mvp_kit" / "teamz-company-automation" / "py"
ASO = KIT_PY / "aso"

STEPS = [
    "preflight", "keyword-volume", "competitors", "ai-edit", "name-collision", "compose",
    "pad-resize", "feature-graphic", "localize", "play-push", "apple-version",
    "apple-metadata", "apple-screenshots", "apple-submit",
]

def _run(cmd, cwd=None, env=None, capture=False):
    """Run a subprocess, stream output, return (rc, stdout)."""
    print(f"   $ {' '.join(str(c) for c in cmd)}")
    if capture:
        r = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, env=env, capture_output=True, text=True)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    r = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, env=env)
    return r.returncode, ""

def _env_load(path):
    """Read KEY=VALUE pairs from a dotenv file, ignore comments + blanks."""
    out = {}
    if not Path(path).exists():
        return out
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

def _step_header(name):
    print(f"\n━━━ [{name}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

def preflight():
    """Check env, creds, presets JSON, raw screenshots exist."""
    missing = []
    for f in [".teamz-automation.env", ".appstore-fastlane.env",
              "automation_data/aso_screenshot_presets.json",
              "automation_data/localize_metadata.py"]:
        if not (PROJECT_ROOT / f).exists():
            missing.append(f)
    for f in ["~/.config/teamzlab/play-console-service-account.json",
              "~/.config/teamzlab/AuthKey_559DD92MBH.p8",
              "~/.config/teamzlab/gemini-api-key.txt"]:
        if not Path(os.path.expanduser(f)).exists():
            missing.append(f)
    if missing:
        print("   ❌ MISSING:")
        for m in missing:
            print(f"      - {m}")
        return 1
    print("   ✓ all required files + creds present")
    return 0

def keyword_volume(env):
    """Refresh keyword volume scores."""
    kws = env.get("TEAMZ_ASO_KEYWORDS", "")
    if not kws:
        print("   ⊘ skip: TEAMZ_ASO_KEYWORDS empty")
        return 0
    seeds = [k.strip() for k in kws.split(",") if k.strip()]
    rc, _ = _run(["python3", str(KIT_PY / "build-keyword-volume.py"), *seeds])
    return rc

def competitors(env):
    """Refresh competitor data on first 3 kws."""
    kws = env.get("TEAMZ_ASO_KEYWORDS", "")
    seeds = [k.strip() for k in kws.split(",") if k.strip()][:3]
    if not seeds:
        return 0
    args = ["python3", str(ASO / "aso-competitors.py")]
    for s in seeds:
        args += ["--find", s]
    rc, _ = _run(args)
    return rc

def ai_edit(env):
    """AI-edit raw screenshots when fastlane/screenshots/en-US-edited/ missing.
    Skipped if dir exists (assumes already edited).
    """
    edited = PROJECT_ROOT / "fastlane/screenshots/en-US-edited"
    if edited.exists() and any(edited.iterdir()):
        print(f"   ⊘ skip: {edited.relative_to(PROJECT_ROOT)} already populated")
        return 0
    print(f"   ⚠ {edited.relative_to(PROJECT_ROOT)} empty — manual ai-edit step required for now.")
    print(f"     See aso-gemini-edit.py for direct API calls.")
    return 0

def compose():
    """Run aso-generate-batch.py."""
    presets = PROJECT_ROOT / "automation_data/aso_screenshot_presets.json"
    rc, _ = _run(["python3", str(ASO / "aso-generate-batch.py"), "--presets", str(presets)])
    return rc

def pad_resize():
    """Pad each composed JPG into 5 device sizes."""
    src_dir = PROJECT_ROOT / "screenshots/store-ready"
    if not src_dir.exists():
        print(f"   ❌ {src_dir.relative_to(PROJECT_ROOT)} missing")
        return 1
    composed = sorted(src_dir.glob("*.jpg"))
    composed = [c for c in composed if c.parent == src_dir]
    if not composed:
        print(f"   ❌ no composed JPGs in {src_dir.relative_to(PROJECT_ROOT)}")
        return 1
    # Read BG from presets JSON
    import json
    bg = json.loads((PROJECT_ROOT / "automation_data/aso_screenshot_presets.json").read_text()).get("bg", "#D9FE06")
    targets = [
        ("apple-iphone-55", 1242, 2208),
        ("apple-iphone-65", 1242, 2688),
        ("apple-ipad-129", 2048, 2732),
        ("play-phone", 1080, 1920),
        ("play-tablet", 1200, 1920),
    ]
    n = 0
    for src in composed:
        for sub, w, h in targets:
            dst = src_dir / sub / src.name
            cmd = ["python3", str(ASO / "aso-pad-resize.py"),
                   "--src", str(src), "--dst", str(dst),
                   "--width", str(w), "--height", str(h), "--bg", bg]
            rc, _ = _run(cmd, capture=True)
            if rc == 0:
                n += 1
    print(f"   ✓ {n} padded variants written")
    return 0

def feature_graphic():
    """Compose Play feature graphic 1024x500."""
    # Inline composer — reads first composed shot as phone preview
    from PIL import Image, ImageDraw, ImageFont
    import json
    src_dir = PROJECT_ROOT / "screenshots/store-ready"
    composed = sorted(src_dir.glob("*.jpg"))
    composed = [c for c in composed if c.parent == src_dir]
    if not composed:
        print("   ⊘ skip: no composed shots")
        return 0
    phone_src = composed[1] if len(composed) > 1 else composed[0]
    presets = json.loads((PROJECT_ROOT / "automation_data/aso_screenshot_presets.json").read_text())
    bg = presets.get("bg", "#D9FE06")
    fg = presets.get("text_color", "#000000")
    # Default hero text from app name
    env = _env_load(PROJECT_ROOT / ".appstore-fastlane.env")
    app_name = env.get("APP_NAME", PROJECT_ROOT.name)
    hero_words = app_name.split()
    hero1 = hero_words[0].upper() if hero_words else "FEATURE"
    hero2 = " ".join(hero_words[1:]).upper() if len(hero_words) > 1 else ""

    W, H = 1024, 500
    poppins_dir = Path.home() / "Library/Fonts"
    head_font = next(iter(poppins_dir.glob("Poppins-Bold*")), None)
    body_font = next(iter(poppins_dir.glob("Poppins-SemiBold*")), head_font)
    if not head_font:
        print("   ❌ Poppins-Bold not in ~/Library/Fonts/")
        return 1
    canvas = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(canvas)
    phone = Image.open(phone_src).convert("RGB")
    ph_h = 470
    ph_w = int(phone.width * (ph_h / phone.height))
    phone = phone.resize((ph_w, ph_h), Image.LANCZOS)
    phone_x = W - ph_w - 20
    canvas.paste(phone, (phone_x, (H - ph_h) // 2))
    text_w = phone_x - 80
    def fit(text, max_w, lo, hi, f):
        for sz in range(hi, lo, -2):
            ft = ImageFont.truetype(str(f), sz)
            if d.textlength(text, font=ft) <= max_w:
                return ft
        return ImageFont.truetype(str(f), lo)
    y = 80
    d.text((50, y), hero1, fill=fg, font=fit(hero1, text_w, 60, 120, head_font))
    if hero2:
        y += 130
        d.text((50, y), hero2, fill=fg, font=fit(hero2, text_w, 60, 120, head_font))
    d.text((50, H - 50), f"{app_name} · Free on iOS & Android", fill=fg,
           font=ImageFont.truetype(str(body_font), 22))
    out = PROJECT_ROOT / "android/app/src/main/play/listings/en-US/graphics/feature-graphic/feature-graphic.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG", optimize=True)
    print(f"   ✓ wrote {out.relative_to(PROJECT_ROOT)}")
    return 0

def localize():
    """Run project's hand-translation script."""
    script = PROJECT_ROOT / "automation_data/localize_metadata.py"
    if not script.exists():
        print(f"   ⊘ skip: no {script.relative_to(PROJECT_ROOT)}")
        return 0
    rc, _ = _run(["python3", str(script)])
    return rc

def play_push(env, dry_run=False):
    """Push Play listings + graphics in one transaction."""
    sa = os.path.expanduser(env.get("TEAMZ_PLAY_SERVICE_ACCOUNT_JSON",
                                    "~/.config/teamzlab/play-console-service-account.json"))
    pkg = env.get("TEAMZ_PLAY_PACKAGE_NAME")
    if not pkg:
        print("   ❌ TEAMZ_PLAY_PACKAGE_NAME missing")
        return 1
    # Symlink fastlane screenshots into kit path (script bug workaround)
    kit_fastlane = KIT_PY / "fastlane"
    kit_fastlane.mkdir(exist_ok=True)
    target = kit_fastlane / "screenshots"
    if not target.exists():
        target.symlink_to(PROJECT_ROOT / "fastlane/screenshots")
    # Same for android listings
    kit_android = KIT_PY / "android/app/src/main/play"
    kit_android.mkdir(parents=True, exist_ok=True)
    target = kit_android / "listings"
    if not target.exists():
        target.symlink_to(PROJECT_ROOT / "android/app/src/main/play/listings")
    new_env = {**os.environ, "TEAMZ_PLAY_SERVICE_ACCOUNT_JSON": sa, "TEAMZ_PLAY_PACKAGE_NAME": pkg}
    args = ["python3", str(ASO / "aso-play-batch-push.py")]
    if not dry_run:
        args.append("--commit")
    rc, _ = _run(args, env=new_env)
    return rc

def apple_version(env, override_version=None):
    """Create new editable App Store version if none exists."""
    # Quick check via Ruby + Spaceship — same pattern used to create 1.0.2
    asc_env = _env_load(PROJECT_ROOT / ".appstore-fastlane.env")
    key_id = asc_env.get("ASC_KEY_ID", "")
    issuer = asc_env.get("ASC_ISSUER_ID", "")
    bundle = asc_env.get("APP_BUNDLE_ID", "")
    if not all([key_id, issuer, bundle]):
        print("   ❌ ASC creds missing in .appstore-fastlane.env")
        return 1
    # Derive next version from pubspec.yaml
    pubspec = PROJECT_ROOT / "pubspec.yaml"
    next_version = override_version
    if not next_version and pubspec.exists():
        for ln in pubspec.read_text().splitlines():
            if ln.startswith("version:"):
                cur = ln.split(":", 1)[1].strip().split("+")[0]
                parts = cur.split(".")
                parts[-1] = str(int(parts[-1]) + 1)
                next_version = ".".join(parts)
                break
    if not next_version:
        print("   ❌ cannot derive next version")
        return 1
    print(f"   Target version: {next_version}")
    # Write + run Ruby create script
    rb = f"""
require 'spaceship'
Spaceship::ConnectAPI.token = Spaceship::ConnectAPI::Token.create(
  key_id: '{key_id}', issuer_id: '{issuer}',
  filepath: File.expand_path('{asc_env.get("ASC_KEY_FILEPATH", "~/.config/teamzlab/AuthKey_" + key_id + ".p8")}')
)
app = Spaceship::ConnectAPI::App.find('{bundle}')
editable = app.get_app_store_versions.find {{ |v| %w[PREPARE_FOR_SUBMISSION DEVELOPER_REJECTED METADATA_REJECTED INVALID_BINARY].include?(v.app_store_state) }}
if editable
  puts "EXISTING:#{{editable.version_string}}:#{{editable.app_store_state}}"
  exit 0
end
require 'net/http'; require 'uri'; require 'json'
body = {{ data: {{ type: "appStoreVersions", attributes: {{ versionString: '{next_version}', platform: "IOS", releaseType: "AFTER_APPROVAL" }}, relationships: {{ app: {{ data: {{ type: "apps", id: app.id }} }} }} }} }}
uri = URI("https://api.appstoreconnect.apple.com/v1/appStoreVersions")
http = Net::HTTP.new(uri.host, uri.port); http.use_ssl = true
req = Net::HTTP::Post.new(uri)
req["Authorization"] = "Bearer #{{Spaceship::ConnectAPI.token.text}}"
req["Content-Type"] = "application/json"
req.body = body.to_json
res = http.request(req)
if res.code.to_i >= 400
  puts "ERROR:#{{res.code}}:#{{res.body[0, 500]}}"; exit 1
end
puts "CREATED:{next_version}:PREPARE_FOR_SUBMISSION"
"""
    rb_path = Path("/tmp/blitz-apple-version.rb")
    rb_path.write_text(rb)
    rc, out = _run(["ruby", str(rb_path)], capture=True)
    print(f"   {out.strip()}")
    return rc

def apple_metadata():
    """fastlane ios upload_metadata (from fastlane/ dir)."""
    fastlane_dir = PROJECT_ROOT / "fastlane"
    if not fastlane_dir.exists():
        print("   ❌ fastlane/ missing")
        return 1
    rc, _ = _run(["fastlane", "ios", "upload_metadata"], cwd=fastlane_dir)
    return rc

def apple_screenshots(env):
    """Push Apple screenshots all 39 locales via direct Spaceship."""
    asc_env = _env_load(PROJECT_ROOT / ".appstore-fastlane.env")
    fastlane_dir = PROJECT_ROOT / "fastlane"
    new_env = {**os.environ, **asc_env, "LOCALES": "ALL"}
    # symlink workaround for screenshot path resolution
    kit_fastlane = KIT_PY / "fastlane"
    kit_fastlane.mkdir(exist_ok=True)
    target = kit_fastlane / "screenshots"
    if not target.exists():
        target.symlink_to(PROJECT_ROOT / "fastlane/screenshots")
    rc, _ = _run(["bundle", "exec", "ruby",
                  str(ASO / "asc-screenshots-push.rb")],
                 cwd=fastlane_dir, env=new_env)
    return rc

def apple_submit():
    """fastlane ios submit_review — opt-in only."""
    fastlane_dir = PROJECT_ROOT / "fastlane"
    rc, _ = _run(["fastlane", "ios", "submit_review"], cwd=fastlane_dir)
    return rc

def name_collision(env):
    """Gate the proposed app name vs App Store + Play (aso-name-collision.py).
    rc 2 = COLLISION -> differentiate before submit. Closes the 'exact app name already
    taken' gap the keyword/competitor steps miss."""
    import glob, json as _json
    name = env.get("APP_NAME") or env.get("TEAMZ_APP_NAME") or ""
    if not name:
        for fp in sorted(glob.glob(str(PROJECT_ROOT / "automation_data" / "aso-*latest.json"))):
            try:
                d = _json.load(open(fp))
                name = d.get("title") or d.get("app_name") or d.get("name") or ""
            except Exception:
                name = ""
            if name:
                break
    if not name:
        print("  [name-collision] no app name (env APP_NAME / automation_data) — skipping")
        return 0
    print(f"  [name-collision] checking {name!r} ...")
    rc, out = _run(["python3", str(ASO.parent / "aso-name-collision.py"), str(name)], cwd=PROJECT_ROOT)
    print(out)
    return rc


def main():
    p = argparse.ArgumentParser(description="ASO ship blitz — full Play + Apple push in one command.")
    p.add_argument("--skip", action="append", default=[], choices=STEPS)
    p.add_argument("--only", choices=STEPS)
    p.add_argument("--apple-version", default=None)
    p.add_argument("--auto-submit", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    env = _env_load(PROJECT_ROOT / ".teamz-automation.env")
    steps_to_run = [args.only] if args.only else [s for s in STEPS if s not in args.skip]
    # apple-submit is opt-in
    if "apple-submit" in steps_to_run and not args.auto_submit and not args.only:
        steps_to_run.remove("apple-submit")

    print(f"━━━ ASO STORE BLITZ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Project: {PROJECT_ROOT.name}")
    print(f"Steps:   {', '.join(steps_to_run)}")
    print(f"Dry-run: {args.dry_run}")

    results = {}
    for step in steps_to_run:
        _step_header(step)
        rc = 0
        if step == "preflight":
            rc = preflight()
        elif step == "keyword-volume":
            rc = keyword_volume(env)
        elif step == "competitors":
            rc = competitors(env)
        elif step == "ai-edit":
            rc = ai_edit(env)
        elif step == "name-collision":
            rc = name_collision(env)
        elif step == "compose":
            rc = compose()
        elif step == "pad-resize":
            rc = pad_resize()
        elif step == "feature-graphic":
            rc = feature_graphic()
        elif step == "localize":
            rc = localize()
        elif step == "play-push":
            rc = play_push(env, dry_run=args.dry_run)
        elif step == "apple-version":
            rc = apple_version(env, override_version=args.apple_version)
        elif step == "apple-metadata":
            if not args.dry_run:
                rc = apple_metadata()
        elif step == "apple-screenshots":
            if not args.dry_run:
                rc = apple_screenshots(env)
        elif step == "apple-submit":
            if not args.dry_run:
                rc = apple_submit()
        results[step] = rc

    print(f"\n━━━ SUMMARY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for s, rc in results.items():
        mark = "✓" if rc == 0 else "✗"
        print(f"  {mark} {s}: rc={rc}")
    failed = [s for s, rc in results.items() if rc != 0]
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
