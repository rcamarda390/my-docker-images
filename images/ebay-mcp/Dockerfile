# syntax=docker/dockerfile:1.7

ARG EBAY_MCP_VERSION=1.16.0
ARG EBAY_MCP_COMMIT=edb937b44a47bf3d353ab9afb8818b6834ac222c
ARG NODE_VERSION=22.23.2
ARG PNPM_VERSION=10.14.0
ARG NODE_IMAGE_DIGEST=sha256:72c5815a06aed9a2273aea5628d74d348af57843a7b547af2fe53dd3e4b95261

FROM node:${NODE_VERSION}-alpine3.23@${NODE_IMAGE_DIGEST} AS builder
ARG EBAY_MCP_VERSION
ARG EBAY_MCP_COMMIT
ARG NODE_VERSION
ARG PNPM_VERSION

WORKDIR /src

RUN set -eux; \
    test "$(node --version)" = "v${NODE_VERSION}"; \
    apk upgrade --no-cache; \
    apk add --no-cache ca-certificates git; \
    npm install --global "pnpm@${PNPM_VERSION}"; \
    test "$(pnpm --version)" = "${PNPM_VERSION}"; \
    git clone --depth 1 --branch "v${EBAY_MCP_VERSION}" \
      https://github.com/YosefHayim/ebay-mcp.git .; \
    test "$(git rev-parse HEAD)" = "${EBAY_MCP_COMMIT}"; \
    test "$(node -p "require('./package.json').version")" = "${EBAY_MCP_VERSION}"

# Keep vulnerable transitive runtime dependencies above their fixed versions. These exact
# overrides are applied to the pinned upstream lockfile before installation.
RUN node -e "const fs=require('fs'); const p=require('./package.json'); p.pnpm=p.pnpm||{}; p.pnpm.overrides={...(p.pnpm.overrides||{}),'fast-uri':'3.1.6','ip-address':'10.3.1','brace-expansion@2':'2.1.4'}; fs.writeFileSync('package.json', JSON.stringify(p,null,2)+'\\n')" \
    && pnpm install --no-frozen-lockfile --ignore-scripts \
    && pnpm run build \
    && pnpm prune --prod --ignore-scripts

FROM node:${NODE_VERSION}-alpine3.23@${NODE_IMAGE_DIGEST}
ARG EBAY_MCP_VERSION
ARG EBAY_MCP_COMMIT
ARG NODE_VERSION

WORKDIR /app

RUN set -eux; \
    test "$(node --version)" = "v${NODE_VERSION}"; \
    apk upgrade --no-cache; \
    npm_root="$(npm root -g)"; \
    rm -rf "$npm_root/npm" /usr/local/bin/npm /usr/local/bin/npx; \
    mkdir -p /home/node/.ebay-mcp/logs; \
    touch /app/.env; \
    chown -R node:node /app /home/node/.ebay-mcp

COPY --from=builder --chown=node:node /src/package.json /src/pnpm-lock.yaml ./
COPY --from=builder --chown=node:node /src/node_modules ./node_modules
COPY --from=builder --chown=node:node /src/build ./build
COPY --from=builder --chown=node:node /src/docs ./docs
COPY --from=builder --chown=node:node /src/public ./public
COPY --chown=node:node runtime-smoke.mjs ./runtime-smoke.mjs

ENV NODE_ENV=production \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=3000 \
    EBAY_ENABLE_FILE_LOGGING=false

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null "http://127.0.0.1:${MCP_PORT}/health" || exit 1

LABEL org.opencontainers.image.title="ebay-mcp" \
      org.opencontainers.image.description="Unofficial eBay Sell API MCP server" \
      org.opencontainers.image.source="https://github.com/YosefHayim/ebay-mcp" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${EBAY_MCP_VERSION}" \
      org.opencontainers.image.revision="${EBAY_MCP_COMMIT}"

CMD ["node", "build/serverHttp.js"]
