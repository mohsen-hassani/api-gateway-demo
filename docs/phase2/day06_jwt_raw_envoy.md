# Day 6: Register, login and JWT in raw Envoy

[← Roadmap](../ROADMAP.md) · Week one: raw Envoy in Docker Compose · [← Day 5](day05_lua_transformation.md) · [Day 7 →](day07_rate_limit_canary.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

Authentication moves into the gateway. Envoy exposes exactly two auth-service paths, `/auth/register` and `/auth/login`, so the frontend can create a user and get a token. The `jwt_authn` filter then verifies that token on `/api/orders`. It checks the signature against `keys/jwks.json` (mounted into Envoy, because auth-service serves no JWKS endpoint), and the issuer, audience and expiry. Envoy copies the `sub` and `email` claims into `x-user-id` and `x-user-email`, the only identity orders-service trusts ([spec sections 5.4 and 6](../PHASE1_TECHNICAL_SPEC.md#6-auth-service-and-the-auth-contract)). The forged-header check proves that a client cannot impersonate someone by sending those headers itself.

`scripts/auth-flow.sh` already exists from Phase 1. Today it runs end to end through Envoy: `export TOKEN=$(scripts/auth-flow.sh)`.

## Read first (about 75 min)

1. [JWT authentication filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/jwt_authn_filter) (20 min). What the filter checks (signature, `iss`, `aud`, `exp`), where it looks for the token (the `Authorization: Bearer` header by default), and that failures return 401 before the request reaches the upstream.
2. [jwt\_authn config reference](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/http/jwt_authn/v3/config.proto) (25 min). JwtProvider (`issuer`, `audiences`, `local_jwks` or `remote_jwks`, `claim_to_headers`, `forward`) and RequirementRule (a route `match` plus `requires`: a provider, `requires_any`, `requires_all`, `allow_missing`). Paths with no matching rule are not checked.
3. [Introduction to JSON Web Tokens](https://jwt.io/introduction) (15 min). A JWT is `header.payload.signature` in base64url, carrying registered claims such as `iss`, `sub`, `aud` and `exp`. With RS256, the private key signs and the public key verifies, and a JWKS is a set of public keys selected by `kid`. That is why the gateway can verify tokens without any shared secret.
4. [OAuth2 filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/oauth2_filter) (15 min, concept only). Here Envoy runs the browser login itself: it redirects to an identity provider and keeps the session in cookies. Contrast it with today's flow, where the frontend gets a token from auth-service and sends it explicitly.

## Learn

The `jwt_authn` filter: providers, local JWKS (a file mounted into Envoy, since auth-service serves no JWKS endpoint) versus remote JWKS, `rules` per route, and `claim_to_headers`. The flow: the frontend registers and logs in through Envoy (public routes), receives a token, then sends it as `Authorization: Bearer ...` on every call to protected routes. Read about the `oauth2` filter conceptually only.

## AI generates

Exact-path routes and a cluster for `/auth/register` and `/auth/login` to the auth-service (the `/auth` prefix stripped), and the `jwt_authn` provider reading `keys/jwks.json` (mounted into Envoy).

## Your blanks

- [ ] The `rules` section, so that `/`, `/blog`, `/unsubscribe`, `/auth/register` and `/auth/login` stay open while `/api/orders` requires a valid token.
- [ ] Map the `sub` and `email` claims to `x-user-id` and `x-user-email`.

## Done when

- [ ] In the browser, opening Orders shows the login and register form (the 401), and after registering and logging in the orders panel loads.
- [ ] With curl, orders returns 401 without a token and with a garbage token, and 200 with a valid one.
- [ ] A request carrying a forged `x-user-id` header plus a valid token still comes back with the token's `user_id` in the orders response.

## Notes

_Working notes, commands that helped, blanks cut for time._

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
