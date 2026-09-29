#!/bin/sh
# Filters AgentMemory's bracketed "[...]" startup log lines out of its
# stdout before they reach Cline over stdio, since they would otherwise
# corrupt the MCP JSON-RPC stream. stdin is left untouched (this is the
# first command in the pipeline, so it still gets our real stdin).
set -eu

AGENTMEMORY_ENTRY="/opt/agentmemory/node_modules/@agentmemory/agentmemory/dist/index.mjs"

exec node "$AGENTMEMORY_ENTRY" mcp "$@" 2>&1 | grep -av --line-buffered '^\['
