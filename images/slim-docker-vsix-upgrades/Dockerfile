# syntax=docker/dockerfile:1.7
# File: images/slim-docker-vsix-upgrades/Dockerfile
FROM node:24-trixie-slim@sha256:8ec5d7557396cfe32d21c3f9c13072355ceab22b584578ca4bb28af31120cffe AS prepare
RUN apt-get update && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
# Builder-only compatibility parser; never installed into extension payloads.
RUN npm install --prefix /checks --ignore-scripts --no-audit --no-fund semver@7.7.2
ENV NODE_PATH=/checks/node_modules
ARG IMAGE_VERSION
ARG SOURCE_REVISION
ENV IMAGE_VERSION=${IMAGE_VERSION} SOURCE_REVISION=${SOURCE_REVISION}
WORKDIR /checks
COPY prepare.py test-prepare.py extensions.json ./
RUN python3 test-prepare.py && python3 prepare.py extensions.json /slim
COPY AGENT.md /slim/AGENT.md

FROM scratch
ARG IMAGE_VERSION
LABEL org.opencontainers.image.title="slim-docker-vsix-upgrades" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.source="https://github.com/rcamarda390/my-docker-images" \
      slim.payload.method="official-marketplace-vsix" \
      slim.payload.target-vscode="1.98.2" \
      slim.payload.path="/slim/payload"
COPY --from=prepare /slim /slim
