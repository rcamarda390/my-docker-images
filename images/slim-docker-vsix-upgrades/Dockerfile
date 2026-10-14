# syntax=docker/dockerfile:1.7
# File: images/slim-docker-vsix-upgrades/Dockerfile
# Python and network access exist only in the builder. Final image is scratch.
FROM python:3.12-slim AS prepare
ARG VSCODE_TARGET_VERSION
COPY prepare.py verify.py test-prepare.py extensions.json /build/
RUN python -I /build/test-prepare.py \
    && python -I /build/prepare.py /build/extensions.json /slim "${VSCODE_TARGET_VERSION}" \
    && python -I /build/verify.py /build/extensions.json /slim "${VSCODE_TARGET_VERSION}"
COPY AGENT.md /slim/AGENT.md

FROM scratch
ARG VSCODE_TARGET_VERSION
LABEL org.opencontainers.image.title="slim-docker-vsix-upgrades" \
      org.opencontainers.image.version="${VSCODE_TARGET_VERSION}" \
      org.opencontainers.image.source="https://github.com/rcamarda390/my-docker-images" \
      slim.payload.software="vscode-extensions-upgrades" \
      slim.payload.version="${VSCODE_TARGET_VERSION}" \
      slim.payload.path="/slim/payload" \
      slim.payload.method="official-marketplace-vsix" \
      slim.payload.docs="/slim/AGENT.md"
COPY --from=prepare /slim /slim
