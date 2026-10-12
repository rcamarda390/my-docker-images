# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS prepare
ARG VSIX_VERSION
ARG VSIX_SHA256
COPY prepare.py test-prepare.py remediate.py security-fixes.json codeburn.codeburn-*.vsix /build/
RUN python /build/test-prepare.py \
    && python /build/remediate.py \
    && python /build/prepare.py "${VSIX_VERSION}" "$(sha256sum /build/fixed.vsix | cut -d " " -f 1)" \
       /build/fixed.vsix /slim
COPY AGENT.md /slim/AGENT.md
COPY security-fixes.json /slim/metadata/security-fixes.json

FROM node:22.22.0-slim AS verify
COPY --from=prepare /slim /slim
COPY test-runtime.mjs security-fixes.json /checks/
RUN node /checks/test-runtime.mjs /slim/payload/unpacked/codeburn.codeburn-1.0.2/extension/cli

FROM scratch
ARG VSIX_VERSION
LABEL org.opencontainers.image.title="slim-docker-codeburn" \
      org.opencontainers.image.version="${VSIX_VERSION}" \
      org.opencontainers.image.source="https://github.com/rcamarda390/my-docker-images" \
      slim.payload.software="codeburn.codeburn" \
      slim.payload.path="/slim/payload" \
      slim.payload.method="downstream-security-repack" \
      slim.payload.docs="/slim/AGENT.md"
COPY --from=verify /slim /slim
