#!/bin/sh
set -eu

/app/github-mcp-server --version | grep -qF 'Version: v2.0.3'

# Disposable token. MCP initialize does not call the GitHub API. The server
# answers asynchronously and exits on stdin EOF, so hold stdin open for a few
# seconds; closing it right after the request dropped the response (CI run
# 41358517740).
out="$( { printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"runtime-smoke","version":"0"}}}'; sleep 5; } \
    | GITHUB_PERSONAL_ACCESS_TOKEN=github-mcp-runtime-smoke-token /app/github-mcp-server stdio --read-only 2>/dev/null)"
printf '%s' "$out" | grep -qF '"protocolVersion"'
printf '%s' "$out" | grep -qF '"serverInfo"'
echo "github-mcp-server version and MCP stdio initialize smoke OK"
