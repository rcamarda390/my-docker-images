#!/bin/sh
# agentmemory first-boot entrypoint.
#
# Runs as root so it can:
#   1. chown the platform-mounted /data volume to the runtime user
#      (managed platforms mount volumes root-owned 755 by default).
#   2. Generate the HMAC secret on first boot and persist it to
#      /data/.hmac (chmod 600) so the secret survives restarts.
#
# Then it runs the agentmemory CLI under gosu as the unprivileged
# `node` user.

set -eu

DATA_DIR="${AGENTMEMORY_DATA_DIR:-/data}"
export AGENTMEMORY_DATA_DIR="$DATA_DIR"
HMAC_FILE="${AGENTMEMORY_HMAC_FILE:-/data/.hmac}"
RUN_AS="node:node"

if [ "${1:-}" = "--offline-embedding-test" ]; then
  shift
  exec gosu "$RUN_AS" node /opt/agentmemory/offline-embedding-smoke.mjs "$@"
fi

if [ "${1:-}" = "--runtime-smoke-test" ]; then
  shift
  exec node /opt/agentmemory/runtime-smoke.mjs "$@"
fi

mkdir -p "$DATA_DIR"
chown -R "$RUN_AS" "$DATA_DIR"

if [ ! -s "$HMAC_FILE" ]; then
  SECRET="$(openssl rand -hex 32)"
  umask 077
  printf '%s\n' "$SECRET" > "$HMAC_FILE"
  chmod 600 "$HMAC_FILE"
  chown "$RUN_AS" "$HMAC_FILE"
  echo "================================================================"
  echo "agentmemory: generated HMAC secret on first boot"
  echo "Stored at protected path: $HMAC_FILE (chmod 600)"
  echo "Read it from the persistent volume; it is never printed to logs."
  echo "To rotate: delete $HMAC_FILE on the persistent volume and restart."
  echo "================================================================"
fi

AGENTMEMORY_SECRET="$(cat "$HMAC_FILE")"
export AGENTMEMORY_SECRET

if [ -n "${FLY_APP_NAME:-}" ] || [ -n "${FLY_ALLOC_ID:-}" ]; then
  : "${AGENTMEMORY_VIEWER_HOST:=::}"
  : "${VIEWER_ALLOWED_HOSTS:=localhost:3113,127.0.0.1:3113,[::1]:3113}"
  export AGENTMEMORY_VIEWER_HOST VIEWER_ALLOWED_HOSTS
fi

gosu "$RUN_AS" agentmemory "$@"

# Subcommands (for example `stop`) return here. A bare start hands off to
# agentmemory 0.9.31, which detaches the iii Compose daemon and exits 0. Hold
# PID 1 open so the container stays up, and stop AgentMemory cleanly on SIGTERM.
if [ "$#" -gt 0 ]; then
  exit 0
fi
# ponytail: a dead Compose daemon leaves the container running. Upgrade path:
# loop on a /agentmemory/livez probe and exit when it fails.
trap 'gosu "$RUN_AS" agentmemory stop; exit 0' TERM INT
while :; do
  sleep 60 & wait $!
done
