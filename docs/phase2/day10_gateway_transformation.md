# Day 10: Request transformation in Envoy Gateway

[← Roadmap](../ROADMAP.md) · Week two: Envoy Gateway on Kubernetes · [← Day 9](day09_internal_isolation.md) · [Day 11 →](day11_jwt_security_policy.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

You port the Day 3 and Day 4 transformations to Envoy Gateway, and the goal is identical results in `/debug/request`. Most of it maps directly onto HTTPRoute filters: `RequestHeaderModifier`, `ResponseHeaderModifier` and `URLRewrite`. Behind Cloudflare, the client IP also needs ClientTrafficPolicy, otherwise every request appears to come from Cloudflare.

Watch for two gaps. First, `RequestHeaderModifier` sets only fixed values, so a rename that keeps the original value (Day 4's `x-client-token` → `x-api-key`) needs Lua through EnvoyExtensionPolicy, or whatever your pinned version offers. Second, the standard `URLRewrite` has no regex option, so check whether your Envoy Gateway version has its own extension for Day 3's regex rewrite. Write down what you find; it is a good demo talking point about raw Envoy vs a higher-level API.

## Read first (about 60 min)

1. [HTTP request headers](https://gateway.envoyproxy.io/docs/tasks/traffic/http-request-headers/) (20 min). `RequestHeaderModifier` with `add` (appends), `set` (overwrites) and `remove`, attached to a route rule.
2. [HTTP response headers](https://gateway.envoyproxy.io/docs/tasks/traffic/http-response-headers/) (10 min). The same operations on responses with `ResponseHeaderModifier`. This is where you strip `server`.
3. [HTTP URL rewrite](https://gateway.envoyproxy.io/docs/tasks/traffic/http-urlrewrite/) (15 min). `URLRewrite` with `ReplacePrefixMatch` or `ReplaceFullPath`, plus hostname rewrites, and any regex extension your version documents.
4. [Lua extensions](https://gateway.envoyproxy.io/docs/tasks/extensibility/lua/) (15 min, optional, only if your version supports it). EnvoyExtensionPolicy attaches a Lua script (inline or from a ConfigMap) to a route or Gateway: your Day 5 script, moved to Kubernetes.

## Learn

The HTTPRoute filters `RequestHeaderModifier`, `ResponseHeaderModifier` and `URLRewrite`; Envoy Gateway's ClientTrafficPolicy for client-IP handling behind Cloudflare; EnvoyExtensionPolicy for Lua or ext\_proc, if your Envoy Gateway version supports it.

## AI generates

HTTPRoute filters that port the Day 3 and Day 4 behaviour.

## Your blanks

- [ ] The header rename.
- [ ] The path rewrite for `/api/orders`.

## Done when

- [ ] `/debug/request` through the gateway shows the same results as week one.

## Notes

_Working notes, commands that helped, blanks cut for time. What couldn't be expressed with standard HTTPRoute filters, and how you solved it:_

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
