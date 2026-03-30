#!/usr/bin/env python3
"""
Teamz Lab Tools — Content Distribution Script
Posts articles to multiple platforms with duplicate detection.

Usage:
    python3 scripts/distribute/distribute.py post "Title" content.md [--platforms devto,hashnode,...]
    python3 scripts/distribute/distribute.py edit "slug" content.md [--platforms devto,bluesky,...]
    python3 scripts/distribute/distribute.py delete "slug" [--platforms devto,bluesky,...]
    python3 scripts/distribute/distribute.py list [--platform devto]          # List all posts on a platform
    python3 scripts/distribute/distribute.py status                           # Show posting history
    python3 scripts/distribute/distribute.py setup                            # Show setup instructions
    python3 scripts/distribute/distribute.py test                             # Test API connections

Platforms: devto, hashnode, medium, blogger, wordpress, tumblr, bluesky, mastodon, github_discussions, google_sites, pinterest
"""

import json
import os
import sys
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import ssl
import base64
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is expected locally
    yaml = None

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
HISTORY_FILE = SCRIPT_DIR / "history.json"
EXAMPLE_CONFIG = SCRIPT_DIR / "config.example.json"
ARTICLES_DIR = SCRIPT_DIR / "articles"

ALL_PLATFORMS = ["devto", "hashnode", "medium", "blogger", "wordpress", "tumblr", "bluesky", "mastodon", "github_discussions", "gitlab", "substack", "telegraph", "google_sites", "pinterest"]

# Localized footer text — article language should match tool language
LOCALIZED_FOOTERS = {
    "en": "Originally published at",
    "de": "Ursprünglich veröffentlicht auf",
    "nl": "Oorspronkelijk gepubliceerd op",
    "fr": "Publié à l'origine sur",
    "es": "Publicado originalmente en",
    "pt": "Publicado originalmente em",
    "pl": "Pierwotnie opublikowano na",
    "cs": "Původně publikováno na",
    "fi": "Alun perin julkaistu osoitteessa",
    "sv": "Ursprungligen publicerad på",
    "nb": "Opprinnelig publisert på",
    "da": "Oprindeligt udgivet på",
    "ja": "初出掲載",
    "it": "Pubblicato originariamente su",
    "ar": "نُشر في الأصل على",
    "id": "Pertama kali diterbitkan di",
    "vi": "Được xuất bản lần đầu tại",
}

# SSL context for HTTPS requests
SSL_CTX = ssl.create_default_context()


# ─── Helpers ───────────────────────────────────────────────────────────────────

def load_config():
    if not CONFIG_FILE.exists():
        print(f"\n  ERROR: Config file not found: {CONFIG_FILE}")
        print(f"  Copy the example and fill in your API keys:")
        print(f"    cp scripts/distribute/config.example.json scripts/distribute/config.json")
        print(f"  Then run: python3 scripts/distribute/distribute.py setup")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_history():
    if not HISTORY_FILE.exists():
        return {"posts": []}
    with open(HISTORY_FILE) as f:
        return json.load(f)


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"  History saved to {HISTORY_FILE}")


def content_hash(title, body):
    return hashlib.sha256(f"{title}|{body[:500]}".encode()).hexdigest()[:16]


def is_duplicate(history, slug, platform):
    for post in history["posts"]:
        if post["slug"] == slug and platform in post.get("platforms", {}):
            return post["platforms"][platform]
    return None


def api_request(url, data=None, headers=None, method=None):
    """Make HTTP request, return (status_code, response_dict)."""
    if headers is None:
        headers = {}
    if "User-Agent" not in headers:
        headers["User-Agent"] = "TeamzLabDistribute/1.0"
    if data is not None and isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
    if method is None:
        method = "POST" if data else "GET"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, {"raw": body}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"error": body}
    except Exception as e:
        return 0, {"error": str(e)}


def api_request_form(url, form_fields, headers=None):
    """POST application/x-www-form-urlencoded (Pinterest OAuth token refresh)."""
    if headers is None:
        headers = {}
    if "User-Agent" not in headers:
        headers["User-Agent"] = "TeamzLabDistribute/1.0"
    data = urllib.parse.urlencode(form_fields).encode("utf-8")
    if "Content-Type" not in headers:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, {"raw": body}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"error": body}


def slugify(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:80]


def normalize_tags(raw_tags, default="tools,free,web"):
    """Normalize tag frontmatter from YAML lists or comma-separated strings."""
    source = raw_tags if raw_tags not in (None, "") else default

    if isinstance(source, list):
        tags = [str(tag).strip() for tag in source]
    elif isinstance(source, str):
        tags = [tag.strip() for tag in source.split(",")]
    else:
        tags = [str(source).strip()]

    tags = [tag for tag in tags if tag]
    return tags or [tag.strip() for tag in default.split(",") if tag.strip()]


def read_markdown(filepath):
    with open(filepath) as f:
        content = f.read()

    # Extract frontmatter if present (---\n...\n---)
    meta = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            if yaml:
                try:
                    parsed = yaml.safe_load(frontmatter)
                    if isinstance(parsed, dict):
                        meta = parsed
                    else:
                        meta = {}
                except Exception:
                    meta = {}
            if not meta:
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        meta[key.strip()] = val.strip().strip('"').strip("'")
            body = parts[2].strip()

    return meta, body


def truncate(text, max_len=300):
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


# ─── Platform Posters ─────────────────────────────────────────────────────────

def post_devto(config, title, body, tags, canonical_url):
    """Post article to Dev.to via REST API."""
    cfg = config["devto"]
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    article = {
        "article": {
            "title": title,
            "body_markdown": body,
            "published": True,
            "tags": [clean for clean in (re.sub(r'[^a-zA-Z0-9]', '', t) for t in tags[:4]) if clean],  # Dev.to: alphanumeric only, max 4
        }
    }
    if canonical_url:
        article["article"]["canonical_url"] = canonical_url

    status, resp = api_request(
        "https://dev.to/api/articles",
        data=article,
        headers={"api-key": cfg["api_key"]}
    )

    if status in (200, 201):
        return resp.get("url", resp.get("canonical_url", "posted")), None

    # If canonical_url is already taken, retry without it
    if status == 422 and canonical_url and "canonical" in json.dumps(resp).lower():
        del article["article"]["canonical_url"]
        status, resp = api_request(
            "https://dev.to/api/articles",
            data=article,
            headers={"api-key": cfg["api_key"]}
        )
        if status in (200, 201):
            return resp.get("url", resp.get("canonical_url", "posted")), None

    return None, f"HTTP {status}: {json.dumps(resp)[:200]}"


def post_hashnode(config, title, body, tags, canonical_url):
    """Post article to Hashnode via GraphQL API."""
    cfg = config["hashnode"]
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    tag_objects = [
        {"slug": slugify(tag), "name": tag}
        for tag in tags[:5]
        if slugify(tag)
    ]

    query = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post {
          url
          id
        }
      }
    }
    """
    variables = {
        "input": {
            "title": title,
            "contentMarkdown": body,
            "publicationId": cfg["publication_id"],
            "tags": tag_objects,
        }
    }
    if canonical_url:
        variables["input"]["originalArticleURL"] = canonical_url

    status, resp = api_request(
        "https://gql.hashnode.com",
        data={"query": query, "variables": variables},
        headers={"Authorization": cfg["api_key"]}
    )

    if status == 200 and "data" in resp:
        post_data = resp.get("data", {}).get("publishPost", {}).get("post", {})
        return post_data.get("url", "posted"), None
    errors = resp.get("errors", [{}])
    err_msg = errors[0].get("message", json.dumps(resp)[:200]) if errors else json.dumps(resp)[:200]
    return None, f"HTTP {status}: {err_msg}"


def post_medium(config, title, body, tags, canonical_url):
    """Post article to Medium via REST API."""
    cfg = config["medium"]
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    # First get user ID
    status, user_resp = api_request(
        "https://api.medium.com/v1/me",
        headers={
            "Authorization": f"Bearer {cfg['integration_token']}",
            "Accept": "application/json"
        }
    )
    if status != 200:
        return None, f"Failed to get user: HTTP {status}"

    user_id = user_resp.get("data", {}).get("id")
    if not user_id:
        return None, "Could not get Medium user ID"

    post_data = {
        "title": title,
        "contentFormat": "markdown",
        "content": f"# {title}\n\n{body}",
        "tags": tags[:5],
        "publishStatus": "public"
    }
    if canonical_url:
        post_data["canonicalUrl"] = canonical_url

    status, resp = api_request(
        f"https://api.medium.com/v1/users/{user_id}/posts",
        data=post_data,
        headers={
            "Authorization": f"Bearer {cfg['integration_token']}",
            "Accept": "application/json"
        }
    )

    if status in (200, 201):
        return resp.get("data", {}).get("url", "posted"), None
    return None, f"HTTP {status}: {json.dumps(resp)[:200]}"


def refresh_google_token(creds_file):
    """Refresh Google OAuth2 access token using refresh token."""
    with open(creds_file) as f:
        creds = json.load(f)

    refresh_token = creds.get("refresh_token")
    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")

    if not all([refresh_token, client_id, client_secret]):
        return None

    import urllib.parse as up
    token_data = up.urlencode({
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }).encode()

    status, resp = api_request("https://oauth2.googleapis.com/token", data=None, headers={"User-Agent": "TeamzLabDistribute/1.0"})
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=token_data,
        headers={"User-Agent": "TeamzLabDistribute/1.0"})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
            tokens = json.loads(r.read())
            new_token = tokens.get("access_token")
            if new_token:
                creds["access_token"] = new_token
                with open(creds_file, "w") as f:
                    json.dump(creds, f, indent=2)
                return new_token
    except Exception:
        pass
    return None


def post_blogger(config, title, body, tags, canonical_url):
    """Post article to Blogger via REST API."""
    cfg = config["blogger"]
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    creds_file = os.path.expanduser(cfg["credentials_file"])
    if not os.path.exists(creds_file):
        return None, f"Credentials file not found: {creds_file}. Run: python3 scripts/distribute/blogger-auth.py"

    with open(creds_file) as f:
        creds = json.load(f)

    access_token = creds.get("access_token")
    if not access_token:
        return None, "No access_token. Run: python3 scripts/distribute/blogger-auth.py"

    # Convert markdown to basic HTML
    html_body = markdown_to_html(body)

    post_data = {
        "kind": "blogger#post",
        "title": title,
        "content": html_body,
        "labels": tags[:5]
    }

    status, resp = api_request(
        f"https://www.googleapis.com/blogger/v3/blogs/{cfg['blog_id']}/posts/",
        data=post_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if status in (200, 201):
        return resp.get("url", "posted"), None

    # Try refreshing token
    if status == 401:
        new_token = refresh_google_token(creds_file)
        if new_token:
            status, resp = api_request(
                f"https://www.googleapis.com/blogger/v3/blogs/{cfg['blog_id']}/posts/",
                data=post_data,
                headers={"Authorization": f"Bearer {new_token}"}
            )
            if status in (200, 201):
                return resp.get("url", "posted"), None

        return None, "Access token expired. Run: python3 scripts/distribute/blogger-auth.py"
    return None, f"HTTP {status}: {json.dumps(resp)[:200]}"


def post_wordpress(config, title, body, tags, canonical_url):
    """Post article to WordPress.com via REST API (OAuth2)."""
    cfg = config["wordpress"]
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    # Check for OAuth2 access token (from wordpress-auth.py)
    access_token = cfg.get("access_token", "")
    if not access_token:
        return None, "No access_token. Run: python3 scripts/distribute/wordpress-auth.py CLIENT_ID CLIENT_SECRET"

    post_data = {
        "title": title,
        "content": markdown_to_html(body),
        "status": "publish",
        "format": "standard"
    }
    if tags:
        post_data["tags"] = ",".join(tags[:5])

    site = cfg["site"]
    status, resp = api_request(
        f"https://public-api.wordpress.com/rest/v1.1/sites/{site}/posts/new",
        data=post_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if status in (200, 201):
        return resp.get("URL", resp.get("short_URL", "posted")), None
    return None, f"HTTP {status}: {json.dumps(resp)[:200]}"


def post_tumblr(config, title, body, tags, canonical_url):
    """Post to Tumblr via v2 API with OAuth1."""
    cfg = config["tumblr"]
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    # Tumblr NPF (Neue Post Format) via API key auth
    # Using simple API key auth for creating posts
    import hmac
    import time
    import binascii

    blog = cfg["blog_name"]
    consumer_key = cfg["consumer_key"]
    consumer_secret = cfg["consumer_secret"]
    oauth_token = cfg["oauth_token"]
    oauth_secret = cfg["oauth_secret"]

    url = f"https://api.tumblr.com/v2/blog/{blog}/post"

    # Build OAuth 1.0a signature
    timestamp = str(int(time.time()))
    nonce = hashlib.md5(f"{timestamp}{consumer_key}".encode()).hexdigest()

    params = {
        "oauth_consumer_key": consumer_key,
        "oauth_token": oauth_token,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp,
        "oauth_nonce": nonce,
        "oauth_version": "1.0",
        "type": "text",
        "title": title,
        "body": markdown_to_html(body),
        "tags": ",".join(tags[:10]),
        "format": "html",
        "state": "published"
    }

    # Create signature base string
    sorted_params = "&".join(f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
                             for k, v in sorted(params.items()))
    base_string = f"POST&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(sorted_params, safe='')}"
    signing_key = f"{urllib.parse.quote(consumer_secret, safe='')}&{urllib.parse.quote(oauth_secret, safe='')}"
    signature = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()

    # Build Authorization header
    auth_header = (
        f'OAuth oauth_consumer_key="{consumer_key}", '
        f'oauth_token="{oauth_token}", '
        f'oauth_signature_method="HMAC-SHA1", '
        f'oauth_timestamp="{timestamp}", '
        f'oauth_nonce="{nonce}", '
        f'oauth_version="1.0", '
        f'oauth_signature="{urllib.parse.quote(signature, safe="")}"'
    )

    # Post data (form-encoded, not JSON)
    post_params = {
        "type": "text",
        "title": title,
        "body": markdown_to_html(body),
        "tags": ",".join(tags[:10]),
        "format": "html",
        "state": "published"
    }
    post_body = urllib.parse.urlencode(post_params).encode()

    req = urllib.request.Request(url, data=post_body, method="POST")
    req.add_header("Authorization", auth_header)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            post_id = result.get("response", {}).get("id", "")
            return f"https://{blog}.tumblr.com/post/{post_id}", None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        return None, f"HTTP {e.code}: {err_body[:200]}"
    except Exception as e:
        return None, str(e)


def post_bluesky(config, title, body, tags, canonical_url):
    """Post to Bluesky via AT Protocol."""
    cfg = config["bluesky"]
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    # Create session
    status, session = api_request(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        data={
            "identifier": cfg["handle"],
            "password": cfg["app_password"]
        }
    )
    if status != 200:
        return None, f"Auth failed: HTTP {status}"

    did = session.get("did")
    access_jwt = session.get("accessJwt")

    # Create post text with link
    text = f"{title}\n\n"
    summary = truncate(body.split("\n")[0] if body else "", 200)
    if summary:
        text += f"{summary}\n\n"
    if canonical_url:
        text += canonical_url
    if tags:
        text += "\n\n" + " ".join(f"#{t.replace(' ', '')}" for t in tags[:5])

    # Truncate to 300 chars (Bluesky limit)
    if len(text) > 300:
        text = text[:297] + "..."

    # Build facets for link detection
    facets = []
    if canonical_url and canonical_url in text:
        byte_start = text.encode("utf-8").index(canonical_url.encode("utf-8"))
        byte_end = byte_start + len(canonical_url.encode("utf-8"))
        facets.append({
            "index": {"byteStart": byte_start, "byteEnd": byte_end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": canonical_url}]
        })

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": now,
    }
    if facets:
        record["facets"] = facets

    # Add link card embed if canonical URL provided
    if canonical_url:
        record["embed"] = {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": canonical_url,
                "title": title,
                "description": summary
            }
        }

    status, resp = api_request(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        data={
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": record
        },
        headers={"Authorization": f"Bearer {access_jwt}"}
    )

    if status == 200:
        uri = resp.get("uri", "")
        # Convert AT URI to web URL
        rkey = uri.split("/")[-1] if "/" in uri else ""
        handle = cfg["handle"]
        web_url = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else "posted"
        return web_url, None
    return None, f"HTTP {status}: {json.dumps(resp)[:200]}"


def post_mastodon(config, title, body, tags, canonical_url):
    """Post to Mastodon via REST API."""
    cfg = config["mastodon"]
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    instance = cfg["instance"].rstrip("/")

    # Build status text
    text = f"{title}\n\n"
    summary = truncate(body.split("\n")[0] if body else "", 250)
    if summary:
        text += f"{summary}\n\n"
    if canonical_url:
        text += f"{canonical_url}\n\n"
    if tags:
        text += " ".join(f"#{t.replace(' ', '').replace('-', '')}" for t in tags[:5])

    # Mastodon limit is 500 chars
    if len(text) > 500:
        text = text[:497] + "..."

    status_code, resp = api_request(
        f"{instance}/api/v1/statuses",
        data={"status": text, "visibility": "public"},
        headers={"Authorization": f"Bearer {cfg['access_token']}"}
    )

    if status_code in (200, 201):
        return resp.get("url", "posted"), None
    return None, f"HTTP {status_code}: {json.dumps(resp)[:200]}"


def post_github_discussions(config, title, body, tags, canonical_url):
    """Post to GitHub Discussions via GraphQL API (uses gh CLI)."""
    cfg = config.get("github_discussions", {})
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    repo_id = cfg.get("repo_id", "")
    category_id = cfg.get("category_id", "")
    if not repo_id or not category_id:
        return None, "Missing repo_id or category_id in config"

    # Build body with canonical link
    full_body = body
    if canonical_url:
        full_body += f"\n\n---\n\nOriginally published at [{canonical_url}]({canonical_url})"

    # Escape for JSON
    escaped_body = json.dumps(full_body)[1:-1]  # Remove outer quotes
    escaped_title = json.dumps(title)[1:-1]

    query = f'''mutation {{
      createDiscussion(input: {{
        repositoryId: "{repo_id}",
        categoryId: "{category_id}",
        title: "{escaped_title}",
        body: "{escaped_body}"
      }}) {{
        discussion {{ url }}
      }}
    }}'''

    # Use subprocess to call gh CLI (avoids needing separate GitHub token)
    import subprocess
    try:
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            resp = json.loads(result.stdout)
            url = resp.get("data", {}).get("createDiscussion", {}).get("discussion", {}).get("url", "")
            if url:
                return url, None
            return None, f"No URL in response: {result.stdout[:200]}"
        return None, f"gh CLI error: {result.stderr[:200]}"
    except FileNotFoundError:
        return None, "gh CLI not installed"
    except subprocess.TimeoutExpired:
        return None, "gh CLI timed out"
    except Exception as e:
        return None, str(e)


def markdown_to_plain_excerpt(md, max_len=800):
    """Strip basic markdown for Pinterest description (API limit 800 chars)."""
    t = md or ""
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 — \2", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return truncate(t, max_len)


def pinterest_refresh_access_token(cfg, creds_path):
    """Refresh Pinterest access token; update credentials file. Returns new token or None."""
    with open(creds_path) as f:
        creds = json.load(f)
    refresh_token = creds.get("refresh_token")
    if not refresh_token:
        return None
    app_id = cfg.get("app_id", "")
    app_secret = cfg.get("app_secret", "")
    if not app_id or not app_secret:
        return None
    basic = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
    status, resp = api_request_form(
        "https://api.pinterest.com/v5/oauth/token",
        {"grant_type": "refresh_token", "refresh_token": refresh_token},
        headers={"Authorization": f"Basic {basic}"},
    )
    if status != 200:
        return None
    access = resp.get("access_token")
    if not access:
        return None
    creds["access_token"] = access
    if resp.get("refresh_token"):
        creds["refresh_token"] = resp["refresh_token"]
    with open(creds_path, "w") as f:
        json.dump(creds, f, indent=2)
    try:
        os.chmod(creds_path, 0o600)
    except OSError:
        pass
    return access


def post_gitlab(config, title, body, tags, canonical_url):
    """Post to GitLab Snippets — dofollow backlinks, DA 95+."""
    cfg = config.get("gitlab", {})
    token = cfg.get("access_token", "")
    if not token:
        token_file = os.path.expanduser("~/.config/teamzlab/gitlab-token.txt")
        if os.path.exists(token_file):
            with open(token_file) as f:
                token = f.read().strip()
    if not token:
        return None, "No GitLab access_token"

    try:
        # Add footer link to body
        body_with_link = body + "\n\n---\n\n*Originally published at [tool.teamzlab.com](https://tool.teamzlab.com)*"

        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        payload = json.dumps({
            "title": title,
            "description": f"Free browser-based tools — no signup, 100% private. Visit https://tool.teamzlab.com",
            "visibility": "public",
            "files": [{
                "file_path": f"{slug}.md",
                "content": f"# {title}\n\n{body_with_link}"
            }]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://gitlab.com/api/v4/snippets',
            data=payload,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'PRIVATE-TOKEN': token
            }
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        snippet_id = result.get('id')
        web_url = result.get('web_url')
        if web_url:
            return web_url, None
        elif snippet_id:
            return f"https://gitlab.com/-/snippets/{snippet_id}", None
        else:
            return None, result.get('error', result.get('message', 'Unknown GitLab error'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')[:200] if hasattr(e, 'read') else ''
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, str(e)[:120]


def post_substack(config, title, body, tags, canonical_url):
    """Post to Substack — dofollow backlinks, DA 90+. Uses python-substack library."""
    cfg = config.get("substack", {})
    pub_url = cfg.get("publication_url", "")
    if not pub_url:
        return None, "No Substack publication_url in config"

    try:
        from substack import Api
        from substack.post import Post as SubstackPost

        # Auth: cookie string (from file or config) or email/password
        cookie_string = cfg.get("cookies_string", "")
        if not cookie_string:
            cookie_file = os.path.expanduser("~/.config/teamzlab/substack-cookie-string.txt")
            if os.path.exists(cookie_file):
                with open(cookie_file) as f:
                    cookie_string = f.read().strip()

        email = cfg.get("email", "")
        password = cfg.get("password", "")

        if cookie_string:
            api = Api(cookies_string=cookie_string, publication_url=pub_url)
        else:
            return None, "No Substack cookie. Run: browser DevTools → Cookies → substack.sid → save as 'substack.sid=VALUE' to ~/.config/teamzlab/substack-cookie-string.txt"

        try:
            user_id = api.get_user_id()
        except Exception:
            return None, "Substack cookie EXPIRED. Fix: browser DevTools → Application → Cookies → substack.com → copy substack.sid value → save as 'substack.sid=VALUE' to ~/.config/teamzlab/substack-cookie-string.txt"

        post = SubstackPost(
            title=title,
            subtitle="Free browser-based tools — no signup, 100% private",
            user_id=user_id,
            audience="everyone",
        )

        def md_inline_to_chunks(text):
            """Convert markdown inline formatting to Substack content chunks."""
            chunks = []
            pattern = r'(\*\*\[([^\]]+)\]\(([^)]+)\)\*\*|\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|\*(.+?)\*)'
            last_end = 0
            for m in re.finditer(pattern, text):
                if m.start() > last_end:
                    plain = text[last_end:m.start()]
                    if plain:
                        chunks.append({'content': plain})
                if m.group(2) and m.group(3):  # **[text](url)** — bold link
                    chunks.append({'content': m.group(2), 'marks': [{'type': 'bold'}, {'type': 'link', 'href': m.group(3)}]})
                elif m.group(4) and m.group(5):  # [text](url) — link
                    chunks.append({'content': m.group(4), 'marks': [{'type': 'link', 'href': m.group(5)}]})
                elif m.group(6):  # **text** — bold
                    chunks.append({'content': m.group(6), 'marks': [{'type': 'bold'}]})
                elif m.group(7):  # *text* — italic
                    chunks.append({'content': m.group(7), 'marks': [{'type': 'italic'}]})
                last_end = m.end()
            if last_end < len(text):
                remaining = text[last_end:]
                if remaining:
                    chunks.append({'content': remaining})
            if not chunks:
                chunks.append({'content': text})
            return chunks

        # Convert markdown paragraphs to Substack content blocks
        paragraphs = re.split(r'\n\n+', body.strip())
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if p.startswith('#'):
                level = len(re.match(r'^(#+)', p).group(1))
                text = re.sub(r'^#+\s*', '', p)
                post.add({'type': 'heading', 'content': text, 'level': min(level, 3)})
            elif p.startswith('---'):
                post.add({'type': 'horizontal_rule'})
            elif p.startswith('|'):
                rows = [r.strip() for r in p.split('\n') if r.strip() and '---' not in r]
                for row in rows:
                    cells = [c.strip() for c in row.split('|') if c.strip()]
                    chunks = md_inline_to_chunks(' | '.join(cells))
                    post.add({'type': 'paragraph', 'content': chunks})
            elif p.startswith('- ') or p.startswith('* '):
                # List items — each as separate paragraph with bullet
                for line in p.split('\n'):
                    line = re.sub(r'^[-*]\s+', '', line.strip())
                    if line:
                        chunks = md_inline_to_chunks(line)
                        post.add({'type': 'paragraph', 'content': [{'content': '• '}] + chunks})
            else:
                # Handle multi-line paragraphs
                lines = p.split('\n')
                all_chunks = []
                for i, line in enumerate(lines):
                    all_chunks.extend(md_inline_to_chunks(line))
                    if i < len(lines) - 1:
                        all_chunks.append({'content': '\n'})
                post.add({'type': 'paragraph', 'content': all_chunks})

        # Add footer with link
        post.add({'type': 'horizontal_rule'})
        post.add({'type': 'paragraph', 'content': [
            {'content': 'Originally published at '},
            {'content': 'tool.teamzlab.com', 'marks': [{'type': 'link', 'href': 'https://tool.teamzlab.com'}]}
        ]})

        # Create and publish
        draft = api.post_draft(post.get_draft())
        draft_id = draft.get("id")
        if draft_id:
            api.prepublish_draft(draft_id)
            api.publish_draft(draft_id)
            # Use the canonical URL from Substack's response, or construct from draft ID
            url = f"https://substack.com/home/post/p-{draft_id}"
            return url, None
        else:
            return None, "Draft creation failed"

    except ImportError:
        return None, "python-substack not installed (pip install python-substack)"
    except Exception as e:
        return None, str(e)[:120]


def post_telegraph(config, title, body, tags, canonical_url):
    """Post to Telegraph (telegra.ph) — dofollow backlinks, DA 90+."""
    cfg = config.get("telegraph", {})
    token = cfg.get("access_token", "")
    if not token:
        token_file = os.path.expanduser("~/.config/teamzlab/telegraph-token.txt")
        if os.path.exists(token_file):
            with open(token_file) as f:
                token = f.read().strip()
    if not token:
        return None, "No Telegraph access_token"

    def md_to_nodes(md):
        """Convert markdown to Telegraph Node array."""
        nodes = []
        paragraphs = re.split(r'\n\n+', md.strip())
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            # Horizontal rule
            if re.match(r'^---+$', p):
                nodes.append({"tag": "hr"})
                continue
            # Headers
            h_match = re.match(r'^(#{1,3})\s+(.+)$', p)
            if h_match:
                level = len(h_match.group(1))
                tag = "h3" if level <= 2 else "h4"
                nodes.append({"tag": tag, "children": inline_parse(h_match.group(2))})
                continue
            # Table — convert to simple text
            if '|' in p and '---' in p:
                rows = [r.strip() for r in p.split('\n') if r.strip() and '---' not in r]
                for row in rows:
                    cells = [c.strip() for c in row.split('|') if c.strip()]
                    nodes.append({"tag": "p", "children": inline_parse(' | '.join(cells))})
                continue
            # Regular paragraph (may have multiple lines)
            children = []
            lines = p.split('\n')
            for i, line in enumerate(lines):
                children.extend(inline_parse(line))
                if i < len(lines) - 1:
                    children.append({"tag": "br"})
            nodes.append({"tag": "p", "children": children})
        return nodes

    def inline_parse(text):
        """Parse inline markdown (bold, italic, links) into Telegraph children."""
        children = []
        # Process links, bold, italic via regex
        pattern = r'(\*\*(.+?)\*\*|\*(.+?)\*|\[([^\]]+)\]\(([^)]+)\))'
        last_end = 0
        for m in re.finditer(pattern, text):
            # Add text before match
            if m.start() > last_end:
                children.append(text[last_end:m.start()])
            if m.group(2):  # Bold
                children.append({"tag": "b", "children": [m.group(2)]})
            elif m.group(3):  # Italic
                children.append({"tag": "i", "children": [m.group(3)]})
            elif m.group(4) and m.group(5):  # Link
                children.append({"tag": "a", "attrs": {"href": m.group(5)}, "children": [m.group(4)]})
            last_end = m.end()
        # Add remaining text
        if last_end < len(text):
            children.append(text[last_end:])
        if not children:
            children.append(text)
        return children

    try:
        nodes = md_to_nodes(body)
        # Add properly formatted footer with dofollow link
        nodes.append({"tag": "hr"})
        nodes.append({"tag": "p", "children": [
            {"tag": "i", "children": [
                "Originally published at ",
                {"tag": "a", "attrs": {"href": "https://tool.teamzlab.com"}, "children": ["tool.teamzlab.com"]}
            ]}
        ]})
        payload = json.dumps({
            'access_token': token,
            'title': title[:256],
            'author_name': cfg.get('author_name', 'Teamz Lab'),
            'author_url': cfg.get('author_url', 'https://tool.teamzlab.com'),
            'content': nodes,
            'return_content': False,
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.telegra.ph/createPage',
            data=payload,
            method='POST',
            headers={'Content-Type': 'application/json'}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        if result.get('ok') and result.get('result', {}).get('url'):
            return result['result']['url'], None
        else:
            return None, result.get('error', 'Unknown Telegraph error')
    except Exception as e:
        return None, str(e)[:120]


def post_google_sites(config, title, body, tags, canonical_url):
    """Post to Google Sites via Apps Script bridge — dofollow backlinks, DA 96+.

    Creates a publicly-viewable Google Doc organized under a 'Teamz Lab Articles' folder.
    The Apps Script web app handles doc creation, sharing, and tracking.
    """
    cfg = config.get("google_sites", {})
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    webapp_url = cfg.get("webapp_url", "").strip()
    secret_key = cfg.get("secret_key", "")

    if not secret_key:
        key_file = os.path.expanduser("~/.config/teamzlab/google-sites-key.txt")
        if os.path.exists(key_file):
            with open(key_file) as f:
                secret_key = f.read().strip()

    if not webapp_url:
        return None, "No webapp_url configured. Deploy google-sites-bridge.gs as Apps Script web app first"
    if not secret_key:
        return None, "No secret_key configured. Set it in config or ~/.config/teamzlab/google-sites-key.txt"

    try:
        # Add footer link
        body_with_link = body + "\n\n---\n\n*Originally published at [tool.teamzlab.com](https://tool.teamzlab.com)*"

        payload = json.dumps({
            "key": secret_key,
            "action": "create",
            "title": title[:256],
            "body": body_with_link,
            "tags": tags[:10] if tags else [],
            "canonical_url": canonical_url or ""
        }).encode("utf-8")

        req = urllib.request.Request(
            webapp_url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        if result.get("status") == "created" and result.get("url"):
            return result["url"], None
        else:
            return None, result.get("error", "Unknown Google Sites bridge error")

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")[:200] if hasattr(e, "read") else ""
        return None, f"HTTP {e.code}: {err_body}"
    except Exception as e:
        return None, str(e)[:120]


def post_pinterest(config, title, body, tags, canonical_url, pin_image_url=""):
    """
    Create a Pin on Pinterest (v5 API). Requires a public HTTPS image URL.
    Per-article: frontmatter pin_image or og_image; fallback: default_pin_image_url in config.
    """
    cfg = config.get("pinterest", {})
    if not cfg.get("enabled"):
        return None, "Platform disabled in config"

    creds_path = os.path.expanduser(
        cfg.get("credentials_file", "~/.config/teamzlab/pinterest-credentials.json")
    )
    if not os.path.isfile(creds_path):
        return None, f"Missing credentials. Run: python3 {SCRIPT_DIR}/pinterest-auth.py"

    defaults = config.get("defaults", {})
    site_url = defaults.get("site_url", "https://tool.teamzlab.com")

    image_url = (pin_image_url or "").strip() or (cfg.get("default_pin_image_url") or "").strip()
    if not image_url:
        return (
            None,
            "Pinterest needs an image URL: set pin_image (or og_image) in article frontmatter "
            "or pinterest.default_pin_image_url in config",
        )

    if not image_url.startswith("https://"):
        return None, "pin image URL must be https:// (Pinterest API requirement)"

    board_id = (cfg.get("board_id") or "").strip()
    if not board_id:
        return None, "Set pinterest.board_id in config (run pinterest-auth.py to list boards)"

    link = (canonical_url or "").strip() or site_url
    if len(link) > 2048:
        link = link[:2045] + "..."

    desc = markdown_to_plain_excerpt(body, 760)
    if tags:
        tag_bits = " ".join("#" + re.sub(r"\s+", "", t) for t in tags[:8])
        desc = truncate(desc + "\n\n" + tag_bits, 800)

    title_pin = title[:100] if title else "Post"

    payload = {
        "board_id": board_id,
        "title": title_pin,
        "description": desc,
        "link": link,
        "media_source": {"source_type": "image_url", "url": image_url},
    }

    with open(creds_path) as f:
        creds = json.load(f)
    access = creds.get("access_token")
    if not access:
        return None, "No access_token in credentials file. Run pinterest-auth.py"

    def create_with_token(token):
        return api_request(
            "https://api.pinterest.com/v5/pins",
            data=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    status, resp = create_with_token(access)
    if status == 401:
        new_access = pinterest_refresh_access_token(cfg, creds_path)
        if new_access:
            status, resp = create_with_token(new_access)

    if status in (200, 201):
        pin_id = resp.get("id", "")
        if pin_id:
            return f"https://www.pinterest.com/pin/{pin_id}/", None
        return resp.get("link") or "posted", None

    return None, f"HTTP {status}: {json.dumps(resp)[:350]}"


# ─── Markdown to HTML (basic) ─────────────────────────────────────────────────

def markdown_to_html(md):
    """Convert basic markdown to HTML for platforms that need it."""
    html = md

    # Headers
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Links
    html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)

    # Inline code
    html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)

    # Lists
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"(<li>.*</li>\n?)+", lambda m: f"<ul>\n{m.group(0)}</ul>\n", html)

    # Paragraphs (double newline)
    paragraphs = html.split("\n\n")
    processed = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith("<h") or p.startswith("<ul") or p.startswith("<ol"):
            processed.append(p)
        else:
            processed.append(f"<p>{p}</p>")
    html = "\n\n".join(processed)

    return html


# ─── Commands ─────────────────────────────────────────────────────────────────

def update_github_blog_readme(history):
    """Auto-update the teamz-lab-blogs repo README with all distributed articles."""
    REPO = "Teamz-Lab-LTD/teamz-lab-blogs"
    try:
        import subprocess

        repo_root = SCRIPT_DIR.parent.parent
        excluded_hubs = {
            "branding", "shared", "docs", "scripts", "logs", ".github",
            "__pycache__", "icons", "fonts", "images", "assets", "node_modules"
        }
        hub_counts = {}
        for hub_dir in repo_root.iterdir():
            if not hub_dir.is_dir() or hub_dir.name.startswith(".") or hub_dir.name in excluded_hubs:
                continue
            tool_count = len(list(hub_dir.glob("*/index.html")))
            if tool_count:
                hub_counts[hub_dir.name] = tool_count

        total_tools = sum(hub_counts.values())
        live_hubs = len(hub_counts)
        country_rows = [
            ("🇺🇸 United States", hub_counts.get("us", 0), "tax, finance, military", "us"),
            ("🇬🇧 United Kingdom", hub_counts.get("uk", 0), "tax, MTD, leave, childcare", "uk"),
            ("🇩🇪 Germany", hub_counts.get("de", 0), "Brutto-Netto, Grundsteuer, Elterngeld", "de"),
            ("🇫🇷 France", hub_counts.get("fr", 0), "APL, Prime d'activité, CROUS", "fr"),
            ("🇧🇪 Belgium", hub_counts.get("be", 0), "bruto-netto, registratierechten, erfbelasting", "be"),
            ("🇱🇺 Luxembourg", hub_counts.get("lu", 0), "Gehaltsrechner, Steuer, Grenzgänger", "lu"),
            ("🇵🇱 Poland", hub_counts.get("pl", 0), "wynagrodzenia, kredyt, PIT", "pl"),
            ("🇨🇿 Czech Republic", hub_counts.get("cz", 0), "mzdy, hypotéky, daně", "cz"),
            ("🇯🇵 Japan", hub_counts.get("jp", 0), "Tedori, Furusato Nozei, housing loan", "jp"),
            ("🇸🇬 Singapore", hub_counts.get("sg", 0), "TDSR, HDB, CPF, SPL", "sg"),
            ("🇳🇿 New Zealand", hub_counts.get("nz", 0), "KiwiSaver, PAYE, mortgage", "nz"),
            ("🇦🇪 UAE", hub_counts.get("ae", 0), "gratuity, Salik, visa fines", "ae"),
            ("🇧🇩 Bangladesh", hub_counts.get("bd", 0), "bKash, Nagad, tax, CGPA", "bd"),
            ("🇦🇺 Australia", hub_counts.get("au", 0), "HECS, super, MLS, CGT", "au"),
            ("🇨🇦 Canada", hub_counts.get("ca", 0), "TFSA, RRSP, EI, CCB", "ca"),
            ("🇮🇳 India", hub_counts.get("in", 0), "GST, EMI, PPF, SIP", "in"),
            ("🇪🇸 Spain", hub_counts.get("es", 0), "hipoteca, finiquito, nómina", "es"),
            ("🇵🇹 Portugal", hub_counts.get("pt", 0), "CLT vs PJ, empréstimo, IMC", "pt"),
            ("🇳🇱 Netherlands", hub_counts.get("nl", 0), "30%-ruling, hypotheek, loon", "nl"),
            ("🇫🇮 Finland", hub_counts.get("fi", 0), "verolaskuri, asumistuki, eläke", "fi"),
            ("🇸🇪 Sweden", hub_counts.get("se", 0), "skatt, pension, bolån", "se"),
            ("🇳🇴 Norway", hub_counts.get("no", 0), "skatt, boliglån, feriepenger", "no"),
            ("🇮🇹 Italy", hub_counts.get("it", 0), "stipendio, mutuo, TFR", "it"),
        ]
        country_table = "\n".join(
            f"| {name} | {count} | {focus} | [Browse →](https://tool.teamzlab.com/{slug}/) |"
            for name, count, focus, slug in country_rows
            if count
        )

        # Build articles table from history
        rows = []
        for post in history.get("posts", []):
            title = post.get("title", "")
            platforms = post.get("platforms", {})
            gh_url = platforms.get("github_discussions", {}).get("url", "")
            devto_url = platforms.get("devto", {}).get("url", "")
            hashnode_url = platforms.get("hashnode", {}).get("url", "")
            blogger_url = platforms.get("blogger", {}).get("url", "")
            telegraph_url = platforms.get("telegraph", {}).get("url", "")

            # Skip deleted/empty posts
            if not any([devto_url, hashnode_url, blogger_url]):
                continue

            # Title links to GH discussion if available, otherwise first platform
            title_link = gh_url or devto_url or hashnode_url or blogger_url
            title_cell = f"[{title}]({title_link})" if title_link else title
            devto_cell = f"[Read]({devto_url})" if devto_url else "—"
            hashnode_cell = f"[Read]({hashnode_url})" if hashnode_url else "—"
            blogger_cell = f"[Read]({blogger_url})" if blogger_url else "—"
            telegraph_cell = f"[Read]({telegraph_url})" if telegraph_url else "—"
            rows.append(f"| {title_cell} | {devto_cell} | {hashnode_cell} | {blogger_cell} | {telegraph_cell} |")

        articles_table = "\n".join(rows) if rows else "| *No articles yet* | — | — | — |"

        readme = f"""# Awesome Free Browser Tools [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

> A curated collection of **{total_tools:,} free browser-based tools** across **{live_hubs} live hubs** — no signup, no downloads, 100% private. Everything runs client-side; your data never leaves your device.

**[tool.teamzlab.com](https://tool.teamzlab.com)** — Built by [Teamz Lab](https://teamzlab.com)

---

## Contents

- [Finance & Money](#finance--money)
- [Developer Tools](#developer-tools)
- [Health & Wellness](#health--wellness)
- [Beauty & Skincare](#beauty--skincare)
- [AI-Powered Tools](#ai-powered-tools)
- [Design & Images](#design--images)
- [Home & Housing](#home--housing)
- [Career & Resume](#career--resume)
- [Math & Science](#math--science)
- [Gaming](#gaming)
- [Privacy & Security](#privacy--security)
- [Food & Drink](#food--drink)
- [Kids & Education](#kids--education)
- [Country-Specific Tools](#country-specific-tools)
- [Articles & Guides](#articles--guides)

---

## Finance & Money

- [50/30/20 Budget Calculator](https://tool.teamzlab.com/evergreen/50-30-20-budget-calculator/) — Split income into needs, wants, and savings
- [Compound Interest Calculator](https://tool.teamzlab.com/evergreen/compound-interest-calculator/) — See how your money grows over time
- [Debt Snowball vs Avalanche](https://tool.teamzlab.com/evergreen/debt-snowball-vs-avalanche/) — Compare debt payoff strategies
- [FIRE Calculator](https://tool.teamzlab.com/evergreen/fire-calculator/) — Find out when you can retire early
- [Mortgage Calculator](https://tool.teamzlab.com/evergreen/mortgage-calculator/) — Monthly payment, amortization, total interest
- [Rent vs Buy Calculator](https://tool.teamzlab.com/evergreen/rent-vs-buy-calculator/) — Honest comparison including opportunity cost
- [Investment Return Calculator](https://tool.teamzlab.com/evergreen/investment-return-calculator/) — Project portfolio growth
- [Credit Card Payoff Calculator](https://tool.teamzlab.com/evergreen/credit-card-payoff-calculator/) — Payoff timeline and total interest
- [Net Worth Calculator](https://tool.teamzlab.com/evergreen/net-worth-calculator/) — Track assets minus liabilities
- [Side Hustle Profit Calculator](https://tool.teamzlab.com/evergreen/side-hustle-profit-calculator/) — Real hourly rate after expenses

**[Browse all {hub_counts.get("evergreen", 0)} finance tools →](https://tool.teamzlab.com/evergreen/)**

## Developer Tools

- [JSON Formatter](https://tool.teamzlab.com/dev/json-formatter/) — Beautify, validate, and explore JSON
- [JWT Decoder](https://tool.teamzlab.com/dev/jwt-decoder/) — Decode JWT tokens instantly
- [Regex Tester](https://tool.teamzlab.com/dev/regex-tester/) — Real-time regex matching with capture groups
- [Cron Expression Generator](https://tool.teamzlab.com/dev/cron-expression-generator/) — Build cron schedules visually
- [CSS Gradient Generator](https://tool.teamzlab.com/dev/css-gradient-generator/) — Design gradients, copy CSS
- [Docker Run to Compose](https://tool.teamzlab.com/dev/docker-run-to-compose/) — Convert docker run to docker-compose.yml
- [Base64 Encode/Decode](https://tool.teamzlab.com/dev/base64-encode-decode/) — Encode and decode Base64
- [UUID Generator](https://tool.teamzlab.com/dev/uuid-generator/) — Generate v4 UUIDs in bulk
- [Subnet Calculator](https://tool.teamzlab.com/dev/subnet-calculator/) — CIDR, network ranges, host counts

**[Browse all {hub_counts.get("dev", 0)} developer tools →](https://tool.teamzlab.com/dev/)**

## Health & Wellness

- [TDEE Calculator](https://tool.teamzlab.com/health/tdee-calculator/) — Total Daily Energy Expenditure
- [BMI Calculator](https://tool.teamzlab.com/evergreen/bmi-calculator/) — Body Mass Index with health category
- [Macro Calculator](https://tool.teamzlab.com/health/macro-calculator/) — Protein, carbs, fat split
- [Sleep Calculator](https://tool.teamzlab.com/health/sleep-calculator/) — Optimal bedtime based on sleep cycles
- [Burnout Test](https://tool.teamzlab.com/health/burnout-test/) — Clinical-grade burnout assessment
- [Reaction Time Test](https://tool.teamzlab.com/health/reaction-time-test/) — Measure reflexes in milliseconds
- [Body Fat Calculator](https://tool.teamzlab.com/health/body-fat-calculator/) — Estimate from measurements
- [Phone Addiction Test](https://tool.teamzlab.com/health/phone-addiction-test/) — Screen time assessment

**[Browse all {hub_counts.get("health", 0)} health tools →](https://tool.teamzlab.com/health/)**

## Beauty & Skincare

- [Ingredient Checker](https://tool.teamzlab.com/skincare/ingredient-checker/) — Flag irritants, comedogenic ingredients, fragrance, and pregnancy-unsafe actives
- [Product Expiry Tracker](https://tool.teamzlab.com/skincare/product-expiry-tracker/) — Track PAO dates and know what to use up first
- [SPF Calculator](https://tool.teamzlab.com/skincare/spf-calculator/) — Estimate the SPF level you need by skin tone and UV exposure
- [Sunscreen Reapply Timer](https://tool.teamzlab.com/skincare/sunscreen-reapply-timer/) — Time your next sunscreen reapplication by activity
- [Skin Type Quiz](https://tool.teamzlab.com/skincare/skin-type-quiz/) — Get a simple skincare starting point based on your skin profile

**[Browse all {hub_counts.get("skincare", 0)} skincare tools →](https://tool.teamzlab.com/skincare/)**

## AI-Powered Tools

- [Grammar Checker](https://tool.teamzlab.com/ai/grammar-checker/) — Fix grammar, spelling, punctuation in browser
- [Article Summarizer](https://tool.teamzlab.com/ai/article-summarizer/) — TL;DR any article into bullet points
- [Resume Summary Generator](https://tool.teamzlab.com/ai/resume-summary-generator/) — Professional summary from experience
- [Cover Letter Helper](https://tool.teamzlab.com/ai/cover-letter-helper/) — Generate tailored cover letters
- [Headline Generator](https://tool.teamzlab.com/ai/headline-generator/) — Click-worthy headlines with AI

**[Browse all 25+ AI tools →](https://tool.teamzlab.com/ai/)**

## Design & Images

- [Background Remover](https://tool.teamzlab.com/design/background-remover/) — Remove backgrounds with AI, in-browser
- [Image Compressor](https://tool.teamzlab.com/image/image-compressor/) — Compress without quality loss
- [Favicon Generator](https://tool.teamzlab.com/image/favicon-generator/) — All sizes from any image, ICO included
- [Photo to Pencil Sketch](https://tool.teamzlab.com/image/photo-to-pencil-sketch/) — Convert photos to sketch art
- [Color Palette Extractor](https://tool.teamzlab.com/image/color-palette-extractor/) — Extract dominant colors with hex codes
- [Meme Maker](https://tool.teamzlab.com/image/meme-maker/) — Classic meme generator

**[Browse all design tools →](https://tool.teamzlab.com/design/)**

## Home & Housing

- [Kitchen Remodel Calculator](https://tool.teamzlab.com/housing/kitchen-remodel-calculator/) — Cabinets, counters, appliances breakdown
- [Bathroom Remodel Calculator](https://tool.teamzlab.com/housing/bathroom-remodel-calculator/) — Tile, vanity, plumbing estimates
- [Paint Calculator](https://tool.teamzlab.com/housing/paint-calculator/) — Exact gallons needed for any room
- [Solar Panel Calculator](https://tool.teamzlab.com/evergreen/solar-panel-calculator/) — Payback period, savings, ROI
- [Electricity Cost Calculator](https://tool.teamzlab.com/evergreen/electricity-cost-calculator/) — Cost per appliance per day/month/year
- [Roommate Split Calculator](https://tool.teamzlab.com/housing/roommate-split-calculator/) — Fair rent split by room features

**[Browse all 29+ housing tools →](https://tool.teamzlab.com/housing/)**

## Career & Resume

- [ATS Resume Checker](https://tool.teamzlab.com/career/ats-resume-checker/) — Check if your resume passes ATS filters
- [Resume Keyword Scanner](https://tool.teamzlab.com/career/resume-keyword-scanner/) — Match resume keywords to job descriptions
- [LinkedIn Summary Generator](https://tool.teamzlab.com/career/linkedin-summary-generator/) — Professional LinkedIn About section
- [Salary Negotiation Script Generator](https://tool.teamzlab.com/career/salary-negotiation-script-generator/) — Generate negotiation scripts in multiple tones and currencies
- [Offer Comparison Calculator](https://tool.teamzlab.com/career/offer-comparison-calculator/) — Compare job offers with total compensation

**[Browse all {hub_counts.get("career", 0)} career tools →](https://tool.teamzlab.com/career/)**

## Math & Science

- [Scientific Calculator](https://tool.teamzlab.com/evergreen/scientific-calculator/) — Full scientific calculator with history
- [Graph Plotter](https://tool.teamzlab.com/math/graph-plotter/) — Plot any equation with zoom and pan
- [Matrix Calculator](https://tool.teamzlab.com/math/matrix-calculator/) — Operations up to 10x10 matrices
- [Standard Deviation Calculator](https://tool.teamzlab.com/math/standard-deviation-calculator/) — Mean, median, variance

**[Browse all {hub_counts.get("math", 0)} math tools →](https://tool.teamzlab.com/math/)**

## Gaming

- [Click Speed Test](https://tool.teamzlab.com/gaming/click-speed-test/) — Measure CPS (clicks per second)
- [Keyboard Tester](https://tool.teamzlab.com/gaming/keyboard-tester/) — Visual key registration test
- [DPI Calculator](https://tool.teamzlab.com/gaming/dpi-calculator/) — Effective DPI and sensitivity converter
- [PC Bottleneck Calculator](https://tool.teamzlab.com/gaming/pc-bottleneck-calculator/) — CPU vs GPU bottleneck analysis

**[Browse all {hub_counts.get("gaming", 0)} gaming tools →](https://tool.teamzlab.com/gaming/)**

## Privacy & Security

- [Password Strength Checker](https://tool.teamzlab.com/diagnostic/password-strength-checker/) — Crack time estimation, runs locally
- [DNS Leak Test](https://tool.teamzlab.com/diagnostic/dns-leak-test/) — Check if your VPN is leaking
- [Browser Fingerprint Checker](https://tool.teamzlab.com/diagnostic/browser-fingerprint-checker/) — See how trackable you are
- [WebRTC Leak Checker](https://tool.teamzlab.com/diagnostic/webrtc-leak-checker/) — Detect IP leaks through WebRTC

**[Browse all {hub_counts.get("diagnostic", 0)} diagnostic tools →](https://tool.teamzlab.com/diagnostic/)**

## Food & Drink

- [Coffee-to-Water Ratio](https://tool.teamzlab.com/coffee/coffee-to-water-ratio-calculator/) — Perfect ratio for any brew method
- [Recipe Scaler](https://tool.teamzlab.com/baking/recipe-scaler-calculator/) — Scale recipes up or down
- [Sourdough Hydration](https://tool.teamzlab.com/baking/sourdough-hydration-calculator/) — Baker's percentages
- [Caffeine Half-Life](https://tool.teamzlab.com/coffee/caffeine-half-life-calculator/) — Caffeine remaining at bedtime

**Browse: [Coffee](https://tool.teamzlab.com/coffee/) · [Baking](https://tool.teamzlab.com/baking/) · [Tea](https://tool.teamzlab.com/tea/)**

## Kids & Education

- [Times Table Quiz](https://tool.teamzlab.com/kids/times-table-quiz/) — Timed multiplication practice
- [Typing Speed Test for Kids](https://tool.teamzlab.com/kids/typing-speed-test-kids/) — Kid-friendly WPM test
- [Reading Level Test](https://tool.teamzlab.com/kids/reading-level-test/) — Reading comprehension assessment
- [Math Word Problem Generator](https://tool.teamzlab.com/kids/math-word-problem-generator/) — Grade-appropriate problems

**[Browse all kids tools →](https://tool.teamzlab.com/kids/)**

## Country-Specific Tools

| Country | Tools | Link |
|---------|-------|------|
{country_table}

---

## Articles & Guides

| Article | Dev.to | Hashnode | Blogger | Telegraph |
|---------|--------|---------|---------|-----------|
{articles_table}

**[View all articles →](https://github.com/Teamz-Lab-LTD/teamz-lab-blogs/discussions)**

---

## Full Tool Index

**[View all {total_tools:,} tools organized by category → TOOLS.md](TOOLS.md)**

Every tool with a direct link — searchable, browsable, and all dofollow.

---

## Why These Tools?

- **No signup, no email** — open and use immediately
- **No downloads** — runs entirely in your browser
- **100% private** — your data never leaves your device (client-side JavaScript)
- **No paywall** — everything is free, forever
- **Works offline** — many tools work without internet after first load
- **Mobile friendly** — responsive design for all screen sizes

## For Developers

- **AI-discoverable** — indexed via [llms.txt](https://tool.teamzlab.com/llms.txt) for ChatGPT, Perplexity, Claude
- **Static site** — hosted on GitHub Pages, no backend
- **Open standards** — JSON-LD schemas, sitemap, RSS

## Contributing

Found a bug? Have a tool suggestion? [Open a discussion](https://github.com/Teamz-Lab-LTD/teamz-lab-blogs/discussions/new?category=ideas).

## License

Tools are free to use. Content is copyright [Teamz Lab](https://teamzlab.com).
"""
        # Push README via GitHub API
        encoded = base64.b64encode(readme.encode("utf-8")).decode("utf-8")

        # Get current SHA (needed for update)
        result = subprocess.run(
            ["gh", "api", f"repos/{REPO}/contents/README.md", "--jq", ".sha"],
            capture_output=True, text=True, timeout=15
        )
        sha = result.stdout.strip() if result.returncode == 0 else ""

        # Build API call
        cmd = ["gh", "api", f"repos/{REPO}/contents/README.md", "-X", "PUT",
               "-f", "message=Auto-update README with latest articles",
               "-f", f"content={encoded}"]
        if sha:
            cmd += ["-f", f"sha={sha}"]
        cmd += ["--jq", ".content.html_url"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"  [github-readme] Updated — {result.stdout.strip()}")
        else:
            print(f"  [github-readme] SKIP — could not update README ({result.stderr.strip()[:80]})")

    except Exception as e:
        print(f"  [github-readme] SKIP — {str(e)[:80]}")


def cmd_post(title, filepath, platforms):
    """Post article to specified platforms."""
    config = load_config()
    history = load_history()

    if not os.path.exists(filepath):
        print(f"  ERROR: File not found: {filepath}")
        sys.exit(1)

    meta, body = read_markdown(filepath)
    slug = meta.get("slug", slugify(title))
    tags = normalize_tags(meta.get("tags"))
    canonical_url = meta.get("canonical_url", meta.get("canonical", ""))
    language = meta.get("language", meta.get("lang", "en"))

    # Use defaults from config
    defaults = config.get("defaults", {})
    if not canonical_url and "canonical_base" in defaults:
        canonical_url = ""  # Don't auto-generate, user should set it

    print(f"\n{'=' * 60}")
    print(f"  Distributing: {title}")
    print(f"  Slug: {slug}")
    print(f"  Language: {language}")
    print(f"  Tags: {', '.join(tags)}")
    print(f"  Canonical: {canonical_url or '(none)'}")
    print(f"  Platforms: {', '.join(platforms)}")
    print(f"{'=' * 60}\n")

    # Add localized backlink footer to body
    site_url = defaults.get("site_url", "https://tool.teamzlab.com")
    footer_text = LOCALIZED_FOOTERS.get(language, LOCALIZED_FOOTERS["en"])
    body_with_footer = body + f"\n\n---\n\n*{footer_text} [{site_url}]({site_url})*"

    # Find or create history entry for this slug
    entry = None
    for post in history["posts"]:
        if post["slug"] == slug:
            entry = post
            break
    if entry is None:
        entry = {
            "slug": slug,
            "title": title,
            "hash": content_hash(title, body),
            "created": datetime.now(timezone.utc).isoformat(),
            "platforms": {}
        }
        history["posts"].append(entry)

    # Dispatch to each platform
    platform_funcs = {
        "devto": post_devto,
        "hashnode": post_hashnode,
        "medium": post_medium,
        "blogger": post_blogger,
        "wordpress": post_wordpress,
        "tumblr": post_tumblr,
        "bluesky": post_bluesky,
        "mastodon": post_mastodon,
        "github_discussions": post_github_discussions,
        "gitlab": post_gitlab,
        "substack": post_substack,
        "telegraph": post_telegraph,
        "google_sites": post_google_sites,
    }

    results = {}
    for platform in platforms:
        if platform not in platform_funcs:
            print(f"  [{platform}] SKIP — unknown platform")
            continue

        # Check duplicate
        existing = is_duplicate(history, slug, platform)
        if existing:
            print(f"  [{platform}] SKIP — already posted: {existing.get('url', 'unknown')}")
            results[platform] = {"status": "duplicate", "url": existing.get("url")}
            continue

        # Check if platform is configured
        if platform not in config or not config[platform].get("enabled"):
            print(f"  [{platform}] SKIP — not enabled in config")
            results[platform] = {"status": "disabled"}
            continue

        print(f"  [{platform}] Posting...", end=" ", flush=True)
        if platform == "pinterest":
            pin_img = (meta.get("pin_image") or meta.get("og_image") or "").strip()
            url, error = post_pinterest(config, title, body, tags, canonical_url, pin_img)
        elif platform in ("telegraph", "substack", "gitlab", "google_sites"):
            # These platforms handle their own formatting/footer — send raw body
            url, error = platform_funcs[platform](config, title, body, tags, canonical_url)
        else:
            url, error = platform_funcs[platform](config, title, body_with_footer, tags, canonical_url)

        if url:
            print(f"OK — {url}")
            entry["platforms"][platform] = {
                "url": url,
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "status": "published"
            }
            results[platform] = {"status": "published", "url": url}
        else:
            print(f"FAILED — {error}")
            results[platform] = {"status": "failed", "error": error}

    save_history(history)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  RESULTS:")
    ok = sum(1 for r in results.values() if r["status"] == "published")
    skip = sum(1 for r in results.values() if r["status"] in ("duplicate", "disabled"))
    fail = sum(1 for r in results.values() if r["status"] == "failed")
    print(f"  Published: {ok}  |  Skipped: {skip}  |  Failed: {fail}")
    for p, r in results.items():
        icon = "✓" if r["status"] == "published" else "⊘" if r["status"] == "duplicate" else "—" if r["status"] == "disabled" else "✗"
        detail = r.get("url", r.get("error", ""))
        print(f"    {icon} {p}: {detail}")
    print(f"{'=' * 60}\n")

    # Auto-update GitHub blog README with new article
    if ok > 0:
        update_github_blog_readme(history)


def cmd_status():
    """Show posting history."""
    history = load_history()

    if not history["posts"]:
        print("\n  No posts distributed yet.\n")
        return

    print(f"\n{'=' * 60}")
    print(f"  DISTRIBUTION HISTORY ({len(history['posts'])} articles)")
    print(f"{'=' * 60}\n")

    for post in history["posts"]:
        print(f"  {post['title']}")
        print(f"  Slug: {post['slug']}  |  Created: {post.get('created', 'unknown')}")
        platforms = post.get("platforms", {})
        if platforms:
            for p, info in platforms.items():
                status = info.get("status", "unknown")
                url = info.get("url", "")
                date = info.get("posted_at", "")[:10]
                icon = "✓" if status == "published" else "✗"
                print(f"    {icon} {p}: {url} ({date})")
        else:
            print(f"    (no platforms posted yet)")
        print()


def cmd_test():
    """Test API connections for all enabled platforms."""
    config = load_config()

    print(f"\n{'=' * 60}")
    print(f"  TESTING API CONNECTIONS")
    print(f"{'=' * 60}\n")

    tests = {
        "devto": ("https://dev.to/api/articles/me?per_page=1", {"api-key": config.get("devto", {}).get("api_key", "")}),
        "hashnode": None,  # GraphQL, special handling
        "medium": ("https://api.medium.com/v1/me", {"Authorization": f"Bearer {config.get('medium', {}).get('integration_token', '')}"}),
        "bluesky": None,  # Session-based, special handling
        "mastodon": (f"{config.get('mastodon', {}).get('instance', 'https://mastodon.social')}/api/v1/accounts/verify_credentials",
                     {"Authorization": f"Bearer {config.get('mastodon', {}).get('access_token', '')}"}),
    }

    for platform in ALL_PLATFORMS:
        cfg = config.get(platform, {})
        if not cfg.get("enabled"):
            print(f"  [{platform}] DISABLED — skipping")
            continue

        print(f"  [{platform}] Testing...", end=" ", flush=True)

        if platform == "hashnode":
            query = '{"query": "{ me { id username } }"}'
            status, resp = api_request(
                "https://gql.hashnode.com",
                data=json.loads(query),
                headers={"Authorization": cfg.get("api_key", "")}
            )
            if status == 200 and "data" in resp:
                user = resp["data"].get("me", {}).get("username", "unknown")
                print(f"OK — connected as @{user}")
            else:
                print(f"FAILED — HTTP {status}")

        elif platform == "bluesky":
            status, resp = api_request(
                "https://bsky.social/xrpc/com.atproto.server.createSession",
                data={"identifier": cfg.get("handle", ""), "password": cfg.get("app_password", "")}
            )
            if status == 200:
                print(f"OK — connected as {resp.get('handle', 'unknown')}")
            else:
                print(f"FAILED — HTTP {status}")

        elif platform == "blogger":
            creds_file = os.path.expanduser(cfg.get("credentials_file", ""))
            if os.path.exists(creds_file):
                print(f"OK — credentials file found")
            else:
                print(f"FAILED — credentials file not found: {creds_file}")

        elif platform == "wordpress":
            token = cfg.get("access_token", "")
            if not token:
                print(f"FAILED — no access_token. Run wordpress-auth.py first")
                continue
            status, resp = api_request(
                f"https://public-api.wordpress.com/rest/v1.1/sites/{cfg.get('site', '')}/",
                headers={"Authorization": f"Bearer {token}"}
            )
            if status == 200:
                print(f"OK — site: {resp.get('name', 'unknown')}")
            else:
                print(f"FAILED — HTTP {status}")

        elif platform == "tumblr":
            status, resp = api_request(
                f"https://api.tumblr.com/v2/blog/{cfg.get('blog_name', '')}/info?api_key={cfg.get('consumer_key', '')}"
            )
            if status == 200:
                blog_title = resp.get("response", {}).get("blog", {}).get("title", "unknown")
                print(f"OK — blog: {blog_title}")
            else:
                print(f"FAILED — HTTP {status}")

        elif platform in tests and tests[platform]:
            url, headers = tests[platform]
            status, resp = api_request(url, headers=headers)
            if status == 200:
                if platform == "devto":
                    print(f"OK — connected")
                elif platform == "medium":
                    name = resp.get("data", {}).get("name", "unknown")
                    print(f"OK — connected as {name}")
                elif platform == "mastodon":
                    acct = resp.get("acct", resp.get("username", "unknown"))
                    print(f"OK — connected as @{acct}")
                else:
                    print(f"OK")
            else:
                print(f"FAILED — HTTP {status}")
        elif platform == "github_discussions":
            import subprocess
            try:
                result = subprocess.run(
                    ["gh", "api", "graphql", "-f", f'query={{ repository(owner:"Teamz-Lab-LTD", name:"teamz-lab-blogs") {{ id }} }}'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and "repository" in result.stdout:
                    print(f"OK — connected to Teamz-Lab-LTD/teamz-lab-blogs")
                else:
                    print(f"FAILED — {result.stderr[:100]}")
            except Exception as e:
                print(f"FAILED — {e}")

        elif platform == "pinterest":
            creds_path = os.path.expanduser(
                cfg.get("credentials_file", "~/.config/teamzlab/pinterest-credentials.json")
            )
            if not os.path.isfile(creds_path):
                print(f"FAILED — run pinterest-auth.py first")
                continue
            with open(creds_path) as f:
                pcreds = json.load(f)
            token = pcreds.get("access_token", "")
            if not token:
                print(f"FAILED — no access_token in credentials file")
                continue
            status, resp = api_request(
                "https://api.pinterest.com/v5/boards?page_size=1",
                headers={"Authorization": f"Bearer {token}"},
            )
            if status == 401:
                new_t = pinterest_refresh_access_token(cfg, creds_path)
                if new_t:
                    status, resp = api_request(
                        "https://api.pinterest.com/v5/boards?page_size=1",
                        headers={"Authorization": f"Bearer {new_t}"},
                    )
            if status == 200:
                n = len(resp.get("items") or [])
                print(f"OK — API reachable ({n}+ board(s) visible)")
            else:
                print(f"FAILED — HTTP {status}: {json.dumps(resp)[:120]}")

        elif platform == "google_sites":
            webapp_url = cfg.get("webapp_url", "").strip()
            secret_key = cfg.get("secret_key", "")
            if not secret_key:
                key_file = os.path.expanduser("~/.config/teamzlab/google-sites-key.txt")
                if os.path.exists(key_file):
                    with open(key_file) as f:
                        secret_key = f.read().strip()
            if not webapp_url:
                print(f"FAILED — no webapp_url. Deploy google-sites-bridge.gs first")
                continue
            if not secret_key:
                print(f"FAILED — no secret_key configured")
                continue
            # Health check via GET
            try:
                health_url = webapp_url + ("&" if "?" in webapp_url else "?") + "action=health"
                status, resp = api_request(health_url)
                if status == 200 and resp.get("status") == "ok":
                    print(f"OK — bridge v{resp.get('version', '?')} connected")
                else:
                    print(f"FAILED — HTTP {status}: {json.dumps(resp)[:100]}")
            except Exception as e:
                print(f"FAILED — {str(e)[:100]}")

        else:
            print(f"SKIP — no test available")

    print()


def cmd_setup():
    """Print setup instructions for all platforms."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  Teamz Lab Tools — Distribution Setup Guide                  ║
╚══════════════════════════════════════════════════════════════╝

Step 1: Copy config file
────────────────────────
  cp scripts/distribute/config.example.json scripts/distribute/config.json

Step 2: Get API keys (one-time per platform)
────────────────────────────────────────────

1. DEV.TO (easiest)
   → Go to https://dev.to/settings/extensions
   → Scroll to "DEV Community API Keys"
   → Generate a new key, name it "teamzlab-distribute"
   → Copy the key to config: devto.api_key
   → Set devto.enabled = true

2. HASHNODE
   → Go to https://hashnode.com/settings/developer
   → Click "Generate New Token"
   → Copy the PAT to config: hashnode.api_key
   → Get your Publication ID:
     - Go to your blog dashboard → Settings → General
     - The publication ID is in the URL or settings
   → Set hashnode.enabled = true

3. MEDIUM
   → Go to https://medium.com/me/settings/security
   → Scroll to "Integration tokens"
   → Generate a token, copy to config: medium.integration_token
   → Set medium.enabled = true

4. BLOGGER (Google)
   → Go to https://console.cloud.google.com/apis
   → Create project or select existing
   → Enable "Blogger API v3"
   → Create OAuth2 credentials (Desktop app)
   → Download credentials JSON to ~/.config/teamzlab/blogger-credentials.json
   → Run: python3 scripts/distribute-blogger-auth.py (first time)
   → Get Blog ID: go to your Blogger dashboard, it's in the URL
   → Set blogger.enabled = true

5. WORDPRESS.COM
   → Create free blog at https://wordpress.com
   → Go to https://wordpress.com/me/security/two-step
   → Scroll to "Application Passwords"
   → Create one, name it "teamzlab-distribute"
   → Copy username + app password to config
   → Site = "yourblog.wordpress.com"
   → Set wordpress.enabled = true

6. TUMBLR
   → Go to https://www.tumblr.com/oauth/apps
   → Register an app (name: "teamzlab-distribute")
   → You'll get consumer_key + consumer_secret
   → For OAuth token: use the OAuth1 flow or
     run: python3 scripts/distribute-tumblr-auth.py
   → Set tumblr.enabled = true

7. BLUESKY (very easy)
   → Go to https://bsky.app/settings/app-passwords
   → Click "Add App Password"
   → Name it "teamzlab-distribute"
   → Copy the password to config: bluesky.app_password
   → Set handle to your full handle (e.g., "you.bsky.social")
   → Set bluesky.enabled = true

8. MASTODON
   → Go to your instance (e.g., https://mastodon.social)
   → Settings → Development → New Application
   → Name: "teamzlab-distribute"
   → Scopes: read, write:statuses
   → Copy "Your access token" to config: mastodon.access_token
   → Set mastodon.enabled = true

9. GOOGLE SITES (DA 96+ dofollow backlinks via Apps Script bridge)
   → Create a Google Site: https://sites.google.com → New
   → Go to https://script.google.com → New Project
   → Paste the contents of scripts/distribute/google-sites-bridge.gs into Code.gs
   → Set SECRET_KEY in Project Settings → Script Properties
   → Deploy → New deployment → Web app:
     - Execute as: Me
     - Who has access: Anyone
   → Copy the web app URL to config: google_sites.webapp_url
   → Set the same secret key in config: google_sites.secret_key
   → Or run: python3 scripts/distribute/google-sites-auth.py (interactive setup)
   → Set google_sites.enabled = true

10. PINTEREST (Pins — requires a public image URL per post)
   → Create a developer app: https://developers.pinterest.com/apps/
   → Add Redirect URI: must match pinterest.redirect_uri (default http://localhost:8085/)
   → Copy App id + App secret into config: pinterest.app_id, pinterest.app_secret
   → Run: python3 scripts/distribute/pinterest-auth.py
   → Copy a board_id from the script output into pinterest.board_id
   → Set pinterest.default_pin_image_url to a stable https image (e.g. hub OG image), or set
     pin_image / og_image per article in frontmatter
   → Set pinterest.enabled = true

Step 3: Test connections
────────────────────────
  python3 scripts/distribute/distribute.py test

Step 4: Create your first article
──────────────────────────────────
  Create a markdown file (e.g., scripts/distribute/articles/my-first-post.md):

  ---
  slug: my-first-post
  tags: tools, free, web, calculator
  canonical_url: https://tool.teamzlab.com/your-tool/
  pin_image: https://tool.teamzlab.com/og-images/tools.png
  ---

  Your article content here in markdown...

  Check out [Tool Name](https://tool.teamzlab.com/your-tool/) — a free
  browser-based calculator that runs entirely in your browser.

Step 5: Distribute!
───────────────────
  python3 scripts/distribute/distribute.py post "My Article Title" scripts/distribute/articles/my-first-post.md

  # Or specific platforms only:
  python3 scripts/distribute/distribute.py post "Title" scripts/distribute/articles/my-post.md --platforms devto,hashnode,pinterest

  # Check what's been posted:
  python3 scripts/distribute/distribute.py status
""")


# ─── Edit / Delete / List ─────────────────────────────────────────────────────

def cmd_edit(slug, filepath, platforms):
    """Edit an existing post on specified platforms."""
    config = load_config()
    history = load_history()

    if not os.path.exists(filepath):
        print(f"  ERROR: File not found: {filepath}")
        sys.exit(1)

    meta, body = read_markdown(filepath)
    tags = normalize_tags(meta.get("tags"))
    canonical_url = meta.get("canonical_url", meta.get("canonical", ""))

    # Find the history entry
    entry = None
    for post in history["posts"]:
        if post["slug"] == slug:
            entry = post
            break

    if not entry:
        print(f"  ERROR: No post found with slug '{slug}'")
        print(f"  Run 'status' to see all slugs")
        sys.exit(1)

    # Add footer
    defaults = config.get("defaults", {})
    site_url = defaults.get("site_url", "https://tool.teamzlab.com")
    body_with_footer = body + f"\n\n---\n\n*Originally published at [{site_url}]({site_url})*"

    title = entry["title"]

    print(f"\n{'=' * 60}")
    print(f"  Editing: {title}")
    print(f"  Slug: {slug}")
    print(f"  Platforms: {', '.join(platforms)}")
    print(f"{'=' * 60}\n")

    for platform in platforms:
        posted = entry.get("platforms", {}).get(platform)
        if not posted:
            print(f"  [{platform}] SKIP — not posted yet (use 'post' first)")
            continue

        cfg = config.get(platform, {})
        if not cfg.get("enabled"):
            print(f"  [{platform}] SKIP — not enabled in config")
            continue

        print(f"  [{platform}] Editing...", end=" ", flush=True)

        if platform == "devto":
            # Get article ID
            status, articles = api_request(
                "https://dev.to/api/articles/me?per_page=50",
                headers={"api-key": cfg["api_key"], "User-Agent": "TeamzLabDistribute/1.0"}
            )
            article_id = None
            if status == 200:
                posted_url = posted.get("url", "")
                for a in articles:
                    if a.get("url") == posted_url or a.get("canonical_url") == posted_url:
                        article_id = a["id"]
                        break
                # Fallback: match by slug in URL
                if not article_id:
                    for a in articles:
                        if slug.replace("-", "") in a.get("url", "").replace("-", ""):
                            article_id = a["id"]
                            break

            if not article_id:
                print(f"FAILED — could not find article on Dev.to")
                continue

            update_data = {
                "article": {
                    "body_markdown": body_with_footer,
                    "tags": tags[:4],
                }
            }
            if canonical_url:
                update_data["article"]["canonical_url"] = canonical_url

            status, resp = api_request(
                f"https://dev.to/api/articles/{article_id}",
                data=update_data,
                headers={"api-key": cfg["api_key"], "User-Agent": "TeamzLabDistribute/1.0"},
                method="PUT"
            )
            if status == 200:
                print(f"OK — {resp.get('url', 'updated')}")
                entry["platforms"][platform]["updated_at"] = datetime.now(timezone.utc).isoformat()
            else:
                print(f"FAILED — HTTP {status}")

        elif platform == "bluesky":
            # Bluesky can't edit — delete and repost
            old_url = posted.get("url", "")
            old_rkey = old_url.split("/")[-1] if "/" in old_url else ""

            # Login
            status, session = api_request(
                "https://bsky.social/xrpc/com.atproto.server.createSession",
                data={"identifier": cfg["handle"], "password": cfg["app_password"]},
                headers={"User-Agent": "TeamzLabDistribute/1.0"}
            )
            if status != 200:
                print(f"FAILED — auth error")
                continue

            did = session["did"]
            jwt = session["accessJwt"]

            # Delete old
            if old_rkey:
                api_request(
                    "https://bsky.social/xrpc/com.atproto.repo.deleteRecord",
                    data={"repo": did, "collection": "app.bsky.feed.post", "rkey": old_rkey},
                    headers={"Authorization": f"Bearer {jwt}", "User-Agent": "TeamzLabDistribute/1.0"}
                )

            # Create new short post from article
            summary = truncate(body.split("\n\n")[0] if body else "", 200)
            text = f"{summary}\n\n"
            if canonical_url:
                text += canonical_url
            elif site_url:
                text += site_url
            if tags:
                text += "\n\n" + " ".join(f"#{t.replace(' ', '')}" for t in tags[:3])
            if len(text) > 300:
                text = text[:297] + "..."

            link_url = canonical_url or site_url
            facets = []
            if link_url and link_url in text:
                bs = text.encode("utf-8").index(link_url.encode("utf-8"))
                be = bs + len(link_url.encode("utf-8"))
                facets.append({
                    "index": {"byteStart": bs, "byteEnd": be},
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link_url}]
                })

            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            record = {"$type": "app.bsky.feed.post", "text": text, "createdAt": now}
            if facets:
                record["facets"] = facets

            status, resp = api_request(
                "https://bsky.social/xrpc/com.atproto.repo.createRecord",
                data={"repo": did, "collection": "app.bsky.feed.post", "record": record},
                headers={"Authorization": f"Bearer {jwt}", "User-Agent": "TeamzLabDistribute/1.0"}
            )
            if status == 200:
                rkey = resp.get("uri", "").split("/")[-1]
                new_url = f"https://bsky.app/profile/{cfg['handle']}/post/{rkey}"
                print(f"OK — {new_url}")
                entry["platforms"][platform]["url"] = new_url
                entry["platforms"][platform]["updated_at"] = datetime.now(timezone.utc).isoformat()
            else:
                print(f"FAILED — HTTP {status}")

        elif platform == "mastodon":
            # Mastodon supports edit via PUT /api/v1/statuses/:id
            instance = cfg["instance"].rstrip("/")
            old_url = posted.get("url", "")
            # Extract status ID from URL (last path segment)
            status_id = old_url.rstrip("/").split("/")[-1] if old_url else ""

            if not status_id:
                print(f"FAILED — no status ID found")
                continue

            summary = truncate(body.split("\n\n")[0] if body else "", 250)
            text = f"{summary}\n\n"
            if canonical_url:
                text += f"{canonical_url}\n\n"
            if tags:
                text += " ".join(f"#{t.replace(' ', '').replace('-', '')}" for t in tags[:5])
            if len(text) > 500:
                text = text[:497] + "..."

            status, resp = api_request(
                f"{instance}/api/v1/statuses/{status_id}",
                data={"status": text},
                headers={"Authorization": f"Bearer {cfg['access_token']}", "User-Agent": "TeamzLabDistribute/1.0"},
                method="PUT"
            )
            if status == 200:
                print(f"OK — {resp.get('url', 'updated')}")
                entry["platforms"][platform]["updated_at"] = datetime.now(timezone.utc).isoformat()
            else:
                print(f"FAILED — HTTP {status}")

        else:
            print(f"SKIP — edit not implemented for {platform} yet")

    save_history(history)


def cmd_delete(slug, platforms):
    """Delete a post from specified platforms."""
    config = load_config()
    history = load_history()

    entry = None
    for post in history["posts"]:
        if post["slug"] == slug:
            entry = post
            break

    if not entry:
        print(f"  ERROR: No post found with slug '{slug}'")
        print(f"  Run 'status' to see all slugs")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"  Deleting: {entry['title']}")
    print(f"  Slug: {slug}")
    print(f"  Platforms: {', '.join(platforms)}")
    print(f"{'=' * 60}\n")

    for platform in platforms:
        posted = entry.get("platforms", {}).get(platform)
        if not posted:
            print(f"  [{platform}] SKIP — not posted")
            continue

        cfg = config.get(platform, {})
        if not cfg.get("enabled"):
            print(f"  [{platform}] SKIP — not enabled")
            continue

        print(f"  [{platform}] Deleting...", end=" ", flush=True)

        if platform == "devto":
            # Dev.to: unpublish (set published=false)
            status, articles = api_request(
                "https://dev.to/api/articles/me?per_page=50",
                headers={"api-key": cfg["api_key"], "User-Agent": "TeamzLabDistribute/1.0"}
            )
            article_id = None
            if status == 200:
                posted_url = posted.get("url", "")
                for a in articles:
                    if a.get("url") == posted_url:
                        article_id = a["id"]
                        break
                if not article_id:
                    for a in articles:
                        if slug.replace("-", "") in a.get("url", "").replace("-", ""):
                            article_id = a["id"]
                            break

            if not article_id:
                print(f"FAILED — could not find article")
                continue

            status, resp = api_request(
                f"https://dev.to/api/articles/{article_id}",
                data={"article": {"published": False}},
                headers={"api-key": cfg["api_key"], "User-Agent": "TeamzLabDistribute/1.0"},
                method="PUT"
            )
            if status == 200:
                print(f"OK — unpublished")
                del entry["platforms"][platform]
            else:
                print(f"FAILED — HTTP {status}")

        elif platform == "bluesky":
            old_url = posted.get("url", "")
            old_rkey = old_url.split("/")[-1] if "/" in old_url else ""

            status, session = api_request(
                "https://bsky.social/xrpc/com.atproto.server.createSession",
                data={"identifier": cfg["handle"], "password": cfg["app_password"]},
                headers={"User-Agent": "TeamzLabDistribute/1.0"}
            )
            if status != 200:
                print(f"FAILED — auth error")
                continue

            if old_rkey:
                status, resp = api_request(
                    "https://bsky.social/xrpc/com.atproto.repo.deleteRecord",
                    data={"repo": session["did"], "collection": "app.bsky.feed.post", "rkey": old_rkey},
                    headers={"Authorization": f"Bearer {session['accessJwt']}", "User-Agent": "TeamzLabDistribute/1.0"}
                )
                if status == 200:
                    print(f"OK — deleted")
                    del entry["platforms"][platform]
                else:
                    print(f"FAILED — HTTP {status}")
            else:
                print(f"FAILED — no post ID found")

        elif platform == "mastodon":
            instance = cfg["instance"].rstrip("/")
            old_url = posted.get("url", "")
            status_id = old_url.rstrip("/").split("/")[-1] if old_url else ""

            if not status_id:
                print(f"FAILED — no status ID")
                continue

            status, resp = api_request(
                f"{instance}/api/v1/statuses/{status_id}",
                headers={"Authorization": f"Bearer {cfg['access_token']}", "User-Agent": "TeamzLabDistribute/1.0"},
                method="DELETE"
            )
            if status == 200:
                print(f"OK — deleted")
                del entry["platforms"][platform]
            else:
                print(f"FAILED — HTTP {status}")

        else:
            print(f"SKIP — delete not implemented for {platform} yet")

    # Remove entry if no platforms left
    if not entry.get("platforms"):
        history["posts"] = [p for p in history["posts"] if p["slug"] != slug]
        print(f"\n  Removed '{slug}' from history (no platforms left)")

    save_history(history)


def cmd_list(platform=None):
    """List all posts, optionally filtered by platform."""
    config = load_config()
    history = load_history()

    if not history["posts"]:
        print("\n  No posts distributed yet.\n")
        return

    print(f"\n{'=' * 60}")
    if platform:
        print(f"  POSTS ON: {platform.upper()}")
    else:
        print(f"  ALL DISTRIBUTED POSTS")
    print(f"{'=' * 60}\n")

    # Also fetch live data from Dev.to if requested
    live_posts = {}
    if platform == "devto" or platform is None:
        cfg = config.get("devto", {})
        if cfg.get("enabled"):
            status, articles = api_request(
                "https://dev.to/api/articles/me?per_page=50",
                headers={"api-key": cfg["api_key"], "User-Agent": "TeamzLabDistribute/1.0"}
            )
            if status == 200:
                for a in articles:
                    live_posts[a.get("url", "")] = {
                        "title": a.get("title"),
                        "views": a.get("page_views_count", 0),
                        "reactions": a.get("public_reactions_count", 0),
                        "comments": a.get("comments_count", 0),
                        "published": a.get("published_at", "")[:10],
                    }

    count = 0
    for post in history["posts"]:
        platforms_posted = post.get("platforms", {})

        if platform and platform not in platforms_posted:
            continue

        count += 1
        print(f"  {count}. {post['title']}")
        print(f"     Slug: {post['slug']}")

        for p, info in platforms_posted.items():
            if platform and p != platform:
                continue

            url = info.get("url", "")
            date = info.get("posted_at", "")[:10]
            updated = info.get("updated_at", "")[:10]

            line = f"     {p}: {url}"
            if updated:
                line += f" (posted: {date}, edited: {updated})"
            else:
                line += f" (posted: {date})"

            # Add live stats for Dev.to
            if p == "devto" and url in live_posts:
                stats = live_posts[url]
                line += f"\n            Views: {stats['views']} | Reactions: {stats['reactions']} | Comments: {stats['comments']}"

            print(line)
        print()

    if count == 0:
        print(f"  No posts found{f' on {platform}' if platform else ''}.\n")
    else:
        print(f"  Total: {count} article(s)\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "setup":
        cmd_setup()

    elif command == "status":
        cmd_status()

    elif command == "test":
        cmd_test()

    elif command == "post":
        if len(sys.argv) < 4:
            print("  Usage: python3 scripts/distribute/distribute.py post \"Article Title\" content.md [--platforms devto,hashnode,...]")
            sys.exit(1)

        title = sys.argv[2]
        filepath = sys.argv[3]

        # Parse --platforms flag
        platforms = ALL_PLATFORMS[:]
        for i, arg in enumerate(sys.argv[4:], 4):
            if arg == "--platforms" and i + 1 < len(sys.argv):
                platforms_str = sys.argv[i + 1]
                if platforms_str == "all":
                    platforms = ALL_PLATFORMS[:]
                else:
                    platforms = [p.strip() for p in platforms_str.split(",")]
                break

        cmd_post(title, filepath, platforms)

    elif command == "edit":
        if len(sys.argv) < 4:
            print('  Usage: python3 scripts/distribute/distribute.py edit "slug" content.md [--platforms devto,bluesky,...]')
            sys.exit(1)
        slug = sys.argv[2]
        filepath = sys.argv[3]
        platforms = ALL_PLATFORMS[:]
        for i, arg in enumerate(sys.argv[4:], 4):
            if arg == "--platforms" and i + 1 < len(sys.argv):
                platforms = [p.strip() for p in sys.argv[i + 1].split(",")]
                break
        cmd_edit(slug, filepath, platforms)

    elif command == "delete":
        if len(sys.argv) < 3:
            print('  Usage: python3 scripts/distribute/distribute.py delete "slug" [--platforms devto,bluesky,...]')
            sys.exit(1)
        slug = sys.argv[2]
        platforms = ALL_PLATFORMS[:]
        for i, arg in enumerate(sys.argv[3:], 3):
            if arg == "--platforms" and i + 1 < len(sys.argv):
                platforms = [p.strip() for p in sys.argv[i + 1].split(",")]
                break
        cmd_delete(slug, platforms)

    elif command == "list":
        platform = None
        for i, arg in enumerate(sys.argv[2:], 2):
            if arg == "--platform" and i + 1 < len(sys.argv):
                platform = sys.argv[i + 1]
                break
        cmd_list(platform)

    else:
        print(f"  Unknown command: {command}")
        print(f"  Available: post, edit, delete, list, status, test, setup")
        sys.exit(1)


if __name__ == "__main__":
    main()
