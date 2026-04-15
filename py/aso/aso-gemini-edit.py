#!/usr/bin/env python3
"""Minimal Gemini 2.5 Flash Image (Nano Banana) edit_image wrapper.

Calls the REST API directly — no MCP server install needed.

Usage:
    python3 gemini_edit.py \\
        --prompt "Enhance this App Store screenshot..." \\
        --image /path/to/scaffold.png \\
        --image /path/to/style_template.jpg \\
        --output /path/to/v1.jpg
"""
import argparse
import base64
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path

MODEL = "nano-banana-pro-preview"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
KEY_FILE = Path.home() / ".config" / "teamzlab" / "gemini-api-key.txt"


def _load_key() -> str:
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    k = os.environ.get("GEMINI_API_KEY", "")
    if not k:
        print(f"[ERROR] No API key. Put it in {KEY_FILE} or set GEMINI_API_KEY.", file=sys.stderr)
        sys.exit(1)
    return k


def _b64(path: Path) -> dict:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return {"inlineData": {"mimeType": mime, "data": base64.b64encode(path.read_bytes()).decode()}}


def edit(prompt: str, image_paths: list[Path], out_path: Path) -> bool:
    key = _load_key()
    parts = [{"text": prompt}]
    for p in image_paths:
        if not p.exists():
            print(f"[ERROR] Missing input image: {p}", file=sys.stderr)
            return False
        parts.append(_b64(p))

    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }).encode()

    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json", "X-goog-api-key": key},
        method="POST",
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] HTTP {e.code}: {err[:500]}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return False

    # Extract image from response
    candidates = data.get("candidates", [])
    if not candidates:
        print(f"[ERROR] No candidates in response: {json.dumps(data)[:500]}", file=sys.stderr)
        return False

    for part in candidates[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(base64.b64decode(inline["data"]))
            size_kb = out_path.stat().st_size // 1024
            print(f"  [ok] Wrote {out_path} ({size_kb}KB)", file=sys.stderr)
            return True

    print(f"[ERROR] No image in response. Text: {json.dumps(data)[:500]}", file=sys.stderr)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--image", action="append", default=[], required=True,
                    help="Input image path (can repeat)")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    ok = edit(args.prompt, [Path(p) for p in args.image], Path(args.output))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
