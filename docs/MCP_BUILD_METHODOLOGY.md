# MCP image build methodology

The MCP images built by this repository are published with the same versioned
tag in both registries:

- `ghcr.io/rcamarda390/<image>:<upstream-version>-v<revision>`
- `docker.io/rcamarda390/<image>:<upstream-version>-v<revision>`

The current images are `agentmemory-mcp`, `gnosis-mcp`, `sooperset-mcp-atlassian`,
`bifrost-mcp`, `headroom-mcp`, and `sqz-mcp`. Their metadata is human-edited
in `images/<image-dir>/image.yaml`. Published MCP builds automatically
increment and commit the image revision. When `upstream_version` changes, the
revision resets to `1`; pull request validation builds do not consume
revisions. Image-specific Docker build arguments are also defined there.

All repository images are published for `linux/amd64` only, matching the
air-gapped RHEL EC2 deployment. The shared `build-image.yml` default and
image-specific caller workflows enforce this. Do not add `arm64` or
multi-architecture publication without explicit deployment-owner approval.

`agentmemory-mcp` is built from `images/agentmemory-server/`: agentmemory and its
compatible `iii` engine binary are bundled into one image, there is no
separate `iii-engine` image or workflow. `images/agentmemory-server/image.yaml`'s
`build_args.III_VERSION` tracks the exact iii version agentmemory's own
`iii-sdk` dependency pins — it is not bumped independently just because a
newer `iii-hq/iii` release exists. See
[`images/agentmemory-server/README.md`](../images/agentmemory-server/README.md)
for the full architecture and update procedure.

The `sqz-mcp` build vendors `images/sqz-mcp/Cargo.lock` because its upstream
repository does not commit a lockfile. Regenerate that lockfile with
`cargo generate-lockfile` whenever `SQZ_VERSION` changes.

Image builds are manual: each image caller workflow is triggered with
`workflow_dispatch`, so pull requests and scheduled runs do not build or publish
images. Run the workflow for the image you want to build. `headroom-mcp` is the
one exception — it also builds on a push to `main` under
`images/headroom-mcp/**`, which matters when bumping its version (below).

`headroom-mcp` currently ships a downstream source patch for Cline's
OpenAI-compatible Bedrock transport. The main `Dockerfile` applies that patch
inside its builder stage and runs the regression suite before the finished venv
enters the runtime image. Bumping `upstream_version` therefore takes one build,
and the shared workflow resets every new upstream release to revision `v1`.
The full procedure, including how to re-verify the patch against the new release
before building, is in
[`images/headroom-mcp/CLINE_BEDROCK.md`](../images/headroom-mcp/CLINE_BEDROCK.md).

`gnosis-mcp` currently means the air-gap build: its ONNX embedding model is
pre-bundled and the image is labeled with `gnosis.airgap=true`. The air-gap
variant is not represented by a tag suffix. MCP workflows publish versioned
tags only and do not publish `latest`, `latest-airgap`, or `-build-*` tags.

Each image has an individual caller workflow. The shared
`.github/workflows/build-image.yml` workflow owns checkout, metadata parsing,
GHCR authentication with `GITHUB_TOKEN`, Docker Hub authentication with
`vars.DOCKERHUB_USERNAME` and `secrets.DOCKERHUB_TOKEN`, and dual publishing.
Image-specific smoke tests remain in the caller workflows. Gnosis candidates
are also scanned with Trivy for HIGH and CRITICAL vulnerabilities, including
unfixed findings, before any registry login or publication. Scan findings are
reported but do not block publication; external image scanning tools provide
additional security review.

The non-MCP `.github/workflows/dockerhub.yml` workflow builds the repository
root `Dockerfile` and remains outside this MCP standardization.

## Triaging scanner findings against Debian base images

Xray and Trivy report a CVE when the *package version* falls in the affected
range. Debian backports fixes without changing upstream version numbers, and it
also declines to fix issues it considers minor, so a finding needs to be checked
against the [Debian Security Tracker](https://security-tracker.debian.org/tracker/)
before it is treated as either real or false. Record the outcome in the
Dockerfile next to the package it concerns.

Three outcomes are possible, and they need different responses:

1. **Not applicable to Debian's build.** The vulnerable code is not compiled in.
   Example: `zlib1g` CVE-2023-45853 (CVSS 9.8) is MiniZip only, which Debian
   does not build in bookworm's `zlib1g`; the tracker marks it `<ignored>`.
   Nothing to do but document it — the finding is noise.
2. **Real but unfixable in this suite.** Debian marks it `<no-dsa>`
   ("Minor issue") with no fixed version, so `apt-get upgrade` can never clear
   it. Example: `libsqlite3-0` CVE-2025-7458 and `libc-bin` CVE-2026-5450, both
   of which are also still unfixed in trixie. Document the reachability
   argument; only a base-image move or a vendored build actually clears it.
3. **Genuinely fixed upstream in a newer suite.** Then it is a deliberate
   base-image decision, not a purge.

### Purging a package is a functional change, not a scanner tweak

Purging is only valid when nothing in the image uses the package. Check before
purging, and never infer it from an assumption about static linking:

    docker run --rm <base> apt-cache rdepends --installed <pkg>
    docker run --rm <base> ldd /usr/local/lib/python3.13/lib-dynload/<mod>.so

`libsqlite3-0` was purged from `headroom-mcp` on the theory that Python bundles
SQLite statically. It does not: `_sqlite3.cpython-313-*.so` links
`libsqlite3.so.0` dynamically, and the published image died at startup with
`ImportError: libsqlite3.so.0: cannot open shared object file`. The same false
premise was still recorded for `zlib1g`, which Python's `zlib` module also links
dynamically.

### Make the build fail where the mistake is made

That purge passed a build-time check of `python -c "import sys; sys.exit(0)"`,
which cannot detect a missing shared library. The runtime stage now imports the
stdlib modules whose backing libraries a purge could remove and exercises
`sqlite3` and `ssl`, so a bad purge fails in the layer that caused it instead of
surfacing later as an opaque MCP startup error. Guards must also be falsifiable:
`! command -v ncurses` never fails, because no `ncurses` binary exists in any
image — `ncurses-bin` ships `tput`, which is what the check now tests.

## Triaging scanner findings against Go binaries

Go images are scanned differently from Debian ones. Xray reads the module graph
and the compiler version out of the binary's own build info, so every entry in
`go list -m all` is a scanned component and `github.com/golang/go` — the
toolchain that compiled the binary — is one too. Bumping the builder base image
is therefore part of remediation, not housekeeping.

Three rules follow from that:

1. **Upgrade to the fix version; never downgrade.** An older release is not a
   remediated release. `bifrost-mcp` was once "fixed" by moving go-git from
   v5.19.2 to v5.12.0 and Go from 1.26.5 to 1.23.4 — every one of those moves
   walked *away* from the versions the scanner asked for, and all of it was
   reverted. Read the Fix Version column and go to it or past it.
2. **Prove the upgrade reached the binary.** `go get` sets a minimum, and
   minimal version selection may settle a module higher to satisfy another
   module's requirement — `go-openapi/spec` v0.22.9 is what drags the swag
   submodules to v0.27.3. Assert the resolved versions with `go list -m` after
   the upgrade and the stamped toolchain with `go version -m` on the built
   binary, so a pin that silently stops applying fails the build instead of
   shipping.
3. **One advisory can name more than one module.** Raising the module a finding
   is reported against does not clear the same advisory where it is reported
   against a sibling. XRAY-1032962 and XRAY-1032963 were answered on
   `go-openapi/spec` in `1.6.11-v7`; the `-v8` scan reported both again against
   `go-openapi/validate` v0.25.1, which upstream requires separately and which
   MVS therefore left untouched. After remediating, re-scan and pin whatever the
   next report names — a pin covers the module it names and nothing else.

Pins belong in the Dockerfile with the finding they answer recorded next to
them, and they come out again once upstream's own `go.mod` requires that
version or newer.
