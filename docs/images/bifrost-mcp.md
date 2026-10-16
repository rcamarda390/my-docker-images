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

## Upgrade to 2.3.0

The image builds `transports/v2.3.0` at commit
`9237ec06672406e437b3cb33fc793ffd0403b3ae` (peeled tag commit). Upstream
`transports/go.mod` is unchanged from 2.2.6 for every pinned module, so all
Xray Go pins and the mcp-go body-limit patch are retained. mcp-go is still
v0.43.2 upstream and `server.StreamableHTTPServer` is still not constructed;
the new A2A handler calls a generic `ServeHTTP`, not mcp-go's.

Deployment notes from the upstream release:

- MCP OAuth server hardening: before upgrading, list every remote OAuth callback
  URI in `client.oauth2_server_config.allowed_redirect_uris` (loopback and
  `cursor://anysphere.cursor-mcp` are always allowed). Unlisted remote callbacks
  are rejected, including existing registrations. Keep the 2.2.6 `issuer_url`
  requirement as well.
- 45 config-store and 9 log-store migrations. `move_config_json_vk_limits_to_model_configs`
  is non-reversible; back up `/app/data` first. Run a single pod during rollout
  if virtual-key limits must stay enforced.
- `enforce_vk_object_ownership` defaults to `true` (files/batches only via the
  creating virtual key); set `client.enforce_vk_object_ownership: false` to share.
- Warp AI assistant is on by default; set `feature_flags.flags.warp.enabled: false`
  for air-gapped deployments.
- Gateway request ID is `x-bifrost-request-id`; provider `base_url` may not carry
  userinfo, query or fragment; semantic cache skips tool-call responses unless
  `cache_tool_call_responses: true`; truncated Bedrock Converse streams return 502.
- Bedrock fixes: guardrail `guardContent`/`tagSuffix`, document `cachePoint`,
  Claude root `oneOf/anyOf/allOf` tool schemas, thinking-block ordering, and
  `/bedrock_passthrough` (InvokeAgent, Retrieve, ApplyGuardrail).

Full Xray clearance, GovCloud streaming and the Cline/Headroom path still need
deployment testing.

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

In pinned Bifrost 2.3.0, production code uses mcp-go clients and an in-process
MCPServer, with no StreamableHTTPServer constructor or ServeHTTP call. Its
public HTTP transport is fasthttp with its own configured body limit.
The downstream patch protects the library path if it becomes used later.
It does not change Bifrost's configurable public HTTP request limit.

Xray can continue reporting the original version despite this source fix.
A fresh scan is required; do not claim scanner clearance from a passing build.
Remove the patch after adopting a compatible upstream release with a verified
bounded read. Publication uses the existing next-published-revision workflow.

## XRAY-1110429: go-jose v4.1.4

Source: Xray scan of `bifrost-mcp:2.3.0-v3` (7.5, CWE-407). Component
`github.com/go-jose/go-jose/v4` v4.1.4, fixed in v4.1.6. It is an indirect
upstream dependency of Bifrost 2.3.0 (`transports/go.mod`).

Remediation: Dockerfile pins `GO_JOSE_VERSION=v4.1.6`, checks the resolved
module list, and asserts the version in the final binary's build info. Drop the
pin once upstream requires v4.1.6 or newer. Status: pending rescan of the new
published digest.

The same scan still reports CVE-2026-108859 (mcp-go 0.56.0, no fix version). It
stays open in the scanner: the downstream body-limit patch is retained, and
the module version is unchanged. Verified 2026-10-16: no official fix in
mcp-go through v1.3.0.

### CVE-2026-108859 tracking (2026-10-16)

- Scanned `2.3.0-v3` reports mcp-go 0.56.0; published `2.3.0-v4` still carried the downstream vendor patch. Rescan of v4 pending.
- Reachability, from pinned Bifrost `transports/v2.3.0` (`9237ec06672406e437b3cb33fc793ffd0403b3ae`): `grep -rn "NewStreamableHTTPServer\|StreamableHTTPServer"` over non-test Go files matches only `examples/mcps/*` (separate `go.mod` per example, not in the `./bifrost-http` binary). The only gateway consumer, `transports/bifrost-http/handlers/mcpserver.go`, uses `server.NewMCPServer` and its in-process `MCPServer`, never a `StreamableHTTPServer` or its `ServeHTTP`. The patch/fork is defence in depth.
- Upstream fix, unreleased: https://github.com/mark3labs/mcp-go/pull/1092 (4 MiB default, `WithMaxRequestBodyBytes`). mcp-go v1.3.0 is still unbounded.

#### Fork replace (adopted; Xray cleared `2.3.0-v5` on 2026-10-16)

`github.com/rcamarda390/mcp-go` branch `claude/bifrost-body-limit` = upstream v0.56.0 + cherry-pick of PR #1092 (commit `aa78020aa10ffa85f1cdce32bfbbef35c98a5870`). The Dockerfile now `go mod edit -replace`s mcp-go to it and no longer applies `mcp-go-body-limit.patch` (removed). The fork's tags/`main` could not be pushed from the agent session, so the version is the pseudo-version `v0.0.0-20261016132355-aa78020aa10f`.

Go build info keeps `dep github.com/mark3labs/mcp-go v0.56.0` and adds `=> github.com/rcamarda390/mcp-go <pseudo-version>`; the build asserts both lines. A scanner reading only the `dep` line may still report the CVE. The regression test now uses the fork's 4 MiB `DefaultMaxRequestBodyBytes`.

Outcome rule: if Xray clears the fork build, keep it until upstream releases PR #1092, then drop the replace. If Xray still reports it, revert to the vendor patch (git history: PR #72) and keep the finding documented as not reachable and source-fixed.

#### Result (2026-10-16)

User Xray scan of `rcamarda390/bifrost-mcp/2.3.0-v5` (image digest not supplied): clean. Both findings cleared: XRAY-1110429 (go-jose pinned to v4.1.6) and CVE-2026-108859 (mcp-go resolved to the fork). So Xray follows the `=>` replacement in Go build info. Keep the fork until a released mcp-go contains upstream PR #1092, then drop the replace and fork. The fork's tags and `main` are still unpushed (agent session limits); the Dockerfile pins the commit by pseudo-version.
