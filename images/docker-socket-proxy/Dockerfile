# syntax=docker/dockerfile:1.7

ARG DOCKER_SOCKET_PROXY_VERSION=0.5.0
ARG HAPROXY_VERSION=3.5-dev6
ARG HAPROXY_DIGEST=sha256:447fc45c1e65f9b67d7333c97aa72de64bc892831281e0a4cc2770b46e8016d7

FROM haproxy:${HAPROXY_VERSION}-alpine@${HAPROXY_DIGEST}

ARG DOCKER_SOCKET_PROXY_VERSION
ARG HAPROXY_VERSION
ARG HAPROXY_DIGEST

USER root

# Xray reported libssl3/libcrypto3 3.5.7-r0. Alpine v3.24 now provides the
# fixed 3.5.8-r0 packages. HAProxy 3.5-dev6 includes the upstream fix for
# CVE-2026-90678, which affects 3.5-dev1 through 3.5-dev5.
RUN set -eux; \
    apk add --no-cache --upgrade \
        "libssl3>=3.5.8-r0" \
        "libcrypto3>=3.5.8-r0"; \
    apk info -e "libssl3>=3.5.8-r0"; \
    apk info -e "libcrypto3>=3.5.8-r0"; \
    haproxy -vv | grep -F "HAProxy version ${HAPROXY_VERSION}"

COPY docker-entrypoint.sh /usr/local/bin/docker-socket-proxy-entrypoint.sh
COPY haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg.template

RUN chmod 0755 /usr/local/bin/docker-socket-proxy-entrypoint.sh \
    && touch /var/lib/haproxy/server-state

# Runtime permissions from the deployment configuration. The upstream image
# keeps harmless API sections enabled by default (PING and VERSION).
ENV CONTAINERS=1 \
    EXEC=1 \
    POST=1 \
    IMAGES=0 \
    NETWORKS=0 \
    VOLUMES=0 \
    BUILD=0 \
    COMMIT=0 \
    CONFIGS=0 \
    DISTRIBUTION=0 \
    PLUGINS=0 \
    SERVICES=0 \
    SESSION=0 \
    SWARM=0 \
    SYSTEM=0 \
    TASKS=0 \
    NODES=0 \
    INFO=0 \
    ALLOW_START=0 \
    ALLOW_STOP=0 \
    ALLOW_RESTARTS=0 \
    AUTH=0 \
    DISABLE_IPV6=0 \
    EVENTS=1 \
    GRPC=0 \
    LOG_LEVEL=info \
    PING=1 \
    SECRETS=0 \
    SOCKET_PATH=/var/run/docker.sock \
    VERSION=1

WORKDIR /var/lib/haproxy
EXPOSE 2375

LABEL org.opencontainers.image.title="docker-socket-proxy" \
      org.opencontainers.image.description="Docker socket proxy with restricted API access" \
      org.opencontainers.image.source="https://github.com/Tecnativa/docker-socket-proxy" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${DOCKER_SOCKET_PROXY_VERSION}" \
      org.opencontainers.image.revision="${HAPROXY_DIGEST}"

STOPSIGNAL SIGUSR1
ENTRYPOINT ["/usr/local/bin/docker-socket-proxy-entrypoint.sh"]
CMD ["haproxy", "-f", "/tmp/haproxy.cfg"]
