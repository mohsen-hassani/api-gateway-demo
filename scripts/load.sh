#!/usr/bin/env bash
# Sends sequential requests and prints a count per status code.
set -u

usage() {
  cat <<'USAGE'
Usage: scripts/load.sh <url> [count=100]

Sends <count> sequential requests to <url> and prints how many came back with each status.

Env:
  TOKEN   sent as "Authorization: Bearer $TOKEN"
  METHOD  HTTP method (default GET)
  BODY    JSON body, sent with content-type: application/json (needed for POST /auth/login)

Example: METHOD=POST BODY='{"email":"a@b.co","password":"wrong-password"}' scripts/load.sh http://localhost:10000/auth/login 30
USAGE
}
case "${1:-}" in -h|--help) usage; exit 0 ;; "") usage >&2; exit 2 ;; esac

command -v curl >/dev/null || { echo "curl is required" >&2; exit 2; }
url=$1
count=${2:-100}
case "$count" in ''|*[!0-9]*) echo "count must be a number" >&2; exit 2 ;; esac

args=(-sS -m 15 -o /dev/null -w '%{http_code}\n' -X "${METHOD:-GET}")
[ -n "${TOKEN:-}" ] && args+=(-H "authorization: Bearer $TOKEN")
[ -n "${BODY:-}" ] && args+=(-H 'content-type: application/json' -d "$BODY")

for ((i = 0; i < count; i++)); do
  curl "${args[@]}" "$url" 2>/dev/null || echo 000
done | sort | uniq -c | awk '{printf "%6d x %s\n", $1, $2}'
