# Bifrost image

[Back to repository README](../../README.md) · [Image source](../../images/bifrost-mcp/)

Current release metadata: [image.yaml](../../images/bifrost-mcp/image.yaml).

The notes below describe earlier dependency and base-image maintenance. Inspect the current Dockerfile and manifest before applying them to a newer release.

For Bifrost v1.6.11, prior investigation established that the upstream release should be followed closely rather than maintaining unnecessary dependency overrides.

Relevant upstream characteristics identified during that work included:

- Bifrost v1.6.11
- released `transports/go.mod`
- `GOWORK=off`
- Alpine-based build/runtime stages

The project removed or avoided custom Go dependency overrides that downgraded dependencies relative to the upstream release.

When maintaining the Bifrost image, prefer an upstream-compatible build unless a documented air-gap or security requirement makes a divergence necessary.

## Upgrade to 2.2.6

The image builds `transports/v2.2.6` at commit
`8b4fce4f1709d66f9208d02f50552da522535f9e`. Existing Xray Go dependency
fix pins remain necessary against this release's transport module graph.

Before deployment, configure `BIFROST_SETUP_TOKEN` (or `setup_token` in the
runtime config) if dashboard authentication is disabled. Management API clients
must send `X-Bifrost-Setup-Token` until dashboard authentication is configured.
Fresh configurations default to authenticated inference; use the deployment's
virtual keys and explicitly review the inference authentication setting.
MCP OAuth deployments require a non-empty `oauth2_server_config.issuer_url`.

Private HTTP URLs for pricing, model-parameter, and MCP-library catalogs are
rejected. Air-gapped deployments should use local `file://` catalog URLs.
Semantic cache entries are partitioned by virtual key, so expect a cold cache
after upgrade. No new database migrations are listed upstream.

PR validation builds through the existing workflow without publishing and
checks startup, version, rejected unauthenticated management access, and accepted
setup-token access. A merge affecting this image publishes on main; manual dispatch remains available.
GovCloud streaming and the full Cline/Headroom path require deployment testing
with runtime IAM credentials; CI does not carry those credentials.
