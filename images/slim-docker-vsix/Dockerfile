# syntax=docker/dockerfile:1.7
# File: images/slim-docker-vsix/Dockerfile
# Tools and original vulnerable VSIX remain builder-only.
FROM node:24-trixie-slim@sha256:8ec5d7557396cfe32d21c3f9c13072355ceab22b584578ca4bb28af31120cffe AS rebuild
ARG LIVE_PREVIEW_COMMIT
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && git clone https://github.com/microsoft/vscode-livepreview.git /src \
    && git -C /src checkout "${LIVE_PREVIEW_COMMIT}" \
    && test "$(git -C /src rev-parse HEAD)" = "${LIVE_PREVIEW_COMMIT}"
WORKDIR /src
COPY yarn.lock /src/yarn.lock
RUN npm install --global yarn@1.22.22 --force \
    && node -e 'const fs=require("fs");const p=require("./package.json");p.dependencies.ws="8.21.0";fs.writeFileSync("package.json",JSON.stringify(p,null,2))' \
    && yarn install --frozen-lockfile --ignore-scripts --ignore-engines --non-interactive
COPY build.cjs verify-ws.cjs /checks/
RUN node /checks/verify-ws.cjs && node /checks/build.cjs

FROM python:3.12-slim AS prepare
ARG VSIX_VERSION
ARG VSIX_SHA256
COPY --from=rebuild /src/out/extension.js /src/out/extension.js
COPY --from=rebuild /src/runtime-packages.json /src/runtime-packages.json
COPY prepare.py /prepare.py
RUN python /prepare.py "${VSIX_VERSION}" "${VSIX_SHA256}" /slim /src
COPY AGENT.md /slim/AGENT.md

FROM scratch
ARG VSIX_VERSION
LABEL org.opencontainers.image.title="slim-docker-vsix" \
      org.opencontainers.image.version="${VSIX_VERSION}" \
      org.opencontainers.image.source="https://github.com/rcamarda390/my-docker-images" \
      slim.payload.software="ms-vscode.live-server" \
      slim.payload.version="${VSIX_VERSION}" \
      slim.payload.path="/slim/payload" \
      slim.payload.method="vsix-custom-rebuild" \
      slim.payload.docs="/slim/AGENT.md"
COPY --from=prepare /slim /slim
