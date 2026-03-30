#!/usr/bin/env bash

# Shared configuration loader for teamz-company-automation shell scripts.
# Source this file, then call `teamz_load_config`.

teamz_load_config() {
  local script_path script_dir
  script_path="$(readlink -f "$1" 2>/dev/null || realpath "$1" 2>/dev/null || echo "$1")"
  script_dir="$(cd "$(dirname "$script_path")" && pwd)"

  # sh/ -> automation root -> host project root
  export TEAMZ_AUTOMATION_ROOT="${TEAMZ_AUTOMATION_ROOT:-$(cd "$script_dir/.." && pwd)}"
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
  case "$TEAMZ_SITE_PROPERTY" in
    */) : ;;
    *) TEAMZ_SITE_PROPERTY="${TEAMZ_SITE_PROPERTY}/" ;;
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
  export TEAMZ_CLARITY_TOKEN_FILE="${TEAMZ_CLARITY_TOKEN_FILE:-$TEAMZ_CONFIG_DIR/clarity-token.txt}"

  export TEAMZ_DATA_DIR="${TEAMZ_DATA_DIR:-$TEAMZ_AUTOMATION_ROOT/data}"
  export TEAMZ_REPORT_DIR="${TEAMZ_REPORT_DIR:-$TEAMZ_HOST_SITE_ROOT/docs}"
}

