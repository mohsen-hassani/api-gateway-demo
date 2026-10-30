# Day 4: Request transformation, part 1 (headers)

[← Roadmap](../ROADMAP.md) · Week one: raw Envoy in Docker Compose · [← Day 3](day03_routing.md) · [Day 5 →](day05_lua_transformation.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

This is the first half of the "request transformation" demo feature. Using only declarative route config, no code, you add, overwrite, remove and rename headers on requests and responses. Dynamic values (the client IP, other request headers) come from Envoy's format strings. `/debug/request` (through `/blog/debug/request`) shows every header the upstream received, so each change can be proven. The services deliberately keep their default `server` header so that you have something to strip ([spec section 7.3](../PHASE1_TECHNICAL_SPEC.md#73-response-headers)).

## Read first (about 45 min)

1. [HTTP header manipulation](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/headers) (20 min, the "Custom request/response headers" section). Where you can add or remove headers (weighted cluster, route, virtual host, route configuration), the order in which those levels are applied, and which headers Envoy itself adds or sanitises (`x-forwarded-for`, `x-request-id`, `x-envoy-*`).
2. [HeaderValueOption and append\_action](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/core/v3/base.proto) (10 min, just that message). A header plus how to apply it: `APPEND_IF_EXISTS_OR_ADD`, `ADD_IF_ABSENT`, `OVERWRITE_IF_EXISTS_OR_ADD` or `OVERWRITE_IF_EXISTS`, and `keep_empty_value`.
3. [Format strings / command operators](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage) (15 min, skim `%REQ()%` and `%DOWNSTREAM_REMOTE_ADDRESS%`). The substitution syntax that access logs use is also allowed in custom header values. `%REQ(x-client-token)%` copies another header's value, which is what makes a rename possible.

## Learn

`request_headers_to_add` / `request_headers_to_remove` and their response equivalents, `append_action`, dynamic values like `%DOWNSTREAM_REMOTE_ADDRESS%` and `%REQ(header)%`, and renaming as copy plus remove.

## AI generates

Examples that add `x-gateway: envoy`, inject the client IP, and remove `x-debug` from incoming requests.

## Your blanks

- [ ] Rename `x-client-token` to `x-api-key` before forwarding.
- [ ] Strip `server` and `x-envoy-upstream-service-time` from responses.

## Done when

- [ ] `/debug/request` proves each change.
- [ ] Response headers are clean.

## Notes

_Working notes, commands that helped, blanks cut for time._

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
