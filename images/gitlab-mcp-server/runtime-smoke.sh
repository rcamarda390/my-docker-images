#!/bin/sh
set -eu

/app/gitlab-mcp-server --version | grep -qF '3.4.0'

# Disposable token. MCP initialize does not call GitLab. The server exits on
# stdin EOF, so hold stdin open for a few seconds before closing it.
out="$( { printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"runtime-smoke","version":"0"}}}'; sleep 5; } \
    | GITLAB_TOKEN=glpat-runtime-smoke-token GITLAB_URL=https://gitlab.example.invalid/api/v4 /app/gitlab-mcp-server --transport stdio 2>/dev/null)"
printf '%s' "$out" | grep -qF '"protocolVersion"'
printf '%s' "$out" | grep -qF '"serverInfo"'
echo "gitlab-mcp-server version and MCP stdio initialize smoke OK"
