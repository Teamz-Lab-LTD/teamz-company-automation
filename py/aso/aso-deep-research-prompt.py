#!/usr/bin/env python3
"""Generate a Deep Research SERP-analysis prompt for ChatGPT.

Why this exists: the global rule "SEO content workflow" says when SEO
scripts alone are not enough, ask the user for a ChatGPT Deep Research
prompt + paste results back. This script emits a standardized prompt
keyed to a specific app + target keywords so the user does not have to
rewrite it from scratch every time.

Usage:
    python3 aso-deep-research-prompt.py \
        --app no-trace-chat \
        --keywords-file keywords.txt \
        [--competitors signal,telegram,threema,session] \
        [--country us] \
        [--out prompt.txt]

The output is plain text — copy/paste into ChatGPT (or any deep-research
agent) verbatim. Then save the response and feed it back into
``aso-master-precheck.sh --deep-research result.json``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path


def _load_keywords(path: Path) -> list[str]:
    if not path.exists():
        print(f"ERROR: keyword file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]


def _maybe_load_app_card(landing_root: Path, app_slug: str) -> dict | None:
    candidate = landing_root / "src" / "content" / "apps" / f"{app_slug}.md"
    if not candidate.exists():
        return None
    text = candidate.read_text(encoding="utf-8")
    # naive YAML frontmatter pull — we only need top-level scalars
    front = {}
    if text.startswith("---"):
        try:
            end = text.index("\n---", 3)
            body = text[3:end]
            for line in body.splitlines():
                if ":" in line and not line.startswith(" "):
                    key, val = line.split(":", 1)
                    front[key.strip()] = val.strip().strip("'\"")
        except ValueError:
            pass
    return {"slug": app_slug, "frontmatter": front, "path": str(candidate)}


PROMPT_TEMPLATE = """\
You are a senior SEO + product researcher. Conduct a deep SERP intent
analysis for the keywords below as they relate to the app described.
Use live Google search (or your equivalent). Be specific, cite sources,
and avoid generic claims.

# App in scope
- Name: {app_name}
- Tagline: {app_tagline}
- One-line value: {app_value}
- Primary platforms: {app_platforms}
- Direct competitors (already paid / no-account messengers): {competitors}
- Country market for this research: {country}
- Date of this brief: {today}

# Target keywords (analyze EACH separately)
{keyword_block}

# For each keyword return a markdown table row with these columns
1. **Keyword** — verbatim
2. **Intent class** — one of: navigational | informational | transactional | commercial-investigation | comparison
3. **Top-1 result type** — listicle | how-to | landing page | comparison | forum | video | reddit | wikipedia | other
4. **Top-3 word count average** — integer
5. **Top-3 common H2 themes** — comma-separated, max 5
6. **Schema markup the winners use** — Article / HowTo / FAQPage / Product / SoftwareApplication / Review / WebPage / none
7. **Notable SERP features** — featured snippet, PAA, video, image pack, knowledge panel, "things to know", AI Overview
8. **Word-for-word PAA questions (top 3)** — quote exactly
9. **Common reader complaint about top results** — one short sentence
10. **Content gap our app could fill** — one short sentence specific to OUR app's USPs (no-account + code-based rooms + 3 privacy presets + anonymous public rooms)
11. **Recommended angle** — one short sentence
12. **Suggested blog title** — under 60 chars, click-worthy, includes the keyword

# Then add a closing section called "## Top 3 USP angles competitors do NOT cover"
List the 3 strongest topics our app can own based on what was missing in the SERP.

# Strict rules
- Do not invent statistics. If unsure, write "unknown" — that's fine.
- Do not pad. Short, sharp, specific.
- Do not recommend topics already covered well by Top-3 unless we have a clear differentiation.
- If a keyword is dominated by official brand pages (e.g. signal.org), say so and recommend a different angle.

When done, return ONE JSON code block at the very end with this shape so a script can parse it:

```json
{{
  "generated_at": "ISO-8601 timestamp",
  "app": "{app_slug}",
  "country": "{country}",
  "keywords": [
    {{
      "keyword": "...",
      "intent_class": "...",
      "top1_type": "...",
      "top3_word_count_avg": 0,
      "top3_h2_themes": ["..."],
      "winner_schema": ["..."],
      "serp_features": ["..."],
      "paa": ["..."],
      "common_complaint": "...",
      "content_gap": "...",
      "recommended_angle": "...",
      "blog_title": "..."
    }}
  ],
  "top_usp_angles": ["...", "...", "..."]
}}
```
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a Deep Research SERP prompt for ChatGPT.")
    parser.add_argument("--app", required=True, help="App slug (matches src/content/apps/<slug>.md if found)")
    parser.add_argument("--keywords-file", type=Path, required=True, help="One keyword per line, # for comments")
    parser.add_argument(
        "--competitors",
        default="signal,telegram,threema,session,whatsapp",
        help="Comma-separated competitor slugs (used in the prompt only)",
    )
    parser.add_argument("--country", default="us")
    parser.add_argument(
        "--landing-root",
        type=Path,
        default=Path.home() / "Projects" / "Teamz Lab Projects" / "teamz-projects" / "teamz-lab-generic-landing-pages",
        help="Landing-pages project root — used to auto-load app card metadata",
    )
    parser.add_argument("--out", type=Path, help="Write prompt to this path (default: stdout)")
    args = parser.parse_args()

    kws = _load_keywords(args.keywords_file)
    if not kws:
        print("ERROR: no keywords found in file.", file=sys.stderr)
        return 1

    card = _maybe_load_app_card(args.landing_root, args.app)
    front = (card or {}).get("frontmatter", {})

    prompt = PROMPT_TEMPLATE.format(
        app_slug=args.app,
        app_name=front.get("appName", args.app),
        app_tagline=front.get("tagline", "(no tagline on file)"),
        app_value=front.get("shortDescription", "(no short description on file)"),
        app_platforms=front.get("platforms", "ios+android+web"),
        competitors=args.competitors,
        country=args.country,
        today=date.today().isoformat(),
        keyword_block="\n".join(f"- {kw}" for kw in kws),
    )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(prompt, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
