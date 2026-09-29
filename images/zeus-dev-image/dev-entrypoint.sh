#!/bin/bash
# zeus-dev-image entrypoint.
#
# The prompt and host-tmp permissions are configured at build time while the
# image is root. The final image runs as UID 1001, so this entrypoint must not
# modify root-owned paths.
set -eu

exec "$@"
