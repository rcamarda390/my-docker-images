# Cline 4.0.12 → Headroom 0.40.0 → AWS Bedrock

This image carries a downstream Headroom 0.40.0 compatibility patch for Cline's
OpenAI-compatible transport to AWS Bedrock.

Headroom 0.40.0's upstream dependency lock resolves LiteLLM 1.101.0. The image
pins LiteLLM 1.101.3, the version verified for Bedrock Converse cache-point
conversion, and asserts that exact version in the final runtime.

Headroom 0.40.0 reads `HEADROOM_LICENSE` and makes usage reporting opt-in;
review these runtime settings during deployment. The removed CrewAI extra is
not used by this image. Upstream now locks AnyIO 4.14.2, so the old AnyIO
override is removed. PyJWT follows the newer upstream 2.15.1 lock.

## Container authentication in 0.40.0

The container binds `0.0.0.0`. Set `HEADROOM_PROXY_TOKEN` as a runtime secret
and configure callers to send that token using `Authorization: Bearer ...`
or `X-Headroom-Token`. Upstream refuses this bind without a token. Do not bake
the token into the image. Loopback callers and GET health probes are exempt;
network callers must authenticate. For a trusted remote compression sidecar,
also set `HEADROOM_COMPRESS_ALLOW_REMOTE=1`; that setting retains token checks.
The smoke test uses a disposable generated token and verifies an unauthenticated
non-loopback compression request is rejected before testing authenticated,
offline compression.

## Request shaping

Cline 4.0.12 sends `parallel_tool_calls=true`. Headroom 0.40.0 treats unknown
OpenAI request keys as `extra_body`, and LiteLLM consequently forwards this key
toward Bedrock, which rejects it. The downstream patch removes only
`parallel_tool_calls` from `extra_body` when the configured Headroom provider is
`bedrock`. Other providers retain the existing passthrough behavior.

Both `send_openai_message()` and `stream_openai_message()` are patched.

## Bedrock prompt caching

Cline's OpenAI-compatible path does not emit Bedrock cache markers. The
downstream hotfix enables prompt caching only when LiteLLM's
`supports_prompt_caching()` reports that the exact Bedrock model supports it.
`get_supported_openai_params()` is not used as the gate: it lists request
parameters, not the model's prompt-caching capability. In the verified LiteLLM
1.101.3 runtime it lists `cache_control` for the tested Bedrock model IDs, while
`supports_prompt_caching()` remains the dedicated per-model capability check.

For supported models, the patch adds:

```json
{"cache_control":{"type":"ephemeral"}}
```

to the stable system message (or the last block of list-form system content).
LiteLLM 1.101.3 natively converts that message-level marker into a Bedrock
Converse `cachePoint`.

For models that do not report `cache_control` support, no marker is added and
the request proceeds normally with prompt caching effectively off.

The previous `cache_control_injection_points` approach remains intentionally
unused. LiteLLM 1.101.3 recognizes that field only for `tool_config` and can
append a tool cache point; this image uses the tested system-message path only.

Dynamic user and assistant turns are not automatically marked. The system
prefix is the highest-value stable region for Cline and avoids moving cache
breakpoints as the conversation grows.

Tool-config caching is intentionally not injected by this patch. LiteLLM
1.101.3 supports a `tool_config` marker through
`cache_control_injection_points`, but this carry has validated only the native
system-message conversion and intentionally avoids changing tool payload
behavior.

## Completion-token compatibility

Bifrost translates `max_tokens` to `max_completion_tokens`. Headroom 0.40.0
already includes the translated name in its standard OpenAI parameters, so it
passes through as a normal LiteLLM argument. The build-time regression verifies
it remains top-level and does not leak into `extra_body`. The downstream patch
only adds the parameter on older supported source shapes; it does not duplicate
an upstream entry.

## Output-token shaping

The image enables Headroom's output shaper with:

```text
HEADROOM_OUTPUT_SHAPER=1
```

Headroom 0.40.0 reads this setting live on each proxy request. No fixed
`HEADROOM_VERBOSITY_LEVEL` is set.

`headroom learn --verbosity --apply` remains a deployment-time operation because
it depends on agent session history.

## Health check in the air-gapped deployment

The image sets `HEADROOM_SKIP_UPSTREAM_CHECK=1` to suppress Headroom 0.40.0's
external upstream readiness probe in the air-gapped Bedrock deployment. This
does not weaken TLS verification for Bedrock traffic.

## Build strategy

The patch is applied inside the main `Dockerfile` builder stage, directly to the
venv produced from the pinned upstream source. One action now produces the
finished image; there is no intermediate base image or second carry build.

The patch script expects exactly two Headroom 0.40.0 OpenAI call sites and fails
the build if the upstream source shape changes. Both are present at `v0.40.0`; the checked
anchor verification and regression suite pass. The build compiles the patched module and runs the
regression suite before copying the venv into the runtime image.

The patch and regression scripts remain in the builder stage. Only the patched
`/opt/venv` and the pre-cached compression assets cross into the runtime image.

## Upgrading Headroom while this carry exists

A version bump is one build. `images/headroom-mcp/image.yaml` carries the
upstream version, revision floor, and exact upstream commit.

1. Bump `upstream_version` and `build_args.HEADROOM_COMMIT` to the new tag and
   its commit (`git ls-remote --tags https://github.com/headroomlabs-ai/headroom.git`),
   reset `revision` to `1`, and update `ARG HEADROOM_VERSION` /
   `ARG HEADROOM_COMMIT` in `Dockerfile` to match. The build asserts the installed
   `headroom-ai` version equals `HEADROOM_VERSION`, and the source stage
   asserts the cloned tag equals `HEADROOM_COMMIT`, so a mismatch fails the
   build rather than shipping.
2. Re-verify the patch against the new release with the command below.
3. Merge the version PR. The push to `main` starts **Build and publish Headroom
   MCP image**, and the shared workflow forces a changed upstream version to
   revision `v1`.

Re-verify the patch before merging rather than discovering an anchor change in
CI. From `images/headroom-mcp/`, against the real package:

```bash
uv venv --python 3.13 /tmp/hr && \
export LITELLM_LOCAL_MODEL_COST_MAP=True && \
uv pip install --python /tmp/hr/bin/python "headroom-ai==<new-version>" "litellm==1.101.3" && \
target=$(/tmp/hr/bin/python -c 'import headroom.backends.litellm as m; print(m.__file__)') && \
/tmp/hr/bin/python patch-headroom-bedrock-openai.py "$target" && \
/tmp/hr/bin/python -m py_compile "$target" && \
/tmp/hr/bin/python bedrock-openai-regression.py
```

This is the same patch, compile, and regression sequence the Dockerfile runs.
The patch fails closed when the two call sites it anchors on no longer match.

## Verification

`bedrock-openai-regression.py` runs during the image build and verifies:

1. non-streaming Bedrock drops the unsafe `parallel_tool_calls` passthrough;
2. streaming Bedrock receives the same protection;
3. supported Bedrock models get native system `cache_control` markers using
   LiteLLM's prompt-caching capability API;
4. unsupported Bedrock models receive no cache marker;
5. `cache_control_injection_points` is never sent;
6. non-Bedrock providers remain unchanged;
7. dynamic user/assistant turns are not marked;
8. list-form system content receives the marker on its last block;
9. `max_completion_tokens` is forwarded as a standard argument, not through
   `extra_body`.

This is a temporary local carry for
[headroomlabs-ai/headroom#3554](https://github.com/headroomlabs-ai/headroom/issues/3554).
Remove it once Headroom releases the fix, then re-verify that allowed-request
behavior is unchanged.

After deployment, verify a sufficiently large stable Cline request reports
cache creation tokens on the first call and cache read tokens on a repeated
request, while normal Cline tool calls continue to succeed.

## Dashboard

Headroom serves per-request data (`recent_requests`, `/transformations/feed`)
only to loopback callers, which a bridge-network container is not. See
`DASHBOARD_TELEMETRY.md` for why the dashboard's Recent Requests table stays
empty while aggregate telemetry populates, and how to configure around it.
