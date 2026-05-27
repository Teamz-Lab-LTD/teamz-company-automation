#!/usr/bin/env python3
"""OpenRouter image-edit wrapper for ASO screenshot polish.

Cheapest workable image-to-image model: google/gemini-2.5-flash-image-preview
(~$0.04/edit, preserves UI, fast, supports multi-image input).

Usage:
  python3 openrouter_image_edit.py \\
    --prompt "..." \\
    --image src.png \\
    --output out.png \\
    [--model google/gemini-2.5-flash-image-preview]
"""
import argparse
import base64
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "google/gemini-2.5-flash-image-preview"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
KEY_FILE = Path.home() / ".config" / "teamzlab" / "openrouter-api-key.txt"


def _load_key() -> str:
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    k = os.environ.get("OPENROUTER_API_KEY", "")
    if not k:
        print(f"[err] no token at {KEY_FILE} or OPENROUTER_API_KEY env", file=sys.stderr)
        sys.exit(1)
    return k


def _data_url(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def edit(prompt: str, image_paths: list[Path], out_path: Path, model: str) -> bool:
    key = _load_key()
    content = [{"type": "text", "text": prompt}]
    for p in image_paths:
        if not p.exists():
            print(f"[err] missing input: {p}", file=sys.stderr)
            return False
        content.append({"type": "image_url", "image_url": {"url": _data_url(p)}})

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
    }).encode()

    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://teamzlab.com",
            "X-Title": "DeviceGPT ASO Screenshots",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=180) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"[err] HTTP {e.code}: {err[:800]}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[err] {e}", file=sys.stderr)
        return False

    choices = data.get("choices", [])
    if not choices:
        print(f"[err] no choices: {json.dumps(data)[:500]}", file=sys.stderr)
        return False

    msg = choices[0].get("message", {})
    images = msg.get("images") or []
    if images:
        img_obj = images[0]
        url = img_obj.get("image_url", {}).get("url") if isinstance(img_obj.get("image_url"), dict) else img_obj.get("image_url")
        if isinstance(url, str) and url.startswith("data:"):
            b64 = url.split(",", 1)[1]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(base64.b64decode(b64))
            usage = data.get("usage", {})
            print(f"[ok] wrote {out_path} ({out_path.stat().st_size//1024}KB)")
            if usage:
                print(f"[usage] {usage}")
            return True

    content_field = msg.get("content")
    if isinstance(content_field, list):
        for item in content_field:
            if isinstance(item, dict) and item.get("type") == "image_url":
                url = item.get("image_url", {}).get("url", "")
                if url.startswith("data:"):
                    b64 = url.split(",", 1)[1]
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(base64.b64decode(b64))
                    print(f"[ok] wrote {out_path} ({out_path.stat().st_size//1024}KB)")
                    return True

    print(f"[err] no image in response. msg={json.dumps(msg)[:600]}", file=sys.stderr)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--image", action="append", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    ok = edit(args.prompt, args.image, args.output, args.model)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
