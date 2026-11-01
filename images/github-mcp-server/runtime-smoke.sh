#!/bin/sh
set -eu

/app/github-mcp-server --version | grep -qF 'Version: v2.0.3'

# Disposable token. MCP initialize does not call the GitHub API. stdin EOF
# ends the stdio server, so no timeout wrapper is needed.
out="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"runtime-smoke","version":"0"}}}' \
    | GITHUB_PERSONAL_ACCESS_TOKEN=github-mcp-runtime-smoke-token /app/github-mcp-server stdio --read-only)"
printf '%s' "$out" | grep -qF '"protocolVersion"'
printf '%s' "$out" | grep -qF '"serverInfo"'
echo "github-mcp-server version and MCP stdio initialize smoke OK"
