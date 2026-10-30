# Day 3: Routing deep dive

[← Roadmap](../ROADMAP.md) · Week one: raw Envoy in Docker Compose · [← Day 2](day02_first_envoy.md) · [Day 4 →](day04_header_transformation.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

Today is about how Envoy picks a route and how it changes the path on the way upstream. You add the orders route (`/api/orders` → `/orders`), a host-based virtual host, and a catch-all 404 as a direct response. For the catch-all to ever match, the Day 2 frontend route must shrink to exact `/` plus prefix `/assets/`, as the [gateway path map](../PHASE1_TECHNICAL_SPEC.md#4-gateway-path-map-contract-with-the-frontend) describes. You write a regex rewrite yourself, aimed at `GET /orders/{id}`, and fix the order of two overlapping routes.

To see what the upstream actually received, use `/blog/debug/request` (it shows `/debug/request` after the prefix strip). For the orders routes, look at the `path` field that every non-auth service puts in its error bodies, or at the service's JSON log line. Orders answers 401 until Day 6 unless you send `x-user-id` and `x-user-email` yourself.

## Read first (about 60 min)

1. [HTTP routing](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/http_routing) (30 min). How the router filter works: virtual hosts chosen by the Host (`:authority`) header, route matching on path, headers and query parameters, first match wins, plus rewrites, redirects and direct responses. Retries and timeouts per route are previewed here too.
2. [Route components reference](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/route/v3/route_components.proto) (30 min). Read only VirtualHost (`domains`, `routes`), RouteMatch (`prefix`, `path`, `safe_regex`), RouteAction's `prefix_rewrite` and `regex_rewrite` (an RE2 pattern plus a substitution), and DirectResponseAction (a status and an optional body).

## Learn

Prefix vs path vs safe\_regex matching, route ordering, `prefix_rewrite` and `regex_rewrite`, virtual hosts by Host header, `direct_response` for a custom 404.

## AI generates

Routes for orders (`/api/orders` → `/orders`), a host-based virtual host example, and a catch-all 404 (which means narrowing the Day 2 frontend route to exact `/` plus prefix `/assets/`).

## Your blanks

- [ ] A regex rewrite (for example `/api/v1/orders/123` → `/orders/123`).
- [ ] The correct ordering of two overlapping routes.

## Done when

- [ ] `/debug/request` shows the rewritten path the upstream actually received.
- [ ] An unknown path gets your custom 404, and the frontend still loads.

## Notes

_Working notes, commands that helped, blanks cut for time._

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
