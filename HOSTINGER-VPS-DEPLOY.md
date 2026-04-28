# Hostinger VPS Deployment — Reusable Playbook

Single source of truth for deploying any Teamz static site to the shared
Hostinger VPS. Read this entire doc before deploying. The "Gotchas" section
captures real failure modes encountered on prior deploys; skipping it costs
~30 min per repeat.

## Shared Infrastructure (already provisioned)

- **Hostinger account** — managed via REST API at `https://developers.hostinger.com/api/`
- **API token** — `~/.config/teamzlab/hostinger-api-token.txt` (or read from `~/.claude/settings.json` → `hostinger-mcp.env.API_TOKEN`)
- **VPS ID** — `1004515`
- **VPS public IP** — `72.60.184.132`
- **VPS hostname** — `srv1004515.hstgr.cloud`
- **OS** — Ubuntu 25.04 (kernel 6.14)
- **Web server** — **Apache 2.4** (NOT nginx — nginx is installed but disabled)
- **Already-hosted sites** — apps, ecom, invoice, learn, secom, mvecom, banner.jiwerrawda, jiwerrawda, fedex, hs-beauty, aibackend (FastAPI), wordpress
- **DNS** — Cloudflare (zone `teamzlab.com`, NOT Hostinger DNS)
- **SSH key for Claude** — `~/.ssh/teamzlab_vps_ed25519` (ed25519 — RSA disabled by Ubuntu 25.04)
- **Git credentials on VPS** — `/root/.git-credentials` stores GitHub fine-grained PAT for clone+pull
- **SSL** — Let's Encrypt via certbot (`certbot --apache`)

## Quick Deploy (existing VPS, new site/subdomain)

```bash
# 1. SSH in
ssh -i ~/.ssh/teamzlab_vps_ed25519 root@72.60.184.132

# 2. Clone repo (token already stored in /root/.git-credentials)
cd /var/www && git clone https://github.com/Teamz-Lab-LTD/REPO_NAME.git SUBDOMAIN.teamzlab.com
cd SUBDOMAIN.teamzlab.com && git submodule update --init --recursive

# 3. Apache vhost (port 80 only — certbot creates 443 vhost itself)
cat > /etc/apache2/sites-available/SUBDOMAIN.teamzlab.com.conf <<'CONF'
<VirtualHost *:80>
    ServerName SUBDOMAIN.teamzlab.com
    DocumentRoot /var/www/SUBDOMAIN.teamzlab.com
    <Directory /var/www/SUBDOMAIN.teamzlab.com>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
        DirectoryIndex index.html
    </Directory>
    <DirectoryMatch "/\.">
        Require all denied
    </DirectoryMatch>
    <FilesMatch "\.(css|js|woff2|woff|ttf|otf|eot|png|jpg|jpeg|gif|webp|avif|svg|ico)$">
        Header set Cache-Control "public, max-age=604800, immutable"
    </FilesMatch>
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    ErrorDocument 404 /404.html
    ErrorLog ${APACHE_LOG_DIR}/SUBDOMAIN_error.log
    CustomLog ${APACHE_LOG_DIR}/SUBDOMAIN_access.log combined
</VirtualHost>
CONF
a2enmod headers expires deflate rewrite
a2ensite SUBDOMAIN.teamzlab.com
apache2ctl configtest && systemctl reload apache2

# 4. DNS (Cloudflare — manual or via API)
# Add: A SUBDOMAIN -> 72.60.184.132, proxy = orange (Full Strict mode)

# 5. SSL (after DNS resolves)
certbot --apache -d SUBDOMAIN.teamzlab.com --non-interactive --agree-tos -m hello@teamzlab.com --redirect

# 6. Auto-pull cron
cat > /usr/local/bin/SUBDOMAIN-pull.sh <<'PULL'
#!/bin/bash
cd /var/www/SUBDOMAIN.teamzlab.com || exit 1
git fetch --all --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [ "$LOCAL" != "$REMOTE" ]; then
    git reset --hard origin/main >/dev/null 2>&1
    git submodule update --init --recursive >/dev/null 2>&1
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) deployed $REMOTE" >> /var/log/SUBDOMAIN-deploy.log
fi
PULL
chmod +x /usr/local/bin/SUBDOMAIN-pull.sh
( crontab -l 2>/dev/null | grep -v SUBDOMAIN-pull; echo '*/3 * * * * /usr/local/bin/SUBDOMAIN-pull.sh' ) | crontab -
```

## First-Time Setup (new VPS or no SSH access)

If SSH key not yet authorized for this VPS:

1. Generate **ed25519** key on Mac (NOT RSA — Ubuntu 25.04 disables ssh-rsa):
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/teamzlab_vps_ed25519 -N ""
   ```

2. Hostinger API does NOT auto-push SSH keys to running VPS even after reboot. User must paste pub key into VPS via **Hostinger Browser Terminal** at `https://hpanel.hostinger.com/vps/<VPS_ID>` → "Browser terminal":
   ```bash
   mkdir -p ~/.ssh && chmod 700 ~/.ssh
   cat >> ~/.ssh/authorized_keys <<'EOF'
   <paste ed25519 pub key>
   EOF
   chmod 600 ~/.ssh/authorized_keys
   ```

3. Verify: `ssh -i ~/.ssh/teamzlab_vps_ed25519 root@<IP> "echo OK"`

## Gotchas (real failures from prior deploys)

### 1. **Always check SSL cert subject FIRST when HTTPS misroutes** ⚠️
If `curl https://NEW_DOMAIN/` returns wrong content (e.g. JSON from a different site), do NOT assume Cloudflare hijack. Run:
```bash
curl -v https://NEW_DOMAIN/ 2>&1 | grep "subject:"
```
If subject is some OTHER domain on this VPS → Apache has no 443 vhost for the new domain and falls back to **default 443 site** (whichever vhost loaded first alphabetically — currently `aibackend.teamzlab.com`). Fix: run `certbot --apache -d NEW_DOMAIN` to create the 443 vhost. **Do not waste time hunting Cloudflare Workers/Pages/Tunnels.**

### 2. **Ubuntu 25.04 disables `ssh-rsa` keys**
Old `~/.ssh/id_rsa` will fail with `Permission denied (publickey)` even when added to authorized_keys. Always generate **ed25519** keys for new VPS access.

### 3. **Ports 80 and 443 already used by Apache — do NOT install/enable nginx**
The bootstrap pattern from a fresh-VPS playbook installs nginx and tries to bind 80. Apache holds both ports for existing sites. Adding new sites = new Apache vhost, not nginx.

### 4. **Hostinger SSH-key-attach API does NOT push to running VPS**
`POST /api/vps/v1/public-keys/attach/{vps_id}` adds to account metadata but doesn't write to `~/.ssh/authorized_keys`. Even VPS reboot won't help. Only Browser Terminal paste OR rebuild VPS.

### 5. **Public GitHub repos may still require auth from VPS IP**
`Teamz-Lab-LTD/teamzlab-tools` reports `private: false` via authenticated `gh api`, but anonymous clone returns 401. Hostinger IP range may be flagged or org has SAML/IP rules. Workaround: clone with HTTPS+token via `/root/.git-credentials`. Token from `gh auth token` works.

### 6. **GitHub fine-grained PAT cannot create deploy keys**
Even with full repo "Contents: read", deploy-keys API returns 403 "Resource not accessible by personal access token". Need explicit "Administration: read+write" scope. Workaround: use HTTPS+token for clone and auto-pull instead of deploy keys.

### 7. **Cloudflare proxy + new subdomain SSL**
With orange cloud, Let's Encrypt HTTP-01 challenge can fail because CF intercepts /.well-known/acme-challenge/. Two options:
   - Temporarily grey-cloud → run certbot → flip back to orange
   - OR use DNS-01 challenge (requires Cloudflare API token with DNS edit scope)

### 8. **Cloudflare proxy intercept warning is real**
Grey-clouding any one record on the shared VPS exposes the VPS IP, undermining proxy on other subdomains. Mitigation: get cert via DNS-01 from start (see #7) or accept brief grey window during certbot run.

### 9. **The local Cloudflare token at `~/.config/teamzlab/cloudflare-api-token.txt` is scoped ONLY for Cache Purge**
Cannot list DNS records, Workers, Pages, or routes. Need a broader token for any debugging. Token format prefix `cfut_` indicates user-token (not admin).

## Useful API Recipes

### List VPS instances
```bash
TOKEN=$(cat ~/.config/teamzlab/hostinger-api-token.txt)
curl -s -H "Authorization: Bearer $TOKEN" "https://developers.hostinger.com/api/vps/v1/virtual-machines" | python3 -m json.tool
```

### List managed Cloudflare zones (verify token scope first)
```bash
CF=$(cat ~/.config/teamzlab/cloudflare-api-token.txt | tr -d '\n')
curl -s -H "Authorization: Bearer $CF" https://api.cloudflare.com/client/v4/user/tokens/verify | python3 -m json.tool
curl -s -H "Authorization: Bearer $CF" "https://api.cloudflare.com/client/v4/zones" | python3 -m json.tool
```

### Force-deploy a specific commit (bypass cron)
```bash
ssh -i ~/.ssh/teamzlab_vps_ed25519 root@72.60.184.132 \
  "cd /var/www/SUBDOMAIN.teamzlab.com && git fetch && git reset --hard origin/main && git submodule update --init --recursive"
```

### Tail deploy log
```bash
ssh -i ~/.ssh/teamzlab_vps_ed25519 root@72.60.184.132 \
  "tail -f /var/log/SUBDOMAIN-deploy.log"
```

## Currently Deployed (as of 2026-04-28)

| Subdomain | Repo | DocumentRoot | SSL | Auto-pull |
|-----------|------|--------------|-----|-----------|
| tool.teamzlab.com | Teamz-Lab-LTD/teamzlab-tools | /var/www/tool.teamzlab.com | LE 2026-07-27 | */3 cron |
| aibackend.teamzlab.com | (FastAPI service) | — | — | — |
| apps, ecom, invoice, learn, etc. | (legacy) | /var/www/{domain}/public | LE | — |
