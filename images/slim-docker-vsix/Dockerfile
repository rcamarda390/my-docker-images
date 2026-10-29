# syntax=docker/dockerfile:1.7
# File: images/slim-docker-vsix/Dockerfile
# Single official Marketplace VSIX, preserved byte-for-byte, for Xray scanning.
FROM python:3.12-slim AS prepare
ARG VSIX_VERSION
ARG VSIX_SHA256
COPY prepare-vsix.py test-prepare-vsix.py /
RUN python /test-prepare-vsix.py \
    && python /prepare-vsix.py ms-mssql mssql "${VSIX_VERSION}" "${VSIX_SHA256}" /slim
COPY AGENT.md /slim/AGENT.md

FROM scratch
ARG VSIX_VERSION
LABEL org.opencontainers.image.title="slim-docker-vsix" \
      org.opencontainers.image.version="${VSIX_VERSION}" \
      org.opencontainers.image.source="https://github.com/rcamarda390/my-docker-images" \
      slim.payload.software="ms-mssql.mssql" \
      slim.payload.version="${VSIX_VERSION}" \
      slim.payload.path="/slim/payload" \
      slim.payload.method="official-marketplace-vsix" \
      slim.payload.docs="/slim/AGENT.md"
COPY --from=prepare /slim /slim
