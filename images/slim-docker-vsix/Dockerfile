# File: images/slim-docker-vsix/Dockerfile
# syntax=docker/dockerfile:1.7
# Builder tools never enter the payload image.
FROM python:3.12-slim AS prepare
ARG VSIX_VERSION
ARG VSIX_SHA256
COPY prepare.py /prepare.py
RUN python /prepare.py "${VSIX_VERSION}" "${VSIX_SHA256}" /slim
COPY AGENT.md /slim/AGENT.md

FROM scratch
ARG VSIX_VERSION
LABEL org.opencontainers.image.title="slim-docker-vsix" \
      org.opencontainers.image.version="${VSIX_VERSION}" \
      org.opencontainers.image.source="https://github.com/rcamarda390/my-docker-images" \
      slim.payload.software="ms-vscode.live-server" \
      slim.payload.version="${VSIX_VERSION}" \
      slim.payload.path="/slim/payload" \
      slim.payload.method="vsix" \
      slim.payload.docs="/slim/AGENT.md"
COPY --from=prepare /slim /slim
