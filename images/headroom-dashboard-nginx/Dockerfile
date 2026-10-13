# syntax=docker/dockerfile:1.7

ARG NGINX_VERSION=1.30.5
ARG NGINX_DIGEST=sha256:56b8272e43a0525f67aed68d1e0794a712d10e3e45a563e118e9a77c817e6f86

FROM nginxinc/nginx-unprivileged:${NGINX_VERSION}-alpine@${NGINX_DIGEST}

ARG NGINX_VERSION

USER root

COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY 15-require-token.sh /docker-entrypoint.d/15-require-token.sh
RUN chmod 0755 /docker-entrypoint.d/15-require-token.sh

# Build-time assertions: pinned nginx, and the rendered config parses.
RUN set -eux; \
    nginx -v 2>&1 | grep -F "nginx/${NGINX_VERSION}"; \
    HEADROOM_UPSTREAM=http://headroom-mcp:8787 HEADROOM_PROXY_TOKEN=build-test \
    DASHBOARD_ALLOW_CIDR=10.0.0.0/8 DNS_RESOLVER=127.0.0.11 \
      envsubst '${DNS_RESOLVER} ${HEADROOM_UPSTREAM} ${DASHBOARD_ALLOW_CIDR} ${HEADROOM_PROXY_TOKEN}' \
      < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf; \
    nginx -t; \
    rm -f /etc/nginx/conf.d/default.conf

# Operator overrides. HEADROOM_PROXY_TOKEN has no default and is required.
ENV HEADROOM_UPSTREAM=http://headroom-mcp:8787 \
    DASHBOARD_ALLOW_CIDR=10.0.0.0/8 \
    DNS_RESOLVER=127.0.0.11

USER 101

LABEL org.opencontainers.image.title="headroom-dashboard-nginx" \
      org.opencontainers.image.description="nginx sidecar that adds the Headroom proxy token for browser dashboard access" \
      org.opencontainers.image.source="https://github.com/nginx/docker-nginx-unprivileged" \
      org.opencontainers.image.version="${NGINX_VERSION}"
