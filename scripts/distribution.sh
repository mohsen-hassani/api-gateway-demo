#!/usr/bin/env bash
# Sends requests and prints how many responses carried each value of a response header.
set -u

usage() {
  cat <<'USAGE'
Usage: scripts/distribution.sh <url> [count=100] [header=x-service-version]

Sends <count> sequential GET requests to <url> and prints a count per value of the response
header, for example x-instance-id to see load balancing, or x-service-version for a canary.
Responses without the header are counted as "(none)".

Env:
  TOKEN   sent as "Authorization: Bearer $TOKEN"
USAGE
}
case "${1:-}" in -h|--help) usage; exit 0 ;; "") usage >&2; exit 2 ;; esac

command -v curl >/dev/null || { echo "curl is required" >&2; exit 2; }
url=$1
count=${2:-100}
header=$(printf '%s' "${3:-x-service-version}" | tr 'A-Z' 'a-z')
case "$count" in ''|*[!0-9]*) echo "count must be a number" >&2; exit 2 ;; esac

args=(-sS -m 15 -o /dev/null -D -)
[ -n "${TOKEN:-}" ] && args+=(-H "authorization: Bearer $TOKEN")

for ((i = 0; i < count; i++)); do
  value=$(curl "${args[@]}" "$url" 2>/dev/null | tr -d '\r' | awk -F': *' -v h="$header" 'tolower($1) == h {print $2; exit}')
  echo "${value:-(none)}"
done | sort | uniq -c | awk '{c = $1; $1 = ""; sub(/^ /, ""); printf "%6d x %s\n", c, $0}'
