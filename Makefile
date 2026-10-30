# Phase 1 demo backend. See README.md.
REGISTRY ?= localhost
TAG      ?= dev
FORCE    ?=

# Compose reads these for the image names (docker-compose.yml)
export REGISTRY TAG

PY_SERVICES := auth blog newsletter orders inventory pricing
SERVICES    := $(PY_SERVICES) frontend
AUTH_IMAGE  := $(REGISTRY)/envoy-demo-auth:$(TAG)

.PHONY: help build push keys up down test smoke k8s-apply

help:
	@echo "Targets: build push keys up down test smoke k8s-apply"
	@echo "Variables: REGISTRY=$(REGISTRY) TAG=$(TAG) FORCE=$(FORCE)"

build:
	docker compose build

push: build
	@for s in $(SERVICES); do \
	  echo "push $(REGISTRY)/envoy-demo-$$s:$(TAG)"; \
	  docker push $(REGISTRY)/envoy-demo-$$s:$(TAG) || exit 1; \
	done

# Generates the dev RSA key pair and JWKS inside the auth-service image, then copies them
# for kustomize. Idempotent: existing keys are kept unless FORCE=1, because new keys
# invalidate every issued token and the gateway's copy of the JWKS.
keys:
	@mkdir -p keys k8s/base/keys
	@if [ -z "$(FORCE)" ] && [ -f keys/jwt-private.pem ] && [ -f keys/jwks.json ]; then \
	  echo "keys/ already has a key pair, keeping it (FORCE=1 to regenerate)"; \
	elif [ -z "$(FORCE)" ] && { [ -f keys/jwt-private.pem ] || [ -f keys/jwks.json ]; }; then \
	  echo "keys/ has only one of jwt-private.pem and jwks.json: fix it by hand or run make keys FORCE=1" >&2; \
	  exit 1; \
	else \
	  docker build -q -f services/auth/Dockerfile -t $(AUTH_IMAGE) services >/dev/null && \
	  docker run --rm --user "$$(id -u):$$(id -g)" -v "$$PWD/keys:/keys" $(AUTH_IMAGE) python -m app.keys /keys; \
	fi
	@cp keys/jwt-private.pem keys/jwks.json k8s/base/keys/

up: keys
	docker compose up -d --build

down:
	docker compose down

# Every service's pytest suite, inside its own image (no local Python needed)
test:
	@for s in $(PY_SERVICES); do \
	  echo "== $$s"; \
	  docker build -q --target test -f services/$$s/Dockerfile -t $(REGISTRY)/envoy-demo-$$s-test:$(TAG) services >/dev/null || exit 1; \
	  docker run --rm $(REGISTRY)/envoy-demo-$$s-test:$(TAG) || exit 1; \
	done

smoke:
	scripts/smoke.sh

# Deploys k8s/overlays/dev with images $(REGISTRY)/envoy-demo-<service>:$(TAG). A throwaway
# overlay on top of the dev one sets the images, so no manifest is edited by hand.
k8s-apply:
	@if [ ! -f k8s/base/keys/jwt-private.pem ] || [ ! -f k8s/base/keys/jwks.json ]; then \
	  echo "k8s/base/keys/ is missing or incomplete: run 'make keys' first" >&2; exit 1; \
	fi
	@dir=$$(mktemp -d k8s/overlays/.apply-XXXXXX) && trap 'rm -rf "$$dir"' EXIT && \
	{ \
	  echo "resources:"; echo "  - ../dev"; echo "images:"; \
	  for s in $(SERVICES); do \
	    echo "  - name: envoy-demo-$$s"; \
	    echo "    newName: $(REGISTRY)/envoy-demo-$$s"; \
	    echo "    newTag: \"$(TAG)\""; \
	  done; \
	} > "$$dir/kustomization.yaml" && \
	kubectl apply -k "$$dir"
