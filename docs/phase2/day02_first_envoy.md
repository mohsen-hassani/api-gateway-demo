# Day 2: First Envoy in front of the app

[← Roadmap](../ROADMAP.md) · Week one: raw Envoy in Docker Compose · [← Day 1](day01_foundations.md) · [Day 3 →](day03_routing.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

Envoy goes in front of the Phase 1 app for the first time. You add an `envoy` service to Docker Compose with a static `envoy/envoy.yaml`: one listener on port 10000, the HTTP connection manager, and routes to the blog-service and the frontend. You write the newsletter route and cluster yourself. After today the frontend page opens through Envoy, and its Blog and Newsletter panels work, because the page uses same-origin URLs ([spec section 8.1](../PHASE1_TECHNICAL_SPEC.md#81-files-and-configuration)).

Follow the [gateway path map](../PHASE1_TECHNICAL_SPEC.md#4-gateway-path-map-contract-with-the-frontend): `/blog` has its prefix stripped before it reaches blog-service, and `/unsubscribe` is passed through unchanged. A simple `/` prefix route to the frontend is fine today; Day 3 narrows it.

## Read first (about 60 min)

1. [Quick start: static configuration](https://www.envoyproxy.io/docs/envoy/latest/start/quick-start/configuration-static) (20 min). The anatomy of a bootstrap file: `static_resources` with `listeners` and `clusters`, plus the `admin` block. This is the skeleton of today's `envoy.yaml`.
2. [Service discovery types](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery) (15 min, focus on STRICT\_DNS). The ways a cluster finds its hosts: STATIC, STRICT\_DNS, LOGICAL\_DNS, EDS and ORIGINAL\_DST. STRICT\_DNS keeps resolving a name and uses every returned address as an endpoint, which fits Compose service names like `blog-service`.
3. [Administration interface](https://www.envoyproxy.io/docs/envoy/latest/operations/admin) (15 min, skim `/clusters`, `/config_dump`, `/stats`). `/clusters` shows each cluster's hosts and health, `/config_dump` shows the full effective config, and `/stats` shows counters and gauges. The admin port must never be exposed publicly.
4. [Front proxy sandbox](https://www.envoyproxy.io/docs/envoy/latest/start/sandboxes/front_proxy) (10 min, closest to what you build today). Envoy in front of two services in Compose, routing by path: essentially today's setup.

## Learn

Static bootstrap config, the admin listener, STRICT\_DNS clusters in Compose.

## AI generates

Envoy added to docker-compose, and an `envoy.yaml` with the listener, the HCM, a route for `/blog` → blog-service, and a route for `/` to the frontend page.

## Your blanks

- [ ] The route and cluster for newsletter-service.

## Done when

- [ ] `curl localhost:10000/blog/posts` and the unsubscribe endpoint both work through Envoy.
- [ ] The frontend page opens at localhost:10000.
- [ ] You can find both clusters in the admin `/clusters` output.

## Notes

_Working notes, commands that helped, blanks cut for time._

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
