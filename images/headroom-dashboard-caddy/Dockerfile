# syntax=docker/dockerfile:1.7

ARG CADDY_VERSION=2.11.7

FROM caddy:${CADDY_VERSION}-alpine

ARG CADDY_VERSION

COPY Caddyfile /etc/caddy/Caddyfile
COPY entrypoint.sh /usr/local/bin/headroom-dashboard-entrypoint
RUN chmod 0755 /usr/local/bin/headroom-dashboard-entrypoint

# Build-time assertions: pinned Caddy, and the Caddyfile parses.
RUN set -eux; \
    caddy version | grep -F "v${CADDY_VERSION}"; \
    HEADROOM_UPSTREAM=http://headroom-mcp:8787 HEADROOM_PROXY_TOKEN=build-test \
    DASHBOARD_ALLOW_CIDR=10.0.0.0/8 \
      caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

# Operator overrides. HEADROOM_PROXY_TOKEN has no default and is required.
ENV HEADROOM_UPSTREAM=http://headroom-mcp:8787 \
    DASHBOARD_ALLOW_CIDR=10.0.0.0/8

ENTRYPOINT ["/usr/local/bin/headroom-dashboard-entrypoint"]
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]

LABEL org.opencontainers.image.title="headroom-dashboard-caddy" \
      org.opencontainers.image.description="Caddy sidecar that adds the Headroom proxy token for browser dashboard access" \
      org.opencontainers.image.source="https://github.com/caddyserver/caddy" \
      org.opencontainers.image.version="${CADDY_VERSION}"
