#!/usr/bin/env bash

# Shared configuration loader for teamz-company-automation shell scripts.
# Source this file, then call `teamz_load_config`.

teamz_load_config() {
  local script_path script_dir
  script_path="$(readlink -f "$1" 2>/dev/null || realpath "$1" 2>/dev/null || echo "$1")"
  script_dir="$(cd "$(dirname "$script_path")" && pwd)"

  # sh/ -> automation root
  export TEAMZ_AUTOMATION_ROOT="${TEAMZ_AUTOMATION_ROOT:-$(cd "$script_dir/.." && pwd)}"

  # HOST SITE ROOT — the repo that CALLED us. Must NOT be derived from the *resolved*
  # script path: every script in a host repo's scripts/ dir is a SYMLINK into this
  # automation repo, so readlink -f collapses them all to <automation>/sh|py, and
  # <automation>/.. is the shared parent dir — never the caller. The old line below did
  # exactly that, so EVERY host repo silently fell back to the default site
  # (tool.teamzlab.com): other sites' nightlies pulled GSC for, and requested indexing
  # of, the WRONG property, and build-sitemap/search-index wrote their output one level
  # above the repo. Found live 2026-07-12 on apps.teamzlab.com.
  # Resolution order: explicit env > walk up from CWD for .teamz-automation.env > legacy.
  if [[ -z "${TEAMZ_HOST_SITE_ROOT:-}" ]]; then
    local _d="$PWD"
    while [[ "$_d" != "/" && -n "$_d" ]]; do
      if [[ -f "$_d/.teamz-automation.env" ]]; then
        export TEAMZ_HOST_SITE_ROOT="$_d"
        break
      fi
      _d="$(dirname "$_d")"
    done
  fi
  export TEAMZ_HOST_SITE_ROOT="${TEAMZ_HOST_SITE_ROOT:-$(cd "$TEAMZ_AUTOMATION_ROOT/.." && pwd)}"

  # Optional base config file (machine-level, shared across projects).
  local base_env_default
  base_env_default="$HOME/.config/teamzlab/automation.base.env"
  if [[ -n "${TEAMZ_BASE_ENV:-}" && -f "${TEAMZ_BASE_ENV}" ]]; then
    # shellcheck disable=SC1090
    source "${TEAMZ_BASE_ENV}"
  elif [[ -f "$base_env_default" ]]; then
    # shellcheck disable=SC1090
    source "$base_env_default"
  fi

  # Optional project-level env files (override base values).
  if [[ -n "${TEAMZ_AUTOMATION_ENV:-}" && -f "${TEAMZ_AUTOMATION_ENV}" ]]; then
    # shellcheck disable=SC1090
    source "${TEAMZ_AUTOMATION_ENV}"
  elif [[ -f "${TEAMZ_HOST_SITE_ROOT}/.teamz-automation.env" ]]; then
    # shellcheck disable=SC1091
    source "${TEAMZ_HOST_SITE_ROOT}/.teamz-automation.env"
  elif [[ -f "${TEAMZ_AUTOMATION_ROOT}/.teamz-automation.env" ]]; then
    # shellcheck disable=SC1091
    source "${TEAMZ_AUTOMATION_ROOT}/.teamz-automation.env"
  fi

  export TEAMZ_SITE_URL="${TEAMZ_SITE_URL:-https://tool.teamzlab.com/}"
  export TEAMZ_SITE_PROPERTY="${TEAMZ_SITE_PROPERTY:-$TEAMZ_SITE_URL}"

  # A GSC property is one of TWO kinds and they normalise DIFFERENTLY:
  #   URL-prefix   https://tool.teamzlab.com/     -> MUST end in "/"
  #   domain       sc-domain:goalkit.teamzlab.com -> MUST NOT end in "/"
  # The old code appended "/" to both, producing "sc-domain:goalkit.teamzlab.com/",
  # which the Search Console API rejects with HTTP 400. Every script then reported
  # the site as having no sitemap and zero clicks — goalkit really has 920 clicks at
  # a 16.7% CTR, its best-converting property. Found live 2026-07-12.
  case "$TEAMZ_SITE_PROPERTY" in
    sc-domain:*) TEAMZ_SITE_PROPERTY="${TEAMZ_SITE_PROPERTY%/}" ;;
    */)          : ;;
    *)           TEAMZ_SITE_PROPERTY="${TEAMZ_SITE_PROPERTY}/" ;;
  esac
  case "$TEAMZ_SITE_URL" in
    */) : ;;
    *) TEAMZ_SITE_URL="${TEAMZ_SITE_URL}/" ;;
  esac

  export TEAMZ_CONFIG_DIR="${TEAMZ_CONFIG_DIR:-$HOME/.config/teamzlab}"
  export TEAMZ_GOOGLE_CLOUD_PROJECT="${TEAMZ_GOOGLE_CLOUD_PROJECT:-teamzlab-tools}"
  export TEAMZ_GA4_PROPERTY_ID="${TEAMZ_GA4_PROPERTY_ID:-528521795}"
  export TEAMZ_PROJECT_TYPE="${TEAMZ_PROJECT_TYPE:-website}"

  export TEAMZ_SC_TOKEN_FILE="${TEAMZ_SC_TOKEN_FILE:-$TEAMZ_CONFIG_DIR/search-console-token.json}"
  export TEAMZ_GA4_TOKEN_FILE="${TEAMZ_GA4_TOKEN_FILE:-$TEAMZ_CONFIG_DIR/analytics-token.json}"
  export TEAMZ_ADSENSE_TOKEN_FILE="${TEAMZ_ADSENSE_TOKEN_FILE:-$TEAMZ_CONFIG_DIR/adsense-token.json}"
  export TEAMZ_PAGESPEED_KEY_FILE="${TEAMZ_PAGESPEED_KEY_FILE:-$TEAMZ_CONFIG_DIR/pagespeed-api-key.txt}"
  # IndexNow key must be hex (8-128 chars); per-host value lives in the host's .teamz-automation.env
  export TEAMZ_INDEXNOW_KEY="${TEAMZ_INDEXNOW_KEY:-teamzlab-indexnow-key}"
  export TEAMZ_CLARITY_TOKEN_FILE="${TEAMZ_CLARITY_TOKEN_FILE:-$TEAMZ_CONFIG_DIR/clarity-token.txt}"

  # Cloudflare DNS. TWO files on purpose, because conflating them cost a whole round
  # trip once: `cloudflare-api-token.txt` is Zone:Read only — it can list zones and
  # nothing else, and every /dns_records call with it returns "Authentication error".
  # DNS writes need their own token with Zone -> DNS -> Edit, kept separately so a
  # script can tell which capability it actually has instead of assuming.
  export TEAMZ_CF_READ_TOKEN_FILE="${TEAMZ_CF_READ_TOKEN_FILE:-$TEAMZ_CONFIG_DIR/cloudflare-api-token.txt}"
  export TEAMZ_CF_DNS_TOKEN_FILE="${TEAMZ_CF_DNS_TOKEN_FILE:-$TEAMZ_CONFIG_DIR/cloudflare-dns-token.txt}"

  export TEAMZ_DATA_DIR="${TEAMZ_DATA_DIR:-$TEAMZ_AUTOMATION_ROOT/data}"
  export TEAMZ_REPORT_DIR="${TEAMZ_REPORT_DIR:-$TEAMZ_HOST_SITE_ROOT/docs}"
}

