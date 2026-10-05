# AI CLI runner image

[Image source](../../images/ai-cli-runner/) · [image.yaml](../../images/ai-cli-runner/image.yaml)

GitLab CI job image with the Claude Code and Cline CLIs, for the air-gapped
RHEL EC2 runners. Not an MCP server; there is no service or health endpoint.

## Contents

- Chainguard Wolfi runtime (glibc, same digest as litellm; Debian slim failed the Trivy gate on unfixed base-package CVEs), digest-pinned Node builder stage, `linux/amd64`.
- `claude` and `cline`: self-contained glibc executables from the pinned npm
  platform packages. No Node.js or npm in the final image (asserted at build).
- `git`, `ca-certificates`, `bash`, and the base's busybox.
- Alpine is not used: both CLI binaries require glibc.

## Tag

`<upstream_version>-v<revision>`, e.g. `claude2.1.289-cline3.0.68-v1`.
`revision` resets to `v1` per version pair and is derived from published
Docker Hub tags. Published to GHCR and Docker Hub only; mirror to Artifactory
manually. No `latest`.

## Runtime configuration

Baked defaults: `CLAUDE_CODE_USE_BEDROCK=1`, autoupdate, telemetry and
non-essential traffic disabled, `DO_NOT_TRACK=1`.

Supplied by the GitLab job, never baked in: `AWS_REGION`, AWS credentials or
role/ARN (instance role, `AWS_ROLE_ARN`, etc.), and Bedrock model IDs. Cline
Bedrock/provider settings are likewise runtime configuration.

GitLab: set `entrypoint: [""]` if the runner overrides it. The image runs as
root by default (needed for the docker executor's build volumes); a `runner`
user (uid 1000) exists for jobs that set `user:`.

## Version bumps

- `check-ai-cli-versions.yml` runs weekly, compares npm `latest` for both
  packages, and opens a PR editing `image.yaml`, `package.json`, and
  `package-lock.json`.
- Merge, then dispatch **Build and publish AI CLI runner image**.
- Manual bump: edit the three versions in `image.yaml`, run in the image dir
  `npm pkg set` for both deps and `npm install --package-lock-only --ignore-scripts`.
  The build fails if the lockfile and `image.yaml` disagree.

## Validation

Build asserts versions, runs both CLIs, and checks Node/npm are absent. CI
smoke-tests with networking disabled and Trivy blocks publication on
HIGH/CRITICAL. Run Xray on the published tag before relying on it.
