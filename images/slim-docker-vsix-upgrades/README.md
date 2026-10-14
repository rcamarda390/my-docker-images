<!-- File: images/slim-docker-vsix-upgrades/README.md -->
# slim-docker-vsix-upgrades

Scan-only image: original Marketplace VSIX files + fully unpacked trees + SBOMs for Artifactory Xray.
Target VS Code **1.98.2**. Image: `ghcr.io/rcamarda390/slim-docker-vsix-upgrades:<upstream>-v<rev>` (no `latest`).
Do NOT install anything on the VS Code host from this build.

## Extensions (candidates; `extensions.json` is the pin list)

| Extension | Installed | New | Source | VSIX SHA-256 |
|---|---|---|---|---|
| `amazonwebservices.aws-toolkit-vscode` | 4.10.0 | 4.17.0 | Marketplace | PENDING (build records sha256) |
| `anthropic.claude-code` | 2.1.295 | 2.1.299 | Marketplace | PENDING (build records sha256) |
| `francescoanzalone.vsc-todo` | 2.2.1 | 2.3.5 | Marketplace | PENDING (build records sha256) |
| `esbenp.prettier-vscode` | 11.0.0 | 11.0.3 | Marketplace | PENDING (build records sha256) |
| `gitlab.gitlab-workflow` | 6.64.0 | 6.92.0 | Marketplace | PENDING (build records sha256) |
| `growthjack.claude-code-usage` | 2.3.0 | 2.4.1 | Marketplace | PENDING (build records sha256) |
| `mechatroner.rainbow-csv` | 3.23.0 | 3.24.1 | Marketplace | PENDING (build records sha256) |
| `ms-python.autopep8` | 2025.3.11811013 | 2026.4.0 | Marketplace | PENDING (build records sha256) |
| `ms-python.debugpy` | 2025.15.2025100201 | 2026.6.0 | Marketplace | PENDING (build records sha256) |
| `ms-python.python` | 2025.17.2025100201 | 2026.4.0 | Marketplace | PENDING (build records sha256) |
| `mtxr.sqltools` | 0.28.5 | 0.28.6 | Marketplace | PENDING (build records sha256) |
| `mtxr.sqltools-driver-pg` | 0.5.7 | 0.5.8 | Marketplace | PENDING (build records sha256) |
| `redhat.vscode-yaml` | 1.20.2025100808 | 1.25.0 | Marketplace | PENDING (build records sha256) |

Pre-build evidence (Marketplace `Microsoft.VisualStudio.Code.Manifest`, 2026-10-14, read via Firecrawl; VSIX bytes not yet downloaded):

| Extension | engines.vscode | allows 1.98.2 |
|---|---|---|
| `amazonwebservices.aws-toolkit-vscode` | `^1.83.0` | yes |
| `anthropic.claude-code` | `^1.94.0` | yes |
| `francescoanzalone.vsc-todo` | `^1.75.0` | yes |
| `esbenp.prettier-vscode` | `^1.80.0` | yes |
| `gitlab.gitlab-workflow` | `^1.92.2` | yes |
| `growthjack.claude-code-usage` | `^1.74.0` | yes |
| `mechatroner.rainbow-csv` | `^1.95.0` | yes |
| `ms-python.autopep8` | `^1.74.0` | yes |
| `ms-python.debugpy` | `^1.92.0` | yes |
| `ms-python.python` | `^1.95.0` | yes |
| `mtxr.sqltools` | `^1.78.0` | yes |
| `mtxr.sqltools-driver-pg` | `^1.78.0` | yes |
| `redhat.vscode-yaml` | `^1.90.0` | yes |

Note: `ms-python.autopep8` manifest has `preview: true` (Marketplace badge); pre-release channel flag was not read here. Build checks the VSIX `PreRelease` property and fails if set.

Excluded: `saoudrizwan.claude-dev` (custom fork), `ms-python.vscode-pylance`, `oracle.sql-developer`, `atlassian.atlascode`, all others without a verified candidate.

Compatibility: `engines.vscode` checked pre-build against Marketplace manifests (see PR) and re-checked in `prepare.py` (npm-semver subset, tested in `test-prepare.py`). Pre-release packages are rejected from the VSIX manifest.

## Build

Workflow `build-slim-docker-vsix-upgrades.yml` (manual dispatch publishes; PRs build + scan only).
Local: `docker build --build-arg VSCODE_TARGET_VERSION=1.98.2 images/slim-docker-vsix-upgrades`

## Xray procedure

Pull via Artifactory, wait for scan, compare components under `/slim/payload/unpacked/*`. Record: scan completed, components recognised, vulns (path + version), zero-vuln is NOT proof of coverage. Remediation: bump version in `extensions.json` (check engines), never edit payload.

## Known limits

SBOM lists only package.json manifests inside VSIX; bundled/minified deps unlisted. No Syft. Hashes recorded at build time, not pinned. Platform: tries `linux-x64`, else universal; actual value in `manifest.json`.
