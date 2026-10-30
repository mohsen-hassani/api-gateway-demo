# syntax=docker/dockerfile:1
# Build context is services/:  docker build -f frontend/Dockerfile services
FROM nginxinc/nginx-unprivileged:1.27.3-alpine

ENV APP_VERSION=v1 \
    API_BASE_URL=

# The nginx image renders /etc/nginx/templates/*.template (envsubst) on start-up, then runs
# the scripts in /docker-entrypoint.d/ in order.
COPY frontend/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=0755 frontend/nginx/40-config-js.sh /docker-entrypoint.d/40-config-js.sh
COPY frontend/html /usr/share/nginx/html

EXPOSE 8080
