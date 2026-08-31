#!/bin/bash
# =============================================================
#  Teamz Lab — Cloudflare DNS, for every project
#  Usage:
#    bash scripts/cf-dns.sh doctor
#    bash scripts/cf-dns.sh list   <zone>
#    bash scripts/cf-dns.sh get    <zone> <fqdn>
#    bash scripts/cf-dns.sh set    <zone> <TYPE> <fqdn> <content> [--proxied]
#    bash scripts/cf-dns.sh delete <zone> <fqdn> [TYPE]
#
#  Examples:
#    bash scripts/cf-dns.sh set teamzlab.com CNAME auth.teamzlab.com ai-resume-coach-by-teamzlab.web.app
#    bash scripts/cf-dns.sh get teamzlab.com auth.teamzlab.com
#
#  WHY THIS EXISTS
#  Every Teamz Lab domain lives on Cloudflare, and every project eventually needs a
#  record: a Firebase Auth sending domain, a store-listing verification TXT, a VPS A
#  record, a DMARC entry. Before this, each one was done by hand in the dashboard and
#  nothing recorded which token could do what — so an agent read `cloudflare-api-token.txt`,
#  saw a valid token, promised to add records, and only found out at the API that the
#  token is Zone:Read. `doctor` exists so that can never be discovered late again.
#
#  CREDENTIALS  (see docs/cloudflare-setup.md)
#    $TEAMZ_CF_DNS_TOKEN_FILE   Zone -> DNS -> Edit     <- required for set/delete
#    $TEAMZ_CF_READ_TOKEN_FILE  Zone -> Zone -> Read    <- enough for list/get
# =============================================================

set -euo pipefail
_SCRIPT="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
SCRIPT_DIR="$(cd "$(dirname "$_SCRIPT")" && pwd)"
AUTOMATION_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck disable=SC1091
source "$AUTOMATION_ROOT/sh/lib/config.sh"
teamz_load_config "$_SCRIPT"

API="https://api.cloudflare.com/client/v4"

_read_token() {
  local f="$1"
  [ -f "$f" ] || return 1
  local t
  t="$(tr -d '\n\r ' < "$f")"
  [ -n "$t" ] || return 1
  printf '%s' "$t"
}

# Returns the first configured token that can actually reach /dns_records.
#
# Capability is PROBED, never assumed from the filename. Both of these have been true
# at once here: a token that is valid, active, lists zones and purges cache, and is
# still refused on every DNS call. Choosing by probe means adding `Zone -> DNS -> Edit`
# to the token you already have is enough — no second file required.
_token_for() {
  local need_write="$1" f t

  for f in "$TEAMZ_CF_DNS_TOKEN_FILE" "$TEAMZ_CF_READ_TOKEN_FILE"; do
    t="$(_read_token "$f" 2>/dev/null)" || continue
    if [ "$need_write" != "1" ]; then
      printf '%s' "$t"; return 0
    fi
    if _can_touch_dns "$t"; then
      printf '%s' "$t"; return 0
    fi
  done

  if [ "$need_write" = "1" ]; then
    cat >&2 <<EOF
ERROR: no Cloudflare token here can write DNS.

  Checked: $TEAMZ_CF_DNS_TOKEN_FILE
           $TEAMZ_CF_READ_TOKEN_FILE

  Easiest fix — widen the token you already have:
    1. https://dash.cloudflare.com/profile/api-tokens
    2. Find the existing Teamz Lab token, "..." -> Edit
    3. Add a permission row:  Zone | DNS | Edit
    4. Zone Resources: Include | All zones from an account | Teamz Lab
    5. Continue -> Save. The token string does not change, so nothing else breaks.
    6. bash scripts/cf-dns.sh doctor

  Or create a separate one and save it to $TEAMZ_CF_DNS_TOKEN_FILE (chmod 600).
  See docs/cloudflare-setup.md.
EOF
  fi
  return 1
}

# One cheap GET. Succeeds only when the token carries a DNS scope; Zone:Read alone
# returns "Authentication error" here, which is exactly the case this guards.
_can_touch_dns() {
  local t="$1" zid
  zid="$(_api "$t" GET "/zones?per_page=1" | python3 -c "
import sys, json
d = json.load(sys.stdin)
rs = d.get('result') or []
print(rs[0]['id'] if rs else '')
" 2>/dev/null)"
  [ -n "$zid" ] || return 1
  _api "$t" GET "/zones/$zid/dns_records?per_page=1" | python3 -c "
import sys, json
raise SystemExit(0 if json.load(sys.stdin).get('success') else 1)
" 2>/dev/null
}

_api() {
  local token="$1" method="$2" path="$3" body="${4:-}"
  if [ -n "$body" ]; then
    curl -sS -X "$method" -H "Authorization: Bearer $token" \
      -H "Content-Type: application/json" -d "$body" "$API$path"
  else
    curl -sS -X "$method" -H "Authorization: Bearer $token" "$API$path"
  fi
}

_zone_id() {
  local token="$1" zone="$2"
  _api "$token" GET "/zones?name=$zone" | python3 -c "
import sys, json
d = json.load(sys.stdin)
rs = d.get('result') or []
if not d.get('success') or not rs:
    sys.stderr.write('ERROR: zone not found or not permitted: ' + json.dumps(d.get('errors'))[:200] + '\n')
    raise SystemExit(1)
print(rs[0]['id'])
"
}

cmd_doctor() {
  echo "Cloudflare credentials"
  for pair in "DNS(write):$TEAMZ_CF_DNS_TOKEN_FILE" "READ:$TEAMZ_CF_READ_TOKEN_FILE"; do
    local label="${pair%%:*}" file="${pair#*:}" t
    printf '  %-12s %s\n' "$label" "$file"
    if ! t="$(_read_token "$file" 2>/dev/null)"; then
      printf '  %-12s -> MISSING\n' ""
      continue
    fi
    # Probe, do not assume. A token being valid says nothing about what it may touch.
    local zones dns
    zones="$(_api "$t" GET "/zones?per_page=50" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(','.join(z['name'] for z in (d.get('result') or [])) if d.get('success') else 'REFUSED')
")"
    printf '  %-12s -> zones: %s\n' "" "${zones:-none}"
    local first="${zones%%,*}"
    if [ -n "$first" ] && [ "$first" != "REFUSED" ]; then
      local zid; zid="$(_zone_id "$t" "$first" 2>/dev/null || true)"
      if [ -n "$zid" ]; then
        dns="$(_api "$t" GET "/zones/$zid/dns_records?per_page=1" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('yes' if d.get('success') else 'NO (Zone:Read only)')
")"
        printf '  %-12s -> can read DNS: %s\n' "" "$dns"
      fi
    fi
  done
}

cmd_list() {
  local zone="$1" t zid
  t="$(_token_for 0)"; zid="$(_zone_id "$t" "$zone")"
  _api "$t" GET "/zones/$zid/dns_records?per_page=200" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if not d.get('success'):
    sys.stderr.write('ERROR: '+json.dumps(d.get('errors'))[:250]+'\n'); raise SystemExit(1)
for r in d['result']:
    print(f\"{r['type']:6s} {r['name']:44s} {r['content'][:60]:62s} proxied={r.get('proxied')}\")
"
}

cmd_get() {
  local zone="$1" name="$2" t zid
  t="$(_token_for 0)"; zid="$(_zone_id "$t" "$zone")"
  _api "$t" GET "/zones/$zid/dns_records?name=$name" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if not d.get('success'):
    sys.stderr.write('ERROR: '+json.dumps(d.get('errors'))[:250]+'\n'); raise SystemExit(1)
rs=d['result']
print(f'{len(rs)} record(s) for $name')
for r in rs:
    print(f\"  {r['type']} -> {r['content']}  proxied={r.get('proxied')} ttl={r['ttl']} id={r['id']}\")
"
}

# Create or update. Idempotent: running it twice leaves one record, not two.
cmd_set() {
  local zone="$1" type="$2" name="$3" content="$4" proxied="false"
  shift 4
  for a in "$@"; do [ "$a" = "--proxied" ] && proxied="true"; done

  local t zid; t="$(_token_for 1)"; zid="$(_zone_id "$t" "$zone")"
  local existing
  existing="$(_api "$t" GET "/zones/$zid/dns_records?name=$name&type=$type" | python3 -c "
import sys,json
d=json.load(sys.stdin)
rs=(d.get('result') or [])
print(rs[0]['id'] if rs else '')
")"

  local body
  body="$(python3 -c "
import json,sys
print(json.dumps({'type':sys.argv[1],'name':sys.argv[2],'content':sys.argv[3],
                  'ttl':300,'proxied':sys.argv[4]=='true'}))
" "$type" "$name" "$content" "$proxied")"

  local out
  if [ -n "$existing" ]; then
    out="$(_api "$t" PUT "/zones/$zid/dns_records/$existing" "$body")"
  else
    out="$(_api "$t" POST "/zones/$zid/dns_records" "$body")"
  fi
  printf '%s' "$out" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if not d.get('success'):
    sys.stderr.write('ERROR: '+json.dumps(d.get('errors'))[:300]+'\n'); raise SystemExit(1)
r=d['result']
print(f\"OK  {r['type']} {r['name']} -> {r['content']}  proxied={r['proxied']} ttl={r['ttl']}\")
"
}

cmd_delete() {
  local zone="$1" name="$2" type="${3:-}" t zid
  t="$(_token_for 1)"; zid="$(_zone_id "$t" "$zone")"
  local q="name=$name"; [ -n "$type" ] && q="$q&type=$type"
  local ids
  ids="$(_api "$t" GET "/zones/$zid/dns_records?$q" | python3 -c "
import sys,json
print('\n'.join(r['id'] for r in (json.load(sys.stdin).get('result') or [])))
")"
  [ -z "$ids" ] && { echo "nothing to delete for $name"; return 0; }
  while read -r id; do
    [ -z "$id" ] && continue
    _api "$t" DELETE "/zones/$zid/dns_records/$id" >/dev/null
    echo "deleted $id"
  done <<< "$ids"
}

case "${1:-doctor}" in
  doctor) cmd_doctor ;;
  list)   shift; cmd_list "$@" ;;
  get)    shift; cmd_get "$@" ;;
  set)    shift; cmd_set "$@" ;;
  delete) shift; cmd_delete "$@" ;;
  *) sed -n '2,20p' "$_SCRIPT"; exit 1 ;;
esac
