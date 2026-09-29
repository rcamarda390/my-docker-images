# fib_docker Agent Instructions

> [!IMPORTANT]
> This is the authoritative repository-wide AI agent instruction document.
>
> `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md` are discovery/adaptor files only.
> Do not duplicate repository policy in agent-specific files. Update this document instead.

Repository: `https://github.com/rcamarda390/fib_docker`

## Purpose

This repository builds, validates, scans, and publishes reproducible Docker images for connected-build and restricted-runtime environments.

The target runtime may be air-gapped or tightly network-controlled. Docker is available on the Linux host, but host-level software installation should not be assumed or required.

The permanent artifact is the image build itself. Interactive changes inside a running container are diagnostic only.

## Mandatory preflight

Before changing anything:

1. Start from the current default branch, normally `main`.
2. Inspect the target image directory:
   - `images/<target>/Dockerfile`
   - `images/<target>/image.yaml`
   - entrypoint/start scripts
   - checked-in patch files
   - target-specific README/docs
3. Inspect the target workflow: `.github/workflows/build-<target>.yml`.
4. Inspect the shared workflow: `.github/workflows/build-image.yml`.
5. Review this document, `docs/MCP_BUILD_METHODOLOGY.md`, and relevant image-specific documentation. Use `docs/PROJECT_URLS.md` for upstream and release/package URLs when identifying sources or checking all images for updates; documentation links are listed where available.
6. Check recent commits and PRs for the same image before inventing a new pattern.
7. Do not overwrite or revert unrelated work.

Do not assume all images use identical build, scan, smoke-test, or revision behavior. Read the actual caller workflow first.

## GitHub access

For work in `github.com/rcamarda390`, use the configured ChatGPT Work **GitHub plugin** as the primary repository interface.

- Use it to inspect repositories, files, branches, pull requests, Actions, issues, and reviews.
- Use its branch, file-update, commit, pull-request, and workflow controls for repository changes and builds.
- Do not substitute unauthenticated Git CLI access or browser editing when the plugin is available.
- If the plugin is unavailable, disconnected, or lacks a required capability, report that specific blocker before using another access method.

## Branch and pull request rules

Do not make feature or remediation changes directly on `main`.

Use a dedicated feature/fix branch and a non-draft PR targeting `main`. Keep changes surgical.

PR descriptions must include:

- problem being solved;
- image or area affected;
- upstream version when applicable;
- exact remediation/change;
- validation performed;
- security findings addressed;
- remaining limitations or blockers;
- agent that performed the work;
- LLM/model used when available.

Do not create a second overlapping workflow to build or publish an image when an existing image-specific workflow already owns that responsibility.

## `image.yaml` is the release source of truth

Each image's `images/<target>/image.yaml` defines release metadata.

Typical structure:

```yaml
name: example-mcp
upstream_version: 1.2.3
revision: 4
build_args:
  EXAMPLE_COMMIT: abcdef...
publish:
  ghcr: true
  dockerhub: true
  latest: false
```

Rules:

- Preserve the image name unless explicitly asked to rename it.
- Preserve registry publication behavior unless explicitly asked to change it.
- MCP images use immutable explicit tags: `<upstream_version>-v<revision>`.
- Do not publish `latest` for MCP images unless repository policy is explicitly changed.
- New upstream releases normally restart the local image revision at `v1`.
- Security/package/build-only changes on the same upstream release increment the local `vN`.

### Revision behavior is workflow-specific

Do not assume how the next revision is calculated.

The repository has more than one revision strategy, including:

- automatic revision increment followed by a revision PR;
- revision derived from already-published tags;
- configured revision used as a floor.

Inspect the target image caller workflow and shared `build-image.yml` before editing `revision:`.

Never overwrite an existing immutable published tag.

## Upstream version changes

When asked to build a new upstream version:

1. Verify the upstream release/tag exists.
2. Inspect upstream release notes and dependency/lockfile changes.
3. Update `upstream_version`.
4. Update any exact upstream commit pin used by the image.
5. Update target-specific build arguments required by the new release.
6. Remove obsolete downstream dependency overrides when upstream now contains the fix.
7. Revalidate every downstream patch against the new upstream source.
8. Follow the image's existing revision-reset behavior so the first published local build is `v1`.

Do not carry old patches, pins, or workarounds forward blindly.

## Permanent fix rule

A successful interactive edit inside a running container is not the finished solution.

Temporary container modifications may be used to prove a diagnosis. The final correction must normally be represented in source control through one or more of:

- `Dockerfile`;
- entrypoint/start script;
- checked-in patch script;
- dependency/package pin;
- source patch;
- image-specific configuration;
- build-time assertion;
- GitHub Actions workflow.

After converting a diagnostic fix into the build, rebuild from a clean image and retest.

## Xray / Trivy security remediation

Security remediation means moving the vulnerable component to the scanner's stated fixed version or newer while preserving application functionality.

Do not silence, hide, suppress, or cosmetically remove findings merely to produce a clean report. Do not downgrade a dependency and call it remediated.

For every HIGH/CRITICAL finding supplied by the user:

1. Record component/package/module, installed version, fix version, and CVE/Xray advisory.
2. Determine where the component enters the image: base image, OS package, Python package, Go module/toolchain, Rust crate, Node package, vendored binary, or upstream source dependency.
3. Update to the fix version or newer.
4. Prove the corrected version is actually present in the final image or binary.
5. Rebuild.
6. Re-scan.
7. Repeat for findings that remain or move to sibling/transitive dependencies.

A successful build does not prove security remediation succeeded.

### No-fix findings: conditional removal of unused components

If the scanner, distribution tracker, or upstream project provides no usable fix,
removal is allowed only when the vulnerable component is proven unnecessary in the
**final runtime image**. This is a functional change, not a scanner workaround.

Before removing it, perform and record an image-specific usage analysis:

1. Trace how the component enters the final stage and whether it is needed only by
   the builder. Keep builder-only tools in the builder; do not remove a runtime
   dependency just because the application source does not call its CLI.
2. Deep-dive the target application's checked-in and upstream source, startup and
   entrypoint scripts, Dockerfile stages, build scripts, configuration, and tests
   for direct invocation, process spawning, plugin loading, dynamic imports, or
   bundled-binary use. For a command such as `tar`, search for both the command
   and its common aliases/wrappers.
3. Prove the installed dependency closure does not require it. Use the native
   package manager's installed reverse-dependency query and inspect executable or
   extension shared-library links where applicable. Do not infer static linking.
4. If the evidence is incomplete or any supported runtime path needs the
   component, do not remove it. Document the no-fix/reachability result and
   escalate a base-image, upstream, or product decision instead.

Remove the package in the final image stage after its last required package
installation. Add a falsifiable build-time assertion that the package is absent
from the final package database and that its executable/library is absent. Then
run the target's normal smoke/runtime validation and re-scan the rebuilt image.

For example, removal of an unused Debian `tar` package requires all of: source
analysis showing no supported runtime use; installed reverse-dependency and
dynamic-link checks; `dpkg --purge tar` in the final stage; assertions such as
`! dpkg-query -W tar` and `! command -v tar`; a passing runtime smoke test; and
a new Xray/Trivy result. Do not treat any single one of those checks as proof.

## Debian / Ubuntu base-image findings

Before remediation, determine whether a Debian-family finding is:

1. fixed by a newer package in the same suite;
2. fixed only in a newer suite;
3. marked `no-dsa` or otherwise not scheduled for a security update;
4. ignored because the vulnerable feature is not built/applicable;
5. still genuinely unfixed and reachable.

Do not purge libraries merely to satisfy a scanner.

Before removing a package, prove the application does not dynamically depend on it. Useful checks include:

```bash
apt-cache rdepends --installed <package>
ldd <binary-or-python-extension>
```

Past project experience proved assumptions about Python statically bundling libraries can be wrong. If removal could affect a runtime library, add a build-time import or execution test proving the resulting runtime works.

## Go security remediation

For Go-built images, Xray can identify vulnerabilities from modules recorded in binary build info and from the Go compiler/toolchain itself.

Rules:

1. Upgrade to the scanner fix version or newer.
2. Never remediate by downgrading to an older release.
3. Inspect the resolved module graph with `go list -m all`.
4. Prove important modules with `go list -m <module>`.
5. Prove final binary module/toolchain versions with `go version -m <binary>`.
6. Remember one advisory may be reported against several sibling modules.
7. Re-scan the image before concluding remediation is complete.
8. Document temporary downstream Go pins next to the finding they remediate and remove them once upstream requires an adequate version.

Bifrost is the precedent for this process.

## Build-time assertions

When a security or compatibility fix depends on a particular resolved version, make the build prove it.

Examples:

- assert a Go module version;
- assert the Go toolchain version;
- import Python modules whose shared libraries could have been affected;
- execute a small deterministic command;
- validate a patch changed the expected upstream code;
- verify an upstream tag maps to the pinned commit;
- verify required model/dependency files are baked into an air-gap image.

Prefer failures during `docker build` to delayed failures after publication. Tests must be falsifiable.

## Validation layers

Validate at the smallest useful layer first.

### Build validation

Confirm:

- Docker build succeeds;
- expected dependency versions are present;
- downstream patches apply;
- no unexpected runtime package download is required.

### Image smoke validation

Use the target image's existing smoke mechanism where available. The shared workflow supports direct smoke commands, health checks, bounded timeouts, and Trivy scans.

Do not weaken an existing smoke test to get a build green.

### Application validation

A health endpoint alone is not sufficient evidence an MCP service is usable.

Where practical, validate:

1. container starts;
2. readiness/health works;
3. MCP transport initializes;
4. JSON-RPC initialization succeeds;
5. one small deterministic tool/resource request succeeds;
6. dependent service connectivity works when required.

For multi-hop systems such as:

```text
Cline
  ↓
Bifrost
  ↓
Headroom
  ↓
LiteLLM
  ↓
AWS Bedrock
```

test each layer directly before changing multiple layers. Do not re-debug conclusively proven lower layers unless new evidence invalidates the prior proof.

## Air-gap requirements

Images intended for restricted environments should be self-contained where practical.

At runtime:

- do not assume public package repositories are reachable;
- do not download dependencies that can be baked into the image;
- do not download embedding/model artifacts that can be baked into the image;
- preserve only external connectivity the application actually requires;
- keep persistent state outside disposable container layers;
- obtain AWS credentials from runtime IAM/environment, never from files copied into the image.

A service requiring AWS Bedrock connectivity is not fully offline. Do not enable a global offline mode when it would disable required Bedrock connectivity.

## Secrets

Never commit AWS keys, API tokens, PATs, registry passwords, Bifrost virtual-key secrets, private certificates, or environment-specific credentials.

Use IAM roles, GitHub Actions secrets, runtime environment variables, secret mounts, or approved enterprise secret-management mechanisms.

## Image-specific guidance

Always inspect current files because versions change.

### Bifrost MCP — `images/bifrost-mcp/`

- Prefer upstream-compatible source/dependency state.
- Pin the exact upstream commit when the manifest/workflow expects it.
- Verify the upstream tag corresponds to that commit.
- Treat Go modules and the Go toolchain as part of Xray remediation.
- Prove resolved dependency versions in the built binary.
- Follow the caller workflow's published-tag-based revision logic.
- Do not recreate dependency downgrades that move away from scanner fix versions.

### Headroom MCP — `images/headroom-mcp/`

This image has downstream compatibility/security carries.

Before bumping upstream Headroom:

- inspect `CLINE_BEDROCK.md`;
- revalidate the Bedrock/Cline patch;
- preserve required Bedrock dependency extras;
- preserve AWS runtime connectivity;
- update downstream LiteLLM/security pins only when still required;
- verify custom Debian/glibc backports remain necessary and internally consistent;
- run the Headroom smoke command and security scan.

Temporary Headroom edits proven in a running container must be folded back into the build.

### Gnosis MCP — `images/gnosis-mcp/`

- Preserve the air-gap design.
- Bundle required embedding/tokenizer/model artifacts during build.
- Validate with offline environment settings.
- Preserve persistent `/data` behavior.
- Keep its blocking security scan as an actual release gate when configured.
- Revalidate upstream Streamable HTTP / REST lifespan handling on every Gnosis
  upgrade. Keep a local patch only if the selected upstream release regresses
  the combined lifespan behavior.

### Sooperset MCP Atlassian — `images/sooperset-mcp-atlassian/`

Past successful Xray remediation is precedent: apply scanner fix versions in the image build, rebuild, then verify with a new scan.

### SQZ MCP — `images/sqz-mcp/`

- Preserve the exact upstream commit pin.
- The repository vendors `Cargo.lock` because upstream does not.
- Regenerate the vendored lockfile when the upstream SQZ version changes.
- Do not leave an old lockfile attached to a new upstream source version.

### AgentMemory — `images/agentmemory-server/`

Architecture is intentionally one self-contained server image containing AgentMemory and the compatible iii engine.

Do not introduce a separate iii-engine image/container unless explicitly requested.

`III_VERSION` must match the iii version required by AgentMemory's compatible SDK/dependency relationship, not simply the newest available iii release.

Persistent application state belongs outside the disposable container filesystem.

## GitHub Actions rules

The normal design is:

```text
image-specific caller workflow
          ↓
.github/workflows/build-image.yml
          ↓
build candidate
          ↓
smoke test / health validation
          ↓
security scan where configured
          ↓
registry login
          ↓
publish immutable tag
```

Preserve this separation.

### Image platform policy

All images published by this repository must target `linux/amd64`. This matches the air-gapped RHEL EC2 deployment and prevents unnecessary multi-architecture manifest lists.

The shared `.github/workflows/build-image.yml` default and every image-specific caller workflow must use `linux/amd64`. Do not add `arm64` or multi-architecture publication unless the deployment owner explicitly approves a documented exception.

Do not duplicate shared build logic without need, create competing publish workflows, publish before validation, hide scanner output, disable a blocking scan merely to pass, or expand scope into unrelated CI hardening unless requested.

## Failed build handling

If a GitHub Actions build fails:

1. inspect the actual failing step and log;
2. identify the first meaningful error, not a later cascading error;
3. modify source/build/workflow;
4. push to the same working branch/PR where practical;
5. rerun;
6. continue until successful or a real external blocker is proven.

Do not create multiple speculative workflows. Do not report success merely because a PR merged; verify the requested image workflow and artifact.

## Xray follow-up loop

When the user provides another Xray report after a build:

1. compare it with the previous report;
2. determine which findings were cleared;
3. identify findings that moved to sibling/transitive dependencies;
4. apply current fix versions;
5. rebuild as the next local revision;
6. publish through the normal workflow;
7. verify the new artifact.

A clean Xray result is stronger evidence than a successful Docker build. Bifrost and Sooperset remediation history are precedent for this iterative process.

## Avoid unrequested scope expansion

Unless explicitly requested or necessary for remediation, avoid adding:

- multi-architecture support;
- new signing systems;
- new SBOM/provenance mechanisms;
- new Dependabot ecosystems;
- broad base-image replacements;
- unrelated non-root conversions;
- unrelated action pinning;
- unrelated workflow rewrites.

Make the smallest reliable change that solves the actual problem.

## Completion criteria

An image change is complete only when applicable items are satisfied:

- target files and existing workflow inspected;
- change exists in source control, not only a live container;
- upstream version/commit relationship correct;
- `image.yaml` correct;
- requested security fix versions present or exceeded;
- build-time assertions prove important dependency resolutions;
- Docker build succeeds;
- smoke/runtime validation succeeds;
- Trivy/Xray findings addressed according to the task;
- feature/fix branch pushed;
- PR targets `main`;
- requested image workflow succeeds;
- exact published image tag identified;
- no secrets committed;
- operational documentation updated when behavior changed.

## Final agent report

When work is complete, report concisely:

```text
Image:
Upstream version:
Published tag:
PR:
GitHub Action:
Security remediation:
Validation:
Remaining findings/blockers:
Agent:
LLM/model:
```

Include clickable GitHub links for the PR and workflow run when available.

## Governing principle

For `fib_docker`, the correct fix is reproducible, reviewable, security-verifiable, and suitable for rebuilding from scratch.

Diagnose in a running container if useful.

Ship the fix in the image build.
