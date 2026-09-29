# my-docker-images

Docker image build repository for development and air-gapped deployment workflows.

Repository:

```text
https://github.com/rcamarda390/my-docker-images
```

The project is used to build container images outside restricted work environments, publish or transfer those images through an approved registry/artifact path, and run them on Linux hosts where Docker is available but host-level software installation is not.

## Why this repository exists

The target work environment has several important constraints:

- Linux EC2 hosts can run Docker.
- Software should not be installed directly on the EC2 host.
- Some development environments are air-gapped or have tightly controlled network access.
- The Windows work environment may not have Docker available.
- Images therefore need to be built in a connected environment, then moved through the approved registry/Artifactory/manual import process.

`my-docker-images` centralizes the Dockerfiles, entrypoints, patches, documentation, and CI build logic needed for those images.

## Repository inventory

The live `main` branch contains image targets under `images/`:

| Directory | Image | Upstream version | Revision | Notes |
| --- | --- | ---: | ---: | --- |
| `images/agentmemory-server/` | `agentmemory` | 0.9.29 | 1 | Self-contained AgentMemory server; builds with iii engine 0.11.2 |
| `images/bifrost-mcp/` | `bifrost-mcp` | 1.6.11 | 9 | Bifrost gateway image pinned to a specific upstream commit |
| `images/gnosis-mcp/` | `gnosis-mcp` | 0.17.5 | 11 | Air-gap Gnosis documentation MCP server with local embeddings |
| `images/headroom-mcp/` | `headroom-mcp` | 0.38.0 | 1 | Headroom proxy/MCP image with Bedrock-oriented variants |
| `images/litellm/` | `litellm` | 1.94.3 | 1 | LiteLLM AI Gateway built from a pinned upstream commit |
| `images/sooperset-mcp-atlassian/` | `sooperset-mcp-atlassian` | 0.23.1 | 6 | Sooperset Atlassian MCP image |
| `images/sqz-mcp/` | `sqz-mcp` | 1.3.0 | 4 | SQZ MCP image pinned to a specific upstream commit |

The repository root currently also contains:

```text
.github/
docs/
images/
build-airflow-dev-image.ps1
```

The `docs/` directory contains project-level operational documentation including:

```text
docs/MCP_BUILD_METHODOLOGY.md
docs/agent-review-reply.md
```

The primary image structure is therefore:

```text
images/
├── agentmemory-server/
├── bifrost-mcp/
├── gnosis-mcp/
├── headroom-mcp/
├── sooperset-mcp-atlassian/
└── sqz-mcp/
```

Each current image target has an `image.yaml` manifest that records its image name, upstream version, local revision, build arguments, and registry publication settings.

All current manifests are configured to publish to both:

```text
GHCR
Docker Hub
```

and currently have:

```yaml
latest: false
```

This means published images are intended to use explicit version/revision tags rather than relying on a moving `latest` tag.

## Build philosophy

Changes required by a runtime image should be made in the Docker image build whenever possible.

Avoid treating edits made interactively inside a running container as the permanent solution. Temporary container edits are useful for diagnosis, but the final fix should normally be represented by one or more of:

- `Dockerfile`
- image entrypoint
- checked-in patch script
- pinned dependency change
- image-specific configuration
- CI build workflow

This makes the resulting image reproducible and suitable for import into restricted environments.

## Image publishing

The current image manifests publish to both GitHub Container Registry (GHCR) and Docker Hub.

The GHCR image format is:

```text
ghcr.io/rcamarda390/<image-name>:<version>-v<revision>
```

Each `images/<target>/image.yaml` controls the target's upstream version, local image revision, build arguments, and publication behavior.

Current manifests use:

```yaml
publish:
  ghcr: true
  dockerhub: true
  latest: false
```

The preferred operational model is to perform image builds and publishing in a connected build environment rather than requiring Docker on the restricted Windows workstation.

## GitHub Actions

GitHub Actions provides the repository's image build/publish automation.

The live workflow inventory includes image-specific entry-point workflows:

```text
.github/workflows/
├── build-agentmemory-server.yml
├── build-bifrost-mcp.yml
├── build-gnosis-mcp.yml
├── build-headroom-mcp.yml
├── build-sooperset-mcp-atlassian.yml
├── build-sqz-mcp.yml
├── build-image.yml
└── check-upstream-versions.yml
```

`build-image.yml` is the shared/general image-build workflow used by the repository, while the individual `build-*.yml` workflows provide image-specific build entry points.

`check-upstream-versions.yml` supports maintenance by checking for upstream version changes.

This is important because the restricted work Windows system does not need a local Docker installation merely to produce an image.

General flow:

```text
git push
   ↓
GitHub repository
   ↓
image-specific GitHub Actions workflow
   ↓
shared build logic
   ↓
container build
   ↓
GHCR + Docker Hub
   ↓
approved air-gap / artifact-transfer process
   ↓
work EC2 Docker host
```

Avoid creating overlapping workflows that independently publish the same image unless there is a deliberate operational reason.

## Air-gapped deployment principles

Images intended for the restricted work environment should be as self-contained as practical.

At runtime:

- do not assume public package repositories are reachable;
- do not download Python, Node, model, or other dependencies that can be baked into the image;
- prefer pinned dependencies for reproducibility;
- retain only the external connectivity that the application genuinely requires;
- use mounted persistent storage for state that must survive container replacement;
- obtain AWS credentials from the runtime environment rather than embedding credentials in the image.

For AWS workloads, credentials should not be copied into the Docker image.

## Gnosis MCP image

The repository contains an air-gap-oriented Gnosis MCP image at:

```text
images/gnosis-mcp/
```

Current manifest:

```yaml
name: gnosis-mcp
upstream_version: 0.17.5
revision: 11
build_args:
  EMBED_MODEL: "MongoDB/mdbr-leaf-ir"
  EXTRAS: "embeddings"
  PYTHON_VERSION: "3.13"
publish:
  ghcr: true
  dockerhub: true
  latest: false
```

Its purpose is to provide a self-hosted MCP documentation server suitable for restricted/offline runtime environments.

The image pre-bundles the local embedding model required by Gnosis rather than downloading it after deployment. The Docker build downloads the required tokenizer and ONNX model artifacts into:

```text
/gnosis-model-cache
```

Runtime defaults include:

```text
GNOSIS_MCP_HOST=0.0.0.0
GNOSIS_MCP_PORT=8000
GNOSIS_MCP_DATABASE_URL=sqlite:////data/docs.db
GNOSIS_MCP_EMBED_PROVIDER=local
GNOSIS_MCP_WRITABLE=false
XDG_DATA_HOME=/gnosis-model-cache
```

Persistent state is expected under:

```text
/data
```

and the image exposes port:

```text
8000
```

The runtime runs as the non-root `gnosis` user.

### Gnosis Streamable HTTP support

Gnosis 0.17.5 includes the REST/StreamableHTTP lifespan handling required to
initialize the MCP session manager when both transports are mounted together.
The image therefore no longer carries a local `rest.py` patch; the build still
verifies the resulting runtime and exercises the combined transport through
the image smoke test.

The image starts Gnosis with:

```text
gnosis-mcp serve --transport streamable-http --rest
```

The image also includes security-hardening work, including Python 3.13 and Debian package updates. Security scanner findings should remain a release gate when a critical base-library vulnerability does not yet have an upstream distribution fix.

## Headroom / AWS Bedrock image

A significant project area is:

```text
images/headroom-mcp/
```

This image supports the Headroom → LiteLLM → AWS Bedrock path used in the work environment.

Verified runtime chain:

```text
Cline
  ↓
Bifrost
  ↓
Headroom
  ↓
LiteLLM
  ↓
AWS Bedrock GovCloud
```

The Headroom image has required Bedrock-specific dependencies in addition to the base proxy dependencies.

A prior build used:

```text
uv sync --frozen --extra proxy --no-dev --no-editable
```

The Bedrock-capable build needs the Bedrock dependency extra as well:

```text
uv sync --frozen --extra proxy --extra bedrock --no-dev --no-editable
```

The Bedrock extra supplies the AWS SDK dependencies required by the Headroom/LiteLLM backend rather than installing them manually with `pip`.

AWS credentials should continue to come from the host/runtime IAM environment.

### Offline-oriented environment settings

For an air-gap-oriented Headroom image, previous project work identified these settings as useful:

```text
LITELLM_LOCAL_MODEL_COST_MAP=True
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_HUB_DISABLE_TELEMETRY=1
HEADROOM_UPDATE_CHECK=off
```

Do **not** blindly set:

```text
HEADROOM_OFFLINE=1
```

when the container still needs to communicate with AWS Bedrock.

### Permanent patches

Compatibility fixes discovered through live-container testing should be folded back into:

```text
images/headroom-mcp/
```

rather than left only in the running container.

One area investigated was Headroom/LiteLLM OpenAI-compatible request handling, including SSL verification and translation between OpenAI-compatible token parameters and the Bedrock-facing implementation.

The repository already contains:

```text
patch-headroom-bedrock-openai.py
```

for image-build-time compatibility handling.

## Bifrost image work

`my-docker-images` has also been used for Bifrost dependency and base-image maintenance.

For Bifrost v1.6.11, prior investigation established that the upstream release should be followed closely rather than maintaining unnecessary dependency overrides.

Relevant upstream characteristics identified during that work included:

- Bifrost v1.6.11
- released `transports/go.mod`
- `GOWORK=off`
- Alpine-based build/runtime stages

The project removed or avoided custom Go dependency overrides that downgraded dependencies relative to the upstream release.

When maintaining the Bifrost image, prefer an upstream-compatible build unless a documented air-gap or security requirement makes a divergence necessary.

## Sooperset MCP Atlassian image

The repository builds the Sooperset MCP Atlassian project from:

```text
images/sooperset-mcp-atlassian/
```

The image manifest defines its current upstream version and local revision:

```text
images/sooperset-mcp-atlassian/image.yaml
```

## SQZ MCP image

The repository contains:

```text
images/sqz-mcp/
```

Current manifest:

```yaml
name: sqz-mcp
upstream_version: 1.3.0
revision: 4
build_args:
  SQZ_COMMIT: d024b6b6bec152dfa7a63e2316054b1bb33a8110
publish:
  ghcr: true
  dockerhub: true
  latest: false
```

The explicit upstream commit pin makes the build reproducible even when the upstream repository continues to move.

## AgentMemory image architecture

AgentMemory work in this repository was simplified around a single self-contained server image for air-gapped deployment.

Target architecture:

```text
EC2 Linux host
└── Docker container: agentmemory-server
    ├── AgentMemory
    ├── compatible iii engine
    └── persistent /data

VS Code devcontainers
└── @agentmemory/mcp
    └── connects over HTTP to agentmemory-server:3111
```

For this use case:

- do not deploy a separate `iii-engine` container;
- avoid multiple overlapping GitHub Actions workflows capable of building the same AgentMemory stack;
- persist required AgentMemory state outside the disposable container filesystem.

## Local development

Clone the repository:

```bash
git clone https://github.com/rcamarda390/my-docker-images.git
cd my-docker-images
```

Create a feature branch for changes:

```bash
git switch -c <feature-branch>
```

Do not make feature changes directly on `main`.

Build an image from the relevant image directory or from the build context expected by its workflow.

Example pattern:

```bash
docker build -t <image-name>:<tag> <build-context>
```

Use the actual image-specific Dockerfile and build context documented in that directory.

## Validation

Image validation should happen at multiple levels.

### 1. Build validation

Confirm the image builds without pulling dependencies unexpectedly during runtime initialization.

### 2. Import validation

Confirm the built artifact can be moved through the approved registry or air-gap process and imported on the target Docker host.

### 3. Runtime validation

Confirm the container starts with the same mounts, IAM access, CA certificates, network paths, and resource limits used in the target environment.

### 4. Application validation

Test the service directly before introducing additional proxies or gateways.

For example, Headroom troubleshooting has used a direct OpenAI-compatible request to the Headroom service before testing the complete Bifrost route. This distinguishes a Headroom/backend problem from a Bifrost routing problem.

## Persistent data

Do not assume container filesystems are durable.

Any database, workspace, configuration, model cache, or other state that must survive an image upgrade should be stored in:

- a bind mount;
- a named Docker volume; or
- another explicitly persistent external location.

Before replacing an existing container, inspect its mounts and environment so the new image is started with equivalent persistent storage.

## Security

Do not commit:

- AWS access keys;
- Bifrost virtual-key secrets;
- API tokens;
- registry passwords;
- private certificates;
- environment-specific secrets.

Use IAM roles, CI secrets, runtime environment variables, secret mounts, or the applicable enterprise secret-management process.

## Branching and change management

Use feature branches and pull requests for image changes.

A typical change should include:

1. Dockerfile or supporting-file modification.
2. Dependency/pin change where required.
3. CI workflow update if the image build process changes.
4. Build validation.
5. Runtime smoke test.
6. Documentation update when operational behavior changes.

Keep image fixes reproducible and reviewable rather than relying on undocumented commands run against a live container.

## Troubleshooting approach

When debugging an image built by this repository:

1. Test the target service directly.
2. Inspect the container logs.
3. Verify environment variables.
4. Verify mounted CA certificates and persistent volumes.
5. Verify network reachability from inside the container.
6. Verify IAM/runtime credentials without embedding credentials.
7. Reproduce the fix in the image build.
8. Rebuild and retest from a clean container.

This is especially important for multi-hop chains such as:

```text
client → Bifrost → Headroom → LiteLLM → Bedrock
```

A direct test at each layer generally isolates problems faster than changing multiple components simultaneously.

## Project status

`my-docker-images` is an active infrastructure repository rather than a single-application Docker example. Its role is to make third-party and internal tooling reproducible, portable, and deployable into restricted Docker-based environments.

Current image areas include:

- AgentMemory
- Atlassian MCP
- Bifrost
- Gnosis MCP with bundled local embeddings
- Headroom with AWS Bedrock support
- Sooperset MCP Atlassian
- SQZ MCP
- air-gap hardening
- dependency/security maintenance
- reproducible container builds

When adding a new image, follow the same principle: everything required to reproduce the deployable artifact should live in source control whenever it is safe and practical to do so.
