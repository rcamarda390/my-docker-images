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
- Docker CLI with `docker exec` for use through the host daemon; Buildx is excluded
- `xdg-user-dir` from pinned xdg-user-dirs commit `cd05b6d29da1abdb3cd253ef496ae7fd1593e4bb`
- Apache Airflow 3.3.2 with Python 3.12 constraints and the selected providers
- AWS CLI 1.46.1, boto3/botocore 1.43.75
- AgentMemory CLI and MCP package 0.9.29, with OpenTelemetry 2.9.0 security overrides and the tested iii-sdk compatibility patch
- Bifrost CLI 0.10.6, installed and checksum-verified during the connected build
- Cline CLI 3.0.61 with undici 6.28.1, and Claude Code CLI 2.1.252
- SQLFluff 4.2.0 and the Python data/development packages in the Dockerfile, including security-pinned msgpack 1.2.2 and setuptools 84.0.0
- pip 26.2.1 for developer package management
- TypeScript 6.0.3 for the GitLab MCP dependencies
- Archify 2.17.0-dev.1 from pinned commit `06dd052602dd9a369e4d034e24faef0917b5a60c`
- GitLab MCP Node dependencies under `/opt/gitlab-mcp-server/node_modules`
- OS utilities and optional convenience tools in the Dockerfile

pip also bundles separate, older copies of msgpack and part of setuptools.
[The scoped OpenVEX assessment](pip-vendored.openvex.json) classifies two
findings against that bundle as not affected: pip does not use msgpack's
vulnerable Unpacker path, and its setuptools subset has no vulnerable
PackageIndex code. Trivy still displays both in its suppressed section.
The verification script pins and checks the assessed pip bundle, while the
standalone Python packages remain at their fixed versions. This assessment
applies to the Trivy PR scan; internal Xray review remains separate.

SQZ and the Cline VS Code extension are excluded.

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

The [documented npm command](https://docs.getbifrost.ai/quickstart/cli/getting-started)
is an installer. The npm wrapper version (1.0.1) differs from the actual CLI
version (0.10.6). The Dockerfile runs the pinned installer at build time, checks
the pinned SHA-256, and copies the static linux/amd64 binary to the system PATH.
Node 22/npm, Git, and Claude CLI are already present; no additional shared
libraries are required by the static binary. The attached air-gap tarball recipe
for npm binary packages would only package the downloader, so it is not used.

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
The upstream checksum was independently retrieved from the versioned download
URL. Build/smoke checks verify the exact installed bytes and help command;
a live gateway/Bedrock session must be tested in the deployment environment.
