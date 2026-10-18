<!-- File: images/slim-docker-vsix-upgrades/README.md -->
# VSIX upgrade scan artifact

New, independent image for Microsoft VS Code **1.98.2**. Original Marketplace VSIX archives and every archive member are preserved. No extension is rebuilt, installed, or remediated. Custom Cline is excluded.

| Extension | Installed | Selected stable version | VS Code engine | Platform |
|---|---|---|---|---|
| amazonwebservices.aws-toolkit-vscode | 4.10.0 | 4.17.0 | ^1.83.0 | universal |
| anthropic.claude-code | 2.1.295 | 2.1.301 | ^1.94.0 | linux-x64 |
| francescoanzalone.vsc-todo | 2.2.1 | 2.3.5 | ^1.75.0 | universal |
| esbenp.prettier-vscode | 11.0.0 | 11.0.3 | ^1.80.0 | universal |
| gitlab.gitlab-workflow | 6.64.0 | 6.92.0 | ^1.92.2 | universal |
| growthjack.claude-code-usage | 2.3.0 | 2.5.0 | ^1.74.0 | universal |
| mechatroner.rainbow-csv | 3.23.0 | 3.24.1 | ^1.95.0 | universal |
| ms-python.autopep8 | 2025.3.11811013 | 2026.4.0 | ^1.74.0 | universal |
| ms-python.debugpy | 2025.15.2025100201 | 2026.6.0 | ^1.92.0 | linux-x64 |
| ms-python.python | 2025.17.2025100201 | 2026.10.0 | ^1.95.0 | linux-x64 |
| mtxr.sqltools | 0.28.5 | 0.28.6 | ^1.78.0 | universal |
| mtxr.sqltools-driver-pg | 0.5.7 | 0.5.8 | ^1.78.0 | universal |
| redhat.vscode-yaml | 1.20.2025100808 | 2.0.0 | ^1.91.0 | universal |

## Per-extension images

The workflow's manual run has an **extension** choice. `all` builds the combined `slim-docker-vsix-upgrades` image from `image.yaml`. Any one extension builds `slim-docker-vsix-<extension-id>` (e.g. `slim-docker-vsix-gitlab.gitlab-workflow`) from `configs/<extension-id>.yaml`, tagged `<extension version>-vN`. Configs must match `extensions.json` (checked by `test-prepare.py`); update both when a pin changes. The Dockerfile takes `EXTENSION_ID` and `IMAGE_NAME` build args, set by the config. Each run's summary lists where watched npm packages (hono, MCP SDK, qs, ...) sit per VSIX.

## Provenance and validation

`extensions.json` pins official Marketplace URLs, original VSIX SHA-256 values, verified manifest engine requirements, platforms and verification dates. Microsoft Marketplace packages were downloaded and their ZIP and package manifests inspected on 2026-10-14 (unchanged pins) and 2026-10-18 (updated pins). All selected engine ranges permit 1.98.2 using npm semver. Linux x64 is selected where the retrieved artifact is platform-specific. These are verified upgrade candidates, not a claim that each is the newest compatible release. Native binary execution/AL2 glibc compatibility is outside the scan-artifact acceptance test.

Builder validates archive identity, platform, stable channel, checksum and engine, rejects unsafe/duplicate archive paths and verifies every extracted file byte-for-byte. Tests cover traversal, absolute paths, symlinks, path conflicts, hidden files, bundled dependencies and empty directories. Final image checks repeat checksums and inventory validation after Docker extraction.

Payload layout:

- `/slim/payload/vsix/`: complete original VSIX archives.
- `/slim/payload/unpacked/<id>-<version>/`: complete expanded archives.
- `/slim/manifest.json`: inventory and package provenance.
- `/slim/metadata/`: compatibility, provenance, checksums, per-file hashes and coverage.
- `/slim/sbom/`: combined and per-extension CycloneDX 1.5 JSON.

SBOM component versions come from physically present package manifests. Declared dependency ranges remain separately recorded, not fabricated resolved versions. Bundled/minified code and native binaries can contain additional components. No missing lockfiles are invented. Checksum files are verified from `/slim`. Final stage is `scratch`, with no tools, ports or runtime.

## Build and publication

```bash
python3 images/slim-docker-vsix-upgrades/test-prepare.py
docker build --build-arg IMAGE_VERSION=2026.10.18 -t slim-docker-vsix-upgrades:validation images/slim-docker-vsix-upgrades
```

Run **Build and publish slim VSIX upgrades for VS Code 1.98.2** manually after workflow registration on the default branch. PRs validate without publishing. The existing reusable build workflow owns build, advisory Trivy scanning and GHCR and Docker Hub publication. `latest` is disabled. Images are `ghcr.io/rcamarda390/slim-docker-vsix-upgrades` and `docker.io/<DOCKERHUB_USERNAME>/slim-docker-vsix-upgrades` (always include the registry host when pulling). Tags use `2026.10.18-vN`; manual workflow run number plus configured revision guarantees unique revisions. The evidence job records the exact pulled registry digest and uploads metadata/SBOM/checksum evidence. Actual published tag and digest are available in its summary; do not infer them from configured revision.

```bash
mkdir -p /tmp/.vsix
cid=$(docker create slim-docker-vsix-upgrades:validation /unused)
docker cp "$cid:/slim/payload/vsix/." /tmp/.vsix/
docker rm "$cid"
find /tmp/.vsix -type f -name '*.vsix'
```

For a published image, pull the exact reference from the Actions summary and use that reference with `docker create`. Expanded trees can similarly be copied from `/slim/payload/unpacked/.`.

## Xray acceptance and future remediation

Xray is not accessible from this build environment. Scan completion, component detection and vulnerability clearance remain **unverified** until the user's Artifactory scan is supplied. Trivy is advisory and does not establish Xray clearance.

First user-side acceptance step: import the exact published tag/digest into the existing Artifactory scan process. Then inspect detected components and paths against per-extension package inventories and SBOM counts. Record digest, component counts, missing components and vulnerability component/path/version. Zero findings do not prove complete coverage. Embedded SBOM ingestion depends on the deployed Xray configuration.

For future findings, use the repository remediation process and ledger; keep original archives and bundled dependencies intact. Remediation through a modified VSIX requires a separately authorized source rebuild/repack and explicit provenance rather than overwriting official packages.

