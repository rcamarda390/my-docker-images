# syntax=docker/dockerfile:1.7

ARG EBAY_MCP_VERSION=2.0.4
# Upstream v2.0.4 retains package.json version 1.18.0; verify both identities.
ARG EBAY_PACKAGE_VERSION=1.18.0
ARG EBAY_MCP_COMMIT=3c12ea5441961d5d0ce728d8585d2c1acbd0079d
ARG NODE_VERSION=24.22.3
ARG PNPM_VERSION=10.14.0
ARG NODE_IMAGE_DIGEST=sha256:3946fb783fdce8a2812136ea694bc95c698c4f4096f3fd18568dc27a8ac389dc

FROM node:${NODE_VERSION}-alpine3.23@${NODE_IMAGE_DIGEST} AS builder
ARG EBAY_MCP_VERSION
ARG EBAY_PACKAGE_VERSION
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
    test "$(node -p "require('./package.json').version")" = "${EBAY_PACKAGE_VERSION}"

# Install the upstream lockfile, which includes the patched dependencies.
RUN pnpm install --frozen-lockfile --ignore-scripts \
    && pnpm run build \
    && pnpm prune --prod --ignore-scripts

# Verify every physical pnpm runtime copy, including transitive dependencies.
RUN node -e "const fs=require('fs'); const root='node_modules/.pnpm'; const expected={'@modelcontextprotocol/sdk':'1.32.1','fast-uri':'3.1.8','proxy-addr':'2.0.8'}; for (const [name,version] of Object.entries(expected)) { let seen=0; for (const entry of fs.readdirSync(root)) { const file=root+'/'+entry+'/node_modules/'+name+'/package.json'; if (fs.existsSync(file)) { const actual=JSON.parse(fs.readFileSync(file)).version; if (actual!==version) throw new Error(name+': '+actual); seen++; } } if (!seen) throw new Error('Missing runtime dependency '+name); console.log(name+'='+version+' ('+seen+' copies)'); }"

FROM node:${NODE_VERSION}-alpine3.23@${NODE_IMAGE_DIGEST}
ARG EBAY_MCP_VERSION
ARG EBAY_PACKAGE_VERSION
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

