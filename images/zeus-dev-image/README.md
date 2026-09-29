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
- `xdg-user-dir` from pinned xdg-user-dirs commit `cd05b6d29da1abdb3cd253ef496ae7fd1593e4bb`
- Apache Airflow 3.3.2 with Python 3.12 constraints and the selected providers
- AWS CLI 1.45.12, boto3/botocore 1.43.54
- AgentMemory and MCP package 0.9.29
- Cline CLI 3.0.61 and Claude Code CLI 2.1.252
- SQLFluff 4.1.0 and the Python data/development packages in the Dockerfile
- Archify 2.17.0-dev.1 from pinned commit `06dd052602dd9a369e4d034e24faef0917b5a60c`
- GitLab MCP Node dependencies under `/opt/gitlab-mcp-server/node_modules`
- OS utilities and optional convenience tools in the Dockerfile

SQZ and the Cline VS Code extension are excluded.

This image has no internal user roster, site wrappers, custom shell prompt,
host-specific directories, or entrypoint. Its installation check fails the
build when required software is missing. The downstream build must add its
own site configuration and verify the final image separately.

## Build and release

Dispatch `.github/workflows/build-zeus-dev-image.yml`. It builds, verifies,
scans with Trivy, and publishes the image using the version and revision from
`image.yaml`. The workflow automatically proposes the next revision after
publication. Import the exact published image for internal Xray scanning.

The software versions listed above describe the current image. A separate
version review and compatibility test is required before upgrading them.
