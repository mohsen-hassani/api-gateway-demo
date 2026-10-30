# Day 7: Rate limiting, canary, and week-one review

[← Roadmap](../ROADMAP.md) · Week one: raw Envoy in Docker Compose · [← Day 6](day06_jwt_raw_envoy.md) · [Day 8 →](day08_envoy_gateway.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

Two more demo features in raw Envoy, then a pause to consolidate. First, the local rate limit filter: a token bucket per route, with a loose limit on `/unsubscribe` and a tight one on `/auth/login` to slow down password guessing. Second, canary splitting: weighted clusters send about 90% of orders traffic to orders-v1 and 10% to orders-v2, and a header match sends `x-canary: true` straight to v2. Both orders services already exist in Compose from Phase 1, and their deterministic seeded orders make the split easy to watch ([spec section 5.4](../PHASE1_TECHNICAL_SPEC.md#54-orders-service)).

Use `scripts/load.sh` for the rate limits. For `/auth/login`, set `METHOD=POST` and a `BODY`. Use `scripts/distribution.sh` (with `TOKEN` set) for the split. The day ends with a written review and a git tag for week one.

## Read first (about 60 min)

1. [Local rate limit filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/local_rate_limit_filter) (25 min, token bucket and per-route config). The token bucket fields (`max_tokens`, `tokens_per_fill`, `fill_interval`), enabling and enforcing the filter (`filter_enabled`, `filter_enforced`), per-route overrides through `typed_per_filter_config`, and the 429 response. Limits apply to each Envoy instance separately.
2. [Global rate limiting](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/other_features/global_rate_limiting) (15 min, concept only). Envoy asks an external rate limit service (backed by Redis) whether a request's descriptors are over their limit, so the limit is shared across all instances. Week two (Day 12) uses this.
3. [Traffic shifting and splitting](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/traffic_splitting) (20 min, weighted clusters). Shifting between routes with runtime fractions, splitting one route across clusters with `weighted_clusters`, and steering specific requests with header matches.

## Learn

`local_ratelimit` (token bucket, per route), the idea of global rate limiting with an external service and Redis (reading only), `weighted_clusters`, and header-based route matching.

## AI generates

Clusters for the existing orders-v1 and orders-v2 Compose services, the local rate limit filter (with a tight limit on `/auth/login` to slow down password guessing), and weighted cluster scaffolding.

## Your blanks

- [ ] Token bucket numbers (for example 5 requests per 10 seconds on `/unsubscribe`).
- [ ] The 90/10 weights.
- [ ] A route that sends `x-canary: true` straight to v2.

## Done when

- [ ] `scripts/load.sh` shows 429s past the limit.
- [ ] `scripts/distribution.sh` shows roughly 90/10.

## Review

- [ ] Write half a page in your own words on what each config block does (put it in the Summary below).
- [ ] Commit week one as a tag.

## Notes

_Working notes, commands that helped, blanks cut for time._

## Summary

_Fill in when the day is finished (or skipped). Include the week-one review here; Day 14 rereads it._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
- **Week-one review:**
