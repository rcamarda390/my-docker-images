<!-- README.md: Zeus software image documentation. -->
# zeus-dev-image

Public software base for the internal Zeus developer image. GitHub Actions builds
this image from public upstream sources. After import and Xray approval, the
internal Dockerfile uses this image as its `FROM` and adds local users, groups,
site configuration, mounts, and startup behavior. Xray scans this published base
image; it does not scan the downstream image.

The build does not use separately transferred `files/` or `preload/` artifacts.

## Software

Edit [software.yaml](software.yaml) to request additions, removals, or version changes.
An agent then updates the Dockerfile and validates the resulting image. The catalog
records the current direct software choices and sources; it is not executed by
Docker and does not prove a build has passed.

- Base: UBI 10 with Python 3.12 from UBI AppStream
- Node.js 22 and PostgreSQL 15 client
- Docker Compose 5.6.0 official binary, checksum-verified with Go 1.26.8 and containerd 2.4.1
- Docker CLI with `docker exec` for use through the host daemon; Buildx is excluded
- `xdg-user-dir` from pinned xdg-user-dirs commit `cd05b6d29da1abdb3cd253ef496ae7fd1593e4bb`
- Apache Airflow 3.3.2 with Python 3.12 constraints and the selected providers
- AWS CLI 1.46.1, boto3/botocore 1.43.75
- AgentMemory CLI and MCP package 0.9.29, with OpenTelemetry 2.9.0 security overrides and the tested iii-sdk compatibility patch
- Bifrost CLI 0.10.6, installed and built from the same pinned source using Go 1.26.6
- Cline CLI 3.0.61 with undici 6.28.1, and Claude Code CLI 2.1.260
- SQLFluff 4.2.0 and the Python data/development packages in the Dockerfile, including security-pinned msgpack 1.2.3 and setuptools 84.0.0
- Security pins: urllib3 2.8.0 (main Python and AWS CLI), PyJWT 2.15.0, Mako 1.4.2, Werkzeug 3.1.9
- GitLab MCP SDK 1.31.0 and axios 1.20.0; Cline/AgentMemory overrides cover nested security dependencies; a narrow Cline import patch preserves compatibility with simple-git 4
- pip 26.2.1 for developer package management and the AWS CLI virtual environment, with vendored urllib3 upgraded to 2.8.0 and pip compatibility patches retained
- TypeScript 6.0.3 for the GitLab MCP dependencies
- Archify 2.17.0-dev.1 from pinned commit `06dd052602dd9a369e4d034e24faef0917b5a60c`
- GitLab MCP Node dependencies under `/opt/gitlab-mcp-server/node_modules`
- OS utilities and optional convenience tools in the Dockerfile

pip also bundles separate, older copies of msgpack and part of setuptools.
[The scoped OpenVEX assessment](pip-vendored.openvex.json) classifies three
findings against that bundle as not affected: pip does not use msgpack's
vulnerable Unpacker path, and its setuptools subset has no vulnerable
PackageIndex or jaraco.context tarball extraction code. This covers
CVE-2025-47273, CVE-2026-23949, and the msgpack advisory
GHSA-6v7p-g79w-8964 (reported by Xray as CVE-2026-57585).
Trivy displays matching assessments in its suppressed section.
Only pip's urllib3 subtree is upgraded to 2.8.0, retaining pip's vendoring patches;
its SBOM and installation record reflect the actual replacement code. The
verification script checks the assessed components in both the main
interpreter and AWS CLI venv, verifies the vulnerable setuptools files are
absent, and exercises pip cache serialization through pure-Python msgpack. The
standalone Python packages remain at their fixed versions. This assessment
applies to the Trivy PR scan; internal Xray review remains separate.

SQZ and the Cline VS Code extension are excluded.

vi and Vim are excluded, including inherited Vim RPMs. Use VS Code for editing
or install an approved editor in the downstream internal image.

This image has no internal user roster, site wrappers, custom shell prompt,
host-specific directories, or entrypoint. Its installation check fails the
build when required software is missing. The downstream build must add its
own site configuration and verify the final image separately.

## Build and release

Dispatch `.github/workflows/build-zeus-dev-image.yml`. It builds, verifies,
scans with Trivy, and publishes the image using the version from `image.yaml`
and the next revision derived from successfully published Docker Hub tags.
Publications are serialized; failed builds consume no revision and no revision
PR is created. Pull requests build and scan without publishing.
Import the exact published image for internal Xray scanning.

The software versions listed above describe the current image. A separate
version review and compatibility test is required before upgrading them.

## Bifrost CLI

Run `bifrost` in an interactive VS Code terminal. It launches the **Claude Code
CLI** already installed in Zeus through your existing Bifrost gateway; it does
not configure the Cline VS Code extension. Choose the reachable gateway URL,
virtual key (if required), and model at runtime. Gateway/Bedrock credentials
are not baked into the image. Other supported agents (Codex, Gemini, OpenCode)
are not dependencies and are not added by this change; installing them from
the chooser requires npm connectivity.

The CLI is now compiled from the previously verified upstream commit using Go
1.26.6. This preserves CLI 0.10.6 while addressing the Go compiler findings.
The builder runs upstream tests and records `go version -m` output and a checksum;
only the static linux/amd64 binary and verification metadata enter the final image.

Virtual-key persistence uses Linux Secret Service over a user D-Bus session.
An unlocked keyring (such as GNOME Keyring) and accessible session bus must be
provided/configured in the downstream runtime if persistence is required.
Installing a keyring package alone does not establish that session. Without
it, upstream warns and requires the key again next session. Never put the key
in the image or config file. Keep the user's `.bifrost` state in persistent
storage. `BIFROST_NO_UPDATE_CHECK=1` disables upstream public update checks
using its supported environment switch. Deliver updates by rebuilding the image.

Source inspection matched the binary's embedded commit
[`a0d7aaf`](https://github.com/maximhq/bifrost/tree/a0d7aafab999509121154452e455d970ae2572b4/cli).
The source-build checksum is checked during build and smoke validation.
A live gateway/Bedrock session must be tested in the deployment environment.

## Xray follow-up

The October 2 report omits installed versions, component paths and image digest.
The build verifies fixed Python/npm versions, including nested npm copies and the
AWS CLI venv, and refreshes RPM packages after installation. The Bifrost toolchain
fix covers that binary; Docker Compose is upgraded to its official fixed release with containerd 2.4.1.
Any remaining Go/containerd findings still require attribution to their actual binary. node-forge 1.4.0 carries the nested DigestAlgorithm validation fix proposed in
upstream PR #1152 for CVE-2026-85393. Its regression rejects malformed signatures
and verifies valid ones during build/smoke. The upstream package version remains
1.4.0, so scanners can still report it; this is a tested backport, not a released
package upgrade. Unfixed RPMs remain subject to the rebuilt image's scan. Required developer tools are retained.
