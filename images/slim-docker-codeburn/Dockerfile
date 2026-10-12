# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS prepare
ARG VSIX_VERSION
ARG VSIX_SHA256
COPY prepare.py test-prepare.py codeburn.codeburn-*.vsix /build/
RUN python /build/test-prepare.py \
    && python /build/prepare.py "${VSIX_VERSION}" "${VSIX_SHA256}" \
       "/build/codeburn.codeburn-${VSIX_VERSION}.vsix" /slim
COPY AGENT.md /slim/AGENT.md

FROM scratch
ARG VSIX_VERSION
LABEL org.opencontainers.image.title="slim-docker-codeburn" \
      org.opencontainers.image.version="${VSIX_VERSION}" \
      org.opencontainers.image.source="https://github.com/rcamarda390/my-docker-images" \
      slim.payload.software="codeburn.codeburn" \
      slim.payload.path="/slim/payload" \
      slim.payload.method="official-marketplace-vsix" \
      slim.payload.docs="/slim/AGENT.md"
COPY --from=prepare /slim /slim
