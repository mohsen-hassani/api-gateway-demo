# Day 8: Envoy Gateway on the cluster

[← Roadmap](../ROADMAP.md) · Week two: Envoy Gateway on Kubernetes · [← Day 7](day07_rate_limit_canary.md) · [Day 9 →](day09_internal_isolation.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

Week two starts. Instead of writing Envoy config by hand, you describe intent with Kubernetes Gateway API resources, and Envoy Gateway translates them into the same xDS config you wrote last week. Today you install the Gateway API CRDs and Envoy Gateway (pinned version) with Helm. You then run `make keys` and `make k8s-apply` to deploy the Phase 1 app, including the `auth-jwt-key` Secret and the `auth-jwks` ConfigMap ([spec section 10.2](../PHASE1_TECHNICAL_SPEC.md#102-kubernetes)). Next you expose the Envoy proxy on the single-node cluster and keep its resources small. You write the first HTTPRoute yourself, then find it in the generated Envoy config with `egctl`, linking week two back to week one.

## Read first (about 90 min)

1. [Gateway API overview](https://gateway-api.sigs.k8s.io/concepts/api-overview/) (25 min, GatewayClass, Gateway, HTTPRoute). The resources are split by role: a GatewayClass names the implementation, a Gateway defines listeners (owned by the cluster operator), and HTTPRoutes attach application routing to a Gateway through `parentRefs`. Also covers ReferenceGrant and the status conditions that tell you whether a route was accepted.
2. [Envoy Gateway quickstart](https://gateway.envoyproxy.io/docs/tasks/quickstart/) (20 min). Install, apply an example GatewayClass, Gateway and HTTPRoute, and curl through it: the smallest end-to-end loop.
3. [Install with Helm](https://gateway.envoyproxy.io/docs/install/install-helm/) (15 min). The OCI Helm chart, how to pin a version, the Gateway API CRDs it installs, and where the values live that Day 12 changes for global rate limiting.
4. [Customize EnvoyProxy](https://gateway.envoyproxy.io/docs/tasks/operations/customize-envoyproxy/) (15 min, resources for a small node). The EnvoyProxy resource, referenced from the GatewayClass (or a Gateway), sets the proxy Deployment's replicas, resources and Service type (for example NodePort).
5. [egctl](https://gateway.envoyproxy.io/docs/tasks/operations/egctl/) (15 min, inspecting the generated Envoy config). `egctl config envoy-proxy ...` dumps the generated listeners, routes and clusters from a running proxy, and `egctl x translate` shows the translation offline.

## Learn

GatewayClass, Gateway and HTTPRoute; how Envoy Gateway translates these into xDS; `egctl` for inspecting the generated config.

## Do

- Install the Gateway API CRDs and Envoy Gateway with Helm (pin a stable version).
- Run `make keys`, then deploy the Phase 1 app with kustomize (`make k8s-apply`). This includes the JWT key Secret and the JWKS ConfigMap.
- On the single-node cluster, expose the Envoy service through your existing load balancer setup, MetalLB or a NodePort, with Cloudflare in front for TLS.
- Keep the Envoy proxy's resource requests small (an EnvoyProxy resource).

## AI generates

Helm values, the GatewayClass, the Gateway, and an EnvoyProxy resource with small resources.

## Your blanks

- [ ] Write the HTTPRoute for blog-service yourself.

## Done when

- [ ] Blog is reachable through the gateway.
- [ ] You can find your route in the `egctl config envoy-proxy route` output (or the config dump).
- [ ] The Envoy Gateway version is pinned and noted below.

## Notes

_Working notes, commands that helped, blanks cut for time. Pinned Envoy Gateway version:_

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
