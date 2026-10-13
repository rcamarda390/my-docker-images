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

## CVE-2026-108859

Xray reports mcp-go v0.56.0 (CVSS 7.5, CWE-770); its fix version is N/A.
The latest upstream release checked on 2026-10-13, v1.2.1, also buffers POST
bodies without a limit. Updating to it would not remediate this finding.

The build vendors the resolved dependencies and patches mcp-go's
StreamableHTTPServer before compilation. Known oversized bodies are rejected
before reading; unknown-length bodies are capped with http.MaxBytesReader.
Both return HTTP 413 above 100 MiB, matching Bifrost's default body ceiling.
The build runs regression checks for both paths and normal MCP initialization.
The original module version remains recorded; no scanner metadata is hidden.

In pinned Bifrost 2.2.6, production code uses mcp-go clients and an in-process
MCPServer, with no StreamableHTTPServer constructor or ServeHTTP call. Its
public HTTP transport is fasthttp with its own configured body limit.
The downstream patch protects the library path if it becomes used later.
It does not change Bifrost's configurable public HTTP request limit.

Xray can continue reporting the original version despite this source fix.
A fresh scan is required; do not claim scanner clearance from a passing build.
Remove the patch after adopting a compatible upstream release with a verified
bounded read. Publication uses the existing next-published-revision workflow.
