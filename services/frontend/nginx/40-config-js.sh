#!/bin/sh
# Generate /assets/config.js from API_BASE_URL. Empty means "same origin".
set -e
escaped=$(printf '%s' "${API_BASE_URL:-}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
printf 'window.APP_CONFIG = { apiBaseUrl: "%s" };\n' "$escaped" > /tmp/config.js
echo "40-config-js.sh: wrote /tmp/config.js (apiBaseUrl=\"${API_BASE_URL:-}\")"
