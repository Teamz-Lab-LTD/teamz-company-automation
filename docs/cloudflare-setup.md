# Cloudflare DNS — one token, every Teamz Lab project

Every Teamz Lab domain is on Cloudflare. Sooner or later each project needs a DNS
record written, not read:

| Project need | Record |
|---|---|
| Firebase Auth custom sending domain (stops verification mail landing in spam) | `CNAME auth.<domain> -> <project>.web.app` |
| Google / Bing / Pinterest site verification | `TXT` |
| A VPS-hosted app or landing page | `A` |
| Mail authentication for a new sender | `TXT` (SPF, DKIM, DMARC) |

Use [`sh/cf-dns.sh`](../sh/cf-dns.sh) for all of them. Never the dashboard, so the change
is repeatable and reviewable.

## Why there are two token files

This is the part that cost real time, so it is written down.

| File | Scope | Can it write DNS? |
|---|---|---|
| `~/.config/teamzlab/cloudflare-api-token.txt` | `Zone → Zone → Read` | **No** |
| `~/.config/teamzlab/cloudflare-dns-token.txt` | `Zone → DNS → Edit` | Yes |

The read-only token is a **valid, active token**. `/user/tokens/verify` returns success
for it, and it lists zones happily. It just returns `Authentication error` on every
`/dns_records` call. So "the Cloudflare token works" is not the same claim as "I can add
a DNS record", and an agent that checks only the first will promise the second and fail
at the last step.

`cf-dns.sh doctor` exists to collapse that gap: it probes an actual `/dns_records` call
and prints whether each token can really do it.

```
$ bash scripts/cf-dns.sh doctor
Cloudflare credentials
  DNS(write)   ~/.config/teamzlab/cloudflare-dns-token.txt
               -> MISSING
  READ         ~/.config/teamzlab/cloudflare-api-token.txt
               -> zones: teamzlab.com
               -> can read DNS: NO (Zone:Read only)
```

## Getting write access — widen the token you already have

`cf-dns.sh` picks its token by PROBING `/dns_records`, not by filename, so there is no
need for a second file. The existing `cloudflare-api-token.txt` already carries
`Zone → Zone → Read` and `Zone → Cache Purge` (that is what `py/cloudflare-purge.py`
uses). Adding one permission row to it makes everything work from the one file:

1. <https://dash.cloudflare.com/profile/api-tokens>
2. Find the existing Teamz Lab token → **…** → **Edit**
3. Add a permission row: `Zone` · `DNS` · **Edit**
4. Zone Resources: **Include · All zones from an account · Teamz Lab**
   All zones, not one. The next project should not have to repeat this.
5. **Continue → Save.** The token string does not change, so nothing that already uses
   it breaks — cache purge keeps working.
6. `bash scripts/cf-dns.sh doctor` → must say `can read DNS: yes`

If you would rather keep write access separate, create a second token with the same DNS
permission and save it to `~/.config/teamzlab/cloudflare-dns-token.txt` (`chmod 600`).
`cf-dns.sh` prefers that file when it is present.

Tokens are never committed. `~/.config/teamzlab/` sits outside every repo — the same
rule the Search Console, GA4 and AdSense tokens follow.

## Usage

```bash
bash scripts/cf-dns.sh list   teamzlab.com
bash scripts/cf-dns.sh get    teamzlab.com auth.teamzlab.com
bash scripts/cf-dns.sh set    teamzlab.com CNAME auth.teamzlab.com ai-resume-coach-by-teamzlab.web.app
bash scripts/cf-dns.sh set    teamzlab.com TXT  _dmarc.teamzlab.com 'v=DMARC1; p=none; rua=mailto:hello@teamzlab.com'
bash scripts/cf-dns.sh delete teamzlab.com auth.teamzlab.com CNAME
```

`set` is idempotent — it updates a matching record rather than adding a second one, so
re-running a setup script cannot produce duplicates.

## The proxy rule

`set` creates records **DNS-only (grey cloud)** unless you pass `--proxied`. That
default is deliberate:

- **Never proxy** anything used for certificate issuance or domain verification —
  Firebase Auth sending domains, Firebase Hosting custom domains, ACME challenges. The
  orange cloud terminates TLS at Cloudflare and the issuing service never sees its own
  challenge, so verification hangs with no error that says why.
- **Proxy** ordinary web traffic you want cached and shielded.

## Firebase Auth sending domain, end to end

The reason this file exists. Verification mail sent from
`noreply@<project>.firebaseapp.com` has no alignment with the company domain and is
shared with every Firebase project, so it lands in spam — and Firebase silently refuses
custom email BODIES until a sending domain is verified (the API returns 200 and keeps
the stock template).

```bash
# 1. Register the domain with Hosting and Auth (API, no console needed)
TOK=$(gcloud auth print-access-token)
curl -s -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" -d '{}' \
  "https://firebasehosting.googleapis.com/v1beta1/projects/$P/sites/$SITE/customDomains?customDomainId=auth.teamzlab.com"

# 2. Ask Firebase what it wants, rather than guessing
curl -s -H "Authorization: Bearer $TOK" \
  "https://firebasehosting.googleapis.com/v1beta1/projects/$P/sites/$SITE/customDomains/auth.teamzlab.com"
#    -> requiredDnsUpdates.desired[].records[]

# 3. Write it
bash scripts/cf-dns.sh set teamzlab.com CNAME auth.teamzlab.com "$SITE.web.app"

# 4. Point Auth at it
curl -s -X PATCH -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"notification":{"sendEmail":{"dnsInfo":{"customDomain":"auth.teamzlab.com"}}}}' \
  "https://identitytoolkit.googleapis.com/admin/v2/projects/$P/config?updateMask=notification.sendEmail.dnsInfo.customDomain"
```

Use a **subdomain** (`auth.`), never the apex. teamzlab.com's root SPF points at Zoho for
real company mail, and a subdomain leaves it untouched.
