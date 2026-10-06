# syntax=docker/dockerfile:1.7

# Slim payload image: carries the @agentmemory/mcp stdio shim (installed tree),
# nothing else. Not runnable (FROM scratch). Consumers copy /opt/agentmemory-mcp.
# The agentmemory SERVER is out of scope: the shim talks to it over HTTP
# (AGENTMEMORY_URL, runtime env only). Same glibc Node base as slim-archify.
ARG NODE_IMAGE=node:24-trixie-slim@sha256:8ec5d7557396cfe32d21c3f9c13072355ceab22b584578ca4bb28af31120cffe

FROM ${NODE_IMAGE} AS build
ARG AGENTMEMORY_MCP_VERSION
ARG NODE_MAJOR
ENV NPM_CONFIG_UPDATE_NOTIFIER=false NPM_CONFIG_FUND=false NPM_CONFIG_AUDIT=false
RUN set -eu; \
    test "$(node -p 'process.versions.node.split(".")[0]')" = "${NODE_MAJOR}"; \
    npm install "@agentmemory/mcp@${AGENTMEMORY_MCP_VERSION}" --prefix /opt/agentmemory-mcp --omit=dev; \
    test "$(node -p "require('/opt/agentmemory-mcp/node_modules/@agentmemory/mcp/package.json').version")" = "${AGENTMEMORY_MCP_VERSION}"; \
    npm cache clean --force
# Proxy mode (standalone.mjs) never loads these. Verified against the real 0.9.29
# tree: Claude Agent SDK (+ platform binaries), sharp/libvips and jieba natives
# (optional deps of the full server), OpenTelemetry (iii-sdk only), sourcemaps,
# type stubs. package.json / package-lock.json / node_modules/.package-lock.json
# are kept so Xray can identify components.
RUN set -eu; cd /opt/agentmemory-mcp/node_modules; \
    rm -rf @anthropic-ai/claude-agent-sdk @anthropic-ai/claude-agent-sdk-* \
           @img @node-rs @opentelemetry @types; \
    find . -type d -name 'onnxruntime-web' -prune -exec rm -rf {} +; \
    find . -name '*.map' -delete
# Falsifiable checks against the final tree, no server, no network:
#  - version + bin entry present and parseable
#  - shim starts and answers JSON-RPC initialize (module resolution works after trim)
#  - trimmed components are really gone
RUN set -eu; \
    P=/opt/agentmemory-mcp/node_modules/@agentmemory/mcp; \
    BIN="$P/$(node -p "require('$P/package.json').bin['agentmemory-mcp']")"; \
    test -f "$BIN"; \
    chmod 755 "$BIN"; \
    node --check "$BIN"; \
    ! ls /opt/agentmemory-mcp/node_modules/@anthropic-ai | grep -q claude-agent-sdk; \
    ! find /opt/agentmemory-mcp -name 'onnxruntime-web' | grep -q .; \
    test ! -e /opt/agentmemory-mcp/node_modules/@opentelemetry; \
    OUT="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"verify","version":"0"}}}' \
      | AGENTMEMORY_URL=http://127.0.0.1:1 timeout 20 node "$BIN" 2>/dev/null)"; \
    echo "$OUT" | grep -q "\"version\":\"${AGENTMEMORY_MCP_VERSION}\""; \
    du -sh /opt/agentmemory-mcp; \
    find /opt/agentmemory-mcp -type d -name 'onnxruntime-node' | head

FROM scratch
ARG AGENTMEMORY_MCP_VERSION
LABEL org.opencontainers.image.title="slim-agentmemory-mcp" \
      org.opencontainers.image.version="${AGENTMEMORY_MCP_VERSION}" \
      org.opencontainers.image.source="https://github.com/rohitg00/agentmemory" \
      org.opencontainers.image.licenses="Apache-2.0" \
      slim.payload.software="agentmemory-mcp" \
      slim.payload.version="${AGENTMEMORY_MCP_VERSION}" \
      slim.payload.path="/opt/agentmemory-mcp" \
      slim.payload.method="build-copy"
COPY --from=build /opt/agentmemory-mcp /opt/agentmemory-mcp
