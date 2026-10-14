<!-- File: images/slim-docker-vsix-upgrades/README.md -->
# slim-docker-vsix-upgrades

Scan-only image: original Marketplace VSIX files + fully unpacked trees + SBOMs for Artifactory Xray.
Target VS Code **1.98.2**. Image: `ghcr.io/rcamarda390/slim-docker-vsix-upgrades:<upstream>-v<rev>` (no `latest`).
Do NOT install anything on the VS Code host from this build.

## Extensions (candidates; `extensions.json` is the pin list)

| Extension | Installed | New | Source | VSIX SHA-256 |
|---|---|---|---|---|
| `amazonwebservices.aws-toolkit-vscode` | 4.10.0 | 4.17.0 | Marketplace | `fbfe4262a7e41c01cfc1625806fc8592fee5bc5f542dee97a5981e45c1372b0b` |
| `anthropic.claude-code` | 2.1.295 | 2.1.299 | Marketplace | `c4776f521668113527622a689e6f03ce2a677791eef39787996f7a9316c343d4` |
| `francescoanzalone.vsc-todo` | 2.2.1 | 2.3.5 | Marketplace | `ee63b39f453324a08537dd51e2bdb1de3c58fff9b2a861d0d5266baa1f37d84d` |
| `esbenp.prettier-vscode` | 11.0.0 | 11.0.3 | Marketplace | `a966c72d664e038d17a4d019da1a2f3e8f08cec4d88cc10d239358ffba9fba99` |
| `gitlab.gitlab-workflow` | 6.64.0 | 6.92.0 | Marketplace | `0d1d20e1a1c059e3eee3a20734fbf1ac50c11e86261cc9a2126e33e00bc1e264` |
| `growthjack.claude-code-usage` | 2.3.0 | 2.4.1 | Marketplace | `31824cde04a1025cd233a5ae853716677194c26556254c01c7b07af29ee12f19` |
| `mechatroner.rainbow-csv` | 3.23.0 | 3.24.1 | Marketplace | `c59a4aea924d5e7c6e75abb32628448bd5404915e2f3dfa19fbbdf177dea4606` |
| `ms-python.autopep8` | 2025.3.11811013 | 2026.4.0 | Marketplace | `a6bda5216055d54c9ad3d94c6bc057cd54418cfe4d47399b92e2ea1701b0abf5` |
| `ms-python.debugpy` | 2025.15.2025100201 | 2026.6.0 | Marketplace | `3ae417f78bce17992b9e0efba160a43a85a8b695bd387e150d4df24e366c7b01` |
| `ms-python.python` | 2025.17.2025100201 | 2026.4.0 | Marketplace | `1d07e60d5eab257ea5d691b26def3fff642b4d2c04fab94424e8b8fe25baf656` |
| `mtxr.sqltools` | 0.28.5 | 0.28.6 | Marketplace | `4a95451fe41ff6da67366e09e73ddf3a15b3cd83f42e49c3366f3c2473319085` |
| `mtxr.sqltools-driver-pg` | 0.5.7 | 0.5.8 | Marketplace | `1a3b7c63e89baf8df591b0e8f382084da71ddce30b07e44ca2aace6f3ed43f06` |
| `redhat.vscode-yaml` | 1.20.2025100808 | 1.25.0 | Marketplace | `2a833480d9754d83afb64df758c50735201d759b53cdb29be7b7a8114dca2ae4` |

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

SBOM lists only package.json manifests inside VSIX; bundled/minified deps unlisted. No Syft. VSIX SHA-256 pinned in `extensions.json`; build fails on mismatch (checked before extraction). Hashes were taken from the first CI build (run 38592558399), so they are trust-on-first-use, not independently verified. Platform: tries `linux-x64`, else universal; actual value in `manifest.json`.
