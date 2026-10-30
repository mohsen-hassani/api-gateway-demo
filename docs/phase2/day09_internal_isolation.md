# Day 9: Public routes and internal-only isolation

[← Roadmap](../ROADMAP.md) · Week two: Envoy Gateway on Kubernetes · [← Day 8](day08_envoy_gateway.md) · [Day 10 →](day10_gateway_transformation.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

This is the "access control" demo feature, in two layers. The first layer is the gateway: "no route means no way in", so you create HTTPRoutes only for the public paths in the [gateway path map](../PHASE1_TECHNICAL_SPEC.md#4-gateway-path-map-contract-with-the-frontend). That means the frontend (exact `/` plus `/assets/`), blog, newsletter, and exactly `/auth/register` and `/auth/login`. inventory, pricing and every other auth-service path have no route at all. The second layer is the network: a default-deny NetworkPolicy for the namespace, plus allow rules for gateway → public services and orders → inventory. You write the inventory → pricing rule. The policies select pods by the exact labels in [spec section 3](../PHASE1_TECHNICAL_SPEC.md#3-services).

Check first that your CNI actually enforces NetworkPolicy. If it doesn't, the policies apply cleanly and do nothing.

## Read first (about 60 min)

1. [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) (30 min, default deny and selectors). Policies select pods, list allowed ingress and egress peers by pod and namespace selectors, and add up (there are no deny rules, only "not allowed"). A pod becomes isolated as soon as any policy selects it. If you also restrict egress, remember to allow DNS.
2. [Gateway API HTTP routing guide](https://gateway-api.sigs.k8s.io/guides/http-routing/) (15 min). Matching on hostnames, paths and headers, and several HTTPRoutes attached to one Gateway.
3. [Envoy Gateway HTTP routing task](https://gateway.envoyproxy.io/docs/tasks/traffic/http-routing/) (15 min). The same ideas as concrete Envoy Gateway examples you can adapt.

## Learn

"No route means no way in", and Kubernetes NetworkPolicy (default deny, pod and namespace selectors). Check that your CNI enforces NetworkPolicy.

## AI generates

- HTTPRoutes for blog, newsletter, frontend and auth-service (exact paths `/auth/register` and `/auth/login` only, so nothing else on auth-service is exposed).
- A default-deny policy for the namespace.
- Allow rules for gateway → public services (including auth-service) and orders → inventory.

## Your blanks

- [ ] The NetworkPolicy that lets only inventory-service talk to pricing-service.

## Done when

- [ ] From the internet, inventory, pricing and every auth-service path except register and login are unreachable.
- [ ] From a debug pod in another namespace, they're blocked.
- [ ] orders → inventory → pricing still works.

## Notes

_Working notes, commands that helped, blanks cut for time. CNI and whether it enforces NetworkPolicy:_

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
