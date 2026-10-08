#!/bin/sh
set -eu

export APP_DIR="$(mktemp -d)"
# Disposable test credential only; never used by a deployment.
export BIFROST_SETUP_TOKEN=bifrost-runtime-smoke-token
/app/main > "$APP_DIR/server.log" 2>&1 &
server_pid=$!
cleanup() {
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
    cat "$APP_DIR/server.log"
    rm -rf "$APP_DIR"
}
trap cleanup EXIT

ready=false
for attempt in $(seq 1 60); do
    kill -0 "$server_pid"
    if wget -q -O /dev/null http://127.0.0.1:8080/health; then
        ready=true
        break
    fi
    sleep 1
done
test "$ready" = true
wget -q -O - http://127.0.0.1:8080/api/version | grep -F '2.2.6'
if wget -S -O /dev/null http://127.0.0.1:8080/api/config 2> "$APP_DIR/unauthorized.log"; then
    echo "Management API accepted an unauthenticated request" >&2
    exit 1
fi
grep -q '401' "$APP_DIR/unauthorized.log"
wget -q -O /dev/null --header="X-Bifrost-Setup-Token: $BIFROST_SETUP_TOKEN" \
    http://127.0.0.1:8080/api/config
echo "Bifrost health, version, and setup-token authentication smoke OK"
