#!/usr/bin/env bash
# Checks any auth implementation against the auth contract (spec section 6).
set -u

usage() {
  cat <<'USAGE'
Usage: scripts/auth-contract-test.sh <base-url>

<base-url> is where /register and /login live, for example http://localhost:8006, or
http://localhost:10000/auth through the gateway.

Checks: register (201), duplicate register (409), password too short (422), email
normalisation, login (200 with the documented body), wrong password and unknown email both
401 invalid_credentials, the required claims with the expected iss and aud, exp - iat ==
expires_in, the kid is in the JWKS, the signature verifies against the JWKS, and /me, /docs,
/redoc, /openapi.json, /debug/request and /.well-known/jwks.json all return 404.

Signatures are verified by scripts/lib/verify_jwt.py inside the auth-service image.

Env:
  JWKS_FILE     JWKS to verify against (default keys/jwks.json)
  JWKS_URL      fetch the JWKS from this URL instead (for a replacement that publishes one)
  EXPECTED_ISS  expected iss claim (default http://auth-service)
  EXPECTED_AUD  expected aud claim (default envoy-demo)
  AUTH_IMAGE    image that runs verify_jwt.py (default ${REGISTRY:-localhost}/envoy-demo-auth:${TAG:-dev})
  VERIFY_PYTHON a local python with PyJWT and cryptography, used instead of docker

Exits non-zero if any check fails.
USAGE
}
case "${1:-}" in -h|--help) usage; exit 0 ;; "") usage >&2; exit 2 ;; esac

BASE="${1%/}"
JWKS_FILE="${JWKS_FILE:-keys/jwks.json}"
EXPECTED_ISS="${EXPECTED_ISS:-http://auth-service}"
EXPECTED_AUD="${EXPECTED_AUD:-envoy-demo}"
AUTH_IMAGE="${AUTH_IMAGE:-${REGISTRY:-localhost}/envoy-demo-auth:${TAG:-dev}}"
LIB_DIR="$(cd "$(dirname "$0")/lib" && pwd)"

for tool in curl jq; do
  command -v "$tool" >/dev/null || { echo "$tool is required" >&2; exit 2; }
done

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
failures=0
pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s\n' "$1"; failures=$((failures + 1)); }

# call METHOD PATH [json-body] -> $status, $body
call() {
  local args=()
  [ $# -ge 3 ] && args=(-H 'content-type: application/json' -d "$3")
  status=$(curl -sS -m 15 -X "$1" -o "$tmp/body" -w '%{http_code}' "${args[@]}" "$BASE$2" 2>"$tmp/err") || status=000
  body=$(cat "$tmp/body")
}
jq_is() { [ "$(printf '%s' "$body" | jq -r "$1" 2>/dev/null)" = "true" ]; }

if [ -n "${JWKS_URL:-}" ]; then
  curl -sSf -m 15 -o "$tmp/jwks.json" "$JWKS_URL" || { echo "could not fetch JWKS_URL=$JWKS_URL" >&2; exit 1; }
  JWKS_FILE="$tmp/jwks.json"
fi
[ -f "$JWKS_FILE" ] || { echo "JWKS file $JWKS_FILE not found (run make keys, or set JWKS_FILE / JWKS_URL)" >&2; exit 1; }

email="contract-$RANDOM$RANDOM@example.com"
password="contract-password"
creds="{\"email\":\"$email\",\"password\":\"$password\"}"

echo "Register"
call POST /register "$creds"
if [ "$status" = 201 ] && jq_is ".email == \"$email\" and (.id | type) == \"string\" and (.id | length) > 0"; then pass "register returns 201 with id and email"; else fail "register (got $status: ${body:0:150})"; fi
call POST /register "$creds"
if [ "$status" = 409 ] && jq_is '.error == "email_taken"'; then pass "duplicate register is 409 email_taken"; else fail "duplicate register (got $status: ${body:0:150})"; fi
call POST /register "{\"email\":\"short-$email\",\"password\":\"short\"}"
if [ "$status" = 422 ] && jq_is '.error == "invalid_input"'; then pass "short password is 422 invalid_input"; else fail "short password (got $status: ${body:0:150})"; fi
upper=$(printf '%s' "$email" | tr 'a-z' 'A-Z')
call POST /register "{\"email\":\"  $upper \",\"password\":\"$password\"}"
if [ "$status" = 409 ]; then pass "email is trimmed and lowercased (differently written duplicate is 409)"; else fail "email normalisation (got $status: ${body:0:150})"; fi

echo "Login"
call POST /login "$creds"
token=""
if [ "$status" = 200 ] && jq_is '.token_type == "Bearer" and (.expires_in | type) == "number" and (.access_token | type) == "string"'; then
  pass "login returns 200 with access_token, token_type and expires_in"
  token=$(printf '%s' "$body" | jq -r .access_token)
  expires_in=$(printf '%s' "$body" | jq -r .expires_in)
else
  fail "login (got $status: ${body:0:150})"
fi
call POST /login "{\"email\":\"$email\",\"password\":\"wrong-password\"}"
wrong_status=$status; wrong_body=$body
if [ "$status" = 401 ] && jq_is '.error == "invalid_credentials"'; then pass "wrong password is 401 invalid_credentials"; else fail "wrong password (got $status: ${body:0:150})"; fi
call POST /login "{\"email\":\"nobody-$email\",\"password\":\"$password\"}"
if [ "$status" = 401 ] && jq_is '.error == "invalid_credentials"'; then pass "unknown email is 401 invalid_credentials"; else fail "unknown email (got $status: ${body:0:150})"; fi
if [ "$status" = "$wrong_status" ] && [ "$(printf '%s' "$body" | jq -S .)" = "$(printf '%s' "$wrong_body" | jq -S .)" ]; then pass "wrong password and unknown email give the same answer"; else fail "wrong password and unknown email answers differ"; fi

echo "Token"
if [ -n "$token" ]; then
  if [ -n "${VERIFY_PYTHON:-}" ]; then
    verified=$("$VERIFY_PYTHON" "$LIB_DIR/verify_jwt.py" "$JWKS_FILE" "$token" "$EXPECTED_ISS" "$EXPECTED_AUD" 2>"$tmp/verify.err")
  else
    command -v docker >/dev/null || { echo "docker is required to verify tokens (or set VERIFY_PYTHON)" >&2; exit 2; }
    verified=$(docker run --rm -v "$LIB_DIR:/lib:ro" -v "$(cd "$(dirname "$JWKS_FILE")" && pwd)/$(basename "$JWKS_FILE"):/jwks.json:ro" \
      "$AUTH_IMAGE" python /lib/verify_jwt.py /jwks.json "$token" "$EXPECTED_ISS" "$EXPECTED_AUD" 2>"$tmp/verify.err")
  fi
  if [ $? -eq 0 ]; then
    pass "kid is in the JWKS, signature verifies, iss=$EXPECTED_ISS and aud=$EXPECTED_AUD are valid"
    body=$verified
    if jq_is '.claims | has("sub") and has("email") and has("iat") and has("exp")'; then pass "claims sub, email, iat and exp are present"; else fail "required claims missing"; fi
    if jq_is ".claims.email == \"$email\""; then pass "email claim is the normalised email"; else fail "email claim is not $email"; fi
    if jq_is ".claims.exp - .claims.iat == $expires_in"; then pass "exp - iat == expires_in ($expires_in)"; else fail "exp - iat != expires_in ($expires_in)"; fi
  else
    fail "token verification: $(cat "$tmp/verify.err")"
  fi
else
  fail "no token to verify"
fi

echo "Nothing else is served"
for path in /me /docs /redoc /openapi.json /debug/request /.well-known/jwks.json; do
  call GET "$path"
  if [ "$status" = 404 ]; then pass "GET $path is 404"; else fail "GET $path (want 404, got $status)"; fi
done

echo
if [ "$failures" -eq 0 ]; then echo "Auth contract: all checks passed."; else echo "Auth contract: $failures check(s) failed." >&2; exit 1; fi
