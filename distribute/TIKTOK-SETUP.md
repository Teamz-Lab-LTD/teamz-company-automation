# TikTok Distribution — Setup & Recovery

## Current Status
- **Submitted for review:** 2026-04-21
- **Mode:** Sandbox (until TikTok approves production)
- **Expected approval:** 2-6 weeks from submission

## How it works

`distribute.py next` automatically fires TikTok alongside articles + YouTube. No manual step needed. TikTok entry in `ALL_PLATFORMS`, `PLATFORM_LIMITS`, and both `platform_funcs` dicts.

**Rate limits:** 2/day, 4h gap, 5/week (enforced inside `tiktok-upload.js`).
**Mode:** Inbox drafts (not direct publish). Videos land in TikTok app inbox — user taps Publish.
**Tracking:** Each reel in `reel-history.json` has `platforms.tiktok.posted` flag. Same video → both YouTube + TikTok, tracked separately, retried independently.

## After TikTok approval

When you get the approval email, run:

```bash
# 1. Swap sandbox → production credentials
bash ~/.config/teamzlab/tiktok-switch.sh prod

# 2. Fresh OAuth against production
cd "/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects/teamzlab-tools/teamz-company-automation/distribute/remotion"
node upload/tiktok-auth.js

# 3. Verify
bash ~/.config/teamzlab/tiktok-switch.sh   # shows current mode
```

Then `distribute.py next` posts to real public TikTok.

**Also rotate the client_secret** at developers.tiktok.com/app/7627188585389459476 → Credentials → regenerate. Update the new secret in `~/.config/teamzlab/tiktok-config.production.json`.

## Manual commands

```bash
# Check TikTok quota
cd "/Users/mdgolamkibriaemon/Projects/Teamz Lab Projects/teamz-projects/teamzlab-tools/teamz-company-automation/distribute/remotion"
node upload/tiktok-upload.js --quota

# Push next unposted from reel-history.json
node upload/tiktok-upload.js --from-history --count 1

# Bypass 4h gap (safe for inbox drafts)
node upload/tiktok-upload.js --from-history --count 2 --force

# Upload a specific file
node upload/tiktok-upload.js --file ~/Videos/teamzlab-reels/slug.mp4 --caption "..."
```

## Files on disk

```
~/.config/teamzlab/
├── tiktok-config.json            active — copy of sandbox OR production
├── tiktok-config.sandbox.json    backup
├── tiktok-config.production.json ready for approval swap
├── tiktok-token.json             current OAuth token
└── tiktok-switch.sh              mode switcher (prod|sandbox|no-arg for status)
```

## Caption strategy (for virality)

- Hub-specific hashtag pools defined in `content-engine.py` (HUB_HASHTAGS dict)
  and mirrored in `remotion/scripts/regen-tiktok-captions.py`
- Format: hook → engagement prompt → 🔗 url → 5 hashtags incl. `#fyp`
- Regenerate all existing captions: `python3 remotion/scripts/regen-tiktok-captions.py`

## Known constraints during sandbox

- Can only post to `@teamzlab` (configured in sandbox Target Users)
- Only inbox/draft mode works (direct publish needs audit + private account; Business accounts can't go private)
- Videos may silently not appear in inbox on some sandbox configs — known TikTok limitation, resolves after production approval

## If things break

| Symptom | Fix |
|---|---|
| `Token exchange failed: code_verifier invalid` | PKCE mismatch — restart fresh OAuth: `node upload/tiktok-auth.js` |
| `redirect_uri` error on authorize screen | Desktop redirect URI `http://localhost:8889/callback/` missing in Login Kit → add it in TikTok dev portal |
| `unaudited_client_can_only_post_to_private_accounts` | Make sure `tiktok-upload.js` uses `/v2/post/publish/inbox/video/init/` (inbox mode), NOT `/v2/post/publish/video/init/` (direct) |
| `EADDRINUSE :8889` | Kill stale auth server: `lsof -ti :8889 \| xargs kill -9` |
| No inbox notification on phone after upload | Sandbox silently drops — confirms production approval is still needed |
