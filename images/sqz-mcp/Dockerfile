# syntax=docker/dockerfile:1.7

ARG SQZ_VERSION=1.3.0
ARG SQZ_COMMIT=d024b6b6bec152dfa7a63e2316054b1bb33a8110

FROM alpine:3.23.4@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11 AS source
ARG SQZ_VERSION
ARG SQZ_COMMIT
RUN apk add --no-cache ca-certificates git \
    && git clone --depth 1 --branch "v${SQZ_VERSION}" \
       https://github.com/ojuschugh1/sqz.git /src \
    && test "$(git -C /src rev-parse HEAD)" = "$SQZ_COMMIT"

FROM rust:1.85-alpine AS builder
WORKDIR /build
RUN apk add --no-cache musl-dev
COPY --from=source /src/ .
# Upstream's .cargo/config.toml is written for cross-compiling from a glibc host:
# it forces `-C target-feature=+crt-static` and a `x86_64-linux-musl-gcc` linker.
# On rust:*-alpine the host triple IS x86_64-unknown-linux-musl, so those settings
# apply to host build units too — forced crt-static makes proc-macros (serde_derive)
# impossible to build, and that linker does not exist in this image. Alpine's musl
# target is statically linked by default, so dropping the file loses nothing.
RUN rm -f .cargo/config.toml
# Upstream gitignores its lockfile, so pin the dependency graph ourselves.
# Regenerate with `cargo generate-lockfile` whenever SQZ_VERSION changes.
COPY Cargo.lock ./Cargo.lock
RUN cargo build --release --locked --package sqz-mcp \
    && test -f target/release/sqz-mcp \
    && mkdir -p /app \
    && cp target/release/sqz-mcp /app/sqz-mcp

FROM scratch
ARG SQZ_VERSION
ARG SQZ_COMMIT
WORKDIR /app
COPY --from=builder /app/sqz-mcp /app/sqz-mcp
COPY --from=source /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

LABEL org.opencontainers.image.title="sqz-mcp" \
      org.opencontainers.image.description="MCP server for sqz context compression, built from source" \
      org.opencontainers.image.source="https://github.com/ojuschugh1/sqz" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${SQZ_VERSION}" \
      org.opencontainers.image.revision="${SQZ_COMMIT}"

ENTRYPOINT ["/app/sqz-mcp"]
