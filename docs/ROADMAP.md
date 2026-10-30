# Envoy API Gateway — Two-Week Learning & Build Plan

Goal: in 14 days, understand Envoy and Envoy Gateway well enough to put a small microservice system behind Envoy as the API gateway, and demo the features Babak asked for.

**Core demo features**

1. Request transformation (add, set, rename, remove headers; path rewrites)
2. Access control: public unprotected routes, login-protected routes, and internal-only services that are never reachable from outside
3. Authentication: a simple frontend page sends JSON register and login requests through the gateway to a small, swappable auth-service; after login, protected calls carry a token the gateway verifies
4. Rate limiting
5. Canary traffic splitting

**Stretch goals (only if time remains, otherwise left out of the demo)**

- Load balancing across several replicas (round robin, least request, session affinity)
- Retries with timeouts
- Circuit breaking
- Observability (metrics, access logs, tracing)

**Overall approach:** Phase 1 a coding agent builds the backend on its own. Phase 2 is 14 days: week one is raw Envoy in Docker Compose (learn the engine), week two is Envoy Gateway on the Kubernetes cluster (the real API gateway and the demo).

## Learning resources

### Week one: Envoy core

- Envoy Quick start (static and dynamic config basics): https://www.envoyproxy.io/docs/envoy/latest/start/quick-start/
- Envoy architecture overview, especially "Life of a Request": https://www.envoyproxy.io/docs/envoy/latest/intro/life\_of\_a\_request
- Envoy Sandboxes (Docker Compose examples for front proxy, Lua, JWT, rate limiting, etc.): https://www.envoyproxy.io/docs/envoy/latest/start/sandboxes/ and repo https://github.com/envoyproxy/examples
- Solo Academy, "Introduction to Envoy Proxy" hands-on lab (free): https://www.solo.io/resources/lab/solo-academy-course-introduction-to-envoy-proxy
- Curated list of articles, talks and workshops: https://github.com/calvin-puram/Knowledge-Hub-for-Envoy-Proxy
- Reference you'll keep open: the Envoy config reference for the HTTP connection manager, route configuration, jwt\_authn, local\_ratelimit and Lua filters (all under the envoyproxy.io docs "Configuration reference").

### Week two: Envoy Gateway and Gateway API

- Envoy Gateway docs home and concepts: https://gateway.envoyproxy.io/docs/
- Envoy Gateway Quickstart: https://gateway.envoyproxy.io/latest/tasks/quickstart/
- Envoy Gateway "Tasks" section (use the stable docs version, not "latest"): Traffic tasks (HTTP routing, request/response header modification, URL rewrite, traffic splitting, rate limit, retry, timeouts, circuit breaker), Security tasks (OIDC authentication, JWT authentication, CORS, external authorization), Observability tasks (proxy metrics, access logs, tracing).
- Kubernetes Gateway API docs (GatewayClass, Gateway, HTTPRoute, filters, weights): https://gateway-api.sigs.k8s.io/
- Envoy Gateway GitHub (issues and examples): https://github.com/envoyproxy/gateway

## How we work with the AI (the "blanks" convention)

- The AI writes most config, scripts and manifests, but leaves 1 to 3 deliberate blanks per day, marked with a comment like `# TODO(mohsen): ...` plus a one-line hint.
- Each day ends with a verification step: a curl command or small script whose expected output tells you whether your blank is right.
- After filling a blank, ask the AI to review your version before it shows its own answer.
- Daily prompt template for the coding agent:

> Today is Day N of my Envoy plan: \[paste the day's section\]. Generate the files for this day on top of the current repo. Leave the items under "Your blanks" as TODO(mohsen) comments with a short hint, do not fill them. Give me the verification commands and expected results. Do not modify the services in /services.

## Phase 1: Tech spec for the coding agent

The full spec lives in [PHASE1_TECHNICAL_SPEC.md](PHASE1_TECHNICAL_SPEC.md). Hand that file to the coding agent as-is.

In short: six small FastAPI services (blog, newsletter, orders deployed as v1 and v2, inventory, pricing, auth) plus a static nginx frontend, all in Docker Compose and on Kubernetes (namespace `envoy-demo`), with no gateway configuration. auth-service issues RS256 JWTs whose public keys reach the gateway out of band (`keys/jwks.json` and the `auth-jwks` ConfigMap). orders-service trusts only `x-user-id` and `x-user-email`. Every service except auth echoes requests at `/debug/request` and supports fault injection. The spec's gateway path map (section 4) is the reference for the public paths used throughout Phase 2.

## Phase 2: The 14-day plan

Each day: goal, what to learn, what the AI generates, your blanks, and how you know you're done. Week one runs in Docker Compose, adding an `envoy` service with a mounted `envoy/envoy.yaml`.

Every day opens with a **Read first** list: read those pages before touching any config. Links point to the "latest" docs; once you pin versions, switch to the matching version in the docs' version picker. If a page has moved, search its title in the docs sidebar.

From Day 3 to Day 5, orders-service itself answers 401 unless you send `x-user-id` and `x-user-email` yourself (curl `-H`). From Day 6 on, orders needs a login. `scripts/auth-flow.sh` (built in Phase 1) registers a test user, logs in and prints a token; `load.sh` and `distribution.sh` send it as a bearer token when you set the `TOKEN` environment variable. In the browser, the frontend does the same: it shows the login form as soon as orders answers 401.

### Day 1: Foundations

**Read first (about 3 hours, the only long reading day):**

1. [What is Envoy](https://www.envoyproxy.io/docs/envoy/latest/intro/what_is_envoy) (15 min)
2. [Life of a Request](https://www.envoyproxy.io/docs/envoy/latest/intro/life_of_a_request) (60 min, the most important page of the two weeks)
3. [Listeners](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/listeners/listeners) (15 min)
4. [HTTP connection management](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/http_connection_management) (20 min)
5. [Cluster manager](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/cluster_manager) (15 min)
6. [xDS and dynamic configuration](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/operations/dynamic_configuration) (15 min)
7. [Envoy Gateway concepts](https://gateway.envoyproxy.io/docs/concepts/) (20 min, for Envoy vs Envoy Gateway)

- **Learn:** Envoy architecture: downstream vs upstream, listeners, filter chains, network filters vs HTTP filters, the HTTP connection manager, routes, clusters, endpoints. Data plane vs control plane, xDS in one paragraph. Envoy vs Envoy Gateway.
- **Do:** read Quick start and Life of a Request; run the front-proxy sandbox; poke the admin interface (`/clusters`, `/config_dump`, `/stats`).
- **AI generates:** a one-page cheat sheet of the config hierarchy and 10 self-check questions.
- **Your blanks:** draw the request flow for one HTTP request through Envoy and answer the questions without notes.
- **Done when:** you can explain listener → filter chain → HCM → route → cluster → endpoint out loud.

### Day 2: First Envoy in front of the app

**Read first (about 60 min):**

1. [Quick start: static configuration](https://www.envoyproxy.io/docs/envoy/latest/start/quick-start/configuration-static) (20 min)
2. [Service discovery types](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery) (15 min, focus on STRICT\_DNS)
3. [Administration interface](https://www.envoyproxy.io/docs/envoy/latest/operations/admin) (15 min, skim `/clusters`, `/config_dump`, `/stats`)
4. [Front proxy sandbox](https://www.envoyproxy.io/docs/envoy/latest/start/sandboxes/front_proxy) (10 min, closest to what you build today)

- **Learn:** static bootstrap config, admin listener, STRICT\_DNS clusters in Compose.
- **AI generates:** Envoy added to docker-compose; `envoy.yaml` with the listener, HCM and a route for `/blog` → blog-service, plus a route for / to the frontend page.
- **Your blanks:** the route and cluster for newsletter-service.
- **Done when:** `curl localhost:10000/blog/posts` and the unsubscribe endpoint both work through Envoy, the frontend page opens at localhost:10000, and you can find both clusters in the admin `/clusters` output.

### Day 3: Routing deep dive

**Read first (about 60 min):**

1. [HTTP routing](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/http_routing) (30 min)
2. [Route components reference](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/route/v3/route_components.proto) (30 min, only VirtualHost, RouteMatch, RouteAction's `prefix_rewrite` and `regex_rewrite`, and DirectResponseAction)

- **Learn:** prefix vs path vs safe\_regex matching, route ordering, `prefix_rewrite` and `regex_rewrite`, virtual hosts by Host header, `direct_response` for a custom 404.
- **AI generates:** routes for orders (`/api/orders` → `/orders`), a host-based virtual host example, a catch-all 404 (which means narrowing the Day 2 frontend route to exact `/` plus prefix `/assets/`).
- **Your blanks:** a regex rewrite (e.g. `/api/v1/orders/123` → `/orders/123`) and the correct ordering of two overlapping routes.
- **Done when:** `/debug/request` shows the rewritten path the upstream actually received.

### Day 4: Request transformation, part 1 (headers)

**Read first (about 45 min):**

1. [HTTP header manipulation](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/headers) (20 min, the "Custom request/response headers" section)
2. [HeaderValueOption and append\_action](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/core/v3/base.proto) (10 min, just that message)
3. [Format strings / command operators](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage) (15 min, skim `%REQ()%` and `%DOWNSTREAM_REMOTE_ADDRESS%`)

- **Learn:** `request_headers_to_add` / `request_headers_to_remove`, response equivalents, `append_action`, dynamic values like `%DOWNSTREAM_REMOTE_ADDRESS%` and `%REQ(header)%`, renaming as copy plus remove.
- **AI generates:** examples adding `x-gateway: envoy`, injecting client IP, removing `x-debug` from incoming requests.
- **Your blanks:** rename `x-client-token` to `x-api-key` before forwarding; strip `server` and `x-envoy-upstream-service-time` from responses.
- **Done when:** `/debug/request` proves each change, and response headers are clean.

### Day 5: Request transformation, part 2 (Lua and beyond)

**Read first (about 60 min):**

1. [Lua filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/lua_filter) (35 min, the script API and per-route config)
2. [Lua sandbox](https://www.envoyproxy.io/docs/envoy/latest/start/sandboxes/lua) (15 min)
3. [External processing filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_proc_filter) (10 min, intro only, to know when to reach for it)

- **Learn:** the Lua HTTP filter (`envoy_on_request`, `envoy_on_response`), per-route enabling or disabling of filters, when to reach for ext\_proc or Wasm instead (read only).
- **AI generates:** a Lua filter skeleton wired into the filter chain, plus one finished example (add a computed header).
- **Your blanks:** the Lua body that normalises a header (e.g. lowercase an email header) and adds `x-request-start` with a timestamp.
- **Done when:** both headers appear in `/debug/request` and the filter is disabled on the blog route.

### Day 6: Register, login and JWT in raw Envoy

**Read first (about 75 min):**

1. [JWT authentication filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/jwt_authn_filter) (20 min)
2. [jwt\_authn config reference](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/http/jwt_authn/v3/config.proto) (25 min, JwtProvider, local and remote JWKS, RequirementRule, `claim_to_headers`)
3. [Introduction to JSON Web Tokens](https://jwt.io/introduction) (15 min, header, claims, signature, and why a JWKS lets the gateway verify tokens without a shared secret)
4. [OAuth2 filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/oauth2_filter) (15 min, concept only)

- **Learn:** the `jwt_authn` filter: providers, local JWKS (a file mounted into Envoy, since auth-service serves no JWKS endpoint) versus remote JWKS, `rules` per route, `claim_to_headers`. The flow: the frontend registers and logs in through Envoy (public routes), receives a token, then sends it as `Authorization: Bearer ...` on every call to protected routes. Read about the `oauth2` filter conceptually only.
- **AI generates:** exact-path routes and a cluster for `/auth/register` and `/auth/login` to the auth-service (the `/auth` prefix stripped), and the `jwt_authn` provider reading `keys/jwks.json` (mounted into Envoy). `scripts/auth-flow.sh` from Phase 1 now runs end to end through Envoy.
- **Your blanks:** the `rules` section so `/`, `/blog`, `/unsubscribe`, `/auth/register` and `/auth/login` stay open while `/api/orders` requires a valid token; map the `sub` and `email` claims to `x-user-id` and `x-user-email`.
- **Done when:** in the browser, opening Orders shows the login and register form (the 401), and after registering and logging in the orders panel loads. With curl, orders returns 401 without a token or with a garbage token and 200 with a valid one, and a request carrying a forged `x-user-id` header plus a valid token still comes back with the token's `user_id` in the orders response.

### Day 7: Rate limiting, canary, and week-one review

**Read first (about 60 min):**

1. [Local rate limit filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/local_rate_limit_filter) (25 min, token bucket and per-route config)
2. [Global rate limiting](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/other_features/global_rate_limiting) (15 min, concept only)
3. [Traffic shifting and splitting](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/traffic_splitting) (20 min, weighted clusters)

- **Learn:** `local_ratelimit` (token bucket, per-route), the idea of global rate limiting with an external service and Redis (read only), `weighted_clusters` and header-based route matching.
- **AI generates:** clusters for the existing orders-v1 and orders-v2 Compose services, the local rate limit filter (with a tight limit on /auth/login to slow down password guessing), weighted cluster scaffolding.
- **Your blanks:** token bucket numbers (e.g. 5 requests per 10 seconds on `/unsubscribe`), the 90/10 weights, and a route that sends `x-canary: true` straight to v2.
- **Done when:** `scripts/load.sh` shows 429s past the limit, and `scripts/distribution.sh` shows roughly 90/10.
- **Review:** write half a page in your own words on what each config block does. Commit week one as a tag.

### Day 8: Envoy Gateway on the cluster

**Read first (about 90 min):**

1. [Gateway API overview](https://gateway-api.sigs.k8s.io/concepts/api-overview/) (25 min, GatewayClass, Gateway, HTTPRoute)
2. [Envoy Gateway quickstart](https://gateway.envoyproxy.io/docs/tasks/quickstart/) (20 min)
3. [Install with Helm](https://gateway.envoyproxy.io/docs/install/install-helm/) (15 min)
4. [Customize EnvoyProxy](https://gateway.envoyproxy.io/docs/tasks/operations/customize-envoyproxy/) (15 min, resources for a small node)
5. [egctl](https://gateway.envoyproxy.io/docs/tasks/operations/egctl/) (15 min, inspecting the generated Envoy config)

- **Learn:** GatewayClass, Gateway, HTTPRoute; how Envoy Gateway translates these into xDS; `egctl` for inspecting generated config.
- **Do:** install Gateway API CRDs and Envoy Gateway via Helm (pin a stable version); run make keys, then deploy the Phase 1 app with kustomize (this includes the JWT key Secret and the JWKS ConfigMap). On the single-node cluster, expose the Envoy service via your existing load balancer setup, MetalLB, or a NodePort, with Cloudflare in front for TLS. Keep Envoy proxy resource requests small (an EnvoyProxy resource).
- **AI generates:** Helm values, GatewayClass, Gateway, an EnvoyProxy resource with small resources.
- **Your blanks:** write the HTTPRoute for blog-service yourself.
- **Done when:** blog is reachable through the gateway, and you can find your route inside `egctl config envoy-proxy route` output (or the config dump).

### Day 9: Public routes and internal-only isolation

**Read first (about 60 min):**

1. [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) (30 min, default deny and selectors)
2. [Gateway API HTTP routing guide](https://gateway-api.sigs.k8s.io/guides/http-routing/) (15 min)
3. [Envoy Gateway HTTP routing task](https://gateway.envoyproxy.io/docs/tasks/traffic/http-routing/) (15 min)

- **Learn:** "no route means no way in", Kubernetes NetworkPolicy (default deny, pod and namespace selectors). Check that your CNI enforces NetworkPolicy.
- **AI generates:** HTTPRoutes for blog, newsletter, frontend and auth-service (exact paths /auth/register and /auth/login only, so nothing else on auth-service is exposed); a default-deny policy for the namespace; allow rules for gateway → public services (including auth-service) and orders → inventory.
- **Your blanks:** the NetworkPolicy that lets only inventory-service talk to pricing-service.
- **Done when:** from the internet, inventory, pricing and every auth-service path except register and login are unreachable; from a debug pod in another namespace they're blocked; orders → inventory → pricing still works.

### Day 10: Request transformation in Envoy Gateway

**Read first (about 60 min):**

1. [HTTP request headers](https://gateway.envoyproxy.io/docs/tasks/traffic/http-request-headers/) (20 min)
2. [HTTP response headers](https://gateway.envoyproxy.io/docs/tasks/traffic/http-response-headers/) (10 min)
3. [HTTP URL rewrite](https://gateway.envoyproxy.io/docs/tasks/traffic/http-urlrewrite/) (15 min)
4. [Lua extensions](https://gateway.envoyproxy.io/docs/tasks/extensibility/lua/) (15 min, optional, only if your version supports it)

- **Learn:** HTTPRoute filters `RequestHeaderModifier`, `ResponseHeaderModifier`, `URLRewrite`; Envoy Gateway's ClientTrafficPolicy for client-IP handling behind Cloudflare; EnvoyExtensionPolicy for Lua or ext\_proc if your Envoy Gateway version supports it.
- **AI generates:** HTTPRoute filters porting Day 3 and Day 4 behaviour.
- **Your blanks:** the header rename and the path rewrite for `/api/orders`.
- **Done when:** `/debug/request` through the gateway shows the same results as week one.

### Day 11: Register, login and JWT with SecurityPolicy

**Read first (about 60 min):**

1. [JWT authentication](https://gateway.envoyproxy.io/docs/tasks/security/jwt-authentication/) (30 min, remote and local JWKS, claim-to-header)
2. [OIDC authentication](https://gateway.envoyproxy.io/docs/tasks/security/oidc/) (20 min, skim only, to contrast browser login with the token flow)
3. Your Day 6 notes and `scripts/auth-flow.sh` (10 min)

- **Learn:** SecurityPolicy `jwt`: providers, `localJWKS` (key set from the `auth-jwks` ConfigMap, the right fit because auth-service serves no JWKS) versus `remoteJWKS` (an HTTPS URI or a Backend resource, what a replacement like Keycloak would use), `claimToHeaders`, and attaching a policy to a specific route. Only the orders route gets the policy; the register and login routes carry none.
- **AI generates:** a SecurityPolicy skeleton that reads the `auth-jwks` ConfigMap, with issuer and audience matching the auth-service config. The frontend needs no change: it uses same-origin URLs by default.
- **Your blanks:** the SecurityPolicy `targetRefs` (orders only) and the claim-to-header mapping.
- **Done when:** on your hostname, the frontend loads, Orders shows the login and register form, and after registering and logging in the orders panel loads. With curl, orders returns 401 without a token and 200 with one; blog, unsubscribe, register and login stay open; orders-service sees `x-user-id` and `x-user-email` from the token; and after restarting the auth-service pod, an unexpired token still works.
- **Optional:** if time remains, run `scripts/auth-contract-test.sh` against a second implementation (a stub, or Keycloak behind a small adapter) and check that only the JWKS setting in the SecurityPolicy has to change.

### Day 12: Rate limiting with BackendTrafficPolicy

**Read first (about 60 min):**

1. [Rate limiting concepts](https://gateway.envoyproxy.io/docs/concepts/rate-limiting/) (15 min)
2. [Local rate limit task](https://gateway.envoyproxy.io/docs/tasks/traffic/local-rate-limit/) (20 min)
3. [Global rate limit task](https://gateway.envoyproxy.io/docs/tasks/traffic/global-rate-limit/) (25 min, Redis setup and client selectors)

- **Learn:** local vs global rate limiting in Envoy Gateway; global needs Redis configured in the Envoy Gateway Helm values; client selectors by source IP and by header.
- **AI generates:** Redis deployment, Helm values change, a local per-IP policy on public routes, with a tighter one on /auth/login to slow down password guessing.
- **Your blanks:** a global per-user limit on orders keyed on `x-user-id`, with your chosen numbers.
- **Done when:** load tests show 429s per IP on blog and on /auth/login, and per user on orders, while a second signed-up user is unaffected.

### Day 13: Canary traffic splitting

**Read first (about 40 min):**

1. [HTTP traffic splitting task](https://gateway.envoyproxy.io/docs/tasks/traffic/http-traffic-splitting/) (20 min)
2. [Gateway API traffic splitting guide](https://gateway-api.sigs.k8s.io/guides/traffic-splitting/) (20 min)

- **Learn:** `backendRefs` with `weight`, header matches for test traffic, rollout and rollback by editing weights.
- **AI generates:** HTTPRoute pointing at orders-v1 and orders-v2.
- **Your blanks:** the weights for three rollout steps (90/10, 50/50, 0/100) and the `x-canary: true` rule.
- **Done when:** `scripts/distribution.sh` matches each step, and rollback is a one-line change.

### Day 14: Demo day

**Read first:** no new docs. Reread your Day 7 review notes and your filled blanks from week two (30 min).

- **AI generates:** a `demo.sh` that walks through each feature with pauses, and a one-page architecture diagram description for your slides.
- **You:** rehearse twice, write a short README section "What I learned", and list open questions for Babak.
- **Demo flow:** public blog and unsubscribe → frontend page → Orders triggers the login and register form (the gateway's 401) → register, log in and orders loads → identity headers arriving at orders → header and path transformation via `/debug/request` → internal services unreachable from outside → rate limiting 429s → canary split shifting live.

## Stretch goals (pull in only if a day finishes early)

**Read first, per item:**

1. Load balancing: [Load balancing task](https://gateway.envoyproxy.io/docs/tasks/traffic/load-balancing/) and [Supported load balancers](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/load_balancers) (45 min)
2. Retries and timeouts: [Retry](https://gateway.envoyproxy.io/docs/tasks/traffic/retry/) and [HTTP timeouts](https://gateway.envoyproxy.io/docs/tasks/traffic/http-timeouts/) (40 min)
3. Circuit breaking: [Circuit breaker](https://gateway.envoyproxy.io/docs/tasks/traffic/circuit-breaker/) (25 min)
4. Observability: [Proxy metrics](https://gateway.envoyproxy.io/docs/tasks/observability/proxy-metric/) and [Proxy access logs](https://gateway.envoyproxy.io/docs/tasks/observability/proxy-accesslog/) (40 min)

- **Load balancing:** scale orders-v1 to 3 replicas and compare policies with a BackendTrafficPolicy `loadBalancer`: RoundRobin, LeastRequest (the Envoy Gateway default), Random, and ConsistentHash by header or source IP for session affinity. Watch the spread of `x-instance-id` with `scripts/distribution.sh`. This is not the same as canary: canary splits traffic between versions, load balancing spreads it across the replicas of one version. Blank for you: the policy and one affinity rule.
- **Retries with timeouts:** HTTPRoute timeouts plus BackendTrafficPolicy retries; test with `FAIL_RATE=0.3` on orders-v2 and `?delay_ms`. Blank for you: retry conditions and per-try timeout.
- **Circuit breaking:** BackendTrafficPolicy circuit breaker and passive health checks (outlier detection); test with `load.sh` under failures. Blank for you: the thresholds.
- **Observability:** Envoy proxy metrics to Prometheus, access logs in JSON, optional tracing; dashboards in your existing Grafana. Blank for you: the access log format fields.

If none of these fit, leave them out of the demo and mention them as next steps.

## Notes and risks

- Single node with 4 CPU and 8 GiB RAM: keep replicas at 1 (the load balancing stretch goal temporarily scales orders to 3), keep every container's limits small, and remove week-one Compose services from the cluster plan.
- Pin Envoy and Envoy Gateway versions on Day 1 and Day 8, and use the docs for those exact versions; field names in policies change between releases.
- If a day overruns, cut that day's blanks rather than skipping verification.

* The auth-service is demo-grade: in-memory users, no email verification, no password reset, no refresh tokens. Use throwaway passwords.

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
