# syntax=docker/dockerfile:1.7

ARG BIFROST_VERSION=2.3.0
ARG BIFROST_COMMIT=9237ec06672406e437b3cb33fc793ffd0403b3ae

# Bifrost v2.3.0 declares Go 1.27.0; Xray's supplied Go findings require
# Go 1.27.2 (or 1.26.9). Stay on the upstream Go 1.27 release line.
# Xray also reads the compiler version from the binary's build info, so keep
# the toolchain pinned and verified as part of the image supply chain.
ARG GO_VERSION=1.27.2

# Keep downstream Go pins only where upstream v2.3.0 still resolves below the
# verified Xray fix:
#   mcp-go v0.43.2          CVE-2026-81092; fixed in v0.56.0
#   x/crypto v0.55.0        CVE-2026-56855/CVE-2026-78662; fixed in v0.56.0;
#                           x/net v0.60.0 requires v0.57.0
#   x/net v0.58.0           CVE-2026-78663/78669/78660/78659/97032;
#                           fixed in v0.60.0
#   go-openapi/spec v0.22.3 XRAY-1032958/1032961/1032962, fixed in v0.22.7,
#                           and XRAY-1032963 (9.3), fixed in v0.22.9
#   swag/{json,yaml}utils   XRAY-1032959/1032960 against v0.25.4, fixed in
#                           v0.27.1; v0.27.3 is required by go-openapi/spec v0.22.9
#   go-openapi/validate     XRAY-1032963 (9.3, CWE-918) and XRAY-1032962
#     v0.25.1               (5.3, CWE-400), fixed in v0.26.1
# Upstream v2.3.0 already requires x/text v0.41.0,
# go-git/v5 v5.19.2, gRPC v1.83.2, and otel/sdk v1.45.0, so those overrides
# are intentionally omitted.
# Drop a pin once upstream's own go.mod requires that version or newer.
ARG GO_CRYPTO_VERSION=v0.57.0
ARG GO_NET_VERSION=v0.60.0
ARG GO_OPENAPI_SPEC_VERSION=v0.22.9
ARG GO_OPENAPI_SWAG_VERSION=v0.27.3
ARG GO_OPENAPI_VALIDATE_VERSION=v0.26.1
# mcp-go v0.43.2 is reported by Xray as CVE-2026-81092 (6.8, CWE-346),
# fixed in v0.56.0.
ARG GO_MCP_GO_VERSION=v0.56.0

FROM alpine:3.23.5@sha256:fd791d74b68913cbb027c6546007b3f0d3bc45125f797758156952bc2d6daf40 AS source
ARG BIFROST_VERSION
ARG BIFROST_COMMIT
RUN apk upgrade --no-cache \
    && apk add --no-cache ca-certificates git \
    && git clone --depth 1 --branch "transports/v${BIFROST_VERSION}" \
       https://github.com/maximhq/bifrost.git /src \
    && test "$(git -C /src rev-parse HEAD)" = "$BIFROST_COMMIT"

FROM node:25-alpine3.23@sha256:bdf2cca6fe3dabd014ea60163eca3f0f7015fbd5c7ee1b0e9ccb4ced6eb02ef4 AS ui-builder
WORKDIR /app
RUN apk upgrade --no-cache
COPY --from=source /src/ui/package*.json ./
RUN npm ci
COPY --from=source /src/ui/ ./
RUN npm run build-enterprise

FROM golang:1.27.2-alpine3.24@sha256:f92b6ef800e499660581efdabdf25d9d817a9d124eaf900924f0504e7e27e12d AS builder
ARG GO_VERSION
WORKDIR /app
# The digest is what actually selects the image, so confirm it still carries the
# toolchain GO_VERSION names rather than trusting the tag written beside it.
RUN go version | grep -qwF "go${GO_VERSION}" \
    && apk upgrade --no-cache \
    && apk add --no-cache gcc musl-dev sqlite-dev binutils binutils-gold patch
ENV CGO_ENABLED=1 \
    GOOS=linux \
    GOWORK=off \
    GOTOOLCHAIN=local

COPY --from=source /src/transports/go.mod /src/transports/go.sum ./
RUN go mod download
COPY --from=source /src/transports/ ./
COPY --from=ui-builder /app/out ./bifrost-http/ui

# Raise the flagged modules to their fix versions, then prove the resolved
# build list matches. Upstream is pinned to an exact commit and every pin below
# is an exact version, so module resolution is reproducible: a mismatch means an
# input moved and the new graph needs re-checking, not that the check is noisy.
ARG GO_CRYPTO_VERSION
ARG GO_NET_VERSION
ARG GO_OPENAPI_SPEC_VERSION
ARG GO_OPENAPI_SWAG_VERSION
ARG GO_OPENAPI_VALIDATE_VERSION
ARG GO_MCP_GO_VERSION
RUN set -eu; \
    GOFLAGS=-mod=mod go get \
      "github.com/mark3labs/mcp-go@${GO_MCP_GO_VERSION}" \
      "github.com/mark3labs/mcp-go/mcp@${GO_MCP_GO_VERSION}" \
      "golang.org/x/crypto@${GO_CRYPTO_VERSION}" \
      "golang.org/x/net@${GO_NET_VERSION}" \
      "github.com/go-openapi/spec@${GO_OPENAPI_SPEC_VERSION}" \
      "github.com/go-openapi/swag/jsonutils@${GO_OPENAPI_SWAG_VERSION}" \
      "github.com/go-openapi/swag/yamlutils@${GO_OPENAPI_SWAG_VERSION}" \
      "github.com/go-openapi/validate@${GO_OPENAPI_VALIDATE_VERSION}"; \
    for pin in \
      "golang.org/x/crypto=${GO_CRYPTO_VERSION}" \
      "golang.org/x/net=${GO_NET_VERSION}" \
      "github.com/go-openapi/spec=${GO_OPENAPI_SPEC_VERSION}" \
      "github.com/go-openapi/swag/jsonutils=${GO_OPENAPI_SWAG_VERSION}" \
      "github.com/go-openapi/swag/yamlutils=${GO_OPENAPI_SWAG_VERSION}" \
      "github.com/go-openapi/validate=${GO_OPENAPI_VALIDATE_VERSION}" \
      "github.com/mark3labs/mcp-go=${GO_MCP_GO_VERSION}"; \
    do \
      module="${pin%=*}"; expected="${pin##*=}"; \
      resolved="$(go list -m -f '{{.Version}}' "$module")"; \
      if test "$resolved" != "$expected"; then \
        echo "unremediated: $module resolved to '$resolved', expected $expected" >&2; \
        exit 1; \
      fi; \
      echo "remediated: $module $resolved"; \
    done
# No upstream fix verified for CVE-2026-108859 as of 2026-10-15;
# v1.3.0 still buffers without a cap.
# Patch a private vendor tree; retain the real module version in build info.
COPY mcp-go-body-limit.patch mcp-go-body-limit_test.go /tmp/
RUN go mod vendor \
    && patch --batch --fuzz=0 -p1 -d vendor/github.com/mark3labs/mcp-go < /tmp/mcp-go-body-limit.patch \
    && cp /tmp/mcp-go-body-limit_test.go vendor/github.com/mark3labs/mcp-go/server/ \
    && go test -mod=vendor ./vendor/github.com/mark3labs/mcp-go/server -run '^TestXrayBodyLimit$' -count=1 -v
ARG BIFROST_VERSION
RUN go build -mod=vendor \
      -ldflags="-w -s -X main.Version=v${BIFROST_VERSION} -extldflags '-static'" \
      -a -trimpath \
      -tags "sqlite_static" \
      -o /app/main \
      ./bifrost-http \
    && test -f /app/main
# The compiler stamped into the binary is the component Xray scans, so fail here
# if the build somehow ran on a toolchain other than the pinned one.
RUN set -eu; \
    go version -m /app/main > /tmp/binary-build-info; \
    cat /tmp/binary-build-info; \
    grep -qwF "go${GO_VERSION}" /tmp/binary-build-info; \
    awk -v expected="$GO_NET_VERSION" \
      '$1 == "dep" && $2 == "golang.org/x/net" { found = ($3 == expected) } END { exit !found }' \
      /tmp/binary-build-info; \
    awk -v expected="$GO_MCP_GO_VERSION" \
      '$1 == "dep" && $2 == "github.com/mark3labs/mcp-go" { found = ($3 == expected) } END { exit !found }' \
      /tmp/binary-build-info

FROM alpine:3.23.5@sha256:fd791d74b68913cbb027c6546007b3f0d3bc45125f797758156952bc2d6daf40
ARG BIFROST_VERSION
ARG BIFROST_COMMIT
WORKDIR /app
RUN apk upgrade --no-cache \
    && apk add --no-cache musl libgcc ca-certificates zlib

COPY --from=builder /app/main .
COPY --from=source /src/transports/docker-entrypoint.sh .
COPY runtime-smoke.sh /app/runtime-smoke.sh

ENV APP_DIR=/app/data \
    APP_PORT=8080 \
    APP_HOST=0.0.0.0 \
    LOG_LEVEL=info \
    LOG_STYLE=json \
    GOGC="" \
    GOMEMLIMIT=""

RUN mkdir -p "$APP_DIR/logs" \
    && adduser -D -s /bin/sh appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:0 "$APP_DIR" \
    && { [ "$APP_DIR" = "/app" ] || chmod -R g=rwX "$APP_DIR"; } \
    && chmod +x /app/docker-entrypoint.sh
USER 1000:0

VOLUME ["${APP_DIR}"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:${APP_PORT}/health || exit 1

LABEL org.opencontainers.image.title="bifrost-mcp" \
      org.opencontainers.image.description="Bifrost AI gateway with MCP tool support, built from source" \
      org.opencontainers.image.source="https://github.com/maximhq/bifrost" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${BIFROST_VERSION}" \
      org.opencontainers.image.revision="${BIFROST_COMMIT}"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["/app/main"]
