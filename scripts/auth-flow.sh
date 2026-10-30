#!/usr/bin/env bash
# Registers a test user, logs in, optionally calls the protected orders endpoint.
# Progress goes to stderr and only the token goes to stdout:  export TOKEN=$(scripts/auth-flow.sh)
set -u

usage() {
  cat <<'USAGE'
Usage: scripts/auth-flow.sh [base-url]

Registers a user (random, or EMAIL / PASSWORD from the environment; an already registered
EMAIL is fine), logs in, and calls the protected orders endpoint with the token. Prints only
the token on stdout.

  base-url    defaults to http://localhost:10000 (the gateway, from Phase 2)

Env:
  AUTH_URL    where /register and /login live (default <base-url>/auth)
  ORDERS_URL  protected endpoint to call (default <base-url>/api/orders; empty skips the call)
  EMAIL, PASSWORD   credentials to use (default: random user, random password)

Example without a gateway:  AUTH_URL=http://localhost:8006 ORDERS_URL= scripts/auth-flow.sh
USAGE
}
case "${1:-}" in -h|--help) usage; exit 0 ;; esac

for tool in curl jq; do
  command -v "$tool" >/dev/null || { echo "$tool is required" >&2; exit 2; }
done

BASE="${1:-http://localhost:10000}"
BASE="${BASE%/}"
AUTH_URL="${AUTH_URL-$BASE/auth}"
ORDERS_URL="${ORDERS_URL-$BASE/api/orders}"
EMAIL="${EMAIL:-demo-$RANDOM$RANDOM@example.com}"
PASSWORD="${PASSWORD:-demo-password-$RANDOM}"
creds=$(jq -n --arg email "$EMAIL" --arg password "$PASSWORD" '{email: $email, password: $password}')

log() { echo "$*" >&2; }
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

post() { # path -> prints status, body in $tmp
  curl -sS -m 15 -X POST -H 'content-type: application/json' -d "$creds" -o "$tmp" -w '%{http_code}' "$AUTH_URL$1"
}

log "register $EMAIL at $AUTH_URL/register"
status=$(post /register) || { log "could not reach $AUTH_URL"; exit 1; }
case "$status" in
  201) log "  registered" ;;
  409) log "  already registered, continuing" ;;
  *) log "  register failed with $status: $(cat "$tmp")"; exit 1 ;;
esac

log "login"
status=$(post /login) || exit 1
if [ "$status" != 200 ]; then log "  login failed with $status: $(cat "$tmp")"; exit 1; fi
token=$(jq -r '.access_token // empty' "$tmp")
[ -n "$token" ] || { log "  login response has no access_token: $(cat "$tmp")"; exit 1; }
log "  got a token (expires in $(jq -r .expires_in "$tmp")s)"

if [ -n "$ORDERS_URL" ]; then
  log "GET $ORDERS_URL with the token"
  status=$(curl -sS -m 15 -H "authorization: Bearer $token" -o "$tmp" -w '%{http_code}' "$ORDERS_URL") || exit 1
  if [ "$status" != 200 ]; then log "  failed with $status: $(head -c 300 "$tmp")"; exit 1; fi
  log "  200: $(jq -c '{user_id, user_email, version, orders: (.orders | length)}' "$tmp" 2>/dev/null || head -c 200 "$tmp")"
fi

printf '%s\n' "$token"
