# Day 1: Foundations

[← Roadmap](../ROADMAP.md) · Week one: raw Envoy in Docker Compose · [Next: Day 2 →](day02_first_envoy.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

Today is the theory day, and the only long reading day of the plan. You build a mental model of how Envoy handles a request, so that every config block you write later has an obvious place to go. You read the core architecture pages, run the front-proxy sandbox to see a real config working, and look around the admin interface. You also learn where Envoy Gateway fits: it is a control plane that writes Envoy config for you, which is what week two uses.

Pin the Envoy version you will use for week one today, and read the docs for that version from now on.

## Read first (about 3 hours)

1. [What is Envoy](https://www.envoyproxy.io/docs/envoy/latest/intro/what_is_envoy) (15 min). Envoy's design goals: an out-of-process L7 proxy with a pluggable filter architecture, first-class HTTP/2 and gRPC, service discovery, health checking, advanced load balancing and deep observability. Take away why Envoy is an engine you configure, not a ready-made API gateway.
2. [Life of a Request](https://www.envoyproxy.io/docs/envoy/latest/intro/life_of_a_request) (60 min, the most important page of the two weeks). Follows one request from the accepted downstream connection through listener filters, filter chain match, TLS, the HTTP connection manager, the HTTP filter chain, the router, cluster and endpoint selection, the upstream connection pool, and back on the response path. Take away the order of these stages: every later day plugs config into one of them.
3. [Listeners](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/listeners/listeners) (15 min). A listener is a named address (IP and port) that downstream clients connect to. It holds one or more filter chains, chosen per connection. Listener filters (such as the TLS inspector) run before a chain is chosen.
4. [HTTP connection management](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/http_connection_management) (20 min). The HTTP connection manager (HCM) is the network filter that turns bytes into HTTP requests. It supports HTTP/1.1, HTTP/2 and HTTP/3, runs the HTTP filter chain, holds the route table, and manages request ids and header sanitising.
5. [Cluster manager](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/cluster_manager) (15 min). A cluster is a group of upstream hosts. The cluster manager owns all clusters and their health checking, load balancing and connection pools, whether they are defined statically or arrive dynamically (CDS).
6. [xDS and dynamic configuration](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/operations/dynamic_configuration) (15 min). Config can come from a static file or from a management server over the xDS APIs: LDS (listeners), RDS (routes), CDS (clusters), EDS (endpoints) and SDS (secrets). Envoy Gateway is such a management server.
7. [Envoy Gateway concepts](https://gateway.envoyproxy.io/docs/concepts/) (20 min, for Envoy vs Envoy Gateway). Envoy Gateway watches Kubernetes Gateway API resources plus its own policy CRDs, translates them into xDS, and manages the Envoy proxy deployment. You write YAML about intent; it writes the Envoy config.

## Learn

Envoy architecture: downstream vs upstream, listeners, filter chains, network filters vs HTTP filters, the HTTP connection manager, routes, clusters and endpoints. Data plane vs control plane, and xDS in one paragraph. Envoy vs Envoy Gateway.

## Do

Read Quick start and Life of a Request. Run the front-proxy sandbox. Poke around the admin interface (`/clusters`, `/config_dump`, `/stats`).

## AI generates

A one-page cheat sheet of the config hierarchy and 10 self-check questions.

## Your blanks

- [ ] Draw the request flow for one HTTP request through Envoy.
- [ ] Answer the 10 questions without notes.

## Done when

- [ ] You can explain listener → filter chain → HCM → route → cluster → endpoint out loud.
- [ ] The Envoy version for week one is pinned and noted below.

## Notes

_Working notes, commands that helped, blanks cut for time. Pinned Envoy version:_

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
