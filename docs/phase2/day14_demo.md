# Day 14: Demo day

[← Roadmap](../ROADMAP.md) · Week two: Envoy Gateway on Kubernetes · [← Day 13](day13_canary.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

No new technology today. You turn the two weeks into a demo that tells one story: a user arrives through the gateway, sees public content, is asked to log in, and then gets an identity, transformations, isolation, limits and a canary, all enforced at the gateway while the services themselves stay dumb. The AI writes a `demo.sh` that walks through each feature with pauses. You rehearse it twice, write down what you learned, and collect open questions for Babak. Use the frontend's debug panel to make headers, 401s, 429s and `x-service-version` visible live. If a stretch goal got done, add it to the end of the flow. If not, list the remaining ones as next steps.

## Read first

No new docs. Reread your Day 7 review notes ([Day 7 summary](day07_rate_limit_canary.md#summary)) and your filled blanks from week two (30 min).

## AI generates

A `demo.sh` that walks through each feature with pauses, and a one-page architecture diagram description for your slides.

## You

- [ ] Rehearse twice.
- [ ] Write a short README section, "What I learned".
- [ ] List open questions for Babak.

## Demo flow

1. Public blog and unsubscribe.
2. The frontend page.
3. Orders triggers the login and register form (the gateway's 401).
4. Register and log in, and orders loads.
5. Identity headers arriving at orders.
6. Header and path transformation via `/debug/request`.
7. Internal services unreachable from outside.
8. Rate limiting 429s.
9. The canary split shifting live.

## Notes

_Working notes, rehearsal timings, things to fix before the real demo._

## Summary

_Fill in after the demo._

- **How the demo went:**
- **Feedback from Babak:**
- **What I learned over the two weeks:**
- **Open questions / next steps:**
- **Commit / tag:**
