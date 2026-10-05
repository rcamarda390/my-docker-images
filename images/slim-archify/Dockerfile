# syntax=docker/dockerfile:1.7

# Slim payload image: carries archify + the Node binary it needs, nothing else.
# Not runnable (FROM scratch). It exists so Artifactory/Xray scans exactly the
# bytes that a consuming image later copies in. See docs/SLIM_IMAGES.md.
#
# archify is plain Node ESM using only node:* builtins at runtime (its npm
# dependencies are devDependencies), so COPY is the install.
ARG WOLFI_IMAGE=cgr.dev/chainguard/wolfi-base@sha256:65e1acb87a2bf356b92c5f70f3980f03b4bb51dfd483c834e01557525f15c1d9
# Official Node image (nodejs.org release tarball on Debian). Same pin as
# images/ai-cli-runner so the Node binary is already a known quantity.
ARG NODE_IMAGE=node:24-trixie-slim@sha256:8ec5d7557396cfe32d21c3f9c13072355ceab22b584578ca4bb28af31120cffe

FROM ${WOLFI_IMAGE} AS source
ARG ARCHIFY_VERSION
ARG ARCHIFY_COMMIT
RUN apk upgrade --no-cache \
    && apk add --no-cache ca-certificates-bundle git \
    && git clone --branch "v${ARCHIFY_VERSION}" https://github.com/tt-a1i/archify.git /src \
    && test "$(git -C /src rev-parse HEAD)" = "$ARCHIFY_COMMIT" \
    && mkdir -p /slim/payload \
    && cp -a /src/archify /slim/payload/archify \
    && cp /src/LICENSE /slim/payload/archify/LICENSE.repo \
    && rm -rf /slim/payload/archify/test

FROM ${NODE_IMAGE} AS verify
ARG ARCHIFY_VERSION
ARG NODE_MAJOR
COPY --from=source /slim /slim
COPY AGENT.md /slim/AGENT.md
# Node: binary + licence only. npm/corepack are not needed and only add scan surface.
RUN mkdir -p /slim/payload/node/bin \
    && cp /usr/local/bin/node /slim/payload/node/bin/node \
    && cp /usr/local/LICENSE /slim/payload/node/LICENSE
# Falsifiable checks, all against the PAYLOAD copy with no npm install:
#  - node major matches image.yaml
#  - archify's own doctor passes and the demo renders
#  - archify version matches image.yaml
#  - no node_modules shipped (proves copy-only claim)
RUN set -eu; \
    N=/slim/payload/node/bin/node; A=/slim/payload/archify; \
    NODE_VERSION="$($N --version)"; \
    test "${NODE_VERSION%%.*}" = "v${NODE_MAJOR}"; \
    test ! -e "$A/node_modules"; \
    test "$($N -p "require('$A/package.json').version")" = "$ARCHIFY_VERSION"; \
    $N "$A/bin/archify.mjs" doctor; \
    $N "$A/bin/archify.mjs" demo /tmp/demo; \
    test -s /tmp/demo/archify-demo.html; \
    NEEDS="$(ldd $N | awk '/=>/ {print $1}' | sort -u | sed 's/.*/"&"/' | paste -sd,)"; \
    printf '{\n  "software": "archify",\n  "version": "%s",\n  "method": "copy",\n  "install_step": "none",\n  "payload": "/slim/payload",\n  "node": {"version": "%s", "path": "payload/node/bin/node", "needs": [%s]}\n}\n' \
      "$ARCHIFY_VERSION" "$NODE_VERSION" "$NEEDS" > /slim/manifest.json; \
    cat /slim/manifest.json

FROM scratch
ARG ARCHIFY_VERSION
LABEL org.opencontainers.image.title="slim-archify" \
      org.opencontainers.image.version="${ARCHIFY_VERSION}" \
      org.opencontainers.image.source="https://github.com/tt-a1i/archify" \
      org.opencontainers.image.licenses="MIT" \
      slim.payload.software="archify" \
      slim.payload.version="${ARCHIFY_VERSION}" \
      slim.payload.path="/slim/payload" \
      slim.payload.method="copy" \
      slim.payload.docs="/slim/AGENT.md"
COPY --from=verify /slim /slim
