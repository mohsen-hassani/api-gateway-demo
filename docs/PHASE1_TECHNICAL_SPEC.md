# Phase 1 Technical Spec: Demo Microservice Backend

This is the spec for Phase 1 of the [roadmap](ROADMAP.md). Give this file to the coding agent as-is. Phase 2 (the 14-day Envoy plan) builds on what is described here, so it describes both what to build and the contracts the gateway will rely on later.

## 1. Purpose and scope

Build a small, deliberately simple microservice system that will later sit behind Envoy. Apart from auth-service, which only creates user identities and issues tokens, the services contain **no** authentication checks, rate limiting or routing logic. Token verification, rate limiting and routing will all be added at the gateway in Phase 2.

**Out of scope for Phase 1:**

- Any Envoy, Envoy Gateway, Gateway API, Ingress, LoadBalancer or NetworkPolicy configuration. The gateway path map in section 4 describes how the gateway *will* route. It is there to tell the frontend which paths to call. Do not implement it.
- Databases or persistent storage. All data lives in memory.
- Auth features beyond the contract in section 6: no refresh tokens, email verification, password reset, roles or social login.

## 2. Tech choices

- Python 3.12, FastAPI, uvicorn for every service except the frontend. Pin dependency versions in each service's requirements file.
- The frontend is the one exception: plain HTML and vanilla JavaScript (no framework, no build step), served by an unprivileged nginx image listening on port 8080.
- One Docker image per service. Shared Python code lives in `services/common/` and is copied into each image (build context `services/`).
- Configuration comes from environment variables only. Every variable has a working default for Docker Compose.
- Structured JSON logging to stdout (section 7.6).
- Host prerequisites: Docker (with Compose v2), make, bash, curl and jq. Tests and key generation run inside containers, so no local Python packages are needed.

## 3. Services

| Service | Compose / Kubernetes name | Container port | Host port (Compose) | Pod labels | Exposure (Phase 2) | Purpose |
| --- | --- | --- | --- | --- | --- | --- |
| frontend | `frontend` | 8080 | 8080 | `app=frontend` | Public, served at `/` | One static page: blog, unsubscribe, orders, login and register |
| blog-service | `blog-service` | 8001 | 8001 | `app=blog` | Public, unprotected | Read blog posts |
| newsletter-service | `newsletter-service` | 8002 | 8002 | `app=newsletter` | Public, unprotected | Email unsubscribe |
| orders-service v1 | `orders-v1` | 8003 | 8003 | `app=orders, version=v1` | Public, login required | The caller's orders (stable version) |
| orders-service v2 | `orders-v2` | 8003 | 8013 | `app=orders, version=v2` | Public, login required (canary) | Same image with `APP_VERSION=v2` |
| inventory-service | `inventory-service` | 8004 | 8004 | `app=inventory` | Internal only | Stock levels, called only by orders |
| pricing-service | `pricing-service` | 8005 | 8005 | `app=pricing` | Internal only | Prices, called only by inventory |
| auth-service | `auth-service` | 8006 | 8006 | `app=auth` | Public: only `/auth/register` and `/auth/login` | Register, log in, issue JWTs. Swappable behind the auth contract |

Notes:

- The Compose service names and the Kubernetes Service names are the same, so service-to-service URLs need no per-environment changes.
- In Compose, host ports are bound to `127.0.0.1` only. They exist for `scripts/smoke.sh` and for debugging. Week one of Phase 2 adds Envoy on port 10000 as the way in.
- orders-v1 and orders-v2 use the **same image**. Only `APP_VERSION` differs. Both listen on 8003 inside their containers.
- auth-service must run as exactly one replica, because its users are held in memory.

## 4. Gateway path map (contract with the frontend)

The frontend calls only these public paths. In Phase 2 the gateway maps them to services as follows. This table is the shared reference for the frontend and every Phase 2 day.

| Public path (via gateway) | Match | Upstream | Path the service receives | Access |
| --- | --- | --- | --- | --- |
| `/` | exact | frontend | `/` | open |
| `/assets/...` | prefix | frontend | unchanged | open |
| `/blog/...` | prefix | blog-service | `/blog` stripped (`/blog/posts` → `/posts`) | open |
| `/unsubscribe` | exact | newsletter-service | unchanged | open (rate limited from Day 7) |
| `/api/orders...` | prefix | orders-v1 / orders-v2 | `/api/orders` → `/orders` | valid token (from Day 6) |
| `/auth/register` | exact | auth-service | `/register` | open |
| `/auth/login` | exact | auth-service | `/login` | open (tight rate limit from Day 7) |

All frontend files except `index.html` are served under `/assets/`. That way the gateway only needs `/` (exact) and `/assets/` (prefix) for the frontend, which leaves room for the Day 3 catch-all 404. It also keeps the frontend's `/healthz` from being exposed publicly.

## 5. Service endpoints

All request and response bodies are JSON. Error responses use the common error shape (section 7.4).

### 5.1 Shared seed data

`services/common/` defines the seed data, so services that share it always agree:

- **Catalog:** five SKUs, `SKU-001` to `SKU-005`, each with a name. pricing-service owns the prices (`amount`, `currency` `"EUR"`). inventory-service owns the stock levels. Stock levels are fixed: creating an order does **not** decrement them, so every replica and version reports the same numbers.
- **Blog posts:** five posts with integer ids 1 to 5.

### 5.2 blog-service

- `GET /posts` returns `{"posts": [...]}` with the five posts. Each post has `id`, `title`, `author`, `published_at` and `summary`.
- `GET /posts/{id}` returns one post, including its `body`. An unknown id returns 404 `post_not_found`.

### 5.3 newsletter-service

- `GET /unsubscribe?token=...` takes any non-empty token. A missing or empty token returns 422 `invalid_input`.
- `POST /unsubscribe` with `{"email": "..."}`. A malformed email returns 422 `invalid_input`.
- Both return 200 with `{"status": "unsubscribed", "message": "..."}`. Unsubscribed emails are kept in an in-memory set. Repeating the call is harmless and returns the same answer.

### 5.4 orders-service

**Caller identity.** The caller's identity is read **only** from the headers `x-user-id` and `x-user-email`. In Phase 2 the gateway sets them from the verified token's `sub` and `email` claims. If either header is missing or empty, every `/orders` endpoint returns 401 `missing_identity`. The service trusts these headers completely. Keeping forged headers out is the gateway's job (it overwrites them on Day 6 and Day 11), and that is why orders is never reachable except through the gateway.

**Endpoints:**

- `GET /orders` returns the caller's orders.
- `GET /orders/{id}` returns one of the caller's orders. If the order does not exist or belongs to someone else, it returns 404 `order_not_found`. (Day 3 rewrites `/api/v1/orders/123` to this endpoint.)
- `POST /orders` with `{"sku": "SKU-001", "quantity": 2}` creates an order and returns 201. `quantity` must be an integer from 1 to 10, otherwise the response is 422 `invalid_input`. If inventory reports the SKU as unknown, the response is 422 `unknown_sku`.

**Downstream calls.** For every order in a response, orders-service calls inventory-service `GET /stock/{sku}` and includes the result as `stock`. If inventory fails, times out or is unreachable, the whole request returns 502 `upstream_unavailable`.

**Response shape** (`GET /orders`; the single-order and create responses use the same envelope with `order` in place of `orders`):

```json
{
  "user_id": "<x-user-id as received>",
  "user_email": "<x-user-email as received>",
  "version": "v1",
  "orders": [
    {
      "id": "ord-3f9a1c2e-1",
      "sku": "SKU-002",
      "quantity": 2,
      "created_at": "2026-01-01T00:00:00Z",
      "stock": {"sku": "SKU-002", "in_stock": 42, "price": {"amount": 19.99, "currency": "EUR"}}
    }
  ]
}
```

**v2 behaviour.** When `APP_VERSION=v2`, responses carry `"version": "v2"` and an extra field, `"recommendations"`: a list of up to two catalog SKUs the caller has not ordered. v2 computes this locally, without extra downstream calls. v1 never includes the field.

**State across instances.** Each instance keeps its own in-memory orders, and orders-v1 and orders-v2 do not share state. To make canary splitting and load balancing easy to demo anyway, the first time a user id is seen the service seeds **two orders derived deterministically from the user id** (ids, SKUs, quantities and timestamps all come from a hash of the id). Every instance and version therefore shows the same starting orders, and `GET /orders/{id}` works for seeded orders on any instance. Orders created with `POST` exist only on the instance that handled the request. This is expected, and `x-instance-id` and `x-service-version` show which instance answered.

### 5.5 inventory-service

- `GET /stock/{sku}` calls pricing-service `GET /price/{sku}` and returns `{"sku": "...", "in_stock": 42, "price": {"amount": 19.99, "currency": "EUR"}}`.
- An unknown SKU returns 404 `unknown_sku`. A pricing failure, timeout or connection error returns 502 `upstream_unavailable`.

### 5.6 pricing-service

- `GET /price/{sku}` returns `{"sku": "...", "amount": 19.99, "currency": "EUR"}`. An unknown SKU returns 404 `unknown_sku`.

### 5.7 Downstream configuration

| Variable | Used by | Default |
| --- | --- | --- |
| `INVENTORY_URL` | orders-service | `http://inventory-service:8004` |
| `PRICING_URL` | inventory-service | `http://pricing-service:8005` |
| `UPSTREAM_TIMEOUT_SECONDS` | orders, inventory | `2` |

The defaults work unchanged in both Compose and Kubernetes.

## 6. auth-service and the auth contract

auth-service is the only component that knows about passwords. Keep it tiny and replaceable. The frontend, the gateway and the other services depend only on the contract below, never on how auth-service is built. Any open source auth service can take its place if it honours the same contract, either directly or through a thin adapter.

### 6.1 Endpoints (the only two it exposes)

- `POST /register` with `{"email": "...", "password": "..."}` returns 201 with `{"id": "...", "email": "..."}`.
- `POST /login` with the same JSON returns 200 with `{"access_token": "...", "token_type": "Bearer", "expires_in": 900}`. `expires_in` equals `TOKEN_TTL_SECONDS`.
- Emails are trimmed and lowercased before they are stored or compared, so `Alice@Example.com` and `alice@example.com` are the same user. The `email` in responses and tokens is the normalised form.
- Errors are always exactly `{"error": "<code>", "message": "..."}`:
  - `invalid_input` (422): a body that is not JSON, a missing field, a malformed email, a password under 8 characters, or a password over 72 bytes (bcrypt's limit).
  - `email_taken` (409).
  - `invalid_credentials` (401): the same answer for an unknown email and for a wrong password.
- Nothing else is served: no `/me`, no JWKS endpoint, no admin API, and no `/debug/request`. FastAPI's `/docs`, `/redoc` and `/openapi.json` are turned off. `/healthz` and `/readyz` exist for probes only, and the gateway never routes them. Unknown paths return 404 and wrong methods return 405, both in the error shape above.

### 6.2 Token contract

- The access token is a JWT signed with RS256. Its header carries a `kid`, which is the RFC 7638 JWK thumbprint of the public key. `make keys` computes it the same way, so the `kid` in tokens always matches the one in `jwks.json`.
- Claims:

  | Claim | Value | Configured by |
  | --- | --- | --- |
  | `iss` | issuer | `JWT_ISSUER`, default `http://auth-service` |
  | `aud` | audience | `JWT_AUDIENCE`, default `envoy-demo` |
  | `sub` | the user id | n/a |
  | `email` | the normalised email | n/a |
  | `iat` | issue time | n/a |
  | `exp` | `iat` + TTL | `TOKEN_TTL_SECONDS`, default `900` |

- The gateway reads `sub` and `email` and passes them on as `x-user-id` and `x-user-email`. Those two claims are the only identity the rest of the system ever sees.

### 6.3 Key contract

- The gateway verifies tokens with auth-service's public keys, delivered as a JWKS document out of band: a file (`keys/jwks.json`) in Docker Compose, and a ConfigMap (`auth-jwks`) in Kubernetes. auth-service does not serve the JWKS over HTTP.
- The private key is read from the file at `JWT_PRIVATE_KEY_PATH` (default `/keys/jwt-private.pem`).
- `make keys` generates a dev RSA key pair. It writes `keys/jwt-private.pem` and the matching public `keys/jwks.json`, and copies both into `k8s/base/keys/` for kustomize (section 10). Both directories are git-ignored. The target is idempotent: it never overwrites existing keys unless you run it with `FORCE=1`, because new keys invalidate every issued token and the gateway's JWKS. Generation runs inside the auth-service image, so no local Python is needed.
- If the key file is missing, the service generates a key at startup and logs a warning. Tokens signed with that key match no published JWKS, so the gateway rejects them, and they stop working after a restart anyway. This fallback exists only so the service can start. `make up` runs `make keys` first, so the fallback normally never triggers.
- Users are in memory: restarting auth-service loses every registered user. Tokens that were already issued stay valid until they expire, because the key comes from a file or Secret (the roadmap checks this on Day 11).

### 6.4 Swapping it for another auth service

A replacement must:

1. offer the two endpoints with the same request and response shapes (or sit behind a thin adapter that does),
2. issue RS256 tokens with the same claims and a `kid`, and
3. publish a JWKS the gateway can load.

Only the gateway's JWKS location changes: a local file or ConfigMap becomes a remote URL. The frontend and the other services do not change. `scripts/auth-contract-test.sh` (section 11) checks all of this against any implementation.

### 6.5 Implementation

FastAPI, in-memory users, bcrypt password hashing (the `bcrypt` package), PyJWT with `cryptography`. Of the common behaviour in section 7, auth-service has the probes, the response headers, the error shape, request ids and logging. It has no `/debug/request`, no fault injection and no `/metrics`.

## 7. Common behaviour

### 7.1 Which component gets what

| Behaviour | Python services (blog, newsletter, orders, inventory, pricing) | auth-service | frontend (nginx) |
| --- | --- | --- | --- |
| `/healthz`, `/readyz` | yes | yes | yes |
| `x-service-*` / `x-instance-id` response headers | yes | yes | yes |
| Common error shape | yes, plus `path` | yes, exactly two fields | n/a |
| `x-request-id` handling | yes | yes | n/a |
| JSON request log | yes | yes | nginx access log is fine |
| `/debug/request` | yes | **no** | no |
| Fault injection | yes | **no** | no |
| `/metrics` (optional) | yes | **no** | no |

### 7.2 Probes

- `GET /healthz` (liveness) returns 200 while the process is running.
- `GET /readyz` (readiness) returns 200 once the app has started. It does **not** check downstream services, so a failing pricing-service never takes orders out of rotation.
- Probes are never affected by fault injection and are never routed through the gateway.

### 7.3 Response headers

Every response, errors included, carries:

- `x-service-name`, for example `orders-service` (for both orders deployments) or `frontend`.
- `x-service-version`, the value of `APP_VERSION` (default `v1`).
- `x-instance-id`, the container hostname (the pod name in Kubernetes), so replicas of the same service can be told apart.
- `x-request-id` (section 7.5).

Keep the default `server` header (uvicorn, nginx). Day 4 of the roadmap strips it at the gateway, and it has to be there to be stripped. Services do not send CORS headers: the frontend and the API share one origin through the gateway.

### 7.4 Error shape

Every error response is JSON: `{"error": "<snake_case_code>", "message": "<human readable>"}`. The Python services other than auth-service also add `"path"`, the path exactly as the service received it. This helps check gateway rewrites, because even a 404 shows what arrived upstream. FastAPI's default validation errors (`{"detail": [...]}`), 404s and 405s are all converted to this shape (`invalid_input`, `not_found`, `method_not_allowed`).

Error codes used across the system: `invalid_input`, `not_found`, `method_not_allowed`, `missing_identity`, `post_not_found`, `order_not_found`, `unknown_sku`, `upstream_unavailable`, `injected_failure`, `email_taken`, `invalid_credentials`.

### 7.5 Request ids

If a request carries `x-request-id`, the service uses it. Otherwise it generates a UUID4. The id goes into the log line, is sent on every downstream call, and is returned in the `x-request-id` response header. The whole orders → inventory → pricing chain logs the same id.

### 7.6 Logging

Each service writes one JSON line to stdout per request, with `timestamp`, `level`, `service`, `version`, `instance`, `method`, `path` (as received), `status`, `duration_ms` and `request_id`. Uvicorn's own access log is turned off so requests are not logged twice. Downstream call failures are logged at `warning` with the same `request_id`.

### 7.7 `/debug/request`

`GET /debug/request`, plus **any method** on `/debug/request/{path:path}`, echoes the request back. This is the main tool for checking gateway transformations in Phase 2.

```json
{
  "service": "blog-service",
  "version": "v1",
  "instance": "<hostname>",
  "method": "GET",
  "path": "/debug/request/anything",
  "query": "a=1&b=2",
  "headers": {"host": "...", "x-request-id": "...", "x-gateway": "envoy"},
  "client": "172.18.0.5:51234"
}
```

- `path` is the raw path as received, and `query` is the raw query string.
- `headers` contains **all** request headers. Names are lowercased. A header that appears more than once is shown as a list.
- `client` is the address of the direct peer (the gateway, once it exists).

Through the gateway, `/blog/debug/request` reaches blog-service's echo endpoint (Day 2 onwards).

### 7.8 Fault injection (for Phase 2 resilience tests)

These apply to every endpoint except `/healthz`, `/readyz` and `/metrics`:

- `?delay_ms=500` waits that long before handling the request (capped at 10000).
- `?fail=503` immediately returns that status with error `injected_failure`. Only 400 to 599 are accepted; anything else is 422 `invalid_input`.
- The env var `FAIL_RATE` (0.0 to 1.0, default 0) makes that random fraction of requests return 503 `injected_failure`.
- Faults apply only to the service that receives the query parameters. They are not passed on to downstream calls.

### 7.9 Versioning

`APP_VERSION` (default `v1`) is reported in `x-service-version`, in `/debug/request`, and in the logs. Only orders-service changes its behaviour by version (section 5.4).

### 7.10 Metrics (optional)

`GET /metrics` in Prometheus format via `prometheus-fastapi-instrumentator`. It is never routed through the gateway.

## 8. Frontend

One page, plain HTML and vanilla JavaScript, served by nginx (`nginxinc/nginx-unprivileged`, pinned tag) on port 8080.

### 8.1 Files and configuration

- `index.html` at `/`. Everything else lives under `/assets/` (`app.js`, `style.css`, `config.js`), as section 4 requires. Add `<link rel="icon" href="data:,">` so the browser never requests `/favicon.ico`.
- `/assets/config.js` sets `window.APP_CONFIG = { apiBaseUrl: "..." }`. It is generated when the container starts, from the env var `API_BASE_URL`. The default is empty, which means relative URLs on the same origin. With the default, the page works unchanged behind Envoy in Compose (`http://localhost:10000`) and behind Envoy Gateway on your hostname. Set `API_BASE_URL` only if the page is served from a different origin than the API.
- nginx serves `/healthz` and `/readyz` (200) and adds the `x-service-*` / `x-instance-id` headers (`add_header ... always`, with `$hostname`).
- The page calls only the gateway paths in section 4, never a service directly.

### 8.2 Panels

- **Blog** (public): lists posts from `GET /blog/posts`. Clicking a post loads `GET /blog/posts/{id}`.
- **Newsletter** (public): an email form that sends `POST /unsubscribe` with `{"email": "..."}` and shows the confirmation message.
- **Orders** (login required): lists orders from `GET /api/orders`, has a small form (SKU dropdown for `SKU-001` to `SKU-005`, quantity) that sends `POST /api/orders`, and shows `user_id`, `user_email`, `version` and, for v2, `recommendations`.

### 8.3 Auth behaviour

- When a request returns 401, the page shows a login and register form in place of the panel that asked. A "Log in" button in the header opens the same form at any time.
- The form sends JSON to `POST /auth/register` and `POST /auth/login`. A successful register logs in automatically with the same credentials.
- After a successful login the page stores `access_token` in `sessionStorage` and retries the original request with `Authorization: Bearer <token>`. The token is attached **only** to `/api/...` requests.
- A logout button clears the token. An expired or rejected token produces a 401, and the form appears again.
- Errors from the auth endpoints show their `message` (wrong password, email taken, password too short). A 401 from `/auth/login` shows the error and does not loop back into the form.
- The page has no auth logic beyond handling 401 and attaching the token. It never decodes the JWT.

### 8.4 Gateway-originated responses

- On 429 the page shows a friendly "too many requests, try again in a moment" message.
- 401 and 429 responses produced by the gateway are often **plain text, not JSON** (for example Envoy's `Jwt is missing` or `local_rate_limited`). The page must handle any response body without crashing: parse JSON when the content type says so, otherwise show the text.
- When the gateway is not there yet (the page opened directly on port 8080), API calls fail or return 404. The panels then show "API not reachable" and still render, and the login form still opens.

### 8.5 Debug panel

A small always-visible panel shows the last request: method, URL, status, duration, all response headers (readable from JavaScript because the page and API share an origin) and the start of the body. This makes header transformations, `x-service-version`, `x-instance-id` and 429s visible live during the demo.

## 9. Repository layout

The repository root is this repo (`api-gateway-demo/`):

```
api-gateway-demo/
  docs/
    ROADMAP.md
    PHASE1_TECHNICAL_SPEC.md
    phase2/                   # one file per Phase 2 day (dayNN_*.md)
  services/
    common/                   # shared Python: logging, request ids, headers, errors, debug echo, faults, seed data
    auth/  blog/  newsletter/  orders/  inventory/  pricing/
                              # each: app/, tests/, requirements.txt, Dockerfile
    frontend/                 # index.html, assets/, nginx config, entrypoint writing assets/config.js
  docker-compose.yml          # services only, no proxy yet
  keys/                       # created by make keys, git-ignored: jwt-private.pem, jwks.json
  k8s/
    base/                     # kustomize: namespace, Deployments, ClusterIP Services, key Secret and JWKS ConfigMap generators
      keys/                   # copied by make keys, git-ignored
    overlays/dev/             # image registry and tag, any dev tweaks
  scripts/
    smoke.sh
    auth-contract-test.sh
    auth-flow.sh
    load.sh
    distribution.sh
    lib/verify_jwt.py         # used by auth-contract-test.sh, run inside the auth-service image
  Makefile
  README.md
  .gitignore                  # keys/, k8s/base/keys/, Python caches
```

Phase 2 later adds `envoy/` (week one) and gateway manifests (week two). Phase 1 creates neither.

## 10. Docker Compose and Kubernetes

### 10.1 Docker Compose

- One Compose service per row of the table in section 3, with those names and host ports (bound to `127.0.0.1`).
- `orders-v1` and `orders-v2` both run the orders image, with `APP_VERSION=v1` and `APP_VERSION=v2`.
- auth-service mounts `./keys` read-only at `/keys`.
- Every service has a Compose healthcheck on `/healthz`.

### 10.2 Kubernetes

- Namespace `envoy-demo`.
- Every component gets a Deployment (1 replica, requests 50m CPU / 64Mi, limits 200m CPU / 128Mi) and a ClusterIP Service named as in section 3. The Service port equals the container port. Every Deployment has readiness (`/readyz`) and liveness (`/healthz`) probes, and its containers run as non-root.
- Pod labels follow section 3. The Day 9 NetworkPolicies select on `app` (and `version` for orders), so keep them exact.
- orders-service has two Deployments, `orders-v1` and `orders-v2`, each with its own Service (`orders-v1` selects `app=orders,version=v1`, `orders-v2` selects `app=orders,version=v2`). There is no combined `orders` Service: the Day 13 canary HTTPRoute weights between the two.
- **Signing key and JWKS:** `k8s/base/kustomization.yaml` uses a `secretGenerator` for the Secret `auth-jwt-key` (key `jwt-private.pem`, from `keys/jwt-private.pem`) and a `configMapGenerator` for the ConfigMap `auth-jwks` (key `jwks.json`, from `keys/jwks.json`). Both read the copies that `make keys` places in `k8s/base/keys/`. Set `generatorOptions: disableNameSuffixHash: true`: the Day 11 SecurityPolicy refers to the ConfigMap by the exact name `auth-jwks`, and kustomize cannot rewrite names inside custom resources. If the pinned Envoy Gateway version expects a different data key for local JWKS, that is a one-line change to the generator on Day 11.
- auth-service mounts the Secret so the key file sits at `JWT_PRIVATE_KEY_PATH` (`/keys/jwt-private.pem`). The gateway reads the `auth-jwks` ConfigMap directly and never calls auth-service for keys.
- No Ingress, LoadBalancer, NetworkPolicy or gateway resources.
- Any service except auth-service can be scaled to several replicas. The load balancing stretch goal scales orders-v1 to 3.

### 10.3 Images

- Images are named `$(REGISTRY)/envoy-demo-<service>:$(TAG)`, for example `envoy-demo-orders` (shared by v1 and v2) and `envoy-demo-frontend`.
- `REGISTRY` and `TAG` are Makefile variables. `make k8s-apply` deploys `k8s/overlays/dev` with those images (for example through kustomize `images:`) without hand-editing manifests.

## 11. Scripts

All scripts are bash. They depend only on curl and jq (plus docker for `auth-contract-test.sh`), exit non-zero on failure, and print usage with `-h`.

| Script | Usage | Behaviour |
| --- | --- | --- |
| `smoke.sh` | `scripts/smoke.sh` | Calls every service directly on its host port: probes, one business endpoint each, the `x-service-*` headers, `/debug/request` echoing a custom header, the orders → inventory → pricing chain on both orders-v1 and orders-v2 (sending `x-user-id` / `x-user-email` itself), orders without identity headers returning 401, and the frontend serving `/` and `/assets/config.js`. |
| `auth-contract-test.sh` | `scripts/auth-contract-test.sh <base-url>` | Runs the contract checks listed in acceptance criterion 5 (section 14) against any implementation. `<base-url>` is where `/register` and `/login` live (for example `http://localhost:8006`, or `http://localhost:10000/auth` through Envoy). Env: `JWKS_FILE` (default `keys/jwks.json`) or `JWKS_URL` (for a replacement that publishes its JWKS), plus `EXPECTED_ISS` and `EXPECTED_AUD` (defaults match section 6.2). Verifies signatures with `scripts/lib/verify_jwt.py` inside the auth-service image. |
| `auth-flow.sh` | `scripts/auth-flow.sh [base-url]` | Registers a random test user (or `EMAIL` / `PASSWORD` from env), logs in, and calls the protected orders endpoint with the token. `base-url` defaults to `http://localhost:10000`. Env `AUTH_URL` defaults to `<base-url>/auth`, and `ORDERS_URL` defaults to `<base-url>/api/orders` (set it empty to skip the protected call). Progress goes to stderr and **only the token goes to stdout**, so `export TOKEN=$(scripts/auth-flow.sh)` works. |
| `load.sh` | `scripts/load.sh <url> [count=100]` | Sends `count` sequential requests and prints a count per status code. Env: `TOKEN` (sent as a bearer token), `METHOD` (default `GET`), `BODY` (JSON body, sent with `content-type: application/json`, needed for `POST /auth/login`). |
| `distribution.sh` | `scripts/distribution.sh <url> [count=100] [header=x-service-version]` | Sends `count` requests and prints a count per value of the response header, for example `x-instance-id` for load balancing. Env: `TOKEN`, as above. |

## 12. Makefile

| Target | Behaviour |
| --- | --- |
| `build` | Builds all images. |
| `push` | Pushes all images to `$(REGISTRY)` with `$(TAG)`. |
| `keys` | Generates the dev key pair and JWKS (section 6.3). Idempotent; `FORCE=1` regenerates. |
| `up` | Runs `keys`, then `docker compose up -d --build`. |
| `down` | `docker compose down`. |
| `test` | Runs every service's pytest suite inside Docker. |
| `smoke` | Runs `scripts/smoke.sh`. |
| `k8s-apply` | Applies `k8s/overlays/dev` with the configured images. Fails with a clear message if `k8s/base/keys/` is missing. |

## 13. Tests

pytest unit tests per service, using FastAPI's `TestClient` with downstream calls mocked. Cover at least:

- the endpoints and error codes in section 5,
- the common behaviour: headers, error shape, request id propagation, the debug echo, and fault injection (including that probes are exempt),
- orders: the 401 without identity, v1 vs v2 response shapes, deterministic seeding (the same user id gives the same orders in two fresh app instances), and 502 when inventory fails,
- auth: register, duplicate (409), login, wrong email and wrong password giving the same 401, password length limits, email normalisation, token claims and `kid`, verification against a generated JWKS, and the disabled `/docs`, `/redoc` and `/openapi.json`.

## 14. Acceptance criteria

1. `make up` starts every service in Docker Compose, and `scripts/smoke.sh` passes.
2. The orders → inventory → pricing call chain works in Compose and in Kubernetes, and all three services log the same `x-request-id`.
3. `/debug/request` echoes method, path, query, all headers and the client address correctly.
4. `make test` passes for every service.
5. `scripts/auth-contract-test.sh http://localhost:8006` passes. It checks: register (201), duplicate register (409), password too short (422), login (200 with the documented body), wrong password and unknown email both 401 `invalid_credentials`, the required claims with the expected `iss` and `aud`, `exp - iat == expires_in`, the header `kid` present in the JWKS, the signature verifying against `keys/jwks.json`, and `/me`, `/docs`, `/redoc`, `/openapi.json`, `/debug/request` and `/.well-known/jwks.json` all returning 404.
6. `AUTH_URL=http://localhost:8006 ORDERS_URL= scripts/auth-flow.sh` registers a user, logs in, and prints a token on stdout.
7. Calling orders-v1 (port 8003) and orders-v2 (port 8013) directly with the same `x-user-id` returns the same seeded orders. v2 additionally includes `"version": "v2"` and `recommendations`.
8. The frontend opens at http://localhost:8080 and renders its panels, the debug panel and the login and register form. Its API calls start working once the gateway routes them (from Day 2 of Phase 2).
9. `make keys && make k8s-apply` deploys everything into `envoy-demo`, all pods become ready, and the Secret `auth-jwt-key` and ConfigMap `auth-jwks` exist under exactly those names.
10. The README explains prerequisites, how to run locally and on Kubernetes, the ports, the key workflow, and the scripts.

## 15. How Phase 2 uses this (traceability)

| Spec feature | Used on |
| --- | --- |
| Gateway path map (section 4), `/assets/` layout | Day 2 (first routes), Day 3 (rewrites, catch-all 404), Day 9 (HTTPRoutes) |
| `/debug/request`, `path` in error bodies, kept `server` header | Days 3, 4, 5 and 10 (verifying transformations) |
| `GET /orders/{id}` | Day 3 (regex rewrite) |
| `x-user-id` / `x-user-email` only identity; echoed `user_id` | Day 6 and Day 11 (claim-to-header, forged-header test), Day 12 (per-user limit) |
| `/auth/register`, `/auth/login`; `keys/jwks.json`; ConfigMap `auth-jwks` | Day 6 (local JWKS file), Day 11 (local JWKS ConfigMap, restart test) |
| `auth-flow.sh`, `TOKEN` in `load.sh` / `distribution.sh` | Days 6, 7, 11, 12 and 13 |
| `METHOD` / `BODY` in `load.sh` | Day 7 and Day 12 (rate limiting `/auth/login`) |
| orders-v1 / orders-v2, deterministic seeding, `x-service-version` | Day 7 and Day 13 (canary) |
| Frontend 401 / 429 handling, plain-text tolerance, debug panel | Days 6, 7, 11, 12 and 14 (demo) |
| Internal-only inventory and pricing, ClusterIP only, exact labels | Day 9 (isolation, NetworkPolicy) |
| `x-instance-id`, scalable Deployments | Stretch: load balancing |
| `FAIL_RATE`, `?fail`, `?delay_ms` | Stretch: retries, timeouts, circuit breaking |
| JSON logs, optional `/metrics` | Stretch: observability |
