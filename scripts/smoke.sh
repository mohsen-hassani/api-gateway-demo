#!/usr/bin/env bash
# Calls every service directly on its host port and checks the basics.
set -u

usage() {
  cat <<'USAGE'
Usage: scripts/smoke.sh

Checks every service on its Docker Compose host port (127.0.0.1): probes, one business
endpoint each, the x-service-* headers, /debug/request, the orders -> inventory -> pricing
chain on orders-v1 and orders-v2, 401 without identity headers, and the frontend.

Env:
  HOST          host to call (default 127.0.0.1)
  WAIT_SECONDS  how long to wait for services to answer (default 60)

Exits non-zero if any check fails.
USAGE
}
[ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] && { usage; exit 0; }

HOST="${HOST:-127.0.0.1}"
WAIT_SECONDS="${WAIT_SECONDS:-60}"
for tool in curl jq; do
  command -v "$tool" >/dev/null || { echo "$tool is required" >&2; exit 2; }
done

declare -A PORT=(
  [frontend]=8080 [blog-service]=8001 [newsletter-service]=8002 [orders-v1]=8003
  [orders-v2]=8013 [inventory-service]=8004 [pricing-service]=8005 [auth-service]=8006
)
declare -A SERVICE_NAME=(
  [frontend]=frontend [blog-service]=blog-service [newsletter-service]=newsletter-service
  [orders-v1]=orders-service [orders-v2]=orders-service [inventory-service]=inventory-service
  [pricing-service]=pricing-service [auth-service]=auth-service
)
declare -A VERSION=([orders-v2]=v2)

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
failures=0

pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s\n' "$1"; failures=$((failures + 1)); }

# call METHOD URL [curl args...] -> sets $status, $body, and writes headers to $tmp/headers
call() {
  local method=$1 url=$2
  shift 2
  status=$(curl -sS -m 10 -X "$method" -D "$tmp/headers" -o "$tmp/body" -w '%{http_code}' "$@" "$url" 2>"$tmp/err") || status=000
  body=$(cat "$tmp/body" 2>/dev/null)
}

header() { grep -i "^$1:" "$tmp/headers" | head -1 | cut -d: -f2- | tr -d '\r' | sed 's/^ *//'; }

expect_status() { # description want
  if [ "$status" = "$2" ]; then pass "$1"; else fail "$1 (want $2, got $status: ${body:0:120})"; fi
}
expect_jq() { # description jq-filter  (filter must output true)
  if [ "$(printf '%s' "$body" | jq -r "$2" 2>/dev/null)" = "true" ]; then pass "$1"; else fail "$1 (body: ${body:0:160})"; fi
}

url() { echo "http://$HOST:${PORT[$1]}$2"; }

echo "Waiting for services (up to ${WAIT_SECONDS}s)"
deadline=$((SECONDS + WAIT_SECONDS))
for svc in "${!PORT[@]}"; do
  until [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' "$(url "$svc" /healthz)")" = 200 ]; do
    if [ $SECONDS -ge $deadline ]; then echo "  $svc did not become healthy on port ${PORT[$svc]}" >&2; exit 1; fi
    sleep 1
  done
done

echo "Probes and response headers"
for svc in frontend blog-service newsletter-service orders-v1 orders-v2 inventory-service pricing-service auth-service; do
  call GET "$(url "$svc" /healthz)"; expect_status "$svc /healthz" 200
  call GET "$(url "$svc" /readyz)"; expect_status "$svc /readyz" 200
  [ "$(header x-service-name)" = "${SERVICE_NAME[$svc]}" ] && pass "$svc x-service-name" || fail "$svc x-service-name ($(header x-service-name))"
  [ "$(header x-service-version)" = "${VERSION[$svc]:-v1}" ] && pass "$svc x-service-version" || fail "$svc x-service-version ($(header x-service-version))"
  [ -n "$(header x-instance-id)" ] && pass "$svc x-instance-id" || fail "$svc x-instance-id missing"
done

echo "Business endpoints"
call GET "$(url blog-service /posts)"; expect_status "blog GET /posts" 200
expect_jq "blog returns 5 posts" '(.posts | length) == 5'
call GET "$(url blog-service /posts/2)"; expect_jq "blog GET /posts/2 has a body" '.id == 2 and (.body | length) > 0'
call GET "$(url blog-service /posts/99)"; expect_status "blog unknown post" 404
expect_jq "blog 404 error shape" '.error == "post_not_found" and .path == "/posts/99"'

call POST "$(url newsletter-service /unsubscribe)" -H 'content-type: application/json' -d '{"email":"smoke@example.com"}'
expect_status "newsletter POST /unsubscribe" 200
expect_jq "newsletter says unsubscribed" '.status == "unsubscribed"'

call GET "$(url pricing-service /price/SKU-002)"; expect_jq "pricing GET /price/SKU-002" '.amount == 19.99 and .currency == "EUR"'
call GET "$(url inventory-service /stock/SKU-002)"; expect_jq "inventory GET /stock/SKU-002 (via pricing)" '.in_stock == 42 and .price.amount == 19.99'

echo "Debug echo"
for svc in blog-service newsletter-service orders-v1 inventory-service pricing-service; do
  call GET "$(url "$svc" '/debug/request/some/path?a=1&b=2')" -H 'x-smoke-header: hello'
  expect_jq "$svc /debug/request echoes path, query and header" \
    '.path == "/debug/request/some/path" and .query == "a=1&b=2" and .headers["x-smoke-header"] == "hello" and (.client | length) > 0'
done

echo "Orders chain (orders -> inventory -> pricing)"
rid="smoke-$RANDOM$RANDOM"
declare -A seeded
# a fresh user per run: orders created by an earlier run would otherwise change the list
user="smoke-user-$RANDOM$RANDOM"
ident=(-H "x-user-id: $user" -H "x-user-email: $user@example.com")
call GET "$(url orders-v1 /orders)"; expect_status "orders-v1 without identity" 401
expect_jq "orders 401 is missing_identity" '.error == "missing_identity"'
call GET "$(url orders-v2 /orders)"; expect_status "orders-v2 without identity" 401
for svc in orders-v1 orders-v2; do
  call GET "$(url "$svc" /orders)" "${ident[@]}" -H "x-request-id: $rid-$svc"
  expect_status "$svc GET /orders" 200
  expect_jq "$svc echoes identity and has stock + price" \
    ".user_id == \"$user\" and .user_email == \"$user@example.com\" and (.orders | length) == 2 and (.orders | all(.stock.price.currency == \"EUR\"))"
  [ "$(header x-request-id)" = "$rid-$svc" ] && pass "$svc returns the request id" || fail "$svc request id ($(header x-request-id))"
  seeded[$svc]=$(printf '%s' "$body" | jq -c .orders)
done
call GET "$(url orders-v1 /orders)" "${ident[@]}"; expect_jq "orders-v1 version v1, no recommendations" '.version == "v1" and (has("recommendations") | not)'
call GET "$(url orders-v2 /orders)" "${ident[@]}"; expect_jq "orders-v2 version v2 with recommendations" '.version == "v2" and (.recommendations | type) == "array"'
[ "${seeded[orders-v1]}" = "${seeded[orders-v2]}" ] && pass "v1 and v2 return the same seeded orders" || fail "v1 and v2 orders differ"
call POST "$(url orders-v1 /orders)" "${ident[@]}" -H 'content-type: application/json' -d '{"sku":"SKU-003","quantity":2}'
expect_status "orders-v1 POST /orders" 201
call POST "$(url orders-v1 /orders)" "${ident[@]}" -H 'content-type: application/json' -d '{"sku":"SKU-003","quantity":99}'
expect_status "orders rejects quantity 99" 422

# The same request id should appear in all three service logs (needs docker compose)
if command -v docker >/dev/null && docker compose ps -q >/dev/null 2>&1 && [ -n "$(docker compose ps -q 2>/dev/null)" ]; then
  sleep 1
  for svc in orders-v1 inventory-service pricing-service; do
    docker compose logs --no-color "$svc" 2>/dev/null | grep -q "$rid-orders-v1" \
      && pass "$svc logged request id $rid-orders-v1" || fail "$svc did not log request id $rid-orders-v1"
  done
else
  echo "  skip request id in logs (docker compose not running here)"
fi

echo "Auth service"
email="smoke-$RANDOM$RANDOM@example.com"
call POST "$(url auth-service /register)" -H 'content-type: application/json' -d "{\"email\":\"$email\",\"password\":\"smoke-password\"}"
expect_status "auth POST /register" 201
call POST "$(url auth-service /login)" -H 'content-type: application/json' -d "{\"email\":\"$email\",\"password\":\"smoke-password\"}"
expect_status "auth POST /login" 200
expect_jq "auth login body" '.token_type == "Bearer" and .expires_in == 900 and (.access_token | split(".") | length) == 3'

echo "Frontend"
call GET "$(url frontend /)"; expect_status "frontend GET /" 200
grep -qi '<title>' "$tmp/body" && pass "frontend serves the page" || fail "frontend page has no <title>"
call GET "$(url frontend /assets/config.js)"; expect_status "frontend GET /assets/config.js" 200
grep -q 'window.APP_CONFIG' "$tmp/body" && pass "config.js sets window.APP_CONFIG" || fail "config.js content"
call GET "$(url frontend /assets/app.js)"; expect_status "frontend GET /assets/app.js" 200
call GET "$(url frontend /assets/style.css)"; expect_status "frontend GET /assets/style.css" 200

echo
if [ "$failures" -eq 0 ]; then echo "All smoke checks passed."; else echo "$failures check(s) failed." >&2; exit 1; fi
