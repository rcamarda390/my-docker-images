#!/bin/sh
set -eu
if [ -z "${HEADROOM_PROXY_TOKEN:-}" ]; then
    echo "HEADROOM_PROXY_TOKEN must be set (same value as the headroom-mcp container)." >&2
    exit 1
fi
