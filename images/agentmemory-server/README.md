# AgentMemory image

This image intentionally follows the upstream `rohitg00/agentmemory` deployment pattern as closely as possible while adding a connected-build, air-gapped local embedding runtime.

## Upstream components

- AgentMemory: `0.9.30`
- iii engine: `0.22.1`
- iii SDK: `0.22.1`
- Runtime base: `node:26-slim`
- Local embedding runtime: `@huggingface/transformers` `4.2.0`
- Local embedding model: `Xenova/all-MiniLM-L6-v2` (`q8`, 384 dimensions)
- Published architecture: `linux/amd64` (the RHEL EC2 deployment target)

The Dockerfile uses the official `iiidev/iii` image as a build stage and copies `/app/iii` into the final AgentMemory image, matching upstream. AgentMemory itself is installed from npm at build time.

The Dockerfile downloads the pinned model revision during the connected build, verifies SHA-256 checksums, and stores the model under `/opt/agentmemory/models/`. A preload module configures Transformers.js to use that path, disables remote model loading, and uses the explicit read-only cache path `/opt/agentmemory/transformers-cache`. Runtime embedding therefore does not require OpenAI, Voyage, Cohere, Gemini, or OpenRouter credentials and does not download model files.

## Build metadata

`image.yaml` controls the upstream AgentMemory version, iii version, and local revision/tagging used by the reusable GitHub Actions workflow.

The published image is named `agentmemory-mcp` in both registries:

- Docker Hub: `docker.io/rcamarda390/agentmemory-mcp`
- GHCR: `ghcr.io/rcamarda390/agentmemory-mcp`

The source repository is `rcamarda390/my-docker-images`; the image's OCI source
label links the GHCR package to this repository. Earlier images published as
`agentmemory` remain under their original name. This name change does not rename
the application, its HTTP paths, or the persistent `agentmemory-data` volume.

Revision lookup uses published Docker Hub tags under `agentmemory-mcp`, so the
old `agentmemory` tag history does not determine the next revision. After a
successful main-branch publication, set `AGENTMEMORY_IMAGE_TAG` to the exact
versioned tag reported in the Actions summary before using `docker-compose.yml`
or the validation command below. The compose file requires this value instead
of assuming a tag has already been published.

The first build of a new upstream version is published as `UPSTREAM_VERSION-v1`; subsequent security or packaging revisions increment the `vN` suffix without changing the upstream version.

## Runtime data

Persist `/data` for AgentMemory state and the generated HMAC secret. Port `3111` exposes the AgentMemory HTTP service and health endpoint. The image starts with graph extraction, consolidation, auto-compression, and context injection disabled; enable graph extraction and consolidation only after the Headroom path is validated.

## Upgrade to 0.9.30

Back up the persistent `/data` volume before the first start. AgentMemory runs
one-time data migrations; test rollback against the backup rather than assuming
the upgraded store is readable by 0.9.29. The image preserves `/data/.hmac` and
the existing state/stream paths. REST requests now require Bearer authentication
by default. Configure remote MCP shims with `AGENTMEMORY_SECRET` from the
protected persistent secret; do not copy it into an image or source control.
Upgrade `slim-agentmemory-mcp` to 0.9.30 alongside this server.

The compatible iii engine and SDK are both 0.22.1. The old Resource API patch
and runtime OpenTelemetry SDK overrides are obsolete in that SDK and removed.
The generated-output array bound remains necessary and is regression-tested
against both 0.9.30 entry bundles.

## Combined runtime

The image contains one AgentMemory process and its compatible iii engine. Do not add a separate `iii-engine` container or process. The existing MCP client shim remains outside this image at:

```text
/opt/agentmemory-mcp/node_modules/@agentmemory/mcp/bin.mjs
```

Devcontainers remain client-only and connect to the persistent service over HTTP.

## Headroom readiness

When Headroom is available, inject these values at runtime through the protected deployment environment; do not put them in Git, the Dockerfile, compose files, or image layers:

```env
OPENAI_API_KEY=<Headroom inbound token>
OPENAI_BASE_URL=http://<headroom-host>:<port>/v1
OPENAI_MODEL=<exact model ID accepted by Headroom and Bedrock>
GRAPH_EXTRACTION_ENABLED=true
CONSOLIDATION_ENABLED=true
AGENTMEMORY_AUTO_COMPRESS=false
AGENTMEMORY_INJECT_CONTEXT=false
EMBEDDING_PROVIDER=local
```

The path is `AgentMemory -> Headroom -> Bifrost/LiteLLM -> AWS Bedrock`. Headroom is an HTTP LLM proxy, not an MCP server, so it does not belong in `cline_mcp_settings.json`. From inside the container, `localhost` refers to the AgentMemory container; use the Headroom Docker service name or a reachable host gateway instead.

## Existing vector data

AgentMemory 0.9.30 persists its search vector index as serialized Float32 vectors in the iii state store. The local provider and model above use 384 dimensions. AgentMemory checks persisted vector dimensions at startup and refuses to load mismatched vectors unless `AGENTMEMORY_DROP_STALE_INDEX=true` is explicitly set.

Before changing embedding providers, back up `/data` and export the AgentMemory data. If the existing vector index was written by another provider, start the new image once with `AGENTMEMORY_DROP_STALE_INDEX=true`; this discards only the stale vector index while preserving memories and observations. Re-import the export with the AgentMemory API using `strategy: "replace"` so the imported records are indexed again with the local provider. Confirm the service log reports `Embedding provider: local (384 dims)` and `Loaded persisted vector index` after the re-index completes. Do not mix vectors from different providers or dimensions.

## Validation

The image build runs `/usr/local/lib/agentmemory/offline-embedding-smoke.mjs` in a `RUN --network=none` layer. The image-specific workflow repeats the test in a disposable container with `--network none` and then checks `/agentmemory/livez`. To run the embedding check locally:

```bash
docker run --rm --network none "docker.io/rcamarda390/agentmemory-mcp:${AGENTMEMORY_IMAGE_TAG:?Set AGENTMEMORY_IMAGE_TAG to the exact published tag}" --offline-embedding-test
```

The expected result is `dimensions=384` with `remote_models=false`.

## Security follow-up: 2026-10-02

See [SECURITY-20261002.md](SECURITY-20261002.md) for the Xray findings,
patched components, required runtime libraries, and unresolved findings.
Pull requests affecting this image now run the existing build, offline runtime
smoke, health, and advisory Trivy checks without publishing or consuming a tag.
Merging a validated image change publishes on main using the next published revision.
