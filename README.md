# API gateway demo: backend (Phase 1)

A small microservice system that later sits behind Envoy. The services contain no authentication checks, rate limiting or routing logic (apart from auth-service, which only creates identities and issues tokens). Those arrive at the gateway in Phase 2.

- [docs/ROADMAP.md](docs/ROADMAP.md): the two-week plan
- [docs/PHASE1_TECHNICAL_SPEC.md](docs/PHASE1_TECHNICAL_SPEC.md): what this repository implements

## Prerequisites

Docker with Compose v2, make, bash, curl and jq. Tests and key generation run inside containers, so no local Python is needed. For Kubernetes you also need `kubectl` and a cluster that can see your images (kind, minikube, or a registry).

## Run locally (Docker Compose)

```bash
make up       # generates the dev keys if needed, then builds and starts everything
make smoke    # checks every service on its host port
make down
```

| Service | Host port | Container port | Notes |
| --- | --- | --- | --- |
| frontend | 8080 | 8080 | one page: blog, newsletter, orders, login |
| blog-service | 8001 | 8001 | public |
| newsletter-service | 8002 | 8002 | public |
| orders-v1 | 8003 | 8003 | `APP_VERSION=v1` |
| orders-v2 | 8013 | 8003 | same image, `APP_VERSION=v2` |
| inventory-service | 8004 | 8004 | internal, called by orders |
| pricing-service | 8005 | 8005 | internal, called by inventory |
| auth-service | 8006 | 8006 | `/register` and `/login` only |

Host ports are bound to `127.0.0.1`. They are for the scripts and for debugging. Open http://localhost:8080 to see the page. Its API calls only start working once the gateway routes them (Phase 2, Day 2 onwards); until then the panels say "API not reachable" and the login form still opens.

The call chain is orders → inventory → pricing, and all three log the same `x-request-id`:

```bash
curl -s -H 'x-user-id: alice' -H 'x-user-email: alice@example.com' localhost:8003/orders | jq
curl -s localhost:8001/debug/request/anything?a=1 | jq     # echoes what the service received
curl -s 'localhost:8001/posts?delay_ms=500'                # fault injection: ?delay_ms=, ?fail=503, FAIL_RATE
```

## Keys

auth-service signs RS256 tokens with a private key; the gateway verifies them with the public key from a JWKS document delivered out of band (auth-service never serves it).

```bash
make keys             # writes keys/jwt-private.pem and keys/jwks.json, copies both to k8s/base/keys/
make keys FORCE=1     # regenerate: invalidates every issued token and the gateway's JWKS
```

`make keys` is idempotent and runs inside the auth-service image. `keys/` and `k8s/base/keys/` are git-ignored. `make up` runs it for you. Compose mounts `./keys` into auth-service; Kubernetes gets the Secret `auth-jwt-key` and the ConfigMap `auth-jwks` from kustomize generators.

Users are in memory, so restarting auth-service forgets them. Tokens already issued stay valid until they expire.

## Kubernetes

```bash
make keys
make build push REGISTRY=registry.example.com/me TAG=dev      # or load the images into kind/minikube
make k8s-apply REGISTRY=registry.example.com/me TAG=dev
kubectl -n envoy-demo get pods
```

Everything goes into the namespace `envoy-demo`: one Deployment and one ClusterIP Service per component (`orders-v1` and `orders-v2` each have their own), no Ingress or LoadBalancer. `REGISTRY` and `TAG` default to `localhost` and `dev`. `make k8s-apply` applies `k8s/overlays/dev` with images `$(REGISTRY)/envoy-demo-<service>:$(TAG)`; it stops with a message if `k8s/base/keys/` is missing. Run auth-service as exactly one replica.

## Scripts

| Script | What it does |
| --- | --- |
| `scripts/smoke.sh` | Direct checks of every service on its host port (`make smoke`) |
| `scripts/auth-contract-test.sh <base-url>` | Checks any auth implementation against the contract, for example `scripts/auth-contract-test.sh http://localhost:8006` |
| `scripts/auth-flow.sh [base-url]` | Registers a user, logs in, calls the protected orders endpoint, prints only the token: `export TOKEN=$(scripts/auth-flow.sh)`. Without a gateway: `AUTH_URL=http://localhost:8006 ORDERS_URL= scripts/auth-flow.sh` |
| `scripts/load.sh <url> [count]` | Sequential requests, a count per status code. Env `TOKEN`, `METHOD`, `BODY` |
| `scripts/distribution.sh <url> [count] [header]` | A count per value of a response header (default `x-service-version`; try `x-instance-id`). Env `TOKEN` |

All of them print usage with `-h`.

## Tests

```bash
make test     # pytest for every Python service, each inside its own image
```

Shared behaviour (headers, error shape, request ids, debug echo, fault injection) is tested once in `services/common/testing.py` and run by every service's suite.

## Layout

```
services/common/    shared Python: logging, request ids, headers, errors, debug echo, faults, seed data
services/<name>/    app/, tests/, requirements.txt, Dockerfile   (auth, blog, newsletter, orders, inventory, pricing)
services/frontend/  index.html, assets/, nginx config, entrypoint that writes assets/config.js
docker-compose.yml  services only, no proxy yet
k8s/base/           kustomize: namespace, Deployments, Services, key Secret and JWKS ConfigMap
k8s/overlays/dev/   dev tweaks; images are set by make k8s-apply
scripts/            smoke, auth contract test, auth flow, load, distribution
```

## Configuration

Environment variables only; every one has a working default.

| Variable | Used by | Default |
| --- | --- | --- |
| `APP_VERSION` | all | `v1` |
| `FAIL_RATE` | Python services except auth | `0` |
| `INVENTORY_URL` | orders | `http://inventory-service:8004` |
| `PRICING_URL` | inventory | `http://pricing-service:8005` |
| `UPSTREAM_TIMEOUT_SECONDS` | orders, inventory | `2` |
| `JWT_ISSUER` / `JWT_AUDIENCE` | auth | `http://auth-service` / `envoy-demo` |
| `TOKEN_TTL_SECONDS` | auth | `900` |
| `JWT_PRIVATE_KEY_PATH` | auth | `/keys/jwt-private.pem` |
| `API_BASE_URL` | frontend | empty (same origin) |
