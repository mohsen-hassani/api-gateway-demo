# Day 11: Register, login and JWT with SecurityPolicy

[← Roadmap](../ROADMAP.md) · Week two: Envoy Gateway on Kubernetes · [← Day 10](day10_gateway_transformation.md) · [Day 12 →](day12_rate_limiting.md)

| | |
| --- | --- |
| **Status** | Not started |
| **Started** | – |
| **Finished** | – |

_Status values: Not started · In progress · Finished · Skipped_

## What this day is about

You rebuild Day 6 on Kubernetes. A SecurityPolicy with a `jwt` provider attaches to the orders HTTPRoute only. It verifies tokens against the public keys in the `auth-jwks` ConfigMap (`localJWKS`) and copies the `sub` and `email` claims into `x-user-id` and `x-user-email`. The register and login routes from Day 9 carry no policy. The frontend needs no change, because it uses same-origin URLs.

Two checks prove the design. Restarting the auth-service pod loses every user but not the signing key, which comes from the `auth-jwt-key` Secret, so unexpired tokens keep working. And swapping auth-service for another implementation should change only the JWKS setting in this policy ([spec section 6.4](../PHASE1_TECHNICAL_SPEC.md#64-swapping-it-for-another-auth-service)). If your pinned version expects a different ConfigMap data key for local JWKS, change it in the `configMapGenerator` ([spec section 10.2](../PHASE1_TECHNICAL_SPEC.md#102-kubernetes)).

## Read first (about 60 min)

1. [JWT authentication](https://gateway.envoyproxy.io/docs/tasks/security/jwt-authentication/) (30 min, remote and local JWKS, claim-to-header). The SecurityPolicy `jwt` section: providers with `issuer`, `audiences`, `remoteJWKS` or `localJWKS`, `claimToHeaders`, and `targetRefs` to attach the policy to a Gateway or one HTTPRoute.
2. [OIDC authentication](https://gateway.envoyproxy.io/docs/tasks/security/oidc/) (20 min, skim only, to contrast browser login with the token flow). Here the gateway itself redirects the browser to an identity provider and keeps the session in cookies, the Kubernetes counterpart of Envoy's oauth2 filter from Day 6.
3. Your Day 6 notes and `scripts/auth-flow.sh` (10 min). Today is the same flow in a new API; reread what you found tricky.

## Learn

The SecurityPolicy `jwt` section:

- providers;
- `localJWKS` (the key set from the `auth-jwks` ConfigMap, the right fit because auth-service serves no JWKS) versus `remoteJWKS` (an HTTPS URI or a Backend resource, what a replacement like Keycloak would use);
- `claimToHeaders`;
- attaching a policy to a specific route.

Only the orders route gets the policy; the register and login routes carry none.

## AI generates

A SecurityPolicy skeleton that reads the `auth-jwks` ConfigMap, with issuer and audience matching the auth-service config. The frontend needs no change: it uses same-origin URLs by default.

## Your blanks

- [ ] The SecurityPolicy `targetRefs` (orders only).
- [ ] The claim-to-header mapping.

## Done when

- [ ] On your hostname, the frontend loads, Orders shows the login and register form, and after registering and logging in the orders panel loads.
- [ ] With curl, orders returns 401 without a token and 200 with one; blog, unsubscribe, register and login stay open.
- [ ] orders-service sees `x-user-id` and `x-user-email` from the token.
- [ ] After restarting the auth-service pod, an unexpired token still works.

## Optional

- [ ] If time remains, run `scripts/auth-contract-test.sh` against a second implementation (a stub, or Keycloak behind a small adapter) and check that only the JWKS setting in the SecurityPolicy has to change.

## Notes

_Working notes, commands that helped, blanks cut for time._

## Summary

_Fill in when the day is finished (or skipped)._

- **What I built:**
- **What I learned:**
- **What tripped me up:**
- **Open questions:**
- **Commit / tag:**
