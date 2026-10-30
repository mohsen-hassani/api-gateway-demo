# Day 13: Canary traffic splitting

[← Roadmap](../ROADMAP.md) · Week two: Envoy Gateway on Kubernetes · [← Day 12](day12_rate_limiting.md) · [Day 14 →](day14_demo.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

This is the last demo feature: a canary rollout of orders-v2. The orders HTTPRoute lists the `orders-v1` and `orders-v2` Services as `backendRefs` with weights. There is deliberately no combined `orders` Service ([spec section 10.2](../PHASE1_TECHNICAL_SPEC.md#102-kubernetes)). You walk through three rollout steps, 90/10, 50/50 and 0/100, and add a header rule so testers sending `x-canary: true` always reach v2. Rolling back must be a one-line weight change, which is the point to make in the demo.

The orders route already carries the Day 11 SecurityPolicy, so set `TOKEN` before running `scripts/distribution.sh` (it counts `x-service-version` by default). Every user's seeded orders are the same on v1 and v2, so the frontend stays consistent while the split changes. Only v2's `recommendations` field shows which version answered.

## Read first (about 40 min)

1. [HTTP traffic splitting task](https://gateway.envoyproxy.io/docs/tasks/traffic/http-traffic-splitting/) (20 min). Several `backendRefs` on one rule with `weight`, how weights become proportions, and a weight of 0 to drain a backend.
2. [Gateway API traffic splitting guide](https://gateway-api.sigs.k8s.io/guides/traffic-splitting/) (20 min). The canary and blue-green patterns step by step, including a separate rule with a header match so test traffic always reaches the new version.

## Learn

`backendRefs` with `weight`, header matches for test traffic, and rollout and rollback by editing weights.

## AI generates

An HTTPRoute pointing at orders-v1 and orders-v2.

## Your blanks

- [ ] The weights for three rollout steps (90/10, 50/50, 0/100).
- [ ] The `x-canary: true` rule.

## Done when

- [ ] `scripts/distribution.sh` matches each step.
- [ ] Rollback is a one-line change.

## Notes

_Working notes, commands that helped, blanks cut for time. Distribution results per step:_

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
