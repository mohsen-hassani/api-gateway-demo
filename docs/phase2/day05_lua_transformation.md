# Day 5: Request transformation, part 2 (Lua and beyond)

[← Roadmap](../ROADMAP.md) · Week one: raw Envoy in Docker Compose · [← Day 4](day04_header_transformation.md) · [Day 6 →](day06_jwt_raw_envoy.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

Some transformations can't be expressed as static header rules, for example changing a value or computing a new one. Today you add the Lua HTTP filter to the chain and write a small script that normalises a header and adds a timestamp header. You also learn to turn a filter off per route (here, the blog route), a pattern you will use again for JWT and rate limiting. Finally you read just enough about ext\_proc and Wasm to know when Lua stops being the right tool.

## Read first (about 60 min)

1. [Lua filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/lua_filter) (35 min, the script API and per-route config). The script defines `envoy_on_request(handle)` and `envoy_on_response(handle)`. The handle gives you `headers()`, `body()`, `logInfo()`, `httpCall()` and `respond()`. Per-route config can disable the filter or pick a named script. Scripts run on every worker, so keep them short and non-blocking.
2. [Lua sandbox](https://www.envoyproxy.io/docs/envoy/latest/start/sandboxes/lua) (15 min). A working Compose example of a Lua filter changing headers: a quick reference for the wiring.
3. [External processing filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_proc_filter) (10 min, intro only, to know when to reach for it). ext\_proc streams headers and bodies to an external gRPC service that can change them. Use it for heavy logic or logic in another language, at the cost of a network hop per request.

## Learn

The Lua HTTP filter (`envoy_on_request`, `envoy_on_response`), enabling or disabling filters per route, and when to reach for ext\_proc or Wasm instead (reading only).

## AI generates

A Lua filter skeleton wired into the filter chain, plus one finished example (adding a computed header).

## Your blanks

- [ ] The Lua body that normalises a header (for example, lowercases an email header).
- [ ] Add `x-request-start` with a timestamp.

## Done when

- [ ] Both headers appear in `/debug/request`.
- [ ] The filter is disabled on the blog route.

## Notes

_Working notes, commands that helped, blanks cut for time._

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
