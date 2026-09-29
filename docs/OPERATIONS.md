# Development and operations

[Back to repository README](../README.md) · [MCP build methodology](MCP_BUILD_METHODOLOGY.md)

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

Check the target image's `image.yaml` for its publication settings.

The preferred operational model is to perform image builds and publishing in a connected build environment rather than requiring Docker on the restricted Windows workstation.

## GitHub Actions

GitHub Actions provides the repository's image build/publish automation.

See the [current workflow directory](../.github/workflows/) for image-specific entry points, the shared build workflow, and upstream version checks.

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
