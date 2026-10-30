# Envoy API Gateway: Two-Week Learning & Build Plan

Goal: in 14 days, understand Envoy and Envoy Gateway well enough to put a small microservice system behind Envoy as the API gateway, and demo the features Babak asked for.

**Overall approach:** in Phase 1, a coding agent builds the backend on its own. Phase 2 takes 14 days: week one is raw Envoy in Docker Compose (learn the engine), and week two is Envoy Gateway on the Kubernetes cluster (the real API gateway and the demo).

## Core demo features

1. Request transformation (add, set, rename and remove headers; path rewrites)
2. Access control: public unprotected routes, login-protected routes, and internal-only services that are never reachable from outside
3. Authentication: a simple frontend page sends JSON register and login requests through the gateway to a small, swappable auth-service. After login, protected calls carry a token that the gateway verifies
4. Rate limiting
5. Canary traffic splitting

## Stretch goals

Only if time remains: pull one in when a day finishes early. Otherwise leave them out of the demo and mention them as next steps.

| Stretch goal | Read first | What to do | Your blank |
| --- | --- | --- | --- |
| Load balancing across several replicas | [Load balancing task](https://gateway.envoyproxy.io/docs/tasks/traffic/load-balancing/) and [Supported load balancers](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/load_balancers) (45 min) | Scale orders-v1 to 3 replicas and compare policies with a BackendTrafficPolicy `loadBalancer`: RoundRobin, LeastRequest (the Envoy Gateway default), Random, and ConsistentHash by header or source IP for session affinity. Watch the spread of `x-instance-id` with `scripts/distribution.sh`. This is not the same as canary: canary splits traffic between versions, while load balancing spreads it across the replicas of one version. | The policy and one affinity rule |
| Retries with timeouts | [Retry](https://gateway.envoyproxy.io/docs/tasks/traffic/retry/) and [HTTP timeouts](https://gateway.envoyproxy.io/docs/tasks/traffic/http-timeouts/) (40 min) | HTTPRoute timeouts plus BackendTrafficPolicy retries. Test with `FAIL_RATE=0.3` on orders-v2 and with `?delay_ms`. | Retry conditions and per-try timeout |
| Circuit breaking | [Circuit breaker](https://gateway.envoyproxy.io/docs/tasks/traffic/circuit-breaker/) (25 min) | BackendTrafficPolicy circuit breaker and passive health checks (outlier detection). Test with `load.sh` under failures. | The thresholds |
| Observability (metrics, access logs, tracing) | [Proxy metrics](https://gateway.envoyproxy.io/docs/tasks/observability/proxy-metric/) and [Proxy access logs](https://gateway.envoyproxy.io/docs/tasks/observability/proxy-accesslog/) (40 min) | Envoy proxy metrics to Prometheus, access logs in JSON, optional tracing, and dashboards in your existing Grafana. | The access log format fields |

The backend already supports all four: `x-instance-id` and scalable Deployments, fault injection (`FAIL_RATE`, `?fail`, `?delay_ms`), and JSON logs ([spec section 7](PHASE1_TECHNICAL_SPEC.md#7-common-behaviour)).

## Learning resources

### Week one: Envoy core

- Envoy Quick start (static and dynamic config basics): https://www.envoyproxy.io/docs/envoy/latest/start/quick-start/
- Envoy architecture overview, especially "Life of a Request": https://www.envoyproxy.io/docs/envoy/latest/intro/life_of_a_request
- Envoy Sandboxes (Docker Compose examples for front proxy, Lua, JWT, rate limiting, and more): https://www.envoyproxy.io/docs/envoy/latest/start/sandboxes/ and the repo https://github.com/envoyproxy/examples
- Solo Academy, "Introduction to Envoy Proxy" hands-on lab (free): https://www.solo.io/resources/lab/solo-academy-course-introduction-to-envoy-proxy
- Curated list of articles, talks and workshops: https://github.com/calvin-puram/Knowledge-Hub-for-Envoy-Proxy
- Reference to keep open: the Envoy config reference for the HTTP connection manager, route configuration, and the jwt\_authn, local\_ratelimit and Lua filters (all under "Configuration reference" in the envoyproxy.io docs).

### Week two: Envoy Gateway and Gateway API

- Envoy Gateway docs home and concepts: https://gateway.envoyproxy.io/docs/
- Envoy Gateway Quickstart: https://gateway.envoyproxy.io/latest/tasks/quickstart/
- The Envoy Gateway "Tasks" section (use the stable docs version, not "latest"):
  - Traffic tasks: HTTP routing, request/response header modification, URL rewrite, traffic splitting, rate limit, retry, timeouts, circuit breaker.
  - Security tasks: OIDC authentication, JWT authentication, CORS, external authorization.
  - Observability tasks: proxy metrics, access logs, tracing.
- Kubernetes Gateway API docs (GatewayClass, Gateway, HTTPRoute, filters, weights): https://gateway-api.sigs.k8s.io/
- Envoy Gateway GitHub (issues and examples): https://github.com/envoyproxy/gateway

## How we work with the AI (the "blanks" convention)

- The AI writes most of the config, scripts and manifests, but leaves 1 to 3 deliberate blanks per day. Each is marked with a comment like `# TODO(mohsen): ...` plus a one-line hint.
- Each day ends with a verification step: a curl command or small script whose expected output tells you whether your blank is right.
- After filling a blank, ask the AI to review your version before it shows its own answer.
- Daily prompt template for the coding agent:

> Today is Day N of my Envoy plan: \[paste the day file from "What this day is about" through "Done when"\]. Generate the files for this day on top of the current repo. Leave the items under "Your blanks" as TODO(mohsen) comments with a short hint, do not fill them. Give me the verification commands and expected results. Do not modify the services in /services.

## The plan files

| File | What it holds |
| --- | --- |
| `docs/ROADMAP.md` (this file) | Goals, features, stretch goals, resources, the working convention, risks and courses. |
| [`docs/PHASE1_TECHNICAL_SPEC.md`](PHASE1_TECHNICAL_SPEC.md) | The Phase 1 spec, handed to the coding agent as-is. |
| `docs/phase2/dayNN_*.md` | One file per day of Phase 2, listed below. |

### Phase 1: the backend

Six small FastAPI services (blog, newsletter, orders deployed as v1 and v2, inventory, pricing, auth) plus a static nginx frontend. They run in Docker Compose and on Kubernetes (namespace `envoy-demo`), with no gateway configuration. auth-service issues RS256 JWTs, and its public keys reach the gateway out of band (`keys/jwks.json` and the `auth-jwks` ConfigMap). orders-service trusts only `x-user-id` and `x-user-email`. Every service except auth echoes requests at `/debug/request` and supports fault injection. The spec's [gateway path map](PHASE1_TECHNICAL_SPEC.md#4-gateway-path-map-contract-with-the-frontend) is the reference for the public paths used throughout Phase 2.

### Phase 2: the 14 days

Every day file has the same shape:

- a **status** block (Not started, In progress, Finished or Skipped, plus dates),
- **What this day is about**,
- **Read first**, with a short brief of each reading. Read these before touching any config. Links point to the "latest" docs; once you pin versions, switch to the matching version in the docs' version picker. If a page has moved, search for its title in the docs sidebar,
- **Learn**, **AI generates**, **Your blanks** and **Done when**,
- a **Notes** section for while you work and a **Summary** to fill in once the day is finished.

The status in each day file is the single source of truth for progress.

Week one runs in Docker Compose, adding an `envoy` service with a mounted `envoy/envoy.yaml`. Week two runs Envoy Gateway on the single-node Kubernetes cluster.

**Logging in:** from Day 3 to Day 5, orders-service itself answers 401 unless you send `x-user-id` and `x-user-email` yourself (curl `-H`). From Day 6 on, orders needs a login. `scripts/auth-flow.sh` (built in Phase 1) registers a test user, logs in and prints a token. `load.sh` and `distribution.sh` send it as a bearer token when you set the `TOKEN` environment variable. In the browser the frontend does the same: it shows the login form as soon as orders answers 401.

| Day | File | Focus |
| --- | --- | --- |
| **Week one: raw Envoy in Docker Compose** | | |
| 1 | [day01_foundations.md](phase2/day01_foundations.md) | Envoy architecture: listener → filter chain → HCM → route → cluster → endpoint |
| 2 | [day02_first_envoy.md](phase2/day02_first_envoy.md) | Static config, first routes to blog, newsletter and the frontend |
| 3 | [day03_routing.md](phase2/day03_routing.md) | Matching, ordering, prefix and regex rewrites, virtual hosts, catch-all 404 |
| 4 | [day04_header_transformation.md](phase2/day04_header_transformation.md) | Adding, removing and renaming request and response headers |
| 5 | [day05_lua_transformation.md](phase2/day05_lua_transformation.md) | The Lua filter and per-route filter config |
| 6 | [day06_jwt_raw_envoy.md](phase2/day06_jwt_raw_envoy.md) | Register, login and JWT verification with `jwt_authn` |
| 7 | [day07_rate_limit_canary.md](phase2/day07_rate_limit_canary.md) | Local rate limiting, weighted canary, week-one review |
| **Week two: Envoy Gateway on Kubernetes** | | |
| 8 | [day08_envoy_gateway.md](phase2/day08_envoy_gateway.md) | Install Envoy Gateway, deploy the app, first HTTPRoute |
| 9 | [day09_internal_isolation.md](phase2/day09_internal_isolation.md) | Public routes, internal-only services, NetworkPolicy |
| 10 | [day10_gateway_transformation.md](phase2/day10_gateway_transformation.md) | Header and path transformation with HTTPRoute filters |
| 11 | [day11_jwt_security_policy.md](phase2/day11_jwt_security_policy.md) | JWT with SecurityPolicy |
| 12 | [day12_rate_limiting.md](phase2/day12_rate_limiting.md) | Local and global rate limiting with BackendTrafficPolicy |
| 13 | [day13_canary.md](phase2/day13_canary.md) | Weighted canary rollout and rollback |
| 14 | [day14_demo.md](phase2/day14_demo.md) | Demo script, rehearsal, wrap-up |

## Notes and risks

- The cluster is a single node with 4 CPU and 8 GiB RAM. Keep replicas at 1 (the load balancing stretch goal temporarily scales orders to 3), keep every container's limits small, and leave the week-one Compose setup out of the cluster plan.
- Pin the Envoy and Envoy Gateway versions on Day 1 and Day 8, and use the docs for those exact versions. Field names in policies change between releases.
- If a day overruns, cut that day's blanks rather than skipping verification. Mark cut items in the day's notes.
- The auth-service is demo-grade: in-memory users, no email verification, no password reset, no refresh tokens. Use throwaway passwords.

## Video courses and tutorials

These are optional extras to use alongside the daily reading. Most are free, and they're listed in the order they fit the plan.

| Resource | Type | Cost | Best for |
| --- | --- | --- | --- |
| [Tetrate Academy: Envoy Fundamentals](https://academy.tetrate.io/courses/envoy-fundamentals) | 8-part course with labs and quizzes | Free | Week one |
| [Tetrate Academy: Envoy Gateway Fundamentals](https://academy.tetrate.io/courses/envoy-gateway-fundamentals) | Course | Free | Week two |
| [Hussein Nasser: Envoy Proxy Crash Course](https://www.youtube.com/watch?v=40gKzHQWgP0) | YouTube video | Free | Architecture and proxying concepts (older, so some config syntax may be dated) |
| [Hussein Nasser: Envoy, Edge and Service Proxy](https://www.udemy.com/course/envoy-edge-and-service-proxy-course/) | Udemy course | Paid | Going deeper, if you like his style |
| [Solo Academy: API Gateway Basics](https://www.solo.io/resources/lab/solo-academy-course-api-gateway-basics) | Video-led course | Free | General API gateway concepts in Kubernetes |
| [Marcel Dempers: Introduction to Envoy Gateway API for Kubernetes beginners](https://www.youtube.com/watch?v=me_5W_Q4ZWg) | YouTube video | Free | The evening before Day 8 |
| [CNCF talk: Envoy Gateway, the API Gateway in the Cloud Native Era](https://www.classcentral.com/course/youtube-envoy-gateway-the-api-gateway-in-the-cloud-native-era-xunzhuo-liu-tencent-huabing-zhao-261648) | Conference talk by the maintainers | Free | Why Envoy Gateway exists |

freeCodeCamp and Coursera have no Envoy or API gateway course worth your time. Their API courses are beginner-level.
