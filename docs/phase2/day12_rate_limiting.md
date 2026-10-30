# Day 12: Rate limiting with BackendTrafficPolicy

[← Roadmap](../ROADMAP.md) · Week two: Envoy Gateway on Kubernetes · [← Day 11](day11_jwt_security_policy.md) · [Day 13 →](day13_canary.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

You port Day 7's rate limits to Envoy Gateway and add one that raw Envoy week didn't have: a **global per-user** limit on orders. Local limits (per client IP on the public routes, tighter on `/auth/login`) live in each Envoy replica. A per-user limit must be shared, so it needs the global rate limit service, backed by Redis and switched on in the Envoy Gateway Helm values. You key it on `x-user-id`, which the Day 11 SecurityPolicy sets from the verified token, so the limit follows the logged-in user and can't be dodged by changing a header. A second signed-up user proves the limit really is per user.

Use `scripts/load.sh` with `TOKEN` from `scripts/auth-flow.sh` (one token per user), and `METHOD=POST` with a `BODY` for `/auth/login`.

## Read first (about 60 min)

1. [Rate limiting concepts](https://gateway.envoyproxy.io/docs/concepts/rate-limiting/) (15 min). Local vs global rate limiting in Envoy Gateway, both configured through BackendTrafficPolicy, and why global needs a separate rate limit service with Redis.
2. [Local rate limit task](https://gateway.envoyproxy.io/docs/tasks/traffic/local-rate-limit/) (20 min). A BackendTrafficPolicy `rateLimit` of type Local with rules, `clientSelectors` and `limit` (requests per unit). Each Envoy replica counts on its own.
3. [Global rate limit task](https://gateway.envoyproxy.io/docs/tasks/traffic/global-rate-limit/) (25 min, Redis setup and client selectors). Deploying Redis, pointing Envoy Gateway at it in the Helm values, and `clientSelectors` that match a header value or source CIDR, including the "distinct" type that gives every value (every user, every IP) its own bucket.

## Learn

Local vs global rate limiting in Envoy Gateway; global needs Redis configured in the Envoy Gateway Helm values; client selectors by source IP and by header.

## AI generates

A Redis deployment, the Helm values change, and a local per-IP policy on public routes, with a tighter one on `/auth/login` to slow down password guessing.

## Your blanks

- [ ] A global per-user limit on orders keyed on `x-user-id`, with your chosen numbers.

## Done when

- [ ] Load tests show 429s per IP on blog and on `/auth/login`.
- [ ] Load tests show 429s per user on orders, while a second signed-up user is unaffected.

## Notes

_Working notes, commands that helped, blanks cut for time. Chosen limits:_

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
