#!/bin/sh
# Thin wrapper around the `jira` pip package's jirashell entry point.
# Installed to /usr/local/bin/jirashell so it takes precedence over the
# console script pip drops in the same directory; calling the module
# directly (rather than depending on that script's own path) keeps this
# working regardless of install order.
#
# ponytail: no default JIRA server/auth is baked in here since the internal
# defaults weren't provided to this build. Set JIRA_SERVER / JIRA_USER /
# JIRA_TOKEN (or pass jirashell's own flags) at runtime.
set -eu
exec python3 -m jira.jirashell "$@"
