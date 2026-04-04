# Pinterest Standard Access — Video Script & Application Guide

## Video Script (Record with QuickTime → Screen Recording, ~60 seconds)

### Scene 1: Show the website (10 sec)
**[Open browser → go to tool.teamzlab.com]**

> "This is Teamz Lab Tools — a directory of 2000+ free browser-based tools. We create educational content pins to help users discover these tools on Pinterest."

### Scene 2: Show the pin images (10 sec)
**[Open Finder → navigate to scripts/distribute/pin-images/ → show the folders and images]**

> "We have pre-designed pin images for each tool category — finance, developer tools, health, and general tools. Each image is optimized for Pinterest's recommended dimensions."

### Scene 3: Show OAuth authentication (15 sec)
**[Open terminal → run the command below]**

```bash
python3 scripts/distribute/pinterest-auth.py
```

> "Our distribution script authenticates through Pinterest's official OAuth2 flow. Users authorize via browser redirect, and the token is stored securely on their local machine."

**[Show the browser opening the Pinterest authorization page]**

### Scene 4: Show pin creation flow (15 sec)
**[Run the distribute command — it will fail with Trial error, that's fine]**

```bash
python3 scripts/distribute/distribute.py post "Free Finance Tools" scripts/distribute/articles/us-finance-tools-2026.md --platforms pinterest
```

> "The script reads the article content, selects the matching pin image, and creates a pin on the configured board via Pinterest's v5 API. Currently blocked by Trial access — requesting Standard to enable production pin creation."

### Scene 5: Show the boards (10 sec)
**[Open pinterest.com → show the 3 empty boards]**

> "We've set up three boards matching our content categories: Finance & Calculator Tools, Free Online Tools, and Web Dev & Tech Tools. Once Standard access is approved, pins will be automatically posted to the correct board."

---

## Application Form — Copy-Paste Answers

### App purpose (paste this):
```
Automated pin creation for tool.teamzlab.com — a directory of 2000+ free browser-based tools. Our Python distribution script creates pins with custom-designed images (1000x1500px) linking to individual tool pages. Each pin includes a descriptive title, tool summary, and direct link. We publish across 3 boards: Finance Tools, Developer Tools, and General Tools. All pins drive traffic to free, educational, no-signup browser tools. We post 1-3 pins per day, never spam. The script uses Pinterest's official v5 API with OAuth2 authentication.
```

### Use cases:
- ✅ Pin creation and scheduling
- ✅ Publishing content on Pinterest

### Audience:
- ✅ Pinners
- ✅ Creators

---

## Recording Tips
1. Use **QuickTime Player** → File → New Screen Recording
2. Keep it under **90 seconds**
3. Save as **.mp4** (Pinterest requires this)
4. No voiceover needed (but helps if you add one)
5. Show the terminal commands clearly — zoom in if needed
6. It's OK that the pin creation fails with "Trial access" error — that's literally why you're applying

---

## After Approval
Once Standard access is granted, run:
```bash
# Post all articles with pin images to Pinterest
python3 scripts/distribute/distribute.py post "TITLE" article.md --platforms pinterest
```

The script will automatically:
- Match article to the correct board (finance/dev/general)
- Use the pre-designed pin image from pin-images/
- Create the pin with title, description, and link to tool.teamzlab.com
